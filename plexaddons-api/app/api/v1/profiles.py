"""Public profile endpoints - accessible without authentication."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from typing import List
from app.database import get_db
from app.models import User, Addon
from app.schemas import UserPublicProfile, AddonResponse

router = APIRouter(prefix="/u", tags=["Profiles"])


@router.get("/{identifier}", response_model=UserPublicProfile)
async def get_public_profile(
    identifier: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get a user's public profile.
    
    The identifier can be:
    - A Discord ID (numeric string like "123456789012345678")
    - A custom profile slug (for Pro/Premium users)
    
    Returns 404 if user not found or profile is not public.
    """
    # Try to find user by Discord ID or profile slug
    result = await db.execute(
        select(User).where(
            or_(
                User.discord_id == identifier,
                User.profile_slug == identifier
            )
        )
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )
    
    # Check if profile is public
    if not user.profile_public:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )
    
    # Get user's addons if show_addons is enabled
    addons_list = None
    if user.show_addons:
        addons_result = await db.execute(
            select(Addon)
            .where(Addon.owner_id == user.id)
            .where(Addon.is_public == True)
            .order_by(Addon.name)
        )
        addons = addons_result.scalars().all()
        addons_list = [
            AddonResponse(
                id=addon.id,
                owner_id=addon.owner_id,
                name=addon.name,
                slug=addon.slug,
                description=addon.description,
                homepage=addon.homepage,
                external=addon.external,
                is_active=addon.is_active,
                is_public=addon.is_public,
                created_at=addon.created_at,
                updated_at=addon.updated_at,
                owner_username=user.discord_username,
            )
            for addon in addons
        ]
    
    # Parse badges JSON if stored as string
    badges = user.badges if user.badges else []
    
    return UserPublicProfile(
        discord_id=user.discord_id,
        discord_username=user.discord_username,
        discord_avatar=user.discord_avatar,
        subscription_tier=user.subscription_tier,
        bio=user.bio,
        website=user.website,
        github_username=user.github_username,
        twitter_username=user.twitter_username,
        profile_slug=user.profile_slug,
        badges=badges,
        banner_url=user.banner_url,
        accent_color=user.accent_color,
        created_at=user.created_at,
        addons=addons_list,
    )
