# Sprint 2 Testing - Quick Start Guide

## 🚀 Get Started in 5 Minutes

### 1. Install Dependencies
```bash
pip install -r requirements-dev.txt
```

### 2. Run Existing Tests
```bash
# All Sprint 2 tests
pytest -m "oauth or mcp" -v

# Specific test files
pytest tests/integration/test_api_integrations.py -v
pytest tests/unit/test_oauth_service.py -v
pytest tests/e2e/test_mcp_integration_flow.py -v
```

### 3. Check Coverage
```bash
pytest -m "oauth or mcp" --cov=backend/app --cov-report=html
open htmlcov/index.html
```

---

## 📁 What's Already Done

✅ **Core Fixtures** (`tests/fixtures/`)
- `mcp_responses.py` - Mock API responses for all platforms
- `integration_fixtures.py` - Factories for test data
- `conftest.py` - All test fixtures configured

✅ **Integration Tests** (`tests/integration/`)
- `test_api_integrations.py` - 17 tests for API endpoints (Issue #4)

✅ **Unit Tests** (`tests/unit/`)
- `test_oauth_service.py` - 23 tests for OAuth service (Issue #5)

✅ **E2E Tests** (`tests/e2e/`)
- `test_mcp_integration_flow.py` - 9 end-to-end workflow tests

✅ **Documentation**
- `SPRINT2_TEST_PLAN.md` - Detailed test specifications
- `SPRINT2_DELIVERY_SUMMARY.md` - Complete delivery summary
- `QUICK_START_SPRINT2.md` - This file

---

## 🎯 What Needs to Be Done

### Priority 1: OAuth Flow Tests
**File:** `tests/integration/test_oauth_flows.py`
**Estimated Time:** 4-6 hours

```python
# Template
@pytest.mark.integration
@pytest.mark.oauth
@pytest.mark.asyncio
async def test_complete_oauth_flow_zoom(api_client, mock_oauth_service):
    """Test complete OAuth flow for Zoom"""
    # 1. Generate authorization URL
    # 2. Simulate callback
    # 3. Exchange code for tokens
    # 4. Verify integration created
    pass
```

**Run:** `pytest tests/integration/test_oauth_flows.py -v`

### Priority 2: Health Check Service Tests
**File:** `tests/unit/test_health_check_service.py`
**Estimated Time:** 4-5 hours

```python
# Template
@pytest.mark.unit
@pytest.mark.health
@pytest.mark.asyncio
async def test_health_check_for_zoom_connector(mock_health_check_service):
    """Test health check for Zoom connector"""
    # 1. Create integration
    # 2. Perform health check
    # 3. Verify status
    pass
```

**Run:** `pytest tests/unit/test_health_check_service.py -v`

### Priority 3: Health Monitoring Integration Tests
**File:** `tests/integration/test_health_monitoring.py`
**Estimated Time:** 5-7 hours

```python
# Template
@pytest.mark.integration
@pytest.mark.health
@pytest.mark.asyncio
async def test_scheduled_health_check_execution(mock_scheduler):
    """Test scheduled health check execution"""
    # 1. Schedule health checks
    # 2. Trigger execution
    # 3. Verify all integrations checked
    pass
```

**Run:** `pytest tests/integration/test_health_monitoring.py -v`

### Priority 4: Connector Tests
**Files:** `tests/unit/connectors/test_*.py`
**Estimated Time:** 2-3 hours per connector

```python
# Template
@pytest.mark.unit
@pytest.mark.connector
@pytest.mark.asyncio
async def test_zoom_connection_establishment(mock_zoom_connector):
    """Test Zoom connection establishment"""
    # 1. Connect with credentials
    # 2. Verify connection successful
    # 3. Test API calls
    pass
```

**Run:** `pytest tests/unit/connectors/ -v`

---

## 🧪 Using Test Fixtures

### OAuth Fixtures
```python
def test_example(mock_oauth_service, mock_oauth_token):
    # OAuth service already configured
    tokens = mock_oauth_service.exchange_code_for_token("zoom", "code")
    assert "access_token" in tokens
```

### MCP Connector Fixtures
```python
async def test_example(mock_zoom_connector):
    # Zoom connector with realistic responses
    meetings = await mock_zoom_connector.fetch_meetings()
    assert len(meetings["meetings"]) > 0
```

### Integration Fixtures
```python
def test_example(sample_integration, sample_oauth_token):
    # Pre-configured integration and token
    assert sample_integration["status"] == "connected"
    assert sample_oauth_token["integration_id"] == sample_integration["id"]
```

### Health Check Fixtures
```python
async def test_example(mock_health_check_service):
    # Health check service configured
    health = await mock_health_check_service.check_integration(integration_id)
    assert health["is_healthy"] is True
```

---

## 🏭 Using Test Factories

### Create Test Data
```python
from tests.fixtures.integration_fixtures import (
    IntegrationFactory,
    OAuthTokenFactory,
    HealthCheckFactory
)

# Simple usage
integration = IntegrationFactory.connected(platform="zoom")

# Specialized variants
expired_token = OAuthTokenFactory.expired()
unhealthy_check = HealthCheckFactory.unhealthy(error="Connection failed")

# Complex scenarios
from tests.fixtures.integration_fixtures import (
    create_integration_with_oauth,
    create_workspace_with_integrations
)

oauth_data = create_integration_with_oauth(platform="zoom")
workspace_data = create_workspace_with_integrations(["zoom", "slack"])
```

---

## 📦 Mock API Responses

### Get Platform Responses
```python
from tests.fixtures.mcp_responses import (
    get_zoom_meetings_list,
    get_slack_messages_list,
    get_oauth_token_response,
    get_rate_limit_error
)

# OAuth responses
token_response = get_oauth_token_response(platform="zoom")

# Platform API responses
meetings = get_zoom_meetings_list(count=10)
messages = get_slack_messages_list(count=20)

# Error responses
rate_limit = get_rate_limit_error(platform="zoom")
```

---

## 🎨 Test Patterns

### AAA Pattern (Arrange-Act-Assert)
```python
async def test_example(self, mock_service):
    # ARRANGE - Set up test data
    workspace_id = str(uuid4())
    integration = IntegrationFactory.connected()

    # ACT - Execute the code being tested
    result = await mock_service.create_integration(integration)

    # ASSERT - Verify the results
    assert result["status"] == "connected"
```

### Parameterized Tests
```python
@pytest.mark.parametrize("platform,expected", [
    ("zoom", "zoom.us"),
    ("slack", "slack.com"),
    ("discord", "discord.com"),
])
def test_oauth_url_generation(platform, expected, mock_oauth_service):
    url, _ = mock_oauth_service.generate_authorization_url(platform, workspace_id)
    assert expected in url
```

### Error Testing
```python
async def test_invalid_credentials(self, mock_service):
    """Test that invalid credentials raise appropriate error"""
    with pytest.raises(ValueError, match="Invalid credentials"):
        await mock_service.authenticate("invalid_token")
```

---

## 🏃 Common Commands

### Run Tests by Category
```bash
# OAuth tests only
pytest -m oauth -v

# Health monitoring tests
pytest -m health -v

# Connector tests
pytest -m connector -v

# All MCP tests
pytest -m mcp -v

# Fast tests only (skip E2E)
pytest -m "not slow" -v

# Integration tests only
pytest -m integration -v
```

### Run Specific Tests
```bash
# Single test file
pytest tests/unit/test_oauth_service.py -v

# Single test class
pytest tests/unit/test_oauth_service.py::TestOAuthStateManagement -v

# Single test method
pytest tests/unit/test_oauth_service.py::TestOAuthStateManagement::test_generate_oauth_state -v
```

### Coverage Reports
```bash
# Terminal report
pytest -m oauth --cov=backend/app --cov-report=term-missing

# HTML report
pytest -m oauth --cov=backend/app --cov-report=html
open htmlcov/index.html

# XML report (for CI)
pytest -m oauth --cov=backend/app --cov-report=xml
```

### Debugging
```bash
# Verbose output
pytest tests/unit/test_oauth_service.py -vv

# Show print statements
pytest tests/unit/test_oauth_service.py -s

# Debug on failure
pytest tests/unit/test_oauth_service.py --pdb

# Show slowest tests
pytest --durations=10
```

---

## 🔍 Finding Things

### Find Test Examples
```bash
# Find all OAuth tests
grep -r "@pytest.mark.oauth" tests/

# Find all health tests
grep -r "@pytest.mark.health" tests/

# Find usage of a fixture
grep -r "mock_zoom_connector" tests/
```

### Find Fixtures
```bash
# All fixtures in conftest.py
grep "^def " tests/conftest.py

# All factories
grep "class.*Factory" tests/fixtures/integration_fixtures.py
```

### Find Mock Responses
```bash
# Available mock responses
grep "^def get_" tests/fixtures/mcp_responses.py
```

---

## ❓ Troubleshooting

### Import Errors
```bash
# Ensure PYTHONPATH is set
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Or run with Python module syntax
python -m pytest tests/
```

### Fixture Not Found
```python
# Check fixture is in conftest.py
@pytest.fixture
def my_fixture():
    return "value"

# Check fixture scope matches test
@pytest.fixture(scope="function")  # default
@pytest.fixture(scope="class")
@pytest.fixture(scope="module")
@pytest.fixture(scope="session")
```

### Mock Not Working
```python
# Ensure correct import path
with patch("app.api.v1.integrations.get_integration_service"):
    # Not the module where it's defined, but where it's imported

# Use AsyncMock for async functions
from unittest.mock import AsyncMock
mock_service = AsyncMock()
```

### Tests Running Slow
```bash
# Run in parallel
pytest -n auto

# Skip slow tests
pytest -m "not slow"

# Run specific subset
pytest tests/unit/ -v
```

---

## 📚 Resources

### Documentation
- **Test Plan:** `tests/SPRINT2_TEST_PLAN.md` - Detailed specifications
- **Delivery Summary:** `tests/SPRINT2_DELIVERY_SUMMARY.md` - Complete summary
- **Main README:** `tests/README.md` - General testing guide
- **Backlog:** `backlog.md` - Acceptance criteria

### Reference Tests
- **Integration API:** `tests/integration/test_api_integrations.py`
- **OAuth Service:** `tests/unit/test_oauth_service.py`
- **E2E Flows:** `tests/e2e/test_mcp_integration_flow.py`

### External Docs
- Pytest: https://docs.pytest.org/
- Factory Boy: https://factoryboy.readthedocs.io/
- AsyncIO Testing: https://docs.pytest.org/en/stable/how-to/async.html

---

## 🎯 Success Checklist

### Before Submitting Tests
- [ ] All tests pass locally
- [ ] Coverage ≥ 80% for new code
- [ ] Tests follow AAA pattern
- [ ] Descriptive test names with docstrings
- [ ] No hardcoded values (use factories)
- [ ] Async tests marked with @pytest.mark.asyncio
- [ ] Appropriate markers added (@pytest.mark.oauth, etc.)
- [ ] No flaky tests (run 3 times to verify)

### Code Review Checklist
- [ ] Tests are isolated (no dependencies between tests)
- [ ] Mocks used for external dependencies
- [ ] Error cases covered
- [ ] Happy path and edge cases tested
- [ ] Tests are fast (<1s per test ideally)

---

## 💡 Pro Tips

1. **Use Existing Fixtures**
   - Don't create new mocks if fixture exists
   - Check `conftest.py` first

2. **Copy Existing Patterns**
   - Find similar test in codebase
   - Copy and modify for your case

3. **Use Factories for Test Data**
   - More maintainable than manual creation
   - Provides consistent test data

4. **Run Tests Frequently**
   - Run after each test written
   - Catch issues early

5. **Use Coverage to Find Gaps**
   - `--cov-report=term-missing` shows uncovered lines
   - Write tests for uncovered code paths

6. **Keep Tests Simple**
   - One assertion per test when possible
   - Clear and obvious what's being tested

7. **Document Complex Scenarios**
   - Add docstrings explaining the scenario
   - Use step-by-step comments in E2E tests

---

**Need Help?**
- Check `SPRINT2_TEST_PLAN.md` for detailed specifications
- Reference existing tests for patterns
- Look at fixtures in `conftest.py` for available mocks
- See `SPRINT2_DELIVERY_SUMMARY.md` for full context

**Current Status:** 60% Complete
**Next Priority:** `tests/integration/test_oauth_flows.py`

---

**Last Updated:** 2025-10-30
**Sprint:** Sprint 2 - MCP Integration Framework
