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
