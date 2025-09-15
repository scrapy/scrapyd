# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

Scrapyd is a service for deploying and running Scrapy spiders. It provides a JSON API to upload Scrapy projects and control their spiders.

## Development Commands

### Running Tests
```bash
# Run unit tests with coverage
coverage run --source=scrapyd -m pytest tests

# Run integration tests (requires Scrapyd to be running)
pytest integration_tests

# Run tests with warnings as errors
pytest -W error -W ignore::ResourceWarning -W ignore::DeprecationWarning:scrapyd.runner tests
```

### Starting Scrapyd
```bash
# Run Scrapyd service
scrapyd

# Run with custom config file
scrapyd -c scrapyd.conf

# Run as a Python module
python -m scrapyd
```

### Code Quality
```bash
# Run ruff linter (configured in pyproject.toml)
ruff check .

# Format code with ruff
ruff format .
```

### Documentation
```bash
# Build HTML documentation
cd docs && make html

# View documentation
python -c "import webbrowser; webbrowser.open('docs/_build/html/index.html')"
```

## Architecture Overview

### Core Components

**Application Structure** (`scrapyd/app.py`): The main application factory that creates a Twisted application with all necessary components and services.

**Service Components**:
- **Launcher** (`launcher.py`): Manages Scrapy process spawning and execution. Uses process slots determined by `max_proc` configuration.
- **Scheduler** (`scheduler.py`): Handles spider scheduling through the `ISpiderScheduler` interface.
- **Poller** (`poller.py`): Polls the queue for pending jobs to be executed.
- **Web Service** (`webservice.py`, `website.py`): Provides HTTP API endpoints for project/spider management and a web console interface.

**Storage Components**:
- **EggStorage** (`eggstorage.py`): Manages uploaded Scrapy project eggs. Default implementation stores on filesystem.
- **JobStorage** (`jobstorage.py`): Tracks running and finished jobs. Default uses in-memory storage.
- **SpiderQueue** (`spiderqueue.py`): Manages the queue of spiders waiting to be executed. SQLite-backed by default.

**Configuration** (`config.py`): Handles reading configuration from `scrapyd.conf` files and environment variables.

### Key Interfaces

The codebase uses Zope interfaces (`interfaces.py`) to define component contracts:
- `IEggStorage`: Project egg storage interface
- `IJobStorage`: Job tracking interface
- `IPoller`: Queue polling interface
- `ISpiderScheduler`: Spider scheduling interface
- `IEnvironment`: Environment configuration interface

### Process Flow

1. Projects are uploaded as eggs via the web API and stored by EggStorage
2. Spider runs are scheduled through the Scheduler and added to SpiderQueue
3. The Poller continuously checks the queue for pending jobs
4. The Launcher spawns Scrapy processes in available slots
5. Job status is tracked by JobStorage
6. Results are accessible through the web API

### Testing

The test suite includes:
- Unit tests in `tests/` directory
- Integration tests in `integration_tests/` directory
- Mock projects in `tests/projects/` for testing various scenarios
- Uses pytest with twisted support via pytest-twisted

### Dependencies

- Python 3.10+ required
- Core dependencies: Scrapy, Twisted, setuptools
- Testing: pytest, pytest-twisted, coverage
- Documentation: Sphinx with Furo theme