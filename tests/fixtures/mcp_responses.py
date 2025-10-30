"""
AI Chief of Staff - Mock MCP Response Fixtures
Sprint 2: MCP Integration Framework Testing

This module provides mock responses for all MCP integration platforms.
Used for testing OAuth flows, API calls, and error handling without
requiring actual platform credentials.
"""

from datetime import datetime, timedelta
from typing import Dict, Any
from uuid import uuid4


# ============================================================================
# OAUTH TOKEN RESPONSES
# ============================================================================

def get_oauth_token_response(
    platform: str = "zoom",
    access_token: str = None,
    refresh_token: str = None,
    expires_in: int = 3600
) -> Dict[str, Any]:
    """
    Generate mock OAuth token exchange response

    Args:
        platform: Platform name (zoom, slack, etc.)
        access_token: Access token (auto-generated if None)
        refresh_token: Refresh token (auto-generated if None)
        expires_in: Token expiry in seconds

    Returns:
        OAuth token response dictionary
    """
    return {
        "access_token": access_token or f"mock_access_token_{platform}_{uuid4().hex[:8]}",
        "token_type": "Bearer",
        "refresh_token": refresh_token or f"mock_refresh_token_{platform}_{uuid4().hex[:8]}",
        "expires_in": expires_in,
        "scope": "read write",
        "created_at": int(datetime.utcnow().timestamp())
    }


def get_oauth_refresh_response(
    platform: str = "zoom",
    access_token: str = None,
    expires_in: int = 3600
) -> Dict[str, Any]:
    """
    Generate mock OAuth refresh token response

    Args:
        platform: Platform name
        access_token: New access token (auto-generated if None)
        expires_in: Token expiry in seconds

    Returns:
        OAuth refresh response dictionary
    """
    return {
        "access_token": access_token or f"mock_refreshed_token_{platform}_{uuid4().hex[:8]}",
        "token_type": "Bearer",
        "expires_in": expires_in,
        "scope": "read write",
        "created_at": int(datetime.utcnow().timestamp())
    }


def get_expired_token_error() -> Dict[str, Any]:
    """Generate mock expired token error response"""
    return {
        "error": "invalid_grant",
        "error_description": "Token has expired",
        "status_code": 401
    }


def get_invalid_token_error() -> Dict[str, Any]:
    """Generate mock invalid token error response"""
    return {
        "error": "invalid_token",
        "error_description": "The access token is invalid",
        "status_code": 401
    }


# ============================================================================
# ZOOM MCP RESPONSES
# ============================================================================

def get_zoom_user_info() -> Dict[str, Any]:
    """Mock Zoom user info response"""
    return {
        "id": f"zoom_user_{uuid4().hex[:8]}",
        "first_name": "Test",
        "last_name": "User",
        "email": "test.user@example.com",
        "type": 2,
        "status": "active",
        "created_at": datetime.utcnow().isoformat(),
        "timezone": "America/Los_Angeles",
        "verified": 1
    }


def get_zoom_meetings_list(count: int = 5) -> Dict[str, Any]:
    """
    Mock Zoom meetings list response

    Args:
        count: Number of meetings to generate

    Returns:
        Zoom meetings list response
    """
    meetings = []
    for i in range(count):
        start_time = datetime.utcnow() + timedelta(days=i, hours=10)
        meetings.append({
            "uuid": str(uuid4()),
            "id": 10000000000 + i,
            "host_id": f"zoom_host_{uuid4().hex[:8]}",
            "topic": f"Test Meeting {i + 1}",
            "type": 2,  # Scheduled meeting
            "start_time": start_time.isoformat() + "Z",
            "duration": 60,
            "timezone": "America/Los_Angeles",
            "agenda": f"Agenda for meeting {i + 1}",
            "created_at": datetime.utcnow().isoformat() + "Z",
            "join_url": f"https://zoom.us/j/{10000000000 + i}"
        })

    return {
        "page_count": 1,
        "page_number": 1,
        "page_size": count,
        "total_records": count,
        "meetings": meetings
    }


def get_zoom_meeting_detail(meeting_id: str = None) -> Dict[str, Any]:
    """Mock Zoom meeting detail response"""
    return {
        "uuid": meeting_id or str(uuid4()),
        "id": 10000000000,
        "host_id": f"zoom_host_{uuid4().hex[:8]}",
        "topic": "Detailed Test Meeting",
        "type": 2,
        "start_time": (datetime.utcnow() + timedelta(hours=1)).isoformat() + "Z",
        "duration": 60,
        "timezone": "America/Los_Angeles",
        "agenda": "Test meeting agenda",
        "start_url": "https://zoom.us/s/10000000000",
        "join_url": "https://zoom.us/j/10000000000",
        "password": "test123",
        "h323_password": "123456",
        "settings": {
            "host_video": True,
            "participant_video": True,
            "audio": "both",
            "auto_recording": "cloud"
        }
    }


# ============================================================================
# SLACK MCP RESPONSES
# ============================================================================

def get_slack_auth_test() -> Dict[str, Any]:
    """Mock Slack auth.test response"""
    return {
        "ok": True,
        "url": "https://testworkspace.slack.com/",
        "team": "Test Workspace",
        "user": "testuser",
        "team_id": f"T{uuid4().hex[:8].upper()}",
        "user_id": f"U{uuid4().hex[:8].upper()}",
        "bot_id": f"B{uuid4().hex[:8].upper()}",
        "is_enterprise_install": False
    }


def get_slack_messages_list(count: int = 10) -> Dict[str, Any]:
    """
    Mock Slack conversations.history response

    Args:
        count: Number of messages to generate

    Returns:
        Slack messages list response
    """
    messages = []
    base_ts = datetime.utcnow().timestamp()

    for i in range(count):
        ts = base_ts - (i * 3600)  # 1 hour apart
        messages.append({
            "type": "message",
            "user": f"U{uuid4().hex[:8].upper()}",
            "text": f"Test message {i + 1}",
            "ts": str(ts),
            "team": f"T{uuid4().hex[:8].upper()}",
            "client_msg_id": str(uuid4()),
            "reactions": [] if i % 3 else [{"name": "thumbsup", "count": 2}]
        })

    return {
        "ok": True,
        "messages": messages,
        "has_more": False,
        "pin_count": 0,
        "channel_actions_ts": None,
        "channel_actions_count": 0
    }


def get_slack_channel_info() -> Dict[str, Any]:
    """Mock Slack conversations.info response"""
    return {
        "ok": True,
        "channel": {
            "id": f"C{uuid4().hex[:8].upper()}",
            "name": "general",
            "is_channel": True,
            "is_group": False,
            "is_im": False,
            "is_mpim": False,
            "is_private": False,
            "created": int(datetime.utcnow().timestamp()),
            "is_archived": False,
            "is_general": True,
            "unlinked": 0,
            "name_normalized": "general",
            "is_shared": False,
            "is_org_shared": False,
            "is_member": True,
            "is_pending_ext_shared": False,
            "pending_shared": [],
            "topic": {
                "value": "Test channel topic",
                "creator": f"U{uuid4().hex[:8].upper()}",
                "last_set": int(datetime.utcnow().timestamp())
            },
            "purpose": {
                "value": "Test channel purpose",
                "creator": f"U{uuid4().hex[:8].upper()}",
                "last_set": int(datetime.utcnow().timestamp())
            }
        }
    }


# ============================================================================
# DISCORD MCP RESPONSES
# ============================================================================

def get_discord_user_info() -> Dict[str, Any]:
    """Mock Discord user info response"""
    return {
        "id": str(uuid4().int)[:18],
        "username": "testuser",
        "discriminator": "1234",
        "avatar": "test_avatar_hash",
        "bot": True,
        "system": False,
        "mfa_enabled": True,
        "verified": True,
        "email": "bot@example.com",
        "flags": 0,
        "premium_type": 0,
        "public_flags": 0
    }


def get_discord_guild_channels(count: int = 5) -> list[Dict[str, Any]]:
    """
    Mock Discord guild channels list

    Args:
        count: Number of channels to generate

    Returns:
        List of Discord channels
    """
    channels = []
    for i in range(count):
        channels.append({
            "id": str(uuid4().int)[:18],
            "type": 0,  # GUILD_TEXT
            "name": f"test-channel-{i + 1}",
            "position": i,
            "permission_overwrites": [],
            "rate_limit_per_user": 0,
            "nsfw": False,
            "topic": f"Test channel {i + 1} topic",
            "last_message_id": str(uuid4().int)[:18],
            "parent_id": None
        })

    return channels


def get_discord_messages_list(count: int = 10) -> list[Dict[str, Any]]:
    """
    Mock Discord channel messages

    Args:
        count: Number of messages to generate

    Returns:
        List of Discord messages
    """
    messages = []
    for i in range(count):
        timestamp = datetime.utcnow() - timedelta(hours=i)
        messages.append({
            "id": str(uuid4().int)[:18],
            "type": 0,
            "content": f"Test message {i + 1}",
            "channel_id": str(uuid4().int)[:18],
            "author": {
                "id": str(uuid4().int)[:18],
                "username": f"user{i}",
                "discriminator": "0001",
                "avatar": "avatar_hash"
            },
            "timestamp": timestamp.isoformat(),
            "edited_timestamp": None,
            "tts": False,
            "mention_everyone": False,
            "mentions": [],
            "mention_roles": [],
            "attachments": [],
            "embeds": [],
            "reactions": [],
            "pinned": False
        })

    return messages


# ============================================================================
# OUTLOOK MCP RESPONSES
# ============================================================================

def get_outlook_user_profile() -> Dict[str, Any]:
    """Mock Outlook/Microsoft Graph user profile response"""
    return {
        "id": str(uuid4()),
        "userPrincipalName": "test.user@example.com",
        "displayName": "Test User",
        "givenName": "Test",
        "surname": "User",
        "mail": "test.user@example.com",
        "mobilePhone": "+1-555-0123",
        "officeLocation": "Building 1",
        "preferredLanguage": "en-US",
        "jobTitle": "Software Engineer"
    }


def get_outlook_messages_list(count: int = 10) -> Dict[str, Any]:
    """
    Mock Outlook messages list response

    Args:
        count: Number of messages to generate

    Returns:
        Outlook messages response
    """
    messages = []
    for i in range(count):
        timestamp = datetime.utcnow() - timedelta(hours=i)
        messages.append({
            "id": str(uuid4()),
            "createdDateTime": timestamp.isoformat() + "Z",
            "lastModifiedDateTime": timestamp.isoformat() + "Z",
            "receivedDateTime": timestamp.isoformat() + "Z",
            "sentDateTime": timestamp.isoformat() + "Z",
            "hasAttachments": False,
            "internetMessageId": f"<{uuid4()}@example.com>",
            "subject": f"Test Email {i + 1}",
            "bodyPreview": f"Preview of test email {i + 1}...",
            "importance": "normal",
            "conversationId": str(uuid4()),
            "isRead": i % 2 == 0,
            "isDraft": False,
            "webLink": f"https://outlook.office365.com/mail/inbox/id/{uuid4()}",
            "from": {
                "emailAddress": {
                    "name": f"Sender {i}",
                    "address": f"sender{i}@example.com"
                }
            },
            "toRecipients": [
                {
                    "emailAddress": {
                        "name": "Test User",
                        "address": "test.user@example.com"
                    }
                }
            ],
            "body": {
                "contentType": "html",
                "content": f"<html><body>Test email content {i + 1}</body></html>"
            }
        })

    return {
        "@odata.context": "https://graph.microsoft.com/v1.0/$metadata#users('id')/messages",
        "@odata.nextLink": None,
        "value": messages
    }


# ============================================================================
# MONDAY.COM MCP RESPONSES
# ============================================================================

def get_monday_user_info() -> Dict[str, Any]:
    """Mock Monday.com user info response"""
    return {
        "data": {
            "me": {
                "id": str(uuid4().int)[:10],
                "name": "Test User",
                "email": "test.user@example.com",
                "enabled": True,
                "is_admin": True,
                "is_guest": False,
                "is_pending": False,
                "is_view_only": False,
                "created_at": datetime.utcnow().isoformat(),
                "time_zone_identifier": "America/Los_Angeles"
            }
        }
    }


def get_monday_boards_list(count: int = 3) -> Dict[str, Any]:
    """
    Mock Monday.com boards list response

    Args:
        count: Number of boards to generate

    Returns:
        Monday.com boards response
    """
    boards = []
    for i in range(count):
        boards.append({
            "id": str(uuid4().int)[:10],
            "name": f"Test Board {i + 1}",
            "description": f"Description for board {i + 1}",
            "state": "active",
            "board_folder_id": None,
            "board_kind": "public",
            "permissions": "everyone",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        })

    return {
        "data": {
            "boards": boards
        }
    }


def get_monday_create_item_response() -> Dict[str, Any]:
    """Mock Monday.com create item response"""
    return {
        "data": {
            "create_item": {
                "id": str(uuid4().int)[:10],
                "name": "Test Task",
                "state": "active",
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "column_values": []
            }
        }
    }


# ============================================================================
# NOTION MCP RESPONSES
# ============================================================================

def get_notion_user_info() -> Dict[str, Any]:
    """Mock Notion user info response"""
    return {
        "object": "user",
        "id": str(uuid4()),
        "type": "person",
        "person": {
            "email": "test.user@example.com"
        },
        "name": "Test User",
        "avatar_url": "https://example.com/avatar.png"
    }


def get_notion_databases_list(count: int = 3) -> Dict[str, Any]:
    """
    Mock Notion databases list response

    Args:
        count: Number of databases to generate

    Returns:
        Notion databases response
    """
    results = []
    for i in range(count):
        results.append({
            "object": "database",
            "id": str(uuid4()),
            "created_time": datetime.utcnow().isoformat() + "Z",
            "last_edited_time": datetime.utcnow().isoformat() + "Z",
            "title": [
                {
                    "type": "text",
                    "text": {
                        "content": f"Test Database {i + 1}",
                        "link": None
                    }
                }
            ],
            "properties": {
                "Name": {
                    "id": "title",
                    "type": "title",
                    "title": {}
                },
                "Status": {
                    "id": str(uuid4()),
                    "type": "select",
                    "select": {}
                }
            }
        })

    return {
        "object": "list",
        "results": results,
        "has_more": False,
        "next_cursor": None
    }


# ============================================================================
# GRANOLA MCP RESPONSES
# ============================================================================

def get_granola_kpis() -> Dict[str, Any]:
    """Mock Granola KPI data response"""
    return {
        "data": {
            "mrr": 45000.00,
            "arr": 540000.00,
            "cac": 850.00,
            "ltv": 12500.00,
            "churn_rate": 0.045,
            "conversion_rate": 0.18,
            "active_users": 1250,
            "trial_users": 85,
            "paid_users": 450,
            "timestamp": datetime.utcnow().isoformat(),
            "period": "monthly"
        },
        "trends": {
            "mrr_growth": 0.12,
            "user_growth": 0.08,
            "churn_trend": -0.02
        }
    }


# ============================================================================
# ERROR RESPONSES
# ============================================================================

def get_rate_limit_error(platform: str = "zoom") -> Dict[str, Any]:
    """
    Generate mock rate limit error response

    Args:
        platform: Platform name

    Returns:
        Rate limit error response
    """
    return {
        "error": "rate_limit_exceeded",
        "error_description": f"API rate limit exceeded for {platform}",
        "status_code": 429,
        "retry_after": 60
    }


def get_unauthorized_error() -> Dict[str, Any]:
    """Generate mock unauthorized error response"""
    return {
        "error": "unauthorized",
        "error_description": "Invalid or missing authentication credentials",
        "status_code": 401
    }


def get_forbidden_error() -> Dict[str, Any]:
    """Generate mock forbidden error response"""
    return {
        "error": "forbidden",
        "error_description": "Insufficient permissions to access this resource",
        "status_code": 403
    }


def get_not_found_error() -> Dict[str, Any]:
    """Generate mock not found error response"""
    return {
        "error": "not_found",
        "error_description": "The requested resource was not found",
        "status_code": 404
    }


def get_internal_server_error() -> Dict[str, Any]:
    """Generate mock internal server error response"""
    return {
        "error": "internal_error",
        "error_description": "An internal server error occurred",
        "status_code": 500
    }


def get_service_unavailable_error() -> Dict[str, Any]:
    """Generate mock service unavailable error response"""
    return {
        "error": "service_unavailable",
        "error_description": "The service is temporarily unavailable",
        "status_code": 503,
        "retry_after": 300
    }


# ============================================================================
# OAUTH ERROR RESPONSES
# ============================================================================

def get_oauth_denied_error() -> Dict[str, Any]:
    """Generate mock OAuth access denied error"""
    return {
        "error": "access_denied",
        "error_description": "The user denied the authorization request",
        "status_code": 400
    }


def get_oauth_invalid_state_error() -> Dict[str, Any]:
    """Generate mock OAuth invalid state error"""
    return {
        "error": "invalid_state",
        "error_description": "The state parameter is invalid or has expired",
        "status_code": 400
    }


def get_oauth_invalid_code_error() -> Dict[str, Any]:
    """Generate mock OAuth invalid authorization code error"""
    return {
        "error": "invalid_grant",
        "error_description": "The authorization code is invalid or has expired",
        "status_code": 400
    }


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_mock_response_for_platform(platform: str, endpoint: str = "user_info") -> Dict[str, Any]:
    """
    Get mock response for a specific platform and endpoint

    Args:
        platform: Platform name (zoom, slack, discord, etc.)
        endpoint: API endpoint (user_info, messages_list, etc.)

    Returns:
        Mock response dictionary

    Raises:
        ValueError: If platform or endpoint is not supported
    """
    platform_endpoints = {
        "zoom": {
            "user_info": get_zoom_user_info,
            "meetings_list": get_zoom_meetings_list,
            "meeting_detail": get_zoom_meeting_detail
        },
        "slack": {
            "auth_test": get_slack_auth_test,
            "messages_list": get_slack_messages_list,
            "channel_info": get_slack_channel_info
        },
        "discord": {
            "user_info": get_discord_user_info,
            "channels_list": get_discord_guild_channels,
            "messages_list": get_discord_messages_list
        },
        "outlook": {
            "user_profile": get_outlook_user_profile,
            "messages_list": get_outlook_messages_list
        },
        "monday": {
            "user_info": get_monday_user_info,
            "boards_list": get_monday_boards_list,
            "create_item": get_monday_create_item_response
        },
        "notion": {
            "user_info": get_notion_user_info,
            "databases_list": get_notion_databases_list
        },
        "granola": {
            "kpis": get_granola_kpis
        }
    }

    if platform not in platform_endpoints:
        raise ValueError(f"Platform '{platform}' not supported")

    if endpoint not in platform_endpoints[platform]:
        raise ValueError(f"Endpoint '{endpoint}' not supported for platform '{platform}'")

    return platform_endpoints[platform][endpoint]()
