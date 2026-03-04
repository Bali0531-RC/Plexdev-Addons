"""Collaborator management endpoints for addons (Pro+ feature)."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models import User, CollaboratorRole
from app.schemas import (
    CollaboratorInvite,
    CollaboratorUpdate,
    CollaboratorResponse,
    TransferOwnershipRequest,
)
from app.services import CollaboratorService
from app.api.deps import get_current_user, require_pro, rate_limit_check_authenticated, get_effective_tier
from app.core.exceptions import ForbiddenError
from app.models import SubscriptionTier

router = APIRouter(prefix="/addons/{addon_id}/collaborators", tags=["Collaborators"])


@router.get("", response_model=list[CollaboratorResponse])
async def list_collaborators(
    addon_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """List all collaborators for an addon. Requires ownership or admin collaborator role."""
    can = await CollaboratorService.can_manage_addon(db, addon_id, user)
    if not can:
        raise ForbiddenError("You don't have access to this addon's collaborators")
    return await CollaboratorService.list_collaborators(db, addon_id)


@router.post("", response_model=CollaboratorResponse)
async def invite_collaborator(
    addon_id: int,
    data: CollaboratorInvite,
    user: User = Depends(require_pro),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """Invite a user as a collaborator (Pro+ feature). Only addon owner can invite."""
    addon = await CollaboratorService.get_addon_with_owner_check(db, addon_id, user)
    collab = await CollaboratorService.invite_collaborator(
        db, addon.id, data.user_id, data.role, user
    )
    # Return with user info
    collaborators = await CollaboratorService.list_collaborators(db, addon_id)
    return next(c for c in collaborators if c["id"] == collab.id)


@router.patch("/{collaborator_id}", response_model=CollaboratorResponse)
async def update_collaborator(
    addon_id: int,
    collaborator_id: int,
    data: CollaboratorUpdate,
    user: User = Depends(require_pro),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """Update a collaborator's role. Only addon owner can update."""
    await CollaboratorService.get_addon_with_owner_check(db, addon_id, user)
    await CollaboratorService.update_collaborator_role(db, collaborator_id, data.role)
    collaborators = await CollaboratorService.list_collaborators(db, addon_id)
    return next(c for c in collaborators if c["id"] == collaborator_id)


@router.delete("/{collaborator_id}", status_code=204)
async def remove_collaborator(
    addon_id: int,
    collaborator_id: int,
    user: User = Depends(require_pro),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """Remove a collaborator from an addon. Only addon owner can remove."""
    await CollaboratorService.get_addon_with_owner_check(db, addon_id, user)
    await CollaboratorService.remove_collaborator(db, collaborator_id)


# Transfer ownership endpoint
transfer_router = APIRouter(prefix="/addons/{addon_id}/transfer", tags=["Addons"])


@transfer_router.post("")
async def transfer_addon_ownership(
    addon_id: int,
    data: TransferOwnershipRequest,
    user: User = Depends(require_pro),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """Transfer addon ownership to another user (Pro+ feature)."""
    addon = await CollaboratorService.transfer_ownership(
        db, addon_id, data.new_owner_id, user
    )
    return {"message": "Ownership transferred successfully", "new_owner_id": addon.owner_id}


# Invitation management (user-facing, not addon-specific)
invitation_router = APIRouter(prefix="/collaborations", tags=["Collaborators"])


@invitation_router.get("/invitations")
async def get_my_invitations(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """Get pending collaboration invitations for the current user."""
    return await CollaboratorService.get_my_invitations(db, user)


@invitation_router.post("/invitations/{collaborator_id}/accept")
async def accept_invitation(
    collaborator_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """Accept a collaboration invitation."""
    collab = await CollaboratorService.accept_invitation(db, collaborator_id, user)
    return {"message": "Invitation accepted", "addon_id": collab.addon_id}


@invitation_router.delete("/invitations/{collaborator_id}")
async def decline_invitation(
    collaborator_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """Decline a collaboration invitation."""
    await CollaboratorService.decline_invitation(db, collaborator_id, user)
    return {"message": "Invitation declined"}
