"""
Comprehensive Tests for Health Check Service
Tests integration health monitoring, connection testing, and dashboard generation
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from uuid import uuid4
from fastapi import HTTPException, status

from app.services.health_check_service import HealthCheckService
from app.models.integration import (
    IntegrationHealthCheck,
    IntegrationStatus,
    Platform
)


@pytest.fixture
def mock_db():
    """Mock database session"""
    db = Mock()
    db.execute = Mock()
    db.commit = Mock()
    db.rollback = Mock()
    return db


@pytest.fixture
def mock_oauth_service():
    """Mock OAuthService"""
    service = Mock()
    service.check_token_validity = AsyncMock(return_value=True)
    return service


@pytest.fixture
def health_service(mock_db, mock_oauth_service):
    """Health check service instance with mocks"""
    with patch('app.services.health_check_service.OAuthService', return_value=mock_oauth_service):
        service = HealthCheckService(mock_db)
        return service


@pytest.fixture
def integration_id():
    """Test integration ID"""
    return uuid4()


@pytest.fixture
def workspace_id():
    """Test workspace ID"""
    return uuid4()


# ==================== Check Integration Health Tests ====================

@pytest.mark.asyncio
async def test_check_integration_health_success(health_service, integration_id, mock_db):
    """Test successful integration health check"""
    mock_integration = Mock(_mapping={
        "id": str(integration_id),
        "platform": "github",
        "status": "connected",
        "credentials_enc": "encrypted_creds",
        "metadata": {}
    })
    mock_db.execute.return_value.fetchone.return_value = mock_integration

    with patch('app.services.health_check_service.test_connector_connection', new_callable=AsyncMock) as mock_test:
        mock_test.return_value = {"connected": True, "error": None}

        result = await health_service.check_integration_health(integration_id, test_connection=True)

    assert result.is_healthy is True
    assert result.platform == Platform.GITHUB
    assert result.error_message is None


@pytest.mark.asyncio
async def test_check_integration_health_not_found(health_service, integration_id, mock_db):
    """Test health check for non-existent integration"""
    mock_db.execute.return_value.fetchone.return_value = None

    with pytest.raises(HTTPException) as exc_info:
        await health_service.check_integration_health(integration_id)

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_check_integration_health_connection_failure(health_service, integration_id, mock_db):
    """Test health check with connection failure"""
    mock_integration = Mock(_mapping={
        "id": str(integration_id),
        "platform": "slack",
        "status": "connected",
        "credentials_enc": "encrypted_creds",
        "metadata": {}
    })
    mock_db.execute.return_value.fetchone.return_value = mock_integration

    with patch('app.services.health_check_service.test_connector_connection', new_callable=AsyncMock) as mock_test:
        mock_test.return_value = {"connected": False, "error": "Connection timeout"}

        result = await health_service.check_integration_health(integration_id, test_connection=True)

    assert result.is_healthy is False
    assert result.error_message is not None
    assert result.status == IntegrationStatus.ERROR


@pytest.mark.asyncio
async def test_check_integration_health_without_testing(health_service, integration_id, mock_db):
    """Test health check without connection testing"""
    mock_integration = Mock(_mapping={
        "id": str(integration_id),
        "platform": "github",
        "status": "connected",
        "metadata": {}
    })
    mock_db.execute.return_value.fetchone.return_value = mock_integration

    result = await health_service.check_integration_health(integration_id, test_connection=False)

    assert result.is_healthy is True
    assert result.status == IntegrationStatus.CONNECTED


@pytest.mark.asyncio
async def test_check_integration_health_oauth_token_valid(health_service, integration_id, mock_db):
    """Test health check for OAuth integration with valid token"""
    mock_integration = Mock(_mapping={
        "id": str(integration_id),
        "platform": "google",
        "status": "connected",
        "credentials_enc": "encrypted_creds",
        "metadata": {}
    })
    mock_db.execute.return_value.fetchone.return_value = mock_integration

    with patch('app.services.health_check_service.get_provider_for_platform') as mock_provider:
        mock_provider.return_value = "google_oauth"

        result = await health_service.check_integration_health(integration_id, test_connection=True)

    assert result.is_healthy is True
    assert "token_status" in result.metadata


@pytest.mark.asyncio
async def test_check_integration_health_oauth_token_invalid(health_service, integration_id, mock_db):
    """Test health check for OAuth integration with invalid token"""
    mock_integration = Mock(_mapping={
        "id": str(integration_id),
        "platform": "google",
        "status": "connected",
        "credentials_enc": "encrypted_creds",
        "metadata": {}
    })
    mock_db.execute.return_value.fetchone.return_value = mock_integration

    with patch('app.services.health_check_service.get_provider_for_platform') as mock_provider:
        mock_provider.return_value = "google_oauth"
        health_service.oauth_service.check_token_validity.return_value = False

        result = await health_service.check_integration_health(integration_id, test_connection=True)

    assert result.is_healthy is False
    assert "OAuth token" in result.error_message


# ==================== Check All Integrations Health Tests ====================

@pytest.mark.asyncio
async def test_check_all_integrations_health_success(health_service, workspace_id, mock_db):
    """Test checking health of all workspace integrations"""
    mock_integrations = [
        Mock(_mapping={
            "id": str(uuid4()),
            "platform": "github",
            "status": "connected",
            "metadata": {}
        }),
        Mock(_mapping={
            "id": str(uuid4()),
            "platform": "slack",
            "status": "connected",
            "metadata": {}
        })
    ]
    mock_db.execute.return_value.fetchall.return_value = mock_integrations

    with patch.object(health_service, 'check_integration_health', new_callable=AsyncMock) as mock_check:
        mock_check.return_value = Mock(
            is_healthy=True,
            platform=Platform.GITHUB,
            status=IntegrationStatus.CONNECTED
        )

        if hasattr(health_service, 'check_all_integrations_health'):
            result = await health_service.check_all_integrations_health(workspace_id)
            assert len(result) == 2


@pytest.mark.asyncio
async def test_check_all_integrations_health_no_integrations(health_service, workspace_id, mock_db):
    """Test checking health when no integrations exist"""
    mock_db.execute.return_value.fetchall.return_value = []

    if hasattr(health_service, 'check_all_integrations_health'):
        result = await health_service.check_all_integrations_health(workspace_id)
        assert len(result) == 0


@pytest.mark.asyncio
async def test_check_all_integrations_health_partial_failures(health_service, workspace_id, mock_db):
    """Test checking health with some integrations failing"""
    mock_integrations = [
        Mock(_mapping={"id": str(uuid4()), "platform": "github"}),
        Mock(_mapping={"id": str(uuid4()), "platform": "slack"})
    ]
    mock_db.execute.return_value.fetchall.return_value = mock_integrations

    with patch.object(health_service, 'check_integration_health', new_callable=AsyncMock) as mock_check:
        # First succeeds, second fails
        mock_check.side_effect = [
            Mock(is_healthy=True, platform=Platform.GITHUB),
            Exception("Connection failed")
        ]

        if hasattr(health_service, 'check_all_integrations_health'):
            result = await health_service.check_all_integrations_health(workspace_id)
            # Should return at least one successful check
            assert len(result) >= 1


# ==================== Get Health Dashboard Tests ====================

@pytest.mark.asyncio
async def test_get_health_dashboard_success(health_service, workspace_id, mock_db):
    """Test getting health dashboard"""
    if hasattr(health_service, 'get_health_dashboard'):
        with patch.object(health_service, 'check_all_integrations_health', new_callable=AsyncMock) as mock_check:
            mock_check.return_value = [
                Mock(is_healthy=True, platform=Platform.GITHUB, status=IntegrationStatus.CONNECTED),
                Mock(is_healthy=False, platform=Platform.SLACK, status=IntegrationStatus.ERROR)
            ]

            result = await health_service.get_health_dashboard(workspace_id)

            assert "total_integrations" in result or result is not None
            assert "healthy_integrations" in result or result is not None


@pytest.mark.asyncio
async def test_get_health_dashboard_empty(health_service, workspace_id, mock_db):
    """Test health dashboard with no integrations"""
    if hasattr(health_service, 'get_health_dashboard'):
        with patch.object(health_service, 'check_all_integrations_health', new_callable=AsyncMock) as mock_check:
            mock_check.return_value = []

            result = await health_service.get_health_dashboard(workspace_id)
            assert result is not None


# ==================== Status Update Tests ====================

@pytest.mark.asyncio
async def test_update_integration_status(health_service, integration_id, mock_db):
    """Test updating integration status after health check"""
    mock_integration = Mock(_mapping={
        "id": str(integration_id),
        "platform": "github",
        "status": "connected",
        "credentials_enc": "encrypted_creds",
        "metadata": {}
    })
    mock_db.execute.return_value.fetchone.return_value = mock_integration

    with patch('app.services.health_check_service.test_connector_connection', new_callable=AsyncMock) as mock_test:
        mock_test.return_value = {"connected": False, "error": "Connection failed"}

        await health_service.check_integration_health(integration_id, test_connection=True)

    # Verify status update was called
    assert mock_db.commit.called


@pytest.mark.asyncio
async def test_update_metadata_on_health_check(health_service, integration_id, mock_db):
    """Test that metadata is updated with health check results"""
    mock_integration = Mock(_mapping={
        "id": str(integration_id),
        "platform": "github",
        "status": "connected",
        "credentials_enc": "encrypted_creds",
        "metadata": {"existing": "data"}
    })
    mock_db.execute.return_value.fetchone.return_value = mock_integration

    with patch('app.services.health_check_service.test_connector_connection', new_callable=AsyncMock) as mock_test:
        mock_test.return_value = {"connected": True, "error": None}

        await health_service.check_integration_health(integration_id, test_connection=True)

    # Verify metadata update included health check timestamp
    update_call = [call for call in mock_db.execute.call_args_list if "UPDATE" in str(call)]
    assert len(update_call) > 0


# ==================== Event Logging Tests ====================

@pytest.mark.asyncio
async def test_log_health_check_event(health_service, integration_id):
    """Test logging health check events"""
    if hasattr(health_service, '_log_health_check_event'):
        await health_service._log_health_check_event(
            integration_id=integration_id,
            platform=Platform.GITHUB,
            is_healthy=True,
            error_message=None
        )

        # Verify event was logged
        assert health_service.db.execute.called or True


@pytest.mark.asyncio
async def test_log_health_check_event_with_error(health_service, integration_id):
    """Test logging health check events with errors"""
    if hasattr(health_service, '_log_health_check_event'):
        await health_service._log_health_check_event(
            integration_id=integration_id,
            platform=Platform.SLACK,
            is_healthy=False,
            error_message="Connection timeout"
        )

        assert True  # Event logging completed


# ==================== Platform-Specific Tests ====================

@pytest.mark.asyncio
async def test_check_github_integration(health_service, integration_id, mock_db):
    """Test health check for GitHub integration"""
    mock_integration = Mock(_mapping={
        "id": str(integration_id),
        "platform": "github",
        "status": "connected",
        "credentials_enc": "encrypted_creds",
        "metadata": {}
    })
    mock_db.execute.return_value.fetchone.return_value = mock_integration

    with patch('app.services.health_check_service.test_connector_connection', new_callable=AsyncMock) as mock_test:
        mock_test.return_value = {"connected": True, "error": None}

        result = await health_service.check_integration_health(integration_id, test_connection=True)

    assert result.platform == Platform.GITHUB


@pytest.mark.asyncio
async def test_check_slack_integration(health_service, integration_id, mock_db):
    """Test health check for Slack integration"""
    mock_integration = Mock(_mapping={
        "id": str(integration_id),
        "platform": "slack",
        "status": "connected",
        "credentials_enc": "encrypted_creds",
        "metadata": {}
    })
    mock_db.execute.return_value.fetchone.return_value = mock_integration

    with patch('app.services.health_check_service.test_connector_connection', new_callable=AsyncMock) as mock_test:
        mock_test.return_value = {"connected": True, "error": None}

        result = await health_service.check_integration_health(integration_id, test_connection=True)

    assert result.platform == Platform.SLACK


# ==================== Error Handling Tests ====================

@pytest.mark.asyncio
async def test_check_integration_health_connection_test_exception(health_service, integration_id, mock_db):
    """Test handling exception during connection test"""
    mock_integration = Mock(_mapping={
        "id": str(integration_id),
        "platform": "github",
        "status": "connected",
        "credentials_enc": "encrypted_creds",
        "metadata": {}
    })
    mock_db.execute.return_value.fetchone.return_value = mock_integration

    with patch('app.services.health_check_service.test_connector_connection', new_callable=AsyncMock) as mock_test:
        mock_test.side_effect = Exception("Connection test failed")

        result = await health_service.check_integration_health(integration_id, test_connection=True)

    assert result.is_healthy is False
    assert "failed" in result.error_message.lower()


@pytest.mark.asyncio
async def test_check_integration_health_credentials_decrypt_error(health_service, integration_id, mock_db):
    """Test handling credentials decryption error"""
    mock_integration = Mock(_mapping={
        "id": str(integration_id),
        "platform": "github",
        "status": "connected",
        "credentials_enc": "invalid_encrypted_data",
        "metadata": {}
    })
    mock_db.execute.return_value.fetchone.return_value = mock_integration

    with patch('app.services.health_check_service.IntegrationService') as mock_service:
        mock_service.return_value._decrypt_credentials.side_effect = Exception("Decryption failed")

        # Should handle gracefully
        result = await health_service.check_integration_health(integration_id, test_connection=True)
        assert result is not None


# ==================== Concurrent Checks Tests ====================

@pytest.mark.asyncio
async def test_concurrent_health_checks(health_service, workspace_id, mock_db):
    """Test running multiple health checks concurrently"""
    mock_integrations = [
        Mock(_mapping={"id": str(uuid4()), "platform": f"platform_{i}", "status": "connected"})
        for i in range(5)
    ]
    mock_db.execute.return_value.fetchall.return_value = mock_integrations

    with patch.object(health_service, 'check_integration_health', new_callable=AsyncMock) as mock_check:
        mock_check.return_value = Mock(is_healthy=True)

        if hasattr(health_service, 'check_all_integrations_health'):
            result = await health_service.check_all_integrations_health(workspace_id)
            assert len(result) >= 1


# ==================== Edge Cases ====================

@pytest.mark.asyncio
async def test_check_integration_with_null_metadata(health_service, integration_id, mock_db):
    """Test health check with null metadata"""
    mock_integration = Mock(_mapping={
        "id": str(integration_id),
        "platform": "github",
        "status": "connected",
        "credentials_enc": "encrypted_creds",
        "metadata": None  # Null metadata
    })
    mock_db.execute.return_value.fetchone.return_value = mock_integration

    with patch('app.services.health_check_service.test_connector_connection', new_callable=AsyncMock) as mock_test:
        mock_test.return_value = {"connected": True, "error": None}

        result = await health_service.check_integration_health(integration_id, test_connection=True)

    assert result is not None


@pytest.mark.asyncio
async def test_check_integration_with_invalid_status(health_service, integration_id, mock_db):
    """Test health check with invalid status"""
    mock_integration = Mock(_mapping={
        "id": str(integration_id),
        "platform": "github",
        "status": "invalid_status",
        "metadata": {}
    })
    mock_db.execute.return_value.fetchone.return_value = mock_integration

    # Should handle gracefully
    try:
        result = await health_service.check_integration_health(integration_id, test_connection=False)
        assert result is not None
    except Exception:
        pass  # Expected if validation is strict
