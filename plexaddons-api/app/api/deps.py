from typing import Optional
from fastapi import Depends, Request, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models import User
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


async def get_user_from_api_key(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """
    Get user from API key header.
    
    API keys are formatted as: pa_<64_hex_chars>
    Only Premium users can have API keys.
    """
    if not x_api_key:
        return None
    
    # Validate API key format
    if not x_api_key.startswith("pa_") or len(x_api_key) != 67:  # 3 + 64
        return None
    
    result = await db.execute(
        select(User).where(User.api_key == x_api_key)
    )
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
                    return user
    
    # Then try API key
    if x_api_key and x_api_key.startswith("pa_") and len(x_api_key) == 67:
        result = await db.execute(
            select(User).where(User.api_key == x_api_key)
        )
        user = result.scalar_one_or_none()
        if user:
            return user
    
    raise UnauthorizedError("Missing or invalid authentication")
