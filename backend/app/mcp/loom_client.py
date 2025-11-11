"""
Loom MCP Client
Handles communication with Loom API for video ingestion and transcript extraction
"""
import logging
import re
from typing import Dict, Any, Optional, List
from datetime import datetime
from pydantic import BaseModel, Field

from app.connectors.loom_connector import LoomConnector
from app.connectors.base_connector import ConnectorResponse, ConnectorStatus


logger = logging.getLogger(__name__)


class LoomVideoData(BaseModel):
    """Loom video metadata"""
    video_id: str
    title: str
    description: Optional[str] = None
    duration_seconds: int
    thumbnail_url: Optional[str] = None
    video_url: str
    created_at: datetime
    owner_name: Optional[str] = None
    owner_email: Optional[str] = None


class LoomTranscriptData(BaseModel):
    """Loom video transcript"""
    video_id: str
    transcript_text: str
    words: List[Dict[str, Any]] = Field(default_factory=list)
    language: str = "en"


class LoomMCPClient:
    """
    MCP Client for Loom video platform

    Provides high-level interface for:
    - Fetching video metadata
    - Extracting transcripts
    - Downloading videos
    - Connection testing
    """

    def __init__(self, credentials: Dict[str, str]):
        """
        Initialize Loom MCP client

        Args:
            credentials: API credentials (api_key, client_id, client_secret)
        """
        self.credentials = credentials
        self.api_key = credentials.get("api_key")
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    async def __aenter__(self):
        """Async context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        pass

    async def get_video_details(self, video_id: str) -> Optional[LoomVideoData]:
        """
        Fetch video metadata from Loom API

        Args:
            video_id: Loom video ID

        Returns:
            LoomVideoData if successful, None otherwise
        """
        try:
            response = await self._make_request("GET", f"/videos/{video_id}")

            if response.status != ConnectorStatus.SUCCESS:
                self.logger.error(f"Failed to fetch video details: {response.error}")
                return None

            data = response.data

            return LoomVideoData(
                video_id=video_id,
                title=data.get("title", "Untitled Video"),
                description=data.get("description"),
                duration_seconds=data.get("duration", 0),
                thumbnail_url=data.get("thumbnail_url"),
                video_url=data.get("video_url", f"https://www.loom.com/share/{video_id}"),
                created_at=self._parse_datetime(data.get("created_at")),
                owner_name=data.get("owner", {}).get("name"),
                owner_email=data.get("owner", {}).get("email")
            )

        except Exception as e:
            self.logger.error(f"Error fetching video details: {str(e)}")
            raise

    async def get_video_transcript(self, video_id: str) -> Optional[LoomTranscriptData]:
        """
        Fetch video transcript from Loom API

        Args:
            video_id: Loom video ID

        Returns:
            LoomTranscriptData if successful, None otherwise
        """
        try:
            response = await self._make_request("GET", f"/videos/{video_id}/transcript")

            if response.status != ConnectorStatus.SUCCESS:
                self.logger.error(f"Failed to fetch transcript: {response.error}")
                return None

            data = response.data

            return LoomTranscriptData(
                video_id=video_id,
                transcript_text=data.get("transcript", ""),
                words=data.get("words", []),
                language=data.get("language", "en")
            )

        except Exception as e:
            self.logger.error(f"Error fetching transcript: {str(e)}")
            return None

    async def get_video_download_url(self, video_id: str) -> Optional[str]:
        """
        Get temporary download URL for video

        Args:
            video_id: Loom video ID

        Returns:
            Download URL if successful, None otherwise
        """
        try:
            response = await self._make_request("GET", f"/videos/{video_id}/download")

            if response.status != ConnectorStatus.SUCCESS:
                self.logger.error(f"Failed to get download URL: {response.error}")
                return None

            return response.data.get("download_url")

        except Exception as e:
            self.logger.error(f"Error getting download URL: {str(e)}")
            return None

    async def test_connection(self) -> bool:
        """
        Test Loom API connection

        Returns:
            True if connection successful, False otherwise
        """
        try:
            response = await self._make_request("GET", "/users/me")
            return response.status == ConnectorStatus.SUCCESS
        except Exception as e:
            self.logger.error(f"Connection test failed: {str(e)}")
            return False

    def extract_video_id_from_url(self, url: str) -> Optional[str]:
        """
        Extract Loom video ID from URL

        Args:
            url: Loom video URL

        Returns:
            Video ID if found, None otherwise
        """
        patterns = [
            r'loom\.com/share/([a-zA-Z0-9]+)',
            r'loom\.com/embed/([a-zA-Z0-9]+)'
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)

        return None

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None
    ) -> ConnectorResponse:
        """
        Make HTTP request to Loom API via connector

        Args:
            method: HTTP method
            endpoint: API endpoint
            params: Query parameters
            json: JSON body

        Returns:
            ConnectorResponse
        """
        async with LoomConnector(self.credentials) as connector:
            return await connector.make_request(method, endpoint, params=params, json=json)

    def _parse_datetime(self, dt_string: Optional[str]) -> datetime:
        """
        Parse datetime string

        Args:
            dt_string: ISO datetime string

        Returns:
            datetime object, defaults to now if invalid
        """
        if not dt_string:
            return datetime.utcnow()

        try:
            return datetime.fromisoformat(dt_string.replace("Z", "+00:00"))
        except Exception:
            return datetime.utcnow()
