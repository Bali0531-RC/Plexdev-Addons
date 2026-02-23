"""Analytics endpoints for addon usage statistics."""

import csv
import io
import json
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import date, timedelta
from app.database import get_db
from app.models import User, Addon, SubscriptionTier, ApiKey, ApiRequestLog
from app.schemas import AddonAnalyticsResponse, AnalyticsSummary
from app.services import AnalyticsService
from app.api.deps import get_current_user, rate_limit_check_authenticated, get_effective_tier

router = APIRouter(prefix="/analytics", tags=["Analytics"])


def _get_max_days(effective_tier: SubscriptionTier) -> int:
    return 90 if effective_tier == SubscriptionTier.PREMIUM else 30


@router.get("/summary", response_model=AnalyticsSummary)
async def get_my_analytics_summary(
    days: int = Query(None, ge=1, le=90, description="Custom date range (days). Capped by tier."),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """
    Get analytics summary for all of the current user's addons.
    
    Supports custom date range via `days` parameter (capped by tier limit).
    """
    effective_tier = get_effective_tier(user)
    if effective_tier == SubscriptionTier.FREE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Analytics require Pro or Premium subscription"
        )
    
    max_days = _get_max_days(effective_tier)
    actual_days = min(days, max_days) if days else max_days
    
    summary = await AnalyticsService.get_user_analytics_summary(
        db, user.id, actual_days
    )
    
    return summary


@router.get("/addons/{addon_id}", response_model=AddonAnalyticsResponse)
async def get_addon_analytics(
    addon_id: int,
    days: int = Query(None, ge=1, le=90, description="Custom date range (days). Capped by tier."),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """
    Get detailed analytics for a specific addon.
    
    Supports custom date range via `days` parameter (capped by tier limit).
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
    
    if addon.owner_id != user.id and not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view analytics for your own addons"
        )
    
    max_days = _get_max_days(effective_tier)
    actual_days = min(days, max_days) if days else max_days
    
    analytics = await AnalyticsService.get_addon_analytics(
        db, addon_id, actual_days
    )
    
    return analytics


@router.get("/addons/{addon_id}/export")
async def export_addon_analytics(
    addon_id: int,
    format: str = Query("csv", regex="^(csv|json)$"),
    days: int = Query(None, ge=1, le=90),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """Export addon analytics data as CSV or JSON (Pro+ feature)."""
    effective_tier = get_effective_tier(user)
    if effective_tier == SubscriptionTier.FREE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Analytics export requires Pro or Premium subscription"
        )
    
    addon_result = await db.execute(select(Addon).where(Addon.id == addon_id))
    addon = addon_result.scalar_one_or_none()
    if not addon:
        raise HTTPException(status_code=404, detail="Addon not found")
    if addon.owner_id != user.id and not user.is_admin:
        raise HTTPException(status_code=403, detail="Not your addon")
    
    max_days = _get_max_days(effective_tier)
    actual_days = min(days, max_days) if days else max_days
    
    analytics = await AnalyticsService.get_addon_analytics(db, addon_id, actual_days)
    
    if format == "json":
        export_data = {
            "addon": analytics.addon_name,
            "period_days": analytics.period_days,
            "total_checks": analytics.total_checks,
            "total_unique_users": analytics.total_unique_users,
            "daily_stats": [
                {"date": str(d.date), "check_count": d.check_count, "unique_users": d.unique_users}
                for d in analytics.daily_stats
            ],
            "version_distribution": [
                {
                    "version": v.version, "check_count": v.check_count,
                    "unique_users": v.unique_users, "percentage": v.percentage
                }
                for v in analytics.version_distribution
            ],
        }
        content = json.dumps(export_data, indent=2)
        return StreamingResponse(
            io.BytesIO(content.encode()),
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename={analytics.addon_slug}-analytics.json"},
        )
    else:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["date", "check_count", "unique_users"])
        for d in analytics.daily_stats:
            writer.writerow([str(d.date), d.check_count, d.unique_users])
        content = output.getvalue()
        return StreamingResponse(
            io.BytesIO(content.encode()),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={analytics.addon_slug}-analytics.csv"},
        )


@router.get("/api-usage")
async def get_api_key_usage(
    days: int = Query(7, ge=1, le=30),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """
    Get API key usage analytics (Pro+ feature).
    
    Returns per-key request counts and top endpoints.
    """
    effective_tier = get_effective_tier(user)
    if effective_tier == SubscriptionTier.FREE:
        raise HTTPException(status_code=403, detail="API usage analytics require Pro or Premium subscription")
    
    # Get user's API keys
    keys_result = await db.execute(
        select(ApiKey).where(ApiKey.user_id == user.id, ApiKey.is_active == True)
    )
    keys = keys_result.scalars().all()
    
    cutoff = date.today() - timedelta(days=days)
    
    # Get per-endpoint breakdown for user's requests
    endpoint_stats = await db.execute(
        select(
            ApiRequestLog.endpoint,
            ApiRequestLog.method,
            func.count(ApiRequestLog.id).label("request_count"),
        ).where(
            ApiRequestLog.user_id == user.id,
            ApiRequestLog.timestamp >= cutoff,
        ).group_by(ApiRequestLog.endpoint, ApiRequestLog.method)
        .order_by(func.count(ApiRequestLog.id).desc())
        .limit(20)
    )
    
    top_endpoints = [
        {"endpoint": row.endpoint, "method": row.method, "count": row.request_count}
        for row in endpoint_stats.all()
    ]
    
    # Daily request counts
    daily_stats = await db.execute(
        select(
            func.date(ApiRequestLog.timestamp).label("date"),
            func.count(ApiRequestLog.id).label("count"),
        ).where(
            ApiRequestLog.user_id == user.id,
            ApiRequestLog.timestamp >= cutoff,
        ).group_by(func.date(ApiRequestLog.timestamp))
        .order_by(func.date(ApiRequestLog.timestamp))
    )
    
    daily = [{"date": str(row.date), "count": row.count} for row in daily_stats.all()]
    
    key_summaries = [
        {
            "name": k.name,
            "key_prefix": k.key_prefix,
            "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None,
            "usage_count": k.usage_count,
            "is_active": k.is_active,
        }
        for k in keys
    ]
    
    return {
        "keys": key_summaries,
        "top_endpoints": top_endpoints,
        "daily_requests": daily,
        "period_days": days,
    }
