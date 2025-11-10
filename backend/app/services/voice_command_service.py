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
from sqlalchemy import text


logger = logging.getLogger(__name__)


class VoiceCommandService:
    """Service for processing voice commands"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        # Intent patterns for command recognition
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

            # In production, this would integrate with ZeroVoice MCP
            # For now, simulate transcription
            # TODO: Integrate with actual ZeroVoice MCP connector

            transcript = self._mock_transcription(request)
            duration_seconds = time.time() - start_time

            response = VoiceTranscriptionResponse(
                workspace_id=request.workspace_id,
                founder_id=request.founder_id,
                transcript=transcript,
                confidence=0.95,
                language=request.language,
                duration_seconds=duration_seconds
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

        Args:
            request: Voice command request

        Returns:
            Processed command with intent and action taken
        """
        try:
            start_time = time.time()

            # Get or create transcript
            if request.transcript:
                transcript = request.transcript
            else:
                # Transcribe audio first
                transcription_req = VoiceTranscriptionRequest(
                    workspace_id=request.workspace_id,
                    founder_id=request.founder_id,
                    audio_url=request.audio_url,
                    audio_base64=request.audio_base64
                )
                transcription = await self.transcribe_audio(transcription_req)
                if not transcription:
                    raise ValueError("Failed to transcribe audio")
                transcript = transcription.transcript

            # Recognize intent
            intent, confidence = self._recognize_intent(transcript)

            # Extract entities
            entities = self._extract_entities(transcript, intent)

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

            # Execute the command
            action_taken, result_data = await self._execute_command(
                command_id, intent, entities, request.workspace_id, request.founder_id
            )

            processing_time_ms = int((time.time() - start_time) * 1000)

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
                        "processing_time_ms": processing_time_ms
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
                processing_time_ms=processing_time_ms,
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

    def _mock_transcription(self, request: VoiceTranscriptionRequest) -> str:
        """Mock transcription for testing"""
        # In production, this would call ZeroVoice MCP
        return "Create a task to follow up with investors by Friday"

    def _recognize_intent(self, transcript: str) -> tuple[VoiceCommandIntent, float]:
        """
        Recognize intent from transcript

        Args:
            transcript: Voice command transcript

        Returns:
            Tuple of (intent, confidence_score)
        """
        transcript_lower = transcript.lower()

        best_intent = VoiceCommandIntent.UNKNOWN
        best_score = 0.0

        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if pattern in transcript_lower:
                    # Simple scoring based on pattern match
                    score = len(pattern) / len(transcript_lower)
                    if score > best_score:
                        best_score = score
                        best_intent = intent

        # If we found a match, set confidence based on score
        confidence = min(0.95, 0.7 + best_score)

        if best_intent == VoiceCommandIntent.UNKNOWN:
            confidence = 0.3

        return best_intent, confidence

    def _extract_entities(self, transcript: str, intent: VoiceCommandIntent) -> Dict[str, Any]:
        """
        Extract entities from transcript based on intent

        Args:
            transcript: Voice command transcript
            intent: Recognized intent

        Returns:
            Dictionary of extracted entities
        """
        entities = {}

        # Simple entity extraction
        # In production, this would use NLP/NER models

        if intent == VoiceCommandIntent.CREATE_TASK:
            # Extract task description
            for prefix in ["create task", "add task", "new task", "remind me to"]:
                if prefix in transcript.lower():
                    entities["task"] = transcript.lower().split(prefix)[-1].strip()
                    break

        elif intent == VoiceCommandIntent.SCHEDULE_MEETING:
            # Extract meeting details
            entities["meeting_subject"] = "Meeting"  # Simplified

        elif intent == VoiceCommandIntent.SEND_MESSAGE:
            # Extract message content
            for prefix in ["send message", "message", "tell"]:
                if prefix in transcript.lower():
                    entities["message"] = transcript.lower().split(prefix)[-1].strip()
                    break

        return entities

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
