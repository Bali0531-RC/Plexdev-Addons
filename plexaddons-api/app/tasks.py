"""
Background task worker using arq (async Redis queue).

Usage:
    arq app.tasks.WorkerSettings

This supplements APScheduler for ad-hoc or long-running tasks
(email sending, webhook delivery, analytics aggregation).
"""
from arq import create_pool
from arq.connections import RedisSettings, ArqRedis
from app.config import get_settings

settings = get_settings()


def get_redis_settings() -> RedisSettings:
    """Parse Redis URL into arq RedisSettings."""
    from urllib.parse import urlparse
    parsed = urlparse(settings.redis_url)
    return RedisSettings(
        host=parsed.hostname or "localhost",
        port=parsed.port or 6379,
        database=int(parsed.path.lstrip("/") or "0"),
    )


async def send_webhook_task(ctx: dict, addon_id: int, event: str, payload: dict) -> None:
    """Deliver a webhook notification asynchronously."""
    from app.services.webhook_service import WebhookService
    from app.database import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        service = WebhookService(db)
        await service.deliver_webhook(addon_id, event, payload)


async def send_email_task(ctx: dict, to: str, subject: str, html: str) -> None:
    """Send an email asynchronously."""
    from app.services.email_service import EmailService
    service = EmailService()
    await service.send_raw(to, subject, html)


async def aggregate_analytics_task(ctx: dict, addon_id: int) -> None:
    """Aggregate analytics for an addon."""
    from app.services.analytics_service import AnalyticsService
    from app.database import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        service = AnalyticsService(db)
        await service.recalculate_unique_users()


async def startup(ctx: dict) -> None:
    """Worker startup hook."""
    pass


async def shutdown(ctx: dict) -> None:
    """Worker shutdown hook."""
    pass


class WorkerSettings:
    """arq worker settings."""
    functions = [
        send_webhook_task,
        send_email_task,
        aggregate_analytics_task,
    ]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = get_redis_settings()
    max_jobs = 10
    job_timeout = 300  # 5 minutes


async def enqueue_task(func_name: str, *args, **kwargs) -> None:
    """Enqueue a task to the arq worker."""
    redis: ArqRedis = await create_pool(get_redis_settings())
    try:
        await redis.enqueue_job(func_name, *args, **kwargs)
    finally:
        await redis.close()
