"""
Unit tests for Discord Connector
Tests Discord bot interactions, message handling, and guild operations
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from app.connectors.discord_connector import DiscordConnector
from app.connectors.base_connector import ConnectorResponse, ConnectorStatus, ConnectorError
from tests.fixtures.discord_fixtures import (
    MOCK_DISCORD_BOT,
    MOCK_DISCORD_GUILDS,
    MOCK_DISCORD_CHANNELS,
    MOCK_DISCORD_MESSAGES,
    MOCK_DISCORD_MEMBERS,
    DISCORD_EMBED_TEMPLATES,
    get_mock_guild,
    get_mock_channel,
    get_mock_message,
    create_mock_discord_message,
    create_discord_embed
)


class TestDiscordConnectorInitialization:
    """Test connector initialization"""

    def test_connector_initialization(self):
        """Test connector initializes with bot token"""
        credentials = {"bot_token": "test_bot_token"}
        connector = DiscordConnector(credentials)

        assert connector.credentials == credentials
        assert connector.platform_name == "discord"
        assert connector.base_url == "https://discord.com/api/v10"

    def test_connector_headers_use_bot_format(self):
        """Test authorization header uses Bot prefix"""
        credentials = {"bot_token": "test_bot_token"}
        connector = DiscordConnector(credentials)
        headers = connector._get_default_headers()

        assert "Authorization" in headers
        assert headers["Authorization"] == "Bot test_bot_token"

    def test_connector_platform_name(self):
        """Test platform name is correct"""
        connector = DiscordConnector({})
        assert connector.platform_name == "discord"


class TestDiscordConnectionTesting:
    """Test connection validation"""

    @pytest.mark.asyncio
    async def test_test_connection_success(self):
        """Test successful connection test"""
        connector = DiscordConnector({"bot_token": "test_token"})

        with patch.object(connector, 'get_user_info') as mock_get_user:
            mock_get_user.return_value = ConnectorResponse(
                status=ConnectorStatus.SUCCESS,
                data=MOCK_DISCORD_BOT
            )

            response = await connector.test_connection()

            assert response.status == ConnectorStatus.SUCCESS
            assert response.data["connected"] is True
            assert "user" in response.data

    @pytest.mark.asyncio
    async def test_test_connection_failure(self):
        """Test connection failure"""
        connector = DiscordConnector({})

        with patch.object(connector, 'validate_credentials') as mock_validate:
            mock_validate.side_effect = ConnectorError("No credentials provided")

            response = await connector.test_connection()

            assert response.status == ConnectorStatus.ERROR

    @pytest.mark.asyncio
    async def test_get_user_info_bot(self):
        """Test getting bot user information"""
        connector = DiscordConnector({"bot_token": "test_token"})

        with patch.object(connector, 'make_request') as mock_request:
            mock_request.return_value = ConnectorResponse(
                status=ConnectorStatus.SUCCESS,
                data=MOCK_DISCORD_BOT
            )

            response = await connector.get_user_info()

            assert response.status == ConnectorStatus.SUCCESS
            assert response.data["bot"] is True
            assert response.data["username"] == MOCK_DISCORD_BOT["username"]
            mock_request.assert_called_once_with("GET", "/users/@me")


class TestGuildOperations:
    """Test guild (server) operations"""

    @pytest.mark.asyncio
    async def test_list_guilds_success(self):
        """Test listing guilds bot is in"""
        connector = DiscordConnector({"bot_token": "test_token"})

        with patch.object(connector, 'make_request') as mock_request:
            mock_request.return_value = ConnectorResponse(
                status=ConnectorStatus.SUCCESS,
                data=MOCK_DISCORD_GUILDS
            )

            response = await connector.list_guilds()

            assert response.status == ConnectorStatus.SUCCESS
            assert len(response.data) == len(MOCK_DISCORD_GUILDS)
            mock_request.assert_called_once_with("GET", "/users/@me/guilds")

    @pytest.mark.asyncio
    async def test_get_guild_by_id(self):
        """Test getting specific guild"""
        connector = DiscordConnector({"bot_token": "test_token"})
        guild = MOCK_DISCORD_GUILDS[0]

        with patch.object(connector, 'make_request') as mock_request:
            mock_request.return_value = ConnectorResponse(
                status=ConnectorStatus.SUCCESS,
                data=guild
            )

            response = await connector.get_guild(guild["id"])

            assert response.status == ConnectorStatus.SUCCESS
            assert response.data["id"] == guild["id"]
            assert response.data["name"] == guild["name"]
            mock_request.assert_called_once_with("GET", f"/guilds/{guild['id']}")

    @pytest.mark.asyncio
    async def test_list_guild_channels(self):
        """Test listing channels in a guild"""
        connector = DiscordConnector({"bot_token": "test_token"})
        guild_id = "111111111111111111"

        with patch.object(connector, 'make_request') as mock_request:
            mock_request.return_value = ConnectorResponse(
                status=ConnectorStatus.SUCCESS,
                data=MOCK_DISCORD_CHANNELS
            )

            response = await connector.list_guild_channels(guild_id)

            assert response.status == ConnectorStatus.SUCCESS
            assert len(response.data) > 0
            mock_request.assert_called_once_with("GET", f"/guilds/{guild_id}/channels")


class TestChannelMessageOperations:
    """Test channel and message operations"""

    @pytest.mark.asyncio
    async def test_get_channel_messages_default(self):
        """Test getting messages from channel with default params"""
        connector = DiscordConnector({"bot_token": "test_token"})
        channel_id = "ch_general"

        with patch.object(connector, 'make_request') as mock_request:
            mock_request.return_value = ConnectorResponse(
                status=ConnectorStatus.SUCCESS,
                data=MOCK_DISCORD_MESSAGES
            )

            response = await connector.get_channel_messages(channel_id)

            assert response.status == ConnectorStatus.SUCCESS
            assert len(response.data) > 0
            call_args = mock_request.call_args
            assert call_args[1]["params"]["limit"] == 50

    @pytest.mark.asyncio
    async def test_get_channel_messages_with_limit(self):
        """Test getting messages with custom limit"""
        connector = DiscordConnector({"bot_token": "test_token"})
        channel_id = "ch_general"

        with patch.object(connector, 'make_request') as mock_request:
            mock_request.return_value = ConnectorResponse(
                status=ConnectorStatus.SUCCESS,
                data=MOCK_DISCORD_MESSAGES[:10]
            )

            await connector.get_channel_messages(channel_id, limit=10)

            call_args = mock_request.call_args
            assert call_args[1]["params"]["limit"] == 10

    @pytest.mark.asyncio
    async def test_get_channel_messages_before_id(self):
        """Test getting messages before a specific message ID"""
        connector = DiscordConnector({"bot_token": "test_token"})
        channel_id = "ch_general"
        before_id = "msg_123"

        with patch.object(connector, 'make_request') as mock_request:
            mock_request.return_value = ConnectorResponse(
                status=ConnectorStatus.SUCCESS,
                data=[]
            )

            await connector.get_channel_messages(channel_id, before=before_id)

            call_args = mock_request.call_args
            assert call_args[1]["params"]["before"] == before_id

    @pytest.mark.asyncio
    async def test_get_channel_messages_after_id(self):
        """Test getting messages after a specific message ID"""
        connector = DiscordConnector({"bot_token": "test_token"})
        channel_id = "ch_general"
        after_id = "msg_100"

        with patch.object(connector, 'make_request') as mock_request:
            mock_request.return_value = ConnectorResponse(
                status=ConnectorStatus.SUCCESS,
                data=MOCK_DISCORD_MESSAGES
            )

            await connector.get_channel_messages(channel_id, after=after_id)

            call_args = mock_request.call_args
            assert call_args[1]["params"]["after"] == after_id

    @pytest.mark.asyncio
    async def test_get_channel_messages_limit_cap(self):
        """Test that message limit is capped at 100"""
        connector = DiscordConnector({"bot_token": "test_token"})

        with patch.object(connector, 'make_request') as mock_request:
            mock_request.return_value = ConnectorResponse(
                status=ConnectorStatus.SUCCESS,
                data=[]
            )

            await connector.get_channel_messages("ch_test", limit=200)

            call_args = mock_request.call_args
            # Discord API max limit is 100
            assert call_args[1]["params"]["limit"] == 100


class TestSendMessages:
    """Test sending messages"""

    @pytest.mark.asyncio
    async def test_send_message_simple_text(self):
        """Test sending simple text message"""
        connector = DiscordConnector({"bot_token": "test_token"})
        channel_id = "ch_general"
        content = "Test message"

        with patch.object(connector, 'make_request') as mock_request:
            sent_message = create_mock_discord_message(content, channel_id)
            mock_request.return_value = ConnectorResponse(
                status=ConnectorStatus.SUCCESS,
                data=sent_message
            )

            response = await connector.send_message(channel_id, content)

            assert response.status == ConnectorStatus.SUCCESS
            assert response.data["content"] == content
            mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_message_with_embed(self):
        """Test sending message with embed"""
        connector = DiscordConnector({"bot_token": "test_token"})
        channel_id = "ch_general"
        content = "Check this out"
        embed = create_discord_embed("Test Embed", "Description")

        with patch.object(connector, 'make_request') as mock_request:
            mock_request.return_value = ConnectorResponse(
                status=ConnectorStatus.SUCCESS,
                data={"content": content, "embeds": [embed]}
            )

            response = await connector.send_message(
                channel_id,
                content,
                embeds=[embed]
            )

            assert response.status == ConnectorStatus.SUCCESS
            call_args = mock_request.call_args
            assert "embeds" in call_args[1]["json"]

    @pytest.mark.asyncio
    async def test_send_message_multiple_embeds(self):
        """Test sending message with multiple embeds"""
        connector = DiscordConnector({"bot_token": "test_token"})
        channel_id = "ch_general"

        embeds = [
            create_discord_embed("Embed 1", "First embed"),
            create_discord_embed("Embed 2", "Second embed")
        ]

        with patch.object(connector, 'make_request') as mock_request:
            mock_request.return_value = ConnectorResponse(
                status=ConnectorStatus.SUCCESS,
                data={"content": "", "embeds": embeds}
            )

            response = await connector.send_message(
                channel_id,
                "",
                embeds=embeds
            )

            call_args = mock_request.call_args
            assert len(call_args[1]["json"]["embeds"]) == 2


class TestGuildMembers:
    """Test guild member operations"""

    @pytest.mark.asyncio
    async def test_list_guild_members(self):
        """Test listing guild members"""
        connector = DiscordConnector({"bot_token": "test_token"})
        guild_id = "111111111111111111"

        with patch.object(connector, 'make_request') as mock_request:
            mock_request.return_value = ConnectorResponse(
                status=ConnectorStatus.SUCCESS,
                data=MOCK_DISCORD_MEMBERS
            )

            response = await connector.list_guild_members(guild_id)

            assert response.status == ConnectorStatus.SUCCESS
            assert len(response.data) == len(MOCK_DISCORD_MEMBERS)

    @pytest.mark.asyncio
    async def test_list_guild_members_with_limit(self):
        """Test listing members with custom limit"""
        connector = DiscordConnector({"bot_token": "test_token"})
        guild_id = "111111111111111111"

        with patch.object(connector, 'make_request') as mock_request:
            mock_request.return_value = ConnectorResponse(
                status=ConnectorStatus.SUCCESS,
                data=MOCK_DISCORD_MEMBERS[:50]
            )

            await connector.list_guild_members(guild_id, limit=50)

            call_args = mock_request.call_args
            assert call_args[1]["params"]["limit"] == 50

    @pytest.mark.asyncio
    async def test_list_guild_members_limit_cap(self):
        """Test that member limit is capped at 1000"""
        connector = DiscordConnector({"bot_token": "test_token"})
        guild_id = "111111111111111111"

        with patch.object(connector, 'make_request') as mock_request:
            mock_request.return_value = ConnectorResponse(
                status=ConnectorStatus.SUCCESS,
                data=[]
            )

            await connector.list_guild_members(guild_id, limit=2000)

            call_args = mock_request.call_args
            assert call_args[1]["params"]["limit"] == 1000

    @pytest.mark.asyncio
    async def test_get_guild_member(self):
        """Test getting specific guild member"""
        connector = DiscordConnector({"bot_token": "test_token"})
        guild_id = "111111111111111111"
        user_id = "usr_alice"

        with patch.object(connector, 'make_request') as mock_request:
            mock_request.return_value = ConnectorResponse(
                status=ConnectorStatus.SUCCESS,
                data=MOCK_DISCORD_MEMBERS[0]
            )

            response = await connector.get_member(guild_id, user_id)

            assert response.status == ConnectorStatus.SUCCESS
            assert response.data["user"]["id"] == user_id
            mock_request.assert_called_once_with(
                "GET",
                f"/guilds/{guild_id}/members/{user_id}"
            )


class TestErrorHandling:
    """Test error handling"""

    @pytest.mark.asyncio
    async def test_invalid_bot_token(self):
        """Test with invalid bot token"""
        connector = DiscordConnector({})

        with pytest.raises(ConnectorError):
            connector.validate_credentials()

    @pytest.mark.asyncio
    async def test_unauthorized_error(self):
        """Test unauthorized access"""
        connector = DiscordConnector({"bot_token": "invalid_token"})

        with patch.object(connector, 'make_request') as mock_request:
            mock_request.side_effect = ConnectorError(
                "Unauthorized",
                status_code=401
            )

            with pytest.raises(ConnectorError) as exc_info:
                await connector.get_user_info()

            assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_rate_limit_error(self):
        """Test rate limit handling"""
        connector = DiscordConnector({"bot_token": "test_token"})

        with patch.object(connector, 'make_request') as mock_request:
            mock_request.side_effect = ConnectorError(
                "Rate limit exceeded",
                status_code=429
            )

            with pytest.raises(ConnectorError) as exc_info:
                await connector.send_message("ch_test", "message")

            assert exc_info.value.status_code == 429

    @pytest.mark.asyncio
    async def test_forbidden_error(self):
        """Test forbidden access"""
        connector = DiscordConnector({"bot_token": "test_token"})

        with patch.object(connector, 'make_request') as mock_request:
            mock_request.side_effect = ConnectorError(
                "Forbidden - bot lacks permissions",
                status_code=403
            )

            with pytest.raises(ConnectorError) as exc_info:
                await connector.send_message("ch_restricted", "message")

            assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_not_found_error(self):
        """Test not found error"""
        connector = DiscordConnector({"bot_token": "test_token"})

        with patch.object(connector, 'make_request') as mock_request:
            mock_request.side_effect = ConnectorError(
                "Channel not found",
                status_code=404
            )

            with pytest.raises(ConnectorError) as exc_info:
                await connector.get_channel_messages("invalid_channel")

            assert exc_info.value.status_code == 404


class TestContextManager:
    """Test async context manager"""

    @pytest.mark.asyncio
    async def test_context_manager_lifecycle(self):
        """Test connector lifecycle with context manager"""
        async with DiscordConnector({"bot_token": "test_token"}) as connector:
            assert connector.credentials["bot_token"] == "test_token"

        assert connector._http_client is None
