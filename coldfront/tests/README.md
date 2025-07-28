# ColdFront Testing Protocol

This directory contains comprehensive tests for the ColdFront application using pytest and django-pytest.

## Directory Structure

```
tests/
├── conftest.py              # Global fixtures and configuration
├── README.md               # This file
└── {app_name}/             # Tests for each app (utils, project, etc.)
    ├── conftest.py         # App-specific fixtures
    ├── unit/               # Unit tests - test individual functions/methods
    │   ├── __init__.py
    │   └── test_*.py
    ├── whitebox/           # Whitebox tests - test internal behavior/integration
    │   ├── __init__.py
    │   └── test_*.py
    └── blackbox/           # Blackbox tests - test external behavior/end-to-end
        ├── __init__.py
        └── test_*.py
```

## Test Types

### Unit Tests (`unit/`)
- Test individual functions, methods, and classes in isolation
- Use mocks for external dependencies
- Fast execution, no database interactions unless necessary
- Focus on business logic and edge cases

### Whitebox Tests (`whitebox/`)
- Test internal behavior and integration between components
- May use database and external services
- Test data flow, error handling, and component interactions
- Knowledge of internal implementation is used

### Blackbox Tests (`blackbox/`)
- Test external behavior from user's perspective
- Full end-to-end workflows
- Test through HTTP requests, UI interactions
- No knowledge of internal implementation

## Running Tests

```bash
# Run all tests
pytest coldfront/tests/

# Run specific app tests
pytest coldfront/tests/utils/

# Run specific test type
pytest coldfront/tests/utils/unit/
pytest coldfront/tests/utils/whitebox/
pytest coldfront/tests/utils/blackbox/

# Run with coverage
pytest --cov=coldfront coldfront/tests/

# Run specific test file
pytest coldfront/tests/utils/unit/test_tracking_base.py

# Run with specific markers
pytest -m "unit" coldfront/tests/
pytest -m "slow" coldfront/tests/
```

## Test Markers

Use pytest markers to categorize tests:

```python
@pytest.mark.unit          # Unit test
@pytest.mark.whitebox      # Whitebox test  
@pytest.mark.blackbox      # Blackbox test
@pytest.mark.slow          # Slow running test
@pytest.mark.django_db     # Requires database
@pytest.mark.parametrize   # Parameterized test
```

## Best Practices

1. **Fixtures**: Use fixtures in `conftest.py` for common test data and setup
2. **Parameterization**: Use `@pytest.mark.parametrize` for testing multiple scenarios
3. **Database**: Use `@pytest.mark.django_db` sparingly, prefer mocking when possible
4. **Isolation**: Each test should be independent and not rely on other tests
5. **Naming**: Use descriptive test names that explain the scenario being tested
6. **Arrange-Act-Assert**: Structure tests clearly with setup, execution, and verification
7. **Edge Cases**: Test both happy path and error conditions

## Example Test Structure

```python
import pytest
from unittest.mock import Mock, patch

class TestYourClass:
    """Tests for YourClass functionality."""
    
    @pytest.mark.unit
    @pytest.mark.parametrize("input_value,expected", [
        ("value1", "result1"),
        ("value2", "result2"),
    ])
    def test_method_with_different_inputs(self, input_value, expected):
        # Arrange
        instance = YourClass()
        
        # Act
        result = instance.method(input_value)
        
        # Assert
        assert result == expected

    @pytest.mark.django_db
    @pytest.mark.whitebox
    def test_method_with_database(self, user_factory):
        # Test with database interactions
        pass
```

## Adding New Tests

When adding tests for a new app:

1. Create `tests/{app_name}/` directory
2. Add `conftest.py` with app-specific fixtures
3. Create `unit/`, `whitebox/`, `blackbox/` subdirectories
4. Add `__init__.py` files to make them Python packages
5. Write tests following the naming convention `test_*.py`