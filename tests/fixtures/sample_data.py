"""
AI Chief of Staff - Test Data Factories
Sprint 1: Factory-based test data generation

This module provides factory classes for generating consistent test data
using Factory Boy and Faker.
"""

from datetime import datetime, timedelta
from typing import Any, Optional
from uuid import uuid4

import factory
from faker import Faker

fake = Faker()


# ============================================================================
# WORKSPACE FACTORIES
# ============================================================================

class WorkspaceFactory(factory.Factory):
    """Factory for generating workspace test data."""

    class Meta:
        model = dict

    id = factory.LazyFunction(lambda: str(uuid4()))
    name = factory.LazyAttribute(lambda _: fake.company())
    created_at = factory.LazyFunction(lambda: datetime.utcnow().isoformat())


class MemberFactory(factory.Factory):
    """Factory for generating member test data."""

    class Meta:
        model = dict

    id = factory.LazyFunction(lambda: str(uuid4()))
    workspace_id = factory.LazyFunction(lambda: str(uuid4()))
    user_id = factory.LazyFunction(lambda: str(uuid4()))
    role = factory.Iterator(["owner", "admin", "member", "viewer"])
    created_at = factory.LazyFunction(lambda: datetime.utcnow().isoformat())


class FounderFactory(factory.Factory):
    """Factory for generating founder test data."""

    class Meta:
        model = dict

    id = factory.LazyFunction(lambda: str(uuid4()))
    workspace_id = factory.LazyFunction(lambda: str(uuid4()))
    user_id = factory.LazyFunction(lambda: str(uuid4()))
    display_name = factory.LazyAttribute(lambda _: fake.name())
    email = factory.LazyAttribute(lambda _: fake.email())
    preferences = factory.LazyFunction(lambda: {
        "timezone": fake.timezone(),
        "language": "en",
        "notifications_enabled": True,
    })
    created_at = factory.LazyFunction(lambda: datetime.utcnow().isoformat())


# ============================================================================
# INTEGRATION FACTORIES
# ============================================================================

class IntegrationFactory(factory.Factory):
    """Factory for generating integration test data."""

    class Meta:
        model = dict

    id = factory.LazyFunction(lambda: str(uuid4()))
    workspace_id = factory.LazyFunction(lambda: str(uuid4()))
    founder_id = factory.LazyFunction(lambda: str(uuid4()))
    platform = factory.Iterator([
        "gmail", "outlook", "slack", "discord", "zoom",
        "loom", "fireflies", "otter", "monday", "notion", "granola"
    ])
    connection_type = factory.Iterator(["mcp", "api"])
    status = factory.Iterator(["connected", "error", "revoked", "pending"])
    credentials_enc = factory.LazyFunction(lambda: b"encrypted_mock_credentials")
    metadata = factory.LazyFunction(lambda: {
        "oauth_version": "2.0",
        "scopes": ["read", "write"],
        "last_sync": datetime.utcnow().isoformat(),
    })
    connected_at = factory.LazyFunction(lambda: datetime.utcnow().isoformat())
    updated_at = factory.LazyFunction(lambda: datetime.utcnow().isoformat())


# ============================================================================
# COMMUNICATION FACTORIES
# ============================================================================

class ThreadFactory(factory.Factory):
    """Factory for generating thread test data."""

    class Meta:
        model = dict

    id = factory.LazyFunction(lambda: str(uuid4()))
    workspace_id = factory.LazyFunction(lambda: str(uuid4()))
    founder_id = factory.LazyFunction(lambda: str(uuid4()))
    platform = factory.Iterator(["gmail", "outlook", "slack", "discord"])
    external_id = factory.LazyAttribute(lambda _: fake.uuid4())
    subject = factory.LazyAttribute(lambda _: fake.sentence())
    created_at = factory.LazyFunction(lambda: datetime.utcnow().isoformat())


class CommunicationFactory(factory.Factory):
    """Factory for generating communication test data."""

    class Meta:
        model = dict

    id = factory.LazyFunction(lambda: str(uuid4()))
    workspace_id = factory.LazyFunction(lambda: str(uuid4()))
    founder_id = factory.LazyFunction(lambda: str(uuid4()))
    thread_id = factory.LazyFunction(lambda: str(uuid4()))
    platform = factory.Iterator(["gmail", "outlook", "slack", "discord"])
    source = factory.Iterator(["email", "slack", "discord", "system"])
    sender = factory.LazyAttribute(lambda _: fake.email())
    recipients = factory.LazyFunction(lambda: [fake.email() for _ in range(2)])
    subject = factory.LazyAttribute(lambda _: fake.sentence())
    content = factory.LazyAttribute(lambda _: fake.paragraph(nb_sentences=5))
    snippet = factory.LazyAttribute(lambda _: fake.text(max_nb_chars=100))
    sentiment = factory.LazyFunction(lambda: {
        "score": fake.pyfloat(min_value=-1, max_value=1),
        "label": fake.random_element(["positive", "neutral", "negative"]),
    })
    urgency = factory.Iterator(["urgent", "high", "normal", "low"])
    followup_needed = factory.LazyFunction(lambda: fake.boolean())
    received_at = factory.LazyFunction(lambda: (datetime.utcnow() - timedelta(days=fake.random_int(0, 7))).isoformat())
    embedding = factory.LazyFunction(lambda: [fake.pyfloat(min_value=0, max_value=1) for _ in range(1536)])
    raw = factory.LazyFunction(lambda: {
        "message_id": fake.uuid4(),
        "headers": {},
    })
    created_at = factory.LazyFunction(lambda: datetime.utcnow().isoformat())


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
    platform = factory.Iterator(["zoom", "outlook"])
    external_id = factory.LazyAttribute(lambda _: fake.uuid4())
    title = factory.LazyAttribute(lambda _: fake.sentence())
    agenda = factory.LazyAttribute(lambda _: fake.paragraph())
    start_time = factory.LazyFunction(lambda: (datetime.utcnow() + timedelta(hours=fake.random_int(1, 24))).isoformat())
    end_time = factory.LazyFunction(lambda: (datetime.utcnow() + timedelta(hours=fake.random_int(25, 48))).isoformat())
    location_url = factory.LazyAttribute(lambda _: fake.url())
    summary = factory.LazyAttribute(lambda _: fake.paragraph())
    action_items = factory.LazyFunction(lambda: [
        {"task": fake.sentence(), "assignee": fake.name(), "due_date": fake.future_date().isoformat()}
        for _ in range(fake.random_int(1, 3))
    ])
    created_at = factory.LazyFunction(lambda: datetime.utcnow().isoformat())


class TranscriptFactory(factory.Factory):
    """Factory for generating transcript test data."""

    class Meta:
        model = dict

    id = factory.LazyFunction(lambda: str(uuid4()))
    workspace_id = factory.LazyFunction(lambda: str(uuid4()))
    founder_id = factory.LazyFunction(lambda: str(uuid4()))
    meeting_id = factory.LazyFunction(lambda: str(uuid4()))
    provider = factory.Iterator(["zoom", "fireflies", "otter"])
    title = factory.LazyAttribute(lambda _: fake.sentence())
    url = factory.LazyAttribute(lambda _: fake.url())
    language = "en"
    summary = factory.LazyFunction(lambda: {
        "tl_dr": fake.paragraph(),
        "key_points": [fake.sentence() for _ in range(3)],
        "decisions": [fake.sentence() for _ in range(2)],
    })
    action_items = factory.LazyFunction(lambda: [
        {"task": fake.sentence(), "assignee": fake.name()}
        for _ in range(fake.random_int(1, 4))
    ])
    recorded_at = factory.LazyFunction(lambda: (datetime.utcnow() - timedelta(days=fake.random_int(0, 7))).isoformat())
    created_at = factory.LazyFunction(lambda: datetime.utcnow().isoformat())


class TranscriptChunkFactory(factory.Factory):
    """Factory for generating transcript chunk test data."""

    class Meta:
        model = dict

    id = factory.LazyFunction(lambda: str(uuid4()))
    transcript_id = factory.LazyFunction(lambda: str(uuid4()))
    start_sec = factory.LazyFunction(lambda: fake.random_int(0, 3600))
    end_sec = factory.LazyFunction(lambda: fake.random_int(3601, 7200))
    speaker = factory.LazyAttribute(lambda _: fake.name())
    text = factory.LazyAttribute(lambda _: fake.paragraph(nb_sentences=3))
    embedding = factory.LazyFunction(lambda: [fake.pyfloat(min_value=0, max_value=1) for _ in range(1536)])


# ============================================================================
# TASK FACTORIES
# ============================================================================

class TaskFactory(factory.Factory):
    """Factory for generating task test data."""

    class Meta:
        model = dict

    id = factory.LazyFunction(lambda: str(uuid4()))
    workspace_id = factory.LazyFunction(lambda: str(uuid4()))
    founder_id = factory.LazyFunction(lambda: str(uuid4()))
    title = factory.LazyAttribute(lambda _: fake.sentence())
    description = factory.LazyAttribute(lambda _: fake.paragraph())
    platform = factory.Iterator(["monday", "notion"])
    priority = factory.Iterator(["urgent", "high", "normal", "low"])
    status = factory.Iterator(["todo", "in_progress", "blocked", "done", "canceled"])
    due_date = factory.LazyFunction(lambda: (datetime.utcnow() + timedelta(days=fake.random_int(1, 14))).isoformat())
    source_ref = factory.LazyFunction(lambda: {
        "entity": fake.random_element(["meeting", "communication", "media"]),
        "id": str(uuid4()),
    })
    created_at = factory.LazyFunction(lambda: datetime.utcnow().isoformat())
    updated_at = factory.LazyFunction(lambda: datetime.utcnow().isoformat())


# ============================================================================
# INSIGHT FACTORIES
# ============================================================================

class InsightFactory(factory.Factory):
    """Factory for generating insight test data."""

    class Meta:
        model = dict

    id = factory.LazyFunction(lambda: str(uuid4()))
    workspace_id = factory.LazyFunction(lambda: str(uuid4()))
    founder_id = factory.LazyFunction(lambda: str(uuid4()))
    source = factory.Iterator(["granola", "meetings", "loom", "slack", "discord"])
    insight_type = factory.Iterator(["kpi", "decision_hint", "recommendation", "risk", "anomaly"])
    content = factory.LazyFunction(lambda: {
        "title": fake.sentence(),
        "description": fake.paragraph(),
        "data": {
            "metric": fake.word(),
            "value": fake.pyfloat(min_value=0, max_value=1000),
            "trend": fake.random_element(["up", "down", "stable"]),
        },
    })
    confidence = factory.LazyFunction(lambda: fake.pyfloat(min_value=0.5, max_value=1.0))
    created_at = factory.LazyFunction(lambda: datetime.utcnow().isoformat())
    embedding = factory.LazyFunction(lambda: [fake.pyfloat(min_value=0, max_value=1) for _ in range(1536)])


# ============================================================================
# EVENT FACTORIES
# ============================================================================

class EventFactory(factory.Factory):
    """Factory for generating event test data."""

    class Meta:
        model = dict

    id = factory.LazyFunction(lambda: str(uuid4()))
    workspace_id = factory.LazyFunction(lambda: str(uuid4()))
    actor_type = factory.Iterator(["agent", "user", "system"])
    actor_id = factory.LazyFunction(lambda: str(uuid4()))
    event_type = factory.Iterator([
        "workspace.created",
        "integration.connected",
        "meeting.ingested",
        "task.created",
        "insight.generated",
        "briefing.generated",
    ])
    payload = factory.LazyFunction(lambda: {
        "action": fake.word(),
        "entity": fake.word(),
        "details": fake.pydict(),
    })
    linked_entity = factory.Iterator(["workspace", "integration", "meeting", "task", "insight"])
    linked_id = factory.LazyFunction(lambda: str(uuid4()))
    created_at = factory.LazyFunction(lambda: datetime.utcnow().isoformat())


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def create_test_workspace_with_members(num_members: int = 3) -> dict:
    """
    Create a complete test workspace with members and founder.
    Returns a dictionary with all related entities.
    """
    workspace = WorkspaceFactory()
    founder = FounderFactory(workspace_id=workspace["id"])
    members = [
        MemberFactory(workspace_id=workspace["id"])
        for _ in range(num_members)
    ]

    return {
        "workspace": workspace,
        "founder": founder,
        "members": members,
    }


def create_test_meeting_with_transcript() -> dict:
    """
    Create a complete test meeting with transcript and chunks.
    """
    meeting = MeetingFactory()
    transcript = TranscriptFactory(
        workspace_id=meeting["workspace_id"],
        founder_id=meeting["founder_id"],
        meeting_id=meeting["id"],
    )
    chunks = [
        TranscriptChunkFactory(transcript_id=transcript["id"])
        for _ in range(5)
    ]

    return {
        "meeting": meeting,
        "transcript": transcript,
        "chunks": chunks,
    }


def create_test_communication_thread(num_messages: int = 5) -> dict:
    """
    Create a complete test communication thread with messages.
    """
    thread = ThreadFactory()
    communications = [
        CommunicationFactory(
            workspace_id=thread["workspace_id"],
            founder_id=thread["founder_id"],
            thread_id=thread["id"],
            platform=thread["platform"],
        )
        for _ in range(num_messages)
    ]

    return {
        "thread": thread,
        "communications": communications,
    }
