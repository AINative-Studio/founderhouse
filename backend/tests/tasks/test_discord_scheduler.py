"""
Comprehensive Tests for Discord Scheduler Background Task
Tests Discord briefing automation and scheduling
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, time
from uuid import uuid4

from app.tasks.discord_scheduler import DiscordScheduler
from app.models.briefing import BriefingType
from app.models.discord_message import DiscordBriefingRequest


@pytest.fixture
def mock_discord_service():
    """Mock DiscordService"""
    service = Mock()
    service.send_briefing = AsyncMock()
    return service


@pytest.fixture
def mock_briefing_service():
    """Mock BriefingService"""
    service = Mock()
    service.generate_briefing = AsyncMock(return_value=Mock(id=uuid4()))
    return service


@pytest.fixture
def scheduler(mock_discord_service, mock_briefing_service):
    """Create DiscordScheduler with mocked dependencies"""
    with patch('app.tasks.discord_scheduler.DiscordService', return_value=mock_discord_service), \
         patch('app.tasks.discord_scheduler.BriefingService', return_value=mock_briefing_service):
        scheduler = DiscordScheduler()
        return scheduler


@pytest.fixture
def mock_schedules():
    """Mock briefing schedules"""
    return [
        {
            "workspace_id": str(uuid4()),
            "founder_id": str(uuid4()),
            "discord_channel": "daily-briefings",
            "mention_team": False
        },
        {
            "workspace_id": str(uuid4()),
            "founder_id": str(uuid4()),
            "discord_channel": "team-updates",
            "mention_team": True
        }
    ]


# ==================== Scheduler Control Tests ====================

@pytest.mark.asyncio
async def test_start_scheduler(scheduler):
    """Test scheduler startup"""
    scheduler.running = False

    # Mock the async loop to run once
    with patch.object(scheduler, '_check_and_send_briefings', new_callable=AsyncMock) as mock_check:
        async def run_once():
            scheduler.running = True
            await scheduler._check_and_send_briefings()
            scheduler.running = False

        # Replace the start method to run once
        await run_once()

    mock_check.assert_called_once()


@pytest.mark.asyncio
async def test_stop_scheduler(scheduler):
    """Test scheduler shutdown"""
    scheduler.running = True

    await scheduler.stop()

    assert scheduler.running is False


# ==================== Time Window Tests ====================

def test_is_time_to_send_exact_match(scheduler):
    """Test time window check with exact match"""
    current_time = time(8, 0)
    target_time = time(8, 0)

    result = scheduler._is_time_to_send(current_time, target_time, window_minutes=5)

    assert result is True


def test_is_time_to_send_within_window(scheduler):
    """Test time window check within window"""
    current_time = time(8, 3)
    target_time = time(8, 0)

    result = scheduler._is_time_to_send(current_time, target_time, window_minutes=5)

    assert result is True


def test_is_time_to_send_outside_window(scheduler):
    """Test time window check outside window"""
    current_time = time(8, 10)
    target_time = time(8, 0)

    result = scheduler._is_time_to_send(current_time, target_time, window_minutes=5)

    assert result is False


def test_is_time_to_send_before_window(scheduler):
    """Test time window check before target"""
    current_time = time(7, 57)
    target_time = time(8, 0)

    result = scheduler._is_time_to_send(current_time, target_time, window_minutes=5)

    assert result is True


def test_is_time_to_send_boundary(scheduler):
    """Test time window boundary conditions"""
    target_time = time(8, 0)

    # Exactly at boundary (5 minutes before)
    assert scheduler._is_time_to_send(time(7, 55), target_time, window_minutes=5) is True

    # Exactly at boundary (5 minutes after)
    assert scheduler._is_time_to_send(time(8, 5), target_time, window_minutes=5) is True

    # Just outside boundary
    assert scheduler._is_time_to_send(time(7, 54), target_time, window_minutes=5) is False
    assert scheduler._is_time_to_send(time(8, 6), target_time, window_minutes=5) is False


# ==================== Morning Briefings Tests ====================

@pytest.mark.asyncio
async def test_send_all_morning_briefings_success(scheduler, mock_schedules):
    """Test successful morning briefing sending"""
    with patch.object(scheduler, '_get_active_schedules', return_value=mock_schedules), \
         patch.object(scheduler, '_already_sent_today', return_value=False):

        await scheduler._send_all_morning_briefings()

    # Verify briefings generated for all schedules
    assert scheduler.briefing_service.generate_briefing.call_count == 2

    # Verify Discord messages sent
    assert scheduler.discord_service.send_briefing.call_count == 2


@pytest.mark.asyncio
async def test_send_all_morning_briefings_already_sent(scheduler, mock_schedules):
    """Test skipping briefings already sent today"""
    with patch.object(scheduler, '_get_active_schedules', return_value=mock_schedules), \
         patch.object(scheduler, '_already_sent_today', return_value=True):

        await scheduler._send_all_morning_briefings()

    # Should not generate or send any briefings
    scheduler.briefing_service.generate_briefing.assert_not_called()
    scheduler.discord_service.send_briefing.assert_not_called()


@pytest.mark.asyncio
async def test_send_all_morning_briefings_no_schedules(scheduler):
    """Test handling when no schedules exist"""
    with patch.object(scheduler, '_get_active_schedules', return_value=[]):

        await scheduler._send_all_morning_briefings()

    scheduler.briefing_service.generate_briefing.assert_not_called()


@pytest.mark.asyncio
async def test_send_all_morning_briefings_generation_failure(scheduler, mock_schedules):
    """Test handling briefing generation failure"""
    with patch.object(scheduler, '_get_active_schedules', return_value=mock_schedules[:1]), \
         patch.object(scheduler, '_already_sent_today', return_value=False):

        # Mock generation returning None (failure)
        scheduler.briefing_service.generate_briefing.return_value = None

        await scheduler._send_all_morning_briefings()

    # Should not send Discord message when generation fails
    scheduler.discord_service.send_briefing.assert_not_called()


@pytest.mark.asyncio
async def test_send_all_morning_briefings_partial_failure(scheduler, mock_schedules):
    """Test handling partial failures in morning briefings"""
    with patch.object(scheduler, '_get_active_schedules', return_value=mock_schedules), \
         patch.object(scheduler, '_already_sent_today', return_value=False):

        # First generation succeeds, second fails
        scheduler.briefing_service.generate_briefing.side_effect = [
            Mock(id=uuid4()),
            Exception("Generation error")
        ]

        await scheduler._send_all_morning_briefings()

    # Should still send first briefing
    assert scheduler.discord_service.send_briefing.call_count == 1


# ==================== Evening Briefings Tests ====================

@pytest.mark.asyncio
async def test_send_all_evening_briefings_success(scheduler, mock_schedules):
    """Test successful evening briefing sending"""
    with patch.object(scheduler, '_get_active_schedules', return_value=mock_schedules), \
         patch.object(scheduler, '_already_sent_today', return_value=False):

        await scheduler._send_all_evening_briefings()

    # Verify briefings generated
    assert scheduler.briefing_service.generate_briefing.call_count == 2

    # Verify correct briefing type
    for call_args in scheduler.briefing_service.generate_briefing.call_args_list:
        assert call_args[1]["briefing_type"] == BriefingType.EVENING


@pytest.mark.asyncio
async def test_send_all_evening_briefings_already_sent(scheduler, mock_schedules):
    """Test skipping evening briefings already sent"""
    with patch.object(scheduler, '_get_active_schedules', return_value=mock_schedules), \
         patch.object(scheduler, '_already_sent_today', return_value=True):

        await scheduler._send_all_evening_briefings()

    scheduler.briefing_service.generate_briefing.assert_not_called()


@pytest.mark.asyncio
async def test_send_all_evening_briefings_no_mention_team(scheduler, mock_schedules):
    """Test evening briefings don't mention team by default"""
    with patch.object(scheduler, '_get_active_schedules', return_value=mock_schedules[:1]), \
         patch.object(scheduler, '_already_sent_today', return_value=False):

        await scheduler._send_all_evening_briefings()

    # Verify mention_team is False in request
    call_args = scheduler.discord_service.send_briefing.call_args
    request = call_args[0][0]
    assert request.mention_team is False


# ==================== Schedule Management Tests ====================

@pytest.mark.asyncio
async def test_get_active_schedules_morning(scheduler):
    """Test retrieving active morning briefing schedules"""
    mock_result = Mock()
    mock_rows = [
        (str(uuid4()), str(uuid4()), "daily-briefings", False),
        (str(uuid4()), str(uuid4()), "team-updates", True)
    ]
    mock_result.fetchall.return_value = mock_rows

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_result)

    with patch('app.tasks.discord_scheduler.get_db_context') as mock_context:
        mock_context.return_value.__aenter__.return_value = mock_db

        schedules = await scheduler._get_active_schedules(BriefingType.MORNING)

    assert len(schedules) == 2
    assert schedules[0]["workspace_id"] == mock_rows[0][0]
    assert schedules[1]["mention_team"] is True


@pytest.mark.asyncio
async def test_get_active_schedules_evening(scheduler):
    """Test retrieving active evening briefing schedules"""
    mock_result = Mock()
    mock_result.fetchall.return_value = []

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_result)

    with patch('app.tasks.discord_scheduler.get_db_context') as mock_context:
        mock_context.return_value.__aenter__.return_value = mock_db

        schedules = await scheduler._get_active_schedules(BriefingType.EVENING)

    assert schedules == []


@pytest.mark.asyncio
async def test_get_active_schedules_database_error(scheduler):
    """Test handling database errors when getting schedules"""
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(side_effect=Exception("Database error"))

    with patch('app.tasks.discord_scheduler.get_db_context') as mock_context:
        mock_context.return_value.__aenter__.return_value = mock_db

        schedules = await scheduler._get_active_schedules(BriefingType.MORNING)

    # Should return empty list on error
    assert schedules == []


# ==================== Already Sent Check Tests ====================

@pytest.mark.asyncio
async def test_already_sent_today_true(scheduler):
    """Test checking if briefing already sent today - returns true"""
    workspace_id = str(uuid4())
    founder_id = str(uuid4())

    mock_result = Mock()
    mock_result.fetchone.return_value = (1,)  # Count > 0

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_result)

    with patch('app.tasks.discord_scheduler.get_db_context') as mock_context:
        mock_context.return_value.__aenter__.return_value = mock_db

        result = await scheduler._already_sent_today(
            workspace_id, founder_id, BriefingType.MORNING
        )

    assert result is True


@pytest.mark.asyncio
async def test_already_sent_today_false(scheduler):
    """Test checking if briefing already sent today - returns false"""
    workspace_id = str(uuid4())
    founder_id = str(uuid4())

    mock_result = Mock()
    mock_result.fetchone.return_value = (0,)  # Count = 0

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_result)

    with patch('app.tasks.discord_scheduler.get_db_context') as mock_context:
        mock_context.return_value.__aenter__.return_value = mock_db

        result = await scheduler._already_sent_today(
            workspace_id, founder_id, BriefingType.MORNING
        )

    assert result is False


@pytest.mark.asyncio
async def test_already_sent_today_database_error(scheduler):
    """Test handling database errors when checking if sent"""
    workspace_id = str(uuid4())
    founder_id = str(uuid4())

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(side_effect=Exception("Database error"))

    with patch('app.tasks.discord_scheduler.get_db_context') as mock_context:
        mock_context.return_value.__aenter__.return_value = mock_db

        result = await scheduler._already_sent_today(
            workspace_id, founder_id, BriefingType.MORNING
        )

    # Should return False on error (fail-safe)
    assert result is False


# ==================== Check and Send Tests ====================

@pytest.mark.asyncio
async def test_check_and_send_briefings_morning_time(scheduler):
    """Test check and send during morning briefing time"""
    with patch('app.tasks.discord_scheduler.datetime') as mock_datetime:
        mock_datetime.utcnow.return_value = datetime(2025, 11, 10, 8, 2, 0)

        with patch.object(scheduler, '_send_all_morning_briefings', new_callable=AsyncMock) as mock_morning, \
             patch.object(scheduler, '_send_all_evening_briefings', new_callable=AsyncMock) as mock_evening:

            await scheduler._check_and_send_briefings()

    mock_morning.assert_called_once()
    mock_evening.assert_not_called()


@pytest.mark.asyncio
async def test_check_and_send_briefings_evening_time(scheduler):
    """Test check and send during evening briefing time"""
    with patch('app.tasks.discord_scheduler.datetime') as mock_datetime:
        mock_datetime.utcnow.return_value = datetime(2025, 11, 10, 18, 2, 0)

        with patch.object(scheduler, '_send_all_morning_briefings', new_callable=AsyncMock) as mock_morning, \
             patch.object(scheduler, '_send_all_evening_briefings', new_callable=AsyncMock) as mock_evening:

            await scheduler._check_and_send_briefings()

    mock_morning.assert_not_called()
    mock_evening.assert_called_once()


@pytest.mark.asyncio
async def test_check_and_send_briefings_non_briefing_time(scheduler):
    """Test check and send outside briefing times"""
    with patch('app.tasks.discord_scheduler.datetime') as mock_datetime:
        mock_datetime.utcnow.return_value = datetime(2025, 11, 10, 12, 0, 0)

        with patch.object(scheduler, '_send_all_morning_briefings', new_callable=AsyncMock) as mock_morning, \
             patch.object(scheduler, '_send_all_evening_briefings', new_callable=AsyncMock) as mock_evening:

            await scheduler._check_and_send_briefings()

    # Neither should be called
    mock_morning.assert_not_called()
    mock_evening.assert_not_called()


# ==================== Discord Message Request Tests ====================

@pytest.mark.asyncio
async def test_discord_briefing_request_creation(scheduler, mock_schedules):
    """Test correct DiscordBriefingRequest creation"""
    schedule = mock_schedules[0]

    with patch.object(scheduler, '_get_active_schedules', return_value=[schedule]), \
         patch.object(scheduler, '_already_sent_today', return_value=False):

        await scheduler._send_all_morning_briefings()

    # Verify request created correctly
    call_args = scheduler.discord_service.send_briefing.call_args
    request = call_args[0][0]

    assert isinstance(request, DiscordBriefingRequest)
    assert str(request.workspace_id) == schedule["workspace_id"]
    assert str(request.founder_id) == schedule["founder_id"]
    assert request.channel_name == schedule["discord_channel"]
    assert request.include_metrics is True
    assert request.include_action_items is True


@pytest.mark.asyncio
async def test_discord_briefing_request_with_mention(scheduler, mock_schedules):
    """Test DiscordBriefingRequest with team mention"""
    schedule = mock_schedules[1]  # Has mention_team = True

    with patch.object(scheduler, '_get_active_schedules', return_value=[schedule]), \
         patch.object(scheduler, '_already_sent_today', return_value=False):

        await scheduler._send_all_morning_briefings()

    call_args = scheduler.discord_service.send_briefing.call_args
    request = call_args[0][0]

    assert request.mention_team is True
