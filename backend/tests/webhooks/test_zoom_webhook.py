"""
Comprehensive tests for Zoom webhook handler
Tests signature verification, event handling, and security
"""
import pytest
import hmac
import hashlib
import time
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import status
from fastapi.testclient import TestClient

from app.main import app
from app.api.webhooks.zoom_webhook import (
    ZoomWebhookHandler,
    init_webhook_handler,
    _webhook_handler
)


# Use webhook_client from conftest.py


@pytest.fixture
def zoom_secret():
    """Zoom webhook secret"""
    return "test-zoom-secret-key-for-webhook-verification"


@pytest.fixture
def zoom_handler(zoom_secret):
    """Initialize Zoom webhook handler"""
    handler = ZoomWebhookHandler(zoom_secret, None)
    return handler


@pytest.fixture
def zoom_webhook_payload():
    """Sample Zoom webhook payload for meeting.ended event"""
    return {
        "event": "meeting.ended",
        "payload": {
            "object": {
                "id": "123456789",
                "uuid": "abc-def-ghi-jkl",
                "host_id": "host123",
                "host_email": "host@example.com",
                "topic": "Sprint Planning Meeting",
                "start_time": "2025-11-10T10:00:00Z",
                "duration": 60,
                "timezone": "UTC"
            }
        },
        "event_ts": int(time.time() * 1000)
    }


@pytest.fixture
def zoom_recording_payload():
    """Sample Zoom webhook payload for recording.completed event"""
    return {
        "event": "recording.completed",
        "payload": {
            "object": {
                "id": "987654321",
                "uuid": "xyz-abc-def",
                "host_id": "host456",
                "host_email": "host@example.com",
                "topic": "Product Review",
                "start_time": "2025-11-10T14:00:00Z",
                "duration": 45,
                "recording_files": [
                    {
                        "id": "rec123",
                        "recording_type": "audio_transcript",
                        "download_url": "https://zoom.us/rec/download/abc123",
                        "file_size": 1024000
                    },
                    {
                        "id": "rec456",
                        "recording_type": "shared_screen_with_speaker_view",
                        "download_url": "https://zoom.us/rec/download/def456",
                        "file_size": 5120000
                    }
                ]
            }
        },
        "event_ts": int(time.time() * 1000)
    }


def generate_zoom_signature(payload: dict, timestamp: str, secret: str) -> str:
    """Generate valid Zoom webhook signature"""
    import json
    message = f"v0:{timestamp}:{json.dumps(payload, separators=(',', ':'))}"
    signature = hmac.new(
        secret.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()
    return f"v0={signature}"


class TestZoomWebhookSignatureVerification:
    """Test signature verification functionality"""

    def test_verify_signature_valid(self, zoom_handler, zoom_secret):
        """Test signature verification with valid signature"""
        # Arrange
        import json
        payload = {"event": "test", "event_ts": 1699632000000}
        payload_str = json.dumps(payload, separators=(',', ':'))
        timestamp = str(payload["event_ts"])

        message = f"v0:{timestamp}:{payload_str}"
        signature = hmac.new(
            zoom_secret.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        signature_header = f"v0={signature}"

        # Act
        result = zoom_handler.verify_signature(
            payload_str.encode(),
            timestamp,
            signature_header
        )

        # Assert
        assert result is True

    def test_verify_signature_invalid(self, zoom_handler):
        """Test signature verification with invalid signature"""
        # Arrange
        payload = b'{"event":"test"}'
        timestamp = str(int(time.time()))
        invalid_signature = "v0=invalid_signature_hash"

        # Act
        result = zoom_handler.verify_signature(
            payload,
            timestamp,
            invalid_signature
        )

        # Assert
        assert result is False

    def test_verify_signature_wrong_secret(self, zoom_secret):
        """Test signature verification with wrong secret"""
        # Arrange
        import json
        handler_wrong = ZoomWebhookHandler("wrong-secret", None)
        payload = {"event": "test", "event_ts": 1699632000000}
        payload_str = json.dumps(payload, separators=(',', ':'))
        timestamp = str(payload["event_ts"])

        # Generate signature with correct secret
        message = f"v0:{timestamp}:{payload_str}"
        signature = hmac.new(
            zoom_secret.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        signature_header = f"v0={signature}"

        # Act - verify with wrong secret
        result = handler_wrong.verify_signature(
            payload_str.encode(),
            timestamp,
            signature_header
        )

        # Assert
        assert result is False

    def test_verify_signature_malformed_format(self, zoom_handler):
        """Test signature verification with malformed signature format"""
        # Arrange
        payload = b'{"event":"test"}'
        timestamp = str(int(time.time()))
        malformed_signature = "invalid_format_no_prefix"

        # Act
        result = zoom_handler.verify_signature(
            payload,
            timestamp,
            malformed_signature
        )

        # Assert
        assert result is False


class TestZoomWebhookEndpoint:
    """Test webhook endpoint handling"""

    @patch('app.api.webhooks.zoom_webhook._webhook_handler')
    def test_webhook_endpoint_valid_signature(
        self, mock_handler, webhook_client, zoom_webhook_payload, zoom_secret
    ):
        """Test webhook endpoint with valid signature"""
        # Arrange
        import json
        mock_handler.verify_signature = MagicMock(return_value=True)
        mock_handler.handle_meeting_ended = AsyncMock(return_value={
            "status": "logged",
            "meeting_id": "123456789"
        })

        timestamp = str(zoom_webhook_payload["event_ts"])
        payload_str = json.dumps(zoom_webhook_payload, separators=(',', ':'))
        signature = generate_zoom_signature(zoom_webhook_payload, timestamp, zoom_secret)

        headers = {
            "x-zm-signature": signature,
            "x-zm-request-timestamp": timestamp
        }

        # Act
        response = webhook_client.post(
            "/api/webhooks/zoom",
            json=zoom_webhook_payload,
            headers=headers
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "logged"

    @patch('app.api.webhooks.zoom_webhook._webhook_handler')
    def test_webhook_endpoint_invalid_signature(
        self, mock_handler, webhook_client, zoom_webhook_payload
    ):
        """Test webhook endpoint rejects invalid signature"""
        # Arrange
        mock_handler.verify_signature = MagicMock(return_value=False)

        headers = {
            "x-zm-signature": "v0=invalid_signature",
            "x-zm-request-timestamp": str(zoom_webhook_payload["event_ts"])
        }

        # Act
        response = webhook_client.post(
            "/api/webhooks/zoom",
            json=zoom_webhook_payload,
            headers=headers
        )

        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid signature" in response.json()["detail"]

    @patch('app.api.webhooks.zoom_webhook._webhook_handler')
    def test_webhook_endpoint_missing_signature(
        self, mock_handler, webhook_client, zoom_webhook_payload
    ):
        """Test webhook endpoint when signature header is missing"""
        # Arrange
        mock_handler.verify_signature = MagicMock(return_value=True)
        mock_handler.handle_meeting_ended = AsyncMock(return_value={
            "status": "logged",
            "meeting_id": "123456789"
        })

        # Act - No signature headers provided
        response = webhook_client.post(
            "/api/webhooks/zoom",
            json=zoom_webhook_payload
        )

        # Assert - Should process if handler is initialized (no signature required when header absent)
        assert response.status_code == status.HTTP_200_OK

    @patch('app.api.webhooks.zoom_webhook._webhook_handler', None)
    def test_webhook_endpoint_handler_not_initialized(
        self, webhook_client, zoom_webhook_payload
    ):
        """Test webhook endpoint when handler is not initialized"""
        # Act
        response = webhook_client.post(
            "/api/webhooks/zoom",
            json=zoom_webhook_payload
        )

        # Assert
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "not initialized" in response.json()["detail"]


class TestZoomWebhookEvents:
    """Test handling of different Zoom event types"""

    @patch('app.api.webhooks.zoom_webhook._webhook_handler')
    @pytest.mark.asyncio
    async def test_meeting_ended_event(
        self, mock_handler, webhook_client, zoom_webhook_payload, zoom_secret
    ):
        """Test handling of meeting.ended event"""
        # Arrange
        mock_handler.verify_signature = MagicMock(return_value=True)
        mock_handler.handle_meeting_ended = AsyncMock(return_value={
            "status": "logged",
            "meeting_id": "123456789"
        })

        import json
        timestamp = str(zoom_webhook_payload["event_ts"])
        signature = generate_zoom_signature(zoom_webhook_payload, timestamp, zoom_secret)

        headers = {
            "x-zm-signature": signature,
            "x-zm-request-timestamp": timestamp
        }

        # Act
        response = webhook_client.post(
            "/api/webhooks/zoom",
            json=zoom_webhook_payload,
            headers=headers
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "logged"

    @patch('app.api.webhooks.zoom_webhook._webhook_handler')
    def test_recording_completed_event(
        self, mock_handler, webhook_client, zoom_recording_payload, zoom_secret
    ):
        """Test handling of recording.completed event (background task)"""
        # Arrange
        mock_handler.verify_signature = MagicMock(return_value=True)
        mock_handler.handle_recording_completed = AsyncMock(return_value={
            "status": "success",
            "meeting_id": str(uuid4())
        })

        import json
        timestamp = str(zoom_recording_payload["event_ts"])
        signature = generate_zoom_signature(zoom_recording_payload, timestamp, zoom_secret)

        headers = {
            "x-zm-signature": signature,
            "x-zm-request-timestamp": timestamp
        }

        # Act
        response = webhook_client.post(
            "/api/webhooks/zoom",
            json=zoom_recording_payload,
            headers=headers
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "processing"

    @patch('app.api.webhooks.zoom_webhook._webhook_handler')
    def test_url_validation_event(
        self, mock_handler, webhook_client, zoom_secret
    ):
        """Test handling of endpoint.url_validation event"""
        # Arrange
        mock_handler.verify_signature = MagicMock(return_value=True)

        payload = {
            "event": "endpoint.url_validation",
            "payload": {
                "plainToken": "test_plain_token_12345",
                "encryptedToken": "test_encrypted_token_67890"
            },
            "event_ts": int(time.time() * 1000)
        }

        import json
        timestamp = str(payload["event_ts"])
        signature = generate_zoom_signature(payload, timestamp, zoom_secret)

        headers = {
            "x-zm-signature": signature,
            "x-zm-request-timestamp": timestamp
        }

        # Act
        response = webhook_client.post(
            "/api/webhooks/zoom",
            json=payload,
            headers=headers
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "plainToken" in data
        assert data["plainToken"] == "test_plain_token_12345"

    @patch('app.api.webhooks.zoom_webhook._webhook_handler')
    def test_unsupported_event_type(
        self, mock_handler, webhook_client, zoom_secret
    ):
        """Test handling of unsupported event types"""
        # Arrange
        mock_handler.verify_signature = MagicMock(return_value=True)

        payload = {
            "event": "meeting.participant_joined",
            "payload": {
                "object": {
                    "id": "123",
                    "participant": {
                        "user_name": "John Doe"
                    }
                }
            },
            "event_ts": int(time.time() * 1000)
        }

        import json
        timestamp = str(payload["event_ts"])
        signature = generate_zoom_signature(payload, timestamp, zoom_secret)

        headers = {
            "x-zm-signature": signature,
            "x-zm-request-timestamp": timestamp
        }

        # Act
        response = webhook_client.post(
            "/api/webhooks/zoom",
            json=payload,
            headers=headers
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "ignored"
        assert data["event"] == "meeting.participant_joined"


class TestZoomWebhookHandlerMethods:
    """Test ZoomWebhookHandler class methods"""

    @pytest.mark.asyncio
    async def test_handle_recording_completed_success(self, zoom_handler):
        """Test successful recording.completed event handling"""
        # Arrange
        payload = {
            "object": {
                "id": "123456789",
                "uuid": "abc-def",
                "host_email": "host@example.com",
                "topic": "Team Standup",
                "recording_files": [
                    {"recording_type": "audio_transcript"}
                ]
            }
        }

        mock_meeting = MagicMock()
        mock_meeting.id = uuid4()

        with patch.object(
            zoom_handler.ingestion_service,
            'ingest_from_zoom',
            new=AsyncMock(return_value=(mock_meeting, False))
        ):
            # Act
            result = await zoom_handler.handle_recording_completed(payload)

        # Assert
        assert result["status"] == "success"
        assert "meeting_id" in result
        assert result["duplicate"] is False

    @pytest.mark.asyncio
    async def test_handle_recording_completed_no_workspace(self, zoom_handler):
        """Test recording.completed when no workspace is found"""
        # Arrange
        payload = {
            "object": {
                "id": "123456789",
                "uuid": "abc-def",
                "host_email": "unknown@example.com",
                "topic": "Test Meeting"
            }
        }

        with patch.object(
            zoom_handler,
            '_get_workspace_for_zoom_account',
            new=AsyncMock(return_value=None)
        ):
            # Act
            result = await zoom_handler.handle_recording_completed(payload)

        # Assert
        assert result["status"] == "skipped"
        assert result["reason"] == "no_workspace"

    @pytest.mark.asyncio
    async def test_handle_recording_completed_duplicate(self, zoom_handler):
        """Test recording.completed with duplicate meeting"""
        # Arrange
        payload = {
            "object": {
                "id": "duplicate123",
                "uuid": "dup-abc-def",
                "host_email": "host@example.com",
                "topic": "Duplicate Meeting"
            }
        }

        mock_meeting = MagicMock()
        mock_meeting.id = uuid4()

        with patch.object(
            zoom_handler.ingestion_service,
            'ingest_from_zoom',
            new=AsyncMock(return_value=(mock_meeting, True))
        ):
            # Act
            result = await zoom_handler.handle_recording_completed(payload)

        # Assert
        assert result["status"] == "success"
        assert result["duplicate"] is True

    @pytest.mark.asyncio
    async def test_handle_recording_completed_error(self, zoom_handler):
        """Test recording.completed with ingestion error"""
        # Arrange
        payload = {
            "object": {
                "id": "error123",
                "uuid": "err-abc",
                "host_email": "host@example.com",
                "topic": "Error Meeting"
            }
        }

        with patch.object(
            zoom_handler.ingestion_service,
            'ingest_from_zoom',
            new=AsyncMock(side_effect=Exception("API Error"))
        ):
            # Act
            result = await zoom_handler.handle_recording_completed(payload)

        # Assert
        assert result["status"] == "error"
        assert "API Error" in result["error"]

    @pytest.mark.asyncio
    async def test_handle_meeting_ended_success(self, zoom_handler):
        """Test successful meeting.ended event handling"""
        # Arrange
        payload = {
            "object": {
                "id": "789012345",
                "uuid": "meeting-ended-uuid",
                "topic": "Daily Standup"
            }
        }

        # Act
        result = await zoom_handler.handle_meeting_ended(payload)

        # Assert
        assert result["status"] == "logged"
        assert result["meeting_id"] == "789012345"

    @pytest.mark.asyncio
    async def test_handle_meeting_ended_graceful_empty(self, zoom_handler):
        """Test meeting.ended handles empty payload gracefully"""
        # Arrange
        payload = {}  # Missing required fields

        # Act
        result = await zoom_handler.handle_meeting_ended(payload)

        # Assert
        # Handler is designed to be graceful - logs None meeting_id
        assert result["status"] == "logged"
        assert result["meeting_id"] is None


class TestZoomWebhookStatus:
    """Test webhook status endpoint"""

    @patch('app.api.webhooks.zoom_webhook._webhook_handler')
    def test_status_endpoint_initialized(self, mock_handler, webhook_client):
        """Test status endpoint when handler is initialized"""
        # Act
        response = webhook_client.get("/api/webhooks/zoom/status")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["platform"] == "zoom"
        assert data["status"] == "active"
        assert "timestamp" in data

    @patch('app.api.webhooks.zoom_webhook._webhook_handler', None)
    def test_status_endpoint_not_initialized(self, webhook_client):
        """Test status endpoint when handler is not initialized"""
        # Act
        response = webhook_client.get("/api/webhooks/zoom/status")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["platform"] == "zoom"
        assert data["status"] == "not_initialized"


class TestZoomWebhookEdgeCases:
    """Test edge cases and error scenarios"""

    @patch('app.api.webhooks.zoom_webhook._webhook_handler')
    def test_malformed_json_payload(self, mock_handler, webhook_client):
        """Test handling of malformed JSON payload"""
        # Arrange
        headers = {
            "x-zm-signature": "v0=test",
            "x-zm-request-timestamp": str(int(time.time()))
        }

        # Act
        response = webhook_client.post(
            "/api/webhooks/zoom",
            data="invalid json {not valid}",
            headers=headers
        )

        # Assert
        assert response.status_code in [
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            status.HTTP_500_INTERNAL_SERVER_ERROR
        ]

    @patch('app.api.webhooks.zoom_webhook._webhook_handler')
    def test_missing_event_field(self, mock_handler, webhook_client, zoom_secret):
        """Test payload missing required 'event' field"""
        # Arrange
        mock_handler.verify_signature = MagicMock(return_value=True)

        payload = {
            "payload": {"object": {"id": "123"}},
            "event_ts": int(time.time() * 1000)
        }

        import json
        timestamp = str(payload["event_ts"])
        signature = generate_zoom_signature(payload, timestamp, zoom_secret)

        headers = {
            "x-zm-signature": signature,
            "x-zm-request-timestamp": timestamp
        }

        # Act
        response = webhook_client.post(
            "/api/webhooks/zoom",
            json=payload,
            headers=headers
        )

        # Assert
        # Should handle gracefully
        assert response.status_code == status.HTTP_200_OK

    @patch('app.api.webhooks.zoom_webhook._webhook_handler')
    def test_empty_payload(self, mock_handler, webhook_client, zoom_secret):
        """Test handling of empty payload"""
        # Arrange
        mock_handler.verify_signature = MagicMock(return_value=True)

        payload = {}

        import json
        timestamp = str(int(time.time() * 1000))
        signature = generate_zoom_signature(payload, timestamp, zoom_secret)

        headers = {
            "x-zm-signature": signature,
            "x-zm-request-timestamp": timestamp
        }

        # Act
        response = webhook_client.post(
            "/api/webhooks/zoom",
            json=payload,
            headers=headers
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK


class TestZoomWebhookInitialization:
    """Test webhook handler initialization"""

    def test_init_webhook_handler(self):
        """Test initializing the global webhook handler"""
        # Arrange
        secret = "test-secret-123"

        # Act
        init_webhook_handler(secret, None)

        # Assert
        from app.api.webhooks.zoom_webhook import _webhook_handler
        assert _webhook_handler is not None
        assert _webhook_handler.secret_token == secret

    def test_handler_initialization_with_supabase(self):
        """Test handler initialization with Supabase client"""
        # Arrange
        secret = "test-secret-456"
        mock_supabase = MagicMock()

        # Act
        handler = ZoomWebhookHandler(secret, mock_supabase)

        # Assert
        assert handler.secret_token == secret
        assert handler.ingestion_service is not None
