"""
Caching system for Scrapyd

Provides multiple cache backends including in-memory and Redis.
"""

from .memory_cache import MemoryCache, LRUCache

try:
    from .redis_cache import RedisCache
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


def create_cache(backend='memory', **kwargs):
    """
    Create cache instance based on backend type

    Args:
        backend: Cache backend type ('memory', 'redis', 'lru')
        **kwargs: Backend-specific configuration

    Returns:
        Cache instance
    """
    if backend == 'memory':
        return MemoryCache(**kwargs)
    elif backend == 'lru':
        return LRUCache(**kwargs)
    elif backend == 'redis':
        if not REDIS_AVAILABLE:
            raise ImportError("Redis backend requires 'redis' package")
        return RedisCache(**kwargs)
    else:
        raise ValueError(f"Unknown cache backend: {backend}")


__all__ = ['MemoryCache', 'LRUCache', 'create_cache']

if REDIS_AVAILABLE:
    __all__.append('RedisCache')