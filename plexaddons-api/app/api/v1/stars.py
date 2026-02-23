from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from typing import Optional
from app.database import get_db
from app.models import User, Addon, AddonStar
from app.schemas import StarResponse, AddonResponse, AddonListResponse
from app.services import AddonService
from app.api.deps import get_current_user, get_current_user_optional, rate_limit_check, rate_limit_check_authenticated
from app.core.exceptions import NotFoundError

router = APIRouter(prefix="/stars", tags=["Stars"])


@router.post("/addons/{slug}", response_model=StarResponse)
async def star_addon(
    slug: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """Star/favorite an addon."""
    addon = await AddonService.get_addon_by_slug(db, slug)
    if not addon:
        raise NotFoundError("Addon not found")

    # Check if already starred
    existing = await db.execute(
        select(AddonStar)
        .where(AddonStar.user_id == user.id, AddonStar.addon_id == addon.id)
    )
    if existing.scalar_one_or_none():
        # Already starred — return current state
        count = await _get_star_count(db, addon.id)
        return StarResponse(starred=True, star_count=count)

    star = AddonStar(user_id=user.id, addon_id=addon.id)
    db.add(star)
    await db.commit()

    count = await _get_star_count(db, addon.id)
    return StarResponse(starred=True, star_count=count)


@router.delete("/addons/{slug}", response_model=StarResponse)
async def unstar_addon(
    slug: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """Remove star from an addon."""
    addon = await AddonService.get_addon_by_slug(db, slug)
    if not addon:
        raise NotFoundError("Addon not found")

    await db.execute(
        delete(AddonStar)
        .where(AddonStar.user_id == user.id, AddonStar.addon_id == addon.id)
    )
    await db.commit()

    count = await _get_star_count(db, addon.id)
    return StarResponse(starred=False, star_count=count)


@router.get("/addons/{slug}", response_model=StarResponse)
async def get_addon_star_status(
    slug: str,
    user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check),
):
    """Get star status and count for an addon."""
    addon = await AddonService.get_addon_by_slug(db, slug)
    if not addon:
        raise NotFoundError("Addon not found")

    starred = False
    if user:
        result = await db.execute(
            select(AddonStar)
            .where(AddonStar.user_id == user.id, AddonStar.addon_id == addon.id)
        )
        starred = result.scalar_one_or_none() is not None

    count = await _get_star_count(db, addon.id)
    return StarResponse(starred=starred, star_count=count)


@router.get("/mine", response_model=AddonListResponse)
async def list_my_starred_addons(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """List addons the current user has starred."""
    skip = (page - 1) * per_page

    # Get starred addon IDs
    count_result = await db.execute(
        select(func.count(AddonStar.id))
        .where(AddonStar.user_id == user.id)
    )
    total = count_result.scalar() or 0

    starred_result = await db.execute(
        select(AddonStar.addon_id)
        .where(AddonStar.user_id == user.id)
        .order_by(AddonStar.created_at.desc())
        .offset(skip)
        .limit(per_page)
    )
    addon_ids = [row[0] for row in starred_result.all()]

    if not addon_ids:
        return AddonListResponse(addons=[], total=0, page=page, per_page=per_page)

    # Fetch the addons in the starred order
    addons, _ = await AddonService.list_addons(
        db,
        skip=0,
        limit=len(addon_ids),
        addon_ids=addon_ids,
        public_only=False,
    )

    return AddonListResponse(
        addons=[AddonResponse(**a) for a in addons],
        total=total,
        page=page,
        per_page=per_page,
    )


async def _get_star_count(db: AsyncSession, addon_id: int) -> int:
    result = await db.execute(
        select(func.count(AddonStar.id)).where(AddonStar.addon_id == addon_id)
    )
    return result.scalar() or 0
