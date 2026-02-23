"""Webhook notification service for Premium users.

Supports:
- Multiple endpoints per user with event filtering
- Exponential backoff retries (1m, 5m, 30m, 2h, 12h)
- Delivery logging (last 100 per endpoint)
- Custom payload templates
- Discord webhook auto-detection and formatting
"""

import hmac
import hashlib
import json
import re
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, Tuple
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func
from app.models import User, Addon, Version, SubscriptionTier, WebhookEndpoint, WebhookDelivery
from app.config import get_settings
from app.api.deps import get_effective_tier

settings = get_settings()

# Retry backoff intervals in minutes
RETRY_INTERVALS = [1, 5, 30, 120, 720]  # 1m, 5m, 30m, 2h, 12h


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
    def render_template(template: str, data: Dict[str, Any]) -> str:
        """Simple template rendering: replaces {{key}} with values from data.
        Supports dot notation for nested access: {{addon.name}}"""
        def replacer(match):
            key_path = match.group(1).strip()
            obj = data
            for part in key_path.split('.'):
                if isinstance(obj, dict):
                    obj = obj.get(part)
                else:
                    return match.group(0)
                if obj is None:
                    return ''
            return str(obj) if obj is not None else ''
        return re.sub(r'\{\{(.+?)\}\}', replacer, template)

    @staticmethod
    def format_discord_payload(event_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Format payload for Discord webhook (embeds)."""
        colors = {
            WebhookEvent.VERSION_RELEASED: 0x22c55e,
            WebhookEvent.VERSION_UPDATED: 0x3b82f6,
            WebhookEvent.VERSION_DELETED: 0xef4444,
            WebhookEvent.ADDON_CREATED: 0x8b5cf6,
            WebhookEvent.ADDON_UPDATED: 0xf59e0b,
            WebhookEvent.ADDON_DELETED: 0xef4444,
            "test": 0x6366f1,
        }
        
        color = colors.get(event_type, 0x5865f2)
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
        
        return {"embeds": [embed]}

    # ==================== Multi-endpoint delivery ====================

    @staticmethod
    async def deliver_to_endpoint(
        endpoint: WebhookEndpoint,
        event_type: str,
        payload_json: str,
    ) -> Tuple[bool, Optional[int], Optional[str]]:
        """Deliver a payload to a single endpoint.
        Returns: (success, status_code, error_message)"""
        is_discord = WebhookService.is_discord_webhook(endpoint.url)

        headers = {
            "Content-Type": "application/json",
            "User-Agent": "PlexAddons-Webhook/2.0",
        }
        if not is_discord:
            signature = WebhookService.sign_payload(payload_json, endpoint.secret)
            headers["X-PlexAddons-Event"] = event_type
            headers["X-PlexAddons-Signature"] = signature
            headers["X-PlexAddons-Timestamp"] = str(int(datetime.now(timezone.utc).timestamp()))
            headers["X-PlexAddons-Endpoint-Id"] = str(endpoint.id)

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(endpoint.url, content=payload_json, headers=headers)
                if 200 <= response.status_code < 300:
                    return True, response.status_code, None
                else:
                    body = response.text[:500] if response.text else ""
                    return False, response.status_code, f"HTTP {response.status_code}: {body}"
        except httpx.TimeoutException:
            return False, None, "Request timed out after 10 seconds"
        except httpx.RequestError as e:
            return False, None, f"Request failed: {str(e)}"
        except Exception as e:
            return False, None, f"Unexpected error: {str(e)}"

    @staticmethod
    async def _build_payload(
        endpoint: WebhookEndpoint,
        event_type: str,
        data: Dict[str, Any],
    ) -> str:
        """Build the JSON payload for an endpoint, applying templates if set."""
        is_discord = WebhookService.is_discord_webhook(endpoint.url)

        if is_discord:
            payload = WebhookService.format_discord_payload(event_type, data)
        elif endpoint.payload_template:
            rendered = WebhookService.render_template(endpoint.payload_template, {
                "event": event_type,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                **data,
            })
            try:
                json.loads(rendered)
                return rendered
            except json.JSONDecodeError:
                payload = {"event": event_type, "timestamp": datetime.now(timezone.utc).isoformat(), "data": data, "template_error": "Invalid JSON after rendering"}
        else:
            payload = {"event": event_type, "timestamp": datetime.now(timezone.utc).isoformat(), "data": data}

        return json.dumps(payload, default=str)

    @staticmethod
    async def _prune_deliveries(db: AsyncSession, endpoint_id: int, keep: int = 100):
        """Keep only the latest N deliveries per endpoint."""
        count_result = await db.execute(
            select(func.count()).where(WebhookDelivery.endpoint_id == endpoint_id)
        )
        total = count_result.scalar() or 0
        if total > keep:
            oldest = await db.execute(
                select(WebhookDelivery.id)
                .where(WebhookDelivery.endpoint_id == endpoint_id)
                .order_by(WebhookDelivery.created_at)
                .limit(total - keep)
            )
            ids_to_delete = [row[0] for row in oldest.all()]
            if ids_to_delete:
                await db.execute(
                    delete(WebhookDelivery).where(WebhookDelivery.id.in_(ids_to_delete))
                )

    @staticmethod
    async def dispatch_event(
        db: AsyncSession,
        user: User,
        event_type: str,
        data: Dict[str, Any],
    ) -> int:
        """Dispatch a webhook event to all matching endpoints for a user.
        Returns count of deliveries created."""
        effective_tier = get_effective_tier(user)
        if effective_tier != SubscriptionTier.PREMIUM:
            await WebhookService._send_legacy_webhook(user, event_type, data)
            return 0

        result = await db.execute(
            select(WebhookEndpoint).where(
                WebhookEndpoint.user_id == user.id,
                WebhookEndpoint.is_active == True,
            )
        )
        endpoints = result.scalars().all()

        if not endpoints:
            await WebhookService._send_legacy_webhook(user, event_type, data)
            return 0

        count = 0
        for endpoint in endpoints:
            if endpoint.event_filter:
                if event_type not in endpoint.event_filter:
                    continue

            payload_json = await WebhookService._build_payload(endpoint, event_type, data)

            success, status_code, error = await WebhookService.deliver_to_endpoint(
                endpoint, event_type, payload_json
            )

            now = datetime.now(timezone.utc)
            delivery = WebhookDelivery(
                endpoint_id=endpoint.id,
                event_type=event_type,
                payload=payload_json,
                status="success" if success else "pending",
                status_code=status_code,
                error_message=error,
                attempt=1,
                max_attempts=6,
                delivered_at=now if success else None,
            )

            if not success:
                delivery.next_retry_at = now + timedelta(minutes=RETRY_INTERVALS[0])

            db.add(delivery)
            await WebhookService._prune_deliveries(db, endpoint.id)
            count += 1

        await db.commit()
        return count

    @staticmethod
    async def process_retries(db: AsyncSession):
        """Process pending webhook retries. Called by scheduler."""
        now = datetime.now(timezone.utc)
        result = await db.execute(
            select(WebhookDelivery)
            .where(
                WebhookDelivery.status == "pending",
                WebhookDelivery.next_retry_at <= now,
            )
            .limit(50)
        )
        deliveries = result.scalars().all()

        for delivery in deliveries:
            ep_result = await db.execute(
                select(WebhookEndpoint).where(WebhookEndpoint.id == delivery.endpoint_id)
            )
            endpoint = ep_result.scalar_one_or_none()
            if not endpoint or not endpoint.is_active:
                delivery.status = "failed"
                delivery.error_message = "Endpoint disabled or deleted"
                continue

            success, status_code, error = await WebhookService.deliver_to_endpoint(
                endpoint, delivery.event_type, delivery.payload
            )

            delivery.attempt += 1
            delivery.status_code = status_code

            if success:
                delivery.status = "success"
                delivery.delivered_at = now
                delivery.error_message = None
                delivery.next_retry_at = None
            elif delivery.attempt >= delivery.max_attempts:
                delivery.status = "failed"
                delivery.error_message = error
                delivery.next_retry_at = None
            else:
                retry_idx = min(delivery.attempt - 1, len(RETRY_INTERVALS) - 1)
                delivery.next_retry_at = now + timedelta(minutes=RETRY_INTERVALS[retry_idx])
                delivery.error_message = error

        await db.commit()

    @staticmethod
    async def test_endpoint(endpoint: WebhookEndpoint) -> Dict[str, Any]:
        """Send a test event to a specific endpoint."""
        data = {"message": "This is a test webhook from PlexAddons", "endpoint_id": endpoint.id}
        payload_json = await WebhookService._build_payload(endpoint, "test", data)
        success, status_code, error = await WebhookService.deliver_to_endpoint(endpoint, "test", payload_json)

        if success:
            return {"success": True, "status_code": status_code}
        return {"success": False, "status_code": status_code, "error": error or "Delivery failed"}

    # ==================== Legacy single-endpoint support ====================

    @staticmethod
    async def _send_legacy_webhook(user: User, event_type: str, data: Dict[str, Any]) -> bool:
        """Fallback: send to the legacy single webhook_url on User model."""
        if not user.webhook_enabled or not user.webhook_url or not user.webhook_secret:
            return False

        is_discord = WebhookService.is_discord_webhook(user.webhook_url)
        if is_discord:
            payload = WebhookService.format_discord_payload(event_type, data)
        else:
            payload = {"event": event_type, "timestamp": datetime.now(timezone.utc).isoformat(), "data": data}

        payload_json = json.dumps(payload, default=str)
        signature = WebhookService.sign_payload(payload_json, user.webhook_secret)

        headers = {"Content-Type": "application/json", "User-Agent": "PlexAddons-Webhook/1.0"}
        if not is_discord:
            headers["X-PlexAddons-Event"] = event_type
            headers["X-PlexAddons-Signature"] = signature
            headers["X-PlexAddons-Timestamp"] = str(int(datetime.now(timezone.utc).timestamp()))

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(user.webhook_url, content=payload_json, headers=headers)
                return 200 <= response.status_code < 300
        except Exception as e:
            print(f"Legacy webhook delivery failed for user {user.id}: {e}")
            return False

    @staticmethod
    async def send_webhook(
        user: User,
        event_type: str,
        data: Dict[str, Any],
    ) -> bool:
        """Legacy: Send a webhook notification via single user webhook URL."""
        return await WebhookService._send_legacy_webhook(user, event_type, data)

    # ==================== Convenience methods ====================

    @staticmethod
    async def notify_version_released(
        db: AsyncSession,
        addon: Addon,
        version: Version,
        owner: User,
    ) -> bool:
        data = {
            "addon": {"id": addon.id, "name": addon.name, "slug": addon.slug},
            "version": {
                "id": version.id, "version": version.version,
                "download_url": version.download_url, "description": version.description,
                "changelog_url": version.changelog_url, "breaking": version.breaking,
                "urgent": version.urgent,
                "release_date": version.release_date.isoformat() if version.release_date else None,
            },
        }
        count = await WebhookService.dispatch_event(db, owner, WebhookEvent.VERSION_RELEASED, data)
        return count > 0

    @staticmethod
    async def notify_version_updated(
        db: AsyncSession,
        addon: Addon,
        version: Version,
        owner: User,
    ) -> bool:
        data = {
            "addon": {"id": addon.id, "name": addon.name, "slug": addon.slug},
            "version": {
                "id": version.id, "version": version.version,
                "download_url": version.download_url, "description": version.description,
                "breaking": version.breaking, "urgent": version.urgent,
            },
        }
        count = await WebhookService.dispatch_event(db, owner, WebhookEvent.VERSION_UPDATED, data)
        return count > 0

    @staticmethod
    async def notify_version_deleted(
        db: AsyncSession,
        addon: Addon,
        version_str: str,
        owner: User,
    ) -> bool:
        data = {
            "addon": {"id": addon.id, "name": addon.name, "slug": addon.slug},
            "version": version_str,
        }
        count = await WebhookService.dispatch_event(db, owner, WebhookEvent.VERSION_DELETED, data)
        return count > 0

    @staticmethod
    async def notify_addon_created(
        db: AsyncSession,
        addon: Addon,
        owner: User,
    ) -> bool:
        data = {
            "addon": {
                "id": addon.id, "name": addon.name, "slug": addon.slug,
                "description": addon.description, "homepage": addon.homepage,
                "is_public": addon.is_public,
            },
        }
        count = await WebhookService.dispatch_event(db, owner, WebhookEvent.ADDON_CREATED, data)
        return count > 0

    @staticmethod
    async def notify_addon_updated(
        db: AsyncSession,
        addon: Addon,
        owner: User,
    ) -> bool:
        data = {
            "addon": {
                "id": addon.id, "name": addon.name, "slug": addon.slug,
                "description": addon.description, "homepage": addon.homepage,
                "is_public": addon.is_public,
            },
        }
        count = await WebhookService.dispatch_event(db, owner, WebhookEvent.ADDON_UPDATED, data)
        return count > 0

    @staticmethod
    async def notify_addon_deleted(
        db: AsyncSession,
        addon_name: str,
        addon_slug: str,
        owner: User,
    ) -> bool:
        data = {"addon": {"name": addon_name, "slug": addon_slug}}
        count = await WebhookService.dispatch_event(db, owner, WebhookEvent.ADDON_DELETED, data)
        return count > 0

    @staticmethod
    async def test_webhook(user: User) -> Dict[str, Any]:
        """Legacy test for the single user webhook URL."""
        if not user.webhook_url or not user.webhook_secret:
            return {"success": False, "error": "Webhook URL or secret not configured"}

        is_discord = WebhookService.is_discord_webhook(user.webhook_url)
        if is_discord:
            test_payload = WebhookService.format_discord_payload("test", {
                "message": "This is a test webhook from PlexAddons",
                "user_id": user.id,
            })
        else:
            test_payload = {
                "event": "test",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data": {"message": "This is a test webhook from PlexAddons", "user_id": user.id},
            }

        payload_json = json.dumps(test_payload, default=str)
        signature = WebhookService.sign_payload(payload_json, user.webhook_secret)

        headers = {"Content-Type": "application/json", "User-Agent": "PlexAddons-Webhook/1.0"}
        if not is_discord:
            headers["X-PlexAddons-Event"] = "test"
            headers["X-PlexAddons-Signature"] = signature
            headers["X-PlexAddons-Timestamp"] = str(int(datetime.now(timezone.utc).timestamp()))

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(user.webhook_url, content=payload_json, headers=headers)
                if 200 <= response.status_code < 300:
                    return {"success": True, "status_code": response.status_code}
                return {"success": False, "error": f"Received status code {response.status_code}", "status_code": response.status_code}
        except httpx.TimeoutException:
            return {"success": False, "error": "Request timed out after 10 seconds"}
        except httpx.RequestError as e:
            return {"success": False, "error": f"Request failed: {str(e)}"}
        except Exception as e:
            return {"success": False, "error": f"Unexpected error: {str(e)}"}


webhook_service = WebhookService()
