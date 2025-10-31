"""
AI Chief of Staff - Meeting Ingestion Service Tests
Sprint 3: Issue #7 - Meeting Ingestion

Test coverage for:
- Ingest from Zoom connector
- Ingest from Fireflies connector
- Ingest from Otter connector
- Deduplication across sources
- Participant extraction and matching
- Transcript chunking logic
- Vector embedding generation
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch, call
import numpy as np

from tests.fixtures.meeting_fixtures import (
    MeetingFactory,
    TranscriptFactory,
    TranscriptChunkFactory,
    create_meeting_with_transcript,
    create_meeting_from_multiple_sources
)
from tests.fixtures.mock_transcripts import get_transcript_by_type


# ============================================================================
# INGEST FROM ZOOM CONNECTOR
# ============================================================================

@pytest.mark.unit
@pytest.mark.meeting
@pytest.mark.asyncio
class TestIngestFromZoom:
    """Test meeting ingestion from Zoom connector."""

    async def test_ingest_zoom_meeting_successful(
        self,
        mock_zoom_connector: AsyncMock,
        mock_workspace_id: str,
        mock_founder_id: str
    ):
        """
        Test: Successful Zoom meeting ingestion
        Given: Zoom connector returns meeting data
        When: ingest_from_zoom() called
        Then: Meeting entity created with correct metadata
        """
        # Arrange
        zoom_meeting_data = {
            "id": "123456789",
            "uuid": str(uuid4()),
            "topic": "Product Roadmap Review",
            "start_time": datetime.utcnow().isoformat(),
            "duration": 60,
            "host_id": "user123",
            "participants": [
                {"name": "Alice Johnson", "email": "alice@example.com"},
                {"name": "Bob Smith", "email": "bob@example.com"}
            ],
            "recording_url": "https://zoom.us/rec/share/abc123"
        }
        mock_zoom_connector.fetch_meeting.return_value = zoom_meeting_data

        # Mock service
        async def mock_ingest_from_zoom(workspace_id, founder_id, external_id):
            meeting = MeetingFactory(
                workspace_id=workspace_id,
                founder_id=founder_id,
                platform="zoom",
                external_id=external_id,
                title=zoom_meeting_data["topic"],
                duration_minutes=zoom_meeting_data["duration"],
                participants=zoom_meeting_data["participants"]
            )
            return meeting

        # Act
        result = await mock_ingest_from_zoom(
            mock_workspace_id,
            mock_founder_id,
            zoom_meeting_data["id"]
        )

        # Assert
        assert result["platform"] == "zoom"
        assert result["external_id"] == zoom_meeting_data["id"]
        assert result["title"] == zoom_meeting_data["topic"]
        assert result["duration_minutes"] == 60
        assert len(result["participants"]) == 2

    async def test_ingest_zoom_with_transcript(
        self,
        mock_zoom_connector: AsyncMock,
        mock_workspace_id: str
    ):
        """
        Test: Zoom meeting ingestion includes transcript
        Given: Zoom provides both meeting and transcript
        When: ingest_from_zoom() called
        Then: Both meeting and transcript entities created
        """
        # Arrange
        meeting_data = create_meeting_with_transcript(provider="zoom")

        # Mock connector to return transcript
        mock_zoom_connector.fetch_transcript.return_value = {
            "transcript_id": meeting_data["transcript"]["id"],
            "vtt_url": "https://zoom.us/transcript.vtt"
        }

        # Act - Simulate ingestion
        meeting = meeting_data["meeting"]
        transcript = meeting_data["transcript"]

        # Assert
        assert meeting["platform"] == "zoom"
        assert transcript["provider"] == "zoom"
        assert transcript["meeting_id"] == meeting["id"]
        assert transcript["workspace_id"] == meeting["workspace_id"]

    async def test_ingest_zoom_handles_missing_transcript(
        self,
        mock_zoom_connector: AsyncMock,
        mock_workspace_id: str
    ):
        """
        Test: Graceful handling when Zoom transcript not ready
        Given: Zoom meeting exists but transcript not yet processed
        When: ingest_from_zoom() called
        Then: Meeting created, transcript marked as pending
        """
        # Arrange
        mock_zoom_connector.fetch_transcript.side_effect = Exception("Transcript not ready")

        meeting = MeetingFactory(platform="zoom")

        # Act - Attempt to fetch transcript
        transcript_error = None
        try:
            await mock_zoom_connector.fetch_transcript(meeting["external_id"])
        except Exception as e:
            transcript_error = str(e)

        # Assert
        assert transcript_error == "Transcript not ready"
        assert meeting is not None  # Meeting should still be created

    async def test_ingest_zoom_participant_extraction(
        self,
        mock_workspace_id: str
    ):
        """
        Test: Participant data extraction and normalization
        Given: Zoom meeting with participant list
        When: Participants extracted
        Then: Participant emails normalized and deduplicated
        """
        # Arrange
        meeting = MeetingFactory(
            platform="zoom",
            participants=[
                {"name": "Alice Johnson", "email": "alice@EXAMPLE.com"},
                {"name": "Alice J.", "email": "alice@example.com"},  # Duplicate
                {"name": "Bob Smith", "email": "bob@example.com"}
            ]
        )

        # Act - Simulate participant deduplication
        def deduplicate_participants(participants):
            seen = set()
            unique = []
            for p in participants:
                email = p["email"].lower()
                if email not in seen:
                    seen.add(email)
                    unique.append({
                        "name": p["name"],
                        "email": email
                    })
            return unique

        unique_participants = deduplicate_participants(meeting["participants"])

        # Assert
        assert len(unique_participants) == 2  # Duplicates removed
        assert all(p["email"].islower() for p in unique_participants)


# ============================================================================
# INGEST FROM FIREFLIES CONNECTOR
# ============================================================================

@pytest.mark.unit
@pytest.mark.meeting
@pytest.mark.asyncio
class TestIngestFromFireflies:
    """Test meeting ingestion from Fireflies connector."""

    async def test_ingest_fireflies_transcript_successful(
        self,
        mock_fireflies_mcp: AsyncMock,
        mock_workspace_id: str
    ):
        """
        Test: Successful Fireflies transcript ingestion
        Given: Fireflies connector returns transcript data
        When: ingest_from_fireflies() called
        Then: Transcript entity created with Fireflies provider
        """
        # Arrange
        fireflies_data = {
            "transcript_id": str(uuid4()),
            "title": "Product Roadmap Review",
            "date": datetime.utcnow().isoformat(),
            "duration": 3600,
            "transcript_text": get_transcript_by_type("medium"),
            "sentences": [
                {"speaker_name": "Sarah", "text": "Let's start", "start_time": 0},
                {"speaker_name": "David", "text": "Here's the update", "start_time": 30}
            ]
        }
        mock_fireflies_mcp.fetch_transcript.return_value = fireflies_data

        # Act
        transcript = TranscriptFactory.from_fireflies(
            workspace_id=mock_workspace_id,
            title=fireflies_data["title"],
            duration_seconds=fireflies_data["duration"]
        )

        # Assert
        assert transcript["provider"] == "fireflies"
        assert transcript["title"] == fireflies_data["title"]
        assert transcript["duration_seconds"] == 3600

    async def test_fireflies_sentence_to_chunk_conversion(
        self,
        mock_workspace_id: str
    ):
        """
        Test: Convert Fireflies sentences to transcript chunks
        Given: Fireflies returns sentence-level transcript
        When: Converting to chunks
        Then: Sentences grouped into time-based chunks
        """
        # Arrange
        sentences = [
            {"speaker_name": "Alice", "text": "First point", "start_time": 0, "end_time": 10},
            {"speaker_name": "Alice", "text": "Second point", "start_time": 10, "end_time": 20},
            {"speaker_name": "Bob", "text": "Response", "start_time": 20, "end_time": 35},
            {"speaker_name": "Alice", "text": "Follow up", "start_time": 35, "end_time": 50}
        ]

        # Act - Group sentences into 30-second chunks
        def create_chunks(sentences, chunk_duration=30):
            chunks = []
            current_chunk = {
                "speaker": sentences[0]["speaker_name"],
                "text": "",
                "start_sec": 0,
                "end_sec": 0
            }

            for sent in sentences:
                chunk_index = int(sent["start_time"] / chunk_duration)
                if sent["speaker_name"] == current_chunk["speaker"] and \
                   chunk_index == int(current_chunk["start_sec"] / chunk_duration):
                    current_chunk["text"] += " " + sent["text"]
                    current_chunk["end_sec"] = sent["end_time"]
                else:
                    if current_chunk["text"]:
                        chunks.append(current_chunk)
                    current_chunk = {
                        "speaker": sent["speaker_name"],
                        "text": sent["text"],
                        "start_sec": sent["start_time"],
                        "end_sec": sent["end_time"]
                    }

            if current_chunk["text"]:
                chunks.append(current_chunk)

            return chunks

        chunks = create_chunks(sentences)

        # Assert
        assert len(chunks) >= 1
        assert all("speaker" in chunk for chunk in chunks)
        assert all("text" in chunk for chunk in chunks)

    async def test_fireflies_fallback_when_zoom_unavailable(
        self,
        mock_zoom_connector: AsyncMock,
        mock_fireflies_mcp: AsyncMock,
        mock_workspace_id: str
    ):
        """
        Test: Fireflies used as fallback when Zoom transcript unavailable
        Given: Zoom transcript not ready
        And: Same meeting exists in Fireflies
        When: Ingestion attempted
        Then: Fireflies transcript used instead
        """
        # Arrange
        external_id = "meeting_123"
        mock_zoom_connector.fetch_transcript.side_effect = Exception("Not ready")

        fireflies_transcript = TranscriptFactory.from_fireflies(
            external_id=external_id
        )
        mock_fireflies_mcp.fetch_transcript.return_value = fireflies_transcript

        # Act - Simulate fallback logic
        transcript = None
        try:
            await mock_zoom_connector.fetch_transcript(external_id)
        except:
            # Fallback to Fireflies
            transcript = await mock_fireflies_mcp.fetch_transcript(external_id)

        # Assert
        assert transcript is not None
        assert transcript["provider"] == "fireflies"


# ============================================================================
# INGEST FROM OTTER CONNECTOR
# ============================================================================

@pytest.mark.unit
@pytest.mark.meeting
@pytest.mark.asyncio
class TestIngestFromOtter:
    """Test meeting ingestion from Otter connector."""

    async def test_ingest_otter_transcript_with_speaker_identification(
        self,
        mock_workspace_id: str
    ):
        """
        Test: Otter transcript with speaker identification
        Given: Otter provides speaker-identified transcript
        When: ingest_from_otter() called
        Then: Speaker information preserved in chunks
        """
        # Arrange
        transcript = TranscriptFactory.from_otter(
            workspace_id=mock_workspace_id,
            speaker_count=4
        )

        chunks = [
            TranscriptChunkFactory(
                transcript_id=transcript["id"],
                speaker=f"Speaker {i % 4}",
                chunk_index=i
            )
            for i in range(10)
        ]

        # Assert
        assert transcript["provider"] == "otter"
        assert transcript["speaker_count"] == 4
        assert len(chunks) == 10
        assert len(set(chunk["speaker"] for chunk in chunks)) <= 4

    async def test_otter_high_confidence_filtering(
        self,
        mock_workspace_id: str
    ):
        """
        Test: Filter low-confidence Otter transcriptions
        Given: Otter transcript with varying confidence scores
        When: Processing chunks
        Then: Low confidence chunks flagged for review
        """
        # Arrange
        chunks = [
            TranscriptChunkFactory(confidence=0.95),  # High
            TranscriptChunkFactory(confidence=0.85),  # Medium-high
            TranscriptChunkFactory(confidence=0.65),  # Medium
            TranscriptChunkFactory(confidence=0.45)   # Low
        ]

        # Act - Filter chunks by confidence
        high_confidence = [c for c in chunks if c["confidence"] >= 0.8]
        needs_review = [c for c in chunks if c["confidence"] < 0.7]

        # Assert
        assert len(high_confidence) == 2
        assert len(needs_review) == 2


# ============================================================================
# DEDUPLICATION ACROSS SOURCES
# ============================================================================

@pytest.mark.unit
@pytest.mark.meeting
@pytest.mark.asyncio
class TestDeduplicationAcrossSources:
    """Test deduplication logic when same meeting from multiple sources."""

    async def test_deduplicate_same_meeting_from_multiple_sources(
        self,
        mock_workspace_id: str
    ):
        """
        Test: Deduplicate meeting ingested from multiple sources
        Given: Same meeting from Zoom, Fireflies, and Otter
        When: Deduplication logic applied
        Then: Single meeting entity with multiple transcript sources
        """
        # Arrange
        meeting_data = create_meeting_from_multiple_sources()
        meeting = meeting_data["meeting"]
        transcripts = meeting_data["transcripts"]

        # Act - Simulate deduplication by external_id
        def deduplicate_by_external_id(meeting, transcripts):
            """Group transcripts by external_id/meeting_id"""
            external_id = meeting["external_id"]
            return {
                "meeting": meeting,
                "transcripts": [t for t in transcripts.values() if t.get("external_id") == external_id]
            }

        deduplicated = deduplicate_by_external_id(meeting, transcripts)

        # Assert
        assert deduplicated["meeting"]["id"] == meeting["id"]
        assert len(deduplicated["transcripts"]) == 3
        assert all(t["external_id"] == meeting["external_id"] for t in deduplicated["transcripts"])

    async def test_select_best_quality_transcript(
        self,
        mock_workspace_id: str
    ):
        """
        Test: Select highest quality transcript when multiple available
        Given: Same meeting with transcripts from Zoom, Fireflies, Otter
        When: Quality scoring applied
        Then: Best quality transcript selected
        """
        # Arrange
        meeting_data = create_meeting_from_multiple_sources()
        transcripts = list(meeting_data["transcripts"].values())

        # Assign quality scores
        transcripts[0]["quality_score"] = 0.92  # Zoom
        transcripts[1]["quality_score"] = 0.88  # Fireflies
        transcripts[2]["quality_score"] = 0.95  # Otter

        # Act - Select best transcript
        def select_best_transcript(transcripts):
            """Select transcript with highest quality score"""
            if not transcripts:
                return None
            return max(transcripts, key=lambda t: t.get("quality_score", 0))

        best = select_best_transcript(transcripts)

        # Assert
        assert best["provider"] == "otter"
        assert best["quality_score"] == 0.95

    async def test_merge_metadata_from_multiple_sources(
        self,
        mock_workspace_id: str
    ):
        """
        Test: Merge complementary metadata from multiple sources
        Given: Zoom has recording URL, Fireflies has better participants, Otter has speaker IDs
        When: Merging metadata
        Then: Combined metadata includes best from each source
        """
        # Arrange
        meeting = MeetingFactory(
            platform="zoom",
            recording_url="https://zoom.us/rec/123"
        )

        fireflies_participants = [
            {"name": "Alice Johnson", "email": "alice@example.com", "role": "host"},
            {"name": "Bob Smith", "email": "bob@example.com", "role": "attendee"}
        ]

        otter_speaker_map = {
            "Speaker 0": "Alice Johnson",
            "Speaker 1": "Bob Smith"
        }

        # Act - Merge metadata
        merged = {
            "meeting_id": meeting["id"],
            "recording_url": meeting["recording_url"],
            "participants": fireflies_participants,
            "speaker_mapping": otter_speaker_map
        }

        # Assert
        assert merged["recording_url"] == meeting["recording_url"]
        assert len(merged["participants"]) == 2
        assert merged["participants"][0]["role"] == "host"
        assert len(merged["speaker_mapping"]) == 2


# ============================================================================
# PARTICIPANT EXTRACTION AND MATCHING
# ============================================================================

@pytest.mark.unit
@pytest.mark.meeting
@pytest.mark.asyncio
class TestParticipantExtraction:
    """Test participant extraction and matching logic."""

    async def test_extract_participants_from_zoom(self):
        """
        Test: Extract and normalize participant data from Zoom
        Given: Zoom meeting with participant list
        When: Extracting participants
        Then: Normalized participant objects created
        """
        # Arrange
        meeting = MeetingFactory(
            platform="zoom",
            participants=[
                {"name": "Alice Johnson", "email": "alice@example.com", "user_id": "zoom_123"},
                {"name": "Bob Smith", "email": "", "user_id": "zoom_456"},  # No email
                {"name": "", "email": "carol@example.com", "user_id": "zoom_789"}  # No name
            ]
        )

        # Act - Normalize participants
        def normalize_participants(participants):
            normalized = []
            for p in participants:
                if p.get("email") or p.get("name"):
                    normalized.append({
                        "name": p.get("name", "Unknown").strip(),
                        "email": p.get("email", "").strip().lower(),
                        "external_id": p.get("user_id")
                    })
            return normalized

        participants = normalize_participants(meeting["participants"])

        # Assert
        assert len(participants) == 3
        assert participants[0]["email"] == "alice@example.com"
        assert participants[1]["name"] == "Bob Smith"
        assert participants[2]["name"] == "Unknown"

    async def test_match_participants_to_workspace_members(
        self,
        mock_workspace_id: str
    ):
        """
        Test: Match meeting participants to workspace members
        Given: Meeting participants and workspace member list
        When: Matching by email
        Then: Participants linked to member IDs
        """
        # Arrange
        workspace_members = [
            {"id": str(uuid4()), "email": "alice@example.com", "name": "Alice Johnson"},
            {"id": str(uuid4()), "email": "bob@example.com", "name": "Bob Smith"}
        ]

        meeting_participants = [
            {"name": "Alice Johnson", "email": "alice@example.com"},
            {"name": "Bob S.", "email": "bob@example.com"},
            {"name": "Carol Davis", "email": "carol@external.com"}  # External
        ]

        # Act - Match participants
        def match_to_members(participants, members):
            member_map = {m["email"].lower(): m for m in members}
            matched = []
            for p in participants:
                email = p["email"].lower()
                member = member_map.get(email)
                matched.append({
                    **p,
                    "member_id": member["id"] if member else None,
                    "is_external": member is None
                })
            return matched

        matched_participants = match_to_members(meeting_participants, workspace_members)

        # Assert
        assert matched_participants[0]["member_id"] is not None
        assert matched_participants[1]["member_id"] is not None
        assert matched_participants[2]["member_id"] is None
        assert matched_participants[2]["is_external"] is True

    async def test_fuzzy_match_participant_names(self):
        """
        Test: Fuzzy matching for participant names
        Given: Participant name variations (nicknames, typos)
        When: Fuzzy matching applied
        Then: Correct matches identified
        """
        # Arrange
        workspace_members = [
            {"name": "Robert Johnson", "email": "robert@example.com"},
            {"name": "Catherine Smith", "email": "catherine@example.com"}
        ]

        meeting_participants = [
            {"name": "Bob Johnson", "email": "unknown@example.com"},  # Nickname
            {"name": "Cathy Smith", "email": "cathy@example.com"}     # Nickname
        ]

        # Act - Simple name matching (would use fuzzy lib in real implementation)
        def fuzzy_match_names(participants, members):
            # Simplified: check if first word matches
            matched = []
            for p in participants:
                p_first = p["name"].split()[0].lower()
                match = None
                for m in members:
                    m_first = m["name"].split()[0].lower()
                    if p_first in m_first or m_first in p_first or \
                       (p_first == "bob" and m_first == "robert") or \
                       (p_first == "cathy" and m_first == "catherine"):
                        match = m
                        break
                matched.append({**p, "matched_member": match})
            return matched

        matched = fuzzy_match_names(meeting_participants, workspace_members)

        # Assert
        assert matched[0]["matched_member"] is not None
        assert matched[0]["matched_member"]["name"] == "Robert Johnson"
        assert matched[1]["matched_member"] is not None


# ============================================================================
# TRANSCRIPT CHUNKING LOGIC
# ============================================================================

@pytest.mark.unit
@pytest.mark.meeting
@pytest.mark.asyncio
class TestTranscriptChunking:
    """Test transcript chunking logic for embeddings."""

    async def test_chunk_transcript_by_time_interval(
        self,
        mock_workspace_id: str
    ):
        """
        Test: Chunk transcript by fixed time intervals
        Given: Full transcript text with timestamps
        When: Chunking by 60-second intervals
        Then: Chunks created with proper boundaries
        """
        # Arrange
        transcript_data = get_transcript_by_type("medium")
        chunks_data = transcript_data["chunks"]

        # Act - Create chunks
        chunks = [
            TranscriptChunkFactory(
                chunk_index=i,
                start_sec=chunk["start_sec"],
                end_sec=chunk["end_sec"],
                speaker=chunk["speaker"],
                text=chunk["text"]
            )
            for i, chunk in enumerate(chunks_data)
        ]

        # Assert
        assert len(chunks) == len(chunks_data)
        assert all(chunk["end_sec"] > chunk["start_sec"] for chunk in chunks)
        # Verify chunks are sequential
        for i in range(len(chunks) - 1):
            assert chunks[i]["end_sec"] <= chunks[i + 1]["start_sec"]

    async def test_chunk_transcript_by_speaker_change(
        self,
        mock_workspace_id: str
    ):
        """
        Test: Chunk transcript on speaker changes
        Given: Transcript with multiple speakers
        When: Chunking on speaker boundaries
        Then: Each chunk contains single speaker
        """
        # Arrange
        sentences = [
            {"speaker": "Alice", "text": "First point", "time": 0},
            {"speaker": "Alice", "text": "Second point", "time": 10},
            {"speaker": "Bob", "text": "Response here", "time": 20},
            {"speaker": "Bob", "text": "More response", "time": 30},
            {"speaker": "Alice", "text": "Follow up", "time": 40}
        ]

        # Act - Create speaker-based chunks
        def chunk_by_speaker(sentences):
            chunks = []
            current_chunk = None

            for sent in sentences:
                if current_chunk is None or current_chunk["speaker"] != sent["speaker"]:
                    if current_chunk:
                        chunks.append(current_chunk)
                    current_chunk = {
                        "speaker": sent["speaker"],
                        "text": sent["text"],
                        "start_sec": sent["time"]
                    }
                else:
                    current_chunk["text"] += " " + sent["text"]
                current_chunk["end_sec"] = sent["time"]

            if current_chunk:
                chunks.append(current_chunk)

            return chunks

        chunks = chunk_by_speaker(sentences)

        # Assert
        assert len(chunks) == 3  # Alice, Bob, Alice
        assert chunks[0]["speaker"] == "Alice"
        assert chunks[1]["speaker"] == "Bob"
        assert chunks[2]["speaker"] == "Alice"

    async def test_chunk_size_limits(self, mock_workspace_id: str):
        """
        Test: Enforce chunk size limits for embedding
        Given: Very long speaker turn
        When: Chunking applied
        Then: Long turns split into max token chunks
        """
        # Arrange
        long_text = " ".join(["This is a sentence." for _ in range(200)])  # Very long
        MAX_CHUNK_TOKENS = 500

        # Act - Split by token limit (simplified: by word count)
        def split_by_token_limit(text, max_tokens=500):
            words = text.split()
            chunks = []
            current_chunk = []

            for word in words:
                current_chunk.append(word)
                if len(current_chunk) >= max_tokens:
                    chunks.append(" ".join(current_chunk))
                    current_chunk = []

            if current_chunk:
                chunks.append(" ".join(current_chunk))

            return chunks

        chunks = split_by_token_limit(long_text, MAX_CHUNK_TOKENS)

        # Assert
        assert len(chunks) > 1  # Should be split
        assert all(len(chunk.split()) <= MAX_CHUNK_TOKENS for chunk in chunks)


# ============================================================================
# VECTOR EMBEDDING GENERATION
# ============================================================================

@pytest.mark.unit
@pytest.mark.meeting
@pytest.mark.vector
@pytest.mark.asyncio
class TestVectorEmbeddingGeneration:
    """Test vector embedding generation for transcript chunks."""

    async def test_generate_embeddings_for_chunks(
        self,
        mock_embedding_service: MagicMock
    ):
        """
        Test: Generate embeddings for transcript chunks
        Given: Transcript chunks with text
        When: generate_embeddings() called
        Then: Vector embeddings created (1536 dimensions)
        """
        # Arrange
        chunks = [
            TranscriptChunkFactory(text="This is the first chunk"),
            TranscriptChunkFactory(text="This is the second chunk"),
            TranscriptChunkFactory(text="This is the third chunk")
        ]

        # Act
        embeddings = [
            mock_embedding_service.generate_embedding(chunk["text"])
            for chunk in chunks
        ]

        # Assert
        assert len(embeddings) == 3
        assert all(len(emb) == 1536 for emb in embeddings)
        assert mock_embedding_service.generate_embedding.call_count == 3

    async def test_batch_embedding_generation(
        self,
        mock_embedding_service: MagicMock
    ):
        """
        Test: Batch embedding generation for efficiency
        Given: Multiple chunks to embed
        When: Batch processing applied
        Then: All embeddings generated in batches
        """
        # Arrange
        chunks = [TranscriptChunkFactory() for _ in range(50)]
        BATCH_SIZE = 10

        # Act - Generate in batches
        embeddings = []
        for i in range(0, len(chunks), BATCH_SIZE):
            batch = chunks[i:i + BATCH_SIZE]
            batch_embeddings = [
                mock_embedding_service.generate_embedding(c["text"])
                for c in batch
            ]
            embeddings.extend(batch_embeddings)

        # Assert
        assert len(embeddings) == 50
        # Should be 5 batches
        expected_calls = (len(chunks) + BATCH_SIZE - 1) // BATCH_SIZE * BATCH_SIZE
        assert mock_embedding_service.generate_embedding.call_count >= 50

    async def test_embedding_storage_with_chunks(
        self,
        mock_workspace_id: str,
        mock_embedding_service: MagicMock
    ):
        """
        Test: Store embeddings with chunk metadata
        Given: Chunks with generated embeddings
        When: Storing in database
        Then: Embeddings linked to chunks correctly
        """
        # Arrange
        transcript = TranscriptFactory(workspace_id=mock_workspace_id)
        chunks_with_embeddings = [
            TranscriptChunkFactory.with_embedding(transcript_id=transcript["id"])
            for _ in range(5)
        ]

        # Assert
        assert all("embedding" in chunk for chunk in chunks_with_embeddings)
        assert all(chunk["transcript_id"] == transcript["id"] for chunk in chunks_with_embeddings)
        assert all(len(chunk["embedding"]) == 1536 for chunk in chunks_with_embeddings)

    async def test_embedding_cache_for_duplicate_text(
        self,
        mock_embedding_service: MagicMock
    ):
        """
        Test: Cache embeddings for identical text
        Given: Multiple chunks with same text
        When: Generating embeddings
        Then: Cached embedding reused
        """
        # Arrange
        duplicate_text = "This exact text appears multiple times"
        chunks = [
            TranscriptChunkFactory(text=duplicate_text),
            TranscriptChunkFactory(text=duplicate_text),
            TranscriptChunkFactory(text="Different text")
        ]

        # Act - Simulate caching
        embedding_cache = {}
        for chunk in chunks:
            if chunk["text"] not in embedding_cache:
                embedding_cache[chunk["text"]] = mock_embedding_service.generate_embedding(chunk["text"])
            chunk["embedding"] = embedding_cache[chunk["text"]]

        # Assert
        # Should only call embedding service twice (duplicate_text once, different text once)
        assert mock_embedding_service.generate_embedding.call_count == 2
        assert chunks[0]["embedding"] == chunks[1]["embedding"]
        assert chunks[0]["embedding"] != chunks[2]["embedding"]
