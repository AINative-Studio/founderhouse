"""
Briefings API Endpoints
Endpoints for generating and managing daily briefings
"""
from typing import List, Optional
from uuid import UUID
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Depends, Query, Body

from app.services.briefing_service import BriefingService
from app.models.briefing import (
    BriefingResponse,
    BriefingListResponse,
    BriefingGenerateRequest,
    BriefingType,
    BriefingStatus,
    BriefingSchedule,
    BriefingScheduleResponse,
    DeliveryChannel
)


router = APIRouter(prefix="/briefings", tags=["Briefings"])


def get_briefing_service() -> BriefingService:
    """Dependency for briefing service"""
    return BriefingService()


@router.get("/{founder_id}", response_model=BriefingResponse)
async def get_latest_briefing(
    founder_id: UUID,
    workspace_id: UUID = Query(..., description="Workspace ID"),
    briefing_type: Optional[BriefingType] = Query(None, description="Filter by briefing type"),
    briefing_service: BriefingService = Depends(get_briefing_service)
):
    """
    Get latest briefing for a founder

    Returns the most recent briefing of the specified type.
    """
    try:
        query = briefing_service.supabase.table("briefings").select("*").eq(
            "workspace_id", str(workspace_id)
        ).eq("founder_id", str(founder_id))

        if briefing_type:
            query = query.eq("briefing_type", briefing_type.value)

        result = query.order("created_at", desc=True).limit(1).execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="No briefing found")

        return BriefingResponse(**result.data[0])

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching briefing: {str(e)}")


@router.post("/generate", response_model=BriefingResponse)
async def generate_briefing(
    request: BriefingGenerateRequest = Body(...),
    briefing_service: BriefingService = Depends(get_briefing_service)
):
    """
    Generate a new briefing

    Creates a briefing of the specified type with optional customization.
    """
    try:
        briefing = await briefing_service.generate_briefing(
            workspace_id=request.workspace_id,
            founder_id=request.founder_id,
            briefing_type=request.briefing_type,
            start_date=request.start_date,
            end_date=request.end_date
        )

        if not briefing:
            raise HTTPException(status_code=500, detail="Failed to generate briefing")

        return briefing

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating briefing: {str(e)}")


@router.get("/morning", response_model=BriefingResponse)
async def get_morning_brief(
    workspace_id: UUID = Query(...),
    founder_id: UUID = Query(...),
    date: Optional[datetime] = Query(None, description="Specific date (defaults to today)"),
    briefing_service: BriefingService = Depends(get_briefing_service)
):
    """
    Get or generate morning brief

    Returns today's morning brief, generating it if it doesn't exist.
    """
    try:
        if not date:
            date = datetime.utcnow()

        # Try to find existing briefing
        start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = date.replace(hour=23, minute=59, second=59, microsecond=999999)

        result = briefing_service.supabase.table("briefings").select("*").eq(
            "workspace_id", str(workspace_id)
        ).eq("founder_id", str(founder_id)).eq(
            "briefing_type", BriefingType.MORNING.value
        ).gte("created_at", start_of_day.isoformat()).lte(
            "created_at", end_of_day.isoformat()
        ).execute()

        if result.data:
            return BriefingResponse(**result.data[0])

        # Generate new briefing
        briefing = await briefing_service.generate_briefing(
            workspace_id=workspace_id,
            founder_id=founder_id,
            briefing_type=BriefingType.MORNING
        )

        if not briefing:
            raise HTTPException(status_code=500, detail="Failed to generate morning brief")

        return briefing

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting morning brief: {str(e)}")


@router.get("/evening", response_model=BriefingResponse)
async def get_evening_wrap(
    workspace_id: UUID = Query(...),
    founder_id: UUID = Query(...),
    date: Optional[datetime] = Query(None),
    briefing_service: BriefingService = Depends(get_briefing_service)
):
    """
    Get or generate evening wrap

    Returns today's evening wrap, generating it if it doesn't exist.
    """
    try:
        if not date:
            date = datetime.utcnow()

        start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = date.replace(hour=23, minute=59, second=59, microsecond=999999)

        result = briefing_service.supabase.table("briefings").select("*").eq(
            "workspace_id", str(workspace_id)
        ).eq("founder_id", str(founder_id)).eq(
            "briefing_type", BriefingType.EVENING.value
        ).gte("created_at", start_of_day.isoformat()).lte(
            "created_at", end_of_day.isoformat()
        ).execute()

        if result.data:
            return BriefingResponse(**result.data[0])

        briefing = await briefing_service.generate_briefing(
            workspace_id=workspace_id,
            founder_id=founder_id,
            briefing_type=BriefingType.EVENING
        )

        if not briefing:
            raise HTTPException(status_code=500, detail="Failed to generate evening wrap")

        return briefing

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting evening wrap: {str(e)}")


@router.get("/investor-weekly", response_model=BriefingResponse)
async def get_investor_summary(
    workspace_id: UUID = Query(...),
    founder_id: UUID = Query(...),
    week_start: Optional[datetime] = Query(None, description="Start of week"),
    briefing_service: BriefingService = Depends(get_briefing_service)
):
    """
    Get or generate weekly investor summary

    Returns the investor update for the specified week.
    """
    try:
        if not week_start:
            # Default to current week (Monday)
            today = datetime.utcnow()
            week_start = today - timedelta(days=today.weekday())

        week_end = week_start + timedelta(days=6)

        result = briefing_service.supabase.table("briefings").select("*").eq(
            "workspace_id", str(workspace_id)
        ).eq("founder_id", str(founder_id)).eq(
            "briefing_type", BriefingType.INVESTOR.value
        ).gte("start_date", week_start.isoformat()).lte(
            "end_date", week_end.isoformat()
        ).execute()

        if result.data:
            return BriefingResponse(**result.data[0])

        briefing = await briefing_service.generate_briefing(
            workspace_id=workspace_id,
            founder_id=founder_id,
            briefing_type=BriefingType.INVESTOR,
            start_date=week_start,
            end_date=week_end
        )

        if not briefing:
            raise HTTPException(status_code=500, detail="Failed to generate investor summary")

        return briefing

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting investor summary: {str(e)}")


@router.post("/schedule", response_model=BriefingScheduleResponse)
async def schedule_briefing(
    schedule: BriefingSchedule = Body(...),
    briefing_service: BriefingService = Depends(get_briefing_service)
):
    """
    Schedule automated briefing delivery

    Configures when and how briefings should be generated and delivered.
    """
    try:
        result = briefing_service.supabase.table("briefing_schedules").upsert(
            schedule.model_dump(mode="json")
        ).execute()

        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to create schedule")

        return BriefingScheduleResponse(**result.data[0])

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error scheduling briefing: {str(e)}")


@router.get("/list", response_model=BriefingListResponse)
async def list_briefings(
    workspace_id: UUID = Query(...),
    founder_id: Optional[UUID] = Query(None),
    briefing_type: Optional[List[BriefingType]] = Query(None),
    status: Optional[List[BriefingStatus]] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    briefing_service: BriefingService = Depends(get_briefing_service)
):
    """
    List briefings with optional filtering

    Returns paginated list of briefings.
    """
    try:
        query = briefing_service.supabase.table("briefings").select("*").eq(
            "workspace_id", str(workspace_id)
        )

        if founder_id:
            query = query.eq("founder_id", str(founder_id))

        if briefing_type:
            query = query.in_("briefing_type", [bt.value for bt in briefing_type])

        if status:
            query = query.in_("status", [s.value for s in status])

        if start_date:
            query = query.gte("created_at", start_date.isoformat())

        if end_date:
            query = query.lte("created_at", end_date.isoformat())

        count_result = query.execute()
        total_count = len(count_result.data)

        result = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()

        briefings = [BriefingResponse(**b) for b in result.data]

        return BriefingListResponse(
            briefings=briefings,
            total_count=total_count,
            has_more=total_count > (offset + limit),
            filters_applied={
                "workspace_id": str(workspace_id)
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing briefings: {str(e)}")
