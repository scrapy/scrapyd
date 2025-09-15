#!/usr/bin/env python3
"""
Performance Benchmarks for Scrapyd

Comprehensive performance testing suite to measure and compare
sync vs async implementations of Scrapyd.
"""

import asyncio
import concurrent.futures
import json
import time
import statistics
from typing import Dict, List, Any
from dataclasses import dataclass
from contextlib import asynccontextmanager
import aiohttp
import requests
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
import threading
import multiprocessing


@dataclass
class BenchmarkResult:
    """Result of a benchmark test"""
    name: str
    total_requests: int
    total_time: float
    requests_per_second: float
    avg_response_time: float
    min_response_time: float
    max_response_time: float
    p95_response_time: float
    error_count: int
    error_rate: float
    memory_usage: float
    cpu_usage: float


class PerformanceBenchmark:
    """Performance benchmark suite for Scrapyd"""

    def __init__(self, base_url: str = "http://localhost:6800"):
        if not PSUTIL_AVAILABLE:
            raise ImportError("psutil package is required for performance benchmarks. Install with: pip install psutil")
        self.base_url = base_url
        self.results = []

    async def run_all_benchmarks(self):
        """Run all performance benchmarks"""
        print("Starting Scrapyd Performance Benchmarks...")
        print("=" * 50)

        # API endpoint benchmarks
        await self.benchmark_daemon_status()
        await self.benchmark_list_projects()
        await self.benchmark_list_spiders()
        await self.benchmark_concurrent_requests()
        await self.benchmark_mixed_workload()

        # System benchmarks
        await self.benchmark_memory_usage()
        await self.benchmark_cpu_usage()

        # Generate report
        self.generate_report()

    async def benchmark_daemon_status(self):
        """Benchmark /daemonstatus.json endpoint"""
        print("Benchmarking daemon status endpoint...")

        async def make_request(session):
            start_time = time.time()
            try:
                async with session.get(f"{self.base_url}/daemonstatus.json") as response:
                    await response.json()
                    return time.time() - start_time, response.status == 200
            except Exception:
                return time.time() - start_time, False

        result = await self._run_concurrent_benchmark(
            "Daemon Status",
            make_request,
            concurrent_requests=50,
            total_requests=1000
        )
        self.results.append(result)

    async def benchmark_list_projects(self):
        """Benchmark /listprojects.json endpoint"""
        print("Benchmarking list projects endpoint...")

        async def make_request(session):
            start_time = time.time()
            try:
                async with session.get(f"{self.base_url}/listprojects.json") as response:
                    await response.json()
                    return time.time() - start_time, response.status == 200
            except Exception:
                return time.time() - start_time, False

        result = await self._run_concurrent_benchmark(
            "List Projects",
            make_request,
            concurrent_requests=30,
            total_requests=500
        )
        self.results.append(result)

    async def benchmark_list_spiders(self):
        """Benchmark /listspiders.json endpoint"""
        print("Benchmarking list spiders endpoint...")

        async def make_request(session):
            start_time = time.time()
            try:
                params = {"project": "test_project"}
                async with session.get(f"{self.base_url}/listspiders.json", params=params) as response:
                    await response.json()
                    return time.time() - start_time, response.status == 200
            except Exception:
                return time.time() - start_time, False

        result = await self._run_concurrent_benchmark(
            "List Spiders",
            make_request,
            concurrent_requests=20,
            total_requests=300
        )
        self.results.append(result)

    async def benchmark_concurrent_requests(self):
        """Benchmark high concurrency scenarios"""
        print("Benchmarking high concurrency...")

        async def make_request(session):
            start_time = time.time()
            try:
                # Mix different endpoints
                endpoints = [
                    "/daemonstatus.json",
                    "/listprojects.json",
                    "/listspiders.json?project=test"
                ]
                endpoint = endpoints[int(time.time() * 1000) % len(endpoints)]
                async with session.get(f"{self.base_url}{endpoint}") as response:
                    await response.json()
                    return time.time() - start_time, response.status == 200
            except Exception:
                return time.time() - start_time, False

        result = await self._run_concurrent_benchmark(
            "High Concurrency",
            make_request,
            concurrent_requests=100,
            total_requests=2000
        )
        self.results.append(result)

    async def benchmark_mixed_workload(self):
        """Benchmark realistic mixed workload"""
        print("Benchmarking mixed workload...")

        async def make_mixed_requests(session):
            """Simulate realistic user behavior"""
            response_times = []
            success_count = 0

            # Typical user flow: check status -> list projects -> list spiders
            flows = [
                ["/daemonstatus.json"],
                ["/listprojects.json"],
                ["/listspiders.json?project=test"],
                ["/daemonstatus.json", "/listprojects.json"],
                ["/listprojects.json", "/listspiders.json?project=test"]
            ]

            for endpoints in flows:
                for endpoint in endpoints:
                    start_time = time.time()
                    try:
                        async with session.get(f"{self.base_url}{endpoint}") as response:
                            await response.json()
                            response_times.append(time.time() - start_time)
                            if response.status == 200:
                                success_count += 1
                    except Exception:
                        response_times.append(time.time() - start_time)

                    # Small delay between requests in a flow
                    await asyncio.sleep(0.01)

            return response_times, success_count

        start_time = time.time()
        memory_start = psutil.Process().memory_info().rss / 1024 / 1024

        # Run mixed workload
        connector = aiohttp.TCPConnector(limit=50)
        async with aiohttp.ClientSession(connector=connector) as session:
            tasks = [make_mixed_requests(session) for _ in range(20)]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        total_time = time.time() - start_time
        memory_end = psutil.Process().memory_info().rss / 1024 / 1024

        # Process results
        all_response_times = []
        total_success = 0
        total_requests = 0

        for result in results:
            if isinstance(result, tuple):
                response_times, success_count = result
                all_response_times.extend(response_times)
                total_success += success_count
                total_requests += len(response_times)

        if all_response_times:
            result = BenchmarkResult(
                name="Mixed Workload",
                total_requests=total_requests,
                total_time=total_time,
                requests_per_second=total_requests / total_time,
                avg_response_time=statistics.mean(all_response_times),
                min_response_time=min(all_response_times),
                max_response_time=max(all_response_times),
                p95_response_time=statistics.quantiles(all_response_times, n=20)[18],
                error_count=total_requests - total_success,
                error_rate=(total_requests - total_success) / total_requests * 100,
                memory_usage=memory_end - memory_start,
                cpu_usage=0.0
            )
            self.results.append(result)

    async def benchmark_memory_usage(self):
        """Benchmark memory usage under load"""
        print("Benchmarking memory usage...")

        process = psutil.Process()
        memory_samples = []

        async def monitor_memory():
            for _ in range(60):  # Monitor for 60 seconds
                memory_samples.append(process.memory_info().rss / 1024 / 1024)
                await asyncio.sleep(1)

        async def generate_load():
            connector = aiohttp.TCPConnector(limit=100)
            async with aiohttp.ClientSession(connector=connector) as session:
                tasks = []
                for _ in range(500):
                    task = session.get(f"{self.base_url}/daemonstatus.json")
                    tasks.append(task)

                responses = await asyncio.gather(*tasks, return_exceptions=True)
                for response in responses:
                    if hasattr(response, 'close'):
                        await response.close()

        # Run memory monitoring and load generation concurrently
        await asyncio.gather(monitor_memory(), generate_load())

        # Analyze memory usage
        if memory_samples:
            memory_result = BenchmarkResult(
                name="Memory Usage",
                total_requests=500,
                total_time=60.0,
                requests_per_second=500 / 60.0,
                avg_response_time=0.0,
                min_response_time=0.0,
                max_response_time=0.0,
                p95_response_time=0.0,
                error_count=0,
                error_rate=0.0,
                memory_usage=max(memory_samples) - min(memory_samples),
                cpu_usage=0.0
            )
            self.results.append(memory_result)

    async def benchmark_cpu_usage(self):
        """Benchmark CPU usage under load"""
        print("Benchmarking CPU usage...")

        process = psutil.Process()
        cpu_samples = []

        async def monitor_cpu():
            # Initial CPU reading
            process.cpu_percent()
            await asyncio.sleep(1)

            for _ in range(30):  # Monitor for 30 seconds
                cpu_samples.append(process.cpu_percent())
                await asyncio.sleep(1)

        async def generate_cpu_load():
            connector = aiohttp.TCPConnector(limit=200)
            async with aiohttp.ClientSession(connector=connector) as session:
                # Generate sustained load
                for _ in range(10):  # 10 batches
                    tasks = []
                    for _ in range(50):  # 50 requests per batch
                        task = session.get(f"{self.base_url}/daemonstatus.json")
                        tasks.append(task)

                    responses = await asyncio.gather(*tasks, return_exceptions=True)
                    for response in responses:
                        if hasattr(response, 'close'):
                            await response.close()

                    await asyncio.sleep(0.5)  # Small delay between batches

        # Run CPU monitoring and load generation concurrently
        await asyncio.gather(monitor_cpu(), generate_cpu_load())

        # Analyze CPU usage
        if cpu_samples:
            cpu_result = BenchmarkResult(
                name="CPU Usage",
                total_requests=500,
                total_time=30.0,
                requests_per_second=500 / 30.0,
                avg_response_time=0.0,
                min_response_time=0.0,
                max_response_time=0.0,
                p95_response_time=0.0,
                error_count=0,
                error_rate=0.0,
                memory_usage=0.0,
                cpu_usage=max(cpu_samples)
            )
            self.results.append(cpu_result)

    async def _run_concurrent_benchmark(self, name: str, request_func, concurrent_requests: int,
                                      total_requests: int) -> BenchmarkResult:
        """Run a concurrent benchmark test"""
        start_time = time.time()
        response_times = []
        error_count = 0
        memory_start = psutil.Process().memory_info().rss / 1024 / 1024

        connector = aiohttp.TCPConnector(limit=concurrent_requests * 2)
        async with aiohttp.ClientSession(connector=connector) as session:
            semaphore = asyncio.Semaphore(concurrent_requests)

            async def limited_request():
                async with semaphore:
                    return await request_func(session)

            # Create all tasks
            tasks = [limited_request() for _ in range(total_requests)]

            # Execute tasks
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            for result in results:
                if isinstance(result, tuple):
                    response_time, success = result
                    response_times.append(response_time)
                    if not success:
                        error_count += 1
                else:
                    error_count += 1
                    response_times.append(1.0)  # Assume 1s for errors

        total_time = time.time() - start_time
        memory_end = psutil.Process().memory_info().rss / 1024 / 1024

        # Calculate statistics
        if response_times:
            return BenchmarkResult(
                name=name,
                total_requests=total_requests,
                total_time=total_time,
                requests_per_second=total_requests / total_time,
                avg_response_time=statistics.mean(response_times),
                min_response_time=min(response_times),
                max_response_time=max(response_times),
                p95_response_time=statistics.quantiles(response_times, n=20)[18] if len(response_times) > 20 else max(response_times),
                error_count=error_count,
                error_rate=error_count / total_requests * 100,
                memory_usage=memory_end - memory_start,
                cpu_usage=0.0
            )

    def generate_report(self):
        """Generate performance report"""
        print("\n" + "=" * 80)
        print("SCRAPYD PERFORMANCE BENCHMARK REPORT")
        print("=" * 80)

        print(f"{'Benchmark':<20} {'RPS':<10} {'Avg RT':<10} {'P95 RT':<10} {'Errors':<8} {'Memory':<10}")
        print("-" * 80)

        for result in self.results:
            print(f"{result.name:<20} "
                  f"{result.requests_per_second:<10.1f} "
                  f"{result.avg_response_time*1000:<10.1f} "
                  f"{result.p95_response_time*1000:<10.1f} "
                  f"{result.error_rate:<8.1f}% "
                  f"{result.memory_usage:<10.1f}")

        # Summary statistics
        total_requests = sum(r.total_requests for r in self.results)
        total_time = sum(r.total_time for r in self.results)
        avg_rps = statistics.mean([r.requests_per_second for r in self.results])
        avg_response_time = statistics.mean([r.avg_response_time for r in self.results])

        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print(f"Total Requests: {total_requests}")
        print(f"Total Time: {total_time:.2f}s")
        print(f"Average RPS: {avg_rps:.1f}")
        print(f"Average Response Time: {avg_response_time*1000:.1f}ms")

        # Performance rating
        if avg_rps > 1000:
            rating = "Excellent"
        elif avg_rps > 500:
            rating = "Good"
        elif avg_rps > 200:
            rating = "Fair"
        else:
            rating = "Needs Improvement"

        print(f"Performance Rating: {rating}")

        # Save detailed results
        self.save_results()

    def save_results(self):
        """Save results to JSON file"""
        results_data = {
            'timestamp': time.time(),
            'system_info': {
                'cpu_count': psutil.cpu_count(),
                'memory_total': psutil.virtual_memory().total / 1024 / 1024 / 1024,
                'python_version': f"{psutil.Process().as_dict()['name']}"
            },
            'benchmarks': [
                {
                    'name': r.name,
                    'total_requests': r.total_requests,
                    'total_time': r.total_time,
                    'requests_per_second': r.requests_per_second,
                    'avg_response_time': r.avg_response_time,
                    'min_response_time': r.min_response_time,
                    'max_response_time': r.max_response_time,
                    'p95_response_time': r.p95_response_time,
                    'error_count': r.error_count,
                    'error_rate': r.error_rate,
                    'memory_usage': r.memory_usage,
                    'cpu_usage': r.cpu_usage
                }
                for r in self.results
            ]
        }

        timestamp = int(time.time())
        filename = f"benchmark_results_{timestamp}.json"

        with open(filename, 'w') as f:
            json.dump(results_data, f, indent=2)

        print(f"\nDetailed results saved to: {filename}")


class ComparisonBenchmark:
    """Compare sync vs async implementations"""

    def __init__(self, sync_url: str = "http://localhost:6800",
                 async_url: str = "http://localhost:6801"):
        self.sync_url = sync_url
        self.async_url = async_url

    async def run_comparison(self):
        """Run comparison between sync and async implementations"""
        print("Running Sync vs Async Comparison...")
        print("=" * 50)

        # Test both implementations
        sync_results = await self._test_implementation("Sync", self.sync_url)
        async_results = await self._test_implementation("Async", self.async_url)

        # Generate comparison report
        self._generate_comparison_report(sync_results, async_results)

    async def _test_implementation(self, name: str, base_url: str) -> Dict[str, float]:
        """Test a specific implementation"""
        print(f"Testing {name} implementation at {base_url}...")

        # Test daemon status endpoint
        start_time = time.time()
        connector = aiohttp.TCPConnector(limit=100)

        async with aiohttp.ClientSession(connector=connector) as session:
            tasks = []
            for _ in range(500):
                tasks.append(session.get(f"{base_url}/daemonstatus.json"))

            responses = await asyncio.gather(*tasks, return_exceptions=True)

            # Close responses
            for response in responses:
                if hasattr(response, 'close'):
                    await response.close()

        total_time = time.time() - start_time
        rps = 500 / total_time

        return {
            'requests_per_second': rps,
            'total_time': total_time,
            'avg_response_time': total_time / 500
        }

    def _generate_comparison_report(self, sync_results: Dict, async_results: Dict):
        """Generate comparison report"""
        print("\n" + "=" * 60)
        print("SYNC vs ASYNC COMPARISON")
        print("=" * 60)

        print(f"{'Metric':<25} {'Sync':<15} {'Async':<15} {'Improvement':<15}")
        print("-" * 60)

        # RPS comparison
        sync_rps = sync_results['requests_per_second']
        async_rps = async_results['requests_per_second']
        rps_improvement = (async_rps - sync_rps) / sync_rps * 100

        print(f"{'Requests/sec':<25} {sync_rps:<15.1f} {async_rps:<15.1f} {rps_improvement:<15.1f}%")

        # Response time comparison
        sync_rt = sync_results['avg_response_time'] * 1000
        async_rt = async_results['avg_response_time'] * 1000
        rt_improvement = (sync_rt - async_rt) / sync_rt * 100

        print(f"{'Avg Response Time (ms)':<25} {sync_rt:<15.1f} {async_rt:<15.1f} {rt_improvement:<15.1f}%")

        # Total time comparison
        sync_time = sync_results['total_time']
        async_time = async_results['total_time']
        time_improvement = (sync_time - async_time) / sync_time * 100

        print(f"{'Total Time (s)':<25} {sync_time:<15.2f} {async_time:<15.2f} {time_improvement:<15.1f}%")

        # Overall assessment
        print(f"\nOverall Performance Improvement: {rps_improvement:.1f}%")

        if rps_improvement > 50:
            assessment = "Significant improvement with async implementation"
        elif rps_improvement > 20:
            assessment = "Good improvement with async implementation"
        elif rps_improvement > 0:
            assessment = "Modest improvement with async implementation"
        else:
            assessment = "No significant improvement with async implementation"

        print(f"Assessment: {assessment}")


async def main():
    """Main benchmark runner"""
    import argparse

    parser = argparse.ArgumentParser(description="Scrapyd Performance Benchmarks")
    parser.add_argument("--url", default="http://localhost:6800",
                       help="Base URL for Scrapyd instance")
    parser.add_argument("--compare", action="store_true",
                       help="Run sync vs async comparison")
    parser.add_argument("--sync-url", default="http://localhost:6800",
                       help="URL for sync implementation")
    parser.add_argument("--async-url", default="http://localhost:6801",
                       help="URL for async implementation")

    args = parser.parse_args()

    if args.compare:
        comparison = ComparisonBenchmark(args.sync_url, args.async_url)
        await comparison.run_comparison()
    else:
        benchmark = PerformanceBenchmark(args.url)
        await benchmark.run_all_benchmarks()


if __name__ == "__main__":
    asyncio.run(main())