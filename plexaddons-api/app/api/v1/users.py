from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from typing import Optional
from datetime import datetime, timezone
from app.database import get_db
from app.models import User, Subscription, SubscriptionStatus, PaymentProvider, SubscriptionTier, Addon
from app.schemas import (
    UserResponse,
    UserStorageResponse,
    UserUpdate,
    SubscriptionResponse,
    UserProfileUpdate,
    UserPublicProfile,
    AddonResponse,
    WebhookConfigUpdate,
    WebhookConfigResponse,
    WebhookSecretResponse,
    WebhookTestResponse,
)
from app.services import UserService, StripeService, PayPalService, WebhookService, webhook_service
from app.api.deps import get_current_user, rate_limit_check_authenticated, get_effective_tier

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
    effective_tier = get_effective_tier(user)
    
    # Validate tier restrictions
    if "profile_slug" in update_data and update_data["profile_slug"] is not None:
        if effective_tier == SubscriptionTier.FREE:
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
        if effective_tier != SubscriptionTier.PREMIUM:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Custom banners require Premium subscription"
            )
        # Validate banner URL format
        banner = update_data["banner_url"]
        if not banner.startswith(("https://", "http://")):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Banner URL must start with https:// or http://"
            )
    
    if "accent_color" in update_data and update_data["accent_color"] is not None:
        if effective_tier == SubscriptionTier.FREE:
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




# ============== Webhook Endpoints ==============

@router.get("/me/webhook", response_model=WebhookConfigResponse)
async def get_my_webhook_config(
    user: User = Depends(get_current_user),
    _: None = Depends(rate_limit_check_authenticated),
):
    """Get current user's webhook configuration."""
    masked_secret = None
    if user.webhook_secret:
        # Show first 6 and last 4 characters: wh_xxxx...xxxx
        masked_secret = f"wh_{user.webhook_secret[:4]}...{user.webhook_secret[-4:]}"
    
    return WebhookConfigResponse(
        webhook_url=user.webhook_url,
        webhook_enabled=user.webhook_enabled or False,
        has_secret=user.webhook_secret is not None,
        masked_secret=masked_secret,
    )


@router.patch("/me/webhook", response_model=WebhookConfigResponse)
async def update_my_webhook_config(
    data: WebhookConfigUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """
    Update webhook configuration.
    
    Requirements:
    - Premium subscription required
    """
    effective_tier = get_effective_tier(user)
    if effective_tier != SubscriptionTier.PREMIUM:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Webhook notifications require Premium subscription"
        )
    
    update_data = data.model_dump(exclude_unset=True)
    
    # Validate URL if provided
    if "webhook_url" in update_data and update_data["webhook_url"]:
        url = update_data["webhook_url"]
        if not url.startswith(("http://", "https://")):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Webhook URL must start with http:// or https://"
            )
    
    # Apply updates
    for key, value in update_data.items():
        setattr(user, key, value)
    
    await db.commit()
    await db.refresh(user)
    
    masked_secret = None
    if user.webhook_secret:
        masked_secret = f"wh_{user.webhook_secret[:4]}...{user.webhook_secret[-4:]}"
    
    return WebhookConfigResponse(
        webhook_url=user.webhook_url,
        webhook_enabled=user.webhook_enabled or False,
        has_secret=user.webhook_secret is not None,
        masked_secret=masked_secret,
    )


@router.post("/me/webhook/secret", response_model=WebhookSecretResponse)
async def regenerate_webhook_secret(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """
    Generate a new webhook secret.
    
    Requirements:
    - Premium subscription required
    - Replaces any existing secret
    
    The full secret is only shown once!
    """
    effective_tier = get_effective_tier(user)
    if effective_tier != SubscriptionTier.PREMIUM:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Webhook notifications require Premium subscription"
        )
    
    # Generate new secret
    new_secret = WebhookService.generate_webhook_secret()
    user.webhook_secret = new_secret
    
    await db.commit()
    
    return WebhookSecretResponse(webhook_secret=new_secret)


@router.post("/me/webhook/test", response_model=WebhookTestResponse)
async def test_my_webhook(
    user: User = Depends(get_current_user),
    _: None = Depends(rate_limit_check_authenticated),
):
    """
    Send a test webhook to verify configuration.
    
    Requirements:
    - Premium subscription required
    - Webhook URL and secret must be configured
    """
    effective_tier = get_effective_tier(user)
    if effective_tier != SubscriptionTier.PREMIUM:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Webhook notifications require Premium subscription"
        )
    
    if not user.webhook_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Webhook URL not configured"
        )
    
    if not user.webhook_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Webhook secret not configured. Generate one first."
        )
    
    result = await webhook_service.test_webhook(user)
    
    return WebhookTestResponse(**result)


@router.delete("/me/webhook", status_code=status.HTTP_204_NO_CONTENT)
async def disable_my_webhook(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """Disable and clear webhook configuration."""
    user.webhook_url = None
    user.webhook_secret = None
    user.webhook_enabled = False
    
    await db.commit()
    
    return None
