from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import redis.asyncio as redis
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta, timezone

from app.config import get_settings
from app.database import engine, Base, AsyncSessionLocal
from app.api.v1 import router as v1_router
from app.api.public import router as public_router
from app.webhooks import router as webhooks_router
from app.core.rate_limit import RateLimitMiddleware, set_rate_limiter, set_redis_client
from app.core.exceptions import PlexAddonsException

settings = get_settings()

# Scheduler for periodic tasks
scheduler = AsyncIOScheduler()


async def cleanup_audit_logs():
    """Scheduled task to clean up old audit logs."""
    from app.models import AdminAuditLog
    from sqlalchemy import delete
    
    async with AsyncSessionLocal() as db:
        cutoff = datetime.now(timezone.utc) - timedelta(days=settings.audit_log_retention_days)
        await db.execute(
            delete(AdminAuditLog).where(AdminAuditLog.created_at < cutoff)
        )
        await db.commit()
        print(f"[Scheduler] Cleaned up audit logs older than {cutoff}")


async def cleanup_api_request_logs():
    """Scheduled task to clean up old API request logs (keep 30 days)."""
    from app.models import ApiRequestLog
    from sqlalchemy import delete
    
    async with AsyncSessionLocal() as db:
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        await db.execute(
            delete(ApiRequestLog).where(ApiRequestLog.timestamp < cutoff)
        )
        await db.commit()
        print(f"[Scheduler] Cleaned up API request logs older than {cutoff}")


async def send_weekly_summary():
    """Send weekly summary email to admin."""
    from app.services.email_service import email_service
    
    async with AsyncSessionLocal() as db:
        result = await email_service.send_admin_weekly_summary(db)
        if result:
            print("[Scheduler] Weekly summary email sent")
        else:
            print("[Scheduler] Weekly summary email skipped (no admin email configured)")


async def compress_ticket_attachments():
    """Scheduled task to compress old ticket attachments."""
    from app.services.ticket_service import ticket_service
    
    async with AsyncSessionLocal() as db:
        compressed_count = await ticket_service.compress_old_attachments(db)
        print(f"[Scheduler] Compressed {compressed_count} ticket attachments")


async def cleanup_ticket_attachments():
    """Scheduled task to delete very old ticket attachments."""
    from app.services.ticket_service import ticket_service
    
    async with AsyncSessionLocal() as db:
        deleted_count = await ticket_service.delete_old_attachments(db)
        removed_dirs = await ticket_service.cleanup_empty_directories()
        print(f"[Scheduler] Deleted {deleted_count} old ticket attachments, removed {removed_dirs} empty directories")


async def publish_scheduled_versions():
    """Scheduled task to publish versions that have reached their scheduled release time."""
    from app.models import Version
    from sqlalchemy import select, and_
    async with AsyncSessionLocal() as db:
        now = datetime.now(timezone.utc)
        
        # Find versions that are scheduled and ready to publish
        result = await db.execute(
            select(Version).where(
                and_(
                    Version.scheduled_release_at.isnot(None),
                    Version.scheduled_release_at <= now,
                    Version.is_published == False
                )
            )
        )
        versions = result.scalars().all()
        
        for version in versions:
            version.is_published = True
            print(f"[Scheduler] Published scheduled version {version.version} for addon {version.addon_id}")
        
        if versions:
            await db.commit()
            print(f"[Scheduler] Published {len(versions)} scheduled versions")


async def bootstrap_initial_admin():
    """Create initial admin user if configured."""
    if not settings.initial_admin_discord_id:
        return
    
    from app.models import User
    from sqlalchemy import select
    
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User).where(User.discord_id == settings.initial_admin_discord_id)
        )
        user = result.scalar_one_or_none()
        
        if user and not user.is_admin:
            user.is_admin = True
            await db.commit()
            print(f"[Bootstrap] Promoted existing user {user.discord_username} to admin")
        elif not user:
            print(f"[Bootstrap] Initial admin Discord ID configured: {settings.initial_admin_discord_id}")
            print("[Bootstrap] User will be promoted to admin on first login")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    print("[Startup] Initializing database...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Initialize Redis for rate limiting
    print("[Startup] Connecting to Redis...")
    try:
        redis_client = redis.from_url(settings.redis_url, decode_responses=True)
        await redis_client.ping()
        set_redis_client(redis_client)  # Store globally for OAuth state storage
        rate_limiter = RateLimitMiddleware(redis_client)
        set_rate_limiter(rate_limiter)
        print("[Startup] Redis connected successfully")
    except Exception as e:
        print(f"[Startup] Redis connection failed: {e}")
        print("[Startup] Rate limiting will be disabled")
    
    # Bootstrap initial admin
    await bootstrap_initial_admin()
    
    # Start scheduler
    scheduler.add_job(
        cleanup_audit_logs,
        "cron",
        hour=3,  # Run at 3 AM daily
        minute=0,
    )
    scheduler.add_job(
        cleanup_api_request_logs,
        "cron",
        hour=3,  # Run at 3 AM daily
        minute=30,
    )
    scheduler.add_job(
        send_weekly_summary,
        "cron",
        day_of_week="mon",  # Run every Monday
        hour=8,  # at 8 AM UTC
        minute=0,
    )
    scheduler.add_job(
        compress_ticket_attachments,
        "cron",
        hour=4,  # Run at 4 AM daily
        minute=0,
    )
    scheduler.add_job(
        cleanup_ticket_attachments,
        "cron",
        hour=4,  # Run at 4 AM daily
        minute=30,
    )
    scheduler.add_job(
        publish_scheduled_versions,
        "interval",
        minutes=5,  # Check every 5 minutes for scheduled versions
    )
    scheduler.start()
    print("[Startup] Scheduler started")
    
    yield
    
    # Shutdown
    print("[Shutdown] Stopping scheduler...")
    scheduler.shutdown()
    print("[Shutdown] Closing database connections...")
    await engine.dispose()


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="PlexAddons Version Management API",
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url="/redoc" if settings.environment != "production" else None,
    openapi_url="/openapi.json",  # Always available for frontend ReDoc
    lifespan=lifespan,
)

# CORS middleware
cors_origins = [settings.frontend_url]
if settings.environment != "production":
    cors_origins.extend([
        "http://localhost:3000",
        "http://localhost:5173",
    ])

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(PlexAddonsException)
async def plexaddons_exception_handler(request: Request, exc: PlexAddonsException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=getattr(exc, "headers", None),
    )


# Add rate limit headers to responses
@app.middleware("http")
async def add_rate_limit_headers(request: Request, call_next):
    response = await call_next(request)
    
    # Add rate limit headers if available
    if hasattr(request.state, "rate_limit_headers"):
        for key, value in request.state.rate_limit_headers.items():
            response.headers[key] = value
    
    return response


# Security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    
    # Prevent clickjacking
    response.headers["X-Frame-Options"] = "DENY"
    
    # Prevent MIME type sniffing
    response.headers["X-Content-Type-Options"] = "nosniff"
    
    # XSS Protection (legacy but still useful)
    response.headers["X-XSS-Protection"] = "1; mode=block"
    
    # Referrer policy
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    
    # Permissions policy (disable unnecessary browser features)
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

    # HSTS - enforce HTTPS in production
    if settings.environment == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

    return response


# Include routers
app.include_router(v1_router, prefix="/api")
app.include_router(public_router)  # Public API at root level
app.include_router(webhooks_router, prefix="/api")  # Webhooks at /api/webhooks


# Health check endpoint
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "version": settings.app_version,
        "environment": settings.environment,
    }


@app.get("/")
async def root():
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs" if settings.environment != "production" else None,
        "api": "/api/v1",
        "versions_json": "/versions.json",
    }
