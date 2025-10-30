"""
Tests for MCP Connectors
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch

from app.connectors.base_connector import BaseConnector, ConnectorResponse, ConnectorStatus, ConnectorError
from app.connectors.zoom_connector import ZoomConnector
from app.connectors.slack_connector import SlackConnector
from app.connectors.connector_registry import get_connector, is_platform_supported, list_supported_platforms


class TestBaseConnector:
    """Test base connector functionality"""

    @pytest.mark.asyncio
    async def test_base_connector_headers(self):
        """Test default header generation"""
        credentials = {"access_token": "test_token"}
        connector = ZoomConnector(credentials)

        headers = connector._get_default_headers()

        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer test_token"
        assert headers["Accept"] == "application/json"

    @pytest.mark.asyncio
    async def test_connector_context_manager(self):
        """Test connector context manager"""
        credentials = {"access_token": "test_token"}

        async with ZoomConnector(credentials) as connector:
            assert connector is not None
            assert connector._http_client is not None

        # After context exit, client should be closed
        assert connector._http_client is None


class TestConnectorRegistry:
    """Test connector registry"""

    def test_list_supported_platforms(self):
        """Test listing supported platforms"""
        platforms = list_supported_platforms()

        assert "zoom" in platforms
        assert "slack" in platforms
        assert "discord" in platforms
        assert len(platforms) == 13  # All 13 platforms

    def test_is_platform_supported(self):
        """Test platform support check"""
        assert is_platform_supported("zoom") is True
        assert is_platform_supported("slack") is True
        assert is_platform_supported("invalid_platform") is False

    def test_get_connector(self):
        """Test getting connector instance"""
        credentials = {"access_token": "test_token"}

        connector = get_connector("zoom", credentials)

        assert isinstance(connector, ZoomConnector)
        assert connector.platform_name == "zoom"

    def test_get_connector_invalid_platform(self):
        """Test getting connector for invalid platform"""
        credentials = {"access_token": "test_token"}

        with pytest.raises(ValueError, match="Unsupported platform"):
            get_connector("invalid_platform", credentials)


class TestZoomConnector:
    """Test Zoom connector"""

    @pytest.mark.asyncio
    async def test_zoom_connection(self):
        """Test Zoom connection test"""
        credentials = {"access_token": "test_token"}
        connector = ZoomConnector(credentials)

        # Mock the HTTP response
        with patch.object(connector, 'make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = ConnectorResponse(
                status=ConnectorStatus.SUCCESS,
                data={"id": "user123", "email": "test@example.com"}
            )

            result = await connector.test_connection()

            assert result.status == ConnectorStatus.SUCCESS
            assert result.data["connected"] is True

    @pytest.mark.asyncio
    async def test_zoom_list_meetings(self):
        """Test listing Zoom meetings"""
        credentials = {"access_token": "test_token"}
        connector = ZoomConnector(credentials)

        with patch.object(connector, 'make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = ConnectorResponse(
                status=ConnectorStatus.SUCCESS,
                data={
                    "meetings": [
                        {"id": "123", "topic": "Test Meeting"}
                    ]
                }
            )

            result = await connector.list_meetings()

            assert result.status == ConnectorStatus.SUCCESS
            assert "meetings" in result.data


class TestSlackConnector:
    """Test Slack connector"""

    @pytest.mark.asyncio
    async def test_slack_connection(self):
        """Test Slack connection test"""
        credentials = {"access_token": "test_token"}
        connector = SlackConnector(credentials)

        with patch.object(connector, 'make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = ConnectorResponse(
                status=ConnectorStatus.SUCCESS,
                data={"ok": True, "user": "test_user"}
            )

            result = await connector.test_connection()

            assert result.status == ConnectorStatus.SUCCESS
            assert result.data["connected"] is True

    @pytest.mark.asyncio
    async def test_slack_send_message(self):
        """Test sending Slack message"""
        credentials = {"access_token": "test_token"}
        connector = SlackConnector(credentials)

        with patch.object(connector, 'make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = ConnectorResponse(
                status=ConnectorStatus.SUCCESS,
                data={"ok": True, "ts": "1234567890.123456"}
            )

            result = await connector.send_message(
                channel_id="C123456",
                text="Test message"
            )

            assert result.status == ConnectorStatus.SUCCESS
            assert result.data["ok"] is True


class TestConnectorErrorHandling:
    """Test connector error handling"""

    @pytest.mark.asyncio
    async def test_connector_error(self):
        """Test ConnectorError exception"""
        error = ConnectorError(
            message="Test error",
            status_code=400,
            details={"key": "value"}
        )

        assert error.message == "Test error"
        assert error.status_code == 400
        assert error.details == {"key": "value"}

    @pytest.mark.asyncio
    async def test_http_error_handling(self):
        """Test HTTP error handling"""
        credentials = {"access_token": "test_token"}
        connector = ZoomConnector(credentials)

        with patch('httpx.AsyncClient.request') as mock_request:
            mock_response = Mock()
            mock_response.status_code = 401
            mock_response.text = "Unauthorized"
            mock_response.json.return_value = {"error": "Invalid token"}
            mock_request.return_value = mock_response

            with pytest.raises(ConnectorError, match="API request failed"):
                await connector.make_request("GET", "/test")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
