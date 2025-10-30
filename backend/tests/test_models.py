"""
Tests for Pydantic models
"""
import pytest
from uuid import uuid4
from datetime import datetime
from app.models.workspace import WorkspaceCreate, WorkspaceResponse
from app.models.integration import (
    IntegrationConnectRequest,
    Platform,
    ConnectionType
)


def test_workspace_create_model():
    """Test WorkspaceCreate model validation"""
    workspace = WorkspaceCreate(name="Test Workspace")
    assert workspace.name == "Test Workspace"


def test_workspace_create_validation():
    """Test WorkspaceCreate validates name"""
    with pytest.raises(ValueError):
        WorkspaceCreate(name="")  # Empty name should fail


def test_workspace_response_model():
    """Test WorkspaceResponse model"""
    workspace = WorkspaceResponse(
        id=uuid4(),
        name="Test Workspace",
        created_at=datetime.utcnow()
    )
    assert workspace.name == "Test Workspace"
    assert isinstance(workspace.id, type(uuid4()))


def test_integration_connect_request():
    """Test IntegrationConnectRequest model"""
    request = IntegrationConnectRequest(
        platform=Platform.SLACK,
        connection_type=ConnectionType.MCP,
        credentials={"access_token": "test", "team_id": "T123"},
        metadata={"display_name": "My Slack"}
    )
    assert request.platform == Platform.SLACK
    assert request.connection_type == ConnectionType.MCP
    assert request.credentials["access_token"] == "test"


def test_integration_platform_enum():
    """Test Platform enum values"""
    assert Platform.ZOOM.value == "zoom"
    assert Platform.SLACK.value == "slack"
    assert Platform.NOTION.value == "notion"


def test_integration_credentials_validation():
    """Test credential validation for specific platforms"""
    # Valid Slack credentials
    request = IntegrationConnectRequest(
        platform=Platform.SLACK,
        connection_type=ConnectionType.MCP,
        credentials={"access_token": "xoxb-123", "team_id": "T123"}
    )
    assert request.credentials["access_token"] == "xoxb-123"

    # Missing required fields should raise validation error
    with pytest.raises(ValueError):
        IntegrationConnectRequest(
            platform=Platform.ZOOM,
            connection_type=ConnectionType.MCP,
            credentials={"client_id": "test"}  # Missing client_secret
        )
