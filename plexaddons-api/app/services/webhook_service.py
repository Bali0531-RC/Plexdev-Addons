"""Webhook notification service for Premium users."""

import hmac
import hashlib
import json
import secrets
from datetime import datetime, timezone
from typing import Optional, Dict, Any
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import User, Addon, Version, SubscriptionTier
from app.config import get_settings

settings = get_settings()


class WebhookEvent:
    """Webhook event types."""
    VERSION_RELEASED = "version.released"
    VERSION_UPDATED = "version.updated"
    VERSION_DELETED = "version.deleted"
    ADDON_CREATED = "addon.created"
    ADDON_UPDATED = "addon.updated"
    ADDON_DELETED = "addon.deleted"


class WebhookService:
    """Service for sending webhook notifications to Premium users."""
    
    @staticmethod
    def generate_webhook_secret() -> str:
        """Generate a secure webhook secret."""
        return secrets.token_hex(32)
    
    @staticmethod
    def sign_payload(payload: str, secret: str) -> str:
        """Sign a webhook payload using HMAC-SHA256."""
        signature = hmac.new(
            secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return f"sha256={signature}"
    
    @staticmethod
    def verify_signature(payload: str, signature: str, secret: str) -> bool:
        """Verify a webhook signature."""
        expected = WebhookService.sign_payload(payload, secret)
        return hmac.compare_digest(expected, signature)
    
    @staticmethod
    async def send_webhook(
        user: User,
        event_type: str,
        data: Dict[str, Any],
    ) -> bool:
        """
        Send a webhook notification to a user.
        
        Args:
            user: The user to send the webhook to
            event_type: The type of event (e.g., "version.released")
            data: The event data
            
        Returns:
            True if webhook was sent successfully, False otherwise
        """
        # Check if user is Premium and has webhooks enabled
        if user.subscription_tier != SubscriptionTier.PREMIUM:
            return False
        
        if not user.webhook_enabled or not user.webhook_url or not user.webhook_secret:
            return False
        
        # Build webhook payload
        payload = {
            "event": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": data,
        }
        
        payload_json = json.dumps(payload, default=str)
        
        # Sign the payload
        signature = WebhookService.sign_payload(payload_json, user.webhook_secret)
        
        # Send the webhook
        headers = {
            "Content-Type": "application/json",
            "X-PlexAddons-Event": event_type,
            "X-PlexAddons-Signature": signature,
            "X-PlexAddons-Timestamp": str(int(datetime.now(timezone.utc).timestamp())),
            "User-Agent": "PlexAddons-Webhook/1.0",
        }
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    user.webhook_url,
                    content=payload_json,
                    headers=headers,
                )
                return 200 <= response.status_code < 300
        except Exception as e:
            # Log error but don't fail the operation
            print(f"Webhook delivery failed for user {user.id}: {e}")
            return False
    
    @staticmethod
    async def notify_version_released(
        db: AsyncSession,
        addon: Addon,
        version: Version,
        owner: User,
    ) -> bool:
        """Send webhook notification when a new version is released."""
        data = {
            "addon": {
                "id": addon.id,
                "name": addon.name,
                "slug": addon.slug,
            },
            "version": {
                "id": version.id,
                "version": version.version,
                "download_url": version.download_url,
                "description": version.description,
                "changelog_url": version.changelog_url,
                "breaking": version.breaking,
                "urgent": version.urgent,
                "release_date": version.release_date.isoformat() if version.release_date else None,
            },
        }
        return await WebhookService.send_webhook(owner, WebhookEvent.VERSION_RELEASED, data)
    
    @staticmethod
    async def notify_version_updated(
        db: AsyncSession,
        addon: Addon,
        version: Version,
        owner: User,
    ) -> bool:
        """Send webhook notification when a version is updated."""
        data = {
            "addon": {
                "id": addon.id,
                "name": addon.name,
                "slug": addon.slug,
            },
            "version": {
                "id": version.id,
                "version": version.version,
                "download_url": version.download_url,
                "description": version.description,
                "breaking": version.breaking,
                "urgent": version.urgent,
            },
        }
        return await WebhookService.send_webhook(owner, WebhookEvent.VERSION_UPDATED, data)
    
    @staticmethod
    async def notify_version_deleted(
        db: AsyncSession,
        addon: Addon,
        version_str: str,
        owner: User,
    ) -> bool:
        """Send webhook notification when a version is deleted."""
        data = {
            "addon": {
                "id": addon.id,
                "name": addon.name,
                "slug": addon.slug,
            },
            "version": version_str,
        }
        return await WebhookService.send_webhook(owner, WebhookEvent.VERSION_DELETED, data)
    
    @staticmethod
    async def notify_addon_created(
        db: AsyncSession,
        addon: Addon,
        owner: User,
    ) -> bool:
        """Send webhook notification when an addon is created."""
        data = {
            "addon": {
                "id": addon.id,
                "name": addon.name,
                "slug": addon.slug,
                "description": addon.description,
                "homepage": addon.homepage,
                "is_public": addon.is_public,
            },
        }
        return await WebhookService.send_webhook(owner, WebhookEvent.ADDON_CREATED, data)
    
    @staticmethod
    async def notify_addon_updated(
        db: AsyncSession,
        addon: Addon,
        owner: User,
    ) -> bool:
        """Send webhook notification when an addon is updated."""
        data = {
            "addon": {
                "id": addon.id,
                "name": addon.name,
                "slug": addon.slug,
                "description": addon.description,
                "homepage": addon.homepage,
                "is_public": addon.is_public,
            },
        }
        return await WebhookService.send_webhook(owner, WebhookEvent.ADDON_UPDATED, data)
    
    @staticmethod
    async def notify_addon_deleted(
        db: AsyncSession,
        addon_name: str,
        addon_slug: str,
        owner: User,
    ) -> bool:
        """Send webhook notification when an addon is deleted."""
        data = {
            "addon": {
                "name": addon_name,
                "slug": addon_slug,
            },
        }
        return await WebhookService.send_webhook(owner, WebhookEvent.ADDON_DELETED, data)
    
    @staticmethod
    async def test_webhook(user: User) -> Dict[str, Any]:
        """
        Send a test webhook to verify configuration.
        
        Returns:
            Dict with success status and any error message
        """
        if not user.webhook_url or not user.webhook_secret:
            return {
                "success": False,
                "error": "Webhook URL or secret not configured",
            }
        
        test_payload = {
            "event": "test",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": {
                "message": "This is a test webhook from PlexAddons",
                "user_id": user.id,
            },
        }
        
        payload_json = json.dumps(test_payload, default=str)
        signature = WebhookService.sign_payload(payload_json, user.webhook_secret)
        
        headers = {
            "Content-Type": "application/json",
            "X-PlexAddons-Event": "test",
            "X-PlexAddons-Signature": signature,
            "X-PlexAddons-Timestamp": str(int(datetime.now(timezone.utc).timestamp())),
            "User-Agent": "PlexAddons-Webhook/1.0",
        }
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    user.webhook_url,
                    content=payload_json,
                    headers=headers,
                )
                
                if 200 <= response.status_code < 300:
                    return {
                        "success": True,
                        "status_code": response.status_code,
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Received status code {response.status_code}",
                        "status_code": response.status_code,
                    }
        except httpx.TimeoutException:
            return {
                "success": False,
                "error": "Request timed out after 10 seconds",
            }
        except httpx.RequestError as e:
            return {
                "success": False,
                "error": f"Request failed: {str(e)}",
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}",
            }


webhook_service = WebhookService()
