"""
Comprehensive Tests for Briefing Scheduler Background Task
Tests daily briefing generation and delivery
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock, call
from datetime import datetime, time
from uuid import uuid4

from app.tasks.briefing_scheduler import BriefingSchedulerJob
from app.models.briefing import BriefingType, DeliveryChannel


@pytest.fixture
def mock_supabase():
    """Mock Supabase client"""
    mock = Mock()
    mock.table = Mock(return_value=mock)
    mock.select = Mock(return_value=mock)
    mock.eq = Mock(return_value=mock)
    mock.update = Mock(return_value=mock)
    mock.insert = Mock(return_value=mock)
    mock.execute = Mock(return_value=Mock(data=[]))
    return mock


@pytest.fixture
def mock_briefing_service():
    """Mock BriefingService"""
    service = Mock()
    service.generate_briefing = AsyncMock(return_value=Mock(id=uuid4()))
    return service


@pytest.fixture
def scheduler_job(mock_supabase, mock_briefing_service):
    """Create BriefingSchedulerJob with mocked dependencies"""
    with patch('app.tasks.briefing_scheduler.get_supabase_client', return_value=mock_supabase):
        with patch('app.tasks.briefing_scheduler.BriefingService', return_value=mock_briefing_service):
            job = BriefingSchedulerJob()
            return job


@pytest.fixture
def mock_schedules():
    """Mock briefing schedules"""
    return [
        {
            "id": str(uuid4()),
            "workspace_id": str(uuid4()),
            "founder_id": str(uuid4()),
            "briefing_type": BriefingType.MORNING.value,
            "enabled": True,
            "delivery_channels": [DeliveryChannel.IN_APP.value]
        },
        {
            "id": str(uuid4()),
            "workspace_id": str(uuid4()),
            "founder_id": str(uuid4()),
            "briefing_type": BriefingType.MORNING.value,
            "enabled": True,
            "delivery_channels": [DeliveryChannel.EMAIL.value, DeliveryChannel.SLACK.value]
        }
    ]


# ==================== Morning Briefs Tests ====================

@pytest.mark.asyncio
async def test_generate_morning_briefs_success(scheduler_job, mock_schedules):
    """Test successful morning brief generation for multiple founders"""
    scheduler_job.supabase.execute.return_value = Mock(data=mock_schedules)

    await scheduler_job.generate_morning_briefs()

    # Verify service called for each schedule
    assert scheduler_job.briefing_service.generate_briefing.call_count == 2

    # Verify correct parameters passed
    calls = scheduler_job.briefing_service.generate_briefing.call_args_list
    for i, call_args in enumerate(calls):
        assert call_args[1]["workspace_id"] == mock_schedules[i]["workspace_id"]
        assert call_args[1]["founder_id"] == mock_schedules[i]["founder_id"]
        assert call_args[1]["briefing_type"] == BriefingType.MORNING


@pytest.mark.asyncio
async def test_generate_morning_briefs_no_schedules(scheduler_job):
    """Test morning brief generation when no schedules exist"""
    scheduler_job.supabase.execute.return_value = Mock(data=[])

    await scheduler_job.generate_morning_briefs()

    # Verify no briefings generated
    scheduler_job.briefing_service.generate_briefing.assert_not_called()


@pytest.mark.asyncio
async def test_generate_morning_briefs_with_delivery_failure(scheduler_job, mock_schedules):
    """Test handling of delivery failures during morning brief generation"""
    scheduler_job.supabase.execute.return_value = Mock(data=mock_schedules[:1])

    # Mock delivery failure
    with patch.object(scheduler_job, '_deliver_briefing', side_effect=Exception("Delivery failed")):
        await scheduler_job.generate_morning_briefs()

    # Should still generate briefing despite delivery failure
    scheduler_job.briefing_service.generate_briefing.assert_called_once()


@pytest.mark.asyncio
async def test_generate_morning_briefs_service_error(scheduler_job, mock_schedules):
    """Test handling of service errors during morning brief generation"""
    scheduler_job.supabase.execute.return_value = Mock(data=mock_schedules)
    scheduler_job.briefing_service.generate_briefing.side_effect = Exception("Service error")

    # Should not raise exception
    await scheduler_job.generate_morning_briefs()

    # Verify service was called despite errors
    assert scheduler_job.briefing_service.generate_briefing.call_count == 2


@pytest.mark.asyncio
async def test_generate_morning_briefs_database_error(scheduler_job):
    """Test handling of database errors"""
    scheduler_job.supabase.execute.side_effect = Exception("Database error")

    # Should not raise exception
    await scheduler_job.generate_morning_briefs()


# ==================== Evening Wraps Tests ====================

@pytest.mark.asyncio
async def test_generate_evening_wraps_success(scheduler_job, mock_schedules):
    """Test successful evening wrap generation"""
    evening_schedules = [
        {**schedule, "briefing_type": BriefingType.EVENING.value}
        for schedule in mock_schedules
    ]
    scheduler_job.supabase.execute.return_value = Mock(data=evening_schedules)

    await scheduler_job.generate_evening_wraps()

    # Verify service called for each schedule
    assert scheduler_job.briefing_service.generate_briefing.call_count == 2

    # Verify correct briefing type
    calls = scheduler_job.briefing_service.generate_briefing.call_args_list
    for call_args in calls:
        assert call_args[1]["briefing_type"] == BriefingType.EVENING


@pytest.mark.asyncio
async def test_generate_evening_wraps_no_schedules(scheduler_job):
    """Test evening wrap generation when no schedules exist"""
    scheduler_job.supabase.execute.return_value = Mock(data=[])

    await scheduler_job.generate_evening_wraps()

    scheduler_job.briefing_service.generate_briefing.assert_not_called()


@pytest.mark.asyncio
async def test_generate_evening_wraps_partial_success(scheduler_job, mock_schedules):
    """Test evening wrap generation with partial failures"""
    evening_schedules = [
        {**schedule, "briefing_type": BriefingType.EVENING.value}
        for schedule in mock_schedules
    ]
    scheduler_job.supabase.execute.return_value = Mock(data=evening_schedules)

    # First call succeeds, second fails
    scheduler_job.briefing_service.generate_briefing.side_effect = [
        Mock(id=uuid4()),
        Exception("Generation failed")
    ]

    await scheduler_job.generate_evening_wraps()

    # Should call service for both despite failure
    assert scheduler_job.briefing_service.generate_briefing.call_count == 2


# ==================== Investor Summaries Tests ====================

@pytest.mark.asyncio
async def test_generate_weekly_investor_summaries_success(scheduler_job, mock_schedules):
    """Test successful investor summary generation on Sunday"""
    investor_schedules = [
        {**schedule, "briefing_type": BriefingType.INVESTOR.value,
         "delivery_channels": [DeliveryChannel.EMAIL.value]}
        for schedule in mock_schedules
    ]
    scheduler_job.supabase.execute.return_value = Mock(data=investor_schedules)

    # Mock Sunday (weekday = 6)
    with patch('app.tasks.briefing_scheduler.datetime') as mock_datetime:
        mock_datetime.now.return_value = Mock(weekday=Mock(return_value=6))
        mock_datetime.utcnow.return_value = datetime.utcnow()

        await scheduler_job.generate_weekly_investor_summaries()

    # Verify service called
    assert scheduler_job.briefing_service.generate_briefing.call_count == 2


@pytest.mark.asyncio
async def test_generate_weekly_investor_summaries_not_sunday(scheduler_job):
    """Test investor summary skipped when not Sunday"""
    # Mock Monday (weekday = 0)
    with patch('app.tasks.briefing_scheduler.datetime') as mock_datetime:
        mock_datetime.now.return_value = Mock(weekday=Mock(return_value=0))

        await scheduler_job.generate_weekly_investor_summaries()

    # Should not generate briefings
    scheduler_job.briefing_service.generate_briefing.assert_not_called()


@pytest.mark.asyncio
async def test_generate_weekly_investor_summaries_no_schedules(scheduler_job):
    """Test investor summary generation when no schedules exist"""
    scheduler_job.supabase.execute.return_value = Mock(data=[])

    with patch('app.tasks.briefing_scheduler.datetime') as mock_datetime:
        mock_datetime.now.return_value = Mock(weekday=Mock(return_value=6))
        mock_datetime.utcnow.return_value = datetime.utcnow()

        await scheduler_job.generate_weekly_investor_summaries()

    scheduler_job.briefing_service.generate_briefing.assert_not_called()


# ==================== Delivery Tests ====================

@pytest.mark.asyncio
async def test_deliver_briefing_email(scheduler_job):
    """Test briefing delivery via email"""
    briefing = Mock(id=uuid4())
    channels = [DeliveryChannel.EMAIL.value]

    with patch.object(scheduler_job, '_send_email', new_callable=AsyncMock) as mock_email:
        await scheduler_job._deliver_briefing(briefing, channels)

    mock_email.assert_called_once_with(briefing)

    # Verify status update
    scheduler_job.supabase.table.assert_called_with("briefings")


@pytest.mark.asyncio
async def test_deliver_briefing_slack(scheduler_job):
    """Test briefing delivery via Slack"""
    briefing = Mock(id=uuid4())
    channels = [DeliveryChannel.SLACK.value]

    with patch.object(scheduler_job, '_send_slack', new_callable=AsyncMock) as mock_slack:
        await scheduler_job._deliver_briefing(briefing, channels)

    mock_slack.assert_called_once_with(briefing)


@pytest.mark.asyncio
async def test_deliver_briefing_discord(scheduler_job):
    """Test briefing delivery via Discord"""
    briefing = Mock(id=uuid4())
    channels = [DeliveryChannel.DISCORD.value]

    with patch.object(scheduler_job, '_send_discord', new_callable=AsyncMock) as mock_discord:
        await scheduler_job._deliver_briefing(briefing, channels)

    mock_discord.assert_called_once_with(briefing)


@pytest.mark.asyncio
async def test_deliver_briefing_multiple_channels(scheduler_job):
    """Test briefing delivery via multiple channels"""
    briefing = Mock(id=uuid4())
    channels = [DeliveryChannel.EMAIL.value, DeliveryChannel.SLACK.value, DeliveryChannel.DISCORD.value]

    with patch.object(scheduler_job, '_send_email', new_callable=AsyncMock) as mock_email, \
         patch.object(scheduler_job, '_send_slack', new_callable=AsyncMock) as mock_slack, \
         patch.object(scheduler_job, '_send_discord', new_callable=AsyncMock) as mock_discord:

        await scheduler_job._deliver_briefing(briefing, channels)

    mock_email.assert_called_once()
    mock_slack.assert_called_once()
    mock_discord.assert_called_once()


@pytest.mark.asyncio
async def test_deliver_briefing_in_app_only(scheduler_job):
    """Test briefing delivery for in-app only (no external delivery)"""
    briefing = Mock(id=uuid4())
    channels = [DeliveryChannel.IN_APP.value]

    with patch.object(scheduler_job, '_send_email', new_callable=AsyncMock) as mock_email:
        await scheduler_job._deliver_briefing(briefing, channels)

    # Should not send external messages for in-app only
    mock_email.assert_not_called()


@pytest.mark.asyncio
async def test_deliver_briefing_channel_failure(scheduler_job):
    """Test handling of channel delivery failures"""
    briefing = Mock(id=uuid4())
    channels = [DeliveryChannel.EMAIL.value, DeliveryChannel.SLACK.value]

    with patch.object(scheduler_job, '_send_email', side_effect=Exception("Email failed")), \
         patch.object(scheduler_job, '_send_slack', new_callable=AsyncMock) as mock_slack:

        # Should not raise exception
        await scheduler_job._deliver_briefing(briefing, channels)

        # Should still try other channels
        mock_slack.assert_called_once()


# ==================== Scheduler Control Tests ====================

def test_start_scheduler():
    """Test scheduler startup"""
    with patch('app.tasks.briefing_scheduler.get_supabase_client'), \
         patch('app.tasks.briefing_scheduler.BriefingService'), \
         patch('app.tasks.briefing_scheduler.AsyncIOScheduler') as mock_scheduler_class:

        mock_scheduler = Mock()
        mock_scheduler_class.return_value = mock_scheduler

        job = BriefingSchedulerJob()
        job.start()

        # Verify jobs added
        assert mock_scheduler.add_job.call_count == 3

        # Verify job IDs
        job_ids = [call[1]["id"] for call in mock_scheduler.add_job.call_args_list]
        assert "morning_briefs" in job_ids
        assert "evening_wraps" in job_ids
        assert "investor_summaries" in job_ids

        # Verify scheduler started
        mock_scheduler.start.assert_called_once()


def test_stop_scheduler():
    """Test scheduler shutdown"""
    with patch('app.tasks.briefing_scheduler.get_supabase_client'), \
         patch('app.tasks.briefing_scheduler.BriefingService'), \
         patch('app.tasks.briefing_scheduler.AsyncIOScheduler') as mock_scheduler_class:

        mock_scheduler = Mock()
        mock_scheduler_class.return_value = mock_scheduler

        job = BriefingSchedulerJob()
        job.stop()

        # Verify scheduler stopped
        mock_scheduler.shutdown.assert_called_once()


# ==================== Edge Cases ====================

@pytest.mark.asyncio
async def test_generate_briefing_returns_none(scheduler_job, mock_schedules):
    """Test handling when briefing generation returns None"""
    scheduler_job.supabase.execute.return_value = Mock(data=mock_schedules[:1])
    scheduler_job.briefing_service.generate_briefing.return_value = None

    with patch.object(scheduler_job, '_deliver_briefing', new_callable=AsyncMock) as mock_deliver:
        await scheduler_job.generate_morning_briefs()

    # Should not attempt delivery when briefing is None
    mock_deliver.assert_not_called()


@pytest.mark.asyncio
async def test_missing_delivery_channels_default(scheduler_job):
    """Test default delivery channel when not specified"""
    schedule = {
        "id": str(uuid4()),
        "workspace_id": str(uuid4()),
        "founder_id": str(uuid4()),
        "briefing_type": BriefingType.MORNING.value,
        "enabled": True
        # No delivery_channels specified
    }
    scheduler_job.supabase.execute.return_value = Mock(data=[schedule])

    await scheduler_job.generate_morning_briefs()

    # Should still generate briefing with default channel
    scheduler_job.briefing_service.generate_briefing.assert_called_once()
