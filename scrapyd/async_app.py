"""
Async Scrapyd Application

Modern async implementation of Scrapyd using aiohttp for better performance
and concurrency handling.
"""

import asyncio
import logging
import signal
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

import aiohttp_cors
from aiohttp import web, ClientSession
from aiohttp.web_middlewares import normalize_path_middleware

from scrapyd.config import Config
from scrapyd.async_launcher import AsyncLauncher
from scrapyd.async_poller import AsyncPoller
from scrapyd.async_scheduler import AsyncScheduler
from scrapyd.cache.redis_cache import RedisCache
from scrapyd.cache.memory_cache import MemoryCache
from scrapyd.metrics.prometheus import PrometheusMetrics
from scrapyd.rich_logging import get_rich_logger
from scrapyd.storage.factory import create_storage_backend

logger = get_rich_logger(__name__)


class AsyncScrapydApp:
    """Async implementation of Scrapyd application"""

    def __init__(self, config: Config):
        self.config = config
        self.app = web.Application()
        self.cache = None
        self.metrics = None
        self.scheduler = None
        self.launcher = None
        self.poller = None
        self.storage = None
        self.background_tasks = set()
        self.shutdown_event = asyncio.Event()

        self._setup_logging()
        self._setup_components()
        self._setup_middleware()
        self._setup_routes()
        self._setup_cors()

    def _setup_logging(self):
        """Configure structured logging for async app"""
        log_level = self.config.get('log_level', 'INFO')
        logging.basicConfig(
            level=getattr(logging, log_level),
            format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
            stream=sys.stdout
        )

    def _setup_components(self):
        """Initialize async components"""
        # Cache setup
        cache_backend = self.config.get('cache_backend', 'memory')
        if cache_backend == 'redis':
            redis_url = self.config.get('redis_url', 'redis://localhost:6379')
            self.cache = RedisCache.from_url(redis_url)
        else:
            self.cache = MemoryCache()

        # Metrics setup
        self.metrics = PrometheusMetrics(namespace='scrapyd')

        # Storage setup
        self.storage = create_storage_backend(self.config)

        # Core components
        self.scheduler = AsyncScheduler(self.config, self.storage, self.cache)
        self.launcher = AsyncLauncher(self.config, self.storage, self.metrics)
        self.poller = AsyncPoller(self.config, self.scheduler, self.launcher)

        # Store components in app for access in handlers
        self.app['config'] = self.config
        self.app['cache'] = self.cache
        self.app['metrics'] = self.metrics
        self.app['scheduler'] = self.scheduler
        self.app['launcher'] = self.launcher
        self.app['poller'] = self.poller
        self.app['storage'] = self.storage

    def _setup_middleware(self):
        """Setup middleware stack"""
        # Normalize paths (remove trailing slashes)
        self.app.middlewares.append(normalize_path_middleware(append_slash=False))

        # Error handling middleware
        self.app.middlewares.append(self._error_middleware)

        # Metrics middleware
        self.app.middlewares.append(self._metrics_middleware)

        # Cache middleware
        self.app.middlewares.append(self._cache_middleware)

        # Rate limiting middleware
        if self.config.getbool('rate_limiting_enabled', False):
            self.app.middlewares.append(self._rate_limit_middleware)

        # Authentication middleware
        if self.config.get('auth_enabled', False):
            self.app.middlewares.append(self._auth_middleware)

    def _setup_routes(self):
        """Setup API routes"""
        from scrapyd.async_webservice import setup_routes
        setup_routes(self.app)

    def _setup_cors(self):
        """Setup CORS for cross-origin requests"""
        cors = aiohttp_cors.setup(self.app, defaults={
            "*": aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
                allow_methods="*"
            )
        })

        # Add CORS to all routes
        for route in list(self.app.router.routes()):
            cors.add(route)

    @web.middleware
    async def _error_middleware(self, request, handler):
        """Handle errors and return proper JSON responses"""
        try:
            return await handler(request)
        except web.HTTPException as ex:
            return web.json_response({
                'status': 'error',
                'message': ex.reason,
                'code': ex.status
            }, status=ex.status)
        except Exception as e:
            logger.exception(f"Unhandled error in {request.path}")
            self.metrics.error_count.labels(
                endpoint=request.path,
                error_type=type(e).__name__
            ).inc()
            return web.json_response({
                'status': 'error',
                'message': 'Internal server error',
                'code': 500
            }, status=500)

    @web.middleware
    async def _metrics_middleware(self, request, handler):
        """Collect metrics for requests"""
        start_time = time.time()

        try:
            response = await handler(request)
            status = response.status
        except web.HTTPException as ex:
            status = ex.status
            raise
        except Exception:
            status = 500
            raise
        finally:
            duration = time.time() - start_time
            self.metrics.request_count.labels(
                method=request.method,
                endpoint=request.path,
                status=status
            ).inc()
            self.metrics.request_duration.labels(
                method=request.method,
                endpoint=request.path
            ).observe(duration)

        return response

    @web.middleware
    async def _cache_middleware(self, request, handler):
        """Handle response caching"""
        if request.method != 'GET':
            return await handler(request)

        # Check if endpoint should be cached
        cacheable_endpoints = ['/listprojects.json', '/listspiders.json']
        if request.path not in cacheable_endpoints:
            return await handler(request)

        # Generate cache key
        cache_key = f"response:{request.path}:{hash(str(sorted(request.query.items())))}"

        # Try to get from cache
        cached_response = await self.cache.get(cache_key)
        if cached_response:
            self.metrics.cache_hits.labels(endpoint=request.path).inc()
            return web.json_response(cached_response)

        # Execute handler and cache result
        response = await handler(request)
        if response.status == 200 and response.content_type == 'application/json':
            try:
                response_data = await response.json()
                await self.cache.set(cache_key, response_data, ttl=300)  # 5 minutes
                self.metrics.cache_misses.labels(endpoint=request.path).inc()
            except Exception as e:
                logger.warning(f"Failed to cache response: {e}")

        return response

    @web.middleware
    async def _rate_limit_middleware(self, request, handler):
        """Basic rate limiting based on IP"""
        client_ip = request.remote
        rate_limit_key = f"rate_limit:{client_ip}"

        # Get current request count
        current_count = await self.cache.get(rate_limit_key) or 0
        max_requests = self.config.getint('rate_limit_max_requests', 100)
        window_seconds = self.config.getint('rate_limit_window', 60)

        if current_count >= max_requests:
            raise web.HTTPTooManyRequests(
                text='Rate limit exceeded',
                headers={'Retry-After': str(window_seconds)}
            )

        # Increment counter
        await self.cache.set(rate_limit_key, current_count + 1, ttl=window_seconds)

        return await handler(request)

    @web.middleware
    async def _auth_middleware(self, request, handler):
        """Handle authentication"""
        # Skip auth for health check and metrics endpoints
        public_endpoints = ['/health', '/metrics', '/daemonstatus.json']
        if request.path in public_endpoints:
            return await handler(request)

        # Check for API key or basic auth
        auth_header = request.headers.get('Authorization', '')
        if not auth_header:
            raise web.HTTPUnauthorized(text='Authentication required')

        if auth_header.startswith('Bearer '):
            # API key authentication
            api_key = auth_header[7:]
            valid_keys = self.config.get('api_keys', [])
            if api_key not in valid_keys:
                raise web.HTTPUnauthorized(text='Invalid API key')
        elif auth_header.startswith('Basic '):
            # Basic authentication
            import base64
            try:
                credentials = base64.b64decode(auth_header[6:]).decode('utf-8')
                username, password = credentials.split(':', 1)

                valid_username = self.config.get('auth_username')
                valid_password = self.config.get('auth_password')

                if username != valid_username or password != valid_password:
                    raise web.HTTPUnauthorized(text='Invalid credentials')
            except Exception:
                raise web.HTTPUnauthorized(text='Invalid authentication format')
        else:
            raise web.HTTPUnauthorized(text='Unsupported authentication method')

        return await handler(request)

    async def startup(self):
        """Initialize application components"""
        logger.info("Starting AsyncScrapyd application...")

        # Initialize cache
        if hasattr(self.cache, 'connect'):
            await self.cache.connect()

        # Initialize storage
        if hasattr(self.storage, 'connect'):
            await self.storage.connect()

        # Start background tasks
        await self._start_background_tasks()

        logger.info("AsyncScrapyd startup complete")

    async def shutdown(self):
        """Cleanup application components"""
        logger.info("Shutting down AsyncScrapyd application...")

        # Signal shutdown to background tasks
        self.shutdown_event.set()

        # Stop background tasks
        await self._stop_background_tasks()

        # Cleanup components
        if hasattr(self.launcher, 'shutdown'):
            await self.launcher.shutdown()

        if hasattr(self.storage, 'disconnect'):
            await self.storage.disconnect()

        if hasattr(self.cache, 'disconnect'):
            await self.cache.disconnect()

        logger.info("AsyncScrapyd shutdown complete")

    async def _start_background_tasks(self):
        """Start background tasks"""
        # Job polling task
        poll_task = asyncio.create_task(self._poll_jobs())
        self.background_tasks.add(poll_task)
        poll_task.add_done_callback(self.background_tasks.discard)

        # Metrics collection task
        metrics_task = asyncio.create_task(self._collect_metrics())
        self.background_tasks.add(metrics_task)
        metrics_task.add_done_callback(self.background_tasks.discard)

        # Cache cleanup task
        cache_cleanup_task = asyncio.create_task(self._cleanup_cache())
        self.background_tasks.add(cache_cleanup_task)
        cache_cleanup_task.add_done_callback(self.background_tasks.discard)

        # Health check task
        health_task = asyncio.create_task(self._health_check())
        self.background_tasks.add(health_task)
        health_task.add_done_callback(self.background_tasks.discard)

    async def _stop_background_tasks(self):
        """Stop all background tasks"""
        for task in self.background_tasks:
            task.cancel()

        if self.background_tasks:
            await asyncio.gather(*self.background_tasks, return_exceptions=True)

    async def _poll_jobs(self):
        """Background task to poll for pending jobs"""
        poll_interval = self.config.getfloat('poll_interval', 5.0)

        while not self.shutdown_event.is_set():
            try:
                await self.poller.poll()
            except Exception as e:
                logger.error(f"Error in job polling: {e}")

            try:
                await asyncio.wait_for(
                    self.shutdown_event.wait(),
                    timeout=poll_interval
                )
                break  # Shutdown requested
            except asyncio.TimeoutError:
                continue  # Continue polling

    async def _collect_metrics(self):
        """Background task to collect system metrics"""
        while not self.shutdown_event.is_set():
            try:
                # Collect system metrics
                await self._update_system_metrics()

                # Collect job metrics
                await self._update_job_metrics()

            except Exception as e:
                logger.error(f"Error collecting metrics: {e}")

            try:
                await asyncio.wait_for(
                    self.shutdown_event.wait(),
                    timeout=60  # Update every minute
                )
                break
            except asyncio.TimeoutError:
                continue

    async def _cleanup_cache(self):
        """Background task to cleanup expired cache entries"""
        while not self.shutdown_event.is_set():
            try:
                if hasattr(self.cache, 'cleanup_expired'):
                    await self.cache.cleanup_expired()
            except Exception as e:
                logger.error(f"Error cleaning up cache: {e}")

            try:
                await asyncio.wait_for(
                    self.shutdown_event.wait(),
                    timeout=3600  # Cleanup every hour
                )
                break
            except asyncio.TimeoutError:
                continue

    async def _health_check(self):
        """Background task to perform health checks"""
        while not self.shutdown_event.is_set():
            try:
                # Check storage health
                storage_healthy = await self._check_storage_health()

                # Check cache health
                cache_healthy = await self._check_cache_health()

                # Update health metrics
                self.metrics.health_status.labels(component='storage').set(
                    1 if storage_healthy else 0
                )
                self.metrics.health_status.labels(component='cache').set(
                    1 if cache_healthy else 0
                )

            except Exception as e:
                logger.error(f"Error in health check: {e}")

            try:
                await asyncio.wait_for(
                    self.shutdown_event.wait(),
                    timeout=30  # Check every 30 seconds
                )
                break
            except asyncio.TimeoutError:
                continue

    async def _update_system_metrics(self):
        """Update system resource metrics"""
        import psutil

        # CPU usage
        cpu_percent = psutil.cpu_percent()
        self.metrics.system_cpu_usage.set(cpu_percent)

        # Memory usage
        memory = psutil.virtual_memory()
        self.metrics.system_memory_usage.set(memory.percent)

        # Disk usage
        disk = psutil.disk_usage('/')
        self.metrics.system_disk_usage.set(disk.percent)

        # Process metrics
        process = psutil.Process()
        self.metrics.process_memory_bytes.set(process.memory_info().rss)
        self.metrics.process_cpu_percent.set(process.cpu_percent())

    async def _update_job_metrics(self):
        """Update job-related metrics"""
        try:
            # Get job statistics
            pending_count = await self.scheduler.get_pending_count()
            running_count = len(self.launcher.get_running_jobs())

            self.metrics.pending_jobs.set(pending_count)
            self.metrics.running_jobs.set(running_count)

        except Exception as e:
            logger.error(f"Error updating job metrics: {e}")

    async def _check_storage_health(self) -> bool:
        """Check if storage backend is healthy"""
        try:
            if hasattr(self.storage, 'health_check'):
                return await self.storage.health_check()
            return True
        except Exception:
            return False

    async def _check_cache_health(self) -> bool:
        """Check if cache backend is healthy"""
        try:
            if hasattr(self.cache, 'health_check'):
                return await self.cache.health_check()
            return True
        except Exception:
            return False


def create_app(config: Optional[Config] = None) -> web.Application:
    """Create and configure AsyncScrapyd application"""
    if config is None:
        config = Config()

    async_app = AsyncScrapydApp(config)

    # Setup startup and cleanup handlers
    async def startup_handler(app):
        await async_app.startup()

    async def cleanup_handler(app):
        await async_app.shutdown()

    async_app.app.on_startup.append(startup_handler)
    async_app.app.on_cleanup.append(cleanup_handler)

    return async_app.app


def run_app(config: Optional[Config] = None, **kwargs):
    """Run AsyncScrapyd application"""
    if config is None:
        config = Config()

    app = create_app(config)

    # Setup signal handlers for graceful shutdown
    def signal_handler(sig, frame):
        logger.info(f"Received signal {sig}, initiating shutdown...")
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    # Configure web runner
    host = config.get('bind_address', '127.0.0.1')
    port = config.getint('http_port', 6800)

    try:
        web.run_app(
            app,
            host=host,
            port=port,
            access_log=logger,
            **kwargs
        )
    except KeyboardInterrupt:
        logger.info("Application shutdown requested")


if __name__ == '__main__':
    config = Config()
    run_app(config)