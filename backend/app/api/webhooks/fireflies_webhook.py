"""
Fireflies Webhook Handler
Handles Fireflies transcript ready events
"""
import hashlib
import hmac
import logging
from typing import Dict, Any
from datetime import datetime

from fastapi import APIRouter, Request, HTTPException, Header, BackgroundTasks

from app.services.meeting_ingestion_service import MeetingIngestionService


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhooks/fireflies", tags=["webhooks"])


class FirefliesWebhookHandler:
    """Handle Fireflies webhooks with signature verification"""

    def __init__(self, webhook_secret: str, supabase_client=None):
        self.webhook_secret = webhook_secret
        self.ingestion_service = MeetingIngestionService(supabase_client)
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def verify_signature(self, payload: str, signature: str) -> bool:
        """Verify Fireflies webhook signature"""
        try:
            expected_signature = hmac.new(
                self.webhook_secret.encode(),
                payload.encode(),
                hashlib.sha256
            ).hexdigest()
            return hmac.compare_digest(expected_signature, signature)
        except Exception as e:
            self.logger.error(f"Signature verification failed: {str(e)}")
            return False

    async def handle_transcript_ready(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle transcript ready event"""
        try:
            transcript_id = payload.get("transcript_id")
            self.logger.info(f"Processing transcript ready: {transcript_id}")

            # Get workspace info (placeholder)
            workspace_id = await self._get_workspace_for_fireflies_account()
            founder_id = await self._get_founder_for_workspace(workspace_id)
            credentials = await self._get_fireflies_credentials(workspace_id)

            # Ingest transcript
            meeting, is_duplicate = await self.ingestion_service.ingest_from_fireflies(
                workspace_id=workspace_id,
                founder_id=founder_id,
                transcript_id=transcript_id,
                credentials=credentials
            )

            return {
                "status": "success",
                "meeting_id": str(meeting.id),
                "duplicate": is_duplicate
            }

        except Exception as e:
            self.logger.error(f"Failed to handle transcript ready: {str(e)}")
            return {"status": "error", "error": str(e)}

    async def _get_workspace_for_fireflies_account(self):
        from uuid import uuid4
        return uuid4()

    async def _get_founder_for_workspace(self, workspace_id):
        from uuid import uuid4
        return uuid4()

    async def _get_fireflies_credentials(self, workspace_id):
        return {"api_key": "placeholder_key"}


_webhook_handler = None


def init_webhook_handler(webhook_secret: str, supabase_client=None):
    global _webhook_handler
    _webhook_handler = FirefliesWebhookHandler(webhook_secret, supabase_client)


@router.post("")
async def fireflies_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_fireflies_signature: str = Header(None, alias="x-fireflies-signature")
):
    """Fireflies webhook endpoint"""
    try:
        body = await request.body()

        if not _webhook_handler:
            raise HTTPException(status_code=500, detail="Webhook handler not initialized")

        # Verify signature if present
        if x_fireflies_signature and not _webhook_handler.verify_signature(
            body.decode(), x_fireflies_signature
        ):
            logger.warning("Invalid Fireflies webhook signature")
            raise HTTPException(status_code=401, detail="Invalid signature")

        event_data = await request.json()
        event_type = event_data.get("event")

        logger.info(f"Received Fireflies webhook: {event_type}")

        if event_type == "transcript.ready":
            background_tasks.add_task(
                _webhook_handler.handle_transcript_ready,
                event_data.get("data", {})
            )
            return {"status": "processing"}

        return {"status": "ignored", "event": event_type}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Fireflies webhook processing failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def webhook_status():
    return {
        "platform": "fireflies",
        "status": "active" if _webhook_handler else "not_initialized",
        "timestamp": datetime.utcnow().isoformat()
    }
