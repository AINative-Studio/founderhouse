"""
Comprehensive tests for BriefingService
Tests briefing generation for morning briefs, evening wraps, and investor summaries
"""
import pytest
from uuid import uuid4
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.briefing_service import BriefingService
from app.models.briefing import BriefingType, BriefingStatus


@pytest.fixture
def mock_supabase():
    """Mock Supabase client"""
    client = MagicMock()

    # Mock table operations
    table_mock = MagicMock()

    # Mock insert
    insert_result = MagicMock()
    insert_result.execute.return_value.data = [{
        "id": str(uuid4()),
        "workspace_id": str(uuid4()),
        "briefing_type": "morning",
        "title": "Morning Brief",
        "status": "completed"
    }]
    table_mock.insert.return_value = insert_result

    # Mock select (for founder data)
    select_result = MagicMock()
    select_result.single.return_value.execute.return_value.data = {
        "id": str(uuid4()),
        "display_name": "John Founder",
        "email": "john@startup.com"
    }
    table_mock.select.return_value = select_result

    client.table.return_value = table_mock
    yield client


@pytest.fixture
def briefing_service(mock_supabase):
    """Create BriefingService instance"""
    with patch('app.services.briefing_service.get_supabase_client', return_value=mock_supabase):
        return BriefingService()


class TestGenerateMorningBrief:
    """Tests for morning brief generation"""

    @pytest.mark.asyncio
    async def test_generate_morning_brief_success(self, briefing_service, mock_supabase):
        """Test successful morning brief generation"""
        # Arrange
        workspace_id = uuid4()
        founder_id = uuid4()

        # Mock helper methods
        with patch.object(briefing_service, '_get_founder', return_value={"display_name": "John"}):
            with patch.object(briefing_service, '_get_today_schedule', return_value=[]):
                with patch.object(briefing_service, '_get_overnight_updates', return_value=[]):
                    with patch.object(briefing_service, '_get_kpi_snapshot', return_value={}):
                        with patch.object(briefing_service, '_get_urgent_items', return_value=[]):
                            with patch.object(briefing_service, '_get_top_recommendations', return_value=[]):
                                with patch.object(briefing_service, '_get_unread_summary', return_value={}):
                                    # Act
                                    result = await briefing_service.generate_briefing(
                                        workspace_id=workspace_id,
                                        founder_id=founder_id,
                                        briefing_type=BriefingType.MORNING
                                    )

        # Assert
        assert result is not None
        assert "Morning Brief" in result.title
        assert len(result.sections) > 0

    @pytest.mark.asyncio
    async def test_morning_brief_includes_schedule(self, briefing_service, mock_supabase):
        """Test morning brief includes today's schedule"""
        # Arrange
        workspace_id = uuid4()
        founder_id = uuid4()
        schedule = [
            {"time": "9:00 AM", "title": "Team Standup"},
            {"time": "2:00 PM", "title": "Investor Call"}
        ]

        # Mock methods
        with patch.object(briefing_service, '_get_founder', return_value={"display_name": "John"}):
            with patch.object(briefing_service, '_get_today_schedule', return_value=schedule):
                with patch.object(briefing_service, '_get_overnight_updates', return_value=[]):
                    with patch.object(briefing_service, '_get_kpi_snapshot', return_value={}):
                        with patch.object(briefing_service, '_get_urgent_items', return_value=[]):
                            with patch.object(briefing_service, '_get_top_recommendations', return_value=[]):
                                with patch.object(briefing_service, '_get_unread_summary', return_value={}):
                                    # Act
                                    result = await briefing_service.generate_briefing(
                                        workspace_id=workspace_id,
                                        founder_id=founder_id,
                                        briefing_type=BriefingType.MORNING
                                    )

        # Assert
        schedule_section = next((s for s in result.sections if s.section_type == "schedule"), None)
        assert schedule_section is not None
        assert schedule_section.title == "Today's Schedule"

    @pytest.mark.asyncio
    async def test_morning_brief_includes_urgent_items(self, briefing_service, mock_supabase):
        """Test morning brief includes urgent items"""
        # Arrange
        workspace_id = uuid4()
        founder_id = uuid4()
        urgent_items = [
            {"description": "Critical bug fix needed", "priority": "urgent"},
            {"description": "Investor follow-up required", "priority": "high"}
        ]

        # Mock methods
        with patch.object(briefing_service, '_get_founder', return_value={"display_name": "John"}):
            with patch.object(briefing_service, '_get_today_schedule', return_value=[]):
                with patch.object(briefing_service, '_get_overnight_updates', return_value=[]):
                    with patch.object(briefing_service, '_get_kpi_snapshot', return_value={}):
                        with patch.object(briefing_service, '_get_urgent_items', return_value=urgent_items):
                            with patch.object(briefing_service, '_get_top_recommendations', return_value=[]):
                                with patch.object(briefing_service, '_get_unread_summary', return_value={}):
                                    # Act
                                    result = await briefing_service.generate_briefing(
                                        workspace_id=workspace_id,
                                        founder_id=founder_id,
                                        briefing_type=BriefingType.MORNING
                                    )

        # Assert
        urgent_section = next((s for s in result.sections if s.section_type == "urgent"), None)
        assert urgent_section is not None
        assert urgent_section.importance == 5


class TestGenerateEveningWrap:
    """Tests for evening wrap generation"""

    @pytest.mark.asyncio
    async def test_generate_evening_wrap_success(self, briefing_service, mock_supabase):
        """Test successful evening wrap generation"""
        # Arrange
        workspace_id = uuid4()
        founder_id = uuid4()

        # Mock helper methods
        with patch.object(briefing_service, '_get_founder', return_value={"display_name": "John"}):
            with patch.object(briefing_service, '_get_meetings_today', return_value=[]):
                with patch.object(briefing_service, '_get_completed_tasks', return_value=[]):
                    with patch.object(briefing_service, '_get_pending_tasks', return_value=[]):
                        with patch.object(briefing_service, '_get_kpi_changes', return_value={}):
                            with patch.object(briefing_service, '_get_new_insights', return_value=[]):
                                with patch.object(briefing_service, '_get_tomorrow_preview', return_value={}):
                                    # Act
                                    result = await briefing_service.generate_briefing(
                                        workspace_id=workspace_id,
                                        founder_id=founder_id,
                                        briefing_type=BriefingType.EVENING
                                    )

        # Assert
        assert result is not None
        assert "Evening Wrap" in result.title
        assert len(result.sections) > 0

    @pytest.mark.asyncio
    async def test_evening_wrap_includes_meetings(self, briefing_service, mock_supabase):
        """Test evening wrap includes today's meetings"""
        # Arrange
        workspace_id = uuid4()
        founder_id = uuid4()
        meetings = [
            {"title": "Team Standup", "duration": 15},
            {"title": "Product Review", "duration": 60}
        ]

        # Mock methods
        with patch.object(briefing_service, '_get_founder', return_value={"display_name": "John"}):
            with patch.object(briefing_service, '_get_meetings_today', return_value=meetings):
                with patch.object(briefing_service, '_get_completed_tasks', return_value=[]):
                    with patch.object(briefing_service, '_get_pending_tasks', return_value=[]):
                        with patch.object(briefing_service, '_get_kpi_changes', return_value={}):
                            with patch.object(briefing_service, '_get_new_insights', return_value=[]):
                                with patch.object(briefing_service, '_get_tomorrow_preview', return_value={}):
                                    # Act
                                    result = await briefing_service.generate_briefing(
                                        workspace_id=workspace_id,
                                        founder_id=founder_id,
                                        briefing_type=BriefingType.EVENING
                                    )

        # Assert
        meetings_section = next((s for s in result.sections if s.section_type == "meetings"), None)
        assert meetings_section is not None

    @pytest.mark.asyncio
    async def test_evening_wrap_includes_tasks(self, briefing_service, mock_supabase):
        """Test evening wrap includes completed and pending tasks"""
        # Arrange
        workspace_id = uuid4()
        founder_id = uuid4()
        completed_tasks = [
            {"description": "Complete feature X", "completed_at": datetime.utcnow()},
            {"description": "Review PR", "completed_at": datetime.utcnow()}
        ]
        pending_tasks = [
            {"description": "Deploy to production", "due_date": datetime.utcnow() + timedelta(days=1)}
        ]

        # Mock methods
        with patch.object(briefing_service, '_get_founder', return_value={"display_name": "John"}):
            with patch.object(briefing_service, '_get_meetings_today', return_value=[]):
                with patch.object(briefing_service, '_get_completed_tasks', return_value=completed_tasks):
                    with patch.object(briefing_service, '_get_pending_tasks', return_value=pending_tasks):
                        with patch.object(briefing_service, '_get_kpi_changes', return_value={}):
                            with patch.object(briefing_service, '_get_new_insights', return_value=[]):
                                with patch.object(briefing_service, '_get_tomorrow_preview', return_value={}):
                                    # Act
                                    result = await briefing_service.generate_briefing(
                                        workspace_id=workspace_id,
                                        founder_id=founder_id,
                                        briefing_type=BriefingType.EVENING
                                    )

        # Assert
        tasks_section = next((s for s in result.sections if s.section_type == "tasks"), None)
        assert tasks_section is not None


class TestGenerateInvestorSummary:
    """Tests for investor summary generation"""

    @pytest.mark.asyncio
    async def test_generate_investor_summary_success(self, briefing_service, mock_supabase):
        """Test successful investor summary generation"""
        # Arrange
        workspace_id = uuid4()
        founder_id = uuid4()

        # Mock helper methods
        with patch.object(briefing_service, '_get_investor_metrics', return_value={}):
            with patch.object(briefing_service, '_get_growth_highlights', return_value=[]):
                with patch.object(briefing_service, '_get_challenges', return_value=[]):
                    with patch.object(briefing_service, '_get_financial_overview', return_value={}):
                        # Act
                        result = await briefing_service.generate_briefing(
                            workspace_id=workspace_id,
                            founder_id=founder_id,
                            briefing_type=BriefingType.INVESTOR
                        )

        # Assert
        assert result is not None
        assert "Weekly Update" in result.title
        assert len(result.sections) >= 2

    @pytest.mark.asyncio
    async def test_investor_summary_includes_metrics(self, briefing_service, mock_supabase):
        """Test investor summary includes key metrics"""
        # Arrange
        workspace_id = uuid4()
        founder_id = uuid4()
        metrics = {
            "mrr": {"value": 50000, "change": 10},
            "users": {"value": 1000, "change": 15},
            "churn": {"value": 2.5, "change": -0.5}
        }

        # Mock methods
        with patch.object(briefing_service, '_get_investor_metrics', return_value=metrics):
            with patch.object(briefing_service, '_get_growth_highlights', return_value=[]):
                with patch.object(briefing_service, '_get_challenges', return_value=[]):
                    with patch.object(briefing_service, '_get_financial_overview', return_value={}):
                        # Act
                        result = await briefing_service.generate_briefing(
                            workspace_id=workspace_id,
                            founder_id=founder_id,
                            briefing_type=BriefingType.INVESTOR
                        )

        # Assert
        metrics_section = next((s for s in result.sections if s.section_type == "metrics"), None)
        assert metrics_section is not None
        assert metrics_section.importance == 5

    @pytest.mark.asyncio
    async def test_investor_summary_includes_growth_highlights(self, briefing_service, mock_supabase):
        """Test investor summary includes growth highlights"""
        # Arrange
        workspace_id = uuid4()
        founder_id = uuid4()
        growth_highlights = [
            "Reached $50k MRR milestone",
            "Signed 3 enterprise customers",
            "Product featured in TechCrunch"
        ]

        # Mock methods
        with patch.object(briefing_service, '_get_investor_metrics', return_value={}):
            with patch.object(briefing_service, '_get_growth_highlights', return_value=growth_highlights):
                with patch.object(briefing_service, '_get_challenges', return_value=[]):
                    with patch.object(briefing_service, '_get_financial_overview', return_value={}):
                        # Act
                        result = await briefing_service.generate_briefing(
                            workspace_id=workspace_id,
                            founder_id=founder_id,
                            briefing_type=BriefingType.INVESTOR
                        )

        # Assert
        assert len(result.key_highlights) > 0


class TestBriefingDateRanges:
    """Tests for briefing date range handling"""

    @pytest.mark.asyncio
    async def test_morning_brief_default_date_range(self, briefing_service, mock_supabase):
        """Test morning brief uses correct default date range (yesterday to today)"""
        # Arrange
        workspace_id = uuid4()
        founder_id = uuid4()

        # Mock all helper methods
        with patch.object(briefing_service, '_get_founder', return_value={"display_name": "John"}):
            with patch.object(briefing_service, '_get_today_schedule', return_value=[]):
                with patch.object(briefing_service, '_get_overnight_updates', return_value=[]):
                    with patch.object(briefing_service, '_get_kpi_snapshot', return_value={}):
                        with patch.object(briefing_service, '_get_urgent_items', return_value=[]):
                            with patch.object(briefing_service, '_get_top_recommendations', return_value=[]):
                                with patch.object(briefing_service, '_get_unread_summary', return_value={}):
                                    # Act
                                    result = await briefing_service.generate_briefing(
                                        workspace_id=workspace_id,
                                        founder_id=founder_id,
                                        briefing_type=BriefingType.MORNING
                                    )

        # Assert
        assert result.start_date is not None
        assert result.end_date is not None
        assert (result.end_date - result.start_date).days <= 1

    @pytest.mark.asyncio
    async def test_investor_summary_default_date_range(self, briefing_service, mock_supabase):
        """Test investor summary uses correct default date range (7 days)"""
        # Arrange
        workspace_id = uuid4()
        founder_id = uuid4()

        # Mock all helper methods
        with patch.object(briefing_service, '_get_investor_metrics', return_value={}):
            with patch.object(briefing_service, '_get_growth_highlights', return_value=[]):
                with patch.object(briefing_service, '_get_challenges', return_value=[]):
                    with patch.object(briefing_service, '_get_financial_overview', return_value={}):
                        # Act
                        result = await briefing_service.generate_briefing(
                            workspace_id=workspace_id,
                            founder_id=founder_id,
                            briefing_type=BriefingType.INVESTOR
                        )

        # Assert
        assert result.start_date is not None
        assert result.end_date is not None
        assert (result.end_date - result.start_date).days == 7

    @pytest.mark.asyncio
    async def test_custom_date_range(self, briefing_service, mock_supabase):
        """Test briefing with custom date range"""
        # Arrange
        workspace_id = uuid4()
        founder_id = uuid4()
        start_date = datetime.utcnow() - timedelta(days=14)
        end_date = datetime.utcnow()

        # Mock all helper methods
        with patch.object(briefing_service, '_get_investor_metrics', return_value={}):
            with patch.object(briefing_service, '_get_growth_highlights', return_value=[]):
                with patch.object(briefing_service, '_get_challenges', return_value=[]):
                    with patch.object(briefing_service, '_get_financial_overview', return_value={}):
                        # Act
                        result = await briefing_service.generate_briefing(
                            workspace_id=workspace_id,
                            founder_id=founder_id,
                            briefing_type=BriefingType.INVESTOR,
                            start_date=start_date,
                            end_date=end_date
                        )

        # Assert
        assert result.start_date == start_date
        assert result.end_date == end_date


class TestFormattingMethods:
    """Tests for content formatting methods"""

    def test_format_schedule(self, briefing_service):
        """Test schedule formatting"""
        # Arrange
        schedule = [
            {"time": "9:00 AM", "title": "Team Standup"},
            {"time": "2:00 PM", "title": "Client Call"}
        ]

        # Act
        result = briefing_service._format_schedule(schedule)

        # Assert
        assert "9:00 AM" in result
        assert "Team Standup" in result

    def test_format_empty_schedule(self, briefing_service):
        """Test formatting empty schedule"""
        # Act
        result = briefing_service._format_schedule([])

        # Assert
        assert "No meetings scheduled" in result

    def test_extract_highlights(self, briefing_service):
        """Test highlight extraction"""
        # Arrange
        kpis = {"revenue": 50000}
        urgent = [
            {"description": "Critical bug"},
            {"description": "Important meeting"}
        ]

        # Act
        highlights = briefing_service._extract_highlights(kpis, urgent)

        # Assert
        assert len(highlights) > 0
        assert any("urgent" in h.lower() for h in highlights)

    def test_extract_actions(self, briefing_service):
        """Test action extraction"""
        # Arrange
        urgent = [
            {"description": "Fix production bug"},
            {"description": "Update documentation"}
        ]
        recs = []

        # Act
        actions = briefing_service._extract_actions(urgent, recs)

        # Assert
        assert len(actions) > 0


class TestErrorHandling:
    """Tests for error handling"""

    @pytest.mark.asyncio
    async def test_generate_briefing_with_database_error(self, briefing_service, mock_supabase):
        """Test briefing generation handles database errors gracefully"""
        # Arrange
        workspace_id = uuid4()
        founder_id = uuid4()

        # Mock database error
        mock_supabase.table.return_value.insert.side_effect = Exception("Database error")

        # Mock all helper methods
        with patch.object(briefing_service, '_get_founder', return_value={"display_name": "John"}):
            with patch.object(briefing_service, '_get_today_schedule', return_value=[]):
                with patch.object(briefing_service, '_get_overnight_updates', return_value=[]):
                    with patch.object(briefing_service, '_get_kpi_snapshot', return_value={}):
                        with patch.object(briefing_service, '_get_urgent_items', return_value=[]):
                            with patch.object(briefing_service, '_get_top_recommendations', return_value=[]):
                                with patch.object(briefing_service, '_get_unread_summary', return_value={}):
                                    # Act
                                    result = await briefing_service.generate_briefing(
                                        workspace_id=workspace_id,
                                        founder_id=founder_id,
                                        briefing_type=BriefingType.MORNING
                                    )

        # Assert - should return None on error
        assert result is None

    @pytest.mark.asyncio
    async def test_unsupported_briefing_type(self, briefing_service, mock_supabase):
        """Test handling of unsupported briefing type"""
        # Arrange
        workspace_id = uuid4()
        founder_id = uuid4()

        # Act & Assert - should raise ValueError
        with pytest.raises(ValueError):
            await briefing_service.generate_briefing(
                workspace_id=workspace_id,
                founder_id=founder_id,
                briefing_type="unsupported_type"  # type: ignore
            )
