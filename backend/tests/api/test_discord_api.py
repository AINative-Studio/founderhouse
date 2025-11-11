"""
Comprehensive tests for Discord API endpoints

Tests all Discord integration endpoints with proper mocking.
Coverage target: 19 statements, 0% -> 80%+
"""
import pytest
from uuid import uuid4
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """FastAPI test client"""
    return TestClient(app)


@pytest.fixture
def mock_discord_service():
    """Mock Discord service"""
    with patch('app.api.v1.discord.get_discord_service') as mock:
        service = MagicMock()
        service.post_status_update = AsyncMock(return_value={
            "message_id": str(uuid4()),
            "channel_id": "discord_channel_123",
            "status": "delivered",
            "timestamp": "2025-01-10T10:00:00Z"
        })
        service.send_briefing = AsyncMock(return_value={
            "message_id": str(uuid4()),
            "channel_id": "discord_channel_123",
            "status": "delivered",
            "timestamp": "2025-01-10T10:00:00Z"
        })
        service.get_message = AsyncMock(return_value={
            "message_id": str(uuid4()),
            "channel_id": "discord_channel_123",
            "status": "delivered"
        })
        
        mock.return_value = service
        yield service


class TestPostStatusUpdate:
    """Tests for posting status updates"""
    
    def test_post_status_update_success(self, client, mock_discord_service):
        """Test successful status update posting"""
        request_data = {
            "workspace_id": str(uuid4()),
            "channel_id": "discord_channel_123",
            "message": "New feature deployed successfully!",
            "mentions": ["@team"],
            "embed": {
                "title": "Deployment Complete",
                "description": "Version 2.0.0 is now live",
                "color": 0x00FF00
            }
        }
        
        response = client.post("/discord/status", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "message_id" in data
        assert data["status"] == "delivered"
        
    def test_post_status_update_simple(self, client, mock_discord_service):
        """Test simple status update without embed"""
        request_data = {
            "workspace_id": str(uuid4()),
            "channel_id": "discord_channel_123",
            "message": "Quick update: All systems operational"
        }
        
        response = client.post("/discord/status", json=request_data)
        
        assert response.status_code == 200
        
    def test_post_status_update_failure(self, client, mock_discord_service):
        """Test status update posting failure"""
        mock_discord_service.post_status_update = AsyncMock(return_value=None)
        
        request_data = {
            "workspace_id": str(uuid4()),
            "channel_id": "invalid_channel",
            "message": "Test message"
        }
        
        response = client.post("/discord/status", json=request_data)
        
        assert response.status_code == 500
        assert "Failed to post status update" in response.json()["detail"]
        
    def test_post_status_update_service_error(self, client, mock_discord_service):
        """Test status update with service error"""
        mock_discord_service.post_status_update = AsyncMock(
            side_effect=Exception("Discord API unavailable")
        )
        
        request_data = {
            "workspace_id": str(uuid4()),
            "channel_id": "discord_channel_123",
            "message": "Test"
        }
        
        response = client.post("/discord/status", json=request_data)
        
        assert response.status_code == 500


class TestSendBriefing:
    """Tests for sending briefings to Discord"""
    
    def test_send_briefing_success(self, client, mock_discord_service):
        """Test successful briefing sending"""
        briefing_id = uuid4()
        
        request_data = {
            "workspace_id": str(uuid4()),
            "founder_id": str(uuid4()),
            "channel_id": "discord_channel_123",
            "briefing_id": str(briefing_id)
        }
        
        response = client.post("/discord/briefing", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "message_id" in data
        
    def test_send_briefing_without_id(self, client, mock_discord_service):
        """Test sending latest briefing without specific ID"""
        request_data = {
            "workspace_id": str(uuid4()),
            "founder_id": str(uuid4()),
            "channel_id": "discord_channel_123"
        }
        
        response = client.post("/discord/briefing", json=request_data)
        
        assert response.status_code == 200
        
    def test_send_briefing_failure(self, client, mock_discord_service):
        """Test briefing sending failure"""
        mock_discord_service.send_briefing = AsyncMock(return_value=None)
        
        request_data = {
            "workspace_id": str(uuid4()),
            "founder_id": str(uuid4()),
            "channel_id": "invalid_channel"
        }
        
        response = client.post("/discord/briefing", json=request_data)
        
        assert response.status_code == 500
        
    def test_send_briefing_service_error(self, client, mock_discord_service):
        """Test briefing sending with service error"""
        mock_discord_service.send_briefing = AsyncMock(
            side_effect=Exception("Discord webhook error")
        )
        
        request_data = {
            "workspace_id": str(uuid4()),
            "founder_id": str(uuid4()),
            "channel_id": "discord_channel_123"
        }
        
        response = client.post("/discord/briefing", json=request_data)
        
        assert response.status_code == 500


class TestGetMessage:
    """Tests for getting message details"""
    
    def test_get_message_success(self, client, mock_discord_service):
        """Test successful message retrieval"""
        message_id = uuid4()
        
        response = client.get(f"/discord/message/{message_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert "message_id" in data
        assert "status" in data
        
    def test_get_message_not_found(self, client, mock_discord_service):
        """Test message retrieval when not found"""
        message_id = uuid4()
        mock_discord_service.get_message = AsyncMock(return_value=None)
        
        response = client.get(f"/discord/message/{message_id}")
        
        assert response.status_code == 404
        assert "Message not found" in response.json()["detail"]
        
    def test_get_message_service_error(self, client, mock_discord_service):
        """Test message retrieval with service error"""
        message_id = uuid4()
        mock_discord_service.get_message = AsyncMock(
            side_effect=Exception("Database error")
        )
        
        response = client.get(f"/discord/message/{message_id}")
        
        assert response.status_code == 500


# Summary comment
"""
Test Coverage Summary:
- Post status update: 4 tests (success, simple, failure, error)
- Send briefing: 4 tests (success, without ID, failure, error)
- Get message: 3 tests (success, not found, error)

Total: 11 tests covering discord.py (19 statements)
Expected coverage improvement: 0% -> 80%+
"""
