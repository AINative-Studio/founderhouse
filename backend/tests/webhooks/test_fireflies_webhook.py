"""
Comprehensive tests for Fireflies webhook handler
Tests signature verification, transcript processing, and event handling
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
from app.api.webhooks.fireflies_webhook import (
    FirefliesWebhookHandler,
    init_webhook_handler,
    _webhook_handler
)


# Use webhook_client from conftest.py


@pytest.fixture
def fireflies_secret():
    """Fireflies webhook secret"""
    return "test-fireflies-secret-key-for-webhook-verification"


@pytest.fixture
def fireflies_handler(fireflies_secret):
    """Initialize Fireflies webhook handler"""
    handler = FirefliesWebhookHandler(fireflies_secret, None)
    return handler


@pytest.fixture
def fireflies_transcript_payload():
    """Sample Fireflies webhook payload for transcript.ready event"""
    return {
        "event": "transcript.ready",
        "data": {
            "transcript_id": "fireflies_abc123",
            "meeting_id": "meeting_xyz456",
            "title": "Product Review Meeting",
            "date": "2025-11-10T14:00:00Z",
            "duration": 3600,
            "participants": [
                {
                    "name": "John Doe",
                    "email": "john@example.com"
                },
                {
                    "name": "Jane Smith",
                    "email": "jane@example.com"
                }
            ],
            "transcript_url": "https://fireflies.ai/view/abc123"
        },
        "timestamp": int(time.time())
    }


def generate_fireflies_signature(payload: str, secret: str) -> str:
    """Generate valid Fireflies webhook signature"""
    signature = hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
    return signature


class TestFirefliesWebhookSignatureVerification:
    """Test signature verification functionality"""

    def test_verify_signature_valid(self, fireflies_handler, fireflies_secret):
        """Test signature verification with valid signature"""
        # Arrange
        import json
        payload = {"event": "test", "data": {"transcript_id": "123"}}
        payload_str = json.dumps(payload, separators=(',', ':'))

        expected_signature = hmac.new(
            fireflies_secret.encode(),
            payload_str.encode(),
            hashlib.sha256
        ).hexdigest()

        # Act
        result = fireflies_handler.verify_signature(payload_str, expected_signature)

        # Assert
        assert result is True

    def test_verify_signature_invalid(self, fireflies_handler):
        """Test signature verification with invalid signature"""
        # Arrange
        import json
        payload = {"event": "test"}
        payload_str = json.dumps(payload)
        invalid_signature = "invalid_signature_hash_12345"

        # Act
        result = fireflies_handler.verify_signature(payload_str, invalid_signature)

        # Assert
        assert result is False

    def test_verify_signature_wrong_secret(self, fireflies_secret):
        """Test signature verification with wrong secret"""
        # Arrange
        import json
        handler_wrong = FirefliesWebhookHandler("wrong-secret", None)
        payload = {"event": "test"}
        payload_str = json.dumps(payload)

        # Generate signature with correct secret
        correct_signature = hmac.new(
            fireflies_secret.encode(),
            payload_str.encode(),
            hashlib.sha256
        ).hexdigest()

        # Act - verify with wrong secret
        result = handler_wrong.verify_signature(payload_str, correct_signature)

        # Assert
        assert result is False

    def test_verify_signature_empty_payload(self, fireflies_handler):
        """Test signature verification with empty payload"""
        # Arrange
        payload_str = ""
        signature = "some_signature"

        # Act
        result = fireflies_handler.verify_signature(payload_str, signature)

        # Assert
        assert result is False

    def test_verify_signature_exception_handling(self, fireflies_handler):
        """Test signature verification handles exceptions gracefully"""
        # Arrange - None values should cause exception
        payload_str = None
        signature = None

        # Act
        result = fireflies_handler.verify_signature(payload_str, signature)

        # Assert
        assert result is False


class TestFirefliesWebhookEndpoint:
    """Test webhook endpoint handling"""

    @patch('app.api.webhooks.fireflies_webhook._webhook_handler')
    def test_webhook_endpoint_valid_signature(
        self, mock_handler, webhook_client, fireflies_transcript_payload, fireflies_secret
    ):
        """Test webhook endpoint with valid signature"""
        # Arrange
        import json
        mock_handler.verify_signature = MagicMock(return_value=True)
        mock_handler.handle_transcript_ready = AsyncMock(return_value={
            "status": "success",
            "meeting_id": str(uuid4())
        })

        payload_str = json.dumps(fireflies_transcript_payload, separators=(',', ':'))
        signature = generate_fireflies_signature(payload_str, fireflies_secret)

        headers = {
            "x-fireflies-signature": signature
        }

        # Act
        response = webhook_client.post(
            "/api/webhooks/fireflies",
            json=fireflies_transcript_payload,
            headers=headers
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "processing"

    @patch('app.api.webhooks.fireflies_webhook._webhook_handler')
    def test_webhook_endpoint_invalid_signature(
        self, mock_handler, webhook_client, fireflies_transcript_payload
    ):
        """Test webhook endpoint rejects invalid signature"""
        # Arrange
        mock_handler.verify_signature = MagicMock(return_value=False)

        headers = {
            "x-fireflies-signature": "invalid_signature_hash"
        }

        # Act
        response = webhook_client.post(
            "/api/webhooks/fireflies",
            json=fireflies_transcript_payload,
            headers=headers
        )

        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid signature" in response.json()["detail"]

    @patch('app.api.webhooks.fireflies_webhook._webhook_handler')
    def test_webhook_endpoint_no_signature_header(
        self, mock_handler, webhook_client, fireflies_transcript_payload
    ):
        """Test webhook endpoint when signature header is absent"""
        # Arrange
        mock_handler.verify_signature = MagicMock(return_value=True)

        # Act - No signature header
        response = webhook_client.post(
            "/api/webhooks/fireflies",
            json=fireflies_transcript_payload
        )

        # Assert
        # Should process if no signature header is provided
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_401_UNAUTHORIZED]

    @patch('app.api.webhooks.fireflies_webhook._webhook_handler', None)
    def test_webhook_endpoint_handler_not_initialized(
        self, webhook_client, fireflies_transcript_payload
    ):
        """Test webhook endpoint when handler is not initialized"""
        # Act
        response = webhook_client.post(
            "/api/webhooks/fireflies",
            json=fireflies_transcript_payload
        )

        # Assert
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "not initialized" in response.json()["detail"]


class TestFirefliesWebhookEvents:
    """Test handling of different Fireflies event types"""

    @patch('app.api.webhooks.fireflies_webhook._webhook_handler')
    def test_transcript_ready_event(
        self, mock_handler, webhook_client, fireflies_transcript_payload, fireflies_secret
    ):
        """Test handling of transcript.ready event"""
        # Arrange
        import json
        mock_handler.verify_signature = MagicMock(return_value=True)
        mock_handler.handle_transcript_ready = AsyncMock(return_value={
            "status": "success",
            "meeting_id": str(uuid4()),
            "duplicate": False
        })

        payload_str = json.dumps(fireflies_transcript_payload, separators=(',', ':'))
        signature = generate_fireflies_signature(payload_str, fireflies_secret)

        headers = {
            "x-fireflies-signature": signature
        }

        # Act
        response = webhook_client.post(
            "/api/webhooks/fireflies",
            json=fireflies_transcript_payload,
            headers=headers
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "processing"

    @patch('app.api.webhooks.fireflies_webhook._webhook_handler')
    def test_unsupported_event_type(
        self, mock_handler, webhook_client, fireflies_secret
    ):
        """Test handling of unsupported event types"""
        # Arrange
        import json
        mock_handler.verify_signature = MagicMock(return_value=True)

        payload = {
            "event": "meeting.started",
            "data": {
                "meeting_id": "xyz123"
            }
        }

        payload_str = json.dumps(payload, separators=(',', ':'))
        signature = generate_fireflies_signature(payload_str, fireflies_secret)

        headers = {
            "x-fireflies-signature": signature
        }

        # Act
        response = webhook_client.post(
            "/api/webhooks/fireflies",
            json=payload,
            headers=headers
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "ignored"
        assert data["event"] == "meeting.started"

    @patch('app.api.webhooks.fireflies_webhook._webhook_handler')
    def test_transcript_with_minimal_data(
        self, mock_handler, webhook_client, fireflies_secret
    ):
        """Test transcript event with minimal required data"""
        # Arrange
        import json
        mock_handler.verify_signature = MagicMock(return_value=True)
        mock_handler.handle_transcript_ready = AsyncMock(return_value={
            "status": "success",
            "meeting_id": str(uuid4())
        })

        payload = {
            "event": "transcript.ready",
            "data": {
                "transcript_id": "minimal_123"
            }
        }

        payload_str = json.dumps(payload, separators=(',', ':'))
        signature = generate_fireflies_signature(payload_str, fireflies_secret)

        headers = {
            "x-fireflies-signature": signature
        }

        # Act
        response = webhook_client.post(
            "/api/webhooks/fireflies",
            json=payload,
            headers=headers
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK


class TestFirefliesWebhookHandlerMethods:
    """Test FirefliesWebhookHandler class methods"""

    @pytest.mark.asyncio
    async def test_handle_transcript_ready_success(self, fireflies_handler):
        """Test successful transcript.ready event handling"""
        # Arrange
        payload = {
            "transcript_id": "fireflies_abc123",
            "meeting_id": "meeting_xyz456",
            "title": "Team Sync",
            "participants": [
                {"name": "Alice", "email": "alice@example.com"}
            ]
        }

        mock_meeting = MagicMock()
        mock_meeting.id = uuid4()

        with patch.object(
            fireflies_handler.ingestion_service,
            'ingest_from_fireflies',
            new=AsyncMock(return_value=(mock_meeting, False))
        ):
            # Act
            result = await fireflies_handler.handle_transcript_ready(payload)

        # Assert
        assert result["status"] == "success"
        assert "meeting_id" in result
        assert result["duplicate"] is False

    @pytest.mark.asyncio
    async def test_handle_transcript_ready_duplicate(self, fireflies_handler):
        """Test transcript.ready with duplicate meeting"""
        # Arrange
        payload = {
            "transcript_id": "duplicate_abc123",
            "meeting_id": "duplicate_meeting"
        }

        mock_meeting = MagicMock()
        mock_meeting.id = uuid4()

        with patch.object(
            fireflies_handler.ingestion_service,
            'ingest_from_fireflies',
            new=AsyncMock(return_value=(mock_meeting, True))
        ):
            # Act
            result = await fireflies_handler.handle_transcript_ready(payload)

        # Assert
        assert result["status"] == "success"
        assert result["duplicate"] is True

    @pytest.mark.asyncio
    async def test_handle_transcript_ready_error(self, fireflies_handler):
        """Test transcript.ready with ingestion error"""
        # Arrange
        payload = {
            "transcript_id": "error_abc123"
        }

        with patch.object(
            fireflies_handler.ingestion_service,
            'ingest_from_fireflies',
            new=AsyncMock(side_effect=Exception("Fireflies API Error"))
        ):
            # Act
            result = await fireflies_handler.handle_transcript_ready(payload)

        # Assert
        assert result["status"] == "error"
        assert "Fireflies API Error" in result["error"]

    @pytest.mark.asyncio
    async def test_handle_transcript_ready_missing_id(self, fireflies_handler):
        """Test transcript.ready with missing transcript_id"""
        # Arrange
        payload = {
            "meeting_id": "meeting123"
            # Missing transcript_id
        }

        with patch.object(
            fireflies_handler.ingestion_service,
            'ingest_from_fireflies',
            new=AsyncMock(side_effect=Exception("Missing transcript_id"))
        ):
            # Act
            result = await fireflies_handler.handle_transcript_ready(payload)

        # Assert
        assert result["status"] == "error"

    @pytest.mark.asyncio
    async def test_handle_transcript_empty_payload(self, fireflies_handler):
        """Test handling of empty payload"""
        # Arrange
        payload = {}

        with patch.object(
            fireflies_handler.ingestion_service,
            'ingest_from_fireflies',
            new=AsyncMock(side_effect=Exception("Invalid payload"))
        ):
            # Act
            result = await fireflies_handler.handle_transcript_ready(payload)

        # Assert
        assert result["status"] == "error"


class TestFirefliesWebhookStatus:
    """Test webhook status endpoint"""

    @patch('app.api.webhooks.fireflies_webhook._webhook_handler')
    def test_status_endpoint_initialized(self, mock_handler, webhook_client):
        """Test status endpoint when handler is initialized"""
        # Act
        response = webhook_client.get("/api/webhooks/fireflies/status")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["platform"] == "fireflies"
        assert data["status"] == "active"
        assert "timestamp" in data

    @patch('app.api.webhooks.fireflies_webhook._webhook_handler', None)
    def test_status_endpoint_not_initialized(self, webhook_client):
        """Test status endpoint when handler is not initialized"""
        # Act
        response = webhook_client.get("/api/webhooks/fireflies/status")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["platform"] == "fireflies"
        assert data["status"] == "not_initialized"


class TestFirefliesWebhookEdgeCases:
    """Test edge cases and error scenarios"""

    @patch('app.api.webhooks.fireflies_webhook._webhook_handler')
    def test_malformed_json_payload(self, mock_handler, webhook_client):
        """Test handling of malformed JSON payload"""
        # Arrange
        headers = {
            "x-fireflies-signature": "test_signature"
        }

        # Act
        response = webhook_client.post(
            "/api/webhooks/fireflies",
            data="invalid json {not valid}",
            headers=headers
        )

        # Assert
        assert response.status_code in [
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            status.HTTP_500_INTERNAL_SERVER_ERROR
        ]

    @patch('app.api.webhooks.fireflies_webhook._webhook_handler')
    def test_missing_event_field(self, mock_handler, webhook_client, fireflies_secret):
        """Test payload missing required 'event' field"""
        # Arrange
        import json
        mock_handler.verify_signature = MagicMock(return_value=True)

        payload = {
            "data": {"transcript_id": "123"}
            # Missing 'event' field
        }

        payload_str = json.dumps(payload, separators=(',', ':'))
        signature = generate_fireflies_signature(payload_str, fireflies_secret)

        headers = {
            "x-fireflies-signature": signature
        }

        # Act
        response = webhook_client.post(
            "/api/webhooks/fireflies",
            json=payload,
            headers=headers
        )

        # Assert
        # Should handle gracefully
        assert response.status_code == status.HTTP_200_OK

    @patch('app.api.webhooks.fireflies_webhook._webhook_handler')
    def test_empty_data_field(self, mock_handler, webhook_client, fireflies_secret):
        """Test payload with empty data field"""
        # Arrange
        import json
        mock_handler.verify_signature = MagicMock(return_value=True)
        mock_handler.handle_transcript_ready = AsyncMock(return_value={
            "status": "error",
            "error": "No data provided"
        })

        payload = {
            "event": "transcript.ready",
            "data": {}
        }

        payload_str = json.dumps(payload, separators=(',', ':'))
        signature = generate_fireflies_signature(payload_str, fireflies_secret)

        headers = {
            "x-fireflies-signature": signature
        }

        # Act
        response = webhook_client.post(
            "/api/webhooks/fireflies",
            json=payload,
            headers=headers
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK

    @patch('app.api.webhooks.fireflies_webhook._webhook_handler')
    def test_large_transcript_payload(self, mock_handler, webhook_client, fireflies_secret):
        """Test handling of large transcript payload"""
        # Arrange
        import json
        mock_handler.verify_signature = MagicMock(return_value=True)
        mock_handler.handle_transcript_ready = AsyncMock(return_value={
            "status": "success",
            "meeting_id": str(uuid4())
        })

        # Create large payload with many participants
        payload = {
            "event": "transcript.ready",
            "data": {
                "transcript_id": "large_transcript_123",
                "participants": [
                    {"name": f"User {i}", "email": f"user{i}@example.com"}
                    for i in range(100)
                ]
            }
        }

        payload_str = json.dumps(payload, separators=(',', ':'))
        signature = generate_fireflies_signature(payload_str, fireflies_secret)

        headers = {
            "x-fireflies-signature": signature
        }

        # Act
        response = webhook_client.post(
            "/api/webhooks/fireflies",
            json=payload,
            headers=headers
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK


class TestFirefliesWebhookInitialization:
    """Test webhook handler initialization"""

    def test_init_webhook_handler(self):
        """Test initializing the global webhook handler"""
        # Arrange
        secret = "test-fireflies-secret-123"

        # Act
        init_webhook_handler(secret, None)

        # Assert
        from app.api.webhooks.fireflies_webhook import _webhook_handler
        assert _webhook_handler is not None
        assert _webhook_handler.webhook_secret == secret

    def test_handler_initialization_with_supabase(self):
        """Test handler initialization with Supabase client"""
        # Arrange
        secret = "test-fireflies-secret-456"
        mock_supabase = MagicMock()

        # Act
        handler = FirefliesWebhookHandler(secret, mock_supabase)

        # Assert
        assert handler.webhook_secret == secret
        assert handler.ingestion_service is not None

    @pytest.mark.asyncio
    async def test_get_workspace_for_fireflies_account(self, fireflies_handler):
        """Test workspace lookup placeholder"""
        # Act
        workspace_id = await fireflies_handler._get_workspace_for_fireflies_account()

        # Assert
        assert workspace_id is not None

    @pytest.mark.asyncio
    async def test_get_founder_for_workspace(self, fireflies_handler):
        """Test founder lookup placeholder"""
        # Arrange
        workspace_id = uuid4()

        # Act
        founder_id = await fireflies_handler._get_founder_for_workspace(workspace_id)

        # Assert
        assert founder_id is not None

    @pytest.mark.asyncio
    async def test_get_fireflies_credentials(self, fireflies_handler):
        """Test credentials lookup placeholder"""
        # Arrange
        workspace_id = uuid4()

        # Act
        credentials = await fireflies_handler._get_fireflies_credentials(workspace_id)

        # Assert
        assert "api_key" in credentials
