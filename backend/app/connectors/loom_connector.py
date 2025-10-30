"""
Loom MCP Connector
Handles Loom videos and transcripts
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from app.connectors.base_connector import BaseConnector, ConnectorResponse, ConnectorStatus, ConnectorError


class LoomConnector(BaseConnector):
    """Connector for Loom API"""

    @property
    def platform_name(self) -> str:
        return "loom"

    @property
    def base_url(self) -> str:
        return "https://www.loom.com/api/v1"

    async def test_connection(self) -> ConnectorResponse:
        """Test connection to Loom API"""
        try:
            self.validate_credentials()
            user_info = await self.get_user_info()
            return ConnectorResponse(
                status=ConnectorStatus.SUCCESS,
                data={"connected": True, "user": user_info.data},
                metadata={"platform": self.platform_name}
            )
        except Exception as e:
            self.logger.error(f"Loom connection test failed: {str(e)}")
            return ConnectorResponse(
                status=ConnectorStatus.ERROR,
                error=str(e),
                metadata={"platform": self.platform_name}
            )

    async def get_user_info(self) -> ConnectorResponse:
        """Get authenticated user information"""
        return await self.make_request("GET", "/users/me")

    async def list_videos(
        self,
        limit: int = 50,
        offset: int = 0,
        sort_by: str = "createdAt",
        sort_direction: str = "desc"
    ) -> ConnectorResponse:
        """
        List user's videos

        Args:
            limit: Number of videos to retrieve
            offset: Pagination offset
            sort_by: Sort field
            sort_direction: Sort direction (asc or desc)

        Returns:
            ConnectorResponse with videos list
        """
        params = {
            "limit": limit,
            "offset": offset,
            "sort_by": sort_by,
            "sort_direction": sort_direction
        }
        return await self.make_request("GET", "/videos", params=params)

    async def get_video(self, video_id: str) -> ConnectorResponse:
        """
        Get video details

        Args:
            video_id: Video ID

        Returns:
            ConnectorResponse with video details
        """
        return await self.make_request("GET", f"/videos/{video_id}")

    async def get_video_transcript(self, video_id: str) -> ConnectorResponse:
        """
        Get video transcript

        Args:
            video_id: Video ID

        Returns:
            ConnectorResponse with transcript data
        """
        return await self.make_request("GET", f"/videos/{video_id}/transcript")

    async def get_video_insights(self, video_id: str) -> ConnectorResponse:
        """
        Get video analytics and insights

        Args:
            video_id: Video ID

        Returns:
            ConnectorResponse with insights data
        """
        return await self.make_request("GET", f"/videos/{video_id}/insights")

    async def search_videos(
        self,
        query: str,
        limit: int = 50
    ) -> ConnectorResponse:
        """
        Search videos

        Args:
            query: Search query
            limit: Number of results

        Returns:
            ConnectorResponse with search results
        """
        params = {
            "query": query,
            "limit": limit
        }
        return await self.make_request("GET", "/videos/search", params=params)

    async def list_folders(self) -> ConnectorResponse:
        """
        List user's folders

        Returns:
            ConnectorResponse with folders list
        """
        return await self.make_request("GET", "/folders")

    async def get_folder_videos(
        self,
        folder_id: str,
        limit: int = 50
    ) -> ConnectorResponse:
        """
        Get videos in a folder

        Args:
            folder_id: Folder ID
            limit: Number of videos

        Returns:
            ConnectorResponse with videos list
        """
        params = {"limit": limit}
        return await self.make_request("GET", f"/folders/{folder_id}/videos", params=params)

    async def update_video(
        self,
        video_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None
    ) -> ConnectorResponse:
        """
        Update video metadata

        Args:
            video_id: Video ID
            title: New video title
            description: New video description

        Returns:
            ConnectorResponse with updated video
        """
        json_data = {}
        if title:
            json_data["title"] = title
        if description:
            json_data["description"] = description

        return await self.make_request("PATCH", f"/videos/{video_id}", json=json_data)

    async def delete_video(self, video_id: str) -> ConnectorResponse:
        """
        Delete a video

        Args:
            video_id: Video ID

        Returns:
            ConnectorResponse with deletion status
        """
        return await self.make_request("DELETE", f"/videos/{video_id}")
