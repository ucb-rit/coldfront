# MyBRC/MyLRC User Portal

The MyBRC User Portal is an access management system for UC Berkeley Research IT's Berkeley Research Computing program. It enables users to create or join projects, gain access to the clusters managed by BRC, view the statuses of their requests and access, view their allocation quotas and usages, and update personal information. It enable administrators to handle these requests and manage users and projects.

The MyLRC User Portal is a second instance of the same system, developed for Lawrence Berkeley National Laboratory's Laboratory Research Computing program.

The portal is implemented on top of a fork of [ColdFront](https://coldfront.readthedocs.io/en/latest/).

## Getting started

1. After cloning the repository, prevent Git from detecting changes to file permissions.

   ```bash
   git config core.fileMode false
   ```

2. Select one of the following options for setting up a development environment.

   - [Docker](bootstrap/development/docker/README.md) (Recommended)
   - [Vagrant VM on VirtualBox](bootstrap/development/docs/vagrant-vm-README.md)

## Documentation

Documentation resides in a separate repository. Please request access.

### Miscellaneous Topics

- [Deployment](bootstrap/ansible/README.md)
- [REST API](coldfront/api/README.md)

## Running Tests

### Setting Up the Test Environment

1. **Activate the virtual environment**:
   ```bash
   source coldfront/venv/bin/activate  # or wherever your venv is located
   ```

2. **Install test dependencies** (if not already installed):
   ```bash
   pip install pytest pytest-django pytest-cov factory-boy
   ```

3. **Configure Django settings for tests**:
   The test configuration is already set up in `pytest.ini` and uses `coldfront.config.test_settings` which configures an in-memory SQLite database for fast test execution.

### Running Tests

**Run all tests**:
```bash
pytest coldfront/tests
```

**Run specific test directories**:
```bash
# Unit tests only
pytest coldfront/tests/utils/unit/

# Whitebox integration tests
pytest coldfront/tests/utils/whitebox/

# Blackbox end-to-end tests
pytest coldfront/tests/utils/blackbox/
```

**Run tests with coverage report**:
```bash
pytest coldfront/tests --cov=coldfront --cov-report=html
# View coverage report in htmlcov/index.html
```

**Run tests with specific markers**:
```bash
# Run only unit tests
pytest -m unit

# Run only whitebox tests
pytest -m whitebox

# Run only blackbox tests
pytest -m blackbox
```

**Run tests verbosely**:
```bash
pytest -v  # Verbose output
pytest -vv # Very verbose output
pytest -s  # Show print statements
```

### Test Structure

- **Unit Tests** (`coldfront/tests/utils/unit/`): Test individual components in isolation
- **Whitebox Tests** (`coldfront/tests/utils/whitebox/`): Test internal behavior and integrations
- **Blackbox Tests** (`coldfront/tests/utils/blackbox/`): Test end-to-end functionality from user perspective

### Test Fixtures

Test fixtures are defined in:
- `coldfront/tests/conftest.py` - Global fixtures for all tests
- `coldfront/tests/utils/conftest.py` - Fixtures specific to utils tests

Key fixtures include:
- `user`, `staff_user`, `superuser` - Different user types
- `project`, `allocation` - Project and allocation instances
- `project_user`, `active_project_user` - User-project relationships
- `django_db_setup` - Session-scoped database setup with required reference data

## License

ColdFront is released under the GPLv3 license. See the LICENSE file.
