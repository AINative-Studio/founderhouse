"""
ZeroVoice MCP Connector
Handles voice commands and transcription via Twilio
"""
from typing import Dict, Any, List, Optional

from app.connectors.base_connector import BaseConnector, ConnectorResponse, ConnectorStatus, ConnectorError


class ZeroVoiceConnector(BaseConnector):
    """Connector for ZeroVoice (Twilio-based voice interface)"""

    @property
    def platform_name(self) -> str:
        return "zerovoice"

    @property
    def base_url(self) -> str:
        # Twilio API base URL
        account_sid = self.credentials.get("account_sid", "")
        return f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}"

    def _get_default_headers(self) -> Dict[str, str]:
        """Override to use Basic Auth for Twilio"""
        import base64
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "AI-Chief-of-Staff/1.0"
        }

        # Twilio uses Basic Auth with account_sid:auth_token
        account_sid = self.credentials.get("account_sid", "")
        auth_token = self.credentials.get("auth_token", "")

        if account_sid and auth_token:
            credentials = f"{account_sid}:{auth_token}"
            encoded = base64.b64encode(credentials.encode()).decode()
            headers["Authorization"] = f"Basic {encoded}"

        return headers

    async def test_connection(self) -> ConnectorResponse:
        """Test connection to Twilio API"""
        try:
            self.validate_credentials()
            account_info = await self.get_user_info()
            return ConnectorResponse(
                status=ConnectorStatus.SUCCESS,
                data={"connected": True, "account": account_info.data},
                metadata={"platform": self.platform_name}
            )
        except Exception as e:
            self.logger.error(f"ZeroVoice connection test failed: {str(e)}")
            return ConnectorResponse(
                status=ConnectorStatus.ERROR,
                error=str(e),
                metadata={"platform": self.platform_name}
            )

    async def get_user_info(self) -> ConnectorResponse:
        """Get Twilio account information"""
        return await self.make_request("GET", ".json")

    async def send_sms(
        self,
        to: str,
        from_: str,
        body: str
    ) -> ConnectorResponse:
        """
        Send an SMS message

        Args:
            to: Recipient phone number
            from_: Sender phone number
            body: Message body

        Returns:
            ConnectorResponse with sent message details
        """
        data = {
            "To": to,
            "From": from_,
            "Body": body
        }
        return await self.make_request("POST", "/Messages.json", data=data)

    async def make_call(
        self,
        to: str,
        from_: str,
        twiml_url: str
    ) -> ConnectorResponse:
        """
        Make a voice call

        Args:
            to: Recipient phone number
            from_: Caller phone number
            twiml_url: URL to TwiML instructions

        Returns:
            ConnectorResponse with call details
        """
        data = {
            "To": to,
            "From": from_,
            "Url": twiml_url
        }
        return await self.make_request("POST", "/Calls.json", data=data)

    async def list_recordings(
        self,
        page_size: int = 50
    ) -> ConnectorResponse:
        """
        List call recordings

        Args:
            page_size: Number of recordings per page

        Returns:
            ConnectorResponse with recordings list
        """
        params = {"PageSize": page_size}
        return await self.make_request("GET", "/Recordings.json", params=params)

    async def get_recording(self, recording_sid: str) -> ConnectorResponse:
        """
        Get recording details

        Args:
            recording_sid: Recording SID

        Returns:
            ConnectorResponse with recording details
        """
        return await self.make_request("GET", f"/Recordings/{recording_sid}.json")

    async def download_recording(
        self,
        recording_sid: str,
        format: str = "mp3"
    ) -> ConnectorResponse:
        """
        Download recording audio

        Args:
            recording_sid: Recording SID
            format: Audio format (mp3 or wav)

        Returns:
            ConnectorResponse with audio data
        """
        url = f"/Recordings/{recording_sid}.{format}"
        response = await self.http_client.get(
            f"{self.base_url}{url}",
            headers=self._get_default_headers()
        )

        if response.status_code == 200:
            return ConnectorResponse(
                status=ConnectorStatus.SUCCESS,
                data=response.content,
                metadata={"content_type": f"audio/{format}"}
            )
        else:
            raise ConnectorError(
                f"Failed to download recording: {response.status_code}",
                status_code=response.status_code
            )

    async def transcribe_recording(
        self,
        recording_sid: str
    ) -> ConnectorResponse:
        """
        Get recording transcription

        Args:
            recording_sid: Recording SID

        Returns:
            ConnectorResponse with transcription
        """
        return await self.make_request("GET", f"/Recordings/{recording_sid}/Transcriptions.json")

    async def list_messages(
        self,
        page_size: int = 50
    ) -> ConnectorResponse:
        """
        List SMS messages

        Args:
            page_size: Number of messages per page

        Returns:
            ConnectorResponse with messages list
        """
        params = {"PageSize": page_size}
        return await self.make_request("GET", "/Messages.json", params=params)

    async def get_message(self, message_sid: str) -> ConnectorResponse:
        """
        Get message details

        Args:
            message_sid: Message SID

        Returns:
            ConnectorResponse with message details
        """
        return await self.make_request("GET", f"/Messages/{message_sid}.json")

    async def list_calls(
        self,
        page_size: int = 50,
        status: Optional[str] = None
    ) -> ConnectorResponse:
        """
        List calls

        Args:
            page_size: Number of calls per page
            status: Optional filter by status

        Returns:
            ConnectorResponse with calls list
        """
        params = {"PageSize": page_size}
        if status:
            params["Status"] = status

        return await self.make_request("GET", "/Calls.json", params=params)
