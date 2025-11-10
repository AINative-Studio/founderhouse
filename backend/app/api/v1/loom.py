"""
Loom Video API Endpoints
Endpoints for ingesting and summarizing Loom videos
"""
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends, Query, Body, Path

from app.services.loom_service import LoomService
from app.models.loom_video import (
    LoomVideoIngestRequest,
    LoomVideoResponse,
    LoomSummarizeRequest,
    LoomVideoListResponse,
    LoomVideoStatus,
    LoomVideoType
)


router = APIRouter(prefix="/loom", tags=["Loom Videos"])


def get_loom_service() -> LoomService:
    """Dependency for Loom service"""
    return LoomService()


@router.post("/ingest", response_model=LoomVideoResponse)
async def ingest_video(
    request: LoomVideoIngestRequest = Body(...),
    service: LoomService = Depends(get_loom_service)
):
    """
    Ingest a Loom video for processing

    Accepts a Loom video URL and optionally starts automatic summarization.
    The video will be downloaded, transcribed, and summarized if auto_summarize is true.
    """
    try:
        result = await service.ingest_video(request)

        if not result:
            raise HTTPException(status_code=500, detail="Failed to ingest video")

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error ingesting video: {str(e)}")


@router.post("/{video_id}/summarize", response_model=LoomVideoResponse)
async def summarize_video(
    video_id: UUID = Path(..., description="Video ID"),
    request: LoomSummarizeRequest = Body(...),
    service: LoomService = Depends(get_loom_service)
):
    """
    Generate summary for a Loom video

    Creates an AI-powered summary with key points, action items, and topics.
    The video must already be ingested and transcribed.
    """
    try:
        result = await service.summarize_video(video_id, request)

        if not result:
            raise HTTPException(status_code=500, detail="Failed to summarize video")

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error summarizing video: {str(e)}")


@router.get("/{video_id}", response_model=LoomVideoResponse)
async def get_video(
    video_id: UUID = Path(..., description="Video ID"),
    service: LoomService = Depends(get_loom_service)
):
    """
    Get video details by ID

    Returns full video information including transcript, summary, and processing status.
    """
    try:
        video = await service.get_video(video_id)

        if not video:
            raise HTTPException(status_code=404, detail="Video not found")

        return video

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching video: {str(e)}")


@router.get("/list", response_model=LoomVideoListResponse)
async def list_videos(
    workspace_id: UUID = Query(..., description="Workspace ID"),
    founder_id: Optional[UUID] = Query(None, description="Filter by founder"),
    video_type: Optional[LoomVideoType] = Query(None, description="Filter by type"),
    status: Optional[LoomVideoStatus] = Query(None, description="Filter by status"),
    limit: int = Query(50, le=100, description="Max number of videos to return"),
    service: LoomService = Depends(get_loom_service)
):
    """
    List Loom videos with filters

    Returns paginated list of videos with optional filtering by founder, type, and status.
    """
    try:
        videos = await service.list_videos(
            workspace_id=workspace_id,
            founder_id=founder_id,
            video_type=video_type,
            status=status,
            limit=limit
        )

        return LoomVideoListResponse(
            videos=videos,
            total_count=len(videos),
            has_more=len(videos) >= limit,
            filters_applied={
                "workspace_id": str(workspace_id),
                "founder_id": str(founder_id) if founder_id else None,
                "video_type": video_type.value if video_type else None,
                "status": status.value if status else None
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing videos: {str(e)}")
