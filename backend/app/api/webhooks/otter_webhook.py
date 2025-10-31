"""
Otter Webhook Handler
Handles Otter transcript events
"""
import hashlib
import hmac
import logging
from typing import Dict, Any
from datetime import datetime

from fastapi import APIRouter, Request, HTTPException, Header, BackgroundTasks

from app.services.meeting_ingestion_service import MeetingIngestionService


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhooks/otter", tags=["webhooks"])


class OtterWebhookHandler:
    """Handle Otter webhooks with signature verification"""

    def __init__(self, webhook_secret: str, supabase_client=None):
        self.webhook_secret = webhook_secret
        self.ingestion_service = MeetingIngestionService(supabase_client)
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def verify_signature(self, payload: str, signature: str) -> bool:
        """Verify Otter webhook signature"""
        try:
            expected_signature = hmac.new(
                self.webhook_secret.encode(),
                payload.encode(),
                hashlib.sha256
            ).hexdigest()
            return hmac.compare_digest(f"sha256={expected_signature}", signature)
        except Exception as e:
            self.logger.error(f"Signature verification failed: {str(e)}")
            return False

    async def handle_speech_created(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle speech created/updated event"""
        try:
            speech_id = payload.get("speech_id")
            self.logger.info(f"Processing speech: {speech_id}")

            workspace_id = await self._get_workspace_for_otter_account()
            founder_id = await self._get_founder_for_workspace(workspace_id)
            credentials = await self._get_otter_credentials(workspace_id)

            meeting, is_duplicate = await self.ingestion_service.ingest_from_otter(
                workspace_id=workspace_id,
                founder_id=founder_id,
                speech_id=speech_id,
                credentials=credentials
            )

            return {
                "status": "success",
                "meeting_id": str(meeting.id),
                "duplicate": is_duplicate
            }

        except Exception as e:
            self.logger.error(f"Failed to handle speech created: {str(e)}")
            return {"status": "error", "error": str(e)}

    async def _get_workspace_for_otter_account(self):
        from uuid import uuid4
        return uuid4()

    async def _get_founder_for_workspace(self, workspace_id):
        from uuid import uuid4
        return uuid4()

    async def _get_otter_credentials(self, workspace_id):
        return {"access_token": "placeholder_token"}


_webhook_handler = None


def init_webhook_handler(webhook_secret: str, supabase_client=None):
    global _webhook_handler
    _webhook_handler = OtterWebhookHandler(webhook_secret, supabase_client)


@router.post("")
async def otter_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_otter_signature: str = Header(None, alias="x-otter-signature")
):
    """Otter webhook endpoint"""
    try:
        body = await request.body()

        if not _webhook_handler:
            raise HTTPException(status_code=500, detail="Webhook handler not initialized")

        if x_otter_signature and not _webhook_handler.verify_signature(
            body.decode(), x_otter_signature
        ):
            logger.warning("Invalid Otter webhook signature")
            raise HTTPException(status_code=401, detail="Invalid signature")

        event_data = await request.json()
        event_type = event_data.get("event")

        logger.info(f"Received Otter webhook: {event_type}")

        if event_type in ["speech.created", "speech.updated"]:
            background_tasks.add_task(
                _webhook_handler.handle_speech_created,
                event_data.get("data", {})
            )
            return {"status": "processing"}

        return {"status": "ignored", "event": event_type}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Otter webhook processing failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def webhook_status():
    return {
        "platform": "otter",
        "status": "active" if _webhook_handler else "not_initialized",
        "timestamp": datetime.utcnow().isoformat()
    }
