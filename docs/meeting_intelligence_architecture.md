# Meeting Intelligence Architecture

**Version:** 1.0
**Date:** 2025-10-30
**Sprint:** 3 - Meeting & Communication Intelligence
**Author:** System Architect

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [System Overview](#system-overview)
3. [Meeting Ingestion Pipeline](#meeting-ingestion-pipeline)
4. [Transcript Processing Architecture](#transcript-processing-architecture)
5. [Summarization Pipeline](#summarization-pipeline)
6. [Action Item Extraction](#action-item-extraction)
7. [Task Routing Engine](#task-routing-engine)
8. [Performance Requirements](#performance-requirements)
9. [Data Flow Diagrams](#data-flow-diagrams)
10. [API Specifications](#api-specifications)

---

## Executive Summary

The Meeting Intelligence system transforms raw meeting recordings and transcripts into actionable insights through a multi-stage AI pipeline. This architecture supports three meeting sources (Zoom, Fireflies, Otter), performs intelligent summarization, extracts action items, and automatically routes tasks to Monday.com.

### Key Capabilities

| Feature | Description | Performance Target |
|---------|-------------|-------------------|
| **Multi-Source Ingestion** | Zoom, Fireflies, Otter transcript ingestion | Real-time + batch modes |
| **Smart Chunking** | Semantic transcript segmentation | 500-1000 tokens/chunk |
| **AI Summarization** | LangChain-powered multi-stage summarization | <2 min post-meeting |
| **Action Extraction** | AI-powered action item detection | 90%+ precision |
| **Task Routing** | Automatic Monday.com task creation | <30s latency |
| **Speaker Diarization** | Track who said what | Per-speaker insights |

### Architecture Decisions

| Decision | Rationale | Impact |
|----------|-----------|---------|
| **LangChain Orchestration** | Industry-standard LLM orchestration | Flexible, maintainable chains |
| **Multi-Stage Summarization** | Extractive → Abstractive | Higher quality summaries |
| **Vector Embeddings** | Semantic search across transcripts | Fast contextual retrieval |
| **Webhook + Polling** | Dual ingestion modes | Reliability + real-time |
| **Async Processing** | Non-blocking pipeline | Scalable processing |
| **Confidence Scoring** | ML-based action item confidence | Reduced false positives |

---

## System Overview

### Architecture Layers

```
┌─────────────────────────────────────────────────────────────────────┐
│                    MEETING SOURCES                                   │
│     Zoom API/Webhooks │ Fireflies API │ Otter API                   │
└────────────────────────────┬─────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                 INGESTION LAYER (FastAPI)                            │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ Webhook Receivers │ Polling Workers │ Deduplication          │  │
│  │ Metadata Extraction │ Validation │ Source Merging            │  │
│  └──────────────────────────────────────────────────────────────┘  │
└────────────────────────────┬─────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│              TRANSCRIPT PROCESSING (Chunking)                        │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ Semantic Chunking │ Speaker Diarization │ Timestamp Alignment │  │
│  │ Vector Embedding (OpenAI ada-002) │ Topic Extraction         │  │
│  └──────────────────────────────────────────────────────────────┘  │
└────────────────────────────┬─────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│         AI SUMMARIZATION PIPELINE (LangChain)                        │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ Stage 1: Extractive Summary (Key Points)                      │  │
│  │ Stage 2: Abstractive Summary (Narrative)                      │  │
│  │ Stage 3: Action Item Extraction (ML Classification)           │  │
│  │ Stage 4: Decision Tracking                                    │  │
│  │ Stage 5: Follow-up Identification                             │  │
│  └──────────────────────────────────────────────────────────────┘  │
└────────────────────────────┬─────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│              TASK ROUTING ENGINE                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ Action Item Classifier │ Assignee Inference │ Priority Logic  │  │
│  │ Due Date Extraction │ Monday.com Task Creation               │  │
│  │ Task Linking │ Notification Dispatch                          │  │
│  └──────────────────────────────────────────────────────────────┘  │
└────────────────────────────┬─────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│           STORAGE & RETRIEVAL (Supabase + pgvector)                  │
│  meetings.transcripts │ meetings.transcript_chunks │ work.tasks      │
└─────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

#### 1. Ingestion Layer
- **Webhook Receivers**: Handle real-time notifications from Zoom/Fireflies/Otter
- **Polling Workers**: Batch fetch recordings for platforms without webhooks
- **Deduplication**: Detect and merge duplicate transcripts from multiple sources
- **Metadata Extraction**: Parse meeting title, participants, duration, timestamps

#### 2. Processing Layer
- **Semantic Chunking**: Split transcripts into meaningful segments (500-1000 tokens)
- **Speaker Diarization**: Track speaker changes and attributes
- **Vector Embedding**: Generate embeddings for semantic search
- **Topic Extraction**: Identify key themes using NLP

#### 3. Summarization Layer
- **Extractive Stage**: Extract key sentences and quotes
- **Abstractive Stage**: Generate human-readable narrative summary
- **Action Item ML**: Classify sentences as actionable vs informational
- **Decision Tracking**: Identify explicit decisions made
- **Follow-up Detection**: Extract future commitments and next steps

#### 4. Routing Layer
- **Assignee Inference**: Parse mentions, roles, and context to infer assignee
- **Priority Classification**: Detect urgency keywords (ASAP, urgent, critical)
- **Due Date Extraction**: Parse temporal expressions (tomorrow, next week, by Friday)
- **Monday.com Sync**: Create tasks with proper board/column placement
- **Notification**: Alert assignees via Slack/Email

---

## Meeting Ingestion Pipeline

### Multi-Source Ingestion Strategy

#### Zoom Ingestion Flow

**Real-Time Mode (Webhook):**
```
Zoom Recording Complete
    │
    ▼
Zoom Webhook: recording.completed
    │
    ▼
FastAPI Webhook Handler
    │
    ├─ Verify webhook signature
    ├─ Extract meeting metadata
    ├─ Queue transcript fetch job
    └─ Return 200 OK (< 5s)
    │
    ▼
Background Worker
    │
    ├─ Download VTT transcript
    ├─ Download audio (if needed)
    ├─ Parse participant list
    └─ Store in meetings.transcripts
```

**Batch Mode (Polling):**
```
Scheduled Job (every 15 min)
    │
    ▼
Query Zoom API /users/{userId}/recordings
    │
    ├─ Filter: recordingEnd >= last_sync
    ├─ Paginate through results
    └─ For each recording:
        │
        ├─ Check if already ingested
        ├─ Download transcript
        └─ Store in database
```

#### Fireflies Ingestion Flow

**Webhook Mode:**
```
Fireflies Transcript Ready
    │
    ▼
Webhook: transcript.ready
    │
    ▼
FastAPI Webhook Handler
    │
    ├─ Authenticate webhook
    ├─ Fetch transcript via API
    ├─ Extract AI notes
    └─ Store as secondary source
```

#### Otter Ingestion Flow

**API Polling Mode:**
```
Scheduled Job (every 30 min)
    │
    ▼
Query Otter API /speeches
    │
    ├─ Filter: created_at > last_sync
    └─ For each speech:
        │
        ├─ Fetch full transcript
        ├─ Extract speaker segments
        └─ Store as tertiary source
```

### Deduplication Logic

```python
class TranscriptDeduplicator:
    """Detect and merge duplicate transcripts from multiple sources"""

    async def find_duplicates(
        self,
        transcript: Dict,
        window_hours: int = 24
    ) -> List[TranscriptMatch]:
        """
        Find potential duplicate transcripts using:
        1. Time window matching (±24h)
        2. Title similarity (fuzzy match)
        3. Participant overlap
        4. Duration similarity
        """

        candidates = await db.fetch(
            """
            SELECT id, title, recorded_at, metadata
            FROM meetings.transcripts
            WHERE workspace_id = $1
              AND recorded_at BETWEEN $2 AND $3
              AND provider != $4
            """,
            workspace_id,
            recorded_at - timedelta(hours=window_hours),
            recorded_at + timedelta(hours=window_hours),
            transcript['provider']
        )

        matches = []
        for candidate in candidates:
            score = self.calculate_similarity(transcript, candidate)
            if score > 0.85:  # 85% confidence threshold
                matches.append(TranscriptMatch(
                    id=candidate['id'],
                    score=score,
                    reason=self.explain_match(transcript, candidate)
                ))

        return matches

    def calculate_similarity(
        self,
        t1: Dict,
        t2: Dict
    ) -> float:
        """
        Composite similarity score:
        - Title similarity (40%)
        - Time proximity (30%)
        - Duration match (15%)
        - Participant overlap (15%)
        """

        # Title similarity using Levenshtein distance
        title_sim = fuzz.ratio(
            t1['title'].lower(),
            t2['title'].lower()
        ) / 100

        # Time proximity (inverse of minutes apart)
        time_diff_mins = abs(
            (t1['recorded_at'] - t2['recorded_at']).total_seconds() / 60
        )
        time_sim = max(0, 1 - (time_diff_mins / 120))  # 2h window

        # Duration similarity
        if t1['duration'] and t2['duration']:
            duration_diff = abs(t1['duration'] - t2['duration'])
            duration_sim = max(0, 1 - (duration_diff / 60))
        else:
            duration_sim = 0.5

        # Participant overlap (Jaccard similarity)
        p1 = set(t1.get('participants', []))
        p2 = set(t2.get('participants', []))
        if p1 and p2:
            participant_sim = len(p1 & p2) / len(p1 | p2)
        else:
            participant_sim = 0.5

        # Weighted average
        score = (
            0.40 * title_sim +
            0.30 * time_sim +
            0.15 * duration_sim +
            0.15 * participant_sim
        )

        return score

    async def merge_transcripts(
        self,
        primary_id: uuid,
        secondary_ids: List[uuid]
    ) -> uuid:
        """
        Merge multiple transcript sources into one canonical record

        Strategy:
        1. Primary = longest/most detailed transcript
        2. Merge action items from all sources
        3. Combine summary sections
        4. Keep all source references
        """

        # Fetch all transcripts
        transcripts = await self.fetch_transcripts(
            [primary_id] + secondary_ids
        )

        # Determine best source for each field
        merged = {
            'id': primary_id,
            'title': self.select_best_title(transcripts),
            'transcript': self.merge_transcript_texts(transcripts),
            'action_items': self.merge_action_items(transcripts),
            'summary': self.merge_summaries(transcripts),
            'metadata': {
                'sources': [t['provider'] for t in transcripts],
                'merged_from': secondary_ids,
                'merged_at': datetime.utcnow().isoformat()
            }
        }

        # Update primary transcript
        await db.execute(
            """
            UPDATE meetings.transcripts
            SET
                title = $1,
                summary = $2,
                action_items = $3,
                metadata = metadata || $4::jsonb
            WHERE id = $5
            """,
            merged['title'],
            merged['summary'],
            merged['action_items'],
            json.dumps(merged['metadata']),
            primary_id
        )

        # Mark secondary transcripts as merged
        await db.execute(
            """
            UPDATE meetings.transcripts
            SET metadata = metadata || jsonb_build_object(
                'merged_into', $1,
                'merged_at', now()
            )
            WHERE id = ANY($2)
            """,
            primary_id,
            secondary_ids
        )

        return primary_id
```

### Webhook Handler Architecture

```python
from fastapi import APIRouter, Request, HTTPException, BackgroundTasks
from app.services.meeting_ingestion import MeetingIngestionService
from app.security.webhook_verification import verify_webhook_signature

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

@router.post("/zoom/recording-completed")
async def zoom_recording_webhook(
    request: Request,
    background_tasks: BackgroundTasks
):
    """
    Zoom webhook handler for recording.completed events

    Zoom webhook documentation:
    https://developers.zoom.us/docs/api/rest/webhook-reference/recording-events/
    """

    # 1. Verify webhook signature
    signature = request.headers.get("x-zm-signature")
    timestamp = request.headers.get("x-zm-request-timestamp")

    payload = await request.body()

    if not verify_webhook_signature(
        payload=payload,
        signature=signature,
        timestamp=timestamp,
        secret=settings.ZOOM_WEBHOOK_SECRET
    ):
        raise HTTPException(status_code=401, detail="Invalid signature")

    # 2. Parse webhook payload
    data = await request.json()
    event = data.get("event")

    if event != "recording.completed":
        return {"status": "ignored", "reason": "Not a recording.completed event"}

    # 3. Extract meeting metadata
    payload = data.get("payload", {})
    meeting_data = {
        "zoom_meeting_id": payload["object"]["id"],
        "topic": payload["object"]["topic"],
        "start_time": payload["object"]["start_time"],
        "duration": payload["object"]["duration"],
        "host_email": payload["object"]["host_email"],
        "recording_files": payload["object"]["recording_files"]
    }

    # 4. Queue background job for transcript ingestion
    # This returns quickly (< 5s) to meet Zoom's webhook timeout
    background_tasks.add_task(
        ingest_zoom_recording,
        meeting_data=meeting_data,
        workspace_id=extract_workspace_from_host(
            payload["object"]["host_email"]
        )
    )

    # 5. Log webhook event
    await log_webhook_event(
        platform="zoom",
        event_type="recording.completed",
        payload=data,
        status="queued"
    )

    return {
        "status": "accepted",
        "meeting_id": meeting_data["zoom_meeting_id"]
    }


async def ingest_zoom_recording(
    meeting_data: Dict,
    workspace_id: uuid
):
    """
    Background task to fetch and process Zoom recording

    Steps:
    1. Download VTT transcript file
    2. Parse transcript and metadata
    3. Store in meetings.transcripts
    4. Chunk transcript for vector search
    5. Queue AI summarization
    """

    service = MeetingIngestionService()

    try:
        # Find workspace integration
        integration = await db.fetchrow(
            """
            SELECT id, credentials_enc
            FROM core.integrations
            WHERE workspace_id = $1
              AND platform = 'zoom'
              AND status = 'connected'
            LIMIT 1
            """,
            workspace_id
        )

        if not integration:
            logger.error(f"No Zoom integration for workspace {workspace_id}")
            return

        # Decrypt OAuth tokens
        tokens = decrypt_credentials(integration['credentials_enc'])

        # Download transcript from Zoom
        transcript_data = await service.download_zoom_transcript(
            meeting_id=meeting_data["zoom_meeting_id"],
            access_token=tokens["access_token"]
        )

        # Store transcript
        transcript_id = await service.store_transcript(
            workspace_id=workspace_id,
            provider="zoom",
            meeting_data=meeting_data,
            transcript_data=transcript_data
        )

        # Check for duplicates
        duplicates = await service.deduplicator.find_duplicates(
            transcript_id=transcript_id,
            window_hours=24
        )

        if duplicates:
            logger.info(
                f"Found {len(duplicates)} duplicate transcripts "
                f"for {transcript_id}"
            )
            # Merge if high confidence match
            if duplicates[0].score > 0.90:
                await service.deduplicator.merge_transcripts(
                    primary_id=transcript_id,
                    secondary_ids=[d.id for d in duplicates]
                )

        # Queue chunking and summarization
        await service.queue_transcript_processing(transcript_id)

        logger.info(f"Successfully ingested Zoom recording {transcript_id}")

    except Exception as e:
        logger.error(
            f"Failed to ingest Zoom recording: {e}",
            exc_info=True
        )

        # Log error
        await log_integration_error(
            integration_id=integration['id'],
            error_type="transcript_ingestion_failed",
            error_message=str(e)
        )
```

---

## Transcript Processing Architecture

### Semantic Chunking Strategy

**Why Semantic Chunking?**
- Fixed-size chunks break sentences mid-thought
- Context-aware chunks improve embedding quality
- Better retrieval during QA and summarization

**Chunking Algorithm:**

```python
class SemanticTranscriptChunker:
    """
    Chunk transcripts semantically based on:
    - Speaker changes
    - Topic shifts
    - Temporal boundaries
    - Token limits (500-1000 tokens)
    """

    def __init__(
        self,
        target_tokens: int = 750,
        min_tokens: int = 500,
        max_tokens: int = 1000
    ):
        self.target_tokens = target_tokens
        self.min_tokens = min_tokens
        self.max_tokens = max_tokens
        self.tokenizer = tiktoken.encoding_for_model("gpt-4")

    async def chunk_transcript(
        self,
        transcript: Dict
    ) -> List[TranscriptChunk]:
        """
        Chunk transcript into semantic segments

        Algorithm:
        1. Split by speaker changes
        2. Merge small segments
        3. Split large segments at sentence boundaries
        4. Ensure token limits
        """

        # Parse VTT or plain text transcript
        segments = self.parse_transcript(transcript['text'])

        chunks = []
        current_chunk = []
        current_tokens = 0
        current_speaker = None

        for segment in segments:
            segment_tokens = self.count_tokens(segment['text'])

            # Start new chunk on speaker change
            if segment['speaker'] != current_speaker and current_tokens > self.min_tokens:
                if current_chunk:
                    chunks.append(self.finalize_chunk(current_chunk))
                    current_chunk = []
                    current_tokens = 0

            # Add segment to current chunk
            current_chunk.append(segment)
            current_tokens += segment_tokens
            current_speaker = segment['speaker']

            # Finalize chunk if exceeds max tokens
            if current_tokens >= self.max_tokens:
                chunks.append(self.finalize_chunk(current_chunk))
                current_chunk = []
                current_tokens = 0
                current_speaker = None

        # Finalize remaining chunk
        if current_chunk:
            chunks.append(self.finalize_chunk(current_chunk))

        return chunks

    def parse_transcript(self, text: str) -> List[Dict]:
        """Parse VTT or plain text into segments with speakers and timestamps"""

        if self.is_vtt_format(text):
            return self.parse_vtt(text)
        else:
            return self.parse_plain_text(text)

    def parse_vtt(self, vtt_text: str) -> List[Dict]:
        """
        Parse WebVTT format:

        WEBVTT

        00:00:00.000 --> 00:00:05.000
        [Speaker Name]: Hello everyone...
        """

        segments = []
        lines = vtt_text.split('\n')

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            # Match timestamp line
            if '-->' in line:
                timestamp_match = re.match(
                    r'(\d{2}:\d{2}:\d{2}\.\d{3}) --> (\d{2}:\d{2}:\d{2}\.\d{3})',
                    line
                )

                if timestamp_match:
                    start_time = self.parse_timestamp(timestamp_match.group(1))
                    end_time = self.parse_timestamp(timestamp_match.group(2))

                    # Next line is the text
                    i += 1
                    if i < len(lines):
                        text_line = lines[i].strip()

                        # Extract speaker
                        speaker_match = re.match(r'\[(.*?)\]:\s*(.*)', text_line)
                        if speaker_match:
                            speaker = speaker_match.group(1)
                            text = speaker_match.group(2)
                        else:
                            speaker = "Unknown"
                            text = text_line

                        segments.append({
                            'start_sec': start_time,
                            'end_sec': end_time,
                            'speaker': speaker,
                            'text': text
                        })

            i += 1

        return segments

    def parse_timestamp(self, timestamp: str) -> int:
        """Convert HH:MM:SS.mmm to seconds"""
        h, m, s = timestamp.split(':')
        s, ms = s.split('.')
        return int(h) * 3600 + int(m) * 60 + int(s)

    def count_tokens(self, text: str) -> int:
        """Count tokens using tiktoken"""
        return len(self.tokenizer.encode(text))

    def finalize_chunk(self, segments: List[Dict]) -> TranscriptChunk:
        """Combine segments into a single chunk with metadata"""

        text = ' '.join([s['text'] for s in segments])

        return TranscriptChunk(
            start_sec=segments[0]['start_sec'],
            end_sec=segments[-1]['end_sec'],
            speaker=segments[0]['speaker'],  # Primary speaker
            text=text,
            token_count=self.count_tokens(text),
            metadata={
                'speaker_changes': len(set(s['speaker'] for s in segments)),
                'segment_count': len(segments)
            }
        )
```

### Vector Embedding Pipeline

```python
class TranscriptEmbeddingService:
    """Generate and store vector embeddings for transcript chunks"""

    def __init__(self):
        self.openai_client = AsyncOpenAI()
        self.model = "text-embedding-ada-002"  # 1536 dimensions

    async def embed_transcript_chunks(
        self,
        transcript_id: uuid
    ):
        """
        Generate embeddings for all chunks of a transcript

        Batch processing for efficiency (up to 100 chunks at once)
        """

        # Fetch chunks
        chunks = await db.fetch(
            """
            SELECT id, text
            FROM meetings.transcript_chunks
            WHERE transcript_id = $1
              AND embedding IS NULL
            ORDER BY chunk_index
            """,
            transcript_id
        )

        if not chunks:
            return

        # Batch embed (OpenAI allows up to 2048 texts per request)
        batch_size = 100
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i+batch_size]

            # Generate embeddings
            response = await self.openai_client.embeddings.create(
                model=self.model,
                input=[chunk['text'] for chunk in batch]
            )

            # Store embeddings
            for j, embedding_obj in enumerate(response.data):
                chunk_id = batch[j]['id']
                embedding = embedding_obj.embedding

                await db.execute(
                    """
                    UPDATE meetings.transcript_chunks
                    SET embedding = $1
                    WHERE id = $2
                    """,
                    embedding,
                    chunk_id
                )

        logger.info(f"Generated embeddings for {len(chunks)} chunks")
```

---

## Summarization Pipeline

### LangChain Multi-Stage Architecture

```python
from langchain.chains import (
    LLMChain,
    MapReduceDocumentsChain,
    ReduceDocumentsChain,
    StuffDocumentsChain
)
from langchain.prompts import PromptTemplate
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import ChatOpenAI

class MeetingSummarizationPipeline:
    """
    Multi-stage meeting summarization using LangChain

    Stages:
    1. Extractive Summary: Extract key points from chunks
    2. Abstractive Summary: Generate narrative summary
    3. Action Item Extraction: Identify actionable items
    4. Decision Tracking: Detect decisions made
    5. Follow-up Identification: Extract next steps
    """

    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-4-turbo-preview",
            temperature=0.3  # Lower temp for factual accuracy
        )

        self.fast_llm = ChatOpenAI(
            model="gpt-3.5-turbo",
            temperature=0.3
        )

    async def summarize_meeting(
        self,
        transcript_id: uuid
    ) -> MeetingSummary:
        """
        Complete summarization pipeline for a meeting transcript

        Returns:
            MeetingSummary with:
            - tldr (1-2 sentences)
            - key_points (bullet list)
            - narrative_summary (2-3 paragraphs)
            - action_items (classified)
            - decisions (tracked)
            - follow_ups (next steps)
        """

        # 1. Fetch transcript and chunks
        transcript, chunks = await self.fetch_transcript_data(transcript_id)

        # 2. Stage 1: Extractive Summary
        key_points = await self.extract_key_points(chunks)

        # 3. Stage 2: Abstractive Summary
        narrative = await self.generate_narrative_summary(
            transcript, key_points
        )

        # 4. Stage 3: Action Item Extraction
        action_items = await self.extract_action_items(chunks)

        # 5. Stage 4: Decision Tracking
        decisions = await self.extract_decisions(chunks)

        # 6. Stage 5: Follow-up Identification
        follow_ups = await self.extract_follow_ups(chunks)

        # 7. Generate TLDR
        tldr = await self.generate_tldr(narrative, key_points)

        # 8. Store summary
        summary = MeetingSummary(
            transcript_id=transcript_id,
            tldr=tldr,
            key_points=key_points,
            narrative=narrative,
            action_items=action_items,
            decisions=decisions,
            follow_ups=follow_ups
        )

        await self.store_summary(summary)

        return summary

    async def extract_key_points(
        self,
        chunks: List[TranscriptChunk]
    ) -> List[str]:
        """
        Stage 1: Extract key points from each chunk using Map-Reduce

        Map: Extract 2-3 key points per chunk
        Reduce: Consolidate into top 10 overall key points
        """

        # Map: Extract key points from each chunk
        map_prompt = PromptTemplate(
            input_variables=["text"],
            template="""
Extract 2-3 key points from this meeting segment. Focus on:
- Important decisions or conclusions
- Action items or commitments
- Key information shared
- Questions raised

Meeting Segment:
{text}

Key Points (bullet format):
"""
        )

        map_chain = LLMChain(llm=self.fast_llm, prompt=map_prompt)

        chunk_summaries = []
        for chunk in chunks:
            result = await map_chain.arun(text=chunk.text)
            chunk_summaries.append(result)

        # Reduce: Consolidate into top points
        reduce_prompt = PromptTemplate(
            input_variables=["summaries"],
            template="""
You are given key points extracted from different parts of a meeting.
Consolidate these into the top 10 most important points for the meeting.
Remove duplicates and organize by importance.

Extracted Points:
{summaries}

Top 10 Key Points:
"""
        )

        reduce_chain = LLMChain(llm=self.llm, prompt=reduce_prompt)

        key_points_text = await reduce_chain.arun(
            summaries='\n\n'.join(chunk_summaries)
        )

        # Parse bullet points
        key_points = [
            point.strip('- ').strip()
            for point in key_points_text.split('\n')
            if point.strip().startswith('-')
        ]

        return key_points[:10]

    async def generate_narrative_summary(
        self,
        transcript: Dict,
        key_points: List[str]
    ) -> str:
        """
        Stage 2: Generate narrative summary from key points

        Creates a 2-3 paragraph human-readable summary
        """

        prompt = PromptTemplate(
            input_variables=["title", "key_points", "participants"],
            template="""
Generate a concise 2-3 paragraph summary of this meeting.

Meeting Title: {title}
Participants: {participants}

Key Points Discussed:
{key_points}

Write a narrative summary that:
1. Opens with the meeting's main purpose
2. Covers the key discussion points naturally
3. Ends with outcomes and next steps
4. Uses professional but accessible language

Summary:
"""
        )

        chain = LLMChain(llm=self.llm, prompt=prompt)

        narrative = await chain.arun(
            title=transcript['title'],
            key_points='\n'.join(f"- {kp}" for kp in key_points),
            participants=', '.join(transcript.get('participants', []))
        )

        return narrative.strip()

    async def extract_action_items(
        self,
        chunks: List[TranscriptChunk]
    ) -> List[ActionItem]:
        """
        Stage 3: Extract and classify action items

        Uses ML classification to:
        - Detect actionable statements
        - Extract assignee mentions
        - Infer due dates
        - Assign confidence scores
        """

        prompt = PromptTemplate(
            input_variables=["text"],
            template="""
Extract action items from this meeting segment.

For each action item, identify:
- The task/action to be done
- Who should do it (if mentioned)
- When it should be done (if mentioned)
- Why it's important (context)

Meeting Segment:
{text}

Action Items (JSON format):
[
  {{
    "action": "...",
    "assignee": "...",
    "due_date": "...",
    "priority": "high/normal/low",
    "context": "..."
  }}
]

If no action items, return empty array [].
"""
        )

        chain = LLMChain(llm=self.llm, prompt=prompt)

        all_action_items = []

        for chunk in chunks:
            result = await chain.arun(text=chunk.text)

            try:
                items = json.loads(result)
                for item in items:
                    action_item = ActionItem(
                        action=item['action'],
                        assignee=item.get('assignee'),
                        due_date_text=item.get('due_date'),
                        priority=item.get('priority', 'normal'),
                        context=item.get('context', ''),
                        source_chunk_id=chunk.id,
                        confidence=self.calculate_confidence(item)
                    )
                    all_action_items.append(action_item)

            except json.JSONDecodeError:
                logger.warning(f"Failed to parse action items from chunk {chunk.id}")

        # Deduplicate similar action items
        action_items = self.deduplicate_action_items(all_action_items)

        return action_items

    def calculate_confidence(self, action_item: Dict) -> float:
        """
        Calculate confidence score for action item

        Factors:
        - Has explicit assignee: +0.3
        - Has due date: +0.2
        - Contains action verbs: +0.2
        - Specific (not vague): +0.3
        """

        score = 0.0

        # Has assignee
        if action_item.get('assignee'):
            score += 0.3

        # Has due date
        if action_item.get('due_date'):
            score += 0.2

        # Contains strong action verbs
        action_text = action_item['action'].lower()
        strong_verbs = [
            'will', 'need to', 'should', 'must', 'going to',
            'schedule', 'send', 'create', 'update', 'complete'
        ]
        if any(verb in action_text for verb in strong_verbs):
            score += 0.2

        # Specific (not vague)
        vague_words = ['something', 'maybe', 'possibly', 'think about']
        if not any(word in action_text for word in vague_words):
            score += 0.3

        return min(1.0, score)

    async def extract_decisions(
        self,
        chunks: List[TranscriptChunk]
    ) -> List[Decision]:
        """
        Stage 4: Extract explicit decisions made during meeting

        Detects:
        - "We decided to..."
        - "The conclusion is..."
        - "We're going with..."
        """

        prompt = PromptTemplate(
            input_variables=["text"],
            template="""
Extract any explicit decisions made in this meeting segment.

A decision is:
- An explicit choice between options
- A conclusion reached
- A direction chosen

Meeting Segment:
{text}

Decisions (JSON format):
[
  {{
    "decision": "What was decided",
    "rationale": "Why this decision was made",
    "alternatives": ["Other options considered"],
    "decided_by": "Person who made decision"
  }}
]

If no decisions, return [].
"""
        )

        chain = LLMChain(llm=self.llm, prompt=prompt)

        decisions = []

        for chunk in chunks:
            result = await chain.arun(text=chunk.text)

            try:
                chunk_decisions = json.loads(result)
                for d in chunk_decisions:
                    decision = Decision(
                        decision=d['decision'],
                        rationale=d.get('rationale', ''),
                        alternatives=d.get('alternatives', []),
                        decided_by=d.get('decided_by'),
                        source_chunk_id=chunk.id
                    )
                    decisions.append(decision)

            except json.JSONDecodeError:
                pass

        return decisions

    async def extract_follow_ups(
        self,
        chunks: List[TranscriptChunk]
    ) -> List[FollowUp]:
        """
        Stage 5: Extract follow-up items and next steps

        Different from action items:
        - Future meetings to schedule
        - Information to gather
        - People to contact
        - Questions to answer
        """

        prompt = PromptTemplate(
            input_variables=["text"],
            template="""
Extract follow-up items from this meeting segment.

Follow-ups include:
- Future meetings to schedule
- Information someone needs to gather
- People to contact or loop in
- Questions that need answers
- Updates to be shared

Meeting Segment:
{text}

Follow-ups (JSON format):
[
  {{
    "type": "meeting/info/contact/question",
    "description": "...",
    "owner": "..."
  }}
]

If no follow-ups, return [].
"""
        )

        chain = LLMChain(llm=self.fast_llm, prompt=prompt)

        follow_ups = []

        for chunk in chunks:
            result = await chain.arun(text=chunk.text)

            try:
                chunk_follow_ups = json.loads(result)
                for f in chunk_follow_ups:
                    follow_up = FollowUp(
                        type=f['type'],
                        description=f['description'],
                        owner=f.get('owner'),
                        source_chunk_id=chunk.id
                    )
                    follow_ups.append(follow_up)

            except json.JSONDecodeError:
                pass

        return follow_ups

    async def generate_tldr(
        self,
        narrative: str,
        key_points: List[str]
    ) -> str:
        """Generate 1-2 sentence TLDR"""

        prompt = PromptTemplate(
            input_variables=["narrative", "key_points"],
            template="""
Generate a 1-2 sentence TLDR (Too Long; Didn't Read) summary.

Full Summary:
{narrative}

Key Points:
{key_points}

TLDR (1-2 sentences):
"""
        )

        chain = LLMChain(llm=self.llm, prompt=prompt)

        tldr = await chain.arun(
            narrative=narrative,
            key_points='\n'.join(f"- {kp}" for kp in key_points)
        )

        return tldr.strip()
```

---

## Action Item Extraction

### ML-Based Classification

```python
class ActionItemClassifier:
    """
    Classify sentences as action items with confidence scoring

    Uses:
    - Pattern matching for explicit action phrases
    - ML model for implicit action detection
    - Temporal expression parsing for due dates
    - Named entity recognition for assignees
    """

    def __init__(self):
        self.action_patterns = [
            r'\b(will|need to|should|must|have to)\b',
            r'\b(going to|planning to)\b',
            r'\b(task|todo|action item)\b',
            r'\b(deadline|due|by)\b',
            r'\b(assign|responsible|owner)\b'
        ]

        self.temporal_parser = self.init_temporal_parser()
        self.ner_model = self.init_ner_model()

    async def classify_action_item(
        self,
        text: str,
        context: Dict
    ) -> Optional[ClassifiedActionItem]:
        """
        Classify text as action item with extracted metadata

        Returns None if confidence < 0.7
        """

        # Pattern-based scoring
        pattern_score = self.calculate_pattern_score(text)

        # ML-based scoring (can use a fine-tuned BERT classifier)
        ml_score = await self.ml_classify(text)

        # Combined confidence
        confidence = (pattern_score + ml_score) / 2

        if confidence < 0.7:
            return None

        # Extract metadata
        assignee = self.extract_assignee(text, context)
        due_date = self.extract_due_date(text)
        priority = self.infer_priority(text)

        return ClassifiedActionItem(
            action=text,
            confidence=confidence,
            assignee=assignee,
            due_date=due_date,
            priority=priority,
            classification_method='hybrid'
        )

    def calculate_pattern_score(self, text: str) -> float:
        """Score based on action phrase patterns"""

        matches = 0
        for pattern in self.action_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                matches += 1

        # Normalize to 0-1
        return min(1.0, matches / 3)

    async def ml_classify(self, text: str) -> float:
        """ML-based classification score"""

        # Placeholder for ML model
        # In production, use fine-tuned BERT or similar
        return 0.8  # Simplified

    def extract_assignee(
        self,
        text: str,
        context: Dict
    ) -> Optional[str]:
        """
        Extract assignee from action text

        Strategies:
        1. Explicit mention: "John will..."
        2. Tag pattern: "@john should..."
        3. Possessive: "John's task is to..."
        4. Context-based: "He will..." (resolve pronoun)
        """

        # Strategy 1: Explicit mention with action verb
        name_action_pattern = r'(\b[A-Z][a-z]+\b)\s+(will|should|needs? to)'
        match = re.search(name_action_pattern, text)
        if match:
            return match.group(1)

        # Strategy 2: Tag pattern
        tag_pattern = r'@(\w+)'
        match = re.search(tag_pattern, text)
        if match:
            return match.group(1)

        # Strategy 3: Possessive
        possessive_pattern = r"(\b[A-Z][a-z]+)'s\s+(task|responsibility)"
        match = re.search(possessive_pattern, text)
        if match:
            return match.group(1)

        # Strategy 4: Use NER
        entities = self.ner_model.extract_persons(text)
        if entities:
            return entities[0]

        return None

    def extract_due_date(self, text: str) -> Optional[datetime]:
        """
        Extract due date from temporal expressions

        Examples:
        - "by Friday" → next Friday
        - "tomorrow" → tomorrow's date
        - "end of week" → coming Sunday
        - "in 3 days" → 3 days from now
        """

        # Use dateparser library
        import dateparser

        # Extract temporal phrases
        temporal_patterns = [
            r'\bby\s+([^\.,]+)',
            r'\bdue\s+([^\.,]+)',
            r'\buntil\s+([^\.,]+)',
            r'\bin\s+(\d+\s+(?:days?|weeks?|months?))',
            r'\b(tomorrow|today|monday|tuesday|wednesday|thursday|friday)',
        ]

        for pattern in temporal_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                date_text = match.group(1)
                parsed_date = dateparser.parse(
                    date_text,
                    settings={'PREFER_DATES_FROM': 'future'}
                )
                if parsed_date:
                    return parsed_date

        return None

    def infer_priority(self, text: str) -> str:
        """
        Infer priority from keywords

        urgent: ASAP, urgent, critical, immediately
        high: important, priority, soon
        normal: default
        low: eventually, someday, nice to have
        """

        text_lower = text.lower()

        if any(word in text_lower for word in ['asap', 'urgent', 'critical', 'immediately', 'emergency']):
            return 'urgent'

        if any(word in text_lower for word in ['important', 'priority', 'soon', 'quickly']):
            return 'high'

        if any(word in text_lower for word in ['eventually', 'someday', 'nice to have', 'optional']):
            return 'low'

        return 'normal'
```

---

## Task Routing Engine

### Automatic Monday.com Task Creation

```python
class TaskRoutingEngine:
    """
    Route action items from meetings to Monday.com

    Decision Logic:
    1. Filter action items by confidence (>0.8)
    2. Enrich with metadata (assignee, due date, priority)
    3. Map to appropriate Monday board/column
    4. Create task via Monday GraphQL API
    5. Link task back to source meeting
    6. Send notifications
    """

    def __init__(self):
        self.monday_client = MondayClient()
        self.confidence_threshold = 0.8

    async def route_action_items(
        self,
        meeting_summary: MeetingSummary,
        workspace_id: uuid
    ):
        """
        Route all action items from meeting to Monday.com

        Returns: List of created task IDs
        """

        # Filter high-confidence action items
        action_items = [
            item for item in meeting_summary.action_items
            if item.confidence >= self.confidence_threshold
        ]

        if not action_items:
            logger.info(f"No high-confidence action items for meeting {meeting_summary.transcript_id}")
            return []

        # Get Monday integration
        integration = await self.get_monday_integration(workspace_id)
        if not integration:
            logger.warning(f"No Monday integration for workspace {workspace_id}")
            return []

        # Create tasks
        created_tasks = []

        for action_item in action_items:
            try:
                task_id = await self.create_monday_task(
                    action_item=action_item,
                    meeting_summary=meeting_summary,
                    integration=integration
                )

                created_tasks.append(task_id)

                # Send notification to assignee
                if action_item.assignee:
                    await self.notify_assignee(
                        assignee=action_item.assignee,
                        task_id=task_id,
                        action_item=action_item,
                        workspace_id=workspace_id
                    )

            except Exception as e:
                logger.error(
                    f"Failed to create Monday task for action item: {e}",
                    exc_info=True
                )

        logger.info(f"Created {len(created_tasks)} Monday tasks from meeting")

        return created_tasks

    async def create_monday_task(
        self,
        action_item: ActionItem,
        meeting_summary: MeetingSummary,
        integration: Dict
    ) -> uuid:
        """
        Create task in Monday.com and local database

        Steps:
        1. Determine board and column placement
        2. Create task via Monday GraphQL API
        3. Store in local work.tasks
        4. Create task link in work.task_links
        """

        # Decrypt Monday credentials
        credentials = decrypt_credentials(integration['credentials_enc'])

        # Determine board placement
        board_config = await self.determine_board_placement(
            action_item=action_item,
            workspace_id=integration['workspace_id']
        )

        # Prepare Monday task data
        monday_data = {
            'board_id': board_config['board_id'],
            'group_id': board_config['group_id'],
            'item_name': action_item.action,
            'column_values': self.build_column_values(
                action_item=action_item,
                board_config=board_config
            )
        }

        # Create in Monday via GraphQL
        monday_item = await self.monday_client.create_item(
            api_key=credentials['api_key'],
            data=monday_data
        )

        # Store locally
        task_id = await db.fetchval(
            """
            INSERT INTO work.tasks (
                workspace_id,
                founder_id,
                title,
                description,
                platform,
                priority,
                status,
                due_date,
                assignee,
                source_ref,
                metadata
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            RETURNING id
            """,
            integration['workspace_id'],
            integration['founder_id'],
            action_item.action,
            action_item.context,
            'monday',
            action_item.priority,
            'todo',
            action_item.due_date,
            action_item.assignee,
            json.dumps({
                'type': 'meeting',
                'transcript_id': str(meeting_summary.transcript_id)
            }),
            json.dumps({
                'confidence': action_item.confidence,
                'chunk_id': str(action_item.source_chunk_id)
            })
        )

        # Create task link
        await db.execute(
            """
            INSERT INTO work.task_links (
                task_id,
                platform,
                external_id,
                url,
                sync_status,
                last_synced
            ) VALUES ($1, $2, $3, $4, $5, now())
            """,
            task_id,
            'monday',
            monday_item['id'],
            monday_item['url'],
            'synced'
        )

        logger.info(f"Created Monday task {monday_item['id']} for action item")

        return task_id

    async def determine_board_placement(
        self,
        action_item: ActionItem,
        workspace_id: uuid
    ) -> Dict:
        """
        Determine which Monday board and group to place task

        Strategy:
        1. Check workspace preferences for board mapping
        2. Use priority-based default boards
        3. Fallback to "Action Items" board
        """

        # Get workspace Monday configuration
        config = await db.fetchrow(
            """
            SELECT metadata
            FROM core.integrations
            WHERE workspace_id = $1
              AND platform = 'monday'
              AND status = 'connected'
            LIMIT 1
            """,
            workspace_id
        )

        monday_config = config['metadata'].get('board_config', {})

        # Priority-based board selection
        if action_item.priority == 'urgent':
            board_id = monday_config.get('urgent_board_id', monday_config.get('default_board_id'))
            group_id = 'urgent'
        elif action_item.priority == 'high':
            board_id = monday_config.get('high_priority_board_id', monday_config.get('default_board_id'))
            group_id = 'high_priority'
        else:
            board_id = monday_config.get('default_board_id')
            group_id = 'new_group'

        return {
            'board_id': board_id,
            'group_id': group_id,
            'column_mapping': monday_config.get('column_mapping', {})
        }

    def build_column_values(
        self,
        action_item: ActionItem,
        board_config: Dict
    ) -> Dict:
        """
        Build Monday column values from action item

        Maps to standard Monday columns:
        - status: Status
        - person: Person
        - date: Due Date
        - text: Priority
        """

        column_mapping = board_config.get('column_mapping', {})

        column_values = {}

        # Status
        if 'status' in column_mapping:
            column_values[column_mapping['status']] = {
                'label': 'To Do'
            }

        # Assignee
        if action_item.assignee and 'person' in column_mapping:
            # Resolve person ID from name
            person_id = self.resolve_monday_person(
                action_item.assignee,
                board_config['board_id']
            )
            if person_id:
                column_values[column_mapping['person']] = {
                    'personsAndTeams': [{'id': person_id, 'kind': 'person'}]
                }

        # Due Date
        if action_item.due_date and 'date' in column_mapping:
            column_values[column_mapping['date']] = {
                'date': action_item.due_date.strftime('%Y-%m-%d')
            }

        # Priority
        if 'priority' in column_mapping:
            priority_map = {
                'urgent': 'Critical',
                'high': 'High',
                'normal': 'Medium',
                'low': 'Low'
            }
            column_values[column_mapping['priority']] = {
                'label': priority_map.get(action_item.priority, 'Medium')
            }

        return json.dumps(column_values)

    async def notify_assignee(
        self,
        assignee: str,
        task_id: uuid,
        action_item: ActionItem,
        workspace_id: uuid
    ):
        """
        Send notification to assignee about new task

        Channels:
        1. Slack DM (if Slack integration active)
        2. Email (fallback)
        """

        # Try Slack first
        slack_sent = await self.send_slack_notification(
            assignee=assignee,
            task_id=task_id,
            action_item=action_item,
            workspace_id=workspace_id
        )

        if not slack_sent:
            # Fallback to email
            await self.send_email_notification(
                assignee=assignee,
                task_id=task_id,
                action_item=action_item,
                workspace_id=workspace_id
            )
```

---

## Performance Requirements

### Latency Targets

| Operation | Target | Max Acceptable |
|-----------|--------|----------------|
| **Webhook Receipt** | <100ms | 5s (platform timeout) |
| **Transcript Ingestion** | <30s | 2 min |
| **Transcript Chunking** | <10s per 1hr meeting | 30s |
| **Vector Embedding** | <5s per 100 chunks | 20s |
| **Summary Generation** | <90s per 1hr meeting | 5 min |
| **Action Extraction** | <30s per meeting | 2 min |
| **Task Creation** | <10s per task | 30s |
| **End-to-End Pipeline** | <3 min post-meeting | 10 min |

### Throughput Requirements

- **Concurrent Meetings**: Handle 50 concurrent meeting ingestions
- **Daily Volume**: Process 500+ meetings per day
- **Peak Load**: 100 meetings within 1 hour (post-workday spike)
- **API Rate Limits**:
  - OpenAI: 3,500 RPM (tokens per minute)
  - Monday.com: 60 requests/minute per user
  - Zoom: 100 requests/minute

### Scaling Strategy

```python
# Celery task queue for async processing
from celery import Celery

celery_app = Celery('meeting_intelligence')

@celery_app.task(bind=True, max_retries=3)
async def process_transcript_pipeline(
    self,
    transcript_id: uuid
):
    """
    Async pipeline for transcript processing

    Steps executed sequentially:
    1. Chunk transcript
    2. Generate embeddings
    3. Summarize meeting
    4. Extract action items
    5. Route to Monday

    Each step can retry independently
    """

    try:
        # Step 1: Chunking
        await chunk_transcript(transcript_id)

        # Step 2: Embeddings
        await generate_embeddings(transcript_id)

        # Step 3: Summarization
        summary = await summarize_meeting(transcript_id)

        # Step 4: Task Routing
        await route_action_items(summary)

        logger.info(f"Completed pipeline for transcript {transcript_id}")

    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=2 ** self.request.retries)
```

---

## Data Flow Diagrams

### End-to-End Flow

```
1. MEETING OCCURS
   │
   ▼
2. RECORDING COMPLETED (Zoom/Fireflies/Otter)
   │
   ▼
3. WEBHOOK/POLL → FastAPI Ingestion Handler
   │
   ├─ Verify signature
   ├─ Extract metadata
   └─ Queue job → Celery
   │
   ▼
4. BACKGROUND WORKER: Download Transcript
   │
   ├─ Fetch VTT/SRT file
   ├─ Parse speakers & timestamps
   └─ Store in meetings.transcripts
   │
   ▼
5. CHECK DUPLICATES
   │
   ├─ Find similar transcripts (time + title)
   └─ Merge if duplicate (score > 0.90)
   │
   ▼
6. CHUNK TRANSCRIPT
   │
   ├─ Semantic chunking (500-1000 tokens)
   ├─ Speaker diarization
   └─ Store in meetings.transcript_chunks
   │
   ▼
7. GENERATE EMBEDDINGS
   │
   ├─ OpenAI ada-002 (1536-dim)
   ├─ Batch process (100 chunks at once)
   └─ Update transcript_chunks.embedding
   │
   ▼
8. AI SUMMARIZATION (LangChain)
   │
   ├─ Stage 1: Extract key points (Map-Reduce)
   ├─ Stage 2: Generate narrative summary
   ├─ Stage 3: Extract action items (ML classification)
   ├─ Stage 4: Identify decisions
   ├─ Stage 5: Extract follow-ups
   └─ Store in meetings.transcripts.summary
   │
   ▼
9. TASK ROUTING
   │
   ├─ Filter action items (confidence > 0.8)
   ├─ Enrich metadata (assignee, due date, priority)
   ├─ Create Monday.com tasks (GraphQL)
   ├─ Store in work.tasks + work.task_links
   └─ Send notifications (Slack/Email)
   │
   ▼
10. BRIEFING INTEGRATION
    │
    ├─ Include in Morning Brief
    ├─ Add to Evening Wrap
    └─ Surface in unified dashboard
```

---

## API Specifications

### Webhook Endpoints

#### POST /webhooks/zoom/recording-completed

**Request:**
```json
{
  "event": "recording.completed",
  "payload": {
    "object": {
      "id": "1234567890",
      "topic": "Q4 Planning Meeting",
      "start_time": "2025-10-30T14:00:00Z",
      "duration": 3600,
      "host_email": "founder@startup.com",
      "recording_files": [
        {
          "file_type": "MP4",
          "download_url": "https://zoom.us/rec/download/..."
        },
        {
          "file_type": "TRANSCRIPT",
          "download_url": "https://zoom.us/rec/download/transcript.vtt"
        }
      ]
    }
  }
}
```

**Response:**
```json
{
  "status": "accepted",
  "meeting_id": "1234567890",
  "transcript_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

#### POST /webhooks/fireflies/transcript-ready

**Request:**
```json
{
  "event_type": "transcript.ready",
  "transcript_id": "abc123",
  "meeting": {
    "title": "Product Roadmap Discussion",
    "date": "2025-10-30T10:00:00Z",
    "duration": 2700,
    "participants": ["John", "Jane", "Bob"]
  },
  "transcript_url": "https://fireflies.ai/view/abc123"
}
```

**Response:**
```json
{
  "status": "accepted",
  "transcript_id": "660e8400-e29b-41d4-a716-446655440001"
}
```

### REST API Endpoints

#### POST /meetings/ingest

Manually trigger meeting ingestion (for retroactive sync).

**Request:**
```json
{
  "platform": "zoom",
  "meeting_id": "1234567890",
  "workspace_id": "770e8400-e29b-41d4-a716-446655440002"
}
```

**Response:**
```json
{
  "status": "queued",
  "job_id": "880e8400-e29b-41d4-a716-446655440003",
  "estimated_completion": "2025-10-30T14:05:00Z"
}
```

#### GET /meetings/{transcript_id}/summary

Retrieve meeting summary.

**Response:**
```json
{
  "transcript_id": "550e8400-e29b-41d4-a716-446655440000",
  "meeting_id": "1234567890",
  "title": "Q4 Planning Meeting",
  "recorded_at": "2025-10-30T14:00:00Z",
  "duration_mins": 60,
  "summary": {
    "tldr": "Team aligned on Q4 priorities: launch feature X by Nov 15, hire 2 engineers, and secure $2M funding.",
    "key_points": [
      "Feature X launch target: November 15",
      "Need to hire 2 senior engineers ASAP",
      "Fundraising goal: $2M by end of Q4"
    ],
    "narrative": "The team convened to finalize Q4 priorities...",
    "action_items": [
      {
        "action": "Schedule interviews for engineering candidates",
        "assignee": "Jane",
        "due_date": "2025-11-05",
        "priority": "high",
        "confidence": 0.92
      }
    ],
    "decisions": [
      {
        "decision": "Go-to-market strategy will focus on enterprise customers",
        "rationale": "Higher revenue per customer and better retention"
      }
    ],
    "follow_ups": [
      {
        "type": "meeting",
        "description": "Schedule investor pitch session with partner A",
        "owner": "John"
      }
    ]
  },
  "processed_at": "2025-10-30T14:03:12Z"
}
```

#### POST /meetings/{transcript_id}/reprocess

Reprocess meeting with updated AI models.

**Request:**
```json
{
  "stages": ["summarization", "action_extraction"]
}
```

**Response:**
```json
{
  "status": "queued",
  "job_id": "990e8400-e29b-41d4-a716-446655440004"
}
```

#### GET /meetings/search

Semantic search across all meeting transcripts.

**Query Parameters:**
- `q`: Search query
- `workspace_id`: Workspace UUID
- `date_from`: ISO date filter
- `date_to`: ISO date filter
- `limit`: Results limit (default: 10)

**Response:**
```json
{
  "results": [
    {
      "transcript_id": "550e8400-e29b-41d4-a716-446655440000",
      "title": "Q4 Planning Meeting",
      "recorded_at": "2025-10-30T14:00:00Z",
      "relevance_score": 0.89,
      "matching_chunks": [
        {
          "chunk_id": "aa0e8400-e29b-41d4-a716-446655440005",
          "text": "We need to prioritize feature X for Q4 launch...",
          "speaker": "Jane",
          "timestamp": "00:05:23"
        }
      ]
    }
  ],
  "total": 1
}
```

---

## Conclusion

This Meeting Intelligence architecture provides a comprehensive, scalable solution for automatically transforming meeting recordings into actionable insights. Key strengths:

1. **Multi-Source Reliability**: Ingests from 3 platforms with deduplication
2. **AI-Powered Summarization**: LangChain multi-stage pipeline ensures high-quality summaries
3. **Intelligent Task Routing**: ML-based classification with confidence scoring reduces false positives
4. **Performance Optimized**: Async processing with Celery ensures sub-5-minute end-to-end latency
5. **Production-Ready**: Comprehensive error handling, retry logic, and monitoring

### Next Steps

1. Implement database migration (004_meeting_intelligence.sql)
2. Build LLM integration layer
3. Develop webhook handlers
4. Create testing framework with sample transcripts
5. Deploy to staging environment

---

**Document Version:** 1.0
**Last Updated:** 2025-10-30
**Maintained By:** System Architect
