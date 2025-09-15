"""
Async Web Service Handlers

High-performance async implementations of Scrapyd API endpoints using aiohttp.
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime
from typing import Dict, Any, Optional

from aiohttp import web, hdrs
from aiohttp.web_exceptions import HTTPBadRequest, HTTPNotFound, HTTPInternalServerError

logger = logging.getLogger(__name__)


class AsyncWebService:
    """Base class for async web service handlers"""

    def __init__(self, app: web.Application):
        self.app = app
        self.config = app['config']
        self.cache = app['cache']
        self.metrics = app['metrics']
        self.scheduler = app['scheduler']
        self.launcher = app['launcher']
        self.storage = app['storage']

    def json_response(self, data: Dict[str, Any], status: int = 200) -> web.Response:
        """Create JSON response"""
        return web.json_response(data, status=status)

    def error_response(self, message: str, status: int = 400) -> web.Response:
        """Create error response"""
        return self.json_response({
            'status': 'error',
            'message': message
        }, status=status)


class DaemonStatusHandler(AsyncWebService):
    """Handler for /daemonstatus.json endpoint"""

    async def handle(self, request: web.Request) -> web.Response:
        """Get daemon status"""
        try:
            # Get basic statistics
            pending_count = await self.scheduler.get_pending_count()
            running_jobs = self.launcher.get_running_jobs()
            running_count = len(running_jobs)

            # Get finished count from storage
            finished_count = 0
            if hasattr(self.storage, 'get_finished_count'):
                finished_count = await self.storage.get_finished_count()

            # Node name for distributed setups
            node_name = self.config.get('node_name', 'default')

            response_data = {
                'status': 'ok',
                'pending': pending_count,
                'running': running_count,
                'finished': finished_count,
                'node_name': node_name
            }

            return self.json_response(response_data)

        except Exception as e:
            logger.error(f"Error getting daemon status: {e}")
            return self.error_response("Failed to get daemon status", 500)


class ScheduleHandler(AsyncWebService):
    """Handler for /schedule.json endpoint"""

    async def handle(self, request: web.Request) -> web.Response:
        """Schedule a spider"""
        try:
            # Parse form data
            data = await request.post()

            # Validate required parameters
            project = data.get('project')
            spider = data.get('spider')

            if not project:
                return self.error_response("'project' parameter is required")

            if not spider:
                return self.error_response("'spider' parameter is required")

            # Optional parameters
            version = data.get('version')
            priority = float(data.get('priority', 0))
            job_id = data.get('jobid') or str(uuid.uuid4())

            # Extract settings (parameters starting with 'setting')
            settings = {}
            for key, value in data.items():
                if key.startswith('setting'):
                    setting_name = key.replace('setting', '', 1).lstrip('.')
                    if setting_name:
                        settings[setting_name] = value

            # Extract spider arguments (all other parameters)
            args = {}
            excluded_params = {'project', 'spider', 'version', 'priority', 'jobid'}
            for key, value in data.items():
                if key not in excluded_params and not key.startswith('setting'):
                    args[key] = value

            # Validate spider exists
            if not await self._spider_exists(project, spider, version):
                return self.error_response(f"spider '{spider}' not found")

            # Create job data
            job_data = {
                'job_id': job_id,
                'project': project,
                'spider': spider,
                'version': version,
                'priority': priority,
                'settings': settings,
                'args': args,
                'scheduled_time': datetime.utcnow()
            }

            # Schedule the spider
            await self.scheduler.schedule(job_data)

            # Record metrics
            if self.metrics:
                self.metrics.record_spider_scheduled(project, spider)

            # Node name for response
            node_name = self.config.get('node_name', 'default')

            return self.json_response({
                'status': 'ok',
                'jobid': job_id,
                'node_name': node_name
            })

        except Exception as e:
            logger.error(f"Error scheduling spider: {e}")
            return self.error_response(f"Failed to schedule spider: {str(e)}", 500)

    async def _spider_exists(self, project: str, spider: str, version: Optional[str] = None) -> bool:
        """Check if spider exists in project"""
        try:
            if hasattr(self.storage, 'spider_exists'):
                return await self.storage.spider_exists(project, spider, version)

            # Fallback: check spider list
            spider_list = await self._get_spider_list(project, version)
            return spider in spider_list

        except Exception as e:
            logger.error(f"Error checking spider existence: {e}")
            return False

    async def _get_spider_list(self, project: str, version: Optional[str] = None) -> list:
        """Get list of spiders for project"""
        cache_key = f"spiders:{project}:{version or 'latest'}"

        # Try cache first
        cached_list = await self.cache.get(cache_key)
        if cached_list is not None:
            return cached_list

        # Get from storage
        try:
            if hasattr(self.storage, 'list_spiders'):
                spider_list = await self.storage.list_spiders(project, version)
            else:
                spider_list = []

            # Cache for 5 minutes
            await self.cache.set(cache_key, spider_list, ttl=300)
            return spider_list

        except Exception as e:
            logger.error(f"Error getting spider list: {e}")
            return []


class CancelHandler(AsyncWebService):
    """Handler for /cancel.json endpoint"""

    async def handle(self, request: web.Request) -> web.Response:
        """Cancel a running spider"""
        try:
            data = await request.post()

            project = data.get('project')
            job_id = data.get('job')

            if not project:
                return self.error_response("'project' parameter is required")

            if not job_id:
                return self.error_response("'job' parameter is required")

            # Cancel the job
            success = await self.launcher.cancel_spider(job_id)

            if success:
                # Update metrics
                if self.metrics:
                    # Get spider name for metrics (if available)
                    running_jobs = self.launcher.get_running_jobs()
                    spider = next((job['spider'] for job in running_jobs if job['id'] == job_id), 'unknown')
                    self.metrics.record_spider_cancelled(project, spider)

                return self.json_response({
                    'status': 'ok',
                    'prevstate': 'running'
                })
            else:
                return self.json_response({
                    'status': 'ok',
                    'prevstate': 'finished'
                })

        except Exception as e:
            logger.error(f"Error cancelling job: {e}")
            return self.error_response(f"Failed to cancel job: {str(e)}", 500)


class ListProjectsHandler(AsyncWebService):
    """Handler for /listprojects.json endpoint"""

    async def handle(self, request: web.Request) -> web.Response:
        """List all projects"""
        try:
            cache_key = "projects:list"

            # Try cache first
            cached_projects = await self.cache.get(cache_key)
            if cached_projects is not None:
                return self.json_response({
                    'status': 'ok',
                    'projects': cached_projects
                })

            # Get from storage
            if hasattr(self.storage, 'list_projects'):
                projects = await self.storage.list_projects()
            else:
                projects = []

            # Cache for 5 minutes
            await self.cache.set(cache_key, projects, ttl=300)

            return self.json_response({
                'status': 'ok',
                'projects': projects
            })

        except Exception as e:
            logger.error(f"Error listing projects: {e}")
            return self.error_response("Failed to list projects", 500)


class ListSpidersHandler(AsyncWebService):
    """Handler for /listspiders.json endpoint"""

    async def handle(self, request: web.Request) -> web.Response:
        """List spiders in a project"""
        try:
            project = request.query.get('project')
            version = request.query.get('version')

            if not project:
                return self.error_response("'project' parameter is required")

            cache_key = f"spiders:{project}:{version or 'latest'}"

            # Try cache first
            cached_spiders = await self.cache.get(cache_key)
            if cached_spiders is not None:
                return self.json_response({
                    'status': 'ok',
                    'spiders': cached_spiders
                })

            # Get from storage
            if hasattr(self.storage, 'list_spiders'):
                spiders = await self.storage.list_spiders(project, version)
            else:
                spiders = []

            # Cache for 5 minutes
            await self.cache.set(cache_key, spiders, ttl=300)

            return self.json_response({
                'status': 'ok',
                'spiders': spiders
            })

        except Exception as e:
            logger.error(f"Error listing spiders: {e}")
            return self.error_response("Failed to list spiders", 500)


class ListJobsHandler(AsyncWebService):
    """Handler for /listjobs.json endpoint"""

    async def handle(self, request: web.Request) -> web.Response:
        """List jobs for a project"""
        try:
            project = request.query.get('project')

            if not project:
                return self.error_response("'project' parameter is required")

            # Get pending jobs
            pending_jobs = []
            if hasattr(self.scheduler, 'list_pending'):
                pending_jobs = await self.scheduler.list_pending(project)

            # Get running jobs
            running_jobs = [
                job for job in self.launcher.get_running_jobs()
                if job['project'] == project
            ]

            # Get finished jobs
            finished_jobs = []
            if hasattr(self.storage, 'list_finished'):
                finished_jobs = await self.storage.list_finished(project)

            return self.json_response({
                'status': 'ok',
                'pending': pending_jobs,
                'running': running_jobs,
                'finished': finished_jobs
            })

        except Exception as e:
            logger.error(f"Error listing jobs: {e}")
            return self.error_response("Failed to list jobs", 500)


class MetricsHandler(AsyncWebService):
    """Handler for /metrics endpoint (Prometheus format)"""

    async def handle(self, request: web.Request) -> web.Response:
        """Return Prometheus metrics"""
        try:
            if not self.metrics:
                return web.Response(
                    text="# Metrics not available\n",
                    content_type="text/plain"
                )

            metrics_text = self.metrics.generate_metrics()
            content_type = self.metrics.get_content_type()

            return web.Response(
                text=metrics_text,
                content_type=content_type
            )

        except Exception as e:
            logger.error(f"Error generating metrics: {e}")
            return web.Response(
                text=f"# Error generating metrics: {e}\n",
                content_type="text/plain",
                status=500
            )


class HealthHandler(AsyncWebService):
    """Handler for /health endpoint"""

    async def handle(self, request: web.Request) -> web.Response:
        """Health check endpoint"""
        try:
            health_status = {
                'status': 'healthy',
                'timestamp': datetime.utcnow().isoformat(),
                'components': {}
            }

            # Check cache health
            if self.cache:
                cache_healthy = await self.cache.health_check()
                health_status['components']['cache'] = 'healthy' if cache_healthy else 'unhealthy'

            # Check storage health
            if self.storage and hasattr(self.storage, 'health_check'):
                storage_healthy = await self.storage.health_check()
                health_status['components']['storage'] = 'healthy' if storage_healthy else 'unhealthy'

            # Check scheduler health
            if self.scheduler and hasattr(self.scheduler, 'health_check'):
                scheduler_healthy = await self.scheduler.health_check()
                health_status['components']['scheduler'] = 'healthy' if scheduler_healthy else 'unhealthy'

            # Overall health
            all_healthy = all(
                status == 'healthy'
                for status in health_status['components'].values()
            )

            if not all_healthy:
                health_status['status'] = 'unhealthy'
                return self.json_response(health_status, status=503)

            return self.json_response(health_status)

        except Exception as e:
            logger.error(f"Error in health check: {e}")
            return self.json_response({
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }, status=503)


class LogsHandler(AsyncWebService):
    """Handler for /logs endpoints"""

    async def handle_log_list(self, request: web.Request) -> web.Response:
        """List available log files"""
        try:
            project = request.match_info.get('project')
            spider = request.match_info.get('spider')

            if not project:
                return self.error_response("Project parameter is required")

            # Get log files from storage
            if hasattr(self.storage, 'list_log_files'):
                log_files = await self.storage.list_log_files(project, spider)
            else:
                log_files = []

            return self.json_response({
                'status': 'ok',
                'logs': log_files
            })

        except Exception as e:
            logger.error(f"Error listing log files: {e}")
            return self.error_response("Failed to list log files", 500)

    async def handle_log_download(self, request: web.Request) -> web.Response:
        """Download log file"""
        try:
            project = request.match_info.get('project')
            spider = request.match_info.get('spider')
            job_id = request.match_info.get('job_id')

            if not all([project, spider, job_id]):
                return self.error_response("Missing required parameters")

            # Get log content from storage
            if hasattr(self.storage, 'get_log_content'):
                log_content = await self.storage.get_log_content(project, spider, job_id)
                if log_content is None:
                    raise HTTPNotFound(text="Log file not found")

                return web.Response(
                    body=log_content,
                    content_type='text/plain',
                    headers={
                        'Content-Disposition': f'attachment; filename="{job_id}.log"'
                    }
                )
            else:
                raise HTTPNotFound(text="Log access not supported")

        except HTTPNotFound:
            raise
        except Exception as e:
            logger.error(f"Error downloading log file: {e}")
            return self.error_response("Failed to download log file", 500)


def setup_routes(app: web.Application):
    """Setup all API routes"""

    # Create handler instances
    daemon_status = DaemonStatusHandler(app)
    schedule = ScheduleHandler(app)
    cancel = CancelHandler(app)
    list_projects = ListProjectsHandler(app)
    list_spiders = ListSpidersHandler(app)
    list_jobs = ListJobsHandler(app)
    metrics = MetricsHandler(app)
    health = HealthHandler(app)
    logs = LogsHandler(app)

    # API routes
    app.router.add_get('/daemonstatus.json', daemon_status.handle)
    app.router.add_post('/schedule.json', schedule.handle)
    app.router.add_post('/cancel.json', cancel.handle)
    app.router.add_get('/listprojects.json', list_projects.handle)
    app.router.add_get('/listspiders.json', list_spiders.handle)
    app.router.add_get('/listjobs.json', list_jobs.handle)

    # Health and metrics
    app.router.add_get('/health', health.handle)
    app.router.add_get('/metrics', metrics.handle)

    # Log endpoints
    app.router.add_get('/logs/{project}/', logs.handle_log_list)
    app.router.add_get('/logs/{project}/{spider}/', logs.handle_log_list)
    app.router.add_get('/logs/{project}/{spider}/{job_id}.log', logs.handle_log_download)

    # Root endpoint (basic info)
    async def root_handler(request):
        return web.json_response({
            'status': 'ok',
            'service': 'scrapyd',
            'version': '2.0.0-async',
            'endpoints': [
                '/daemonstatus.json',
                '/schedule.json',
                '/cancel.json',
                '/listprojects.json',
                '/listspiders.json',
                '/listjobs.json',
                '/health',
                '/metrics',
                '/logs/'
            ]
        })

    app.router.add_get('/', root_handler)

    logger.info("API routes configured")