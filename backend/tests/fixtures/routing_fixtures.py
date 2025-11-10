"""
Agent routing and orchestration test fixtures
Mock data for multi-agent coordination and task routing
"""
from datetime import datetime, timedelta
from typing import Dict, Any, List
from uuid import uuid4


# Agent Types
AGENT_TYPES = {
    "MEETING_AGENT": "meeting_intelligence",
    "KPI_AGENT": "kpi_monitoring",
    "TASK_AGENT": "task_management",
    "BRIEFING_AGENT": "briefing_generation",
    "VOICE_AGENT": "voice_processing",
    "VIDEO_AGENT": "video_summarization",
    "DISCORD_AGENT": "discord_collaboration"
}


# Mock Agent Definitions
MOCK_AGENTS = [
    {
        "id": "agent_meeting",
        "name": "Meeting Intelligence Agent",
        "type": AGENT_TYPES["MEETING_AGENT"],
        "capabilities": [
            "transcribe_meeting",
            "extract_action_items",
            "identify_decisions",
            "summarize_meeting"
        ],
        "status": "active",
        "load": 0.35,
        "max_concurrent_tasks": 5,
        "current_tasks": 2,
        "average_response_time_ms": 850,
        "success_rate": 0.98
    },
    {
        "id": "agent_kpi",
        "name": "KPI Monitoring Agent",
        "type": AGENT_TYPES["KPI_AGENT"],
        "capabilities": [
            "ingest_kpi_data",
            "detect_anomalies",
            "analyze_trends",
            "generate_alerts"
        ],
        "status": "active",
        "load": 0.62,
        "max_concurrent_tasks": 10,
        "current_tasks": 6,
        "average_response_time_ms": 320,
        "success_rate": 0.99
    },
    {
        "id": "agent_task",
        "name": "Task Management Agent",
        "type": AGENT_TYPES["TASK_AGENT"],
        "capabilities": [
            "create_task",
            "update_task",
            "route_to_platform",
            "track_completion"
        ],
        "status": "active",
        "load": 0.45,
        "max_concurrent_tasks": 8,
        "current_tasks": 4,
        "average_response_time_ms": 1200,
        "success_rate": 0.96
    },
    {
        "id": "agent_briefing",
        "name": "Briefing Generation Agent",
        "type": AGENT_TYPES["BRIEFING_AGENT"],
        "capabilities": [
            "generate_daily_briefing",
            "generate_weekly_briefing",
            "customize_content",
            "deliver_briefing"
        ],
        "status": "active",
        "load": 0.28,
        "max_concurrent_tasks": 3,
        "current_tasks": 1,
        "average_response_time_ms": 2500,
        "success_rate": 0.97
    },
    {
        "id": "agent_voice",
        "name": "Voice Processing Agent",
        "type": AGENT_TYPES["VOICE_AGENT"],
        "capabilities": [
            "transcribe_voice",
            "extract_intent",
            "execute_command",
            "generate_tts_response"
        ],
        "status": "active",
        "load": 0.18,
        "max_concurrent_tasks": 6,
        "current_tasks": 1,
        "average_response_time_ms": 1800,
        "success_rate": 0.94
    },
    {
        "id": "agent_video",
        "name": "Video Summarization Agent",
        "type": AGENT_TYPES["VIDEO_AGENT"],
        "capabilities": [
            "fetch_video_transcript",
            "summarize_video",
            "extract_key_points",
            "identify_action_items"
        ],
        "status": "active",
        "load": 0.52,
        "max_concurrent_tasks": 4,
        "current_tasks": 2,
        "average_response_time_ms": 3200,
        "success_rate": 0.95
    },
    {
        "id": "agent_discord",
        "name": "Discord Collaboration Agent",
        "type": AGENT_TYPES["DISCORD_AGENT"],
        "capabilities": [
            "send_message",
            "create_thread",
            "post_briefing",
            "handle_commands"
        ],
        "status": "active",
        "load": 0.21,
        "max_concurrent_tasks": 10,
        "current_tasks": 2,
        "average_response_time_ms": 450,
        "success_rate": 0.99
    }
]


# Mock Routing Rules
ROUTING_RULES = [
    {
        "id": "rule_meeting_transcription",
        "name": "Meeting Transcription Routing",
        "trigger": {
            "type": "event",
            "event_type": "meeting_started"
        },
        "conditions": [
            {"field": "meeting.has_audio", "operator": "equals", "value": True}
        ],
        "route_to": "agent_meeting",
        "priority": "high",
        "timeout_seconds": 300
    },
    {
        "id": "rule_voice_command",
        "name": "Voice Command Processing",
        "trigger": {
            "type": "event",
            "event_type": "voice_command_received"
        },
        "conditions": [],
        "route_to": "agent_voice",
        "priority": "urgent",
        "timeout_seconds": 5,
        "fallback_agent": "agent_task"
    },
    {
        "id": "rule_kpi_anomaly",
        "name": "KPI Anomaly Detection",
        "trigger": {
            "type": "schedule",
            "cron": "*/15 * * * *"  # Every 15 minutes
        },
        "conditions": [
            {"field": "kpi.last_check", "operator": "older_than", "value": "15m"}
        ],
        "route_to": "agent_kpi",
        "priority": "normal",
        "timeout_seconds": 60
    },
    {
        "id": "rule_daily_briefing",
        "name": "Daily Briefing Generation",
        "trigger": {
            "type": "schedule",
            "cron": "0 8 * * *"  # Daily at 8 AM
        },
        "conditions": [],
        "route_to": "agent_briefing",
        "priority": "normal",
        "timeout_seconds": 120,
        "on_complete": [
            {"agent": "agent_discord", "action": "post_briefing"}
        ]
    },
    {
        "id": "rule_loom_video",
        "name": "Loom Video Summarization",
        "trigger": {
            "type": "event",
            "event_type": "loom_video_shared"
        },
        "conditions": [
            {"field": "video.status", "operator": "equals", "value": "COMPLETED"}
        ],
        "route_to": "agent_video",
        "priority": "normal",
        "timeout_seconds": 180
    }
]


# Mock Routing Requests
MOCK_ROUTING_REQUESTS = [
    {
        "id": str(uuid4()),
        "type": "meeting_transcription",
        "source": "granola_mcp",
        "payload": {
            "meeting_id": str(uuid4()),
            "audio_url": "https://example.com/audio/meeting_1.mp3",
            "duration": 3600,
            "attendees": ["alice@example.com", "bob@example.com"]
        },
        "required_capabilities": ["transcribe_meeting", "extract_action_items"],
        "priority": "high",
        "created_at": datetime.utcnow().isoformat(),
        "timeout_at": (datetime.utcnow() + timedelta(minutes=5)).isoformat()
    },
    {
        "id": str(uuid4()),
        "type": "voice_command",
        "source": "zerovoice_mcp",
        "payload": {
            "recording_sid": "RE1111111111111111111111111111111",
            "transcription": "Create a task to review the sprint metrics",
            "caller": "+15551234567"
        },
        "required_capabilities": ["extract_intent", "execute_command"],
        "priority": "urgent",
        "created_at": datetime.utcnow().isoformat(),
        "timeout_at": (datetime.utcnow() + timedelta(seconds=5)).isoformat()
    },
    {
        "id": str(uuid4()),
        "type": "kpi_analysis",
        "source": "scheduled_job",
        "payload": {
            "workspace_id": str(uuid4()),
            "kpi_types": ["revenue", "churn", "active_users"],
            "time_range": "24h"
        },
        "required_capabilities": ["detect_anomalies", "analyze_trends"],
        "priority": "normal",
        "created_at": datetime.utcnow().isoformat(),
        "timeout_at": (datetime.utcnow() + timedelta(minutes=1)).isoformat()
    },
    {
        "id": str(uuid4()),
        "type": "video_summarization",
        "source": "loom_mcp",
        "payload": {
            "video_id": "video_1_sprint_review",
            "video_url": "https://www.loom.com/share/video_1_sprint_review",
            "duration": 1800,
            "requested_by": "alice@example.com"
        },
        "required_capabilities": ["summarize_video", "extract_key_points"],
        "priority": "normal",
        "created_at": datetime.utcnow().isoformat(),
        "timeout_at": (datetime.utcnow() + timedelta(minutes=3)).isoformat()
    }
]


# Mock Routing Decisions
MOCK_ROUTING_DECISIONS = [
    {
        "request_id": MOCK_ROUTING_REQUESTS[0]["id"],
        "selected_agent": "agent_meeting",
        "reasoning": "Agent has required capabilities and lowest current load (35%)",
        "alternative_agents": [],
        "confidence": 0.98,
        "decision_time_ms": 45,
        "routing_metadata": {
            "rule_matched": "rule_meeting_transcription",
            "load_balanced": True
        }
    },
    {
        "request_id": MOCK_ROUTING_REQUESTS[1]["id"],
        "selected_agent": "agent_voice",
        "reasoning": "Urgent priority, agent specialized for voice commands",
        "alternative_agents": ["agent_task"],
        "confidence": 0.95,
        "decision_time_ms": 12,
        "routing_metadata": {
            "rule_matched": "rule_voice_command",
            "latency_optimized": True
        }
    }
]


# Cross-Agent Collaboration Workflows
COLLABORATION_WORKFLOWS = [
    {
        "id": "workflow_meeting_to_tasks",
        "name": "Meeting → Action Items → Tasks",
        "description": "Extract action items from meeting and create tasks",
        "steps": [
            {
                "step": 1,
                "agent": "agent_meeting",
                "action": "transcribe_and_extract",
                "output": "action_items"
            },
            {
                "step": 2,
                "agent": "agent_task",
                "action": "create_tasks",
                "input": "action_items",
                "output": "created_tasks"
            },
            {
                "step": 3,
                "agent": "agent_discord",
                "action": "notify_team",
                "input": "created_tasks"
            }
        ],
        "estimated_duration_seconds": 180,
        "success_rate": 0.94
    },
    {
        "id": "workflow_voice_to_briefing",
        "name": "Voice Command → Update Briefing",
        "description": "Process voice command and update daily briefing",
        "steps": [
            {
                "step": 1,
                "agent": "agent_voice",
                "action": "extract_intent",
                "output": "command_intent"
            },
            {
                "step": 2,
                "agent": "agent_briefing",
                "action": "update_briefing",
                "input": "command_intent",
                "output": "updated_briefing"
            }
        ],
        "estimated_duration_seconds": 45,
        "success_rate": 0.92
    },
    {
        "id": "workflow_kpi_alert_chain",
        "name": "KPI Alert → Task → Notification",
        "description": "Detect KPI anomaly, create task, notify team",
        "steps": [
            {
                "step": 1,
                "agent": "agent_kpi",
                "action": "detect_anomaly",
                "output": "anomaly_details"
            },
            {
                "step": 2,
                "agent": "agent_task",
                "action": "create_investigation_task",
                "input": "anomaly_details",
                "output": "investigation_task"
            },
            {
                "step": 3,
                "agent": "agent_discord",
                "action": "post_alert",
                "input": "anomaly_details,investigation_task"
            },
            {
                "step": 4,
                "agent": "agent_briefing",
                "action": "add_to_briefing",
                "input": "anomaly_details"
            }
        ],
        "estimated_duration_seconds": 90,
        "success_rate": 0.96
    }
]


# Agent Performance Metrics
AGENT_PERFORMANCE_METRICS = {
    "agent_meeting": {
        "total_requests": 1523,
        "successful_requests": 1492,
        "failed_requests": 31,
        "average_latency_ms": 850,
        "p95_latency_ms": 1200,
        "p99_latency_ms": 1850,
        "uptime_percentage": 99.8
    },
    "agent_voice": {
        "total_requests": 892,
        "successful_requests": 838,
        "failed_requests": 54,
        "average_latency_ms": 1800,
        "p95_latency_ms": 2400,
        "p99_latency_ms": 2950,
        "uptime_percentage": 99.2
    },
    "agent_kpi": {
        "total_requests": 4567,
        "successful_requests": 4522,
        "failed_requests": 45,
        "average_latency_ms": 320,
        "p95_latency_ms": 580,
        "p99_latency_ms": 890,
        "uptime_percentage": 99.9
    }
}


def get_mock_agent(agent_id: str = None) -> Dict[str, Any]:
    """Get mock agent by ID"""
    if agent_id:
        for agent in MOCK_AGENTS:
            if agent["id"] == agent_id:
                return agent
    return MOCK_AGENTS[0]


def get_agents_by_capability(capability: str) -> List[Dict[str, Any]]:
    """Get all agents with a specific capability"""
    return [
        agent for agent in MOCK_AGENTS
        if capability in agent["capabilities"]
    ]


def create_routing_request(
    request_type: str,
    payload: Dict[str, Any],
    priority: str = "normal",
    required_capabilities: List[str] = None
) -> Dict[str, Any]:
    """Create a mock routing request"""
    return {
        "id": str(uuid4()),
        "type": request_type,
        "source": "test",
        "payload": payload,
        "required_capabilities": required_capabilities or [],
        "priority": priority,
        "created_at": datetime.utcnow().isoformat(),
        "timeout_at": (datetime.utcnow() + timedelta(minutes=5)).isoformat()
    }
