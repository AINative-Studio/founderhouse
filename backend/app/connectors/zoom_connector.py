"""
Zoom MCP Connector
Handles Zoom meetings, recordings, and transcripts
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from app.connectors.base_connector import BaseConnector, ConnectorResponse, ConnectorStatus, ConnectorError


class ZoomConnector(BaseConnector):
    """Connector for Zoom API"""

    @property
    def platform_name(self) -> str:
        return "zoom"

    @property
    def base_url(self) -> str:
        return "https://api.zoom.us/v2"

    async def test_connection(self) -> ConnectorResponse:
        """Test connection to Zoom API"""
        try:
            self.validate_credentials()
            user_info = await self.get_user_info()
            return ConnectorResponse(
                status=ConnectorStatus.SUCCESS,
                data={"connected": True, "user": user_info.data},
                metadata={"platform": self.platform_name}
            )
        except Exception as e:
            self.logger.error(f"Zoom connection test failed: {str(e)}")
            return ConnectorResponse(
                status=ConnectorStatus.ERROR,
                error=str(e),
                metadata={"platform": self.platform_name}
            )

    async def get_user_info(self) -> ConnectorResponse:
        """Get authenticated Zoom user information"""
        return await self.make_request("GET", "/users/me")

    async def list_meetings(
        self,
        user_id: str = "me",
        meeting_type: str = "scheduled",
        page_size: int = 30
    ) -> ConnectorResponse:
        """
        List user's meetings

        Args:
            user_id: User ID or 'me' for authenticated user
            meeting_type: Type of meeting (scheduled, live, upcoming)
            page_size: Number of records per page

        Returns:
            ConnectorResponse with meetings list
        """
        params = {
            "type": meeting_type,
            "page_size": page_size
        }
        return await self.make_request("GET", f"/users/{user_id}/meetings", params=params)

    async def get_meeting(self, meeting_id: str) -> ConnectorResponse:
        """
        Get meeting details

        Args:
            meeting_id: Meeting ID

        Returns:
            ConnectorResponse with meeting details
        """
        return await self.make_request("GET", f"/meetings/{meeting_id}")

    async def list_recordings(
        self,
        user_id: str = "me",
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None
    ) -> ConnectorResponse:
        """
        List cloud recordings

        Args:
            user_id: User ID or 'me' for authenticated user
            from_date: Start date for recordings
            to_date: End date for recordings

        Returns:
            ConnectorResponse with recordings list
        """
        if not from_date:
            from_date = datetime.utcnow() - timedelta(days=30)
        if not to_date:
            to_date = datetime.utcnow()

        params = {
            "from": from_date.strftime("%Y-%m-%d"),
            "to": to_date.strftime("%Y-%m-%d")
        }
        return await self.make_request("GET", f"/users/{user_id}/recordings", params=params)

    async def get_recording(self, meeting_id: str) -> ConnectorResponse:
        """
        Get recording details for a meeting

        Args:
            meeting_id: Meeting ID

        Returns:
            ConnectorResponse with recording details
        """
        return await self.make_request("GET", f"/meetings/{meeting_id}/recordings")

    async def get_meeting_participants(self, meeting_id: str) -> ConnectorResponse:
        """
        Get meeting participants

        Args:
            meeting_id: Meeting ID

        Returns:
            ConnectorResponse with participants list
        """
        return await self.make_request("GET", f"/metrics/meetings/{meeting_id}/participants")

    async def download_recording(self, download_url: str, access_token: str) -> ConnectorResponse:
        """
        Download recording file

        Args:
            download_url: URL to download recording
            access_token: Access token for authentication

        Returns:
            ConnectorResponse with file data
        """
        try:
            headers = {
                "Authorization": f"Bearer {access_token}"
            }
            response = await self.http_client.get(download_url, headers=headers)

            if response.status_code == 200:
                return ConnectorResponse(
                    status=ConnectorStatus.SUCCESS,
                    data=response.content,
                    metadata={"content_type": response.headers.get("content-type")}
                )
            else:
                raise ConnectorError(
                    f"Failed to download recording: {response.status_code}",
                    status_code=response.status_code
                )
        except Exception as e:
            self.logger.error(f"Recording download failed: {str(e)}")
            raise ConnectorError(f"Recording download failed: {str(e)}")
