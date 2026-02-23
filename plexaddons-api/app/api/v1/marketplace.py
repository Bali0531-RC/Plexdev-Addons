"""Marketplace and Sponsorship endpoints (PREM-13, PREM-14)."""

import secrets
import stripe
import logging
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.config import get_settings
from app.database import get_db
from app.models import (
    User, Addon, SubscriptionTier, AddonLicense, LicenseStatus,
)
from app.schemas import (
    AddonPricingUpdate,
    LicenseResponse, LicenseListResponse,
    LicenseVerifyRequest, LicenseVerifyResponse,
    PurchaseAddonRequest, PurchaseAddonResponse,
    StripeConnectOnboardRequest, StripeConnectStatusResponse,
    RevenueStatsResponse,
    SponsorUrlUpdate,
)
from app.api.deps import get_current_user, rate_limit_check_authenticated, get_effective_tier
from app.core.cache import cache

settings = get_settings()
logger = logging.getLogger(__name__)


# ============== MARKETPLACE (PREM-13) ==============

marketplace_router = APIRouter(prefix="/marketplace", tags=["Marketplace"])


@marketplace_router.put("/addons/{addon_id}/pricing")
async def update_addon_pricing(
    addon_id: int,
    body: AddonPricingUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """
    Set up or update pricing for a paid addon (Premium only).
    
    Requires Stripe Connect account to be set up first.
    """
    effective_tier = get_effective_tier(user)
    if effective_tier != SubscriptionTier.PREMIUM and not user.is_admin:
        raise HTTPException(status_code=403, detail="Paid addons require Premium subscription")
    
    result = await db.execute(select(Addon).where(Addon.id == addon_id))
    addon = result.scalar_one_or_none()
    if not addon:
        raise HTTPException(status_code=404, detail="Addon not found")
    if addon.owner_id != user.id and not user.is_admin:
        raise HTTPException(status_code=403, detail="Not your addon")
    
    if body.is_paid and not user.stripe_connect_account_id:
        raise HTTPException(
            status_code=400,
            detail="Set up Stripe Connect first to enable paid addons",
        )
    
    if body.is_paid and (body.price_cents is None or body.price_cents < 100):
        raise HTTPException(
            status_code=400,
            detail="Price must be at least $1.00 for paid addons",
        )
    
    addon.is_paid = body.is_paid
    addon.price_cents = body.price_cents if body.is_paid else None
    addon.revenue_split_percent = body.revenue_split_percent
    
    await db.commit()
    await db.refresh(addon)
    
    await cache.invalidate_addon(addon_id=addon.id, addon_slug=addon.slug)
    
    return {
        "addon_id": addon.id,
        "is_paid": addon.is_paid,
        "price_cents": addon.price_cents,
        "revenue_split_percent": addon.revenue_split_percent,
    }


@marketplace_router.post("/addons/{addon_id}/purchase", response_model=PurchaseAddonResponse)
async def purchase_addon(
    addon_id: int,
    body: PurchaseAddonRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """
    Purchase a paid addon via Stripe Checkout.
    
    Creates a Stripe Checkout Session with Stripe Connect split payments.
    The seller receives their revenue share directly via Stripe Connect,
    and the platform retains the platform fee.
    """
    result = await db.execute(select(Addon).where(Addon.id == addon_id))
    addon = result.scalar_one_or_none()
    if not addon:
        raise HTTPException(status_code=404, detail="Addon not found")
    if not addon.is_paid or not addon.price_cents:
        raise HTTPException(status_code=400, detail="This addon is not a paid addon")
    if addon.owner_id == user.id:
        raise HTTPException(status_code=400, detail="Cannot purchase your own addon")
    
    # Check if user already has an active license
    existing = await db.execute(
        select(AddonLicense).where(
            AddonLicense.addon_id == addon_id,
            AddonLicense.buyer_id == user.id,
            AddonLicense.status == LicenseStatus.ACTIVE,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="You already have an active license for this addon")
    
    # Retrieve the addon owner to get their Connect account
    owner_result = await db.execute(select(User).where(User.id == addon.owner_id))
    owner = owner_result.scalar_one_or_none()
    if not owner or not owner.stripe_connect_account_id:
        raise HTTPException(
            status_code=400,
            detail="The addon developer has not set up payments yet",
        )
    
    # Calculate the platform fee (inverse of developer share)
    split = min(addon.revenue_split_percent or 90, 90)
    developer_share = int(addon.price_cents * split / 100)
    platform_fee = addon.price_cents - developer_share
    
    # Get or create Stripe customer for the buyer
    from app.services.stripe_service import StripeService
    customer_id = await StripeService._get_or_create_customer(user)
    
    success_url = f"{settings.frontend_url}/addons/{addon.slug}?purchase=success"
    cancel_url = f"{settings.frontend_url}/addons/{addon.slug}?purchase=cancelled"
    
    try:
        session = stripe.checkout.Session.create(
            customer=customer_id,
            mode="payment",
            line_items=[{
                "price_data": {
                    "currency": "usd",
                    "product_data": {
                        "name": addon.name,
                        "description": f"License for {addon.name}",
                    },
                    "unit_amount": addon.price_cents,
                },
                "quantity": 1,
            }],
            payment_intent_data={
                "application_fee_amount": platform_fee,
                "transfer_data": {
                    "destination": owner.stripe_connect_account_id,
                },
            },
            metadata={
                "type": "addon_purchase",
                "addon_id": str(addon.id),
                "buyer_id": str(user.id),
                "server_id": body.server_id or "",
                "price_cents": str(addon.price_cents),
                "developer_amount_cents": str(developer_share),
                "platform_amount_cents": str(platform_fee),
            },
            success_url=success_url,
            cancel_url=cancel_url,
        )
        
        return PurchaseAddonResponse(
            checkout_url=session.url,
            session_id=session.id,
        )
    except stripe.error.StripeError as e:
        logger.error(f"Stripe Checkout session creation failed for addon {addon_id}: {e}")
        raise HTTPException(status_code=502, detail="Failed to create payment session. Please try again.")


@marketplace_router.get("/addons/{addon_id}/licenses", response_model=LicenseListResponse)
async def list_addon_licenses(
    addon_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """List all licenses for an addon (owner only)."""
    result = await db.execute(select(Addon).where(Addon.id == addon_id))
    addon = result.scalar_one_or_none()
    if not addon:
        raise HTTPException(status_code=404, detail="Addon not found")
    if addon.owner_id != user.id and not user.is_admin:
        raise HTTPException(status_code=403, detail="Not your addon")
    
    licenses_result = await db.execute(
        select(AddonLicense)
        .where(AddonLicense.addon_id == addon_id)
        .order_by(AddonLicense.created_at.desc())
    )
    licenses = licenses_result.scalars().all()
    
    return LicenseListResponse(licenses=licenses, total=len(licenses))


@marketplace_router.get("/my-licenses", response_model=LicenseListResponse)
async def list_my_licenses(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """List all licenses the current user has purchased."""
    result = await db.execute(
        select(AddonLicense)
        .where(AddonLicense.buyer_id == user.id)
        .order_by(AddonLicense.created_at.desc())
    )
    licenses = result.scalars().all()
    
    return LicenseListResponse(licenses=licenses, total=len(licenses))


@marketplace_router.post("/licenses/{license_id}/revoke", response_model=LicenseResponse)
async def revoke_license(
    license_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """Revoke a license (addon owner or admin only)."""
    result = await db.execute(
        select(AddonLicense).where(AddonLicense.id == license_id)
    )
    license = result.scalar_one_or_none()
    if not license:
        raise HTTPException(status_code=404, detail="License not found")
    
    # Check ownership of the addon
    addon_result = await db.execute(select(Addon).where(Addon.id == license.addon_id))
    addon = addon_result.scalar_one_or_none()
    if not addon or (addon.owner_id != user.id and not user.is_admin):
        raise HTTPException(status_code=403, detail="Not authorized to revoke this license")
    
    license.status = LicenseStatus.REVOKED
    license.revoked_at = datetime.now(timezone.utc)
    
    await db.commit()
    await db.refresh(license)
    return license


@marketplace_router.post("/verify-license", response_model=LicenseVerifyResponse)
async def verify_license(
    body: LicenseVerifyRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Public endpoint to verify a license key.
    
    Used by pavc (version checker) to validate addon licenses.
    No authentication required — only the license key is needed.
    """
    result = await db.execute(
        select(AddonLicense).where(AddonLicense.license_key == body.license_key)
    )
    license = result.scalar_one_or_none()
    
    if not license:
        return LicenseVerifyResponse(valid=False)
    
    # Check if expired
    if license.expires_at and license.expires_at < datetime.now(timezone.utc):
        return LicenseVerifyResponse(
            valid=False,
            addon_id=license.addon_id,
            status=LicenseStatus.EXPIRED,
            expires_at=license.expires_at,
        )
    
    # Check if revoked/suspended
    if license.status != LicenseStatus.ACTIVE:
        return LicenseVerifyResponse(
            valid=False,
            addon_id=license.addon_id,
            status=license.status,
        )
    
    # If server_id was provided, check it matches
    if body.server_id and license.server_id and body.server_id != license.server_id:
        return LicenseVerifyResponse(
            valid=False,
            addon_id=license.addon_id,
            status=license.status,
        )
    
    # Get addon slug
    addon_result = await db.execute(select(Addon.slug).where(Addon.id == license.addon_id))
    addon_slug = addon_result.scalar_one_or_none()
    
    return LicenseVerifyResponse(
        valid=True,
        addon_id=license.addon_id,
        addon_slug=addon_slug,
        status=license.status,
        expires_at=license.expires_at,
    )


@marketplace_router.get("/addons/{addon_id}/revenue", response_model=RevenueStatsResponse)
async def get_revenue_stats(
    addon_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """Get revenue statistics for a paid addon (owner only)."""
    result = await db.execute(select(Addon).where(Addon.id == addon_id))
    addon = result.scalar_one_or_none()
    if not addon:
        raise HTTPException(status_code=404, detail="Addon not found")
    if addon.owner_id != user.id and not user.is_admin:
        raise HTTPException(status_code=403, detail="Not your addon")
    
    stats = await db.execute(
        select(
            func.count(AddonLicense.id).label("total_sales"),
            func.coalesce(func.sum(AddonLicense.amount_cents), 0).label("total_revenue"),
            func.coalesce(func.sum(AddonLicense.developer_amount_cents), 0).label("dev_earnings"),
            func.coalesce(func.sum(AddonLicense.platform_amount_cents), 0).label("platform_fees"),
        ).where(
            AddonLicense.addon_id == addon_id,
        )
    )
    row = stats.one()
    
    active_count = await db.execute(
        select(func.count(AddonLicense.id)).where(
            AddonLicense.addon_id == addon_id,
            AddonLicense.status == LicenseStatus.ACTIVE,
        )
    )
    
    return RevenueStatsResponse(
        total_sales=row.total_sales,
        total_revenue_cents=row.total_revenue,
        developer_earnings_cents=row.dev_earnings,
        platform_fees_cents=row.platform_fees,
        active_licenses=active_count.scalar() or 0,
    )


# ============== STRIPE CONNECT (PREM-13) ==============

connect_router = APIRouter(prefix="/stripe-connect", tags=["Stripe Connect"])


@connect_router.get("/status", response_model=StripeConnectStatusResponse)
async def get_connect_status(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """Get the current user's Stripe Connect account status."""
    effective_tier = get_effective_tier(user)
    if effective_tier != SubscriptionTier.PREMIUM and not user.is_admin:
        raise HTTPException(status_code=403, detail="Stripe Connect requires Premium subscription")
    
    if not user.stripe_connect_account_id:
        return StripeConnectStatusResponse(has_connect_account=False)
    
    try:
        account = stripe.Account.retrieve(user.stripe_connect_account_id)
        return StripeConnectStatusResponse(
            has_connect_account=True,
            account_id=user.stripe_connect_account_id,
            payouts_enabled=account.payouts_enabled or False,
            onboarding_complete=account.details_submitted or False,
        )
    except stripe.error.StripeError as e:
        logger.error(f"Failed to retrieve Stripe Connect account: {e}")
        return StripeConnectStatusResponse(
            has_connect_account=True,
            account_id=user.stripe_connect_account_id,
            payouts_enabled=False,
            onboarding_complete=False,
        )


@connect_router.post("/onboard")
async def start_connect_onboarding(
    body: StripeConnectOnboardRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """
    Start Stripe Connect onboarding.
    
    Creates a Stripe Connect Express account and returns an Account Link URL
    for the user to complete their onboarding.
    """
    effective_tier = get_effective_tier(user)
    if effective_tier != SubscriptionTier.PREMIUM and not user.is_admin:
        raise HTTPException(status_code=403, detail="Stripe Connect requires Premium subscription")
    
    try:
        if user.stripe_connect_account_id:
            # Account already exists — check if onboarding is complete
            account = stripe.Account.retrieve(user.stripe_connect_account_id)
            if account.details_submitted:
                return {
                    "message": "Stripe Connect account already set up",
                    "account_id": user.stripe_connect_account_id,
                }
            # Onboarding incomplete — generate a new Account Link
            account_link = stripe.AccountLink.create(
                account=user.stripe_connect_account_id,
                refresh_url=body.refresh_url,
                return_url=body.return_url,
                type="account_onboarding",
            )
            return {
                "message": "Continue Stripe Connect onboarding",
                "account_id": user.stripe_connect_account_id,
                "onboarding_url": account_link.url,
            }
        
        # Create a new Stripe Connect Express account
        account = stripe.Account.create(
            type="express",
            email=user.email,
            metadata={
                "user_id": str(user.id),
                "discord_id": user.discord_id,
            },
            capabilities={
                "card_payments": {"requested": True},
                "transfers": {"requested": True},
            },
        )
        
        user.stripe_connect_account_id = account.id
        await db.commit()
        
        # Generate an Account Link for onboarding
        account_link = stripe.AccountLink.create(
            account=account.id,
            refresh_url=body.refresh_url,
            return_url=body.return_url,
            type="account_onboarding",
        )
        
        return {
            "message": "Stripe Connect onboarding initiated",
            "account_id": account.id,
            "onboarding_url": account_link.url,
        }
    except stripe.error.StripeError as e:
        logger.error(f"Stripe Connect onboarding failed: {e}")
        raise HTTPException(status_code=502, detail="Failed to set up Stripe Connect. Please try again.")


# ============== SPONSORSHIP (PREM-14) ==============

sponsorship_router = APIRouter(prefix="/addons/{addon_id}/sponsorship", tags=["Sponsorship"])


@sponsorship_router.get("")
async def get_sponsor_url(
    addon_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get the sponsor URL for an addon (public endpoint)."""
    result = await db.execute(
        select(Addon.sponsor_url, Addon.name, Addon.slug).where(Addon.id == addon_id)
    )
    row = result.one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Addon not found")
    
    return {
        "addon_id": addon_id,
        "addon_name": row.name,
        "addon_slug": row.slug,
        "sponsor_url": row.sponsor_url,
    }


@sponsorship_router.put("")
async def update_sponsor_url(
    addon_id: int,
    body: SponsorUrlUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """Update the sponsor/donation URL for an addon (Premium only)."""
    effective_tier = get_effective_tier(user)
    if effective_tier != SubscriptionTier.PREMIUM and not user.is_admin:
        raise HTTPException(status_code=403, detail="Sponsorship features require Premium subscription")
    
    result = await db.execute(select(Addon).where(Addon.id == addon_id))
    addon = result.scalar_one_or_none()
    if not addon:
        raise HTTPException(status_code=404, detail="Addon not found")
    if addon.owner_id != user.id and not user.is_admin:
        raise HTTPException(status_code=403, detail="Not your addon")
    
    addon.sponsor_url = body.sponsor_url
    await db.commit()
    
    await cache.invalidate_addon(addon_id=addon.id, addon_slug=addon.slug)
    
    return {
        "addon_id": addon.id,
        "sponsor_url": addon.sponsor_url,
    }
