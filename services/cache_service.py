"""
Cache Service - Redis-based caching for LLM responses and analysis results

This service provides:
1. LLM response caching (AI analysis, risk assessment)
2. Violation analysis caching
3. User analysis result caching
4. Configurable TTL (Time To Live)
5. Cache invalidation strategies
6. Cache statistics and monitoring
"""

import hashlib
import json
import logging
from functools import wraps
from typing import Any

import redis

logger = logging.getLogger(__name__)


class CacheService:
    """Redis-based caching service for expensive operations"""

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        default_ttl: int = 86400,  # 24 hours
        enabled: bool = True
    ):
        """
        Initialize Cache Service

        Args:
            redis_url: Redis connection URL
            default_ttl: Default TTL in seconds (24 hours)
            enabled: Whether caching is enabled
        """
        self.enabled = enabled
        self.default_ttl = default_ttl

        if not enabled:
            logger.warning("Cache service disabled")
            self.redis_client = None
            return

        try:
            self.redis_client = redis.from_url(
                redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            # Test connection
            self.redis_client.ping()
            logger.info(f"Cache service initialized: {redis_url}")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            logger.warning("Running without cache")
            self.enabled = False
            self.redis_client = None

    def _generate_key(self, prefix: str, *args, **kwargs) -> str:
        """
        Generate cache key from prefix and parameters

        Args:
            prefix: Key prefix (e.g., 'ai_analysis', 'risk_score')
            *args: Positional arguments to include in key
            **kwargs: Keyword arguments to include in key

        Returns:
            Cache key string
        """
        # Create deterministic string from args and kwargs
        key_parts = [str(arg) for arg in args]
        key_parts.extend([f"{k}={v}" for k, v in sorted(kwargs.items())])
        key_string = "|".join(key_parts)

        # Hash to keep keys short
        key_hash = hashlib.sha256(key_string.encode()).hexdigest()[:16]

        return f"compliance:{prefix}:{key_hash}"

    def get(self, key: str) -> Any | None:
        """
        Get value from cache

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        if not self.enabled or not self.redis_client:
            return None

        try:
            value = self.redis_client.get(key)
            if value:
                logger.debug(f"Cache HIT: {key}")
                return json.loads(value)
            else:
                logger.debug(f"Cache MISS: {key}")
                return None
        except Exception as e:
            logger.error(f"Cache GET error: {e}")
            return None

    def set(
        self,
        key: str,
        value: Any,
        ttl: int | None = None
    ) -> bool:
        """
        Set value in cache

        Args:
            key: Cache key
            value: Value to cache (must be JSON serializable)
            ttl: Time to live in seconds (None = use default)

        Returns:
            True if successful, False otherwise
        """
        if not self.enabled or not self.redis_client:
            return False

        try:
            ttl = ttl or self.default_ttl
            serialized = json.dumps(value)
            self.redis_client.setex(key, ttl, serialized)
            logger.debug(f"Cache SET: {key} (TTL={ttl}s)")
            return True
        except Exception as e:
            logger.error(f"Cache SET error: {e}")
            return False

    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        if not self.enabled or not self.redis_client:
            return False

        try:
            self.redis_client.delete(key)
            logger.debug(f"Cache DELETE: {key}")
            return True
        except Exception as e:
            logger.error(f"Cache DELETE error: {e}")
            return False

    def delete_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching pattern

        Args:
            pattern: Redis pattern (e.g., 'compliance:ai_analysis:*')

        Returns:
            Number of keys deleted
        """
        if not self.enabled or not self.redis_client:
            return 0

        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                count = self.redis_client.delete(*keys)
                logger.info(f"Cache DELETED {count} keys matching: {pattern}")
                return count
            return 0
        except Exception as e:
            logger.error(f"Cache DELETE PATTERN error: {e}")
            return 0

    def clear_all(self) -> bool:
        """Clear all cache (use with caution!)"""
        if not self.enabled or not self.redis_client:
            return False

        try:
            self.redis_client.flushdb()
            logger.warning("Cache CLEARED (all keys)")
            return True
        except Exception as e:
            logger.error(f"Cache CLEAR error: {e}")
            return False

    # ==================================================================
    # Domain-Specific Cache Methods
    # ==================================================================

    def get_ai_analysis(
        self,
        user_id: str,
        violation_ids: list[str],
        role_names: list[str]
    ) -> str | None:
        """
        Get cached AI analysis for user+violations

        Args:
            user_id: User ID
            violation_ids: List of violation IDs
            role_names: List of role names

        Returns:
            Cached AI analysis or None
        """
        key = self._generate_key(
            "ai_analysis",
            user_id,
            "|".join(sorted(violation_ids)),
            "|".join(sorted(role_names))
        )
        return self.get(key)

    def set_ai_analysis(
        self,
        user_id: str,
        violation_ids: list[str],
        role_names: list[str],
        analysis: str,
        ttl: int = 86400  # 24 hours
    ) -> bool:
        """
        Cache AI analysis for user+violations

        Args:
            user_id: User ID
            violation_ids: List of violation IDs
            role_names: List of role names
            analysis: AI-generated analysis text
            ttl: Time to live in seconds

        Returns:
            True if cached successfully
        """
        key = self._generate_key(
            "ai_analysis",
            user_id,
            "|".join(sorted(violation_ids)),
            "|".join(sorted(role_names))
        )
        return self.set(key, analysis, ttl)

    def get_user_violations(
        self,
        user_id: str,
        rule_version: str = "v1"
    ) -> list[dict] | None:
        """
        Get cached violation detection results for user

        Args:
            user_id: User ID
            rule_version: SOD rules version (for invalidation)

        Returns:
            List of violation dicts or None
        """
        key = self._generate_key("user_violations", user_id, rule_version)
        return self.get(key)

    def set_user_violations(
        self,
        user_id: str,
        violations: list[dict],
        rule_version: str = "v1",
        ttl: int = 3600  # 1 hour (violations change more frequently)
    ) -> bool:
        """
        Cache violation detection results for user

        Args:
            user_id: User ID
            violations: List of violation dicts
            rule_version: SOD rules version
            ttl: Time to live in seconds

        Returns:
            True if cached successfully
        """
        key = self._generate_key("user_violations", user_id, rule_version)
        return self.set(key, violations, ttl)

    def get_risk_score(
        self,
        user_id: str,
        calculation_method: str = "v1"
    ) -> float | None:
        """
        Get cached risk score for user

        Args:
            user_id: User ID
            calculation_method: Risk calculation version

        Returns:
            Risk score or None
        """
        key = self._generate_key("risk_score", user_id, calculation_method)
        return self.get(key)

    def set_risk_score(
        self,
        user_id: str,
        risk_score: float,
        calculation_method: str = "v1",
        ttl: int = 3600  # 1 hour
    ) -> bool:
        """
        Cache risk score for user

        Args:
            user_id: User ID
            risk_score: Calculated risk score
            calculation_method: Risk calculation version
            ttl: Time to live in seconds

        Returns:
            True if cached successfully
        """
        key = self._generate_key("risk_score", user_id, calculation_method)
        return self.set(key, risk_score, ttl)

    def invalidate_user(self, user_id: str) -> int:
        """
        Invalidate all cached data for a user

        Args:
            user_id: User ID

        Returns:
            Number of keys deleted
        """
        patterns = [
            f"compliance:ai_analysis:*{user_id}*",
            f"compliance:user_violations:*{user_id}*",
            f"compliance:risk_score:*{user_id}*"
        ]

        total_deleted = 0
        for pattern in patterns:
            total_deleted += self.delete_pattern(pattern)

        logger.info(f"Invalidated {total_deleted} cache entries for user: {user_id}")
        return total_deleted

    def get_stats(self) -> dict[str, Any]:
        """
        Get cache statistics

        Returns:
            Dictionary with cache stats
        """
        if not self.enabled or not self.redis_client:
            return {
                "enabled": False,
                "status": "disabled"
            }

        try:
            info = self.redis_client.info()
            stats = {
                "enabled": True,
                "status": "connected",
                "redis_version": info.get("redis_version"),
                "used_memory_human": info.get("used_memory_human"),
                "total_keys": self.redis_client.dbsize(),
                "connected_clients": info.get("connected_clients"),
                "uptime_days": info.get("uptime_in_days"),
                "hit_rate": None  # Would need separate tracking
            }

            # Get key counts by type
            key_patterns = {
                "ai_analysis": "compliance:ai_analysis:*",
                "user_violations": "compliance:user_violations:*",
                "risk_score": "compliance:risk_score:*"
            }

            for name, pattern in key_patterns.items():
                count = len(self.redis_client.keys(pattern))
                stats[f"{name}_keys"] = count

            return stats

        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {
                "enabled": True,
                "status": "error",
                "error": str(e)
            }


# ==================================================================
# Decorator for Automatic Caching
# ==================================================================

def cached(
    cache_service: CacheService,
    prefix: str,
    ttl: int | None = None,
    key_func=None
):
    """
    Decorator to automatically cache function results

    Args:
        cache_service: CacheService instance
        prefix: Cache key prefix
        ttl: Time to live (None = use default)
        key_func: Optional function to generate cache key from args

    Example:
        @cached(cache_service, "expensive_calc", ttl=3600)
        def expensive_calculation(x, y):
            return x ** y
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                key = key_func(*args, **kwargs)
            else:
                key = cache_service._generate_key(prefix, *args, **kwargs)

            # Try to get from cache
            cached_value = cache_service.get(key)
            if cached_value is not None:
                return cached_value

            # Call function
            result = func(*args, **kwargs)

            # Cache result
            if result is not None:
                cache_service.set(key, result, ttl)

            return result

        return wrapper
    return decorator


# ==================================================================
# Global Cache Instance
# ==================================================================

_global_cache_service: CacheService | None = None


def get_cache_service(
    redis_url: str = "redis://localhost:6379/0",
    enabled: bool = True
) -> CacheService:
    """
    Get or create global cache service instance

    Args:
        redis_url: Redis connection URL
        enabled: Whether caching is enabled

    Returns:
        CacheService instance
    """
    global _global_cache_service

    if _global_cache_service is None:
        _global_cache_service = CacheService(
            redis_url=redis_url,
            enabled=enabled
        )

    return _global_cache_service


def reset_cache_service():
    """Reset global cache service (for testing)"""
    global _global_cache_service
    _global_cache_service = None
