"""Marketplace and Sponsorship endpoints (PREM-13, PREM-14)."""

import secrets
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

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
    
    addon.is_paid = body.is_paid
    addon.price_cents = body.price_cents
    addon.revenue_split_percent = body.revenue_split_percent
    
    await db.commit()
    await db.refresh(addon)
    
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
    Purchase a paid addon and receive a license key.
    
    In production, this would integrate with Stripe to process payment.
    For now, it creates a license record (payment would be handled by
    a Stripe Checkout session in the real flow).
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
    
    # Calculate revenue split
    developer_share = int(addon.price_cents * addon.revenue_split_percent / 100)
    platform_share = addon.price_cents - developer_share
    
    # Generate license key
    license_key = f"lic_{secrets.token_hex(24)}"
    
    license = AddonLicense(
        addon_id=addon_id,
        buyer_id=user.id,
        license_key=license_key,
        amount_cents=addon.price_cents,
        developer_amount_cents=developer_share,
        platform_amount_cents=platform_share,
        status=LicenseStatus.ACTIVE,
        server_id=body.server_id,
    )
    db.add(license)
    await db.commit()
    await db.refresh(license)
    
    return PurchaseAddonResponse(license=license, message="Purchase successful")


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
    
    # In production, verify account status with Stripe API
    return StripeConnectStatusResponse(
        has_connect_account=True,
        account_id=user.stripe_connect_account_id,
        payouts_enabled=True,  # Would check via Stripe API
        onboarding_complete=True,  # Would check via Stripe API
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
    
    Returns an onboarding URL for the user to complete their Stripe Connect account setup.
    In production, this creates a Stripe Connect account and returns an Account Link.
    """
    effective_tier = get_effective_tier(user)
    if effective_tier != SubscriptionTier.PREMIUM and not user.is_admin:
        raise HTTPException(status_code=403, detail="Stripe Connect requires Premium subscription")
    
    if user.stripe_connect_account_id:
        return {
            "message": "Stripe Connect account already exists",
            "account_id": user.stripe_connect_account_id,
        }
    
    # In production:
    # 1. Create a Stripe Connect account via stripe.Account.create()
    # 2. Generate an Account Link via stripe.AccountLink.create()
    # 3. Return the URL for the user to complete onboarding
    
    # Placeholder: generate a mock account ID
    mock_account_id = f"acct_{secrets.token_hex(12)}"
    user.stripe_connect_account_id = mock_account_id
    await db.commit()
    
    return {
        "message": "Stripe Connect onboarding initiated",
        "account_id": mock_account_id,
        "onboarding_url": f"{body.return_url}?account={mock_account_id}",
    }


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
    
    return {
        "addon_id": addon.id,
        "sponsor_url": addon.sponsor_url,
    }
