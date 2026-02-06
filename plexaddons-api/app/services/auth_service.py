import httpx
import logging
from cryptography.fernet import Fernet
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.config import get_settings
from app.models import User, SubscriptionTier
from app.core.security import create_access_token
from app.core.exceptions import UnauthorizedError, BadRequestError

settings = get_settings()
logger = logging.getLogger(__name__)

# Derive a Fernet key from the app secret_key (must be 32 url-safe base64-encoded bytes)
import base64
import hashlib
_fernet_key = base64.urlsafe_b64encode(hashlib.sha256(settings.secret_key.encode()).digest())
_fernet = Fernet(_fernet_key)


def _encrypt_token(token: str) -> str:
    """Encrypt a token for storage at rest."""
    return _fernet.encrypt(token.encode()).decode()


def _decrypt_token(encrypted: str) -> str:
    """Decrypt a stored token."""
    return _fernet.decrypt(encrypted.encode()).decode()


class AuthService:
    """Service for handling Discord OAuth2 authentication."""
    
    DISCORD_OAUTH_URL = "https://discord.com/oauth2/authorize"
    DISCORD_TOKEN_URL = f"{settings.discord_api_base}/oauth2/token"
    DISCORD_USER_URL = f"{settings.discord_api_base}/users/@me"
    
    @classmethod
    def get_oauth_url(cls, state: Optional[str] = None) -> str:
        """Generate Discord OAuth2 authorization URL."""
        params = {
            "client_id": settings.discord_client_id,
            "redirect_uri": settings.discord_redirect_uri,
            "response_type": "code",
            "scope": "identify email",
        }
        if state:
            params["state"] = state
        
        query = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{cls.DISCORD_OAUTH_URL}?{query}"
    
    @classmethod
    async def exchange_code(cls, code: str) -> dict:
        """Exchange authorization code for access tokens."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                cls.DISCORD_TOKEN_URL,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": settings.discord_redirect_uri,
                },
                auth=(settings.discord_client_id, settings.discord_client_secret),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            
            if response.status_code != 200:
                logger.error(f"Discord code exchange failed: {response.status_code} {response.text}")
                raise BadRequestError("Failed to exchange authorization code")
            
            return response.json()
    
    @classmethod
    async def refresh_discord_token(cls, refresh_token: str) -> dict:
        """Refresh Discord access token."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                cls.DISCORD_TOKEN_URL,
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                },
                auth=(settings.discord_client_id, settings.discord_client_secret),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            
            if response.status_code != 200:
                raise UnauthorizedError("Failed to refresh Discord token")
            
            return response.json()
    
    @classmethod
    async def get_discord_user(cls, access_token: str) -> dict:
        """Fetch user information from Discord."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                cls.DISCORD_USER_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            
            if response.status_code != 200:
                raise UnauthorizedError("Failed to fetch Discord user")
            
            return response.json()
    
    @classmethod
    async def get_or_create_user(
        cls, 
        db: AsyncSession, 
        tokens: dict,
        background_tasks: Optional[BackgroundTasks] = None
    ) -> User:
        """Get existing user or create new one from Discord OAuth response."""
        from app.services.email_service import email_service
        from app.services.user_service import UserService
        
        # Get Discord user info
        discord_user = await cls.get_discord_user(tokens["access_token"])
        
        # Check if user exists
        result = await db.execute(
            select(User).where(User.discord_id == discord_user["id"])
        )
        user = result.scalar_one_or_none()
        
        token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=tokens.get("expires_in", 604800))
        is_new_user = False
        
        if user:
            # Update existing user
            user.discord_username = discord_user["username"]
            user.discord_avatar = discord_user.get("avatar")
            user.email = discord_user.get("email")
            user.discord_access_token = _encrypt_token(tokens["access_token"])
            user.discord_refresh_token = _encrypt_token(tokens["refresh_token"]) if tokens.get("refresh_token") else None
            user.discord_token_expires_at = token_expires_at
            user.last_login_at = datetime.now(timezone.utc)
        else:
            # Create new user
            is_initial_admin = (
                settings.initial_admin_discord_id and
                discord_user["id"] == settings.initial_admin_discord_id
            )

            user = User(
                discord_id=discord_user["id"],
                discord_username=discord_user["username"],
                discord_avatar=discord_user.get("avatar"),
                email=discord_user.get("email"),
                discord_access_token=_encrypt_token(tokens["access_token"]),
                discord_refresh_token=_encrypt_token(tokens["refresh_token"]) if tokens.get("refresh_token") else None,
                discord_token_expires_at=token_expires_at,
                subscription_tier=SubscriptionTier.FREE,
                storage_quota_bytes=settings.storage_quota_free,
                is_admin=is_initial_admin,
                last_login_at=datetime.now(timezone.utc),
            )
            db.add(user)
            is_new_user = True
        
        await db.commit()
        await db.refresh(user)
        
        # Sync automatic badges (early_adopter, beta_tester, addon_creator, etc.)
        await UserService.sync_automatic_badges(db, user)
        
        # Send welcome email and admin notification for new users
        if is_new_user and user.email and background_tasks:
            background_tasks.add_task(email_service.send_welcome_email, user)
            background_tasks.add_task(email_service.send_admin_new_user, user)
        
        return user
    
    @classmethod
    def create_jwt_token(cls, user: User) -> str:
        """Create JWT token for user."""
        return create_access_token(
            data={
                "sub": str(user.id),
                "discord_id": user.discord_id,
                "is_admin": user.is_admin,
                "tier": user.subscription_tier.value,
            }
        )
    
    @classmethod
    async def maybe_refresh_discord_token(cls, db: AsyncSession, user: User) -> User:
        """Refresh Discord token if it's about to expire (within 25% of lifetime)."""
        if not user.discord_token_expires_at or not user.discord_refresh_token:
            return user
        
        # Check if token expires within 25% of the 7-day lifetime (~1.75 days)
        refresh_threshold = timedelta(days=1, hours=18)
        if user.discord_token_expires_at - datetime.now(timezone.utc) > refresh_threshold:
            return user
        
        try:
            new_tokens = await cls.refresh_discord_token(user.discord_refresh_token)
            user.discord_access_token = new_tokens["access_token"]
            user.discord_refresh_token = new_tokens.get("refresh_token", user.discord_refresh_token)
            user.discord_token_expires_at = datetime.now(timezone.utc) + timedelta(
                seconds=new_tokens.get("expires_in", 604800)
            )
            await db.commit()
        except Exception:
            # If refresh fails, continue with existing token
            pass
        
        return user
