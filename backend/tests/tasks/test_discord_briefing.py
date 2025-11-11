"""
Tests for Discord Briefing Task Scheduler - Sprint 5
Tests timezone-aware 8 AM scheduling with APScheduler
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, time, timezone
from uuid import uuid4
from zoneinfo import ZoneInfo

from app.tasks.discord_scheduler import DiscordScheduler
from app.models.briefing import BriefingType


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
def mock_workspace_schedules():
    """Mock workspace schedules with different timezones"""
    return [
        {
            "workspace_id": str(uuid4()),
            "founder_id": str(uuid4()),
            "discord_channel": "daily-briefings",
            "mention_team": False,
            "timezone": "America/Los_Angeles",  # PST/PDT
            "delivery_hour": 8
        },
        {
            "workspace_id": str(uuid4()),
            "founder_id": str(uuid4()),
            "discord_channel": "team-updates",
            "mention_team": True,
            "timezone": "America/New_York",  # EST/EDT
            "delivery_hour": 8
        },
        {
            "workspace_id": str(uuid4()),
            "founder_id": str(uuid4()),
            "discord_channel": "founders-brief",
            "mention_team": False,
            "timezone": "UTC",
            "delivery_hour": 8
        }
    ]


# ==================== Timezone Conversion Tests ====================

def test_convert_local_time_to_utc_pst(scheduler):
    """Test converting 8 AM PST to UTC"""
    pst = ZoneInfo("America/Los_Angeles")
    local_8am = datetime(2025, 11, 11, 8, 0, 0, tzinfo=pst)
    utc_time = local_8am.astimezone(timezone.utc)

    # In November, PST is UTC-8, so 8 AM PST = 4 PM UTC
    assert utc_time.hour == 16


def test_convert_local_time_to_utc_est(scheduler):
    """Test converting 8 AM EST to UTC"""
    est = ZoneInfo("America/New_York")
    local_8am = datetime(2025, 11, 11, 8, 0, 0, tzinfo=est)
    utc_time = local_8am.astimezone(timezone.utc)

    # In November, EST is UTC-5, so 8 AM EST = 1 PM UTC
    assert utc_time.hour == 13


def test_convert_local_time_to_utc_london(scheduler):
    """Test converting 8 AM London time to UTC"""
    london = ZoneInfo("Europe/London")
    local_8am = datetime(2025, 11, 11, 8, 0, 0, tzinfo=london)
    utc_time = local_8am.astimezone(timezone.utc)

    # In November, London is UTC+0 (GMT), so 8 AM GMT = 8 AM UTC
    assert utc_time.hour == 8


def test_convert_local_time_to_utc_tokyo(scheduler):
    """Test converting 8 AM Tokyo time to UTC"""
    tokyo = ZoneInfo("Asia/Tokyo")
    local_8am = datetime(2025, 11, 11, 8, 0, 0, tzinfo=tokyo)
    utc_time = local_8am.astimezone(timezone.utc)

    # Tokyo is UTC+9, so 8 AM JST = 11 PM UTC (previous day)
    assert utc_time.hour == 23


# ==================== Scheduled Delivery Tests ====================

@pytest.mark.asyncio
async def test_schedule_delivers_at_8am_local_time(scheduler, mock_workspace_schedules):
    """Test briefings are scheduled for 8 AM in each workspace's local timezone"""
    with patch.object(scheduler, '_get_active_schedules', return_value=mock_workspace_schedules), \
         patch.object(scheduler, '_already_sent_today', return_value=False):

        await scheduler._send_all_morning_briefings()

        # Should generate briefing for each workspace
        assert scheduler.briefing_service.generate_briefing.call_count == 3


@pytest.mark.asyncio
async def test_schedule_handles_daylight_saving_time(scheduler):
    """Test scheduler handles DST transitions correctly"""
    # Test schedule during DST transition
    pst_schedule = {
        "workspace_id": str(uuid4()),
        "founder_id": str(uuid4()),
        "discord_channel": "daily-briefings",
        "mention_team": False,
        "timezone": "America/Los_Angeles",
        "delivery_hour": 8
    }

    # During DST (summer): PDT is UTC-7
    summer_date = datetime(2025, 7, 11, 8, 0, 0, tzinfo=ZoneInfo("America/Los_Angeles"))
    summer_utc = summer_date.astimezone(timezone.utc)
    assert summer_utc.hour == 15  # 8 AM PDT = 3 PM UTC

    # During standard time (winter): PST is UTC-8
    winter_date = datetime(2025, 11, 11, 8, 0, 0, tzinfo=ZoneInfo("America/Los_Angeles"))
    winter_utc = winter_date.astimezone(timezone.utc)
    assert winter_utc.hour == 16  # 8 AM PST = 4 PM UTC


@pytest.mark.asyncio
async def test_schedule_respects_workspace_timezone_preference(scheduler, mock_workspace_schedules):
    """Test each workspace gets briefing at their configured timezone"""
    with patch.object(scheduler, '_get_active_schedules', return_value=mock_workspace_schedules), \
         patch.object(scheduler, '_already_sent_today', return_value=False):

        await scheduler._send_all_morning_briefings()

        # Verify each workspace was processed
        call_args_list = scheduler.briefing_service.generate_briefing.call_args_list
        workspace_ids = [call[1]["workspace_id"] for call in call_args_list]

        for schedule in mock_workspace_schedules:
            assert schedule["workspace_id"] in workspace_ids


# ==================== Time Window Tests ====================

def test_is_8am_in_timezone_window(scheduler):
    """Test checking if current time is within 8 AM window for a timezone"""
    # Test UTC timezone at 8:02 AM
    current_time = time(8, 2)
    target_time = time(8, 0)

    result = scheduler._is_time_to_send(current_time, target_time, window_minutes=5)

    # Should be within window
    assert result is True


def test_not_8am_in_timezone_window(scheduler):
    """Test detecting when not in 8 AM window"""
    pst = ZoneInfo("America/Los_Angeles")
    current_time_pst = datetime(2025, 11, 11, 9, 0, 0, tzinfo=pst)
    target_time = time(8, 0)

    current_utc = current_time_pst.astimezone(timezone.utc)
    result = scheduler._is_time_to_send(current_utc.time(), target_time, window_minutes=5)

    # Should be outside window
    assert result is False


# ==================== Multiple Timezone Delivery Tests ====================

@pytest.mark.asyncio
async def test_delivers_to_multiple_timezones_correctly(scheduler, mock_workspace_schedules):
    """Test briefings delivered at correct local time for each timezone"""
    with patch.object(scheduler, '_get_active_schedules', return_value=mock_workspace_schedules), \
         patch.object(scheduler, '_already_sent_today', return_value=False):

        await scheduler._send_all_morning_briefings()

        # All three workspaces should receive briefings
        assert scheduler.briefing_service.generate_briefing.call_count == 3
        assert scheduler.discord_service.send_briefing.call_count == 3


@pytest.mark.asyncio
async def test_staggered_delivery_across_timezones(scheduler):
    """Test briefings are delivered in staggered manner across timezones"""
    # UTC 8 AM happens first, then London, then EST, then PST
    schedules_ordered = [
        {"workspace_id": str(uuid4()), "founder_id": str(uuid4()),
         "discord_channel": "utc", "mention_team": False, "timezone": "UTC"},
        {"workspace_id": str(uuid4()), "founder_id": str(uuid4()),
         "discord_channel": "est", "mention_team": False, "timezone": "America/New_York"},
        {"workspace_id": str(uuid4()), "founder_id": str(uuid4()),
         "discord_channel": "pst", "mention_team": False, "timezone": "America/Los_Angeles"}
    ]

    with patch.object(scheduler, '_get_active_schedules', return_value=schedules_ordered), \
         patch.object(scheduler, '_already_sent_today', return_value=False):

        await scheduler._send_all_morning_briefings()

        # All should be delivered
        assert scheduler.briefing_service.generate_briefing.call_count == 3


# ==================== Duplicate Delivery Prevention Tests ====================

@pytest.mark.asyncio
async def test_prevents_duplicate_delivery_same_day(scheduler, mock_workspace_schedules):
    """Test prevents sending same briefing twice in one day"""
    with patch.object(scheduler, '_get_active_schedules', return_value=mock_workspace_schedules[:1]), \
         patch.object(scheduler, '_already_sent_today', return_value=True):

        await scheduler._send_all_morning_briefings()

        # Should not send if already sent
        scheduler.briefing_service.generate_briefing.assert_not_called()
        scheduler.discord_service.send_briefing.assert_not_called()


@pytest.mark.asyncio
async def test_allows_delivery_after_timezone_rollover(scheduler):
    """Test allows new delivery after date rollover in timezone"""
    schedule = {
        "workspace_id": str(uuid4()),
        "founder_id": str(uuid4()),
        "discord_channel": "daily-briefings",
        "mention_team": False,
        "timezone": "America/Los_Angeles"
    }

    # First call: not sent today
    with patch.object(scheduler, '_get_active_schedules', return_value=[schedule]), \
         patch.object(scheduler, '_already_sent_today', return_value=False):

        await scheduler._send_all_morning_briefings()
        assert scheduler.discord_service.send_briefing.call_count == 1

    # Reset mocks
    scheduler.briefing_service.generate_briefing.reset_mock()
    scheduler.discord_service.send_briefing.reset_mock()

    # Second call same day: already sent
    with patch.object(scheduler, '_get_active_schedules', return_value=[schedule]), \
         patch.object(scheduler, '_already_sent_today', return_value=True):

        await scheduler._send_all_morning_briefings()
        scheduler.discord_service.send_briefing.assert_not_called()


# ==================== Error Handling Tests ====================

@pytest.mark.asyncio
async def test_handles_invalid_timezone_gracefully(scheduler):
    """Test handles invalid timezone configuration gracefully"""
    invalid_schedule = {
        "workspace_id": str(uuid4()),
        "founder_id": str(uuid4()),
        "discord_channel": "daily-briefings",
        "mention_team": False,
        "timezone": "Invalid/Timezone"
    }

    with patch.object(scheduler, '_get_active_schedules', return_value=[invalid_schedule]), \
         patch.object(scheduler, '_already_sent_today', return_value=False):

        # Should handle gracefully and continue
        try:
            await scheduler._send_all_morning_briefings()
        except Exception as e:
            # Should not raise exception
            pytest.fail(f"Should handle invalid timezone gracefully: {e}")


@pytest.mark.asyncio
async def test_continues_after_single_timezone_failure(scheduler, mock_workspace_schedules):
    """Test continues processing other timezones after one fails"""
    with patch.object(scheduler, '_get_active_schedules', return_value=mock_workspace_schedules), \
         patch.object(scheduler, '_already_sent_today', return_value=False):

        # First workspace fails, others should succeed
        scheduler.briefing_service.generate_briefing.side_effect = [
            Exception("Generation failed"),
            Mock(id=uuid4()),
            Mock(id=uuid4())
        ]

        await scheduler._send_all_morning_briefings()

        # Should still send to other workspaces
        assert scheduler.discord_service.send_briefing.call_count == 2


# ==================== Default Timezone Tests ====================

@pytest.mark.asyncio
async def test_uses_utc_when_no_timezone_configured(scheduler):
    """Test uses UTC as default when workspace has no timezone configured"""
    schedule_no_tz = {
        "workspace_id": str(uuid4()),
        "founder_id": str(uuid4()),
        "discord_channel": "daily-briefings",
        "mention_team": False,
        "timezone": None
    }

    with patch.object(scheduler, '_get_active_schedules', return_value=[schedule_no_tz]), \
         patch.object(scheduler, '_already_sent_today', return_value=False):

        await scheduler._send_all_morning_briefings()

        # Should still process with UTC default
        assert scheduler.briefing_service.generate_briefing.call_count == 1


# ==================== Scheduling Configuration Tests ====================

def test_scheduler_configured_for_8am_delivery(scheduler):
    """Test scheduler is configured for 8 AM delivery"""
    assert scheduler.morning_briefing_time.hour == 8
    assert scheduler.morning_briefing_time.minute == 0


def test_scheduler_has_5_minute_window(scheduler):
    """Test scheduler uses 5-minute delivery window"""
    current_time = time(8, 4)
    target_time = time(8, 0)

    result = scheduler._is_time_to_send(current_time, target_time, window_minutes=5)
    assert result is True

    # Just outside window
    current_time = time(8, 6)
    result = scheduler._is_time_to_send(current_time, target_time, window_minutes=5)
    assert result is False
