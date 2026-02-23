from typing import Optional, List
from fastapi import BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, literal_column
from sqlalchemy.orm import aliased
from app.models import Addon, Version, User
from app.schemas import AddonCreate, AddonUpdate
from app.utils import slugify
from app.core.exceptions import NotFoundError, ConflictError, ForbiddenError
from app.services.user_service import UserService


def sanitize_ilike_pattern(search: str) -> str:
    """Escape special characters in ILIKE patterns to prevent SQL injection."""
    return search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class AddonService:
    """Service for addon management operations."""
    
    @staticmethod
    async def get_addon_by_id(db: AsyncSession, addon_id: int) -> Optional[Addon]:
        """Get addon by ID."""
        result = await db.execute(select(Addon).where(Addon.id == addon_id))
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_addon_by_slug(db: AsyncSession, slug: str) -> Optional[Addon]:
        """Get addon by slug."""
        result = await db.execute(select(Addon).where(Addon.slug == slug))
        return result.scalar_one_or_none()
    
    @staticmethod
    async def create_addon(
        db: AsyncSession, 
        owner: User, 
        data: AddonCreate,
        background_tasks: Optional[BackgroundTasks] = None
    ) -> Addon:
        """Create a new addon."""
        from app.services.email_service import email_service
        
        slug = slugify(data.name)
        
        # Check if slug already exists
        existing = await AddonService.get_addon_by_slug(db, slug)
        if existing:
            # Append owner's discord_id to make unique
            slug = f"{slug}-{owner.discord_id[:8]}"
            existing = await AddonService.get_addon_by_slug(db, slug)
            if existing:
                raise ConflictError(f"Addon with slug '{slug}' already exists")
        
        addon = Addon(
            owner_id=owner.id,
            name=data.name,
            slug=slug,
            description=data.description,
            homepage=data.homepage,
            external=data.external,
        )
        db.add(addon)
        await db.commit()
        await db.refresh(addon)
        
        # Send admin notification for new addon
        if background_tasks:
            background_tasks.add_task(
                email_service.send_admin_new_addon,
                owner, addon.name, addon.description or ""
            )
        
        # Check and add addon_creator badge if this is user's first public addon
        if addon.is_public:
            await UserService.check_and_add_creator_badge(db, owner)
        
        return addon
    
    @staticmethod
    async def update_addon(
        db: AsyncSession,
        addon: Addon,
        user: User,
        data: AddonUpdate,
    ) -> Addon:
        """Update an addon."""
        # Check ownership (unless admin)
        if addon.owner_id != user.id and not user.is_admin:
            raise ForbiddenError("You don't have permission to update this addon")
        
        # Update fields
        update_data = data.model_dump(exclude_unset=True)
        
        # If name changed, update slug
        if "name" in update_data and update_data["name"]:
            new_slug = slugify(update_data["name"])
            if new_slug != addon.slug:
                existing = await AddonService.get_addon_by_slug(db, new_slug)
                if existing and existing.id != addon.id:
                    new_slug = f"{new_slug}-{addon.owner_id}"
                addon.slug = new_slug
        
        for key, value in update_data.items():
            if key != "name" or value:  # Skip empty name
                setattr(addon, key, value)
        
        await db.commit()
        await db.refresh(addon)
        return addon
    
    @staticmethod
    async def delete_addon(db: AsyncSession, addon: Addon, user: User) -> None:
        """Delete an addon."""
        # Check ownership (unless admin)
        if addon.owner_id != user.id and not user.is_admin:
            raise ForbiddenError("You don't have permission to delete this addon")
        
        await db.delete(addon)
        await db.commit()
    
    @staticmethod
    async def list_addons(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 20,
        owner_id: Optional[int] = None,
        search: Optional[str] = None,
        public_only: bool = True,
    ) -> tuple[List[dict], int]:
        """List addons with latest version info using optimized JOINs."""
        # Base filters
        filters = []
        if public_only:
            filters.append(Addon.is_public == True)
            filters.append(Addon.is_active == True)
        if owner_id:
            filters.append(Addon.owner_id == owner_id)
        if search:
            safe_search = sanitize_ilike_pattern(search)
            filters.append(Addon.name.ilike(f"%{safe_search}%"))
        
        # Get total count
        count_query = select(func.count(Addon.id))
        if filters:
            count_query = count_query.where(and_(*filters))
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0
        
        # Subquery for latest version per addon
        latest_version_sq = (
            select(
                Version.addon_id,
                Version.version.label("latest_version"),
                Version.release_date.label("latest_release_date"),
                func.row_number().over(
                    partition_by=Version.addon_id,
                    order_by=[Version.release_date.desc(), Version.created_at.desc()]
                ).label("rn")
            )
            .subquery("latest_v")
        )
        
        # Subquery for version count per addon
        version_count_sq = (
            select(
                Version.addon_id,
                func.count(Version.id).label("version_count")
            )
            .group_by(Version.addon_id)
            .subquery("v_count")
        )
        
        # Main query with JOINs
        query = (
            select(
                Addon,
                User.discord_username.label("owner_username"),
                User.discord_id.label("owner_discord_id"),
                latest_version_sq.c.latest_version,
                latest_version_sq.c.latest_release_date,
                func.coalesce(version_count_sq.c.version_count, 0).label("version_count"),
            )
            .join(User, User.id == Addon.owner_id, isouter=True)
            .join(
                latest_version_sq,
                and_(
                    latest_version_sq.c.addon_id == Addon.id,
                    latest_version_sq.c.rn == 1,
                ),
                isouter=True,
            )
            .join(
                version_count_sq,
                version_count_sq.c.addon_id == Addon.id,
                isouter=True,
            )
        )
        
        if filters:
            query = query.where(and_(*filters))
        
        query = query.order_by(Addon.updated_at.desc()).offset(skip).limit(limit)
        result = await db.execute(query)
        rows = result.all()
        
        enriched_addons = []
        for row in rows:
            addon = row[0]
            enriched_addons.append({
                "id": addon.id,
                "slug": addon.slug,
                "name": addon.name,
                "description": addon.description,
                "homepage": addon.homepage,
                "external": addon.external,
                "tags": addon.tags or [],
                "is_active": addon.is_active,
                "is_public": addon.is_public,
                "verified": addon.verified,
                "owner_id": addon.owner_id,
                "owner_username": row.owner_username,
                "owner_discord_id": row.owner_discord_id,
                "latest_version": row.latest_version,
                "latest_release_date": row.latest_release_date,
                "version_count": row.version_count,
                "created_at": addon.created_at,
                "updated_at": addon.updated_at,
            })
        
        return enriched_addons, total
    
    @staticmethod
    async def get_all_public_addons_for_json(db: AsyncSession, client_ip_hash: str = None) -> List[dict]:
        """
        Get all public addons with latest version for versions.json format.
        Uses optimized JOINs instead of per-addon queries.
        
        Args:
            client_ip_hash: Optional hashed IP for A/B rollout consistency.
                           If provided, respects rollout_percentage.
        """
        # Fetch all public addons with owner info in a single query
        addons_query = (
            select(Addon, User.discord_username.label("owner_username"))
            .join(User, User.id == Addon.owner_id, isouter=True)
            .where(Addon.is_public == True)
            .where(Addon.is_active == True)
        )
        addons_result = await db.execute(addons_query)
        addon_rows = addons_result.all()
        
        if not addon_rows:
            return []
        
        # Collect addon IDs
        addon_ids = [row[0].id for row in addon_rows]
        
        # Fetch all published versions for these addons in a single query
        versions_result = await db.execute(
            select(Version)
            .where(Version.addon_id.in_(addon_ids))
            .where(Version.is_published == True)
            .order_by(Version.addon_id, Version.release_date.desc(), Version.created_at.desc())
        )
        all_versions = versions_result.scalars().all()
        
        # Group versions by addon_id
        versions_by_addon: dict[int, list] = {}
        for v in all_versions:
            versions_by_addon.setdefault(v.addon_id, []).append(v)
        
        addon_data = []
        for row in addon_rows:
            addon = row[0]
            owner_username = row.owner_username
            versions = versions_by_addon.get(addon.id, [])
            
            # Find the latest version this user is eligible for (based on rollout)
            latest_version = None
            for version in versions:
                if version.rollout_percentage >= 100:
                    latest_version = version
                    break
                elif client_ip_hash and version.rollout_percentage > 0:
                    # Use consistent hash to determine if user is in rollout
                    hash_value = int(client_ip_hash[:8], 16) % 100
                    if hash_value < version.rollout_percentage:
                        latest_version = version
                        break
            
            # Fallback to first fully-rolled-out published version
            if not latest_version:
                for v in versions:
                    if v.rollout_percentage >= 100:
                        latest_version = v
                        break
            
            if latest_version:
                addon_data.append({
                    "name": addon.name,
                    "slug": addon.slug,
                    "version": latest_version.version,
                    "release_date": latest_version.release_date.isoformat(),
                    "download_url": latest_version.download_url,
                    "description": latest_version.description,
                    "breaking": latest_version.breaking,
                    "urgent": latest_version.urgent,
                    "external": addon.external,
                    "author": owner_username,
                    "homepage": addon.homepage,
                    "changelog": latest_version.changelog_url,
                    "tags": addon.tags or [],
                })
        
        return addon_data
