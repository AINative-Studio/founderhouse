"""
Base Connector
Abstract base class for all MCP and API connectors
"""
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum

import httpx
from pydantic import BaseModel, Field


logger = logging.getLogger(__name__)


class ConnectorStatus(str, Enum):
    """Connector operation status"""
    SUCCESS = "success"
    ERROR = "error"
    PARTIAL = "partial"
    TIMEOUT = "timeout"


class ConnectorResponse(BaseModel):
    """Standard response from connector operations"""
    status: ConnectorStatus
    data: Optional[Any] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ConnectorError(Exception):
    """Custom exception for connector errors"""

    def __init__(self, message: str, status_code: Optional[int] = None, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class BaseConnector(ABC):
    """
    Abstract base class for all platform connectors

    Provides common functionality for:
    - Connection testing
    - Authentication management
    - Rate limiting
    - Error handling
    - Data transformation
    """

    def __init__(self, credentials: Dict[str, Any], config: Optional[Dict[str, Any]] = None):
        """
        Initialize connector

        Args:
            credentials: Platform-specific credentials (access tokens, API keys, etc.)
            config: Optional configuration parameters
        """
        self.credentials = credentials
        self.config = config or {}
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._http_client: Optional[httpx.AsyncClient] = None

    @property
    @abstractmethod
    def platform_name(self) -> str:
        """Platform name identifier"""
        pass

    @property
    @abstractmethod
    def base_url(self) -> str:
        """Base API URL for the platform"""
        pass

    @property
    def http_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client"""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                timeout=30.0,
                headers=self._get_default_headers()
            )
        return self._http_client

    def _get_default_headers(self) -> Dict[str, str]:
        """
        Get default HTTP headers for API requests
        Override in subclasses for platform-specific headers

        Returns:
            Dictionary of HTTP headers
        """
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "AI-Chief-of-Staff/1.0"
        }

        # Add authorization header if access token is present
        access_token = self.credentials.get("access_token")
        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"

        # Add API key header if present
        api_key = self.credentials.get("api_key") or self.credentials.get("api_token")
        if api_key and "Authorization" not in headers:
            headers["Authorization"] = f"Bearer {api_key}"

        return headers

    async def close(self):
        """Close HTTP client and cleanup resources"""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None

    @abstractmethod
    async def test_connection(self) -> ConnectorResponse:
        """
        Test connection to the platform

        Returns:
            ConnectorResponse with connection status

        Raises:
            ConnectorError: If connection test fails
        """
        pass

    @abstractmethod
    async def get_user_info(self) -> ConnectorResponse:
        """
        Get authenticated user information

        Returns:
            ConnectorResponse with user data

        Raises:
            ConnectorError: If user info retrieval fails
        """
        pass

    async def make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None
    ) -> ConnectorResponse:
        """
        Make HTTP request to platform API

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, etc.)
            endpoint: API endpoint (will be appended to base_url)
            params: Query parameters
            data: Form data
            json: JSON body
            headers: Additional headers
            timeout: Request timeout in seconds

        Returns:
            ConnectorResponse with API response

        Raises:
            ConnectorError: If request fails
        """
        try:
            url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"

            # Merge custom headers with defaults
            request_headers = self._get_default_headers()
            if headers:
                request_headers.update(headers)

            self.logger.debug(f"Making {method} request to {url}")

            response = await self.http_client.request(
                method=method,
                url=url,
                params=params,
                data=data,
                json=json,
                headers=request_headers,
                timeout=timeout or 30.0
            )

            # Check for HTTP errors
            if response.status_code >= 400:
                error_msg = f"API request failed with status {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg += f": {error_data}"
                except:
                    error_msg += f": {response.text}"

                self.logger.error(error_msg)
                raise ConnectorError(
                    error_msg,
                    status_code=response.status_code,
                    details={"response": response.text}
                )

            # Parse response
            try:
                response_data = response.json()
            except:
                response_data = response.text

            return ConnectorResponse(
                status=ConnectorStatus.SUCCESS,
                data=response_data,
                metadata={
                    "status_code": response.status_code,
                    "url": url,
                    "method": method
                }
            )

        except ConnectorError:
            raise
        except httpx.TimeoutException as e:
            self.logger.error(f"Request timeout: {str(e)}")
            raise ConnectorError(
                f"Request timeout after {timeout or 30.0} seconds",
                details={"url": url, "method": method}
            )
        except Exception as e:
            self.logger.error(f"Request failed: {str(e)}")
            raise ConnectorError(
                f"Request failed: {str(e)}",
                details={"url": url, "method": method}
            )

    async def handle_rate_limit(self, response: httpx.Response) -> bool:
        """
        Handle rate limiting from platform API
        Override in subclasses for platform-specific rate limit handling

        Args:
            response: HTTP response object

        Returns:
            True if rate limited, False otherwise
        """
        if response.status_code == 429:
            self.logger.warning(f"Rate limited by {self.platform_name} API")
            return True
        return False

    def validate_credentials(self) -> bool:
        """
        Validate that required credentials are present
        Override in subclasses for platform-specific validation

        Returns:
            True if credentials are valid

        Raises:
            ConnectorError: If credentials are invalid
        """
        if not self.credentials:
            raise ConnectorError("No credentials provided")
        return True

    async def __aenter__(self):
        """Context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup resources"""
        await self.close()
