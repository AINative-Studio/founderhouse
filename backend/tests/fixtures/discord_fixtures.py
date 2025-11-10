"""
Discord integration test fixtures
Mock data for Discord bot interactions and async collaboration
"""
from datetime import datetime, timedelta
from typing import Dict, Any, List


# Mock Discord Bot User
MOCK_DISCORD_BOT = {
    "id": "987654321098765432",
    "username": "AI Chief of Staff",
    "discriminator": "0001",
    "avatar": "abc123def456",
    "bot": True,
    "system": False,
    "verified": True,
    "flags": 0,
    "public_flags": 0
}


# Mock Discord Guilds (Servers)
MOCK_DISCORD_GUILDS = [
    {
        "id": "111111111111111111",
        "name": "Engineering Team",
        "icon": "guild_icon_1",
        "owner_id": "222222222222222222",
        "permissions": "2147483647",
        "features": ["COMMUNITY", "NEWS"],
        "member_count": 45
    },
    {
        "id": "333333333333333333",
        "name": "Product & Design",
        "icon": "guild_icon_2",
        "owner_id": "444444444444444444",
        "permissions": "2147483647",
        "features": ["COMMUNITY"],
        "member_count": 28
    },
    {
        "id": "555555555555555555",
        "name": "Executive Team",
        "icon": "guild_icon_3",
        "owner_id": "666666666666666666",
        "permissions": "2147483647",
        "features": ["PRIVATE_THREADS"],
        "member_count": 8
    }
]


# Mock Discord Channels
MOCK_DISCORD_CHANNELS = [
    {
        "id": "ch_general",
        "type": 0,  # GUILD_TEXT
        "guild_id": "111111111111111111",
        "name": "general",
        "position": 0,
        "topic": "General engineering discussions",
        "nsfw": False,
        "last_message_id": "msg_123",
        "rate_limit_per_user": 0
    },
    {
        "id": "ch_sprint_planning",
        "type": 0,
        "guild_id": "111111111111111111",
        "name": "sprint-planning",
        "position": 1,
        "topic": "Sprint planning and task coordination",
        "nsfw": False,
        "last_message_id": "msg_456",
        "rate_limit_per_user": 0
    },
    {
        "id": "ch_ai_updates",
        "type": 0,
        "guild_id": "111111111111111111",
        "name": "ai-updates",
        "position": 2,
        "topic": "AI Chief of Staff automated updates",
        "nsfw": False,
        "last_message_id": "msg_789",
        "rate_limit_per_user": 5
    },
    {
        "id": "ch_product_feedback",
        "type": 0,
        "guild_id": "333333333333333333",
        "name": "product-feedback",
        "position": 0,
        "topic": "User feedback and feature requests",
        "nsfw": False,
        "last_message_id": "msg_101",
        "rate_limit_per_user": 0
    },
    {
        "id": "ch_exec_briefings",
        "type": 0,
        "guild_id": "555555555555555555",
        "name": "exec-briefings",
        "position": 0,
        "topic": "Daily executive briefings",
        "nsfw": False,
        "last_message_id": "msg_202",
        "rate_limit_per_user": 0
    }
]


# Mock Discord Messages
MOCK_DISCORD_MESSAGES = [
    {
        "id": "msg_123",
        "channel_id": "ch_general",
        "author": {
            "id": "usr_alice",
            "username": "alice",
            "discriminator": "1234",
            "avatar": "avatar_alice"
        },
        "content": "@AI Chief of Staff can you summarize the latest sprint review video?",
        "timestamp": (datetime.utcnow() - timedelta(minutes=30)).isoformat(),
        "edited_timestamp": None,
        "tts": False,
        "mention_everyone": False,
        "mentions": [MOCK_DISCORD_BOT],
        "embeds": [],
        "attachments": [],
        "reactions": []
    },
    {
        "id": "msg_456",
        "channel_id": "ch_sprint_planning",
        "author": {
            "id": "usr_bob",
            "username": "bob",
            "discriminator": "5678",
            "avatar": "avatar_bob"
        },
        "content": "!task create Review Q4 metrics @alice priority:high due:2024-12-31",
        "timestamp": (datetime.utcnow() - timedelta(hours=2)).isoformat(),
        "edited_timestamp": None,
        "tts": False,
        "mention_everyone": False,
        "mentions": [{"id": "usr_alice", "username": "alice"}],
        "embeds": [],
        "attachments": [],
        "reactions": [
            {"emoji": {"name": "✅"}, "count": 3}
        ]
    },
    {
        "id": "msg_789",
        "channel_id": "ch_ai_updates",
        "author": MOCK_DISCORD_BOT,
        "content": "Daily Briefing - December 5, 2024",
        "timestamp": (datetime.utcnow() - timedelta(hours=6)).isoformat(),
        "edited_timestamp": None,
        "tts": False,
        "mention_everyone": False,
        "mentions": [],
        "embeds": [
            {
                "title": "Daily Briefing - December 5, 2024",
                "description": "Your personalized daily briefing",
                "color": 5793266,
                "fields": [
                    {
                        "name": "🎯 Key Priorities",
                        "value": "- Review Sprint 4 deliverables\n- Plan Sprint 5 tasks\n- Address critical bugs",
                        "inline": False
                    },
                    {
                        "name": "📊 KPI Alerts",
                        "value": "Revenue: ↑ 12% MoM\nChurn Rate: ↓ 2.1%",
                        "inline": False
                    },
                    {
                        "name": "✅ Action Items",
                        "value": "3 tasks due today",
                        "inline": False
                    }
                ],
                "timestamp": datetime.utcnow().isoformat()
            }
        ],
        "attachments": [],
        "reactions": [
            {"emoji": {"name": "👍"}, "count": 5}
        ]
    },
    {
        "id": "msg_101",
        "channel_id": "ch_product_feedback",
        "author": {
            "id": "usr_charlie",
            "username": "charlie",
            "discriminator": "9012",
            "avatar": "avatar_charlie"
        },
        "content": "The voice command feature is really useful! Would love to see more natural language support.",
        "timestamp": (datetime.utcnow() - timedelta(days=1)).isoformat(),
        "edited_timestamp": None,
        "tts": False,
        "mention_everyone": False,
        "mentions": [],
        "embeds": [],
        "attachments": [],
        "reactions": [
            {"emoji": {"name": "❤️"}, "count": 8},
            {"emoji": {"name": "🚀"}, "count": 4}
        ]
    },
    {
        "id": "msg_202",
        "channel_id": "ch_exec_briefings",
        "author": MOCK_DISCORD_BOT,
        "content": None,
        "timestamp": datetime.utcnow().isoformat(),
        "edited_timestamp": None,
        "tts": False,
        "mention_everyone": False,
        "mentions": [],
        "embeds": [
            {
                "title": "Executive Briefing - Sprint 5 Progress",
                "description": "Orchestration, Voice & Async Collaboration",
                "color": 3447003,
                "fields": [
                    {
                        "name": "Sprint Progress",
                        "value": "65% complete - on track",
                        "inline": True
                    },
                    {
                        "name": "Team Velocity",
                        "value": "42 story points/sprint",
                        "inline": True
                    },
                    {
                        "name": "Critical Issues",
                        "value": "None",
                        "inline": False
                    }
                ],
                "timestamp": datetime.utcnow().isoformat()
            }
        ],
        "attachments": [],
        "reactions": []
    }
]


# Mock Guild Members
MOCK_DISCORD_MEMBERS = [
    {
        "user": {
            "id": "usr_alice",
            "username": "alice",
            "discriminator": "1234",
            "avatar": "avatar_alice"
        },
        "nick": "Alice - Engineering Lead",
        "roles": ["role_engineering", "role_admin"],
        "joined_at": "2024-01-01T00:00:00Z",
        "premium_since": None,
        "deaf": False,
        "mute": False
    },
    {
        "user": {
            "id": "usr_bob",
            "username": "bob",
            "discriminator": "5678",
            "avatar": "avatar_bob"
        },
        "nick": "Bob - Product Manager",
        "roles": ["role_product"],
        "joined_at": "2024-01-02T00:00:00Z",
        "premium_since": None,
        "deaf": False,
        "mute": False
    },
    {
        "user": {
            "id": "usr_charlie",
            "username": "charlie",
            "discriminator": "9012",
            "avatar": "avatar_charlie"
        },
        "nick": "Charlie - Designer",
        "roles": ["role_design"],
        "joined_at": "2024-01-03T00:00:00Z",
        "premium_since": "2024-06-01T00:00:00Z",
        "deaf": False,
        "mute": False
    }
]


# Discord Command Patterns
DISCORD_COMMAND_PATTERNS = [
    {
        "command": "!task create",
        "pattern": r"!task create (.+?) @(\w+) priority:(\w+) due:(\d{4}-\d{2}-\d{2})",
        "intent": "create_task",
        "example": "!task create Review Q4 metrics @alice priority:high due:2024-12-31"
    },
    {
        "command": "!briefing",
        "pattern": r"!briefing(?: (\w+))?",
        "intent": "get_briefing",
        "example": "!briefing daily"
    },
    {
        "command": "!summary",
        "pattern": r"!summary (.+)",
        "intent": "summarize_content",
        "example": "!summary https://www.loom.com/share/abc123"
    },
    {
        "command": "!kpi",
        "pattern": r"!kpi (\w+)(?: (\d+[dwmy]))?",
        "intent": "get_kpi",
        "example": "!kpi revenue 30d"
    }
]


# Discord Webhook Events
MOCK_DISCORD_WEBHOOKS = [
    {
        "type": "MESSAGE_CREATE",
        "data": MOCK_DISCORD_MESSAGES[0]
    },
    {
        "type": "MESSAGE_REACTION_ADD",
        "data": {
            "message_id": "msg_456",
            "channel_id": "ch_sprint_planning",
            "user_id": "usr_alice",
            "emoji": {"name": "✅"}
        }
    }
]


# Discord Embed Templates
DISCORD_EMBED_TEMPLATES = {
    "briefing": {
        "title": "Daily Briefing",
        "color": 5793266,  # Blue
        "fields": [
            {"name": "🎯 Key Priorities", "value": "", "inline": False},
            {"name": "📊 KPI Alerts", "value": "", "inline": False},
            {"name": "✅ Action Items", "value": "", "inline": False}
        ]
    },
    "task_created": {
        "title": "Task Created",
        "color": 3066993,  # Green
        "fields": [
            {"name": "Description", "value": "", "inline": False},
            {"name": "Assignee", "value": "", "inline": True},
            {"name": "Priority", "value": "", "inline": True},
            {"name": "Due Date", "value": "", "inline": True}
        ]
    },
    "error": {
        "title": "Error",
        "color": 15158332,  # Red
        "fields": [
            {"name": "Message", "value": "", "inline": False}
        ]
    },
    "success": {
        "title": "Success",
        "color": 3066993,  # Green
        "fields": [
            {"name": "Message", "value": "", "inline": False}
        ]
    }
}


def get_mock_guild(guild_id: str = None) -> Dict[str, Any]:
    """Get mock guild by ID"""
    if guild_id:
        for guild in MOCK_DISCORD_GUILDS:
            if guild["id"] == guild_id:
                return guild
    return MOCK_DISCORD_GUILDS[0]


def get_mock_channel(channel_id: str = None) -> Dict[str, Any]:
    """Get mock channel by ID"""
    if channel_id:
        for channel in MOCK_DISCORD_CHANNELS:
            if channel["id"] == channel_id:
                return channel
    return MOCK_DISCORD_CHANNELS[0]


def get_mock_message(message_id: str = None) -> Dict[str, Any]:
    """Get mock message by ID"""
    if message_id:
        for message in MOCK_DISCORD_MESSAGES:
            if message["id"] == message_id:
                return message
    return MOCK_DISCORD_MESSAGES[0]


def create_mock_discord_message(
    content: str,
    channel_id: str = "ch_general",
    author_id: str = "usr_test",
    mentions: List[Dict] = None,
    embeds: List[Dict] = None
) -> Dict[str, Any]:
    """Create a mock Discord message with custom parameters"""
    return {
        "id": f"msg_{datetime.utcnow().timestamp()}",
        "channel_id": channel_id,
        "author": {
            "id": author_id,
            "username": "test_user",
            "discriminator": "0000",
            "avatar": "test_avatar"
        },
        "content": content,
        "timestamp": datetime.utcnow().isoformat(),
        "edited_timestamp": None,
        "tts": False,
        "mention_everyone": False,
        "mentions": mentions or [],
        "embeds": embeds or [],
        "attachments": [],
        "reactions": []
    }


def create_discord_embed(
    title: str,
    description: str = None,
    color: int = 5793266,
    fields: List[Dict] = None
) -> Dict[str, Any]:
    """Create a Discord embed"""
    return {
        "title": title,
        "description": description,
        "color": color,
        "fields": fields or [],
        "timestamp": datetime.utcnow().isoformat()
    }
