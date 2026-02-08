# Testing

## Running Tests

Use the virtual environment and run:

```powershell
pytest .
```

## Pytest Configuration

The repo includes a `pytest.ini` at the root that:

- adds the repo root to `pythonpath` for imports like `blueprints.*`
- limits discovery to `tests/python`

## Environment Overrides

These environment variables override runtime paths, including in migrations:

- `OP-1Z_SM_CONFIG_DIR` sets the config directory
- `OP-1Z_SM_WORKING_DIR` sets the working directory

When `OP-1Z_SM_WORKING_DIR` causes v1 and v2 working directories to resolve to
the same path, the v2.0.0 migration skips working-directory copying to avoid
self-copy.

## Running Migrations In Tests

Migrations are skipped by default in tests. To enable them for a specific test,
add the `run_migrations` marker:

```python
import pytest

@pytest.mark.run_migrations
def test_migration_runs(app):
    # call app_startup_tasks() or invoke migrator directly
    ...
```
