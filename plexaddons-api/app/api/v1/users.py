from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from typing import Optional
import secrets
from datetime import datetime
from app.database import get_db
from app.models import User, Subscription, SubscriptionStatus, PaymentProvider, SubscriptionTier, Addon
from app.schemas import (
    UserResponse,
    UserStorageResponse,
    UserUpdate,
    SubscriptionResponse,
    UserProfileUpdate,
    UserPublicProfile,
    ApiKeyCreate,
    ApiKeyResponse,
    AddonResponse,
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


# ============== Profile Endpoints ==============

@router.patch("/me/profile", response_model=UserResponse)
async def update_my_profile(
    data: UserProfileUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """
    Update current user's profile.
    
    Tier restrictions:
    - profile_slug: Pro and Premium only (Free users use Discord ID)
    - banner_url: Premium only
    - accent_color: Pro and Premium only
    """
    update_data = data.model_dump(exclude_unset=True)
    
    # Validate tier restrictions
    if "profile_slug" in update_data and update_data["profile_slug"] is not None:
        if user.subscription_tier == SubscriptionTier.FREE:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Custom profile URLs require Pro or Premium subscription"
            )
        # Check slug uniqueness
        existing = await db.execute(
            select(User).where(
                User.profile_slug == update_data["profile_slug"],
                User.id != user.id
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This profile URL is already taken"
            )
    
    if "banner_url" in update_data and update_data["banner_url"] is not None:
        if user.subscription_tier != SubscriptionTier.PREMIUM:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Custom banners require Premium subscription"
            )
    
    if "accent_color" in update_data and update_data["accent_color"] is not None:
        if user.subscription_tier == SubscriptionTier.FREE:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Custom accent colors require Pro or Premium subscription"
            )
    
    # Apply updates
    for key, value in update_data.items():
        setattr(user, key, value)
    
    await db.commit()
    await db.refresh(user)
    
    return user


@router.get("/me/api-key", response_model=ApiKeyResponse)
async def get_my_api_key(
    user: User = Depends(get_current_user),
    _: None = Depends(rate_limit_check_authenticated),
):
    """Get current user's API key status."""
    masked_key = None
    if user.api_key:
        # Show first 6 and last 4 characters: pa_xxxx...xxxx
        masked_key = f"{user.api_key[:6]}...{user.api_key[-4:]}"
    
    return ApiKeyResponse(
        has_api_key=user.api_key is not None,
        created_at=user.api_key_created_at,
        masked_key=masked_key
    )


@router.post("/me/api-key", response_model=ApiKeyCreate)
async def create_my_api_key(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """
    Generate a new API key for the current user.
    
    Requirements:
    - Premium subscription required
    - Replaces any existing API key
    
    The full API key is only shown once!
    """
    if user.subscription_tier != SubscriptionTier.PREMIUM:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API keys require Premium subscription"
        )
    
    # Generate new API key with pa_ prefix
    api_key = f"pa_{secrets.token_hex(32)}"
    now = datetime.utcnow()
    
    user.api_key = api_key
    user.api_key_created_at = now
    
    await db.commit()
    
    return ApiKeyCreate(
        api_key=api_key,
        created_at=now
    )


@router.delete("/me/api-key", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_my_api_key(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """Revoke the current user's API key."""
    if not user.api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No API key to revoke"
        )
    
    user.api_key = None
    user.api_key_created_at = None
    
    await db.commit()
    
    return None
