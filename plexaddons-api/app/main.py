from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import redis.asyncio as redis
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta

from app.config import get_settings
from app.database import engine, Base
from app.api.v1 import router as v1_router
from app.api.public import router as public_router
from app.webhooks import router as webhooks_router
from app.core.rate_limit import RateLimitMiddleware, set_rate_limiter
from app.core.exceptions import PlexAddonsException

settings = get_settings()

# Scheduler for periodic tasks
scheduler = AsyncIOScheduler()


async def cleanup_audit_logs():
    """Scheduled task to clean up old audit logs."""
    from app.database import AsyncSessionLocal
    from app.models import AdminAuditLog
    from sqlalchemy import delete
    
    async with AsyncSessionLocal() as db:
        cutoff = datetime.utcnow() - timedelta(days=settings.audit_log_retention_days)
        await db.execute(
            delete(AdminAuditLog).where(AdminAuditLog.created_at < cutoff)
        )
        await db.commit()
        print(f"[Scheduler] Cleaned up audit logs older than {cutoff}")


async def bootstrap_initial_admin():
    """Create initial admin user if configured."""
    if not settings.initial_admin_discord_id:
        return
    
    from app.database import AsyncSessionLocal
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
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.frontend_url,
        "http://localhost:3000",
        "http://localhost:5173",
    ],
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
