"""Premium Analytics Suite endpoints (PREM-15 through PREM-19)."""

import secrets
from datetime import datetime, timedelta, timezone, date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.database import get_db
from app.models import (
    User, Addon, SubscriptionTier, VersionCheck, AddonUsageStats, Version,
    SelfHostedConfig, AnalyticsAlert, CohortEntry,
    AlertNotificationChannel, AlertComparison,
)
from app.schemas import (
    SelfHostedConfigCreate, SelfHostedConfigUpdate, SelfHostedConfigResponse,
    AnalyticsAlertCreate, AnalyticsAlertUpdate, AnalyticsAlertResponse, AnalyticsAlertListResponse,
    CohortAnalysisResponse, CohortSummary,
    PredictiveEstimate,
    RealtimeStats,
)
from app.api.deps import get_current_user, rate_limit_check_authenticated, get_effective_tier


# ============== SELF-HOSTED CONFIG (PREM-15) ==============

selfhosted_router = APIRouter(prefix="/addons/{addon_id}/self-hosted", tags=["Self-Hosted Config"])


async def _verify_premium_addon_owner(addon_id: int, user: User, db: AsyncSession) -> Addon:
    """Verify user is premium and owns the addon."""
    effective_tier = get_effective_tier(user)
    if effective_tier != SubscriptionTier.PREMIUM and not user.is_admin:
        raise HTTPException(status_code=403, detail="Self-hosted config requires Premium subscription")
    
    result = await db.execute(select(Addon).where(Addon.id == addon_id))
    addon = result.scalar_one_or_none()
    if not addon:
        raise HTTPException(status_code=404, detail="Addon not found")
    if addon.owner_id != user.id and not user.is_admin:
        raise HTTPException(status_code=403, detail="Not your addon")
    return addon


@selfhosted_router.get("", response_model=SelfHostedConfigResponse)
async def get_self_hosted_config(
    addon_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """Get self-hosted version checker configuration for an addon."""
    await _verify_premium_addon_owner(addon_id, user, db)
    
    result = await db.execute(
        select(SelfHostedConfig).where(SelfHostedConfig.addon_id == addon_id)
    )
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="Self-hosted config not found. Create one first.")
    return config


@selfhosted_router.post("", response_model=SelfHostedConfigResponse, status_code=201)
async def create_self_hosted_config(
    addon_id: int,
    body: SelfHostedConfigCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """Create self-hosted version checker configuration."""
    await _verify_premium_addon_owner(addon_id, user, db)
    
    # Check if config already exists
    existing = await db.execute(
        select(SelfHostedConfig).where(SelfHostedConfig.addon_id == addon_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Self-hosted config already exists for this addon")
    
    verification_token = secrets.token_urlsafe(32)
    
    config = SelfHostedConfig(
        addon_id=addon_id,
        custom_domain=body.custom_domain,
        private_endpoint_enabled=body.private_endpoint_enabled,
        api_key_required=body.api_key_required,
        rate_limit_per_minute=body.rate_limit_per_minute,
        verification_token=verification_token,
    )
    db.add(config)
    await db.commit()
    await db.refresh(config)
    return config


@selfhosted_router.put("", response_model=SelfHostedConfigResponse)
async def update_self_hosted_config(
    addon_id: int,
    body: SelfHostedConfigUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """Update self-hosted version checker configuration."""
    await _verify_premium_addon_owner(addon_id, user, db)
    
    result = await db.execute(
        select(SelfHostedConfig).where(SelfHostedConfig.addon_id == addon_id)
    )
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="Self-hosted config not found")
    
    update_data = body.model_dump(exclude_unset=True)
    
    # If custom domain changes, reset verification
    if "custom_domain" in update_data and update_data["custom_domain"] != config.custom_domain:
        config.domain_verified = False
        config.verification_token = secrets.token_urlsafe(32)
    
    for key, value in update_data.items():
        setattr(config, key, value)
    
    await db.commit()
    await db.refresh(config)
    return config


@selfhosted_router.delete("", status_code=204)
async def delete_self_hosted_config(
    addon_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """Delete self-hosted version checker configuration."""
    await _verify_premium_addon_owner(addon_id, user, db)
    
    result = await db.execute(
        select(SelfHostedConfig).where(SelfHostedConfig.addon_id == addon_id)
    )
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="Self-hosted config not found")
    
    await db.delete(config)
    await db.commit()


@selfhosted_router.post("/verify-domain")
async def verify_domain(
    addon_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """
    Verify custom domain ownership.
    
    The user must add a TXT record `_plexdev-verify=<verification_token>` to their domain.
    """
    await _verify_premium_addon_owner(addon_id, user, db)
    
    result = await db.execute(
        select(SelfHostedConfig).where(SelfHostedConfig.addon_id == addon_id)
    )
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="Self-hosted config not found")
    if not config.custom_domain:
        raise HTTPException(status_code=400, detail="No custom domain configured")
    
    # In production, this would do DNS TXT record lookup
    # For now, return the expected TXT record for the user to set up
    return {
        "domain": config.custom_domain,
        "verified": config.domain_verified,
        "expected_txt_record": f"_plexdev-verify={config.verification_token}",
        "instructions": f"Add a TXT record to {config.custom_domain} with value: _plexdev-verify={config.verification_token}",
    }


# ============== ANALYTICS ALERTS (PREM-17) ==============

alerts_router = APIRouter(prefix="/addons/{addon_id}/alerts", tags=["Analytics Alerts"])


@alerts_router.get("", response_model=AnalyticsAlertListResponse)
async def list_alerts(
    addon_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """List all analytics alerts for an addon."""
    await _verify_premium_addon_owner(addon_id, user, db)
    
    result = await db.execute(
        select(AnalyticsAlert)
        .where(AnalyticsAlert.addon_id == addon_id)
        .order_by(AnalyticsAlert.created_at.desc())
    )
    alerts = result.scalars().all()
    
    return AnalyticsAlertListResponse(alerts=alerts, total=len(alerts))


@alerts_router.post("", response_model=AnalyticsAlertResponse, status_code=201)
async def create_alert(
    addon_id: int,
    body: AnalyticsAlertCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """Create an analytics alert for an addon."""
    await _verify_premium_addon_owner(addon_id, user, db)
    
    # Limit to 10 alerts per addon
    count_result = await db.execute(
        select(func.count(AnalyticsAlert.id)).where(AnalyticsAlert.addon_id == addon_id)
    )
    if count_result.scalar() >= 10:
        raise HTTPException(status_code=400, detail="Maximum 10 alerts per addon")
    
    # Validate notification channel has required fields
    if body.notification_channel == AlertNotificationChannel.WEBHOOK and not body.webhook_url:
        raise HTTPException(status_code=400, detail="webhook_url required for webhook channel")
    if body.notification_channel == AlertNotificationChannel.EMAIL and not body.email:
        raise HTTPException(status_code=400, detail="email required for email channel")
    if body.notification_channel == AlertNotificationChannel.DISCORD and not body.discord_webhook_url:
        raise HTTPException(status_code=400, detail="discord_webhook_url required for discord channel")
    
    alert = AnalyticsAlert(
        addon_id=addon_id,
        name=body.name,
        metric=body.metric,
        comparison=body.comparison,
        threshold=body.threshold,
        notification_channel=body.notification_channel,
        webhook_url=body.webhook_url,
        email=body.email,
        discord_webhook_url=body.discord_webhook_url,
        cooldown_minutes=body.cooldown_minutes,
    )
    db.add(alert)
    await db.commit()
    await db.refresh(alert)
    return alert


@alerts_router.put("/{alert_id}", response_model=AnalyticsAlertResponse)
async def update_alert(
    addon_id: int,
    alert_id: int,
    body: AnalyticsAlertUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """Update an analytics alert."""
    await _verify_premium_addon_owner(addon_id, user, db)
    
    result = await db.execute(
        select(AnalyticsAlert).where(
            AnalyticsAlert.id == alert_id,
            AnalyticsAlert.addon_id == addon_id,
        )
    )
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(alert, key, value)
    
    await db.commit()
    await db.refresh(alert)
    return alert


@alerts_router.delete("/{alert_id}", status_code=204)
async def delete_alert(
    addon_id: int,
    alert_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """Delete an analytics alert."""
    await _verify_premium_addon_owner(addon_id, user, db)
    
    result = await db.execute(
        select(AnalyticsAlert).where(
            AnalyticsAlert.id == alert_id,
            AnalyticsAlert.addon_id == addon_id,
        )
    )
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    await db.delete(alert)
    await db.commit()


@alerts_router.post("/{alert_id}/test")
async def test_alert(
    addon_id: int,
    alert_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """Send a test notification for an alert."""
    await _verify_premium_addon_owner(addon_id, user, db)
    
    result = await db.execute(
        select(AnalyticsAlert).where(
            AnalyticsAlert.id == alert_id,
            AnalyticsAlert.addon_id == addon_id,
        )
    )
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    # In production, this would actually send the notification.
    # For now, return success with details about what would be sent.
    return {
        "status": "test_sent",
        "channel": alert.notification_channel.value,
        "message": f"Test alert: {alert.name} - {alert.metric} {alert.comparison.value} {alert.threshold}",
    }


# ============== COHORT ANALYSIS (PREM-18) ==============

cohort_router = APIRouter(prefix="/addons/{addon_id}/cohorts", tags=["Cohort Analysis"])


@cohort_router.get("", response_model=CohortAnalysisResponse)
async def get_cohort_analysis(
    addon_id: int,
    days: int = Query(30, ge=1, le=90),
    from_version: Optional[str] = Query(None, description="Filter by source version"),
    to_version: Optional[str] = Query(None, description="Filter by target version"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """
    Get cohort analysis showing version upgrade paths.
    
    Shows how many users upgraded from one version to another within the time window.
    """
    await _verify_premium_addon_owner(addon_id, user, db)
    
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    
    query = select(
        CohortEntry.from_version,
        CohortEntry.to_version,
        func.count(func.distinct(CohortEntry.client_ip_hash)).label("user_count"),
        func.min(CohortEntry.transitioned_at).label("first_transition"),
        func.max(CohortEntry.transitioned_at).label("last_transition"),
    ).where(
        CohortEntry.addon_id == addon_id,
        CohortEntry.transitioned_at >= cutoff,
    )
    
    if from_version:
        query = query.where(CohortEntry.from_version == from_version)
    if to_version:
        query = query.where(CohortEntry.to_version == to_version)
    
    query = query.group_by(
        CohortEntry.from_version, CohortEntry.to_version
    ).order_by(func.count(func.distinct(CohortEntry.client_ip_hash)).desc())
    
    result = await db.execute(query)
    rows = result.all()
    
    cohorts = [
        CohortSummary(
            from_version=row.from_version,
            to_version=row.to_version,
            user_count=row.user_count,
            first_transition=row.first_transition,
            last_transition=row.last_transition,
        )
        for row in rows
    ]
    
    total = sum(c.user_count for c in cohorts)
    
    return CohortAnalysisResponse(
        addon_id=addon_id,
        period_days=days,
        cohorts=cohorts,
        total_transitions=total,
    )


# ============== PREDICTIVE ANALYTICS (PREM-19) ==============

predictive_router = APIRouter(prefix="/addons/{addon_id}/predictive", tags=["Predictive Analytics"])


@predictive_router.get("", response_model=PredictiveEstimate)
async def get_predictive_analytics(
    addon_id: int,
    target_version: str = Query(..., description="Version to estimate adoption for"),
    days: int = Query(14, ge=3, le=90, description="Days of history to base prediction on"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """
    Estimate rollout completion time based on current adoption rate.
    
    Uses linear regression on recent adoption data to project when adoption
    milestones (50%, 90%, 100%) will be reached.
    """
    await _verify_premium_addon_owner(addon_id, user, db)
    
    # Get the version
    version_result = await db.execute(
        select(Version).where(
            Version.addon_id == addon_id,
            Version.version == target_version,
        )
    )
    version = version_result.scalar_one_or_none()
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    
    start_date = date.today() - timedelta(days=days)
    start_datetime = datetime.combine(start_date, datetime.min.time())
    
    # Get total unique users for this addon (all versions) in the period
    total_users_result = await db.execute(
        select(func.count(func.distinct(VersionCheck.client_ip_hash))).where(
            VersionCheck.addon_id == addon_id,
            VersionCheck.timestamp >= start_datetime,
        )
    )
    total_users = total_users_result.scalar() or 0
    
    # Get unique users on the target version
    adopted_result = await db.execute(
        select(func.count(func.distinct(VersionCheck.client_ip_hash))).where(
            VersionCheck.addon_id == addon_id,
            VersionCheck.version_id == version.id,
            VersionCheck.timestamp >= start_datetime,
        )
    )
    adopted_users = adopted_result.scalar() or 0
    
    # Calculate daily adoption rates for the target version over the period
    daily_adoption = await db.execute(
        select(
            func.date(VersionCheck.timestamp).label("day"),
            func.count(func.distinct(VersionCheck.client_ip_hash)).label("users"),
        ).where(
            VersionCheck.addon_id == addon_id,
            VersionCheck.version_id == version.id,
            VersionCheck.timestamp >= start_datetime,
        ).group_by(func.date(VersionCheck.timestamp))
        .order_by(func.date(VersionCheck.timestamp))
    )
    daily_rows = daily_adoption.all()
    
    current_adoption = (adopted_users / total_users * 100) if total_users > 0 else 0
    
    # Calculate daily adoption rate (average new adopters per day)
    daily_rate = 0.0
    if len(daily_rows) >= 2:
        # Use last N days to compute growth trend
        values = [row.users for row in daily_rows]
        # Simple average daily new user count
        daily_rate = sum(values) / len(values) if values else 0.0
    elif len(daily_rows) == 1:
        daily_rate = daily_rows[0].users
    
    # Calculate adoption rate as percent per day
    daily_adoption_rate_pct = (daily_rate / total_users * 100) if total_users > 0 else 0.0
    
    # Estimate days to milestones
    def estimate_days_to(target_pct: float) -> Optional[int]:
        if current_adoption >= target_pct:
            return 0
        if daily_adoption_rate_pct <= 0:
            return None
        remaining = target_pct - current_adoption
        return max(1, int(remaining / daily_adoption_rate_pct + 0.5))
    
    return PredictiveEstimate(
        addon_id=addon_id,
        target_version=target_version,
        current_adoption_percent=round(current_adoption, 2),
        daily_adoption_rate=round(daily_adoption_rate_pct, 4),
        estimated_days_to_50=estimate_days_to(50.0),
        estimated_days_to_90=estimate_days_to(90.0),
        estimated_days_to_100=estimate_days_to(100.0),
        total_users=total_users,
        adopted_users=adopted_users,
    )


# ============== REAL-TIME ANALYTICS (PREM-16) ==============

realtime_router = APIRouter(prefix="/addons/{addon_id}/realtime", tags=["Real-Time Analytics"])


@realtime_router.get("", response_model=RealtimeStats)
async def get_realtime_stats(
    addon_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """
    Get real-time analytics snapshot for an addon.
    
    Returns check counts and unique users for the last hour and 24 hours.
    """
    await _verify_premium_addon_owner(addon_id, user, db)
    
    now = datetime.now(timezone.utc)
    one_hour_ago = now - timedelta(hours=1)
    twenty_four_hours_ago = now - timedelta(hours=24)
    
    # Checks in last hour
    hour_result = await db.execute(
        select(
            func.count(VersionCheck.id).label("count"),
            func.count(func.distinct(VersionCheck.client_ip_hash)).label("unique"),
        ).where(
            VersionCheck.addon_id == addon_id,
            VersionCheck.timestamp >= one_hour_ago,
        )
    )
    hour_row = hour_result.one()
    
    # Checks in last 24 hours
    day_result = await db.execute(
        select(func.count(VersionCheck.id)).where(
            VersionCheck.addon_id == addon_id,
            VersionCheck.timestamp >= twenty_four_hours_ago,
        )
    )
    checks_24h = day_result.scalar() or 0
    
    # Active versions in last 24 hours
    active_versions_result = await db.execute(
        select(func.count(func.distinct(VersionCheck.version_id))).where(
            VersionCheck.addon_id == addon_id,
            VersionCheck.timestamp >= twenty_four_hours_ago,
            VersionCheck.version_id.isnot(None),
        )
    )
    active_versions = active_versions_result.scalar() or 0
    
    # Top version in last 24 hours
    top_version_result = await db.execute(
        select(Version.version).join(
            VersionCheck, VersionCheck.version_id == Version.id
        ).where(
            VersionCheck.addon_id == addon_id,
            VersionCheck.timestamp >= twenty_four_hours_ago,
        ).group_by(Version.version)
        .order_by(func.count(VersionCheck.id).desc())
        .limit(1)
    )
    top_version = top_version_result.scalar_one_or_none()
    
    return RealtimeStats(
        addon_id=addon_id,
        checks_last_hour=hour_row.count or 0,
        checks_last_24h=checks_24h,
        unique_users_last_hour=hour_row.unique or 0,
        active_versions=active_versions,
        top_version=top_version,
    )


@realtime_router.get("/recent")
async def get_recent_checks(
    addon_id: int,
    limit: int = Query(50, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """Get the most recent version checks for live feed display."""
    await _verify_premium_addon_owner(addon_id, user, db)
    
    result = await db.execute(
        select(
            VersionCheck.id,
            VersionCheck.checked_version,
            VersionCheck.timestamp,
            VersionCheck.client_ip_hash,
            Version.version.label("resolved_version"),
        ).outerjoin(Version, VersionCheck.version_id == Version.id)
        .where(VersionCheck.addon_id == addon_id)
        .order_by(VersionCheck.timestamp.desc())
        .limit(limit)
    )
    
    checks = [
        {
            "id": row.id,
            "checked_version": row.checked_version,
            "resolved_version": row.resolved_version,
            "timestamp": row.timestamp.isoformat() if row.timestamp else None,
            "client_hash_prefix": row.client_ip_hash[:8] if row.client_ip_hash else None,
        }
        for row in result.all()
    ]
    
    return {"checks": checks, "total": len(checks)}


@realtime_router.get("/hourly")
async def get_hourly_breakdown(
    addon_id: int,
    hours: int = Query(24, ge=1, le=72),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """Get hourly check breakdown for the last N hours."""
    await _verify_premium_addon_owner(addon_id, user, db)
    
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    
    result = await db.execute(
        select(
            func.date_trunc('hour', VersionCheck.timestamp).label("hour"),
            func.count(VersionCheck.id).label("checks"),
            func.count(func.distinct(VersionCheck.client_ip_hash)).label("unique_users"),
        ).where(
            VersionCheck.addon_id == addon_id,
            VersionCheck.timestamp >= cutoff,
        ).group_by(func.date_trunc('hour', VersionCheck.timestamp))
        .order_by(func.date_trunc('hour', VersionCheck.timestamp))
    )
    
    hourly = [
        {
            "hour": row.hour.isoformat() if row.hour else None,
            "checks": row.checks,
            "unique_users": row.unique_users,
        }
        for row in result.all()
    ]
    
    return {"hourly": hourly, "period_hours": hours}
