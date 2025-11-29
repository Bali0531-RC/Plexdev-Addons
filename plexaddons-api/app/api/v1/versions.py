from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from app.database import get_db
from app.models import User
from app.schemas import (
    VersionCreate,
    VersionUpdate,
    VersionResponse,
)
from app.services import AddonService, VersionService
from app.api.deps import get_current_user, get_current_user_optional, rate_limit_check, rate_limit_check_authenticated
from app.core.exceptions import NotFoundError, ForbiddenError

router = APIRouter(tags=["Versions"])


@router.post("/addons/{slug}/versions", response_model=VersionResponse)
async def create_version(
    slug: str,
    data: VersionCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """Create a new version for an addon."""
    addon = await AddonService.get_addon_by_slug(db, slug)
    if not addon:
        raise NotFoundError("Addon not found")
    
    # Check ownership
    if addon.owner_id != user.id and not user.is_admin:
        raise ForbiddenError("You don't have permission to add versions to this addon")
    
    version = await VersionService.create_version(db, addon, user, data)
    return VersionResponse.model_validate(version)


@router.get("/addons/{slug}/versions/{version_str}", response_model=VersionResponse)
async def get_version(
    slug: str,
    version_str: str,
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional),
    _: None = Depends(rate_limit_check),
):
    """Get a specific version of an addon."""
    addon = await AddonService.get_addon_by_slug(db, slug)
    if not addon:
        raise NotFoundError("Addon not found")
    
    # Check access for non-public addons
    if not addon.is_public:
        if not user or (addon.owner_id != user.id and not user.is_admin):
            raise NotFoundError("Addon not found")
    
    version = await VersionService.get_version_by_addon_and_version(db, addon.id, version_str)
    if not version:
        raise NotFoundError("Version not found")
    
    return VersionResponse.model_validate(version)


@router.get("/addons/{slug}/versions/latest", response_model=VersionResponse)
async def get_latest_version(
    slug: str,
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional),
    _: None = Depends(rate_limit_check),
):
    """Get the latest version of an addon."""
    addon = await AddonService.get_addon_by_slug(db, slug)
    if not addon:
        raise NotFoundError("Addon not found")
    
    # Check access
    if not addon.is_public:
        if not user or (addon.owner_id != user.id and not user.is_admin):
            raise NotFoundError("Addon not found")
    
    version = await VersionService.get_latest_version(db, addon.id)
    if not version:
        raise NotFoundError("No versions found for this addon")
    
    return VersionResponse.model_validate(version)


@router.patch("/addons/{slug}/versions/{version_str}", response_model=VersionResponse)
async def update_version(
    slug: str,
    version_str: str,
    data: VersionUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """Update a version."""
    addon = await AddonService.get_addon_by_slug(db, slug)
    if not addon:
        raise NotFoundError("Addon not found")
    
    # Check ownership
    if addon.owner_id != user.id and not user.is_admin:
        raise ForbiddenError("You don't have permission to update this version")
    
    version = await VersionService.get_version_by_addon_and_version(db, addon.id, version_str)
    if not version:
        raise NotFoundError("Version not found")
    
    updated = await VersionService.update_version(db, version, user, data)
    return VersionResponse.model_validate(updated)


@router.delete("/addons/{slug}/versions/{version_str}")
async def delete_version(
    slug: str,
    version_str: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """Delete a version."""
    addon = await AddonService.get_addon_by_slug(db, slug)
    if not addon:
        raise NotFoundError("Addon not found")
    
    # Check ownership
    if addon.owner_id != user.id and not user.is_admin:
        raise ForbiddenError("You don't have permission to delete this version")
    
    version = await VersionService.get_version_by_addon_and_version(db, addon.id, version_str)
    if not version:
        raise NotFoundError("Version not found")
    
    await VersionService.delete_version(db, version, user)
    return {"status": "deleted"}
