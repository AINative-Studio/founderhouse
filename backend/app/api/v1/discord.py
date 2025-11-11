"""
Discord Integration API Endpoints
Endpoints for posting updates and briefings to Discord
Includes schedule management for automated daily briefings
"""
from typing import Optional, List
from uuid import UUID
from datetime import time

from fastapi import APIRouter, HTTPException, Depends, Body
from pydantic import BaseModel, Field

from app.services.discord_service import DiscordService
from app.models.discord_message import (
    DiscordStatusUpdateRequest,
    DiscordBriefingRequest,
    DiscordMessageResponse
)
from app.models.briefing import BriefingType
from app.database import get_db
from sqlalchemy.orm import Session
from sqlalchemy import text


router = APIRouter(prefix="/discord", tags=["Discord"])


class BriefingScheduleCreate(BaseModel):
    """Create briefing schedule request"""
    workspace_id: UUID
    founder_id: UUID
    briefing_type: BriefingType = Field(default=BriefingType.MORNING)
    discord_channel: str = Field(default="daily-briefings")
    timezone: str = Field(default="UTC", description="IANA timezone (e.g., America/Los_Angeles)")
    delivery_hour: int = Field(default=8, ge=0, le=23, description="Hour to deliver (0-23)")
    mention_team: bool = Field(default=False)
    is_active: bool = Field(default=True)


class BriefingScheduleResponse(BaseModel):
    """Briefing schedule response"""
    id: UUID
    workspace_id: UUID
    founder_id: UUID
    briefing_type: str
    discord_channel: str
    timezone: str
    delivery_hour: int
    mention_team: bool
    is_active: bool


def get_discord_service() -> DiscordService:
    """Dependency for Discord service"""
    return DiscordService()


@router.post("/status", response_model=DiscordMessageResponse)
async def post_status_update(
    request: DiscordStatusUpdateRequest = Body(...),
    service: DiscordService = Depends(get_discord_service)
):
    """
    Post a status update to Discord

    Sends a message to the specified Discord channel with optional rich embed and mentions.
    Can be used for announcements, notifications, or general updates.
    """
    try:
        result = await service.post_status_update(request)

        if not result:
            raise HTTPException(status_code=500, detail="Failed to post status update")

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error posting status update: {str(e)}")


@router.post("/briefing", response_model=DiscordMessageResponse)
async def send_briefing(
    request: DiscordBriefingRequest = Body(...),
    service: DiscordService = Depends(get_discord_service)
):
    """
    Send a daily briefing to Discord

    Posts a formatted briefing to Discord with key highlights, metrics, and action items.
    If no briefing_id is provided, generates and sends the latest morning briefing.
    """
    try:
        result = await service.send_briefing(request)

        if not result:
            raise HTTPException(status_code=500, detail="Failed to send briefing")

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error sending briefing: {str(e)}")


@router.get("/message/{message_id}", response_model=DiscordMessageResponse)
async def get_message(
    message_id: UUID,
    service: DiscordService = Depends(get_discord_service)
):
    """
    Get Discord message details by ID

    Returns information about a previously sent Discord message including delivery status.
    """
    try:
        message = await service.get_message(message_id)

        if not message:
            raise HTTPException(status_code=404, detail="Message not found")

        return message

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching message: {str(e)}")


@router.post("/briefing/schedule", response_model=BriefingScheduleResponse)
async def create_briefing_schedule(
    schedule: BriefingScheduleCreate = Body(...),
    db: Session = Depends(get_db)
):
    """
    Create a new Discord briefing schedule

    Configures automated daily briefings to be sent to Discord at a specific time
    in the workspace's local timezone.

    - **timezone**: IANA timezone identifier (e.g., "America/Los_Angeles", "Europe/London")
    - **delivery_hour**: Hour in 24-hour format (0-23) in the specified timezone
    - **briefing_type**: Type of briefing (morning, evening, investor)
    """
    try:
        # Validate timezone
        try:
            from zoneinfo import ZoneInfo
            ZoneInfo(schedule.timezone)
        except Exception:
            raise HTTPException(status_code=400, detail=f"Invalid timezone: {schedule.timezone}")

        # Create schedule in database
        result = db.execute(
            text("""
                INSERT INTO briefing_schedules
                (workspace_id, founder_id, briefing_type, discord_channel, timezone,
                 delivery_hour, mention_team, is_active, delivery_channels)
                VALUES (:workspace_id, :founder_id, :briefing_type, :discord_channel,
                        :timezone, :delivery_hour, :mention_team, :is_active, ARRAY['discord'])
                RETURNING id, workspace_id, founder_id, briefing_type, discord_channel,
                          timezone, delivery_hour, mention_team, is_active
            """),
            {
                "workspace_id": str(schedule.workspace_id),
                "founder_id": str(schedule.founder_id),
                "briefing_type": schedule.briefing_type.value,
                "discord_channel": schedule.discord_channel,
                "timezone": schedule.timezone,
                "delivery_hour": schedule.delivery_hour,
                "mention_team": schedule.mention_team,
                "is_active": schedule.is_active
            }
        )
        db.commit()

        row = result.fetchone()
        if not row:
            raise HTTPException(status_code=500, detail="Failed to create schedule")

        return BriefingScheduleResponse(
            id=row[0],
            workspace_id=UUID(row[1]),
            founder_id=UUID(row[2]),
            briefing_type=row[3],
            discord_channel=row[4],
            timezone=row[5],
            delivery_hour=row[6],
            mention_team=row[7],
            is_active=row[8]
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating schedule: {str(e)}")


@router.get("/briefing/schedule/{workspace_id}", response_model=List[BriefingScheduleResponse])
async def get_briefing_schedules(
    workspace_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get all briefing schedules for a workspace

    Returns all configured Discord briefing schedules for the specified workspace.
    """
    try:
        result = db.execute(
            text("""
                SELECT id, workspace_id, founder_id, briefing_type, discord_channel,
                       timezone, delivery_hour, mention_team, is_active
                FROM briefing_schedules
                WHERE workspace_id = :workspace_id
                AND delivery_channels @> ARRAY['discord']
                ORDER BY delivery_hour
            """),
            {"workspace_id": str(workspace_id)}
        )

        schedules = []
        for row in result.fetchall():
            schedules.append(BriefingScheduleResponse(
                id=row[0],
                workspace_id=UUID(row[1]),
                founder_id=UUID(row[2]),
                briefing_type=row[3],
                discord_channel=row[4],
                timezone=row[5],
                delivery_hour=row[6],
                mention_team=row[7],
                is_active=row[8]
            ))

        return schedules

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching schedules: {str(e)}")


@router.patch("/briefing/schedule/{schedule_id}")
async def update_briefing_schedule(
    schedule_id: UUID,
    is_active: bool = Body(...),
    db: Session = Depends(get_db)
):
    """
    Update briefing schedule status

    Enable or disable a Discord briefing schedule.
    """
    try:
        result = db.execute(
            text("""
                UPDATE briefing_schedules
                SET is_active = :is_active
                WHERE id = :schedule_id
                RETURNING id
            """),
            {"schedule_id": str(schedule_id), "is_active": is_active}
        )
        db.commit()

        if not result.fetchone():
            raise HTTPException(status_code=404, detail="Schedule not found")

        return {"status": "success", "schedule_id": str(schedule_id), "is_active": is_active}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating schedule: {str(e)}")


@router.delete("/briefing/schedule/{schedule_id}")
async def delete_briefing_schedule(
    schedule_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Delete a briefing schedule

    Permanently removes a Discord briefing schedule.
    """
    try:
        result = db.execute(
            text("DELETE FROM briefing_schedules WHERE id = :schedule_id RETURNING id"),
            {"schedule_id": str(schedule_id)}
        )
        db.commit()

        if not result.fetchone():
            raise HTTPException(status_code=404, detail="Schedule not found")

        return {"status": "success", "message": "Schedule deleted"}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting schedule: {str(e)}")
