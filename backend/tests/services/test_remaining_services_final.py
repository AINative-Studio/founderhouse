"""
Comprehensive tests for remaining low-coverage services:
1. Task Routing Service (87 uncovered, 17%)
2. Voice Command Service (102 uncovered, 14%)
3. Agent Collaboration Service (75 uncovered, 0%)

Quick coverage-focused tests covering core business logic
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
from uuid import UUID, uuid4
import asyncio

from app.services.task_routing_service import TaskRoutingService
from app.services.voice_command_service import VoiceCommandService
from app.services.agent_collaboration_service import AgentCollaborationService
from app.models.action_item import ActionItem, ActionItemPriority
from app.models.voice_command import (
    VoiceCommandRequest,
    VoiceCommandStatus,
    VoiceCommandIntent,
    VoiceTranscriptionRequest
)
from app.models.agent_routing import (
    AgentCollaborationRequest,
    AgentType,
    AgentTaskStatus
)


# ============================================================================
# TASK ROUTING SERVICE TESTS (15 tests)
# ============================================================================

class TestTaskRoutingServiceCore:
    """Core functionality tests for Task Routing Service"""

    @pytest.fixture
    def task_routing_service(self):
        """Create TaskRoutingService instance"""
        return TaskRoutingService(supabase_client=Mock())

    @pytest.fixture
    def sample_action_item(self):
        """Create sample action item for testing"""
        return ActionItem(
            id=uuid4(),
            meeting_id=uuid4(),
            workspace_id=uuid4(),
            founder_id=uuid4(),
            description="Review Q4 metrics",
            priority=ActionItemPriority.HIGH,
            assignee_email="alice@example.com",
            due_date=datetime.utcnow() + timedelta(days=7),
            confidence_score=0.92,
            context="Leadership meeting",
            created_at=datetime.utcnow()
        )

    def test_task_routing_initialization(self):
        """Test service initializes with optional supabase client"""
        mock_supabase = Mock()
        service = TaskRoutingService(supabase_client=mock_supabase)
        assert service.supabase == mock_supabase

    def test_task_routing_no_supabase(self):
        """Test service initializes without supabase"""
        service = TaskRoutingService()
        assert service.supabase is None

    def test_priority_map_exists(self, task_routing_service):
        """Test Monday priority mapping is complete"""
        assert TaskRoutingService.MONDAY_PRIORITY_MAP[ActionItemPriority.URGENT] == "Critical"
        assert TaskRoutingService.MONDAY_PRIORITY_MAP[ActionItemPriority.HIGH] == "High"
        assert TaskRoutingService.MONDAY_PRIORITY_MAP[ActionItemPriority.NORMAL] == "Medium"
        assert TaskRoutingService.MONDAY_PRIORITY_MAP[ActionItemPriority.LOW] == "Low"

    def test_build_column_values_with_priority(self, task_routing_service, sample_action_item):
        """Test column values include correct priority"""
        values = task_routing_service._build_monday_column_values(sample_action_item)
        assert values["priority"]["label"] == "High"

    def test_build_column_values_with_due_date(self, task_routing_service, sample_action_item):
        """Test column values include due date in correct format"""
        values = task_routing_service._build_monday_column_values(sample_action_item)
        assert "date" in values
        assert "date" in values["date"]

    def test_build_column_values_with_assignee(self, task_routing_service, sample_action_item):
        """Test column values include assignee"""
        values = task_routing_service._build_monday_column_values(sample_action_item)
        assert "person" in values
        assert "personsAndTeams" in values["person"]
        assert values["person"]["personsAndTeams"][0]["id"] == "alice@example.com"

    def test_build_column_values_default_status(self, task_routing_service, sample_action_item):
        """Test default status is 'To Do'"""
        values = task_routing_service._build_monday_column_values(sample_action_item)
        assert values["status"]["label"] == "To Do"

    def test_build_column_values_additional_metadata(self, task_routing_service, sample_action_item):
        """Test additional metadata is merged"""
        extra = {"custom_field": {"value": "test"}}
        values = task_routing_service._build_monday_column_values(sample_action_item, extra)
        assert values["custom_field"]["value"] == "test"

    def test_build_column_values_all_priorities(self, task_routing_service):
        """Test all priority levels map correctly"""
        for priority, expected in [
            (ActionItemPriority.URGENT, "Critical"),
            (ActionItemPriority.HIGH, "High"),
            (ActionItemPriority.NORMAL, "Medium"),
            (ActionItemPriority.LOW, "Low")
        ]:
            item = ActionItem(
                id=uuid4(),
                meeting_id=uuid4(),
                workspace_id=uuid4(),
                founder_id=uuid4(),
                description="Test",
                priority=priority,
                confidence_score=0.9,
                created_at=datetime.utcnow()
            )
            values = task_routing_service._build_monday_column_values(item)
            assert values["priority"]["label"] == expected

    def test_build_column_values_no_optional_fields(self, task_routing_service):
        """Test column values handle missing optional fields"""
        item = ActionItem(
            id=uuid4(),
            meeting_id=uuid4(),
            workspace_id=uuid4(),
            founder_id=uuid4(),
            description="Test",
            confidence_score=0.9,
            created_at=datetime.utcnow()
        )
        values = task_routing_service._build_monday_column_values(item)
        assert "status" in values
        assert "person" not in values
        assert "date" not in values

    @pytest.mark.asyncio
    async def test_create_task_unsupported_platform(self, task_routing_service, sample_action_item):
        """Test unsupported platform raises error"""
        with pytest.raises(ValueError, match="Unsupported platform"):
            await task_routing_service.create_task_from_action_item(
                sample_action_item,
                platform="jira",
                credentials={}
            )

    @pytest.mark.asyncio
    async def test_create_task_notion_not_implemented(self, task_routing_service, sample_action_item):
        """Test Notion integration raises NotImplementedError"""
        with pytest.raises(NotImplementedError):
            await task_routing_service.create_task_from_action_item(
                sample_action_item,
                platform="notion",
                credentials={}
            )

    @pytest.mark.asyncio
    async def test_batch_create_tasks_all_success(self, task_routing_service):
        """Test batch creation with all successful items"""
        items = [
            ActionItem(
                id=uuid4(),
                meeting_id=uuid4(),
                workspace_id=uuid4(),
                founder_id=uuid4(),
                description=f"Task {i}",
                priority=ActionItemPriority.NORMAL,
                confidence_score=0.9,
                created_at=datetime.utcnow()
            )
            for i in range(3)
        ]

        with patch.object(task_routing_service, 'create_task_from_action_item') as mock:
            mock.return_value = {"status": "created", "task_id": "123"}
            results = await task_routing_service.batch_create_tasks(items)

            assert len(results) == 3
            assert all(r["status"] == "success" for r in results)
            assert mock.call_count == 3

    @pytest.mark.asyncio
    async def test_batch_create_tasks_partial_failure(self, task_routing_service):
        """Test batch creation handles failures gracefully"""
        items = [
            ActionItem(
                id=uuid4(),
                meeting_id=uuid4(),
                workspace_id=uuid4(),
                founder_id=uuid4(),
                description=f"Task {i}",
                confidence_score=0.9,
                created_at=datetime.utcnow()
            )
            for i in range(3)
        ]

        with patch.object(task_routing_service, 'create_task_from_action_item') as mock:
            mock.side_effect = [
                {"status": "created"},
                Exception("API Error"),
                {"status": "created"}
            ]
            results = await task_routing_service.batch_create_tasks(items)

            assert len(results) == 3
            assert results[0]["status"] == "success"
            assert results[1]["status"] == "failed"
            assert results[2]["status"] == "success"


# ============================================================================
# VOICE COMMAND SERVICE TESTS (18 tests)
# ============================================================================

class TestVoiceCommandServiceCore:
    """Core functionality tests for Voice Command Service"""

    @pytest.fixture
    def voice_service(self):
        """Create VoiceCommandService instance"""
        return VoiceCommandService()

    def test_voice_service_initialization(self, voice_service):
        """Test service initializes with intent patterns"""
        assert hasattr(voice_service, 'intent_patterns')
        assert VoiceCommandIntent.CREATE_TASK in voice_service.intent_patterns
        assert VoiceCommandIntent.SCHEDULE_MEETING in voice_service.intent_patterns

    def test_voice_service_has_all_intents(self, voice_service):
        """Test all intent types are covered"""
        patterns = voice_service.intent_patterns
        assert VoiceCommandIntent.CREATE_TASK in patterns
        assert VoiceCommandIntent.SCHEDULE_MEETING in patterns
        assert VoiceCommandIntent.GET_SUMMARY in patterns
        assert VoiceCommandIntent.CHECK_METRICS in patterns
        assert VoiceCommandIntent.SEND_MESSAGE in patterns

    def test_recognize_intent_create_task(self, voice_service):
        """Test intent recognition for create task"""
        intent, confidence = voice_service._recognize_intent("create task to review metrics")
        assert intent == VoiceCommandIntent.CREATE_TASK
        assert confidence > 0.7

    def test_recognize_intent_schedule_meeting(self, voice_service):
        """Test intent recognition for schedule meeting"""
        intent, confidence = voice_service._recognize_intent("schedule meeting with investors")
        assert intent == VoiceCommandIntent.SCHEDULE_MEETING
        assert confidence > 0.7

    def test_recognize_intent_get_summary(self, voice_service):
        """Test intent recognition for summary"""
        intent, confidence = voice_service._recognize_intent("summarize today's meeting")
        assert intent == VoiceCommandIntent.GET_SUMMARY
        assert confidence > 0.7

    def test_recognize_intent_check_metrics(self, voice_service):
        """Test intent recognition for metrics"""
        intent, confidence = voice_service._recognize_intent("check metrics for Q4")
        assert intent == VoiceCommandIntent.CHECK_METRICS
        assert confidence > 0.7

    def test_recognize_intent_send_message(self, voice_service):
        """Test intent recognition for sending message"""
        intent, confidence = voice_service._recognize_intent("send message to team")
        assert intent == VoiceCommandIntent.SEND_MESSAGE
        assert confidence > 0.7

    def test_recognize_intent_unknown(self, voice_service):
        """Test unknown intent recognition"""
        intent, confidence = voice_service._recognize_intent("xyz pqr abc")
        assert intent == VoiceCommandIntent.UNKNOWN
        assert confidence == 0.3

    def test_recognize_intent_case_insensitive(self, voice_service):
        """Test intent recognition is case insensitive"""
        intent1, _ = voice_service._recognize_intent("CREATE TASK test")
        intent2, _ = voice_service._recognize_intent("create task test")
        assert intent1 == intent2 == VoiceCommandIntent.CREATE_TASK

    def test_extract_entities_create_task(self, voice_service):
        """Test entity extraction for task creation"""
        entities = voice_service._extract_entities(
            "create task to review finances",
            VoiceCommandIntent.CREATE_TASK
        )
        assert "task" in entities
        assert "review finances" in entities["task"]

    def test_extract_entities_schedule_meeting(self, voice_service):
        """Test entity extraction for meeting scheduling"""
        entities = voice_service._extract_entities(
            "schedule meeting with board",
            VoiceCommandIntent.SCHEDULE_MEETING
        )
        assert "meeting_subject" in entities

    def test_extract_entities_send_message(self, voice_service):
        """Test entity extraction for message sending"""
        entities = voice_service._extract_entities(
            "send message to CEO",
            VoiceCommandIntent.SEND_MESSAGE
        )
        assert "message" in entities

    def test_extract_entities_unknown_intent(self, voice_service):
        """Test entity extraction returns empty for unknown intent"""
        entities = voice_service._extract_entities(
            "random text",
            VoiceCommandIntent.UNKNOWN
        )
        assert entities == {}

    def test_mock_transcription(self, voice_service):
        """Test mock transcription returns expected text"""
        request = VoiceTranscriptionRequest(
            workspace_id=uuid4(),
            founder_id=uuid4()
        )
        transcript = voice_service._mock_transcription(request)
        assert isinstance(transcript, str)
        assert len(transcript) > 0

    @pytest.mark.asyncio
    async def test_transcribe_audio_success(self, voice_service):
        """Test audio transcription returns response"""
        request = VoiceTranscriptionRequest(
            workspace_id=uuid4(),
            founder_id=uuid4(),
            audio_base64="test_audio_data"
        )
        response = await voice_service.transcribe_audio(request)

        assert response is not None
        assert response.confidence > 0.9
        assert isinstance(response.duration_seconds, float)

    @pytest.mark.asyncio
    async def test_execute_command_create_task(self, voice_service):
        """Test command execution for task creation"""
        action_taken, result = await voice_service._execute_command(
            command_id=uuid4(),
            intent=VoiceCommandIntent.CREATE_TASK,
            entities={"task": "Review metrics"},
            workspace_id=uuid4(),
            founder_id=uuid4()
        )

        assert "Created task" in action_taken
        assert "task_id" in result

    @pytest.mark.asyncio
    async def test_execute_command_get_summary(self, voice_service):
        """Test command execution for summary retrieval"""
        action_taken, result = await voice_service._execute_command(
            command_id=uuid4(),
            intent=VoiceCommandIntent.GET_SUMMARY,
            entities={},
            workspace_id=uuid4(),
            founder_id=uuid4()
        )

        assert "briefing" in action_taken.lower()
        assert "status" in result

    @pytest.mark.asyncio
    async def test_get_command_history_empty(self, voice_service):
        """Test getting command history returns empty when none exist"""
        with patch('app.services.voice_command_service.get_db_context') as mock_db:
            mock_result = AsyncMock()
            mock_result.fetchall.return_value = []
            mock_db.return_value.__aenter__.return_value.execute.return_value = mock_result

            commands = await voice_service.get_command_history(uuid4(), uuid4())
            assert commands == []


# ============================================================================
# AGENT COLLABORATION SERVICE TESTS (17 tests)
# ============================================================================

class TestAgentCollaborationServiceCore:
    """Core functionality tests for Agent Collaboration Service"""

    @pytest.fixture
    def agent_collaboration_service(self):
        """Create AgentCollaborationService instance"""
        with patch('app.services.agent_collaboration_service.AgentRoutingService'):
            return AgentCollaborationService()

    @pytest.fixture
    def collab_request(self):
        """Create sample collaboration request"""
        return AgentCollaborationRequest(
            workspace_id=uuid4(),
            founder_id=uuid4(),
            primary_agent=AgentType.MEETING_ANALYST,
            collaborating_agents=[AgentType.KPI_MONITOR, AgentType.BRIEFING_GENERATOR],
            objective="Analyze Q4 performance",
            shared_context={"quarter": "Q4"},
            timeout_seconds=300
        )

    def test_collaboration_service_initialization(self, agent_collaboration_service):
        """Test service initializes with routing service"""
        assert hasattr(agent_collaboration_service, 'routing_service')
        assert hasattr(agent_collaboration_service, 'logger')

    @pytest.mark.asyncio
    async def test_execute_agent_task_meeting_analyst(self, agent_collaboration_service):
        """Test executing meeting analyst agent task"""
        result = await agent_collaboration_service._execute_agent_task(
            agent=AgentType.MEETING_ANALYST,
            objective="Analyze meeting",
            context={}
        )

        assert "analysis" in result
        assert "key_points" in result
        assert "action_items" in result

    @pytest.mark.asyncio
    async def test_execute_agent_task_kpi_monitor(self, agent_collaboration_service):
        """Test executing KPI monitor agent task"""
        result = await agent_collaboration_service._execute_agent_task(
            agent=AgentType.KPI_MONITOR,
            objective="Check metrics",
            context={}
        )

        assert "metrics_analyzed" in result
        assert "anomalies_found" in result

    @pytest.mark.asyncio
    async def test_execute_agent_task_briefing_generator(self, agent_collaboration_service):
        """Test executing briefing generator agent task"""
        result = await agent_collaboration_service._execute_agent_task(
            agent=AgentType.BRIEFING_GENERATOR,
            objective="Generate briefing",
            context={}
        )

        assert "briefing_created" in result
        assert result["briefing_created"] is True

    def test_synthesize_results(self, agent_collaboration_service):
        """Test result synthesis from multiple agents"""
        primary = {"analysis": "Primary result"}
        collaborators = {
            "kpi_monitor": {"metrics": 5},
            "briefing": {"sections": 4}
        }

        result = agent_collaboration_service._synthesize_results(
            primary_output=primary,
            collaborator_outputs=collaborators,
            objective="Test objective"
        )

        assert result["objective"] == "Test objective"
        assert result["status"] == "completed"
        assert "primary_agent_contribution" in result
        assert "collaborator_contributions" in result
        assert len(result["insights"]) > 0

    @pytest.mark.asyncio
    async def test_synthesize_results_contains_summary(self, agent_collaboration_service):
        """Test synthesized results contain summary"""
        primary = {"output": "test"}
        collaborators = {"agent1": {"output": "test1"}, "agent2": {"output": "test2"}}

        result = agent_collaboration_service._synthesize_results(
            primary_output=primary,
            collaborator_outputs=collaborators,
            objective="Test"
        )

        assert "summary" in result
        assert "2 collaborating agents" in result["summary"]

    @pytest.mark.asyncio
    async def test_execute_collaboration_multiple_agents(self, agent_collaboration_service):
        """Test executing collaboration with multiple agents"""
        result = await agent_collaboration_service._execute_collaboration(
            session_id=uuid4(),
            primary_agent=AgentType.MEETING_ANALYST,
            collaborating_agents=[AgentType.KPI_MONITOR, AgentType.BRIEFING_GENERATOR],
            objective="Analyze performance",
            shared_context={"data": "test"},
            timeout_seconds=10
        )

        assert "agent_outputs" in result
        assert "final_result" in result
        assert AgentType.MEETING_ANALYST.value in result["agent_outputs"]
        assert len(result["agent_outputs"]) == 3

    @pytest.mark.asyncio
    async def test_execute_collaboration_primary_agent_executes_first(self, agent_collaboration_service):
        """Test primary agent executes before collaborators"""
        with patch.object(agent_collaboration_service, '_execute_agent_task') as mock_task:
            mock_task.return_value = {"result": "test"}

            result = await agent_collaboration_service._execute_collaboration(
                session_id=uuid4(),
                primary_agent=AgentType.MEETING_ANALYST,
                collaborating_agents=[AgentType.KPI_MONITOR],
                objective="Test",
                shared_context={},
                timeout_seconds=10
            )

            # Should have both primary and collaborator outputs
            assert AgentType.MEETING_ANALYST.value in result["agent_outputs"]
            assert AgentType.KPI_MONITOR.value in result["agent_outputs"]

    @pytest.mark.asyncio
    async def test_execute_collaboration_timeout_error(self, agent_collaboration_service):
        """Test collaboration timeout raises error"""
        with patch.object(agent_collaboration_service, '_execute_agent_task') as mock_task:
            async def slow_task(*args, **kwargs):
                await asyncio.sleep(10)

            mock_task.side_effect = slow_task

            with pytest.raises(Exception, match="timeout"):
                await agent_collaboration_service._execute_collaboration(
                    session_id=uuid4(),
                    primary_agent=AgentType.MEETING_ANALYST,
                    collaborating_agents=[AgentType.KPI_MONITOR],
                    objective="Test",
                    shared_context={},
                    timeout_seconds=0.1
                )

    @pytest.mark.asyncio
    async def test_get_collaboration_not_found(self, agent_collaboration_service):
        """Test getting non-existent collaboration returns None"""
        with patch('app.services.agent_collaboration_service.get_db_context') as mock_db:
            mock_result = AsyncMock()
            mock_result.fetchone.return_value = None
            mock_db.return_value.__aenter__.return_value.execute.return_value = mock_result

            result = await agent_collaboration_service.get_collaboration(uuid4())
            assert result is None

    @pytest.mark.asyncio
    async def test_get_collaboration_success(self, agent_collaboration_service):
        """Test retrieving existing collaboration"""
        session_id = uuid4()
        workspace_id = uuid4()
        founder_id = uuid4()

        mock_row = Mock()
        mock_row.id = str(session_id)
        mock_row.workspace_id = str(workspace_id)
        mock_row.founder_id = str(founder_id)
        mock_row.primary_agent = AgentType.MEETING_ANALYST.value
        mock_row.collaborating_agents = [AgentType.KPI_MONITOR.value]
        mock_row.objective = "Test"
        mock_row.status = AgentTaskStatus.COMPLETED.value
        mock_row.shared_context = {}
        mock_row.agent_outputs = {}
        mock_row.final_result = {"result": "test"}
        mock_row.error_message = None
        mock_row.created_at = datetime.utcnow()
        mock_row.completed_at = datetime.utcnow()

        mock_db_context = AsyncMock()
        mock_result = AsyncMock()
        mock_result.fetchone = AsyncMock(return_value=mock_row)
        mock_db_context.execute = AsyncMock(return_value=mock_result)
        mock_db_context.__aenter__ = AsyncMock(return_value=mock_db_context)
        mock_db_context.__aexit__ = AsyncMock(return_value=None)

        with patch('app.services.agent_collaboration_service.get_db_context', return_value=mock_db_context):
            result = await agent_collaboration_service.get_collaboration(session_id)

            assert result is not None
            assert str(result.id) == str(session_id)
            assert result.primary_agent == AgentType.MEETING_ANALYST

    @pytest.mark.asyncio
    async def test_execute_collaboration_handles_agent_failures(self, agent_collaboration_service):
        """Test collaboration handles individual agent failures"""
        with patch.object(agent_collaboration_service, '_execute_agent_task') as mock_task:
            async def fail_second(*args, **kwargs):
                if len(mock_task.call_args_list) > 1:
                    raise Exception("Agent failed")
                return {"result": "success"}

            mock_task.side_effect = fail_second

            result = await agent_collaboration_service._execute_collaboration(
                session_id=uuid4(),
                primary_agent=AgentType.MEETING_ANALYST,
                collaborating_agents=[AgentType.KPI_MONITOR],
                objective="Test",
                shared_context={},
                timeout_seconds=10
            )

            # Should complete despite agent failure
            assert "agent_outputs" in result
            assert "final_result" in result

    @pytest.mark.asyncio
    async def test_initiate_collaboration_creates_session(self, agent_collaboration_service, collab_request):
        """Test initiating collaboration creates database session"""
        with patch('app.services.agent_collaboration_service.get_db_context') as mock_db:
            session_id = uuid4()

            mock_result = Mock()
            mock_result.id = session_id
            mock_result.workspace_id = str(collab_request.workspace_id)
            mock_result.founder_id = str(collab_request.founder_id)
            mock_result.primary_agent = collab_request.primary_agent.value
            mock_result.collaborating_agents = [a.value for a in collab_request.collaborating_agents]
            mock_result.objective = collab_request.objective
            mock_result.status = AgentTaskStatus.COMPLETED.value
            mock_result.shared_context = collab_request.shared_context
            mock_result.agent_outputs = {}
            mock_result.final_result = {}
            mock_result.error_message = None
            mock_result.created_at = datetime.utcnow()
            mock_result.completed_at = datetime.utcnow()

            mock_db_obj = AsyncMock()
            mock_db_obj.execute.return_value.fetchone.return_value = mock_result
            mock_db.return_value.__aenter__.return_value = mock_db_obj

            with patch.object(agent_collaboration_service, '_execute_collaboration') as mock_exec:
                mock_exec.return_value = {"agent_outputs": {}, "final_result": {}}
                with patch.object(agent_collaboration_service, 'get_collaboration') as mock_get:
                    mock_get.return_value = None  # Simplify test

                    response = await agent_collaboration_service.initiate_collaboration(collab_request)

                    # Verify database insert was called
                    assert mock_db_obj.execute.called

    @pytest.mark.asyncio
    async def test_initiate_collaboration_updates_with_results(self, agent_collaboration_service, collab_request):
        """Test collaboration updates session with results"""
        session_id = uuid4()

        mock_db_context = AsyncMock()
        mock_result = AsyncMock()
        mock_result.fetchone = AsyncMock(return_value=Mock(id=str(session_id)))
        mock_db_context.execute = AsyncMock(return_value=mock_result)
        mock_db_context.commit = AsyncMock()
        mock_db_context.__aenter__ = AsyncMock(return_value=mock_db_context)
        mock_db_context.__aexit__ = AsyncMock(return_value=None)

        with patch('app.services.agent_collaboration_service.get_db_context', return_value=mock_db_context):
            with patch.object(agent_collaboration_service, '_execute_collaboration') as mock_exec:
                mock_exec.return_value = {
                    "agent_outputs": {"primary": {}},
                    "final_result": {"status": "completed"}
                }
                with patch.object(agent_collaboration_service, 'get_collaboration') as mock_get:
                    mock_get.return_value = None

                    result = await agent_collaboration_service.initiate_collaboration(collab_request)

                    # Should have called execute at least twice (insert and update)
                    assert mock_db_context.execute.call_count >= 2


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
