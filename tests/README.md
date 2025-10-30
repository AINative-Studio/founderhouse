# AI Chief of Staff - Testing Infrastructure

## Overview

Comprehensive testing infrastructure for Sprint 1 of the AI Chief of Staff project. This test suite ensures 90%+ code coverage and validates all core functionality including multi-tenant isolation, Row-Level Security (RLS), vector search, and MCP integrations.

## Test Structure

```
tests/
├── conftest.py              # Shared fixtures and configuration
├── fixtures/
│   ├── __init__.py
│   └── sample_data.py       # Factory Boy test data generators
├── unit/
│   ├── __init__.py
│   ├── test_models.py       # Pydantic model validation tests
│   ├── test_services.py     # Business logic unit tests
│   └── test_database.py     # Database, RLS, and vector search tests
├── integration/
│   ├── __init__.py
│   ├── test_api_health.py   # Health and monitoring endpoint tests
│   ├── test_api_workspaces.py  # Workspace API tests
│   └── test_api_integrations.py  # MCP integration tests
├── e2e/
│   ├── __init__.py
│   └── test_workspace_flow.py  # End-to-end user workflow tests
└── README.md                # This file
```

## Quick Start

### Installation

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Or with Poetry
poetry install --with dev
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=backend/app --cov-report=html

# Run specific test categories
pytest -m unit          # Unit tests only
pytest -m integration   # Integration tests only
pytest -m e2e          # End-to-end tests only
pytest -m rls          # RLS policy tests
pytest -m vector       # Vector search tests

# Run parallel for speed
pytest -n auto

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/unit/test_models.py

# Run specific test
pytest tests/unit/test_models.py::TestWorkspaceBase::test_valid_workspace_name
```

## Test Categories

### Unit Tests (`tests/unit/`)

Fast, isolated tests that validate individual components without external dependencies.

**Coverage:**
- Pydantic model validation
- Field constraints and data types
- Serialization/deserialization
- Business logic functions
- Database queries (mocked)

**Example:**
```python
def test_workspace_name_required():
    """Test that workspace name is required."""
    with pytest.raises(ValidationError):
        WorkspaceBase()
```

**Run:**
```bash
pytest tests/unit/ -m unit
```

### Integration Tests (`tests/integration/`)

Tests that verify interactions between components, including API endpoints and database.

**Coverage:**
- FastAPI endpoint responses
- Request/response validation
- Authentication and authorization
- Database transactions
- MCP integration connections

**Example:**
```python
def test_health_endpoint_returns_200(client):
    """Test that /health endpoint returns 200 OK."""
    response = client.get("/health")
    assert response.status_code == 200
```

**Run:**
```bash
pytest tests/integration/ -m integration
```

### End-to-End Tests (`tests/e2e/`)

Complete user workflow tests that simulate real-world usage scenarios.

**Coverage:**
- Complete workspace setup workflow
- Meeting ingestion → transcript → task creation
- Multi-workspace isolation
- Communication intelligence flows
- Briefing generation workflows

**Example:**
```python
async def test_complete_workspace_onboarding(client, auth_headers):
    """Test complete workspace setup from creation to usage."""
    # Create workspace
    workspace = await client.post("/api/v1/workspaces", ...)

    # Add members
    await client.post(f"/api/v1/workspaces/{workspace_id}/members", ...)

    # Connect integrations
    await client.post("/api/v1/integrations/connect", ...)
```

**Run:**
```bash
pytest tests/e2e/ -m e2e
```

## Test Fixtures

### Database Fixtures

```python
@pytest_asyncio.fixture
async def db_connection(test_env):
    """Provides async database connection with automatic rollback."""
    # Connection automatically cleaned up after test
```

### Supabase Client Fixtures

```python
@pytest.fixture
def supabase_client_mock():
    """Mock Supabase client for testing without database."""
    # Returns configured mock
```

### MCP Integration Mocks

```python
@pytest.fixture
def mock_zoom_mcp():
    """Mock Zoom MCP integration."""
    # Returns AsyncMock with standard responses
```

### Test Data Factories

```python
from tests.fixtures.sample_data import WorkspaceFactory, MemberFactory

def test_with_factory():
    workspace = WorkspaceFactory()
    member = MemberFactory(workspace_id=workspace["id"])
```

## Configuration

### pytest.ini

Main pytest configuration with markers, coverage settings, and test discovery rules.

```ini
[pytest]
testpaths = tests
python_files = test_*.py
addopts =
    --cov=backend/app
    --cov-fail-under=90
    -v
```

### .coveragerc

Coverage configuration with exclusions and thresholds.

```ini
[run]
source = backend/app
omit = */tests/*, */migrations/*

[report]
fail_under = 90
```

## Test Markers

Use markers to categorize and filter tests:

```python
@pytest.mark.unit
def test_something():
    """Fast unit test."""
    pass

@pytest.mark.integration
@pytest.mark.database
async def test_with_database(db_connection):
    """Integration test requiring database."""
    pass

@pytest.mark.e2e
@pytest.mark.slow
async def test_complete_flow():
    """End-to-end test (may be slow)."""
    pass

@pytest.mark.rls
def test_row_level_security():
    """Test RLS policies."""
    pass

@pytest.mark.vector
def test_vector_search():
    """Test pgvector functionality."""
    pass
```

**Run specific markers:**
```bash
pytest -m "unit and not slow"
pytest -m "integration and database"
pytest -m "not slow"
```

## Coverage Requirements

### Sprint 1 Requirements

- **Overall Coverage:** 90% minimum
- **Unit Tests:** 95% minimum
- **Integration Tests:** 85% minimum
- **Critical Paths:** 100% required
  - Authentication
  - RLS policies
  - Workspace isolation
  - Data encryption

### Viewing Coverage Reports

```bash
# Generate HTML report
pytest --cov=backend/app --cov-report=html

# Open in browser
open htmlcov/index.html

# Terminal report
pytest --cov=backend/app --cov-report=term-missing

# XML report (for CI/CD)
pytest --cov=backend/app --cov-report=xml
```

## Database Testing

### Setup Test Database

Tests use PostgreSQL with pgvector extension:

```bash
# Using Docker
docker run -d \
  --name ai-cos-test-db \
  -e POSTGRES_PASSWORD=postgres \
  -p 5432:5432 \
  ankane/pgvector:latest

# Run migrations
alembic upgrade head
```

### RLS Testing

Row-Level Security tests verify multi-tenant isolation:

```python
@pytest.mark.rls
async def test_workspace_isolation(db_connection, test_workspaces):
    """Verify users cannot access other workspaces."""
    workspace_a_id, workspace_b_id = test_workspaces

    # User A tries to access workspace B data
    result = await db_connection.fetch(
        "SELECT * FROM core.founders WHERE workspace_id = $1",
        workspace_b_id
    )

    # Should return empty due to RLS
    assert len(result) == 0
```

### Vector Search Testing

Test pgvector semantic search functionality:

```python
@pytest.mark.vector
async def test_cosine_similarity_search(db_connection):
    """Test vector similarity search performance."""
    query_embedding = [0.1] * 1536

    results = await db_connection.fetch(
        """
        SELECT name, 1 - (embedding <=> $1::vector) AS similarity
        FROM core.contacts
        WHERE workspace_id = $2
        ORDER BY embedding <=> $1::vector
        LIMIT 5
        """,
        query_embedding,
        workspace_id
    )

    assert len(results) == 5
    assert all(r["similarity"] >= 0 for r in results)
```

## Continuous Integration

### GitHub Actions Workflow

The test suite runs automatically on:
- Push to `main` or `develop`
- Pull requests to `main` or `develop`
- Manual workflow dispatch

**Workflow stages:**
1. **Lint** - Black, isort, flake8, mypy, pylint
2. **Unit Tests** - Fast isolated tests
3. **Integration Tests** - API and database tests
4. **E2E Tests** - Complete workflow tests
5. **Coverage** - Enforce 90% minimum
6. **Security** - Safety and Bandit scans
7. **Mutation Testing** - Test quality validation (main branch only)

### CI/CD Commands

```bash
# Local CI simulation
pytest --cov=backend/app --cov-fail-under=90 -v -n auto

# Same as CI pipeline
pytest tests/ \
  --cov=backend/app \
  --cov-report=xml \
  --cov-report=term-missing \
  --cov-fail-under=90 \
  -v -n auto
```

## Writing Tests

### Test-Driven Development (TDD)

1. **Write failing test first**
```python
def test_workspace_creation():
    """Test workspace can be created with valid name."""
    workspace = create_workspace("Test Workspace")
    assert workspace.name == "Test Workspace"
```

2. **Implement minimal code to pass**
```python
def create_workspace(name: str) -> Workspace:
    return Workspace(name=name)
```

3. **Refactor and improve**
```python
def create_workspace(name: str) -> Workspace:
    if not name or len(name) > 255:
        raise ValueError("Invalid workspace name")
    return Workspace(name=name)
```

### Test Structure (AAA Pattern)

```python
def test_example():
    # ARRANGE - Set up test data
    workspace_id = uuid4()
    user_id = uuid4()

    # ACT - Execute the code being tested
    result = create_member(workspace_id, user_id, role="admin")

    # ASSERT - Verify the results
    assert result.role == "admin"
    assert result.workspace_id == workspace_id
```

### Property-Based Testing

Use Hypothesis for property-based tests:

```python
from hypothesis import given, strategies as st

@given(st.text(min_size=1, max_size=255))
def test_workspace_accepts_valid_strings(name: str):
    """Test workspace accepts any string within constraints."""
    workspace = WorkspaceBase(name=name)
    assert workspace.name == name
```

## Mutation Testing

Mutation testing validates test quality by introducing bugs:

```bash
# Run mutation testing
mutmut run --paths-to-mutate=backend/app

# View results
mutmut results

# Show surviving mutants
mutmut show

# Generate HTML report
mutmut html
```

**Interpreting results:**
- **Killed mutants:** Good - tests caught the bug
- **Surviving mutants:** Bad - tests didn't catch the bug
- **Timeout:** Mutant caused infinite loop
- **Suspicious:** Unexpected behavior

## Performance Testing

### Load Testing

```python
@pytest.mark.slow
async def test_concurrent_requests():
    """Test system under concurrent load."""
    async with AsyncClient(app=app) as client:
        tasks = [client.get("/health") for _ in range(100)]
        responses = await asyncio.gather(*tasks)

        assert all(r.status_code == 200 for r in responses)
```

### Query Performance

```python
@pytest.mark.database
async def test_query_performance(db_connection):
    """Test query completes within 300ms."""
    import time

    start = time.time()
    result = await db_connection.fetch("SELECT * FROM ...")
    elapsed = (time.time() - start) * 1000

    assert elapsed < 300, f"Query took {elapsed}ms"
```

## Troubleshooting

### Common Issues

**Tests fail with database connection error:**
```bash
# Ensure PostgreSQL is running
docker ps | grep postgres

# Check connection settings in conftest.py
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
```

**Coverage below 90%:**
```bash
# Find uncovered lines
pytest --cov=backend/app --cov-report=term-missing

# Add tests for uncovered code
# or add `# pragma: no cover` for non-testable code
```

**Slow tests:**
```bash
# Run tests in parallel
pytest -n auto

# Skip slow tests during development
pytest -m "not slow"

# Profile test duration
pytest --durations=10
```

**Import errors:**
```bash
# Ensure backend is in PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Or run with Python module syntax
python -m pytest tests/
```

## Best Practices

1. **Keep tests independent** - No test should depend on another
2. **Use descriptive names** - Test name should describe what's being tested
3. **Test one thing** - Each test should validate one behavior
4. **Fast feedback** - Unit tests should run in milliseconds
5. **Clean up** - Use fixtures for automatic cleanup
6. **Mock external services** - Don't call real APIs in tests
7. **Test edge cases** - Empty strings, null values, max lengths
8. **Document acceptance criteria** - Include in docstring
9. **Maintain test quality** - Tests should be as clean as production code
10. **Update tests with code** - Keep tests synchronized with changes

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [Factory Boy](https://factoryboy.readthedocs.io/)
- [Hypothesis](https://hypothesis.readthedocs.io/)
- [Coverage.py](https://coverage.readthedocs.io/)
- [Mutmut](https://mutmut.readthedocs.io/)

## Sprint 1 Test Checklist

- [x] Test directory structure created
- [x] Pytest configuration (pytest.ini)
- [x] Coverage configuration (.coveragerc)
- [x] Shared fixtures (conftest.py)
- [x] Test data factories (fixtures/sample_data.py)
- [x] Model validation tests (unit/test_models.py)
- [x] Database and RLS tests (unit/test_database.py)
- [x] Health endpoint tests (integration/test_api_health.py)
- [x] Workspace API tests (integration/test_api_workspaces.py)
- [x] End-to-end workflow tests (e2e/test_workspace_flow.py)
- [x] GitHub Actions CI/CD (.github/workflows/test.yml)
- [x] Testing documentation (tests/README.md)

## Next Steps

### Sprint 2: MCP Integration Testing
- Test MCP connector registry
- OAuth flow testing
- Integration health check tests
- Token refresh testing

### Sprint 3: Meeting Intelligence Testing
- Transcript ingestion tests
- Summarization pipeline tests
- Action item extraction tests
- Task routing tests

### Sprint 4: Insights & Briefings Testing
- KPI ingestion tests
- Anomaly detection tests
- Brief generation tests
- Investor report tests

## Contact

For questions or issues with the test infrastructure, please:
1. Check this documentation
2. Review test examples in the codebase
3. Open an issue in GitHub
4. Contact the test engineering team

---

**Remember:** Good tests are the foundation of reliable software. Invest time in writing quality tests and they'll save you time debugging later.
