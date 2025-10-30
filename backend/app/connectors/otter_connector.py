"""
Otter.ai MCP Connector
Handles meeting transcripts from Otter
"""
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.connectors.base_connector import BaseConnector, ConnectorResponse, ConnectorStatus, ConnectorError


class OtterConnector(BaseConnector):
    """Connector for Otter.ai API"""

    @property
    def platform_name(self) -> str:
        return "otter"

    @property
    def base_url(self) -> str:
        return "https://otter.ai/forward/api/v1"

    async def test_connection(self) -> ConnectorResponse:
        """Test connection to Otter API"""
        try:
            self.validate_credentials()
            user_info = await self.get_user_info()
            return ConnectorResponse(
                status=ConnectorStatus.SUCCESS,
                data={"connected": True, "user": user_info.data},
                metadata={"platform": self.platform_name}
            )
        except Exception as e:
            self.logger.error(f"Otter connection test failed: {str(e)}")
            return ConnectorResponse(
                status=ConnectorStatus.ERROR,
                error=str(e),
                metadata={"platform": self.platform_name}
            )

    async def get_user_info(self) -> ConnectorResponse:
        """Get authenticated user information"""
        return await self.make_request("GET", "/user")

    async def list_speeches(
        self,
        folder: Optional[str] = None,
        page_size: int = 50,
        offset: int = 0
    ) -> ConnectorResponse:
        """
        List transcribed speeches (conversations)

        Args:
            folder: Optional folder ID to filter by
            page_size: Number of results per page
            offset: Pagination offset

        Returns:
            ConnectorResponse with speeches list
        """
        params = {
            "page_size": page_size,
            "offset": offset
        }
        if folder:
            params["folder"] = folder

        return await self.make_request("GET", "/speeches", params=params)

    async def get_speech(self, speech_id: str) -> ConnectorResponse:
        """
        Get speech (conversation) details

        Args:
            speech_id: Speech ID

        Returns:
            ConnectorResponse with speech details
        """
        return await self.make_request("GET", f"/speeches/{speech_id}")

    async def get_speech_transcript(self, speech_id: str) -> ConnectorResponse:
        """
        Get speech transcript with full text

        Args:
            speech_id: Speech ID

        Returns:
            ConnectorResponse with transcript data
        """
        params = {"include_transcript": "true"}
        return await self.make_request("GET", f"/speeches/{speech_id}", params=params)

    async def get_speech_summary(self, speech_id: str) -> ConnectorResponse:
        """
        Get AI-generated summary for a speech

        Args:
            speech_id: Speech ID

        Returns:
            ConnectorResponse with summary
        """
        return await self.make_request("GET", f"/speeches/{speech_id}/summary")

    async def search_speeches(
        self,
        query: str,
        page_size: int = 50
    ) -> ConnectorResponse:
        """
        Search transcripts

        Args:
            query: Search query
            page_size: Number of results

        Returns:
            ConnectorResponse with search results
        """
        params = {
            "query": query,
            "page_size": page_size
        }
        return await self.make_request("GET", "/speeches/search", params=params)

    async def list_folders(self) -> ConnectorResponse:
        """
        List user's folders

        Returns:
            ConnectorResponse with folders list
        """
        return await self.make_request("GET", "/folders")

    async def get_folder_speeches(
        self,
        folder_id: str,
        page_size: int = 50
    ) -> ConnectorResponse:
        """
        Get speeches in a folder

        Args:
            folder_id: Folder ID
            page_size: Number of speeches

        Returns:
            ConnectorResponse with speeches list
        """
        return await self.list_speeches(folder=folder_id, page_size=page_size)

    async def update_speech(
        self,
        speech_id: str,
        title: Optional[str] = None,
        summary: Optional[str] = None
    ) -> ConnectorResponse:
        """
        Update speech metadata

        Args:
            speech_id: Speech ID
            title: New title
            summary: New summary

        Returns:
            ConnectorResponse with updated speech
        """
        json_data = {}
        if title:
            json_data["title"] = title
        if summary:
            json_data["summary"] = summary

        return await self.make_request("PATCH", f"/speeches/{speech_id}", json=json_data)

    async def delete_speech(self, speech_id: str) -> ConnectorResponse:
        """
        Delete a speech

        Args:
            speech_id: Speech ID

        Returns:
            ConnectorResponse with deletion status
        """
        return await self.make_request("DELETE", f"/speeches/{speech_id}")
