from sqlalchemy import Column, Integer, String, Boolean, BigInteger, Text, DateTime, ForeignKey, Date, Index, Enum as SQLEnum, JSON
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


# Predefined addon tags
class AddonTag(str, enum.Enum):
    UTILITY = "utility"           # General utility tools
    MEDIA = "media"               # Media management
    AUTOMATION = "automation"     # Automated tasks
    MODERATION = "moderation"     # Server moderation tools
    FUN = "fun"                   # Games and entertainment
    ECONOMY = "economy"           # Virtual currency systems
    MUSIC = "music"               # Music playback features
    LEVELING = "leveling"         # XP and level systems
    LOGGING = "logging"           # Event and action logging
    INTEGRATION = "integration"   # Third-party integrations
    OTHER = "other"               # Miscellaneous


# Organization member roles
class OrganizationRole(str, enum.Enum):
    OWNER = "owner"       # Full control, billing
    ADMIN = "admin"       # Can manage addons and members
    MEMBER = "member"     # Can create/edit addons


# API Key Scopes - defines what each key can access
class ApiKeyScope(str, enum.Enum):
    # Read operations (Pro+)
    ADDONS_READ = "addons:read"           # Read addon info
    VERSIONS_READ = "versions:read"       # Read version info
    ANALYTICS_READ = "analytics:read"     # Read usage analytics
    
    # Write operations (Premium)
    VERSIONS_WRITE = "versions:write"     # Publish new versions
    ADDONS_WRITE = "addons:write"         # Create/update addons
    WEBHOOKS_MANAGE = "webhooks:manage"   # Manage webhook config
    
    # Full access (Premium)
    FULL_ACCESS = "full:access"           # All permissions


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
    storage_quota_bytes = Column(BigInteger, default=5 * 1024 * 1024)  # 5MB default
    
    # Admin flag
    is_admin = Column(Boolean, default=False, index=True)
    
    # ============== PROFILE FIELDS ==============
    # Basic profile info
    bio = Column(Text, nullable=True)  # Max 500 chars enforced at API level
    website = Column(String(500), nullable=True)
    github_username = Column(String(100), nullable=True)
    twitter_username = Column(String(100), nullable=True)
    
    # Custom profile URL (Pro+ only)
    profile_slug = Column(String(50), unique=True, nullable=True, index=True)
    
    # Profile visibility
    profile_public = Column(Boolean, default=True)
    show_addons = Column(Boolean, default=True)
    
    # Badges (JSON array of badge IDs)
    badges = Column(Text, nullable=True)  # e.g., '["pro", "early_adopter", "addon_creator"]'
    
    # Profile customization (tier-locked)
    banner_url = Column(String(500), nullable=True)  # Pro+ only
    accent_color = Column(String(7), nullable=True)  # Premium only, hex color e.g., "#e9a426"
    
    # ============== API KEY (Premium only) ==============
    api_key = Column(String(67), unique=True, nullable=True, index=True)  # pa_ + 64 hex chars
    api_key_created_at = Column(DateTime(timezone=True), nullable=True)
    
    # ============== WEBHOOK NOTIFICATIONS (Premium only) ==============
    webhook_url = Column(String(500), nullable=True)  # URL to send notifications to
    webhook_secret = Column(String(64), nullable=True)  # Secret for signing webhook payloads
    webhook_enabled = Column(Boolean, default=False)  # Whether webhooks are active
    
    # ============== TEMPORARY TIER (Admin-granted) ==============
    # When set, this overrides subscription_tier until expiration
    temp_tier = Column(SQLEnum(SubscriptionTier), nullable=True)
    temp_tier_expires_at = Column(DateTime(timezone=True), nullable=True)
    temp_tier_granted_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    temp_tier_granted_at = Column(DateTime(timezone=True), nullable=True)
    temp_tier_reason = Column(String(500), nullable=True)  # Why was temp tier granted
    
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
    owned_organizations = relationship("Organization", back_populates="owner", foreign_keys="Organization.owner_id")
    organization_memberships = relationship("OrganizationMember", back_populates="user", foreign_keys="OrganizationMember.user_id")


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
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True)
    
    # Addon identification
    name = Column(String(100), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    
    # Metadata
    description = Column(Text, nullable=True)
    homepage = Column(String(500), nullable=True)
    external = Column(Boolean, default=False)  # true = free community addon
    tags = Column(JSON, default=list)  # List of AddonTag values
    
    # Status
    is_active = Column(Boolean, default=True)
    is_public = Column(Boolean, default=True, index=True)
    verified = Column(Boolean, default=False, index=True)  # Verified by PlexDevelopment team
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    owner = relationship("User", back_populates="addons")
    organization = relationship("Organization", back_populates="addons")
    versions = relationship("Version", back_populates="addon", cascade="all, delete-orphan", order_by="desc(Version.release_date)")
    
    __table_args__ = (
        Index("idx_addons_owner_name", "owner_id", "name", unique=True),
        Index("idx_addons_organization", "organization_id"),
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
    
    # Pro+ Feature: Scheduled releases
    scheduled_release_at = Column(DateTime(timezone=True), nullable=True)  # If set, version is hidden until this time
    is_published = Column(Boolean, default=True)  # False if scheduled and not yet published
    
    # Premium Feature: A/B Rollouts
    rollout_percentage = Column(Integer, default=100)  # 0-100, percentage of users who see this version
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    addon = relationship("Addon", back_populates="versions")
    
    __table_args__ = (
        Index("idx_versions_addon_version", "addon_id", "version", unique=True),
        Index("idx_versions_release_date", "release_date"),
        Index("idx_versions_scheduled_release", "scheduled_release_at"),
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


# ============== USAGE ANALYTICS SYSTEM ==============

class VersionCheck(Base):
    """Raw version check logs for analytics"""
    __tablename__ = "version_checks"

    id = Column(Integer, primary_key=True, index=True)
    addon_id = Column(Integer, ForeignKey("addons.id", ondelete="CASCADE"), nullable=False)
    version_id = Column(Integer, ForeignKey("versions.id", ondelete="SET NULL"), nullable=True)
    
    # Version the client reported they're running
    checked_version = Column(String(50), nullable=True)
    
    # Privacy-preserving unique user tracking (hashed IP with daily rotating salt)
    client_ip_hash = Column(String(64), nullable=True)
    
    # Timestamp
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    __table_args__ = (
        Index("idx_version_checks_addon_id", "addon_id"),
        Index("idx_version_checks_timestamp", "timestamp"),
        Index("idx_version_checks_addon_timestamp", "addon_id", "timestamp"),
    )


class AddonUsageStats(Base):
    """Daily aggregated usage statistics per addon/version"""
    __tablename__ = "addon_usage_stats"

    id = Column(Integer, primary_key=True, index=True)
    addon_id = Column(Integer, ForeignKey("addons.id", ondelete="CASCADE"), nullable=False)
    version_id = Column(Integer, ForeignKey("versions.id", ondelete="SET NULL"), nullable=True)
    
    # The date this aggregate is for
    date = Column(Date, nullable=False, index=True)
    
    # Aggregated counts
    check_count = Column(Integer, default=0)  # Total version checks that day
    unique_users = Column(Integer, default=0)  # Unique IP hashes
    
    # Relationships
    addon = relationship("Addon")
    version = relationship("Version")
    
    __table_args__ = (
        Index("idx_addon_usage_stats_addon_date", "addon_id", "date"),
        Index("idx_addon_usage_stats_addon_version_date", "addon_id", "version_id", "date", unique=True),
    )


# ============== ORGANIZATION MODELS (Premium Feature) ==============

class Organization(Base):
    """Organizations for team addon management (Premium feature)."""
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Organization info
    name = Column(String(100), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    
    # Avatar/branding
    avatar_url = Column(String(500), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    owner = relationship("User", back_populates="owned_organizations", foreign_keys=[owner_id])
    members = relationship("OrganizationMember", back_populates="organization", cascade="all, delete-orphan")
    addons = relationship("Addon", back_populates="organization")
    
    __table_args__ = (
        Index("idx_organizations_owner", "owner_id"),
    )


class OrganizationMember(Base):
    """Organization membership with roles."""
    __tablename__ = "organization_members"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Role
    role = Column(SQLEnum(OrganizationRole), default=OrganizationRole.MEMBER, nullable=False)
    
    # Invitation tracking
    invited_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    joined_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    organization = relationship("Organization", back_populates="members")
    user = relationship("User", back_populates="organization_memberships", foreign_keys=[user_id])
    invited_by = relationship("User", foreign_keys=[invited_by_id])
    
    __table_args__ = (
        Index("idx_org_members_org_user", "organization_id", "user_id", unique=True),
        Index("idx_org_members_user", "user_id"),
    )


# ============== API KEYS SYSTEM (Pro+) ==============

class ApiKey(Base):
    """API keys with granular permissions for automation."""
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Key identification
    name = Column(String(100), nullable=False)  # User-friendly name
    key_prefix = Column(String(10), nullable=False)  # First 8 chars for identification (pa_xxxx)
    key_hash = Column(String(128), nullable=False, unique=True)  # SHA-256 hash of full key
    
    # Permissions - stored as JSON array of ApiKeyScope values
    scopes = Column(JSON, nullable=False, default=list)  # ["addons:read", "versions:write"]
    
    # Usage tracking
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    last_used_ip = Column(String(45), nullable=True)
    usage_count = Column(Integer, default=0)
    
    # Expiration (optional)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True, index=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", backref="api_keys")
    
    __table_args__ = (
        Index("idx_api_keys_user_id", "user_id"),
        Index("idx_api_keys_key_hash", "key_hash"),
    )
