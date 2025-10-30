"""
Slack MCP Connector
Handles Slack messages, channels, and users
"""
from typing import Dict, Any, List, Optional

from app.connectors.base_connector import BaseConnector, ConnectorResponse, ConnectorStatus, ConnectorError


class SlackConnector(BaseConnector):
    """Connector for Slack API"""

    @property
    def platform_name(self) -> str:
        return "slack"

    @property
    def base_url(self) -> str:
        return "https://slack.com/api"

    async def test_connection(self) -> ConnectorResponse:
        """Test connection to Slack API"""
        try:
            self.validate_credentials()
            auth_test = await self.make_request("POST", "/auth.test")
            return ConnectorResponse(
                status=ConnectorStatus.SUCCESS,
                data={"connected": True, "auth": auth_test.data},
                metadata={"platform": self.platform_name}
            )
        except Exception as e:
            self.logger.error(f"Slack connection test failed: {str(e)}")
            return ConnectorResponse(
                status=ConnectorStatus.ERROR,
                error=str(e),
                metadata={"platform": self.platform_name}
            )

    async def get_user_info(self) -> ConnectorResponse:
        """Get authenticated Slack user information"""
        return await self.make_request("POST", "/auth.test")

    async def list_channels(self, types: str = "public_channel,private_channel") -> ConnectorResponse:
        """
        List Slack channels

        Args:
            types: Comma-separated list of channel types

        Returns:
            ConnectorResponse with channels list
        """
        params = {
            "types": types,
            "exclude_archived": True
        }
        return await self.make_request("POST", "/conversations.list", params=params)

    async def get_channel_history(
        self,
        channel_id: str,
        limit: int = 100,
        oldest: Optional[str] = None,
        latest: Optional[str] = None
    ) -> ConnectorResponse:
        """
        Get channel message history

        Args:
            channel_id: Channel ID
            limit: Number of messages to retrieve
            oldest: Start of time range (Unix timestamp)
            latest: End of time range (Unix timestamp)

        Returns:
            ConnectorResponse with message history
        """
        params = {
            "channel": channel_id,
            "limit": limit
        }
        if oldest:
            params["oldest"] = oldest
        if latest:
            params["latest"] = latest

        return await self.make_request("POST", "/conversations.history", params=params)

    async def get_thread_replies(self, channel_id: str, thread_ts: str) -> ConnectorResponse:
        """
        Get replies to a thread

        Args:
            channel_id: Channel ID
            thread_ts: Thread timestamp

        Returns:
            ConnectorResponse with thread replies
        """
        params = {
            "channel": channel_id,
            "ts": thread_ts
        }
        return await self.make_request("POST", "/conversations.replies", params=params)

    async def send_message(
        self,
        channel_id: str,
        text: str,
        thread_ts: Optional[str] = None,
        blocks: Optional[List[Dict[str, Any]]] = None
    ) -> ConnectorResponse:
        """
        Send a message to a channel

        Args:
            channel_id: Channel ID
            text: Message text
            thread_ts: Optional thread timestamp to reply to
            blocks: Optional Block Kit blocks

        Returns:
            ConnectorResponse with sent message details
        """
        json_data = {
            "channel": channel_id,
            "text": text
        }
        if thread_ts:
            json_data["thread_ts"] = thread_ts
        if blocks:
            json_data["blocks"] = blocks

        return await self.make_request("POST", "/chat.postMessage", json=json_data)

    async def list_users(self) -> ConnectorResponse:
        """
        List workspace users

        Returns:
            ConnectorResponse with users list
        """
        return await self.make_request("POST", "/users.list")

    async def get_user(self, user_id: str) -> ConnectorResponse:
        """
        Get user details

        Args:
            user_id: User ID

        Returns:
            ConnectorResponse with user details
        """
        params = {"user": user_id}
        return await self.make_request("POST", "/users.info", params=params)

    async def search_messages(self, query: str, count: int = 20) -> ConnectorResponse:
        """
        Search messages in workspace

        Args:
            query: Search query
            count: Number of results

        Returns:
            ConnectorResponse with search results
        """
        params = {
            "query": query,
            "count": count
        }
        return await self.make_request("POST", "/search.messages", params=params)
