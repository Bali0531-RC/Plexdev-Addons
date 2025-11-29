from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from typing import Optional, List
from datetime import datetime, timedelta
import json
from app.database import get_db
from app.models import User, Addon, Version, Subscription, AdminAuditLog, SubscriptionTier, SubscriptionStatus
from app.schemas import (
    UserResponse,
    AdminUserUpdate,
    AdminStatsResponse,
    AuditLogEntry,
    AuditLogListResponse,
    AddonResponse,
)
from app.services import UserService, AddonService
from app.api.deps import get_admin_user, rate_limit_check_authenticated
from app.core.exceptions import NotFoundError, BadRequestError

router = APIRouter(prefix="/admin", tags=["Admin"])


async def log_admin_action(
    db: AsyncSession,
    admin: User,
    action: str,
    target_type: Optional[str] = None,
    target_id: Optional[int] = None,
    details: Optional[dict] = None,
    ip_address: Optional[str] = None,
):
    """Log an admin action."""
    log_entry = AdminAuditLog(
        admin_id=admin.id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        details=json.dumps(details) if details else None,
        ip_address=ip_address,
    )
    db.add(log_entry)
    await db.commit()


@router.get("/stats", response_model=AdminStatsResponse)
async def get_admin_stats(
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """Get platform statistics."""
    # Total users
    total_users_result = await db.execute(select(func.count(User.id)))
    total_users = total_users_result.scalar() or 0
    
    # Total addons
    total_addons_result = await db.execute(select(func.count(Addon.id)))
    total_addons = total_addons_result.scalar() or 0
    
    # Total versions
    total_versions_result = await db.execute(select(func.count(Version.id)))
    total_versions = total_versions_result.scalar() or 0
    
    # Active subscriptions
    active_subs_result = await db.execute(
        select(func.count(Subscription.id))
        .where(Subscription.status == SubscriptionStatus.ACTIVE)
    )
    active_subscriptions = active_subs_result.scalar() or 0
    
    # Users by tier
    users_by_tier = {}
    for tier in SubscriptionTier:
        count_result = await db.execute(
            select(func.count(User.id)).where(User.subscription_tier == tier)
        )
        users_by_tier[tier.value] = count_result.scalar() or 0
    
    # Recent signups (last 7 days)
    week_ago = datetime.utcnow() - timedelta(days=7)
    recent_result = await db.execute(
        select(func.count(User.id)).where(User.created_at >= week_ago)
    )
    recent_signups = recent_result.scalar() or 0
    
    return AdminStatsResponse(
        total_users=total_users,
        total_addons=total_addons,
        total_versions=total_versions,
        active_subscriptions=active_subscriptions,
        users_by_tier=users_by_tier,
        recent_signups=recent_signups,
    )


@router.get("/users")
async def list_users(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    search: Optional[str] = None,
    tier: Optional[SubscriptionTier] = None,
    is_admin: Optional[bool] = None,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """List all users with live storage calculation."""
    skip = (page - 1) * per_page
    users, total = await UserService.list_users(
        db, skip=skip, limit=per_page, search=search, tier=tier, is_admin=is_admin
    )
    
    # Calculate live storage for each user
    user_responses = []
    for u in users:
        storage_used = await UserService.calculate_storage_used(db, u.id)
        user_responses.append(UserResponse(
            id=u.id,
            discord_id=u.discord_id,
            discord_username=u.discord_username,
            discord_avatar=u.discord_avatar,
            email=u.email,
            subscription_tier=u.subscription_tier,
            storage_used_bytes=storage_used,
            storage_quota_bytes=u.storage_quota_bytes,
            is_admin=u.is_admin,
            created_at=u.created_at,
            last_login_at=u.last_login_at,
        ))
    
    return {
        "users": user_responses,
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """Get user details with live storage calculation."""
    user = await UserService.get_user_by_id(db, user_id)
    if not user:
        raise NotFoundError("User not found")
    
    # Calculate live storage
    storage_used = await UserService.calculate_storage_used(db, user.id)
    
    return UserResponse(
        id=user.id,
        discord_id=user.discord_id,
        discord_username=user.discord_username,
        discord_avatar=user.discord_avatar,
        email=user.email,
        subscription_tier=user.subscription_tier,
        storage_used_bytes=storage_used,
        storage_quota_bytes=user.storage_quota_bytes,
        is_admin=user.is_admin,
        created_at=user.created_at,
        last_login_at=user.last_login_at,
    )


@router.patch("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    data: AdminUserUpdate,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """Update user (admin only)."""
    user = await UserService.get_user_by_id(db, user_id)
    if not user:
        raise NotFoundError("User not found")
    
    # Prevent self-demotion
    if user.id == admin.id and data.is_admin is False:
        raise BadRequestError("You cannot demote yourself")
    
    update_dict = data.model_dump(exclude_unset=True)
    
    # Handle tier change
    if "subscription_tier" in update_dict and update_dict["subscription_tier"]:
        await UserService.update_user_tier(db, user, update_dict["subscription_tier"])
        del update_dict["subscription_tier"]
    
    # Update other fields
    updated_user = await UserService.update_user(db, user, **update_dict)
    
    # Log admin action
    await log_admin_action(
        db, admin,
        action="update_user",
        target_type="user",
        target_id=user_id,
        details={"changes": data.model_dump(exclude_unset=True)},
    )
    
    return updated_user


@router.post("/users/{user_id}/promote")
async def promote_to_admin(
    user_id: int,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """Promote user to admin."""
    user = await UserService.get_user_by_id(db, user_id)
    if not user:
        raise NotFoundError("User not found")
    
    if user.is_admin:
        raise BadRequestError("User is already an admin")
    
    user.is_admin = True
    await db.commit()
    
    await log_admin_action(
        db, admin,
        action="promote_admin",
        target_type="user",
        target_id=user_id,
        details={"username": user.discord_username},
    )
    
    return {"status": "promoted", "user_id": user_id}


@router.post("/users/{user_id}/demote")
async def demote_from_admin(
    user_id: int,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """Demote user from admin."""
    user = await UserService.get_user_by_id(db, user_id)
    if not user:
        raise NotFoundError("User not found")
    
    if user.id == admin.id:
        raise BadRequestError("You cannot demote yourself")
    
    if not user.is_admin:
        raise BadRequestError("User is not an admin")
    
    user.is_admin = False
    await db.commit()
    
    await log_admin_action(
        db, admin,
        action="demote_admin",
        target_type="user",
        target_id=user_id,
        details={"username": user.discord_username},
    )
    
    return {"status": "demoted", "user_id": user_id}


@router.get("/addons")
async def list_all_addons(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    search: Optional[str] = None,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """List all addons (including non-public)."""
    skip = (page - 1) * per_page
    addons, total = await AddonService.list_addons(
        db, skip=skip, limit=per_page, search=search, public_only=False
    )
    
    return {
        "addons": [AddonResponse(**addon) for addon in addons],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.delete("/addons/{addon_id}")
async def admin_delete_addon(
    addon_id: int,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """Delete an addon (admin override)."""
    result = await db.execute(select(Addon).where(Addon.id == addon_id))
    addon = result.scalar_one_or_none()
    if not addon:
        raise NotFoundError("Addon not found")
    
    addon_name = addon.name
    await db.delete(addon)
    await db.commit()
    
    await log_admin_action(
        db, admin,
        action="delete_addon",
        target_type="addon",
        target_id=addon_id,
        details={"addon_name": addon_name},
    )
    
    return {"status": "deleted"}


@router.get("/audit-log", response_model=AuditLogListResponse)
async def get_audit_log(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """Get admin audit log."""
    skip = (page - 1) * per_page
    
    # Count total
    count_result = await db.execute(select(func.count(AdminAuditLog.id)))
    total = count_result.scalar() or 0
    
    # Get entries with admin username
    result = await db.execute(
        select(AdminAuditLog)
        .order_by(AdminAuditLog.created_at.desc())
        .offset(skip)
        .limit(per_page)
    )
    entries = result.scalars().all()
    
    # Enrich with admin usernames
    enriched = []
    for entry in entries:
        admin_username = None
        if entry.admin_id:
            admin_result = await db.execute(select(User).where(User.id == entry.admin_id))
            admin_user = admin_result.scalar_one_or_none()
            admin_username = admin_user.discord_username if admin_user else None
        
        enriched.append(AuditLogEntry(
            id=entry.id,
            admin_id=entry.admin_id,
            admin_username=admin_username,
            action=entry.action,
            target_type=entry.target_type,
            target_id=entry.target_id,
            details=entry.details,
            ip_address=entry.ip_address,
            created_at=entry.created_at,
        ))
    
    return AuditLogListResponse(
        entries=enriched,
        total=total,
        page=page,
        per_page=per_page,
    )


@router.post("/audit-log/cleanup")
async def cleanup_audit_log(
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """Manually trigger audit log cleanup (removes entries older than 90 days)."""
    from app.config import get_settings
    settings = get_settings()
    
    cutoff = datetime.utcnow() - timedelta(days=settings.audit_log_retention_days)
    
    result = await db.execute(
        delete(AdminAuditLog).where(AdminAuditLog.created_at < cutoff)
    )
    deleted_count = result.rowcount
    await db.commit()
    
    await log_admin_action(
        db, admin,
        action="cleanup_audit_log",
        details={"deleted_count": deleted_count},
    )
    
    return {"status": "cleaned", "deleted_count": deleted_count}
