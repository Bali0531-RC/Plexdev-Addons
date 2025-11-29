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
            storage_quota_bytes=settings.storage_quota_free,
            version_history_limit=settings.version_limit_free,
            rate_limit=settings.rate_limit_user_free,
            features=[
                "Up to 5 versions per addon",
                "50MB storage",
                "Basic support",
                "Public addon listing",
            ],
        ),
        PaymentPlan(
            tier=SubscriptionTier.PRO,
            name="Pro",
            price_monthly=1.0,
            storage_quota_bytes=settings.storage_quota_pro,
            version_history_limit=settings.version_limit_pro,
            rate_limit=settings.rate_limit_user_pro,
            features=[
                "Up to 10 versions per addon",
                "500MB storage",
                "Priority support",
                "Public addon listing",
                "Higher rate limits",
            ],
        ),
        PaymentPlan(
            tier=SubscriptionTier.PREMIUM,
            name="Premium",
            price_monthly=5.0,
            storage_quota_bytes=settings.storage_quota_premium,
            version_history_limit=-1,  # Unlimited
            rate_limit=settings.rate_limit_user_premium,
            features=[
                "Unlimited version history",
                "5GB storage",
                "Premium support",
                "Public addon listing",
                "Highest rate limits",
                "Early access to new features",
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
