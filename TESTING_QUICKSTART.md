# Testing Quick Start Guide

## 5-Minute Setup

### 1. Install Dependencies
```bash
pip install -r requirements-dev.txt
```

### 2. Run Your First Test
```bash
pytest tests/unit/test_models.py -v
```

### 3. Check Coverage
```bash
pytest --cov=backend/app --cov-report=term-missing
```

## Common Commands

```bash
# Run all tests
pytest

# Run specific test type
pytest -m unit              # Unit tests
pytest -m integration       # Integration tests
pytest -m e2e              # End-to-end tests

# Run with coverage
pytest --cov=backend/app --cov-report=html
open htmlcov/index.html    # View report

# Fast tests only
pytest -m "not slow" -n auto

# Watch mode
./run_tests.sh watch

# CI simulation
./run_tests.sh ci
```

## Writing Your First Test

```python
# tests/unit/test_my_feature.py

import pytest

@pytest.mark.unit
def test_my_feature():
    """Test description."""
    # ARRANGE
    input_data = "test"

    # ACT
    result = my_function(input_data)

    # ASSERT
    assert result == expected
```

## Using Fixtures

```python
def test_with_workspace(sample_workspace):
    """Test using workspace fixture."""
    assert sample_workspace["name"]

def test_with_database(db_connection):
    """Test with real database."""
    result = await db_connection.fetch("SELECT 1")
    assert result
```

## Coverage Requirements

- Overall: **90%** minimum
- Unit tests: **95%** target
- Integration: **85%** target
- Critical paths: **100%** required

## Test Markers

```python
@pytest.mark.unit          # Fast unit test
@pytest.mark.integration   # Integration test
@pytest.mark.e2e          # End-to-end test
@pytest.mark.database     # Needs database
@pytest.mark.slow         # Long-running test
@pytest.mark.rls          # RLS policy test
@pytest.mark.vector       # Vector search test
```

## Troubleshooting

**Tests fail with import error:**
```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

**Database connection error:**
```bash
# Start PostgreSQL with pgvector
docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=postgres ankane/pgvector:latest
```

**Coverage below 90%:**
```bash
# Find uncovered lines
pytest --cov=backend/app --cov-report=term-missing

# Run specific uncovered file
pytest tests/unit/test_models.py --cov=backend/app/models/workspace.py
```

## Resources

- **Full Documentation:** [tests/README.md](tests/README.md)
- **Test Summary:** [TESTING_SUMMARY.md](TESTING_SUMMARY.md)
- **Test Runner:** `./run_tests.sh help`

## CI/CD

Tests run automatically on:
- Every push to main/develop
- Every pull request
- Blocks merge if coverage < 90%

View results: GitHub Actions tab

---

**Ready to test? Run:** `./run_tests.sh all`
