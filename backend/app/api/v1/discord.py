"""
Discord Integration API Endpoints
Endpoints for posting updates and briefings to Discord
"""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends, Body

from app.services.discord_service import DiscordService
from app.models.discord_message import (
    DiscordStatusUpdateRequest,
    DiscordBriefingRequest,
    DiscordMessageResponse
)


router = APIRouter(prefix="/discord", tags=["Discord"])


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
