import httpx
import base64
import json
import logging
from typing import Optional
from fastapi import BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta, timezone
from app.config import get_settings
from app.models import User, Subscription, SubscriptionTier, SubscriptionStatus, PaymentProvider, SubscriptionEvent
from app.services.user_service import UserService
from app.core.exceptions import PaymentError, BadRequestError

logger = logging.getLogger(__name__)

settings = get_settings()


class PayPalService:
    """Service for PayPal payment operations."""
    
    _access_token: Optional[str] = None
    _token_expires_at: Optional[datetime] = None
    
    @classmethod
    async def _get_access_token(cls) -> str:
        """Get PayPal API access token."""
        if cls._access_token and cls._token_expires_at and datetime.now(timezone.utc) < cls._token_expires_at:
            return cls._access_token
        
        auth = base64.b64encode(
            f"{settings.paypal_client_id}:{settings.paypal_client_secret}".encode()
        ).decode()
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.paypal_api_base}/v1/oauth2/token",
                headers={
                    "Authorization": f"Basic {auth}",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                data={"grant_type": "client_credentials"},
            )
            
            if response.status_code != 200:
                raise PaymentError("Failed to get PayPal access token")
            
            data = response.json()
            cls._access_token = data["access_token"]
            expires_in = data.get("expires_in", 3600)
            cls._token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in - 60)
            
            return cls._access_token
    
    @classmethod
    async def get_subscription_link(
        cls,
        user: User,
        tier: SubscriptionTier,
        return_url: str,
        cancel_url: str,
    ) -> dict:
        """Get PayPal subscription creation details for frontend."""
        if tier == SubscriptionTier.FREE:
            raise BadRequestError("Cannot create subscription for free tier")
        
        plan_id = (
            settings.paypal_pro_plan_id if tier == SubscriptionTier.PRO
            else settings.paypal_premium_plan_id
        )
        
        return {
            "plan_id": plan_id,
            "custom_id": f"{user.id}:{user.discord_id}",
            "return_url": return_url,
            "cancel_url": cancel_url,
        }
    
    @classmethod
    async def verify_subscription(cls, db: AsyncSession, subscription_id: str) -> dict:
        """Verify a PayPal subscription after approval."""
        token = await cls._get_access_token()
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.paypal_api_base}/v1/billing/subscriptions/{subscription_id}",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
            )
            
            if response.status_code != 200:
                raise PaymentError("Failed to verify PayPal subscription")
            
            return response.json()
    
    @classmethod
    async def activate_subscription(
        cls,
        db: AsyncSession,
        user: User,
        subscription_id: str,
    ) -> Subscription:
        """Activate a PayPal subscription after user approval."""
        # Verify the subscription with PayPal
        sub_data = await cls.verify_subscription(db, subscription_id)
        
        if sub_data["status"] != "ACTIVE":
            raise BadRequestError(f"Subscription is not active: {sub_data['status']}")
        
        # Verify custom_id matches user
        custom_id = sub_data.get("custom_id", "")
        expected_prefix = f"{user.id}:"
        if not custom_id.startswith(expected_prefix):
            raise BadRequestError("Subscription does not belong to this user")
        
        # Determine tier from plan_id
        plan_id = sub_data.get("plan_id")
        tier = SubscriptionTier.PRO
        if plan_id == settings.paypal_premium_plan_id:
            tier = SubscriptionTier.PREMIUM
        
        # Check for existing subscription
        result = await db.execute(
            select(Subscription)
            .where(Subscription.user_id == user.id)
            .where(Subscription.status == SubscriptionStatus.ACTIVE)
        )
        existing = result.scalar_one_or_none()
        if existing:
            raise BadRequestError("You already have an active subscription")
        
        # Parse dates
        billing_info = sub_data.get("billing_info", {})
        current_period_end = None
        if billing_info.get("next_billing_time"):
            current_period_end = datetime.fromisoformat(
                billing_info["next_billing_time"].replace("Z", "+00:00")
            )
        
        # Create subscription record
        sub = Subscription(
            user_id=user.id,
            provider=PaymentProvider.PAYPAL,
            provider_subscription_id=subscription_id,
            tier=tier,
            status=SubscriptionStatus.ACTIVE,
            current_period_start=datetime.now(timezone.utc),
            current_period_end=current_period_end,
        )
        db.add(sub)
        
        # Update user tier
        await UserService.update_user_tier(db, user, tier)
        
        await db.commit()
        await db.refresh(sub)
        
        return sub
    
    @classmethod
    async def cancel_subscription(cls, subscription_id: str, reason: str = "User requested cancellation") -> bool:
        """Cancel a PayPal subscription."""
        token = await cls._get_access_token()
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.paypal_api_base}/v1/billing/subscriptions/{subscription_id}/cancel",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json={"reason": reason},
            )
            
            return response.status_code == 204
    
    @classmethod
    async def verify_webhook_signature(cls, headers: dict, payload: dict) -> bool:
        """Verify PayPal webhook signature using PayPal's verification API."""
        token = await cls._get_access_token()

        verification_body = {
            "auth_algo": headers.get("paypal-auth-algo", ""),
            "cert_url": headers.get("paypal-cert-url", ""),
            "transmission_id": headers.get("paypal-transmission-id", ""),
            "transmission_sig": headers.get("paypal-transmission-sig", ""),
            "transmission_time": headers.get("paypal-transmission-time", ""),
            "webhook_id": settings.paypal_webhook_id,
            "webhook_event": payload,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.paypal_api_base}/v1/notifications/verify-webhook-signature",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json=verification_body,
            )

            if response.status_code != 200:
                logger.error(f"PayPal webhook verification request failed: {response.status_code}")
                return False

            result = response.json()
            return result.get("verification_status") == "SUCCESS"

    @classmethod
    async def handle_webhook_event(
        cls,
        db: AsyncSession,
        payload: dict,
        headers: dict,
        background_tasks: Optional[BackgroundTasks] = None
    ) -> dict:
        """Handle PayPal webhook events."""
        # Verify webhook signature
        is_valid = await cls.verify_webhook_signature(headers, payload)
        if not is_valid:
            logger.warning("PayPal webhook signature verification failed")
            raise BadRequestError("Invalid webhook signature")

        event_type = payload.get("event_type")
        resource = payload.get("resource", {})
        
        # Log the event
        await cls._log_event(db, event_type, resource, payload.get("id"))
        
        # Handle different event types
        handlers = {
            "BILLING.SUBSCRIPTION.ACTIVATED": cls._handle_subscription_activated,
            "BILLING.SUBSCRIPTION.CANCELLED": cls._handle_subscription_cancelled,
            "BILLING.SUBSCRIPTION.SUSPENDED": cls._handle_subscription_suspended,
            "BILLING.SUBSCRIPTION.UPDATED": cls._handle_subscription_updated,
            "PAYMENT.SALE.COMPLETED": cls._handle_payment_completed,
        }
        
        handler = handlers.get(event_type)
        if handler:
            await handler(db, resource, background_tasks)
        
        return {"status": "success", "event_type": event_type}
    
    @classmethod
    async def _handle_subscription_activated(
        cls, 
        db: AsyncSession, 
        resource: dict,
        background_tasks: Optional[BackgroundTasks] = None
    ):
        """Handle subscription activation."""
        from app.services.email_service import email_service
        
        subscription_id = resource.get("id")
        custom_id = resource.get("custom_id", "")
        
        # Parse user_id from custom_id
        try:
            user_id = int(custom_id.split(":")[0])
        except (ValueError, IndexError):
            return
        
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            return
        
        # Check if we already have this subscription
        result = await db.execute(
            select(Subscription)
            .where(Subscription.provider == PaymentProvider.PAYPAL)
            .where(Subscription.provider_subscription_id == subscription_id)
        )
        existing = result.scalar_one_or_none()
        if existing:
            existing.status = SubscriptionStatus.ACTIVE
            await db.commit()
            return
        
        # Create new subscription
        plan_id = resource.get("plan_id")
        tier = SubscriptionTier.PREMIUM if plan_id == settings.paypal_premium_plan_id else SubscriptionTier.PRO
        
        sub = Subscription(
            user_id=user.id,
            provider=PaymentProvider.PAYPAL,
            provider_subscription_id=subscription_id,
            tier=tier,
            status=SubscriptionStatus.ACTIVE,
            current_period_start=datetime.now(timezone.utc),
        )
        db.add(sub)
        
        await UserService.update_user_tier(db, user, tier)
        await db.commit()
        
        # Send subscription confirmation emails
        if background_tasks:
            amount = 5.0 if tier == SubscriptionTier.PRO else 10.0
            plan_name = tier.value.capitalize()
            
            background_tasks.add_task(
                email_service.send_subscription_confirmation,
                user, plan_name, amount, None
            )
            background_tasks.add_task(
                email_service.send_admin_new_payment,
                user, amount, plan_name, "PayPal"
            )
    
    @classmethod
    async def _handle_subscription_cancelled(
        cls, 
        db: AsyncSession, 
        resource: dict,
        background_tasks: Optional[BackgroundTasks] = None
    ):
        """Handle subscription cancellation."""
        from app.services.email_service import email_service
        
        subscription_id = resource.get("id")
        
        result = await db.execute(
            select(Subscription)
            .where(Subscription.provider == PaymentProvider.PAYPAL)
            .where(Subscription.provider_subscription_id == subscription_id)
        )
        sub = result.scalar_one_or_none()
        if not sub:
            return
        
        old_tier = sub.tier
        sub.status = SubscriptionStatus.CANCELED
        sub.canceled_at = datetime.now(timezone.utc)
        
        # Downgrade user
        result = await db.execute(select(User).where(User.id == sub.user_id))
        user = result.scalar_one_or_none()
        if user:
            await UserService.update_user_tier(db, user, SubscriptionTier.FREE)
            
            # Send cancellation email
            if background_tasks:
                plan_name = old_tier.value.capitalize()
                background_tasks.add_task(
                    email_service.send_subscription_cancelled,
                    user, plan_name, sub.current_period_end
                )
        
        await db.commit()
    
    @classmethod
    async def _handle_subscription_suspended(
        cls, 
        db: AsyncSession, 
        resource: dict,
        background_tasks: Optional[BackgroundTasks] = None
    ):
        """Handle subscription suspension (payment failure)."""
        subscription_id = resource.get("id")
        
        result = await db.execute(
            select(Subscription)
            .where(Subscription.provider == PaymentProvider.PAYPAL)
            .where(Subscription.provider_subscription_id == subscription_id)
        )
        sub = result.scalar_one_or_none()
        if sub:
            sub.status = SubscriptionStatus.PAST_DUE
            await db.commit()
    
    @classmethod
    async def _handle_subscription_updated(
        cls, 
        db: AsyncSession, 
        resource: dict,
        background_tasks: Optional[BackgroundTasks] = None
    ):
        """Handle subscription updates."""
        subscription_id = resource.get("id")
        
        result = await db.execute(
            select(Subscription)
            .where(Subscription.provider == PaymentProvider.PAYPAL)
            .where(Subscription.provider_subscription_id == subscription_id)
        )
        sub = result.scalar_one_or_none()
        if not sub:
            return
        
        # Update tier if plan changed
        plan_id = resource.get("plan_id")
        if plan_id:
            tier = SubscriptionTier.PREMIUM if plan_id == settings.paypal_premium_plan_id else SubscriptionTier.PRO
            sub.tier = tier
            
            result = await db.execute(select(User).where(User.id == sub.user_id))
            user = result.scalar_one_or_none()
            if user:
                await UserService.update_user_tier(db, user, tier)
        
        await db.commit()
    
    @classmethod
    async def _handle_payment_completed(
        cls, 
        db: AsyncSession, 
        resource: dict,
        background_tasks: Optional[BackgroundTasks] = None
    ):
        """Handle successful payment."""
        from app.services.email_service import email_service
        
        # Try to send payment receipt
        billing_agreement_id = resource.get("billing_agreement_id")
        if billing_agreement_id and background_tasks:
            result = await db.execute(
                select(Subscription)
                .where(Subscription.provider == PaymentProvider.PAYPAL)
                .where(Subscription.provider_subscription_id == billing_agreement_id)
            )
            sub = result.scalar_one_or_none()
            if sub:
                result = await db.execute(select(User).where(User.id == sub.user_id))
                user = result.scalar_one_or_none()
                if user:
                    amount_data = resource.get("amount", {})
                    amount = float(amount_data.get("total", 0))
                    plan_name = sub.tier.value.capitalize()
                    transaction_id = resource.get("id", "N/A")
                    
                    background_tasks.add_task(
                        email_service.send_payment_received,
                        user, amount, plan_name, transaction_id
                    )
    
    @classmethod
    async def _log_event(
        cls,
        db: AsyncSession,
        event_type: str,
        resource: dict,
        event_id: Optional[str] = None,
    ):
        """Log subscription event."""
        subscription_id = resource.get("id")
        custom_id = resource.get("custom_id", "")
        
        user = None
        sub = None
        
        # Try to get user from custom_id
        try:
            user_id = int(custom_id.split(":")[0])
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
        except (ValueError, IndexError):
            pass
        
        # Try to get subscription
        if subscription_id:
            result = await db.execute(
                select(Subscription)
                .where(Subscription.provider == PaymentProvider.PAYPAL)
                .where(Subscription.provider_subscription_id == subscription_id)
            )
            sub = result.scalar_one_or_none()
        
        event = SubscriptionEvent(
            user_id=user.id if user else None,
            subscription_id=sub.id if sub else None,
            event_type=event_type,
            provider=PaymentProvider.PAYPAL,
            provider_event_id=event_id,
            payload=json.dumps(resource),
        )
        db.add(event)
        await db.commit()
