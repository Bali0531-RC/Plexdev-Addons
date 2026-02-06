from typing import Optional, List
import json
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from app.models import User, Addon, Version, SubscriptionTier, Ticket, TicketMessage, TicketAttachment
from app.config import get_settings

settings = get_settings()


def sanitize_ilike_pattern(search: str) -> str:
    """Escape special characters in ILIKE patterns to prevent SQL injection."""
    return search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


# Available badges in the system
AVAILABLE_BADGES = {
    "supporter": "💎 Supporter",  # Pro or Premium subscriber
    "premium": "👑 Premium",  # Premium subscriber
    "early_adopter": "🌟 Early Adopter",  # Users who joined during alpha/beta
    "beta_tester": "🧪 Beta Tester",  # Users who joined during beta phase
    "addon_creator": "🔧 Addon Creator",  # Has published an addon
    "contributor": "🤝 Contributor",  # Community contributor
    "staff": "🛡️ Staff",  # PlexAddons team member
}

# Cutoff date for early adopter/beta tester badges (timezone-aware)
EARLY_ADOPTER_CUTOFF = datetime(2025, 12, 20, tzinfo=timezone.utc)


def _calculate_string_size(s: Optional[str]) -> int:
    """Calculate byte size of a string."""
    if not s:
        return 0
    return len(s.encode('utf-8'))


class UserService:
    """Service for user management operations."""

    # Allowlist of fields that can be updated via update_user
    UPDATABLE_FIELDS = {
        "discord_username", "discord_avatar", "email", "bio", "website",
        "github_username", "twitter_username", "profile_slug", "profile_public",
        "show_addons", "banner_url", "accent_color",
    }

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
        """Update user fields. Only allows fields in UPDATABLE_FIELDS."""
        for key, value in kwargs.items():
            if key not in UserService.UPDATABLE_FIELDS:
                continue
            if value is not None:
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
        old_tier = user.subscription_tier
        user.subscription_tier = tier
        user.storage_quota_bytes = UserService.get_storage_quota_for_tier(tier)
        
        # Update badges based on tier
        await UserService.update_subscription_badges(db, user, tier)
        
        await db.commit()
        await db.refresh(user)
        return user
    
    @staticmethod
    def _parse_badges(user: User) -> List[str]:
        """Parse badges from JSON string to list."""
        if not user.badges:
            return []
        try:
            badges = json.loads(user.badges)
            return badges if isinstance(badges, list) else []
        except (json.JSONDecodeError, TypeError):
            return []
    
    @staticmethod
    def _save_badges(user: User, badges: List[str]) -> None:
        """Save badges list as JSON string."""
        user.badges = json.dumps(list(set(badges)))  # Remove duplicates
    
    @staticmethod
    async def get_badges(db: AsyncSession, user: User) -> List[str]:
        """Get user's badges as a list."""
        return UserService._parse_badges(user)
    
    @staticmethod
    async def add_badge(db: AsyncSession, user: User, badge: str) -> User:
        """Add a badge to a user."""
        badges = UserService._parse_badges(user)
        if badge not in badges:
            badges.append(badge)
            UserService._save_badges(user, badges)
            await db.commit()
            await db.refresh(user)
        return user
    
    @staticmethod
    async def remove_badge(db: AsyncSession, user: User, badge: str) -> User:
        """Remove a badge from a user."""
        badges = UserService._parse_badges(user)
        if badge in badges:
            badges.remove(badge)
            UserService._save_badges(user, badges)
            await db.commit()
            await db.refresh(user)
        return user
    
    @staticmethod
    async def update_subscription_badges(db: AsyncSession, user: User, tier: SubscriptionTier) -> User:
        """Update badges based on subscription tier."""
        badges = UserService._parse_badges(user)
        
        # Remove subscription-related badges first
        badges = [b for b in badges if b not in ["supporter", "premium"]]
        
        # Add appropriate badges based on tier
        if tier == SubscriptionTier.PRO:
            badges.append("supporter")
        elif tier == SubscriptionTier.PREMIUM:
            badges.append("supporter")
            badges.append("premium")
        
        UserService._save_badges(user, badges)
        return user
    
    @staticmethod
    async def check_and_add_creator_badge(db: AsyncSession, user: User) -> User:
        """Add addon_creator badge if user has published addons."""
        badges = UserService._parse_badges(user)
        if "addon_creator" not in badges:
            # Check if user has any public addons
            addon_count = await db.execute(
                select(func.count(Addon.id))
                .where(Addon.owner_id == user.id)
                .where(Addon.is_public == True)
            )
            count = addon_count.scalar() or 0
            if count > 0:
                badges.append("addon_creator")
                UserService._save_badges(user, badges)
                await db.commit()
                await db.refresh(user)
        return user
    
    @staticmethod
    async def sync_automatic_badges(db: AsyncSession, user: User, commit: bool = True) -> User:
        """
        Sync all automatic badges for a user:
        - early_adopter & beta_tester: Users who registered before 2025-12-20
        - addon_creator: Users who have at least one public addon
        - supporter/premium: Based on subscription tier
        """
        badges = UserService._parse_badges(user)
        changed = False
        
        # Check early adopter / beta tester (users before cutoff date)
        if user.created_at and user.created_at < EARLY_ADOPTER_CUTOFF:
            if "early_adopter" not in badges:
                badges.append("early_adopter")
                changed = True
            if "beta_tester" not in badges:
                badges.append("beta_tester")
                changed = True
        
        # Check addon creator
        if "addon_creator" not in badges:
            addon_count = await db.execute(
                select(func.count(Addon.id))
                .where(Addon.owner_id == user.id)
                .where(Addon.is_public == True)
            )
            count = addon_count.scalar() or 0
            if count > 0:
                badges.append("addon_creator")
                changed = True
        
        # Sync subscription badges
        has_supporter = "supporter" in badges
        has_premium = "premium" in badges
        
        if user.subscription_tier == SubscriptionTier.PRO:
            if not has_supporter:
                badges.append("supporter")
                changed = True
            if has_premium:
                badges.remove("premium")
                changed = True
        elif user.subscription_tier == SubscriptionTier.PREMIUM:
            if not has_supporter:
                badges.append("supporter")
                changed = True
            if not has_premium:
                badges.append("premium")
                changed = True
        else:  # FREE tier
            if has_supporter:
                badges.remove("supporter")
                changed = True
            if has_premium:
                badges.remove("premium")
                changed = True
        
        if changed:
            UserService._save_badges(user, badges)
            if commit:
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
            safe_search = sanitize_ilike_pattern(search)
            search_filter = User.discord_username.ilike(f"%{safe_search}%")
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
