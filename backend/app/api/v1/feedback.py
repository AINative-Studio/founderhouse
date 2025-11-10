"""
Feedback API Endpoints
Endpoints for submitting and managing user feedback
"""
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends, Query, Body, Path

from app.services.feedback_service import FeedbackService
from app.models.feedback import (
    FeedbackSubmitRequest,
    FeedbackResponse,
    FeedbackListResponse,
    FeedbackType,
    FeedbackCategory,
    FeedbackStatus,
    FeedbackSentiment,
    FeedbackAnalytics
)


router = APIRouter(prefix="/feedback", tags=["Feedback"])


def get_feedback_service() -> FeedbackService:
    """Dependency for feedback service"""
    return FeedbackService()


@router.post("", response_model=FeedbackResponse)
async def submit_feedback(
    request: FeedbackSubmitRequest = Body(...),
    service: FeedbackService = Depends(get_feedback_service)
):
    """
    Submit feedback

    Submit bug reports, feature requests, suggestions, or other feedback.
    Feedback is automatically analyzed for sentiment and prioritized.
    """
    try:
        result = await service.submit_feedback(request)

        if not result:
            raise HTTPException(status_code=500, detail="Failed to submit feedback")

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error submitting feedback: {str(e)}")


@router.get("/{feedback_id}", response_model=FeedbackResponse)
async def get_feedback(
    feedback_id: UUID = Path(..., description="Feedback ID"),
    service: FeedbackService = Depends(get_feedback_service)
):
    """
    Get feedback by ID

    Returns detailed information about a specific feedback submission.
    """
    try:
        feedback = await service.get_feedback(feedback_id)

        if not feedback:
            raise HTTPException(status_code=404, detail="Feedback not found")

        return feedback

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching feedback: {str(e)}")


@router.get("", response_model=FeedbackListResponse)
async def list_feedback(
    workspace_id: UUID = Query(..., description="Workspace ID"),
    founder_id: Optional[UUID] = Query(None, description="Filter by founder"),
    feedback_type: Optional[FeedbackType] = Query(None, description="Filter by type"),
    category: Optional[FeedbackCategory] = Query(None, description="Filter by category"),
    status: Optional[FeedbackStatus] = Query(None, description="Filter by status"),
    sentiment: Optional[FeedbackSentiment] = Query(None, description="Filter by sentiment"),
    limit: int = Query(50, le=100, description="Max number of items to return"),
    service: FeedbackService = Depends(get_feedback_service)
):
    """
    List feedback with filters

    Returns paginated list of feedback submissions with optional filtering.
    """
    try:
        feedback_list = await service.list_feedback(
            workspace_id=workspace_id,
            founder_id=founder_id,
            feedback_type=feedback_type,
            category=category,
            status=status,
            sentiment=sentiment,
            limit=limit
        )

        return FeedbackListResponse(
            feedback_items=feedback_list,
            total_count=len(feedback_list),
            has_more=len(feedback_list) >= limit,
            filters_applied={
                "workspace_id": str(workspace_id),
                "founder_id": str(founder_id) if founder_id else None,
                "type": feedback_type.value if feedback_type else None,
                "category": category.value if category else None,
                "status": status.value if status else None,
                "sentiment": sentiment.value if sentiment else None
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing feedback: {str(e)}")


@router.patch("/{feedback_id}/status", response_model=FeedbackResponse)
async def update_feedback_status(
    feedback_id: UUID = Path(..., description="Feedback ID"),
    status: FeedbackStatus = Body(..., description="New status"),
    admin_notes: Optional[str] = Body(None, description="Admin notes"),
    service: FeedbackService = Depends(get_feedback_service)
):
    """
    Update feedback status

    Updates the processing status of feedback (admin only in production).
    """
    try:
        result = await service.update_feedback_status(
            feedback_id=feedback_id,
            status=status,
            admin_notes=admin_notes
        )

        if not result:
            raise HTTPException(status_code=404, detail="Feedback not found")

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating feedback: {str(e)}")


@router.post("/{feedback_id}/upvote")
async def upvote_feedback(
    feedback_id: UUID = Path(..., description="Feedback ID"),
    service: FeedbackService = Depends(get_feedback_service)
):
    """
    Upvote feedback

    Increases the upvote count for feedback, indicating its importance to users.
    """
    try:
        success = await service.upvote_feedback(feedback_id)

        if not success:
            raise HTTPException(status_code=404, detail="Feedback not found")

        return {"status": "upvoted", "feedback_id": str(feedback_id)}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error upvoting feedback: {str(e)}")


@router.get("/analytics/summary", response_model=FeedbackAnalytics)
async def get_feedback_analytics(
    workspace_id: UUID = Query(..., description="Workspace ID"),
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    service: FeedbackService = Depends(get_feedback_service)
):
    """
    Get feedback analytics

    Returns aggregated analytics about feedback submissions including trends,
    sentiment distribution, and top requested features.
    """
    try:
        analytics = await service.get_analytics(
            workspace_id=workspace_id,
            days=days
        )

        return analytics

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching analytics: {str(e)}")
