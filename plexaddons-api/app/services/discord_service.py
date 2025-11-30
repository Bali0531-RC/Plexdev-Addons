"""
Discord Service for PlexAddons
Handles Discord Bot interactions (separate from OAuth2) for DM notifications
"""
import asyncio
import logging
from typing import Optional, Dict, Any

import aiohttp

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class DiscordService:
    """
    Discord Bot service for sending DMs to admin.
    Uses a separate bot token from OAuth2 application.
    """
    
    DISCORD_API_BASE = "https://discord.com/api/v10"
    
    def __init__(self):
        self.bot_token = settings.discord_bot_token
        self.dm_enabled = settings.discord_bot_dm_enabled
        self.admin_user_id = settings.discord_admin_dm_user_id
    
    @property
    def is_configured(self) -> bool:
        """Check if Discord bot is properly configured"""
        return bool(self.bot_token and self.dm_enabled and self.admin_user_id)
    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        json_data: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Make an authenticated request to Discord API"""
        if not self.bot_token:
            logger.warning("Discord bot token not configured")
            return None
        
        headers = {
            "Authorization": f"Bot {self.bot_token}",
            "Content-Type": "application/json"
        }
        
        url = f"{self.DISCORD_API_BASE}{endpoint}"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method,
                    url,
                    headers=headers,
                    json=json_data
                ) as response:
                    if response.status == 204:
                        return {}
                    
                    data = await response.json()
                    
                    if response.status >= 400:
                        logger.error(f"Discord API error: {response.status} - {data}")
                        return None
                    
                    return data
                    
        except Exception as e:
            logger.error(f"Discord API request failed: {e}")
            return None
    
    async def create_dm_channel(self, user_id: str) -> Optional[str]:
        """Create or get existing DM channel with a user"""
        data = await self._make_request(
            "POST",
            "/users/@me/channels",
            {"recipient_id": user_id}
        )
        
        if data:
            return data.get("id")
        return None
    
    async def send_dm(
        self,
        user_id: str,
        content: str,
        embed: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Send a DM to a Discord user"""
        # First create/get DM channel
        channel_id = await self.create_dm_channel(user_id)
        
        if not channel_id:
            logger.error(f"Failed to create DM channel with user {user_id}")
            return False
        
        # Send message
        message_data = {"content": content}
        if embed:
            message_data["embeds"] = [embed]
        
        result = await self._make_request(
            "POST",
            f"/channels/{channel_id}/messages",
            message_data
        )
        
        if result:
            logger.info(f"DM sent to user {user_id}")
            return True
        return False
    
    async def send_admin_dm(
        self,
        content: str,
        embed: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Send a DM to the configured admin user"""
        if not self.is_configured:
            logger.debug("Discord DM notifications not configured, skipping")
            return False
        
        return await self.send_dm(self.admin_user_id, content, embed)
    
    # ============== TICKET NOTIFICATIONS ==============
    
    async def notify_new_ticket(
        self,
        ticket_id: int,
        user_name: str,
        subject: str,
        category: str,
        priority: str,
        is_paid_user: bool
    ) -> bool:
        """Notify admin of a new support ticket"""
        if not self.is_configured:
            return False
        
        # Priority badge
        priority_emoji = {
            "low": "🟢",
            "normal": "🟡",
            "high": "🟠",
            "urgent": "🔴"
        }.get(priority, "⚪")
        
        paid_badge = "💎 " if is_paid_user else ""
        
        embed = {
            "title": f"{priority_emoji} New Ticket #{ticket_id}",
            "description": subject,
            "color": 0xFF6B6B if is_paid_user else 0x4ECDC4,
            "fields": [
                {
                    "name": "From",
                    "value": f"{paid_badge}{user_name}",
                    "inline": True
                },
                {
                    "name": "Category",
                    "value": category.replace("_", " ").title(),
                    "inline": True
                },
                {
                    "name": "Priority",
                    "value": priority.title(),
                    "inline": True
                }
            ],
            "footer": {
                "text": "PlexAddons Support"
            }
        }
        
        content = f"🎫 **New support ticket** from {'paid user ' if is_paid_user else ''}{user_name}"
        
        return await self.send_admin_dm(content, embed)
    
    async def notify_ticket_reply(
        self,
        ticket_id: int,
        user_name: str,
        subject: str,
        message_preview: str,
        is_paid_user: bool
    ) -> bool:
        """Notify admin of a reply to a ticket"""
        if not self.is_configured:
            return False
        
        # Truncate message preview
        if len(message_preview) > 200:
            message_preview = message_preview[:197] + "..."
        
        paid_badge = "💎 " if is_paid_user else ""
        
        embed = {
            "title": f"💬 Reply on Ticket #{ticket_id}",
            "description": f"**{subject}**\n\n{message_preview}",
            "color": 0xFF6B6B if is_paid_user else 0x95E1D3,
            "fields": [
                {
                    "name": "From",
                    "value": f"{paid_badge}{user_name}",
                    "inline": True
                }
            ],
            "footer": {
                "text": "PlexAddons Support"
            }
        }
        
        content = f"💬 **New reply** on ticket #{ticket_id} from {user_name}"
        
        return await self.send_admin_dm(content, embed)
    
    async def notify_urgent_ticket(
        self,
        ticket_id: int,
        user_name: str,
        subject: str,
        reason: str = "Priority escalated"
    ) -> bool:
        """Send urgent notification for high-priority tickets"""
        if not self.is_configured:
            return False
        
        embed = {
            "title": f"🚨 URGENT: Ticket #{ticket_id}",
            "description": subject,
            "color": 0xFF0000,
            "fields": [
                {
                    "name": "User",
                    "value": user_name,
                    "inline": True
                },
                {
                    "name": "Reason",
                    "value": reason,
                    "inline": True
                }
            ],
            "footer": {
                "text": "PlexAddons Support - Immediate attention required"
            }
        }
        
        content = f"🚨 **URGENT TICKET** #{ticket_id} requires immediate attention!"
        
        return await self.send_admin_dm(content, embed)


# Global service instance
discord_service = DiscordService()
