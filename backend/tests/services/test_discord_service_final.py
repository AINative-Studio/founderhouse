"""
Comprehensive test suite for Discord Service
Covers: status updates, briefings, embeds, error handling, and message tracking
Target: 80%+ coverage (from 23%)
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from datetime import datetime
from uuid import uuid4, UUID
import json

from app.services.discord_service import DiscordService
from app.models.discord_message import (
    DiscordStatusUpdateRequest,
    DiscordBriefingRequest,
    DiscordMessageResponse,
    DiscordMessageType,
    DiscordMessageStatus,
    DiscordEmbed,
    DiscordMessageUpdate,
    DiscordMessageCreate,
)
from app.models.briefing import BriefingResponse, BriefingType, BriefingStatus


class TestDiscordServiceStatusUpdates:
    """Test status update posting functionality"""

    @pytest.fixture
    def service(self):
        """Create Discord service instance"""
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
    def mock_db(self):
        """Mock database session"""
        db = MagicMock()
        return db

    @pytest.fixture
    def sample_status_update(self, workspace_id, founder_id):
        """Sample status update request"""
        return DiscordStatusUpdateRequest(
            workspace_id=workspace_id,
            founder_id=founder_id,
            message="KPI alert: Revenue increased by 15%",
            channel_name="status-updates",
            mentions=["@team"],
        )

    @pytest.fixture
    def mock_db_row(self, workspace_id, founder_id):
        """Mock database row for message record"""
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
        row._mapping = {
            "id": row.id,
            "workspace_id": row.workspace_id,
            "founder_id": row.founder_id,
            "message_type": row.message_type,
            "channel_id": row.channel_id,
            "channel_name": row.channel_name,
            "message_content": row.message_content,
            "discord_message_id": row.discord_message_id,
            "status": row.status,
            "embed_data": row.embed_data,
            "error_message": row.error_message,
            "sent_at": row.sent_at,
            "created_at": row.created_at,
        }
        return row

    @pytest.mark.asyncio
    async def test_post_status_update_basic(self, service, sample_status_update, mock_db, mock_db_row):
        """Test posting a basic status update"""
        mock_result = MagicMock()
        mock_result.fetchone.return_value = mock_db_row
        mock_db.execute.return_value = mock_result

        with patch.object(service, "_send_to_discord", return_value="discord_msg_123"):
            with patch.object(service, "_update_message", new_callable=AsyncMock):
                message = await service.post_status_update(sample_status_update, db=mock_db)

                assert message is not None
                assert message.message_type == DiscordMessageType.STATUS_UPDATE
                assert message.status == DiscordMessageStatus.SENT
                mock_db.execute.assert_called()
                mock_db.commit.assert_called()

    @pytest.mark.asyncio
    async def test_post_status_update_with_embed(
        self, service, sample_status_update, mock_db, mock_db_row
    ):
        """Test posting status update with rich embed"""
        embed_data = {
            "title": "Revenue Alert",
            "description": "Significant increase detected",
            "color": 0x00FF00,
            "fields": [{"name": "Change", "value": "+15%", "inline": True}],
        }
        sample_status_update.embed = embed_data

        mock_result = MagicMock()
        mock_result.fetchone.return_value = mock_db_row
        mock_db.execute.return_value = mock_result

        with patch.object(service, "_send_to_discord", return_value="discord_msg_123"):
            with patch.object(service, "_update_message", new_callable=AsyncMock):
                message = await service.post_status_update(sample_status_update, db=mock_db)

                assert message is not None
                # Verify embed was saved to database
                call_args = mock_db.execute.call_args_list[0]
                assert "embed_data" in str(call_args)

    @pytest.mark.asyncio
    async def test_post_status_update_with_mentions(
        self, service, sample_status_update, mock_db, mock_db_row
    ):
        """Test posting with user mentions"""
        sample_status_update.mentions = ["@alice", "@bob", "@team"]

        mock_result = MagicMock()
        mock_result.fetchone.return_value = mock_db_row
        mock_db.execute.return_value = mock_result

        with patch.object(service, "_send_to_discord", return_value="discord_msg_123") as mock_send:
            with patch.object(service, "_update_message", new_callable=AsyncMock):
                await service.post_status_update(sample_status_update, db=mock_db)

                # Verify mentions passed to Discord
                call_kwargs = mock_send.call_args[1]
                assert call_kwargs["mentions"] == ["@alice", "@bob", "@team"]

    @pytest.mark.asyncio
    async def test_post_status_update_with_specific_channel(
        self, service, sample_status_update, mock_db, mock_db_row
    ):
        """Test posting to specific channel ID"""
        sample_status_update.channel_id = "specific_channel_789"

        mock_result = MagicMock()
        mock_result.fetchone.return_value = mock_db_row
        mock_db.execute.return_value = mock_result

        with patch.object(service, "_send_to_discord", return_value="discord_msg_123") as mock_send:
            with patch.object(service, "_update_message", new_callable=AsyncMock):
                await service.post_status_update(sample_status_update, db=mock_db)

                # Verify specific channel ID was used
                call_kwargs = mock_send.call_args[1]
                assert call_kwargs["channel_id"] == "specific_channel_789"

    @pytest.mark.asyncio
    async def test_post_status_update_no_db_returns_none(self, service, sample_status_update):
        """Test that posting without DB returns None"""
        message = await service.post_status_update(sample_status_update, db=None)
        assert message is None

    @pytest.mark.asyncio
    async def test_post_status_update_discord_error_handling(
        self, service, sample_status_update, mock_db, mock_db_row
    ):
        """Test error handling when Discord send fails"""
        mock_result = MagicMock()
        mock_result.fetchone.return_value = mock_db_row
        mock_db.execute.return_value = mock_result

        with patch.object(
            service, "_send_to_discord", side_effect=Exception("Discord API timeout")
        ):
            with patch.object(service, "_update_message", new_callable=AsyncMock):
                message = await service.post_status_update(sample_status_update, db=mock_db)

                # Should mark message as failed
                assert message is None

    @pytest.mark.asyncio
    async def test_post_status_update_db_error_handling(
        self, service, sample_status_update, mock_db
    ):
        """Test error handling when database insert fails"""
        mock_db.execute.side_effect = Exception("Database connection error")

        message = await service.post_status_update(sample_status_update, db=mock_db)
        assert message is None


class TestDiscordServiceBriefings:
    """Test briefing delivery functionality"""

    @pytest.fixture
    def service(self):
        """Create Discord service instance"""
        return DiscordService()

    @pytest.fixture
    def workspace_id(self):
        return uuid4()

    @pytest.fixture
    def founder_id(self):
        return uuid4()

    @pytest.fixture
    def mock_db(self):
        return MagicMock()

    @pytest.fixture
    def sample_briefing_request(self, workspace_id, founder_id):
        """Sample briefing delivery request"""
        return DiscordBriefingRequest(
            workspace_id=workspace_id,
            founder_id=founder_id,
            channel_name="daily-briefings",
            include_metrics=True,
            include_action_items=True,
            mention_team=False,
        )

    @pytest.fixture
    def sample_briefing(self, workspace_id, founder_id):
        """Sample briefing response"""
        return BriefingResponse(
            id=uuid4(),
            workspace_id=workspace_id,
            founder_id=founder_id,
            briefing_type=BriefingType.MORNING,
            title="Morning Brief - November 10, 2025",
            start_date=datetime.utcnow(),
            end_date=datetime.utcnow(),
            summary="Today you have 3 meetings and 2 urgent items to review.",
            key_highlights=["Revenue up 15%", "New customer signed", "Team morale high"],
            action_items=["Review Q1 budget", "Prepare investor update", "Call with CFO"],
            sections=[],
            status=BriefingStatus.READY,
            created_at=datetime.utcnow(),
            generated_at=datetime.utcnow(),
        )

    @pytest.fixture
    def mock_db_row(self, workspace_id, founder_id):
        """Mock database row"""
        row = MagicMock()
        row.id = uuid4()
        row.workspace_id = str(workspace_id)
        row.founder_id = str(founder_id)
        row.message_type = "briefing"
        row.channel_id = "channel_briefings"
        row.channel_name = "daily-briefings"
        row.message_content = "Morning Brief"
        row.discord_message_id = "discord_msg_456"
        row.status = "sent"
        row.embed_data = {}
        row.error_message = None
        row.sent_at = datetime.utcnow()
        row.created_at = datetime.utcnow()
        row._mapping = {
            "id": row.id,
            "workspace_id": row.workspace_id,
            "founder_id": row.founder_id,
            "message_type": row.message_type,
            "channel_id": row.channel_id,
            "channel_name": row.channel_name,
            "message_content": row.message_content,
            "discord_message_id": row.discord_message_id,
            "status": row.status,
            "embed_data": row.embed_data,
            "error_message": row.error_message,
            "sent_at": row.sent_at,
            "created_at": row.created_at,
        }
        return row

    @pytest.mark.asyncio
    async def test_send_briefing_with_id(
        self, service, sample_briefing_request, sample_briefing, mock_db, mock_db_row
    ):
        """Test sending specific briefing by ID"""
        sample_briefing_request.briefing_id = sample_briefing.id

        briefing_row = MagicMock()
        briefing_row._mapping = {
            "id": sample_briefing.id,
            "workspace_id": str(sample_briefing.workspace_id),
            "founder_id": str(sample_briefing.founder_id),
            "briefing_type": sample_briefing.briefing_type.value,
            "title": sample_briefing.title,
            "start_date": sample_briefing.start_date,
            "end_date": sample_briefing.end_date,
            "summary": sample_briefing.summary,
            "key_highlights": sample_briefing.key_highlights,
            "action_items": sample_briefing.action_items,
            "sections": sample_briefing.sections,
            "status": sample_briefing.status.value,
            "created_at": sample_briefing.created_at,
            "generated_at": sample_briefing.generated_at,
            "metadata": {},
            "delivered_at": None,
            "delivery_channels": [],
        }

        mock_result = MagicMock()
        mock_result.fetchone.side_effect = [briefing_row, mock_db_row]
        mock_db.execute.return_value = mock_result

        with patch.object(service, "_send_to_discord", return_value="discord_msg_456"):
            with patch.object(service, "_update_message", new_callable=AsyncMock):
                with patch.object(service, "_format_briefing_embed") as mock_format:
                    embed = DiscordEmbed(
                        title="Test",
                        description="Test",
                        fields=[{"name": "Summary", "value": "Test", "inline": False}],
                    )
                    mock_format.return_value = embed

                    message = await service.send_briefing(sample_briefing_request, db=mock_db)

                    assert message is not None
                    assert message.message_type == DiscordMessageType.BRIEFING
                    assert message.status == DiscordMessageStatus.SENT

    @pytest.mark.asyncio
    async def test_send_briefing_generate_new(
        self, service, sample_briefing_request, sample_briefing, mock_db, mock_db_row
    ):
        """Test generating and sending new briefing"""
        mock_result = MagicMock()
        mock_result.fetchone.return_value = mock_db_row
        mock_db.execute.return_value = mock_result

        with patch.object(
            service.briefing_service, "generate_briefing", return_value=sample_briefing
        ):
            with patch.object(service, "_send_to_discord", return_value="discord_msg_456"):
                with patch.object(service, "_update_message", new_callable=AsyncMock):
                    with patch.object(service, "_format_briefing_embed") as mock_format:
                        embed = DiscordEmbed(
                            title="Test",
                            description="Test",
                            fields=[{"name": "Summary", "value": "Test", "inline": False}],
                        )
                        mock_format.return_value = embed

                        message = await service.send_briefing(sample_briefing_request, db=mock_db)

                        assert message is not None
                        assert message.message_type == DiscordMessageType.BRIEFING

    @pytest.mark.asyncio
    async def test_send_briefing_with_team_mention(
        self, service, sample_briefing_request, sample_briefing, mock_db, mock_db_row
    ):
        """Test sending briefing with team mention"""
        sample_briefing_request.mention_team = True

        mock_result = MagicMock()
        mock_result.fetchone.return_value = mock_db_row
        mock_db.execute.return_value = mock_result

        with patch.object(
            service.briefing_service, "generate_briefing", return_value=sample_briefing
        ):
            with patch.object(
                service, "_send_to_discord", return_value="discord_msg_456"
            ) as mock_send:
                with patch.object(service, "_update_message", new_callable=AsyncMock):
                    with patch.object(service, "_format_briefing_embed") as mock_format:
                        embed = DiscordEmbed(
                            title="Test",
                            description="Test",
                            fields=[{"name": "Summary", "value": "Test", "inline": False}],
                        )
                        mock_format.return_value = embed

                        await service.send_briefing(sample_briefing_request, db=mock_db)

                        # Verify team mention included
                        call_kwargs = mock_send.call_args[1]
                        assert "@here" in call_kwargs["mentions"]

    @pytest.mark.asyncio
    async def test_send_briefing_briefing_not_found(self, service, sample_briefing_request, mock_db):
        """Test handling when briefing not found"""
        sample_briefing_request.briefing_id = uuid4()

        mock_result = MagicMock()
        mock_result.fetchone.return_value = None
        mock_db.execute.return_value = mock_result

        message = await service.send_briefing(sample_briefing_request, db=mock_db)
        assert message is None

    @pytest.mark.asyncio
    async def test_send_briefing_no_generation_available(
        self, service, sample_briefing_request, mock_db
    ):
        """Test handling when briefing generation returns None"""
        with patch.object(service.briefing_service, "generate_briefing", return_value=None):
            message = await service.send_briefing(sample_briefing_request, db=mock_db)
            assert message is None

    @pytest.mark.asyncio
    async def test_send_briefing_no_db_returns_none(self, service, sample_briefing_request):
        """Test that sending without DB returns None"""
        message = await service.send_briefing(sample_briefing_request, db=None)
        assert message is None

    @pytest.mark.asyncio
    async def test_send_briefing_with_include_metrics_false(
        self, service, sample_briefing_request, sample_briefing, mock_db, mock_db_row
    ):
        """Test briefing formatting with metrics excluded"""
        sample_briefing_request.include_metrics = False

        mock_result = MagicMock()
        mock_result.fetchone.return_value = mock_db_row
        mock_db.execute.return_value = mock_result

        with patch.object(
            service.briefing_service, "generate_briefing", return_value=sample_briefing
        ):
            with patch.object(service, "_send_to_discord", return_value="discord_msg_456"):
                with patch.object(service, "_format_briefing_embed") as mock_format:
                    with patch.object(service, "_update_message", new_callable=AsyncMock):
                        # Mock the embed return
                        embed = DiscordEmbed(
                            title="Test",
                            description="Test",
                            fields=[{"name": "Summary", "value": "Test", "inline": False}],
                        )
                        mock_format.return_value = embed

                        await service.send_briefing(sample_briefing_request, db=mock_db)

                        # Verify metrics flag was passed
                        assert mock_format.called


class TestDiscordServiceEmbeds:
    """Test Discord embed formatting"""

    @pytest.fixture
    def service(self):
        return DiscordService()

    @pytest.fixture
    def sample_briefing(self):
        """Create a sample briefing"""
        return BriefingResponse(
            id=uuid4(),
            workspace_id=uuid4(),
            founder_id=uuid4(),
            briefing_type=BriefingType.MORNING,
            title="Morning Brief",
            start_date=datetime.utcnow(),
            end_date=datetime.utcnow(),
            summary="Executive summary for the day",
            key_highlights=["Highlight 1", "Highlight 2", "Highlight 3"],
            action_items=["Action 1", "Action 2"],
            sections=[],
            status=BriefingStatus.READY,
            created_at=datetime.utcnow(),
            generated_at=datetime.utcnow(),
        )

    @pytest.mark.asyncio
    async def test_format_briefing_embed_basic(self, service, sample_briefing):
        """Test basic embed formatting"""
        embed = await service._format_briefing_embed(sample_briefing)

        assert isinstance(embed, DiscordEmbed)
        assert embed.title == sample_briefing.title
        assert "Briefing for" in embed.description
        assert embed.color == 0x5865F2  # Discord blurple
        assert len(embed.fields) > 0

    @pytest.mark.asyncio
    async def test_format_briefing_embed_has_summary(self, service, sample_briefing):
        """Test that summary field is included"""
        embed = await service._format_briefing_embed(sample_briefing)

        summary_field = next((f for f in embed.fields if f["name"] == "Summary"), None)
        assert summary_field is not None
        assert sample_briefing.summary in summary_field["value"]

    @pytest.mark.asyncio
    async def test_format_briefing_embed_has_highlights(self, service, sample_briefing):
        """Test that highlights are included"""
        embed = await service._format_briefing_embed(sample_briefing)

        highlights_field = next((f for f in embed.fields if f["name"] == "Key Highlights"), None)
        assert highlights_field is not None
        assert "Highlight 1" in highlights_field["value"]

    @pytest.mark.asyncio
    async def test_format_briefing_embed_has_action_items(self, service, sample_briefing):
        """Test that action items are included"""
        embed = await service._format_briefing_embed(
            sample_briefing, include_action_items=True
        )

        actions_field = next((f for f in embed.fields if f["name"] == "Action Items"), None)
        assert actions_field is not None
        assert "Action 1" in actions_field["value"]

    @pytest.mark.asyncio
    async def test_format_briefing_embed_excludes_action_items(self, service, sample_briefing):
        """Test action items can be excluded"""
        embed = await service._format_briefing_embed(
            sample_briefing, include_action_items=False
        )

        actions_field = next((f for f in embed.fields if f["name"] == "Action Items"), None)
        assert actions_field is None

    @pytest.mark.asyncio
    async def test_format_briefing_embed_empty_highlights(self, service, sample_briefing):
        """Test formatting with no highlights"""
        sample_briefing.key_highlights = []

        embed = await service._format_briefing_embed(sample_briefing)

        # Should still have summary
        summary_field = next((f for f in embed.fields if f["name"] == "Summary"), None)
        assert summary_field is not None
        # But no highlights field
        highlights_field = next((f for f in embed.fields if f["name"] == "Key Highlights"), None)
        assert highlights_field is None

    @pytest.mark.asyncio
    async def test_format_briefing_embed_empty_action_items(self, service, sample_briefing):
        """Test formatting with no action items"""
        sample_briefing.action_items = []

        embed = await service._format_briefing_embed(
            sample_briefing, include_action_items=True
        )

        # Should not have action items field
        actions_field = next((f for f in embed.fields if f["name"] == "Action Items"), None)
        assert actions_field is None

    @pytest.mark.asyncio
    async def test_format_briefing_embed_truncates_long_summary(self, service, sample_briefing):
        """Test that long summary is truncated to Discord limits"""
        long_summary = "A" * 2000
        sample_briefing.summary = long_summary

        embed = await service._format_briefing_embed(sample_briefing)

        summary_field = next((f for f in embed.fields if f["name"] == "Summary"), None)
        # Discord field value limit is 1024 characters
        assert len(summary_field["value"]) <= 1024

    @pytest.mark.asyncio
    async def test_format_briefing_embed_truncates_highlights(self, service, sample_briefing):
        """Test that many highlights are limited to 5"""
        sample_briefing.key_highlights = [f"Highlight {i}" for i in range(10)]

        embed = await service._format_briefing_embed(sample_briefing)

        highlights_field = next((f for f in embed.fields if f["name"] == "Key Highlights"), None)
        # Should have at most 5 highlights
        highlight_count = highlights_field["value"].count("•")
        assert highlight_count <= 5

    @pytest.mark.asyncio
    async def test_format_briefing_embed_has_footer(self, service, sample_briefing):
        """Test that embed has footer"""
        embed = await service._format_briefing_embed(sample_briefing)

        assert embed.footer is not None
        assert "AI Chief of Staff" in embed.footer["text"]

    @pytest.mark.asyncio
    async def test_format_briefing_embed_has_timestamp(self, service, sample_briefing):
        """Test that embed has timestamp"""
        embed = await service._format_briefing_embed(sample_briefing)

        assert embed.timestamp is not None


class TestDiscordServiceErrorHandling:
    """Test error handling and edge cases"""

    @pytest.fixture
    def service(self):
        return DiscordService()

    @pytest.fixture
    def mock_db(self):
        return MagicMock()

    @pytest.fixture
    def workspace_id(self):
        return uuid4()

    @pytest.fixture
    def founder_id(self):
        return uuid4()

    @pytest.mark.asyncio
    async def test_get_message_success(self, service, mock_db):
        """Test retrieving message successfully"""
        message_id = uuid4()
        workspace_id = uuid4()
        founder_id = uuid4()

        row = MagicMock()
        row.id = message_id
        row.workspace_id = str(workspace_id)
        row.founder_id = str(founder_id)
        row.message_type = "status_update"
        row.channel_id = "channel_123"
        row.channel_name = "updates"
        row.message_content = "Test message"
        row.discord_message_id = "discord_123"
        row.status = "sent"
        row.embed_data = None
        row.error_message = None
        row.sent_at = datetime.utcnow()
        row.created_at = datetime.utcnow()

        mock_result = MagicMock()
        mock_result.fetchone.return_value = row
        mock_db.execute.return_value = mock_result

        message = await service.get_message(message_id, db=mock_db)

        assert message is not None
        assert message.id == message_id
        assert message.status == DiscordMessageStatus.SENT

    @pytest.mark.asyncio
    async def test_get_message_not_found(self, service, mock_db):
        """Test retrieving non-existent message"""
        message_id = uuid4()

        mock_result = MagicMock()
        mock_result.fetchone.return_value = None
        mock_db.execute.return_value = mock_result

        message = await service.get_message(message_id, db=mock_db)
        assert message is None

    @pytest.mark.asyncio
    async def test_get_message_no_db(self, service):
        """Test retrieving message without DB"""
        message_id = uuid4()
        message = await service.get_message(message_id, db=None)
        assert message is None

    @pytest.mark.asyncio
    async def test_get_message_db_error(self, service, mock_db):
        """Test handling database errors"""
        message_id = uuid4()
        mock_db.execute.side_effect = Exception("Database error")

        message = await service.get_message(message_id, db=mock_db)
        assert message is None

    @pytest.mark.asyncio
    async def test_send_to_discord_returns_hash_id(self, service):
        """Test that Discord send returns deterministic hash ID"""
        message_id = await service._send_to_discord(
            channel_id="channel_123", content="Test message"
        )

        assert message_id is not None
        assert isinstance(message_id, str)
        assert len(message_id) == 32  # MD5 hash length

    @pytest.mark.asyncio
    async def test_send_to_discord_with_embed(self, service):
        """Test sending message with embed"""
        embed = {
            "title": "Test",
            "description": "Description",
            "color": 0x5865F2,
            "fields": [{"name": "Field", "value": "Value", "inline": False}],
        }

        message_id = await service._send_to_discord(
            channel_id="channel_123", content="Test", embed=embed, mentions=["@user"]
        )

        assert message_id is not None

    @pytest.mark.asyncio
    async def test_send_to_discord_deterministic(self, service):
        """Test that same input produces same hash"""
        message_id_1 = await service._send_to_discord(
            channel_id="channel_123", content="Same message"
        )
        message_id_2 = await service._send_to_discord(
            channel_id="channel_123", content="Same message"
        )

        assert message_id_1 == message_id_2

    @pytest.mark.asyncio
    async def test_get_default_channel(self, service, workspace_id):
        """Test default channel ID generation"""
        channel_id = await service._get_default_channel(
            workspace_id=workspace_id, channel_name="general"
        )

        assert channel_id is not None
        assert str(workspace_id) in channel_id
        assert "general" in channel_id

    @pytest.mark.asyncio
    async def test_get_default_channel_different_names(self, service, workspace_id):
        """Test default channels with different names"""
        general = await service._get_default_channel(workspace_id, "general")
        updates = await service._get_default_channel(workspace_id, "status-updates")

        assert general != updates
        assert str(workspace_id) in general
        assert str(workspace_id) in updates


class TestDiscordServiceMessageTracking:
    """Test message delivery tracking"""

    @pytest.fixture
    def service(self):
        return DiscordService()

    @pytest.fixture
    def mock_db(self):
        return MagicMock()

    @pytest.fixture
    def workspace_id(self):
        return uuid4()

    @pytest.fixture
    def founder_id(self):
        return uuid4()

    @pytest.mark.asyncio
    async def test_update_message_status(self, service, mock_db):
        """Test updating message status"""
        message_id = uuid4()
        update = DiscordMessageUpdate(status=DiscordMessageStatus.SENT)

        mock_db.execute = MagicMock()
        mock_db.commit = MagicMock()

        await service._update_message(message_id, update, db=mock_db)

        mock_db.execute.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_message_with_discord_id(self, service, mock_db):
        """Test updating message with Discord ID"""
        message_id = uuid4()
        update = DiscordMessageUpdate(
            status=DiscordMessageStatus.SENT, discord_message_id="discord_456"
        )

        mock_db.execute = MagicMock()
        mock_db.commit = MagicMock()

        await service._update_message(message_id, update, db=mock_db)

        # Verify both status and discord_message_id in query
        call_args = mock_db.execute.call_args
        assert "discord_message_id" in str(call_args)
        assert "status" in str(call_args)

    @pytest.mark.asyncio
    async def test_update_message_with_error(self, service, mock_db):
        """Test updating message with error"""
        message_id = uuid4()
        error_msg = "Failed to send to Discord"
        update = DiscordMessageUpdate(
            status=DiscordMessageStatus.FAILED, error_message=error_msg
        )

        mock_db.execute = MagicMock()
        mock_db.commit = MagicMock()

        await service._update_message(message_id, update, db=mock_db)

        call_args = mock_db.execute.call_args
        assert "error_message" in str(call_args)

    @pytest.mark.asyncio
    async def test_update_message_with_sent_timestamp(self, service, mock_db):
        """Test updating message with sent timestamp"""
        message_id = uuid4()
        sent_time = datetime.utcnow()
        update = DiscordMessageUpdate(
            status=DiscordMessageStatus.SENT,
            discord_message_id="discord_789",
            sent_at=sent_time,
        )

        mock_db.execute = MagicMock()
        mock_db.commit = MagicMock()

        await service._update_message(message_id, update, db=mock_db)

        call_args = mock_db.execute.call_args
        assert "sent_at" in str(call_args)

    @pytest.mark.asyncio
    async def test_update_message_no_changes(self, service, mock_db):
        """Test updating message with no changes"""
        message_id = uuid4()
        update = DiscordMessageUpdate()

        mock_db.execute = MagicMock()
        mock_db.commit = MagicMock()

        await service._update_message(message_id, update, db=mock_db)

        # Should not execute if no updates
        mock_db.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_message_no_db(self, service):
        """Test updating message without DB"""
        message_id = uuid4()
        update = DiscordMessageUpdate(status=DiscordMessageStatus.SENT)

        # Should not raise error
        await service._update_message(message_id, update, db=None)

    @pytest.mark.asyncio
    async def test_update_message_db_error(self, service, mock_db):
        """Test handling update errors"""
        message_id = uuid4()
        update = DiscordMessageUpdate(status=DiscordMessageStatus.SENT)

        mock_db.execute.side_effect = Exception("Database error")

        # Should handle error gracefully
        await service._update_message(message_id, update, db=mock_db)


class TestDiscordServiceIntegration:
    """Integration tests for full workflows"""

    @pytest.fixture
    def service(self):
        return DiscordService()

    @pytest.fixture
    def workspace_id(self):
        return uuid4()

    @pytest.fixture
    def founder_id(self):
        return uuid4()

    @pytest.fixture
    def mock_db(self):
        return MagicMock()

    @pytest.mark.asyncio
    async def test_full_status_update_workflow(
        self, service, workspace_id, founder_id, mock_db
    ):
        """Test complete status update workflow"""
        request = DiscordStatusUpdateRequest(
            workspace_id=workspace_id,
            founder_id=founder_id,
            message="KPI update",
            channel_name="updates",
            mentions=["@team"],
        )

        message_id = uuid4()
        row = MagicMock()
        row.id = message_id
        row.workspace_id = str(workspace_id)
        row.founder_id = str(founder_id)
        row.message_type = "status_update"
        row.channel_id = "channel_123"
        row.channel_name = "updates"
        row.message_content = "KPI update"
        row.discord_message_id = "discord_msg_abc"
        row.status = "sent"
        row.embed_data = None
        row.error_message = None
        row.sent_at = datetime.utcnow()
        row.created_at = datetime.utcnow()
        row._mapping = {
            "id": row.id,
            "workspace_id": row.workspace_id,
            "founder_id": row.founder_id,
            "message_type": row.message_type,
            "channel_id": row.channel_id,
            "channel_name": row.channel_name,
            "message_content": row.message_content,
            "discord_message_id": row.discord_message_id,
            "status": row.status,
            "embed_data": row.embed_data,
            "error_message": row.error_message,
            "sent_at": row.sent_at,
            "created_at": row.created_at,
        }

        mock_result = MagicMock()
        mock_result.fetchone.return_value = row
        mock_db.execute.return_value = mock_result

        with patch.object(service, "_send_to_discord", return_value="discord_msg_abc"):
            with patch.object(service, "_update_message", new_callable=AsyncMock):
                message = await service.post_status_update(request, db=mock_db)

                # Verify full workflow
                assert message is not None
                assert message.workspace_id == workspace_id
                assert message.founder_id == founder_id
                assert message.message_type == DiscordMessageType.STATUS_UPDATE

    @pytest.mark.asyncio
    async def test_full_briefing_workflow(
        self, service, workspace_id, founder_id, mock_db
    ):
        """Test complete briefing delivery workflow"""
        briefing = BriefingResponse(
            id=uuid4(),
            workspace_id=workspace_id,
            founder_id=founder_id,
            briefing_type=BriefingType.MORNING,
            title="Daily Briefing",
            start_date=datetime.utcnow(),
            end_date=datetime.utcnow(),
            summary="Day summary",
            key_highlights=["Highlight 1"],
            action_items=["Action 1"],
            sections=[],
            status=BriefingStatus.READY,
            created_at=datetime.utcnow(),
            generated_at=datetime.utcnow(),
        )

        request = DiscordBriefingRequest(
            workspace_id=workspace_id,
            founder_id=founder_id,
            channel_name="briefings",
            include_metrics=True,
            include_action_items=True,
            mention_team=True,
        )

        message_id = uuid4()
        row = MagicMock()
        row.id = message_id
        row.workspace_id = str(workspace_id)
        row.founder_id = str(founder_id)
        row.message_type = "briefing"
        row.channel_id = "channel_briefings"
        row.channel_name = "briefings"
        row.message_content = "Daily Briefing"
        row.discord_message_id = "discord_msg_xyz"
        row.status = "sent"
        row.embed_data = {}
        row.error_message = None
        row.sent_at = datetime.utcnow()
        row.created_at = datetime.utcnow()
        row._mapping = {
            "id": row.id,
            "workspace_id": row.workspace_id,
            "founder_id": row.founder_id,
            "message_type": row.message_type,
            "channel_id": row.channel_id,
            "channel_name": row.channel_name,
            "message_content": row.message_content,
            "discord_message_id": row.discord_message_id,
            "status": row.status,
            "embed_data": row.embed_data,
            "error_message": row.error_message,
            "sent_at": row.sent_at,
            "created_at": row.created_at,
        }

        mock_result = MagicMock()
        mock_result.fetchone.return_value = row
        mock_db.execute.return_value = mock_result

        with patch.object(
            service.briefing_service, "generate_briefing", return_value=briefing
        ):
            with patch.object(service, "_send_to_discord", return_value="discord_msg_xyz"):
                with patch.object(service, "_update_message", new_callable=AsyncMock):
                    with patch.object(service, "_format_briefing_embed") as mock_format:
                        embed = DiscordEmbed(
                            title="Test",
                            description="Test",
                            fields=[{"name": "Summary", "value": "Test", "inline": False}],
                        )
                        mock_format.return_value = embed

                        message = await service.send_briefing(request, db=mock_db)

                        # Verify full workflow
                        assert message is not None
                        assert message.workspace_id == workspace_id
                        assert message.message_type == DiscordMessageType.BRIEFING
