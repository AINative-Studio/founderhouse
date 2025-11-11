"""
Comprehensive tests for Agent Routing Service
Tests task routing, agent selection, health monitoring, and metrics
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from uuid import uuid4, UUID

from app.services.agent_routing_service import AgentRoutingService
from app.models.agent_routing import (
    AgentRouteRequest,
    AgentTaskResponse,
    AgentType,
    AgentTaskStatus,
    AgentTaskPriority,
    AgentHealthStatus,
    AgentMetrics
)


class TestAgentRoutingService:
    """Test suite for AgentRoutingService"""

    @pytest.fixture
    def service(self):
        """Create agent routing service"""
        return AgentRoutingService()

    @pytest.fixture
    def workspace_id(self):
        """Sample workspace ID"""
        return uuid4()

    @pytest.fixture
    def founder_id(self):
        """Sample founder ID"""
        return uuid4()

    @pytest.fixture
    def sample_route_request(self, workspace_id, founder_id):
        """Sample route request"""
        return AgentRouteRequest(
            workspace_id=workspace_id,
            founder_id=founder_id,
            task_type="meeting_analysis",
            task_description="Analyze meeting transcript",
            priority=AgentTaskPriority.MEDIUM,
            input_data={"transcript": "Meeting content here"}
        )

    @pytest.fixture
    def mock_db_row(self, workspace_id, founder_id):
        """Mock database row"""
        row = MagicMock()
        row.id = uuid4()
        row.workspace_id = str(workspace_id)
        row.founder_id = str(founder_id)
        row.task_type = "meeting_analysis"
        row.task_description = "Test task"
        row.priority = "medium"
        row.status = "queued"
        row.assigned_agent = "meeting_analyst"
        row.input_data = {"test": "data"}
        row.output_data = None
        row.context = {}
        row.error_message = None
        row.retry_count = 0
        row.max_retries = 3
        row.dependencies = []
        row.processing_time_ms = None
        row.created_at = datetime.utcnow()
        row.updated_at = datetime.utcnow()
        row.started_at = None
        row.completed_at = None
        row.deadline = None
        return row

    # ==================== TASK ROUTING ====================

    @pytest.mark.asyncio
    async def test_route_task_success(self, service, sample_route_request, mock_db_row):
        """Test successful task routing"""
        with patch('app.services.agent_routing_service.get_db_context') as mock_db:
            mock_context = AsyncMock()
            mock_result = MagicMock()
            mock_result.fetchone.return_value = mock_db_row
            mock_context.execute = AsyncMock(return_value=mock_result)
            mock_context.commit = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_context

            task = await service.route_task(sample_route_request)

            assert task is not None
            assert task.task_type == "meeting_analysis"
            assert task.status == AgentTaskStatus.QUEUED
            assert task.assigned_agent == AgentType.MEETING_ANALYST
            mock_context.execute.assert_called()
            mock_context.commit.assert_called()

    @pytest.mark.asyncio
    async def test_route_task_with_preferred_agent(self, service, sample_route_request, mock_db_row):
        """Test routing with preferred agent"""
        sample_route_request.preferred_agent = AgentType.TASK_MANAGER

        with patch('app.services.agent_routing_service.get_db_context') as mock_db:
            mock_context = AsyncMock()
            mock_result = MagicMock()
            mock_db_row.assigned_agent = "task_manager"
            mock_result.fetchone.return_value = mock_db_row
            mock_context.execute = AsyncMock(return_value=mock_result)
            mock_context.commit = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_context

            task = await service.route_task(sample_route_request)

            assert task.assigned_agent == AgentType.TASK_MANAGER

    @pytest.mark.asyncio
    async def test_route_urgent_task(self, service, sample_route_request, mock_db_row):
        """Test routing urgent task executes immediately"""
        sample_route_request.priority = AgentTaskPriority.URGENT

        with patch('app.services.agent_routing_service.get_db_context') as mock_db:
            mock_context = AsyncMock()
            mock_result = MagicMock()
            mock_result.fetchone.return_value = mock_db_row
            mock_context.execute = AsyncMock(return_value=mock_result)
            mock_context.commit = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_context

            with patch.object(service, '_execute_task') as mock_execute:
                task = await service.route_task(sample_route_request)

                # Should call execute for urgent tasks without dependencies
                mock_execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_route_task_with_dependencies(self, service, sample_route_request, mock_db_row):
        """Test routing task with dependencies doesn't execute immediately"""
        sample_route_request.priority = AgentTaskPriority.URGENT
        sample_route_request.dependencies = [uuid4()]

        with patch('app.services.agent_routing_service.get_db_context') as mock_db:
            mock_context = AsyncMock()
            mock_result = MagicMock()
            mock_result.fetchone.return_value = mock_db_row
            mock_context.execute = AsyncMock(return_value=mock_result)
            mock_context.commit = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_context

            with patch.object(service, '_execute_task') as mock_execute:
                task = await service.route_task(sample_route_request)

                # Should NOT execute when dependencies exist
                mock_execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_route_task_error(self, service, sample_route_request):
        """Test task routing error handling"""
        with patch('app.services.agent_routing_service.get_db_context') as mock_db:
            mock_db.side_effect = Exception("Database error")

            task = await service.route_task(sample_route_request)

            assert task is None

    # ==================== AGENT SELECTION ====================

    def test_select_agent_meeting_analysis(self, service):
        """Test agent selection for meeting analysis"""
        agent = service._select_agent("meeting_analysis", AgentTaskPriority.MEDIUM)
        assert agent == AgentType.MEETING_ANALYST

    def test_select_agent_kpi_analysis(self, service):
        """Test agent selection for KPI analysis"""
        agent = service._select_agent("kpi_analysis", AgentTaskPriority.HIGH)
        assert agent == AgentType.KPI_MONITOR

    def test_select_agent_briefing(self, service):
        """Test agent selection for briefing generation"""
        agent = service._select_agent("generate_briefing", AgentTaskPriority.MEDIUM)
        assert agent == AgentType.BRIEFING_GENERATOR

    def test_select_agent_recommendation(self, service):
        """Test agent selection for recommendations"""
        agent = service._select_agent("recommendation", AgentTaskPriority.LOW)
        assert agent == AgentType.RECOMMENDATION_ENGINE

    def test_select_agent_communication(self, service):
        """Test agent selection for communication"""
        agent = service._select_agent("communication", AgentTaskPriority.MEDIUM)
        assert agent == AgentType.COMMUNICATION_HANDLER

    def test_select_agent_voice_processing(self, service):
        """Test agent selection for voice processing"""
        agent = service._select_agent("voice_processing", AgentTaskPriority.HIGH)
        assert agent == AgentType.VOICE_PROCESSOR

    def test_select_agent_unknown_defaults_to_task_manager(self, service):
        """Test unknown task type defaults to task manager"""
        agent = service._select_agent("unknown_task_type", AgentTaskPriority.MEDIUM)
        assert agent == AgentType.TASK_MANAGER

    # ==================== TASK RETRIEVAL ====================

    @pytest.mark.asyncio
    async def test_get_task_success(self, service, mock_db_row):
        """Test getting task by ID"""
        task_id = uuid4()

        with patch('app.services.agent_routing_service.get_db_context') as mock_db:
            mock_context = AsyncMock()
            mock_result = MagicMock()
            mock_result.fetchone.return_value = mock_db_row
            mock_context.execute = AsyncMock(return_value=mock_result)
            mock_db.return_value.__aenter__.return_value = mock_context

            task = await service.get_task(task_id)

            assert task is not None
            assert isinstance(task, AgentTaskResponse)

    @pytest.mark.asyncio
    async def test_get_task_not_found(self, service):
        """Test getting non-existent task"""
        task_id = uuid4()

        with patch('app.services.agent_routing_service.get_db_context') as mock_db:
            mock_context = AsyncMock()
            mock_result = MagicMock()
            mock_result.fetchone.return_value = None
            mock_context.execute = AsyncMock(return_value=mock_result)
            mock_db.return_value.__aenter__.return_value = mock_context

            task = await service.get_task(task_id)

            assert task is None

    @pytest.mark.asyncio
    async def test_list_tasks_all(self, service, workspace_id, mock_db_row):
        """Test listing all tasks for workspace"""
        with patch('app.services.agent_routing_service.get_db_context') as mock_db:
            mock_context = AsyncMock()
            mock_result = MagicMock()
            mock_result.fetchall.return_value = [mock_db_row, mock_db_row]
            mock_context.execute = AsyncMock(return_value=mock_result)
            mock_db.return_value.__aenter__.return_value = mock_context

            tasks = await service.list_tasks(workspace_id)

            assert len(tasks) == 2
            assert all(isinstance(t, AgentTaskResponse) for t in tasks)

    @pytest.mark.asyncio
    async def test_list_tasks_with_filters(self, service, workspace_id, founder_id, mock_db_row):
        """Test listing tasks with filters"""
        with patch('app.services.agent_routing_service.get_db_context') as mock_db:
            mock_context = AsyncMock()
            mock_result = MagicMock()
            mock_result.fetchall.return_value = [mock_db_row]
            mock_context.execute = AsyncMock(return_value=mock_result)
            mock_db.return_value.__aenter__.return_value = mock_context

            tasks = await service.list_tasks(
                workspace_id=workspace_id,
                founder_id=founder_id,
                status=AgentTaskStatus.QUEUED,
                assigned_agent=AgentType.MEETING_ANALYST,
                limit=10
            )

            assert len(tasks) == 1

    # ==================== TASK MANAGEMENT ====================

    @pytest.mark.asyncio
    async def test_cancel_task_success(self, service):
        """Test cancelling a task"""
        task_id = uuid4()

        with patch('app.services.agent_routing_service.get_db_context') as mock_db:
            mock_context = AsyncMock()
            mock_result = MagicMock()
            mock_result.rowcount = 1
            mock_context.execute = AsyncMock(return_value=mock_result)
            mock_context.commit = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_context

            result = await service.cancel_task(task_id)

            assert result is True
            mock_context.commit.assert_called()

    @pytest.mark.asyncio
    async def test_cancel_task_not_found(self, service):
        """Test cancelling non-existent task"""
        task_id = uuid4()

        with patch('app.services.agent_routing_service.get_db_context') as mock_db:
            mock_context = AsyncMock()
            mock_result = MagicMock()
            mock_result.rowcount = 0
            mock_context.execute = AsyncMock(return_value=mock_result)
            mock_context.commit = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_context

            result = await service.cancel_task(task_id)

            assert result is False

    @pytest.mark.asyncio
    async def test_retry_task_success(self, service, mock_db_row):
        """Test retrying a failed task"""
        task_id = uuid4()
        mock_db_row.status = "failed"
        mock_db_row.retry_count = 0
        mock_db_row.max_retries = 3

        with patch('app.services.agent_routing_service.get_db_context') as mock_db:
            mock_context = AsyncMock()
            mock_result = MagicMock()
            mock_result.fetchone.return_value = mock_db_row
            mock_context.execute = AsyncMock(return_value=mock_result)
            mock_context.commit = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_context

            with patch.object(service, '_execute_task') as mock_execute:
                task = await service.retry_task(task_id)

                mock_execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_retry_task_not_failed(self, service, mock_db_row):
        """Test retrying a non-failed task raises error"""
        task_id = uuid4()
        mock_db_row.status = "queued"

        with patch('app.services.agent_routing_service.get_db_context') as mock_db:
            mock_context = AsyncMock()
            mock_result = MagicMock()
            mock_result.fetchone.return_value = mock_db_row
            mock_context.execute = AsyncMock(return_value=mock_result)
            mock_db.return_value.__aenter__.return_value = mock_context

            task = await service.retry_task(task_id)

            # Should return None due to error
            assert task is None

    @pytest.mark.asyncio
    async def test_retry_task_max_retries_exceeded(self, service, mock_db_row):
        """Test retrying task that exceeded max retries"""
        task_id = uuid4()
        mock_db_row.status = "failed"
        mock_db_row.retry_count = 3
        mock_db_row.max_retries = 3

        with patch('app.services.agent_routing_service.get_db_context') as mock_db:
            mock_context = AsyncMock()
            mock_result = MagicMock()
            mock_result.fetchone.return_value = mock_db_row
            mock_context.execute = AsyncMock(return_value=mock_result)
            mock_db.return_value.__aenter__.return_value = mock_context

            task = await service.retry_task(task_id)

            assert task is None

    # ==================== AGENT HEALTH ====================

    @pytest.mark.asyncio
    async def test_get_agent_health_available(self, service):
        """Test getting agent health when available"""
        with patch('app.services.agent_routing_service.get_db_context') as mock_db:
            mock_context = AsyncMock()
            mock_result = MagicMock()

            # Mock current load query
            load_row = MagicMock()
            load_row.__getitem__.return_value = 5  # 5 tasks processing

            # Mock success rate query
            success_row = MagicMock()
            success_row.__getitem__.side_effect = [8, 10]  # 8 successful out of 10

            mock_result.fetchone.side_effect = [load_row, success_row]
            mock_context.execute = AsyncMock(return_value=mock_result)
            mock_db.return_value.__aenter__.return_value = mock_context

            health = await service.get_agent_health(AgentType.MEETING_ANALYST)

            assert health.agent_type == AgentType.MEETING_ANALYST
            assert health.is_available is True  # 5 < 10 max capacity
            assert health.current_load == 5
            assert health.success_rate == 0.8

    @pytest.mark.asyncio
    async def test_get_agent_health_unavailable(self, service):
        """Test getting agent health when at capacity"""
        with patch('app.services.agent_routing_service.get_db_context') as mock_db:
            mock_context = AsyncMock()
            mock_result = MagicMock()

            load_row = MagicMock()
            load_row.__getitem__.return_value = 10  # At max capacity

            success_row = MagicMock()
            success_row.__getitem__.side_effect = [9, 10]

            mock_result.fetchone.side_effect = [load_row, success_row]
            mock_context.execute = AsyncMock(return_value=mock_result)
            mock_db.return_value.__aenter__.return_value = mock_context

            health = await service.get_agent_health(AgentType.KPI_MONITOR)

            assert health.is_available is False  # At capacity

    @pytest.mark.asyncio
    async def test_get_agent_health_error(self, service):
        """Test agent health error handling"""
        with patch('app.services.agent_routing_service.get_db_context') as mock_db:
            mock_db.side_effect = Exception("Database error")

            health = await service.get_agent_health(AgentType.BRIEFING_GENERATOR)

            assert health.is_available is False
            assert health.success_rate == 0.0

    # ==================== AGENT METRICS ====================

    @pytest.mark.asyncio
    async def test_get_agent_metrics_success(self, service):
        """Test getting agent metrics"""
        with patch('app.services.agent_routing_service.get_db_context') as mock_db:
            mock_context = AsyncMock()
            mock_result = MagicMock()

            metrics_row = MagicMock()
            # total, successful, failed, avg_time, queue_depth
            metrics_row.__getitem__.side_effect = [100, 80, 10, 1500.0, 5]

            mock_result.fetchone.return_value = metrics_row
            mock_context.execute = AsyncMock(return_value=mock_result)
            mock_db.return_value.__aenter__.return_value = mock_context

            metrics = await service.get_agent_metrics(AgentType.MEETING_ANALYST)

            assert metrics.agent_type == AgentType.MEETING_ANALYST
            assert metrics.total_tasks_processed == 100
            assert metrics.successful_tasks == 80
            assert metrics.failed_tasks == 10
            assert metrics.average_processing_time_ms == 1500.0
            assert metrics.current_queue_depth == 5

    @pytest.mark.asyncio
    async def test_get_agent_metrics_no_data(self, service):
        """Test getting metrics with no data"""
        with patch('app.services.agent_routing_service.get_db_context') as mock_db:
            mock_context = AsyncMock()
            mock_result = MagicMock()
            mock_result.fetchone.return_value = None
            mock_context.execute = AsyncMock(return_value=mock_result)
            mock_db.return_value.__aenter__.return_value = mock_context

            metrics = await service.get_agent_metrics(AgentType.TASK_MANAGER)

            assert metrics.total_tasks_processed == 0
            assert metrics.average_processing_time_ms == 0.0

    # ==================== TASK EXECUTION ====================

    @pytest.mark.asyncio
    async def test_execute_task_success(self, service, mock_db_row):
        """Test task execution"""
        task_id = uuid4()

        with patch('app.services.agent_routing_service.get_db_context') as mock_db:
            mock_context = AsyncMock()
            mock_result = MagicMock()
            mock_result.fetchone.return_value = mock_db_row
            mock_context.execute = AsyncMock(return_value=mock_result)
            mock_context.commit = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_context

            await service._execute_task(task_id)

            # Should have updated status to processing, then completed
            assert mock_context.execute.call_count >= 2

    @pytest.mark.asyncio
    async def test_execute_task_failure(self, service):
        """Test task execution failure"""
        task_id = uuid4()

        with patch('app.services.agent_routing_service.get_db_context') as mock_db:
            mock_context = AsyncMock()
            mock_context.execute = AsyncMock(side_effect=Exception("Execution failed"))
            mock_context.commit = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_context

            # Should handle error gracefully
            await service._execute_task(task_id)

    @pytest.mark.asyncio
    async def test_execute_agent_logic(self, service):
        """Test agent-specific logic execution"""
        result = await service._execute_agent_logic(
            agent_type=AgentType.MEETING_ANALYST,
            input_data={"transcript": "Meeting content"},
            context={"session_id": "123"}
        )

        assert result["agent"] == "meeting_analyst"
        assert result["status"] == "completed"
        assert "data" in result

    def test_build_task_response(self, service, mock_db_row):
        """Test building task response from database row"""
        task = service._build_task_response(mock_db_row)

        assert isinstance(task, AgentTaskResponse)
        assert task.task_type == "meeting_analysis"
        assert task.status == AgentTaskStatus.QUEUED
