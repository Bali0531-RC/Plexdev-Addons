from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from app.database import get_db
from app.models import User, SubscriptionTier, ReleaseChannel
from app.schemas import (
    VersionCreate,
    VersionUpdate,
    VersionResponse,
    VersionListResponse,
    VersionDeprecate,
)
from app.services import AddonService, VersionService
from app.api.deps import get_current_user, get_current_user_optional, rate_limit_check, rate_limit_check_authenticated, get_effective_tier
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


@router.post("/addons/{slug}/versions/{version_str}/deprecate", response_model=VersionResponse)
async def deprecate_version(
    slug: str,
    version_str: str,
    data: VersionDeprecate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """
    Mark a version as deprecated (Pro+ feature).
    
    Deprecated versions remain downloadable but show a warning.
    """
    effective_tier = get_effective_tier(user)
    if effective_tier == SubscriptionTier.FREE:
        raise ForbiddenError("Version deprecation requires Pro or Premium subscription")
    
    addon = await AddonService.get_addon_by_slug(db, slug)
    if not addon:
        raise NotFoundError("Addon not found")
    if addon.owner_id != user.id and not user.is_admin:
        raise ForbiddenError("You don't have permission to manage this addon's versions")
    
    version = await VersionService.get_version_by_addon_and_version(db, addon.id, version_str)
    if not version:
        raise NotFoundError("Version not found")
    
    updated = await VersionService.deprecate_version(db, version, data.reason)
    return VersionResponse.model_validate(updated)


@router.post("/addons/{slug}/versions/{version_str}/undeprecate", response_model=VersionResponse)
async def undeprecate_version(
    slug: str,
    version_str: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """Remove deprecation from a version (Pro+ feature)."""
    effective_tier = get_effective_tier(user)
    if effective_tier == SubscriptionTier.FREE:
        raise ForbiddenError("Version management requires Pro or Premium subscription")
    
    addon = await AddonService.get_addon_by_slug(db, slug)
    if not addon:
        raise NotFoundError("Addon not found")
    if addon.owner_id != user.id and not user.is_admin:
        raise ForbiddenError("You don't have permission to manage this addon's versions")
    
    version = await VersionService.get_version_by_addon_and_version(db, addon.id, version_str)
    if not version:
        raise NotFoundError("Version not found")
    
    updated = await VersionService.undeprecate_version(db, version)
    return VersionResponse.model_validate(updated)


@router.post("/addons/{slug}/versions/{version_str}/rollback", response_model=VersionResponse)
async def rollback_to_version(
    slug: str,
    version_str: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """
    Promote a version as the latest by updating its release date to today (Pro+ feature).
    
    This is a quick rollback action — useful when a bad version was published
    and you want to make an older version the "latest" again.
    """
    effective_tier = get_effective_tier(user)
    if effective_tier == SubscriptionTier.FREE:
        raise ForbiddenError("Version rollback requires Pro or Premium subscription")
    
    addon = await AddonService.get_addon_by_slug(db, slug)
    if not addon:
        raise NotFoundError("Addon not found")
    if addon.owner_id != user.id and not user.is_admin:
        raise ForbiddenError("You don't have permission to manage this addon's versions")
    
    version = await VersionService.get_version_by_addon_and_version(db, addon.id, version_str)
    if not version:
        raise NotFoundError("Version not found")
    
    updated = await VersionService.rollback_to_version(db, addon, version)
    return VersionResponse.model_validate(updated)


@router.get("/addons/{slug}/versions/latest/{channel}", response_model=VersionResponse)
async def get_latest_version_by_channel(
    slug: str,
    channel: ReleaseChannel,
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional),
    _: None = Depends(rate_limit_check),
):
    """Get the latest non-deprecated, published version for a specific release channel."""
    addon = await AddonService.get_addon_by_slug(db, slug)
    if not addon:
        raise NotFoundError("Addon not found")
    
    if not addon.is_public:
        if not user or (addon.owner_id != user.id and not user.is_admin):
            raise NotFoundError("Addon not found")
    
    version = await VersionService.get_latest_version_by_channel(db, addon.id, channel)
    if not version:
        raise NotFoundError(f"No {channel.value} version found for this addon")
    
    return VersionResponse.model_validate(version)
