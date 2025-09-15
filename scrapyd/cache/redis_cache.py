"""
Redis Cache Implementation

High-performance Redis-based caching layer for Scrapyd with advanced features
like TTL, compression, and connection pooling.
"""

import asyncio
import json
import pickle
import gzip
import logging
import time
from typing import Any, Optional, Dict, List, Union
from datetime import datetime, timedelta
from urllib.parse import urlparse

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

logger = logging.getLogger(__name__)


class RedisCache:
    """Async Redis cache implementation with advanced features"""

    def __init__(self, host='localhost', port=6379, db=0, password=None,
                 ssl=False, encoding='utf-8', decode_responses=False,
                 max_connections=20, retry_on_timeout=True,
                 health_check_interval=30):
        """
        Initialize Redis cache

        Args:
            host: Redis server host
            port: Redis server port
            db: Redis database number
            password: Redis password
            ssl: Use SSL connection
            encoding: String encoding
            decode_responses: Decode responses to strings
            max_connections: Maximum connection pool size
            retry_on_timeout: Retry operations on timeout
            health_check_interval: Health check interval in seconds
        """
        if not REDIS_AVAILABLE:
            raise ImportError("redis package is required for RedisCache")

        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.ssl = ssl
        self.encoding = encoding
        self.decode_responses = decode_responses
        self.max_connections = max_connections
        self.retry_on_timeout = retry_on_timeout
        self.health_check_interval = health_check_interval

        self.pool = None
        self.client = None
        self.connected = False
        self.default_ttl = 3600  # 1 hour
        self.compression_threshold = 1024  # Compress values larger than 1KB
        self.key_prefix = 'scrapyd:'

        # Statistics
        self.stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0,
            'errors': 0,
            'total_operations': 0,
            'connection_errors': 0,
            'last_health_check': None,
            'health_status': 'unknown'
        }

        # Health monitoring
        self._health_check_task = None

    @classmethod
    def from_url(cls, url: str, **kwargs):
        """Create RedisCache from URL"""
        parsed = urlparse(url)

        config = {
            'host': parsed.hostname or 'localhost',
            'port': parsed.port or 6379,
            'db': int(parsed.path.lstrip('/')) if parsed.path else 0,
            'password': parsed.password,
            'ssl': parsed.scheme == 'rediss'
        }
        config.update(kwargs)

        return cls(**config)

    async def connect(self):
        """Connect to Redis server"""
        if self.connected:
            return

        try:
            self.pool = redis.ConnectionPool(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password,
                ssl=self.ssl,
                encoding=self.encoding,
                decode_responses=self.decode_responses,
                max_connections=self.max_connections,
                retry_on_timeout=self.retry_on_timeout
            )

            self.client = redis.Redis(connection_pool=self.pool)

            # Test connection
            await self.client.ping()

            self.connected = True
            self.stats['health_status'] = 'healthy'
            logger.info(f"Connected to Redis at {self.host}:{self.port}")

            # Start health monitoring
            self._start_health_monitoring()

        except Exception as e:
            self.stats['connection_errors'] += 1
            self.stats['health_status'] = 'unhealthy'
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    async def disconnect(self):
        """Disconnect from Redis server"""
        if not self.connected:
            return

        try:
            # Stop health monitoring
            if self._health_check_task:
                self._health_check_task.cancel()

            if self.client:
                await self.client.close()

            if self.pool:
                await self.pool.disconnect()

            self.connected = False
            logger.info("Disconnected from Redis")

        except Exception as e:
            logger.error(f"Error disconnecting from Redis: {e}")

    def _make_key(self, key: str) -> str:
        """Generate cache key with prefix"""
        return f"{self.key_prefix}{key}"

    def _serialize_value(self, value: Any) -> bytes:
        """Serialize value for storage"""
        # Try JSON first for simple types
        if isinstance(value, (str, int, float, bool, type(None))):
            serialized = json.dumps(value).encode(self.encoding)
        elif isinstance(value, (dict, list, tuple)):
            try:
                serialized = json.dumps(value).encode(self.encoding)
            except (TypeError, ValueError):
                # Fall back to pickle for complex objects
                serialized = pickle.dumps(value)
        else:
            # Use pickle for complex objects
            serialized = pickle.dumps(value)

        # Compress large values
        if len(serialized) > self.compression_threshold:
            compressed = gzip.compress(serialized)
            # Only use compression if it reduces size
            if len(compressed) < len(serialized):
                return b'GZIP:' + compressed

        return serialized

    def _deserialize_value(self, data: bytes) -> Any:
        """Deserialize value from storage"""
        if data.startswith(b'GZIP:'):
            # Decompress
            data = gzip.decompress(data[5:])

        # Try JSON first
        try:
            return json.loads(data.decode(self.encoding))
        except (json.JSONDecodeError, UnicodeDecodeError):
            # Fall back to pickle
            return pickle.loads(data)

    async def get(self, key: str, default=None) -> Any:
        """Get value from cache"""
        if not self.connected:
            return default

        full_key = self._make_key(key)
        self.stats['total_operations'] += 1

        try:
            data = await self.client.get(full_key)

            if data is None:
                self.stats['misses'] += 1
                return default

            value = self._deserialize_value(data)
            self.stats['hits'] += 1
            return value

        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"Error getting key {key}: {e}")
            return default

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache"""
        if not self.connected:
            return False

        full_key = self._make_key(key)
        ttl = ttl or self.default_ttl
        self.stats['total_operations'] += 1

        try:
            data = self._serialize_value(value)
            result = await self.client.setex(full_key, ttl, data)
            self.stats['sets'] += 1
            return bool(result)

        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"Error setting key {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        if not self.connected:
            return False

        full_key = self._make_key(key)
        self.stats['total_operations'] += 1

        try:
            result = await self.client.delete(full_key)
            self.stats['deletes'] += 1
            return bool(result)

        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"Error deleting key {key}: {e}")
            return False

    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        if not self.connected:
            return False

        full_key = self._make_key(key)
        self.stats['total_operations'] += 1

        try:
            return bool(await self.client.exists(full_key))
        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"Error checking key existence {key}: {e}")
            return False

    async def expire(self, key: str, ttl: int) -> bool:
        """Set expiration time for key"""
        if not self.connected:
            return False

        full_key = self._make_key(key)
        self.stats['total_operations'] += 1

        try:
            return bool(await self.client.expire(full_key, ttl))
        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"Error setting expiration for key {key}: {e}")
            return False

    async def ttl(self, key: str) -> int:
        """Get time-to-live for key"""
        if not self.connected:
            return -1

        full_key = self._make_key(key)
        self.stats['total_operations'] += 1

        try:
            return await self.client.ttl(full_key)
        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"Error getting TTL for key {key}: {e}")
            return -1

    async def keys(self, pattern: str = '*') -> List[str]:
        """Get keys matching pattern"""
        if not self.connected:
            return []

        full_pattern = self._make_key(pattern)
        self.stats['total_operations'] += 1

        try:
            keys = await self.client.keys(full_pattern)
            # Remove prefix from keys
            prefix_len = len(self.key_prefix)
            return [key.decode(self.encoding)[prefix_len:] if isinstance(key, bytes) else key[prefix_len:]
                    for key in keys]
        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"Error getting keys with pattern {pattern}: {e}")
            return []

    async def flush(self, pattern: str = '*') -> int:
        """Delete all keys matching pattern"""
        if not self.connected:
            return 0

        try:
            keys = await self.keys(pattern)
            if not keys:
                return 0

            full_keys = [self._make_key(key) for key in keys]
            result = await self.client.delete(*full_keys)
            self.stats['deletes'] += len(full_keys)
            return result

        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"Error flushing keys with pattern {pattern}: {e}")
            return 0

    async def mget(self, keys: List[str]) -> Dict[str, Any]:
        """Get multiple values"""
        if not self.connected or not keys:
            return {}

        full_keys = [self._make_key(key) for key in keys]
        self.stats['total_operations'] += len(keys)

        try:
            values = await self.client.mget(full_keys)
            result = {}

            for i, (key, data) in enumerate(zip(keys, values)):
                if data is not None:
                    try:
                        result[key] = self._deserialize_value(data)
                        self.stats['hits'] += 1
                    except Exception as e:
                        logger.error(f"Error deserializing key {key}: {e}")
                        self.stats['misses'] += 1
                else:
                    self.stats['misses'] += 1

            return result

        except Exception as e:
            self.stats['errors'] += len(keys)
            logger.error(f"Error getting multiple keys: {e}")
            return {}

    async def mset(self, mapping: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """Set multiple values"""
        if not self.connected or not mapping:
            return False

        ttl = ttl or self.default_ttl
        self.stats['total_operations'] += len(mapping)

        try:
            # Use pipeline for atomic operation
            async with self.client.pipeline() as pipe:
                for key, value in mapping.items():
                    full_key = self._make_key(key)
                    data = self._serialize_value(value)
                    pipe.setex(full_key, ttl, data)

                results = await pipe.execute()
                self.stats['sets'] += len(mapping)
                return all(results)

        except Exception as e:
            self.stats['errors'] += len(mapping)
            logger.error(f"Error setting multiple keys: {e}")
            return False

    async def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """Increment numeric value"""
        if not self.connected:
            return None

        full_key = self._make_key(key)
        self.stats['total_operations'] += 1

        try:
            result = await self.client.incrby(full_key, amount)
            return result
        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"Error incrementing key {key}: {e}")
            return None

    async def decrement(self, key: str, amount: int = 1) -> Optional[int]:
        """Decrement numeric value"""
        if not self.connected:
            return None

        full_key = self._make_key(key)
        self.stats['total_operations'] += 1

        try:
            result = await self.client.decrby(full_key, amount)
            return result
        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"Error decrementing key {key}: {e}")
            return None

    async def list_push(self, key: str, *values) -> Optional[int]:
        """Push values to list"""
        if not self.connected or not values:
            return None

        full_key = self._make_key(key)
        self.stats['total_operations'] += 1

        try:
            serialized_values = [self._serialize_value(v) for v in values]
            result = await self.client.lpush(full_key, *serialized_values)
            return result
        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"Error pushing to list {key}: {e}")
            return None

    async def list_pop(self, key: str) -> Any:
        """Pop value from list"""
        if not self.connected:
            return None

        full_key = self._make_key(key)
        self.stats['total_operations'] += 1

        try:
            data = await self.client.rpop(full_key)
            if data is None:
                return None

            return self._deserialize_value(data)
        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"Error popping from list {key}: {e}")
            return None

    async def list_length(self, key: str) -> int:
        """Get list length"""
        if not self.connected:
            return 0

        full_key = self._make_key(key)
        self.stats['total_operations'] += 1

        try:
            return await self.client.llen(full_key)
        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"Error getting list length {key}: {e}")
            return 0

    async def health_check(self) -> bool:
        """Perform health check"""
        if not self.connected:
            return False

        try:
            # Simple ping test
            await self.client.ping()

            # Test basic operations
            test_key = f"health_check:{int(time.time())}"
            await self.set(test_key, "test", ttl=10)
            value = await self.get(test_key)
            await self.delete(test_key)

            health_ok = value == "test"
            self.stats['health_status'] = 'healthy' if health_ok else 'unhealthy'
            self.stats['last_health_check'] = datetime.utcnow()

            return health_ok

        except Exception as e:
            self.stats['health_status'] = 'unhealthy'
            self.stats['last_health_check'] = datetime.utcnow()
            logger.error(f"Health check failed: {e}")
            return False

    def _start_health_monitoring(self):
        """Start background health monitoring"""
        async def health_monitor():
            while self.connected:
                try:
                    await self.health_check()
                    await asyncio.sleep(self.health_check_interval)
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Error in health monitor: {e}")
                    await asyncio.sleep(self.health_check_interval)

        self._health_check_task = asyncio.create_task(health_monitor())

    async def cleanup_expired(self):
        """Cleanup expired keys (Redis handles this automatically)"""
        # Redis automatically removes expired keys
        # This method is kept for interface compatibility
        pass

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        stats = self.stats.copy()

        # Calculate hit rate
        total_gets = stats['hits'] + stats['misses']
        stats['hit_rate'] = (stats['hits'] / total_gets * 100) if total_gets > 0 else 0

        # Calculate error rate
        stats['error_rate'] = (stats['errors'] / max(stats['total_operations'], 1) * 100)

        # Connection info
        stats['connected'] = self.connected
        stats['connection_info'] = {
            'host': self.host,
            'port': self.port,
            'db': self.db,
            'ssl': self.ssl
        }

        return stats

    def __str__(self):
        return f"RedisCache(host={self.host}, port={self.port}, db={self.db})"

    def __repr__(self):
        return self.__str__()