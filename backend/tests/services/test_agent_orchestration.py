"""
Comprehensive tests for Agent Orchestration Service
Tests multi-agent workflows, DAG routing, result aggregation
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from uuid import uuid4, UUID

from app.services.agent_orchestration_service import AgentOrchestrationService
from app.models.agent_routing import (
    AgentType,
    AgentTaskStatus,
    AgentTaskPriority
)


class TestAgentOrchestrationService:
    """Test suite for AgentOrchestrationService"""

    @pytest.fixture
    def service(self):
        """Create agent orchestration service"""
        return AgentOrchestrationService()

    @pytest.fixture
    def workspace_id(self):
        """Sample workspace ID"""
        return uuid4()

    @pytest.fixture
    def founder_id(self):
        """Sample founder ID"""
        return uuid4()

    @pytest.fixture
    def sample_orchestration_request(self, workspace_id, founder_id):
        """Sample orchestration request"""
        return {
            "workspace_id": workspace_id,
            "founder_id": founder_id,
            "objective": "Analyze meeting and create tasks with insights",
            "input_data": {
                "meeting_transcript": "Discussed Q4 goals and team priorities",
                "context": "Strategic planning session"
            },
            "workflow_type": "cos_task_insight"
        }

    # ==================== WORKFLOW GRAPH ====================

    def test_get_workflow_graph_cos_task_insight(self, service):
        """Test CoS → Task → Insight workflow graph retrieval"""
        graph = service.get_workflow_graph("cos_task_insight")

        assert graph is not None
        assert "nodes" in graph
        assert "edges" in graph
        assert len(graph["nodes"]) == 3  # CoS, Task, Insight agents

        # Verify nodes
        node_types = [node["agent_type"] for node in graph["nodes"]]
        assert AgentType.BRIEFING_GENERATOR in node_types  # CoS agent
        assert AgentType.TASK_MANAGER in node_types
        assert AgentType.RECOMMENDATION_ENGINE in node_types  # Insight agent

        # Verify edges (DAG structure)
        assert len(graph["edges"]) == 2
        # CoS → Task
        assert any(e["from"] == AgentType.BRIEFING_GENERATOR and
                  e["to"] == AgentType.TASK_MANAGER
                  for e in graph["edges"])
        # Task → Insight
        assert any(e["from"] == AgentType.TASK_MANAGER and
                  e["to"] == AgentType.RECOMMENDATION_ENGINE
                  for e in graph["edges"])

    def test_get_workflow_graph_unknown(self, service):
        """Test unknown workflow type returns default"""
        graph = service.get_workflow_graph("unknown_workflow")

        assert graph is not None
        assert "nodes" in graph
        # Default should be simple single-agent workflow
        assert len(graph["nodes"]) >= 1

    def test_validate_workflow_graph_valid(self, service):
        """Test workflow graph validation succeeds for valid DAG"""
        graph = service.get_workflow_graph("cos_task_insight")
        is_valid, error = service.validate_workflow_graph(graph)

        assert is_valid is True
        assert error is None

    def test_validate_workflow_graph_cycle_detection(self, service):
        """Test workflow graph validation detects cycles"""
        # Create graph with cycle
        invalid_graph = {
            "nodes": [
                {"id": "node1", "agent_type": AgentType.TASK_MANAGER},
                {"id": "node2", "agent_type": AgentType.BRIEFING_GENERATOR}
            ],
            "edges": [
                {"from": AgentType.TASK_MANAGER, "to": AgentType.BRIEFING_GENERATOR},
                {"from": AgentType.BRIEFING_GENERATOR, "to": AgentType.TASK_MANAGER}  # Cycle
            ]
        }

        is_valid, error = service.validate_workflow_graph(invalid_graph)

        assert is_valid is False
        assert "cycle" in error.lower()

    # ==================== ORCHESTRATION EXECUTION ====================

    @pytest.mark.asyncio
    async def test_orchestrate_workflow_success(
        self,
        service,
        sample_orchestration_request
    ):
        """Test successful multi-agent workflow orchestration"""
        # Mock both routing service and database operations
        with patch.object(service, 'routing_service', AsyncMock()) as mock_routing_instance, \
             patch('app.services.agent_orchestration_service.get_db_context') as mock_db:

            # Mock agent task responses
            mock_cos_task = MagicMock()
            mock_cos_task.id = uuid4()
            mock_cos_task.status = AgentTaskStatus.COMPLETED
            mock_cos_task.output_data = {
                "summary": "Meeting covered Q4 goals",
                "key_points": ["Goal 1", "Goal 2"]
            }

            mock_task_manager_task = MagicMock()
            mock_task_manager_task.id = uuid4()
            mock_task_manager_task.status = AgentTaskStatus.COMPLETED
            mock_task_manager_task.output_data = {
                "tasks_created": 3,
                "task_ids": [str(uuid4()), str(uuid4()), str(uuid4())]
            }

            mock_insight_task = MagicMock()
            mock_insight_task.id = uuid4()
            mock_insight_task.status = AgentTaskStatus.COMPLETED
            mock_insight_task.output_data = {
                "insights": ["Team alignment improved", "Clear priorities set"],
                "recommendations": ["Schedule follow-up"]
            }

            # Configure mock to return tasks in sequence
            # Configure mock routing service
            mock_routing_instance.route_task.side_effect = [
                mock_cos_task,
                mock_task_manager_task,
                mock_insight_task
            ]
            mock_routing_instance.get_task.side_effect = [
                mock_cos_task,
                mock_task_manager_task,
                mock_insight_task,
                mock_cos_task,  # Additional calls for wait_for_task_completion
                mock_task_manager_task,
                mock_insight_task
            ]

            # Mock database context
            mock_context = AsyncMock()
            mock_result = MagicMock()
            workflow_id = uuid4()
            mock_row = MagicMock()
            mock_row.id = workflow_id
            mock_result.fetchone.return_value = mock_row
            mock_context.execute = AsyncMock(return_value=mock_result)
            mock_context.commit = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_context

            # Execute orchestration
            result = await service.orchestrate_workflow(
                workspace_id=sample_orchestration_request["workspace_id"],
                founder_id=sample_orchestration_request["founder_id"],
                objective=sample_orchestration_request["objective"],
                input_data=sample_orchestration_request["input_data"],
                workflow_type=sample_orchestration_request["workflow_type"]
            )

            assert result is not None
            assert result["status"] == "completed"
            assert "workflow_id" in result
            assert "execution_steps" in result
            assert len(result["execution_steps"]) == 3
            assert "aggregated_results" in result

            # Verify routing service was called for each agent
            assert mock_routing_instance.route_task.call_count == 3

    @pytest.mark.asyncio
    async def test_orchestrate_workflow_with_agent_failure(
        self,
        service,
        sample_orchestration_request
    ):
        """Test workflow handles agent failure gracefully"""
        with patch('app.services.agent_orchestration_service.AgentRoutingService') as mock_routing:
            mock_routing_instance = AsyncMock()
            mock_routing.return_value = mock_routing_instance

            # First agent succeeds
            mock_cos_task = MagicMock()
            mock_cos_task.id = uuid4()
            mock_cos_task.status = AgentTaskStatus.COMPLETED
            mock_cos_task.output_data = {"summary": "Meeting summary"}

            # Second agent fails
            mock_task_manager_task = MagicMock()
            mock_task_manager_task.id = uuid4()
            mock_task_manager_task.status = AgentTaskStatus.FAILED
            mock_task_manager_task.error_message = "Task creation failed"

            mock_routing_instance.route_task.side_effect = [
                mock_cos_task,
                mock_task_manager_task
            ]
            mock_routing_instance.get_task.side_effect = [
                mock_cos_task,
                mock_task_manager_task
            ]

            result = await service.orchestrate_workflow(
                workspace_id=sample_orchestration_request["workspace_id"],
                founder_id=sample_orchestration_request["founder_id"],
                objective=sample_orchestration_request["objective"],
                input_data=sample_orchestration_request["input_data"],
                workflow_type=sample_orchestration_request["workflow_type"]
            )

            assert result is not None
            assert result["status"] == "failed"
            assert "error" in result
            assert "execution_steps" in result
            # Should have executed only 2 steps before failure
            assert len([s for s in result["execution_steps"] if s.get("status") != "skipped"]) == 2

    @pytest.mark.asyncio
    async def test_orchestrate_workflow_timeout(
        self,
        service,
        sample_orchestration_request
    ):
        """Test workflow timeout handling"""
        with patch('app.services.agent_orchestration_service.AgentRoutingService') as mock_routing:
            mock_routing_instance = AsyncMock()
            mock_routing.return_value = mock_routing_instance

            # Mock task that never completes
            import asyncio
            async def delayed_task(*args, **kwargs):
                await asyncio.sleep(10)  # Longer than timeout
                return None

            mock_routing_instance.route_task.side_effect = delayed_task

            result = await service.orchestrate_workflow(
                workspace_id=sample_orchestration_request["workspace_id"],
                founder_id=sample_orchestration_request["founder_id"],
                objective=sample_orchestration_request["objective"],
                input_data=sample_orchestration_request["input_data"],
                workflow_type=sample_orchestration_request["workflow_type"],
                timeout_seconds=1  # Short timeout for testing
            )

            assert result is not None
            assert result["status"] == "failed"
            assert "timeout" in result.get("error", "").lower()

    # ==================== RESULT AGGREGATION ====================

    def test_aggregate_results_success(self, service):
        """Test successful result aggregation from multiple agents"""
        execution_steps = [
            {
                "agent_type": AgentType.BRIEFING_GENERATOR,
                "status": "completed",
                "output": {
                    "summary": "Meeting summary",
                    "key_points": ["Point 1", "Point 2"]
                }
            },
            {
                "agent_type": AgentType.TASK_MANAGER,
                "status": "completed",
                "output": {
                    "tasks_created": 5,
                    "task_ids": ["id1", "id2", "id3", "id4", "id5"]
                }
            },
            {
                "agent_type": AgentType.RECOMMENDATION_ENGINE,
                "status": "completed",
                "output": {
                    "insights": ["Insight 1", "Insight 2"],
                    "recommendations": ["Rec 1"]
                }
            }
        ]

        aggregated = service.aggregate_results(execution_steps)

        assert aggregated is not None
        assert "summary" in aggregated
        assert "agent_outputs" in aggregated
        assert len(aggregated["agent_outputs"]) == 3
        assert aggregated["total_agents"] == 3
        assert aggregated["successful_agents"] == 3
        assert aggregated["failed_agents"] == 0

    def test_aggregate_results_with_failures(self, service):
        """Test result aggregation with some failed agents"""
        execution_steps = [
            {
                "agent_type": AgentType.BRIEFING_GENERATOR,
                "status": "completed",
                "output": {"summary": "Success"}
            },
            {
                "agent_type": AgentType.TASK_MANAGER,
                "status": "failed",
                "error": "Failed to create tasks"
            },
            {
                "agent_type": AgentType.RECOMMENDATION_ENGINE,
                "status": "completed",
                "output": {"insights": ["Insight"]}
            }
        ]

        aggregated = service.aggregate_results(execution_steps)

        assert aggregated is not None
        assert aggregated["total_agents"] == 3
        assert aggregated["successful_agents"] == 2
        assert aggregated["failed_agents"] == 1
        assert "errors" in aggregated
        assert len(aggregated["errors"]) == 1

    # ==================== ROUTING LOGIC ====================

    @pytest.mark.asyncio
    async def test_execute_agent_step(self, service, workspace_id, founder_id):
        """Test single agent step execution"""
        with patch('app.services.agent_orchestration_service.AgentRoutingService') as mock_routing:
            mock_routing_instance = AsyncMock()
            mock_routing.return_value = mock_routing_instance

            mock_task = MagicMock()
            mock_task.id = uuid4()
            mock_task.status = AgentTaskStatus.COMPLETED
            mock_task.output_data = {"result": "success"}

            mock_routing_instance.route_task.return_value = mock_task
            mock_routing_instance.get_task.return_value = mock_task

            node = {
                "id": "test_node",
                "agent_type": AgentType.BRIEFING_GENERATOR
            }

            context = {
                "objective": "Test objective",
                "input_data": {"test": "data"}
            }

            result = await service.execute_agent_step(
                workspace_id=workspace_id,
                founder_id=founder_id,
                node=node,
                context=context
            )

            assert result is not None
            assert result["status"] == "completed"
            assert "task_id" in result
            assert "output" in result
            assert result["agent_type"] == AgentType.BRIEFING_GENERATOR

    @pytest.mark.asyncio
    async def test_wait_for_task_completion_success(self, service):
        """Test waiting for task completion - success case"""
        with patch('app.services.agent_orchestration_service.AgentRoutingService') as mock_routing:
            mock_routing_instance = AsyncMock()
            mock_routing.return_value = mock_routing_instance

            task_id = uuid4()

            # Mock task that completes on second check
            mock_task_processing = MagicMock()
            mock_task_processing.status = AgentTaskStatus.PROCESSING

            mock_task_completed = MagicMock()
            mock_task_completed.status = AgentTaskStatus.COMPLETED
            mock_task_completed.output_data = {"result": "done"}

            mock_routing_instance.get_task.side_effect = [
                mock_task_processing,
                mock_task_completed
            ]

            result = await service.wait_for_task_completion(
                task_id=task_id,
                timeout_seconds=10,
                poll_interval=0.1
            )

            assert result is not None
            assert result.status == AgentTaskStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_wait_for_task_completion_failure(self, service):
        """Test waiting for task completion - failure case"""
        with patch('app.services.agent_orchestration_service.AgentRoutingService') as mock_routing:
            mock_routing_instance = AsyncMock()
            mock_routing.return_value = mock_routing_instance

            task_id = uuid4()

            mock_task_failed = MagicMock()
            mock_task_failed.status = AgentTaskStatus.FAILED
            mock_task_failed.error_message = "Agent failed"

            mock_routing_instance.get_task.return_value = mock_task_failed

            result = await service.wait_for_task_completion(
                task_id=task_id,
                timeout_seconds=10,
                poll_interval=0.1
            )

            assert result is not None
            assert result.status == AgentTaskStatus.FAILED

    # ==================== WORKFLOW PERSISTENCE ====================

    @pytest.mark.asyncio
    async def test_save_workflow_execution(
        self,
        service,
        workspace_id,
        founder_id
    ):
        """Test workflow execution persistence"""
        with patch('app.services.agent_orchestration_service.get_db_context') as mock_db:
            mock_context = AsyncMock()
            mock_result = MagicMock()

            workflow_id = uuid4()
            mock_row = MagicMock()
            mock_row.id = workflow_id
            mock_result.fetchone.return_value = mock_row

            mock_context.execute = AsyncMock(return_value=mock_result)
            mock_context.commit = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_context

            execution_data = {
                "workflow_type": "cos_task_insight",
                "status": "completed",
                "execution_steps": [],
                "aggregated_results": {}
            }

            saved_id = await service.save_workflow_execution(
                workspace_id=workspace_id,
                founder_id=founder_id,
                objective="Test objective",
                execution_data=execution_data
            )

            assert saved_id is not None
            assert saved_id == workflow_id
            mock_context.execute.assert_called()
            mock_context.commit.assert_called()

    @pytest.mark.asyncio
    async def test_get_workflow_execution(self, service):
        """Test workflow execution retrieval"""
        with patch('app.services.agent_orchestration_service.get_db_context') as mock_db:
            mock_context = AsyncMock()
            mock_result = MagicMock()

            workflow_id = uuid4()
            workspace_id = uuid4()
            founder_id = uuid4()

            mock_row = MagicMock()
            mock_row.id = workflow_id
            mock_row.workspace_id = str(workspace_id)
            mock_row.founder_id = str(founder_id)
            mock_row.workflow_type = "cos_task_insight"
            mock_row.objective = "Test"
            mock_row.status = "completed"
            mock_row.execution_steps = []
            mock_row.aggregated_results = {}
            mock_row.created_at = datetime.utcnow()
            mock_row.completed_at = datetime.utcnow()

            mock_result.fetchone.return_value = mock_row
            mock_context.execute = AsyncMock(return_value=mock_result)
            mock_db.return_value.__aenter__.return_value = mock_context

            result = await service.get_workflow_execution(workflow_id)

            assert result is not None
            assert result["id"] == workflow_id
            assert result["workflow_type"] == "cos_task_insight"
            assert result["status"] == "completed"

    # ==================== ERROR HANDLING ====================

    @pytest.mark.asyncio
    async def test_orchestrate_with_invalid_workflow_type(
        self,
        service,
        workspace_id,
        founder_id
    ):
        """Test orchestration with invalid workflow type uses default"""
        with patch('app.services.agent_orchestration_service.AgentRoutingService') as mock_routing:
            mock_routing_instance = AsyncMock()
            mock_routing.return_value = mock_routing_instance

            mock_task = MagicMock()
            mock_task.id = uuid4()
            mock_task.status = AgentTaskStatus.COMPLETED
            mock_task.output_data = {"result": "success"}

            mock_routing_instance.route_task.return_value = mock_task
            mock_routing_instance.get_task.return_value = mock_task

            # Should not raise error, use default workflow
            result = await service.orchestrate_workflow(
                workspace_id=workspace_id,
                founder_id=founder_id,
                objective="Test",
                input_data={},
                workflow_type="invalid_type"
            )

            assert result is not None
            assert "workflow_id" in result

    @pytest.mark.asyncio
    async def test_orchestrate_with_empty_input(
        self,
        service,
        workspace_id,
        founder_id
    ):
        """Test orchestration handles empty input gracefully"""
        with patch('app.services.agent_orchestration_service.AgentRoutingService') as mock_routing:
            mock_routing_instance = AsyncMock()
            mock_routing.return_value = mock_routing_instance

            mock_task = MagicMock()
            mock_task.id = uuid4()
            mock_task.status = AgentTaskStatus.COMPLETED
            mock_task.output_data = {}

            mock_routing_instance.route_task.return_value = mock_task
            mock_routing_instance.get_task.return_value = mock_task

            result = await service.orchestrate_workflow(
                workspace_id=workspace_id,
                founder_id=founder_id,
                objective="Test with empty input",
                input_data={},
                workflow_type="cos_task_insight"
            )

            assert result is not None
            assert "workflow_id" in result
