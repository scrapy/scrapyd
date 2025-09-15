"""
Memory Cache Implementation

High-performance in-memory caching with TTL support and automatic cleanup.
"""

import asyncio
import time
import threading
from typing import Any, Dict, Optional, Set
from dataclasses import dataclass
from datetime import datetime, timedelta
import weakref
import logging

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Cache entry with value and expiration"""
    value: Any
    expires_at: Optional[float] = None
    access_count: int = 0
    last_accessed: float = 0

    def __post_init__(self):
        self.last_accessed = time.time()

    def is_expired(self) -> bool:
        """Check if entry is expired"""
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at

    def touch(self):
        """Update access time and count"""
        self.access_count += 1
        self.last_accessed = time.time()


class MemoryCache:
    """Thread-safe in-memory cache with TTL and automatic cleanup"""

    def __init__(self, max_size: int = 10000, default_ttl: int = 3600,
                 cleanup_interval: int = 300):
        """
        Initialize memory cache

        Args:
            max_size: Maximum number of entries
            default_ttl: Default TTL in seconds
            cleanup_interval: Cleanup interval in seconds
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cleanup_interval = cleanup_interval

        self._cache: Dict[str, CacheEntry] = {}
        self._lock = threading.RLock()
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False

        # Statistics
        self.stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0,
            'evictions': 0,
            'cleanups': 0,
            'size': 0,
            'max_size': max_size
        }

    async def connect(self):
        """Initialize cache (start cleanup task)"""
        if self._running:
            return

        self._running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("MemoryCache initialized")

    async def disconnect(self):
        """Cleanup cache resources"""
        if not self._running:
            return

        self._running = False

        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        with self._lock:
            self._cache.clear()

        logger.info("MemoryCache disconnected")

    async def get(self, key: str, default=None) -> Any:
        """Get value from cache"""
        with self._lock:
            entry = self._cache.get(key)

            if entry is None:
                self.stats['misses'] += 1
                return default

            if entry.is_expired():
                del self._cache[key]
                self.stats['misses'] += 1
                self.stats['size'] = len(self._cache)
                return default

            entry.touch()
            self.stats['hits'] += 1
            return entry.value

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache"""
        ttl = ttl or self.default_ttl
        expires_at = time.time() + ttl if ttl > 0 else None

        with self._lock:
            # Check if we need to make space
            if key not in self._cache and len(self._cache) >= self.max_size:
                self._evict_lru()

            self._cache[key] = CacheEntry(value=value, expires_at=expires_at)
            self.stats['sets'] += 1
            self.stats['size'] = len(self._cache)

        return True

    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                self.stats['deletes'] += 1
                self.stats['size'] = len(self._cache)
                return True
            return False

    async def exists(self, key: str) -> bool:
        """Check if key exists and is not expired"""
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return False

            if entry.is_expired():
                del self._cache[key]
                self.stats['size'] = len(self._cache)
                return False

            return True

    async def keys(self, pattern: str = '*') -> list:
        """Get keys matching pattern (simplified glob matching)"""
        import fnmatch

        with self._lock:
            # Clean up expired entries first
            self._cleanup_expired()

            if pattern == '*':
                return list(self._cache.keys())

            return [key for key in self._cache.keys() if fnmatch.fnmatch(key, pattern)]

    async def flush(self, pattern: str = '*') -> int:
        """Delete all keys matching pattern"""
        import fnmatch

        with self._lock:
            if pattern == '*':
                count = len(self._cache)
                self._cache.clear()
                self.stats['deletes'] += count
                self.stats['size'] = 0
                return count

            keys_to_delete = [key for key in self._cache.keys()
                            if fnmatch.fnmatch(key, pattern)]

            for key in keys_to_delete:
                del self._cache[key]

            count = len(keys_to_delete)
            self.stats['deletes'] += count
            self.stats['size'] = len(self._cache)
            return count

    async def mget(self, keys: list) -> Dict[str, Any]:
        """Get multiple values"""
        result = {}
        for key in keys:
            value = await self.get(key)
            if value is not None:
                result[key] = value
        return result

    async def mset(self, mapping: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """Set multiple values"""
        for key, value in mapping.items():
            await self.set(key, value, ttl)
        return True

    async def ttl(self, key: str) -> int:
        """Get time-to-live for key"""
        with self._lock:
            entry = self._cache.get(key)
            if entry is None or entry.expires_at is None:
                return -1

            if entry.is_expired():
                del self._cache[key]
                self.stats['size'] = len(self._cache)
                return -2

            return int(entry.expires_at - time.time())

    async def expire(self, key: str, ttl: int) -> bool:
        """Set expiration time for key"""
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return False

            entry.expires_at = time.time() + ttl if ttl > 0 else None
            return True

    async def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """Increment numeric value"""
        with self._lock:
            entry = self._cache.get(key)

            if entry is None:
                # Create new entry with initial value
                await self.set(key, amount)
                return amount

            if entry.is_expired():
                del self._cache[key]
                await self.set(key, amount)
                return amount

            try:
                new_value = int(entry.value) + amount
                entry.value = new_value
                entry.touch()
                return new_value
            except (ValueError, TypeError):
                return None

    async def decrement(self, key: str, amount: int = 1) -> Optional[int]:
        """Decrement numeric value"""
        return await self.increment(key, -amount)

    def _evict_lru(self):
        """Evict least recently used entry"""
        if not self._cache:
            return

        # Find LRU entry
        lru_key = min(self._cache.keys(),
                     key=lambda k: self._cache[k].last_accessed)

        del self._cache[lru_key]
        self.stats['evictions'] += 1
        logger.debug(f"Evicted LRU key: {lru_key}")

    def _cleanup_expired(self):
        """Remove expired entries"""
        current_time = time.time()
        expired_keys = [
            key for key, entry in self._cache.items()
            if entry.expires_at and entry.expires_at <= current_time
        ]

        for key in expired_keys:
            del self._cache[key]

        if expired_keys:
            self.stats['cleanups'] += 1
            self.stats['size'] = len(self._cache)
            logger.debug(f"Cleaned up {len(expired_keys)} expired entries")

    async def _cleanup_loop(self):
        """Background cleanup task"""
        while self._running:
            try:
                with self._lock:
                    self._cleanup_expired()

                await asyncio.sleep(self.cleanup_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
                await asyncio.sleep(self.cleanup_interval)

    async def cleanup_expired(self):
        """Manual cleanup of expired entries"""
        with self._lock:
            self._cleanup_expired()

    async def health_check(self) -> bool:
        """Perform health check"""
        try:
            # Test basic operations
            test_key = f"health_check_{time.time()}"
            await self.set(test_key, "test", ttl=1)
            value = await self.get(test_key)
            await self.delete(test_key)
            return value == "test"
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._lock:
            stats = self.stats.copy()
            stats['size'] = len(self._cache)

            # Calculate hit rate
            total_gets = stats['hits'] + stats['misses']
            stats['hit_rate'] = (stats['hits'] / total_gets * 100) if total_gets > 0 else 0

            # Calculate usage
            stats['usage_percent'] = (stats['size'] / stats['max_size'] * 100)

            # Add memory info if available
            try:
                import sys
                total_size = sum(sys.getsizeof(entry.value) + sys.getsizeof(entry)
                               for entry in self._cache.values())
                stats['memory_bytes'] = total_size
            except Exception:
                stats['memory_bytes'] = None

            return stats

    def __str__(self):
        return f"MemoryCache(size={len(self._cache)}/{self.max_size})"

    def __repr__(self):
        return self.__str__()


class LRUCache(MemoryCache):
    """LRU Cache variant with stricter LRU eviction"""

    def __init__(self, max_size: int = 1000, **kwargs):
        super().__init__(max_size=max_size, **kwargs)
        self._access_order = []  # Track access order

    async def get(self, key: str, default=None) -> Any:
        """Get value and update LRU order"""
        result = await super().get(key, default)

        if result is not default:
            with self._lock:
                # Move to end (most recently used)
                if key in self._access_order:
                    self._access_order.remove(key)
                self._access_order.append(key)

        return result

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value and update LRU order"""
        result = await super().set(key, value, ttl)

        with self._lock:
            # Update access order
            if key in self._access_order:
                self._access_order.remove(key)
            self._access_order.append(key)

            # Ensure access order doesn't grow too large
            if len(self._access_order) > self.max_size * 2:
                # Clean up non-existent keys
                self._access_order = [k for k in self._access_order if k in self._cache]

        return result

    def _evict_lru(self):
        """Evict actual LRU entry based on access order"""
        with self._lock:
            # Find the least recently used key that still exists
            for key in self._access_order:
                if key in self._cache:
                    del self._cache[key]
                    self._access_order.remove(key)
                    self.stats['evictions'] += 1
                    logger.debug(f"Evicted LRU key: {key}")
                    break