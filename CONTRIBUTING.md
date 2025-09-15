# Contributing to Scrapyd

Thank you for your interest in contributing to Scrapyd! This document provides guidelines and instructions for contributing to the project.

## Code of Conduct

By participating in this project, you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md). Please read it before contributing.

## Getting Started

### Prerequisites

- Python 3.8 or higher
- Git
- Familiarity with Scrapy and Twisted frameworks
- Basic understanding of web services and APIs

### Development Environment Setup

1. **Fork and Clone the Repository**

   ```bash
   # Fork the repository on GitHub, then clone your fork
   git clone https://github.com/YOUR_USERNAME/scrapyd.git
   cd scrapyd

   # Add upstream remote
   git remote add upstream https://github.com/scrapy/scrapyd.git
   ```

2. **Create Virtual Environment**

   ```bash
   # Create virtual environment
   python -m venv venv

   # Activate virtual environment
   # On Linux/macOS:
   source venv/bin/activate
   # On Windows:
   venv\Scripts\activate
   ```

3. **Install Development Dependencies**

   ```bash
   # Install Scrapyd in development mode
   pip install -e ".[dev,test,docs]"

   # Install additional development tools
   pip install pre-commit black isort mypy

   # Install pre-commit hooks
   pre-commit install
   ```

4. **Verify Installation**

   ```bash
   # Run tests to ensure everything works
   pytest tests/

   # Start Scrapyd
   scrapyd

   # Check if it's running
   curl http://localhost:6800/daemonstatus.json
   ```

## Development Workflow

### 1. Create a Feature Branch

```bash
# Update your fork
git checkout master
git pull upstream master

# Create feature branch
git checkout -b feature/your-feature-name

# Or for bug fixes
git checkout -b fix/issue-number-description
```

### 2. Make Changes

- Follow the existing code style and conventions
- Add tests for new features or bug fixes
- Update documentation if necessary
- Ensure all tests pass

### 3. Commit Changes

```bash
# Stage your changes
git add .

# Commit with descriptive message
git commit -m "Add feature: brief description

Detailed explanation of what was changed and why.

Fixes #issue_number"
```

### 4. Push and Create Pull Request

```bash
# Push to your fork
git push origin feature/your-feature-name

# Create pull request on GitHub
# Include clear description of changes and reference any related issues
```

## Code Style Guidelines

### Python Code Style

We follow [PEP 8](https://pep8.org/) with some modifications configured in `pyproject.toml`.

**Key Guidelines:**
- Line length: 119 characters
- Use 4 spaces for indentation
- Use type hints for new code
- Use f-strings for string formatting
- Follow existing naming conventions

**Example:**

```python
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class SpiderManager:
    """Manages spider execution and monitoring."""

    def __init__(self, config: Dict[str, str]) -> None:
        self.config = config
        self.active_spiders: Dict[str, Any] = {}

    def start_spider(self, project: str, spider: str,
                    settings: Optional[Dict[str, str]] = None) -> str:
        """Start a spider with given settings.

        Args:
            project: Project name
            spider: Spider name
            settings: Optional spider settings

        Returns:
            Job ID of the started spider

        Raises:
            SpiderNotFoundError: If spider doesn't exist
        """
        if not self._spider_exists(project, spider):
            raise SpiderNotFoundError(f"Spider {spider} not found in {project}")

        job_id = self._generate_job_id()
        logger.info(f"Starting spider {spider} in project {project} (job: {job_id})")

        # Implementation here...
        return job_id
```

### Code Formatting

We use automated code formatting tools:

```bash
# Format code with black
black scrapyd/

# Sort imports with isort
isort scrapyd/

# Run type checking with mypy
mypy scrapyd/

# Run linting with ruff
ruff check scrapyd/
```

### Documentation Style

- Use clear, concise language
- Include examples for complex features
- Follow existing documentation structure
- Use proper Markdown formatting

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=scrapyd --cov-report=html

# Run specific test file
pytest tests/test_webservice.py

# Run specific test
pytest tests/test_webservice.py::TestSchedule::test_schedule

# Run integration tests
pytest integration_tests/
```

### Writing Tests

**Test Structure:**
```python
# tests/test_example.py
import pytest
from unittest.mock import Mock, patch
from twisted.trial import unittest

from scrapyd.example import ExampleClass

class TestExampleClass(unittest.TestCase):
    """Test cases for ExampleClass."""

    def setUp(self):
        """Set up test fixtures."""
        self.config = {'setting': 'value'}
        self.example = ExampleClass(self.config)

    def test_basic_functionality(self):
        """Test basic functionality works correctly."""
        result = self.example.do_something()
        self.assertEqual(result, 'expected_value')

    def test_error_handling(self):
        """Test error handling works correctly."""
        with self.assertRaises(ValueError):
            self.example.do_something_invalid()

    @patch('scrapyd.example.external_dependency')
    def test_with_mock(self, mock_dependency):
        """Test with mocked external dependency."""
        mock_dependency.return_value = 'mocked_value'
        result = self.example.use_dependency()
        self.assertEqual(result, 'expected_with_mock')
```

**Testing Guidelines:**
- Write tests for all new features
- Include both positive and negative test cases
- Test error conditions and edge cases
- Use descriptive test method names
- Mock external dependencies
- Aim for >90% code coverage

### Integration Tests

```python
# integration_tests/test_api.py
import requests
import pytest
import subprocess
import time
import tempfile
import os

class TestScrapydAPI:
    """Integration tests for Scrapyd API."""

    @classmethod
    def setup_class(cls):
        """Start Scrapyd instance for testing."""
        cls.tempdir = tempfile.mkdtemp()
        cls.process = subprocess.Popen([
            'scrapyd',
            '--pidfile', os.path.join(cls.tempdir, 'scrapyd.pid'),
            '--logfile', os.path.join(cls.tempdir, 'scrapyd.log'),
            '--port', '6801'
        ])
        time.sleep(2)  # Wait for startup

    @classmethod
    def teardown_class(cls):
        """Stop Scrapyd instance."""
        cls.process.terminate()
        cls.process.wait()

    def test_daemon_status(self):
        """Test daemon status endpoint."""
        response = requests.get('http://localhost:6801/daemonstatus.json')
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'ok'

    def test_schedule_spider(self):
        """Test spider scheduling."""
        # First deploy a project
        # Then schedule a spider
        # Verify it runs successfully
        pass
```

## Documentation

### Building Documentation

```bash
# Install documentation dependencies
pip install -e ".[docs]"

# Build HTML documentation
cd docs/
make html

# View documentation
python -c "import webbrowser; webbrowser.open('_build/html/index.html')"

# Build and serve with live reload
sphinx-autobuild . _build/html
```

### Documentation Guidelines

- Keep documentation up-to-date with code changes
- Include code examples for new features
- Use proper RST or Markdown syntax
- Add docstrings to all public functions and classes
- Update API documentation for interface changes

**Docstring Example:**
```python
def schedule_spider(self, project: str, spider: str, **kwargs) -> str:
    """Schedule a spider for execution.

    This method adds a spider to the execution queue with the specified
    parameters and returns a unique job identifier.

    Args:
        project: Name of the project containing the spider
        spider: Name of the spider to schedule
        **kwargs: Additional arguments passed to the spider

    Returns:
        Unique job identifier for tracking the spider execution

    Raises:
        ProjectNotFoundError: If the specified project doesn't exist
        SpiderNotFoundError: If the spider is not found in the project
        QueueFullError: If the execution queue is at capacity

    Example:
        >>> manager = SpiderManager(config)
        >>> job_id = manager.schedule_spider('myproject', 'myspider',
        ...                                  start_url='http://example.com')
        >>> print(f"Spider scheduled with job ID: {job_id}")
    """
```

## Issue Management

### Reporting Bugs

When reporting bugs, please include:

1. **Clear Title**: Descriptive summary of the issue
2. **Environment**: OS, Python version, Scrapyd version
3. **Steps to Reproduce**: Detailed steps to reproduce the issue
4. **Expected Behavior**: What you expected to happen
5. **Actual Behavior**: What actually happened
6. **Code Examples**: Minimal code to reproduce the issue
7. **Logs**: Relevant error messages and stack traces

**Bug Report Template:**

```markdown
## Bug Description
Brief description of the bug

## Environment
- OS: Ubuntu 20.04
- Python: 3.9.7
- Scrapyd: 1.3.0
- Scrapy: 2.5.1

## Steps to Reproduce
1. Start Scrapyd with default configuration
2. Deploy project using: `scrapyd-deploy`
3. Schedule spider: `curl http://localhost:6800/schedule.json -d project=test -d spider=example`
4. Check logs

## Expected Behavior
Spider should start and begin crawling

## Actual Behavior
Spider fails with ImportError

## Error Logs
```
2023-01-01 12:00:00 [scrapy.core.engine] ERROR: Spider error processing
Traceback (most recent call last):
  ...
```

## Additional Context
Any other relevant information
```

### Feature Requests

For feature requests, please include:

1. **Use Case**: Why is this feature needed?
2. **Proposed Solution**: How should it work?
3. **Alternatives**: Other ways to achieve the same goal
4. **Implementation Notes**: Technical considerations

## Release Process

### Version Numbers

We follow [Semantic Versioning](https://semver.org/):
- **Major** (X.0.0): Breaking changes
- **Minor** (1.X.0): New features, backward compatible
- **Patch** (1.1.X): Bug fixes, backward compatible

### Release Checklist

1. Update version in `pyproject.toml`
2. Update `CHANGELOG.md`
3. Run full test suite
4. Build and test documentation
5. Create git tag
6. Build and upload to PyPI
7. Create GitHub release
8. Announce on mailing list

## Community

### Communication Channels

- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: General questions and discussions
- **Scrapy Mailing List**: Development discussions
- **IRC**: #scrapy on Libera.Chat

### Getting Help

- Check existing issues and documentation first
- Use GitHub Discussions for questions
- Join the IRC channel for real-time help
- Be patient and respectful when asking for help

## Recognition

### Contributors

All contributors are recognized in:
- `AUTHORS` file
- Release notes
- GitHub contributors page

### Types of Contributions

We welcome all types of contributions:
- Code improvements and bug fixes
- Documentation enhancements
- Test coverage improvements
- Issue triage and support
- Translation work
- Performance optimizations
- Security improvements

## Advanced Contributing

### Plugin Development

If you're developing plugins for Scrapyd:

```python
# example_plugin.py
from scrapyd.plugins import SpiderEventPlugin

class EmailNotificationPlugin(SpiderEventPlugin):
    """Send email notifications for spider events."""

    def get_name(self) -> str:
        return "email_notifications"

    def get_version(self) -> str:
        return "1.0.0"

    def initialize(self, config):
        self.smtp_server = config.get('smtp_server')
        self.recipients = config.get('email_recipients', [])

    def on_spider_completed(self, project, spider, job_id, success, stats, **kwargs):
        if not success:
            self.send_failure_notification(project, spider, job_id, stats)

    def send_failure_notification(self, project, spider, job_id, stats):
        # Send email notification
        pass

# Register plugin in setup.py
entry_points = {
    'scrapyd.plugins': [
        'email_notifications = example_plugin:EmailNotificationPlugin',
    ],
}
```

### Performance Contributions

When contributing performance improvements:

1. **Benchmark First**: Measure current performance
2. **Profile Code**: Identify bottlenecks
3. **Measure Impact**: Quantify improvements
4. **Test at Scale**: Verify with realistic workloads
5. **Document Changes**: Explain the optimization

### Security Contributions

For security-related contributions:

1. **Follow Responsible Disclosure**: Report privately first
2. **Include Fix**: Provide both report and solution
3. **Test Thoroughly**: Ensure fix doesn't break functionality
4. **Document Impact**: Explain severity and scope

## License

By contributing to Scrapyd, you agree that your contributions will be licensed under the same [BSD License](LICENSE) as the project.

## Questions?

If you have questions about contributing, please:
1. Check this document first
2. Search existing issues
3. Ask in GitHub Discussions
4. Join our IRC channel

Thank you for contributing to Scrapyd! 🕷️