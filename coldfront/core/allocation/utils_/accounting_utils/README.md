# Accounting Utils

This package experimentally uses a Domain-Driven Design (DDD) approach to organize allocation accounting code.

## Structure

### `__init__.py`
Contains existing utility functions for allocation accounting operations. These are service-layer functions in a procedural style (maintained for backward compatibility).

### `domain.py`
Contains pure domain models with business logic. These classes have no dependencies on Django or infrastructure concerns.

### `services/`
Contains service layer classes that orchestrate workflows and coordinate between domain models and infrastructure.
