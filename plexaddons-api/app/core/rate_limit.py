import time
import logging
import redis.asyncio as redis
from fastapi import Request, HTTPException, status
from typing import Optional, Tuple
from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class RateLimiter:
    """Redis-based sliding window rate limiter with per-IP and per-user limits."""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.window_size = 60  # 1 minute window
    
    async def _check_limit(self, key: str, limit: int) -> Tuple[bool, int, int]:
        """
        Check if the rate limit is exceeded.
        Returns: (is_allowed, remaining, reset_time)
        """
        now = time.time()
        window_start = now - self.window_size
        
        pipe = self.redis.pipeline()
        
        # Remove old entries
        pipe.zremrangebyscore(key, 0, window_start)
        # Count current requests
        pipe.zcard(key)
        # Add current request
        pipe.zadd(key, {str(now): now})
        # Set expiry on the key
        pipe.expire(key, self.window_size + 1)
        
        results = await pipe.execute()
        current_count = results[1]
        
        remaining = max(0, limit - current_count - 1)
        reset_time = int(now + self.window_size)
        
        if current_count >= limit:
            # Remove the request we just added since it's over limit
            await self.redis.zrem(key, str(now))
            return False, 0, reset_time
        
        return True, remaining, reset_time
    
    async def check_ip_limit(self, ip: str, endpoint_type: str = "public") -> Tuple[bool, int, int]:
        """Check IP-based rate limit."""
        limits = {
            "public": settings.rate_limit_public,
            "auth": settings.rate_limit_auth_endpoints,
        }
        limit = limits.get(endpoint_type, settings.rate_limit_public)
        key = f"ratelimit:ip:{ip}:{endpoint_type}"
        return await self._check_limit(key, limit)
    
    async def check_user_limit(self, user_id: int, tier: str) -> Tuple[bool, int, int]:
        """Check user-based rate limit based on subscription tier."""
        limits = {
            "free": settings.rate_limit_user_free,
            "pro": settings.rate_limit_user_pro,
            "premium": settings.rate_limit_user_premium,
        }
        limit = limits.get(tier, settings.rate_limit_user_free)
        key = f"ratelimit:user:{user_id}"
        return await self._check_limit(key, limit)


class RateLimitMiddleware:
    """Middleware for rate limiting requests."""
    
    def __init__(self, redis_client: redis.Redis):
        self.limiter = RateLimiter(redis_client)
    
    def get_client_ip(self, request: Request) -> str:
        """Extract client IP from request, considering proxies."""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            # Use the rightmost IP (closest to our trusted reverse proxy)
            # The leftmost can be spoofed by the client
            ips = [ip.strip() for ip in forwarded.split(",")]
            return ips[-1]
        return request.client.host if request.client else "unknown"
    
    async def check_rate_limit(
        self,
        request: Request,
        user_id: Optional[int] = None,
        user_tier: Optional[str] = None,
        endpoint_type: str = "public"
    ) -> dict:
        """
        Check rate limits and return headers.
        Raises HTTPException if limit exceeded.
        """
        ip = self.get_client_ip(request)
        headers = {}
        
        try:
            # Check IP limit first
            ip_allowed, ip_remaining, ip_reset = await self.limiter.check_ip_limit(ip, endpoint_type)
            
            headers["X-RateLimit-Limit-IP"] = str(
                settings.rate_limit_auth_endpoints if endpoint_type == "auth" else settings.rate_limit_public
            )
            headers["X-RateLimit-Remaining-IP"] = str(ip_remaining)
            headers["X-RateLimit-Reset-IP"] = str(ip_reset)
            
            if not ip_allowed:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded (IP). Please try again later.",
                    headers=headers
                )
            
            # Check user limit if authenticated
            if user_id is not None and user_tier is not None:
                user_allowed, user_remaining, user_reset = await self.limiter.check_user_limit(
                    user_id, user_tier
                )
                
                tier_limits = {
                    "free": settings.rate_limit_user_free,
                    "pro": settings.rate_limit_user_pro,
                    "premium": settings.rate_limit_user_premium,
                }
                
                headers["X-RateLimit-Limit-User"] = str(tier_limits.get(user_tier, settings.rate_limit_user_free))
                headers["X-RateLimit-Remaining-User"] = str(user_remaining)
                headers["X-RateLimit-Reset-User"] = str(user_reset)
                
                if not user_allowed:
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail="Rate limit exceeded (User). Please try again later or upgrade your plan.",
                        headers=headers
                    )
            
            return headers
            
        except redis.RedisError as e:
            # Fail closed: if Redis is unavailable, reject the request
            logger.error(f"Redis unavailable during rate limit check: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Rate limiting service unavailable. Please try again later.",
            )


# Global rate limiter instance (initialized in main.py)
rate_limiter: Optional[RateLimitMiddleware] = None
# Global Redis client (initialized in main.py)
redis_client: Optional[redis.Redis] = None


def get_rate_limiter() -> Optional[RateLimitMiddleware]:
    return rate_limiter


def set_rate_limiter(limiter: RateLimitMiddleware):
    global rate_limiter
    rate_limiter = limiter


def get_redis_client() -> Optional[redis.Redis]:
    return redis_client


def set_redis_client(client: redis.Redis):
    global redis_client
    redis_client = client
