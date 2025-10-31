"""
Meetings API Endpoints
Meeting ingestion, summarization, and intelligence
"""
import logging
from typing import List, Optional
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, Query
from pydantic import BaseModel

from app.models.meeting import (
    Meeting, MeetingIngestRequest, MeetingIngestResponse,
    MeetingStatus, MeetingSource
)
from app.models.meeting_summary import SummaryGenerationRequest, SummaryGenerationResponse
from app.models.action_item import ActionItem, ConvertToTaskRequest
from app.models.decision import Decision
from app.services.meeting_ingestion_service import MeetingIngestionService
from app.services.summarization_service import SummarizationService
from app.services.task_routing_service import TaskRoutingService


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/meetings", tags=["meetings"])


# Dependency injection placeholders
def get_supabase_client():
    """Get Supabase client (to be implemented)"""
    return None


def get_api_keys():
    """Get API keys for LLM providers (to be implemented)"""
    return {}


@router.post("/ingest", response_model=MeetingIngestResponse)
async def ingest_meeting(
    request: MeetingIngestRequest,
    background_tasks: BackgroundTasks,
    supabase=Depends(get_supabase_client)
):
    """
    Manually ingest meeting from platform

    Supports:
    - Zoom meetings
    - Fireflies transcripts
    - Otter speeches
    """
    try:
        start_time = datetime.utcnow()
        logger.info(f"Ingesting meeting from {request.source}: {request.platform_id}")

        # Initialize ingestion service
        ingestion_service = MeetingIngestionService(supabase)

        # Get credentials for platform (placeholder)
        credentials = await _get_platform_credentials(
            request.workspace_id,
            request.source
        )

        # Ingest based on source
        if request.source == MeetingSource.ZOOM:
            meeting, is_duplicate = await ingestion_service.ingest_from_zoom(
                workspace_id=request.workspace_id,
                founder_id=request.founder_id,
                meeting_id=request.platform_id,
                credentials=credentials
            )
        elif request.source == MeetingSource.FIREFLIES:
            meeting, is_duplicate = await ingestion_service.ingest_from_fireflies(
                workspace_id=request.workspace_id,
                founder_id=request.founder_id,
                transcript_id=request.platform_id,
                credentials=credentials
            )
        elif request.source == MeetingSource.OTTER:
            meeting, is_duplicate = await ingestion_service.ingest_from_otter(
                workspace_id=request.workspace_id,
                founder_id=request.founder_id,
                speech_id=request.platform_id,
                credentials=credentials
            )
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported source: {request.source}")

        # Mark ingestion as complete
        await ingestion_service.update_meeting_status(
            meeting.id,
            MeetingStatus.COMPLETED
        )

        # Trigger summarization in background
        if not is_duplicate or request.force_refresh:
            background_tasks.add_task(
                _trigger_summarization,
                meeting.id,
                meeting.workspace_id,
                meeting.founder_id,
                meeting.transcript or "",
                supabase
            )

        ingestion_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        return MeetingIngestResponse(
            meeting_id=meeting.id,
            status=meeting.status,
            message=f"Meeting ingested successfully from {request.source}",
            duplicate=is_duplicate,
            ingestion_time_ms=ingestion_time
        )

    except Exception as e:
        logger.error(f"Meeting ingestion failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{meeting_id}/summarize", response_model=SummaryGenerationResponse)
async def summarize_meeting(
    meeting_id: UUID,
    request: Optional[SummaryGenerationRequest] = None,
    background_tasks: BackgroundTasks = None,
    supabase=Depends(get_supabase_client),
    api_keys=Depends(get_api_keys)
):
    """Generate AI summary for meeting"""
    try:
        start_time = datetime.utcnow()
        logger.info(f"Summarizing meeting: {meeting_id}")

        # Fetch meeting
        meeting = await _get_meeting(meeting_id, supabase)
        if not meeting:
            raise HTTPException(status_code=404, detail="Meeting not found")

        if not meeting.get("transcript"):
            raise HTTPException(status_code=400, detail="Meeting has no transcript")

        # Initialize summarization service
        summarization_service = SummarizationService(supabase, api_keys=api_keys)

        # Run summarization
        result = await summarization_service.summarize_meeting(
            meeting_id=meeting_id,
            workspace_id=UUID(meeting["workspace_id"]),
            founder_id=UUID(meeting["founder_id"]),
            transcript=meeting["transcript"],
            extract_action_items=request.extract_action_items if request else True,
            extract_decisions=request.extract_decisions if request else True,
            analyze_sentiment=request.include_sentiment if request else True
        )

        processing_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        return SummaryGenerationResponse(
            summary_id=result["summary"].id,
            meeting_id=meeting_id,
            status="completed",
            message=f"Summary generated with {result['summary'].action_items_count} action items",
            processing_time_ms=processing_time,
            cost_usd=result["summary"].cost_usd
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Summarization failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{meeting_id}/summary")
async def get_meeting_summary(
    meeting_id: UUID,
    supabase=Depends(get_supabase_client)
):
    """Get meeting summary"""
    try:
        if not supabase:
            raise HTTPException(status_code=503, detail="Database not available")

        result = supabase.table("meeting_summaries").select("*").eq(
            "meeting_id", str(meeting_id)
        ).execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="Summary not found")

        return result.data[0]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch summary: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{meeting_id}/action-items", response_model=List[ActionItem])
async def get_meeting_action_items(
    meeting_id: UUID,
    supabase=Depends(get_supabase_client)
):
    """Get action items for meeting"""
    try:
        if not supabase:
            return []

        result = supabase.table("action_items").select("*").eq(
            "meeting_id", str(meeting_id)
        ).execute()

        return [ActionItem(**item) for item in result.data]

    except Exception as e:
        logger.error(f"Failed to fetch action items: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{meeting_id}/decisions", response_model=List[Decision])
async def get_meeting_decisions(
    meeting_id: UUID,
    supabase=Depends(get_supabase_client)
):
    """Get decisions from meeting"""
    try:
        if not supabase:
            return []

        result = supabase.table("decisions").select("*").eq(
            "meeting_id", str(meeting_id)
        ).execute()

        return [Decision(**dec) for dec in result.data]

    except Exception as e:
        logger.error(f"Failed to fetch decisions: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{meeting_id}/status")
async def get_meeting_status(
    meeting_id: UUID,
    supabase=Depends(get_supabase_client)
):
    """Get meeting ingestion and processing status"""
    try:
        meeting = await _get_meeting(meeting_id, supabase)
        if not meeting:
            raise HTTPException(status_code=404, detail="Meeting not found")

        return {
            "meeting_id": meeting_id,
            "status": meeting.get("status"),
            "ingestion_completed": meeting.get("ingestion_completed_at") is not None,
            "summarization_completed": meeting.get("summarization_completed_at") is not None,
            "error_message": meeting.get("error_message"),
            "created_at": meeting.get("created_at"),
            "updated_at": meeting.get("updated_at")
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch meeting status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{meeting_id}/create-tasks")
async def create_tasks_from_meeting(
    meeting_id: UUID,
    platform: str = "monday",
    board_id: Optional[str] = None,
    min_confidence: float = 0.7,
    supabase=Depends(get_supabase_client)
):
    """Create tasks from meeting action items"""
    try:
        logger.info(f"Creating tasks from meeting {meeting_id}")

        # Get credentials (placeholder)
        credentials = await _get_platform_credentials(None, platform)

        # Initialize task routing service
        task_service = TaskRoutingService(supabase)

        # Create tasks
        results = await task_service.create_tasks_from_meeting(
            meeting_id=meeting_id,
            platform=platform,
            credentials=credentials,
            board_id=board_id,
            min_confidence=min_confidence
        )

        success_count = sum(1 for r in results if r["status"] == "success")

        return {
            "total": len(results),
            "success": success_count,
            "failed": len(results) - success_count,
            "results": results
        }

    except Exception as e:
        logger.error(f"Task creation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch-summarize")
async def batch_summarize_meetings(
    meeting_ids: List[UUID],
    workspace_id: UUID,
    founder_id: UUID,
    background_tasks: BackgroundTasks,
    supabase=Depends(get_supabase_client),
    api_keys=Depends(get_api_keys)
):
    """Batch summarize multiple meetings"""
    try:
        logger.info(f"Batch summarizing {len(meeting_ids)} meetings")

        # Add to background tasks
        background_tasks.add_task(
            _batch_summarize,
            meeting_ids,
            workspace_id,
            founder_id,
            supabase,
            api_keys
        )

        return {
            "status": "processing",
            "meeting_count": len(meeting_ids),
            "message": "Batch summarization started"
        }

    except Exception as e:
        logger.error(f"Batch summarization failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Helper functions

async def _get_meeting(meeting_id: UUID, supabase):
    """Fetch meeting from database"""
    if not supabase:
        return None

    result = supabase.table("meetings").select("*").eq(
        "id", str(meeting_id)
    ).execute()

    return result.data[0] if result.data else None


async def _get_platform_credentials(workspace_id: Optional[UUID], platform: str):
    """Get platform credentials (placeholder)"""
    # In production, fetch encrypted credentials from database
    return {"access_token": "placeholder_token"}


async def _trigger_summarization(
    meeting_id: UUID,
    workspace_id: UUID,
    founder_id: UUID,
    transcript: str,
    supabase
):
    """Background task for summarization"""
    try:
        summarization_service = SummarizationService(supabase)
        await summarization_service.summarize_meeting(
            meeting_id=meeting_id,
            workspace_id=workspace_id,
            founder_id=founder_id,
            transcript=transcript
        )
    except Exception as e:
        logger.error(f"Background summarization failed: {str(e)}")


async def _batch_summarize(
    meeting_ids: List[UUID],
    workspace_id: UUID,
    founder_id: UUID,
    supabase,
    api_keys
):
    """Background task for batch summarization"""
    try:
        summarization_service = SummarizationService(supabase, api_keys=api_keys)
        await summarization_service.batch_summarize(
            meeting_ids=meeting_ids,
            workspace_id=workspace_id,
            founder_id=founder_id
        )
    except Exception as e:
        logger.error(f"Batch summarization failed: {str(e)}")
