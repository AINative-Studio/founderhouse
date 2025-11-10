"""
Unit tests for Task Routing Service
Tests routing logic, agent selection, and cross-agent workflows
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
from uuid import UUID, uuid4

from app.services.task_routing_service import TaskRoutingService
from app.models.action_item import ActionItem, ActionItemPriority
from tests.fixtures.routing_fixtures import (
    MOCK_AGENTS,
    ROUTING_RULES,
    MOCK_ROUTING_REQUESTS,
    MOCK_ROUTING_DECISIONS,
    COLLABORATION_WORKFLOWS,
    get_mock_agent,
    get_agents_by_capability,
    create_routing_request
)


@pytest.fixture
def mock_supabase():
    """Create mock Supabase client"""
    return Mock()


@pytest.fixture
def routing_service(mock_supabase):
    """Create TaskRoutingService instance"""
    return TaskRoutingService(supabase_client=mock_supabase)


@pytest.fixture
def sample_action_item():
    """Create sample action item"""
    return ActionItem(
        id=uuid4(),
        meeting_id=uuid4(),
        workspace_id=uuid4(),
        description="Review Q4 metrics and prepare report",
        priority=ActionItemPriority.HIGH,
        assignee_email="alice@example.com",
        due_date=datetime.utcnow() + timedelta(days=7),
        confidence_score=0.92,
        context="Discussed in leadership meeting",
        created_at=datetime.utcnow()
    )


class TestTaskRoutingInitialization:
    """Test service initialization"""

    def test_service_initialization_with_supabase(self, mock_supabase):
        """Test service initializes with Supabase client"""
        service = TaskRoutingService(supabase_client=mock_supabase)
        assert service.supabase == mock_supabase

    def test_service_initialization_without_supabase(self):
        """Test service initializes without Supabase"""
        service = TaskRoutingService()
        assert service.supabase is None

    def test_priority_mapping_exists(self):
        """Test Monday.com priority mapping is defined"""
        assert hasattr(TaskRoutingService, 'MONDAY_PRIORITY_MAP')
        assert ActionItemPriority.URGENT in TaskRoutingService.MONDAY_PRIORITY_MAP
        assert ActionItemPriority.HIGH in TaskRoutingService.MONDAY_PRIORITY_MAP


class TestMondayTaskCreation:
    """Test Monday.com task creation"""

    @pytest.mark.asyncio
    async def test_create_monday_task_success(self, routing_service, sample_action_item):
        """Test successful Monday task creation"""
        credentials = {"api_token": "test_token"}
        board_id = "12345"

        with patch('app.services.task_routing_service.MondayConnector') as MockConnector:
            mock_connector = AsyncMock()
            MockConnector.return_value.__aenter__.return_value = mock_connector

            # Mock create item response
            from app.connectors.base_connector import ConnectorResponse, ConnectorStatus
            mock_connector.create_item.return_value = ConnectorResponse(
                status=ConnectorStatus.SUCCESS,
                data={
                    "data": {
                        "create_item": {
                            "id": "item_123",
                            "name": sample_action_item.description
                        }
                    }
                }
            )

            result = await routing_service._create_monday_task(
                sample_action_item,
                credentials,
                board_id
            )

            assert result["status"] == "created"
            assert result["task_id"] == "item_123"
            assert result["board_id"] == board_id
            assert "task_url" in result

    @pytest.mark.asyncio
    async def test_create_monday_task_fetches_default_board(self, routing_service, sample_action_item):
        """Test task creation fetches default board if none provided"""
        credentials = {"api_token": "test_token"}

        with patch('app.services.task_routing_service.MondayConnector') as MockConnector:
            mock_connector = AsyncMock()
            MockConnector.return_value.__aenter__.return_value = mock_connector

            # Mock boards list
            from app.connectors.base_connector import ConnectorResponse, ConnectorStatus
            mock_connector.list_boards.return_value = ConnectorResponse(
                status=ConnectorStatus.SUCCESS,
                data={
                    "data": {
                        "boards": [{"id": "board_default", "name": "Default Board"}]
                    }
                }
            )

            mock_connector.create_item.return_value = ConnectorResponse(
                status=ConnectorStatus.SUCCESS,
                data={"data": {"create_item": {"id": "item_123"}}}
            )

            result = await routing_service._create_monday_task(
                sample_action_item,
                credentials,
                None  # No board_id
            )

            mock_connector.list_boards.assert_called_once()
            assert result["board_id"] == "board_default"

    @pytest.mark.asyncio
    async def test_create_monday_task_adds_context_as_update(self, routing_service, sample_action_item):
        """Test context is added as Monday update"""
        credentials = {"api_token": "test_token"}
        board_id = "12345"

        with patch('app.services.task_routing_service.MondayConnector') as MockConnector:
            mock_connector = AsyncMock()
            MockConnector.return_value.__aenter__.return_value = mock_connector

            from app.connectors.base_connector import ConnectorResponse, ConnectorStatus
            mock_connector.create_item.return_value = ConnectorResponse(
                status=ConnectorStatus.SUCCESS,
                data={"data": {"create_item": {"id": "item_123"}}}
            )

            await routing_service._create_monday_task(
                sample_action_item,
                credentials,
                board_id
            )

            # Should call create_update with context
            mock_connector.create_update.assert_called_once()
            call_args = mock_connector.create_update.call_args
            assert sample_action_item.context in call_args[1]["body"]

    @pytest.mark.asyncio
    async def test_create_monday_task_error_no_boards(self, routing_service, sample_action_item):
        """Test error when no boards found"""
        credentials = {"api_token": "test_token"}

        with patch('app.services.task_routing_service.MondayConnector') as MockConnector:
            mock_connector = AsyncMock()
            MockConnector.return_value.__aenter__.return_value = mock_connector

            from app.connectors.base_connector import ConnectorResponse, ConnectorStatus
            mock_connector.list_boards.return_value = ConnectorResponse(
                status=ConnectorStatus.SUCCESS,
                data={"data": {"boards": []}}
            )

            with pytest.raises(ValueError, match="No Monday.com boards found"):
                await routing_service._create_monday_task(
                    sample_action_item,
                    credentials,
                    None
                )


class TestColumnValueMapping:
    """Test Monday.com column value mapping"""

    def test_build_column_values_with_priority(self, routing_service, sample_action_item):
        """Test column values include priority"""
        column_values = routing_service._build_monday_column_values(sample_action_item)

        assert "priority" in column_values
        assert column_values["priority"]["label"] == "High"

    def test_build_column_values_with_due_date(self, routing_service, sample_action_item):
        """Test column values include due date"""
        column_values = routing_service._build_monday_column_values(sample_action_item)

        assert "date" in column_values
        assert "date" in column_values["date"]

    def test_build_column_values_with_assignee(self, routing_service, sample_action_item):
        """Test column values include assignee"""
        column_values = routing_service._build_monday_column_values(sample_action_item)

        assert "person" in column_values
        assert "personsAndTeams" in column_values["person"]

    def test_build_column_values_default_status(self, routing_service, sample_action_item):
        """Test column values default status is To Do"""
        column_values = routing_service._build_monday_column_values(sample_action_item)

        assert "status" in column_values
        assert column_values["status"]["label"] == "To Do"

    def test_build_column_values_priority_mapping(self, routing_service):
        """Test all priority levels map correctly"""
        priorities = {
            ActionItemPriority.URGENT: "Critical",
            ActionItemPriority.HIGH: "High",
            ActionItemPriority.NORMAL: "Medium",
            ActionItemPriority.LOW: "Low"
        }

        for priority, expected_label in priorities.items():
            action_item = ActionItem(
                id=uuid4(),
                meeting_id=uuid4(),
                workspace_id=uuid4(),
                description="Test",
                priority=priority,
                confidence_score=0.9,
                created_at=datetime.utcnow()
            )

            column_values = routing_service._build_monday_column_values(action_item)
            assert column_values["priority"]["label"] == expected_label

    def test_build_column_values_with_additional_metadata(self, routing_service, sample_action_item):
        """Test additional metadata is included"""
        additional = {"custom_field": {"value": "test"}}

        column_values = routing_service._build_monday_column_values(
            sample_action_item,
            additional_metadata=additional
        )

        assert "custom_field" in column_values


class TestBatchTaskCreation:
    """Test batch task creation"""

    @pytest.mark.asyncio
    async def test_batch_create_tasks_success(self, routing_service):
        """Test batch creating multiple tasks"""
        action_items = [
            ActionItem(
                id=uuid4(),
                meeting_id=uuid4(),
                workspace_id=uuid4(),
                description=f"Task {i}",
                priority=ActionItemPriority.NORMAL,
                confidence_score=0.9,
                created_at=datetime.utcnow()
            )
            for i in range(3)
        ]

        credentials = {"api_token": "test_token"}

        with patch.object(routing_service, 'create_task_from_action_item') as mock_create:
            mock_create.return_value = {
                "platform": "monday",
                "task_id": "item_123",
                "status": "created"
            }

            results = await routing_service.batch_create_tasks(
                action_items,
                credentials=credentials
            )

            assert len(results) == 3
            assert all(r["status"] == "success" for r in results)
            assert mock_create.call_count == 3

    @pytest.mark.asyncio
    async def test_batch_create_tasks_partial_failure(self, routing_service):
        """Test batch creation handles individual failures"""
        action_items = [
            ActionItem(
                id=uuid4(),
                meeting_id=uuid4(),
                workspace_id=uuid4(),
                description=f"Task {i}",
                priority=ActionItemPriority.NORMAL,
                confidence_score=0.9,
                created_at=datetime.utcnow()
            )
            for i in range(3)
        ]

        credentials = {"api_token": "test_token"}

        with patch.object(routing_service, 'create_task_from_action_item') as mock_create:
            # Second task fails
            mock_create.side_effect = [
                {"status": "created"},
                Exception("API Error"),
                {"status": "created"}
            ]

            results = await routing_service.batch_create_tasks(
                action_items,
                credentials=credentials
            )

            assert len(results) == 3
            assert results[0]["status"] == "success"
            assert results[1]["status"] == "failed"
            assert results[2]["status"] == "success"


class TestMeetingTaskCreation:
    """Test creating tasks from meeting action items"""

    @pytest.mark.asyncio
    async def test_create_tasks_from_meeting_success(self, routing_service):
        """Test creating tasks from all meeting action items"""
        meeting_id = uuid4()
        credentials = {"api_token": "test_token"}

        action_items = [
            ActionItem(
                id=uuid4(),
                meeting_id=meeting_id,
                workspace_id=uuid4(),
                description=f"Action {i}",
                priority=ActionItemPriority.NORMAL,
                confidence_score=0.8 + (i * 0.05),
                created_at=datetime.utcnow()
            )
            for i in range(5)
        ]

        with patch.object(routing_service, '_get_meeting_action_items') as mock_get:
            with patch.object(routing_service, 'batch_create_tasks') as mock_batch:
                mock_get.return_value = action_items
                mock_batch.return_value = [{"status": "success"}] * 5

                results = await routing_service.create_tasks_from_meeting(
                    meeting_id,
                    credentials=credentials
                )

                assert len(results) == 5
                mock_get.assert_called_once_with(meeting_id)

    @pytest.mark.asyncio
    async def test_create_tasks_from_meeting_filters_by_confidence(self, routing_service):
        """Test filters action items by confidence threshold"""
        meeting_id = uuid4()
        credentials = {"api_token": "test_token"}

        action_items = [
            ActionItem(
                id=uuid4(),
                meeting_id=meeting_id,
                workspace_id=uuid4(),
                description=f"Action {i}",
                priority=ActionItemPriority.NORMAL,
                confidence_score=0.5 + (i * 0.1),  # 0.5, 0.6, 0.7, 0.8, 0.9
                created_at=datetime.utcnow()
            )
            for i in range(5)
        ]

        with patch.object(routing_service, '_get_meeting_action_items') as mock_get:
            with patch.object(routing_service, 'batch_create_tasks') as mock_batch:
                mock_get.return_value = action_items
                mock_batch.return_value = []

                await routing_service.create_tasks_from_meeting(
                    meeting_id,
                    credentials=credentials,
                    min_confidence=0.7
                )

                # Should only pass items with confidence >= 0.7 (3 items)
                call_args = mock_batch.call_args
                filtered_items = call_args[1]["action_items"]
                assert len(filtered_items) == 3
                assert all(item.confidence_score >= 0.7 for item in filtered_items)


class TestPlatformRouting:
    """Test routing to different platforms"""

    @pytest.mark.asyncio
    async def test_create_task_notion_not_implemented(self, routing_service, sample_action_item):
        """Test Notion platform raises NotImplementedError"""
        credentials = {"access_token": "test_token"}

        with pytest.raises(NotImplementedError, match="Notion"):
            await routing_service.create_task_from_action_item(
                sample_action_item,
                platform="notion",
                credentials=credentials
            )

    @pytest.mark.asyncio
    async def test_create_task_unsupported_platform(self, routing_service, sample_action_item):
        """Test unsupported platform raises ValueError"""
        credentials = {"access_token": "test_token"}

        with pytest.raises(ValueError, match="Unsupported platform"):
            await routing_service.create_task_from_action_item(
                sample_action_item,
                platform="jira",
                credentials=credentials
            )


class TestTaskLinking:
    """Test linking tasks to meetings"""

    @pytest.mark.asyncio
    async def test_link_task_to_meeting_success(self, routing_service):
        """Test linking task to meeting"""
        task_id = "item_123"
        meeting_id = uuid4()
        credentials = {"api_token": "test_token"}

        with patch('app.services.task_routing_service.MondayConnector') as MockConnector:
            mock_connector = AsyncMock()
            MockConnector.return_value.__aenter__.return_value = mock_connector

            from app.connectors.base_connector import ConnectorResponse, ConnectorStatus
            mock_connector.create_update.return_value = ConnectorResponse(
                status=ConnectorStatus.SUCCESS,
                data={}
            )

            result = await routing_service.link_task_to_meeting(
                task_id,
                meeting_id,
                credentials=credentials
            )

            assert result["task_id"] == task_id
            assert result["meeting_id"] == str(meeting_id)
            assert result["status"] == "linked"
            mock_connector.create_update.assert_called_once()


class TestDatabaseOperations:
    """Test database operations"""

    @pytest.mark.asyncio
    async def test_update_action_item_task_info(self, routing_service, mock_supabase):
        """Test updating action item with task info"""
        action_item_id = uuid4()
        task_platform = "monday"
        task_id = "item_123"
        task_url = "https://monday.com/boards/123/pulses/456"

        # Mock Supabase update chain
        mock_table = Mock()
        mock_update = Mock()
        mock_eq = Mock()
        mock_supabase.table.return_value = mock_table
        mock_table.update.return_value = mock_update
        mock_update.eq.return_value = mock_eq
        mock_eq.execute.return_value = None

        await routing_service._update_action_item_task_info(
            action_item_id,
            task_platform,
            task_id,
            task_url
        )

        mock_supabase.table.assert_called_once_with("action_items")
        # Verify update was called with correct data
        update_call_args = mock_table.update.call_args[0][0]
        assert update_call_args["task_platform"] == task_platform
        assert update_call_args["task_id"] == task_id
        assert update_call_args["task_url"] == task_url

    @pytest.mark.asyncio
    async def test_update_action_item_without_supabase(self, sample_action_item):
        """Test update gracefully handles no Supabase client"""
        service = TaskRoutingService()  # No Supabase

        # Should not raise error
        await service._update_action_item_task_info(
            sample_action_item.id,
            "monday",
            "item_123",
            "https://example.com"
        )

    @pytest.mark.asyncio
    async def test_get_meeting_action_items(self, routing_service, mock_supabase):
        """Test fetching action items for a meeting"""
        meeting_id = uuid4()

        # Mock Supabase query chain
        mock_table = Mock()
        mock_select = Mock()
        mock_eq = Mock()
        mock_result = Mock()
        mock_result.data = [
            {
                "id": str(uuid4()),
                "meeting_id": str(meeting_id),
                "workspace_id": str(uuid4()),
                "description": "Test action",
                "priority": "normal",
                "confidence_score": 0.9,
                "created_at": datetime.utcnow().isoformat()
            }
        ]

        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value = mock_select
        mock_select.eq.return_value = mock_eq
        mock_eq.execute.return_value = mock_result

        action_items = await routing_service._get_meeting_action_items(meeting_id)

        assert len(action_items) == 1
        assert isinstance(action_items[0], ActionItem)
        mock_supabase.table.assert_called_once_with("action_items")
