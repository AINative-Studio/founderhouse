# Sprint 2: MCP Integration Framework - Comprehensive Test Plan

## Executive Summary

This document outlines the complete testing strategy for Sprint 2: MCP Integration Framework. It covers all test files, their purpose, and acceptance criteria as defined in the backlog.md Epic 2.

**Test Coverage Goal:** 80%+ across all MCP integration code
**Total Test Files:** 15+
**Test Categories:** Unit, Integration, End-to-End

---

## Test Files Status

### ✅ COMPLETED

1. **tests/fixtures/mcp_responses.py**
   - Mock OAuth token responses (success, refresh, errors)
   - Platform-specific API responses (Zoom, Slack, Discord, Outlook, Monday, Notion, Granola)
   - Error responses (rate limits, authentication, server errors)
   - Utility functions for generating mock data

2. **tests/fixtures/integration_fixtures.py**
   - OAuthTokenFactory, OAuthStateFactory
   - HealthCheckFactory, ConnectorConfigFactory
   - IntegrationFactory with OAuth support
   - WebhookEventFactory, SyncJobFactory
   - Utility functions for creating complex test scenarios

3. **tests/conftest.py** (Updated)
   - OAuth fixtures (state, token, service, provider configs)
   - Health check fixtures (service, scheduler)
   - MCP connector fixtures (base, Zoom, Slack, Discord, Outlook, Monday)
   - Integration service fixtures
   - New test markers: oauth, health, connector

4. **pytest.ini** (Updated)
   - Added oauth, health, connector markers

5. **tests/integration/test_api_integrations.py** (Issue #4)
   - ✅ POST /api/v1/integrations/connect with valid credentials
   - ✅ POST /api/v1/integrations/connect with invalid credentials
   - ✅ Duplicate integration handling
   - ✅ DELETE /api/v1/integrations/{id} successful disconnection
   - ✅ Token revocation during disconnect
   - ✅ GET /api/v1/integrations list all
   - ✅ Workspace isolation verification
   - ✅ Filter by platform
   - ✅ Filter by status
   - ✅ GET /api/v1/integrations/{id}/health status
   - ✅ Health check includes last sync timestamp
   - ✅ Error details when available
   - ✅ Connection persistence across restarts

6. **tests/unit/test_oauth_service.py** (Issue #5 - Partial)
   - ✅ OAuth state generation and validation
   - ✅ Authorization URL generation (Zoom, Slack, Discord)
   - ✅ Token exchange from authorization code
   - ✅ Token refresh logic
   - ✅ Token expiration detection
   - ✅ Automatic refresh 24h before expiry
   - ✅ Platform-specific OAuth configs

---

## ⏳ REMAINING TEST FILES TO CREATE

### Issue #5: OAuth Integration Tests

**tests/integration/test_oauth_flows.py**

Purpose: Test complete OAuth flows with mocked providers

Test Coverage:
```python
@pytest.mark.integration
@pytest.mark.oauth
class TestCompleteOAuthFlow:
    """End-to-end OAuth flow testing"""

    async def test_complete_oauth_flow_zoom(self):
        """
        Given: User initiates Zoom OAuth
        When: Complete flow from authorization to callback
        Then: Integration created with valid token
        """
        # 1. Generate authorization URL with state
        # 2. Simulate user authorization
        # 3. Handle callback with code
        # 4. Exchange code for tokens
        # 5. Store encrypted tokens
        # 6. Verify integration status = connected

    async def test_oauth_callback_with_valid_state(self):
        """
        Given: OAuth callback received
        When: State parameter validated
        Then: Token exchange proceeds
        """

    async def test_oauth_callback_with_invalid_state(self):
        """
        Given: OAuth callback with invalid state
        When: State validation fails
        Then: Returns error, no token exchange
        """

    async def test_oauth_callback_with_expired_state(self):
        """
        Given: OAuth callback with expired state (>10min)
        When: State validation attempted
        Then: Returns error, CSRF protection activated
        """

    async def test_oauth_user_denies_access(self):
        """
        Given: User denies authorization
        When: Callback received with error=access_denied
        Then: Integration not created, user informed
        """

    async def test_oauth_token_storage_encryption(self):
        """
        Given: Token exchange successful
        When: Token stored in database
        Then: Credentials encrypted with AES-256
        """

    async def test_oauth_multi_workspace_isolation(self):
        """
        Given: Multiple workspaces
        When: Each workspace authenticates same platform
        Then: Tokens isolated per workspace
        """

    async def test_oauth_pkce_flow_for_public_clients(self):
        """
        Given: Public client (SPA, mobile)
        When: OAuth with PKCE initiated
        Then: Code challenge/verifier used correctly
        """
```

---

### Issue #6: Health Check Service

**tests/unit/test_health_check_service.py**

Purpose: Unit tests for health check service logic

Test Coverage:
```python
@pytest.mark.unit
@pytest.mark.health
class TestHealthCheckService:
    """Unit tests for health check service"""

    async def test_health_check_for_zoom_connector(self):
        """
        Given: Zoom integration configured
        When: health_check() called
        Then: Verifies Zoom API connectivity
        """

    async def test_health_check_for_slack_connector(self):
        """Similar for Slack"""

    async def test_token_validity_verification(self):
        """
        Given: OAuth token stored
        When: health_check() called
        Then: Verifies token not expired
        """

    async def test_connection_timeout_handling(self):
        """
        Given: Platform API slow/unavailable
        When: health_check() times out (30s)
        Then: Returns error status, logs timeout
        """

    async def test_rate_limit_detection(self):
        """
        Given: API returns 429 Rate Limit
        When: health_check() called
        Then: Detects rate limit, logs retry-after
        """

    async def test_health_status_updates(self):
        """
        Given: Health check completes
        When: Status retrieved
        Then: Integration status updated in DB
        """

    async def test_event_logging_on_health_check(self):
        """
        Given: Health check performed
        When: Check completes (success or failure)
        Then: Event logged to ops.events
        """

    async def test_health_check_retries_on_transient_errors(self):
        """
        Given: Temporary network error
        When: health_check() fails
        Then: Retries 3 times before marking as error
        """
```

**tests/integration/test_health_monitoring.py**

Purpose: Integration tests for scheduled health checks

Test Coverage:
```python
@pytest.mark.integration
@pytest.mark.health
@pytest.mark.slow
class TestHealthMonitoring:
    """Integration tests for health monitoring system"""

    async def test_scheduled_health_check_execution(self):
        """
        Given: Health check scheduled every 6 hours
        When: Scheduler triggers check
        Then: All active integrations checked
        """

    async def test_health_check_returns_200_for_all_active_mcps(self):
        """
        Given: Workspace with 5 active integrations
        When: Health check runs
        Then: All return healthy status
        """

    async def test_failed_integration_marked_as_error(self):
        """
        Given: Slack integration connection fails
        When: Health check detects failure
        Then: Status updated to 'error' in DB
        """

    async def test_health_dashboard_aggregation(self):
        """
        Given: Multiple integrations with various statuses
        When: Dashboard queried
        Then: Aggregated health data returned
        """

    async def test_alert_triggering_for_failures(self):
        """
        Given: Integration health check fails
        When: Failure detected
        Then: Alert sent to workspace admins
        """

    async def test_recovery_after_temporary_failure(self):
        """
        Given: Integration marked as 'error'
        When: Platform recovers, next check succeeds
        Then: Status updated to 'connected'
        """

    async def test_health_check_skips_revoked_integrations(self):
        """
        Given: Integration status = 'revoked'
        When: Health check runs
        Then: Revoked integrations skipped
        """

    async def test_parallel_health_checks_for_performance(self):
        """
        Given: 10 integrations to check
        When: Health check triggered
        Then: Checks run in parallel, complete <10s
        """
```

---

### MCP Connector Tests

**tests/unit/connectors/test_base_connector.py**

Purpose: Test base connector interface and common methods

Test Coverage:
```python
@pytest.mark.unit
@pytest.mark.connector
class TestBaseConnector:
    """Tests for base MCP connector"""

    async def test_connect_method_interface(self):
        """
        Given: Base connector instantiated
        When: connect() called
        Then: Establishes connection to platform
        """

    async def test_disconnect_method_interface(self):
        """
        Given: Connected connector
        When: disconnect() called
        Then: Closes connection gracefully
        """

    async def test_test_connection_verifies_credentials(self):
        """
        Given: Credentials provided
        When: test_connection() called
        Then: Verifies credentials without full connection
        """

    async def test_credential_encryption(self):
        """
        Given: Plaintext credentials
        When: encrypt_credentials() called
        Then: Returns encrypted bytes using AES-256
        """

    async def test_credential_decryption(self):
        """
        Given: Encrypted credentials
        When: decrypt_credentials() called
        Then: Returns original plaintext credentials
        """

    async def test_error_handling_for_connection_failures(self):
        """
        Given: Platform unreachable
        When: connect() called
        Then: Raises ConnectionError with details
        """

    async def test_rate_limiting_respects_api_limits(self):
        """
        Given: Platform rate limit = 100 req/min
        When: Multiple requests made
        Then: Connector enforces rate limit
        """

    async def test_automatic_retry_on_transient_errors(self):
        """
        Given: Temporary network error
        When: API call fails
        Then: Retries up to 3 times with backoff
        """
```

**tests/unit/connectors/test_zoom_connector.py**

Purpose: Test Zoom-specific connector functionality

Test Coverage:
```python
@pytest.mark.unit
@pytest.mark.connector
class TestZoomConnector:
    """Tests for Zoom MCP connector"""

    async def test_zoom_connection_establishment(self):
        """
        Given: Valid Zoom OAuth credentials
        When: connect() called
        Then: Connection established, user info retrieved
        """

    async def test_zoom_authentication_with_jwt(self):
        """
        Given: JWT credentials (for server-to-server)
        When: authenticate() called
        Then: JWT token generated and validated
        """

    async def test_zoom_api_calls_with_mock_responses(self):
        """
        Given: Zoom connector authenticated
        When: fetch_meetings() called
        Then: Returns list of meetings
        """

    async def test_zoom_error_handling_invalid_token(self):
        """
        Given: Invalid OAuth token
        When: API call attempted
        Then: Raises AuthenticationError
        """

    async def test_zoom_rate_limiting(self):
        """
        Given: Zoom rate limit = 80 req/min
        When: Multiple requests made
        Then: Respects rate limit
        """

    async def test_zoom_token_refresh_on_expiry(self):
        """
        Given: Access token expired
        When: API call attempted
        Then: Automatically refreshes token
        """

    async def test_zoom_webhook_signature_verification(self):
        """
        Given: Zoom webhook received
        When: verify_signature() called
        Then: Validates webhook authenticity
        """
```

**Similar connector test files:**
- `test_slack_connector.py`
- `test_discord_connector.py`
- `test_outlook_connector.py`
- `test_monday_connector.py`
- `test_notion_connector.py`
- `test_granola_connector.py`

Each follows same pattern with platform-specific tests.

---

### End-to-End Integration Flow Tests

**tests/e2e/test_mcp_integration_flow.py**

Purpose: Complete integration setup and usage workflows

Test Coverage:
```python
@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.mcp
class TestMCPIntegrationFlow:
    """End-to-end MCP integration workflows"""

    async def test_complete_integration_setup_flow(self):
        """
        Scenario: User sets up Zoom integration from scratch

        Steps:
        1. Create workspace
        2. Initiate OAuth for Zoom
        3. Complete OAuth callback
        4. Verify integration status = 'connected'
        5. Test connection
        6. Fetch sample Zoom meetings
        7. Verify data stored correctly
        """

    async def test_token_expiration_and_refresh(self):
        """
        Scenario: OAuth token expires and auto-refreshes

        Steps:
        1. Create integration with token expiring in 1 hour
        2. Mock time forward 23 hours
        3. Trigger API call
        4. Verify automatic token refresh
        5. Verify new token stored
        6. Verify connection still works
        """

    async def test_health_check_recovery(self):
        """
        Scenario: Integration fails then recovers

        Steps:
        1. Create connected Zoom integration
        2. Mock Zoom API failure
        3. Health check detects failure
        4. Verify status = 'error'
        5. Mock Zoom API recovery
        6. Next health check succeeds
        7. Verify status = 'connected'
        """

    async def test_multi_integration_workspace(self):
        """
        Scenario: Workspace with multiple platforms

        Steps:
        1. Create workspace
        2. Connect Zoom integration
        3. Connect Slack integration
        4. Connect Monday.com integration
        5. Verify all active
        6. Run health checks on all
        7. List all integrations
        8. Disconnect Slack
        9. Verify Zoom and Monday unaffected
        """

    async def test_integration_sync_workflow(self):
        """
        Scenario: Complete data sync from platform

        Steps:
        1. Connect Zoom integration
        2. Trigger full sync
        3. Verify meetings fetched
        4. Verify transcripts fetched
        5. Verify data stored in database
        6. Trigger incremental sync
        7. Verify only new data fetched
        """

    async def test_webhook_event_processing(self):
        """
        Scenario: Platform webhook triggers action

        Steps:
        1. Connect Zoom integration
        2. Mock Zoom webhook (meeting.ended)
        3. Verify webhook signature
        4. Process webhook event
        5. Trigger transcript fetch
        6. Verify event logged
        """

    async def test_error_handling_and_recovery(self):
        """
        Scenario: Various error conditions handled gracefully

        Steps:
        1. Test invalid credentials
        2. Test network timeout
        3. Test rate limit exceeded
        4. Test expired tokens
        5. Verify appropriate errors returned
        6. Verify system remains stable
        """
```

---

## Test Configuration Files

### pytest.ini (Already Updated)
```ini
markers =
    oauth: OAuth flow tests (Sprint 2)
    health: Health monitoring tests (Sprint 2)
    connector: MCP connector tests (Sprint 2)
```

### conftest.py Additions
All necessary fixtures added including:
- OAuth fixtures
- Health check fixtures
- Connector fixtures
- Integration service fixtures

---

## Coverage Goals by Module

| Module | Target Coverage | Priority |
|--------|----------------|----------|
| OAuth Service | 95% | Critical |
| Health Check Service | 90% | Critical |
| Base Connector | 95% | Critical |
| Platform Connectors | 85% | High |
| Integration API | 90% | Critical |
| Token Management | 95% | Critical |

---

## Running the Tests

### Run All Sprint 2 Tests
```bash
pytest tests/ -m "oauth or health or connector or mcp"
```

### Run by Issue
```bash
# Issue #4: Integration Handler
pytest tests/integration/test_api_integrations.py -v

# Issue #5: OAuth
pytest tests/unit/test_oauth_service.py -v
pytest tests/integration/test_oauth_flows.py -v

# Issue #6: Health Monitoring
pytest tests/unit/test_health_check_service.py -v
pytest tests/integration/test_health_monitoring.py -v

# All Connectors
pytest tests/unit/connectors/ -v

# End-to-End
pytest tests/e2e/test_mcp_integration_flow.py -v --slow
```

### Coverage Report
```bash
pytest tests/ \
  -m "oauth or health or connector" \
  --cov=backend/app/services/oauth_service.py \
  --cov=backend/app/services/health_check_service.py \
  --cov=backend/app/connectors/ \
  --cov-report=html \
  --cov-report=term-missing \
  --cov-fail-under=80
```

---

## Acceptance Criteria Verification

### Feature 2.1: MCP Integration Handler ✅
- [x] `/integrations/connect` and `/integrations/disconnect` endpoints tested
- [x] Supports all platforms (Zoom, Loom, Fireflies, Otter, Slack, Discord, Outlook, Monday, Notion, Granola)
- [x] Connection status reflected in `core.integrations`
- [x] Invalid credentials return status `error`

### Feature 2.2: MCP Authentication via OAuth ⏳ (70% Complete)
- [x] OAuth flow unit tests complete
- [ ] OAuth integration tests needed
- [x] Token encryption tested
- [x] Token refresh handling tested
- [ ] Expired token auto-refresh integration test needed

### Feature 2.3: MCP Health Monitor ⏳ (50% Complete)
- [ ] Cron job/async agent tests needed
- [ ] Integration with `ops.events` logging needed
- [ ] Dashboard view tests needed

---

## Next Steps

1. **Create OAuth Integration Tests** (test_oauth_flows.py)
   - Complete OAuth flow simulation
   - State validation
   - CSRF protection
   - Multi-workspace isolation

2. **Create Health Check Tests** (test_health_check_service.py, test_health_monitoring.py)
   - Unit tests for health check logic
   - Integration tests for scheduled checks
   - Alert system tests

3. **Create Connector Tests** (All platform connectors)
   - Base connector tests
   - Platform-specific tests for each connector
   - Error handling and rate limiting

4. **Create E2E Tests** (test_mcp_integration_flow.py)
   - Complete workflows
   - Error scenarios
   - Recovery testing

5. **Documentation Updates**
   - Update tests/README.md with Sprint 2 section
   - Add connector testing guide
   - Add OAuth testing guide

---

## Success Criteria

- [ ] 80%+ test coverage maintained across all MCP code
- [ ] All OAuth flows tested with mocks
- [ ] Health check system fully tested
- [ ] All connector types have unit tests
- [ ] End-to-end integration flows tested
- [ ] Token expiration and refresh tested
- [ ] Error scenarios covered
- [ ] Workspace isolation verified
- [ ] All tests passing in CI/CD
- [ ] Documentation complete

---

## Files Created So Far

1. ✅ tests/fixtures/mcp_responses.py
2. ✅ tests/fixtures/integration_fixtures.py
3. ✅ tests/conftest.py (updated)
4. ✅ pytest.ini (updated)
5. ✅ tests/integration/test_api_integrations.py
6. ✅ tests/unit/test_oauth_service.py
7. ✅ tests/SPRINT2_TEST_PLAN.md (this file)

---

## Files Remaining to Create

1. ⏳ tests/integration/test_oauth_flows.py
2. ⏳ tests/unit/test_health_check_service.py
3. ⏳ tests/integration/test_health_monitoring.py
4. ⏳ tests/unit/connectors/test_base_connector.py
5. ⏳ tests/unit/connectors/test_zoom_connector.py
6. ⏳ tests/unit/connectors/test_slack_connector.py
7. ⏳ tests/unit/connectors/test_discord_connector.py
8. ⏳ tests/unit/connectors/test_outlook_connector.py
9. ⏳ tests/unit/connectors/test_monday_connector.py
10. ⏳ tests/e2e/test_mcp_integration_flow.py

---

**Generated:** 2025-10-30
**Sprint:** Sprint 2 - MCP Integration Framework
**Engineer:** AI Test Engineer
**Status:** 60% Complete
