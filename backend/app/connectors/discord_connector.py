"""
Discord MCP Connector
Handles Discord messages, channels, and guilds
"""
from typing import Dict, Any, List, Optional

from app.connectors.base_connector import BaseConnector, ConnectorResponse, ConnectorStatus, ConnectorError


class DiscordConnector(BaseConnector):
    """Connector for Discord API"""

    @property
    def platform_name(self) -> str:
        return "discord"

    @property
    def base_url(self) -> str:
        return "https://discord.com/api/v10"

    def _get_default_headers(self) -> Dict[str, str]:
        """Override to use bot token format for Discord"""
        headers = super()._get_default_headers()
        bot_token = self.credentials.get("bot_token")
        if bot_token:
            headers["Authorization"] = f"Bot {bot_token}"
        return headers

    async def test_connection(self) -> ConnectorResponse:
        """Test connection to Discord API"""
        try:
            self.validate_credentials()
            user_info = await self.get_user_info()
            return ConnectorResponse(
                status=ConnectorStatus.SUCCESS,
                data={"connected": True, "user": user_info.data},
                metadata={"platform": self.platform_name}
            )
        except Exception as e:
            self.logger.error(f"Discord connection test failed: {str(e)}")
            return ConnectorResponse(
                status=ConnectorStatus.ERROR,
                error=str(e),
                metadata={"platform": self.platform_name}
            )

    async def get_user_info(self) -> ConnectorResponse:
        """Get authenticated Discord bot user information"""
        return await self.make_request("GET", "/users/@me")

    async def list_guilds(self) -> ConnectorResponse:
        """
        List guilds (servers) the bot is in

        Returns:
            ConnectorResponse with guilds list
        """
        return await self.make_request("GET", "/users/@me/guilds")

    async def get_guild(self, guild_id: str) -> ConnectorResponse:
        """
        Get guild details

        Args:
            guild_id: Guild ID

        Returns:
            ConnectorResponse with guild details
        """
        return await self.make_request("GET", f"/guilds/{guild_id}")

    async def list_guild_channels(self, guild_id: str) -> ConnectorResponse:
        """
        List channels in a guild

        Args:
            guild_id: Guild ID

        Returns:
            ConnectorResponse with channels list
        """
        return await self.make_request("GET", f"/guilds/{guild_id}/channels")

    async def get_channel_messages(
        self,
        channel_id: str,
        limit: int = 50,
        before: Optional[str] = None,
        after: Optional[str] = None
    ) -> ConnectorResponse:
        """
        Get messages from a channel

        Args:
            channel_id: Channel ID
            limit: Number of messages (1-100)
            before: Get messages before this message ID
            after: Get messages after this message ID

        Returns:
            ConnectorResponse with messages
        """
        params = {"limit": min(limit, 100)}
        if before:
            params["before"] = before
        if after:
            params["after"] = after

        return await self.make_request("GET", f"/channels/{channel_id}/messages", params=params)

    async def send_message(
        self,
        channel_id: str,
        content: str,
        embeds: Optional[List[Dict[str, Any]]] = None
    ) -> ConnectorResponse:
        """
        Send a message to a channel

        Args:
            channel_id: Channel ID
            content: Message content
            embeds: Optional message embeds

        Returns:
            ConnectorResponse with sent message details
        """
        json_data = {"content": content}
        if embeds:
            json_data["embeds"] = embeds

        return await self.make_request("POST", f"/channels/{channel_id}/messages", json=json_data)

    async def list_guild_members(
        self,
        guild_id: str,
        limit: int = 100
    ) -> ConnectorResponse:
        """
        List members in a guild

        Args:
            guild_id: Guild ID
            limit: Number of members to return

        Returns:
            ConnectorResponse with members list
        """
        params = {"limit": min(limit, 1000)}
        return await self.make_request("GET", f"/guilds/{guild_id}/members", params=params)

    async def get_member(self, guild_id: str, user_id: str) -> ConnectorResponse:
        """
        Get guild member details

        Args:
            guild_id: Guild ID
            user_id: User ID

        Returns:
            ConnectorResponse with member details
        """
        return await self.make_request("GET", f"/guilds/{guild_id}/members/{user_id}")
