# Scrapyd

[![PyPI Version](https://img.shields.io/pypi/v/scrapyd.svg)](https://pypi.org/project/scrapyd/)
[![Build Status](https://github.com/scrapy/scrapyd/workflows/Tests/badge.svg)](https://github.com/scrapy/scrapyd/actions)
[![Coverage Status](https://coveralls.io/repos/github/scrapy/scrapyd/badge.svg?branch=master)](https://coveralls.io/github/scrapy/scrapyd?branch=master)
[![Python Version](https://img.shields.io/pypi/pyversions/scrapyd.svg)](https://pypi.org/project/scrapyd/)
[![PyPI Downloads](https://img.shields.io/pypi/dm/scrapyd.svg)](https://pypi.python.org/pypi/scrapyd/)

Scrapyd is a service for deploying and running [Scrapy](https://scrapy.org) spiders.

It enables you to upload Scrapy projects and control their spiders using a JSON API, making it perfect for production web scraping deployments.

## Features

🚀 **Easy Deployment**
Deploy Scrapy projects as Python eggs via HTTP API

📊 **Web Dashboard**
Monitor running jobs, view logs, and manage projects via web interface

🔧 **RESTful API**
Complete JSON API for programmatic spider management

⚡ **Concurrent Processing**
Run multiple spiders simultaneously with configurable concurrency

📈 **Job Management**
Schedule, monitor, and cancel spider jobs with persistent queue

🔒 **Authentication**
Built-in HTTP basic authentication support

📂 **Project Versioning**
Deploy and manage multiple versions of your scraping projects

📊 **Logging & Monitoring**
Comprehensive logging and status monitoring capabilities

## Quick Start

### Installation

```bash
pip install scrapyd
```

### Basic Usage

1. **Start Scrapyd**:

   ```bash
   scrapyd
   ```

   The web interface will be available at http://localhost:6800

2. **Deploy a Project**:

   ```bash
   # Using scrapyd-client
   pip install scrapyd-client
   scrapyd-deploy
   ```

3. **Schedule a Spider**:

   ```bash
   curl http://localhost:6800/schedule.json \
        -d project=myproject \
        -d spider=myspider
   ```

4. **Monitor Jobs**:

   Visit http://localhost:6800 or use the API:

   ```bash
   curl http://localhost:6800/daemonstatus.json
   ```

## API Endpoints

Core endpoints for spider management:

- `/daemonstatus.json` - Get daemon status and job counts
- `/listprojects.json` - List all deployed projects
- `/listspiders.json` - List spiders in a project
- `/listjobs.json` - List pending/running/finished jobs
- `/schedule.json` - Schedule a spider to run
- `/cancel.json` - Cancel a running job
- `/addversion.json` - Deploy a new project version
- `/delversion.json` - Delete a project version
- `/delproject.json` - Delete an entire project

## Example API Usage

```python
import requests

# Check status
response = requests.get('http://localhost:6800/daemonstatus.json')
print(response.json())

# Schedule a spider
response = requests.post('http://localhost:6800/schedule.json', data={
    'project': 'myproject',
    'spider': 'myspider',
    'setting': 'DOWNLOAD_DELAY=2'
})
job_id = response.json()['jobid']

# Monitor the job
response = requests.get('http://localhost:6800/listjobs.json?project=myproject')
jobs = response.json()
```

## Configuration

Create `scrapyd.conf` to customize settings:

```ini
[scrapyd]
bind_address = 0.0.0.0
http_port = 6800
max_proc_per_cpu = 4
username = admin
password = secret
```

## Docker Support

```bash
# Run with Docker
docker run -p 6800:6800 scrapy/scrapyd

# Or build from source
docker build -t scrapyd .
docker run -p 6800:6800 scrapyd
```

## Scrapy Ecosystem Integration

Scrapyd is part of the larger Scrapy ecosystem. Here's how the main components work together:

🕷️ **Scrapy** - The Core Framework
The foundational web scraping framework for Python that provides the tools to build spiders, handle requests/responses, and extract data from websites.

🚀 **Scrapyd** - Deployment & Management Server
A service that allows you to deploy Scrapy projects and run spiders remotely via HTTP API. Perfect for production deployments where you need to manage multiple projects and schedule spider execution.

📦 **scrapyd-client** - Deployment Tools
Command-line tools that simplify deploying Scrapy projects to Scrapyd servers:

- `scrapyd-deploy` - Builds and uploads project eggs to Scrapyd
- `scrapyd-client` - Programmatic Python client for Scrapyd API
- Handles versioning, dependencies, and configuration management

⚡ **Scrapyrt** - Real-time HTTP API
A lightweight HTTP interface for Scrapy that enables real-time scraping requests. Unlike Scrapyd (designed for long-running spiders), Scrapyrt is optimized for quick, on-demand scraping tasks.

### Typical Workflow

1. **Development**: Create spiders using **Scrapy** framework
2. **Deployment**: Use **scrapyd-client** to deploy projects to **Scrapyd**
3. **Execution**: Schedule and monitor spiders via **Scrapyd** API
4. **Real-time Tasks**: Use **Scrapyrt** for immediate scraping needs

```bash
# 1. Create Scrapy project
scrapy startproject myproject

# 2. Deploy to Scrapyd
scrapyd-deploy

# 3. Schedule spider via Scrapyd
curl http://localhost:6800/schedule.json -d project=myproject -d spider=myspider

# 4. Real-time scraping via Scrapyrt (alternative approach)
curl "localhost:9080/crawl.json?spider_name=myspider&url=http://example.com"
```

### When to Use Which Tool

| Use Case           | Scrapy                | Scrapyd              | Scrapyrt           |
|--------------------|-----------------------|----------------------|--------------------|
| Development        | ✅ Core framework     | ❌ Not needed        | ❌ Not needed      |
| Local Testing      | ✅ `scrapy crawl`     | ❌ Overkill          | ✅ Quick HTTP tests |
| Production Batches | ✅ Spider logic       | ✅ Job scheduling    | ❌ Not suitable    |
| Long-running Jobs  | ✅ Spider logic       | ✅ Process management| ❌ Not recommended |
| Real-time API      | ✅ Spider logic       | ❌ Too heavy         | ✅ Perfect fit     |
| Multiple Projects  | ✅ Individual dev     | ✅ Centralized mgmt  | ❌ Single project  |
| Job Monitoring     | ❌ Limited            | ✅ Full dashboard    | ❌ Limited         |

## Documentation

📚 **Full Documentation**: https://scrapyd.readthedocs.io/

- [Getting Started Guide](https://scrapyd.readthedocs.io/en/latest/tutorials/getting-started.html)
- [API Reference](https://scrapyd.readthedocs.io/en/latest/api.html)
- [Configuration Options](https://scrapyd.readthedocs.io/en/latest/config.html)
- [Deployment Guide](https://scrapyd.readthedocs.io/en/latest/deploy.html)

## Community

- **Issues**: Report bugs and request features on [GitHub Issues](https://github.com/scrapy/scrapyd/issues)
- **Discussions**: Join conversations on [GitHub Discussions](https://github.com/scrapy/scrapyd/discussions)
- **Stack Overflow**: Ask questions with the `scrapy` tag

## Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

## License

BSD 3-Clause License. See [LICENSE](LICENSE) for details.