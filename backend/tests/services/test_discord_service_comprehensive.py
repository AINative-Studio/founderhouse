"""
Comprehensive tests for Discord Service
Target: 90%+ coverage of discord_service.py
Tests all methods: post_status_update, send_briefing, get_message,
_send_to_discord, _get_default_channel, _format_briefing_embed, _update_message
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
    DiscordMessageUpdate
)
from app.models.briefing import BriefingResponse, BriefingType, BriefingStatus


class TestDiscordServiceComprehensive:
    """Comprehensive test suite for DiscordService"""

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
    def message_id(self):
        """Sample message ID"""
        return uuid4()

    @pytest.fixture
    def mock_db_session(self):
        """Create mock database session"""
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_session.execute.return_value = mock_result
        mock_session.commit = MagicMock()
        return mock_session

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
            created_at=datetime.utcnow(),
            generated_at=datetime.utcnow()
        )

    def create_mock_db_row(self, workspace_id, founder_id, message_id, message_type="status_update",
                          status="pending", with_embed=False):
        """Helper to create mock database row"""
        row = MagicMock()
        row.id = message_id
        row.workspace_id = str(workspace_id)
        row.founder_id = str(founder_id)
        row.message_type = message_type
        row.channel_id = "channel_123"
        row.channel_name = "status-updates"
        row.message_content = "Test message"
        row.discord_message_id = "discord_msg_123" if status == "sent" else None
        row.status = status
        row.embed_data = {"title": "Test Embed"} if with_embed else None
        row.error_message = "Test error" if status == "failed" else None
        row.sent_at = datetime.utcnow() if status == "sent" else None
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
            "created_at": row.created_at
        }
        return row

    # ==================== POST STATUS UPDATE TESTS ====================

    @pytest.mark.asyncio
    async def test_post_status_update_no_db(self, service, sample_status_update):
        """Test post_status_update returns None when no db session provided"""
        result = await service.post_status_update(sample_status_update, db=None)
        assert result is None

    @pytest.mark.asyncio
    async def test_post_status_update_success(self, service, sample_status_update,
                                             workspace_id, founder_id, message_id, mock_db_session):
        """Test successful status update posting"""
        # Create mock rows for insert and get_message
        insert_row = self.create_mock_db_row(workspace_id, founder_id, message_id)
        sent_row = self.create_mock_db_row(workspace_id, founder_id, message_id, status="sent")

        mock_result1 = MagicMock()
        mock_result1.fetchone.return_value = insert_row

        mock_result2 = MagicMock()
        mock_result2.fetchone.return_value = sent_row

        mock_db_session.execute.side_effect = [mock_result1, mock_result2, mock_result2]

        with patch.object(service, '_send_to_discord', return_value="discord_msg_123") as mock_send:
            result = await service.post_status_update(sample_status_update, db=mock_db_session)

        assert result is not None
        assert isinstance(result, DiscordMessageResponse)
        assert result.workspace_id == workspace_id
        mock_send.assert_called_once()
        assert mock_db_session.commit.call_count >= 1

    @pytest.mark.asyncio
    async def test_post_status_update_with_embed(self, service, sample_status_update,
                                                workspace_id, founder_id, message_id, mock_db_session):
        """Test posting status update with embed data"""
        sample_status_update.embed = {
            "title": "Revenue Alert",
            "description": "Significant increase",
            "color": 0x00FF00
        }

        insert_row = self.create_mock_db_row(workspace_id, founder_id, message_id, with_embed=True)
        sent_row = self.create_mock_db_row(workspace_id, founder_id, message_id, status="sent", with_embed=True)

        mock_result1 = MagicMock()
        mock_result1.fetchone.return_value = insert_row

        mock_result2 = MagicMock()
        mock_result2.fetchone.return_value = sent_row

        mock_db_session.execute.side_effect = [mock_result1, mock_result2, mock_result2]

        with patch.object(service, '_send_to_discord', return_value="discord_msg_123"):
            result = await service.post_status_update(sample_status_update, db=mock_db_session)

        assert result is not None

    @pytest.mark.asyncio
    async def test_post_status_update_with_channel_id(self, service, sample_status_update,
                                                     workspace_id, founder_id, message_id, mock_db_session):
        """Test posting with explicit channel_id"""
        sample_status_update.channel_id = "explicit_channel_456"

        insert_row = self.create_mock_db_row(workspace_id, founder_id, message_id)
        sent_row = self.create_mock_db_row(workspace_id, founder_id, message_id, status="sent")

        mock_result1 = MagicMock()
        mock_result1.fetchone.return_value = insert_row

        mock_result2 = MagicMock()
        mock_result2.fetchone.return_value = sent_row

        mock_db_session.execute.side_effect = [mock_result1, mock_result2, mock_result2]

        with patch.object(service, '_send_to_discord', return_value="discord_msg_123") as mock_send:
            result = await service.post_status_update(sample_status_update, db=mock_db_session)

        assert result is not None
        # Verify explicit channel_id was used
        call_kwargs = mock_send.call_args[1]
        assert call_kwargs['channel_id'] == "explicit_channel_456"

    @pytest.mark.asyncio
    async def test_post_status_update_without_channel_id(self, service, sample_status_update,
                                                        workspace_id, founder_id, message_id, mock_db_session):
        """Test posting without channel_id uses default"""
        sample_status_update.channel_id = None

        insert_row = self.create_mock_db_row(workspace_id, founder_id, message_id)
        sent_row = self.create_mock_db_row(workspace_id, founder_id, message_id, status="sent")

        mock_result1 = MagicMock()
        mock_result1.fetchone.return_value = insert_row

        mock_result2 = MagicMock()
        mock_result2.fetchone.return_value = sent_row

        mock_db_session.execute.side_effect = [mock_result1, mock_result2, mock_result2]

        with patch.object(service, '_get_default_channel', return_value="default_channel") as mock_default:
            with patch.object(service, '_send_to_discord', return_value="discord_msg_123"):
                result = await service.post_status_update(sample_status_update, db=mock_db_session)

        assert result is not None
        mock_default.assert_called_once_with(workspace_id, "status-updates")

    @pytest.mark.asyncio
    async def test_post_status_update_error_before_insert(self, service, sample_status_update, mock_db_session):
        """Test error handling before message insert"""
        mock_db_session.execute.side_effect = Exception("Database error")

        result = await service.post_status_update(sample_status_update, db=mock_db_session)

        assert result is None

    @pytest.mark.asyncio
    async def test_post_status_update_error_after_insert(self, service, sample_status_update,
                                                        workspace_id, founder_id, message_id, mock_db_session):
        """Test error handling after message insert (Discord send fails)"""
        insert_row = self.create_mock_db_row(workspace_id, founder_id, message_id)

        mock_result = MagicMock()
        mock_result.fetchone.return_value = insert_row

        mock_db_session.execute.return_value = mock_result

        with patch.object(service, '_send_to_discord', side_effect=Exception("Discord API error")):
            result = await service.post_status_update(sample_status_update, db=mock_db_session)

        assert result is None
        # Should have called update_message to mark as failed
        assert mock_db_session.execute.call_count >= 2

    # ==================== SEND BRIEFING TESTS ====================

    @pytest.mark.asyncio
    async def test_send_briefing_no_db(self, service, sample_briefing_request):
        """Test send_briefing returns None when no db session provided"""
        result = await service.send_briefing(sample_briefing_request, db=None)
        assert result is None

    @pytest.mark.asyncio
    async def test_send_briefing_with_briefing_id(self, service, sample_briefing_request, sample_briefing,
                                                  workspace_id, founder_id, message_id, mock_db_session):
        """Test sending existing briefing by ID"""
        sample_briefing_request.briefing_id = sample_briefing.id

        # Mock briefing fetch
        briefing_row = MagicMock()
        briefing_row.id = sample_briefing.id
        briefing_row.workspace_id = str(sample_briefing.workspace_id)
        briefing_row.founder_id = str(sample_briefing.founder_id)
        briefing_row.briefing_type = sample_briefing.briefing_type.value
        briefing_row.title = sample_briefing.title
        briefing_row.start_date = sample_briefing.start_date
        briefing_row.end_date = sample_briefing.end_date
        briefing_row.summary = sample_briefing.summary
        briefing_row.key_highlights = sample_briefing.key_highlights
        briefing_row.action_items = sample_briefing.action_items
        briefing_row.sections = sample_briefing.sections
        briefing_row.status = sample_briefing.status.value
        briefing_row.created_at = sample_briefing.created_at
        briefing_row.generated_at = sample_briefing.generated_at
        briefing_row._mapping = {
            "id": briefing_row.id,
            "workspace_id": briefing_row.workspace_id,
            "founder_id": briefing_row.founder_id,
            "briefing_type": briefing_row.briefing_type,
            "title": briefing_row.title,
            "start_date": briefing_row.start_date,
            "end_date": briefing_row.end_date,
            "summary": briefing_row.summary,
            "key_highlights": briefing_row.key_highlights,
            "action_items": briefing_row.action_items,
            "sections": briefing_row.sections,
            "status": briefing_row.status,
            "created_at": briefing_row.created_at,
            "generated_at": briefing_row.generated_at
        }

        insert_row = self.create_mock_db_row(workspace_id, founder_id, message_id, message_type="briefing")
        sent_row = self.create_mock_db_row(workspace_id, founder_id, message_id,
                                          message_type="briefing", status="sent")

        mock_result1 = MagicMock()
        mock_result1.fetchone.return_value = briefing_row

        mock_result2 = MagicMock()
        mock_result2.fetchone.return_value = insert_row

        mock_result3 = MagicMock()
        mock_result3.fetchone.return_value = sent_row

        mock_db_session.execute.side_effect = [mock_result1, mock_result2, mock_result3, mock_result3]

        with patch.object(service, '_format_briefing_embed') as mock_format:
            mock_embed = MagicMock()
            mock_embed.model_dump.return_value = {
                "title": "Test",
                "description": "Test",
                "fields": [],
                "color": 0x5865F2
            }
            mock_format.return_value = mock_embed

            with patch.object(service, '_send_to_discord', return_value="discord_msg_123"):
                result = await service.send_briefing(sample_briefing_request, db=mock_db_session)

        assert result is not None
        assert result.message_type == DiscordMessageType.BRIEFING

    @pytest.mark.asyncio
    async def test_send_briefing_briefing_not_found(self, service, sample_briefing_request, mock_db_session):
        """Test sending non-existent briefing"""
        sample_briefing_request.briefing_id = uuid4()

        mock_result = MagicMock()
        mock_result.fetchone.return_value = None
        mock_db_session.execute.return_value = mock_result

        result = await service.send_briefing(sample_briefing_request, db=mock_db_session)

        assert result is None

    @pytest.mark.asyncio
    async def test_send_briefing_generate_new(self, service, sample_briefing_request, sample_briefing,
                                             workspace_id, founder_id, message_id, mock_db_session):
        """Test sending newly generated briefing"""
        # No briefing_id, so should generate new
        sample_briefing_request.briefing_id = None

        insert_row = self.create_mock_db_row(workspace_id, founder_id, message_id, message_type="briefing")
        sent_row = self.create_mock_db_row(workspace_id, founder_id, message_id,
                                          message_type="briefing", status="sent")

        mock_result1 = MagicMock()
        mock_result1.fetchone.return_value = insert_row

        mock_result2 = MagicMock()
        mock_result2.fetchone.return_value = sent_row

        mock_db_session.execute.side_effect = [mock_result1, mock_result2, mock_result2]

        with patch.object(service.briefing_service, 'generate_briefing', return_value=sample_briefing):
            with patch.object(service, '_format_briefing_embed') as mock_format:
                mock_embed = MagicMock()
                mock_embed.model_dump.return_value = {"title": "Test", "fields": [], "color": 0x5865F2}
                mock_format.return_value = mock_embed

                with patch.object(service, '_send_to_discord', return_value="discord_msg_123"):
                    result = await service.send_briefing(sample_briefing_request, db=mock_db_session)

        assert result is not None

    @pytest.mark.asyncio
    async def test_send_briefing_no_briefing_available(self, service, sample_briefing_request, mock_db_session):
        """Test when briefing generation returns None"""
        sample_briefing_request.briefing_id = None

        with patch.object(service.briefing_service, 'generate_briefing', return_value=None):
            result = await service.send_briefing(sample_briefing_request, db=mock_db_session)

        assert result is None

    @pytest.mark.asyncio
    async def test_send_briefing_with_team_mention(self, service, sample_briefing_request, sample_briefing,
                                                   workspace_id, founder_id, message_id, mock_db_session):
        """Test briefing with mention_team=True"""
        sample_briefing_request.mention_team = True
        sample_briefing_request.briefing_id = None

        insert_row = self.create_mock_db_row(workspace_id, founder_id, message_id, message_type="briefing")
        sent_row = self.create_mock_db_row(workspace_id, founder_id, message_id,
                                          message_type="briefing", status="sent")

        mock_result1 = MagicMock()
        mock_result1.fetchone.return_value = insert_row

        mock_result2 = MagicMock()
        mock_result2.fetchone.return_value = sent_row

        mock_db_session.execute.side_effect = [mock_result1, mock_result2, mock_result2]

        with patch.object(service.briefing_service, 'generate_briefing', return_value=sample_briefing):
            with patch.object(service, '_format_briefing_embed') as mock_format:
                mock_embed = MagicMock()
                mock_embed.model_dump.return_value = {"title": "Test", "fields": [], "color": 0x5865F2}
                mock_format.return_value = mock_embed

                with patch.object(service, '_send_to_discord', return_value="discord_msg_123") as mock_send:
                    result = await service.send_briefing(sample_briefing_request, db=mock_db_session)

        assert result is not None
        # Verify @here mention was added
        call_kwargs = mock_send.call_args[1]
        assert "@here" in call_kwargs['mentions']

    @pytest.mark.asyncio
    async def test_send_briefing_without_team_mention(self, service, sample_briefing_request, sample_briefing,
                                                      workspace_id, founder_id, message_id, mock_db_session):
        """Test briefing with mention_team=False"""
        sample_briefing_request.mention_team = False
        sample_briefing_request.briefing_id = None

        insert_row = self.create_mock_db_row(workspace_id, founder_id, message_id, message_type="briefing")
        sent_row = self.create_mock_db_row(workspace_id, founder_id, message_id,
                                          message_type="briefing", status="sent")

        mock_result1 = MagicMock()
        mock_result1.fetchone.return_value = insert_row

        mock_result2 = MagicMock()
        mock_result2.fetchone.return_value = sent_row

        mock_db_session.execute.side_effect = [mock_result1, mock_result2, mock_result2]

        with patch.object(service.briefing_service, 'generate_briefing', return_value=sample_briefing):
            with patch.object(service, '_format_briefing_embed') as mock_format:
                mock_embed = MagicMock()
                mock_embed.model_dump.return_value = {"title": "Test", "fields": [], "color": 0x5865F2}
                mock_format.return_value = mock_embed

                with patch.object(service, '_send_to_discord', return_value="discord_msg_123") as mock_send:
                    result = await service.send_briefing(sample_briefing_request, db=mock_db_session)

        assert result is not None
        call_kwargs = mock_send.call_args[1]
        assert len(call_kwargs['mentions']) == 0

    @pytest.mark.asyncio
    async def test_send_briefing_with_channel_id(self, service, sample_briefing_request, sample_briefing,
                                                 workspace_id, founder_id, message_id, mock_db_session):
        """Test sending briefing with explicit channel_id"""
        sample_briefing_request.channel_id = "explicit_briefing_channel"
        sample_briefing_request.briefing_id = None

        insert_row = self.create_mock_db_row(workspace_id, founder_id, message_id, message_type="briefing")
        sent_row = self.create_mock_db_row(workspace_id, founder_id, message_id,
                                          message_type="briefing", status="sent")

        mock_result1 = MagicMock()
        mock_result1.fetchone.return_value = insert_row

        mock_result2 = MagicMock()
        mock_result2.fetchone.return_value = sent_row

        mock_db_session.execute.side_effect = [mock_result1, mock_result2, mock_result2]

        with patch.object(service.briefing_service, 'generate_briefing', return_value=sample_briefing):
            with patch.object(service, '_format_briefing_embed') as mock_format:
                mock_embed = MagicMock()
                mock_embed.model_dump.return_value = {"title": "Test", "fields": [], "color": 0x5865F2}
                mock_format.return_value = mock_embed

                with patch.object(service, '_send_to_discord', return_value="discord_msg_123") as mock_send:
                    result = await service.send_briefing(sample_briefing_request, db=mock_db_session)

        assert result is not None
        call_kwargs = mock_send.call_args[1]
        assert call_kwargs['channel_id'] == "explicit_briefing_channel"

    @pytest.mark.asyncio
    async def test_send_briefing_error_after_insert(self, service, sample_briefing_request, sample_briefing,
                                                    workspace_id, founder_id, message_id, mock_db_session):
        """Test error handling when Discord send fails after message insert"""
        sample_briefing_request.briefing_id = None

        insert_row = self.create_mock_db_row(workspace_id, founder_id, message_id, message_type="briefing")

        mock_result = MagicMock()
        mock_result.fetchone.return_value = insert_row
        mock_db_session.execute.return_value = mock_result

        with patch.object(service.briefing_service, 'generate_briefing', return_value=sample_briefing):
            with patch.object(service, '_send_to_discord', side_effect=Exception("Discord error")):
                result = await service.send_briefing(sample_briefing_request, db=mock_db_session)

        assert result is None

    # ==================== GET MESSAGE TESTS ====================

    @pytest.mark.asyncio
    async def test_get_message_no_db(self, service, message_id):
        """Test get_message returns None when no db session provided"""
        result = await service.get_message(message_id, db=None)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_message_success(self, service, workspace_id, founder_id,
                                       message_id, mock_db_session):
        """Test successful message retrieval"""
        mock_row = self.create_mock_db_row(workspace_id, founder_id, message_id, status="sent")

        mock_result = MagicMock()
        mock_result.fetchone.return_value = mock_row
        mock_db_session.execute.return_value = mock_result

        result = await service.get_message(message_id, db=mock_db_session)

        assert result is not None
        assert isinstance(result, DiscordMessageResponse)
        assert result.id == message_id
        assert result.workspace_id == workspace_id
        assert result.founder_id == founder_id

    @pytest.mark.asyncio
    async def test_get_message_not_found(self, service, message_id, mock_db_session):
        """Test getting non-existent message"""
        mock_result = MagicMock()
        mock_result.fetchone.return_value = None
        mock_db_session.execute.return_value = mock_result

        result = await service.get_message(message_id, db=mock_db_session)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_message_with_embed(self, service, workspace_id, founder_id,
                                         message_id, mock_db_session):
        """Test getting message with embed_data"""
        mock_row = self.create_mock_db_row(workspace_id, founder_id, message_id,
                                           status="sent", with_embed=True)

        mock_result = MagicMock()
        mock_result.fetchone.return_value = mock_row
        mock_db_session.execute.return_value = mock_result

        result = await service.get_message(message_id, db=mock_db_session)

        assert result is not None
        assert result.embed_data is not None

    @pytest.mark.asyncio
    async def test_get_message_error(self, service, message_id, mock_db_session):
        """Test error handling in get_message"""
        mock_db_session.execute.side_effect = Exception("Database error")

        result = await service.get_message(message_id, db=mock_db_session)

        assert result is None

    # ==================== HELPER METHOD TESTS ====================

    @pytest.mark.asyncio
    async def test_send_to_discord_basic(self, service):
        """Test _send_to_discord generates message ID"""
        message_id = await service._send_to_discord(
            channel_id="channel_123",
            content="Test message",
            embed=None,
            mentions=[]
        )

        assert message_id is not None
        assert isinstance(message_id, str)
        assert len(message_id) > 0

    @pytest.mark.asyncio
    async def test_send_to_discord_with_embed(self, service):
        """Test _send_to_discord with embed"""
        embed = {
            "title": "Test Embed",
            "description": "Test description",
            "color": 0x5865F2,
            "fields": [{"name": "Field", "value": "Value"}]
        }

        message_id = await service._send_to_discord(
            channel_id="channel_123",
            content="Test with embed",
            embed=embed,
            mentions=["@user1", "@user2"]
        )

        assert message_id is not None

    @pytest.mark.asyncio
    async def test_send_to_discord_deterministic(self, service):
        """Test that same input produces same message ID"""
        message_id1 = await service._send_to_discord(
            channel_id="channel_123",
            content="Test message",
            embed=None,
            mentions=[]
        )

        message_id2 = await service._send_to_discord(
            channel_id="channel_123",
            content="Test message",
            embed=None,
            mentions=[]
        )

        assert message_id1 == message_id2

    @pytest.mark.asyncio
    async def test_get_default_channel(self, service, workspace_id):
        """Test _get_default_channel generates channel ID"""
        channel_id = await service._get_default_channel(
            workspace_id=workspace_id,
            channel_name="general"
        )

        assert channel_id is not None
        assert str(workspace_id) in channel_id
        assert "general" in channel_id

    @pytest.mark.asyncio
    async def test_get_default_channel_different_names(self, service, workspace_id):
        """Test default channel for different channel names"""
        channel1 = await service._get_default_channel(workspace_id, "status-updates")
        channel2 = await service._get_default_channel(workspace_id, "daily-briefings")

        assert channel1 != channel2
        assert "status-updates" in channel1
        assert "daily-briefings" in channel2

    @pytest.mark.asyncio
    async def test_format_briefing_embed_full(self, service, sample_briefing):
        """Test formatting briefing with all fields"""
        embed = await service._format_briefing_embed(
            briefing=sample_briefing,
            include_metrics=True,
            include_action_items=True
        )

        assert isinstance(embed, DiscordEmbed)
        assert embed.title == sample_briefing.title
        assert embed.color == 0x5865F2
        assert len(embed.fields) >= 3  # Summary, Highlights, Action Items

        field_names = [f["name"] for f in embed.fields]
        assert "Summary" in field_names
        assert "Key Highlights" in field_names
        assert "Action Items" in field_names

    @pytest.mark.asyncio
    async def test_format_briefing_embed_without_action_items(self, service, sample_briefing):
        """Test formatting without action items"""
        embed = await service._format_briefing_embed(
            briefing=sample_briefing,
            include_action_items=False
        )

        field_names = [f["name"] for f in embed.fields]
        assert "Action Items" not in field_names

    @pytest.mark.asyncio
    async def test_format_briefing_embed_no_highlights(self, service, sample_briefing):
        """Test formatting when briefing has no highlights"""
        sample_briefing.key_highlights = []

        embed = await service._format_briefing_embed(sample_briefing)

        assert isinstance(embed, DiscordEmbed)
        field_names = [f["name"] for f in embed.fields]
        # Should still have summary
        assert "Summary" in field_names

    @pytest.mark.asyncio
    async def test_format_briefing_embed_no_action_items(self, service, sample_briefing):
        """Test formatting when briefing has no action items"""
        sample_briefing.action_items = []

        embed = await service._format_briefing_embed(
            sample_briefing,
            include_action_items=True
        )

        field_names = [f["name"] for f in embed.fields]
        # Should not include action items if none exist
        assert "Action Items" not in field_names

    @pytest.mark.asyncio
    async def test_format_briefing_embed_no_summary(self, service, sample_briefing):
        """Test formatting when briefing has no summary"""
        sample_briefing.summary = None

        embed = await service._format_briefing_embed(sample_briefing)

        summary_field = next((f for f in embed.fields if f["name"] == "Summary"), None)
        assert summary_field is not None
        assert summary_field["value"] == "No summary available"

    @pytest.mark.asyncio
    async def test_format_briefing_embed_truncates_summary(self, service, sample_briefing):
        """Test that long summary is truncated to Discord's 1024 char limit"""
        sample_briefing.summary = "A" * 2000

        embed = await service._format_briefing_embed(sample_briefing)

        summary_field = next(f for f in embed.fields if f["name"] == "Summary")
        assert len(summary_field["value"]) <= 1024

    @pytest.mark.asyncio
    async def test_format_briefing_embed_truncates_highlights(self, service, sample_briefing):
        """Test that highlights are limited and truncated"""
        sample_briefing.key_highlights = ["Highlight " + str(i) for i in range(10)]

        embed = await service._format_briefing_embed(sample_briefing)

        highlights_field = next((f for f in embed.fields if f["name"] == "Key Highlights"), None)
        assert highlights_field is not None
        # Should truncate to 1024 chars
        assert len(highlights_field["value"]) <= 1024

    @pytest.mark.asyncio
    async def test_format_briefing_embed_truncates_actions(self, service, sample_briefing):
        """Test that action items are limited and truncated"""
        sample_briefing.action_items = ["Action " + str(i) for i in range(10)]

        embed = await service._format_briefing_embed(
            sample_briefing,
            include_action_items=True
        )

        actions_field = next((f for f in embed.fields if f["name"] == "Action Items"), None)
        assert actions_field is not None
        assert len(actions_field["value"]) <= 1024

    @pytest.mark.asyncio
    async def test_format_briefing_embed_has_footer(self, service, sample_briefing):
        """Test that embed includes footer"""
        embed = await service._format_briefing_embed(sample_briefing)

        assert embed.footer is not None
        assert embed.footer["text"] == "AI Chief of Staff"

    @pytest.mark.asyncio
    async def test_format_briefing_embed_has_timestamp(self, service, sample_briefing):
        """Test that embed includes timestamp"""
        embed = await service._format_briefing_embed(sample_briefing)

        assert embed.timestamp is not None
        assert isinstance(embed.timestamp, datetime)

    # ==================== UPDATE MESSAGE TESTS ====================

    @pytest.mark.asyncio
    async def test_update_message_no_db(self, service, message_id):
        """Test _update_message returns early when no db session"""
        update = DiscordMessageUpdate(status=DiscordMessageStatus.SENT)

        # Should not raise exception
        await service._update_message(message_id, update, db=None)

    @pytest.mark.asyncio
    async def test_update_message_status_only(self, service, message_id, mock_db_session):
        """Test updating only status"""
        update = DiscordMessageUpdate(status=DiscordMessageStatus.SENT)

        await service._update_message(message_id, update, db=mock_db_session)

        mock_db_session.execute.assert_called_once()
        mock_db_session.commit.assert_called_once()

        call_args = mock_db_session.execute.call_args[0]
        query = str(call_args[0])
        assert "status = :status" in query

    @pytest.mark.asyncio
    async def test_update_message_discord_id(self, service, message_id, mock_db_session):
        """Test updating discord_message_id"""
        update = DiscordMessageUpdate(discord_message_id="discord_123")

        await service._update_message(message_id, update, db=mock_db_session)

        call_args = mock_db_session.execute.call_args[0]
        query = str(call_args[0])
        assert "discord_message_id = :discord_message_id" in query

    @pytest.mark.asyncio
    async def test_update_message_error_message(self, service, message_id, mock_db_session):
        """Test updating error_message"""
        update = DiscordMessageUpdate(
            status=DiscordMessageStatus.FAILED,
            error_message="Discord API error"
        )

        await service._update_message(message_id, update, db=mock_db_session)

        call_args = mock_db_session.execute.call_args[0]
        query = str(call_args[0])
        assert "error_message = :error_message" in query

    @pytest.mark.asyncio
    async def test_update_message_sent_at(self, service, message_id, mock_db_session):
        """Test updating sent_at timestamp"""
        now = datetime.utcnow()
        update = DiscordMessageUpdate(sent_at=now)

        await service._update_message(message_id, update, db=mock_db_session)

        call_args = mock_db_session.execute.call_args[0]
        query = str(call_args[0])
        assert "sent_at = :sent_at" in query

    @pytest.mark.asyncio
    async def test_update_message_multiple_fields(self, service, message_id, mock_db_session):
        """Test updating multiple fields at once"""
        now = datetime.utcnow()
        update = DiscordMessageUpdate(
            status=DiscordMessageStatus.SENT,
            discord_message_id="discord_123",
            sent_at=now
        )

        await service._update_message(message_id, update, db=mock_db_session)

        call_args = mock_db_session.execute.call_args[0]
        query = str(call_args[0])
        assert "status = :status" in query
        assert "discord_message_id = :discord_message_id" in query
        assert "sent_at = :sent_at" in query

    @pytest.mark.asyncio
    async def test_update_message_no_changes(self, service, message_id, mock_db_session):
        """Test that no query is executed when no fields to update"""
        update = DiscordMessageUpdate()

        await service._update_message(message_id, update, db=mock_db_session)

        # Should not execute any query
        mock_db_session.execute.assert_not_called()
        mock_db_session.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_message_error_handling(self, service, message_id, mock_db_session):
        """Test error handling in _update_message"""
        update = DiscordMessageUpdate(status=DiscordMessageStatus.SENT)
        mock_db_session.execute.side_effect = Exception("Database error")

        # Should not raise exception
        await service._update_message(message_id, update, db=mock_db_session)

    # ==================== EDGE CASES AND ERROR SCENARIOS ====================

    @pytest.mark.asyncio
    async def test_service_initialization(self, service):
        """Test service initializes correctly"""
        assert service.logger is not None
        assert service.settings is not None
        assert service.briefing_service is not None

    @pytest.mark.asyncio
    async def test_post_status_update_empty_embed(self, service, sample_status_update,
                                                  workspace_id, founder_id, message_id, mock_db_session):
        """Test posting with None embed is handled correctly"""
        sample_status_update.embed = None

        insert_row = self.create_mock_db_row(workspace_id, founder_id, message_id)
        sent_row = self.create_mock_db_row(workspace_id, founder_id, message_id, status="sent")

        mock_result1 = MagicMock()
        mock_result1.fetchone.return_value = insert_row

        mock_result2 = MagicMock()
        mock_result2.fetchone.return_value = sent_row

        mock_db_session.execute.side_effect = [mock_result1, mock_result2, mock_result2]

        with patch.object(service, '_send_to_discord', return_value="discord_msg_123"):
            result = await service.post_status_update(sample_status_update, db=mock_db_session)

        assert result is not None

    @pytest.mark.asyncio
    async def test_send_briefing_with_metrics_flag(self, service, sample_briefing_request,
                                                   sample_briefing, workspace_id, founder_id,
                                                   message_id, mock_db_session):
        """Test include_metrics parameter is passed correctly"""
        sample_briefing_request.include_metrics = False
        sample_briefing_request.briefing_id = None

        insert_row = self.create_mock_db_row(workspace_id, founder_id, message_id, message_type="briefing")
        sent_row = self.create_mock_db_row(workspace_id, founder_id, message_id,
                                          message_type="briefing", status="sent")

        mock_result1 = MagicMock()
        mock_result1.fetchone.return_value = insert_row

        mock_result2 = MagicMock()
        mock_result2.fetchone.return_value = sent_row

        mock_db_session.execute.side_effect = [mock_result1, mock_result2, mock_result2]

        with patch.object(service.briefing_service, 'generate_briefing', return_value=sample_briefing):
            with patch.object(service, '_format_briefing_embed') as mock_format:
                mock_format.return_value = DiscordEmbed(
                    title="Test",
                    description="Test",
                    fields=[],
                    color=0x5865F2
                )
                with patch.object(service, '_send_to_discord', return_value="discord_msg_123"):
                    result = await service.send_briefing(sample_briefing_request, db=mock_db_session)

        assert result is not None
        # Verify include_metrics was passed
        mock_format.assert_called_once()
        call_kwargs = mock_format.call_args[1]
        assert call_kwargs['include_metrics'] == False
