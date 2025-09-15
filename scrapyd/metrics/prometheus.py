"""
Prometheus Metrics Integration

Comprehensive metrics collection for Scrapyd using Prometheus client library.
"""

import time
import logging
from typing import Dict, Any, Optional
from datetime import datetime

try:
    from prometheus_client import (
        Counter, Gauge, Histogram, Summary, Info,
        CollectorRegistry, generate_latest, CONTENT_TYPE_LATEST
    )
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

logger = logging.getLogger(__name__)


class PrometheusMetrics:
    """Prometheus metrics collector for Scrapyd"""

    def __init__(self, namespace: str = 'scrapyd', registry: Optional[CollectorRegistry] = None):
        """
        Initialize Prometheus metrics

        Args:
            namespace: Metric namespace prefix
            registry: Custom registry (uses default if None)
        """
        if not PROMETHEUS_AVAILABLE:
            raise ImportError("prometheus_client package is required for PrometheusMetrics")

        self.namespace = namespace
        self.registry = registry or CollectorRegistry()

        # Initialize all metrics
        self._init_request_metrics()
        self._init_spider_metrics()
        self._init_system_metrics()
        self._init_cache_metrics()
        self._init_queue_metrics()
        self._init_process_metrics()
        self._init_error_metrics()
        self._init_performance_metrics()

        logger.info(f"Prometheus metrics initialized with namespace: {namespace}")

    def _init_request_metrics(self):
        """Initialize HTTP request metrics"""
        self.request_count = Counter(
            'http_requests_total',
            'Total HTTP requests',
            ['method', 'endpoint', 'status'],
            namespace=self.namespace,
            registry=self.registry
        )

        self.request_duration = Histogram(
            'http_request_duration_seconds',
            'HTTP request duration in seconds',
            ['method', 'endpoint'],
            namespace=self.namespace,
            registry=self.registry,
            buckets=(.005, .01, .025, .05, .075, .1, .25, .5, .75, 1.0, 2.5, 5.0, 7.5, 10.0, float('inf'))
        )

        self.request_size = Summary(
            'http_request_size_bytes',
            'HTTP request size in bytes',
            ['method', 'endpoint'],
            namespace=self.namespace,
            registry=self.registry
        )

        self.response_size = Summary(
            'http_response_size_bytes',
            'HTTP response size in bytes',
            ['method', 'endpoint'],
            namespace=self.namespace,
            registry=self.registry
        )

    def _init_spider_metrics(self):
        """Initialize spider execution metrics"""
        self.spiders_scheduled = Counter(
            'spiders_scheduled_total',
            'Total spiders scheduled',
            ['project', 'spider'],
            namespace=self.namespace,
            registry=self.registry
        )

        self.spiders_started = Counter(
            'spiders_started_total',
            'Total spiders started',
            ['project', 'spider'],
            namespace=self.namespace,
            registry=self.registry
        )

        self.spiders_completed = Counter(
            'spiders_completed_total',
            'Total spiders completed successfully',
            ['project', 'spider'],
            namespace=self.namespace,
            registry=self.registry
        )

        self.spiders_failed = Counter(
            'spiders_failed_total',
            'Total spiders failed',
            ['project', 'spider', 'error'],
            namespace=self.namespace,
            registry=self.registry
        )

        self.spiders_cancelled = Counter(
            'spiders_cancelled_total',
            'Total spiders cancelled',
            ['project', 'spider'],
            namespace=self.namespace,
            registry=self.registry
        )

        self.spider_execution_time = Histogram(
            'spider_execution_duration_seconds',
            'Spider execution duration in seconds',
            ['project', 'spider'],
            namespace=self.namespace,
            registry=self.registry,
            buckets=(1, 5, 10, 30, 60, 300, 600, 1800, 3600, 7200, float('inf'))
        )

        self.spider_items_scraped = Counter(
            'spider_items_scraped_total',
            'Total items scraped by spiders',
            ['project', 'spider'],
            namespace=self.namespace,
            registry=self.registry
        )

        self.spider_pages_crawled = Counter(
            'spider_pages_crawled_total',
            'Total pages crawled by spiders',
            ['project', 'spider'],
            namespace=self.namespace,
            registry=self.registry
        )

    def _init_system_metrics(self):
        """Initialize system resource metrics"""
        self.system_cpu_usage = Gauge(
            'system_cpu_usage_percent',
            'System CPU usage percentage',
            namespace=self.namespace,
            registry=self.registry
        )

        self.system_memory_usage = Gauge(
            'system_memory_usage_percent',
            'System memory usage percentage',
            namespace=self.namespace,
            registry=self.registry
        )

        self.system_disk_usage = Gauge(
            'system_disk_usage_percent',
            'System disk usage percentage',
            ['mount_point'],
            namespace=self.namespace,
            registry=self.registry
        )

        self.system_load_average = Gauge(
            'system_load_average',
            'System load average',
            ['period'],
            namespace=self.namespace,
            registry=self.registry
        )

    def _init_cache_metrics(self):
        """Initialize cache metrics"""
        self.cache_hits = Counter(
            'cache_hits_total',
            'Total cache hits',
            ['endpoint'],
            namespace=self.namespace,
            registry=self.registry
        )

        self.cache_misses = Counter(
            'cache_misses_total',
            'Total cache misses',
            ['endpoint'],
            namespace=self.namespace,
            registry=self.registry
        )

        self.cache_size = Gauge(
            'cache_size_entries',
            'Current cache size in entries',
            ['type'],
            namespace=self.namespace,
            registry=self.registry
        )

        self.cache_memory_usage = Gauge(
            'cache_memory_usage_bytes',
            'Cache memory usage in bytes',
            ['type'],
            namespace=self.namespace,
            registry=self.registry
        )

        self.cache_operation_duration = Histogram(
            'cache_operation_duration_seconds',
            'Cache operation duration in seconds',
            ['operation', 'type'],
            namespace=self.namespace,
            registry=self.registry
        )

    def _init_queue_metrics(self):
        """Initialize job queue metrics"""
        self.pending_jobs = Gauge(
            'pending_jobs',
            'Number of pending jobs in queue',
            ['project'],
            namespace=self.namespace,
            registry=self.registry
        )

        self.running_jobs = Gauge(
            'running_jobs',
            'Number of currently running jobs',
            ['project'],
            namespace=self.namespace,
            registry=self.registry
        )

        self.finished_jobs = Gauge(
            'finished_jobs',
            'Number of finished jobs',
            ['project'],
            namespace=self.namespace,
            registry=self.registry
        )

        self.queue_wait_time = Histogram(
            'queue_wait_duration_seconds',
            'Time jobs spend waiting in queue',
            ['project'],
            namespace=self.namespace,
            registry=self.registry
        )

    def _init_process_metrics(self):
        """Initialize process management metrics"""
        self.active_processes = Gauge(
            'active_processes',
            'Number of active spider processes',
            namespace=self.namespace,
            registry=self.registry
        )

        self.process_startup_time = Histogram(
            'process_startup_duration_seconds',
            'Process startup duration in seconds',
            namespace=self.namespace,
            registry=self.registry
        )

        self.process_memory_bytes = Gauge(
            'process_memory_usage_bytes',
            'Process memory usage in bytes',
            ['pid'],
            namespace=self.namespace,
            registry=self.registry
        )

        self.process_cpu_percent = Gauge(
            'process_cpu_usage_percent',
            'Process CPU usage percentage',
            ['pid'],
            namespace=self.namespace,
            registry=self.registry
        )

        self.process_pool_size = Gauge(
            'process_pool_size',
            'Size of process pool',
            namespace=self.namespace,
            registry=self.registry
        )

    def _init_error_metrics(self):
        """Initialize error tracking metrics"""
        self.error_count = Counter(
            'errors_total',
            'Total errors',
            ['endpoint', 'error_type'],
            namespace=self.namespace,
            registry=self.registry
        )

        self.critical_errors = Counter(
            'critical_errors_total',
            'Total critical errors',
            ['component', 'error_type'],
            namespace=self.namespace,
            registry=self.registry
        )

        self.timeouts = Counter(
            'timeouts_total',
            'Total timeouts',
            ['component', 'operation'],
            namespace=self.namespace,
            registry=self.registry
        )

    def _init_performance_metrics(self):
        """Initialize performance metrics"""
        self.throughput = Gauge(
            'throughput_items_per_second',
            'Current throughput in items per second',
            ['project', 'spider'],
            namespace=self.namespace,
            registry=self.registry
        )

        self.connection_pool_active = Gauge(
            'connection_pool_active',
            'Active connections in pool',
            ['pool_name'],
            namespace=self.namespace,
            registry=self.registry
        )

        self.connection_pool_idle = Gauge(
            'connection_pool_idle',
            'Idle connections in pool',
            ['pool_name'],
            namespace=self.namespace,
            registry=self.registry
        )

        self.health_status = Gauge(
            'health_status',
            'Health status (1=healthy, 0=unhealthy)',
            ['component'],
            namespace=self.namespace,
            registry=self.registry
        )

        # Application info
        self.info = Info(
            'info',
            'Application information',
            namespace=self.namespace,
            registry=self.registry
        )

    def set_app_info(self, version: str, **kwargs):
        """Set application information"""
        info_data = {
            'version': version,
            'start_time': str(datetime.utcnow()),
            **kwargs
        }
        self.info.info(info_data)

    def record_request(self, method: str, endpoint: str, status: int, duration: float,
                      request_size: Optional[int] = None, response_size: Optional[int] = None):
        """Record HTTP request metrics"""
        self.request_count.labels(method=method, endpoint=endpoint, status=status).inc()
        self.request_duration.labels(method=method, endpoint=endpoint).observe(duration)

        if request_size is not None:
            self.request_size.labels(method=method, endpoint=endpoint).observe(request_size)

        if response_size is not None:
            self.response_size.labels(method=method, endpoint=endpoint).observe(response_size)

    def record_spider_scheduled(self, project: str, spider: str):
        """Record spider scheduling"""
        self.spiders_scheduled.labels(project=project, spider=spider).inc()

    def record_spider_started(self, project: str, spider: str):
        """Record spider start"""
        self.spiders_started.labels(project=project, spider=spider).inc()

    def record_spider_completed(self, project: str, spider: str, duration: float,
                               items_scraped: int = 0, pages_crawled: int = 0):
        """Record spider completion"""
        self.spiders_completed.labels(project=project, spider=spider).inc()
        self.spider_execution_time.labels(project=project, spider=spider).observe(duration)

        if items_scraped > 0:
            self.spider_items_scraped.labels(project=project, spider=spider).inc(items_scraped)

        if pages_crawled > 0:
            self.spider_pages_crawled.labels(project=project, spider=spider).inc(pages_crawled)

    def record_spider_failed(self, project: str, spider: str, error_type: str):
        """Record spider failure"""
        self.spiders_failed.labels(project=project, spider=spider, error=error_type).inc()

    def record_spider_cancelled(self, project: str, spider: str):
        """Record spider cancellation"""
        self.spiders_cancelled.labels(project=project, spider=spider).inc()

    def record_cache_hit(self, endpoint: str):
        """Record cache hit"""
        self.cache_hits.labels(endpoint=endpoint).inc()

    def record_cache_miss(self, endpoint: str):
        """Record cache miss"""
        self.cache_misses.labels(endpoint=endpoint).inc()

    def update_cache_stats(self, cache_type: str, size: int, memory_usage: Optional[int] = None):
        """Update cache statistics"""
        self.cache_size.labels(type=cache_type).set(size)
        if memory_usage is not None:
            self.cache_memory_usage.labels(type=cache_type).set(memory_usage)

    def record_cache_operation(self, operation: str, cache_type: str, duration: float):
        """Record cache operation timing"""
        self.cache_operation_duration.labels(operation=operation, type=cache_type).observe(duration)

    def update_queue_stats(self, project: str, pending: int, running: int, finished: int):
        """Update job queue statistics"""
        self.pending_jobs.labels(project=project).set(pending)
        self.running_jobs.labels(project=project).set(running)
        self.finished_jobs.labels(project=project).set(finished)

    def record_queue_wait_time(self, project: str, wait_time: float):
        """Record job queue wait time"""
        self.queue_wait_time.labels(project=project).observe(wait_time)

    def update_system_stats(self, cpu_percent: float, memory_percent: float,
                           disk_usage: Dict[str, float], load_avg: Optional[tuple] = None):
        """Update system resource statistics"""
        self.system_cpu_usage.set(cpu_percent)
        self.system_memory_usage.set(memory_percent)

        for mount_point, usage in disk_usage.items():
            self.system_disk_usage.labels(mount_point=mount_point).set(usage)

        if load_avg:
            periods = ['1m', '5m', '15m']
            for i, period in enumerate(periods):
                if i < len(load_avg):
                    self.system_load_average.labels(period=period).set(load_avg[i])

    def record_error(self, endpoint: str, error_type: str):
        """Record error occurrence"""
        self.error_count.labels(endpoint=endpoint, error_type=error_type).inc()

    def record_critical_error(self, component: str, error_type: str):
        """Record critical error"""
        self.critical_errors.labels(component=component, error_type=error_type).inc()

    def record_timeout(self, component: str, operation: str):
        """Record timeout occurrence"""
        self.timeouts.labels(component=component, operation=operation).inc()

    def update_process_stats(self, active_count: int, pool_size: int):
        """Update process management statistics"""
        self.active_processes.set(active_count)
        self.process_pool_size.set(pool_size)

    def record_process_startup(self, duration: float):
        """Record process startup time"""
        self.process_startup_time.observe(duration)

    def update_process_resources(self, pid: str, memory_bytes: int, cpu_percent: float):
        """Update individual process resource usage"""
        self.process_memory_bytes.labels(pid=pid).set(memory_bytes)
        self.process_cpu_percent.labels(pid=pid).set(cpu_percent)

    def update_connection_pool(self, pool_name: str, active: int, idle: int):
        """Update connection pool statistics"""
        self.connection_pool_active.labels(pool_name=pool_name).set(active)
        self.connection_pool_idle.labels(pool_name=pool_name).set(idle)

    def set_health_status(self, component: str, healthy: bool):
        """Set component health status"""
        self.health_status.labels(component=component).set(1 if healthy else 0)

    def generate_metrics(self) -> str:
        """Generate metrics in Prometheus format"""
        return generate_latest(self.registry).decode('utf-8')

    def get_content_type(self) -> str:
        """Get content type for metrics endpoint"""
        return CONTENT_TYPE_LATEST

    def clear_metrics(self):
        """Clear all metrics (useful for testing)"""
        self.registry.clear()

    def get_metric_families(self):
        """Get all metric families"""
        return list(self.registry.collect())


class NullMetrics:
    """Null metrics implementation when Prometheus is not available"""

    def __init__(self, *args, **kwargs):
        logger.warning("Prometheus client not available, using null metrics")

    def __getattr__(self, name):
        def null_method(*args, **kwargs):
            pass
        return null_method

    def generate_metrics(self) -> str:
        return "# Prometheus client not available\n"

    def get_content_type(self) -> str:
        return "text/plain"


def create_metrics(namespace: str = 'scrapyd', registry: Optional[CollectorRegistry] = None):
    """Create metrics instance, falling back to null metrics if Prometheus unavailable"""
    if PROMETHEUS_AVAILABLE:
        return PrometheusMetrics(namespace=namespace, registry=registry)
    else:
        return NullMetrics(namespace=namespace, registry=registry)