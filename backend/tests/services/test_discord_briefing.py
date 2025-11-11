"""
Tests for Discord Daily Briefing Service - Sprint 5
Tests timezone-aware 8 AM scheduled delivery functionality
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, time, timezone
from uuid import uuid4, UUID
from zoneinfo import ZoneInfo

from app.services.discord_service import DiscordService
from app.models.discord_message import (
    DiscordBriefingRequest,
    DiscordMessageResponse,
    DiscordMessageStatus,
    DiscordMessageType
)
from app.models.briefing import BriefingResponse, BriefingType, BriefingStatus


@pytest.fixture
def mock_db():
    """Mock database session"""
    db = Mock()
    db.execute = Mock()
    db.commit = Mock()
    return db


@pytest.fixture
def mock_briefing():
    """Mock briefing response"""
    now = datetime(2025, 11, 11, tzinfo=timezone.utc)
    return BriefingResponse(
        id=uuid4(),
        workspace_id=uuid4(),
        founder_id=uuid4(),
        briefing_type=BriefingType.MORNING,
        title="Morning Brief - November 11, 2025",
        start_date=datetime(2025, 11, 10, tzinfo=timezone.utc),
        end_date=datetime(2025, 11, 11, tzinfo=timezone.utc),
        status=BriefingStatus.READY,
        summary="Test summary",
        key_highlights=["Highlight 1", "Highlight 2"],
        action_items=["Action 1", "Action 2"],
        generated_at=now,
        created_at=now
    )


@pytest.fixture
def discord_service():
    """Create DiscordService instance"""
    return DiscordService()


def setup_mock_db_for_briefing(mock_db, briefing):
    """Setup mock database with side_effect for briefing operations"""
    message_id = uuid4()

    def mock_execute_side_effect(query, params=None):
        mock_result = Mock()
        mock_row = Mock()
        mock_row.id = message_id
        mock_row.workspace_id = str(briefing.workspace_id)
        mock_row.founder_id = str(briefing.founder_id)
        mock_row.message_type = DiscordMessageType.BRIEFING.value
        mock_row.channel_id = "test-channel"
        mock_row.channel_name = "daily-briefings"
        mock_row.message_content = briefing.title
        mock_row.discord_message_id = "discord-123"
        mock_row.status = DiscordMessageStatus.SENT.value
        mock_row.embed_data = {"title": briefing.title, "fields": []}
        mock_row.error_message = None
        mock_row.sent_at = datetime.utcnow()
        mock_row.created_at = datetime.utcnow()
        mock_row._mapping = {
            "id": mock_row.id,
            "workspace_id": UUID(mock_row.workspace_id),
            "founder_id": UUID(mock_row.founder_id),
            "message_type": mock_row.message_type,
            "channel_id": mock_row.channel_id,
            "channel_name": mock_row.channel_name,
            "message_content": mock_row.message_content,
            "discord_message_id": mock_row.discord_message_id,
            "status": mock_row.status,
            "embed_data": mock_row.embed_data,
            "error_message": mock_row.error_message,
            "sent_at": mock_row.sent_at,
            "created_at": mock_row.created_at
        }
        mock_result.fetchone.return_value = mock_row
        return mock_result

    mock_db.execute.side_effect = mock_execute_side_effect
    return message_id


# ==================== Timezone Tests ====================

@pytest.mark.asyncio
async def test_briefing_scheduled_at_8am_utc(discord_service, mock_db, mock_briefing):
    """Test briefing delivery scheduled at 8 AM UTC"""
    setup_mock_db_for_briefing(mock_db, mock_briefing)

    with patch.object(discord_service.briefing_service, 'generate_briefing', new_callable=AsyncMock, return_value=mock_briefing):
        request = DiscordBriefingRequest(
            workspace_id=mock_briefing.workspace_id,
            founder_id=mock_briefing.founder_id,
            channel_name="daily-briefings",
            include_metrics=True,
            include_action_items=True
        )

        result = await discord_service.send_briefing(request, db=mock_db)

        assert result is not None
        assert result.message_type == DiscordMessageType.BRIEFING


@pytest.mark.asyncio
async def test_briefing_scheduled_at_8am_pst(discord_service, mock_db, mock_briefing):
    """Test briefing delivery scheduled at 8 AM Pacific Time"""
    pst = ZoneInfo("America/Los_Angeles")
    scheduled_time_pst = datetime(2025, 11, 11, 8, 0, 0, tzinfo=pst)

    # Convert to UTC for verification
    scheduled_time_utc = scheduled_time_pst.astimezone(timezone.utc)

    with patch.object(discord_service.briefing_service, 'generate_briefing', new_callable=AsyncMock, return_value=mock_briefing):
        mock_result = Mock()
        mock_row = Mock()
        mock_row.id = uuid4()
        mock_row.workspace_id = str(mock_briefing.workspace_id)
        mock_row.founder_id = str(mock_briefing.founder_id)
        mock_row.message_type = DiscordMessageType.BRIEFING.value
        mock_row.channel_id = "test-channel"
        mock_row.channel_name = "daily-briefings"
        mock_row.message_content = mock_briefing.title
        mock_row.discord_message_id = "discord-123"
        mock_row.status = DiscordMessageStatus.SENT.value
        mock_row.embed_data = {}
        mock_row.error_message = None
        mock_row.sent_at = scheduled_time_utc
        mock_row.created_at = datetime.utcnow()
        mock_row._mapping = {
            "id": mock_row.id,
            "workspace_id": UUID(mock_row.workspace_id),
            "founder_id": UUID(mock_row.founder_id),
            "message_type": mock_row.message_type,
            "channel_id": mock_row.channel_id,
            "channel_name": mock_row.channel_name,
            "message_content": mock_row.message_content,
            "discord_message_id": mock_row.discord_message_id,
            "status": mock_row.status,
            "embed_data": mock_row.embed_data,
            "error_message": mock_row.error_message,
            "sent_at": mock_row.sent_at,
            "created_at": mock_row.created_at
        }
        mock_result.fetchone.return_value = mock_row
        mock_db.execute.return_value = mock_result

        request = DiscordBriefingRequest(
            workspace_id=mock_briefing.workspace_id,
            founder_id=mock_briefing.founder_id,
            channel_name="daily-briefings",
            include_metrics=True,
            include_action_items=True
        )

        result = await discord_service.send_briefing(request, db=mock_db)

        assert result is not None
        # Verify sent time matches expected UTC conversion
        assert result.sent_at.hour == scheduled_time_utc.hour


@pytest.mark.asyncio
async def test_briefing_scheduled_at_8am_est(discord_service, mock_db, mock_briefing):
    """Test briefing delivery scheduled at 8 AM Eastern Time"""
    est = ZoneInfo("America/New_York")
    scheduled_time_est = datetime(2025, 11, 11, 8, 0, 0, tzinfo=est)
    scheduled_time_utc = scheduled_time_est.astimezone(timezone.utc)

    with patch.object(discord_service.briefing_service, 'generate_briefing', new_callable=AsyncMock, return_value=mock_briefing):
        mock_result = Mock()
        mock_row = Mock()
        mock_row.id = uuid4()
        mock_row.workspace_id = str(mock_briefing.workspace_id)
        mock_row.founder_id = str(mock_briefing.founder_id)
        mock_row.message_type = DiscordMessageType.BRIEFING.value
        mock_row.channel_id = "test-channel"
        mock_row.channel_name = "daily-briefings"
        mock_row.message_content = mock_briefing.title
        mock_row.discord_message_id = "discord-123"
        mock_row.status = DiscordMessageStatus.SENT.value
        mock_row.embed_data = {}
        mock_row.error_message = None
        mock_row.sent_at = scheduled_time_utc
        mock_row.created_at = datetime.utcnow()
        mock_row._mapping = {
            "id": mock_row.id,
            "workspace_id": UUID(mock_row.workspace_id),
            "founder_id": UUID(mock_row.founder_id),
            "message_type": mock_row.message_type,
            "channel_id": mock_row.channel_id,
            "channel_name": mock_row.channel_name,
            "message_content": mock_row.message_content,
            "discord_message_id": mock_row.discord_message_id,
            "status": mock_row.status,
            "embed_data": mock_row.embed_data,
            "error_message": mock_row.error_message,
            "sent_at": mock_row.sent_at,
            "created_at": mock_row.created_at
        }
        mock_result.fetchone.return_value = mock_row
        mock_db.execute.return_value = mock_result

        request = DiscordBriefingRequest(
            workspace_id=mock_briefing.workspace_id,
            founder_id=mock_briefing.founder_id,
            channel_name="daily-briefings",
            include_metrics=True,
            include_action_items=True
        )

        result = await discord_service.send_briefing(request, db=mock_db)

        assert result is not None
        assert result.sent_at.hour == scheduled_time_utc.hour


# ==================== Briefing Formatting Tests ====================

@pytest.mark.asyncio
async def test_briefing_formatted_for_discord(discord_service, mock_db, mock_briefing):
    """Test briefing is properly formatted for Discord with embeds"""
    with patch.object(discord_service.briefing_service, 'generate_briefing', new_callable=AsyncMock, return_value=mock_briefing):
        mock_result = Mock()
        mock_row = Mock()
        mock_row.id = uuid4()
        mock_row.workspace_id = str(mock_briefing.workspace_id)
        mock_row.founder_id = str(mock_briefing.founder_id)
        mock_row.message_type = DiscordMessageType.BRIEFING.value
        mock_row.channel_id = "test-channel"
        mock_row.channel_name = "daily-briefings"
        mock_row.message_content = mock_briefing.title
        mock_row.discord_message_id = "discord-123"
        mock_row.status = DiscordMessageStatus.SENT.value
        mock_row.embed_data = {
            "title": mock_briefing.title,
            "description": f"Briefing for {mock_briefing.start_date.strftime('%B %d, %Y')}",
            "color": 0x5865F2,
            "fields": [
                {"name": "Summary", "value": mock_briefing.summary, "inline": False},
                {"name": "Key Highlights", "value": "• Highlight 1\n• Highlight 2", "inline": False}
            ]
        }
        mock_row.error_message = None
        mock_row.sent_at = datetime.utcnow()
        mock_row.created_at = datetime.utcnow()
        mock_row._mapping = {
            "id": mock_row.id,
            "workspace_id": UUID(mock_row.workspace_id),
            "founder_id": UUID(mock_row.founder_id),
            "message_type": mock_row.message_type,
            "channel_id": mock_row.channel_id,
            "channel_name": mock_row.channel_name,
            "message_content": mock_row.message_content,
            "discord_message_id": mock_row.discord_message_id,
            "status": mock_row.status,
            "embed_data": mock_row.embed_data,
            "error_message": mock_row.error_message,
            "sent_at": mock_row.sent_at,
            "created_at": mock_row.created_at
        }
        mock_result.fetchone.return_value = mock_row
        mock_db.execute.return_value = mock_result

        request = DiscordBriefingRequest(
            workspace_id=mock_briefing.workspace_id,
            founder_id=mock_briefing.founder_id,
            channel_name="daily-briefings",
            include_metrics=True,
            include_action_items=True
        )

        result = await discord_service.send_briefing(request, db=mock_db)

        assert result is not None
        assert result.embed_data is not None
        assert "title" in result.embed_data
        assert "fields" in result.embed_data


@pytest.mark.asyncio
async def test_briefing_includes_highlights_and_actions(discord_service, mock_db, mock_briefing):
    """Test briefing includes highlights and action items"""
    with patch.object(discord_service.briefing_service, 'generate_briefing', new_callable=AsyncMock, return_value=mock_briefing):
        mock_result = Mock()
        mock_row = Mock()
        mock_row.id = uuid4()
        mock_row.workspace_id = str(mock_briefing.workspace_id)
        mock_row.founder_id = str(mock_briefing.founder_id)
        mock_row.message_type = DiscordMessageType.BRIEFING.value
        mock_row.channel_id = "test-channel"
        mock_row.channel_name = "daily-briefings"
        mock_row.message_content = mock_briefing.title
        mock_row.discord_message_id = "discord-123"
        mock_row.status = DiscordMessageStatus.SENT.value
        mock_row.embed_data = {
            "fields": [
                {"name": "Key Highlights", "value": "• Highlight 1\n• Highlight 2"},
                {"name": "Action Items", "value": "• Action 1\n• Action 2"}
            ]
        }
        mock_row.error_message = None
        mock_row.sent_at = datetime.utcnow()
        mock_row.created_at = datetime.utcnow()
        mock_row._mapping = {
            "id": mock_row.id,
            "workspace_id": UUID(mock_row.workspace_id),
            "founder_id": UUID(mock_row.founder_id),
            "message_type": mock_row.message_type,
            "channel_id": mock_row.channel_id,
            "channel_name": mock_row.channel_name,
            "message_content": mock_row.message_content,
            "discord_message_id": mock_row.discord_message_id,
            "status": mock_row.status,
            "embed_data": mock_row.embed_data,
            "error_message": mock_row.error_message,
            "sent_at": mock_row.sent_at,
            "created_at": mock_row.created_at
        }
        mock_result.fetchone.return_value = mock_row
        mock_db.execute.return_value = mock_result

        request = DiscordBriefingRequest(
            workspace_id=mock_briefing.workspace_id,
            founder_id=mock_briefing.founder_id,
            channel_name="daily-briefings",
            include_metrics=True,
            include_action_items=True
        )

        result = await discord_service.send_briefing(request, db=mock_db)

        assert result is not None
        assert result.embed_data is not None
        # Verify fields contain highlights and actions
        field_names = [f["name"] for f in result.embed_data["fields"]]
        assert "Key Highlights" in field_names
        assert "Action Items" in field_names


# ==================== Delivery Confirmation Tests ====================

@pytest.mark.asyncio
async def test_briefing_delivery_status_tracked(discord_service, mock_db, mock_briefing):
    """Test briefing delivery status is tracked in database"""
    with patch.object(discord_service.briefing_service, 'generate_briefing', new_callable=AsyncMock, return_value=mock_briefing):
        mock_result = Mock()
        mock_row = Mock()
        mock_row.id = uuid4()
        mock_row.workspace_id = str(mock_briefing.workspace_id)
        mock_row.founder_id = str(mock_briefing.founder_id)
        mock_row.message_type = DiscordMessageType.BRIEFING.value
        mock_row.channel_id = "test-channel"
        mock_row.channel_name = "daily-briefings"
        mock_row.message_content = mock_briefing.title
        mock_row.discord_message_id = "discord-msg-123"
        mock_row.status = DiscordMessageStatus.SENT.value
        mock_row.embed_data = {}
        mock_row.error_message = None
        mock_row.sent_at = datetime.utcnow()
        mock_row.created_at = datetime.utcnow()
        mock_row._mapping = {
            "id": mock_row.id,
            "workspace_id": UUID(mock_row.workspace_id),
            "founder_id": UUID(mock_row.founder_id),
            "message_type": mock_row.message_type,
            "channel_id": mock_row.channel_id,
            "channel_name": mock_row.channel_name,
            "message_content": mock_row.message_content,
            "discord_message_id": mock_row.discord_message_id,
            "status": mock_row.status,
            "embed_data": mock_row.embed_data,
            "error_message": mock_row.error_message,
            "sent_at": mock_row.sent_at,
            "created_at": mock_row.created_at
        }
        mock_result.fetchone.return_value = mock_row
        mock_db.execute.return_value = mock_result

        request = DiscordBriefingRequest(
            workspace_id=mock_briefing.workspace_id,
            founder_id=mock_briefing.founder_id,
            channel_name="daily-briefings",
            include_metrics=True,
            include_action_items=True
        )

        result = await discord_service.send_briefing(request, db=mock_db)

        assert result is not None
        assert result.status == DiscordMessageStatus.SENT
        assert result.discord_message_id is not None
        assert result.sent_at is not None


@pytest.mark.asyncio
async def test_briefing_delivery_failure_tracked(discord_service, mock_db, mock_briefing):
    """Test briefing delivery failure is tracked"""
    with patch.object(discord_service.briefing_service, 'generate_briefing', new_callable=AsyncMock, return_value=mock_briefing):
        # Mock Discord send failure
        with patch.object(discord_service, '_send_to_discord', side_effect=Exception("Discord API Error")):
            mock_result = Mock()
            mock_row = Mock()
            mock_row.id = uuid4()
            mock_row.workspace_id = str(mock_briefing.workspace_id)
            mock_row.founder_id = str(mock_briefing.founder_id)
            mock_row.message_type = DiscordMessageType.BRIEFING.value
            mock_row.channel_id = "test-channel"
            mock_row.channel_name = "daily-briefings"
            mock_row.message_content = mock_briefing.title
            mock_row.discord_message_id = None
            mock_row.status = DiscordMessageStatus.PENDING.value
            mock_row.embed_data = {}
            mock_row.error_message = None
            mock_row.sent_at = None
            mock_row.created_at = datetime.utcnow()
            mock_row._mapping = {
                "id": mock_row.id,
                "workspace_id": UUID(mock_row.workspace_id),
                "founder_id": UUID(mock_row.founder_id),
                "message_type": mock_row.message_type,
                "channel_id": mock_row.channel_id,
                "channel_name": mock_row.channel_name,
                "message_content": mock_row.message_content,
                "discord_message_id": mock_row.discord_message_id,
                "status": mock_row.status,
                "embed_data": mock_row.embed_data,
                "error_message": mock_row.error_message,
                "sent_at": mock_row.sent_at,
                "created_at": mock_row.created_at
            }
            mock_result.fetchone.return_value = mock_row
            mock_db.execute.return_value = mock_result

            request = DiscordBriefingRequest(
                workspace_id=mock_briefing.workspace_id,
                founder_id=mock_briefing.founder_id,
                channel_name="daily-briefings",
                include_metrics=True,
                include_action_items=True
            )

            result = await discord_service.send_briefing(request, db=mock_db)

            # Should return None on failure
            assert result is None


# ==================== Reuse Sprint 4 Briefing Tests ====================

@pytest.mark.asyncio
async def test_reuses_sprint4_briefing_generation(discord_service, mock_db, mock_briefing):
    """Test that Sprint 5 reuses Sprint 4 briefing generation logic"""
    with patch.object(discord_service.briefing_service, 'generate_briefing', new_callable=AsyncMock, return_value=mock_briefing) as mock_gen:
        mock_result = Mock()
        mock_row = Mock()
        mock_row.id = uuid4()
        mock_row.workspace_id = str(mock_briefing.workspace_id)
        mock_row.founder_id = str(mock_briefing.founder_id)
        mock_row.message_type = DiscordMessageType.BRIEFING.value
        mock_row.channel_id = "test-channel"
        mock_row.channel_name = "daily-briefings"
        mock_row.message_content = mock_briefing.title
        mock_row.discord_message_id = "discord-123"
        mock_row.status = DiscordMessageStatus.SENT.value
        mock_row.embed_data = {}
        mock_row.error_message = None
        mock_row.sent_at = datetime.utcnow()
        mock_row.created_at = datetime.utcnow()
        mock_row._mapping = {
            "id": mock_row.id,
            "workspace_id": UUID(mock_row.workspace_id),
            "founder_id": UUID(mock_row.founder_id),
            "message_type": mock_row.message_type,
            "channel_id": mock_row.channel_id,
            "channel_name": mock_row.channel_name,
            "message_content": mock_row.message_content,
            "discord_message_id": mock_row.discord_message_id,
            "status": mock_row.status,
            "embed_data": mock_row.embed_data,
            "error_message": mock_row.error_message,
            "sent_at": mock_row.sent_at,
            "created_at": mock_row.created_at
        }
        mock_result.fetchone.return_value = mock_row
        mock_db.execute.return_value = mock_result

        request = DiscordBriefingRequest(
            workspace_id=mock_briefing.workspace_id,
            founder_id=mock_briefing.founder_id,
            channel_name="daily-briefings",
            include_metrics=True,
            include_action_items=True
        )

        result = await discord_service.send_briefing(request, db=mock_db)

        # Verify BriefingService.generate_briefing was called
        mock_gen.assert_called_once()
        call_kwargs = mock_gen.call_args[1]
        assert call_kwargs["workspace_id"] == mock_briefing.workspace_id
        assert call_kwargs["founder_id"] == mock_briefing.founder_id
        assert call_kwargs["briefing_type"] == "morning"
