from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models import User, SubscriptionTier, PaymentProvider
from app.schemas import (
    CreateCheckoutRequest,
    CheckoutResponse,
    PaymentPlan,
    PaymentPlansResponse,
)
from app.services import StripeService, PayPalService
from app.api.deps import get_current_user, rate_limit_check_authenticated
from app.config import get_settings

settings = get_settings()

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.get("/plans", response_model=PaymentPlansResponse)
async def get_plans():
    """Get available subscription plans."""
    plans = [
        PaymentPlan(
            tier=SubscriptionTier.FREE,
            name="Free",
            price_monthly=0.0,
            storage_quota_bytes=5 * 1024 * 1024,  # 5MB
            version_history_limit=3,
            rate_limit=100,
            features=[
                "5MB storage",
                "3 version history",
                "100 requests/min",
                "Public profile",
            ],
        ),
        PaymentPlan(
            tier=SubscriptionTier.PRO,
            name="Pro",
            price_monthly=1.0,
            storage_quota_bytes=100 * 1024 * 1024,  # 100MB
            version_history_limit=10,
            rate_limit=300,
            features=[
                "100MB storage",
                "10 version history",
                "300 requests/min",
                "Custom profile URL",
                "Profile banner",
                "Ticket attachments",
                "Usage analytics (30 days)",
                "Private addons",
                "Supporter badge",
            ],
        ),
        PaymentPlan(
            tier=SubscriptionTier.PREMIUM,
            name="Premium",
            price_monthly=5.0,
            storage_quota_bytes=1024 * 1024 * 1024,  # 1GB
            version_history_limit=-1,  # Unlimited
            rate_limit=1000,
            features=[
                "1GB storage",
                "Unlimited version history",
                "1000 requests/min",
                "Custom profile URL",
                "Profile banner",
                "Accent color customization",
                "Ticket attachments",
                "Usage analytics (90 days)",
                "Private addons",
                "API key access",
                "Webhook notifications",
                "Supporter badge",
            ],
        ),
    ]
    return PaymentPlansResponse(plans=plans)


@router.post("/stripe/create-checkout", response_model=CheckoutResponse)
async def create_stripe_checkout(
    data: CreateCheckoutRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """Create a Stripe Checkout session."""
    success_url = data.success_url or f"{settings.frontend_url}/settings/subscription?success=true"
    cancel_url = data.cancel_url or f"{settings.frontend_url}/settings/subscription?canceled=true"
    
    result = await StripeService.create_checkout_session(
        db, user, data.tier, success_url, cancel_url
    )
    return CheckoutResponse(**result)


@router.post("/stripe/create-portal")
async def create_stripe_portal(
    user: User = Depends(get_current_user),
    _: None = Depends(rate_limit_check_authenticated),
):
    """Create a Stripe Billing Portal session."""
    return_url = f"{settings.frontend_url}/settings/subscription"
    portal_url = await StripeService.create_billing_portal_session(user, return_url)
    return {"portal_url": portal_url}


@router.post("/paypal/subscription-details")
async def get_paypal_subscription_details(
    data: CreateCheckoutRequest,
    user: User = Depends(get_current_user),
    _: None = Depends(rate_limit_check_authenticated),
):
    """Get PayPal subscription details for frontend."""
    return_url = data.success_url or f"{settings.frontend_url}/settings/subscription"
    cancel_url = data.cancel_url or f"{settings.frontend_url}/settings/subscription"
    
    details = await PayPalService.get_subscription_link(user, data.tier, return_url, cancel_url)
    return details


@router.post("/paypal/activate")
async def activate_paypal_subscription(
    subscription_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """Activate a PayPal subscription after user approval."""
    subscription = await PayPalService.activate_subscription(db, user, subscription_id)
    return {"status": "activated", "tier": subscription.tier.value}
