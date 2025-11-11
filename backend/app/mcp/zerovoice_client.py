"""
ZeroVoice MCP Client
Client for ZeroVoice Model Context Protocol integration
Handles voice-to-text transcription and intent parsing
"""
import logging
from typing import Optional, Dict, Any, List
import httpx
from datetime import datetime, timedelta

from app.config import get_settings

logger = logging.getLogger(__name__)


class ZeroVoiceClient:
    """
    ZeroVoice MCP client for voice command processing
    Implements voice → intent → action pipeline
    """

    def __init__(self):
        """Initialize ZeroVoice client with settings"""
        self.settings = get_settings()
        self.base_url = self.settings.zerovoice_api_base_url
        self.api_key = self.settings.zerovoice_api_key

        self._access_token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None
        self._client = httpx.AsyncClient(timeout=30.0)

        logger.info("ZeroVoice MCP client initialized")

    async def _ensure_authenticated(self) -> str:
        """
        Ensure we have a valid access token
        Automatically refreshes if expired
        """
        if self._access_token and self._token_expires_at:
            if datetime.utcnow() < self._token_expires_at - timedelta(minutes=5):
                return self._access_token

        # Authenticate using API key
        headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json"
        }

        response = await self._client.post(
            f"{self.base_url}/v1/auth/token",
            headers=headers
        )
        response.raise_for_status()

        data = response.json()
        self._access_token = data["access_token"]
        expires_in = data.get("expires_in", 3600)  # Default 1 hour
        self._token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

        logger.info("ZeroVoice authentication successful")
        return self._access_token

    def _get_headers(self, token: str) -> Dict[str, str]:
        """Get standard headers with authentication"""
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

    async def transcribe_audio(
        self,
        audio_url: Optional[str] = None,
        audio_base64: Optional[str] = None,
        language: str = "en-US",
        include_timestamps: bool = False
    ) -> Dict[str, Any]:
        """
        Transcribe audio to text using ZeroVoice MCP

        Args:
            audio_url: URL to audio file
            audio_base64: Base64-encoded audio data
            language: Language code for transcription
            include_timestamps: Include word-level timestamps

        Returns:
            dict: Transcription result with transcript, confidence, and metadata

        Raises:
            ValueError: If neither audio_url nor audio_base64 provided
            httpx.HTTPError: If API request fails
        """
        if not audio_url and not audio_base64:
            raise ValueError("Either audio_url or audio_base64 must be provided")

        token = await self._ensure_authenticated()

        payload = {
            "language": language,
            "include_timestamps": include_timestamps
        }

        if audio_url:
            payload["audio_url"] = audio_url
        elif audio_base64:
            payload["audio_data"] = audio_base64

        response = await self._client.post(
            f"{self.base_url}/v1/transcribe",
            headers=self._get_headers(token),
            json=payload
        )
        response.raise_for_status()

        result = response.json()
        logger.info(f"Transcription completed with confidence: {result.get('confidence', 0)}")
        return result

    async def parse_intent(
        self,
        transcript: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Parse intent from transcript using ZeroVoice MCP

        Args:
            transcript: Text transcript to analyze
            context: Optional context for better intent recognition

        Returns:
            dict: Intent classification with confidence and extracted entities

        Expected response format:
        {
            "intent": "create_task",
            "confidence": 0.95,
            "entities": {
                "task": "follow up with investors",
                "deadline": "Friday"
            },
            "raw_transcript": "Create a task to follow up with investors by Friday"
        }
        """
        token = await self._ensure_authenticated()

        payload = {
            "transcript": transcript,
            "context": context or {}
        }

        response = await self._client.post(
            f"{self.base_url}/v1/intent/parse",
            headers=self._get_headers(token),
            json=payload
        )
        response.raise_for_status()

        result = response.json()
        logger.info(f"Intent parsed: {result.get('intent')} (confidence: {result.get('confidence', 0)})")
        return result

    async def process_voice_command(
        self,
        audio_url: Optional[str] = None,
        audio_base64: Optional[str] = None,
        transcript: Optional[str] = None,
        language: str = "en-US",
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Complete voice command pipeline: voice → intent → action

        Processes voice command in < 2.5s end-to-end (per PRD requirement)

        Args:
            audio_url: URL to audio file (optional if transcript provided)
            audio_base64: Base64-encoded audio (optional if transcript provided)
            transcript: Pre-transcribed text (optional if audio provided)
            language: Language code for transcription
            context: Optional context for better processing

        Returns:
            dict: Complete processing result with transcript, intent, and entities

        Example response:
        {
            "transcript": "Create a task to follow up with investors by Friday",
            "intent": "create_task",
            "confidence": 0.95,
            "entities": {
                "task": "follow up with investors",
                "deadline": "Friday"
            },
            "processing_time_ms": 1850,
            "transcription_time_ms": 800,
            "intent_parsing_time_ms": 1050
        }
        """
        import time
        start_time = time.time()

        # Step 1: Get transcript (if not provided)
        transcription_time_ms = 0
        if not transcript:
            if not audio_url and not audio_base64:
                raise ValueError("Either transcript or audio must be provided")

            transcribe_start = time.time()
            transcription = await self.transcribe_audio(
                audio_url=audio_url,
                audio_base64=audio_base64,
                language=language
            )
            transcript = transcription["transcript"]
            transcription_time_ms = int((time.time() - transcribe_start) * 1000)

        # Step 2: Parse intent
        intent_start = time.time()
        intent_result = await self.parse_intent(transcript, context)
        intent_parsing_time_ms = int((time.time() - intent_start) * 1000)

        # Calculate total processing time
        processing_time_ms = int((time.time() - start_time) * 1000)

        # Log performance
        if processing_time_ms > 2500:
            logger.warning(f"Voice command processing exceeded 2.5s target: {processing_time_ms}ms")
        else:
            logger.info(f"Voice command processed in {processing_time_ms}ms (< 2.5s target)")

        return {
            "transcript": transcript,
            "intent": intent_result.get("intent"),
            "confidence": intent_result.get("confidence"),
            "entities": intent_result.get("entities", {}),
            "processing_time_ms": processing_time_ms,
            "transcription_time_ms": transcription_time_ms,
            "intent_parsing_time_ms": intent_parsing_time_ms
        }

    async def health_check(self) -> Dict[str, Any]:
        """
        Check ZeroVoice service health

        Returns:
            dict: Service health status
        """
        try:
            response = await self._client.get(
                f"{self.base_url}/v1/health"
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"ZeroVoice health check failed: {str(e)}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }

    async def close(self):
        """Close HTTP client"""
        await self._client.aclose()
        logger.info("ZeroVoice client closed")


# Global ZeroVoice client instance
zerovoice_client = ZeroVoiceClient()


def get_zerovoice() -> ZeroVoiceClient:
    """
    Dependency injection for FastAPI routes

    Usage:
        @app.post("/voice/command")
        async def command(client: ZeroVoiceClient = Depends(get_zerovoice)):
            await client.process_voice_command(...)
    """
    return zerovoice_client
