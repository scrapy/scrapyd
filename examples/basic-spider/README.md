# Basic Spider Example

This example demonstrates how to create, deploy, and run a simple Scrapy spider using Scrapyd.

## Project Structure

```
basic-spider/
├── tutorial/
│   ├── __init__.py
│   ├── items.py
│   ├── middlewares.py
│   ├── pipelines.py
│   ├── settings.py
│   └── spiders/
│       ├── __init__.py
│       ├── quotes_spider.py
│       └── books_spider.py
├── scrapy.cfg
├── setup.py
├── requirements.txt
├── deploy.sh
└── README.md
```

## Step 1: Create the Project

```bash
# Create new Scrapy project
scrapy startproject tutorial
cd tutorial
```

## Step 2: Create Spiders

### Quotes Spider

```python
# tutorial/spiders/quotes_spider.py
import scrapy
from tutorial.items import QuoteItem

class QuotesSpider(scrapy.Spider):
    name = 'quotes'
    allowed_domains = ['quotes.toscrape.com']
    start_urls = ['http://quotes.toscrape.com/']

    def parse(self, response):
        # Extract quotes from the page
        for quote in response.css('div.quote'):
            item = QuoteItem()
            item['text'] = quote.css('span.text::text').get()
            item['author'] = quote.css('small.author::text').get()
            item['tags'] = quote.css('div.tags a.tag::text').getall()
            yield item

        # Follow pagination links
        next_page = response.css('li.next a::attr(href)').get()
        if next_page:
            yield response.follow(next_page, self.parse)

    def parse_author(self, response):
        # Extract author details (optional)
        yield {
            'name': response.css('h3.author-title::text').get(),
            'birth_date': response.css('span.author-born-date::text').get(),
            'birth_location': response.css('span.author-born-location::text').get(),
            'description': response.css('div.author-description::text').get(),
        }
```

### Books Spider

```python
# tutorial/spiders/books_spider.py
import scrapy
from tutorial.items import BookItem

class BooksSpider(scrapy.Spider):
    name = 'books'
    allowed_domains = ['books.toscrape.com']
    start_urls = ['http://books.toscrape.com/']

    def parse(self, response):
        # Extract books from current page
        for book in response.css('article.product_pod'):
            book_url = book.css('h3 a::attr(href)').get()
            if book_url:
                yield response.follow(book_url, self.parse_book)

        # Follow pagination
        next_page = response.css('li.next a::attr(href)').get()
        if next_page:
            yield response.follow(next_page, self.parse)

    def parse_book(self, response):
        item = BookItem()
        item['title'] = response.css('h1::text').get()
        item['price'] = response.css('p.price_color::text').get()
        item['availability'] = response.css('p.instock.availability::text').re_first(r'\((\d+) available\)')
        item['rating'] = self.extract_rating(response.css('p.star-rating::attr(class)').get())
        item['description'] = response.css('#product_description + p::text').get()
        item['upc'] = response.css('table tr:nth-child(1) td::text').get()
        item['category'] = response.css('ul.breadcrumb li:nth-child(3) a::text').get()
        yield item

    def extract_rating(self, rating_class):
        """Extract numerical rating from CSS class"""
        rating_map = {
            'One': 1, 'Two': 2, 'Three': 3, 'Four': 4, 'Five': 5
        }
        for word, number in rating_map.items():
            if word in rating_class:
                return number
        return 0
```

## Step 3: Define Items

```python
# tutorial/items.py
import scrapy

class QuoteItem(scrapy.Item):
    text = scrapy.Field()
    author = scrapy.Field()
    tags = scrapy.Field()

class BookItem(scrapy.Item):
    title = scrapy.Field()
    price = scrapy.Field()
    availability = scrapy.Field()
    rating = scrapy.Field()
    description = scrapy.Field()
    upc = scrapy.Field()
    category = scrapy.Field()
    url = scrapy.Field()

class AuthorItem(scrapy.Item):
    name = scrapy.Field()
    birth_date = scrapy.Field()
    birth_location = scrapy.Field()
    description = scrapy.Field()
```

## Step 4: Configure Settings

```python
# tutorial/settings.py
BOT_NAME = 'tutorial'

SPIDER_MODULES = ['tutorial.spiders']
NEWSPIDER_MODULE = 'tutorial.spiders'

# Obey robots.txt rules
ROBOTSTXT_OBEY = True

# Configure delays
DOWNLOAD_DELAY = 1
RANDOMIZE_DOWNLOAD_DELAY = 0.5

# Configure concurrent requests
CONCURRENT_REQUESTS = 16
CONCURRENT_REQUESTS_PER_DOMAIN = 8

# Configure pipelines
ITEM_PIPELINES = {
    'tutorial.pipelines.ValidationPipeline': 300,
    'tutorial.pipelines.DuplicatesPipeline': 400,
    'tutorial.pipelines.JsonWriterPipeline': 500,
}

# Configure middlewares
DOWNLOADER_MIDDLEWARES = {
    'tutorial.middlewares.RotateUserAgentMiddleware': 110,
    'scrapy.downloadermiddlewares.useragent.UserAgentMiddleware': None,
}

# User agents list
USER_AGENT_LIST = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
]

# Enable autothrottling
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 1
AUTOTHROTTLE_MAX_DELAY = 60
AUTOTHROTTLE_TARGET_CONCURRENCY = 2.0

# Configure logging
LOG_LEVEL = 'INFO'
```

## Step 5: Create Pipelines

```python
# tutorial/pipelines.py
import json
import logging
from itemadapter import ItemAdapter
from scrapy.exceptions import DropItem

class ValidationPipeline:
    """Validate item fields"""

    def process_item(self, item, spider):
        adapter = ItemAdapter(item)

        if 'title' in adapter:
            if not adapter.get('title'):
                raise DropItem(f"Missing title in {item}")

        if 'text' in adapter:
            if not adapter.get('text'):
                raise DropItem(f"Missing text in {item}")

        return item

class DuplicatesPipeline:
    """Filter out duplicate items"""

    def __init__(self):
        self.ids_seen = set()

    def process_item(self, item, spider):
        adapter = ItemAdapter(item)

        # Create unique identifier based on item type
        if 'title' in adapter:
            item_id = adapter['title']
        elif 'text' in adapter:
            item_id = adapter['text']
        else:
            item_id = str(hash(frozenset(adapter.items())))

        if item_id in self.ids_seen:
            raise DropItem(f"Duplicate item found: {item}")
        else:
            self.ids_seen.add(item_id)
            return item

class JsonWriterPipeline:
    """Write items to JSON file"""

    def open_spider(self, spider):
        self.file = open(f'{spider.name}_items.jsonl', 'w')

    def close_spider(self, spider):
        self.file.close()

    def process_item(self, item, spider):
        line = json.dumps(ItemAdapter(item).asdict()) + "\n"
        self.file.write(line)
        return item

class DatabasePipeline:
    """Save items to database (optional)"""

    def __init__(self, db_settings):
        self.db_settings = db_settings

    @classmethod
    def from_crawler(cls, crawler):
        db_settings = crawler.settings.getdict("DATABASE")
        return cls(db_settings)

    def open_spider(self, spider):
        # Initialize database connection
        pass

    def close_spider(self, spider):
        # Close database connection
        pass

    def process_item(self, item, spider):
        # Save item to database
        return item
```

## Step 6: Add Custom Middlewares

```python
# tutorial/middlewares.py
import random
import logging
from scrapy.downloadermiddlewares.useragent import UserAgentMiddleware

class RotateUserAgentMiddleware(UserAgentMiddleware):
    """Rotate user agents randomly"""

    def __init__(self, user_agent=''):
        self.user_agent = user_agent
        self.user_agent_list = []

    @classmethod
    def from_crawler(cls, crawler):
        obj = cls()
        obj.user_agent_list = crawler.settings.get('USER_AGENT_LIST', [])
        return obj

    def process_request(self, request, spider):
        if self.user_agent_list:
            ua = random.choice(self.user_agent_list)
            request.headers['User-Agent'] = ua
        return None

class ProxyMiddleware:
    """Rotate proxies (if available)"""

    def __init__(self):
        self.proxies = []

    @classmethod
    def from_crawler(cls, crawler):
        obj = cls()
        obj.proxies = crawler.settings.get('PROXY_LIST', [])
        return obj

    def process_request(self, request, spider):
        if self.proxies:
            proxy = random.choice(self.proxies)
            request.meta['proxy'] = proxy
        return None
```

## Step 7: Setup Configuration

```ini
# scrapy.cfg
[settings]
default = tutorial.settings

[deploy]
url = http://localhost:6800/
project = tutorial
```

```python
# setup.py
from setuptools import setup, find_packages

setup(
    name='tutorial',
    version='1.0',
    packages=find_packages(),
    entry_points={
        'scrapy': [
            'settings = tutorial.settings'
        ]
    },
    zip_safe=False,
)
```

```
# requirements.txt
scrapy>=2.8.0
itemadapter>=0.7.0
twisted>=22.0.0
```

## Step 8: Deploy to Scrapyd

### Manual Deployment

```bash
# Build egg file
python setup.py bdist_egg

# Deploy to Scrapyd
curl http://localhost:6800/addversion.json \
  -F project=tutorial \
  -F version=1.0 \
  -F egg=@dist/tutorial-1.0-py3.9.egg
```

### Automated Deployment Script

```bash
#!/bin/bash
# deploy.sh

set -e

PROJECT_NAME="tutorial"
VERSION="1.0"
SCRAPYD_URL="http://localhost:6800"

echo "Building project..."
python setup.py bdist_egg

echo "Deploying to Scrapyd..."
RESPONSE=$(curl -s -F project=$PROJECT_NAME \
                 -F version=$VERSION \
                 -F egg=@dist/$PROJECT_NAME-$VERSION-py3.9.egg \
                 $SCRAPYD_URL/addversion.json)

echo "Response: $RESPONSE"

# Check if deployment was successful
if echo "$RESPONSE" | grep -q '"status": "ok"'; then
    echo "✅ Deployment successful!"

    echo "Available spiders:"
    curl -s $SCRAPYD_URL/listspiders.json?project=$PROJECT_NAME | \
        python -m json.tool

    echo ""
    echo "To run a spider:"
    echo "curl $SCRAPYD_URL/schedule.json -d project=$PROJECT_NAME -d spider=quotes"
    echo "curl $SCRAPYD_URL/schedule.json -d project=$PROJECT_NAME -d spider=books"

else
    echo "❌ Deployment failed!"
    exit 1
fi
```

## Step 9: Run Spiders

### Schedule Spider Execution

```bash
# Schedule quotes spider
curl http://localhost:6800/schedule.json \
  -d project=tutorial \
  -d spider=quotes

# Schedule books spider with custom settings
curl http://localhost:6800/schedule.json \
  -d project=tutorial \
  -d spider=books \
  -d setting=DOWNLOAD_DELAY=2 \
  -d setting=CONCURRENT_REQUESTS=8
```

### Monitor Spider Execution

```bash
# Check daemon status
curl http://localhost:6800/daemonstatus.json

# List running jobs
curl http://localhost:6800/listjobs.json?project=tutorial

# Cancel a job (if needed)
curl http://localhost:6800/cancel.json \
  -d project=tutorial \
  -d job=JOB_ID
```

## Step 10: Advanced Features

### Custom Spider Arguments

```python
# tutorial/spiders/quotes_spider.py (modified)
class QuotesSpider(scrapy.Spider):
    name = 'quotes'

    def __init__(self, category=None, max_pages=None, *args, **kwargs):
        super(QuotesSpider, self).__init__(*args, **kwargs)
        self.category = category
        self.max_pages = int(max_pages) if max_pages else None
        self.pages_crawled = 0

    def start_requests(self):
        if self.category:
            url = f'http://quotes.toscrape.com/tag/{self.category}/'
        else:
            url = 'http://quotes.toscrape.com/'
        yield scrapy.Request(url, self.parse)

    def parse(self, response):
        # Check page limit
        if self.max_pages and self.pages_crawled >= self.max_pages:
            return

        self.pages_crawled += 1

        # ... rest of parse method
```

```bash
# Run with custom arguments
curl http://localhost:6800/schedule.json \
  -d project=tutorial \
  -d spider=quotes \
  -d category=love \
  -d max_pages=5
```

### Email Notifications

```python
# tutorial/extensions.py
from scrapy import signals
from scrapy.mail import MailSender

class EmailNotification:
    def __init__(self, crawler):
        self.crawler = crawler
        self.mail = MailSender.from_settings(crawler.settings)

    @classmethod
    def from_crawler(cls, crawler):
        ext = cls(crawler)
        crawler.signals.connect(ext.spider_closed, signal=signals.spider_closed)
        return ext

    def spider_closed(self, spider, reason):
        stats = spider.crawler.stats.get_stats()
        subject = f"Spider {spider.name} finished: {reason}"
        body = f"""
        Spider: {spider.name}
        Reason: {reason}
        Items scraped: {stats.get('item_scraped_count', 0)}
        Pages crawled: {stats.get('downloader/response_count', 0)}
        Duration: {stats.get('elapsed_time_seconds', 0)} seconds
        """

        self.mail.send(
            to=["admin@example.com"],
            subject=subject,
            body=body
        )
```

## Testing

### Unit Tests

```python
# tests/test_spiders.py
import unittest
from scrapy.http import HtmlResponse, Request
from tutorial.spiders.quotes_spider import QuotesSpider

class TestQuotesSpider(unittest.TestCase):
    def setUp(self):
        self.spider = QuotesSpider()

    def test_parse(self):
        # Create mock response
        html = """
        <div class="quote">
            <span class="text">"Test quote"</span>
            <small class="author">Test Author</small>
            <div class="tags">
                <a class="tag" href="/tag/test">test</a>
            </div>
        </div>
        """
        response = HtmlResponse(
            url="http://quotes.toscrape.com/",
            body=html.encode('utf-8')
        )

        # Test parsing
        results = list(self.spider.parse(response))
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['text'], '"Test quote"')
        self.assertEqual(results[0]['author'], 'Test Author')

if __name__ == '__main__':
    unittest.main()
```

### Integration Tests

```bash
# test_integration.sh
#!/bin/bash

set -e

# Start local Scrapyd
scrapyd &
SCRAPYD_PID=$!

# Wait for Scrapyd to start
sleep 5

# Deploy project
./deploy.sh

# Test spider execution
JOB_ID=$(curl -s http://localhost:6800/schedule.json \
  -d project=tutorial \
  -d spider=quotes | \
  python -c "import sys, json; print(json.load(sys.stdin)['jobid'])")

echo "Started job: $JOB_ID"

# Wait for completion
while true; do
    STATUS=$(curl -s http://localhost:6800/listjobs.json?project=tutorial | \
             python -c "import sys, json; data=json.load(sys.stdin); print('finished' if any(job['id']=='$JOB_ID' for job in data['finished']) else 'running')")

    if [ "$STATUS" = "finished" ]; then
        echo "Job completed successfully!"
        break
    fi

    echo "Job still running..."
    sleep 10
done

# Cleanup
kill $SCRAPYD_PID
```

## Troubleshooting

### Common Issues

1. **Import Errors**
   ```bash
   # Check Python path
   echo $PYTHONPATH

   # Test imports
   python -c "from tutorial.spiders.quotes_spider import QuotesSpider"
   ```

2. **Spider Not Found**
   ```bash
   # List available spiders
   curl http://localhost:6800/listspiders.json?project=tutorial

   # Check project deployment
   curl http://localhost:6800/listprojects.json
   ```

3. **Permission Issues**
   ```bash
   # Check file permissions
   ls -la dist/

   # Fix permissions
   chmod 644 dist/*.egg
   ```

### Debugging Tips

1. **Enable Debug Logging**
   ```python
   # Add to settings.py
   LOG_LEVEL = 'DEBUG'
   ```

2. **Use Scrapy Shell**
   ```bash
   # Test selectors interactively
   scrapy shell "http://quotes.toscrape.com/"
   ```

3. **Check Logs**
   ```bash
   # View Scrapyd logs
   tail -f /var/log/scrapyd/scrapyd.log

   # View spider logs
   curl http://localhost:6800/logs/tutorial/quotes/JOB_ID.log
   ```

This example provides a complete foundation for building and deploying Scrapy spiders with Scrapyd!