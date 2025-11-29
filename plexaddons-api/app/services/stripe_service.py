import stripe
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from app.config import get_settings
from app.models import User, Subscription, SubscriptionTier, SubscriptionStatus, PaymentProvider, SubscriptionEvent
from app.services.user_service import UserService
from app.core.exceptions import PaymentError, BadRequestError
import json

settings = get_settings()

# Initialize Stripe
stripe.api_key = settings.stripe_secret_key


class StripeService:
    """Service for Stripe payment operations."""
    
    @staticmethod
    async def create_checkout_session(
        db: AsyncSession,
        user: User,
        tier: SubscriptionTier,
        success_url: str,
        cancel_url: str,
    ) -> dict:
        """Create a Stripe Checkout session for subscription."""
        if tier == SubscriptionTier.FREE:
            raise BadRequestError("Cannot create checkout for free tier")
        
        # Check if user already has an active subscription
        result = await db.execute(
            select(Subscription)
            .where(Subscription.user_id == user.id)
            .where(Subscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING]))
        )
        existing_sub = result.scalar_one_or_none()
        if existing_sub:
            raise BadRequestError("You already have an active subscription. Please cancel it first or manage it in the billing portal.")
        
        # Get or create Stripe customer
        customer_id = await StripeService._get_or_create_customer(user)
        
        # Get price ID based on tier
        price_id = (
            settings.stripe_pro_price_id if tier == SubscriptionTier.PRO
            else settings.stripe_premium_price_id
        )
        
        try:
            session = stripe.checkout.Session.create(
                customer=customer_id,
                mode="subscription",
                line_items=[{"price": price_id, "quantity": 1}],
                success_url=success_url,
                cancel_url=cancel_url,
                metadata={
                    "user_id": str(user.id),
                    "discord_id": user.discord_id,
                    "tier": tier.value,
                },
            )
            return {
                "checkout_url": session.url,
                "session_id": session.id,
            }
        except stripe.error.StripeError as e:
            raise PaymentError(f"Failed to create checkout session: {str(e)}")
    
    @staticmethod
    async def create_billing_portal_session(user: User, return_url: str) -> str:
        """Create a Stripe Billing Portal session."""
        customer_id = await StripeService._get_or_create_customer(user)
        
        try:
            session = stripe.billing_portal.Session.create(
                customer=customer_id,
                return_url=return_url,
            )
            return session.url
        except stripe.error.StripeError as e:
            raise PaymentError(f"Failed to create billing portal: {str(e)}")
    
    @staticmethod
    async def _get_or_create_customer(user: User) -> str:
        """Get existing Stripe customer or create a new one."""
        # Search for existing customer by Discord ID
        try:
            customers = stripe.Customer.search(
                query=f"metadata['discord_id']:'{user.discord_id}'"
            )
            if customers.data:
                return customers.data[0].id
        except stripe.error.StripeError:
            pass
        
        # Create new customer
        try:
            customer = stripe.Customer.create(
                email=user.email,
                name=user.discord_username,
                metadata={
                    "discord_id": user.discord_id,
                    "user_id": str(user.id),
                },
            )
            return customer.id
        except stripe.error.StripeError as e:
            raise PaymentError(f"Failed to create customer: {str(e)}")
    
    @staticmethod
    async def handle_webhook_event(db: AsyncSession, payload: bytes, sig_header: str) -> dict:
        """Handle Stripe webhook events."""
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.stripe_webhook_secret
            )
        except ValueError:
            raise BadRequestError("Invalid payload")
        except stripe.error.SignatureVerificationError:
            raise BadRequestError("Invalid signature")
        
        event_type = event["type"]
        event_data = event["data"]["object"]
        
        # Log the event
        await StripeService._log_event(db, event_type, event_data, event.get("id"))
        
        # Handle different event types
        handlers = {
            "customer.subscription.created": StripeService._handle_subscription_created,
            "customer.subscription.updated": StripeService._handle_subscription_updated,
            "customer.subscription.deleted": StripeService._handle_subscription_deleted,
            "invoice.paid": StripeService._handle_invoice_paid,
            "invoice.payment_failed": StripeService._handle_payment_failed,
        }
        
        handler = handlers.get(event_type)
        if handler:
            await handler(db, event_data)
        
        return {"status": "success", "event_type": event_type}
    
    @staticmethod
    async def _handle_subscription_created(db: AsyncSession, subscription_data: dict):
        """Handle subscription creation."""
        customer_id = subscription_data["customer"]
        subscription_id = subscription_data["id"]
        
        # Get user by customer metadata
        user = await StripeService._get_user_by_customer(db, customer_id)
        if not user:
            return
        
        # Determine tier from price
        tier = StripeService._get_tier_from_subscription(subscription_data)
        status = StripeService._map_stripe_status(subscription_data["status"])
        
        # Create subscription record
        sub = Subscription(
            user_id=user.id,
            provider=PaymentProvider.STRIPE,
            provider_subscription_id=subscription_id,
            provider_customer_id=customer_id,
            tier=tier,
            status=status,
            current_period_start=datetime.fromtimestamp(subscription_data["current_period_start"]),
            current_period_end=datetime.fromtimestamp(subscription_data["current_period_end"]),
        )
        db.add(sub)
        
        # Update user tier if subscription is active
        if status == SubscriptionStatus.ACTIVE:
            await UserService.update_user_tier(db, user, tier)
        
        await db.commit()
    
    @staticmethod
    async def _handle_subscription_updated(db: AsyncSession, subscription_data: dict):
        """Handle subscription updates."""
        subscription_id = subscription_data["id"]
        
        result = await db.execute(
            select(Subscription)
            .where(Subscription.provider == PaymentProvider.STRIPE)
            .where(Subscription.provider_subscription_id == subscription_id)
        )
        sub = result.scalar_one_or_none()
        if not sub:
            return
        
        # Update subscription
        sub.tier = StripeService._get_tier_from_subscription(subscription_data)
        sub.status = StripeService._map_stripe_status(subscription_data["status"])
        sub.current_period_start = datetime.fromtimestamp(subscription_data["current_period_start"])
        sub.current_period_end = datetime.fromtimestamp(subscription_data["current_period_end"])
        
        if subscription_data.get("canceled_at"):
            sub.canceled_at = datetime.fromtimestamp(subscription_data["canceled_at"])
        
        # Get user and update tier
        result = await db.execute(select(User).where(User.id == sub.user_id))
        user = result.scalar_one_or_none()
        if user:
            if sub.status == SubscriptionStatus.ACTIVE:
                await UserService.update_user_tier(db, user, sub.tier)
            elif sub.status in [SubscriptionStatus.CANCELED, SubscriptionStatus.UNPAID]:
                await UserService.update_user_tier(db, user, SubscriptionTier.FREE)
        
        await db.commit()
    
    @staticmethod
    async def _handle_subscription_deleted(db: AsyncSession, subscription_data: dict):
        """Handle subscription cancellation/deletion."""
        subscription_id = subscription_data["id"]
        
        result = await db.execute(
            select(Subscription)
            .where(Subscription.provider == PaymentProvider.STRIPE)
            .where(Subscription.provider_subscription_id == subscription_id)
        )
        sub = result.scalar_one_or_none()
        if not sub:
            return
        
        sub.status = SubscriptionStatus.CANCELED
        sub.canceled_at = datetime.utcnow()
        
        # Downgrade user to free
        result = await db.execute(select(User).where(User.id == sub.user_id))
        user = result.scalar_one_or_none()
        if user:
            await UserService.update_user_tier(db, user, SubscriptionTier.FREE)
        
        await db.commit()
    
    @staticmethod
    async def _handle_invoice_paid(db: AsyncSession, invoice_data: dict):
        """Handle successful invoice payment."""
        # This is mainly for logging/analytics
        pass
    
    @staticmethod
    async def _handle_payment_failed(db: AsyncSession, invoice_data: dict):
        """Handle failed payment."""
        subscription_id = invoice_data.get("subscription")
        if not subscription_id:
            return
        
        result = await db.execute(
            select(Subscription)
            .where(Subscription.provider == PaymentProvider.STRIPE)
            .where(Subscription.provider_subscription_id == subscription_id)
        )
        sub = result.scalar_one_or_none()
        if sub:
            sub.status = SubscriptionStatus.PAST_DUE
            await db.commit()
    
    @staticmethod
    async def _get_user_by_customer(db: AsyncSession, customer_id: str) -> Optional[User]:
        """Get user by Stripe customer ID."""
        try:
            customer = stripe.Customer.retrieve(customer_id)
            discord_id = customer.metadata.get("discord_id")
            if discord_id:
                result = await db.execute(select(User).where(User.discord_id == discord_id))
                return result.scalar_one_or_none()
        except stripe.error.StripeError:
            pass
        return None
    
    @staticmethod
    def _get_tier_from_subscription(subscription_data: dict) -> SubscriptionTier:
        """Determine tier from subscription price."""
        items = subscription_data.get("items", {}).get("data", [])
        if items:
            price_id = items[0].get("price", {}).get("id")
            if price_id == settings.stripe_pro_price_id:
                return SubscriptionTier.PRO
            elif price_id == settings.stripe_premium_price_id:
                return SubscriptionTier.PREMIUM
        return SubscriptionTier.PRO  # Default to pro if unable to determine
    
    @staticmethod
    def _map_stripe_status(status: str) -> SubscriptionStatus:
        """Map Stripe status to our status enum."""
        mapping = {
            "active": SubscriptionStatus.ACTIVE,
            "past_due": SubscriptionStatus.PAST_DUE,
            "canceled": SubscriptionStatus.CANCELED,
            "unpaid": SubscriptionStatus.UNPAID,
            "trialing": SubscriptionStatus.TRIALING,
            "paused": SubscriptionStatus.PAUSED,
            "incomplete": SubscriptionStatus.INCOMPLETE,
            "incomplete_expired": SubscriptionStatus.INCOMPLETE_EXPIRED,
        }
        return mapping.get(status, SubscriptionStatus.INCOMPLETE)
    
    @staticmethod
    async def _log_event(
        db: AsyncSession,
        event_type: str,
        event_data: dict,
        event_id: Optional[str] = None,
    ):
        """Log subscription event."""
        # Try to get user from customer
        customer_id = event_data.get("customer")
        user = await StripeService._get_user_by_customer(db, customer_id) if customer_id else None
        
        # Get subscription
        sub_id = event_data.get("id") if "subscription" in event_type else event_data.get("subscription")
        sub = None
        if sub_id:
            result = await db.execute(
                select(Subscription)
                .where(Subscription.provider == PaymentProvider.STRIPE)
                .where(Subscription.provider_subscription_id == sub_id)
            )
            sub = result.scalar_one_or_none()
        
        event = SubscriptionEvent(
            user_id=user.id if user else None,
            subscription_id=sub.id if sub else None,
            event_type=event_type,
            provider=PaymentProvider.STRIPE,
            provider_event_id=event_id,
            payload=json.dumps(event_data),
        )
        db.add(event)
        await db.commit()
