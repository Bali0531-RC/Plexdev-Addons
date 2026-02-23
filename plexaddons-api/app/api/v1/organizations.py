"""Organization endpoints for team addon management (Premium feature)."""

import hashlib
import secrets
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from typing import List, Optional
from app.database import get_db
from app.models import (
    Organization, OrganizationMember, User, Addon, Version,
    OrganizationRole, SubscriptionTier, OrgAuditLog, OrgApiKey,
    AddonUsageStats,
)
from app.schemas import (
    OrganizationCreate, OrganizationUpdate, OrganizationResponse,
    OrganizationDetailResponse, OrganizationListResponse,
    OrganizationMemberResponse, InviteMemberRequest, UpdateMemberRoleRequest,
    UpdateMemberPermissionsRequest, OrgAuditLogResponse, OrgAuditLogListResponse,
    OrgApiKeyCreate, OrgApiKeyResponse, OrgApiKeyCreateResponse, OrgApiKeyListResponse,
    OrgAnalyticsSummary, OrgPublicPageResponse, AddonResponse,
)
from app.api.deps import get_current_user, require_premium
from app.utils import slugify
from app.config import get_settings

settings = get_settings()

router = APIRouter(prefix="/organizations", tags=["Organizations"])


def get_effective_tier(user: User) -> SubscriptionTier:
    """Get effective tier including temp tier."""
    from datetime import datetime, timezone
    if user.temp_tier and user.temp_tier_expires_at:
        if user.temp_tier_expires_at > datetime.now(timezone.utc):
            return user.temp_tier
    return user.subscription_tier


async def calculate_org_storage(db: AsyncSession, org_id: int) -> int:
    """Calculate total storage used by organization addons."""
    result = await db.execute(
        select(func.sum(Version.storage_size_bytes))
        .join(Addon, Version.addon_id == Addon.id)
        .where(Addon.organization_id == org_id)
    )
    return result.scalar() or 0


async def check_org_storage_quota(db: AsyncSession, org: Organization, owner: User, additional_bytes: int = 0) -> bool:
    """Check if organization has storage quota available."""
    effective_tier = get_effective_tier(owner)
    
    quota_map = {
        SubscriptionTier.FREE: settings.storage_quota_free,
        SubscriptionTier.PRO: settings.storage_quota_pro,
        SubscriptionTier.PREMIUM: settings.storage_quota_premium,
    }
    quota = quota_map.get(effective_tier, settings.storage_quota_free)
    
    current_usage = await calculate_org_storage(db, org.id)
    return (current_usage + additional_bytes) <= quota


async def log_org_audit(
    db: AsyncSession, org_id: int, user_id: int, action: str,
    details: Optional[dict] = None, ip_address: Optional[str] = None,
):
    """Record an audit log entry for an organization action."""
    entry = OrgAuditLog(
        organization_id=org_id,
        user_id=user_id,
        action=action,
        details=details,
        ip_address=ip_address,
    )
    db.add(entry)


@router.post("", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
async def create_organization(
    data: OrganizationCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_premium),
):
    """
    Create a new organization.
    Requires Premium subscription.
    """
    # Check if user already owns an organization
    existing = await db.execute(
        select(Organization).where(Organization.owner_id == current_user.id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You already own an organization"
        )
    
    # Generate slug
    slug = slugify(data.name)
    
    # Check slug uniqueness
    slug_check = await db.execute(
        select(Organization).where(Organization.slug == slug)
    )
    if slug_check.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization name is already taken"
        )
    
    # Create organization
    org = Organization(
        owner_id=current_user.id,
        name=data.name,
        slug=slug,
        description=data.description,
    )
    db.add(org)
    await db.flush()
    
    # Add owner as member with OWNER role
    owner_member = OrganizationMember(
        organization_id=org.id,
        user_id=current_user.id,
        role=OrganizationRole.OWNER,
    )
    db.add(owner_member)
    await db.flush()
    
    await log_org_audit(db, org.id, current_user.id, "org.created",
                        {"name": org.name}, request.client.host if request.client else None)
    await db.commit()
    await db.refresh(org)
    
    return OrganizationResponse(
        id=org.id,
        name=org.name,
        slug=org.slug,
        description=org.description,
        avatar_url=org.avatar_url,
        banner_url=org.banner_url,
        owner_id=org.owner_id,
        created_at=org.created_at,
        updated_at=org.updated_at,
        member_count=1,
        addon_count=0,
        storage_used_bytes=0,
    )


@router.get("", response_model=OrganizationListResponse)
async def list_my_organizations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List organizations the current user is a member of.
    """
    result = await db.execute(
        select(Organization)
        .join(OrganizationMember, Organization.id == OrganizationMember.organization_id)
        .where(OrganizationMember.user_id == current_user.id)
    )
    orgs = result.scalars().all()
    
    # Enrich with counts
    response_orgs = []
    for org in orgs:
        member_count = await db.execute(
            select(func.count(OrganizationMember.id))
            .where(OrganizationMember.organization_id == org.id)
        )
        addon_count = await db.execute(
            select(func.count(Addon.id))
            .where(Addon.organization_id == org.id)
        )
        storage_used = await calculate_org_storage(db, org.id)
        
        response_orgs.append(OrganizationResponse(
            id=org.id,
            name=org.name,
            slug=org.slug,
            description=org.description,
            avatar_url=org.avatar_url,
            banner_url=org.banner_url,
            owner_id=org.owner_id,
            created_at=org.created_at,
            updated_at=org.updated_at,
            member_count=member_count.scalar() or 0,
            addon_count=addon_count.scalar() or 0,
            storage_used_bytes=storage_used,
        ))
    
    return OrganizationListResponse(organizations=response_orgs, total=len(response_orgs))


@router.get("/{org_slug}", response_model=OrganizationDetailResponse)
async def get_organization(
    org_slug: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get organization details.
    Must be a member of the organization.
    """
    result = await db.execute(
        select(Organization).where(Organization.slug == org_slug)
    )
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    
    # Check membership
    membership = await db.execute(
        select(OrganizationMember)
        .where(OrganizationMember.organization_id == org.id)
        .where(OrganizationMember.user_id == current_user.id)
    )
    if not membership.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this organization")
    
    # Get members with user info
    members_result = await db.execute(
        select(OrganizationMember, User)
        .join(User, OrganizationMember.user_id == User.id)
        .where(OrganizationMember.organization_id == org.id)
    )
    members = []
    for member, user in members_result.all():
        members.append(OrganizationMemberResponse(
            id=member.id,
            user_id=member.user_id,
            role=member.role,
            permissions=member.permissions,
            joined_at=member.joined_at,
            discord_username=user.discord_username,
            discord_avatar=user.discord_avatar,
        ))
    
    # Get counts
    addon_count = await db.execute(
        select(func.count(Addon.id)).where(Addon.organization_id == org.id)
    )
    storage_used = await calculate_org_storage(db, org.id)
    
    # Get owner username
    owner_result = await db.execute(select(User).where(User.id == org.owner_id))
    owner = owner_result.scalar_one_or_none()
    
    return OrganizationDetailResponse(
        id=org.id,
        name=org.name,
        slug=org.slug,
        description=org.description,
        avatar_url=org.avatar_url,
        banner_url=org.banner_url,
        owner_id=org.owner_id,
        created_at=org.created_at,
        updated_at=org.updated_at,
        member_count=len(members),
        addon_count=addon_count.scalar() or 0,
        storage_used_bytes=storage_used,
        members=members,
        owner_username=owner.discord_username if owner else None,
    )


@router.patch("/{org_slug}", response_model=OrganizationResponse)
async def update_organization(
    org_slug: str,
    data: OrganizationUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update organization details.
    Must be owner or admin.
    """
    result = await db.execute(
        select(Organization).where(Organization.slug == org_slug)
    )
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    
    # Check permission (owner or admin)
    membership = await db.execute(
        select(OrganizationMember)
        .where(OrganizationMember.organization_id == org.id)
        .where(OrganizationMember.user_id == current_user.id)
        .where(OrganizationMember.role.in_([OrganizationRole.OWNER, OrganizationRole.ADMIN]))
    )
    if not membership.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update this organization")
    
    # Update fields
    changes = {}
    if data.name is not None:
        changes["name"] = data.name
        org.name = data.name
    if data.description is not None:
        changes["description"] = data.description
        org.description = data.description
    if data.avatar_url is not None:
        org.avatar_url = data.avatar_url
    if data.banner_url is not None:
        org.banner_url = data.banner_url
    
    await log_org_audit(db, org.id, current_user.id, "settings.updated",
                        changes or None, request.client.host if request.client else None)
    await db.commit()
    await db.refresh(org)
    
    # Get counts
    member_count = await db.execute(
        select(func.count(OrganizationMember.id)).where(OrganizationMember.organization_id == org.id)
    )
    addon_count = await db.execute(
        select(func.count(Addon.id)).where(Addon.organization_id == org.id)
    )
    storage_used = await calculate_org_storage(db, org.id)
    
    return OrganizationResponse(
        id=org.id,
        name=org.name,
        slug=org.slug,
        description=org.description,
        avatar_url=org.avatar_url,
        banner_url=org.banner_url,
        owner_id=org.owner_id,
        created_at=org.created_at,
        updated_at=org.updated_at,
        member_count=member_count.scalar() or 0,
        addon_count=addon_count.scalar() or 0,
        storage_used_bytes=storage_used,
    )


@router.delete("/{org_slug}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_organization(
    org_slug: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete an organization.
    Must be the owner. All addons will be transferred to owner's personal account.
    """
    result = await db.execute(
        select(Organization).where(Organization.slug == org_slug)
    )
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    
    if org.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the owner can delete the organization")
    
    # Transfer all org addons to owner's personal account
    addons_result = await db.execute(
        select(Addon).where(Addon.organization_id == org.id)
    )
    for addon in addons_result.scalars().all():
        addon.organization_id = None
        addon.owner_id = current_user.id
    
    # Audit log written before deletion (cascades will remove it, but it's good practice)
    await log_org_audit(db, org.id, current_user.id, "org.deleted",
                        {"name": org.name}, request.client.host if request.client else None)
    
    # Delete organization (cascades to members)
    await db.delete(org)
    await db.commit()


@router.post("/{org_slug}/members", response_model=OrganizationMemberResponse)
async def invite_member(
    org_slug: str,
    data: InviteMemberRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Invite a user to the organization by Discord username.
    Must be owner or admin.
    """
    result = await db.execute(
        select(Organization).where(Organization.slug == org_slug)
    )
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    
    # Check permission (owner or admin)
    membership_result = await db.execute(
        select(OrganizationMember)
        .where(OrganizationMember.organization_id == org.id)
        .where(OrganizationMember.user_id == current_user.id)
        .where(OrganizationMember.role.in_([OrganizationRole.OWNER, OrganizationRole.ADMIN]))
    )
    inviter_membership = membership_result.scalar_one_or_none()
    if not inviter_membership:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to invite members")

    # Can't grant OWNER role
    if data.role == OrganizationRole.OWNER:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot grant owner role")

    # Admins can only invite as MEMBER; only owner can grant ADMIN role
    if data.role == OrganizationRole.ADMIN and inviter_membership.role != OrganizationRole.OWNER:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the owner can grant admin role")
    
    # Find user by Discord username
    user_result = await db.execute(
        select(User).where(User.discord_username == data.discord_username)
    )
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    # Check if already a member
    existing = await db.execute(
        select(OrganizationMember)
        .where(OrganizationMember.organization_id == org.id)
        .where(OrganizationMember.user_id == user.id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User is already a member")
    
    # Add member
    member = OrganizationMember(
        organization_id=org.id,
        user_id=user.id,
        role=data.role,
        invited_by_id=current_user.id,
    )
    db.add(member)
    await db.flush()
    
    await log_org_audit(db, org.id, current_user.id, "member.invited",
                        {"user": user.discord_username, "role": data.role.value},
                        request.client.host if request.client else None)
    await db.commit()
    await db.refresh(member)
    
    return OrganizationMemberResponse(
        id=member.id,
        user_id=member.user_id,
        role=member.role,
        permissions=member.permissions,
        joined_at=member.joined_at,
        discord_username=user.discord_username,
        discord_avatar=user.discord_avatar,
    )


@router.patch("/{org_slug}/members/{user_id}", response_model=OrganizationMemberResponse)
async def update_member_role(
    org_slug: str,
    user_id: int,
    data: UpdateMemberRoleRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update a member's role.
    Only owner can change roles.
    """
    result = await db.execute(
        select(Organization).where(Organization.slug == org_slug)
    )
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    
    # Only owner can change roles
    if org.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the owner can change member roles")
    
    # Can't change owner role
    if data.role == OrganizationRole.OWNER:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot grant owner role")
    
    # Find member
    member_result = await db.execute(
        select(OrganizationMember, User)
        .join(User, OrganizationMember.user_id == User.id)
        .where(OrganizationMember.organization_id == org.id)
        .where(OrganizationMember.user_id == user_id)
    )
    row = member_result.first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")
    
    member, user = row
    
    # Can't change owner's role
    if member.role == OrganizationRole.OWNER:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot change owner's role")
    
    old_role = member.role.value
    member.role = data.role
    await log_org_audit(db, org.id, current_user.id, "member.role_updated",
                        {"user_id": user_id, "old_role": old_role, "new_role": data.role.value},
                        request.client.host if request.client else None)
    await db.commit()
    await db.refresh(member)
    
    return OrganizationMemberResponse(
        id=member.id,
        user_id=member.user_id,
        role=member.role,
        permissions=member.permissions,
        joined_at=member.joined_at,
        discord_username=user.discord_username,
        discord_avatar=user.discord_avatar,
    )


@router.delete("/{org_slug}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    org_slug: str,
    user_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Remove a member from the organization.
    Owner/admin can remove members. Members can remove themselves.
    """
    result = await db.execute(
        select(Organization).where(Organization.slug == org_slug)
    )
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    
    # Check if user is trying to remove themselves or has permission
    is_self_removal = user_id == current_user.id
    
    if not is_self_removal:
        # Check permission (owner or admin)
        membership = await db.execute(
            select(OrganizationMember)
            .where(OrganizationMember.organization_id == org.id)
            .where(OrganizationMember.user_id == current_user.id)
            .where(OrganizationMember.role.in_([OrganizationRole.OWNER, OrganizationRole.ADMIN]))
        )
        if not membership.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to remove members")
    
    # Find member to remove
    member_result = await db.execute(
        select(OrganizationMember)
        .where(OrganizationMember.organization_id == org.id)
        .where(OrganizationMember.user_id == user_id)
    )
    member = member_result.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")
    
    # Can't remove owner
    if member.role == OrganizationRole.OWNER:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot remove the owner")
    
    action = "member.left" if is_self_removal else "member.removed"
    await log_org_audit(db, org.id, current_user.id, action,
                        {"user_id": user_id},
                        request.client.host if request.client else None)
    await db.delete(member)
    await db.commit()


# =====================================================================
# Member Permissions
# =====================================================================

@router.put("/{org_slug}/members/{user_id}/permissions", response_model=OrganizationMemberResponse)
async def update_member_permissions(
    org_slug: str,
    user_id: int,
    data: UpdateMemberPermissionsRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update granular permissions for a member. Owner or Admin only."""
    result = await db.execute(select(Organization).where(Organization.slug == org_slug))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")

    # Check permission (owner or admin)
    caller = await db.execute(
        select(OrganizationMember)
        .where(OrganizationMember.organization_id == org.id,
               OrganizationMember.user_id == current_user.id,
               OrganizationMember.role.in_([OrganizationRole.OWNER, OrganizationRole.ADMIN]))
    )
    if not caller.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    row = await db.execute(
        select(OrganizationMember, User)
        .join(User, OrganizationMember.user_id == User.id)
        .where(OrganizationMember.organization_id == org.id,
               OrganizationMember.user_id == user_id)
    )
    pair = row.first()
    if not pair:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")
    member, user = pair

    if member.role == OrganizationRole.OWNER:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot modify owner permissions")

    member.permissions = data.permissions
    await log_org_audit(db, org.id, current_user.id, "member.permissions_updated",
                        {"user_id": user_id, "permissions": data.permissions},
                        request.client.host if request.client else None)
    await db.commit()
    await db.refresh(member)

    return OrganizationMemberResponse(
        id=member.id, user_id=member.user_id, role=member.role,
        permissions=member.permissions, joined_at=member.joined_at,
        discord_username=user.discord_username, discord_avatar=user.discord_avatar,
    )


# =====================================================================
# Audit Logs
# =====================================================================

@router.get("/{org_slug}/audit-logs", response_model=OrgAuditLogListResponse)
async def list_audit_logs(
    org_slug: str,
    page: int = 1,
    per_page: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List audit logs for the organization. Owner or Admin only."""
    result = await db.execute(select(Organization).where(Organization.slug == org_slug))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")

    caller = await db.execute(
        select(OrganizationMember)
        .where(OrganizationMember.organization_id == org.id,
               OrganizationMember.user_id == current_user.id,
               OrganizationMember.role.in_([OrganizationRole.OWNER, OrganizationRole.ADMIN]))
    )
    if not caller.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    total_q = await db.execute(
        select(func.count(OrgAuditLog.id)).where(OrgAuditLog.organization_id == org.id)
    )
    total = total_q.scalar() or 0

    offset = (max(page, 1) - 1) * per_page
    rows = await db.execute(
        select(OrgAuditLog, User)
        .outerjoin(User, OrgAuditLog.user_id == User.id)
        .where(OrgAuditLog.organization_id == org.id)
        .order_by(OrgAuditLog.created_at.desc())
        .offset(offset)
        .limit(min(per_page, 100))
    )

    logs = []
    for log, user in rows.all():
        logs.append(OrgAuditLogResponse(
            id=log.id, action=log.action, details=log.details,
            user_id=log.user_id,
            username=user.discord_username if user else None,
            ip_address=log.ip_address, created_at=log.created_at,
        ))

    return OrgAuditLogListResponse(logs=logs, total=total)


# =====================================================================
# Organization API Keys
# =====================================================================

@router.post("/{org_slug}/api-keys", response_model=OrgApiKeyCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_org_api_key(
    org_slug: str,
    data: OrgApiKeyCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new organization API key. Owner or Admin only."""
    result = await db.execute(select(Organization).where(Organization.slug == org_slug))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")

    caller = await db.execute(
        select(OrganizationMember)
        .where(OrganizationMember.organization_id == org.id,
               OrganizationMember.user_id == current_user.id,
               OrganizationMember.role.in_([OrganizationRole.OWNER, OrganizationRole.ADMIN]))
    )
    if not caller.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    # Limit 10 keys per org
    count_q = await db.execute(
        select(func.count(OrgApiKey.id)).where(OrgApiKey.organization_id == org.id)
    )
    if (count_q.scalar() or 0) >= 10:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Maximum 10 API keys per organization")

    raw_key = secrets.token_urlsafe(32)
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    prefix = raw_key[:8]

    api_key = OrgApiKey(
        organization_id=org.id,
        created_by_id=current_user.id,
        name=data.name,
        key_hash=key_hash,
        key_prefix=prefix,
        scopes=data.scopes,
        expires_at=data.expires_at,
    )
    db.add(api_key)
    await db.flush()

    await log_org_audit(db, org.id, current_user.id, "api_key.created",
                        {"name": data.name, "key_prefix": prefix},
                        request.client.host if request.client else None)
    await db.commit()
    await db.refresh(api_key)

    return OrgApiKeyCreateResponse(
        id=api_key.id, name=api_key.name, key_prefix=api_key.key_prefix,
        scopes=api_key.scopes or [], is_active=api_key.is_active,
        last_used_at=api_key.last_used_at, expires_at=api_key.expires_at,
        created_by_id=api_key.created_by_id, created_at=api_key.created_at,
        key=raw_key,
    )


@router.get("/{org_slug}/api-keys", response_model=OrgApiKeyListResponse)
async def list_org_api_keys(
    org_slug: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List organization API keys. Owner or Admin only."""
    result = await db.execute(select(Organization).where(Organization.slug == org_slug))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")

    caller = await db.execute(
        select(OrganizationMember)
        .where(OrganizationMember.organization_id == org.id,
               OrganizationMember.user_id == current_user.id,
               OrganizationMember.role.in_([OrganizationRole.OWNER, OrganizationRole.ADMIN]))
    )
    if not caller.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    rows = await db.execute(
        select(OrgApiKey, User)
        .outerjoin(User, OrgApiKey.created_by_id == User.id)
        .where(OrgApiKey.organization_id == org.id)
        .order_by(OrgApiKey.created_at.desc())
    )

    keys = []
    for key, creator in rows.all():
        keys.append(OrgApiKeyResponse(
            id=key.id, name=key.name, key_prefix=key.key_prefix,
            scopes=key.scopes or [], is_active=key.is_active,
            last_used_at=key.last_used_at, expires_at=key.expires_at,
            created_by_id=key.created_by_id,
            created_by_username=creator.discord_username if creator else None,
            created_at=key.created_at,
        ))

    return OrgApiKeyListResponse(api_keys=keys, total=len(keys))


@router.delete("/{org_slug}/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_org_api_key(
    org_slug: str,
    key_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete an organization API key. Owner or Admin only."""
    result = await db.execute(select(Organization).where(Organization.slug == org_slug))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")

    caller = await db.execute(
        select(OrganizationMember)
        .where(OrganizationMember.organization_id == org.id,
               OrganizationMember.user_id == current_user.id,
               OrganizationMember.role.in_([OrganizationRole.OWNER, OrganizationRole.ADMIN]))
    )
    if not caller.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    key_result = await db.execute(
        select(OrgApiKey).where(OrgApiKey.id == key_id, OrgApiKey.organization_id == org.id)
    )
    key = key_result.scalar_one_or_none()
    if not key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")

    await log_org_audit(db, org.id, current_user.id, "api_key.deleted",
                        {"name": key.name, "key_prefix": key.key_prefix},
                        request.client.host if request.client else None)
    await db.delete(key)
    await db.commit()


# =====================================================================
# Organization Analytics
# =====================================================================

@router.get("/{org_slug}/analytics", response_model=OrgAnalyticsSummary)
async def get_org_analytics(
    org_slug: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get aggregated analytics for all addons in the organization."""
    result = await db.execute(select(Organization).where(Organization.slug == org_slug))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")

    # Check membership with view_analytics permission
    member_result = await db.execute(
        select(OrganizationMember)
        .where(OrganizationMember.organization_id == org.id,
               OrganizationMember.user_id == current_user.id)
    )
    membership = member_result.scalar_one_or_none()
    if not membership:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member")

    # Non-owner/admin need view_analytics permission
    if membership.role not in (OrganizationRole.OWNER, OrganizationRole.ADMIN):
        perms = membership.permissions or {}
        if not perms.get("view_analytics"):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Missing view_analytics permission")

    # Get org addon IDs
    addon_ids_q = await db.execute(
        select(Addon.id).where(Addon.organization_id == org.id)
    )
    addon_ids = [row[0] for row in addon_ids_q.all()]

    member_count_q = await db.execute(
        select(func.count(OrganizationMember.id)).where(OrganizationMember.organization_id == org.id)
    )
    member_count = member_count_q.scalar() or 0
    storage_used = await calculate_org_storage(db, org.id)

    if not addon_ids:
        return OrgAnalyticsSummary(
            addon_count=0, member_count=member_count, storage_used_bytes=storage_used,
        )

    # Aggregated stats from AddonUsageStats
    stats_q = await db.execute(
        select(
            func.sum(AddonUsageStats.check_count),
            func.sum(AddonUsageStats.unique_users),
        ).where(AddonUsageStats.addon_id.in_(addon_ids))
    )
    row = stats_q.first()
    total_checks = row[0] or 0 if row else 0
    total_unique = row[1] or 0 if row else 0

    # Total downloads from usage stats
    dl_q = await db.execute(
        select(func.sum(AddonUsageStats.check_count))
        .where(AddonUsageStats.addon_id.in_(addon_ids))
    )
    total_downloads = dl_q.scalar() or 0

    # Top addons by total checks
    from sqlalchemy import desc as sa_desc
    top_q = await db.execute(
        select(
            Addon.id, Addon.name, Addon.slug,
            func.coalesce(func.sum(AddonUsageStats.check_count), 0).label("downloads"),
        )
        .outerjoin(AddonUsageStats, AddonUsageStats.addon_id == Addon.id)
        .where(Addon.id.in_(addon_ids))
        .group_by(Addon.id, Addon.name, Addon.slug)
        .order_by(sa_desc("downloads"))
        .limit(10)
    )
    top_addons = [
        {"id": r[0], "name": r[1], "slug": r[2], "downloads": r[3]}
        for r in top_q.all()
    ]

    return OrgAnalyticsSummary(
        total_downloads=total_downloads,
        total_version_checks=total_checks,
        total_unique_users=total_unique,
        addon_count=len(addon_ids),
        member_count=member_count,
        storage_used_bytes=storage_used,
        top_addons=top_addons,
    )


# =====================================================================
# Public Organization Page
# =====================================================================

@router.get("/public/{org_slug}", response_model=OrgPublicPageResponse)
async def get_public_org_page(
    org_slug: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a public-facing organization page (no auth required)."""
    result = await db.execute(select(Organization).where(Organization.slug == org_slug))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")

    # Owner info
    owner_result = await db.execute(select(User).where(User.id == org.owner_id))
    owner = owner_result.scalar_one_or_none()

    member_count_q = await db.execute(
        select(func.count(OrganizationMember.id)).where(OrganizationMember.organization_id == org.id)
    )
    member_count = member_count_q.scalar() or 0

    # Public addons (only active ones)
    addons_result = await db.execute(
        select(Addon)
        .where(Addon.organization_id == org.id, Addon.is_active == True)
        .order_by(Addon.created_at.desc())
        .limit(50)
    )
    addons = addons_result.scalars().all()

    addon_responses = []
    for addon in addons:
        addon_owner_q = await db.execute(select(User).where(User.id == addon.owner_id))
        addon_owner = addon_owner_q.scalar_one_or_none()
        addon_responses.append(AddonResponse(
            id=addon.id, name=addon.name, slug=addon.slug,
            description=addon.description,
            external=addon.external, is_active=addon.is_active,
            is_public=addon.is_public, verified=addon.verified,
            icon_url=addon.icon_url, banner_url=addon.banner_url,
            tags=addon.tags or [],
            owner_id=addon.owner_id,
            owner_username=addon_owner.discord_username if addon_owner else None,
            organization_id=addon.organization_id,
            created_at=addon.created_at,
            updated_at=addon.updated_at,
        ))

    return OrgPublicPageResponse(
        id=org.id, name=org.name, slug=org.slug,
        description=org.description, avatar_url=org.avatar_url,
        banner_url=org.banner_url,
        owner_username=owner.discord_username if owner else None,
        member_count=member_count,
        addon_count=len(addon_responses),
        addons=addon_responses,
        created_at=org.created_at,
    )
