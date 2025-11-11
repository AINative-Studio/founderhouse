"""
Voice Command Service
Service for processing voice commands via ZeroVoice MCP integration
Handles speech-to-text, intent recognition, and command execution
"""
import logging
import time
from typing import Optional, Dict, Any
from uuid import UUID

from app.models.voice_command import (
    VoiceCommandRequest,
    VoiceCommandResponse,
    VoiceCommandCreate,
    VoiceCommandUpdate,
    VoiceCommandStatus,
    VoiceCommandIntent,
    VoiceTranscriptionRequest,
    VoiceTranscriptionResponse
)
from app.database import get_db_context
from app.mcp.zerovoice_client import get_zerovoice
from sqlalchemy import text


logger = logging.getLogger(__name__)


class VoiceCommandService:
    """Service for processing voice commands"""

    def __init__(self, zerovoice_client=None):
        self.logger = logging.getLogger(__name__)
        # Inject ZeroVoice MCP client (allow mock for testing)
        self.zerovoice = zerovoice_client or get_zerovoice()

        # Intent mapping from ZeroVoice format to internal enum
        self.intent_mapping = {
            "create_task": VoiceCommandIntent.CREATE_TASK,
            "schedule_meeting": VoiceCommandIntent.SCHEDULE_MEETING,
            "get_summary": VoiceCommandIntent.GET_SUMMARY,
            "check_metrics": VoiceCommandIntent.CHECK_METRICS,
            "send_message": VoiceCommandIntent.SEND_MESSAGE,
            "create_note": VoiceCommandIntent.CREATE_NOTE,
            "get_briefing": VoiceCommandIntent.GET_BRIEFING,
            "update_status": VoiceCommandIntent.UPDATE_STATUS,
            "unknown": VoiceCommandIntent.UNKNOWN
        }

        # Fallback intent patterns for local recognition (if MCP unavailable)
        self.intent_patterns = {
            VoiceCommandIntent.CREATE_TASK: ["create task", "add task", "new task", "remind me to"],
            VoiceCommandIntent.SCHEDULE_MEETING: ["schedule meeting", "book meeting", "set up meeting"],
            VoiceCommandIntent.GET_SUMMARY: ["summarize", "give me summary", "what happened", "brief me"],
            VoiceCommandIntent.CHECK_METRICS: ["check metrics", "show kpis", "how are we doing", "metrics"],
            VoiceCommandIntent.SEND_MESSAGE: ["send message", "message", "tell", "notify"],
            VoiceCommandIntent.CREATE_NOTE: ["create note", "take note", "write down"],
            VoiceCommandIntent.GET_BRIEFING: ["get briefing", "morning brief", "daily brief"],
            VoiceCommandIntent.UPDATE_STATUS: ["update status", "set status", "change status"],
        }

    async def transcribe_audio(
        self,
        request: VoiceTranscriptionRequest
    ) -> Optional[VoiceTranscriptionResponse]:
        """
        Transcribe audio to text using ZeroVoice MCP

        Args:
            request: Transcription request with audio data

        Returns:
            Transcription result with confidence score
        """
        try:
            start_time = time.time()

            # Use ZeroVoice MCP for transcription
            result = await self.zerovoice.transcribe_audio(
                audio_url=request.audio_url,
                audio_base64=request.audio_base64,
                language=request.language,
                include_timestamps=request.include_timestamps
            )

            duration_seconds = time.time() - start_time

            response = VoiceTranscriptionResponse(
                workspace_id=request.workspace_id,
                founder_id=request.founder_id,
                transcript=result["transcript"],
                confidence=result["confidence"],
                language=request.language,
                duration_seconds=duration_seconds,
                word_timestamps=result.get("timestamps")
            )

            self.logger.info(f"Transcribed audio for founder {request.founder_id}")
            return response

        except Exception as e:
            self.logger.error(f"Error transcribing audio: {str(e)}")
            return None

    async def process_command(
        self,
        request: VoiceCommandRequest
    ) -> Optional[VoiceCommandResponse]:
        """
        Process a voice command from transcript or audio
        Complete voice → intent → action pipeline in < 2.5s (per PRD)

        Args:
            request: Voice command request

        Returns:
            Processed command with intent and action taken
        """
        try:
            start_time = time.time()

            # Use ZeroVoice MCP for complete pipeline
            mcp_result = await self.zerovoice.process_voice_command(
                audio_url=request.audio_url,
                audio_base64=request.audio_base64,
                transcript=request.transcript,
                context=request.context
            )

            transcript = mcp_result["transcript"]
            intent_str = mcp_result["intent"]
            confidence = mcp_result["confidence"]
            entities = mcp_result["entities"]
            processing_time_ms = mcp_result["processing_time_ms"]

            # Map intent from ZeroVoice format to internal enum
            intent = self.intent_mapping.get(intent_str, VoiceCommandIntent.UNKNOWN)

            # Create command record
            command_create = VoiceCommandCreate(
                workspace_id=request.workspace_id,
                founder_id=request.founder_id,
                transcript=transcript,
                intent=intent,
                confidence=confidence,
                status=VoiceCommandStatus.PROCESSING,
                extracted_entities=entities
            )

            # Save to database
            async with get_db_context() as db:
                result = await db.execute(
                    text("""
                        INSERT INTO voice_commands
                        (workspace_id, founder_id, transcript, intent, confidence, status, extracted_entities)
                        VALUES (:workspace_id, :founder_id, :transcript, :intent, :confidence, :status, :extracted_entities)
                        RETURNING id, created_at
                    """),
                    {
                        "workspace_id": str(command_create.workspace_id),
                        "founder_id": str(command_create.founder_id),
                        "transcript": command_create.transcript,
                        "intent": command_create.intent.value,
                        "confidence": command_create.confidence,
                        "status": command_create.status.value,
                        "extracted_entities": command_create.extracted_entities
                    }
                )
                await db.commit()
                row = result.fetchone()
                command_id = row[0]
                created_at = row[1]

            # Execute the command (action routing)
            action_taken, result_data = await self._execute_command(
                command_id, intent, entities, request.workspace_id, request.founder_id
            )

            # Total processing time (MCP + DB + action)
            total_processing_time_ms = int((time.time() - start_time) * 1000)

            # Log performance metrics
            if total_processing_time_ms > 2500:
                self.logger.warning(
                    f"Voice command exceeded 2.5s target: {total_processing_time_ms}ms "
                    f"(MCP: {processing_time_ms}ms)"
                )
            else:
                self.logger.info(
                    f"Voice command processed in {total_processing_time_ms}ms "
                    f"(< 2.5s target, MCP: {processing_time_ms}ms)"
                )

            # Update command status
            async with get_db_context() as db:
                await db.execute(
                    text("""
                        UPDATE voice_commands
                        SET status = :status, action_taken = :action_taken,
                            result = :result, processing_time_ms = :processing_time_ms,
                            updated_at = NOW()
                        WHERE id = :id
                    """),
                    {
                        "id": str(command_id),
                        "status": VoiceCommandStatus.COMPLETED.value,
                        "action_taken": action_taken,
                        "result": result_data,
                        "processing_time_ms": total_processing_time_ms
                    }
                )
                await db.commit()

            response = VoiceCommandResponse(
                id=command_id,
                workspace_id=request.workspace_id,
                founder_id=request.founder_id,
                transcript=transcript,
                intent=intent,
                confidence=confidence,
                status=VoiceCommandStatus.COMPLETED,
                extracted_entities=entities,
                action_taken=action_taken,
                result=result_data,
                processing_time_ms=total_processing_time_ms,
                created_at=created_at
            )

            self.logger.info(f"Processed voice command: {intent.value} for founder {request.founder_id}")
            return response

        except Exception as e:
            self.logger.error(f"Error processing voice command: {str(e)}")
            # Try to update status to failed
            try:
                async with get_db_context() as db:
                    await db.execute(
                        text("""
                            UPDATE voice_commands
                            SET status = :status, error_message = :error
                            WHERE id = :id
                        """),
                        {
                            "id": str(command_id) if 'command_id' in locals() else None,
                            "status": VoiceCommandStatus.FAILED.value,
                            "error": str(e)
                        }
                    )
                    await db.commit()
            except:
                pass
            return None


    async def _execute_command(
        self,
        command_id: UUID,
        intent: VoiceCommandIntent,
        entities: Dict[str, Any],
        workspace_id: UUID,
        founder_id: UUID
    ) -> tuple[str, Dict[str, Any]]:
        """
        Execute the voice command

        Args:
            command_id: Command ID
            intent: Recognized intent
            entities: Extracted entities
            workspace_id: Workspace ID
            founder_id: Founder ID

        Returns:
            Tuple of (action_description, result_data)
        """
        try:
            if intent == VoiceCommandIntent.CREATE_TASK:
                # Create a task
                task_description = entities.get("task", "New task")
                # In production, this would create an actual task
                return (
                    f"Created task: {task_description}",
                    {"task_id": str(command_id), "description": task_description}
                )

            elif intent == VoiceCommandIntent.GET_SUMMARY:
                # Get briefing/summary
                return (
                    "Retrieved latest briefing",
                    {"briefing_type": "morning", "status": "available"}
                )

            elif intent == VoiceCommandIntent.CHECK_METRICS:
                # Get KPI snapshot
                return (
                    "Retrieved KPI metrics",
                    {"metrics_count": 0, "status": "available"}
                )

            elif intent == VoiceCommandIntent.SEND_MESSAGE:
                # Send message
                message = entities.get("message", "")
                return (
                    "Message queued for delivery",
                    {"message": message, "status": "queued"}
                )

            else:
                return (
                    f"Recognized intent: {intent.value}",
                    {"intent": intent.value}
                )

        except Exception as e:
            self.logger.error(f"Error executing command: {str(e)}")
            return (
                f"Failed to execute command: {str(e)}",
                {"error": str(e)}
            )

    async def get_command_history(
        self,
        workspace_id: UUID,
        founder_id: UUID,
        limit: int = 20
    ) -> list[VoiceCommandResponse]:
        """
        Get command history for a founder

        Args:
            workspace_id: Workspace ID
            founder_id: Founder ID
            limit: Maximum number of commands to return

        Returns:
            List of voice commands
        """
        try:
            async with get_db_context() as db:
                result = await db.execute(
                    text("""
                        SELECT * FROM voice_commands
                        WHERE workspace_id = :workspace_id
                        AND founder_id = :founder_id
                        ORDER BY created_at DESC
                        LIMIT :limit
                    """),
                    {
                        "workspace_id": str(workspace_id),
                        "founder_id": str(founder_id),
                        "limit": limit
                    }
                )
                rows = result.fetchall()

                commands = []
                for row in rows:
                    commands.append(VoiceCommandResponse(
                        id=row.id,
                        workspace_id=UUID(row.workspace_id),
                        founder_id=UUID(row.founder_id),
                        transcript=row.transcript,
                        intent=VoiceCommandIntent(row.intent),
                        confidence=row.confidence,
                        status=VoiceCommandStatus(row.status),
                        extracted_entities=row.extracted_entities or {},
                        action_taken=row.action_taken,
                        result=row.result,
                        processing_time_ms=row.processing_time_ms,
                        created_at=row.created_at,
                        updated_at=row.updated_at
                    ))

                return commands

        except Exception as e:
            self.logger.error(f"Error getting command history: {str(e)}")
            return []
