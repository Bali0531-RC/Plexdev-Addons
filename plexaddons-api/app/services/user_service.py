from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from app.models import User, Addon, Version, SubscriptionTier, Ticket, TicketMessage, TicketAttachment
from app.config import get_settings

settings = get_settings()


def _calculate_string_size(s: Optional[str]) -> int:
    """Calculate byte size of a string."""
    if not s:
        return 0
    return len(s.encode('utf-8'))


class UserService:
    """Service for user management operations."""
    
    @staticmethod
    async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
        """Get user by ID."""
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_user_by_discord_id(db: AsyncSession, discord_id: str) -> Optional[User]:
        """Get user by Discord ID."""
        result = await db.execute(select(User).where(User.discord_id == discord_id))
        return result.scalar_one_or_none()
    
    @staticmethod
    async def update_user(db: AsyncSession, user: User, **kwargs) -> User:
        """Update user fields."""
        for key, value in kwargs.items():
            if hasattr(user, key) and value is not None:
                setattr(user, key, value)
        await db.commit()
        await db.refresh(user)
        return user
    
    @staticmethod
    async def calculate_storage_used(db: AsyncSession, user_id: int) -> int:
        """
        Calculate total storage used by a user from actual database content.
        
        Counts bytes from:
        - Addon: name, slug, description, homepage
        - Version: version, download_url, changelog_url, description, changelog_content
        - TicketAttachment: file_size (actual file storage)
        """
        total_bytes = 0
        
        # Fetch all addons with their versions for this user
        result = await db.execute(
            select(Addon)
            .options(selectinload(Addon.versions))
            .where(Addon.owner_id == user_id)
        )
        addons = result.scalars().all()
        
        for addon in addons:
            # Addon data
            total_bytes += _calculate_string_size(addon.name)
            total_bytes += _calculate_string_size(addon.slug)
            total_bytes += _calculate_string_size(addon.description)
            total_bytes += _calculate_string_size(addon.homepage)
            
            # Version data
            for version in addon.versions:
                total_bytes += _calculate_string_size(version.version)
                total_bytes += _calculate_string_size(version.download_url)
                total_bytes += _calculate_string_size(version.changelog_url)
                total_bytes += _calculate_string_size(version.description)
                total_bytes += _calculate_string_size(version.changelog_content)
        
        # Calculate ticket attachment storage
        # Sum file_size for all attachments on tickets owned by this user
        attachment_size_result = await db.execute(
            select(func.coalesce(func.sum(TicketAttachment.file_size), 0))
            .select_from(TicketAttachment)
            .join(TicketMessage, TicketAttachment.message_id == TicketMessage.id)
            .join(Ticket, TicketMessage.ticket_id == Ticket.id)
            .where(Ticket.user_id == user_id)
        )
        attachment_bytes = attachment_size_result.scalar() or 0
        total_bytes += attachment_bytes
        
        return total_bytes
    
    @staticmethod
    async def update_storage_used(db: AsyncSession, user: User) -> User:
        """Recalculate and update user's storage usage."""
        storage_used = await UserService.calculate_storage_used(db, user.id)
        user.storage_used_bytes = storage_used
        await db.commit()
        await db.refresh(user)
        return user
    
    @staticmethod
    async def get_user_stats(db: AsyncSession, user_id: int) -> dict:
        """Get user statistics."""
        # Count addons
        addon_count_result = await db.execute(
            select(func.count(Addon.id)).where(Addon.owner_id == user_id)
        )
        addon_count = addon_count_result.scalar() or 0
        
        # Count versions
        version_count_result = await db.execute(
            select(func.count(Version.id))
            .select_from(Version)
            .join(Addon, Version.addon_id == Addon.id)
            .where(Addon.owner_id == user_id)
        )
        version_count = version_count_result.scalar() or 0
        
        # Get storage used
        storage_used = await UserService.calculate_storage_used(db, user_id)
        
        return {
            "addon_count": addon_count,
            "version_count": version_count,
            "storage_used_bytes": storage_used,
        }
    
    @staticmethod
    def get_storage_quota_for_tier(tier: SubscriptionTier) -> int:
        """Get storage quota for a subscription tier."""
        quotas = {
            SubscriptionTier.FREE: settings.storage_quota_free,
            SubscriptionTier.PRO: settings.storage_quota_pro,
            SubscriptionTier.PREMIUM: settings.storage_quota_premium,
        }
        return quotas.get(tier, settings.storage_quota_free)
    
    @staticmethod
    def get_version_limit_for_tier(tier: SubscriptionTier) -> int:
        """Get version history limit for a subscription tier."""
        limits = {
            SubscriptionTier.FREE: settings.version_limit_free,
            SubscriptionTier.PRO: settings.version_limit_pro,
            SubscriptionTier.PREMIUM: settings.version_limit_premium,
        }
        return limits.get(tier, settings.version_limit_free)
    
    @staticmethod
    async def update_user_tier(db: AsyncSession, user: User, tier: SubscriptionTier) -> User:
        """Update user's subscription tier and quota."""
        user.subscription_tier = tier
        user.storage_quota_bytes = UserService.get_storage_quota_for_tier(tier)
        await db.commit()
        await db.refresh(user)
        return user
    
    @staticmethod
    async def list_users(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 50,
        search: Optional[str] = None,
        tier: Optional[SubscriptionTier] = None,
        is_admin: Optional[bool] = None,
    ) -> tuple[List[User], int]:
        """List users with optional filters."""
        query = select(User)
        count_query = select(func.count(User.id))
        
        if search:
            search_filter = User.discord_username.ilike(f"%{search}%")
            query = query.where(search_filter)
            count_query = count_query.where(search_filter)
        
        if tier:
            query = query.where(User.subscription_tier == tier)
            count_query = count_query.where(User.subscription_tier == tier)
        
        if is_admin is not None:
            query = query.where(User.is_admin == is_admin)
            count_query = count_query.where(User.is_admin == is_admin)
        
        # Get total count
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0
        
        # Get users
        query = query.order_by(User.created_at.desc()).offset(skip).limit(limit)
        result = await db.execute(query)
        users = result.scalars().all()
        
        return list(users), total
