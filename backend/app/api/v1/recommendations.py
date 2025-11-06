"""
Recommendations API Endpoints
Endpoints for generating and managing strategic recommendations
"""
from typing import List, Optional
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, Query, Body

from app.services.recommendation_service import RecommendationService
from app.models.recommendation import (
    RecommendationResponse,
    RecommendationListResponse,
    GenerateRecommendationRequest,
    GenerateRecommendationResponse,
    RecommendationFeedback,
    RecommendationImpact,
    RecommendationType,
    RecommendationStatus,
    RecommendationPriority
)


router = APIRouter(prefix="/recommendations", tags=["Recommendations"])


def get_recommendation_service() -> RecommendationService:
    """Dependency for recommendation service"""
    return RecommendationService()


@router.get("", response_model=RecommendationListResponse)
async def list_recommendations(
    workspace_id: UUID = Query(..., description="Workspace ID"),
    founder_id: Optional[UUID] = Query(None, description="Filter by founder"),
    recommendation_type: Optional[List[RecommendationType]] = Query(None),
    status: Optional[List[RecommendationStatus]] = Query(None),
    priority: Optional[List[RecommendationPriority]] = Query(None),
    min_confidence: Optional[float] = Query(None, ge=0.0, le=1.0),
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    rec_service: RecommendationService = Depends(get_recommendation_service)
):
    """
    List active recommendations

    Returns recommendations with optional filtering.
    """
    try:
        query = rec_service.supabase.table("recommendations").select("*").eq(
            "workspace_id", str(workspace_id)
        )

        if founder_id:
            query = query.eq("founder_id", str(founder_id))

        if recommendation_type:
            query = query.in_("recommendation_type", [rt.value for rt in recommendation_type])

        if status:
            query = query.in_("status", [s.value for s in status])

        if priority:
            query = query.in_("priority", [p.value for p in priority])

        if min_confidence:
            query = query.gte("confidence_score", min_confidence)

        count_result = query.execute()
        total_count = len(count_result.data)

        result = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()

        recommendations = [RecommendationResponse(**r) for r in result.data]

        return RecommendationListResponse(
            recommendations=recommendations,
            total_count=total_count,
            has_more=total_count > (offset + limit),
            filters_applied={
                "workspace_id": str(workspace_id),
                "founder_id": str(founder_id) if founder_id else None
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching recommendations: {str(e)}")


@router.post("/generate", response_model=GenerateRecommendationResponse)
async def generate_recommendations(
    request: GenerateRecommendationRequest = Body(...),
    rec_service: RecommendationService = Depends(get_recommendation_service)
):
    """
    Generate new recommendations

    Analyzes KPIs, anomalies, trends, and business context to generate
    actionable strategic recommendations.
    """
    try:
        recommendations = await rec_service.generate_recommendations(request)

        return GenerateRecommendationResponse(
            workspace_id=request.workspace_id,
            founder_id=request.founder_id,
            recommendations=recommendations,
            analysis_summary={
                "time_range_days": request.time_range_days,
                "focus_areas": [fa.value for fa in request.focus_areas] if request.focus_areas else None,
                "min_confidence": request.min_confidence
            },
            data_sources_used=["kpis", "anomalies", "trends", "meetings"],
            generated_at=datetime.utcnow()
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating recommendations: {str(e)}")


@router.put("/{recommendation_id}/feedback")
async def submit_feedback(
    recommendation_id: UUID,
    feedback: RecommendationFeedback = Body(...),
    rec_service: RecommendationService = Depends(get_recommendation_service)
):
    """
    Submit user feedback on a recommendation

    Collects user feedback to improve future recommendations.
    """
    try:
        # Store feedback
        result = rec_service.supabase.table("recommendation_feedback").insert(
            feedback.model_dump(mode="json")
        ).execute()

        # Update recommendation if implemented
        if feedback.was_implemented:
            rec_service.supabase.table("recommendations").update({
                "status": RecommendationStatus.IMPLEMENTED.value,
                "implemented_at": datetime.utcnow().isoformat()
            }).eq("id", str(recommendation_id)).execute()

        return {
            "status": "success",
            "message": "Feedback recorded successfully",
            "feedback_id": result.data[0]["id"] if result.data else None
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error submitting feedback: {str(e)}")


@router.get("/{recommendation_id}/impact", response_model=RecommendationImpact)
async def get_impact_tracking(
    recommendation_id: UUID,
    rec_service: RecommendationService = Depends(get_recommendation_service)
):
    """
    Track implementation impact of a recommendation

    Returns metrics showing the impact after implementing a recommendation.
    """
    try:
        result = rec_service.supabase.table("recommendation_impacts").select("*").eq(
            "recommendation_id", str(recommendation_id)
        ).order("measurement_date", desc=True).limit(1).execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="No impact data found for this recommendation")

        return RecommendationImpact(**result.data[0])

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching impact data: {str(e)}")
