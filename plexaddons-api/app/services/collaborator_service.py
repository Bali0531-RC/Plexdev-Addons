"""Service for managing addon collaborators and ownership transfers."""

from typing import Optional, List
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.models import Addon, User, AddonCollaborator, CollaboratorRole
from app.core.exceptions import NotFoundError, ForbiddenError, ConflictError


class CollaboratorService:

    @staticmethod
    async def get_addon_with_owner_check(
        db: AsyncSession, addon_id: int, user: User
    ) -> Addon:
        """Get addon and verify user is the owner."""
        result = await db.execute(select(Addon).where(Addon.id == addon_id))
        addon = result.scalar_one_or_none()
        if not addon:
            raise NotFoundError("Addon not found")
        if addon.owner_id != user.id and not user.is_admin:
            raise ForbiddenError("Only the addon owner can manage collaborators")
        return addon

    @staticmethod
    async def can_manage_addon(
        db: AsyncSession, addon_id: int, user: User
    ) -> bool:
        """Check if user is owner or admin collaborator of the addon."""
        result = await db.execute(select(Addon).where(Addon.id == addon_id))
        addon = result.scalar_one_or_none()
        if not addon:
            return False
        if addon.owner_id == user.id or user.is_admin:
            return True
        collab = await db.execute(
            select(AddonCollaborator).where(
                and_(
                    AddonCollaborator.addon_id == addon_id,
                    AddonCollaborator.user_id == user.id,
                    AddonCollaborator.accepted == True,
                    AddonCollaborator.role == CollaboratorRole.ADMIN,
                )
            )
        )
        return collab.scalar_one_or_none() is not None

    @staticmethod
    async def list_collaborators(
        db: AsyncSession, addon_id: int
    ) -> List[dict]:
        """List all collaborators for an addon with user info."""
        result = await db.execute(
            select(AddonCollaborator, User)
            .join(User, AddonCollaborator.user_id == User.id)
            .where(AddonCollaborator.addon_id == addon_id)
            .order_by(AddonCollaborator.created_at)
        )
        rows = result.all()
        collaborators = []
        for collab, user in rows:
            collaborators.append({
                "id": collab.id,
                "addon_id": collab.addon_id,
                "user_id": collab.user_id,
                "role": collab.role,
                "accepted": collab.accepted,
                "username": user.username,
                "display_name": user.display_name,
                "avatar": user.avatar,
                "invited_by_id": collab.invited_by_id,
                "created_at": collab.created_at,
                "accepted_at": collab.accepted_at,
            })
        return collaborators

    @staticmethod
    async def invite_collaborator(
        db: AsyncSession, addon_id: int, user_id: int, role: CollaboratorRole, invited_by: User
    ) -> AddonCollaborator:
        """Invite a user as a collaborator to an addon."""
        # Check addon exists
        addon_result = await db.execute(select(Addon).where(Addon.id == addon_id))
        addon = addon_result.scalar_one_or_none()
        if not addon:
            raise NotFoundError("Addon not found")

        # Can't invite the owner
        if addon.owner_id == user_id:
            raise ConflictError("Cannot add the addon owner as a collaborator")

        # Check target user exists
        target_result = await db.execute(select(User).where(User.id == user_id))
        if not target_result.scalar_one_or_none():
            raise NotFoundError("User not found")

        # Check if already a collaborator
        existing = await db.execute(
            select(AddonCollaborator).where(
                and_(
                    AddonCollaborator.addon_id == addon_id,
                    AddonCollaborator.user_id == user_id,
                )
            )
        )
        if existing.scalar_one_or_none():
            raise ConflictError("User is already a collaborator on this addon")

        collaborator = AddonCollaborator(
            addon_id=addon_id,
            user_id=user_id,
            role=role,
            invited_by_id=invited_by.id,
            accepted=False,
        )
        db.add(collaborator)
        await db.commit()
        await db.refresh(collaborator)
        return collaborator

    @staticmethod
    async def accept_invitation(
        db: AsyncSession, collaborator_id: int, user: User
    ) -> AddonCollaborator:
        """Accept a collaboration invitation."""
        result = await db.execute(
            select(AddonCollaborator).where(AddonCollaborator.id == collaborator_id)
        )
        collab = result.scalar_one_or_none()
        if not collab:
            raise NotFoundError("Invitation not found")
        if collab.user_id != user.id:
            raise ForbiddenError("This invitation is not for you")
        if collab.accepted:
            raise ConflictError("Invitation already accepted")

        collab.accepted = True
        collab.accepted_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(collab)
        return collab

    @staticmethod
    async def decline_invitation(
        db: AsyncSession, collaborator_id: int, user: User
    ) -> None:
        """Decline (delete) a collaboration invitation."""
        result = await db.execute(
            select(AddonCollaborator).where(AddonCollaborator.id == collaborator_id)
        )
        collab = result.scalar_one_or_none()
        if not collab:
            raise NotFoundError("Invitation not found")
        if collab.user_id != user.id:
            raise ForbiddenError("This invitation is not for you")

        await db.delete(collab)
        await db.commit()

    @staticmethod
    async def update_collaborator_role(
        db: AsyncSession, collaborator_id: int, role: CollaboratorRole
    ) -> AddonCollaborator:
        """Update a collaborator's role."""
        result = await db.execute(
            select(AddonCollaborator).where(AddonCollaborator.id == collaborator_id)
        )
        collab = result.scalar_one_or_none()
        if not collab:
            raise NotFoundError("Collaborator not found")

        collab.role = role
        await db.commit()
        await db.refresh(collab)
        return collab

    @staticmethod
    async def remove_collaborator(
        db: AsyncSession, collaborator_id: int
    ) -> None:
        """Remove a collaborator from an addon."""
        result = await db.execute(
            select(AddonCollaborator).where(AddonCollaborator.id == collaborator_id)
        )
        collab = result.scalar_one_or_none()
        if not collab:
            raise NotFoundError("Collaborator not found")

        await db.delete(collab)
        await db.commit()

    @staticmethod
    async def transfer_ownership(
        db: AsyncSession, addon_id: int, new_owner_id: int, current_user: User
    ) -> Addon:
        """Transfer addon ownership to another user."""
        # Get addon
        addon_result = await db.execute(select(Addon).where(Addon.id == addon_id))
        addon = addon_result.scalar_one_or_none()
        if not addon:
            raise NotFoundError("Addon not found")
        if addon.owner_id != current_user.id and not current_user.is_admin:
            raise ForbiddenError("Only the addon owner can transfer ownership")
        if addon.owner_id == new_owner_id:
            raise ConflictError("User is already the owner")

        # Verify new owner exists
        new_owner_result = await db.execute(select(User).where(User.id == new_owner_id))
        new_owner = new_owner_result.scalar_one_or_none()
        if not new_owner:
            raise NotFoundError("New owner not found")

        old_owner_id = addon.owner_id
        addon.owner_id = new_owner_id

        # Remove new owner from collaborators if they were one
        existing_collab = await db.execute(
            select(AddonCollaborator).where(
                and_(
                    AddonCollaborator.addon_id == addon_id,
                    AddonCollaborator.user_id == new_owner_id,
                )
            )
        )
        collab = existing_collab.scalar_one_or_none()
        if collab:
            await db.delete(collab)

        # Add old owner as admin collaborator
        old_collab = AddonCollaborator(
            addon_id=addon_id,
            user_id=old_owner_id,
            role=CollaboratorRole.ADMIN,
            invited_by_id=new_owner_id,
            accepted=True,
            accepted_at=datetime.now(timezone.utc),
        )
        db.add(old_collab)

        await db.commit()
        await db.refresh(addon)
        return addon

    @staticmethod
    async def get_my_invitations(
        db: AsyncSession, user: User
    ) -> List[dict]:
        """Get pending collaboration invitations for the current user."""
        result = await db.execute(
            select(AddonCollaborator, Addon)
            .join(Addon, AddonCollaborator.addon_id == Addon.id)
            .where(
                and_(
                    AddonCollaborator.user_id == user.id,
                    AddonCollaborator.accepted == False,
                )
            )
            .order_by(AddonCollaborator.created_at.desc())
        )
        rows = result.all()
        invitations = []
        for collab, addon in rows:
            invitations.append({
                "id": collab.id,
                "addon_id": collab.addon_id,
                "addon_name": addon.name,
                "addon_slug": addon.slug,
                "role": collab.role,
                "accepted": collab.accepted,
                "user_id": collab.user_id,
                "invited_by_id": collab.invited_by_id,
                "created_at": collab.created_at,
                "accepted_at": collab.accepted_at,
            })
        return invitations
