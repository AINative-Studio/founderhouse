"""
Loom video test fixtures
Mock data for Loom video summarization and processing
"""
from datetime import datetime, timedelta
from typing import Dict, Any, List


# Mock Loom User
MOCK_LOOM_USER = {
    "id": "12345678",
    "name": "Test User",
    "email": "test@example.com",
    "avatar_url": "https://cdn.loom.com/avatars/test_user.jpg",
    "created_at": "2024-01-01T00:00:00Z"
}


# Mock Loom Videos
MOCK_LOOM_VIDEOS = [
    {
        "id": "video_1_sprint_review",
        "name": "Sprint 4 Review - Meeting Intelligence",
        "description": "Review of Sprint 4 deliverables including Granola integration and action item extraction",
        "status": "COMPLETED",
        "duration": 1800,  # 30 minutes
        "created_at": (datetime.utcnow() - timedelta(days=2)).isoformat(),
        "updated_at": (datetime.utcnow() - timedelta(days=2)).isoformat(),
        "views": 42,
        "folder_id": "folder_sprints",
        "thumbnail_url": "https://cdn.loom.com/thumbnails/video_1.jpg",
        "share_url": "https://www.loom.com/share/video_1_sprint_review",
        "video_url": "https://cdn.loom.com/videos/video_1.mp4",
        "owner": MOCK_LOOM_USER
    },
    {
        "id": "video_2_product_demo",
        "name": "Product Demo - AI Chief of Staff Features",
        "description": "Comprehensive demo of the AI Chief of Staff platform capabilities",
        "status": "COMPLETED",
        "duration": 3600,  # 60 minutes
        "created_at": (datetime.utcnow() - timedelta(days=5)).isoformat(),
        "updated_at": (datetime.utcnow() - timedelta(days=5)).isoformat(),
        "views": 156,
        "folder_id": "folder_demos",
        "thumbnail_url": "https://cdn.loom.com/thumbnails/video_2.jpg",
        "share_url": "https://www.loom.com/share/video_2_product_demo",
        "video_url": "https://cdn.loom.com/videos/video_2.mp4",
        "owner": MOCK_LOOM_USER
    },
    {
        "id": "video_3_technical_walkthrough",
        "name": "Technical Architecture Walkthrough",
        "description": "Deep dive into the system architecture and technical decisions",
        "status": "COMPLETED",
        "duration": 2700,  # 45 minutes
        "created_at": (datetime.utcnow() - timedelta(days=1)).isoformat(),
        "updated_at": (datetime.utcnow() - timedelta(days=1)).isoformat(),
        "views": 28,
        "folder_id": "folder_technical",
        "thumbnail_url": "https://cdn.loom.com/thumbnails/video_3.jpg",
        "share_url": "https://www.loom.com/share/video_3_technical_walkthrough",
        "video_url": "https://cdn.loom.com/videos/video_3.mp4",
        "owner": MOCK_LOOM_USER
    },
    {
        "id": "video_4_short_update",
        "name": "Quick Status Update",
        "description": "Brief update on current sprint progress",
        "status": "COMPLETED",
        "duration": 300,  # 5 minutes
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "views": 5,
        "folder_id": "folder_updates",
        "thumbnail_url": "https://cdn.loom.com/thumbnails/video_4.jpg",
        "share_url": "https://www.loom.com/share/video_4_short_update",
        "video_url": "https://cdn.loom.com/videos/video_4.mp4",
        "owner": MOCK_LOOM_USER
    },
    {
        "id": "video_5_processing",
        "name": "Video Being Processed",
        "description": "This video is still being processed",
        "status": "PROCESSING",
        "duration": None,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "views": 0,
        "folder_id": None,
        "thumbnail_url": None,
        "share_url": None,
        "video_url": None,
        "owner": MOCK_LOOM_USER
    }
]


# Mock Video Transcripts
MOCK_VIDEO_TRANSCRIPTS = {
    "video_1_sprint_review": {
        "video_id": "video_1_sprint_review",
        "words": [
            {"text": "Welcome", "start": 0.0, "end": 0.5},
            {"text": "to", "start": 0.5, "end": 0.7},
            {"text": "Sprint", "start": 0.7, "end": 1.0},
            {"text": "4", "start": 1.0, "end": 1.2},
            {"text": "review", "start": 1.2, "end": 1.6}
        ],
        "full_text": "Welcome to Sprint 4 review. Today we're going to cover the meeting intelligence features we built, including the Granola integration for automatic transcription, the action item extraction using Claude, and the summarization pipeline. We successfully integrated with the Granola MCP server, implemented real-time transcript processing, and created an automated task routing system to Monday.com. The key achievements include 95% accuracy in action item detection, sub-2-second processing latency, and seamless integration with existing meeting workflows. Next steps involve adding voice commands and expanding to Loom video processing.",
        "language": "en",
        "created_at": (datetime.utcnow() - timedelta(days=2)).isoformat()
    },
    "video_2_product_demo": {
        "video_id": "video_2_product_demo",
        "words": [],  # Abbreviated for brevity
        "full_text": "This is a comprehensive demonstration of the AI Chief of Staff platform. The system integrates with multiple data sources including meetings, KPIs, and communication channels. It provides intelligent insights, automated task management, and proactive briefings. The platform uses advanced LLMs for natural language understanding, anomaly detection for KPI monitoring, and sophisticated routing algorithms for task distribution. Key features include voice command support, async collaboration via Discord and Loom, and cross-agent workflow orchestration.",
        "language": "en",
        "created_at": (datetime.utcnow() - timedelta(days=5)).isoformat()
    },
    "video_3_technical_walkthrough": {
        "video_id": "video_3_technical_walkthrough",
        "words": [],
        "full_text": "Let's dive into the technical architecture. The system is built on FastAPI with async Python, using Supabase for data persistence and LangChain for LLM orchestration. We implement the Model Context Protocol for standardized integrations, support multiple LLM providers including Claude and GPT-4, and use Celery for background job processing. The architecture follows clean separation of concerns with connectors for external APIs, services for business logic, and chains for LLM workflows. We prioritize observability with comprehensive logging, monitoring, and error tracking.",
        "language": "en",
        "created_at": (datetime.utcnow() - timedelta(days=1)).isoformat()
    },
    "video_4_short_update": {
        "video_id": "video_4_short_update",
        "words": [],
        "full_text": "Quick update on Sprint 5 progress. We're implementing voice command support via ZeroVoice, adding Loom video summarization, and building Discord integration for async collaboration. On track for all deliverables.",
        "language": "en",
        "created_at": datetime.utcnow().isoformat()
    }
}


# Mock Video Insights
MOCK_VIDEO_INSIGHTS = {
    "video_1_sprint_review": {
        "video_id": "video_1_sprint_review",
        "total_views": 42,
        "unique_viewers": 35,
        "avg_watch_percentage": 87.5,
        "avg_watch_time": 1575,  # seconds
        "completion_rate": 0.82,
        "engagement_score": 0.89,
        "viewer_breakdown": {
            "internal": 30,
            "external": 12
        },
        "peak_viewership_time": (datetime.utcnow() - timedelta(days=2, hours=2)).isoformat(),
        "created_at": (datetime.utcnow() - timedelta(days=2)).isoformat()
    },
    "video_2_product_demo": {
        "video_id": "video_2_product_demo",
        "total_views": 156,
        "unique_viewers": 142,
        "avg_watch_percentage": 65.3,
        "avg_watch_time": 2350,
        "completion_rate": 0.58,
        "engagement_score": 0.72,
        "viewer_breakdown": {
            "internal": 45,
            "external": 111
        },
        "peak_viewership_time": (datetime.utcnow() - timedelta(days=5, hours=3)).isoformat(),
        "created_at": (datetime.utcnow() - timedelta(days=5)).isoformat()
    }
}


# Mock Folders
MOCK_LOOM_FOLDERS = [
    {
        "id": "folder_sprints",
        "name": "Sprint Reviews",
        "video_count": 8,
        "created_at": "2024-01-01T00:00:00Z"
    },
    {
        "id": "folder_demos",
        "name": "Product Demos",
        "video_count": 5,
        "created_at": "2024-01-01T00:00:00Z"
    },
    {
        "id": "folder_technical",
        "name": "Technical Walkthroughs",
        "video_count": 12,
        "created_at": "2024-01-01T00:00:00Z"
    },
    {
        "id": "folder_updates",
        "name": "Quick Updates",
        "video_count": 23,
        "created_at": "2024-01-01T00:00:00Z"
    }
]


# Mock Video Summaries (AI-generated)
MOCK_VIDEO_SUMMARIES = {
    "video_1_sprint_review": {
        "video_id": "video_1_sprint_review",
        "summary": "Sprint 4 successfully delivered meeting intelligence features including Granola integration, action item extraction with 95% accuracy, and automated task routing to Monday.com with sub-2-second latency.",
        "key_points": [
            "Granola MCP integration completed",
            "95% accuracy in action item detection",
            "Sub-2-second processing latency achieved",
            "Automated routing to Monday.com implemented"
        ],
        "action_items": [
            "Add voice command support",
            "Implement Loom video processing",
            "Expand meeting workflow integrations"
        ],
        "topics": ["Sprint Review", "Meeting Intelligence", "Integration", "Performance"],
        "sentiment": "positive",
        "confidence": 0.92
    },
    "video_2_product_demo": {
        "video_id": "video_2_product_demo",
        "summary": "Comprehensive platform demo showcasing multi-source integration, intelligent insights, automated task management, and advanced LLM capabilities including voice commands and async collaboration.",
        "key_points": [
            "Multi-source data integration (meetings, KPIs, communications)",
            "Advanced LLM for natural language understanding",
            "Anomaly detection for KPI monitoring",
            "Voice command and async collaboration support"
        ],
        "action_items": [
            "Schedule follow-up demo for specific use cases",
            "Provide trial access to interested teams"
        ],
        "topics": ["Product Demo", "Features", "Integration", "AI/ML"],
        "sentiment": "positive",
        "confidence": 0.88
    },
    "video_3_technical_walkthrough": {
        "video_id": "video_3_technical_walkthrough",
        "summary": "Technical deep-dive covering FastAPI architecture, Supabase persistence, LangChain orchestration, MCP integrations, and comprehensive observability implementation.",
        "key_points": [
            "FastAPI + async Python architecture",
            "Model Context Protocol for standardized integrations",
            "Multi-LLM support (Claude, GPT-4)",
            "Celery for background processing",
            "Clean architecture with separation of concerns"
        ],
        "action_items": [
            "Document MCP connector development guidelines",
            "Create architecture diagram for onboarding"
        ],
        "topics": ["Architecture", "Technical", "MCP", "LLM Integration"],
        "sentiment": "neutral",
        "confidence": 0.85
    }
}


def get_mock_video(video_id: str = None) -> Dict[str, Any]:
    """Get mock video by ID"""
    if video_id:
        for video in MOCK_LOOM_VIDEOS:
            if video["id"] == video_id:
                return video
    return MOCK_LOOM_VIDEOS[0]


def get_mock_transcript(video_id: str) -> Dict[str, Any]:
    """Get mock transcript for video"""
    return MOCK_VIDEO_TRANSCRIPTS.get(
        video_id,
        {"video_id": video_id, "full_text": "", "words": [], "language": "en"}
    )


def get_mock_insights(video_id: str) -> Dict[str, Any]:
    """Get mock insights for video"""
    return MOCK_VIDEO_INSIGHTS.get(video_id, {})


def get_mock_summary(video_id: str) -> Dict[str, Any]:
    """Get mock summary for video"""
    return MOCK_VIDEO_SUMMARIES.get(video_id, {})


def create_mock_loom_video(
    name: str = "Test Video",
    duration: int = 600,
    status: str = "COMPLETED"
) -> Dict[str, Any]:
    """Create a mock Loom video with custom parameters"""
    return {
        "id": f"video_test_{datetime.utcnow().timestamp()}",
        "name": name,
        "description": f"Test video: {name}",
        "status": status,
        "duration": duration,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "views": 0,
        "folder_id": None,
        "thumbnail_url": "https://cdn.loom.com/thumbnails/test.jpg",
        "share_url": f"https://www.loom.com/share/test_{datetime.utcnow().timestamp()}",
        "owner": MOCK_LOOM_USER
    }
