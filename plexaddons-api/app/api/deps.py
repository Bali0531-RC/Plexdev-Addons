from typing import Optional, Tuple
from fastapi import Depends, Request, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models import User, ApiKey
from app.core.security import decode_access_token
from app.core.exceptions import UnauthorizedError, ForbiddenError
from app.core.rate_limit import get_rate_limiter


security = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Get the current authenticated user from JWT token."""
    if not credentials:
        raise UnauthorizedError("Missing authentication token")
    
    payload = decode_access_token(credentials.credentials)
    if not payload:
        raise UnauthorizedError("Invalid or expired token")
    
    user_id = payload.get("sub")
    if not user_id:
        raise UnauthorizedError("Invalid token payload")
    
    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()
    
    if not user:
        raise UnauthorizedError("User not found")
    
    return user


async def get_current_user_optional(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """Get the current user if authenticated, None otherwise."""
    if not credentials:
        return None
    
    payload = decode_access_token(credentials.credentials)
    if not payload:
        return None
    
    user_id = payload.get("sub")
    if not user_id:
        return None
    
    result = await db.execute(select(User).where(User.id == int(user_id)))
    return result.scalar_one_or_none()


async def get_admin_user(
    user: User = Depends(get_current_user),
) -> User:
    """Require admin privileges."""
    if not user.is_admin:
        raise ForbiddenError("Admin access required")
    return user


def get_effective_tier(user: User):
    """Get effective tier including temp tier if active."""
    from datetime import datetime, timezone
    from app.models import SubscriptionTier
    if user.temp_tier and user.temp_tier_expires_at:
        if user.temp_tier_expires_at > datetime.now(timezone.utc):
            return user.temp_tier
    return user.subscription_tier


async def require_pro(
    user: User = Depends(get_current_user),
) -> User:
    """Require Pro or higher subscription."""
    from app.models import SubscriptionTier
    effective = get_effective_tier(user)
    if effective not in [SubscriptionTier.PRO, SubscriptionTier.PREMIUM]:
        raise ForbiddenError("Pro subscription required")
    return user


async def require_premium(
    user: User = Depends(get_current_user),
) -> User:
    """Require Premium subscription."""
    from app.models import SubscriptionTier
    effective = get_effective_tier(user)
    if effective != SubscriptionTier.PREMIUM:
        raise ForbiddenError("Premium subscription required")
    return user


async def rate_limit_check(
    request: Request,
    user: Optional[User] = Depends(get_current_user_optional),
):
    """Check rate limits for the request."""
    limiter = get_rate_limiter()
    if not limiter:
        return
    
    # Determine endpoint type
    path = request.url.path
    endpoint_type = "auth" if "/auth/" in path else "public"
    
    headers = await limiter.check_rate_limit(
        request,
        user_id=user.id if user else None,
        user_tier=user.subscription_tier.value if user else None,
        endpoint_type=endpoint_type,
    )
    
    # Store headers for response
    request.state.rate_limit_headers = headers


async def rate_limit_check_authenticated(
    request: Request,
    user: User = Depends(get_current_user),
):
    """Check rate limits for authenticated requests."""
    limiter = get_rate_limiter()
    if not limiter:
        return
    
    headers = await limiter.check_rate_limit(
        request,
        user_id=user.id,
        user_tier=user.subscription_tier.value,
        endpoint_type="public",
    )
    
    request.state.rate_limit_headers = headers


async def get_api_key_from_header(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    db: AsyncSession = Depends(get_db),
) -> Optional[ApiKey]:
    """
    Get API key from header if valid.
    
    API keys are formatted as: pa_<64_hex_chars>
    """
    if not x_api_key:
        return None
    
    # Validate API key format
    if not x_api_key.startswith("pa_") or len(x_api_key) != 67:  # 3 + 64
        return None
    
    from app.services.api_key_service import ApiKeyService
    return await ApiKeyService.get_key_by_value(db, x_api_key)


async def get_user_from_api_key(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """
    Get user from API key header.
    
    API keys are formatted as: pa_<64_hex_chars>
    """
    api_key = await get_api_key_from_header(x_api_key, db)
    if not api_key:
        return None
    
    result = await db.execute(select(User).where(User.id == api_key.user_id))
    return result.scalar_one_or_none()


async def get_current_user_or_api_key(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Get the current user from either JWT token or API key.
    
    Checks in order:
    1. JWT Bearer token
    2. X-API-Key header
    
    Raises UnauthorizedError if neither is valid.
    """
    # First try JWT token
    if credentials:
        payload = decode_access_token(credentials.credentials)
        if payload:
            user_id = payload.get("sub")
            if user_id:
                result = await db.execute(select(User).where(User.id == int(user_id)))
                user = result.scalar_one_or_none()
                if user:
                    # Store that this is JWT auth, not API key
                    request.state.auth_method = "jwt"
                    request.state.api_key = None
                    return user
    
    # Then try API key
    api_key = await get_api_key_from_header(x_api_key, db)
    if api_key:
        result = await db.execute(select(User).where(User.id == api_key.user_id))
        user = result.scalar_one_or_none()
        if user:
            # Store API key for scope checking
            request.state.auth_method = "api_key"
            request.state.api_key = api_key
            
            # Record API key usage
            from app.services.api_key_service import ApiKeyService
            client_ip = request.client.host if request.client else None
            await ApiKeyService.record_usage(db, api_key, client_ip)
            
            return user
    
    raise UnauthorizedError("Missing or invalid authentication")


async def get_user_and_api_key(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    db: AsyncSession = Depends(get_db),
) -> Tuple[User, Optional[ApiKey]]:
    """
    Get user and optional API key.
    
    Returns (user, api_key) tuple where api_key is None if using JWT auth.
    Use this when you need to check API key scopes.
    """
    # First try JWT token
    if credentials:
        payload = decode_access_token(credentials.credentials)
        if payload:
            user_id = payload.get("sub")
            if user_id:
                result = await db.execute(select(User).where(User.id == int(user_id)))
                user = result.scalar_one_or_none()
                if user:
                    return user, None
    
    # Then try API key
    api_key = await get_api_key_from_header(x_api_key, db)
    if api_key:
        result = await db.execute(select(User).where(User.id == api_key.user_id))
        user = result.scalar_one_or_none()
        if user:
            # Record API key usage
            from app.services.api_key_service import ApiKeyService
            client_ip = request.client.host if request.client else None
            await ApiKeyService.record_usage(db, api_key, client_ip)
            
            return user, api_key
    
    raise UnauthorizedError("Missing or invalid authentication")


def require_scope(scope: str):
    """
    Dependency factory to require a specific API key scope.
    
    Usage:
        @router.post("/endpoint")
        async def endpoint(
            auth: Tuple[User, Optional[ApiKey]] = Depends(require_scope("versions:write"))
        ):
            user, api_key = auth
            ...
    
    If authenticating with JWT, all scopes are implicitly granted.
    If authenticating with API key, the key must have the required scope.
    """
    async def _require_scope(
        request: Request,
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
        x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
        db: AsyncSession = Depends(get_db),
    ) -> Tuple[User, Optional[ApiKey]]:
        user, api_key = await get_user_and_api_key(request, credentials, x_api_key, db)
        
        # JWT auth has full access
        if api_key is None:
            return user, None
        
        # Check scope for API key
        from app.services.api_key_service import ApiKeyService
        if not ApiKeyService.has_scope(api_key, scope):
            raise ForbiddenError(
                f"API key missing required scope: {scope}. "
                f"Your key has: {', '.join(api_key.scopes or [])}"
            )
        
        return user, api_key
    
    return _require_scope
