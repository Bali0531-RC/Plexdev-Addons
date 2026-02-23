from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional
from app.database import get_db
from app.models import User, Addon, AddonReview
from app.schemas import (
    ReviewCreate, ReviewUpdate, ReviewResponse,
    ReviewListResponse,
)
from app.services import AddonService
from app.api.deps import get_current_user, get_current_user_optional, rate_limit_check, rate_limit_check_authenticated
from app.core.exceptions import NotFoundError, ForbiddenError, ConflictError

router = APIRouter(prefix="/addons/{slug}/reviews", tags=["Reviews"])


@router.get("", response_model=ReviewListResponse)
async def list_addon_reviews(
    slug: str,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check),
):
    """List reviews for an addon."""
    addon = await AddonService.get_addon_by_slug(db, slug)
    if not addon:
        raise NotFoundError("Addon not found")

    skip = (page - 1) * per_page

    # Get total count
    count_result = await db.execute(
        select(func.count(AddonReview.id))
        .where(AddonReview.addon_id == addon.id, AddonReview.is_visible == True)
    )
    total = count_result.scalar() or 0

    # Get average rating
    avg_result = await db.execute(
        select(func.avg(AddonReview.rating))
        .where(AddonReview.addon_id == addon.id, AddonReview.is_visible == True)
    )
    average_rating = avg_result.scalar()
    if average_rating is not None:
        average_rating = round(float(average_rating), 1)

    # Get rating distribution
    dist_result = await db.execute(
        select(AddonReview.rating, func.count(AddonReview.id))
        .where(AddonReview.addon_id == addon.id, AddonReview.is_visible == True)
        .group_by(AddonReview.rating)
    )
    rating_distribution = {str(i): 0 for i in range(1, 6)}
    for row in dist_result.all():
        rating_distribution[str(row[0])] = row[1]

    # Get reviews with author info
    reviews_result = await db.execute(
        select(AddonReview, User)
        .outerjoin(User, AddonReview.user_id == User.id)
        .where(AddonReview.addon_id == addon.id, AddonReview.is_visible == True)
        .order_by(AddonReview.created_at.desc())
        .offset(skip)
        .limit(per_page)
    )

    reviews = []
    for review, user in reviews_result.all():
        reviews.append(ReviewResponse(
            id=review.id,
            user_id=review.user_id,
            addon_id=review.addon_id,
            rating=review.rating,
            title=review.title,
            content=review.content,
            is_visible=review.is_visible,
            created_at=review.created_at,
            updated_at=review.updated_at,
            author_username=user.discord_username if user else None,
            author_avatar=user.discord_avatar if user else None,
            author_discord_id=user.discord_id if user else None,
        ))

    return ReviewListResponse(
        reviews=reviews,
        total=total,
        average_rating=average_rating,
        rating_distribution=rating_distribution,
    )


@router.post("", response_model=ReviewResponse)
async def create_review(
    slug: str,
    data: ReviewCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """Create a review for an addon. One review per user per addon."""
    addon = await AddonService.get_addon_by_slug(db, slug)
    if not addon:
        raise NotFoundError("Addon not found")

    # Can't review your own addon
    if addon.owner_id == user.id:
        raise ForbiddenError("You cannot review your own addon")

    # Check for existing review
    existing = await db.execute(
        select(AddonReview)
        .where(AddonReview.user_id == user.id, AddonReview.addon_id == addon.id)
    )
    if existing.scalar_one_or_none():
        raise ConflictError("You have already reviewed this addon. Use PUT to update.")

    review = AddonReview(
        user_id=user.id,
        addon_id=addon.id,
        rating=data.rating,
        title=data.title,
        content=data.content,
    )
    db.add(review)
    await db.commit()
    await db.refresh(review)

    return ReviewResponse(
        id=review.id,
        user_id=review.user_id,
        addon_id=review.addon_id,
        rating=review.rating,
        title=review.title,
        content=review.content,
        is_visible=review.is_visible,
        created_at=review.created_at,
        updated_at=review.updated_at,
        author_username=user.discord_username,
        author_avatar=user.discord_avatar,
        author_discord_id=user.discord_id,
    )


@router.put("", response_model=ReviewResponse)
async def update_review(
    slug: str,
    data: ReviewUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """Update your review for an addon."""
    addon = await AddonService.get_addon_by_slug(db, slug)
    if not addon:
        raise NotFoundError("Addon not found")

    result = await db.execute(
        select(AddonReview)
        .where(AddonReview.user_id == user.id, AddonReview.addon_id == addon.id)
    )
    review = result.scalar_one_or_none()
    if not review:
        raise NotFoundError("You haven't reviewed this addon")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(review, key, value)

    await db.commit()
    await db.refresh(review)

    return ReviewResponse(
        id=review.id,
        user_id=review.user_id,
        addon_id=review.addon_id,
        rating=review.rating,
        title=review.title,
        content=review.content,
        is_visible=review.is_visible,
        created_at=review.created_at,
        updated_at=review.updated_at,
        author_username=user.discord_username,
        author_avatar=user.discord_avatar,
        author_discord_id=user.discord_id,
    )


@router.delete("")
async def delete_review(
    slug: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """Delete your review for an addon."""
    addon = await AddonService.get_addon_by_slug(db, slug)
    if not addon:
        raise NotFoundError("Addon not found")

    result = await db.execute(
        select(AddonReview)
        .where(AddonReview.user_id == user.id, AddonReview.addon_id == addon.id)
    )
    review = result.scalar_one_or_none()
    if not review:
        raise NotFoundError("You haven't reviewed this addon")

    await db.delete(review)
    await db.commit()
    return {"status": "deleted"}
