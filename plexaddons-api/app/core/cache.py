"""Redis caching layer for hot data."""
import json
import logging
from typing import Optional, Any, Callable
from functools import wraps
import redis.asyncio as redis

logger = logging.getLogger(__name__)

# Global cache client
_cache_client: Optional[redis.Redis] = None


def set_cache_client(client: redis.Redis) -> None:
    global _cache_client
    _cache_client = client


def get_cache_client() -> Optional[redis.Redis]:
    return _cache_client


class CacheService:
    """Redis-based caching service for frequently accessed data."""

    # Default TTLs in seconds
    TTL_ADDON_LIST = 60        # Addon listings: 60s
    TTL_ADDON_DETAIL = 120     # Single addon detail: 2min
    TTL_PLANS = 3600           # Payment plans: 1 hour
    TTL_PROFILE = 300          # User profiles: 5 min
    TTL_STATS = 60             # Admin stats: 60s

    @staticmethod
    async def get(key: str) -> Optional[Any]:
        client = get_cache_client()
        if not client:
            return None
        try:
            data = await client.get(f"cache:{key}")
            if data:
                return json.loads(data)
        except Exception as e:
            logger.warning(f"Cache get error for {key}: {e}")
        return None

    @staticmethod
    async def set(key: str, value: Any, ttl: int = 60) -> None:
        client = get_cache_client()
        if not client:
            return
        try:
            await client.setex(f"cache:{key}", ttl, json.dumps(value, default=str))
        except Exception as e:
            logger.warning(f"Cache set error for {key}: {e}")

    @staticmethod
    async def delete(key: str) -> None:
        client = get_cache_client()
        if not client:
            return
        try:
            await client.delete(f"cache:{key}")
        except Exception as e:
            logger.warning(f"Cache delete error for {key}: {e}")

    @staticmethod
    async def delete_pattern(pattern: str) -> None:
        """Delete all keys matching a pattern."""
        client = get_cache_client()
        if not client:
            return
        try:
            cursor = 0
            while True:
                cursor, keys = await client.scan(cursor, match=f"cache:{pattern}", count=100)
                if keys:
                    await client.delete(*keys)
                if cursor == 0:
                    break
        except Exception as e:
            logger.warning(f"Cache delete_pattern error for {pattern}: {e}")

    @staticmethod
    async def invalidate_addon(addon_id: int = None, addon_slug: str = None) -> None:
        """Invalidate cache entries related to an addon."""
        await CacheService.delete_pattern("addon_list:*")
        if addon_id:
            await CacheService.delete(f"addon:{addon_id}")
        if addon_slug:
            await CacheService.delete(f"addon_slug:{addon_slug}")

    @staticmethod
    async def invalidate_user(user_id: int) -> None:
        """Invalidate cache entries related to a user."""
        await CacheService.delete(f"profile:{user_id}")
        await CacheService.delete_pattern(f"user_addons:{user_id}:*")


cache = CacheService()
