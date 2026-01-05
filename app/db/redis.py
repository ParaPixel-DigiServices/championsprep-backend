"""
Redis client configuration for caching and session management.
Provides async Redis operations with connection pooling.
"""

from typing import Optional, Any, Union
import redis.asyncio as aioredis
from redis.asyncio import Redis, ConnectionPool
from redis.exceptions import RedisError
import json
import pickle
import logging

from app.core.config import settings
from app.core.errors import CacheError

logger = logging.getLogger(__name__)


# ============================================================================
# REDIS CLIENT
# ============================================================================

class RedisClient:
    """
    Async Redis client with connection pooling.
    Singleton pattern for application-wide use.
    """
    _instance: Optional[Redis] = None
    _pool: Optional[ConnectionPool] = None
    
    @classmethod
    async def get_client(cls) -> Redis:
        """
        Get or create Redis client instance.
        
        Returns:
            Async Redis client
        """
        if cls._instance is None:
            try:
                # Parse Redis URL
                redis_url = settings.REDIS_URL
                
                # Create connection pool
                cls._pool = ConnectionPool.from_url(
                    redis_url,
                    max_connections=settings.REDIS_MAX_CONNECTIONS,
                    socket_timeout=settings.REDIS_SOCKET_TIMEOUT,
                    socket_connect_timeout=settings.REDIS_SOCKET_CONNECT_TIMEOUT,
                    decode_responses=False,  # We'll handle encoding
                    password=settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None,
                )
                
                # Create client
                cls._instance = Redis(connection_pool=cls._pool)
                
                # Test connection
                await cls._instance.ping()
                
                logger.info(
                    f"Redis client initialized successfully "
                    f"(max_connections={settings.REDIS_MAX_CONNECTIONS})"
                )
                
            except RedisError as e:
                logger.error(f"Failed to connect to Redis: {str(e)}")
                # Redis is not critical, log but don't fail
                logger.warning("Application will run without Redis caching")
                cls._instance = None
            except Exception as e:
                logger.error(f"Unexpected error initializing Redis: {str(e)}")
                cls._instance = None
        
        return cls._instance
    
    @classmethod
    async def close(cls):
        """Close Redis connection."""
        if cls._instance:
            await cls._instance.close()
            if cls._pool:
                await cls._pool.disconnect()
            logger.info("Redis connections closed")
            cls._instance = None
            cls._pool = None


# Global Redis instance
redis_client: Optional[Redis] = None


async def get_redis() -> Optional[Redis]:
    """
    Dependency function to get Redis client.
    
    Returns:
        Redis client or None if not available
    """
    global redis_client
    
    if redis_client is None and settings.CACHE_ENABLED:
        redis_client = await RedisClient.get_client()
    
    return redis_client


# ============================================================================
# CACHE UTILITIES
# ============================================================================

class Cache:
    """
    High-level cache operations with automatic serialization.
    """
    
    @staticmethod
    async def get(key: str, deserialize: bool = True) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            deserialize: Whether to deserialize value (default: True)
        
        Returns:
            Cached value or None if not found
        """
        try:
            client = await get_redis()
            if client is None:
                return None
            
            value = await client.get(key)
            
            if value is None:
                return None
            
            if deserialize:
                try:
                    # Try JSON first
                    return json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    # Fall back to pickle
                    return pickle.loads(value)
            
            return value
            
        except RedisError as e:
            logger.warning(f"Redis get error for key '{key}': {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Cache get error for key '{key}': {str(e)}")
            return None
    
    @staticmethod
    async def set(
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        serialize: bool = True
    ) -> bool:
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (default: from settings)
            serialize: Whether to serialize value (default: True)
        
        Returns:
            True if successful, False otherwise
        """
        try:
            client = await get_redis()
            if client is None:
                return False
            
            if serialize:
                try:
                    # Try JSON first (faster, more readable)
                    serialized_value = json.dumps(value)
                except (TypeError, ValueError):
                    # Fall back to pickle for complex objects
                    serialized_value = pickle.dumps(value)
            else:
                serialized_value = value
            
            if ttl is None:
                ttl = settings.CACHE_TTL
            
            await client.set(key, serialized_value, ex=ttl)
            return True
            
        except RedisError as e:
            logger.warning(f"Redis set error for key '{key}': {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Cache set error for key '{key}': {str(e)}")
            return False
    
    @staticmethod
    async def delete(key: str) -> bool:
        """
        Delete value from cache.
        
        Args:
            key: Cache key
        
        Returns:
            True if successful
        """
        try:
            client = await get_redis()
            if client is None:
                return False
            
            await client.delete(key)
            return True
            
        except RedisError as e:
            logger.warning(f"Redis delete error for key '{key}': {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Cache delete error for key '{key}': {str(e)}")
            return False
    
    @staticmethod
    async def exists(key: str) -> bool:
        """
        Check if key exists in cache.
        
        Args:
            key: Cache key
        
        Returns:
            True if key exists
        """
        try:
            client = await get_redis()
            if client is None:
                return False
            
            result = await client.exists(key)
            return bool(result)
            
        except RedisError as e:
            logger.warning(f"Redis exists error for key '{key}': {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Cache exists error for key '{key}': {str(e)}")
            return False
    
    @staticmethod
    async def clear_pattern(pattern: str) -> int:
        """
        Clear all keys matching pattern.
        
        Args:
            pattern: Redis key pattern (e.g., "user:*")
        
        Returns:
            Number of keys deleted
        """
        try:
            client = await get_redis()
            if client is None:
                return 0
            
            keys = []
            async for key in client.scan_iter(match=pattern):
                keys.append(key)
            
            if keys:
                deleted = await client.delete(*keys)
                logger.info(f"Cleared {deleted} keys matching pattern '{pattern}'")
                return deleted
            
            return 0
            
        except RedisError as e:
            logger.warning(f"Redis clear pattern error for '{pattern}': {str(e)}")
            return 0
        except Exception as e:
            logger.error(f"Cache clear pattern error for '{pattern}': {str(e)}")
            return 0
    
    @staticmethod
    async def increment(key: str, amount: int = 1) -> Optional[int]:
        """
        Increment counter in cache.
        
        Args:
            key: Cache key
            amount: Amount to increment (default: 1)
        
        Returns:
            New value after increment or None
        """
        try:
            client = await get_redis()
            if client is None:
                return None
            
            new_value = await client.incrby(key, amount)
            return new_value
            
        except RedisError as e:
            logger.warning(f"Redis increment error for key '{key}': {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Cache increment error for key '{key}': {str(e)}")
            return None


# ============================================================================
# CACHE DECORATORS
# ============================================================================

def cache_key(*args, **kwargs) -> str:
    """
    Generate cache key from function arguments.
    
    Args:
        *args: Positional arguments
        **kwargs: Keyword arguments
    
    Returns:
        Cache key string
    """
    parts = [str(arg) for arg in args]
    parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
    return ":".join(parts)


# ============================================================================
# SPECIALIZED CACHE HELPERS
# ============================================================================

class UserCache:
    """Cache operations for user data."""
    
    PREFIX = "user"
    
    @staticmethod
    async def get_user(user_id: str) -> Optional[dict]:
        """Get cached user data."""
        return await Cache.get(f"{UserCache.PREFIX}:{user_id}")
    
    @staticmethod
    async def set_user(user_id: str, user_data: dict, ttl: int = 3600) -> bool:
        """Cache user data."""
        return await Cache.set(f"{UserCache.PREFIX}:{user_id}", user_data, ttl=ttl)
    
    @staticmethod
    async def delete_user(user_id: str) -> bool:
        """Delete cached user data."""
        return await Cache.delete(f"{UserCache.PREFIX}:{user_id}")


class SessionCache:
    """Cache operations for study sessions."""
    
    PREFIX = "session"
    
    @staticmethod
    async def get_session(session_id: str) -> Optional[dict]:
        """Get cached session data."""
        return await Cache.get(f"{SessionCache.PREFIX}:{session_id}")
    
    @staticmethod
    async def set_session(session_id: str, session_data: dict, ttl: int = 1800) -> bool:
        """Cache session data."""
        return await Cache.set(f"{SessionCache.PREFIX}:{session_id}", session_data, ttl=ttl)
    
    @staticmethod
    async def delete_session(session_id: str) -> bool:
        """Delete cached session data."""
        return await Cache.delete(f"{SessionCache.PREFIX}:{session_id}")


class ContentCache:
    """Cache operations for AI-generated content."""
    
    PREFIX = "content"
    
    @staticmethod
    async def get_content(content_id: str) -> Optional[dict]:
        """Get cached content."""
        return await Cache.get(f"{ContentCache.PREFIX}:{content_id}")
    
    @staticmethod
    async def set_content(content_id: str, content_data: dict, ttl: int = 7200) -> bool:
        """Cache content data."""
        return await Cache.set(f"{ContentCache.PREFIX}:{content_id}", content_data, ttl=ttl)


# ============================================================================
# RATE LIMITING
# ============================================================================

class RateLimiter:
    """
    Redis-based rate limiting.
    """
    
    @staticmethod
    async def check_rate_limit(
        key: str,
        limit: int,
        window: int = 60
    ) -> tuple[bool, int]:
        """
        Check if rate limit is exceeded.
        
        Args:
            key: Rate limit key (e.g., "api:user_id")
            limit: Maximum number of requests
            window: Time window in seconds
        
        Returns:
            Tuple of (is_allowed, current_count)
        """
        try:
            client = await get_redis()
            if client is None:
                # If Redis is down, allow request
                return True, 0
            
            # Increment counter
            count = await client.incr(key)
            
            # Set expiry on first request
            if count == 1:
                await client.expire(key, window)
            
            is_allowed = count <= limit
            return is_allowed, count
            
        except RedisError as e:
            logger.warning(f"Rate limit check error: {str(e)}")
            # On error, allow request
            return True, 0


# ============================================================================
# INITIALIZATION
# ============================================================================

async def initialize_redis():
    """
    Initialize Redis connection.
    Called during application startup.
    """
    if settings.CACHE_ENABLED:
        logger.info("Initializing Redis connection...")
        client = await RedisClient.get_client()
        
        if client:
            logger.info("✅ Redis initialization successful")
        else:
            logger.warning("⚠️  Redis not available, caching disabled")
    else:
        logger.info("Redis caching is disabled")


async def close_redis():
    """
    Close Redis connection.
    Called during application shutdown.
    """
    await RedisClient.close()