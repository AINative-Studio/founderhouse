"""
AI Chief of Staff - Meeting Test Fixtures
Sprint 3: Issue #7, #8, #9 - Meeting Intelligence Testing

Factory classes for:
- Meeting entities
- Transcripts and chunks
- Action items
- Decisions
- Summaries
- Task entities
"""

from datetime import datetime, timedelta
from typing import Optional, List
from uuid import uuid4

import factory
from faker import Faker

fake = Faker()


# ============================================================================
# MEETING FACTORIES
# ============================================================================

class MeetingFactory(factory.Factory):
    """Factory for generating meeting test data."""

    class Meta:
        model = dict

    id = factory.LazyFunction(lambda: str(uuid4()))
    workspace_id = factory.LazyFunction(lambda: str(uuid4()))
    founder_id = factory.LazyFunction(lambda: str(uuid4()))
    platform = factory.Iterator(["zoom", "outlook", "teams"])
    external_id = factory.LazyAttribute(lambda _: fake.uuid4())
    title = factory.LazyAttribute(lambda _: fake.sentence(nb_words=5))
    agenda = factory.LazyAttribute(lambda _: fake.paragraph(nb_sentences=3))
    start_time = factory.LazyFunction(
        lambda: (datetime.utcnow() - timedelta(hours=2)).isoformat()
    )
    end_time = factory.LazyFunction(
        lambda: (datetime.utcnow() - timedelta(hours=1)).isoformat()
    )
    duration_minutes = 60
    location_url = factory.LazyAttribute(lambda _: f"https://zoom.us/j/{fake.random_int(100000000, 999999999)}")
    participants = factory.LazyFunction(lambda: [
        {"name": fake.name(), "email": fake.email(), "role": "attendee"}
        for _ in range(fake.random_int(2, 6))
    ])
    recording_url = factory.LazyAttribute(lambda _: fake.url())
    summary = None
    action_items = factory.LazyFunction(lambda: [])
    decisions = factory.LazyFunction(lambda: [])
    created_at = factory.LazyFunction(lambda: datetime.utcnow().isoformat())
    updated_at = factory.LazyFunction(lambda: datetime.utcnow().isoformat())

    @classmethod
    def with_action_items(cls, num_items: int = 3, **kwargs):
        """Create meeting with predefined action items."""
        action_items = [
            ActionItemFactory()
            for _ in range(num_items)
        ]
        return cls(action_items=action_items, **kwargs)

    @classmethod
    def with_decisions(cls, num_decisions: int = 2, **kwargs):
        """Create meeting with predefined decisions."""
        decisions = [
            DecisionFactory()
            for _ in range(num_decisions)
        ]
        return cls(decisions=decisions, **kwargs)

    @classmethod
    def completed(cls, **kwargs):
        """Create a completed meeting with full metadata."""
        return cls(
            summary="Meeting summary generated",
            **kwargs
        )


class TranscriptFactory(factory.Factory):
    """Factory for generating transcript test data."""

    class Meta:
        model = dict

    id = factory.LazyFunction(lambda: str(uuid4()))
    workspace_id = factory.LazyFunction(lambda: str(uuid4()))
    founder_id = factory.LazyFunction(lambda: str(uuid4()))
    meeting_id = factory.LazyFunction(lambda: str(uuid4()))
    provider = factory.Iterator(["zoom", "fireflies", "otter"])
    title = factory.LazyAttribute(lambda _: fake.sentence(nb_words=5))
    url = factory.LazyAttribute(lambda _: fake.url())
    language = "en"
    duration_seconds = factory.LazyFunction(lambda: fake.random_int(300, 7200))
    word_count = factory.LazyFunction(lambda: fake.random_int(500, 5000))
    speaker_count = factory.LazyFunction(lambda: fake.random_int(2, 6))
    summary = None
    action_items = factory.LazyFunction(lambda: [])
    decisions = factory.LazyFunction(lambda: [])
    sentiment = None
    recorded_at = factory.LazyFunction(
        lambda: (datetime.utcnow() - timedelta(hours=3)).isoformat()
    )
    processed_at = None
    created_at = factory.LazyFunction(lambda: datetime.utcnow().isoformat())
    updated_at = factory.LazyFunction(lambda: datetime.utcnow().isoformat())

    @classmethod
    def from_zoom(cls, **kwargs):
        """Create Zoom transcript."""
        return cls(provider="zoom", **kwargs)

    @classmethod
    def from_fireflies(cls, **kwargs):
        """Create Fireflies transcript."""
        return cls(provider="fireflies", **kwargs)

    @classmethod
    def from_otter(cls, **kwargs):
        """Create Otter transcript."""
        return cls(provider="otter", **kwargs)

    @classmethod
    def processed(cls, **kwargs):
        """Create processed transcript with summary."""
        summary_data = SummaryFactory()
        return cls(
            summary=summary_data,
            processed_at=datetime.utcnow().isoformat(),
            **kwargs
        )


class TranscriptChunkFactory(factory.Factory):
    """Factory for generating transcript chunk test data."""

    class Meta:
        model = dict

    id = factory.LazyFunction(lambda: str(uuid4()))
    transcript_id = factory.LazyFunction(lambda: str(uuid4()))
    chunk_index = factory.Sequence(lambda n: n)
    start_sec = factory.LazyAttribute(lambda obj: obj.chunk_index * 60)
    end_sec = factory.LazyAttribute(lambda obj: (obj.chunk_index + 1) * 60)
    speaker = factory.LazyAttribute(lambda _: fake.name())
    speaker_id = factory.LazyFunction(lambda: str(uuid4()))
    text = factory.LazyAttribute(lambda _: fake.paragraph(nb_sentences=5))
    word_count = factory.LazyFunction(lambda: fake.random_int(50, 150))
    confidence = factory.LazyFunction(lambda: fake.pyfloat(min_value=0.7, max_value=1.0))
    embedding = None  # Will be set to actual embedding vector in tests
    metadata = factory.LazyFunction(lambda: {
        "language": "en",
        "detected_language_confidence": fake.pyfloat(min_value=0.9, max_value=1.0)
    })

    @classmethod
    def with_embedding(cls, **kwargs):
        """Create chunk with mock embedding vector."""
        import numpy as np
        embedding = np.random.rand(1536).tolist()
        return cls(embedding=embedding, **kwargs)


# ============================================================================
# ACTION ITEM FACTORIES
# ============================================================================

class ActionItemFactory(factory.Factory):
    """Factory for generating action item test data."""

    class Meta:
        model = dict

    id = factory.LazyFunction(lambda: str(uuid4()))
    task = factory.LazyAttribute(lambda _: fake.sentence(nb_words=8))
    description = factory.LazyAttribute(lambda _: fake.paragraph(nb_sentences=2))
    assignee = factory.LazyAttribute(lambda _: fake.name())
    assignee_email = factory.LazyAttribute(lambda _: fake.email())
    due_date = factory.LazyFunction(
        lambda: (datetime.utcnow() + timedelta(days=fake.random_int(1, 14))).isoformat()
    )
    priority = factory.Iterator(["urgent", "high", "normal", "low"])
    status = factory.Iterator(["pending", "in_progress", "completed", "blocked"])
    confidence = factory.LazyFunction(lambda: fake.pyfloat(min_value=0.6, max_value=1.0))
    source_chunk_id = factory.LazyFunction(lambda: str(uuid4()))
    source_timestamp = factory.LazyFunction(lambda: fake.random_int(0, 3600))
    metadata = factory.LazyFunction(lambda: {
        "extraction_method": "llm",
        "model": "gpt-4"
    })

    @classmethod
    def high_priority(cls, **kwargs):
        """Create high priority action item."""
        return cls(
            priority="high",
            due_date=(datetime.utcnow() + timedelta(days=3)).isoformat(),
            **kwargs
        )

    @classmethod
    def urgent(cls, **kwargs):
        """Create urgent action item."""
        return cls(
            priority="urgent",
            due_date=(datetime.utcnow() + timedelta(days=1)).isoformat(),
            **kwargs
        )

    @classmethod
    def with_assignee(cls, assignee_name: str, assignee_email: str, **kwargs):
        """Create action item with specific assignee."""
        return cls(
            assignee=assignee_name,
            assignee_email=assignee_email,
            **kwargs
        )


# ============================================================================
# DECISION FACTORIES
# ============================================================================

class DecisionFactory(factory.Factory):
    """Factory for generating decision test data."""

    class Meta:
        model = dict

    id = factory.LazyFunction(lambda: str(uuid4()))
    decision = factory.LazyAttribute(lambda _: fake.sentence(nb_words=10))
    context = factory.LazyAttribute(lambda _: fake.paragraph(nb_sentences=3))
    decision_maker = factory.LazyAttribute(lambda _: fake.name())
    decision_maker_email = factory.LazyAttribute(lambda _: fake.email())
    outcome = factory.Iterator(["approved", "rejected", "deferred", "needs_revision"])
    impact = factory.Iterator(["high", "medium", "low"])
    confidence = factory.LazyFunction(lambda: fake.pyfloat(min_value=0.7, max_value=1.0))
    source_chunk_id = factory.LazyFunction(lambda: str(uuid4()))
    source_timestamp = factory.LazyFunction(lambda: fake.random_int(0, 3600))
    stakeholders = factory.LazyFunction(lambda: [
        fake.name() for _ in range(fake.random_int(1, 4))
    ])
    metadata = factory.LazyFunction(lambda: {
        "extraction_method": "llm",
        "model": "gpt-4"
    })

    @classmethod
    def high_impact(cls, **kwargs):
        """Create high impact decision."""
        return cls(impact="high", **kwargs)

    @classmethod
    def approved(cls, **kwargs):
        """Create approved decision."""
        return cls(outcome="approved", **kwargs)


# ============================================================================
# SUMMARY FACTORIES
# ============================================================================

class SummaryFactory(factory.Factory):
    """Factory for generating summary test data."""

    class Meta:
        model = dict

    id = factory.LazyFunction(lambda: str(uuid4()))
    tl_dr = factory.LazyAttribute(lambda _: fake.paragraph(nb_sentences=2))
    key_points = factory.LazyFunction(lambda: [
        fake.sentence() for _ in range(fake.random_int(3, 6))
    ])
    topics = factory.LazyFunction(lambda: [
        fake.word() for _ in range(fake.random_int(2, 5))
    ])
    participants_summary = factory.LazyFunction(lambda: {
        fake.name(): {
            "speaking_time_seconds": fake.random_int(60, 600),
            "contribution_percentage": fake.pyfloat(min_value=10, max_value=40)
        }
        for _ in range(fake.random_int(2, 4))
    })
    sentiment = None
    generated_at = factory.LazyFunction(lambda: datetime.utcnow().isoformat())
    model_used = "gpt-4"
    token_count = factory.LazyFunction(lambda: fake.random_int(500, 2000))
    metadata = factory.LazyFunction(lambda: {
        "version": "1.0",
        "method": "extractive_abstractive"
    })

    @classmethod
    def with_sentiment(cls, **kwargs):
        """Create summary with sentiment analysis."""
        sentiment_data = SentimentFactory()
        return cls(sentiment=sentiment_data, **kwargs)


class SentimentFactory(factory.Factory):
    """Factory for generating sentiment analysis data."""

    class Meta:
        model = dict

    overall_score = factory.LazyFunction(lambda: fake.pyfloat(min_value=-1, max_value=1))
    overall_label = factory.Iterator(["positive", "neutral", "negative", "mixed"])
    confidence = factory.LazyFunction(lambda: fake.pyfloat(min_value=0.7, max_value=1.0))
    per_speaker = factory.LazyFunction(lambda: {
        fake.name(): {
            "score": fake.pyfloat(min_value=-1, max_value=1),
            "label": fake.random_element(["positive", "neutral", "negative"])
        }
        for _ in range(fake.random_int(2, 4))
    })
    trajectory = factory.LazyFunction(lambda: [
        {
            "timestamp": i * 300,
            "score": fake.pyfloat(min_value=-1, max_value=1)
        }
        for i in range(fake.random_int(4, 8))
    ])
    key_moments = factory.LazyFunction(lambda: [
        {
            "timestamp": fake.random_int(0, 3600),
            "type": fake.random_element(["peak_positive", "peak_negative", "shift"]),
            "description": fake.sentence()
        }
        for _ in range(fake.random_int(1, 3))
    ])

    @classmethod
    def positive(cls, **kwargs):
        """Create positive sentiment."""
        return cls(
            overall_score=fake.pyfloat(min_value=0.5, max_value=1.0),
            overall_label="positive",
            **kwargs
        )

    @classmethod
    def negative(cls, **kwargs):
        """Create negative sentiment."""
        return cls(
            overall_score=fake.pyfloat(min_value=-1.0, max_value=-0.5),
            overall_label="negative",
            **kwargs
        )


# ============================================================================
# TASK FACTORIES (for Task Routing)
# ============================================================================

class TaskFactory(factory.Factory):
    """Factory for generating task test data."""

    class Meta:
        model = dict

    id = factory.LazyFunction(lambda: str(uuid4()))
    workspace_id = factory.LazyFunction(lambda: str(uuid4()))
    founder_id = factory.LazyFunction(lambda: str(uuid4()))
    title = factory.LazyAttribute(lambda _: fake.sentence(nb_words=6))
    description = factory.LazyAttribute(lambda _: fake.paragraph(nb_sentences=2))
    platform = factory.Iterator(["monday", "notion", "linear"])
    external_id = factory.LazyAttribute(lambda _: fake.uuid4())
    priority = factory.Iterator(["urgent", "high", "normal", "low"])
    status = factory.Iterator(["todo", "in_progress", "blocked", "done", "canceled"])
    assignee = factory.LazyAttribute(lambda _: fake.name())
    assignee_email = factory.LazyAttribute(lambda _: fake.email())
    due_date = factory.LazyFunction(
        lambda: (datetime.utcnow() + timedelta(days=fake.random_int(1, 14))).isoformat()
    )
    source_type = factory.Iterator(["meeting", "communication", "manual"])
    source_id = factory.LazyFunction(lambda: str(uuid4()))
    action_item_id = None
    metadata = factory.LazyFunction(lambda: {
        "board_id": fake.uuid4(),
        "column_ids": {}
    })
    created_at = factory.LazyFunction(lambda: datetime.utcnow().isoformat())
    updated_at = factory.LazyFunction(lambda: datetime.utcnow().isoformat())

    @classmethod
    def from_action_item(cls, action_item: dict, **kwargs):
        """Create task from action item."""
        return cls(
            title=action_item["task"],
            description=action_item.get("description", ""),
            assignee=action_item.get("assignee"),
            assignee_email=action_item.get("assignee_email"),
            due_date=action_item.get("due_date"),
            priority=action_item.get("priority", "normal"),
            source_type="meeting",
            action_item_id=action_item["id"],
            **kwargs
        )

    @classmethod
    def from_meeting(cls, meeting_id: str, **kwargs):
        """Create task from meeting."""
        return cls(
            source_type="meeting",
            source_id=meeting_id,
            **kwargs
        )


# ============================================================================
# WEBHOOK EVENT FACTORIES
# ============================================================================

class WebhookEventFactory(factory.Factory):
    """Factory for generating webhook event test data."""

    class Meta:
        model = dict

    id = factory.LazyFunction(lambda: str(uuid4()))
    platform = factory.Iterator(["zoom", "fireflies", "otter"])
    event_type = factory.Iterator([
        "recording.completed",
        "transcript.completed",
        "meeting.started",
        "meeting.ended"
    ])
    external_id = factory.LazyAttribute(lambda _: fake.uuid4())
    payload = factory.LazyFunction(lambda: {
        "meeting_id": fake.uuid4(),
        "timestamp": datetime.utcnow().isoformat()
    })
    signature = factory.LazyAttribute(lambda _: fake.sha256())
    received_at = factory.LazyFunction(lambda: datetime.utcnow().isoformat())
    processed = False
    processed_at = None
    error_message = None

    @classmethod
    def zoom_recording_completed(cls, **kwargs):
        """Create Zoom recording completed event."""
        return cls(
            platform="zoom",
            event_type="recording.completed",
            payload={
                "event": "recording.completed",
                "payload": {
                    "object": {
                        "id": str(uuid4()),
                        "uuid": str(uuid4()),
                        "host_id": str(uuid4()),
                        "topic": fake.sentence(),
                        "start_time": datetime.utcnow().isoformat(),
                        "duration": 60,
                        "recording_files": [
                            {
                                "id": str(uuid4()),
                                "recording_type": "audio_transcript",
                                "download_url": fake.url()
                            }
                        ]
                    }
                }
            },
            **kwargs
        )

    @classmethod
    def fireflies_transcript_ready(cls, **kwargs):
        """Create Fireflies transcript ready event."""
        return cls(
            platform="fireflies",
            event_type="transcript.completed",
            payload={
                "event_type": "transcript_ready",
                "transcript_id": str(uuid4()),
                "meeting_id": str(uuid4()),
                "title": fake.sentence(),
                "date": datetime.utcnow().isoformat()
            },
            **kwargs
        )


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def create_meeting_with_transcript(
    provider: str = "zoom",
    num_chunks: int = 10,
    with_summary: bool = False,
    with_action_items: bool = False,
    with_decisions: bool = False
) -> dict:
    """
    Create a complete meeting with transcript and optional processing.

    Args:
        provider: Transcript provider (zoom, fireflies, otter)
        num_chunks: Number of transcript chunks
        with_summary: Include summary data
        with_action_items: Include action items
        with_decisions: Include decisions

    Returns:
        Dictionary with meeting, transcript, and chunks
    """
    meeting = MeetingFactory()

    transcript_kwargs = {
        "workspace_id": meeting["workspace_id"],
        "founder_id": meeting["founder_id"],
        "meeting_id": meeting["id"],
        "provider": provider
    }

    if with_summary:
        transcript_kwargs["summary"] = SummaryFactory.with_sentiment()
        transcript_kwargs["processed_at"] = datetime.utcnow().isoformat()

    if with_action_items:
        transcript_kwargs["action_items"] = [
            ActionItemFactory() for _ in range(3)
        ]

    if with_decisions:
        transcript_kwargs["decisions"] = [
            DecisionFactory() for _ in range(2)
        ]

    transcript = TranscriptFactory(**transcript_kwargs)

    chunks = [
        TranscriptChunkFactory(
            transcript_id=transcript["id"],
            chunk_index=i
        )
        for i in range(num_chunks)
    ]

    return {
        "meeting": meeting,
        "transcript": transcript,
        "chunks": chunks
    }


def create_meeting_from_multiple_sources() -> dict:
    """
    Create same meeting ingested from multiple sources (Zoom, Fireflies, Otter).

    Returns:
        Dictionary with meeting and multiple transcripts
    """
    meeting = MeetingFactory()

    zoom_transcript = TranscriptFactory.from_zoom(
        workspace_id=meeting["workspace_id"],
        founder_id=meeting["founder_id"],
        meeting_id=meeting["id"],
        external_id=meeting["external_id"]
    )

    fireflies_transcript = TranscriptFactory.from_fireflies(
        workspace_id=meeting["workspace_id"],
        founder_id=meeting["founder_id"],
        meeting_id=meeting["id"],
        external_id=meeting["external_id"]
    )

    otter_transcript = TranscriptFactory.from_otter(
        workspace_id=meeting["workspace_id"],
        founder_id=meeting["founder_id"],
        meeting_id=meeting["id"],
        external_id=meeting["external_id"]
    )

    return {
        "meeting": meeting,
        "transcripts": {
            "zoom": zoom_transcript,
            "fireflies": fireflies_transcript,
            "otter": otter_transcript
        }
    }


def create_meeting_with_tasks(num_action_items: int = 5) -> dict:
    """
    Create meeting with action items converted to tasks.

    Args:
        num_action_items: Number of action items to generate

    Returns:
        Dictionary with meeting, action items, and tasks
    """
    meeting = MeetingFactory()
    action_items = [ActionItemFactory() for _ in range(num_action_items)]
    tasks = [
        TaskFactory.from_action_item(item, source_id=meeting["id"])
        for item in action_items
    ]

    return {
        "meeting": meeting,
        "action_items": action_items,
        "tasks": tasks
    }
