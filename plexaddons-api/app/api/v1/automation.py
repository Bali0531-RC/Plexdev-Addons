"""
Automation API endpoints for CI/CD integration.

These endpoints allow Premium users to manage their addons programmatically
using API keys, perfect for GitHub Actions and other CI/CD pipelines.
"""

from fastapi import APIRouter, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from pydantic import BaseModel, Field
from datetime import date
from app.database import get_db
from app.models import User, SubscriptionTier
from app.schemas import VersionResponse
from app.services import AddonService, VersionService
from app.api.deps import get_user_from_api_key, get_effective_tier
from app.core.exceptions import NotFoundError, ForbiddenError, UnauthorizedError

router = APIRouter(prefix="/automation", tags=["Automation"])


class PublishVersionRequest(BaseModel):
    """Request body for publishing a new version via API."""
    version: str = Field(..., min_length=1, max_length=50, description="Version string (e.g., '1.0.0')")
    download_url: str = Field(..., description="URL to download this version")
    description: Optional[str] = Field(None, description="Short description of this version")
    changelog: Optional[str] = Field(None, description="Changelog content (markdown supported)")
    changelog_url: Optional[str] = Field(None, description="URL to full changelog")
    breaking: bool = Field(False, description="Whether this version has breaking changes")
    urgent: bool = Field(False, description="Whether this is an urgent/security update")
    release_date: Optional[date] = Field(None, description="Release date (defaults to today)")


class PublishVersionResponse(BaseModel):
    """Response after publishing a version."""
    success: bool
    message: str
    version: Optional[VersionResponse] = None
    addon_slug: str
    addon_name: str


async def require_api_key(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Require valid API key authentication for automation endpoints."""
    if not x_api_key:
        raise UnauthorizedError("API key required. Set X-API-Key header.")
    
    user = await get_user_from_api_key(x_api_key, db)
    if not user:
        raise UnauthorizedError("Invalid API key")
    
    # Check if user has Premium (API keys are Premium-only)
    effective_tier = get_effective_tier(user)
    if effective_tier != SubscriptionTier.PREMIUM:
        raise ForbiddenError("API key access requires Premium subscription")
    
    return user


@router.post("/addons/{slug}/publish", response_model=PublishVersionResponse)
async def publish_version(
    slug: str,
    data: PublishVersionRequest,
    user: User = Depends(require_api_key),
    db: AsyncSession = Depends(get_db),
):
    """
    Publish a new version for an addon.
    
    This endpoint is designed for CI/CD integration (e.g., GitHub Actions).
    Requires a Premium API key.
    
    ## Usage with GitHub Actions
    
    ```yaml
    - name: Publish to PlexAddons
      run: |
        curl -X POST "https://addons.plexdev.live/api/v1/automation/addons/${{ github.event.repository.name }}/publish" \\
          -H "X-API-Key: ${{ secrets.PLEXADDONS_API_KEY }}" \\
          -H "Content-Type: application/json" \\
          -d '{
            "version": "${{ github.event.release.tag_name }}",
            "download_url": "${{ github.event.release.zipball_url }}",
            "description": "${{ github.event.release.name }}",
            "changelog": "${{ github.event.release.body }}"
          }'
    ```
    
    ## Authentication
    
    Pass your API key in the `X-API-Key` header.
    Generate an API key at https://addons.plexdev.live/dashboard/settings
    """
    # Get addon by slug
    addon = await AddonService.get_addon_by_slug(db, slug)
    if not addon:
        raise NotFoundError(f"Addon '{slug}' not found")
    
    # Check ownership
    if addon.owner_id != user.id and not user.is_admin:
        raise ForbiddenError("You don't have permission to publish versions for this addon")
    
    # Check if version already exists
    existing = await VersionService.get_version_by_addon_and_version(db, addon.id, data.version)
    if existing:
        raise ForbiddenError(f"Version {data.version} already exists for this addon")
    
    # Create the version using the VersionCreate schema
    from app.schemas import VersionCreate
    version_data = VersionCreate(
        version=data.version,
        download_url=data.download_url,
        description=data.description,
        changelog_content=data.changelog,
        changelog_url=data.changelog_url,
        breaking=data.breaking,
        urgent=data.urgent,
        release_date=data.release_date,
    )
    
    version = await VersionService.create_version(db, addon, user, version_data)
    
    return PublishVersionResponse(
        success=True,
        message=f"Version {data.version} published successfully",
        version=VersionResponse.model_validate(version),
        addon_slug=addon.slug,
        addon_name=addon.name,
    )


@router.get("/addons/{slug}/latest")
async def get_latest_version_api(
    slug: str,
    user: User = Depends(require_api_key),
    db: AsyncSession = Depends(get_db),
):
    """
    Get the latest version of an addon.
    
    Useful for CI/CD scripts to check the current published version.
    """
    addon = await AddonService.get_addon_by_slug(db, slug)
    if not addon:
        raise NotFoundError(f"Addon '{slug}' not found")
    
    # Check ownership for private addons
    if not addon.is_public and addon.owner_id != user.id and not user.is_admin:
        raise NotFoundError(f"Addon '{slug}' not found")
    
    version = await VersionService.get_latest_version(db, addon.id)
    
    return {
        "addon_slug": addon.slug,
        "addon_name": addon.name,
        "latest_version": version.version if version else None,
        "release_date": version.release_date.isoformat() if version else None,
        "download_url": version.download_url if version else None,
    }


@router.get("/addons")
async def list_my_addons(
    user: User = Depends(require_api_key),
    db: AsyncSession = Depends(get_db),
):
    """
    List all addons owned by the authenticated user.
    
    Useful for CI/CD scripts to discover addon slugs.
    """
    addons = await AddonService.get_addons_by_owner(db, user.id)
    
    return {
        "addons": [
            {
                "id": addon.id,
                "name": addon.name,
                "slug": addon.slug,
                "is_public": addon.is_public,
            }
            for addon in addons
        ],
        "count": len(addons),
    }
