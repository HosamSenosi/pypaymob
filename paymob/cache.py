# Simple memory cache for now - Redis will be implemented later
import time
from typing import Protocol
import logging

logger = logging.getLogger(__name__)


class CacheBackend(Protocol):
    """Protocol for cache backends."""
    
    def get(self, key: str) -> str|None:
        """Get value from cache."""
        ...
    
    def set(self, key: str, value: str, ttl: int) -> None:
        """Set value in cache with TTL in seconds."""
        ...
    
    def delete(self, key: str) -> None:
        """Delete key from cache."""
        ...


class MemoryCache:
    """Simple in-memory cache implementation."""
    
    def __init__(self):
        self._cache: dict[str, tuple[str, float]] = {}
    
    def get(self, key: str) -> str|None:
        """Get value from cache, return None if expired or missing."""
        if key not in self._cache:
            return None
        
        value, expires_at = self._cache[key]
        if time.time() > expires_at:
            del self._cache[key]
            return None
        
        return value
    
    def set(self, key: str, value: str, ttl: int) -> None:
        """Set value in cache with TTL in seconds."""
        expires_at = time.time() + ttl
        self._cache[key] = (value, expires_at)
    
    def delete(self, key: str) -> None:
        """Delete key from cache."""
        self._cache.pop(key, None)
    
    def clear(self) -> None:
        """Clear all cached values."""
        self._cache.clear()


class RedisCache:
    """Redis cache backend implementation."""
    
    def __init__(self, redis_client):
        """
        Initialize with Redis client.
        
        Args:
            redis_client: Redis client instance (e.g., redis.Redis())
        """
        self.redis_client = redis_client
    
    def get(self, key: str) -> str|None:
        """Get value from Redis cache."""
        try:
            value = self.redis_client.get(key)
            return value.decode('utf-8') if value else None
        except Exception as e:
            logger.warning(f"Redis get failed for key '{key}': {e}")
            return None
    
    def set(self, key: str, value: str, ttl: int) -> None:
        """Set value in Redis cache with TTL."""
        try:
            self.redis_client.setex(key, ttl, value)
        except Exception as e:
            logger.warning(f"Redis set failed for key '{key}': {e}")
    
    def delete(self, key: str) -> None:
        """Delete key from Redis cache."""
        try:
            self.redis_client.delete(key)
        except Exception as e:
            logger.warning(f"Redis delete failed for key '{key}': {e}")
