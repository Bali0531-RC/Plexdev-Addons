"""
Ticket Service for PlexAddons
Handles support ticket operations including CRUD, attachments, and compression
"""
import asyncio
import logging
import lzma
import mimetypes
import os
import shutil
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.models import (
    User, Ticket, TicketMessage, TicketAttachment, CannedResponse,
    TicketStatus, TicketPriority, TicketCategory, SubscriptionTier
)
from app.api.deps import get_effective_tier

logger = logging.getLogger(__name__)
settings = get_settings()


class TicketService:
    """Service for managing support tickets"""
    
    # Priority mapping based on subscription tier
    TIER_PRIORITY_MAP = {
        SubscriptionTier.FREE: TicketPriority.LOW,
        SubscriptionTier.PRO: TicketPriority.NORMAL,
        SubscriptionTier.PREMIUM: TicketPriority.HIGH,
    }
    
    def __init__(self):
        self.attachments_path = Path(settings.ticket_attachments_path)
        self.max_attachment_size = settings.ticket_attachment_max_size_mb * 1024 * 1024  # Convert to bytes
        self.compress_after_days = settings.ticket_attachment_compress_days
        self.delete_after_days = settings.ticket_attachment_delete_days
        self.welcome_message = settings.ticket_auto_welcome_message
        
        # Ensure attachments directory exists
        self._ensure_attachments_dir()
    
    def _ensure_attachments_dir(self):
        """Create attachments directory if it doesn't exist"""
        try:
            self.attachments_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Attachments directory ready: {self.attachments_path}")
        except Exception as e:
            logger.error(f"Failed to create attachments directory: {e}")
    
    def _get_priority_for_user(self, user: User) -> TicketPriority:
        """Determine ticket priority based on user's subscription tier"""
        effective_tier = get_effective_tier(user)
        return self.TIER_PRIORITY_MAP.get(effective_tier, TicketPriority.LOW)
    
    def _is_paid_user(self, user: User) -> bool:
        """Check if user has a paid subscription"""
        effective_tier = get_effective_tier(user)
        return effective_tier in (SubscriptionTier.PRO, SubscriptionTier.PREMIUM)
    
    # ============== TICKET CRUD ==============
    
    async def create_ticket(
        self,
        db: AsyncSession,
        user: User,
        subject: str,
        content: str,
        category: TicketCategory = TicketCategory.GENERAL
    ) -> Tuple[Ticket, TicketMessage]:
        """
        Create a new support ticket with initial message.
        Returns tuple of (ticket, initial_message).
        Auto-creates welcome message.
        """
        # Determine priority based on subscription
        priority = self._get_priority_for_user(user)
        
        # Create ticket
        ticket = Ticket(
            user_id=user.id,
            subject=subject,
            category=category,
            priority=priority,
            status=TicketStatus.OPEN
        )
        db.add(ticket)
        await db.flush()  # Get ticket ID
        
        # Create initial message from user
        initial_message = TicketMessage(
            ticket_id=ticket.id,
            author_id=user.id,
            content=content,
            is_staff_reply=False,
            is_system_message=False
        )
        db.add(initial_message)
        
        # Create auto welcome message
        welcome_message = TicketMessage(
            ticket_id=ticket.id,
            author_id=None,  # System message
            content=self.welcome_message,
            is_staff_reply=False,
            is_system_message=True
        )
        db.add(welcome_message)
        
        await db.commit()
        await db.refresh(ticket)
        await db.refresh(initial_message)
        
        logger.info(f"Ticket #{ticket.id} created by user {user.discord_username} (Priority: {priority})")
        
        return ticket, initial_message
    
    async def get_ticket_by_id(
        self,
        db: AsyncSession,
        ticket_id: int,
        include_messages: bool = True
    ) -> Optional[Ticket]:
        """Get a ticket by ID with optional messages"""
        query = select(Ticket).where(Ticket.id == ticket_id)
        
        if include_messages:
            query = query.options(
                selectinload(Ticket.messages).selectinload(TicketMessage.attachments),
                selectinload(Ticket.messages).selectinload(TicketMessage.author),
                selectinload(Ticket.user),
                selectinload(Ticket.assigned_admin)
            )
        else:
            query = query.options(
                selectinload(Ticket.user),
                selectinload(Ticket.assigned_admin)
            )
        
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_user_tickets(
        self,
        db: AsyncSession,
        user_id: int,
        status: Optional[TicketStatus] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Ticket]:
        """Get all tickets for a user"""
        query = select(Ticket).where(Ticket.user_id == user_id)
        
        if status:
            query = query.where(Ticket.status == status)
        
        query = query.options(
            selectinload(Ticket.user),
            selectinload(Ticket.assigned_admin)
        ).order_by(Ticket.updated_at.desc()).offset(offset).limit(limit)
        
        result = await db.execute(query)
        return result.scalars().all()
    
    async def get_all_tickets(
        self,
        db: AsyncSession,
        status: Optional[TicketStatus] = None,
        priority: Optional[TicketPriority] = None,
        category: Optional[TicketCategory] = None,
        assigned_admin_id: Optional[int] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Ticket]:
        """Get all tickets with optional filters (admin)"""
        query = select(Ticket)
        
        filters = []
        if status:
            filters.append(Ticket.status == status)
        if priority:
            filters.append(Ticket.priority == priority)
        if category:
            filters.append(Ticket.category == category)
        if assigned_admin_id is not None:
            filters.append(Ticket.assigned_admin_id == assigned_admin_id)
        
        if filters:
            query = query.where(and_(*filters))
        
        query = query.options(
            selectinload(Ticket.user),
            selectinload(Ticket.assigned_admin)
        ).order_by(
            # Order by priority (urgent first), then by updated date
            Ticket.priority.desc(),
            Ticket.updated_at.desc()
        ).offset(offset).limit(limit)
        
        result = await db.execute(query)
        return result.scalars().all()
    
    async def update_ticket_status(
        self,
        db: AsyncSession,
        ticket: Ticket,
        new_status: TicketStatus,
        admin: Optional[User] = None
    ) -> Ticket:
        """Update ticket status with appropriate timestamp handling"""
        old_status = ticket.status
        ticket.status = new_status
        ticket.updated_at = datetime.utcnow()
        
        # Handle status-specific timestamps
        if new_status == TicketStatus.RESOLVED:
            ticket.resolved_at = datetime.utcnow()
        elif new_status == TicketStatus.CLOSED:
            ticket.closed_at = datetime.utcnow()
        
        # Auto-assign admin if first interaction
        if admin and not ticket.assigned_admin_id:
            ticket.assigned_admin_id = admin.id
        
        # Create system message about status change
        status_message = TicketMessage(
            ticket_id=ticket.id,
            author_id=admin.id if admin else None,
            content=f"Ticket status changed from **{old_status.value}** to **{new_status.value}**",
            is_staff_reply=admin is not None,
            is_system_message=True
        )
        db.add(status_message)
        
        await db.commit()
        await db.refresh(ticket)
        
        logger.info(f"Ticket #{ticket.id} status changed: {old_status} -> {new_status}")
        
        return ticket
    
    async def assign_ticket(
        self,
        db: AsyncSession,
        ticket: Ticket,
        admin: User
    ) -> Ticket:
        """Assign ticket to an admin"""
        old_admin_id = ticket.assigned_admin_id
        ticket.assigned_admin_id = admin.id
        ticket.updated_at = datetime.utcnow()
        
        # Create system message
        if old_admin_id:
            content = f"Ticket reassigned to **{admin.discord_username}**"
        else:
            content = f"Ticket assigned to **{admin.discord_username}**"
        
        system_message = TicketMessage(
            ticket_id=ticket.id,
            author_id=admin.id,
            content=content,
            is_staff_reply=True,
            is_system_message=True
        )
        db.add(system_message)
        
        await db.commit()
        await db.refresh(ticket)
        
        logger.info(f"Ticket #{ticket.id} assigned to admin {admin.discord_username}")
        
        return ticket
    
    async def update_ticket_priority(
        self,
        db: AsyncSession,
        ticket: Ticket,
        new_priority: TicketPriority,
        admin: User
    ) -> Ticket:
        """Update ticket priority (admin only)"""
        old_priority = ticket.priority
        ticket.priority = new_priority
        ticket.updated_at = datetime.utcnow()
        
        # Create system message
        system_message = TicketMessage(
            ticket_id=ticket.id,
            author_id=admin.id,
            content=f"Priority changed from **{old_priority.value}** to **{new_priority.value}**",
            is_staff_reply=True,
            is_system_message=True
        )
        db.add(system_message)
        
        await db.commit()
        await db.refresh(ticket)
        
        logger.info(f"Ticket #{ticket.id} priority changed: {old_priority} -> {new_priority}")
        
        return ticket
    
    # ============== MESSAGES ==============
    
    async def add_message(
        self,
        db: AsyncSession,
        ticket: Ticket,
        author: User,
        content: str,
        is_staff: bool = False
    ) -> TicketMessage:
        """Add a message to a ticket"""
        message = TicketMessage(
            ticket_id=ticket.id,
            author_id=author.id,
            content=content,
            is_staff_reply=is_staff,
            is_system_message=False
        )
        db.add(message)
        
        # Update ticket timestamp
        ticket.updated_at = datetime.utcnow()
        
        # Auto-assign admin on first staff reply
        if is_staff and not ticket.assigned_admin_id:
            ticket.assigned_admin_id = author.id
        
        # Change status to in_progress if open and staff replies
        if is_staff and ticket.status == TicketStatus.OPEN:
            ticket.status = TicketStatus.IN_PROGRESS
        
        await db.commit()
        await db.refresh(message)
        
        return message
    
    async def get_message_by_id(
        self,
        db: AsyncSession,
        message_id: int
    ) -> Optional[TicketMessage]:
        """Get a message by ID"""
        query = select(TicketMessage).where(
            TicketMessage.id == message_id
        ).options(
            selectinload(TicketMessage.attachments),
            selectinload(TicketMessage.author)
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    # ============== ATTACHMENTS ==============
    
    async def add_attachment(
        self,
        db: AsyncSession,
        message: TicketMessage,
        file_content: bytes,
        original_filename: str,
        skip_size_check: bool = False
    ) -> TicketAttachment:
        """Add an attachment to a message
        
        Args:
            skip_size_check: If True, bypasses file size validation (for admins)
        """
        # Validate file size (skip for admins)
        file_size = len(file_content)
        if not skip_size_check and file_size > self.max_attachment_size:
            raise ValueError(f"File size exceeds maximum allowed ({settings.ticket_attachment_max_size_mb}MB)")
        
        # Generate unique filename
        file_ext = Path(original_filename).suffix
        unique_filename = f"{uuid.uuid4().hex}{file_ext}"
        
        # Create directory structure: /attachments/ticket_id/message_id/
        ticket_dir = self.attachments_path / str(message.ticket_id) / str(message.id)
        ticket_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = ticket_dir / unique_filename
        
        # Write file
        with open(file_path, "wb") as f:
            f.write(file_content)
        
        # Detect mime type
        mime_type, _ = mimetypes.guess_type(original_filename)
        
        # Create attachment record
        attachment = TicketAttachment(
            message_id=message.id,
            file_path=str(file_path),
            original_filename=original_filename,
            file_size=file_size,
            mime_type=mime_type
        )
        db.add(attachment)
        await db.commit()
        await db.refresh(attachment)
        
        logger.info(f"Attachment added: {original_filename} ({file_size} bytes) to message #{message.id}")
        
        return attachment
    
    async def get_attachment(
        self,
        db: AsyncSession,
        attachment_id: int
    ) -> Optional[TicketAttachment]:
        """Get attachment metadata by ID"""
        result = await db.execute(
            select(TicketAttachment).where(TicketAttachment.id == attachment_id)
        )
        return result.scalar_one_or_none()
    
    def get_attachment_content(self, attachment: TicketAttachment) -> bytes:
        """Read attachment content from filesystem"""
        file_path = Path(attachment.file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Attachment file not found: {file_path}")
        
        # If compressed, decompress on read
        if attachment.is_compressed:
            with lzma.open(file_path, "rb") as f:
                return f.read()
        else:
            with open(file_path, "rb") as f:
                return f.read()
    
    async def compress_attachment(
        self,
        db: AsyncSession,
        attachment: TicketAttachment
    ) -> TicketAttachment:
        """Compress an attachment using LZMA"""
        if attachment.is_compressed:
            return attachment
        
        file_path = Path(attachment.file_path)
        if not file_path.exists():
            logger.warning(f"Attachment file not found for compression: {file_path}")
            return attachment
        
        try:
            # Read original content
            with open(file_path, "rb") as f:
                original_content = f.read()
            
            # Compress with LZMA preset 9 (maximum compression)
            compressed_content = lzma.compress(original_content, preset=9)
            
            # Write compressed file with .xz extension
            compressed_path = file_path.with_suffix(file_path.suffix + ".xz")
            with open(compressed_path, "wb") as f:
                f.write(compressed_content)
            
            # Remove original file
            file_path.unlink()
            
            # Update attachment record
            attachment.file_path = str(compressed_path)
            attachment.compressed_size = len(compressed_content)
            attachment.is_compressed = True
            attachment.compressed_at = datetime.utcnow()
            
            await db.commit()
            await db.refresh(attachment)
            
            compression_ratio = (1 - len(compressed_content) / len(original_content)) * 100
            logger.info(
                f"Attachment #{attachment.id} compressed: "
                f"{attachment.file_size} -> {attachment.compressed_size} bytes "
                f"({compression_ratio:.1f}% reduction)"
            )
            
            return attachment
            
        except Exception as e:
            logger.error(f"Failed to compress attachment #{attachment.id}: {e}")
            return attachment
    
    async def delete_attachment(
        self,
        db: AsyncSession,
        attachment: TicketAttachment
    ) -> bool:
        """Delete an attachment from filesystem and database"""
        file_path = Path(attachment.file_path)
        
        try:
            # Delete file if exists
            if file_path.exists():
                file_path.unlink()
            
            # Delete database record
            await db.delete(attachment)
            await db.commit()
            
            logger.info(f"Attachment #{attachment.id} deleted: {attachment.original_filename}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete attachment #{attachment.id}: {e}")
            return False
    
    # ============== SCHEDULED TASKS ==============
    
    async def compress_old_attachments(self, db: AsyncSession) -> int:
        """Compress attachments older than configured days"""
        cutoff_date = datetime.utcnow() - timedelta(days=self.compress_after_days)
        
        # Find uncompressed attachments older than cutoff
        result = await db.execute(
            select(TicketAttachment).where(
                and_(
                    TicketAttachment.is_compressed == False,
                    TicketAttachment.created_at < cutoff_date
                )
            )
        )
        attachments = result.scalars().all()
        
        compressed_count = 0
        for attachment in attachments:
            try:
                await self.compress_attachment(db, attachment)
                compressed_count += 1
            except Exception as e:
                logger.error(f"Failed to compress attachment #{attachment.id}: {e}")
        
        logger.info(f"Compressed {compressed_count} attachments older than {self.compress_after_days} days")
        return compressed_count
    
    async def delete_old_attachments(self, db: AsyncSession) -> int:
        """Delete attachments older than configured days"""
        cutoff_date = datetime.utcnow() - timedelta(days=self.delete_after_days)
        
        # Find attachments older than cutoff
        result = await db.execute(
            select(TicketAttachment).where(
                TicketAttachment.created_at < cutoff_date
            )
        )
        attachments = result.scalars().all()
        
        deleted_count = 0
        for attachment in attachments:
            if await self.delete_attachment(db, attachment):
                deleted_count += 1
        
        logger.info(f"Deleted {deleted_count} attachments older than {self.delete_after_days} days")
        return deleted_count
    
    async def cleanup_empty_directories(self) -> int:
        """Remove empty attachment directories"""
        removed_count = 0
        
        if not self.attachments_path.exists():
            return 0
        
        for ticket_dir in self.attachments_path.iterdir():
            if ticket_dir.is_dir():
                for message_dir in ticket_dir.iterdir():
                    if message_dir.is_dir() and not any(message_dir.iterdir()):
                        message_dir.rmdir()
                        removed_count += 1
                
                # Remove ticket dir if empty
                if not any(ticket_dir.iterdir()):
                    ticket_dir.rmdir()
                    removed_count += 1
        
        if removed_count > 0:
            logger.info(f"Removed {removed_count} empty attachment directories")
        
        return removed_count
    
    # ============== CANNED RESPONSES ==============
    
    async def create_canned_response(
        self,
        db: AsyncSession,
        title: str,
        content: str,
        admin: User,
        category: Optional[TicketCategory] = None
    ) -> CannedResponse:
        """Create a new canned response"""
        canned = CannedResponse(
            title=title,
            content=content,
            category=category,
            created_by=admin.id
        )
        db.add(canned)
        await db.commit()
        await db.refresh(canned)
        
        logger.info(f"Canned response created: {title}")
        return canned
    
    async def get_canned_responses(
        self,
        db: AsyncSession,
        category: Optional[TicketCategory] = None,
        active_only: bool = True
    ) -> List[CannedResponse]:
        """Get all canned responses with optional filters"""
        query = select(CannedResponse)
        
        if active_only:
            query = query.where(CannedResponse.is_active == True)
        if category:
            query = query.where(
                or_(
                    CannedResponse.category == category,
                    CannedResponse.category.is_(None)
                )
            )
        
        query = query.order_by(CannedResponse.usage_count.desc())
        
        result = await db.execute(query)
        return result.scalars().all()
    
    async def use_canned_response(
        self,
        db: AsyncSession,
        canned_id: int
    ) -> Optional[CannedResponse]:
        """Get and increment usage count for a canned response"""
        result = await db.execute(
            select(CannedResponse).where(CannedResponse.id == canned_id)
        )
        canned = result.scalar_one_or_none()
        
        if canned:
            canned.usage_count += 1
            await db.commit()
            await db.refresh(canned)
        
        return canned
    
    async def update_canned_response(
        self,
        db: AsyncSession,
        canned: CannedResponse,
        title: Optional[str] = None,
        content: Optional[str] = None,
        category: Optional[TicketCategory] = None,
        is_active: Optional[bool] = None
    ) -> CannedResponse:
        """Update a canned response"""
        if title is not None:
            canned.title = title
        if content is not None:
            canned.content = content
        if category is not None:
            canned.category = category
        if is_active is not None:
            canned.is_active = is_active
        
        await db.commit()
        await db.refresh(canned)
        
        return canned
    
    async def delete_canned_response(
        self,
        db: AsyncSession,
        canned: CannedResponse
    ) -> bool:
        """Delete a canned response"""
        await db.delete(canned)
        await db.commit()
        return True
    
    # ============== STATISTICS ==============
    
    async def get_ticket_stats(self, db: AsyncSession) -> Dict[str, Any]:
        """Get ticket statistics for admin dashboard"""
        stats = {}
        
        # Total tickets by status
        for status in TicketStatus:
            result = await db.execute(
                select(func.count(Ticket.id)).where(Ticket.status == status)
            )
            stats[f"tickets_{status.value}"] = result.scalar() or 0
        
        # Total tickets
        result = await db.execute(select(func.count(Ticket.id)))
        stats["total_tickets"] = result.scalar() or 0
        
        # Tickets by priority
        for priority in TicketPriority:
            result = await db.execute(
                select(func.count(Ticket.id)).where(
                    and_(
                        Ticket.priority == priority,
                        Ticket.status.in_([TicketStatus.OPEN, TicketStatus.IN_PROGRESS])
                    )
                )
            )
            stats[f"active_{priority.value}_priority"] = result.scalar() or 0
        
        # Unassigned tickets
        result = await db.execute(
            select(func.count(Ticket.id)).where(
                and_(
                    Ticket.assigned_admin_id.is_(None),
                    Ticket.status.in_([TicketStatus.OPEN, TicketStatus.IN_PROGRESS])
                )
            )
        )
        stats["unassigned_tickets"] = result.scalar() or 0
        
        # Average resolution time (for resolved tickets)
        # This would require more complex query, simplified for now
        stats["avg_resolution_hours"] = None
        
        return stats


# Global service instance
ticket_service = TicketService()
