from typing import Optional, List
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from app.models import Version, Addon, User, SubscriptionTier
from app.schemas import VersionCreate, VersionUpdate
from app.services.user_service import UserService
from app.core.exceptions import (
    NotFoundError,
    ForbiddenError,
    StorageQuotaExceededError,
    VersionLimitExceededError,
    BadRequestError,
)
from app.utils import calculate_storage_size
from app.utils.semver import is_valid_version


class VersionService:
    """Service for version management operations."""
    
    @staticmethod
    async def get_version_by_id(db: AsyncSession, version_id: int) -> Optional[Version]:
        """Get version by ID."""
        result = await db.execute(select(Version).where(Version.id == version_id))
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_version_by_addon_and_version(
        db: AsyncSession,
        addon_id: int,
        version_str: str,
    ) -> Optional[Version]:
        """Get a specific version of an addon."""
        result = await db.execute(
            select(Version)
            .where(Version.addon_id == addon_id)
            .where(Version.version == version_str)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_latest_version(db: AsyncSession, addon_id: int) -> Optional[Version]:
        """Get the latest version of an addon."""
        result = await db.execute(
            select(Version)
            .where(Version.addon_id == addon_id)
            .order_by(Version.release_date.desc(), Version.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_version_count(db: AsyncSession, addon_id: int) -> int:
        """Get the number of versions for an addon."""
        result = await db.execute(
            select(func.count(Version.id)).where(Version.addon_id == addon_id)
        )
        return result.scalar() or 0
    
    @staticmethod
    async def check_version_limit(
        db: AsyncSession,
        addon: Addon,
        user: User,
    ) -> bool:
        """Check if user can add another version."""
        limit = UserService.get_version_limit_for_tier(user.subscription_tier)
        if limit == -1:  # Unlimited
            return True
        
        current_count = await VersionService.get_version_count(db, addon.id)
        return current_count < limit
    
    @staticmethod
    async def check_storage_quota(
        db: AsyncSession,
        user: User,
        new_content_size: int,
        existing_size: int = 0,
    ) -> bool:
        """Check if user has storage quota for new content."""
        current_usage = await UserService.calculate_storage_used(db, user.id)
        # Subtract existing size if updating
        current_usage -= existing_size
        return (current_usage + new_content_size) <= user.storage_quota_bytes
    
    @staticmethod
    async def cleanup_old_versions(
        db: AsyncSession,
        addon: Addon,
        user: User,
    ) -> int:
        """Remove oldest versions beyond the limit. Returns number deleted."""
        limit = UserService.get_version_limit_for_tier(user.subscription_tier)
        if limit == -1:  # Unlimited
            return 0
        
        # Get IDs of versions to keep (newest ones up to limit)
        keep_result = await db.execute(
            select(Version.id)
            .where(Version.addon_id == addon.id)
            .order_by(Version.release_date.desc(), Version.created_at.desc())
            .limit(limit)
        )
        keep_ids = [row[0] for row in keep_result.all()]
        
        if not keep_ids:
            return 0
        
        # Delete versions not in keep list
        delete_result = await db.execute(
            delete(Version)
            .where(Version.addon_id == addon.id)
            .where(Version.id.notin_(keep_ids))
        )
        
        deleted_count = delete_result.rowcount
        await db.commit()
        
        # Update user storage
        await UserService.update_storage_used(db, user)
        
        return deleted_count
    
    @staticmethod
    async def create_version(
        db: AsyncSession,
        addon: Addon,
        user: User,
        data: VersionCreate,
    ) -> Version:
        """Create a new version for an addon."""
        # Validate version string
        if not is_valid_version(data.version):
            raise BadRequestError(f"Invalid version format: {data.version}. Use semver format (e.g., 1.0.0)")
        
        # Check if version already exists
        existing = await VersionService.get_version_by_addon_and_version(
            db, addon.id, data.version
        )
        if existing:
            raise BadRequestError(f"Version {data.version} already exists for this addon")
        
        # Calculate storage size
        content_size = calculate_storage_size(data.changelog_content or "")
        content_size += calculate_storage_size(data.description or "")
        
        # Check storage quota
        if not await VersionService.check_storage_quota(db, user, content_size):
            raise StorageQuotaExceededError()
        
        # Check version limit and cleanup if needed
        if not await VersionService.check_version_limit(db, addon, user):
            # Auto-cleanup oldest version to make room
            await VersionService.cleanup_old_versions(db, addon, user)
            
            # Re-check limit after cleanup
            if not await VersionService.check_version_limit(db, addon, user):
                raise VersionLimitExceededError()
        
        # Create version
        version = Version(
            addon_id=addon.id,
            version=data.version,
            release_date=data.release_date or date.today(),
            download_url=data.download_url,
            description=data.description,
            changelog_url=data.changelog_url,
            changelog_content=data.changelog_content,
            breaking=data.breaking,
            urgent=data.urgent,
            storage_size_bytes=content_size,
        )
        db.add(version)
        await db.commit()
        await db.refresh(version)
        
        # Update addon's updated_at
        addon.updated_at = version.created_at
        await db.commit()
        
        # Update user storage
        await UserService.update_storage_used(db, user)
        
        return version
    
    @staticmethod
    async def update_version(
        db: AsyncSession,
        version: Version,
        user: User,
        data: VersionUpdate,
    ) -> Version:
        """Update a version."""
        # Calculate new storage size
        new_content = data.changelog_content if data.changelog_content is not None else version.changelog_content
        new_description = data.description if data.description is not None else version.description
        
        new_size = calculate_storage_size(new_content or "")
        new_size += calculate_storage_size(new_description or "")
        
        # Check storage quota (considering current size)
        size_diff = new_size - version.storage_size_bytes
        if size_diff > 0:
            if not await VersionService.check_storage_quota(db, user, size_diff):
                raise StorageQuotaExceededError()
        
        # Update fields
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(version, key, value)
        
        version.storage_size_bytes = new_size
        
        await db.commit()
        await db.refresh(version)
        
        # Update user storage
        await UserService.update_storage_used(db, user)
        
        return version
    
    @staticmethod
    async def delete_version(
        db: AsyncSession,
        version: Version,
        user: User,
    ) -> None:
        """Delete a version."""
        await db.delete(version)
        await db.commit()
        
        # Update user storage
        await UserService.update_storage_used(db, user)
    
    @staticmethod
    async def list_versions(
        db: AsyncSession,
        addon_id: int,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[List[Version], int]:
        """List versions for an addon."""
        # Get total count
        count_result = await db.execute(
            select(func.count(Version.id)).where(Version.addon_id == addon_id)
        )
        total = count_result.scalar() or 0
        
        # Get versions
        result = await db.execute(
            select(Version)
            .where(Version.addon_id == addon_id)
            .order_by(Version.release_date.desc(), Version.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        versions = result.scalars().all()
        
        return list(versions), total
