"""
AI Chief of Staff - Mock LLM Response Data
Sprint 3: Issue #8 - Meeting Summarization Testing

Mock LLM responses for:
- Meeting summarization
- Action item extraction
- Decision extraction
- Sentiment analysis
"""

from datetime import datetime, timedelta


# ============================================================================
# SUMMARIZATION RESPONSES
# ============================================================================

MOCK_SUMMARY_SHORT_MEETING = {
    "tl_dr": "Quick standup covering authentication, database optimization, and UI work. Team making good progress with one blocker on database access.",
    "key_points": [
        "Alice completed user authentication module and pushed to staging",
        "Bob finished database migration and plans to optimize dashboard queries",
        "Bob is blocked on production database access",
        "Carol completed UI mockups for settings page",
        "Carol will send Bob database credentials and review Alice's PR"
    ],
    "topics": ["authentication", "database", "ui_design", "code_review"],
    "participants_summary": {
        "Alice Johnson": {
            "speaking_time_seconds": 120,
            "contribution_percentage": 40.0,
            "key_contributions": ["Completed authentication module", "Advised on testing approach"]
        },
        "Bob Smith": {
            "speaking_time_seconds": 90,
            "contribution_percentage": 30.0,
            "key_contributions": ["Completed database migration", "Identified blocker"]
        },
        "Carol Davis": {
            "speaking_time_seconds": 90,
            "contribution_percentage": 30.0,
            "key_contributions": ["Completed UI mockups", "Offered to resolve blocker"]
        }
    },
    "next_steps": [
        "Carol to send production credentials to Bob",
        "Bob to test query optimizations on staging first",
        "Carol to review authentication PR"
    ]
}


MOCK_SUMMARY_MEDIUM_MEETING = {
    "tl_dr": "Product roadmap review resulted in prioritizing SSO integration over analytics dashboard due to $500K in pending enterprise deals. Analytics pushed to Q1, mobile app ready for beta in 2 weeks.",
    "key_points": [
        "Analytics dashboard is 70% complete, needs 3 more weeks",
        "Main blocker is backend API optimization for streaming",
        "SSO integration is critical for $500K in enterprise deals",
        "Decision made to prioritize SSO over analytics",
        "Analytics completion pushed to mid-January (Q1)",
        "Mobile app MVP ready for beta testing with 50 users in 2 weeks",
        "Backend team to allocate 2 engineers to SSO immediately"
    ],
    "topics": ["product_roadmap", "prioritization", "sso", "analytics", "mobile_app", "enterprise_deals"],
    "participants_summary": {
        "Sarah Chen": {
            "speaking_time_seconds": 720,
            "contribution_percentage": 40.0,
            "key_contributions": ["Led meeting", "Made prioritization decision", "Coordinated resources"]
        },
        "David Kim": {
            "speaking_time_seconds": 360,
            "contribution_percentage": 20.0,
            "key_contributions": ["Provided analytics update", "Accepted revised timeline"]
        },
        "Marcus Rodriguez": {
            "speaking_time_seconds": 450,
            "contribution_percentage": 25.0,
            "key_contributions": ["Highlighted resource constraints", "Provided mobile update"]
        },
        "Emily Watson": {
            "speaking_time_seconds": 270,
            "contribution_percentage": 15.0,
            "key_contributions": ["Provided business context for SSO priority"]
        }
    },
    "decisions_made": [
        "Prioritize SSO integration as top engineering priority",
        "Push analytics dashboard to Q1 (mid-January)",
        "Start mobile beta testing in 2 weeks with 50 users"
    ]
}


MOCK_SUMMARY_LONG_MEETING = {
    "tl_dr": "Investor update preparation meeting. Strong MRR growth (+35% to $180K) offset by concerning churn increase (7% from 4%). Root causes identified: missing mobile app, slow support, lack of integrations. Team addressing with mobile beta in 3 weeks, new integrations, and hiring 2 additional CS managers. Raising $5M Series A.",
    "key_points": [
        "MRR grew 35% this quarter to $180K",
        "Added 42 new customers (above 35 target)",
        "CAC decreased to $1,200 from $1,500",
        "Churn increased to 7% monthly (up from 4%) - major concern",
        "Churn drivers: missing mobile app (60% of cases), slow support, missing integrations",
        "Mobile app beta launches in 3 weeks (iOS first, Android in 6 weeks)",
        "Salesforce and HubSpot integrations shipping next month",
        "Current runway: 8 months, extending to 18 months with $5M raise",
        "Hiring plan: 3 engineers, 2 sales reps, 2 CS managers, 1 product marketer",
        "Post-raise monthly burn: $190K (up from $95K)",
        "Investor narrative: strong growth, proactively addressing identified scaling challenges"
    ],
    "topics": [
        "metrics_review",
        "churn_analysis",
        "fundraising",
        "hiring_plan",
        "product_roadmap",
        "investor_relations"
    ],
    "participants_summary": {
        "Jennifer Martinez": {
            "speaking_time_seconds": 1200,
            "contribution_percentage": 33.3,
            "key_contributions": ["Led meeting", "Made key decisions", "Defined investor narrative"]
        },
        "Tom Anderson": {
            "speaking_time_seconds": 900,
            "contribution_percentage": 25.0,
            "key_contributions": ["Presented metrics", "Detailed financial model", "Updated burn calculations"]
        },
        "Lisa Park": {
            "speaking_time_seconds": 720,
            "contribution_percentage": 20.0,
            "key_contributions": ["Provided churn analysis", "Identified CS staffing gap"]
        },
        "Marcus Taylor": {
            "speaking_time_seconds": 780,
            "contribution_percentage": 21.7,
            "key_contributions": ["Updated on product roadmap", "Highlighted team capacity issues"]
        }
    ],
    "risks_identified": [
        "7% monthly churn rate threatening growth",
        "Engineering team at capacity and showing burnout",
        "CS team underwater (127 customers for 2 people)"
    ],
    "mitigation_strategies": [
        "Ship mobile app beta in 3 weeks to address primary churn driver",
        "Add 2 CS managers to improve support response times",
        "Hire 3 engineers to accelerate product development",
        "Frame churn as identified and being proactively solved for investors"
    ]
}


# ============================================================================
# ACTION ITEM EXTRACTION RESPONSES
# ============================================================================

MOCK_ACTION_ITEMS_SHORT_MEETING = [
    {
        "task": "Send Bob production database credentials",
        "description": "Provide database access to unblock Bob's query optimization work",
        "assignee": "Carol Davis",
        "assignee_email": "carol.davis@example.com",
        "due_date": (datetime.utcnow() + timedelta(hours=2)).isoformat(),
        "priority": "high",
        "status": "pending",
        "confidence": 0.95,
        "source_timestamp": 120,
        "extraction_reasoning": "Explicit commitment: 'I'll send you the credentials right after this call'"
    },
    {
        "task": "Test query optimizations on staging before production",
        "description": "Validate database query optimizations on staging environment before applying to production",
        "assignee": "Bob Smith",
        "assignee_email": "bob.smith@example.com",
        "due_date": (datetime.utcnow() + timedelta(days=1)).isoformat(),
        "priority": "normal",
        "status": "pending",
        "confidence": 0.92,
        "source_timestamp": 180,
        "extraction_reasoning": "Direct instruction from Alice: 'make sure to test those optimizations on a staging copy first'"
    },
    {
        "task": "Review Alice's authentication PR",
        "description": "Code review for authentication module pull request",
        "assignee": "Carol Davis",
        "assignee_email": "carol.davis@example.com",
        "due_date": (datetime.utcnow() + timedelta(hours=6)).isoformat(),
        "priority": "normal",
        "status": "pending",
        "confidence": 0.90,
        "source_timestamp": 240,
        "extraction_reasoning": "Alice's request with Carol's confirmation: 'I'll review it this afternoon'"
    }
]


MOCK_ACTION_ITEMS_MEDIUM_MEETING = [
    {
        "task": "Prioritize SSO integration as top engineering priority",
        "description": "Shift engineering focus to SSO integration to support $500K in enterprise deals",
        "assignee": "Marcus Rodriguez",
        "assignee_email": "marcus.rodriguez@example.com",
        "due_date": (datetime.utcnow() + timedelta(days=1)).isoformat(),
        "priority": "urgent",
        "status": "pending",
        "confidence": 0.98,
        "source_timestamp": 1080,
        "extraction_reasoning": "Direct decision from Sarah: 'Marcus, your team focuses on SSO as top priority'"
    },
    {
        "task": "Allocate two backend engineers to SSO project",
        "description": "Assign two engineers to SSO integration work starting next week",
        "assignee": "Marcus Rodriguez",
        "assignee_email": "marcus.rodriguez@example.com",
        "due_date": (datetime.utcnow() + timedelta(days=7)).isoformat(),
        "priority": "high",
        "status": "pending",
        "confidence": 0.96,
        "source_timestamp": 540,
        "extraction_reasoning": "Marcus's commitment: 'we can allocate two engineers starting next week'"
    },
    {
        "task": "Continue analytics dashboard development with one engineer",
        "description": "Proceed with analytics dashboard using limited engineering resources until SSO ships",
        "assignee": "David Kim",
        "assignee_email": "david.kim@example.com",
        "due_date": (datetime.utcnow() + timedelta(days=90)).isoformat(),
        "priority": "normal",
        "status": "pending",
        "confidence": 0.88,
        "source_timestamp": 1260,
        "extraction_reasoning": "Agreement reached: 'It'll push analytics into early Q1, probably mid-January'"
    },
    {
        "task": "Coordinate beta tester selection with Emily",
        "description": "Work with Emily to select 50 beta users from customer base for mobile app testing",
        "assignee": "Sarah Chen",
        "assignee_email": "sarah.chen@example.com",
        "due_date": (datetime.utcnow() + timedelta(days=10)).isoformat(),
        "priority": "normal",
        "status": "pending",
        "confidence": 0.91,
        "source_timestamp": 1800,
        "extraction_reasoning": "Direct request: 'can you coordinate with Emily on selecting beta testers'"
    },
    {
        "task": "Complete mobile app load testing and Android UI fixes",
        "description": "Finish load testing and resolve UI bugs on Android before beta launch",
        "assignee": "Marcus Rodriguez",
        "assignee_email": "marcus.rodriguez@example.com",
        "due_date": (datetime.utcnow() + timedelta(days=14)).isoformat(),
        "priority": "high",
        "status": "pending",
        "confidence": 0.94,
        "source_timestamp": 1620,
        "extraction_reasoning": "Marcus stated need: 'We need to do load testing and fix some UI bugs on Android'"
    }
]


MOCK_ACTION_ITEMS_LONG_MEETING = [
    {
        "task": "Update hiring plan to include 2 Customer Success managers",
        "description": "Revise hiring plan to add second CS manager due to current team being underwater",
        "assignee": "Tom Anderson",
        "assignee_email": "tom.anderson@example.com",
        "due_date": (datetime.utcnow() + timedelta(days=2)).isoformat(),
        "priority": "high",
        "status": "pending",
        "confidence": 0.97,
        "source_timestamp": 3000,
        "extraction_reasoning": "Decision made by Jennifer: 'Let's update the hiring plan to include 2 CS managers'"
    },
    {
        "task": "Prepare mobile app demo for investor presentation",
        "description": "Create demo of mobile app beta to show investors during Series A pitch",
        "assignee": "Marcus Taylor",
        "assignee_email": "marcus.taylor@example.com",
        "due_date": (datetime.utcnow() + timedelta(days=5)).isoformat(),
        "priority": "urgent",
        "status": "pending",
        "confidence": 0.93,
        "source_timestamp": 3300,
        "extraction_reasoning": "Marcus mentioned: 'We can show them the mobile app demo even though it's beta'"
    },
    {
        "task": "Create integrations roadmap slide for investors",
        "description": "Develop slide showcasing integration pipeline for investor deck",
        "assignee": "Marcus Taylor",
        "assignee_email": "marcus.taylor@example.com",
        "due_date": (datetime.utcnow() + timedelta(days=3)).isoformat(),
        "priority": "high",
        "status": "pending",
        "confidence": 0.89,
        "source_timestamp": 3300,
        "extraction_reasoning": "Implied from: 'demonstrate that we're shipping... showcase the integration pipeline'"
    },
    {
        "task": "Compile churn analysis report with root causes",
        "description": "Document exit interview findings and root cause analysis of churn increase",
        "assignee": "Lisa Park",
        "assignee_email": "lisa.park@example.com",
        "due_date": (datetime.utcnow() + timedelta(days=3)).isoformat(),
        "priority": "high",
        "status": "pending",
        "confidence": 0.91,
        "source_timestamp": 900,
        "extraction_reasoning": "Lisa provided analysis that needs to be formalized for investor deck"
    },
    {
        "task": "Update financial model with revised burn rate ($190K)",
        "description": "Revise financial projections to reflect updated hiring plan and $190K monthly burn",
        "assignee": "Tom Anderson",
        "assignee_email": "tom.anderson@example.com",
        "due_date": (datetime.utcnow() + timedelta(days=2)).isoformat(),
        "priority": "high",
        "status": "pending",
        "confidence": 0.95,
        "source_timestamp": 2700,
        "extraction_reasoning": "Tom calculated: 'Adding another CS hire increases burn to $190K'"
    },
    {
        "task": "Draft investor narrative deck",
        "description": "Create presentation framing churn as identified problem being proactively solved",
        "assignee": "Jennifer Martinez",
        "assignee_email": "jennifer.martinez@example.com",
        "due_date": (datetime.utcnow() + timedelta(days=4)).isoformat(),
        "priority": "urgent",
        "status": "pending",
        "confidence": 0.96,
        "source_timestamp": 3000,
        "extraction_reasoning": "Jennifer outlined: 'We need to be honest about churn but frame it as a solved problem'"
    }
]


# ============================================================================
# DECISION EXTRACTION RESPONSES
# ============================================================================

MOCK_DECISIONS_MEDIUM_MEETING = [
    {
        "decision": "Prioritize SSO integration over analytics dashboard",
        "context": "$500K in enterprise deals are contingent on SSO being ready by end of Q4. Analytics is important for retention but won't directly impact new revenue in the short term.",
        "decision_maker": "Sarah Chen",
        "decision_maker_email": "sarah.chen@example.com",
        "outcome": "approved",
        "impact": "high",
        "confidence": 0.98,
        "source_timestamp": 1080,
        "stakeholders": ["Marcus Rodriguez", "David Kim", "Emily Watson"],
        "rationale": "Revenue impact of $500K outweighs retention benefits of analytics in the short term",
        "alternatives_considered": ["Split engineering resources evenly", "Delay SSO to Q1"],
        "implementation_timeline": "Immediate - starting next week"
    },
    {
        "decision": "Push analytics dashboard completion to Q1 (mid-January)",
        "context": "Analytics dashboard needs backend API optimization which requires 2 engineers. Those resources are being allocated to SSO priority. David can continue with 1 engineer at slower pace.",
        "decision_maker": "Sarah Chen",
        "decision_maker_email": "sarah.chen@example.com",
        "outcome": "approved",
        "impact": "medium",
        "confidence": 0.95,
        "source_timestamp": 1260,
        "stakeholders": ["David Kim", "Marcus Rodriguez"],
        "rationale": "Acceptable delay given SSO revenue priority and David's ability to make progress with reduced resources",
        "implementation_timeline": "New target: mid-January"
    },
    {
        "decision": "Start mobile app beta testing in 2 weeks with 50 users",
        "context": "Mobile app MVP is ready with core features. Some UI bugs on Android need fixing and load testing required before wider release.",
        "decision_maker": "Marcus Rodriguez",
        "decision_maker_email": "marcus.rodriguez@example.com",
        "outcome": "approved",
        "impact": "medium",
        "confidence": 0.92,
        "source_timestamp": 1620,
        "stakeholders": ["Sarah Chen", "Emily Watson"],
        "rationale": "Limited beta allows validation with manageable risk while bugs are fixed",
        "implementation_timeline": "2 weeks from meeting date"
    }
]


MOCK_DECISIONS_LONG_MEETING = [
    {
        "decision": "Add second Customer Success manager to hiring plan",
        "context": "Current CS team (2 people) managing 127 customers, well above industry standard of 1:40-50 ratio. Contributing to slow support response times and churn.",
        "decision_maker": "Jennifer Martinez",
        "decision_maker_email": "jennifer.martinez@example.com",
        "outcome": "approved",
        "impact": "high",
        "confidence": 0.97,
        "source_timestamp": 3000,
        "stakeholders": ["Tom Anderson", "Lisa Park"],
        "rationale": "CS staffing gap is direct contributor to 7% churn rate. Additional hire is justified by churn data and increases burn only modestly to $190K.",
        "financial_impact": "+$5K monthly burn, justified by churn reduction potential",
        "implementation_timeline": "Include in Series A hiring plan"
    },
    {
        "decision": "Set post-fundraise monthly burn rate at $190K",
        "context": "Updated hiring plan with additional CS manager increases burn from planned $180K. Still within acceptable range for $5M raise, providing 18-month runway.",
        "decision_maker": "Tom Anderson",
        "decision_maker_email": "tom.anderson@example.com",
        "outcome": "approved",
        "impact": "high",
        "confidence": 0.96,
        "source_timestamp": 2700,
        "stakeholders": ["Jennifer Martinez", "Lisa Park"],
        "rationale": "18-month runway sufficient for achieving growth milestones and preparing for Series B",
        "financial_impact": "$190K monthly burn rate, 18-month runway on $5M raise",
        "implementation_timeline": "Effective upon fundraise close"
    },
    {
        "decision": "Frame churn issue as identified and being proactively solved in investor narrative",
        "context": "7% churn is concerning but root causes are clearly identified (mobile app, support speed, integrations) and solutions are in motion. Framing shows responsible leadership.",
        "decision_maker": "Jennifer Martinez",
        "decision_maker_email": "jennifer.martinez@example.com",
        "outcome": "approved",
        "impact": "medium",
        "confidence": 0.93,
        "source_timestamp": 3000,
        "stakeholders": ["Tom Anderson", "Marcus Taylor", "Lisa Park"],
        "rationale": "Transparency about challenges combined with clear mitigation plan demonstrates maturity and builds investor confidence",
        "implementation_timeline": "Incorporate into investor deck immediately"
    }
]


# ============================================================================
# SENTIMENT ANALYSIS RESPONSES
# ============================================================================

MOCK_SENTIMENT_SHORT_MEETING = {
    "overall_score": 0.6,
    "overall_label": "positive",
    "confidence": 0.88,
    "per_speaker": {
        "Alice Johnson": {
            "score": 0.7,
            "label": "positive",
            "confidence": 0.90,
            "tone": "confident and helpful"
        },
        "Bob Smith": {
            "score": 0.3,
            "label": "neutral",
            "confidence": 0.85,
            "tone": "focused but slightly frustrated by blocker"
        },
        "Carol Davis": {
            "score": 0.8,
            "label": "positive",
            "confidence": 0.92,
            "tone": "collaborative and solution-oriented"
        }
    },
    "trajectory": [
        {"timestamp": 0, "score": 0.6, "label": "positive"},
        {"timestamp": 60, "score": 0.4, "label": "neutral"},
        {"timestamp": 120, "score": 0.7, "label": "positive"},
        {"timestamp": 180, "score": 0.6, "label": "positive"},
        {"timestamp": 240, "score": 0.7, "label": "positive"}
    ],
    "key_moments": [
        {
            "timestamp": 60,
            "type": "concern_raised",
            "description": "Bob mentions blocker on production access",
            "sentiment_shift": -0.3
        },
        {
            "timestamp": 120,
            "type": "resolution_offered",
            "description": "Carol offers to resolve blocker immediately",
            "sentiment_shift": +0.4
        }
    ],
    "summary": "Overall positive team dynamic with collaborative problem-solving. Minor frustration around blocker quickly resolved by team support."
}


MOCK_SENTIMENT_MIXED_MEETING = {
    "overall_score": -0.1,
    "overall_label": "mixed",
    "confidence": 0.92,
    "per_speaker": {
        "Alex Thompson": {
            "score": 0.2,
            "label": "cautiously_positive",
            "confidence": 0.88,
            "tone": "accountable and forward-looking"
        },
        "Rachel Green": {
            "score": 0.6,
            "label": "positive",
            "confidence": 0.91,
            "tone": "proud of marketing success, optimistic about recovery"
        },
        "James Wilson": {
            "score": -0.7,
            "label": "negative",
            "confidence": 0.94,
            "tone": "frustrated and embarrassed by technical failures"
        },
        "Sarah Martinez": {
            "score": 0.3,
            "label": "neutral",
            "confidence": 0.87,
            "tone": "pragmatic, balancing negative experience with positive recovery"
        }
    },
    "trajectory": [
        {"timestamp": 0, "score": -0.3, "label": "cautiously_negative"},
        {"timestamp": 300, "score": 0.5, "label": "positive"},
        {"timestamp": 600, "score": -0.8, "label": "very_negative"},
        {"timestamp": 900, "score": -0.6, "label": "negative"},
        {"timestamp": 1200, "score": -0.4, "label": "slightly_negative"},
        {"timestamp": 1500, "score": 0.0, "label": "neutral"},
        {"timestamp": 1800, "score": 0.2, "label": "cautiously_positive"},
        {"timestamp": 2100, "score": 0.4, "label": "positive"}
    ],
    "key_moments": [
        {
            "timestamp": 300,
            "type": "peak_positive",
            "description": "Rachel celebrates marketing campaign success (5000 signups, 2x target)",
            "sentiment_shift": +0.8
        },
        {
            "timestamp": 600,
            "type": "peak_negative",
            "description": "James describes server crashes, user frustration, and Product Hunt rating drop",
            "sentiment_shift": -1.3
        },
        {
            "timestamp": 900,
            "type": "accountability_moment",
            "description": "Alex takes responsibility for pushing launch despite engineering concerns",
            "sentiment_shift": +0.2
        },
        {
            "timestamp": 1800,
            "type": "shift_to_positive",
            "description": "Team pivots to action items and recovery plan",
            "sentiment_shift": +0.6
        },
        {
            "timestamp": 2100,
            "type": "hopeful_conclusion",
            "description": "Rachel frames failure as opportunity for comeback story",
            "sentiment_shift": +0.2
        }
    ],
    "summary": "Meeting exhibited strong emotional arc from negative (discussing failure) to cautiously positive (planning recovery). Clear ownership of mistakes and transparent problem-solving approach. Team maintained psychological safety despite discussing painful failure."
}


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_mock_llm_response(response_type: str, meeting_type: str = "short") -> dict:
    """
    Get mock LLM response by type and meeting length.

    Args:
        response_type: One of 'summary', 'action_items', 'decisions', 'sentiment'
        meeting_type: One of 'short', 'medium', 'long'

    Returns:
        Dictionary with mock LLM response
    """
    responses = {
        "summary": {
            "short": MOCK_SUMMARY_SHORT_MEETING,
            "medium": MOCK_SUMMARY_MEDIUM_MEETING,
            "long": MOCK_SUMMARY_LONG_MEETING
        },
        "action_items": {
            "short": MOCK_ACTION_ITEMS_SHORT_MEETING,
            "medium": MOCK_ACTION_ITEMS_MEDIUM_MEETING,
            "long": MOCK_ACTION_ITEMS_LONG_MEETING
        },
        "decisions": {
            "short": [],
            "medium": MOCK_DECISIONS_MEDIUM_MEETING,
            "long": MOCK_DECISIONS_LONG_MEETING
        },
        "sentiment": {
            "short": MOCK_SENTIMENT_SHORT_MEETING,
            "medium": MOCK_SENTIMENT_SHORT_MEETING,  # Reuse positive sentiment
            "mixed": MOCK_SENTIMENT_MIXED_MEETING
        }
    }

    return responses.get(response_type, {}).get(meeting_type, {})
