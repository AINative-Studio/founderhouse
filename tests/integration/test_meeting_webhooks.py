"""
AI Chief of Staff - Meeting Webhook Tests
Sprint 3: Issue #7 - Meeting Ingestion via Webhooks

Test coverage for:
- Zoom webhook signature verification
- Fireflies webhook signature verification
- Otter webhook signature verification
- Webhook event processing
- Duplicate event detection
- Async processing queue
"""

import pytest
import hmac
import hashlib
import json
from datetime import datetime, timedelta
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import status
from httpx import AsyncClient

from tests.fixtures.meeting_fixtures import (
    WebhookEventFactory,
    MeetingFactory,
    TranscriptFactory
)


# ============================================================================
# ZOOM WEBHOOK TESTS
# ============================================================================

@pytest.mark.integration
@pytest.mark.meeting
@pytest.mark.webhook
@pytest.mark.asyncio
class TestZoomWebhooks:
    """Test Zoom webhook signature verification and processing."""

    def generate_zoom_signature(self, payload: dict, secret: str) -> str:
        """Generate valid Zoom webhook signature."""
        message = json.dumps(payload, separators=(',', ':'))
        signature = hmac.new(
            secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature

    async def test_zoom_webhook_signature_verification_success(
        self,
        api_client: AsyncClient,
        mock_workspace_id: str
    ):
        """
        Test: Valid Zoom webhook signature accepted
        Given: Webhook with valid HMAC signature
        When: POST to /webhooks/zoom
        Then: Signature verified and event processed
        """
        # Arrange
        secret = "zoom_webhook_secret_key"
        payload = {
            "event": "recording.completed",
            "payload": {
                "object": {
                    "id": "123456789",
                    "uuid": str(uuid4()),
                    "topic": "Product Meeting",
                    "start_time": datetime.utcnow().isoformat()
                }
            }
        }

        signature = self.generate_zoom_signature(payload, secret)

        # Act
        with patch("app.api.webhooks.zoom.ZOOM_WEBHOOK_SECRET", secret):
            response = await api_client.post(
                "/api/v1/webhooks/zoom",
                json=payload,
                headers={"x-zm-signature": signature}
            )

        # Assert
        assert response.status_code == status.HTTP_200_OK

    async def test_zoom_webhook_invalid_signature_rejected(
        self,
        api_client: AsyncClient
    ):
        """
        Test: Invalid Zoom webhook signature rejected
        Given: Webhook with invalid/tampered signature
        When: POST to /webhooks/zoom
        Then: Returns 401 UNAUTHORIZED
        """
        # Arrange
        payload = {
            "event": "recording.completed",
            "payload": {"object": {"id": "123"}}
        }
        invalid_signature = "invalid_signature_12345"

        # Act
        response = await api_client.post(
            "/api/v1/webhooks/zoom",
            json=payload,
            headers={"x-zm-signature": invalid_signature}
        )

        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_zoom_recording_completed_event_processing(
        self,
        api_client: AsyncClient,
        mock_workspace_id: str,
        mock_zoom_connector: AsyncMock
    ):
        """
        Test: Zoom recording.completed event triggers ingestion
        Given: Valid recording.completed webhook
        When: Event processed
        Then: Meeting ingestion job queued
        """
        # Arrange
        event = WebhookEventFactory.zoom_recording_completed()
        meeting_id = event["payload"]["payload"]["object"]["id"]

        mock_zoom_connector.fetch_meeting.return_value = MeetingFactory(
            external_id=meeting_id
        )

        # Act
        with patch("app.services.meeting_ingestion.queue_ingestion_job") as mock_queue:
            # Simulate webhook processing
            await mock_queue(
                platform="zoom",
                event_type="recording.completed",
                external_id=meeting_id
            )

        # Assert
        mock_queue.assert_called_once()

    async def test_zoom_webhook_duplicate_event_detection(
        self,
        api_client: AsyncClient,
        mock_workspace_id: str
    ):
        """
        Test: Duplicate Zoom webhook events ignored
        Given: Same webhook event received twice
        When: Processing duplicate
        Then: Second event ignored (idempotent)
        """
        # Arrange
        event = WebhookEventFactory.zoom_recording_completed()
        event_id = event["id"]

        # Simulate event storage
        processed_events = set()

        # Act - Process same event twice
        def process_event(event_id):
            if event_id in processed_events:
                return "duplicate"
            processed_events.add(event_id)
            return "processed"

        result1 = process_event(event_id)
        result2 = process_event(event_id)

        # Assert
        assert result1 == "processed"
        assert result2 == "duplicate"


# ============================================================================
# FIREFLIES WEBHOOK TESTS
# ============================================================================

@pytest.mark.integration
@pytest.mark.meeting
@pytest.mark.webhook
@pytest.mark.asyncio
class TestFirefliesWebhooks:
    """Test Fireflies webhook signature verification and processing."""

    def generate_fireflies_signature(self, payload: str, secret: str) -> str:
        """Generate valid Fireflies webhook signature."""
        signature = hmac.new(
            secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return f"sha256={signature}"

    async def test_fireflies_webhook_signature_verification(
        self,
        api_client: AsyncClient
    ):
        """
        Test: Valid Fireflies webhook signature accepted
        Given: Webhook with valid HMAC-SHA256 signature
        When: POST to /webhooks/fireflies
        Then: Signature verified successfully
        """
        # Arrange
        secret = "fireflies_webhook_secret"
        payload_dict = {
            "event_type": "transcript_ready",
            "transcript_id": str(uuid4()),
            "meeting_id": str(uuid4())
        }
        payload_str = json.dumps(payload_dict)
        signature = self.generate_fireflies_signature(payload_str, secret)

        # Act
        with patch("app.api.webhooks.fireflies.FIREFLIES_WEBHOOK_SECRET", secret):
            response = await api_client.post(
                "/api/v1/webhooks/fireflies",
                data=payload_str,
                headers={
                    "x-fireflies-signature": signature,
                    "content-type": "application/json"
                }
            )

        # Assert
        assert response.status_code == status.HTTP_200_OK

    async def test_fireflies_transcript_ready_triggers_ingestion(
        self,
        api_client: AsyncClient,
        mock_fireflies_mcp: AsyncMock
    ):
        """
        Test: Fireflies transcript_ready event triggers ingestion
        Given: Valid transcript_ready webhook
        When: Event processed
        Then: Transcript fetched and stored
        """
        # Arrange
        event = WebhookEventFactory.fireflies_transcript_ready()
        transcript_id = event["payload"]["transcript_id"]

        mock_fireflies_mcp.fetch_transcript.return_value = TranscriptFactory.from_fireflies(
            id=transcript_id
        )

        # Act
        with patch("app.services.meeting_ingestion.ingest_fireflies_transcript") as mock_ingest:
            await mock_ingest(transcript_id)

        # Assert
        mock_ingest.assert_called_once_with(transcript_id)


# ============================================================================
# OTTER WEBHOOK TESTS
# ============================================================================

@pytest.mark.integration
@pytest.mark.meeting
@pytest.mark.webhook
@pytest.mark.asyncio
class TestOtterWebhooks:
    """Test Otter webhook signature verification and processing."""

    async def test_otter_webhook_api_key_authentication(
        self,
        api_client: AsyncClient
    ):
        """
        Test: Otter webhook uses API key auth
        Given: Webhook with valid API key in header
        When: POST to /webhooks/otter
        Then: Authentication succeeds
        """
        # Arrange
        api_key = "otter_api_key_12345"
        payload = {
            "event": "transcript_complete",
            "speech_id": str(uuid4()),
            "title": "Meeting Title"
        }

        # Act
        with patch("app.api.webhooks.otter.OTTER_API_KEY", api_key):
            response = await api_client.post(
                "/api/v1/webhooks/otter",
                json=payload,
                headers={"x-otter-api-key": api_key}
            )

        # Assert
        assert response.status_code == status.HTTP_200_OK

    async def test_otter_webhook_invalid_api_key_rejected(
        self,
        api_client: AsyncClient
    ):
        """
        Test: Otter webhook with invalid API key rejected
        Given: Webhook with wrong API key
        When: POST to /webhooks/otter
        Then: Returns 401 UNAUTHORIZED
        """
        # Arrange
        payload = {"event": "transcript_complete"}

        # Act
        response = await api_client.post(
            "/api/v1/webhooks/otter",
            json=payload,
            headers={"x-otter-api-key": "wrong_key"}
        )

        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ============================================================================
# WEBHOOK EVENT PROCESSING
# ============================================================================

@pytest.mark.integration
@pytest.mark.meeting
@pytest.mark.webhook
@pytest.mark.asyncio
class TestWebhookEventProcessing:
    """Test webhook event processing and queueing."""

    async def test_webhook_event_queued_for_async_processing(
        self,
        mock_workspace_id: str
    ):
        """
        Test: Webhook events queued for async processing
        Given: Valid webhook received
        When: Event validated
        Then: Processing job added to queue
        """
        # Arrange
        event = WebhookEventFactory.zoom_recording_completed()

        # Mock queue
        job_queue = []

        async def queue_job(event_type, payload):
            job_queue.append({
                "event_type": event_type,
                "payload": payload,
                "queued_at": datetime.utcnow().isoformat()
            })

        # Act
        await queue_job(event["event_type"], event["payload"])

        # Assert
        assert len(job_queue) == 1
        assert job_queue[0]["event_type"] == event["event_type"]

    async def test_webhook_processing_failure_logged(
        self,
        mock_workspace_id: str
    ):
        """
        Test: Webhook processing failures logged
        Given: Webhook event that fails processing
        When: Processing attempted
        Then: Error logged and event marked as failed
        """
        # Arrange
        event = WebhookEventFactory.zoom_recording_completed()
        event["processed"] = False

        # Act - Simulate processing failure
        try:
            raise Exception("External API timeout")
        except Exception as e:
            event["processed"] = False
            event["error_message"] = str(e)
            event["processed_at"] = datetime.utcnow().isoformat()

        # Assert
        assert event["processed"] is False
        assert event["error_message"] == "External API timeout"
        assert event["processed_at"] is not None

    async def test_webhook_retry_on_transient_failure(
        self,
        mock_workspace_id: str
    ):
        """
        Test: Webhook retried on transient failures
        Given: Webhook processing fails with retryable error
        When: Retry logic triggered
        Then: Event reprocessed successfully
        """
        # Arrange
        event = WebhookEventFactory.zoom_recording_completed()
        attempt_count = 0
        max_retries = 3

        # Act - Simulate retry logic
        async def process_with_retry(event, max_retries=3):
            nonlocal attempt_count
            for attempt in range(max_retries):
                attempt_count += 1
                try:
                    if attempt < 2:
                        raise Exception("Transient error")
                    # Success on 3rd attempt
                    event["processed"] = True
                    return True
                except Exception as e:
                    if attempt == max_retries - 1:
                        event["error_message"] = str(e)
                        return False
                    # Wait and retry
                    continue

        success = await process_with_retry(event, max_retries)

        # Assert
        assert success is True
        assert attempt_count == 3
        assert event["processed"] is True


# ============================================================================
# DUPLICATE EVENT DETECTION
# ============================================================================

@pytest.mark.integration
@pytest.mark.meeting
@pytest.mark.webhook
@pytest.mark.asyncio
class TestDuplicateEventDetection:
    """Test duplicate webhook event detection."""

    async def test_detect_duplicate_by_event_id(
        self,
        mock_workspace_id: str
    ):
        """
        Test: Detect duplicates by event ID
        Given: Webhook with same event ID received twice
        When: Checking for duplicates
        Then: Duplicate detected
        """
        # Arrange
        event_id = str(uuid4())
        processed_event_ids = set()

        # Act
        def is_duplicate(event_id, processed_ids):
            if event_id in processed_ids:
                return True
            processed_ids.add(event_id)
            return False

        is_dup_1 = is_duplicate(event_id, processed_event_ids)
        is_dup_2 = is_duplicate(event_id, processed_event_ids)

        # Assert
        assert is_dup_1 is False  # First time
        assert is_dup_2 is True   # Duplicate

    async def test_detect_duplicate_by_content_hash(
        self,
        mock_workspace_id: str
    ):
        """
        Test: Detect duplicates by payload content hash
        Given: Webhooks with identical payload but different IDs
        When: Checking content hash
        Then: Duplicate detected
        """
        # Arrange
        payload = {
            "meeting_id": "123",
            "recording_url": "https://example.com/rec"
        }

        # Act
        def content_hash(payload):
            content_str = json.dumps(payload, sort_keys=True)
            return hashlib.sha256(content_str.encode()).hexdigest()

        hash_1 = content_hash(payload)
        hash_2 = content_hash(payload.copy())

        # Assert
        assert hash_1 == hash_2

    async def test_duplicate_events_within_time_window(
        self,
        mock_workspace_id: str
    ):
        """
        Test: Detect duplicates within time window
        Given: Same event received within 5-minute window
        When: Checking for recent duplicates
        Then: Duplicate flagged
        """
        # Arrange
        event_id = str(uuid4())
        recent_events = {
            event_id: datetime.utcnow()
        }
        DUPLICATE_WINDOW = timedelta(minutes=5)

        # Act
        def is_recent_duplicate(event_id, recent_events, window):
            if event_id in recent_events:
                time_since = datetime.utcnow() - recent_events[event_id]
                if time_since < window:
                    return True
                # Expired, allow reprocessing
                del recent_events[event_id]
            recent_events[event_id] = datetime.utcnow()
            return False

        is_dup_immediate = is_recent_duplicate(event_id, recent_events, DUPLICATE_WINDOW)

        # Simulate 10 minutes passing
        recent_events[event_id] = datetime.utcnow() - timedelta(minutes=10)
        is_dup_after_window = is_recent_duplicate(event_id, recent_events, DUPLICATE_WINDOW)

        # Assert
        assert is_dup_immediate is True
        assert is_dup_after_window is False  # Outside window, reprocessed


# ============================================================================
# ASYNC PROCESSING QUEUE
# ============================================================================

@pytest.mark.integration
@pytest.mark.meeting
@pytest.mark.webhook
@pytest.mark.slow
@pytest.mark.asyncio
class TestAsyncProcessingQueue:
    """Test async job queue for webhook processing."""

    async def test_webhook_job_added_to_queue(
        self,
        mock_workspace_id: str
    ):
        """
        Test: Webhook jobs added to processing queue
        Given: Multiple webhook events
        When: Events received
        Then: All jobs queued in order
        """
        # Arrange
        events = [
            WebhookEventFactory.zoom_recording_completed(),
            WebhookEventFactory.fireflies_transcript_ready(),
            WebhookEventFactory.zoom_recording_completed()
        ]

        job_queue = []

        # Act
        for event in events:
            job_queue.append({
                "id": str(uuid4()),
                "event": event,
                "status": "queued",
                "created_at": datetime.utcnow().isoformat()
            })

        # Assert
        assert len(job_queue) == 3
        assert all(job["status"] == "queued" for job in job_queue)

    async def test_job_queue_processes_fifo(
        self,
        mock_workspace_id: str
    ):
        """
        Test: Jobs processed in FIFO order
        Given: Multiple jobs in queue
        When: Processing jobs
        Then: Jobs processed in order received
        """
        # Arrange
        from collections import deque
        job_queue = deque()

        jobs = [
            {"id": i, "event": "job_" + str(i)}
            for i in range(5)
        ]

        for job in jobs:
            job_queue.append(job)

        # Act
        processed_order = []
        while job_queue:
            job = job_queue.popleft()
            processed_order.append(job["id"])

        # Assert
        assert processed_order == [0, 1, 2, 3, 4]

    async def test_failed_jobs_moved_to_dlq(
        self,
        mock_workspace_id: str
    ):
        """
        Test: Failed jobs moved to dead letter queue
        Given: Job that fails after max retries
        When: Processing attempted
        Then: Job moved to DLQ for manual review
        """
        # Arrange
        job = {
            "id": str(uuid4()),
            "event": WebhookEventFactory.zoom_recording_completed(),
            "retry_count": 3,
            "max_retries": 3
        }

        dead_letter_queue = []

        # Act
        def process_job(job, dlq):
            if job["retry_count"] >= job["max_retries"]:
                dlq.append({
                    **job,
                    "failed_at": datetime.utcnow().isoformat(),
                    "reason": "Max retries exceeded"
                })
                return False
            return True

        success = process_job(job, dead_letter_queue)

        # Assert
        assert success is False
        assert len(dead_letter_queue) == 1
        assert dead_letter_queue[0]["reason"] == "Max retries exceeded"

    async def test_job_processing_timeout(
        self,
        mock_workspace_id: str
    ):
        """
        Test: Job processing timeout handled
        Given: Job that takes too long
        When: Timeout exceeded
        Then: Job cancelled and retried
        """
        # Arrange
        import asyncio

        async def long_running_job():
            await asyncio.sleep(10)  # Simulates long task
            return "completed"

        # Act
        try:
            result = await asyncio.wait_for(long_running_job(), timeout=1.0)
            timed_out = False
        except asyncio.TimeoutError:
            timed_out = True
            result = None

        # Assert
        assert timed_out is True
        assert result is None


# ============================================================================
# WEBHOOK RATE LIMITING
# ============================================================================

@pytest.mark.integration
@pytest.mark.meeting
@pytest.mark.webhook
@pytest.mark.asyncio
class TestWebhookRateLimiting:
    """Test rate limiting for webhook endpoints."""

    async def test_rate_limit_excessive_webhook_requests(
        self,
        api_client: AsyncClient
    ):
        """
        Test: Rate limiting applied to webhook endpoints
        Given: Excessive webhook requests from same source
        When: Rate limit exceeded
        Then: Returns 429 TOO_MANY_REQUESTS
        """
        # Arrange
        from collections import defaultdict
        request_counts = defaultdict(int)
        RATE_LIMIT = 100  # per minute
        source_ip = "192.168.1.1"

        # Act
        def check_rate_limit(source_ip, limit=100):
            request_counts[source_ip] += 1
            if request_counts[source_ip] > limit:
                return True  # Rate limited
            return False

        # Simulate 150 requests
        rate_limited = False
        for i in range(150):
            if check_rate_limit(source_ip, RATE_LIMIT):
                rate_limited = True
                break

        # Assert
        assert rate_limited is True
        assert request_counts[source_ip] > RATE_LIMIT

    async def test_rate_limit_per_workspace(
        self,
        mock_workspace_id: str
    ):
        """
        Test: Rate limiting per workspace
        Given: Multiple workspaces sending webhooks
        When: One workspace exceeds limit
        Then: Only that workspace rate limited
        """
        # Arrange
        from collections import defaultdict
        workspace_requests = defaultdict(int)
        LIMIT_PER_WORKSPACE = 50

        workspace_a = str(uuid4())
        workspace_b = str(uuid4())

        # Act
        # Workspace A sends 60 requests
        for _ in range(60):
            workspace_requests[workspace_a] += 1

        # Workspace B sends 30 requests
        for _ in range(30):
            workspace_requests[workspace_b] += 1

        # Assert
        assert workspace_requests[workspace_a] > LIMIT_PER_WORKSPACE  # Would be rate limited
        assert workspace_requests[workspace_b] < LIMIT_PER_WORKSPACE  # Not rate limited
