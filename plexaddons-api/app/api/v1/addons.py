from fastapi import APIRouter, Depends, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, case, desc
from typing import Optional, List, Literal
from datetime import date, timedelta
from app.database import get_db
from app.models import User, Addon, AddonUsageStats, AddonStar, AddonReview, Version, ReleaseChannel
from app.schemas import (
    AddonCreate,
    AddonUpdate,
    AddonResponse,
    AddonListResponse,
    VersionResponse,
    VersionListResponse,
)
from app.services import AddonService, VersionService
from app.api.deps import get_current_user, get_current_user_optional, get_effective_tier, rate_limit_check, rate_limit_check_authenticated, check_paid_addon_access
from app.core.exceptions import NotFoundError, ForbiddenError
from app.core.cache import cache
from app.models import SubscriptionTier

router = APIRouter(prefix="/addons", tags=["Addons"])


@router.get("", response_model=AddonListResponse)
async def list_addons(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    tag: Optional[str] = None,
    sort_by: Literal["newest", "oldest", "name_asc", "name_desc", "updated"] = "updated",
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional),
    _: None = Depends(rate_limit_check),
):
    """List all public addons with server-side search, tag filter, and sorting."""
    skip = (page - 1) * per_page
    
    # Try cache for unauthenticated, unfiltered requests
    cache_key = None
    if not search and not tag:
        cache_key = f"addon_list:{sort_by}:{page}:{per_page}"
        cached = await cache.get(cache_key)
        if cached:
            return AddonListResponse(**cached)
    
    addons, total = await AddonService.list_addons(
        db,
        skip=skip,
        limit=per_page,
        search=search,
        tag=tag,
        sort_by=sort_by,
        public_only=True,
    )
    
    result = AddonListResponse(
        addons=[AddonResponse(**addon) for addon in addons],
        total=total,
        page=page,
        per_page=per_page,
    )
    
    if cache_key:
        await cache.set(cache_key, result.model_dump(), cache.TTL_ADDON_LIST)
    
    return result


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


@router.get("/trending")
async def get_trending_addons(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check),
):
    """Get trending addons based on recent activity growth, stars, and reviews."""
    today = date.today()
    recent_start = today - timedelta(days=7)
    older_start = today - timedelta(days=14)

    # Subquery: recent 7 days check count per addon
    recent_checks = (
        select(
            AddonUsageStats.addon_id,
            func.coalesce(func.sum(AddonUsageStats.check_count), 0).label("recent_checks"),
            func.coalesce(func.sum(AddonUsageStats.unique_users), 0).label("recent_unique"),
        )
        .where(AddonUsageStats.date >= recent_start)
        .group_by(AddonUsageStats.addon_id)
        .subquery()
    )

    # Subquery: older 7 days check count per addon (for growth calculation)
    older_checks = (
        select(
            AddonUsageStats.addon_id,
            func.coalesce(func.sum(AddonUsageStats.check_count), 0).label("older_checks"),
        )
        .where(and_(AddonUsageStats.date >= older_start, AddonUsageStats.date < recent_start))
        .group_by(AddonUsageStats.addon_id)
        .subquery()
    )

    # Subquery: star count per addon
    star_counts = (
        select(
            AddonStar.addon_id,
            func.count(AddonStar.id).label("star_count"),
        )
        .group_by(AddonStar.addon_id)
        .subquery()
    )

    # Subquery: average rating per addon
    review_stats = (
        select(
            AddonReview.addon_id,
            func.avg(AddonReview.rating).label("avg_rating"),
            func.count(AddonReview.id).label("review_count"),
        )
        .where(AddonReview.is_visible == True)
        .group_by(AddonReview.addon_id)
        .subquery()
    )

    # Build composite trending score:
    # score = recent_unique_users * 2 + growth_factor + stars * 3 + (avg_rating * review_count)
    query = (
        select(
            Addon,
            func.coalesce(recent_checks.c.recent_checks, 0).label("recent_checks"),
            func.coalesce(recent_checks.c.recent_unique, 0).label("recent_unique"),
            func.coalesce(older_checks.c.older_checks, 0).label("older_checks"),
            func.coalesce(star_counts.c.star_count, 0).label("star_count"),
            func.coalesce(review_stats.c.avg_rating, 0).label("avg_rating"),
            func.coalesce(review_stats.c.review_count, 0).label("review_count"),
        )
        .outerjoin(recent_checks, Addon.id == recent_checks.c.addon_id)
        .outerjoin(older_checks, Addon.id == older_checks.c.addon_id)
        .outerjoin(star_counts, Addon.id == star_counts.c.addon_id)
        .outerjoin(review_stats, Addon.id == review_stats.c.addon_id)
        .where(Addon.is_public == True, Addon.is_active == True)
        .order_by(
            desc(
                func.coalesce(recent_checks.c.recent_unique, 0) * 2
                + func.coalesce(star_counts.c.star_count, 0) * 3
                + func.coalesce(review_stats.c.avg_rating, 0)
                  * func.coalesce(review_stats.c.review_count, 0)
                + case(
                    (func.coalesce(older_checks.c.older_checks, 0) > 0,
                     func.coalesce(recent_checks.c.recent_checks, 0) * 100
                     / func.coalesce(older_checks.c.older_checks, 1)),
                    else_=func.coalesce(recent_checks.c.recent_checks, 0),
                )
            )
        )
        .limit(limit)
    )

    result = await db.execute(query)
    rows = result.all()

    trending = []
    for row in rows:
        addon = row[0]
        # Get owner
        owner_result = await db.execute(select(User).where(User.id == addon.owner_id))
        owner = owner_result.scalar_one_or_none()

        # Get latest version
        latest_result = await db.execute(
            select(Version)
            .where(Version.addon_id == addon.id)
            .order_by(Version.release_date.desc(), Version.created_at.desc())
            .limit(1)
        )
        latest = latest_result.scalar_one_or_none()

        trending.append({
            "id": addon.id,
            "slug": addon.slug,
            "name": addon.name,
            "description": addon.description,
            "verified": addon.verified,
            "external": addon.external,
            "tags": addon.tags or [],
            "owner_username": owner.discord_username if owner else None,
            "owner_discord_id": owner.discord_id if owner else None,
            "latest_version": latest.version if latest else None,
            "star_count": row.star_count or 0,
            "avg_rating": round(float(row.avg_rating), 1) if row.avg_rating else None,
            "review_count": row.review_count or 0,
            "recent_unique_users": row.recent_unique or 0,
        })

    return {"trending": trending}


@router.post("", response_model=AddonResponse)
async def create_addon(
    data: AddonCreate,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """Create a new addon."""
    from app.services.user_service import UserService
    
    addon = await AddonService.create_addon(db, user, data, background_tasks)
    
    # Add addon_creator badge if this is user's first public addon
    if addon.is_public:
        await UserService.check_and_add_creator_badge(db, user)
    
    await cache.invalidate_addon(addon_id=addon.id, addon_slug=addon.slug)
    
    return AddonResponse(
        id=addon.id,
        slug=addon.slug,
        name=addon.name,
        description=addon.description,
        homepage=addon.homepage,
        external=addon.external,
        is_active=addon.is_active,
        is_public=addon.is_public,
        verified=addon.verified,
        owner_id=addon.owner_id,
        organization_id=addon.organization_id,
        tags=addon.tags or [],
        icon_url=addon.icon_url,
        readme=addon.readme,
        banner_url=addon.banner_url,
        screenshots=addon.screenshots or [],
        theme_accent_color=addon.theme_accent_color,
        theme_header_url=addon.theme_header_url,
        is_paid=addon.is_paid,
        price_cents=addon.price_cents,
        revenue_split_percent=addon.revenue_split_percent,
        sponsor_url=addon.sponsor_url,
        owner_username=user.discord_username,
        owner_discord_id=user.discord_id,
        owner_verified_developer=user.is_verified_developer,
        latest_version=None,
        latest_release_date=None,
        version_count=0,
        download_count=0,
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
    from app.models import Version, AddonUsageStats
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
    
    # Get total download/check count
    download_result = await db.execute(
        select(func.coalesce(func.sum(AddonUsageStats.check_count), 0))
        .where(AddonUsageStats.addon_id == addon.id)
    )
    download_count = download_result.scalar() or 0
    
    return AddonResponse(
        id=addon.id,
        slug=addon.slug,
        name=addon.name,
        description=addon.description,
        homepage=addon.homepage,
        external=addon.external,
        is_active=addon.is_active,
        is_public=addon.is_public,
        verified=addon.verified,
        owner_id=addon.owner_id,
        organization_id=addon.organization_id,
        tags=addon.tags or [],
        icon_url=addon.icon_url,
        readme=addon.readme,
        banner_url=addon.banner_url,
        screenshots=addon.screenshots or [],
        theme_accent_color=addon.theme_accent_color,
        theme_header_url=addon.theme_header_url,
        is_paid=addon.is_paid,
        price_cents=addon.price_cents,
        revenue_split_percent=addon.revenue_split_percent,
        sponsor_url=addon.sponsor_url,
        owner_username=owner.discord_username if owner else None,
        owner_discord_id=owner.discord_id if owner else None,
        owner_verified_developer=owner.is_verified_developer if owner else False,
        latest_version=latest.version if latest else None,
        latest_release_date=latest.release_date if latest else None,
        version_count=version_count,
        download_count=download_count,
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
    
    # Theme customization requires Pro+ tier
    effective_tier = get_effective_tier(user)
    if effective_tier == SubscriptionTier.FREE:
        data.theme_accent_color = None
        data.theme_header_url = None
    
    updated = await AddonService.update_addon(db, addon, user, data)
    await cache.invalidate_addon(addon_id=updated.id, addon_slug=updated.slug)
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
    await cache.invalidate_addon(addon_id=addon.id, addon_slug=addon.slug)
    return {"status": "deleted"}


# Version endpoints under addon
@router.get("/{slug}/versions", response_model=VersionListResponse)
async def list_addon_versions(
    slug: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    channel: Optional[ReleaseChannel] = Query(None, description="Filter by release channel"),
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional),
    _: None = Depends(rate_limit_check),
):
    """List versions for an addon, optionally filtered by release channel."""
    addon = await AddonService.get_addon_by_slug(db, slug)
    if not addon:
        raise NotFoundError("Addon not found")
    
    # Check access
    if not addon.is_public:
        if not user or (addon.owner_id != user.id and not user.is_admin):
            raise NotFoundError("Addon not found")
    
    versions, total = await VersionService.list_versions(db, addon.id, skip=skip, limit=limit, channel=channel)
    
    has_access = await check_paid_addon_access(db, addon, user)
    version_responses = []
    for v in versions:
        resp = VersionResponse.model_validate(v)
        if not has_access:
            resp.download_url = ""
        version_responses.append(resp)
    
    return VersionListResponse(
        versions=version_responses,
        total=total,
    )
