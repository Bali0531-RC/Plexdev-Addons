from fastapi import APIRouter, Depends, Request, Response, BackgroundTasks, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.services import AuthService
from app.schemas import AuthResponse, UserResponse
from app.api.deps import rate_limit_check
from app.config import get_settings
from app.core.rate_limit import get_redis_client
import secrets

settings = get_settings()

router = APIRouter(prefix="/auth", tags=["Authentication"])

# OAuth state TTL in seconds (5 minutes)
OAUTH_STATE_TTL = 300


async def store_oauth_state(state: str) -> bool:
    """Store OAuth state in Redis with TTL."""
    redis = get_redis_client()
    if redis:
        await redis.setex(f"oauth_state:{state}", OAUTH_STATE_TTL, "1")
        return True
    return False


async def verify_and_delete_oauth_state(state: str) -> bool:
    """Verify OAuth state exists and delete it. Returns True if valid."""
    if not state:
        return False
    redis = get_redis_client()
    if redis:
        # Use getdel to atomically get and delete
        result = await redis.getdel(f"oauth_state:{state}")
        return result is not None
    # If Redis unavailable, reject for security
    return False


@router.get("/discord/login")
async def discord_login(
    request: Request,
    _: None = Depends(rate_limit_check),
):
    """Redirect to Discord OAuth2 authorization."""
    state = secrets.token_urlsafe(32)
    stored = await store_oauth_state(state)
    if not stored:
        raise HTTPException(status_code=503, detail="Authentication service temporarily unavailable")
    
    oauth_url = AuthService.get_oauth_url(state=state)
    return RedirectResponse(url=oauth_url)


@router.get("/discord/callback")
async def discord_callback(
    code: str,
    background_tasks: BackgroundTasks,
    state: str = None,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check),
):
    """Handle Discord OAuth2 callback."""
    # Verify state (required for CSRF protection)
    if not await verify_and_delete_oauth_state(state):
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state")
    
    # Exchange code for tokens
    tokens = await AuthService.exchange_code(code)
    
    # Get or create user (sends welcome email for new users)
    user = await AuthService.get_or_create_user(db, tokens, background_tasks)
    
    # Create JWT
    jwt_token = AuthService.create_jwt_token(user)
    
    # Redirect to frontend with token
    frontend_callback = f"{settings.frontend_url}/auth/callback?token={jwt_token}"
    return RedirectResponse(url=frontend_callback)


@router.get("/discord/callback/api", response_model=AuthResponse)
async def discord_callback_api(
    code: str,
    background_tasks: BackgroundTasks,
    state: str = None,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check),
):
    """Handle Discord OAuth2 callback (API response for SPAs)."""
    # Verify state (required for CSRF protection)
    if not await verify_and_delete_oauth_state(state):
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state")
    
    tokens = await AuthService.exchange_code(code)
    user = await AuthService.get_or_create_user(db, tokens, background_tasks)
    jwt_token = AuthService.create_jwt_token(user)
    
    return AuthResponse(
        access_token=jwt_token,
        user=UserResponse.model_validate(user),
    )


@router.post("/refresh")
async def refresh_token(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Refresh JWT token."""
    from app.api.deps import get_current_user
    user = await get_current_user(request, db=db)
    
    # Optionally refresh Discord token
    user = await AuthService.maybe_refresh_discord_token(db, user)
    
    # Create new JWT
    new_token = AuthService.create_jwt_token(user)
    
    return {"access_token": new_token, "token_type": "bearer"}


@router.get("/url")
async def get_auth_url(_: None = Depends(rate_limit_check)):
    """Get Discord OAuth2 URL for frontend redirect."""
    state = secrets.token_urlsafe(32)
    stored = await store_oauth_state(state)
    if not stored:
        raise HTTPException(status_code=503, detail="Authentication service temporarily unavailable")
    
    return {
        "url": AuthService.get_oauth_url(state=state),
        "state": state,
    }
