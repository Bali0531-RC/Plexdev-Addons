from typing import Optional, List
from fastapi import BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from app.models import Addon, Version, User
from app.schemas import AddonCreate, AddonUpdate
from app.utils import slugify
from app.core.exceptions import NotFoundError, ConflictError, ForbiddenError
from app.services.user_service import UserService


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
        """List addons with latest version info."""
        # Base query
        query = select(Addon)
        count_query = select(func.count(Addon.id))
        
        # Filters
        filters = []
        if public_only:
            filters.append(Addon.is_public == True)
            filters.append(Addon.is_active == True)
        if owner_id:
            filters.append(Addon.owner_id == owner_id)
        if search:
            filters.append(Addon.name.ilike(f"%{search}%"))
        
        if filters:
            query = query.where(and_(*filters))
            count_query = count_query.where(and_(*filters))
        
        # Get total count
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0
        
        # Get addons
        query = query.order_by(Addon.updated_at.desc()).offset(skip).limit(limit)
        result = await db.execute(query)
        addons = result.scalars().all()
        
        # Enrich with latest version and owner info
        enriched_addons = []
        for addon in addons:
            # Get owner
            owner_result = await db.execute(select(User).where(User.id == addon.owner_id))
            owner = owner_result.scalar_one_or_none()
            
            # Get latest version
            latest_version_result = await db.execute(
                select(Version)
                .where(Version.addon_id == addon.id)
                .order_by(Version.release_date.desc(), Version.created_at.desc())
                .limit(1)
            )
            latest_version = latest_version_result.scalar_one_or_none()
            
            # Get version count
            version_count_result = await db.execute(
                select(func.count(Version.id)).where(Version.addon_id == addon.id)
            )
            version_count = version_count_result.scalar() or 0
            
            enriched_addons.append({
                "id": addon.id,
                "slug": addon.slug,
                "name": addon.name,
                "description": addon.description,
                "homepage": addon.homepage,
                "external": addon.external,
                "is_active": addon.is_active,
                "is_public": addon.is_public,
                "owner_id": addon.owner_id,
                "owner_username": owner.discord_username if owner else None,
                "latest_version": latest_version.version if latest_version else None,
                "latest_release_date": latest_version.release_date if latest_version else None,
                "version_count": version_count,
                "created_at": addon.created_at,
                "updated_at": addon.updated_at,
            })
        
        return enriched_addons, total
    
    @staticmethod
    async def get_all_public_addons_for_json(db: AsyncSession) -> List[dict]:
        """Get all public addons with latest version for versions.json format."""
        result = await db.execute(
            select(Addon)
            .where(Addon.is_public == True)
            .where(Addon.is_active == True)
        )
        addons = result.scalars().all()
        
        addon_data = []
        for addon in addons:
            # Get owner
            owner_result = await db.execute(select(User).where(User.id == addon.owner_id))
            owner = owner_result.scalar_one_or_none()
            
            # Get latest version
            latest_version_result = await db.execute(
                select(Version)
                .where(Version.addon_id == addon.id)
                .order_by(Version.release_date.desc(), Version.created_at.desc())
                .limit(1)
            )
            latest_version = latest_version_result.scalar_one_or_none()
            
            if latest_version:
                addon_data.append({
                    "name": addon.name,
                    "version": latest_version.version,
                    "release_date": latest_version.release_date.isoformat(),
                    "download_url": latest_version.download_url,
                    "description": latest_version.description,
                    "breaking": latest_version.breaking,
                    "urgent": latest_version.urgent,
                    "external": addon.external,
                    "author": owner.discord_username if owner else None,
                    "homepage": addon.homepage,
                    "changelog": latest_version.changelog_url,
                })
        
        return addon_data
