"""
Loom Video Service
Service for ingesting and summarizing Loom videos
Integrates with Loom MCP connector for video processing
"""
import logging
import re
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime

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
from app.database import get_db_context
from sqlalchemy import text


logger = logging.getLogger(__name__)


class LoomService:
    """Service for Loom video ingestion and summarization"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

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
                    return await self._build_video_response(existing)

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

            video_response = await self._build_video_response(row)

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
            return await self._build_video_response(row)

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

                return await self._build_video_response(row)

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
                    videos.append(await self._build_video_response(row))

                return videos

        except Exception as e:
            self.logger.error(f"Error listing videos: {str(e)}")
            return []

    async def _process_video(self, video_id: UUID):
        """Background processing of video"""
        try:
            # Update status to downloading
            await self._update_video_status(video_id, LoomVideoStatus.DOWNLOADING)

            # In production, download video via Loom MCP
            # For now, simulate processing
            await self._update_video_status(video_id, LoomVideoStatus.TRANSCRIBING)

            # Get transcript from Loom
            # transcript = await loom_mcp.get_transcript(video_id)

            # For now, use mock transcript
            transcript = self._mock_transcript()

            await self._update_video(
                video_id,
                LoomVideoUpdate(transcript=transcript)
            )

            # Generate summary
            await self.summarize_video(
                video_id,
                LoomSummarizeRequest(
                    include_action_items=True,
                    include_topics=True
                )
            )

        except Exception as e:
            self.logger.error(f"Error processing video: {str(e)}")
            await self._update_video(
                video_id,
                LoomVideoUpdate(
                    status=LoomVideoStatus.FAILED,
                    error_message=str(e)
                )
            )

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
        Generate summary from transcript using AI

        In production, this would use LLM for summarization
        """
        # Simple extractive summary for now
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
            topics = ["Product Demo", "Dashboard", "Metrics"]

        return LoomVideoSummary(
            executive_summary=executive_summary,
            key_points=key_points,
            action_items=action_items if include_action_items else [],
            topics=topics if include_topics else [],
            participants=["Team"],
            duration_minutes=5,
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

    async def _build_video_response(self, row) -> LoomVideoResponse:
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
