from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime, date
from app.models import SubscriptionTier, SubscriptionStatus, PaymentProvider


# ============== Auth Schemas ==============

class DiscordUser(BaseModel):
    id: str
    username: str
    avatar: Optional[str] = None
    email: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserResponse"


# ============== User Schemas ==============

class UserBase(BaseModel):
    discord_username: str
    discord_avatar: Optional[str] = None
    email: Optional[EmailStr] = None


class UserResponse(BaseModel):
    id: int
    discord_id: str
    discord_username: str
    discord_avatar: Optional[str] = None
    email: Optional[str] = None
    subscription_tier: SubscriptionTier
    storage_used_bytes: int
    storage_quota_bytes: int
    is_admin: bool
    created_at: datetime
    last_login_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserStorageResponse(BaseModel):
    storage_used_bytes: int
    storage_quota_bytes: int
    storage_used_percent: float
    addon_count: int
    version_count: int


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None


# ============== Subscription Schemas ==============

class SubscriptionResponse(BaseModel):
    id: int
    provider: PaymentProvider
    tier: SubscriptionTier
    status: SubscriptionStatus
    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    canceled_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class CreateCheckoutRequest(BaseModel):
    tier: SubscriptionTier
    provider: PaymentProvider
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None


class CheckoutResponse(BaseModel):
    checkout_url: str
    session_id: Optional[str] = None


# ============== Addon Schemas ==============

class AddonBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    homepage: Optional[str] = None
    external: bool = False


class AddonCreate(AddonBase):
    pass


class AddonUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    homepage: Optional[str] = None
    external: Optional[bool] = None
    is_active: Optional[bool] = None
    is_public: Optional[bool] = None


class AddonResponse(BaseModel):
    id: int
    slug: str
    name: str
    description: Optional[str] = None
    homepage: Optional[str] = None
    external: bool
    is_active: bool
    is_public: bool
    owner_id: int
    created_at: datetime
    updated_at: datetime
    
    # Denormalized for convenience
    owner_username: Optional[str] = None
    latest_version: Optional[str] = None
    latest_release_date: Optional[date] = None
    version_count: int = 0

    class Config:
        from_attributes = True


class AddonListResponse(BaseModel):
    addons: List[AddonResponse]
    total: int
    page: int
    per_page: int


# ============== Version Schemas ==============

class VersionBase(BaseModel):
    version: str = Field(..., min_length=1, max_length=50)
    download_url: str
    description: Optional[str] = None
    changelog_url: Optional[str] = None
    changelog_content: Optional[str] = None
    breaking: bool = False
    urgent: bool = False


class VersionCreate(VersionBase):
    release_date: Optional[date] = None


class VersionUpdate(BaseModel):
    download_url: Optional[str] = None
    description: Optional[str] = None
    changelog_url: Optional[str] = None
    changelog_content: Optional[str] = None
    breaking: Optional[bool] = None
    urgent: Optional[bool] = None


class VersionResponse(BaseModel):
    id: int
    addon_id: int
    version: str
    release_date: date
    download_url: str
    description: Optional[str] = None
    changelog_url: Optional[str] = None
    changelog_content: Optional[str] = None
    breaking: bool
    urgent: bool
    storage_size_bytes: int
    created_at: datetime

    class Config:
        from_attributes = True


class VersionListResponse(BaseModel):
    versions: List[VersionResponse]
    total: int


# ============== Admin Schemas ==============

class AdminUserUpdate(BaseModel):
    is_admin: Optional[bool] = None
    subscription_tier: Optional[SubscriptionTier] = None
    storage_quota_bytes: Optional[int] = None


class AdminStatsResponse(BaseModel):
    total_users: int
    total_addons: int
    total_versions: int
    active_subscriptions: int
    users_by_tier: dict
    recent_signups: int  # Last 7 days


class AuditLogEntry(BaseModel):
    id: int
    admin_id: Optional[int] = None
    admin_username: Optional[str] = None
    action: str
    target_type: Optional[str] = None
    target_id: Optional[int] = None
    details: Optional[str] = None
    ip_address: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AuditLogListResponse(BaseModel):
    entries: List[AuditLogEntry]
    total: int
    page: int
    per_page: int


# ============== Public API Schemas (versions.json compatible) ==============

class PublicAddonVersion(BaseModel):
    version: str
    releaseDate: str
    downloadUrl: str
    description: Optional[str] = None
    breaking: bool = False
    urgent: bool = False
    external: bool = False
    author: Optional[str] = None
    homepage: Optional[str] = None
    changelog: Optional[str] = None


class PublicVersionsJson(BaseModel):
    addons: dict[str, PublicAddonVersion]
    lastUpdated: str
    repository: str = "https://github.com/Bali0531-RC/PlexAddons"
    supportContact: Optional[str] = None


# ============== Payment Plan Schemas ==============

class PaymentPlan(BaseModel):
    tier: SubscriptionTier
    name: str
    price_monthly: float
    storage_quota_bytes: int
    version_history_limit: int
    rate_limit: int
    features: List[str]


class PaymentPlansResponse(BaseModel):
    plans: List[PaymentPlan]


# Forward reference resolution
AuthResponse.model_rebuild()
