"""
API Key service for managing user API keys with granular permissions.
"""

import secrets
import hashlib
from datetime import datetime, timezone
from typing import Optional, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models import ApiKey, User, SubscriptionTier, ApiKeyScope
from app.api.deps import get_effective_tier
from app.core.exceptions import ForbiddenError, BadRequestError, NotFoundError


# Define which scopes are available for each tier
TIER_SCOPES = {
    SubscriptionTier.FREE: [],
    SubscriptionTier.PRO: [
        ApiKeyScope.ADDONS_READ,
        ApiKeyScope.VERSIONS_READ,
        ApiKeyScope.ANALYTICS_READ,
        ApiKeyScope.VERSIONS_WRITE,  # Pro can publish versions via CI/CD
    ],
    SubscriptionTier.PREMIUM: [
        ApiKeyScope.ADDONS_READ,
        ApiKeyScope.VERSIONS_READ,
        ApiKeyScope.ANALYTICS_READ,
        ApiKeyScope.VERSIONS_WRITE,
        ApiKeyScope.ADDONS_WRITE,
        ApiKeyScope.WEBHOOKS_MANAGE,
        ApiKeyScope.FULL_ACCESS,
    ],
}

# Maximum number of API keys per tier
MAX_KEYS_PER_TIER = {
    SubscriptionTier.FREE: 0,
    SubscriptionTier.PRO: 3,
    SubscriptionTier.PREMIUM: 10,
}


class ApiKeyService:
    """Service for API key management."""
    
    @staticmethod
    def generate_key() -> Tuple[str, str, str]:
        """
        Generate a new API key.
        
        Returns:
            Tuple of (full_key, key_prefix, key_hash)
            - full_key: The complete key to show to user (only once!)
            - key_prefix: First 8 chars for display (pa_xxxx)
            - key_hash: SHA-256 hash for storage
        """
        # Generate 32 random bytes = 64 hex chars
        random_bytes = secrets.token_hex(32)
        full_key = f"pa_{random_bytes}"
        key_prefix = full_key[:10]  # pa_ + first 7 hex chars
        key_hash = hashlib.sha256(full_key.encode()).hexdigest()
        
        return full_key, key_prefix, key_hash
    
    @staticmethod
    def hash_key(key: str) -> str:
        """Hash an API key for lookup."""
        return hashlib.sha256(key.encode()).hexdigest()
    
    @staticmethod
    def get_available_scopes(user: User) -> List[ApiKeyScope]:
        """Get scopes available for user's tier."""
        effective_tier = get_effective_tier(user)
        return TIER_SCOPES.get(effective_tier, [])
    
    @staticmethod
    def validate_scopes(user: User, requested_scopes: List[str]) -> List[str]:
        """
        Validate and filter scopes based on user's tier.
        
        Args:
            user: The user creating the key
            requested_scopes: List of scope strings requested
            
        Returns:
            List of valid scope strings
            
        Raises:
            ForbiddenError if user tries to request unavailable scopes
        """
        available = ApiKeyService.get_available_scopes(user)
        available_values = [s.value for s in available]
        
        # Check for invalid scopes
        invalid = [s for s in requested_scopes if s not in available_values]
        if invalid:
            raise ForbiddenError(
                f"Scope(s) not available for your tier: {', '.join(invalid)}. "
                f"Available scopes: {', '.join(available_values)}"
            )
        
        return requested_scopes
    
    @staticmethod
    async def get_key_count(db: AsyncSession, user_id: int) -> int:
        """Get number of active API keys for a user."""
        result = await db.execute(
            select(func.count(ApiKey.id))
            .where(ApiKey.user_id == user_id)
            .where(ApiKey.is_active == True)
        )
        return result.scalar() or 0
    
    @staticmethod
    async def create_key(
        db: AsyncSession,
        user: User,
        name: str,
        scopes: List[str],
        expires_at: Optional[datetime] = None,
    ) -> Tuple[ApiKey, str]:
        """
        Create a new API key for a user.
        
        Args:
            db: Database session
            user: The user creating the key
            name: Friendly name for the key
            scopes: List of scope strings
            expires_at: Optional expiration datetime
            
        Returns:
            Tuple of (ApiKey model, full_key string)
            The full_key is only returned once and should be shown to user!
            
        Raises:
            ForbiddenError if user can't create keys or exceeds limit
        """
        effective_tier = get_effective_tier(user)
        
        # Check if tier allows API keys
        max_keys = MAX_KEYS_PER_TIER.get(effective_tier, 0)
        if max_keys == 0:
            raise ForbiddenError("API keys require Pro or Premium subscription")
        
        # Check key limit
        current_count = await ApiKeyService.get_key_count(db, user.id)
        if current_count >= max_keys:
            raise ForbiddenError(
                f"You have reached the maximum number of API keys ({max_keys}) for your tier"
            )
        
        # Validate scopes
        if not scopes:
            raise BadRequestError("At least one scope is required")
        
        validated_scopes = ApiKeyService.validate_scopes(user, scopes)
        
        # Generate key
        full_key, key_prefix, key_hash = ApiKeyService.generate_key()
        
        # Create record
        api_key = ApiKey(
            user_id=user.id,
            name=name,
            key_prefix=key_prefix,
            key_hash=key_hash,
            scopes=validated_scopes,
            expires_at=expires_at,
        )
        db.add(api_key)
        await db.commit()
        await db.refresh(api_key)
        
        return api_key, full_key
    
    @staticmethod
    async def get_user_keys(db: AsyncSession, user_id: int) -> List[ApiKey]:
        """Get all API keys for a user."""
        result = await db.execute(
            select(ApiKey)
            .where(ApiKey.user_id == user_id)
            .order_by(ApiKey.created_at.desc())
        )
        return list(result.scalars().all())
    
    @staticmethod
    async def get_key_by_id(db: AsyncSession, key_id: int, user_id: int) -> Optional[ApiKey]:
        """Get an API key by ID, ensuring it belongs to user."""
        result = await db.execute(
            select(ApiKey)
            .where(ApiKey.id == key_id)
            .where(ApiKey.user_id == user_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_key_by_value(db: AsyncSession, key_value: str) -> Optional[ApiKey]:
        """
        Get an API key by its full value.
        
        Args:
            db: Database session
            key_value: The full API key string (pa_...)
            
        Returns:
            ApiKey if found and valid, None otherwise
        """
        if not key_value or not key_value.startswith("pa_"):
            return None
        
        key_hash = ApiKeyService.hash_key(key_value)
        result = await db.execute(
            select(ApiKey)
            .where(ApiKey.key_hash == key_hash)
            .where(ApiKey.is_active == True)
        )
        api_key = result.scalar_one_or_none()
        
        if not api_key:
            return None
        
        # Check expiration
        if api_key.expires_at and api_key.expires_at < datetime.now(timezone.utc):
            return None
        
        return api_key
    
    @staticmethod
    async def update_key(
        db: AsyncSession,
        api_key: ApiKey,
        user: User,
        name: Optional[str] = None,
        scopes: Optional[List[str]] = None,
        expires_at: Optional[datetime] = None,
    ) -> ApiKey:
        """Update an API key's name, scopes, or expiration."""
        if name is not None:
            api_key.name = name
        
        if scopes is not None:
            validated_scopes = ApiKeyService.validate_scopes(user, scopes)
            api_key.scopes = validated_scopes
        
        if expires_at is not None:
            api_key.expires_at = expires_at
        
        await db.commit()
        await db.refresh(api_key)
        return api_key
    
    @staticmethod
    async def revoke_key(db: AsyncSession, api_key: ApiKey) -> ApiKey:
        """Revoke an API key."""
        api_key.is_active = False
        api_key.revoked_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(api_key)
        return api_key
    
    @staticmethod
    async def delete_key(db: AsyncSession, api_key: ApiKey):
        """Permanently delete an API key."""
        await db.delete(api_key)
        await db.commit()
    
    @staticmethod
    async def record_usage(
        db: AsyncSession,
        api_key: ApiKey,
        ip_address: Optional[str] = None,
    ):
        """Record API key usage for tracking."""
        api_key.last_used_at = datetime.now(timezone.utc)
        api_key.last_used_ip = ip_address
        api_key.usage_count = (api_key.usage_count or 0) + 1
        await db.commit()
    
    @staticmethod
    def has_scope(api_key: ApiKey, required_scope: str) -> bool:
        """
        Check if an API key has a required scope.
        
        Args:
            api_key: The API key to check
            required_scope: The scope string required (e.g., "versions:write")
            
        Returns:
            True if key has the scope or FULL_ACCESS
        """
        scopes = api_key.scopes or []
        
        # FULL_ACCESS grants everything
        if ApiKeyScope.FULL_ACCESS.value in scopes:
            return True
        
        return required_scope in scopes
    
    @staticmethod
    def require_scope(api_key: ApiKey, required_scope: str):
        """
        Require an API key to have a scope, raising ForbiddenError if not.
        
        Args:
            api_key: The API key to check
            required_scope: The scope string required
            
        Raises:
            ForbiddenError if key doesn't have the required scope
        """
        if not ApiKeyService.has_scope(api_key, required_scope):
            raise ForbiddenError(
                f"API key missing required scope: {required_scope}. "
                f"Current scopes: {', '.join(api_key.scopes or [])}"
            )
