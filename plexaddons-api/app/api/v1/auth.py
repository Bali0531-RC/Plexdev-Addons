from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.services import AuthService
from app.schemas import AuthResponse, UserResponse
from app.api.deps import rate_limit_check
from app.config import get_settings
import secrets

settings = get_settings()

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Store states temporarily (in production, use Redis)
_oauth_states: dict = {}


@router.get("/discord/login")
async def discord_login(
    request: Request,
    _: None = Depends(rate_limit_check),
):
    """Redirect to Discord OAuth2 authorization."""
    state = secrets.token_urlsafe(32)
    _oauth_states[state] = True
    
    oauth_url = AuthService.get_oauth_url(state=state)
    return RedirectResponse(url=oauth_url)


@router.get("/discord/callback")
async def discord_callback(
    code: str,
    state: str = None,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check),
):
    """Handle Discord OAuth2 callback."""
    # Verify state (optional but recommended)
    if state and state in _oauth_states:
        del _oauth_states[state]
    
    # Exchange code for tokens
    tokens = await AuthService.exchange_code(code)
    
    # Get or create user
    user = await AuthService.get_or_create_user(db, tokens)
    
    # Create JWT
    jwt_token = AuthService.create_jwt_token(user)
    
    # Redirect to frontend with token
    frontend_callback = f"{settings.frontend_url}/auth/callback?token={jwt_token}"
    return RedirectResponse(url=frontend_callback)


@router.get("/discord/callback/api", response_model=AuthResponse)
async def discord_callback_api(
    code: str,
    state: str = None,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check),
):
    """Handle Discord OAuth2 callback (API response for SPAs)."""
    if state and state in _oauth_states:
        del _oauth_states[state]
    
    tokens = await AuthService.exchange_code(code)
    user = await AuthService.get_or_create_user(db, tokens)
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
    _oauth_states[state] = True
    
    return {
        "url": AuthService.get_oauth_url(state=state),
        "state": state,
    }
