"""
Comprehensive tests for Discord Service
Tests posting status updates, sending briefings, and message management
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from uuid import uuid4, UUID

from app.services.discord_service import DiscordService
from app.models.discord_message import (
    DiscordStatusUpdateRequest,
    DiscordBriefingRequest,
    DiscordMessageResponse,
    DiscordMessageType,
    DiscordMessageStatus,
    DiscordEmbed
)
from app.models.briefing import BriefingResponse, BriefingType, BriefingStatus


class TestDiscordService:
    """Test suite for DiscordService"""

    @pytest.fixture
    def service(self):
        """Create Discord service"""
        return DiscordService()

    @pytest.fixture
    def workspace_id(self):
        """Sample workspace ID"""
        return uuid4()

    @pytest.fixture
    def founder_id(self):
        """Sample founder ID"""
        return uuid4()

    @pytest.fixture
    def sample_status_update(self, workspace_id, founder_id):
        """Sample status update request"""
        return DiscordStatusUpdateRequest(
            workspace_id=workspace_id,
            founder_id=founder_id,
            message="KPI alert: Revenue increased by 15%",
            channel_name="status-updates",
            mentions=["@team"]
        )

    @pytest.fixture
    def sample_briefing_request(self, workspace_id, founder_id):
        """Sample briefing request"""
        return DiscordBriefingRequest(
            workspace_id=workspace_id,
            founder_id=founder_id,
            channel_name="daily-briefings",
            include_metrics=True,
            include_action_items=True,
            mention_team=True
        )

    @pytest.fixture
    def sample_briefing(self, workspace_id, founder_id):
        """Sample briefing response"""
        return BriefingResponse(
            id=uuid4(),
            workspace_id=workspace_id,
            founder_id=founder_id,
            briefing_type=BriefingType.MORNING,
            title="Morning Brief - January 10, 2025",
            start_date=datetime.utcnow(),
            end_date=datetime.utcnow(),
            summary="Today you have 3 meetings and 2 urgent items.",
            key_highlights=["Revenue up 15%", "New customer signed"],
            action_items=["Review Q1 budget", "Prepare investor update"],
            sections=[],
            status=BriefingStatus.READY,
            created_at=datetime.utcnow()
        )

    @pytest.fixture
    def mock_db_row(self, workspace_id, founder_id):
        """Mock database row for discord message"""
        row = MagicMock()
        row.id = uuid4()
        row.workspace_id = str(workspace_id)
        row.founder_id = str(founder_id)
        row.message_type = "status_update"
        row.channel_id = "channel_123"
        row.channel_name = "status-updates"
        row.message_content = "Test message"
        row.discord_message_id = "discord_msg_123"
        row.status = "sent"
        row.embed_data = None
        row.error_message = None
        row.sent_at = datetime.utcnow()
        row.created_at = datetime.utcnow()
        return row

    # ==================== STATUS UPDATES ====================

    @pytest.mark.asyncio
    async def test_post_status_update_success(self, service, sample_status_update, mock_db_row):
        """Test posting status update successfully"""
        with patch('app.services.discord_service.get_db_context') as mock_db:
            mock_context = AsyncMock()
            mock_result = MagicMock()
            mock_result.fetchone.return_value = mock_db_row
            mock_context.execute = AsyncMock(return_value=mock_result)
            mock_context.commit = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_context

            with patch.object(service, '_send_to_discord', return_value="discord_msg_123") as mock_send:
                message = await service.post_status_update(sample_status_update)

                assert message is not None
                assert message.message_type == DiscordMessageType.STATUS_UPDATE
                assert message.status == DiscordMessageStatus.SENT
                mock_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_post_status_update_with_embed(self, service, sample_status_update, mock_db_row):
        """Test posting status update with embed"""
        sample_status_update.embed = DiscordEmbed(
            title="Revenue Alert",
            description="Significant revenue increase detected",
            color=0x00FF00,
            fields=[{"name": "Change", "value": "+15%", "inline": True}]
        )

        with patch('app.services.discord_service.get_db_context') as mock_db:
            mock_context = AsyncMock()
            mock_result = MagicMock()
            mock_result.fetchone.return_value = mock_db_row
            mock_context.execute = AsyncMock(return_value=mock_result)
            mock_context.commit = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_context

            with patch.object(service, '_send_to_discord', return_value="discord_msg_123"):
                message = await service.post_status_update(sample_status_update)

                assert message is not None

    @pytest.mark.asyncio
    async def test_post_status_update_with_channel_id(self, service, sample_status_update, mock_db_row):
        """Test posting to specific channel ID"""
        sample_status_update.channel_id = "specific_channel_123"

        with patch('app.services.discord_service.get_db_context') as mock_db:
            mock_context = AsyncMock()
            mock_result = MagicMock()
            mock_result.fetchone.return_value = mock_db_row
            mock_context.execute = AsyncMock(return_value=mock_result)
            mock_context.commit = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_context

            with patch.object(service, '_send_to_discord', return_value="discord_msg_123") as mock_send:
                message = await service.post_status_update(sample_status_update)

                # Verify channel_id was used
                call_args = mock_send.call_args
                assert call_args[1]["channel_id"] == "specific_channel_123"

    @pytest.mark.asyncio
    async def test_post_status_update_failure(self, service, sample_status_update, mock_db_row):
        """Test status update failure handling"""
        with patch('app.services.discord_service.get_db_context') as mock_db:
            mock_context = AsyncMock()
            mock_result = MagicMock()
            mock_result.fetchone.return_value = mock_db_row
            mock_context.execute = AsyncMock(return_value=mock_result)
            mock_context.commit = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_context

            with patch.object(service, '_send_to_discord', side_effect=Exception("Discord API error")):
                message = await service.post_status_update(sample_status_update)

                # Should return None on error
                assert message is None

    # ==================== BRIEFING MESSAGES ====================

    @pytest.mark.asyncio
    async def test_send_briefing_with_id(self, service, sample_briefing_request, sample_briefing, mock_db_row):
        """Test sending specific briefing by ID"""
        sample_briefing_request.briefing_id = sample_briefing.id

        with patch('app.services.discord_service.get_db_context') as mock_db:
            mock_context = AsyncMock()
            mock_result = MagicMock()

            # Mock briefing fetch
            briefing_row = MagicMock()
            briefing_row.id = sample_briefing.id
            briefing_row.title = sample_briefing.title
            briefing_row.summary = sample_briefing.summary
            briefing_row.key_highlights = sample_briefing.key_highlights
            briefing_row.action_items = sample_briefing.action_items
            briefing_row.start_date = sample_briefing.start_date

            mock_result.fetchone.side_effect = [briefing_row, mock_db_row]
            mock_context.execute = AsyncMock(return_value=mock_result)
            mock_context.commit = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_context

            with patch.object(service, '_send_to_discord', return_value="discord_msg_123"):
                message = await service.send_briefing(sample_briefing_request)

                assert message is not None
                assert message.message_type == DiscordMessageType.BRIEFING

    @pytest.mark.asyncio
    async def test_send_briefing_generate_new(self, service, sample_briefing_request, sample_briefing, mock_db_row):
        """Test sending newly generated briefing"""
        with patch('app.services.discord_service.get_db_context') as mock_db:
            mock_context = AsyncMock()
            mock_result = MagicMock()
            mock_result.fetchone.return_value = mock_db_row
            mock_context.execute = AsyncMock(return_value=mock_result)
            mock_context.commit = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_context

            with patch.object(service.briefing_service, 'generate_briefing', return_value=sample_briefing):
                with patch.object(service, '_send_to_discord', return_value="discord_msg_123"):
                    message = await service.send_briefing(sample_briefing_request)

                    assert message is not None

    @pytest.mark.asyncio
    async def test_send_briefing_with_team_mention(self, service, sample_briefing_request, sample_briefing, mock_db_row):
        """Test sending briefing with team mention"""
        sample_briefing_request.mention_team = True

        with patch('app.services.discord_service.get_db_context') as mock_db:
            mock_context = AsyncMock()
            mock_result = MagicMock()
            mock_result.fetchone.return_value = mock_db_row
            mock_context.execute = AsyncMock(return_value=mock_result)
            mock_context.commit = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_context

            with patch.object(service.briefing_service, 'generate_briefing', return_value=sample_briefing):
                with patch.object(service, '_send_to_discord', return_value="discord_msg_123") as mock_send:
                    message = await service.send_briefing(sample_briefing_request)

                    # Verify @here mention was included
                    call_args = mock_send.call_args
                    assert "@here" in call_args[1]["mentions"]

    @pytest.mark.asyncio
    async def test_send_briefing_not_found(self, service, sample_briefing_request):
        """Test sending non-existent briefing"""
        sample_briefing_request.briefing_id = uuid4()

        with patch('app.services.discord_service.get_db_context') as mock_db:
            mock_context = AsyncMock()
            mock_result = MagicMock()
            mock_result.fetchone.return_value = None
            mock_context.execute = AsyncMock(return_value=mock_result)
            mock_db.return_value.__aenter__.return_value = mock_context

            message = await service.send_briefing(sample_briefing_request)

            assert message is None

    @pytest.mark.asyncio
    async def test_send_briefing_no_briefing_available(self, service, sample_briefing_request, mock_db_row):
        """Test when no briefing can be generated"""
        with patch('app.services.discord_service.get_db_context') as mock_db:
            mock_context = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_context

            with patch.object(service.briefing_service, 'generate_briefing', return_value=None):
                message = await service.send_briefing(sample_briefing_request)

                assert message is None

    # ==================== MESSAGE RETRIEVAL ====================

    @pytest.mark.asyncio
    async def test_get_message_success(self, service, mock_db_row):
        """Test getting message by ID"""
        message_id = uuid4()

        with patch('app.services.discord_service.get_db_context') as mock_db:
            mock_context = AsyncMock()
            mock_result = MagicMock()
            mock_result.fetchone.return_value = mock_db_row
            mock_context.execute = AsyncMock(return_value=mock_result)
            mock_db.return_value.__aenter__.return_value = mock_context

            message = await service.get_message(message_id)

            assert message is not None
            assert isinstance(message, DiscordMessageResponse)

    @pytest.mark.asyncio
    async def test_get_message_not_found(self, service):
        """Test getting non-existent message"""
        message_id = uuid4()

        with patch('app.services.discord_service.get_db_context') as mock_db:
            mock_context = AsyncMock()
            mock_result = MagicMock()
            mock_result.fetchone.return_value = None
            mock_context.execute = AsyncMock(return_value=mock_result)
            mock_db.return_value.__aenter__.return_value = mock_context

            message = await service.get_message(message_id)

            assert message is None

    # ==================== HELPER METHODS ====================

    @pytest.mark.asyncio
    async def test_send_to_discord(self, service):
        """Test Discord API simulation"""
        message_id = await service._send_to_discord(
            channel_id="channel_123",
            content="Test message",
            embed=None,
            mentions=[]
        )

        assert message_id is not None
        assert isinstance(message_id, str)

    @pytest.mark.asyncio
    async def test_send_to_discord_with_embed(self, service):
        """Test sending with embed"""
        embed = {
            "title": "Test Embed",
            "description": "Test description",
            "color": 0x5865F2
        }

        message_id = await service._send_to_discord(
            channel_id="channel_123",
            content="Test",
            embed=embed,
            mentions=["@user"]
        )

        assert message_id is not None

    @pytest.mark.asyncio
    async def test_get_default_channel(self, service, workspace_id):
        """Test getting default channel"""
        channel_id = await service._get_default_channel(
            workspace_id=workspace_id,
            channel_name="general"
        )

        assert channel_id is not None
        assert str(workspace_id) in channel_id

    @pytest.mark.asyncio
    async def test_format_briefing_embed(self, service, sample_briefing):
        """Test formatting briefing as embed"""
        embed = await service._format_briefing_embed(
            briefing=sample_briefing,
            include_metrics=True,
            include_action_items=True
        )

        assert isinstance(embed, DiscordEmbed)
        assert embed.title == sample_briefing.title
        assert len(embed.fields) > 0
        assert any(f["name"] == "Summary" for f in embed.fields)
        assert any(f["name"] == "Key Highlights" for f in embed.fields)
        assert any(f["name"] == "Action Items" for f in embed.fields)

    @pytest.mark.asyncio
    async def test_format_briefing_embed_no_highlights(self, service, sample_briefing):
        """Test formatting briefing with no highlights"""
        sample_briefing.key_highlights = []

        embed = await service._format_briefing_embed(sample_briefing)

        assert isinstance(embed, DiscordEmbed)
        # Should still have summary field
        assert any(f["name"] == "Summary" for f in embed.fields)

    @pytest.mark.asyncio
    async def test_format_briefing_embed_without_action_items(self, service, sample_briefing):
        """Test formatting without action items"""
        embed = await service._format_briefing_embed(
            briefing=sample_briefing,
            include_action_items=False
        )

        assert not any(f["name"] == "Action Items" for f in embed.fields)

    @pytest.mark.asyncio
    async def test_format_briefing_embed_truncates_long_text(self, service, sample_briefing):
        """Test that long text is truncated to Discord limits"""
        # Create very long summary
        sample_briefing.summary = "A" * 2000

        embed = await service._format_briefing_embed(sample_briefing)

        # Discord field value limit is 1024
        summary_field = next(f for f in embed.fields if f["name"] == "Summary")
        assert len(summary_field["value"]) <= 1024

    @pytest.mark.asyncio
    async def test_update_message_success(self, service, mock_db_row):
        """Test updating message"""
        from app.models.discord_message import DiscordMessageUpdate

        message_id = uuid4()
        update = DiscordMessageUpdate(
            status=DiscordMessageStatus.SENT,
            discord_message_id="discord_123",
            sent_at=datetime.utcnow()
        )

        with patch('app.services.discord_service.get_db_context') as mock_db:
            mock_context = AsyncMock()
            mock_context.execute = AsyncMock()
            mock_context.commit = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_context

            await service._update_message(message_id, update)

            mock_context.execute.assert_called_once()
            mock_context.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_message_with_error(self, service):
        """Test updating message with error"""
        from app.models.discord_message import DiscordMessageUpdate

        message_id = uuid4()
        update = DiscordMessageUpdate(
            status=DiscordMessageStatus.FAILED,
            error_message="Discord API error"
        )

        with patch('app.services.discord_service.get_db_context') as mock_db:
            mock_context = AsyncMock()
            mock_context.execute = AsyncMock()
            mock_context.commit = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_context

            await service._update_message(message_id, update)

            mock_context.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_message_no_changes(self, service):
        """Test updating message with no actual changes"""
        from app.models.discord_message import DiscordMessageUpdate

        message_id = uuid4()
        update = DiscordMessageUpdate()

        with patch('app.services.discord_service.get_db_context') as mock_db:
            mock_context = AsyncMock()
            mock_context.execute = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_context

            await service._update_message(message_id, update)

            # Should not execute any query if no updates
            mock_context.execute.assert_not_called()
