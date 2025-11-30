from sqlalchemy import Column, Integer, String, Boolean, BigInteger, Text, DateTime, ForeignKey, Date, Index, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum


class SubscriptionTier(str, enum.Enum):
    FREE = "free"
    PRO = "pro"
    PREMIUM = "premium"


class SubscriptionStatus(str, enum.Enum):
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    UNPAID = "unpaid"
    TRIALING = "trialing"
    PAUSED = "paused"
    INCOMPLETE = "incomplete"
    INCOMPLETE_EXPIRED = "incomplete_expired"


class PaymentProvider(str, enum.Enum):
    STRIPE = "stripe"
    PAYPAL = "paypal"


# Ticket System Enums
class TicketStatus(str, enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class TicketPriority(str, enum.Enum):
    LOW = "low"          # Free users
    NORMAL = "normal"    # Pro users
    HIGH = "high"        # Premium users
    URGENT = "urgent"    # Admin-set only


class TicketCategory(str, enum.Enum):
    GENERAL = "general"
    BILLING = "billing"
    TECHNICAL = "technical"
    FEATURE_REQUEST = "feature_request"
    BUG_REPORT = "bug_report"


class SubscriptionStatus(str, enum.Enum):
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    UNPAID = "unpaid"
    TRIALING = "trialing"
    PAUSED = "paused"
    INCOMPLETE = "incomplete"
    INCOMPLETE_EXPIRED = "incomplete_expired"


class PaymentProvider(str, enum.Enum):
    STRIPE = "stripe"
    PAYPAL = "paypal"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    discord_id = Column(String(20), unique=True, nullable=False, index=True)
    discord_username = Column(String(100), nullable=False)
    discord_avatar = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True, index=True)
    
    # Subscription tier (denormalized for quick access)
    subscription_tier = Column(
        SQLEnum(SubscriptionTier),
        default=SubscriptionTier.FREE,
        nullable=False
    )
    
    # Storage tracking
    storage_used_bytes = Column(BigInteger, default=0)
    storage_quota_bytes = Column(BigInteger, default=50 * 1024 * 1024)  # 50MB default
    
    # Admin flag
    is_admin = Column(Boolean, default=False, index=True)
    
    # OAuth tokens (should be encrypted in production)
    discord_access_token = Column(Text, nullable=True)
    discord_refresh_token = Column(Text, nullable=True)
    discord_token_expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    subscriptions = relationship("Subscription", back_populates="user", cascade="all, delete-orphan")
    addons = relationship("Addon", back_populates="owner", cascade="all, delete-orphan")


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Provider info
    provider = Column(SQLEnum(PaymentProvider), nullable=False)
    provider_subscription_id = Column(String(255), nullable=False)
    provider_customer_id = Column(String(255), nullable=True)
    
    # Plan details
    tier = Column(SQLEnum(SubscriptionTier), nullable=False)
    
    # Status tracking
    status = Column(SQLEnum(SubscriptionStatus), nullable=False, index=True)
    
    # Dates
    current_period_start = Column(DateTime(timezone=True), nullable=True)
    current_period_end = Column(DateTime(timezone=True), nullable=True)
    canceled_at = Column(DateTime(timezone=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="subscriptions")
    
    __table_args__ = (
        Index("idx_subscriptions_provider_id", "provider", "provider_subscription_id", unique=True),
    )


class Addon(Base):
    __tablename__ = "addons"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Addon identification
    name = Column(String(100), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    
    # Metadata
    description = Column(Text, nullable=True)
    homepage = Column(String(500), nullable=True)
    external = Column(Boolean, default=False)  # true = free community addon
    
    # Status
    is_active = Column(Boolean, default=True)
    is_public = Column(Boolean, default=True, index=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    owner = relationship("User", back_populates="addons")
    versions = relationship("Version", back_populates="addon", cascade="all, delete-orphan", order_by="desc(Version.release_date)")
    
    __table_args__ = (
        Index("idx_addons_owner_name", "owner_id", "name", unique=True),
    )


class Version(Base):
    __tablename__ = "versions"

    id = Column(Integer, primary_key=True, index=True)
    addon_id = Column(Integer, ForeignKey("addons.id", ondelete="CASCADE"), nullable=False)
    
    # Version info
    version = Column(String(50), nullable=False)  # semver: "1.3.2"
    release_date = Column(Date, nullable=False, server_default=func.current_date())
    
    # Download & URLs
    download_url = Column(String(500), nullable=False)
    changelog_url = Column(String(500), nullable=True)
    
    # Content
    description = Column(Text, nullable=True)
    changelog_content = Column(Text, nullable=True)  # Full changelog for quota calculation
    
    # Flags
    breaking = Column(Boolean, default=False)
    urgent = Column(Boolean, default=False)
    
    # Storage tracking
    storage_size_bytes = Column(Integer, default=0)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    addon = relationship("Addon", back_populates="versions")
    
    __table_args__ = (
        Index("idx_versions_addon_version", "addon_id", "version", unique=True),
        Index("idx_versions_release_date", "release_date"),
    )


class AdminAuditLog(Base):
    __tablename__ = "admin_audit_log"

    id = Column(Integer, primary_key=True, index=True)
    admin_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Action details
    action = Column(String(100), nullable=False)  # e.g., "promote_admin", "demote_admin", "delete_addon"
    target_type = Column(String(50), nullable=True)  # e.g., "user", "addon", "subscription"
    target_id = Column(Integer, nullable=True)
    
    # Additional context
    details = Column(Text, nullable=True)  # JSON string with additional details
    ip_address = Column(String(45), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    __table_args__ = (
        # Index for efficient 90-day cleanup
        Index("idx_audit_log_created_at", "created_at"),
    )


class SubscriptionEvent(Base):
    __tablename__ = "subscription_events"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    subscription_id = Column(Integer, ForeignKey("subscriptions.id", ondelete="SET NULL"), nullable=True)
    
    event_type = Column(String(100), nullable=False)
    provider = Column(SQLEnum(PaymentProvider), nullable=True)
    provider_event_id = Column(String(255), nullable=True)
    payload = Column(Text, nullable=True)  # JSON string
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index("idx_subscription_events_user_id", "user_id"),
        Index("idx_subscription_events_created_at", "created_at"),
    )


class ApiRequestLog(Base):
    """Track API requests for analytics and weekly summaries"""
    __tablename__ = "api_request_logs"

    id = Column(Integer, primary_key=True, index=True)
    
    # Request info
    endpoint = Column(String(255), nullable=False)
    method = Column(String(10), nullable=False)
    status_code = Column(Integer, nullable=True)
    
    # Optional user tracking
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Request metadata
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    
    # Timestamp
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    __table_args__ = (
        Index("idx_api_request_logs_timestamp", "timestamp"),
        Index("idx_api_request_logs_endpoint", "endpoint"),
    )


# ============== SUPPORT TICKET SYSTEM ==============

class Ticket(Base):
    """Support tickets created by users"""
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Ticket details
    subject = Column(String(255), nullable=False)
    category = Column(SQLEnum(TicketCategory), default=TicketCategory.GENERAL, nullable=False)
    priority = Column(SQLEnum(TicketPriority), default=TicketPriority.LOW, nullable=False)
    status = Column(SQLEnum(TicketStatus), default=TicketStatus.OPEN, nullable=False, index=True)
    
    # Assignment
    assigned_admin_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    closed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id], backref="tickets")
    assigned_admin = relationship("User", foreign_keys=[assigned_admin_id])
    messages = relationship("TicketMessage", back_populates="ticket", cascade="all, delete-orphan", order_by="TicketMessage.created_at")
    
    __table_args__ = (
        Index("idx_tickets_user_id", "user_id"),
        Index("idx_tickets_status", "status"),
        Index("idx_tickets_priority", "priority"),
        Index("idx_tickets_created_at", "created_at"),
    )


class TicketMessage(Base):
    """Messages within a ticket (both user and staff replies)"""
    __tablename__ = "ticket_messages"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False)
    author_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Message content
    content = Column(Text, nullable=False)
    is_staff_reply = Column(Boolean, default=False)
    is_system_message = Column(Boolean, default=False)  # Auto-generated messages (welcome, status changes)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    edited_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    ticket = relationship("Ticket", back_populates="messages")
    author = relationship("User")
    attachments = relationship("TicketAttachment", back_populates="message", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("idx_ticket_messages_ticket_id", "ticket_id"),
        Index("idx_ticket_messages_created_at", "created_at"),
    )


class TicketAttachment(Base):
    """File attachments for ticket messages"""
    __tablename__ = "ticket_attachments"

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, ForeignKey("ticket_messages.id", ondelete="CASCADE"), nullable=False)
    
    # File info
    file_path = Column(String(500), nullable=False)  # Path on filesystem
    original_filename = Column(String(255), nullable=False)
    file_size = Column(BigInteger, nullable=False)  # Original size in bytes
    compressed_size = Column(BigInteger, nullable=True)  # Size after LZMA compression
    mime_type = Column(String(100), nullable=True)
    
    # Compression status
    is_compressed = Column(Boolean, default=False)
    compressed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    message = relationship("TicketMessage", back_populates="attachments")
    
    __table_args__ = (
        Index("idx_ticket_attachments_message_id", "message_id"),
        Index("idx_ticket_attachments_created_at", "created_at"),
    )


class CannedResponse(Base):
    """Pre-written responses for admin quick replies"""
    __tablename__ = "canned_responses"

    id = Column(Integer, primary_key=True, index=True)
    
    # Response details
    title = Column(String(100), nullable=False)
    content = Column(Text, nullable=False)
    category = Column(SQLEnum(TicketCategory), nullable=True)  # Optional: suggest based on ticket category
    
    # Metadata
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    usage_count = Column(Integer, default=0)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    creator = relationship("User")
    
    __table_args__ = (
        Index("idx_canned_responses_category", "category"),
    )
