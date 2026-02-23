"""Service for creating in-app notifications."""

from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Notification, NotificationType


class NotificationService:
    """Service for creating and managing notifications."""

    @staticmethod
    async def create(
        db: AsyncSession,
        user_id: int,
        type: NotificationType,
        title: str,
        message: str | None = None,
        link: str | None = None,
    ) -> Notification:
        """Create a notification for a user."""
        notification = Notification(
            user_id=user_id,
            type=type,
            title=title,
            message=message,
            link=link,
        )
        db.add(notification)
        await db.commit()
        await db.refresh(notification)
        return notification

    @staticmethod
    async def notify_addon_update(
        db: AsyncSession,
        user_id: int,
        addon_name: str,
        addon_slug: str,
        new_version: str,
    ) -> Notification:
        """Notify user about a new version of a starred addon."""
        return await NotificationService.create(
            db,
            user_id=user_id,
            type=NotificationType.ADDON_UPDATE,
            title=f"{addon_name} updated to v{new_version}",
            message=f"A new version of {addon_name} is available.",
            link=f"/addons/{addon_slug}",
        )

    @staticmethod
    async def notify_review_received(
        db: AsyncSession,
        owner_id: int,
        addon_name: str,
        addon_slug: str,
        reviewer_name: str,
        rating: int,
    ) -> Notification:
        """Notify addon owner about a new review."""
        return await NotificationService.create(
            db,
            user_id=owner_id,
            type=NotificationType.REVIEW_RECEIVED,
            title=f"New {rating}\u2605 review on {addon_name}",
            message=f"{reviewer_name} left a review on {addon_name}.",
            link=f"/addons/{addon_slug}",
        )

    @staticmethod
    async def notify_star_received(
        db: AsyncSession,
        owner_id: int,
        addon_name: str,
        addon_slug: str,
        star_user_name: str,
    ) -> Notification:
        """Notify addon owner when someone stars their addon."""
        return await NotificationService.create(
            db,
            user_id=owner_id,
            type=NotificationType.STAR_RECEIVED,
            title=f"{star_user_name} starred {addon_name}",
            link=f"/addons/{addon_slug}",
        )

    @staticmethod
    async def notify_addon_verified(
        db: AsyncSession,
        owner_id: int,
        addon_name: str,
        addon_slug: str,
    ) -> Notification:
        """Notify addon owner when their addon is verified."""
        return await NotificationService.create(
            db,
            user_id=owner_id,
            type=NotificationType.ADDON_VERIFIED,
            title=f"{addon_name} has been verified!",
            message="Your addon has been verified by the PlexDevelopment team.",
            link=f"/addons/{addon_slug}",
        )

    @staticmethod
    async def notify_system(
        db: AsyncSession,
        user_id: int,
        title: str,
        message: str | None = None,
        link: str | None = None,
    ) -> Notification:
        """Create a system notification."""
        return await NotificationService.create(
            db,
            user_id=user_id,
            type=NotificationType.SYSTEM,
            title=title,
            message=message,
            link=link,
        )
