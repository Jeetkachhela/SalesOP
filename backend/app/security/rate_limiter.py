import os
import time
import logging
import threading
from typing import Dict, Tuple
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)

# Fallback In-Memory Rate Limiting Storage
# Format: { ip_address/user_id + endpoint_key: [timestamp1, timestamp2, ...] }
_mem_lock = threading.Lock()
_mem_storage: Dict[str, list] = {}

class DualRateLimiterMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, redis_url: str = None):
        super().__init__(app)
        self.redis_client = None
        
        # Resolve Redis if URL is provided
        if redis_url:
            try:
                import redis
                self.redis_client = redis.from_url(redis_url, decode_responses=True)
                logger.info("Successfully connected to Redis for rate-limiting throttling.")
            except Exception as e:
                logger.error(f"Failed to initialize Redis client. Falling back to in-memory rate limiting. Error: {str(e)}")
        
        # Route Specific Throttling Configurations: (Limit, Window in Seconds)
        self.limits = {
            "auth": (5, 60),      # /auth/login and /auth/register: 5 requests per 60s
            "ai": (10, 60),      # /explore and /chat: 10 requests per 60s
            "upload": (5, 300),   # /uploads: 5 uploads per 300s (5 mins)
            "default": (60, 60)   # Default: 60 requests per 60s
        }

    def _get_route_bucket(self, path: str) -> Tuple[str, int, int]:
        """Resolves the throttling bucket limit and window based on path"""
        if "/api/v1/auth/login" in path or "/api/v1/auth/register" in path:
            return "auth", self.limits["auth"][0], self.limits["auth"][1]
        elif "/explore" in path or "/chat" in path:
            return "ai", self.limits["ai"][0], self.limits["ai"][1]
        elif "/api/v1/uploads" in path:
            return "upload", self.limits["upload"][0], self.limits["upload"][1]
        else:
            return "default", self.limits["default"][0], self.limits["default"][1]

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path
        
        # Skip rate-limiting for health and root endpoints
        if path == "/" or path == "/api/v1/health" or path == "/health":
            return await call_next(request)
            
        client_ip = request.client.host if request.client else "unknown-ip"
        bucket_key, limit, window = self._get_route_bucket(path)
        
        # Standard Key for identification (IP + route type)
        rate_key = f"rl:{client_ip}:{bucket_key}"
        
        is_allowed = True
        current_time = time.time()
        
        if self.redis_client:
            try:
                # Redis sliding window using sorted sets (ZREMRANGEBYSCORE + ZADD + ZCARD + EXPIRE)
                pipe = self.redis_client.pipeline()
                # Clear expired timestamps
                pipe.zremrangebyscore(rate_key, 0, current_time - window)
                # Add current request timestamp
                pipe.zadd(rate_key, {str(current_time): current_time})
                # Count total active requests in the window
                pipe.zcard(rate_key)
                # Set TTL on the set
                pipe.expire(rate_key, window + 10)
                
                # Execute transaction
                _, _, active_requests, _ = pipe.execute()
                
                if active_requests > limit:
                    is_allowed = False
            except Exception as e:
                logger.error(f"Redis rate limiting failure. Defaulting to in-memory fallback. Error: {str(e)}")
                is_allowed = self._is_allowed_in_memory(rate_key, limit, window, current_time)
        else:
            is_allowed = self._is_allowed_in_memory(rate_key, limit, window, current_time)
            
        if not is_allowed:
            logger.warning(f"Rate limit exceeded for client {client_ip} on path {path} (Bucket: {bucket_key})")
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Too many requests. Please slow down and try again.",
                    "retry_after": window
                }
            )
            
        return await call_next(request)

    def _is_allowed_in_memory(self, key: str, limit: int, window: int, current_time: float) -> bool:
        """Thread-safe in-memory sliding window rate limiting implementation"""
        with _mem_lock:
            if key not in _mem_storage:
                _mem_storage[key] = []
            
            # Filter out timestamps older than our window
            _mem_storage[key] = [ts for ts in _mem_storage[key] if ts > current_time - window]
            
            if len(_mem_storage[key]) >= limit:
                return False
                
            _mem_storage[key].append(current_time)
            return True
