"""Analytics endpoints for addon usage statistics."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models import User, Addon, SubscriptionTier
from app.schemas import AddonAnalyticsResponse, AnalyticsSummary
from app.services import AnalyticsService
from app.api.deps import get_current_user, rate_limit_check_authenticated, get_effective_tier

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/summary", response_model=AnalyticsSummary)
async def get_my_analytics_summary(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """
    Get analytics summary for all of the current user's addons.
    
    Tier restrictions:
    - Pro: 30 days of data
    - Premium: 90 days of data
    - Free: Not available
    """
    effective_tier = get_effective_tier(user)
    if effective_tier == SubscriptionTier.FREE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Analytics require Pro or Premium subscription"
        )
    
    # Determine days based on tier
    days = 90 if effective_tier == SubscriptionTier.PREMIUM else 30
    
    summary = await AnalyticsService.get_user_analytics_summary(
        db, user.id, days
    )
    
    return summary


@router.get("/addons/{addon_id}", response_model=AddonAnalyticsResponse)
async def get_addon_analytics(
    addon_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """
    Get detailed analytics for a specific addon.
    
    Tier restrictions:
    - Pro: 30 days of data
    - Premium: 90 days of data
    - Free: Not available
    
    Only the addon owner can view analytics.
    """
    effective_tier = get_effective_tier(user)
    if effective_tier == SubscriptionTier.FREE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Analytics require Pro or Premium subscription"
        )
    
    # Verify ownership
    addon_result = await db.execute(
        select(Addon).where(Addon.id == addon_id)
    )
    addon = addon_result.scalar_one_or_none()
    
    if not addon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Addon not found"
        )
    
    if addon.user_id != user.id and not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view analytics for your own addons"
        )
    
    # Determine days based on effective tier
    days = 90 if effective_tier == SubscriptionTier.PREMIUM else 30
    
    analytics = await AnalyticsService.get_addon_analytics(
        db, addon_id, days
    )
    
    return analytics
