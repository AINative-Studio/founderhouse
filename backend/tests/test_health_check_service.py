"""
Tests for Health Check Service
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from uuid import uuid4
from datetime import datetime

from app.services.health_check_service import HealthCheckService
from app.models.integration import IntegrationStatus, Platform


@pytest.fixture
def mock_db():
    """Mock Supabase database client"""
    return Mock()


@pytest.fixture
def health_service(mock_db):
    """Create health check service instance"""
    return HealthCheckService(mock_db)


class TestHealthCheckService:
    """Test health check service functionality"""

    @pytest.mark.asyncio
    async def test_check_integration_health_success(self, health_service, mock_db):
        """Test successful integration health check"""
        integration_id = uuid4()

        # Mock database response
        mock_table = Mock()
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.execute.return_value = Mock(data=[{
            "id": str(integration_id),
            "platform": "zoom",
            "status": "connected",
            "credentials_enc": None,
            "metadata": {}
        }])
        mock_table.update.return_value = mock_table
        mock_table.insert.return_value = mock_table

        mock_db.table.return_value = mock_table

        # Mock connector test
        with patch('app.connectors.connector_registry.test_connector_connection', new_callable=AsyncMock) as mock_test:
            mock_test.return_value = {
                "platform": "zoom",
                "status": "success",
                "connected": True,
                "error": None
            }

            result = await health_service.check_integration_health(integration_id, test_connection=True)

            assert result.integration_id == integration_id
            assert result.platform == Platform.ZOOM
            assert result.is_healthy is True
            assert result.error_message is None

    @pytest.mark.asyncio
    async def test_check_integration_health_failure(self, health_service, mock_db):
        """Test failed integration health check"""
        integration_id = uuid4()

        # Mock database response
        mock_table = Mock()
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.execute.return_value = Mock(data=[{
            "id": str(integration_id),
            "platform": "zoom",
            "status": "error",
            "credentials_enc": None,
            "metadata": {}
        }])
        mock_table.update.return_value = mock_table
        mock_table.insert.return_value = mock_table

        mock_db.table.return_value = mock_table

        # Mock connector test failure
        with patch('app.connectors.connector_registry.test_connector_connection', new_callable=AsyncMock) as mock_test:
            mock_test.return_value = {
                "platform": "zoom",
                "status": "error",
                "connected": False,
                "error": "Connection timeout"
            }

            result = await health_service.check_integration_health(integration_id, test_connection=True)

            assert result.integration_id == integration_id
            assert result.is_healthy is False
            assert result.error_message is not None

    @pytest.mark.asyncio
    async def test_check_all_integrations_health(self, health_service, mock_db):
        """Test checking health of all integrations"""
        workspace_id = uuid4()
        integration_id_1 = uuid4()
        integration_id_2 = uuid4()

        # Mock database response
        mock_table = Mock()
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table

        # First call returns list of integrations
        mock_table.execute.side_effect = [
            Mock(data=[
                {"id": str(integration_id_1)},
                {"id": str(integration_id_2)}
            ]),
            Mock(data=[{
                "id": str(integration_id_1),
                "platform": "zoom",
                "status": "connected",
                "credentials_enc": None,
                "metadata": {}
            }]),
            Mock(data=[{
                "id": str(integration_id_2),
                "platform": "slack",
                "status": "connected",
                "credentials_enc": None,
                "metadata": {}
            }])
        ]

        mock_table.update.return_value = mock_table
        mock_table.insert.return_value = mock_table
        mock_db.table.return_value = mock_table

        # Mock connector tests
        with patch('app.connectors.connector_registry.test_connector_connection', new_callable=AsyncMock) as mock_test:
            mock_test.return_value = {
                "status": "success",
                "connected": True,
                "error": None
            }

            results = await health_service.check_all_integrations_health(workspace_id)

            assert len(results) == 2

    @pytest.mark.asyncio
    async def test_get_health_dashboard(self, health_service):
        """Test getting health dashboard"""
        workspace_id = uuid4()

        # Mock check_all_integrations_health
        with patch.object(health_service, 'check_all_integrations_health', new_callable=AsyncMock) as mock_check:
            from app.models.integration import IntegrationHealthCheck

            mock_check.return_value = [
                IntegrationHealthCheck(
                    integration_id=uuid4(),
                    platform=Platform.ZOOM,
                    status=IntegrationStatus.CONNECTED,
                    is_healthy=True,
                    last_checked=datetime.utcnow(),
                    metadata={}
                ),
                IntegrationHealthCheck(
                    integration_id=uuid4(),
                    platform=Platform.SLACK,
                    status=IntegrationStatus.ERROR,
                    is_healthy=False,
                    last_checked=datetime.utcnow(),
                    error_message="Connection failed",
                    metadata={}
                )
            ]

            dashboard = await health_service.get_health_dashboard(workspace_id)

            assert dashboard["summary"]["total_integrations"] == 2
            assert dashboard["summary"]["healthy"] == 1
            assert dashboard["summary"]["unhealthy"] == 1
            assert dashboard["summary"]["success_rate"] == 50.0
            assert "zoom" in dashboard["platform_health"]
            assert "slack" in dashboard["platform_health"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
