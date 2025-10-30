"""
Outlook/Microsoft Graph MCP Connector
Handles Outlook emails and calendar
"""
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.connectors.base_connector import BaseConnector, ConnectorResponse, ConnectorStatus, ConnectorError


class OutlookConnector(BaseConnector):
    """Connector for Microsoft Graph API (Outlook)"""

    @property
    def platform_name(self) -> str:
        return "outlook"

    @property
    def base_url(self) -> str:
        return "https://graph.microsoft.com/v1.0"

    async def test_connection(self) -> ConnectorResponse:
        """Test connection to Microsoft Graph API"""
        try:
            self.validate_credentials()
            user_info = await self.get_user_info()
            return ConnectorResponse(
                status=ConnectorStatus.SUCCESS,
                data={"connected": True, "user": user_info.data},
                metadata={"platform": self.platform_name}
            )
        except Exception as e:
            self.logger.error(f"Outlook connection test failed: {str(e)}")
            return ConnectorResponse(
                status=ConnectorStatus.ERROR,
                error=str(e),
                metadata={"platform": self.platform_name}
            )

    async def get_user_info(self) -> ConnectorResponse:
        """Get authenticated user information"""
        return await self.make_request("GET", "/me")

    async def list_messages(
        self,
        folder: str = "inbox",
        top: int = 50,
        filter_query: Optional[str] = None
    ) -> ConnectorResponse:
        """
        List email messages

        Args:
            folder: Mail folder (inbox, sentitems, drafts, etc.)
            top: Number of messages to retrieve
            filter_query: OData filter query

        Returns:
            ConnectorResponse with messages list
        """
        params = {"$top": top, "$orderby": "receivedDateTime DESC"}
        if filter_query:
            params["$filter"] = filter_query

        return await self.make_request("GET", f"/me/mailFolders/{folder}/messages", params=params)

    async def get_message(self, message_id: str) -> ConnectorResponse:
        """
        Get email message details

        Args:
            message_id: Message ID

        Returns:
            ConnectorResponse with message details
        """
        return await self.make_request("GET", f"/me/messages/{message_id}")

    async def send_email(
        self,
        to_recipients: List[str],
        subject: str,
        body: str,
        body_type: str = "HTML",
        cc_recipients: Optional[List[str]] = None
    ) -> ConnectorResponse:
        """
        Send an email

        Args:
            to_recipients: List of recipient email addresses
            subject: Email subject
            body: Email body content
            body_type: Body content type (HTML or Text)
            cc_recipients: Optional CC recipients

        Returns:
            ConnectorResponse with send status
        """
        message = {
            "message": {
                "subject": subject,
                "body": {
                    "contentType": body_type,
                    "content": body
                },
                "toRecipients": [{"emailAddress": {"address": addr}} for addr in to_recipients]
            }
        }

        if cc_recipients:
            message["message"]["ccRecipients"] = [
                {"emailAddress": {"address": addr}} for addr in cc_recipients
            ]

        return await self.make_request("POST", "/me/sendMail", json=message)

    async def list_calendar_events(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        top: int = 50
    ) -> ConnectorResponse:
        """
        List calendar events

        Args:
            start_date: Start date for events
            end_date: End date for events
            top: Number of events to retrieve

        Returns:
            ConnectorResponse with events list
        """
        params = {"$top": top, "$orderby": "start/dateTime"}

        if start_date and end_date:
            filter_query = (
                f"start/dateTime ge '{start_date.isoformat()}' and "
                f"end/dateTime le '{end_date.isoformat()}'"
            )
            params["$filter"] = filter_query

        return await self.make_request("GET", "/me/calendar/events", params=params)

    async def create_calendar_event(
        self,
        subject: str,
        start_time: datetime,
        end_time: datetime,
        attendees: Optional[List[str]] = None,
        body: Optional[str] = None
    ) -> ConnectorResponse:
        """
        Create a calendar event

        Args:
            subject: Event subject
            start_time: Event start time
            end_time: Event end time
            attendees: Optional list of attendee emails
            body: Optional event description

        Returns:
            ConnectorResponse with created event details
        """
        event = {
            "subject": subject,
            "start": {
                "dateTime": start_time.isoformat(),
                "timeZone": "UTC"
            },
            "end": {
                "dateTime": end_time.isoformat(),
                "timeZone": "UTC"
            }
        }

        if body:
            event["body"] = {
                "contentType": "HTML",
                "content": body
            }

        if attendees:
            event["attendees"] = [
                {
                    "emailAddress": {"address": addr},
                    "type": "required"
                } for addr in attendees
            ]

        return await self.make_request("POST", "/me/calendar/events", json=event)

    async def search_messages(self, query: str, top: int = 50) -> ConnectorResponse:
        """
        Search email messages

        Args:
            query: Search query
            top: Number of results

        Returns:
            ConnectorResponse with search results
        """
        params = {
            "$search": f'"{query}"',
            "$top": top
        }
        return await self.make_request("GET", "/me/messages", params=params)
