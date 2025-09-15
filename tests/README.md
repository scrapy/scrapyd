# Scrapyd Test Suite

This directory contains the comprehensive test suite for Scrapyd, organized into logical groups for efficient testing and development workflows.

## Test Organization

### 📁 Test Categories

#### `unit/` - Unit Tests
Test individual components in isolation without external dependencies.

- **Purpose**: Verify individual functions, classes, and modules work correctly
- **Speed**: Fast (< 1s per test)
- **Dependencies**: Minimal, mostly mocked
- **Examples**: Configuration parsing, storage interfaces, job management

#### `api/` - API Tests
Test web service endpoints and JSON API responses.

- **Purpose**: Verify HTTP endpoints return correct responses
- **Speed**: Medium (1-5s per test)
- **Dependencies**: Mock HTTP clients, no real servers
- **Examples**: `/schedule.json`, `/listjobs.json`, `/cancel.json`

#### `server/` - Server Tests
Test server functionality and web interface components.

- **Purpose**: Verify server configuration, startup, and web UI
- **Speed**: Medium (1-10s per test)
- **Dependencies**: Twisted test framework, mock resources
- **Examples**: Server configuration, web interface rendering

#### `integration_tests/` - Integration Tests
Test full system behavior with real servers and processes.

- **Purpose**: End-to-end testing with actual Scrapyd instances
- **Speed**: Slow (5-30s per test)
- **Dependencies**: Real servers, network connections, file system
- **Examples**: Full deployment workflow, authentication, live API calls

## Running Tests

### Quick Commands

```bash
# Run all tests
pytest

# Run specific test categories
pytest -m unit          # Unit tests only (fast)
pytest -m api           # API tests only
pytest -m server        # Server tests only
pytest -m integration   # Integration tests only (slow)

# Run with coverage
pytest --cov=scrapyd --cov-report=html

# Run specific test groups
pytest tests/unit/                    # All unit tests
pytest tests/api/                     # All API tests
pytest tests/server/                  # All server tests
pytest tests/integration_tests/       # All integration tests
```

### Advanced Usage

```bash
# Run tests by marker combinations
pytest -m "unit and not slow"        # Fast unit tests only
pytest -m "integration and auth"     # Authentication integration tests
pytest -m "not integration"          # Skip slow integration tests

# Run with different verbosity
pytest -v                            # Verbose output
pytest -vv                           # Extra verbose output
pytest -q                            # Quiet output

# Run specific test files or functions
pytest tests/unit/test_config.py     # Single file
pytest tests/unit/test_config.py::test_config_defaults  # Single test

# Debug failing tests
pytest --tb=long                     # Long traceback format
pytest --pdb                         # Drop into debugger on failure
pytest -x                            # Stop on first failure

# Parallel execution (requires pytest-xdist)
pytest -n 4                          # Run with 4 worker processes
pytest -n auto                       # Auto-detect CPU cores
```

## Test Markers

Tests are organized using pytest markers for flexible execution:

| Marker | Description | Speed | Dependencies |
|--------|-------------|-------|--------------|
| `unit` | Individual component tests | Fast | Minimal/Mocked |
| `api` | HTTP endpoint tests | Medium | Mock clients |
| `server` | Server functionality tests | Medium | Twisted framework |
| `integration` | End-to-end system tests | Slow | Real servers |
| `auth` | Authentication-related tests | Varies | Auth servers |
| `slow` | Tests that may timeout | Slow | Various |
| `network` | Tests requiring connectivity | Medium | Network access |

## Development Workflow

### For Contributors

1. **Pre-commit Testing** (fastest feedback):
   ```bash
   pytest -m unit
   ```

2. **Feature Development**:
   ```bash
   pytest tests/unit/ tests/api/
   ```

3. **Before Pull Request**:
   ```bash
   pytest  # Run all tests
   pytest --cov=scrapyd --cov-report=term-missing
   ```

4. **Integration Verification**:
   ```bash
   pytest -m integration
   ```

### Continuous Integration

Different CI stages can run different test subsets:

```yaml
# Example CI configuration
stages:
  - name: "Unit Tests"
    command: "pytest -m unit --junitxml=unit.xml"

  - name: "API Tests"
    command: "pytest -m api --junitxml=api.xml"

  - name: "Integration Tests"
    command: "pytest -m integration --junitxml=integration.xml"
```

## Writing New Tests

### Guidelines

1. **Choose the Right Category**:
   - `unit/` for testing individual functions/classes
   - `api/` for testing HTTP endpoints
   - `server/` for testing server behavior
   - `integration_tests/` for end-to-end scenarios

2. **Add Appropriate Markers**:
   ```python
   import pytest

   pytestmark = pytest.mark.unit  # For unit tests

   @pytest.mark.slow
   def test_long_running_operation():
       pass

   @pytest.mark.network
   def test_external_api():
       pass
   ```

3. **Follow Naming Conventions**:
   - Test files: `test_*.py`
   - Test functions: `test_*`
   - Test classes: `Test*`

### Test Structure Template

```python
import pytest

# Mark the entire module
pytestmark = pytest.mark.unit

class TestMyComponent:
    """Test the MyComponent class."""

    def test_basic_functionality(self):
        """Test basic functionality works correctly."""
        # Arrange
        component = MyComponent(config="test")

        # Act
        result = component.process()

        # Assert
        assert result.success is True

    @pytest.mark.parametrize("input,expected", [
        ("input1", "output1"),
        ("input2", "output2"),
    ])
    def test_multiple_inputs(self, input, expected):
        """Test component handles various inputs."""
        component = MyComponent()
        result = component.process(input)
        assert result == expected

    @pytest.mark.slow
    def test_performance_intensive(self):
        """Test that may take longer to complete."""
        # Use @pytest.mark.slow for tests that might timeout
        pass
```

## Test Data and Fixtures

### Shared Fixtures
Common fixtures are defined in `conftest.py` files:

- `tests/conftest.py` - Root level fixtures available to all tests
- `tests/integration_tests/conftest.py` - Integration-specific fixtures

### Test Data Locations
- `fixtures/` - Static test data files
- `projects/` - Sample Scrapy projects for testing

### Mock Objects
Located in:
- `mockapp.py` - Mock application components
- `mockserver.py` - Mock server implementations

## Troubleshooting

### Common Issues

1. **Import Errors**:
   ```bash
   # Run from project root
   cd /path/to/scrapyd
   pytest tests/
   ```

2. **Integration Tests Failing**:
   ```bash
   # Check if ports are available
   lsof -i :6800

   # Run integration tests with debug output
   pytest tests/integration_tests/ -v -s
   ```

3. **Timeouts**:
   ```bash
   # Increase timeout for slow tests
   pytest --timeout=60

   # Skip slow tests during development
   pytest -m "not slow"
   ```

4. **Coverage Issues**:
   ```bash
   # Generate detailed coverage report
   pytest --cov=scrapyd --cov-report=html
   # Open htmlcov/index.html in browser
   ```

### Debug Helpers

```python
# Add to test for debugging
import pytest
pytest.set_trace()  # Breakpoint

# Or use print debugging
import sys
print("Debug info:", variable, file=sys.stderr)
```

## Performance Optimization

### Test Execution Times

| Category | Typical Time | Parallelizable |
|----------|-------------|----------------|
| Unit | < 30s | ✅ Yes |
| API | 1-2 minutes | ✅ Yes |
| Server | 1-3 minutes | ⚠️ Limited |
| Integration | 3-10 minutes | ❌ No (shared resources) |

### Optimization Tips

1. **Use Parallel Execution**:
   ```bash
   pip install pytest-xdist
   pytest -n auto tests/unit/ tests/api/
   ```

2. **Skip Heavy Tests During Development**:
   ```bash
   pytest -m "not integration and not slow"
   ```

3. **Use Test Selection**:
   ```bash
   pytest tests/unit/test_config.py  # Test single module
   pytest -k "test_basic"           # Run tests matching pattern
   ```

## Contributing

When adding new tests:

1. Place them in the appropriate category directory
2. Add proper markers using `pytestmark`
3. Update this README if adding new test categories
4. Ensure tests are deterministic and don't depend on external services
5. Add docstrings explaining what the test verifies

## Resources

- [pytest documentation](https://docs.pytest.org/)
- [Twisted testing guide](https://docs.twisted.org/en/stable/core/howto/testing.html)
- [Scrapyd development guide](../CONTRIBUTING.md)