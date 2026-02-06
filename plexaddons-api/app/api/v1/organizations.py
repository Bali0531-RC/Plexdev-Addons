"""Organization endpoints for team addon management (Premium feature)."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
from app.database import get_db
from app.models import (
    Organization, OrganizationMember, User, Addon, Version,
    OrganizationRole, SubscriptionTier
)
from app.schemas import (
    OrganizationCreate, OrganizationUpdate, OrganizationResponse,
    OrganizationDetailResponse, OrganizationListResponse,
    OrganizationMemberResponse, InviteMemberRequest, UpdateMemberRoleRequest
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


@router.post("", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
async def create_organization(
    data: OrganizationCreate,
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
    await db.commit()
    await db.refresh(org)
    
    return OrganizationResponse(
        id=org.id,
        name=org.name,
        slug=org.slug,
        description=org.description,
        avatar_url=org.avatar_url,
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
    if data.name is not None:
        org.name = data.name
    if data.description is not None:
        org.description = data.description
    if data.avatar_url is not None:
        org.avatar_url = data.avatar_url
    
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
    
    # Delete organization (cascades to members)
    await db.delete(org)
    await db.commit()


@router.post("/{org_slug}/members", response_model=OrganizationMemberResponse)
async def invite_member(
    org_slug: str,
    data: InviteMemberRequest,
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
    await db.commit()
    await db.refresh(member)
    
    return OrganizationMemberResponse(
        id=member.id,
        user_id=member.user_id,
        role=member.role,
        joined_at=member.joined_at,
        discord_username=user.discord_username,
        discord_avatar=user.discord_avatar,
    )


@router.patch("/{org_slug}/members/{user_id}", response_model=OrganizationMemberResponse)
async def update_member_role(
    org_slug: str,
    user_id: int,
    data: UpdateMemberRoleRequest,
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
    
    member.role = data.role
    await db.commit()
    await db.refresh(member)
    
    return OrganizationMemberResponse(
        id=member.id,
        user_id=member.user_id,
        role=member.role,
        joined_at=member.joined_at,
        discord_username=user.discord_username,
        discord_avatar=user.discord_avatar,
    )


@router.delete("/{org_slug}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    org_slug: str,
    user_id: int,
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
    
    await db.delete(member)
    await db.commit()
