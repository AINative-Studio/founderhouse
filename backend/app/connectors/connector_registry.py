"""
Connector Registry
Factory for creating platform-specific connectors
"""
import logging
from typing import Dict, Any, Optional, Type

from app.connectors.base_connector import BaseConnector
from app.connectors.zoom_connector import ZoomConnector
from app.connectors.slack_connector import SlackConnector
from app.connectors.discord_connector import DiscordConnector
from app.connectors.outlook_connector import OutlookConnector
from app.connectors.monday_connector import MondayConnector
from app.connectors.gmail_connector import GmailConnector
from app.connectors.notion_connector import NotionConnector
from app.connectors.loom_connector import LoomConnector
from app.connectors.fireflies_connector import FirefliesConnector
from app.connectors.otter_connector import OtterConnector
from app.connectors.granola_connector import GranolaConnector
from app.connectors.zerodb_connector import ZeroDBConnector
from app.connectors.zerovoice_connector import ZeroVoiceConnector


logger = logging.getLogger(__name__)


# Connector class mapping
CONNECTOR_REGISTRY: Dict[str, Type[BaseConnector]] = {
    "zoom": ZoomConnector,
    "slack": SlackConnector,
    "discord": DiscordConnector,
    "outlook": OutlookConnector,
    "monday": MondayConnector,
    "gmail": GmailConnector,
    "notion": NotionConnector,
    "loom": LoomConnector,
    "fireflies": FirefliesConnector,
    "otter": OtterConnector,
    "granola": GranolaConnector,
    "zerodb": ZeroDBConnector,
    "zerovoice": ZeroVoiceConnector,
}


def get_connector(
    platform: str,
    credentials: Dict[str, Any],
    config: Optional[Dict[str, Any]] = None
) -> BaseConnector:
    """
    Get connector instance for a platform

    Args:
        platform: Platform identifier (zoom, slack, discord, etc.)
        credentials: Platform credentials
        config: Optional configuration

    Returns:
        Initialized connector instance

    Raises:
        ValueError: If platform is not supported

    Example:
        >>> credentials = {"access_token": "abc123"}
        >>> connector = get_connector("zoom", credentials)
        >>> async with connector:
        ...     result = await connector.test_connection()
    """
    platform_lower = platform.lower()

    if platform_lower not in CONNECTOR_REGISTRY:
        available = ", ".join(CONNECTOR_REGISTRY.keys())
        raise ValueError(
            f"Unsupported platform: {platform}. "
            f"Available platforms: {available}"
        )

    connector_class = CONNECTOR_REGISTRY[platform_lower]
    logger.info(f"Creating connector for platform: {platform}")

    return connector_class(credentials=credentials, config=config or {})


def list_supported_platforms() -> Dict[str, str]:
    """
    List all supported platforms

    Returns:
        Dictionary mapping platform names to connector class names
    """
    return {
        platform: connector_class.__name__
        for platform, connector_class in CONNECTOR_REGISTRY.items()
    }


def is_platform_supported(platform: str) -> bool:
    """
    Check if a platform is supported

    Args:
        platform: Platform identifier

    Returns:
        True if platform is supported
    """
    return platform.lower() in CONNECTOR_REGISTRY


async def test_connector_connection(
    platform: str,
    credentials: Dict[str, Any],
    config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Test connection for a platform connector

    Args:
        platform: Platform identifier
        credentials: Platform credentials
        config: Optional configuration

    Returns:
        Connection test result dictionary

    Raises:
        ValueError: If platform is not supported
    """
    connector = get_connector(platform, credentials, config)

    try:
        async with connector:
            result = await connector.test_connection()
            return {
                "platform": platform,
                "status": result.status.value,
                "connected": result.status.value == "success",
                "error": result.error,
                "data": result.data,
                "timestamp": result.timestamp.isoformat()
            }
    except Exception as e:
        logger.error(f"Connector test failed for {platform}: {str(e)}")
        return {
            "platform": platform,
            "status": "error",
            "connected": False,
            "error": str(e),
            "data": None,
            "timestamp": None
        }
