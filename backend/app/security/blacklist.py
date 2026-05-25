import time
import logging
import threading

logger = logging.getLogger(__name__)

# Thread-safe in-memory blacklist fallback
# Format: { token_jti: expiry_timestamp }
_blacklist_lock = threading.Lock()
_mem_blacklist = {}

class TokenBlacklistManager:
    def __init__(self, redis_url: str = None):
        self.redis_client = None
        if redis_url:
            try:
                import redis
                self.redis_client = redis.from_url(redis_url, decode_responses=True)
                logger.info("Successfully connected to Redis for JWT token blacklisting.")
            except Exception as e:
                logger.error(f"Failed to initialize Redis for token blacklist. Using in-memory fallback. Error: {str(e)}")

    def blacklist_token(self, jti: str, expiry_in_seconds: int):
        """Blacklists a token by its unique identifier (JTI) for its remaining lifespan."""
        if not jti:
            return
            
        if self.redis_client:
            try:
                # Store in Redis with TTL matching token expiry
                self.redis_client.setex(f"bl:{jti}", expiry_in_seconds, "1")
                return
            except Exception as e:
                logger.error(f"Failed to blacklist token in Redis: {str(e)}")
                
        current_time = time.time()
        expiry_timestamp = current_time + expiry_in_seconds
        
        with _blacklist_lock:
            _mem_blacklist[jti] = expiry_timestamp
            
    def is_blacklisted(self, jti: str) -> bool:
        """Returns True if the token JTI is blacklisted."""
        if not jti:
            return False
            
        if self.redis_client:
            try:
                return self.redis_client.exists(f"bl:{jti}") == 1
            except Exception as e:
                logger.error(f"Failed to query Redis blacklist: {str(e)}")
                
        current_time = time.time()
        with _blacklist_lock:
            if jti in _mem_blacklist:
                if _mem_blacklist[jti] > current_time:
                    return True
                else:
                    # Clean up expired entry
                    del _mem_blacklist[jti]
        return False

# Initialize Global Singleton Instance
import os
redis_url = os.getenv("REDIS_URL")
blacklist_manager = TokenBlacklistManager(redis_url=redis_url)
