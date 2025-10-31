"""
Zoom Webhook Handler
Handles Zoom recording completed events
"""
import hashlib
import hmac
import logging
from typing import Dict, Any
from datetime import datetime

from fastapi import APIRouter, Request, HTTPException, Header, BackgroundTasks
from pydantic import BaseModel

from app.services.meeting_ingestion_service import MeetingIngestionService


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhooks/zoom", tags=["webhooks"])


class ZoomWebhookEvent(BaseModel):
    """Zoom webhook event schema"""
    event: str
    event_ts: int
    payload: Dict[str, Any]


class ZoomWebhookHandler:
    """
    Handle Zoom webhooks with signature verification

    Supported events:
    - recording.completed: Recording ready for download
    - meeting.ended: Meeting ended
    """

    def __init__(self, secret_token: str, supabase_client=None):
        """
        Initialize handler

        Args:
            secret_token: Zoom webhook secret token for verification
            supabase_client: Supabase client
        """
        self.secret_token = secret_token
        self.ingestion_service = MeetingIngestionService(supabase_client)
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def verify_signature(
        self,
        request_body: bytes,
        timestamp: str,
        signature: str
    ) -> bool:
        """
        Verify Zoom webhook signature

        Args:
            request_body: Raw request body
            timestamp: Timestamp from header
            signature: Signature from header

        Returns:
            True if signature is valid
        """
        try:
            # Zoom signature format: v0={timestamp}.{request_body}
            message = f"v0:{timestamp}:{request_body.decode()}"

            # Calculate HMAC
            expected_signature = hmac.new(
                self.secret_token.encode(),
                message.encode(),
                hashlib.sha256
            ).hexdigest()

            # Compare signatures
            expected = f"v0={expected_signature}"
            return hmac.compare_digest(expected, signature)

        except Exception as e:
            self.logger.error(f"Signature verification failed: {str(e)}")
            return False

    async def handle_recording_completed(
        self,
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle recording completed event

        Args:
            payload: Webhook payload

        Returns:
            Processing result
        """
        try:
            # Extract meeting details
            meeting_object = payload.get("object", {})
            meeting_id = meeting_object.get("id")
            meeting_uuid = meeting_object.get("uuid")
            topic = meeting_object.get("topic", "Untitled Meeting")

            self.logger.info(f"Processing recording completed for meeting {meeting_id}")

            # Get workspace and founder from database
            # In production, you'd look up which workspace owns this Zoom account
            workspace_id = await self._get_workspace_for_zoom_account(meeting_object.get("host_email"))
            if not workspace_id:
                self.logger.warning(f"No workspace found for Zoom meeting {meeting_id}")
                return {"status": "skipped", "reason": "no_workspace"}

            founder_id = await self._get_founder_for_workspace(workspace_id)

            # Get Zoom credentials for this workspace
            credentials = await self._get_zoom_credentials(workspace_id)

            # Ingest meeting (async in background)
            meeting, is_duplicate = await self.ingestion_service.ingest_from_zoom(
                workspace_id=workspace_id,
                founder_id=founder_id,
                meeting_id=str(meeting_id),
                credentials=credentials
            )

            return {
                "status": "success",
                "meeting_id": str(meeting.id),
                "duplicate": is_duplicate,
                "message": f"Recording ingested for meeting: {topic}"
            }

        except Exception as e:
            self.logger.error(f"Failed to handle recording completed: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }

    async def handle_meeting_ended(
        self,
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle meeting ended event

        Args:
            payload: Webhook payload

        Returns:
            Processing result
        """
        try:
            meeting_object = payload.get("object", {})
            meeting_id = meeting_object.get("id")

            self.logger.info(f"Meeting ended: {meeting_id}")

            # Log event for tracking
            # In production, you might want to update meeting status
            return {
                "status": "logged",
                "meeting_id": meeting_id
            }

        except Exception as e:
            self.logger.error(f"Failed to handle meeting ended: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }

    async def _get_workspace_for_zoom_account(self, host_email: str):
        """Get workspace ID for Zoom account (placeholder)"""
        # In production, query database for workspace with this Zoom account
        # For now, return a mock UUID
        from uuid import uuid4
        return uuid4()

    async def _get_founder_for_workspace(self, workspace_id):
        """Get founder ID for workspace (placeholder)"""
        from uuid import uuid4
        return uuid4()

    async def _get_zoom_credentials(self, workspace_id) -> Dict[str, Any]:
        """Get Zoom credentials for workspace (placeholder)"""
        # In production, fetch encrypted credentials from database
        return {
            "access_token": "placeholder_token"
        }


# Global handler instance (will be initialized with config)
_webhook_handler = None


def init_webhook_handler(secret_token: str, supabase_client=None):
    """Initialize global webhook handler"""
    global _webhook_handler
    _webhook_handler = ZoomWebhookHandler(secret_token, supabase_client)


@router.post("")
async def zoom_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_zm_signature: str = Header(None, alias="x-zm-signature"),
    x_zm_request_timestamp: str = Header(None, alias="x-zm-request-timestamp")
):
    """
    Zoom webhook endpoint

    Handles:
    - Signature verification
    - Event routing
    - Deduplication
    """
    try:
        # Read raw body for signature verification
        body = await request.body()

        # Verify signature
        if not _webhook_handler:
            raise HTTPException(status_code=500, detail="Webhook handler not initialized")

        if x_zm_signature and not _webhook_handler.verify_signature(
            body, x_zm_request_timestamp, x_zm_signature
        ):
            logger.warning("Invalid Zoom webhook signature")
            raise HTTPException(status_code=401, detail="Invalid signature")

        # Parse event
        event_data = await request.json()
        event_type = event_data.get("event")

        logger.info(f"Received Zoom webhook: {event_type}")

        # Handle URL verification challenge
        if event_type == "endpoint.url_validation":
            return {
                "plainToken": event_data.get("payload", {}).get("plainToken"),
                "encryptedToken": event_data.get("payload", {}).get("encryptedToken")
            }

        # Route event to appropriate handler
        if event_type == "recording.completed":
            # Process in background to avoid timeout
            background_tasks.add_task(
                _webhook_handler.handle_recording_completed,
                event_data.get("payload", {})
            )
            return {"status": "processing"}

        elif event_type == "meeting.ended":
            result = await _webhook_handler.handle_meeting_ended(
                event_data.get("payload", {})
            )
            return result

        else:
            logger.info(f"Unhandled Zoom event type: {event_type}")
            return {"status": "ignored", "event": event_type}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Zoom webhook processing failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def webhook_status():
    """Check webhook handler status"""
    return {
        "platform": "zoom",
        "status": "active" if _webhook_handler else "not_initialized",
        "timestamp": datetime.utcnow().isoformat()
    }
