from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional
from app.database import get_db
from app.models import User, Subscription, SubscriptionStatus, PaymentProvider
from app.schemas import (
    UserResponse,
    UserStorageResponse,
    UserUpdate,
    SubscriptionResponse,
)
from app.services import UserService, StripeService, PayPalService
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
    """Get current user's storage usage (calculated live from database content)."""
    stats = await UserService.get_user_stats(db, user.id)
    
    # Calculate storage live from actual data
    storage_used = stats["storage_used_bytes"]
    
    storage_used_percent = 0.0
    if user.storage_quota_bytes > 0:
        storage_used_percent = (storage_used / user.storage_quota_bytes) * 100
    
    return UserStorageResponse(
        storage_used_bytes=storage_used,
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


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_my_account(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """
    Delete current user's account permanently.
    
    This will:
    1. Cancel any active subscriptions (Stripe/PayPal)
    2. Delete all user data (addons, versions, tickets, etc.)
    3. Remove the user account
    
    This action is IRREVERSIBLE.
    """
    # Prevent last admin from deleting themselves
    if user.is_admin:
        admin_count_result = await db.execute(
            select(func.count(User.id)).where(User.is_admin == True)
        )
        admin_count = admin_count_result.scalar() or 0
        if admin_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot delete the last admin account. Promote another user to admin first."
            )
    
    # First, cancel any active subscriptions with payment providers
    result = await db.execute(
        select(Subscription)
        .where(Subscription.user_id == user.id)
        .where(Subscription.status.in_([
            SubscriptionStatus.ACTIVE,
            SubscriptionStatus.TRIALING,
            SubscriptionStatus.PAST_DUE
        ]))
    )
    active_subscriptions = result.scalars().all()
    
    for subscription in active_subscriptions:
        try:
            if subscription.provider == PaymentProvider.STRIPE:
                # Cancel Stripe subscription
                import stripe
                from app.config import get_settings
                settings = get_settings()
                stripe.api_key = settings.stripe_secret_key
                stripe.Subscription.cancel(subscription.provider_subscription_id)
            elif subscription.provider == PaymentProvider.PAYPAL:
                # Cancel PayPal subscription
                await PayPalService.cancel_subscription(
                    subscription.provider_subscription_id,
                    reason="Account deleted by user"
                )
        except Exception as e:
            # Log but don't fail - subscription might already be canceled
            print(f"Warning: Failed to cancel subscription {subscription.id}: {e}")
    
    # Delete the user - CASCADE will handle related records
    await db.delete(user)
    await db.commit()
    
    return None
