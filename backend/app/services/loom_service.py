"""
Loom Video Service
Service for ingesting and summarizing Loom videos
Integrates with Loom MCP connector for video processing with Otter.ai fallback
"""
import logging
import re
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime
import asyncio

from app.models.loom_video import (
    LoomVideoIngestRequest,
    LoomVideoResponse,
    LoomVideoCreate,
    LoomVideoUpdate,
    LoomVideoStatus,
    LoomVideoType,
    LoomVideoSummary,
    LoomSummarizeRequest
)
from app.mcp.loom_client import LoomMCPClient
from app.connectors.otter_connector import OtterConnector
from app.connectors.base_connector import ConnectorStatus
from app.services.summarization_service import SummarizationService
from app.database import get_db_context
from app.config import get_settings
from sqlalchemy import text


logger = logging.getLogger(__name__)
settings = get_settings()


class LoomService:
    """
    Service for Loom video ingestion and summarization

    Features:
    - Loom MCP integration for video metadata and transcripts
    - Otter.ai fallback for transcription when Loom fails
    - Async background processing
    - Reuses meeting summarization logic
    - 3-minute SLA for video processing
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.loom_credentials = {
            "api_key": settings.loom_client_id,
            "client_id": settings.loom_client_id,
            "client_secret": settings.loom_client_secret
        }
        self.otter_credentials = {
            "api_key": getattr(settings, "otter_api_key", None)
        }
        self.summarization_service = SummarizationService()

    async def ingest_video(
        self,
        request: LoomVideoIngestRequest
    ) -> Optional[LoomVideoResponse]:
        """
        Ingest a Loom video for processing

        Args:
            request: Video ingestion request

        Returns:
            Video record
        """
        try:
            # Extract video ID from URL
            video_id = request.video_id or self._extract_video_id(str(request.video_url))

            if not video_id:
                raise ValueError("Could not extract video ID from URL")

            # Check if video already exists
            async with get_db_context() as db:
                result = await db.execute(
                    text("""
                        SELECT * FROM loom_videos
                        WHERE workspace_id = :workspace_id AND video_id = :video_id
                    """),
                    {
                        "workspace_id": str(request.workspace_id),
                        "video_id": video_id
                    }
                )
                existing = result.fetchone()

                if existing:
                    self.logger.info(f"Video {video_id} already exists")
                    return self._build_video_response(existing)

            # Create video record
            video_create = LoomVideoCreate(
                workspace_id=request.workspace_id,
                founder_id=request.founder_id,
                video_id=video_id,
                video_url=str(request.video_url),
                title=request.title,
                description=request.description,
                video_type=request.video_type,
                status=LoomVideoStatus.PENDING
            )

            async with get_db_context() as db:
                result = await db.execute(
                    text("""
                        INSERT INTO loom_videos
                        (workspace_id, founder_id, video_id, video_url, title, description, video_type, status)
                        VALUES (:workspace_id, :founder_id, :video_id, :video_url, :title, :description, :video_type, :status)
                        RETURNING *
                    """),
                    {
                        "workspace_id": str(video_create.workspace_id),
                        "founder_id": str(video_create.founder_id),
                        "video_id": video_create.video_id,
                        "video_url": video_create.video_url,
                        "title": video_create.title,
                        "description": video_create.description,
                        "video_type": video_create.video_type.value,
                        "status": video_create.status.value
                    }
                )
                await db.commit()
                row = result.fetchone()

            video_response = self._build_video_response(row)

            # If auto-summarize is enabled, process video
            if request.auto_summarize:
                # Process video asynchronously (in production, use background task)
                await self._process_video(video_response.id)

            self.logger.info(f"Ingested Loom video {video_id} for workspace {request.workspace_id}")
            return video_response

        except Exception as e:
            self.logger.error(f"Error ingesting video: {str(e)}")
            return None

    async def summarize_video(
        self,
        video_id: UUID,
        request: LoomSummarizeRequest
    ) -> Optional[LoomVideoResponse]:
        """
        Generate summary for a Loom video

        Args:
            video_id: Video ID
            request: Summarization request

        Returns:
            Updated video record with summary
        """
        try:
            # Get video
            async with get_db_context() as db:
                result = await db.execute(
                    text("SELECT * FROM loom_videos WHERE id = :id"),
                    {"id": str(video_id)}
                )
                video = result.fetchone()

                if not video:
                    raise ValueError(f"Video {video_id} not found")

            # Update status to summarizing
            await self._update_video_status(video_id, LoomVideoStatus.SUMMARIZING)

            # Get or generate transcript
            transcript = video.transcript
            if not transcript:
                transcript = await self._get_transcript(video.video_id)
                if transcript:
                    await self._update_video(video_id, LoomVideoUpdate(transcript=transcript))

            if not transcript:
                raise ValueError("No transcript available for video")

            # Generate summary
            summary = await self._generate_summary(
                transcript,
                include_action_items=request.include_action_items,
                include_topics=request.include_topics,
                max_length=request.max_summary_length
            )

            # Update video with summary
            update = LoomVideoUpdate(
                status=LoomVideoStatus.COMPLETED,
                summary=summary,
                completed_at=datetime.utcnow()
            )

            await self._update_video(video_id, update)

            # Get updated video
            async with get_db_context() as db:
                result = await db.execute(
                    text("SELECT * FROM loom_videos WHERE id = :id"),
                    {"id": str(video_id)}
                )
                row = result.fetchone()

            self.logger.info(f"Summarized video {video_id}")
            return self._build_video_response(row)

        except Exception as e:
            self.logger.error(f"Error summarizing video: {str(e)}")
            # Update status to failed
            await self._update_video(
                video_id,
                LoomVideoUpdate(
                    status=LoomVideoStatus.FAILED,
                    error_message=str(e)
                )
            )
            return None

    async def get_video(self, video_id: UUID) -> Optional[LoomVideoResponse]:
        """Get video by ID"""
        try:
            async with get_db_context() as db:
                result = await db.execute(
                    text("SELECT * FROM loom_videos WHERE id = :id"),
                    {"id": str(video_id)}
                )
                row = result.fetchone()

                if not row:
                    return None

                return self._build_video_response(row)

        except Exception as e:
            self.logger.error(f"Error getting video: {str(e)}")
            return None

    async def list_videos(
        self,
        workspace_id: UUID,
        founder_id: Optional[UUID] = None,
        video_type: Optional[LoomVideoType] = None,
        status: Optional[LoomVideoStatus] = None,
        limit: int = 50
    ) -> List[LoomVideoResponse]:
        """List videos with filters"""
        try:
            query = "SELECT * FROM loom_videos WHERE workspace_id = :workspace_id"
            params = {"workspace_id": str(workspace_id)}

            if founder_id:
                query += " AND founder_id = :founder_id"
                params["founder_id"] = str(founder_id)

            if video_type:
                query += " AND video_type = :video_type"
                params["video_type"] = video_type.value

            if status:
                query += " AND status = :status"
                params["status"] = status.value

            query += " ORDER BY created_at DESC LIMIT :limit"
            params["limit"] = limit

            async with get_db_context() as db:
                result = await db.execute(text(query), params)
                rows = result.fetchall()

                videos = []
                for row in rows:
                    videos.append(self._build_video_response(row))

                return videos

        except Exception as e:
            self.logger.error(f"Error listing videos: {str(e)}")
            return []

    async def _process_video(self, video_id: UUID):
        """
        Background processing of video with 3-minute SLA target

        Steps:
        1. Update status to downloading
        2. Fetch video metadata via Loom MCP
        3. Extract transcript (Loom MCP primary, Otter fallback)
        4. Generate summary using meeting summarization logic
        5. Update status to completed

        Raises exception if processing fails
        """
        try:
            processing_start = datetime.utcnow()

            # Get video from database
            async with get_db_context() as db:
                result = await db.execute(
                    text("SELECT * FROM loom_videos WHERE id = :id"),
                    {"id": str(video_id)}
                )
                video = result.fetchone()

                if not video:
                    raise ValueError(f"Video {video_id} not found")

            loom_video_id = video.video_id

            # Update status to downloading
            await self._update_video_status(video_id, LoomVideoStatus.DOWNLOADING)

            # Fetch video metadata via Loom MCP
            video_metadata = await self._get_video_metadata(loom_video_id)

            # Update status to transcribing
            await self._update_video_status(video_id, LoomVideoStatus.TRANSCRIBING)

            # Get transcript - try Loom first, fallback to Otter
            transcript = await self._get_transcript(loom_video_id)

            if not transcript:
                raise ValueError("Failed to obtain transcript from Loom or Otter")

            # Update video with transcript and metadata
            update_data = LoomVideoUpdate(transcript=transcript)
            if video_metadata:
                update_data.thumbnail_url = video_metadata.get("thumbnail_url")
                update_data.duration_seconds = video_metadata.get("duration_seconds")

            await self._update_video(video_id, update_data)

            # Generate summary using meeting summarization logic
            await self.summarize_video(
                video_id,
                LoomSummarizeRequest(
                    include_action_items=True,
                    include_topics=True
                )
            )

            processing_time = (datetime.utcnow() - processing_start).total_seconds()
            self.logger.info(
                f"Video {video_id} processed successfully in {processing_time:.2f}s"
            )

            # Log if SLA exceeded
            if processing_time > 180:  # 3 minutes
                self.logger.warning(
                    f"Video {video_id} processing exceeded 3-minute SLA: {processing_time:.2f}s"
                )

        except Exception as e:
            self.logger.error(f"Error processing video {video_id}: {str(e)}")
            await self._update_video(
                video_id,
                LoomVideoUpdate(
                    status=LoomVideoStatus.FAILED,
                    error_message=str(e)
                )
            )
            raise

    async def _get_video_metadata(self, video_id: str) -> Optional[Dict[str, Any]]:
        """
        Get video metadata from Loom MCP

        Args:
            video_id: Loom video ID

        Returns:
            Video metadata dict or None
        """
        try:
            async with LoomMCPClient(self.loom_credentials) as client:
                video_data = await client.get_video_details(video_id)

                if not video_data:
                    return None

                return {
                    "title": video_data.title,
                    "description": video_data.description,
                    "duration_seconds": video_data.duration_seconds,
                    "thumbnail_url": video_data.thumbnail_url,
                    "owner_name": video_data.owner_name,
                    "owner_email": video_data.owner_email
                }

        except Exception as e:
            self.logger.error(f"Error fetching video metadata: {str(e)}")
            return None

    async def _get_transcript(self, video_id: str) -> Optional[str]:
        """
        Get transcript with fallback strategy:
        1. Try Loom MCP first
        2. Fallback to Otter.ai if Loom fails

        Args:
            video_id: Loom video ID

        Returns:
            Transcript text or None
        """
        # Try Loom MCP first
        transcript = await self._get_transcript_from_loom(video_id)

        if transcript:
            self.logger.info(f"Transcript obtained from Loom MCP for video {video_id}")
            return transcript

        # Fallback to Otter
        self.logger.warning(f"Loom transcript unavailable, attempting Otter fallback for video {video_id}")
        transcript = await self._get_transcript_from_otter(video_id)

        if transcript:
            self.logger.info(f"Transcript obtained from Otter fallback for video {video_id}")
            return transcript

        self.logger.error(f"Failed to obtain transcript from both Loom and Otter for video {video_id}")
        return None

    async def _get_transcript_from_loom(self, video_id: str) -> Optional[str]:
        """
        Get transcript from Loom MCP

        Args:
            video_id: Loom video ID

        Returns:
            Transcript text or None
        """
        try:
            async with LoomMCPClient(self.loom_credentials) as client:
                transcript_data = await client.get_video_transcript(video_id)

                if transcript_data:
                    return transcript_data.transcript_text

                return None

        except Exception as e:
            self.logger.error(f"Error fetching Loom transcript: {str(e)}")
            return None

    async def _get_transcript_from_otter(self, video_id: str) -> Optional[str]:
        """
        Get transcript from Otter.ai fallback

        Args:
            video_id: Video identifier

        Returns:
            Transcript text or None
        """
        try:
            if not self.otter_credentials.get("api_key"):
                self.logger.warning("Otter API key not configured, skipping fallback")
                return None

            async with OtterConnector(self.otter_credentials) as otter:
                # Use video_id as speech_id for Otter
                response = await otter.get_speech_transcript(video_id)

                if response.status == ConnectorStatus.SUCCESS:
                    transcript_data = response.data
                    return transcript_data.get("transcript", {}).get("text")

                return None

        except Exception as e:
            self.logger.error(f"Error fetching Otter transcript: {str(e)}")
            return None

    def _extract_video_id(self, video_url: str) -> Optional[str]:
        """Extract Loom video ID from URL"""
        # Loom URL format: https://www.loom.com/share/{video_id}
        patterns = [
            r'loom\.com/share/([a-zA-Z0-9]+)',
            r'loom\.com/embed/([a-zA-Z0-9]+)'
        ]

        for pattern in patterns:
            match = re.search(pattern, video_url)
            if match:
                return match.group(1)

        return None

    async def _get_transcript(self, video_id: str) -> Optional[str]:
        """Get transcript from Loom API"""
        # In production, this would call Loom MCP
        # For now, return mock transcript
        return self._mock_transcript()

    def _mock_transcript(self) -> str:
        """Mock transcript for testing"""
        return """
        Hey team, this is a quick product demo of our new feature.
        We've built a dashboard that shows real-time metrics.
        The key improvement is the automated anomaly detection.
        Action items: Test the new dashboard and provide feedback by Friday.
        Next steps: Roll out to beta users next week.
        """

    async def _generate_summary(
        self,
        transcript: str,
        include_action_items: bool = True,
        include_topics: bool = True,
        max_length: int = 500
    ) -> LoomVideoSummary:
        """
        Generate summary from transcript using meeting summarization logic

        Reuses existing SummarizationService to maintain consistency
        across meetings and Loom videos.

        Args:
            transcript: Video transcript text
            include_action_items: Extract action items
            include_topics: Extract topics
            max_length: Maximum summary length

        Returns:
            LoomVideoSummary
        """
        try:
            # Use meeting summarization service for consistency
            # Create temporary IDs for the summarization
            temp_meeting_id = uuid4()
            temp_workspace_id = uuid4()
            temp_founder_id = uuid4()

            result = await self.summarization_service.summarize_meeting(
                meeting_id=temp_meeting_id,
                workspace_id=temp_workspace_id,
                founder_id=temp_founder_id,
                transcript=transcript,
                extract_action_items=include_action_items,
                extract_decisions=False,  # Not relevant for videos
                analyze_sentiment=False   # Optional for videos
            )

            # Convert meeting summary to Loom video summary format
            summary_data = result.get("summary")
            action_items_data = result.get("action_items", [])

            # Extract action item descriptions
            action_items = [item.description for item in action_items_data]

            # Truncate executive summary to max length
            executive_summary = summary_data.executive_summary
            if len(executive_summary) > max_length:
                executive_summary = executive_summary[:max_length] + "..."

            return LoomVideoSummary(
                executive_summary=executive_summary,
                key_points=summary_data.key_points[:5],  # Limit to 5
                action_items=action_items if include_action_items else [],
                topics=summary_data.topics_discussed if include_topics else [],
                participants=["Video Creator"],
                duration_minutes=None,
                transcript_length=len(transcript)
            )

        except Exception as e:
            self.logger.error(f"Error generating summary with SummarizationService: {str(e)}")

            # Fallback to simple extractive summary
            lines = [line.strip() for line in transcript.strip().split('\n') if line.strip()]

            executive_summary = " ".join(lines[:2])[:max_length]

            key_points = []
            action_items = []
            topics = []

            for line in lines:
                line_lower = line.lower()
                if "action" in line_lower or "todo" in line_lower or "next step" in line_lower:
                    action_items.append(line)
                elif len(key_points) < 5:
                    key_points.append(line)

            # Extract topics (simplified)
            if include_topics:
                topics = ["Video Content"]

            return LoomVideoSummary(
                executive_summary=executive_summary,
                key_points=key_points,
                action_items=action_items if include_action_items else [],
                topics=topics if include_topics else [],
                participants=["Video Creator"],
                duration_minutes=None,
                transcript_length=len(transcript)
            )

    async def _update_video_status(self, video_id: UUID, status: LoomVideoStatus):
        """Update video status"""
        await self._update_video(video_id, LoomVideoUpdate(status=status))

    async def _update_video(self, video_id: UUID, update: LoomVideoUpdate):
        """Update video record"""
        try:
            updates = []
            params = {"id": str(video_id)}

            if update.status:
                updates.append("status = :status")
                params["status"] = update.status.value

            if update.transcript:
                updates.append("transcript = :transcript")
                params["transcript"] = update.transcript

            if update.summary:
                updates.append("summary = :summary")
                params["summary"] = update.summary.model_dump_json()

            if update.error_message:
                updates.append("error_message = :error_message")
                params["error_message"] = update.error_message

            if update.completed_at:
                updates.append("completed_at = :completed_at")
                params["completed_at"] = update.completed_at

            updates.append("updated_at = NOW()")

            if updates:
                query = f"UPDATE loom_videos SET {', '.join(updates)} WHERE id = :id"
                async with get_db_context() as db:
                    await db.execute(text(query), params)
                    await db.commit()

        except Exception as e:
            self.logger.error(f"Error updating video: {str(e)}")

    def _build_video_response(self, row) -> LoomVideoResponse:
        """Build video response from database row"""
        summary = None
        if row.summary:
            if isinstance(row.summary, str):
                import json
                summary = LoomVideoSummary(**json.loads(row.summary))
            else:
                summary = LoomVideoSummary(**row.summary)

        return LoomVideoResponse(
            id=row.id,
            workspace_id=UUID(row.workspace_id),
            founder_id=UUID(row.founder_id),
            video_id=row.video_id,
            video_url=row.video_url,
            title=row.title,
            description=row.description,
            video_type=LoomVideoType(row.video_type),
            status=LoomVideoStatus(row.status),
            thumbnail_url=row.thumbnail_url,
            duration_seconds=row.duration_seconds,
            transcript=row.transcript,
            summary=summary,
            metadata=row.metadata or {},
            error_message=row.error_message,
            created_at=row.created_at,
            updated_at=row.updated_at,
            completed_at=row.completed_at
        )
