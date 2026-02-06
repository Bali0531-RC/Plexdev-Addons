"""Public profile endpoints - accessible without authentication."""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, func
from sqlalchemy.orm import selectinload
from typing import List, Optional
from datetime import datetime, timezone
from app.database import get_db
from app.models import User, Addon, Version
from app.schemas import UserPublicProfile, AddonResponse

router = APIRouter(prefix="/u", tags=["Profiles"])


def sanitize_ilike_pattern(search: str) -> str:
    """Escape special characters in ILIKE patterns to prevent SQL injection."""
    return search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def get_effective_tier(user: User):
    """Get effective tier considering temp_tier if active."""
    if user.temp_tier and user.temp_tier_expires_at:
        # Check if temp tier is still valid
        now = datetime.now(timezone.utc)
        expires = user.temp_tier_expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if now < expires:
            return user.temp_tier
    return user.subscription_tier


@router.get("", response_model=dict)
async def list_public_users(
    page: int = Query(1, ge=1),
    per_page: int = Query(24, ge=1, le=100),
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    List all users with public profiles.
    Returns basic profile info without detailed addons.
    """
    query = select(User).where(User.profile_public == True)
    count_query = select(func.count(User.id)).where(User.profile_public == True)
    
    if search:
        safe_search = sanitize_ilike_pattern(search)
        search_filter = User.discord_username.ilike(f"%{safe_search}%")
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)
    
    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # Get users with pagination
    skip = (page - 1) * per_page
    query = query.order_by(User.created_at.desc()).offset(skip).limit(per_page)
    result = await db.execute(query)
    users = result.scalars().all()
    
    # Get addon counts for each user
    user_ids = [u.id for u in users]
    addon_counts = {}
    if user_ids:
        counts_result = await db.execute(
            select(Addon.owner_id, func.count(Addon.id))
            .where(Addon.owner_id.in_(user_ids))
            .where(Addon.is_public == True)
            .group_by(Addon.owner_id)
        )
        addon_counts = {row[0]: row[1] for row in counts_result.all()}
    
    users_list = []
    for user in users:
        # Parse badges
        badges = []
        if user.badges:
            import json
            try:
                badges = json.loads(user.badges) if isinstance(user.badges, str) else user.badges
            except Exception:
                badges = []
        
        # Get effective tier (temp_tier if active)
        effective_tier = get_effective_tier(user)
        
        users_list.append({
            "discord_id": user.discord_id,
            "discord_username": user.discord_username,
            "discord_avatar": user.discord_avatar,
            "subscription_tier": effective_tier.value,
            "profile_slug": user.profile_slug,
            "badges": badges,
            "bio": user.bio,
            "addon_count": addon_counts.get(user.id, 0),
            "created_at": user.created_at.isoformat(),
        })
    
    return {
        "users": users_list,
        "total": total,
        "page": page,
        "per_page": per_page,
    }


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
            .options(selectinload(Addon.versions))
            .where(Addon.owner_id == user.id)
            .where(Addon.is_public == True)
            .order_by(Addon.name)
        )
        addons = addons_result.scalars().all()
        addons_list = []
        for addon in addons:
            # Get latest version and count
            versions = sorted(addon.versions, key=lambda v: v.release_date, reverse=True) if addon.versions else []
            latest = versions[0] if versions else None
            addons_list.append(
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
                    owner_discord_id=user.discord_id,
                    latest_version=latest.version if latest else None,
                    latest_release_date=latest.release_date if latest else None,
                    version_count=len(versions),
                )
            )
    
    # Parse badges JSON if stored as string
    badges = user.badges if user.badges else []
    
    # Get effective tier (temp_tier if active)
    effective_tier = get_effective_tier(user)
    
    return UserPublicProfile(
        discord_id=user.discord_id,
        discord_username=user.discord_username,
        discord_avatar=user.discord_avatar,
        subscription_tier=effective_tier,
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
