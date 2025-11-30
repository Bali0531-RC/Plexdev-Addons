"""
Email Service for PlexAddons
Handles all email sending via SMTP with async support
"""
import asyncio
import logging
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional, List, Dict, Any

import aiosmtplib
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import User, Addon, Subscription, ApiRequestLog

logger = logging.getLogger(__name__)

# Get settings instance
settings = get_settings()


class EmailService:
    """Async email service using SMTP"""
    
    def __init__(self):
        self.enabled = settings.email_enabled
        self.host = settings.smtp_host
        self.port = settings.smtp_port
        self.username = settings.smtp_username
        self.password = settings.smtp_password
        self.use_tls = settings.smtp_use_tls
        self.from_address = settings.email_from_address
        self.from_name = settings.email_from_name
        self.admin_email = settings.admin_notification_email
    
    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        plain_content: Optional[str] = None
    ) -> bool:
        """Send an email asynchronously"""
        if not self.enabled:
            logger.info(f"Email disabled, skipping: {subject} to {to_email}")
            return False
        
        if not self.password:
            logger.warning("SMTP password not configured, skipping email")
            return False
        
        try:
            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{self.from_name} <{self.from_address}>"
            msg["To"] = to_email
            
            # Add plain text version (fallback)
            if plain_content:
                msg.attach(MIMEText(plain_content, "plain"))
            
            # Add HTML version
            msg.attach(MIMEText(html_content, "html"))
            
            # Send via SMTP
            await aiosmtplib.send(
                msg,
                hostname=self.host,
                port=self.port,
                username=self.username,
                password=self.password,
                start_tls=self.use_tls
            )
            
            logger.info(f"Email sent successfully: {subject} to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False
    
    async def send_welcome_email(self, user: User) -> bool:
        """Send welcome email to new user"""
        from app.services.email_templates import EmailTemplates
        
        subject = "Welcome to PlexAddons!"
        html_content = EmailTemplates.welcome_email(
            username=user.discord_username,
            email=user.email
        )
        plain_content = f"Welcome to PlexAddons, {user.discord_username}! Your account has been created."
        
        return await self.send_email(user.email, subject, html_content, plain_content)
    
    async def send_subscription_confirmation(
        self,
        user: User,
        plan_name: str,
        amount: float,
        next_billing_date: Optional[datetime] = None
    ) -> bool:
        """Send subscription confirmation email"""
        from app.services.email_templates import EmailTemplates
        
        subject = f"Subscription Confirmed - {plan_name}"
        html_content = EmailTemplates.subscription_confirmation(
            username=user.discord_username,
            plan_name=plan_name,
            amount=amount,
            next_billing_date=next_billing_date
        )
        plain_content = f"Your {plan_name} subscription has been confirmed. Amount: ${amount:.2f}"
        
        return await self.send_email(user.email, subject, html_content, plain_content)
    
    async def send_subscription_cancelled(
        self,
        user: User,
        plan_name: str,
        end_date: Optional[datetime] = None
    ) -> bool:
        """Send subscription cancellation email"""
        from app.services.email_templates import EmailTemplates
        
        subject = f"Subscription Cancelled - {plan_name}"
        html_content = EmailTemplates.subscription_cancelled(
            username=user.discord_username,
            plan_name=plan_name,
            end_date=end_date
        )
        plain_content = f"Your {plan_name} subscription has been cancelled."
        
        return await self.send_email(user.email, subject, html_content, plain_content)
    
    async def send_payment_received(
        self,
        user: User,
        amount: float,
        plan_name: str,
        transaction_id: str
    ) -> bool:
        """Send payment confirmation email"""
        from app.services.email_templates import EmailTemplates
        
        subject = "Payment Received - PlexAddons"
        html_content = EmailTemplates.payment_received(
            username=user.discord_username,
            amount=amount,
            plan_name=plan_name,
            transaction_id=transaction_id
        )
        plain_content = f"Payment of ${amount:.2f} received for {plan_name}. Transaction: {transaction_id}"
        
        return await self.send_email(user.email, subject, html_content, plain_content)
    
    # Admin Notifications
    
    async def send_admin_new_user(self, user: User) -> bool:
        """Notify admin of new user registration"""
        if not self.admin_email:
            return False
        
        from app.services.email_templates import EmailTemplates
        
        subject = f"[PlexAddons Admin] New User: {user.discord_username}"
        html_content = EmailTemplates.admin_new_user(
            username=user.discord_username,
            email=user.email,
            created_at=user.created_at
        )
        
        return await self.send_email(self.admin_email, subject, html_content)
    
    async def send_admin_new_payment(
        self,
        user: User,
        amount: float,
        plan_name: str,
        payment_provider: str
    ) -> bool:
        """Notify admin of new payment"""
        if not self.admin_email:
            return False
        
        from app.services.email_templates import EmailTemplates
        
        subject = f"[PlexAddons Admin] Payment: ${amount:.2f} from {user.discord_username}"
        html_content = EmailTemplates.admin_new_payment(
            username=user.discord_username,
            email=user.email,
            amount=amount,
            plan_name=plan_name,
            payment_provider=payment_provider
        )
        
        return await self.send_email(self.admin_email, subject, html_content)
    
    async def send_admin_new_addon(
        self,
        user: User,
        addon_name: str,
        addon_description: str
    ) -> bool:
        """Notify admin of new addon published"""
        if not self.admin_email:
            return False
        
        from app.services.email_templates import EmailTemplates
        
        subject = f"[PlexAddons Admin] New Addon: {addon_name}"
        html_content = EmailTemplates.admin_new_addon(
            username=user.discord_username,
            addon_name=addon_name,
            addon_description=addon_description
        )
        
        return await self.send_email(self.admin_email, subject, html_content)
    
    # Weekly Summary
    
    async def send_admin_weekly_summary(
        self,
        db: AsyncSession,
        week_start: Optional[datetime] = None
    ) -> bool:
        """Send weekly summary to admin"""
        if not self.admin_email:
            logger.info("No admin email configured, skipping weekly summary")
            return False
        
        from app.services.email_templates import EmailTemplates
        
        # Calculate week range
        if week_start is None:
            week_start = datetime.utcnow() - timedelta(days=7)
        week_end = week_start + timedelta(days=7)
        
        # Gather statistics
        stats = await self._gather_weekly_stats(db, week_start, week_end)
        
        subject = f"[PlexAddons] Weekly Summary - {week_start.strftime('%Y-%m-%d')} to {week_end.strftime('%Y-%m-%d')}"
        html_content = EmailTemplates.admin_weekly_summary(
            week_start=week_start,
            week_end=week_end,
            stats=stats
        )
        
        return await self.send_email(self.admin_email, subject, html_content)
    
    async def _gather_weekly_stats(
        self,
        db: AsyncSession,
        week_start: datetime,
        week_end: datetime
    ) -> Dict[str, Any]:
        """Gather statistics for the weekly summary"""
        stats = {}
        
        # New users this week
        result = await db.execute(
            select(func.count(User.id)).where(
                User.created_at >= week_start,
                User.created_at < week_end
            )
        )
        stats["new_users"] = result.scalar() or 0
        
        # Total users
        result = await db.execute(select(func.count(User.id)))
        stats["total_users"] = result.scalar() or 0
        
        # New addons this week
        result = await db.execute(
            select(func.count(Addon.id)).where(
                Addon.created_at >= week_start,
                Addon.created_at < week_end
            )
        )
        stats["new_addons"] = result.scalar() or 0
        
        # Total addons
        result = await db.execute(select(func.count(Addon.id)))
        stats["total_addons"] = result.scalar() or 0
        
        # New subscriptions this week
        result = await db.execute(
            select(func.count(Subscription.id)).where(
                Subscription.created_at >= week_start,
                Subscription.created_at < week_end
            )
        )
        stats["new_subscriptions"] = result.scalar() or 0
        
        # Active subscriptions
        result = await db.execute(
            select(func.count(Subscription.id)).where(
                Subscription.status == "active"
            )
        )
        stats["active_subscriptions"] = result.scalar() or 0
        
        # API requests this week (if tracking enabled)
        try:
            result = await db.execute(
                select(func.count(ApiRequestLog.id)).where(
                    ApiRequestLog.timestamp >= week_start,
                    ApiRequestLog.timestamp < week_end
                )
            )
            stats["api_requests"] = result.scalar() or 0
        except Exception:
            stats["api_requests"] = "N/A"
        
        return stats


# Global email service instance
email_service = EmailService()
