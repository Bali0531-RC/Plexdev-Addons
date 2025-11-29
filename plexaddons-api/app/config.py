from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    # Application
    app_name: str = "PlexAddons API"
    app_version: str = "1.0.0"
    environment: str = "development"
    debug: bool = False
    secret_key: str
    frontend_url: str = "http://localhost:3000"
    
    # Database
    database_url: str
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    
    # Discord OAuth2
    discord_client_id: str
    discord_client_secret: str
    discord_redirect_uri: str
    discord_api_base: str = "https://discord.com/api/v10"
    
    # Stripe
    stripe_secret_key: str
    stripe_webhook_secret: str
    stripe_pro_price_id: str
    stripe_premium_price_id: str
    
    # PayPal
    paypal_client_id: str
    paypal_client_secret: str
    paypal_webhook_id: str
    paypal_pro_plan_id: str
    paypal_premium_plan_id: str
    paypal_api_base: str = "https://api-m.sandbox.paypal.com"  # Use api-m.paypal.com for production
    
    # Admin
    initial_admin_discord_id: Optional[str] = None
    
    # JWT
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60 * 24 * 7  # 7 days
    
    # Rate Limiting (requests per minute)
    rate_limit_public: int = 100
    rate_limit_auth_endpoints: int = 30
    rate_limit_user_free: int = 200
    rate_limit_user_pro: int = 500
    rate_limit_user_premium: int = 1000
    
    # Storage Quotas (in bytes)
    storage_quota_free: int = 50 * 1024 * 1024  # 50MB
    storage_quota_pro: int = 500 * 1024 * 1024  # 500MB
    storage_quota_premium: int = 5 * 1024 * 1024 * 1024  # 5GB
    
    # Version History Limits
    version_limit_free: int = 5
    version_limit_pro: int = 10
    version_limit_premium: int = -1  # Unlimited
    
    # Audit Log
    audit_log_retention_days: int = 90
    
    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
