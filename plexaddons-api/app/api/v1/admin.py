from fastapi import APIRouter, Depends, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from sqlalchemy.orm import selectinload
from typing import Optional, List
from datetime import datetime, timedelta
import json
from app.database import get_db
from app.models import (
    User, Addon, Version, Subscription, AdminAuditLog, SubscriptionTier, SubscriptionStatus,
    Ticket, TicketMessage, TicketStatus, TicketPriority, TicketCategory, CannedResponse
)
from app.schemas import (
    UserResponse,
    AdminUserUpdate,
    AdminStatsResponse,
    AuditLogEntry,
    AuditLogListResponse,
    AddonResponse,
    AddonUpdate,
    VersionResponse,
    VersionUpdate,
    GrantTempTierRequest,
    # Ticket schemas
    TicketResponse,
    TicketDetailResponse,
    TicketListResponse,
    TicketMessageResponse,
    TicketMessageCreate,
    TicketStatusUpdate,
    TicketPriorityUpdate,
    TicketAssignUpdate,
    TicketStatsResponse,
    TicketAttachmentResponse,
    # Canned response schemas
    CannedResponseCreate,
    CannedResponseUpdate,
    CannedResponseResponse,
    CannedResponseListResponse,
)
from app.services import UserService, AddonService, VersionService, ticket_service, email_service, discord_service
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


@router.post("/users/{user_id}/grant-temp-tier")
async def grant_temp_tier(
    user_id: int,
    request: GrantTempTierRequest,
    background_tasks: BackgroundTasks,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """Grant a temporary tier to a user that expires after specified days."""
    user = await UserService.get_user_by_id(db, user_id)
    if not user:
        raise NotFoundError("User not found")
    
    # Can't downgrade - temp tier must be higher than current tier
    tier_order = {SubscriptionTier.FREE: 0, SubscriptionTier.PRO: 1, SubscriptionTier.PREMIUM: 2}
    if tier_order.get(request.tier, 0) <= tier_order.get(user.subscription_tier, 0):
        raise BadRequestError(
            f"Temp tier must be higher than user's current tier ({user.subscription_tier.value})"
        )
    
    from datetime import datetime, timezone, timedelta
    
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=request.days)
    
    user.temp_tier = request.tier
    user.temp_tier_expires_at = expires_at
    user.temp_tier_granted_by = admin.id
    user.temp_tier_granted_at = now
    
    await db.commit()
    
    await log_admin_action(
        db, admin,
        action="grant_temp_tier",
        target_type="user",
        target_id=user_id,
        details={
            "username": user.discord_username,
            "tier": request.tier.value,
            "days": request.days,
            "expires_at": expires_at.isoformat(),
            "reason": request.reason,
        },
    )
    
    # Send email notification to user
    if user.email:
        background_tasks.add_task(
            email_service.send_temp_tier_granted,
            user,
            request.tier.value.capitalize(),
            request.days,
            expires_at,
            request.reason
        )
    
    return {
        "status": "granted",
        "user_id": user_id,
        "temp_tier": request.tier.value,
        "expires_at": expires_at.isoformat(),
        "days": request.days,
    }


@router.post("/users/{user_id}/revoke-temp-tier")
async def revoke_temp_tier(
    user_id: int,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """Revoke a user's temporary tier early."""
    user = await UserService.get_user_by_id(db, user_id)
    if not user:
        raise NotFoundError("User not found")
    
    if not user.temp_tier:
        raise BadRequestError("User does not have a temporary tier")
    
    old_tier = user.temp_tier.value
    old_expires = user.temp_tier_expires_at.isoformat() if user.temp_tier_expires_at else None
    
    user.temp_tier = None
    user.temp_tier_expires_at = None
    user.temp_tier_granted_by = None
    user.temp_tier_granted_at = None
    
    await db.commit()
    
    await log_admin_action(
        db, admin,
        action="revoke_temp_tier",
        target_type="user",
        target_id=user_id,
        details={
            "username": user.discord_username,
            "revoked_tier": old_tier,
            "was_expiring": old_expires,
        },
    )
    
    return {
        "status": "revoked",
        "user_id": user_id,
        "revoked_tier": old_tier,
    }


@router.get("/users/{user_id}/badges")
async def get_user_badges(
    user_id: int,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """Get a user's badges."""
    user = await UserService.get_user_by_id(db, user_id)
    if not user:
        raise NotFoundError("User not found")
    
    badges = await UserService.get_badges(db, user)
    return {"user_id": user_id, "badges": badges}


@router.post("/users/{user_id}/badges")
async def add_user_badge(
    user_id: int,
    badge: str = Query(..., description="Badge to add"),
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """Add a badge to a user."""
    user = await UserService.get_user_by_id(db, user_id)
    if not user:
        raise NotFoundError("User not found")
    
    await UserService.add_badge(db, user, badge)
    badges = await UserService.get_badges(db, user)
    
    await log_admin_action(
        db, admin,
        action="add_badge",
        target_type="user",
        target_id=user_id,
        details={"username": user.discord_username, "badge": badge},
    )
    
    return {"status": "added", "user_id": user_id, "badge": badge, "badges": badges}


@router.delete("/users/{user_id}/badges")
async def remove_user_badge(
    user_id: int,
    badge: str = Query(..., description="Badge to remove"),
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """Remove a badge from a user."""
    user = await UserService.get_user_by_id(db, user_id)
    if not user:
        raise NotFoundError("User not found")
    
    await UserService.remove_badge(db, user, badge)
    badges = await UserService.get_badges(db, user)
    
    await log_admin_action(
        db, admin,
        action="remove_badge",
        target_type="user",
        target_id=user_id,
        details={"username": user.discord_username, "badge": badge},
    )
    
    return {"status": "removed", "user_id": user_id, "badge": badge, "badges": badges}


@router.post("/badges/sync-all")
async def sync_all_user_badges(
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """
    Sync automatic badges for ALL users.
    This assigns:
    - early_adopter & beta_tester: Users registered before 2025-12-20
    - addon_creator: Users with at least one public addon
    - supporter/premium: Based on subscription tier
    """
    # Get all users
    result = await db.execute(select(User))
    users = result.scalars().all()
    
    synced_count = 0
    for user in users:
        await UserService.sync_automatic_badges(db, user, commit=False)
        synced_count += 1
    
    await db.commit()
    
    await log_admin_action(
        db, admin, "sync_all_badges",
        target_type="system",
        target_id=0,
        details={"users_synced": synced_count},
    )
    
    return {"status": "success", "users_synced": synced_count}


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


@router.get("/addons/{addon_id}")
async def admin_get_addon(
    addon_id: int,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """Get addon details with all versions (admin)."""
    result = await db.execute(
        select(Addon)
        .options(selectinload(Addon.versions))
        .where(Addon.id == addon_id)
    )
    addon = result.scalar_one_or_none()
    if not addon:
        raise NotFoundError("Addon not found")
    
    # Get owner info
    owner_result = await db.execute(select(User).where(User.id == addon.owner_id))
    owner = owner_result.scalar_one_or_none()
    
    # Sort versions by release_date descending
    versions = sorted(addon.versions, key=lambda v: v.release_date, reverse=True)
    
    return {
        "addon": {
            "id": addon.id,
            "slug": addon.slug,
            "name": addon.name,
            "description": addon.description,
            "homepage": addon.homepage,
            "external": addon.external,
            "is_active": addon.is_active,
            "is_public": addon.is_public,
            "owner_id": addon.owner_id,
            "owner_username": owner.discord_username if owner else None,
            "created_at": addon.created_at,
        },
        "versions": [VersionResponse.model_validate(v) for v in versions],
    }


@router.patch("/addons/{addon_id}", response_model=AddonResponse)
async def admin_update_addon(
    addon_id: int,
    data: AddonUpdate,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """Update an addon (admin override)."""
    result = await db.execute(select(Addon).where(Addon.id == addon_id))
    addon = result.scalar_one_or_none()
    if not addon:
        raise NotFoundError("Addon not found")
    
    old_values = {
        "name": addon.name,
        "description": addon.description,
        "homepage": addon.homepage,
        "external": addon.external,
        "is_active": addon.is_active,
        "is_public": addon.is_public,
    }
    
    update_dict = data.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(addon, key, value)
    
    await db.commit()
    await db.refresh(addon)
    
    await log_admin_action(
        db, admin,
        action="update_addon",
        target_type="addon",
        target_id=addon_id,
        details={"changes": update_dict, "old_values": old_values},
    )
    
    # Get owner for response
    owner_result = await db.execute(select(User).where(User.id == addon.owner_id))
    owner = owner_result.scalar_one_or_none()
    
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
        latest_version=None,
        version_count=0,
        created_at=addon.created_at,
    )


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


@router.patch("/addons/{addon_id}/versions/{version_id}", response_model=VersionResponse)
async def admin_update_version(
    addon_id: int,
    version_id: int,
    data: VersionUpdate,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """Update a version (admin override)."""
    # Get addon
    addon_result = await db.execute(select(Addon).where(Addon.id == addon_id))
    addon = addon_result.scalar_one_or_none()
    if not addon:
        raise NotFoundError("Addon not found")
    
    # Get version
    version_result = await db.execute(
        select(Version).where(Version.id == version_id, Version.addon_id == addon_id)
    )
    version = version_result.scalar_one_or_none()
    if not version:
        raise NotFoundError("Version not found")
    
    old_values = {
        "download_url": version.download_url,
        "description": version.description,
        "changelog_url": version.changelog_url,
        "changelog_content": version.changelog_content,
        "breaking": version.breaking,
        "urgent": version.urgent,
    }
    
    update_dict = data.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(version, key, value)
    
    await db.commit()
    await db.refresh(version)
    
    await log_admin_action(
        db, admin,
        action="update_version",
        target_type="version",
        target_id=version_id,
        details={
            "addon_id": addon_id,
            "addon_name": addon.name,
            "version": version.version,
            "changes": update_dict,
            "old_values": old_values,
        },
    )
    
    return version


@router.delete("/addons/{addon_id}/versions/{version_id}")
async def admin_delete_version(
    addon_id: int,
    version_id: int,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """Delete a version (admin override)."""
    # Get addon
    addon_result = await db.execute(select(Addon).where(Addon.id == addon_id))
    addon = addon_result.scalar_one_or_none()
    if not addon:
        raise NotFoundError("Addon not found")
    
    # Get version
    version_result = await db.execute(
        select(Version).where(Version.id == version_id, Version.addon_id == addon_id)
    )
    version = version_result.scalar_one_or_none()
    if not version:
        raise NotFoundError("Version not found")
    
    version_str = version.version
    await db.delete(version)
    await db.commit()
    
    await log_admin_action(
        db, admin,
        action="delete_version",
        target_type="version",
        target_id=version_id,
        details={
            "addon_id": addon_id,
            "addon_name": addon.name,
            "version": version_str,
        },
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


@router.post("/test-email")
async def test_email(
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """Send a test email to verify SMTP configuration."""
    from app.services.email_service import email_service
    from app.services.email_templates import EmailTemplates
    from app.config import get_settings
    
    settings = get_settings()
    
    # Check configuration
    config_info = {
        "email_enabled": settings.email_enabled,
        "smtp_host": settings.smtp_host,
        "smtp_port": settings.smtp_port,
        "smtp_username": settings.smtp_username,
        "smtp_password_set": bool(settings.smtp_password),
        "admin_notification_email": settings.admin_notification_email,
    }
    
    if not settings.email_enabled:
        return {"status": "skipped", "reason": "Email is disabled", "config": config_info}
    
    if not settings.smtp_password:
        return {"status": "error", "reason": "SMTP password not set", "config": config_info}
    
    if not settings.admin_notification_email:
        return {"status": "error", "reason": "Admin notification email not set", "config": config_info}
    
    # Send test email
    subject = "[PlexAddons] Test Email"
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; padding: 20px; }}
            .box {{ background: #f5f5f5; padding: 20px; border-radius: 8px; }}
            h1 {{ color: #e9a426; }}
        </style>
    </head>
    <body>
        <div class="box">
            <h1>🎬 PlexAddons Email Test</h1>
            <p>This is a test email to verify your SMTP configuration is working correctly.</p>
            <p><strong>Sent at:</strong> {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
            <p><strong>Triggered by:</strong> {admin.discord_username}</p>
            <hr>
            <p>If you received this email, your email configuration is working! ✅</p>
        </div>
    </body>
    </html>
    """
    
    try:
        result = await email_service.send_email(
            to_email=settings.admin_notification_email,
            subject=subject,
            html_content=html_content,
            plain_content=f"PlexAddons Email Test - Sent at {datetime.utcnow()} by {admin.discord_username}"
        )
        
        if result:
            await log_admin_action(
                db, admin,
                action="test_email_sent",
                details={"to": settings.admin_notification_email},
            )
            return {"status": "sent", "to": settings.admin_notification_email, "config": config_info}
        else:
            return {"status": "failed", "reason": "send_email returned False", "config": config_info}
    except Exception as e:
        return {"status": "error", "reason": str(e), "config": config_info}


# ============== TICKET MANAGEMENT ==============

def _ticket_to_response(ticket: Ticket) -> TicketResponse:
    """Convert Ticket model to response schema"""
    return TicketResponse(
        id=ticket.id,
        user_id=ticket.user_id,
        user_username=ticket.user.discord_username if ticket.user else None,
        subject=ticket.subject,
        category=ticket.category,
        priority=ticket.priority,
        status=ticket.status,
        assigned_admin_id=ticket.assigned_admin_id,
        assigned_admin_username=ticket.assigned_admin.discord_username if ticket.assigned_admin else None,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
        resolved_at=ticket.resolved_at,
        closed_at=ticket.closed_at,
    )


def _message_to_response(message) -> TicketMessageResponse:
    """Convert TicketMessage model to response schema"""
    return TicketMessageResponse(
        id=message.id,
        ticket_id=message.ticket_id,
        author_id=message.author_id,
        author_username=message.author.discord_username if message.author else "System",
        content=message.content,
        is_staff_reply=message.is_staff_reply,
        is_system_message=message.is_system_message,
        created_at=message.created_at,
        edited_at=message.edited_at,
        attachments=[
            TicketAttachmentResponse(
                id=att.id,
                original_filename=att.original_filename,
                file_size=att.file_size,
                compressed_size=att.compressed_size,
                mime_type=att.mime_type,
                is_compressed=att.is_compressed,
                created_at=att.created_at,
            )
            for att in (message.attachments or [])
        ],
    )


def _ticket_to_detail_response(ticket: Ticket) -> TicketDetailResponse:
    """Convert Ticket model with messages to detail response"""
    return TicketDetailResponse(
        id=ticket.id,
        user_id=ticket.user_id,
        user_username=ticket.user.discord_username if ticket.user else None,
        subject=ticket.subject,
        category=ticket.category,
        priority=ticket.priority,
        status=ticket.status,
        assigned_admin_id=ticket.assigned_admin_id,
        assigned_admin_username=ticket.assigned_admin.discord_username if ticket.assigned_admin else None,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
        resolved_at=ticket.resolved_at,
        closed_at=ticket.closed_at,
        messages=[_message_to_response(msg) for msg in (ticket.messages or [])],
    )


@router.get("/tickets/stats", response_model=TicketStatsResponse)
async def get_ticket_stats(
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """Get ticket statistics for admin dashboard."""
    stats = await ticket_service.get_ticket_stats(db)
    return TicketStatsResponse(**stats)


@router.get("/tickets", response_model=TicketListResponse)
async def list_all_tickets(
    status: Optional[TicketStatus] = Query(None, description="Filter by status"),
    priority: Optional[TicketPriority] = Query(None, description="Filter by priority"),
    category: Optional[TicketCategory] = Query(None, description="Filter by category"),
    assigned_to_me: bool = Query(False, description="Only show tickets assigned to me"),
    unassigned: bool = Query(False, description="Only show unassigned tickets"),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """List all tickets with filters (admin only)."""
    offset = (page - 1) * per_page
    
    # Handle assignment filters
    assigned_admin_id = None
    if assigned_to_me:
        assigned_admin_id = admin.id
    
    tickets = await ticket_service.get_all_tickets(
        db=db,
        status=status,
        priority=priority,
        category=category,
        assigned_admin_id=assigned_admin_id,
        limit=per_page,
        offset=offset,
    )
    
    # Filter unassigned if requested
    if unassigned:
        tickets = [t for t in tickets if t.assigned_admin_id is None]
    
    # Get total count (simplified)
    all_tickets = await ticket_service.get_all_tickets(
        db=db,
        status=status,
        priority=priority,
        category=category,
        assigned_admin_id=assigned_admin_id,
        limit=1000,
        offset=0,
    )
    total = len(all_tickets)
    
    return TicketListResponse(
        tickets=[_ticket_to_response(t) for t in tickets],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/tickets/{ticket_id}", response_model=TicketDetailResponse)
async def admin_get_ticket(
    ticket_id: int,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """Get a specific ticket with all messages (admin)."""
    ticket = await ticket_service.get_ticket_by_id(db, ticket_id, include_messages=True)
    
    if not ticket:
        raise NotFoundError("Ticket not found")
    
    return _ticket_to_detail_response(ticket)


@router.post("/tickets/{ticket_id}/messages", response_model=TicketMessageResponse, status_code=201)
async def admin_add_message(
    ticket_id: int,
    data: TicketMessageCreate,
    background_tasks: BackgroundTasks,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """Add a staff reply to a ticket (admin)."""
    ticket = await ticket_service.get_ticket_by_id(db, ticket_id, include_messages=False)
    
    if not ticket:
        raise NotFoundError("Ticket not found")
    
    message = await ticket_service.add_message(
        db=db,
        ticket=ticket,
        author=admin,
        content=data.content,
        is_staff=True,
    )
    
    # Reload message with relationships
    message = await ticket_service.get_message_by_id(db, message.id)
    
    # Log admin action
    await log_admin_action(
        db, admin,
        action="ticket_reply",
        target_type="ticket",
        target_id=ticket_id,
        details={"message_id": message.id},
    )
    
    # Send email notification to user about staff reply
    # Get ticket with user loaded
    ticket_with_user = await ticket_service.get_ticket_by_id(db, ticket_id, include_messages=False)
    if ticket_with_user and ticket_with_user.user:
        background_tasks.add_task(
            email_service.send_user_ticket_reply,
            ticket_with_user.user,
            ticket_with_user.id,
            ticket_with_user.subject,
            admin.discord_username or "Support Staff",
            data.content[:500]  # Preview first 500 chars
        )
    
    return _message_to_response(message)


@router.patch("/tickets/{ticket_id}/status", response_model=TicketResponse)
async def update_ticket_status(
    ticket_id: int,
    data: TicketStatusUpdate,
    background_tasks: BackgroundTasks,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """Update ticket status (admin)."""
    ticket = await ticket_service.get_ticket_by_id(db, ticket_id, include_messages=False)
    
    if not ticket:
        raise NotFoundError("Ticket not found")
    
    old_status = ticket.status
    ticket = await ticket_service.update_ticket_status(
        db=db,
        ticket=ticket,
        new_status=data.status,
        admin=admin,
    )
    
    await log_admin_action(
        db, admin,
        action="ticket_status_change",
        target_type="ticket",
        target_id=ticket_id,
        details={"old_status": old_status.value, "new_status": data.status.value},
    )
    
    # Send email notification to user about status change
    if ticket.user:
        background_tasks.add_task(
            email_service.send_ticket_status_changed,
            ticket.user,
            ticket.id,
            ticket.subject,
            old_status.value,
            data.status.value
        )
    
    return _ticket_to_response(ticket)


@router.patch("/tickets/{ticket_id}/priority", response_model=TicketResponse)
async def update_ticket_priority(
    ticket_id: int,
    data: TicketPriorityUpdate,
    background_tasks: BackgroundTasks,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """Update ticket priority (admin)."""
    ticket = await ticket_service.get_ticket_by_id(db, ticket_id, include_messages=False)
    
    if not ticket:
        raise NotFoundError("Ticket not found")
    
    old_priority = ticket.priority
    ticket = await ticket_service.update_ticket_priority(
        db=db,
        ticket=ticket,
        new_priority=data.priority,
        admin=admin,
    )
    
    await log_admin_action(
        db, admin,
        action="ticket_priority_change",
        target_type="ticket",
        target_id=ticket_id,
        details={"old_priority": old_priority.value, "new_priority": data.priority.value},
    )
    
    # If escalated to urgent, send notification
    if data.priority == TicketPriority.URGENT and old_priority != TicketPriority.URGENT:
        async def send_urgent_notification():
            await discord_service.notify_urgent_ticket(
                ticket_id=ticket.id,
                user_name=ticket.user.discord_username if ticket.user else "Unknown",
                subject=ticket.subject,
                reason=f"Priority escalated by {admin.discord_username}",
            )
        background_tasks.add_task(send_urgent_notification)
    
    return _ticket_to_response(ticket)


@router.patch("/tickets/{ticket_id}/assign", response_model=TicketResponse)
async def assign_ticket(
    ticket_id: int,
    data: TicketAssignUpdate,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """Assign ticket to an admin."""
    ticket = await ticket_service.get_ticket_by_id(db, ticket_id, include_messages=False)
    
    if not ticket:
        raise NotFoundError("Ticket not found")
    
    # Verify target admin exists and is admin
    target_admin = await UserService.get_user_by_id(db, data.admin_id)
    if not target_admin or not target_admin.is_admin:
        raise BadRequestError("Target user is not an admin")
    
    old_assigned = ticket.assigned_admin_id
    ticket = await ticket_service.assign_ticket(
        db=db,
        ticket=ticket,
        admin=target_admin,
    )
    
    await log_admin_action(
        db, admin,
        action="ticket_assign",
        target_type="ticket",
        target_id=ticket_id,
        details={
            "old_assigned": old_assigned,
            "new_assigned": data.admin_id,
            "assigned_by": admin.id,
        },
    )
    
    return _ticket_to_response(ticket)


@router.post("/tickets/{ticket_id}/assign-to-me", response_model=TicketResponse)
async def assign_ticket_to_me(
    ticket_id: int,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """Assign ticket to the current admin."""
    ticket = await ticket_service.get_ticket_by_id(db, ticket_id, include_messages=False)
    
    if not ticket:
        raise NotFoundError("Ticket not found")
    
    old_assigned = ticket.assigned_admin_id
    ticket = await ticket_service.assign_ticket(
        db=db,
        ticket=ticket,
        admin=admin,
    )
    
    await log_admin_action(
        db, admin,
        action="ticket_self_assign",
        target_type="ticket",
        target_id=ticket_id,
        details={"old_assigned": old_assigned},
    )
    
    return _ticket_to_response(ticket)


# ============== CANNED RESPONSES ==============

@router.get("/canned-responses", response_model=CannedResponseListResponse)
async def list_canned_responses(
    category: Optional[TicketCategory] = Query(None, description="Filter by category"),
    include_inactive: bool = Query(False, description="Include inactive responses"),
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """List all canned responses."""
    responses = await ticket_service.get_canned_responses(
        db=db,
        category=category,
        active_only=not include_inactive,
    )
    
    # Enrich with creator usernames
    enriched = []
    for r in responses:
        creator_username = None
        if r.created_by:
            creator = await UserService.get_user_by_id(db, r.created_by)
            creator_username = creator.discord_username if creator else None
        
        enriched.append(CannedResponseResponse(
            id=r.id,
            title=r.title,
            content=r.content,
            category=r.category,
            created_by=r.created_by,
            creator_username=creator_username,
            usage_count=r.usage_count,
            is_active=r.is_active,
            created_at=r.created_at,
            updated_at=r.updated_at,
        ))
    
    return CannedResponseListResponse(
        responses=enriched,
        total=len(enriched),
    )


@router.post("/canned-responses", response_model=CannedResponseResponse, status_code=201)
async def create_canned_response(
    data: CannedResponseCreate,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """Create a new canned response."""
    canned = await ticket_service.create_canned_response(
        db=db,
        title=data.title,
        content=data.content,
        admin=admin,
        category=data.category,
    )
    
    await log_admin_action(
        db, admin,
        action="create_canned_response",
        target_type="canned_response",
        target_id=canned.id,
        details={"title": data.title},
    )
    
    return CannedResponseResponse(
        id=canned.id,
        title=canned.title,
        content=canned.content,
        category=canned.category,
        created_by=canned.created_by,
        creator_username=admin.discord_username,
        usage_count=canned.usage_count,
        is_active=canned.is_active,
        created_at=canned.created_at,
        updated_at=canned.updated_at,
    )


@router.patch("/canned-responses/{canned_id}", response_model=CannedResponseResponse)
async def update_canned_response(
    canned_id: int,
    data: CannedResponseUpdate,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """Update a canned response."""
    result = await db.execute(
        select(CannedResponse).where(CannedResponse.id == canned_id)
    )
    canned = result.scalar_one_or_none()
    
    if not canned:
        raise NotFoundError("Canned response not found")
    
    canned = await ticket_service.update_canned_response(
        db=db,
        canned=canned,
        title=data.title,
        content=data.content,
        category=data.category,
        is_active=data.is_active,
    )
    
    await log_admin_action(
        db, admin,
        action="update_canned_response",
        target_type="canned_response",
        target_id=canned_id,
        details=data.model_dump(exclude_unset=True),
    )
    
    # Get creator username
    creator_username = None
    if canned.created_by:
        creator = await UserService.get_user_by_id(db, canned.created_by)
        creator_username = creator.discord_username if creator else None
    
    return CannedResponseResponse(
        id=canned.id,
        title=canned.title,
        content=canned.content,
        category=canned.category,
        created_by=canned.created_by,
        creator_username=creator_username,
        usage_count=canned.usage_count,
        is_active=canned.is_active,
        created_at=canned.created_at,
        updated_at=canned.updated_at,
    )


@router.delete("/canned-responses/{canned_id}")
async def delete_canned_response(
    canned_id: int,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """Delete a canned response."""
    result = await db.execute(
        select(CannedResponse).where(CannedResponse.id == canned_id)
    )
    canned = result.scalar_one_or_none()
    
    if not canned:
        raise NotFoundError("Canned response not found")
    
    title = canned.title
    await ticket_service.delete_canned_response(db, canned)
    
    await log_admin_action(
        db, admin,
        action="delete_canned_response",
        target_type="canned_response",
        target_id=canned_id,
        details={"title": title},
    )
    
    return {"status": "deleted"}


@router.get("/canned-responses/{canned_id}/use", response_model=CannedResponseResponse)
async def use_canned_response(
    canned_id: int,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """Get a canned response and increment its usage count."""
    canned = await ticket_service.use_canned_response(db, canned_id)
    
    if not canned:
        raise NotFoundError("Canned response not found")
    
    # Get creator username
    creator_username = None
    if canned.created_by:
        creator = await UserService.get_user_by_id(db, canned.created_by)
        creator_username = creator.discord_username if creator else None
    
    return CannedResponseResponse(
        id=canned.id,
        title=canned.title,
        content=canned.content,
        category=canned.category,
        created_by=canned.created_by,
        creator_username=creator_username,
        usage_count=canned.usage_count,
        is_active=canned.is_active,
        created_at=canned.created_at,
        updated_at=canned.updated_at,
    )


# ============== TICKET ATTACHMENT MANAGEMENT ==============

@router.post("/tickets/compress-old-attachments")
async def compress_old_attachments(
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """Manually trigger compression of old attachments."""
    compressed_count = await ticket_service.compress_old_attachments(db)
    
    await log_admin_action(
        db, admin,
        action="compress_attachments",
        details={"compressed_count": compressed_count},
    )
    
    return {"status": "completed", "compressed_count": compressed_count}


@router.post("/tickets/cleanup-old-attachments")
async def cleanup_old_attachments(
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """Manually trigger deletion of old attachments."""
    deleted_count = await ticket_service.delete_old_attachments(db)
    
    # Clean up empty directories
    removed_dirs = await ticket_service.cleanup_empty_directories()
    
    await log_admin_action(
        db, admin,
        action="cleanup_attachments",
        details={"deleted_count": deleted_count, "removed_dirs": removed_dirs},
    )
    
    return {"status": "completed", "deleted_count": deleted_count, "removed_dirs": removed_dirs}


@router.post("/test-discord-dm")
async def test_discord_dm(
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """Send a test Discord DM to verify bot configuration."""
    from app.config import get_settings
    
    settings = get_settings()
    
    config_info = {
        "discord_bot_token_set": bool(settings.discord_bot_token),
        "discord_bot_dm_enabled": settings.discord_bot_dm_enabled,
        "discord_admin_dm_user_id": settings.discord_admin_dm_user_id,
    }
    
    if not discord_service.is_configured:
        return {
            "status": "not_configured",
            "reason": "Discord DM notifications are not fully configured",
            "config": config_info,
        }
    
    try:
        result = await discord_service.send_admin_dm(
            content=f"🧪 **Test DM from PlexAddons**\n\nTriggered by: {admin.discord_username}\nTime: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}\n\nIf you received this, Discord DM notifications are working! ✅"
        )
        
        if result:
            await log_admin_action(
                db, admin,
                action="test_discord_dm",
                details={"success": True},
            )
            return {"status": "sent", "config": config_info}
        else:
            return {"status": "failed", "reason": "send_admin_dm returned False", "config": config_info}
    except Exception as e:
        return {"status": "error", "reason": str(e), "config": config_info}
