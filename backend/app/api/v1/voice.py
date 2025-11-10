"""
Voice Commands API Endpoints
Endpoints for processing voice commands and transcriptions
"""
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends, Query, Body

from app.services.voice_command_service import VoiceCommandService
from app.models.voice_command import (
    VoiceCommandRequest,
    VoiceCommandResponse,
    VoiceTranscriptionRequest,
    VoiceTranscriptionResponse,
    VoiceCommandListResponse,
    VoiceCommandStatus,
    VoiceCommandIntent
)


router = APIRouter(prefix="/voice", tags=["Voice Commands"])


def get_voice_service() -> VoiceCommandService:
    """Dependency for voice command service"""
    return VoiceCommandService()


@router.post("/command", response_model=VoiceCommandResponse)
async def process_voice_command(
    request: VoiceCommandRequest = Body(...),
    service: VoiceCommandService = Depends(get_voice_service)
):
    """
    Process a voice command

    Accepts either audio (URL or base64) or pre-transcribed text.
    Recognizes intent, extracts entities, and executes the command.
    """
    try:
        result = await service.process_command(request)

        if not result:
            raise HTTPException(status_code=500, detail="Failed to process voice command")

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing command: {str(e)}")


@router.post("/transcribe", response_model=VoiceTranscriptionResponse)
async def transcribe_audio(
    request: VoiceTranscriptionRequest = Body(...),
    service: VoiceCommandService = Depends(get_voice_service)
):
    """
    Transcribe audio to text

    Accepts audio URL or base64-encoded audio data.
    Returns transcript with confidence score.
    """
    try:
        result = await service.transcribe_audio(request)

        if not result:
            raise HTTPException(status_code=500, detail="Failed to transcribe audio")

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error transcribing audio: {str(e)}")


@router.get("/commands/{founder_id}", response_model=VoiceCommandListResponse)
async def get_command_history(
    founder_id: UUID,
    workspace_id: UUID = Query(..., description="Workspace ID"),
    status: Optional[VoiceCommandStatus] = Query(None, description="Filter by status"),
    intent: Optional[VoiceCommandIntent] = Query(None, description="Filter by intent"),
    limit: int = Query(20, le=100, description="Max number of commands to return"),
    service: VoiceCommandService = Depends(get_voice_service)
):
    """
    Get voice command history for a founder

    Returns paginated list of voice commands with filters.
    """
    try:
        commands = await service.get_command_history(
            workspace_id=workspace_id,
            founder_id=founder_id,
            limit=limit
        )

        # Apply filters
        if status:
            commands = [c for c in commands if c.status == status]

        if intent:
            commands = [c for c in commands if c.intent == intent]

        return VoiceCommandListResponse(
            commands=commands,
            total_count=len(commands),
            has_more=len(commands) >= limit,
            filters_applied={
                "workspace_id": str(workspace_id),
                "founder_id": str(founder_id),
                "status": status.value if status else None,
                "intent": intent.value if intent else None
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching command history: {str(e)}")


@router.get("/commands/{command_id}/detail", response_model=VoiceCommandResponse)
async def get_command_detail(
    command_id: UUID,
    workspace_id: UUID = Query(..., description="Workspace ID"),
    service: VoiceCommandService = Depends(get_voice_service)
):
    """
    Get detailed information about a specific voice command

    Returns full command details including transcript, intent, entities, and result.
    """
    try:
        # For now, return from history
        commands = await service.get_command_history(
            workspace_id=workspace_id,
            founder_id=UUID("00000000-0000-0000-0000-000000000000"),  # Will need to improve this
            limit=100
        )

        command = next((c for c in commands if c.id == command_id), None)

        if not command:
            raise HTTPException(status_code=404, detail="Command not found")

        return command

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching command: {str(e)}")
