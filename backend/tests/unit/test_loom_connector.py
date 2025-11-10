"""
Unit tests for Loom Connector
Tests video retrieval, transcription, and summarization
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from app.connectors.loom_connector import LoomConnector
from app.connectors.base_connector import ConnectorResponse, ConnectorStatus, ConnectorError
from tests.fixtures.loom_fixtures import (
    MOCK_LOOM_USER,
    MOCK_LOOM_VIDEOS,
    MOCK_VIDEO_TRANSCRIPTS,
    MOCK_VIDEO_INSIGHTS,
    MOCK_LOOM_FOLDERS,
    get_mock_video,
    get_mock_transcript,
    get_mock_insights,
    create_mock_loom_video
)


class TestLoomConnectorInitialization:
    """Test connector initialization"""

    def test_connector_initialization(self):
        """Test connector initializes with credentials"""
        credentials = {"access_token": "test_token"}
        connector = LoomConnector(credentials)

        assert connector.credentials == credentials
        assert connector.platform_name == "loom"
        assert connector.base_url == "https://www.loom.com/api/v1"

    def test_connector_platform_name(self):
        """Test platform name is correct"""
        connector = LoomConnector({})
        assert connector.platform_name == "loom"

    def test_connector_base_url(self):
        """Test base URL is correct"""
        connector = LoomConnector({})
        assert connector.base_url == "https://www.loom.com/api/v1"


class TestLoomConnectionTesting:
    """Test connection validation"""

    @pytest.mark.asyncio
    async def test_test_connection_success(self):
        """Test successful connection test"""
        connector = LoomConnector({"access_token": "test_token"})

        with patch.object(connector, 'get_user_info') as mock_get_user:
            mock_get_user.return_value = ConnectorResponse(
                status=ConnectorStatus.SUCCESS,
                data=MOCK_LOOM_USER
            )

            response = await connector.test_connection()

            assert response.status == ConnectorStatus.SUCCESS
            assert response.data["connected"] is True
            assert "user" in response.data

    @pytest.mark.asyncio
    async def test_test_connection_failure(self):
        """Test connection failure"""
        connector = LoomConnector({})

        with patch.object(connector, 'validate_credentials') as mock_validate:
            mock_validate.side_effect = ConnectorError("No credentials provided")

            response = await connector.test_connection()

            assert response.status == ConnectorStatus.ERROR

    @pytest.mark.asyncio
    async def test_get_user_info_success(self):
        """Test getting user information"""
        connector = LoomConnector({"access_token": "test_token"})

        with patch.object(connector, 'make_request') as mock_request:
            mock_request.return_value = ConnectorResponse(
                status=ConnectorStatus.SUCCESS,
                data=MOCK_LOOM_USER
            )

            response = await connector.get_user_info()

            assert response.status == ConnectorStatus.SUCCESS
            assert response.data["email"] == MOCK_LOOM_USER["email"]
            mock_request.assert_called_once_with("GET", "/users/me")


class TestVideoRetrieval:
    """Test video retrieval operations"""

    @pytest.mark.asyncio
    async def test_list_videos_default_params(self):
        """Test listing videos with default parameters"""
        connector = LoomConnector({"access_token": "test_token"})

        with patch.object(connector, 'make_request') as mock_request:
            mock_request.return_value = ConnectorResponse(
                status=ConnectorStatus.SUCCESS,
                data={"videos": MOCK_LOOM_VIDEOS}
            )

            response = await connector.list_videos()

            assert response.status == ConnectorStatus.SUCCESS
            assert len(response.data["videos"]) == len(MOCK_LOOM_VIDEOS)
            mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_videos_with_custom_params(self):
        """Test listing videos with custom parameters"""
        connector = LoomConnector({"access_token": "test_token"})

        with patch.object(connector, 'make_request') as mock_request:
            mock_request.return_value = ConnectorResponse(
                status=ConnectorStatus.SUCCESS,
                data={"videos": MOCK_LOOM_VIDEOS[:10]}
            )

            await connector.list_videos(
                limit=10,
                offset=5,
                sort_by="views",
                sort_direction="asc"
            )

            call_args = mock_request.call_args
            assert call_args[1]["params"]["limit"] == 10
            assert call_args[1]["params"]["offset"] == 5
            assert call_args[1]["params"]["sort_by"] == "views"
            assert call_args[1]["params"]["sort_direction"] == "asc"

    @pytest.mark.asyncio
    async def test_list_videos_pagination(self):
        """Test video list pagination"""
        connector = LoomConnector({"access_token": "test_token"})

        with patch.object(connector, 'make_request') as mock_request:
            # First page
            mock_request.return_value = ConnectorResponse(
                status=ConnectorStatus.SUCCESS,
                data={"videos": MOCK_LOOM_VIDEOS[:2]}
            )

            response = await connector.list_videos(limit=2, offset=0)
            assert len(response.data["videos"]) == 2

            # Second page
            mock_request.return_value = ConnectorResponse(
                status=ConnectorStatus.SUCCESS,
                data={"videos": MOCK_LOOM_VIDEOS[2:4]}
            )

            response = await connector.list_videos(limit=2, offset=2)
            assert len(response.data["videos"]) == 2

    @pytest.mark.asyncio
    async def test_get_video_by_id(self):
        """Test getting specific video by ID"""
        connector = LoomConnector({"access_token": "test_token"})
        video = MOCK_LOOM_VIDEOS[0]

        with patch.object(connector, 'make_request') as mock_request:
            mock_request.return_value = ConnectorResponse(
                status=ConnectorStatus.SUCCESS,
                data=video
            )

            response = await connector.get_video(video["id"])

            assert response.status == ConnectorStatus.SUCCESS
            assert response.data["id"] == video["id"]
            assert response.data["name"] == video["name"]
            mock_request.assert_called_once_with("GET", f"/videos/{video['id']}")

    @pytest.mark.asyncio
    async def test_get_video_not_found(self):
        """Test getting non-existent video"""
        connector = LoomConnector({"access_token": "test_token"})

        with patch.object(connector, 'make_request') as mock_request:
            mock_request.side_effect = ConnectorError(
                "Video not found",
                status_code=404
            )

            with pytest.raises(ConnectorError) as exc_info:
                await connector.get_video("invalid_id")

            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_get_video_processing_status(self):
        """Test getting video that is still processing"""
        connector = LoomConnector({"access_token": "test_token"})
        processing_video = MOCK_LOOM_VIDEOS[4]  # Processing video

        with patch.object(connector, 'make_request') as mock_request:
            mock_request.return_value = ConnectorResponse(
                status=ConnectorStatus.SUCCESS,
                data=processing_video
            )

            response = await connector.get_video(processing_video["id"])

            assert response.data["status"] == "PROCESSING"
            assert response.data["duration"] is None


class TestVideoTranscripts:
    """Test video transcript operations"""

    @pytest.mark.asyncio
    async def test_get_video_transcript_success(self):
        """Test getting video transcript"""
        connector = LoomConnector({"access_token": "test_token"})
        video_id = "video_1_sprint_review"
        transcript = get_mock_transcript(video_id)

        with patch.object(connector, 'make_request') as mock_request:
            mock_request.return_value = ConnectorResponse(
                status=ConnectorStatus.SUCCESS,
                data=transcript
            )

            response = await connector.get_video_transcript(video_id)

            assert response.status == ConnectorStatus.SUCCESS
            assert response.data["video_id"] == video_id
            assert len(response.data["full_text"]) > 0
            mock_request.assert_called_once_with(
                "GET",
                f"/videos/{video_id}/transcript"
            )

    @pytest.mark.asyncio
    async def test_get_video_transcript_with_words(self):
        """Test transcript includes word-level timing"""
        connector = LoomConnector({"access_token": "test_token"})
        video_id = "video_1_sprint_review"
        transcript = get_mock_transcript(video_id)

        with patch.object(connector, 'make_request') as mock_request:
            mock_request.return_value = ConnectorResponse(
                status=ConnectorStatus.SUCCESS,
                data=transcript
            )

            response = await connector.get_video_transcript(video_id)

            assert "words" in response.data
            if response.data["words"]:
                word = response.data["words"][0]
                assert "text" in word
                assert "start" in word
                assert "end" in word

    @pytest.mark.asyncio
    async def test_get_video_transcript_empty(self):
        """Test getting transcript for video with no transcript"""
        connector = LoomConnector({"access_token": "test_token"})
        video_id = "video_no_transcript"

        with patch.object(connector, 'make_request') as mock_request:
            mock_request.return_value = ConnectorResponse(
                status=ConnectorStatus.SUCCESS,
                data={"video_id": video_id, "full_text": "", "words": []}
            )

            response = await connector.get_video_transcript(video_id)

            assert response.data["full_text"] == ""
            assert len(response.data["words"]) == 0


class TestVideoInsights:
    """Test video insights and analytics"""

    @pytest.mark.asyncio
    async def test_get_video_insights_success(self):
        """Test getting video insights"""
        connector = LoomConnector({"access_token": "test_token"})
        video_id = "video_1_sprint_review"
        insights = get_mock_insights(video_id)

        with patch.object(connector, 'make_request') as mock_request:
            mock_request.return_value = ConnectorResponse(
                status=ConnectorStatus.SUCCESS,
                data=insights
            )

            response = await connector.get_video_insights(video_id)

            assert response.status == ConnectorStatus.SUCCESS
            assert response.data["total_views"] > 0
            assert "engagement_score" in response.data
            mock_request.assert_called_once_with(
                "GET",
                f"/videos/{video_id}/insights"
            )

    @pytest.mark.asyncio
    async def test_get_video_insights_metrics(self):
        """Test insights include all expected metrics"""
        connector = LoomConnector({"access_token": "test_token"})
        video_id = "video_1_sprint_review"
        insights = get_mock_insights(video_id)

        with patch.object(connector, 'make_request') as mock_request:
            mock_request.return_value = ConnectorResponse(
                status=ConnectorStatus.SUCCESS,
                data=insights
            )

            response = await connector.get_video_insights(video_id)

            data = response.data
            assert "total_views" in data
            assert "unique_viewers" in data
            assert "avg_watch_percentage" in data
            assert "completion_rate" in data
            assert "engagement_score" in data


class TestVideoSearch:
    """Test video search functionality"""

    @pytest.mark.asyncio
    async def test_search_videos_success(self):
        """Test searching videos"""
        connector = LoomConnector({"access_token": "test_token"})

        with patch.object(connector, 'make_request') as mock_request:
            mock_request.return_value = ConnectorResponse(
                status=ConnectorStatus.SUCCESS,
                data={"videos": [MOCK_LOOM_VIDEOS[0]]}
            )

            response = await connector.search_videos("sprint review")

            assert response.status == ConnectorStatus.SUCCESS
            assert len(response.data["videos"]) > 0
            mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_videos_with_limit(self):
        """Test search with custom limit"""
        connector = LoomConnector({"access_token": "test_token"})

        with patch.object(connector, 'make_request') as mock_request:
            mock_request.return_value = ConnectorResponse(
                status=ConnectorStatus.SUCCESS,
                data={"videos": MOCK_LOOM_VIDEOS[:10]}
            )

            await connector.search_videos("sprint", limit=10)

            call_args = mock_request.call_args
            assert call_args[1]["params"]["limit"] == 10

    @pytest.mark.asyncio
    async def test_search_videos_no_results(self):
        """Test search with no results"""
        connector = LoomConnector({"access_token": "test_token"})

        with patch.object(connector, 'make_request') as mock_request:
            mock_request.return_value = ConnectorResponse(
                status=ConnectorStatus.SUCCESS,
                data={"videos": []}
            )

            response = await connector.search_videos("nonexistent query")

            assert response.status == ConnectorStatus.SUCCESS
            assert len(response.data["videos"]) == 0


class TestFolderOperations:
    """Test folder management"""

    @pytest.mark.asyncio
    async def test_list_folders_success(self):
        """Test listing folders"""
        connector = LoomConnector({"access_token": "test_token"})

        with patch.object(connector, 'make_request') as mock_request:
            mock_request.return_value = ConnectorResponse(
                status=ConnectorStatus.SUCCESS,
                data={"folders": MOCK_LOOM_FOLDERS}
            )

            response = await connector.list_folders()

            assert response.status == ConnectorStatus.SUCCESS
            assert len(response.data["folders"]) == len(MOCK_LOOM_FOLDERS)
            mock_request.assert_called_once_with("GET", "/folders")

    @pytest.mark.asyncio
    async def test_get_folder_videos_success(self):
        """Test getting videos in a folder"""
        connector = LoomConnector({"access_token": "test_token"})
        folder_id = "folder_sprints"

        with patch.object(connector, 'make_request') as mock_request:
            mock_request.return_value = ConnectorResponse(
                status=ConnectorStatus.SUCCESS,
                data={"videos": [MOCK_LOOM_VIDEOS[0]]}
            )

            response = await connector.get_folder_videos(folder_id)

            assert response.status == ConnectorStatus.SUCCESS
            assert len(response.data["videos"]) > 0
            mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_folder_videos_with_limit(self):
        """Test getting folder videos with limit"""
        connector = LoomConnector({"access_token": "test_token"})
        folder_id = "folder_demos"

        with patch.object(connector, 'make_request') as mock_request:
            mock_request.return_value = ConnectorResponse(
                status=ConnectorStatus.SUCCESS,
                data={"videos": MOCK_LOOM_VIDEOS[:5]}
            )

            await connector.get_folder_videos(folder_id, limit=5)

            call_args = mock_request.call_args
            assert call_args[1]["params"]["limit"] == 5


class TestVideoManagement:
    """Test video update and delete operations"""

    @pytest.mark.asyncio
    async def test_update_video_title(self):
        """Test updating video title"""
        connector = LoomConnector({"access_token": "test_token"})
        video_id = "video_1_sprint_review"
        new_title = "Updated Sprint Review Title"

        with patch.object(connector, 'make_request') as mock_request:
            updated_video = MOCK_LOOM_VIDEOS[0].copy()
            updated_video["name"] = new_title
            mock_request.return_value = ConnectorResponse(
                status=ConnectorStatus.SUCCESS,
                data=updated_video
            )

            response = await connector.update_video(video_id, title=new_title)

            assert response.status == ConnectorStatus.SUCCESS
            assert response.data["name"] == new_title
            mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_video_description(self):
        """Test updating video description"""
        connector = LoomConnector({"access_token": "test_token"})
        video_id = "video_1_sprint_review"
        new_description = "Updated description"

        with patch.object(connector, 'make_request') as mock_request:
            updated_video = MOCK_LOOM_VIDEOS[0].copy()
            updated_video["description"] = new_description
            mock_request.return_value = ConnectorResponse(
                status=ConnectorStatus.SUCCESS,
                data=updated_video
            )

            response = await connector.update_video(
                video_id,
                description=new_description
            )

            assert response.data["description"] == new_description

    @pytest.mark.asyncio
    async def test_update_video_both_fields(self):
        """Test updating both title and description"""
        connector = LoomConnector({"access_token": "test_token"})
        video_id = "video_1_sprint_review"

        with patch.object(connector, 'make_request') as mock_request:
            mock_request.return_value = ConnectorResponse(
                status=ConnectorStatus.SUCCESS,
                data={}
            )

            await connector.update_video(
                video_id,
                title="New Title",
                description="New Description"
            )

            call_args = mock_request.call_args
            assert "title" in call_args[1]["json"]
            assert "description" in call_args[1]["json"]

    @pytest.mark.asyncio
    async def test_delete_video_success(self):
        """Test deleting a video"""
        connector = LoomConnector({"access_token": "test_token"})
        video_id = "video_to_delete"

        with patch.object(connector, 'make_request') as mock_request:
            mock_request.return_value = ConnectorResponse(
                status=ConnectorStatus.SUCCESS,
                data={"deleted": True}
            )

            response = await connector.delete_video(video_id)

            assert response.status == ConnectorStatus.SUCCESS
            mock_request.assert_called_once_with("DELETE", f"/videos/{video_id}")

    @pytest.mark.asyncio
    async def test_delete_video_not_found(self):
        """Test deleting non-existent video"""
        connector = LoomConnector({"access_token": "test_token"})

        with patch.object(connector, 'make_request') as mock_request:
            mock_request.side_effect = ConnectorError(
                "Video not found",
                status_code=404
            )

            with pytest.raises(ConnectorError):
                await connector.delete_video("invalid_id")


class TestErrorHandling:
    """Test error handling"""

    @pytest.mark.asyncio
    async def test_invalid_credentials(self):
        """Test with invalid credentials"""
        connector = LoomConnector({})

        with pytest.raises(ConnectorError):
            connector.validate_credentials()

    @pytest.mark.asyncio
    async def test_api_rate_limit(self):
        """Test rate limit handling"""
        connector = LoomConnector({"access_token": "test_token"})

        with patch.object(connector, 'make_request') as mock_request:
            mock_request.side_effect = ConnectorError(
                "Rate limit exceeded",
                status_code=429
            )

            with pytest.raises(ConnectorError) as exc_info:
                await connector.list_videos()

            assert exc_info.value.status_code == 429

    @pytest.mark.asyncio
    async def test_unauthorized_access(self):
        """Test unauthorized access error"""
        connector = LoomConnector({"access_token": "invalid_token"})

        with patch.object(connector, 'make_request') as mock_request:
            mock_request.side_effect = ConnectorError(
                "Unauthorized",
                status_code=401
            )

            with pytest.raises(ConnectorError) as exc_info:
                await connector.get_user_info()

            assert exc_info.value.status_code == 401


class TestContextManager:
    """Test async context manager"""

    @pytest.mark.asyncio
    async def test_context_manager_lifecycle(self):
        """Test connector lifecycle with context manager"""
        async with LoomConnector({"access_token": "test_token"}) as connector:
            assert connector.credentials["access_token"] == "test_token"

        assert connector._http_client is None
