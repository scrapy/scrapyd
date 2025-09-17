"""
Async Spider Launcher

High-performance async implementation of spider process launcher with
improved process management and monitoring.
"""

import asyncio
import os
import signal
import sys
import time
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass
from pathlib import Path

from scrapyd.config import Config
from scrapyd.exceptions import LauncherError
from scrapyd.interfaces import IEnvironment, IJobStorage
from scrapyd.rich_logging import get_rich_logger

logger = get_rich_logger(__name__)


@dataclass
class SpiderProcess:
    """Information about a running spider process"""
    job_id: str
    project: str
    spider: str
    process: asyncio.subprocess.Process
    start_time: datetime
    settings: Dict[str, Any]
    args: Dict[str, Any]
    log_file: Optional[Path] = None
    pid: Optional[int] = None
    status: str = "running"


class AsyncLauncher:
    """Async implementation of spider launcher with process pooling"""

    def __init__(self, config: Config, storage=None, metrics=None):
        self.config = config
        self.storage = storage
        self.metrics = metrics

        # Process management
        self.running_processes: Dict[str, SpiderProcess] = {}
        self.process_slots = asyncio.Semaphore(self._get_max_processes())
        self.cleanup_task: Optional[asyncio.Task] = None

        # Configuration
        self.max_proc = self._get_max_processes()
        self.runner = config.get('runner', 'scrapyd.runner')
        self.logs_dir = Path(config.get('logs_dir', 'logs'))
        self.poll_interval = config.getfloat('process_poll_interval', 1.0)

        # Process reuse pool
        self.process_pool_enabled = config.getbool('process_pool_enabled', False)
        self.process_pool: List[asyncio.subprocess.Process] = []
        self.max_pool_size = config.getint('process_pool_size', 5)

        # Performance monitoring
        self.process_stats = {
            'total_started': 0,
            'total_completed': 0,
            'total_failed': 0,
            'avg_startup_time': 0.0,
            'avg_execution_time': 0.0
        }

        # Start background tasks
        self._start_background_tasks()

    def _get_max_processes(self) -> int:
        """Calculate maximum number of concurrent processes"""
        max_proc = self.config.getint('max_proc', 0)
        if max_proc == 0:
            # Auto-detect based on CPU count
            cpu_count = os.cpu_count() or 1
            max_proc_per_cpu = self.config.getint('max_proc_per_cpu', 4)
            max_proc = cpu_count * max_proc_per_cpu

        return max_proc

    def _start_background_tasks(self):
        """Start background monitoring tasks"""
        self.cleanup_task = asyncio.create_task(self._cleanup_processes())

    async def shutdown(self):
        """Shutdown launcher and cleanup resources"""
        logger.info("Shutting down AsyncLauncher...")

        # Cancel background tasks
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass

        # Terminate all running processes
        await self._terminate_all_processes()

        # Cleanup process pool
        await self._cleanup_process_pool()

        logger.info("AsyncLauncher shutdown complete")

    async def launch_spider(self, job_data: Dict[str, Any]) -> str:
        """Launch a spider asynchronously"""
        job_id = job_data['job_id']
        project = job_data['project']
        spider = job_data['spider']

        logger.info(f"Launching spider {spider} in project {project} (job: {job_id})")

        try:
            # Acquire process slot
            await self.process_slots.acquire()

            start_time = time.time()

            # Prepare environment and command
            env = await self._prepare_environment(job_data)
            cmd = await self._build_command(job_data)

            # Create log file
            log_file = await self._create_log_file(project, spider, job_id)

            # Start process
            process = await self._start_process(cmd, env, log_file)

            startup_time = time.time() - start_time
            self._update_startup_stats(startup_time)

            # Create process info
            spider_process = SpiderProcess(
                job_id=job_id,
                project=project,
                spider=spider,
                process=process,
                start_time=datetime.utcnow(),
                settings=job_data.get('settings', {}),
                args=job_data.get('args', {}),
                log_file=log_file,
                pid=process.pid
            )

            self.running_processes[job_id] = spider_process

            # Update metrics
            if self.metrics:
                self.metrics.spiders_started.labels(project=project, spider=spider).inc()
                self.metrics.active_processes.set(len(self.running_processes))

            # Start monitoring this process
            asyncio.create_task(self._monitor_process(spider_process))

            logger.info(f"Spider {spider} started successfully (PID: {process.pid})")
            return job_id

        except Exception as e:
            # Release slot on error
            self.process_slots.release()
            self.process_stats['total_failed'] += 1

            if self.metrics:
                self.metrics.spiders_failed.labels(
                    project=project,
                    spider=spider,
                    error=type(e).__name__
                ).inc()

            logger.error(f"Failed to launch spider {spider}: {e}")
            raise LauncherError(f"Failed to launch spider: {e}") from e

    async def cancel_spider(self, job_id: str) -> bool:
        """Cancel a running spider"""
        if job_id not in self.running_processes:
            logger.warning(f"Job {job_id} not found in running processes")
            return False

        spider_process = self.running_processes[job_id]
        logger.info(f"Cancelling spider {spider_process.spider} (job: {job_id})")

        try:
            # Send SIGTERM first
            spider_process.process.terminate()

            # Wait for graceful shutdown
            try:
                await asyncio.wait_for(spider_process.process.wait(), timeout=30.0)
            except asyncio.TimeoutError:
                # Force kill if graceful shutdown fails
                logger.warning(f"Force killing job {job_id}")
                spider_process.process.kill()
                await spider_process.process.wait()

            spider_process.status = "cancelled"

            if self.metrics:
                self.metrics.spiders_cancelled.labels(
                    project=spider_process.project,
                    spider=spider_process.spider
                ).inc()

            logger.info(f"Spider {spider_process.spider} cancelled successfully")
            return True

        except Exception as e:
            logger.error(f"Error cancelling spider {job_id}: {e}")
            return False

    def get_running_jobs(self) -> List[Dict[str, Any]]:
        """Get list of currently running jobs"""
        jobs = []
        for job_id, spider_process in self.running_processes.items():
            jobs.append({
                'id': job_id,
                'project': spider_process.project,
                'spider': spider_process.spider,
                'pid': spider_process.pid,
                'start_time': spider_process.start_time.isoformat(),
                'log_url': f'/logs/{spider_process.project}/{spider_process.spider}/{job_id}.log'
            })
        return jobs

    async def _prepare_environment(self, job_data: Dict[str, Any]) -> Dict[str, str]:
        """Prepare environment variables for spider process"""
        env = os.environ.copy()

        # Basic Scrapy environment
        env.update({
            'PYTHONIOENCODING': 'UTF-8',
            'SCRAPY_PROJECT': job_data['project'],
            'SCRAPYD_JOB_ID': job_data['job_id'],
        })

        # Add egg version if specified
        if 'version' in job_data:
            env['SCRAPYD_EGG_VERSION'] = job_data['version']

        # Add custom settings as environment variables
        settings = job_data.get('settings', {})
        for key, value in settings.items():
            env[f'SCRAPY_SETTINGS_{key}'] = str(value)

        return env

    async def _build_command(self, job_data: Dict[str, Any]) -> List[str]:
        """Build command line for spider execution"""
        cmd = [sys.executable, '-m', self.runner, 'crawl']

        # Add spider name
        cmd.append(job_data['spider'])

        # Add settings
        settings = job_data.get('settings', {})
        for key, value in settings.items():
            cmd.extend(['-s', f'{key}={value}'])

        # Add spider arguments
        args = job_data.get('args', {})
        for key, value in args.items():
            cmd.extend(['-a', f'{key}={value}'])

        return cmd

    async def _create_log_file(self, project: str, spider: str, job_id: str) -> Path:
        """Create log file for spider output"""
        log_dir = self.logs_dir / project / spider
        log_dir.mkdir(parents=True, exist_ok=True)

        log_file = log_dir / f'{job_id}.log'
        log_file.touch()

        return log_file

    async def _start_process(self, cmd: List[str], env: Dict[str, str],
                           log_file: Path) -> asyncio.subprocess.Process:
        """Start spider subprocess"""
        if self.process_pool_enabled and self.process_pool:
            # Try to reuse process from pool
            process = self.process_pool.pop()
            logger.debug("Reusing process from pool")
        else:
            # Create new process
            with open(log_file, 'wb') as log_fp:
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    env=env,
                    stdout=log_fp,
                    stderr=asyncio.subprocess.STDOUT,
                    cwd=None
                )

        return process

    async def _monitor_process(self, spider_process: SpiderProcess):
        """Monitor a spider process until completion"""
        job_id = spider_process.job_id

        try:
            # Wait for process to complete
            exit_code = await spider_process.process.wait()

            execution_time = (datetime.utcnow() - spider_process.start_time).total_seconds()
            self._update_execution_stats(execution_time)

            # Update process status
            if exit_code == 0:
                spider_process.status = "finished"
                self.process_stats['total_completed'] += 1

                if self.metrics:
                    self.metrics.spiders_completed.labels(
                        project=spider_process.project,
                        spider=spider_process.spider
                    ).inc()
                    self.metrics.spider_execution_time.labels(
                        project=spider_process.project,
                        spider=spider_process.spider
                    ).observe(execution_time)

                logger.info(f"Spider {spider_process.spider} completed successfully "
                           f"(job: {job_id}, duration: {execution_time:.2f}s)")

            else:
                spider_process.status = "failed"
                self.process_stats['total_failed'] += 1

                if self.metrics:
                    self.metrics.spiders_failed.labels(
                        project=spider_process.project,
                        spider=spider_process.spider,
                        error="exit_code_" + str(exit_code)
                    ).inc()

                logger.error(f"Spider {spider_process.spider} failed "
                           f"(job: {job_id}, exit_code: {exit_code})")

            # Store job result if storage is available
            if self.storage:
                await self._store_job_result(spider_process, exit_code)

            # Return process to pool if enabled
            if self.process_pool_enabled and len(self.process_pool) < self.max_pool_size:
                if exit_code == 0:  # Only reuse successful processes
                    self.process_pool.append(spider_process.process)
                    logger.debug("Returned process to pool")

        except Exception as e:
            logger.error(f"Error monitoring process {job_id}: {e}")
            spider_process.status = "error"

        finally:
            # Cleanup
            if job_id in self.running_processes:
                del self.running_processes[job_id]

            # Release process slot
            self.process_slots.release()

            # Update metrics
            if self.metrics:
                self.metrics.active_processes.set(len(self.running_processes))

    async def _store_job_result(self, spider_process: SpiderProcess, exit_code: int):
        """Store job result in storage backend"""
        try:
            job_data = {
                'id': spider_process.job_id,
                'project': spider_process.project,
                'spider': spider_process.spider,
                'start_time': spider_process.start_time,
                'end_time': datetime.utcnow(),
                'exit_code': exit_code,
                'status': spider_process.status,
                'log_url': str(spider_process.log_file) if spider_process.log_file else None
            }

            if hasattr(self.storage, 'store_job_result'):
                await self.storage.store_job_result(job_data)

        except Exception as e:
            logger.error(f"Failed to store job result for {spider_process.job_id}: {e}")

    async def _cleanup_processes(self):
        """Background task to cleanup completed processes"""
        while True:
            try:
                # Check for zombie processes
                completed_jobs = []
                for job_id, spider_process in self.running_processes.items():
                    if spider_process.process.returncode is not None:
                        completed_jobs.append(job_id)

                # Cleanup completed jobs
                for job_id in completed_jobs:
                    if job_id in self.running_processes:
                        spider_process = self.running_processes[job_id]
                        logger.debug(f"Cleaning up completed job {job_id}")

                        # Store final result
                        if self.storage:
                            await self._store_job_result(
                                spider_process,
                                spider_process.process.returncode
                            )

                        del self.running_processes[job_id]
                        self.process_slots.release()

                # Update process count metric
                if self.metrics:
                    self.metrics.active_processes.set(len(self.running_processes))

                await asyncio.sleep(self.poll_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in process cleanup: {e}")
                await asyncio.sleep(self.poll_interval)

    async def _terminate_all_processes(self):
        """Terminate all running processes"""
        if not self.running_processes:
            return

        logger.info(f"Terminating {len(self.running_processes)} running processes...")

        # Send SIGTERM to all processes
        for spider_process in self.running_processes.values():
            try:
                spider_process.process.terminate()
            except Exception as e:
                logger.error(f"Error terminating process {spider_process.job_id}: {e}")

        # Wait for graceful shutdown
        await asyncio.sleep(5.0)

        # Force kill any remaining processes
        for spider_process in self.running_processes.values():
            if spider_process.process.returncode is None:
                try:
                    spider_process.process.kill()
                    await spider_process.process.wait()
                except Exception as e:
                    logger.error(f"Error killing process {spider_process.job_id}: {e}")

        self.running_processes.clear()

    async def _cleanup_process_pool(self):
        """Cleanup process pool"""
        for process in self.process_pool:
            try:
                process.terminate()
                await process.wait()
            except Exception as e:
                logger.error(f"Error cleaning up pooled process: {e}")

        self.process_pool.clear()

    def _update_startup_stats(self, startup_time: float):
        """Update startup time statistics"""
        self.process_stats['total_started'] += 1
        current_avg = self.process_stats['avg_startup_time']
        total_started = self.process_stats['total_started']

        # Calculate running average
        new_avg = ((current_avg * (total_started - 1)) + startup_time) / total_started
        self.process_stats['avg_startup_time'] = new_avg

        if self.metrics:
            self.metrics.process_startup_time.observe(startup_time)

    def _update_execution_stats(self, execution_time: float):
        """Update execution time statistics"""
        current_avg = self.process_stats['avg_execution_time']
        total_completed = self.process_stats['total_completed'] + 1

        # Calculate running average
        new_avg = ((current_avg * (total_completed - 1)) + execution_time) / total_completed
        self.process_stats['avg_execution_time'] = new_avg

    def get_stats(self) -> Dict[str, Any]:
        """Get launcher statistics"""
        return {
            'active_processes': len(self.running_processes),
            'max_processes': self.max_proc,
            'process_pool_size': len(self.process_pool),
            'total_started': self.process_stats['total_started'],
            'total_completed': self.process_stats['total_completed'],
            'total_failed': self.process_stats['total_failed'],
            'avg_startup_time': self.process_stats['avg_startup_time'],
            'avg_execution_time': self.process_stats['avg_execution_time'],
            'success_rate': (
                self.process_stats['total_completed'] /
                max(self.process_stats['total_started'], 1)
            ) * 100
        }