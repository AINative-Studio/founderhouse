"""
Comprehensive tests for Agents API endpoints

Tests agent routing and collaboration endpoints.
Coverage target: 11 statements, 0% -> 80%+
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
def mock_routing_service():
    """Mock agent routing service"""
    with patch('app.api.v1.agents.get_routing_service') as mock:
        service = MagicMock()
        service.route_task = AsyncMock(return_value={
            "task_id": str(uuid4()),
            "assigned_agent": "data_analysis",
            "status": "queued",
            "priority": "high"
        })
        service.get_task = AsyncMock(return_value={
            "task_id": str(uuid4()),
            "status": "completed",
            "result": {"analysis": "completed"}
        })
        service.list_tasks = AsyncMock(return_value=[])
        service.cancel_task = AsyncMock(return_value=True)
        service.retry_task = AsyncMock(return_value={
            "task_id": str(uuid4()),
            "status": "queued"
        })
        service.get_agent_health = AsyncMock(return_value={
            "agent_type": "data_analysis",
            "status": "healthy",
            "uptime": 99.9
        })
        service.get_agent_metrics = AsyncMock(return_value={
            "agent_type": "data_analysis",
            "success_rate": 0.95,
            "avg_processing_time_ms": 1500
        })
        
        mock.return_value = service
        yield service


@pytest.fixture
def mock_collaboration_service():
    """Mock agent collaboration service"""
    with patch('app.api.v1.agents.get_collaboration_service') as mock:
        service = MagicMock()
        service.initiate_collaboration = AsyncMock(return_value={
            "session_id": str(uuid4()),
            "agents_involved": ["data_analysis", "recommendation"],
            "status": "in_progress"
        })
        service.get_collaboration = AsyncMock(return_value={
            "session_id": str(uuid4()),
            "status": "completed",
            "outputs": {}
        })
        
        mock.return_value = service
        yield service


class TestRouteTask:
    """Tests for task routing"""
    
    def test_route_task_success(self, client, mock_routing_service):
        """Test successful task routing"""
        request_data = {
            "workspace_id": str(uuid4()),
            "founder_id": str(uuid4()),
            "task_type": "data_analysis",
            "description": "Analyze Q4 revenue trends",
            "priority": "high",
            "context": {"quarter": "Q4"}
        }
        
        response = client.post("/agents/route", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "task_id" in data
        assert data["status"] == "queued"
        
    def test_route_task_failure(self, client, mock_routing_service):
        """Test task routing failure"""
        mock_routing_service.route_task = AsyncMock(return_value=None)
        
        request_data = {
            "workspace_id": str(uuid4()),
            "founder_id": str(uuid4()),
            "task_type": "invalid_task",
            "description": "Test task"
        }
        
        response = client.post("/agents/route", json=request_data)
        
        assert response.status_code == 500


class TestInitiateCollaboration:
    """Tests for agent collaboration"""
    
    def test_initiate_collaboration_success(self, client, mock_collaboration_service):
        """Test successful collaboration initiation"""
        request_data = {
            "workspace_id": str(uuid4()),
            "founder_id": str(uuid4()),
            "objective": "Generate comprehensive business insights",
            "agents": ["data_analysis", "recommendation"],
            "context": {"time_range": "30d"}
        }
        
        response = client.post("/agents/collaborate", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        
    def test_initiate_collaboration_failure(self, client, mock_collaboration_service):
        """Test collaboration initiation failure"""
        mock_collaboration_service.initiate_collaboration = AsyncMock(return_value=None)
        
        request_data = {
            "workspace_id": str(uuid4()),
            "founder_id": str(uuid4()),
            "objective": "Test",
            "agents": []
        }
        
        response = client.post("/agents/collaborate", json=request_data)
        
        assert response.status_code == 500


class TestGetTask:
    """Tests for getting task details"""
    
    def test_get_task_success(self, client, mock_routing_service):
        """Test successful task retrieval"""
        task_id = uuid4()
        
        response = client.get(f"/agents/tasks/{task_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        
    def test_get_task_not_found(self, client, mock_routing_service):
        """Test task retrieval when not found"""
        task_id = uuid4()
        mock_routing_service.get_task = AsyncMock(return_value=None)
        
        response = client.get(f"/agents/tasks/{task_id}")
        
        assert response.status_code == 404


class TestListTasks:
    """Tests for listing tasks"""
    
    def test_list_tasks_success(self, client, mock_routing_service):
        """Test successful task listing"""
        workspace_id = uuid4()
        
        tasks = [
            {"task_id": str(uuid4()), "status": "completed"},
            {"task_id": str(uuid4()), "status": "queued"}
        ]
        mock_routing_service.list_tasks = AsyncMock(return_value=tasks)
        
        response = client.get(
            "/agents/tasks",
            params={"workspace_id": str(workspace_id)}
        )
        
        assert response.status_code == 200
        assert len(response.json()) == 2


class TestCancelTask:
    """Tests for cancelling tasks"""
    
    def test_cancel_task_success(self, client, mock_routing_service):
        """Test successful task cancellation"""
        task_id = uuid4()
        
        response = client.post(f"/agents/tasks/{task_id}/cancel")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cancelled"
        
    def test_cancel_task_failure(self, client, mock_routing_service):
        """Test task cancellation failure"""
        task_id = uuid4()
        mock_routing_service.cancel_task = AsyncMock(return_value=False)
        
        response = client.post(f"/agents/tasks/{task_id}/cancel")
        
        assert response.status_code == 400


class TestRetryTask:
    """Tests for retrying tasks"""
    
    def test_retry_task_success(self, client, mock_routing_service):
        """Test successful task retry"""
        task_id = uuid4()
        
        response = client.post(f"/agents/tasks/{task_id}/retry")
        
        assert response.status_code == 200
        data = response.json()
        assert "task_id" in data
        
    def test_retry_task_failure(self, client, mock_routing_service):
        """Test task retry failure"""
        task_id = uuid4()
        mock_routing_service.retry_task = AsyncMock(return_value=None)
        
        response = client.post(f"/agents/tasks/{task_id}/retry")
        
        assert response.status_code == 400


class TestGetCollaboration:
    """Tests for getting collaboration details"""
    
    def test_get_collaboration_success(self, client, mock_collaboration_service):
        """Test successful collaboration retrieval"""
        session_id = uuid4()
        
        response = client.get(f"/agents/collaboration/{session_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        
    def test_get_collaboration_not_found(self, client, mock_collaboration_service):
        """Test collaboration retrieval when not found"""
        session_id = uuid4()
        mock_collaboration_service.get_collaboration = AsyncMock(return_value=None)
        
        response = client.get(f"/agents/collaboration/{session_id}")
        
        assert response.status_code == 404


class TestAgentHealth:
    """Tests for agent health status"""
    
    def test_get_agent_health_success(self, client, mock_routing_service):
        """Test successful health status retrieval"""
        response = client.get("/agents/health/data_analysis")
        
        assert response.status_code == 200
        data = response.json()
        assert data["agent_type"] == "data_analysis"
        assert data["status"] == "healthy"


class TestAgentMetrics:
    """Tests for agent performance metrics"""
    
    def test_get_agent_metrics_success(self, client, mock_routing_service):
        """Test successful metrics retrieval"""
        response = client.get("/agents/metrics/data_analysis")
        
        assert response.status_code == 200
        data = response.json()
        assert "success_rate" in data
        assert "avg_processing_time_ms" in data


# Summary comment
"""
Test Coverage Summary:
- Route task: 2 tests
- Initiate collaboration: 2 tests
- Get task: 2 tests
- List tasks: 1 test
- Cancel task: 2 tests
- Retry task: 2 tests
- Get collaboration: 2 tests
- Agent health: 1 test
- Agent metrics: 1 test

Total: 15 tests covering agents.py (11 statements)
Expected coverage improvement: 0% -> 80%+
"""
