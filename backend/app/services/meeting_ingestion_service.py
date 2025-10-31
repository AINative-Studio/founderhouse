"""
Meeting Ingestion Service
Handles ingestion from Zoom, Fireflies, and Otter with deduplication
"""
import logging
import hashlib
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from uuid import UUID

from app.connectors.zoom_connector import ZoomConnector
from app.connectors.fireflies_connector import FirefliesConnector
from app.connectors.otter_connector import OtterConnector
from app.models.meeting import (
    Meeting, MeetingCreate, MeetingSource, MeetingStatus,
    TranscriptChunk, MeetingParticipant, MeetingMetadata
)

logger = logging.getLogger(__name__)


class MeetingIngestionService:
    """
    Service for ingesting meetings from multiple platforms

    Features:
    - Multi-platform ingestion (Zoom, Fireflies, Otter)
    - Deduplication across sources
    - Participant extraction and matching
    - Transcript chunking for vector storage
    """

    def __init__(self, supabase_client=None):
        """
        Initialize ingestion service

        Args:
            supabase_client: Supabase client for database operations
        """
        self.supabase = supabase_client
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    async def ingest_from_zoom(
        self,
        workspace_id: UUID,
        founder_id: UUID,
        meeting_id: str,
        credentials: Dict[str, Any]
    ) -> Tuple[Meeting, bool]:
        """
        Ingest meeting from Zoom

        Args:
            workspace_id: Workspace UUID
            founder_id: Founder UUID
            meeting_id: Zoom meeting ID
            credentials: Zoom API credentials

        Returns:
            Tuple of (Meeting object, is_duplicate flag)
        """
        try:
            # Check for duplicate
            duplicate_hash = self._generate_meeting_hash(MeetingSource.ZOOM, meeting_id)
            existing = await self._find_by_hash(workspace_id, duplicate_hash)
            if existing:
                self.logger.info(f"Meeting already ingested: {meeting_id}")
                return existing, True

            # Connect to Zoom
            async with ZoomConnector(credentials) as zoom:
                # Get meeting details
                meeting_response = await zoom.get_meeting(meeting_id)
                meeting_data = meeting_response.data

                # Get recording if available
                recording_response = await zoom.get_recording(meeting_id)
                recording_data = recording_response.data if recording_response.status.value == "success" else {}

                # Get participants
                participants_response = await zoom.get_meeting_participants(meeting_id)
                participants_data = participants_response.data if participants_response.status.value == "success" else {}

                # Extract transcript from recording
                transcript = self._extract_zoom_transcript(recording_data)
                transcript_chunks = self._chunk_transcript(transcript) if transcript else []

                # Build meeting object
                meeting = Meeting(
                    workspace_id=workspace_id,
                    founder_id=founder_id,
                    title=meeting_data.get("topic", "Untitled Meeting"),
                    source=MeetingSource.ZOOM,
                    status=MeetingStatus.INGESTING,
                    scheduled_at=self._parse_datetime(meeting_data.get("start_time")),
                    host_name=meeting_data.get("host_email", "").split("@")[0],
                    host_email=meeting_data.get("host_email"),
                    participants=self._extract_zoom_participants(participants_data),
                    participant_count=len(participants_data.get("participants", [])),
                    transcript=transcript,
                    transcript_chunks=transcript_chunks,
                    metadata=MeetingMetadata(
                        duration=meeting_data.get("duration"),
                        platform_id=meeting_id,
                        recording_url=recording_data.get("recording_files", [{}])[0].get("download_url") if recording_data else None,
                        platform_data={
                            "meeting_uuid": meeting_data.get("uuid"),
                            "meeting_number": meeting_data.get("id"),
                            "duplicate_hash": duplicate_hash
                        }
                    ),
                    ingestion_started_at=datetime.utcnow()
                )

                # Save to database
                meeting = await self._save_meeting(meeting)

                self.logger.info(f"Successfully ingested Zoom meeting: {meeting_id}")
                return meeting, False

        except Exception as e:
            self.logger.error(f"Failed to ingest Zoom meeting {meeting_id}: {str(e)}")
            raise

    async def ingest_from_fireflies(
        self,
        workspace_id: UUID,
        founder_id: UUID,
        transcript_id: str,
        credentials: Dict[str, Any]
    ) -> Tuple[Meeting, bool]:
        """
        Ingest meeting from Fireflies

        Args:
            workspace_id: Workspace UUID
            founder_id: Founder UUID
            transcript_id: Fireflies transcript ID
            credentials: Fireflies API credentials

        Returns:
            Tuple of (Meeting object, is_duplicate flag)
        """
        try:
            # Check for duplicate
            duplicate_hash = self._generate_meeting_hash(MeetingSource.FIREFLIES, transcript_id)
            existing = await self._find_by_hash(workspace_id, duplicate_hash)
            if existing:
                self.logger.info(f"Fireflies transcript already ingested: {transcript_id}")
                return existing, True

            # Connect to Fireflies
            async with FirefliesConnector(credentials) as fireflies:
                # Get transcript details
                response = await fireflies.get_transcript(transcript_id)
                data = response.data.get("data", {}).get("transcript", {})

                # Extract transcript chunks from sentences
                transcript_chunks = self._extract_fireflies_chunks(data.get("sentences", []))
                full_transcript = " ".join([chunk.text for chunk in transcript_chunks])

                # Build meeting object
                meeting = Meeting(
                    workspace_id=workspace_id,
                    founder_id=founder_id,
                    title=data.get("title", "Untitled Meeting"),
                    source=MeetingSource.FIREFLIES,
                    status=MeetingStatus.INGESTING,
                    scheduled_at=self._parse_datetime(data.get("date")),
                    host_name=data.get("host_name"),
                    host_email=data.get("host_email"),
                    participants=self._extract_fireflies_participants(data.get("meeting_attendees", [])),
                    participant_count=len(data.get("meeting_attendees", [])),
                    transcript=full_transcript,
                    transcript_chunks=transcript_chunks,
                    metadata=MeetingMetadata(
                        duration=data.get("duration"),
                        platform_id=transcript_id,
                        transcript_url=data.get("transcript_url"),
                        audio_url=data.get("audio_url"),
                        video_url=data.get("video_url"),
                        platform_data={
                            "summary": data.get("summary", {}),
                            "duplicate_hash": duplicate_hash
                        }
                    ),
                    ingestion_started_at=datetime.utcnow()
                )

                # Save to database
                meeting = await self._save_meeting(meeting)

                self.logger.info(f"Successfully ingested Fireflies transcript: {transcript_id}")
                return meeting, False

        except Exception as e:
            self.logger.error(f"Failed to ingest Fireflies transcript {transcript_id}: {str(e)}")
            raise

    async def ingest_from_otter(
        self,
        workspace_id: UUID,
        founder_id: UUID,
        speech_id: str,
        credentials: Dict[str, Any]
    ) -> Tuple[Meeting, bool]:
        """
        Ingest meeting from Otter

        Args:
            workspace_id: Workspace UUID
            founder_id: Founder UUID
            speech_id: Otter speech ID
            credentials: Otter API credentials

        Returns:
            Tuple of (Meeting object, is_duplicate flag)
        """
        try:
            # Check for duplicate
            duplicate_hash = self._generate_meeting_hash(MeetingSource.OTTER, speech_id)
            existing = await self._find_by_hash(workspace_id, duplicate_hash)
            if existing:
                self.logger.info(f"Otter speech already ingested: {speech_id}")
                return existing, True

            # Connect to Otter
            async with OtterConnector(credentials) as otter:
                # Get speech details with transcript
                response = await otter.get_speech_transcript(speech_id)
                data = response.data

                # Extract transcript
                transcript = data.get("transcript", {}).get("text", "")
                transcript_chunks = self._extract_otter_chunks(data.get("transcript", {}).get("words", []))

                # Get summary if available
                summary_response = await otter.get_speech_summary(speech_id)
                summary = summary_response.data if summary_response.status.value == "success" else {}

                # Build meeting object
                meeting = Meeting(
                    workspace_id=workspace_id,
                    founder_id=founder_id,
                    title=data.get("title", "Untitled Speech"),
                    source=MeetingSource.OTTER,
                    status=MeetingStatus.INGESTING,
                    scheduled_at=self._parse_datetime(data.get("created_at")),
                    host_name=data.get("creator", {}).get("name"),
                    host_email=data.get("creator", {}).get("email"),
                    participants=self._extract_otter_participants(data.get("speakers", [])),
                    participant_count=len(data.get("speakers", [])),
                    transcript=transcript,
                    transcript_chunks=transcript_chunks,
                    metadata=MeetingMetadata(
                        duration=data.get("duration"),
                        platform_id=speech_id,
                        platform_data={
                            "summary": summary,
                            "duplicate_hash": duplicate_hash
                        }
                    ),
                    ingestion_started_at=datetime.utcnow()
                )

                # Save to database
                meeting = await self._save_meeting(meeting)

                self.logger.info(f"Successfully ingested Otter speech: {speech_id}")
                return meeting, False

        except Exception as e:
            self.logger.error(f"Failed to ingest Otter speech {speech_id}: {str(e)}")
            raise

    def _generate_meeting_hash(self, source: MeetingSource, platform_id: str) -> str:
        """Generate unique hash for meeting deduplication"""
        hash_input = f"{source.value}:{platform_id}"
        return hashlib.sha256(hash_input.encode()).hexdigest()

    async def _find_by_hash(self, workspace_id: UUID, duplicate_hash: str) -> Optional[Meeting]:
        """Find existing meeting by hash"""
        if not self.supabase:
            return None

        try:
            # Query using jsonb path to search in metadata
            result = self.supabase.table("meetings").select("*").eq(
                "workspace_id", str(workspace_id)
            ).execute()

            # Filter by duplicate_hash in metadata
            for row in result.data:
                metadata = row.get("metadata", {})
                platform_data = metadata.get("platform_data", {})
                if platform_data.get("duplicate_hash") == duplicate_hash:
                    return Meeting(**row)

            return None
        except Exception as e:
            self.logger.error(f"Error finding meeting by hash: {str(e)}")
            return None

    async def _save_meeting(self, meeting: Meeting) -> Meeting:
        """Save meeting to database"""
        if not self.supabase:
            self.logger.warning("No Supabase client configured, returning meeting without saving")
            return meeting

        try:
            # Convert to dict for insertion
            meeting_dict = meeting.model_dump(mode='json')
            meeting_dict["id"] = str(meeting.id)
            meeting_dict["workspace_id"] = str(meeting.workspace_id)
            meeting_dict["founder_id"] = str(meeting.founder_id)

            # Insert into database
            result = self.supabase.table("meetings").insert(meeting_dict).execute()

            self.logger.info(f"Saved meeting to database: {meeting.id}")
            return meeting

        except Exception as e:
            self.logger.error(f"Failed to save meeting: {str(e)}")
            raise

    def _chunk_transcript(self, transcript: str, chunk_size: int = 500) -> List[TranscriptChunk]:
        """
        Chunk transcript into smaller pieces for vector embedding

        Args:
            transcript: Full transcript text
            chunk_size: Approximate words per chunk

        Returns:
            List of TranscriptChunk objects
        """
        if not transcript:
            return []

        words = transcript.split()
        chunks = []

        for i in range(0, len(words), chunk_size):
            chunk_words = words[i:i + chunk_size]
            chunks.append(TranscriptChunk(
                text=" ".join(chunk_words),
                chunk_index=len(chunks)
            ))

        return chunks

    def _extract_zoom_transcript(self, recording_data: Dict[str, Any]) -> Optional[str]:
        """Extract transcript from Zoom recording data"""
        # Zoom stores transcripts in recording_files with type "transcript"
        for file in recording_data.get("recording_files", []):
            if file.get("file_type") == "transcript":
                # In production, you'd download and parse the VTT file
                # For now, return a placeholder
                return file.get("download_url")
        return None

    def _extract_zoom_participants(self, participants_data: Dict[str, Any]) -> List[MeetingParticipant]:
        """Extract participant information from Zoom data"""
        participants = []
        for p in participants_data.get("participants", []):
            participants.append(MeetingParticipant(
                name=p.get("name", "Unknown"),
                email=p.get("email"),
                join_time=self._parse_datetime(p.get("join_time")),
                leave_time=self._parse_datetime(p.get("leave_time")),
                duration=p.get("duration")
            ))
        return participants

    def _extract_fireflies_chunks(self, sentences: List[Dict[str, Any]]) -> List[TranscriptChunk]:
        """Extract transcript chunks from Fireflies sentences"""
        chunks = []
        for i, sentence in enumerate(sentences):
            chunks.append(TranscriptChunk(
                text=sentence.get("text", ""),
                speaker_name=sentence.get("speaker_name"),
                start_time=sentence.get("start_time"),
                end_time=sentence.get("end_time"),
                chunk_index=i
            ))
        return chunks

    def _extract_fireflies_participants(self, attendees: List[Dict[str, Any]]) -> List[MeetingParticipant]:
        """Extract participant information from Fireflies data"""
        participants = []
        for attendee in attendees:
            participants.append(MeetingParticipant(
                name=attendee.get("displayName", "Unknown"),
                email=attendee.get("email")
            ))
        return participants

    def _extract_otter_chunks(self, words: List[Dict[str, Any]]) -> List[TranscriptChunk]:
        """Extract transcript chunks from Otter word-level data"""
        # Group words into sentences or fixed-size chunks
        chunks = []
        current_chunk = []
        current_start = None

        for i, word in enumerate(words):
            if current_start is None:
                current_start = word.get("start")

            current_chunk.append(word.get("word", ""))

            # Create chunk every 50 words or at sentence end
            if len(current_chunk) >= 50 or word.get("word", "").endswith((".", "!", "?")):
                chunks.append(TranscriptChunk(
                    text=" ".join(current_chunk),
                    speaker_name=word.get("speaker"),
                    start_time=current_start,
                    end_time=word.get("end"),
                    chunk_index=len(chunks)
                ))
                current_chunk = []
                current_start = None

        # Add remaining words
        if current_chunk:
            chunks.append(TranscriptChunk(
                text=" ".join(current_chunk),
                chunk_index=len(chunks)
            ))

        return chunks

    def _extract_otter_participants(self, speakers: List[Dict[str, Any]]) -> List[MeetingParticipant]:
        """Extract participant information from Otter data"""
        participants = []
        for speaker in speakers:
            participants.append(MeetingParticipant(
                name=speaker.get("name", f"Speaker {speaker.get('id', 'Unknown')}")
            ))
        return participants

    def _parse_datetime(self, dt_string: Optional[str]) -> Optional[datetime]:
        """Parse datetime string to datetime object"""
        if not dt_string:
            return None

        try:
            # Try ISO format
            return datetime.fromisoformat(dt_string.replace("Z", "+00:00"))
        except:
            try:
                # Try common formats
                from dateutil import parser
                return parser.parse(dt_string)
            except:
                return None

    async def update_meeting_status(
        self,
        meeting_id: UUID,
        status: MeetingStatus,
        error_message: Optional[str] = None
    ) -> None:
        """Update meeting processing status"""
        if not self.supabase:
            return

        try:
            update_data = {
                "status": status.value,
                "updated_at": datetime.utcnow().isoformat()
            }

            if status == MeetingStatus.COMPLETED:
                update_data["ingestion_completed_at"] = datetime.utcnow().isoformat()

            if error_message:
                update_data["error_message"] = error_message

            self.supabase.table("meetings").update(update_data).eq(
                "id", str(meeting_id)
            ).execute()

        except Exception as e:
            self.logger.error(f"Failed to update meeting status: {str(e)}")
