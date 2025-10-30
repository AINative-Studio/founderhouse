"""
Gmail MCP Connector
Handles Gmail emails and threads via Google API
"""
from typing import Dict, Any, List, Optional
import base64

from app.connectors.base_connector import BaseConnector, ConnectorResponse, ConnectorStatus, ConnectorError


class GmailConnector(BaseConnector):
    """Connector for Gmail API"""

    @property
    def platform_name(self) -> str:
        return "gmail"

    @property
    def base_url(self) -> str:
        return "https://gmail.googleapis.com/gmail/v1"

    async def test_connection(self) -> ConnectorResponse:
        """Test connection to Gmail API"""
        try:
            self.validate_credentials()
            profile = await self.get_user_info()
            return ConnectorResponse(
                status=ConnectorStatus.SUCCESS,
                data={"connected": True, "profile": profile.data},
                metadata={"platform": self.platform_name}
            )
        except Exception as e:
            self.logger.error(f"Gmail connection test failed: {str(e)}")
            return ConnectorResponse(
                status=ConnectorStatus.ERROR,
                error=str(e),
                metadata={"platform": self.platform_name}
            )

    async def get_user_info(self) -> ConnectorResponse:
        """Get Gmail profile information"""
        return await self.make_request("GET", "/users/me/profile")

    async def list_messages(
        self,
        query: Optional[str] = None,
        label_ids: Optional[List[str]] = None,
        max_results: int = 50
    ) -> ConnectorResponse:
        """
        List Gmail messages

        Args:
            query: Gmail search query
            label_ids: Filter by label IDs
            max_results: Maximum number of messages

        Returns:
            ConnectorResponse with messages list
        """
        params = {"maxResults": max_results}
        if query:
            params["q"] = query
        if label_ids:
            params["labelIds"] = ",".join(label_ids)

        return await self.make_request("GET", "/users/me/messages", params=params)

    async def get_message(
        self,
        message_id: str,
        format: str = "full"
    ) -> ConnectorResponse:
        """
        Get message details

        Args:
            message_id: Message ID
            format: Response format (full, metadata, minimal, raw)

        Returns:
            ConnectorResponse with message details
        """
        params = {"format": format}
        return await self.make_request("GET", f"/users/me/messages/{message_id}", params=params)

    async def send_message(
        self,
        to: str,
        subject: str,
        body: str,
        cc: Optional[str] = None,
        bcc: Optional[str] = None
    ) -> ConnectorResponse:
        """
        Send an email message

        Args:
            to: Recipient email address
            subject: Email subject
            body: Email body (plain text)
            cc: Optional CC recipients
            bcc: Optional BCC recipients

        Returns:
            ConnectorResponse with sent message details
        """
        # Construct MIME message
        message_parts = [
            f"To: {to}",
            f"Subject: {subject}"
        ]
        if cc:
            message_parts.append(f"Cc: {cc}")
        if bcc:
            message_parts.append(f"Bcc: {bcc}")

        message_parts.append("")  # Blank line between headers and body
        message_parts.append(body)

        raw_message = "\n".join(message_parts)

        # Base64url encode the message
        encoded_message = base64.urlsafe_b64encode(raw_message.encode()).decode()

        json_data = {"raw": encoded_message}
        return await self.make_request("POST", "/users/me/messages/send", json=json_data)

    async def list_threads(
        self,
        query: Optional[str] = None,
        max_results: int = 50
    ) -> ConnectorResponse:
        """
        List email threads

        Args:
            query: Gmail search query
            max_results: Maximum number of threads

        Returns:
            ConnectorResponse with threads list
        """
        params = {"maxResults": max_results}
        if query:
            params["q"] = query

        return await self.make_request("GET", "/users/me/threads", params=params)

    async def get_thread(self, thread_id: str) -> ConnectorResponse:
        """
        Get thread details

        Args:
            thread_id: Thread ID

        Returns:
            ConnectorResponse with thread details
        """
        return await self.make_request("GET", f"/users/me/threads/{thread_id}")

    async def modify_message_labels(
        self,
        message_id: str,
        add_label_ids: Optional[List[str]] = None,
        remove_label_ids: Optional[List[str]] = None
    ) -> ConnectorResponse:
        """
        Modify message labels

        Args:
            message_id: Message ID
            add_label_ids: Labels to add
            remove_label_ids: Labels to remove

        Returns:
            ConnectorResponse with modified message
        """
        json_data = {}
        if add_label_ids:
            json_data["addLabelIds"] = add_label_ids
        if remove_label_ids:
            json_data["removeLabelIds"] = remove_label_ids

        return await self.make_request(
            "POST",
            f"/users/me/messages/{message_id}/modify",
            json=json_data
        )

    async def list_labels(self) -> ConnectorResponse:
        """
        List Gmail labels

        Returns:
            ConnectorResponse with labels list
        """
        return await self.make_request("GET", "/users/me/labels")

    async def search_messages(self, query: str, max_results: int = 50) -> ConnectorResponse:
        """
        Search messages with Gmail query syntax

        Args:
            query: Gmail search query (e.g., "from:user@example.com is:unread")
            max_results: Maximum number of results

        Returns:
            ConnectorResponse with search results
        """
        return await self.list_messages(query=query, max_results=max_results)
