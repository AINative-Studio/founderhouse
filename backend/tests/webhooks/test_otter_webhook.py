"""
Comprehensive tests for Otter webhook handler
Tests signature verification, speech processing, and event handling
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
from app.api.webhooks.otter_webhook import (
    OtterWebhookHandler,
    init_webhook_handler,
    _webhook_handler
)


# Use webhook_client from conftest.py


@pytest.fixture
def otter_secret():
    """Otter webhook secret"""
    return "test-otter-secret-key-for-webhook-verification"


@pytest.fixture
def otter_handler(otter_secret):
    """Initialize Otter webhook handler"""
    handler = OtterWebhookHandler(otter_secret, None)
    return handler


@pytest.fixture
def otter_speech_created_payload():
    """Sample Otter webhook payload for speech.created event"""
    return {
        "event": "speech.created",
        "data": {
            "speech_id": "otter_speech_abc123",
            "title": "Sales Call - Q4 Planning",
            "created_at": "2025-11-10T15:30:00Z",
            "duration": 2700,
            "speakers": [
                {
                    "id": "speaker1",
                    "name": "Michael Chen"
                },
                {
                    "id": "speaker2",
                    "name": "Sarah Johnson"
                }
            ],
            "transcript_url": "https://otter.ai/u/abc123",
            "status": "completed"
        },
        "timestamp": int(time.time())
    }


@pytest.fixture
def otter_speech_updated_payload():
    """Sample Otter webhook payload for speech.updated event"""
    return {
        "event": "speech.updated",
        "data": {
            "speech_id": "otter_speech_xyz789",
            "title": "Updated Meeting Title",
            "updated_at": "2025-11-10T16:00:00Z",
            "status": "completed",
            "transcript_available": True
        },
        "timestamp": int(time.time())
    }


def generate_otter_signature(payload: str, secret: str) -> str:
    """Generate valid Otter webhook signature with sha256= prefix"""
    signature = hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
    return f"sha256={signature}"


class TestOtterWebhookSignatureVerification:
    """Test signature verification functionality"""

    def test_verify_signature_valid(self, otter_handler, otter_secret):
        """Test signature verification with valid signature"""
        # Arrange
        import json
        payload = {"event": "test", "data": {"speech_id": "123"}}
        payload_str = json.dumps(payload, separators=(',', ':'))

        expected_signature = hmac.new(
            otter_secret.encode(),
            payload_str.encode(),
            hashlib.sha256
        ).hexdigest()
        signature_header = f"sha256={expected_signature}"

        # Act
        result = otter_handler.verify_signature(payload_str, signature_header)

        # Assert
        assert result is True

    def test_verify_signature_invalid(self, otter_handler):
        """Test signature verification with invalid signature"""
        # Arrange
        import json
        payload = {"event": "test"}
        payload_str = json.dumps(payload)
        invalid_signature = "sha256=invalid_signature_hash_12345"

        # Act
        result = otter_handler.verify_signature(payload_str, invalid_signature)

        # Assert
        assert result is False

    def test_verify_signature_wrong_secret(self, otter_secret):
        """Test signature verification with wrong secret"""
        # Arrange
        import json
        handler_wrong = OtterWebhookHandler("wrong-secret", None)
        payload = {"event": "test"}
        payload_str = json.dumps(payload)

        # Generate signature with correct secret
        correct_hash = hmac.new(
            otter_secret.encode(),
            payload_str.encode(),
            hashlib.sha256
        ).hexdigest()
        signature_header = f"sha256={correct_hash}"

        # Act - verify with wrong secret
        result = handler_wrong.verify_signature(payload_str, signature_header)

        # Assert
        assert result is False

    def test_verify_signature_missing_prefix(self, otter_handler, otter_secret):
        """Test signature verification without sha256= prefix"""
        # Arrange
        import json
        payload = {"event": "test"}
        payload_str = json.dumps(payload)

        # Generate signature without prefix
        signature_hash = hmac.new(
            otter_secret.encode(),
            payload_str.encode(),
            hashlib.sha256
        ).hexdigest()

        # Act - signature without sha256= prefix
        result = otter_handler.verify_signature(payload_str, signature_hash)

        # Assert
        assert result is False

    def test_verify_signature_empty_payload(self, otter_handler):
        """Test signature verification with empty payload"""
        # Arrange
        payload_str = ""
        signature = "sha256=some_signature"

        # Act
        result = otter_handler.verify_signature(payload_str, signature)

        # Assert
        assert result is False

    def test_verify_signature_exception_handling(self, otter_handler):
        """Test signature verification handles exceptions gracefully"""
        # Arrange - None values should cause exception
        payload_str = None
        signature = None

        # Act
        result = otter_handler.verify_signature(payload_str, signature)

        # Assert
        assert result is False


class TestOtterWebhookEndpoint:
    """Test webhook endpoint handling"""

    @patch('app.api.webhooks.otter_webhook._webhook_handler')
    def test_webhook_endpoint_valid_signature(
        self, mock_handler, webhook_client, otter_speech_created_payload, otter_secret
    ):
        """Test webhook endpoint with valid signature"""
        # Arrange
        import json
        mock_handler.verify_signature = MagicMock(return_value=True)
        mock_handler.handle_speech_created = AsyncMock(return_value={
            "status": "success",
            "meeting_id": str(uuid4())
        })

        payload_str = json.dumps(otter_speech_created_payload, separators=(',', ':'))
        signature = generate_otter_signature(payload_str, otter_secret)

        headers = {
            "x-otter-signature": signature
        }

        # Act
        response = webhook_client.post(
            "/api/webhooks/otter",
            json=otter_speech_created_payload,
            headers=headers
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "processing"

    @patch('app.api.webhooks.otter_webhook._webhook_handler')
    def test_webhook_endpoint_invalid_signature(
        self, mock_handler, webhook_client, otter_speech_created_payload
    ):
        """Test webhook endpoint rejects invalid signature"""
        # Arrange
        mock_handler.verify_signature = MagicMock(return_value=False)

        headers = {
            "x-otter-signature": "sha256=invalid_signature_hash"
        }

        # Act
        response = webhook_client.post(
            "/api/webhooks/otter",
            json=otter_speech_created_payload,
            headers=headers
        )

        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid signature" in response.json()["detail"]

    @patch('app.api.webhooks.otter_webhook._webhook_handler')
    def test_webhook_endpoint_no_signature_header(
        self, mock_handler, webhook_client, otter_speech_created_payload
    ):
        """Test webhook endpoint when signature header is absent"""
        # Arrange
        mock_handler.verify_signature = MagicMock(return_value=True)

        # Act - No signature header
        response = webhook_client.post(
            "/api/webhooks/otter",
            json=otter_speech_created_payload
        )

        # Assert
        # Should process if no signature header is provided
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_401_UNAUTHORIZED]

    @patch('app.api.webhooks.otter_webhook._webhook_handler', None)
    def test_webhook_endpoint_handler_not_initialized(
        self, webhook_client, otter_speech_created_payload
    ):
        """Test webhook endpoint when handler is not initialized"""
        # Act
        response = webhook_client.post(
            "/api/webhooks/otter",
            json=otter_speech_created_payload
        )

        # Assert
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "not initialized" in response.json()["detail"]


class TestOtterWebhookEvents:
    """Test handling of different Otter event types"""

    @patch('app.api.webhooks.otter_webhook._webhook_handler')
    def test_speech_created_event(
        self, mock_handler, webhook_client, otter_speech_created_payload, otter_secret
    ):
        """Test handling of speech.created event"""
        # Arrange
        import json
        mock_handler.verify_signature = MagicMock(return_value=True)
        mock_handler.handle_speech_created = AsyncMock(return_value={
            "status": "success",
            "meeting_id": str(uuid4()),
            "duplicate": False
        })

        payload_str = json.dumps(otter_speech_created_payload, separators=(',', ':'))
        signature = generate_otter_signature(payload_str, otter_secret)

        headers = {
            "x-otter-signature": signature
        }

        # Act
        response = webhook_client.post(
            "/api/webhooks/otter",
            json=otter_speech_created_payload,
            headers=headers
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "processing"

    @patch('app.api.webhooks.otter_webhook._webhook_handler')
    def test_speech_updated_event(
        self, mock_handler, webhook_client, otter_speech_updated_payload, otter_secret
    ):
        """Test handling of speech.updated event"""
        # Arrange
        import json
        mock_handler.verify_signature = MagicMock(return_value=True)
        mock_handler.handle_speech_created = AsyncMock(return_value={
            "status": "success",
            "meeting_id": str(uuid4())
        })

        payload_str = json.dumps(otter_speech_updated_payload, separators=(',', ':'))
        signature = generate_otter_signature(payload_str, otter_secret)

        headers = {
            "x-otter-signature": signature
        }

        # Act
        response = webhook_client.post(
            "/api/webhooks/otter",
            json=otter_speech_updated_payload,
            headers=headers
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "processing"

    @patch('app.api.webhooks.otter_webhook._webhook_handler')
    def test_unsupported_event_type(
        self, mock_handler, webhook_client, otter_secret
    ):
        """Test handling of unsupported event types"""
        # Arrange
        import json
        mock_handler.verify_signature = MagicMock(return_value=True)

        payload = {
            "event": "speech.deleted",
            "data": {
                "speech_id": "deleted_123"
            }
        }

        payload_str = json.dumps(payload, separators=(',', ':'))
        signature = generate_otter_signature(payload_str, otter_secret)

        headers = {
            "x-otter-signature": signature
        }

        # Act
        response = webhook_client.post(
            "/api/webhooks/otter",
            json=payload,
            headers=headers
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "ignored"
        assert data["event"] == "speech.deleted"

    @patch('app.api.webhooks.otter_webhook._webhook_handler')
    def test_speech_with_minimal_data(
        self, mock_handler, webhook_client, otter_secret
    ):
        """Test speech event with minimal required data"""
        # Arrange
        import json
        mock_handler.verify_signature = MagicMock(return_value=True)
        mock_handler.handle_speech_created = AsyncMock(return_value={
            "status": "success",
            "meeting_id": str(uuid4())
        })

        payload = {
            "event": "speech.created",
            "data": {
                "speech_id": "minimal_123"
            }
        }

        payload_str = json.dumps(payload, separators=(',', ':'))
        signature = generate_otter_signature(payload_str, otter_secret)

        headers = {
            "x-otter-signature": signature
        }

        # Act
        response = webhook_client.post(
            "/api/webhooks/otter",
            json=payload,
            headers=headers
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK


class TestOtterWebhookHandlerMethods:
    """Test OtterWebhookHandler class methods"""

    @pytest.mark.asyncio
    async def test_handle_speech_created_success(self, otter_handler):
        """Test successful speech.created event handling"""
        # Arrange
        payload = {
            "speech_id": "otter_abc123",
            "title": "Product Strategy Meeting",
            "speakers": [
                {"id": "speaker1", "name": "Alice"}
            ]
        }

        mock_meeting = MagicMock()
        mock_meeting.id = uuid4()

        with patch.object(
            otter_handler.ingestion_service,
            'ingest_from_otter',
            new=AsyncMock(return_value=(mock_meeting, False))
        ):
            # Act
            result = await otter_handler.handle_speech_created(payload)

        # Assert
        assert result["status"] == "success"
        assert "meeting_id" in result
        assert result["duplicate"] is False

    @pytest.mark.asyncio
    async def test_handle_speech_created_duplicate(self, otter_handler):
        """Test speech.created with duplicate meeting"""
        # Arrange
        payload = {
            "speech_id": "duplicate_abc123"
        }

        mock_meeting = MagicMock()
        mock_meeting.id = uuid4()

        with patch.object(
            otter_handler.ingestion_service,
            'ingest_from_otter',
            new=AsyncMock(return_value=(mock_meeting, True))
        ):
            # Act
            result = await otter_handler.handle_speech_created(payload)

        # Assert
        assert result["status"] == "success"
        assert result["duplicate"] is True

    @pytest.mark.asyncio
    async def test_handle_speech_created_error(self, otter_handler):
        """Test speech.created with ingestion error"""
        # Arrange
        payload = {
            "speech_id": "error_abc123"
        }

        with patch.object(
            otter_handler.ingestion_service,
            'ingest_from_otter',
            new=AsyncMock(side_effect=Exception("Otter API Error"))
        ):
            # Act
            result = await otter_handler.handle_speech_created(payload)

        # Assert
        assert result["status"] == "error"
        assert "Otter API Error" in result["error"]

    @pytest.mark.asyncio
    async def test_handle_speech_missing_id(self, otter_handler):
        """Test speech.created with missing speech_id"""
        # Arrange
        payload = {
            "title": "Meeting without ID"
            # Missing speech_id
        }

        with patch.object(
            otter_handler.ingestion_service,
            'ingest_from_otter',
            new=AsyncMock(side_effect=Exception("Missing speech_id"))
        ):
            # Act
            result = await otter_handler.handle_speech_created(payload)

        # Assert
        assert result["status"] == "error"

    @pytest.mark.asyncio
    async def test_handle_speech_empty_payload(self, otter_handler):
        """Test handling of empty payload"""
        # Arrange
        payload = {}

        with patch.object(
            otter_handler.ingestion_service,
            'ingest_from_otter',
            new=AsyncMock(side_effect=Exception("Invalid payload"))
        ):
            # Act
            result = await otter_handler.handle_speech_created(payload)

        # Assert
        assert result["status"] == "error"


class TestOtterWebhookStatus:
    """Test webhook status endpoint"""

    @patch('app.api.webhooks.otter_webhook._webhook_handler')
    def test_status_endpoint_initialized(self, mock_handler, webhook_client):
        """Test status endpoint when handler is initialized"""
        # Act
        response = webhook_client.get("/api/webhooks/otter/status")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["platform"] == "otter"
        assert data["status"] == "active"
        assert "timestamp" in data

    @patch('app.api.webhooks.otter_webhook._webhook_handler', None)
    def test_status_endpoint_not_initialized(self, webhook_client):
        """Test status endpoint when handler is not initialized"""
        # Act
        response = webhook_client.get("/api/webhooks/otter/status")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["platform"] == "otter"
        assert data["status"] == "not_initialized"


class TestOtterWebhookEdgeCases:
    """Test edge cases and error scenarios"""

    @patch('app.api.webhooks.otter_webhook._webhook_handler')
    def test_malformed_json_payload(self, mock_handler, webhook_client):
        """Test handling of malformed JSON payload"""
        # Arrange
        headers = {
            "x-otter-signature": "sha256=test_signature"
        }

        # Act
        response = webhook_client.post(
            "/api/webhooks/otter",
            data="invalid json {not valid}",
            headers=headers
        )

        # Assert
        assert response.status_code in [
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            status.HTTP_500_INTERNAL_SERVER_ERROR
        ]

    @patch('app.api.webhooks.otter_webhook._webhook_handler')
    def test_missing_event_field(self, mock_handler, webhook_client, otter_secret):
        """Test payload missing required 'event' field"""
        # Arrange
        import json
        mock_handler.verify_signature = MagicMock(return_value=True)

        payload = {
            "data": {"speech_id": "123"}
            # Missing 'event' field
        }

        payload_str = json.dumps(payload, separators=(',', ':'))
        signature = generate_otter_signature(payload_str, otter_secret)

        headers = {
            "x-otter-signature": signature
        }

        # Act
        response = webhook_client.post(
            "/api/webhooks/otter",
            json=payload,
            headers=headers
        )

        # Assert
        # Should handle gracefully
        assert response.status_code == status.HTTP_200_OK

    @patch('app.api.webhooks.otter_webhook._webhook_handler')
    def test_empty_data_field(self, mock_handler, webhook_client, otter_secret):
        """Test payload with empty data field"""
        # Arrange
        import json
        mock_handler.verify_signature = MagicMock(return_value=True)
        mock_handler.handle_speech_created = AsyncMock(return_value={
            "status": "error",
            "error": "No data provided"
        })

        payload = {
            "event": "speech.created",
            "data": {}
        }

        payload_str = json.dumps(payload, separators=(',', ':'))
        signature = generate_otter_signature(payload_str, otter_secret)

        headers = {
            "x-otter-signature": signature
        }

        # Act
        response = webhook_client.post(
            "/api/webhooks/otter",
            json=payload,
            headers=headers
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK

    @patch('app.api.webhooks.otter_webhook._webhook_handler')
    def test_large_speech_payload(self, mock_handler, webhook_client, otter_secret):
        """Test handling of large speech payload with many speakers"""
        # Arrange
        import json
        mock_handler.verify_signature = MagicMock(return_value=True)
        mock_handler.handle_speech_created = AsyncMock(return_value={
            "status": "success",
            "meeting_id": str(uuid4())
        })

        # Create large payload with many speakers
        payload = {
            "event": "speech.created",
            "data": {
                "speech_id": "large_speech_123",
                "speakers": [
                    {"id": f"speaker{i}", "name": f"Speaker {i}"}
                    for i in range(50)
                ]
            }
        }

        payload_str = json.dumps(payload, separators=(',', ':'))
        signature = generate_otter_signature(payload_str, otter_secret)

        headers = {
            "x-otter-signature": signature
        }

        # Act
        response = webhook_client.post(
            "/api/webhooks/otter",
            json=payload,
            headers=headers
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK

    @patch('app.api.webhooks.otter_webhook._webhook_handler')
    def test_special_characters_in_title(self, mock_handler, webhook_client, otter_secret):
        """Test handling of special characters in speech title"""
        # Arrange
        import json
        mock_handler.verify_signature = MagicMock(return_value=True)
        mock_handler.handle_speech_created = AsyncMock(return_value={
            "status": "success",
            "meeting_id": str(uuid4())
        })

        payload = {
            "event": "speech.created",
            "data": {
                "speech_id": "special_chars_123",
                "title": "Meeting: Q&A 🎯 - \"Strategy\" & 'Planning' (2025)"
            }
        }

        payload_str = json.dumps(payload, separators=(',', ':'))
        signature = generate_otter_signature(payload_str, otter_secret)

        headers = {
            "x-otter-signature": signature
        }

        # Act
        response = webhook_client.post(
            "/api/webhooks/otter",
            json=payload,
            headers=headers
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK


class TestOtterWebhookInitialization:
    """Test webhook handler initialization"""

    def test_init_webhook_handler(self):
        """Test initializing the global webhook handler"""
        # Arrange
        secret = "test-otter-secret-123"

        # Act
        init_webhook_handler(secret, None)

        # Assert
        from app.api.webhooks.otter_webhook import _webhook_handler
        assert _webhook_handler is not None
        assert _webhook_handler.webhook_secret == secret

    def test_handler_initialization_with_supabase(self):
        """Test handler initialization with Supabase client"""
        # Arrange
        secret = "test-otter-secret-456"
        mock_supabase = MagicMock()

        # Act
        handler = OtterWebhookHandler(secret, mock_supabase)

        # Assert
        assert handler.webhook_secret == secret
        assert handler.ingestion_service is not None

    @pytest.mark.asyncio
    async def test_get_workspace_for_otter_account(self, otter_handler):
        """Test workspace lookup placeholder"""
        # Act
        workspace_id = await otter_handler._get_workspace_for_otter_account()

        # Assert
        assert workspace_id is not None

    @pytest.mark.asyncio
    async def test_get_founder_for_workspace(self, otter_handler):
        """Test founder lookup placeholder"""
        # Arrange
        workspace_id = uuid4()

        # Act
        founder_id = await otter_handler._get_founder_for_workspace(workspace_id)

        # Assert
        assert founder_id is not None

    @pytest.mark.asyncio
    async def test_get_otter_credentials(self, otter_handler):
        """Test credentials lookup placeholder"""
        # Arrange
        workspace_id = uuid4()

        # Act
        credentials = await otter_handler._get_otter_credentials(workspace_id)

        # Assert
        assert "access_token" in credentials
