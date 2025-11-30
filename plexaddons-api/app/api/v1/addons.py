from fastapi import APIRouter, Depends, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from app.database import get_db
from app.models import User, Addon
from app.schemas import (
    AddonCreate,
    AddonUpdate,
    AddonResponse,
    AddonListResponse,
    VersionResponse,
    VersionListResponse,
)
from app.services import AddonService, VersionService
from app.api.deps import get_current_user, get_current_user_optional, rate_limit_check, rate_limit_check_authenticated
from app.core.exceptions import NotFoundError, ForbiddenError

router = APIRouter(prefix="/addons", tags=["Addons"])


@router.get("", response_model=AddonListResponse)
async def list_addons(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional),
    _: None = Depends(rate_limit_check),
):
    """List all public addons."""
    skip = (page - 1) * per_page
    addons, total = await AddonService.list_addons(
        db,
        skip=skip,
        limit=per_page,
        search=search,
        public_only=True,
    )
    
    return AddonListResponse(
        addons=[AddonResponse(**addon) for addon in addons],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/mine", response_model=AddonListResponse)
async def list_my_addons(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """List current user's addons."""
    skip = (page - 1) * per_page
    addons, total = await AddonService.list_addons(
        db,
        skip=skip,
        limit=per_page,
        owner_id=user.id,
        public_only=False,
    )
    
    return AddonListResponse(
        addons=[AddonResponse(**addon) for addon in addons],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.post("", response_model=AddonResponse)
async def create_addon(
    data: AddonCreate,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """Create a new addon."""
    addon = await AddonService.create_addon(db, user, data, background_tasks)
    
    return AddonResponse(
        id=addon.id,
        slug=addon.slug,
        name=addon.name,
        description=addon.description,
        homepage=addon.homepage,
        external=addon.external,
        is_active=addon.is_active,
        is_public=addon.is_public,
        owner_id=addon.owner_id,
        owner_username=user.discord_username,
        latest_version=None,
        latest_release_date=None,
        version_count=0,
        created_at=addon.created_at,
        updated_at=addon.updated_at,
    )


@router.get("/{slug}", response_model=AddonResponse)
async def get_addon(
    slug: str,
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional),
    _: None = Depends(rate_limit_check),
):
    """Get addon by slug."""
    addon = await AddonService.get_addon_by_slug(db, slug)
    if not addon:
        raise NotFoundError("Addon not found")
    
    # Check access for non-public addons
    if not addon.is_public:
        if not user or (addon.owner_id != user.id and not user.is_admin):
            raise NotFoundError("Addon not found")
    
    # Get enriched data
    from app.models import Version
    from sqlalchemy import select, func
    
    # Get owner
    owner_result = await db.execute(select(User).where(User.id == addon.owner_id))
    owner = owner_result.scalar_one_or_none()
    
    # Get latest version
    latest_result = await db.execute(
        select(Version)
        .where(Version.addon_id == addon.id)
        .order_by(Version.release_date.desc())
        .limit(1)
    )
    latest = latest_result.scalar_one_or_none()
    
    # Get version count
    count_result = await db.execute(
        select(func.count(Version.id)).where(Version.addon_id == addon.id)
    )
    version_count = count_result.scalar() or 0
    
    return AddonResponse(
        id=addon.id,
        slug=addon.slug,
        name=addon.name,
        description=addon.description,
        homepage=addon.homepage,
        external=addon.external,
        is_active=addon.is_active,
        is_public=addon.is_public,
        owner_id=addon.owner_id,
        owner_username=owner.discord_username if owner else None,
        latest_version=latest.version if latest else None,
        latest_release_date=latest.release_date if latest else None,
        version_count=version_count,
        created_at=addon.created_at,
        updated_at=addon.updated_at,
    )


@router.patch("/{slug}", response_model=AddonResponse)
async def update_addon(
    slug: str,
    data: AddonUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """Update an addon."""
    addon = await AddonService.get_addon_by_slug(db, slug)
    if not addon:
        raise NotFoundError("Addon not found")
    
    updated = await AddonService.update_addon(db, addon, user, data)
    return await get_addon(updated.slug, db, user)


@router.delete("/{slug}")
async def delete_addon(
    slug: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """Delete an addon."""
    addon = await AddonService.get_addon_by_slug(db, slug)
    if not addon:
        raise NotFoundError("Addon not found")
    
    await AddonService.delete_addon(db, addon, user)
    return {"status": "deleted"}


# Version endpoints under addon
@router.get("/{slug}/versions", response_model=VersionListResponse)
async def list_addon_versions(
    slug: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional),
    _: None = Depends(rate_limit_check),
):
    """List versions for an addon."""
    addon = await AddonService.get_addon_by_slug(db, slug)
    if not addon:
        raise NotFoundError("Addon not found")
    
    # Check access
    if not addon.is_public:
        if not user or (addon.owner_id != user.id and not user.is_admin):
            raise NotFoundError("Addon not found")
    
    versions, total = await VersionService.list_versions(db, addon.id, skip=skip, limit=limit)
    
    return VersionListResponse(
        versions=[VersionResponse.model_validate(v) for v in versions],
        total=total,
    )
