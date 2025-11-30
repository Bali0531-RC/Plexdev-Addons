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
    def is_discord_webhook(url: str) -> bool:
        """Check if URL is a Discord webhook."""
        return 'discord.com/api/webhooks/' in url or 'discordapp.com/api/webhooks/' in url
    
    @staticmethod
    def format_discord_payload(event_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Format payload for Discord webhook (embeds)."""
        # Map event types to colors
        colors = {
            WebhookEvent.VERSION_RELEASED: 0x22c55e,  # green
            WebhookEvent.VERSION_UPDATED: 0x3b82f6,   # blue
            WebhookEvent.VERSION_DELETED: 0xef4444,   # red
            WebhookEvent.ADDON_CREATED: 0x8b5cf6,     # purple
            WebhookEvent.ADDON_UPDATED: 0xf59e0b,    # orange
            WebhookEvent.ADDON_DELETED: 0xef4444,    # red
            "test": 0x6366f1,                         # indigo
        }
        
        color = colors.get(event_type, 0x5865f2)
        
        # Build embed based on event type
        embed = {
            "color": color,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "footer": {"text": "PlexAddons"},
        }
        
        if event_type == WebhookEvent.VERSION_RELEASED:
            addon = data.get("addon", {})
            version = data.get("version", {})
            embed["title"] = f"🚀 New Version Released: {addon.get('name')}"
            embed["description"] = f"Version **{version.get('version')}** is now available!"
            embed["fields"] = []
            if version.get("description"):
                embed["fields"].append({"name": "Description", "value": version.get("description")[:1024], "inline": False})
            if version.get("breaking"):
                embed["fields"].append({"name": "⚠️ Breaking Changes", "value": "This version contains breaking changes", "inline": True})
            if version.get("urgent"):
                embed["fields"].append({"name": "🔴 Urgent", "value": "This is an urgent update", "inline": True})
            embed["url"] = version.get("download_url")
        elif event_type == WebhookEvent.VERSION_UPDATED:
            addon = data.get("addon", {})
            version = data.get("version", {})
            embed["title"] = f"📝 Version Updated: {addon.get('name')}"
            embed["description"] = f"Version **{version.get('version')}** has been updated."
        elif event_type == WebhookEvent.VERSION_DELETED:
            addon = data.get("addon", {})
            embed["title"] = f"🗑️ Version Deleted: {addon.get('name')}"
            embed["description"] = f"Version **{data.get('version')}** has been removed."
        elif event_type == WebhookEvent.ADDON_CREATED:
            addon = data.get("addon", {})
            embed["title"] = f"📦 New Addon Created: {addon.get('name')}"
            embed["description"] = addon.get("description") or "No description"
        elif event_type == WebhookEvent.ADDON_UPDATED:
            addon = data.get("addon", {})
            embed["title"] = f"✏️ Addon Updated: {addon.get('name')}"
            embed["description"] = addon.get("description") or "No description"
        elif event_type == WebhookEvent.ADDON_DELETED:
            addon = data.get("addon", {})
            embed["title"] = f"🗑️ Addon Deleted: {addon.get('name')}"
            embed["description"] = f"The addon **{addon.get('slug')}** has been removed."
        elif event_type == "test":
            embed["title"] = "🧪 PlexAddons Webhook Test"
            embed["description"] = "Your webhook is configured correctly!"
            embed["fields"] = [
                {"name": "Status", "value": "✅ Connected", "inline": True},
            ]
        else:
            embed["title"] = f"📣 {event_type}"
            embed["description"] = json.dumps(data, indent=2, default=str)[:2000]
        
        return {
            "embeds": [embed]
        }
    
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
        
        # Check if this is a Discord webhook
        is_discord = WebhookService.is_discord_webhook(user.webhook_url)
        
        if is_discord:
            # Use Discord embed format
            payload = WebhookService.format_discord_payload(event_type, data)
        else:
            # Use standard PlexAddons format
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
            "User-Agent": "PlexAddons-Webhook/1.0",
        }
        
        # Only add custom headers for non-Discord webhooks
        if not is_discord:
            headers["X-PlexAddons-Event"] = event_type
            headers["X-PlexAddons-Signature"] = signature
            headers["X-PlexAddons-Timestamp"] = str(int(datetime.now(timezone.utc).timestamp()))
        
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
        
        # Check if this is a Discord webhook
        is_discord = WebhookService.is_discord_webhook(user.webhook_url)
        
        if is_discord:
            # Use Discord embed format for test
            test_payload = WebhookService.format_discord_payload("test", {
                "message": "This is a test webhook from PlexAddons",
                "user_id": user.id,
            })
        else:
            # Standard format
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
            "User-Agent": "PlexAddons-Webhook/1.0",
        }
        
        # Only add custom headers for non-Discord webhooks
        if not is_discord:
            headers["X-PlexAddons-Event"] = "test"
            headers["X-PlexAddons-Signature"] = signature
            headers["X-PlexAddons-Timestamp"] = str(int(datetime.now(timezone.utc).timestamp()))
        
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
