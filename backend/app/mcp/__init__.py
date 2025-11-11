"""
MCP (Model Context Protocol) Integration Layer
Provides integration with external AI services and voice systems
"""
from app.mcp.zerovoice_client import ZeroVoiceClient
from app.mcp.loom_client import LoomMCPClient

__all__ = ["ZeroVoiceClient", "LoomMCPClient"]
