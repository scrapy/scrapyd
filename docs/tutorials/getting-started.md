# Getting Started with Scrapyd

This tutorial will guide you through setting up Scrapyd, creating your first spider, and understanding the core concepts.

## Prerequisites

- Python 3.8 or higher
- Basic knowledge of Python and web scraping
- Familiarity with Scrapy framework

## Installation

### Option 1: Using pip

```bash
# Install Scrapyd
pip install scrapyd

# Install additional dependencies
pip install scrapy requests
```

### Option 2: From Source

```bash
# Clone repository
git clone https://github.com/scrapy/scrapyd.git
cd scrapyd

# Install in development mode
pip install -e .
```

### Option 3: Using Docker

```bash
# Pull and run Scrapyd container
docker run -p 6800:6800 scrapy/scrapyd

# Or build from source
docker build -t scrapyd .
docker run -p 6800:6800 scrapyd
```

## Initial Setup

### 1. Configuration

Create a configuration file `scrapyd.conf`:

```ini
[scrapyd]
eggs_dir    = eggs
logs_dir    = logs
items_dir   = items
jobs_to_keep = 5
dbs_dir     = dbs
max_proc    = 0
max_proc_per_cpu = 4
finished_to_keep = 100
poll_interval = 5.0
bind_address = 127.0.0.1
http_port   = 6800
debug       = off
runner      = scrapyd.runner
application = scrapyd.app.application
launcher    = scrapyd.launcher.Launcher
webroot     = scrapyd.website.Root

[services]
schedule.json     = scrapyd.webservice.Schedule
cancel.json       = scrapyd.webservice.Cancel
addversion.json   = scrapyd.webservice.AddVersion
listprojects.json = scrapyd.webservice.ListProjects
listversions.json = scrapyd.webservice.ListVersions
listspiders.json  = scrapyd.webservice.ListSpiders
delproject.json   = scrapyd.webservice.DeleteProject
delversion.json   = scrapyd.webservice.DeleteVersion
listjobs.json     = scrapyd.webservice.ListJobs
daemonstatus.json = scrapyd.webservice.DaemonStatus
```

### 2. Start Scrapyd

```bash
# Start with default configuration
scrapyd

# Start with custom configuration
scrapyd -c /path/to/scrapyd.conf

# Start with custom settings
scrapyd --pidfile=/var/run/scrapyd.pid --logfile=/var/log/scrapyd.log
```

The web interface will be available at: http://localhost:6800

## Understanding Scrapyd

### Core Concepts

1. **Projects** - Collections of spiders (Scrapy projects)
2. **Spiders** - Individual crawlers within a project
3. **Jobs** - Running instances of spiders
4. **Versions** - Different versions of deployed projects

### Directory Structure

```
scrapyd/
├── eggs/           # Deployed project eggs
│   └── myproject/
│       └── 1.0.egg
├── logs/           # Spider execution logs
│   └── myproject/
│       └── spider1/
│           └── job_id.log
├── items/          # Scraped items (if configured)
├── dbs/           # SQLite databases for job queue
└── twistd.pid     # Process ID file
```

### Web Interface

Navigate to http://localhost:6800 to access:

- **Available projects** - View deployed projects
- **Jobs** - Monitor running, finished, and pending jobs
- **Logs** - Download and view spider logs
- **Project management** - Add/remove projects

## Creating Your First Spider

### 1. Create Scrapy Project

```bash
# Create new project
scrapy startproject myproject
cd myproject

# Generate a spider
scrapy genspider example example.com
```

### 2. Basic Spider Example

```python
# myproject/spiders/example.py
import scrapy

class ExampleSpider(scrapy.Spider):
    name = 'example'
    allowed_domains = ['example.com']
    start_urls = ['http://example.com']

    def parse(self, response):
        # Extract data
        for link in response.css('a::attr(href)').getall():
            yield {
                'url': response.urljoin(link),
                'title': response.css('title::text').get()
            }

        # Follow links
        for href in response.css('a::attr(href)').getall():
            yield response.follow(href, self.parse)
```

### 3. Project Configuration

```python
# myproject/settings.py
BOT_NAME = 'myproject'

SPIDER_MODULES = ['myproject.spiders']
NEWSPIDER_MODULE = 'myproject.spiders'

ROBOTSTXT_OBEY = True
DOWNLOAD_DELAY = 1

# Configure item pipelines
ITEM_PIPELINES = {
    'myproject.pipelines.MyPipeline': 300,
}
```

### 4. Setup for Deployment

```python
# setup.py
from setuptools import setup, find_packages

setup(
    name='myproject',
    version='1.0',
    packages=find_packages(),
    entry_points={'scrapy': ['settings = myproject.settings']},
)
```

```ini
# scrapy.cfg
[settings]
default = myproject.settings

[deploy]
url = http://localhost:6800/
project = myproject
```

## Deploying Your Project

### Method 1: Using scrapyd-client

```bash
# Install scrapyd-client
pip install scrapyd-client

# Deploy from project directory
scrapyd-deploy

# Deploy to specific target
scrapyd-deploy production
```

### Method 2: Manual Deployment

```bash
# Build egg file
python setup.py bdist_egg

# Deploy via HTTP API
curl http://localhost:6800/addversion.json \
  -F project=myproject \
  -F version=1.0 \
  -F egg=@dist/myproject-1.0-py3.9.egg
```

### Method 3: Using curl script

```bash
#!/bin/bash
# deploy.sh

PROJECT="myproject"
VERSION="1.0"
SCRAPYD_URL="http://localhost:6800"

echo "Building project..."
python setup.py bdist_egg

echo "Deploying to Scrapyd..."
curl $SCRAPYD_URL/addversion.json \
  -F project=$PROJECT \
  -F version=$VERSION \
  -F egg=@dist/$PROJECT-$VERSION-py3.9.egg

echo "Deployment complete!"
```

## Running Spiders

### 1. Schedule a Spider

```bash
# Basic scheduling
curl http://localhost:6800/schedule.json \
  -d project=myproject \
  -d spider=example

# With custom settings
curl http://localhost:6800/schedule.json \
  -d project=myproject \
  -d spider=example \
  -d setting=DOWNLOAD_DELAY=3 \
  -d setting=CONCURRENT_REQUESTS=1

# With spider arguments
curl http://localhost:6800/schedule.json \
  -d project=myproject \
  -d spider=example \
  -d start_url=http://specific-site.com \
  -d max_pages=10
```

### 2. Monitor Jobs

```bash
# Check daemon status
curl http://localhost:6800/daemonstatus.json

# List all jobs
curl http://localhost:6800/listjobs.json?project=myproject

# Get specific job status
JOB_ID="abc123"
curl http://localhost:6800/listjobs.json?project=myproject | \
  grep $JOB_ID
```

### 3. View Logs

```bash
# List available logs
curl http://localhost:6800/logs/myproject/example/

# Download log file
curl http://localhost:6800/logs/myproject/example/abc123.log

# Stream live logs (if running)
tail -f logs/myproject/example/abc123.log
```

### 4. Cancel Jobs

```bash
# Cancel a running job
curl http://localhost:6800/cancel.json \
  -d project=myproject \
  -d job=abc123
```

## Understanding the API

### Project Management

```bash
# List projects
curl http://localhost:6800/listprojects.json

# List project versions
curl http://localhost:6800/listversions.json?project=myproject

# List spiders in project
curl http://localhost:6800/listspiders.json?project=myproject

# Delete project version
curl http://localhost:6800/delversion.json \
  -d project=myproject \
  -d version=1.0

# Delete entire project
curl http://localhost:6800/delproject.json -d project=myproject
```

### Job Management

```bash
# Schedule with priority
curl http://localhost:6800/schedule.json \
  -d project=myproject \
  -d spider=example \
  -d priority=1

# Schedule with job ID
curl http://localhost:6800/schedule.json \
  -d project=myproject \
  -d spider=example \
  -d jobid=my-custom-job-id
```

### Response Formats

All API responses are in JSON format:

```json
{
  "status": "ok",
  "jobid": "abc123",
  "node_name": "node01"
}
```

Error responses:

```json
{
  "status": "error",
  "message": "spider 'nonexistent' not found"
}
```

## Configuration Options

### Basic Settings

| Setting | Description | Default |
|---------|-------------|---------|
| `bind_address` | IP address to bind | 127.0.0.1 |
| `http_port` | HTTP port | 6800 |
| `max_proc` | Max concurrent processes | 0 (auto) |
| `max_proc_per_cpu` | Max processes per CPU | 4 |
| `poll_interval` | Job polling interval (seconds) | 5.0 |

### Directory Settings

| Setting | Description | Default |
|---------|-------------|---------|
| `eggs_dir` | Project eggs directory | eggs |
| `logs_dir` | Spider logs directory | logs |
| `items_dir` | Items output directory | items |
| `dbs_dir` | Databases directory | dbs |

### Advanced Settings

```ini
[scrapyd]
# Custom runner for spiders
runner = myproject.custom_runner

# Custom launcher
launcher = myproject.custom_launcher

# Custom job storage
jobstorage = scrapyd.jobstorage.SqliteJobStorage

# Custom egg storage
eggstorage = scrapyd.eggstorage.FilesystemEggStorage

# Authentication
username = admin
password = secret

# HTTPS settings
ssl_enabled = true
ssl_cert = /path/to/cert.pem
ssl_key = /path/to/key.pem
```

## Working with Items and Pipelines

### Define Items

```python
# myproject/items.py
import scrapy

class ProductItem(scrapy.Item):
    name = scrapy.Field()
    price = scrapy.Field()
    description = scrapy.Field()
    url = scrapy.Field()
```

### Create Pipelines

```python
# myproject/pipelines.py
import json
from itemadapter import ItemAdapter

class JsonWriterPipeline:
    def open_spider(self, spider):
        self.file = open('items.jsonl', 'w')

    def close_spider(self, spider):
        self.file.close()

    def process_item(self, item, spider):
        line = json.dumps(ItemAdapter(item).asdict()) + "\n"
        self.file.write(line)
        return item

class ValidationPipeline:
    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        if adapter.get('price'):
            # Validate price format
            try:
                float(adapter['price'].replace('$', ''))
            except ValueError:
                spider.logger.warning(f"Invalid price: {adapter['price']}")
        return item
```

### Configure Pipelines

```python
# myproject/settings.py
ITEM_PIPELINES = {
    'myproject.pipelines.ValidationPipeline': 300,
    'myproject.pipelines.JsonWriterPipeline': 400,
}
```

## Monitoring and Maintenance

### Health Checks

```bash
# Simple health check
curl http://localhost:6800/daemonstatus.json

# Check if responsive
curl -f http://localhost:6800/ || echo "Scrapyd not responding"
```

### Log Management

```bash
# Rotate logs daily
logrotate -d /etc/logrotate.d/scrapyd

# Clean old logs
find logs/ -name "*.log" -mtime +30 -delete

# Monitor disk usage
du -sh logs/
```

### Performance Monitoring

```python
# Custom monitoring script
import requests
import time

def monitor_scrapyd():
    url = "http://localhost:6800/daemonstatus.json"
    response = requests.get(url)
    data = response.json()

    print(f"Status: {data['status']}")
    print(f"Pending jobs: {data['pending']}")
    print(f"Running jobs: {data['running']}")
    print(f"Finished jobs: {data['finished']}")

if __name__ == "__main__":
    while True:
        monitor_scrapyd()
        time.sleep(60)
```

## Troubleshooting

### Common Issues

1. **Port already in use**
   ```bash
   # Check what's using the port
   lsof -i :6800

   # Use different port
   scrapyd --port=6801
   ```

2. **Permission denied**
   ```bash
   # Check file permissions
   ls -la eggs/ logs/ items/

   # Fix permissions
   chmod -R 755 eggs/ logs/ items/
   ```

3. **Spider not found**
   ```bash
   # Check deployed projects
   curl http://localhost:6800/listprojects.json

   # Check spiders in project
   curl http://localhost:6800/listspiders.json?project=myproject

   # Redeploy if necessary
   scrapyd-deploy
   ```

4. **Import errors**
   ```bash
   # Check Python path
   python -c "import sys; print(sys.path)"

   # Test spider import
   python -c "from myproject.spiders.example import ExampleSpider"
   ```

### Debug Mode

```bash
# Start with debug logging
scrapyd --debug

# Or set in configuration
echo "debug = on" >> scrapyd.conf
```

### Log Analysis

```bash
# Check for errors in logs
grep -r "ERROR\|CRITICAL" logs/

# Monitor real-time logs
tail -f logs/myproject/example/*.log

# Count items scraped
grep "Scraped from" logs/myproject/example/*.log | wc -l
```

## Next Steps

- Explore [Advanced Features](advanced-features.md)
- Learn about [Deployment Strategies](deployment/)
- Set up [Monitoring and Alerting](monitoring-setup/)
- Check out [Best Practices](best-practices.md)

This guide covers the fundamentals of working with Scrapyd. Practice with these examples and gradually explore more advanced features as you become comfortable with the basic workflow.