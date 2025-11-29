from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from app.database import get_db
from app.models import User
from app.schemas import (
    UserResponse,
    UserStorageResponse,
    UserUpdate,
    SubscriptionResponse,
)
from app.services import UserService
from app.api.deps import get_current_user, rate_limit_check_authenticated

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserResponse)
async def get_me(
    user: User = Depends(get_current_user),
    _: None = Depends(rate_limit_check_authenticated),
):
    """Get current user profile."""
    return user


@router.patch("/me", response_model=UserResponse)
async def update_me(
    data: UserUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """Update current user profile."""
    updated_user = await UserService.update_user(db, user, **data.model_dump(exclude_unset=True))
    return updated_user


@router.get("/me/storage", response_model=UserStorageResponse)
async def get_my_storage(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """Get current user's storage usage."""
    stats = await UserService.get_user_stats(db, user.id)
    
    storage_used_percent = 0.0
    if user.storage_quota_bytes > 0:
        storage_used_percent = (user.storage_used_bytes / user.storage_quota_bytes) * 100
    
    return UserStorageResponse(
        storage_used_bytes=user.storage_used_bytes,
        storage_quota_bytes=user.storage_quota_bytes,
        storage_used_percent=round(storage_used_percent, 2),
        addon_count=stats["addon_count"],
        version_count=stats["version_count"],
    )


@router.get("/me/subscription", response_model=Optional[SubscriptionResponse])
async def get_my_subscription(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """Get current user's active subscription."""
    from sqlalchemy import select
    from app.models import Subscription, SubscriptionStatus
    
    result = await db.execute(
        select(Subscription)
        .where(Subscription.user_id == user.id)
        .where(Subscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING, SubscriptionStatus.PAST_DUE]))
        .order_by(Subscription.created_at.desc())
        .limit(1)
    )
    subscription = result.scalar_one_or_none()
    
    if not subscription:
        return None
    
    return subscription


@router.get("/{discord_id}", response_model=UserResponse)
async def get_user_public(
    discord_id: str,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """Get public user profile by Discord ID."""
    from app.core.exceptions import NotFoundError
    
    user = await UserService.get_user_by_discord_id(db, discord_id)
    if not user:
        raise NotFoundError("User not found")
    
    # Return limited public info
    return UserResponse(
        id=user.id,
        discord_id=user.discord_id,
        discord_username=user.discord_username,
        discord_avatar=user.discord_avatar,
        email=None,  # Hide email
        subscription_tier=user.subscription_tier,
        storage_used_bytes=0,  # Hide storage
        storage_quota_bytes=0,
        is_admin=user.is_admin,
        created_at=user.created_at,
        last_login_at=None,
    )
