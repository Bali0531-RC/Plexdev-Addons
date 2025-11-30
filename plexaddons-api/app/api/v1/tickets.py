"""
Ticket API endpoints for PlexAddons
User-facing support ticket management
"""
import logging
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User, Ticket, TicketStatus, TicketCategory
from app.schemas import (
    TicketCreate,
    TicketMessageCreate,
    TicketResponse,
    TicketDetailResponse,
    TicketListResponse,
    TicketMessageResponse,
    TicketAttachmentResponse,
)
from app.services import ticket_service, email_service, discord_service
from app.api.deps import get_current_user, rate_limit_check_authenticated
from app.core.exceptions import NotFoundError, ForbiddenError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tickets", tags=["Tickets"])


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


@router.post("", response_model=TicketDetailResponse, status_code=201)
async def create_ticket(
    data: TicketCreate,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """
    Create a new support ticket.
    Priority is automatically set based on subscription tier.
    """
    ticket, initial_message = await ticket_service.create_ticket(
        db=db,
        user=user,
        subject=data.subject,
        content=data.content,
        category=data.category,
    )
    
    # Reload ticket with all relationships
    ticket = await ticket_service.get_ticket_by_id(db, ticket.id, include_messages=True)
    
    # Background: Send notifications for paid users
    is_paid = ticket_service._is_paid_user(user)
    
    async def send_notifications():
        # Discord DM notification for paid users
        if is_paid:
            await discord_service.notify_new_ticket(
                ticket_id=ticket.id,
                user_name=user.discord_username,
                subject=data.subject,
                category=data.category.value,
                priority=ticket.priority.value,
                is_paid_user=True,
            )
        
        # Email notification to admin
        if email_service.admin_email:
            await email_service.send_admin_new_ticket(
                user=user,
                ticket_id=ticket.id,
                subject=data.subject,
                category=data.category.value,
                priority=ticket.priority.value,
                is_paid_user=is_paid,
            )
    
    background_tasks.add_task(send_notifications)
    
    return _ticket_to_detail_response(ticket)


@router.get("", response_model=TicketListResponse)
async def list_my_tickets(
    status: Optional[TicketStatus] = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """
    List all tickets for the current user.
    """
    offset = (page - 1) * per_page
    
    tickets = await ticket_service.get_user_tickets(
        db=db,
        user_id=user.id,
        status=status,
        limit=per_page,
        offset=offset,
    )
    
    # Count total (simplified - could optimize with count query)
    all_tickets = await ticket_service.get_user_tickets(
        db=db,
        user_id=user.id,
        status=status,
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


@router.get("/{ticket_id}", response_model=TicketDetailResponse)
async def get_ticket(
    ticket_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """
    Get a specific ticket with all messages.
    Users can only view their own tickets.
    """
    ticket = await ticket_service.get_ticket_by_id(db, ticket_id, include_messages=True)
    
    if not ticket:
        raise NotFoundError("Ticket not found")
    
    # Users can only view their own tickets (admins use admin endpoints)
    if ticket.user_id != user.id and not user.is_admin:
        raise ForbiddenError("You can only view your own tickets")
    
    return _ticket_to_detail_response(ticket)


@router.post("/{ticket_id}/messages", response_model=TicketMessageResponse, status_code=201)
async def add_message(
    ticket_id: int,
    data: TicketMessageCreate,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """
    Add a message/reply to a ticket.
    Users can only reply to their own tickets.
    """
    ticket = await ticket_service.get_ticket_by_id(db, ticket_id, include_messages=False)
    
    if not ticket:
        raise NotFoundError("Ticket not found")
    
    # Users can only reply to their own tickets
    if ticket.user_id != user.id and not user.is_admin:
        raise ForbiddenError("You can only reply to your own tickets")
    
    # Check if ticket is closed
    if ticket.status == TicketStatus.CLOSED:
        raise HTTPException(status_code=400, detail="Cannot reply to a closed ticket")
    
    # Determine if this is a staff reply
    is_staff = user.is_admin
    
    message = await ticket_service.add_message(
        db=db,
        ticket=ticket,
        author=user,
        content=data.content,
        is_staff=is_staff,
    )
    
    # Reload message with relationships
    message = await ticket_service.get_message_by_id(db, message.id)
    
    # Background: Notify admin if user replied (paid users get priority)
    if not is_staff:
        is_paid = ticket_service._is_paid_user(user)
        
        async def send_reply_notifications():
            if is_paid:
                await discord_service.notify_ticket_reply(
                    ticket_id=ticket.id,
                    user_name=user.discord_username,
                    subject=ticket.subject,
                    message_preview=data.content,
                    is_paid_user=True,
                )
        
        background_tasks.add_task(send_reply_notifications)
    
    return _message_to_response(message)


@router.post("/{ticket_id}/messages/{message_id}/attachments", response_model=TicketAttachmentResponse, status_code=201)
async def upload_attachment(
    ticket_id: int,
    message_id: int,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """
    Upload an attachment to a message.
    Users can only upload to their own tickets.
    Max file size: 10MB.
    """
    # Verify ticket ownership
    ticket = await ticket_service.get_ticket_by_id(db, ticket_id, include_messages=False)
    
    if not ticket:
        raise NotFoundError("Ticket not found")
    
    if ticket.user_id != user.id and not user.is_admin:
        raise ForbiddenError("You can only upload to your own tickets")
    
    # Verify message belongs to ticket
    message = await ticket_service.get_message_by_id(db, message_id)
    
    if not message or message.ticket_id != ticket_id:
        raise NotFoundError("Message not found")
    
    # Verify message author (users can only upload to their own messages)
    if message.author_id != user.id and not user.is_admin:
        raise ForbiddenError("You can only upload to your own messages")
    
    # Read file content
    file_content = await file.read()
    
    try:
        attachment = await ticket_service.add_attachment(
            db=db,
            message=message,
            file_content=file_content,
            original_filename=file.filename or "attachment",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    return TicketAttachmentResponse(
        id=attachment.id,
        original_filename=attachment.original_filename,
        file_size=attachment.file_size,
        compressed_size=attachment.compressed_size,
        mime_type=attachment.mime_type,
        is_compressed=attachment.is_compressed,
        created_at=attachment.created_at,
    )


@router.get("/{ticket_id}/attachments/{attachment_id}/download")
async def download_attachment(
    ticket_id: int,
    attachment_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """
    Download an attachment.
    Users can only download from their own tickets.
    """
    from fastapi.responses import Response
    
    # Verify ticket ownership
    ticket = await ticket_service.get_ticket_by_id(db, ticket_id, include_messages=False)
    
    if not ticket:
        raise NotFoundError("Ticket not found")
    
    if ticket.user_id != user.id and not user.is_admin:
        raise ForbiddenError("You can only download from your own tickets")
    
    # Get attachment
    attachment = await ticket_service.get_attachment(db, attachment_id)
    
    if not attachment:
        raise NotFoundError("Attachment not found")
    
    # Verify attachment belongs to this ticket (through message)
    message = await ticket_service.get_message_by_id(db, attachment.message_id)
    if not message or message.ticket_id != ticket_id:
        raise NotFoundError("Attachment not found")
    
    try:
        content = ticket_service.get_attachment_content(attachment)
    except FileNotFoundError:
        raise NotFoundError("Attachment file not found")
    
    return Response(
        content=content,
        media_type=attachment.mime_type or "application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{attachment.original_filename}"'
        }
    )


@router.post("/{ticket_id}/close", response_model=TicketResponse)
async def close_ticket(
    ticket_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """
    Close a ticket.
    Users can close their own tickets.
    """
    ticket = await ticket_service.get_ticket_by_id(db, ticket_id, include_messages=False)
    
    if not ticket:
        raise NotFoundError("Ticket not found")
    
    if ticket.user_id != user.id and not user.is_admin:
        raise ForbiddenError("You can only close your own tickets")
    
    if ticket.status == TicketStatus.CLOSED:
        raise HTTPException(status_code=400, detail="Ticket is already closed")
    
    ticket = await ticket_service.update_ticket_status(
        db=db,
        ticket=ticket,
        new_status=TicketStatus.CLOSED,
        admin=user if user.is_admin else None,
    )
    
    return _ticket_to_response(ticket)


@router.post("/{ticket_id}/reopen", response_model=TicketResponse)
async def reopen_ticket(
    ticket_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """
    Reopen a closed ticket.
    Users can reopen their own tickets.
    """
    ticket = await ticket_service.get_ticket_by_id(db, ticket_id, include_messages=False)
    
    if not ticket:
        raise NotFoundError("Ticket not found")
    
    if ticket.user_id != user.id and not user.is_admin:
        raise ForbiddenError("You can only reopen your own tickets")
    
    if ticket.status != TicketStatus.CLOSED:
        raise HTTPException(status_code=400, detail="Ticket is not closed")
    
    ticket = await ticket_service.update_ticket_status(
        db=db,
        ticket=ticket,
        new_status=TicketStatus.OPEN,
        admin=user if user.is_admin else None,
    )
    
    return _ticket_to_response(ticket)
