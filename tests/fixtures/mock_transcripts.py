"""
AI Chief of Staff - Mock Transcript Data
Sprint 3: Issue #7, #8 - Meeting Intelligence Testing

Sample transcripts for testing meeting intelligence features:
- Short, medium, and long meetings
- Meetings with action items
- Meetings with decisions
- Multi-speaker meetings
"""

from datetime import datetime, timedelta


# ============================================================================
# SHORT MEETING (5 minutes)
# ============================================================================

SHORT_MEETING_TRANSCRIPT = {
    "title": "Quick Standup",
    "duration_seconds": 300,
    "speaker_count": 3,
    "recorded_at": (datetime.utcnow() - timedelta(hours=1)).isoformat(),
    "chunks": [
        {
            "start_sec": 0,
            "end_sec": 60,
            "speaker": "Alice Johnson",
            "text": "Good morning everyone! Let's do a quick standup. I'll start. Yesterday I finished the user authentication module and pushed it to staging. Today I'm going to work on the password reset flow. No blockers for me."
        },
        {
            "start_sec": 60,
            "end_sec": 120,
            "speaker": "Bob Smith",
            "text": "Thanks Alice. I completed the database migration for the new schema. Today I'm planning to optimize the queries for the dashboard. I'm blocked on getting access to the production database though."
        },
        {
            "start_sec": 120,
            "end_sec": 180,
            "speaker": "Carol Davis",
            "text": "I can help you with that Bob, I'll send you the credentials right after this call. On my end, I finished the UI mockups for the settings page. Today I'll implement the responsive layout."
        },
        {
            "start_sec": 180,
            "end_sec": 240,
            "speaker": "Alice Johnson",
            "text": "Great updates everyone. Bob, make sure to test those optimizations on a staging copy first before touching production. Carol, can you also review my authentication PR when you get a chance?"
        },
        {
            "start_sec": 240,
            "end_sec": 300,
            "speaker": "Carol Davis",
            "text": "Will do! I'll review it this afternoon. Alright, let's get back to work everyone. Talk to you tomorrow!"
        }
    ],
    "expected_action_items": [
        {
            "task": "Send Bob production database credentials",
            "assignee": "Carol Davis",
            "priority": "high"
        },
        {
            "task": "Test query optimizations on staging",
            "assignee": "Bob Smith",
            "priority": "normal"
        },
        {
            "task": "Review Alice's authentication PR",
            "assignee": "Carol Davis",
            "priority": "normal"
        }
    ],
    "expected_summary": "Quick standup meeting covering progress on authentication, database optimization, and UI implementation. Team is making good progress with minimal blockers."
}


# ============================================================================
# MEDIUM MEETING (30 minutes)
# ============================================================================

MEDIUM_MEETING_TRANSCRIPT = {
    "title": "Product Roadmap Review",
    "duration_seconds": 1800,
    "speaker_count": 4,
    "recorded_at": (datetime.utcnow() - timedelta(hours=2)).isoformat(),
    "chunks": [
        {
            "start_sec": 0,
            "end_sec": 180,
            "speaker": "Sarah Chen",
            "text": "Thanks everyone for joining. Today we're reviewing our Q4 product roadmap. We have three major initiatives: the new analytics dashboard, mobile app launch, and enterprise SSO integration. Let's start with analytics. David, can you give us an update?"
        },
        {
            "start_sec": 180,
            "end_sec": 360,
            "speaker": "David Kim",
            "text": "Sure. The analytics dashboard is about 70% complete. We've implemented the core metrics visualization and the custom report builder. What's remaining is the real-time data streaming and the export functionality. I estimate we need another 3 weeks to finish. The main blocker right now is the backend API for streaming - it's not optimized yet."
        },
        {
            "start_sec": 360,
            "end_sec": 540,
            "speaker": "Sarah Chen",
            "text": "Three weeks puts us right at the edge of our Q4 deadline. Can we prioritize the streaming optimization? Marcus, can your team help with the backend API?"
        },
        {
            "start_sec": 540,
            "end_sec": 720,
            "speaker": "Marcus Rodriguez",
            "text": "Yes, we can allocate two engineers starting next week. However, we're also working on the SSO integration which is critical for the enterprise deals we're closing. We might need to decide which takes priority."
        },
        {
            "start_sec": 720,
            "end_sec": 900,
            "speaker": "Sarah Chen",
            "text": "Good point. Let's discuss the business impact. Emily, from a revenue perspective, which is more critical - analytics or SSO?"
        },
        {
            "start_sec": 900,
            "end_sec": 1080,
            "speaker": "Emily Watson",
            "text": "SSO is absolutely critical. We have $500K in deals that are contingent on SSO being ready by end of Q4. Analytics is important for retention but won't directly impact new revenue in the short term. I recommend we prioritize SSO."
        },
        {
            "start_sec": 1080,
            "end_sec": 1260,
            "speaker": "Sarah Chen",
            "text": "Okay, decision made. Marcus, your team focuses on SSO as top priority. David, can you work with one backend engineer while the SSO work is in progress, and then get full support after SSO ships?"
        },
        {
            "start_sec": 1260,
            "end_sec": 1440,
            "speaker": "David Kim",
            "text": "That works. It'll push analytics into early Q1, probably mid-January completion. Is that acceptable?"
        },
        {
            "start_sec": 1440,
            "end_sec": 1620,
            "speaker": "Sarah Chen",
            "text": "Yes, Q1 is fine. Now let's talk mobile. Marcus, what's the status on the React Native app?"
        },
        {
            "start_sec": 1620,
            "end_sec": 1800,
            "speaker": "Marcus Rodriguez",
            "text": "The mobile app MVP is ready for beta testing. We've built out the core features - login, dashboard view, and notifications. We need to do load testing and fix some UI bugs on Android. I'd say we can start beta in 2 weeks with 50 users, then expand from there. Sarah, can you coordinate with Emily on selecting beta testers from our customer base?"
        }
    ],
    "expected_action_items": [
        {
            "task": "Prioritize SSO integration work",
            "assignee": "Marcus Rodriguez",
            "priority": "urgent"
        },
        {
            "task": "Allocate two backend engineers to SSO project",
            "assignee": "Marcus Rodriguez",
            "priority": "high"
        },
        {
            "task": "Continue analytics dashboard with one engineer",
            "assignee": "David Kim",
            "priority": "normal"
        },
        {
            "task": "Coordinate beta tester selection with Emily",
            "assignee": "Sarah Chen",
            "priority": "normal"
        },
        {
            "task": "Complete load testing and Android UI fixes",
            "assignee": "Marcus Rodriguez",
            "priority": "high"
        }
    ],
    "expected_decisions": [
        {
            "decision": "Prioritize SSO integration over analytics dashboard",
            "decision_maker": "Sarah Chen",
            "outcome": "approved",
            "impact": "high",
            "context": "$500K in enterprise deals contingent on SSO"
        },
        {
            "decision": "Push analytics dashboard completion to Q1 (mid-January)",
            "decision_maker": "Sarah Chen",
            "outcome": "approved",
            "impact": "medium"
        },
        {
            "decision": "Start mobile app beta testing in 2 weeks with 50 users",
            "decision_maker": "Marcus Rodriguez",
            "outcome": "approved",
            "impact": "medium"
        }
    ],
    "expected_summary": "Product roadmap review covering Q4 initiatives. Key decision: SSO integration prioritized over analytics due to $500K in pending enterprise deals. Analytics pushed to Q1. Mobile app ready for beta testing in 2 weeks."
}


# ============================================================================
# LONG MEETING (1 hour)
# ============================================================================

LONG_MEETING_TRANSCRIPT = {
    "title": "Investor Update Preparation",
    "duration_seconds": 3600,
    "speaker_count": 5,
    "recorded_at": (datetime.utcnow() - timedelta(hours=3)).isoformat(),
    "chunks": [
        {
            "start_sec": 0,
            "end_sec": 300,
            "speaker": "Jennifer Martinez",
            "text": "Welcome everyone. We're meeting today to prepare for our Series A investor update next week. We need to review our metrics, discuss challenges openly, and align on our narrative. Let's start with the metrics. Tom, can you walk us through the numbers?"
        },
        {
            "start_sec": 300,
            "end_sec": 600,
            "speaker": "Tom Anderson",
            "text": "Sure. Good news first - our MRR grew 35% this quarter to $180K. We added 42 new customers, which is above our target of 35. Customer acquisition cost is down to $1,200 from $1,500 last quarter due to our improved content marketing. However, we're seeing concerning churn - it's at 7% monthly, up from 4% last quarter."
        },
        {
            "start_sec": 600,
            "end_sec": 900,
            "speaker": "Jennifer Martinez",
            "text": "That churn number is worrying. Do we understand what's driving it? This is going to be the first question investors ask."
        },
        {
            "start_sec": 900,
            "end_sec": 1200,
            "speaker": "Lisa Park",
            "text": "We've done exit interviews with 15 of the churned customers. The top reasons are: lack of mobile app, slow customer support response times, and missing integrations with their existing tools. The mobile app issue comes up in 60% of churn conversations."
        },
        {
            "start_sec": 1200,
            "end_sec": 1500,
            "speaker": "Jennifer Martinez",
            "text": "Okay, so we have clear product gaps. Marcus, what's our timeline on mobile and integrations?"
        },
        {
            "start_sec": 1500,
            "end_sec": 1800,
            "speaker": "Marcus Taylor",
            "text": "Mobile app beta launches in 3 weeks. We're targeting iOS first, then Android in 6 weeks. For integrations, we have Salesforce and HubSpot in development, shipping next month. But here's the challenge - we're stretched thin. The team is at capacity and we're getting burnout signals."
        },
        {
            "start_sec": 1800,
            "end_sec": 2100,
            "speaker": "Jennifer Martinez",
            "text": "That's exactly why we're raising this Series A. We need to hire. Tom, what's our cash runway and hiring plan?"
        },
        {
            "start_sec": 2100,
            "end_sec": 2400,
            "speaker": "Tom Anderson",
            "text": "Current runway is 8 months at our current burn rate of $95K monthly. If we raise the $5M we're targeting, that extends runway to 18 months. The hiring plan is aggressive: 3 engineers, 2 sales reps, 1 customer success manager, and 1 product marketer. That increases our monthly burn to about $180K but should 3x our growth rate."
        },
        {
            "start_sec": 2400,
            "end_sec": 2700,
            "speaker": "Lisa Park",
            "text": "I want to add context on customer success. Our current CS team is me and one other person handling 127 customers. Industry standard is 1 CS person per 40-50 customers. We're drowning and it's showing in our response times and ultimately in churn. Adding one CS manager isn't enough - we need at least two."
        },
        {
            "start_sec": 2700,
            "end_sec": 3000,
            "speaker": "Tom Anderson",
            "text": "Adding another CS hire increases burn to $190K. Still within acceptable range for our raise size. I think it's justified given the churn data."
        },
        {
            "start_sec": 3000,
            "end_sec": 3300,
            "speaker": "Jennifer Martinez",
            "text": "Agreed. Let's update the hiring plan to include 2 CS managers. Now, let's talk about the investor narrative. We need to be honest about the churn issue but frame it as a solved problem. We know the root causes, we have the product roadmap to address them, and we're raising capital specifically to accelerate those fixes and scale CS."
        },
        {
            "start_sec": 3300,
            "end_sec": 3600,
            "speaker": "Marcus Taylor",
            "text": "I like that framing. We can show them the mobile app demo even though it's beta, demonstrate that we're shipping. We can also showcase the integration pipeline. The narrative is: we've achieved strong growth, identified scaling challenges early, and are raising capital to solve them proactively rather than reactively."
        }
    ],
    "expected_action_items": [
        {
            "task": "Update hiring plan to include 2 Customer Success managers",
            "assignee": "Tom Anderson",
            "priority": "high",
            "due_date": (datetime.utcnow() + timedelta(days=2)).isoformat()
        },
        {
            "task": "Prepare mobile app demo for investor presentation",
            "assignee": "Marcus Taylor",
            "priority": "urgent",
            "due_date": (datetime.utcnow() + timedelta(days=5)).isoformat()
        },
        {
            "task": "Create integrations roadmap slide",
            "assignee": "Marcus Taylor",
            "priority": "high",
            "due_date": (datetime.utcnow() + timedelta(days=3)).isoformat()
        },
        {
            "task": "Compile churn analysis report with root causes",
            "assignee": "Lisa Park",
            "priority": "high",
            "due_date": (datetime.utcnow() + timedelta(days=3)).isoformat()
        },
        {
            "task": "Update financial model with revised burn rate",
            "assignee": "Tom Anderson",
            "priority": "high",
            "due_date": (datetime.utcnow() + timedelta(days=2)).isoformat()
        },
        {
            "task": "Draft investor narrative deck",
            "assignee": "Jennifer Martinez",
            "priority": "urgent",
            "due_date": (datetime.utcnow() + timedelta(days=4)).isoformat()
        }
    ],
    "expected_decisions": [
        {
            "decision": "Add second Customer Success manager to hiring plan",
            "decision_maker": "Jennifer Martinez",
            "outcome": "approved",
            "impact": "high",
            "context": "Current CS team is underwater at 127 customers for 2 people, contributing to churn"
        },
        {
            "decision": "Updated monthly burn rate to $190K post-fundraise",
            "decision_maker": "Tom Anderson",
            "outcome": "approved",
            "impact": "high"
        },
        {
            "decision": "Frame churn issue as identified and being proactively solved",
            "decision_maker": "Jennifer Martinez",
            "outcome": "approved",
            "impact": "medium"
        }
    ],
    "expected_summary": "Investor update preparation meeting. MRR at $180K (+35% quarterly), but churn at 7% (up from 4%) due to missing mobile app, slow support, and lack of integrations. Team is addressing with mobile beta in 3 weeks and hiring 2 CS managers. Raising $5M Series A to extend runway to 18 months and fund aggressive hiring plan."
}


# ============================================================================
# MEETING WITH MIXED SENTIMENT
# ============================================================================

MIXED_SENTIMENT_MEETING = {
    "title": "Product Launch Post-Mortem",
    "duration_seconds": 2400,
    "speaker_count": 4,
    "chunks": [
        {
            "start_sec": 0,
            "end_sec": 300,
            "speaker": "Alex Thompson",
            "text": "Thanks for joining this post-mortem. I know last week's product launch didn't go as planned, and I want to create a safe space to discuss what happened openly. No blame, just learning. Let's start with what went well, then what didn't, then action items."
        },
        {
            "start_sec": 300,
            "end_sec": 600,
            "speaker": "Rachel Green",
            "text": "I'll start with the positives. Our marketing campaign was fantastic - we generated 5,000 sign-ups in the first 24 hours, which exceeded our target by 2x. The messaging resonated, the landing page conversion rate was 12%, and the PR coverage was excellent. We trended on Product Hunt for the entire day."
        },
        {
            "start_sec": 600,
            "end_sec": 900,
            "speaker": "James Wilson",
            "text": "Unfortunately, the product couldn't handle that success. Our servers crashed twice in the first 6 hours. Users experienced 30-second load times. The onboarding flow broke for new users. We got absolutely roasted on Twitter and our rating on Product Hunt dropped from 4.8 to 3.2 stars by end of day. This was embarrassing and entirely preventable."
        },
        {
            "start_sec": 900,
            "end_sec": 1200,
            "speaker": "Alex Thompson",
            "text": "I take full responsibility for this. I pushed for the launch date despite concerns from engineering that we needed more load testing. James, what specifically broke and why?"
        },
        {
            "start_sec": 1200,
            "end_sec": 1500,
            "speaker": "James Wilson",
            "text": "The database connection pool was configured for 100 concurrent users. We hit 3,000 concurrent users within the first hour. The onboarding flow had a memory leak we didn't catch because we never tested with that volume. And our CDN cache was misconfigured, so every request hit our origin servers. All of these issues were discoverable with proper load testing."
        },
        {
            "start_sec": 1500,
            "end_sec": 1800,
            "speaker": "Sarah Martinez",
            "text": "From a customer perspective, we lost credibility. I spent the entire day apologizing to angry users on Twitter and support tickets. However, and this is important, we were transparent about the issues, we kept users updated every hour, and we offered refunds. About 30% of users appreciated our transparency and stuck with us."
        },
        {
            "start_sec": 1800,
            "end_sec": 2100,
            "speaker": "Alex Thompson",
            "text": "Okay, let's turn this into action. James, I want you to lead a complete infrastructure audit. Sarah, let's create a launch playbook so this never happens again. Rachel, can we do a re-launch campaign in 4 weeks to win back the users we lost?"
        },
        {
            "start_sec": 2100,
            "end_sec": 2400,
            "speaker": "Rachel Green",
            "text": "Yes, I like the idea of turning this failure into a comeback story. We can position it as 'We listened, we fixed everything, here's the product you were promised.' I think we can recover. This stings now, but it's not fatal if we act fast."
        }
    ],
    "expected_sentiment": {
        "overall_label": "mixed",
        "overall_score": -0.1,
        "trajectory": [
            {"timestamp": 0, "score": -0.3, "label": "negative"},
            {"timestamp": 600, "score": 0.5, "label": "positive"},
            {"timestamp": 900, "score": -0.8, "label": "very_negative"},
            {"timestamp": 1800, "score": 0.2, "label": "cautiously_positive"}
        ]
    }
}


# ============================================================================
# MEETING WITH MULTIPLE SPEAKERS AND CROSS-TALK
# ============================================================================

MULTI_SPEAKER_MEETING = {
    "title": "Engineering All-Hands",
    "duration_seconds": 1200,
    "speaker_count": 6,
    "chunks": [
        {
            "start_sec": 0,
            "end_sec": 180,
            "speaker": "Chris Lee",
            "text": "Welcome to our monthly engineering all-hands. We have about 20 minutes. Quick updates from each team lead, then open floor for questions. Backend team first - Jordan, what's your update?"
        },
        {
            "start_sec": 180,
            "end_sec": 300,
            "speaker": "Jordan Smith",
            "text": "We completed the API v2 migration. All endpoints are now versioned and documented. We also reduced average API response time from 450ms to 180ms through caching improvements. Next month we're focusing on WebSocket infrastructure for real-time features."
        },
        {
            "start_sec": 300,
            "end_sec": 420,
            "speaker": "Maria Garcia",
            "text": "Frontend here. We shipped the new component library I mentioned last month. It's reduced our build time by 40% and made the UI much more consistent. We're refactoring the dashboard to use the new components. Aiming to have that done by end of month."
        },
        {
            "start_sec": 420,
            "end_sec": 540,
            "speaker": "Raj Patel",
            "text": "DevOps update: we migrated to Kubernetes and it's been smooth. Deploy time went from 15 minutes to 3 minutes. We also set up proper staging environments for each team. Infrastructure costs actually decreased by 20% despite the added environments due to better resource utilization."
        },
        {
            "start_sec": 540,
            "end_sec": 660,
            "speaker": "Nina Okoye",
            "text": "QA and testing update: we hit 85% code coverage this month, up from 72%. We also implemented visual regression testing using Percy. We caught 23 UI bugs before they reached production. The team is growing - we hired two more QA engineers who start next week."
        },
        {
            "start_sec": 660,
            "end_sec": 780,
            "speaker": "Chris Lee",
            "text": "Great updates everyone. Open floor now - any questions or concerns? Anyone need help from another team?"
        },
        {
            "start_sec": 780,
            "end_sec": 900,
            "speaker": "Jordan Smith",
            "text": "Quick ask for Maria's team - can we coordinate on the WebSocket work? The real-time features need updates on both backend and frontend. Let's sync after this call."
        },
        {
            "start_sec": 900,
            "end_sec": 1020,
            "speaker": "Maria Garcia",
            "text": "Absolutely. I'll send you our WebSocket requirements doc and we can do a technical design review together. Maybe loop in Raj too for infrastructure considerations?"
        },
        {
            "start_sec": 1020,
            "end_sec": 1140,
            "speaker": "Raj Patel",
            "text": "Sounds good. I can set up a WebSocket-ready environment in staging for you to test against. Just give me a heads up a day before you need it."
        },
        {
            "start_sec": 1140,
            "end_sec": 1200,
            "speaker": "Chris Lee",
            "text": "Perfect. Love seeing this cross-team collaboration. That's exactly what these all-hands are for. Great work everyone, see you next month."
        }
    ],
    "expected_action_items": [
        {
            "task": "Sync on WebSocket implementation requirements",
            "assignee": "Jordan Smith",
            "priority": "normal"
        },
        {
            "task": "Send WebSocket requirements doc to Jordan",
            "assignee": "Maria Garcia",
            "priority": "normal"
        },
        {
            "task": "Set up WebSocket-ready staging environment",
            "assignee": "Raj Patel",
            "priority": "normal"
        }
    ]
}


# ============================================================================
# UTILITY FUNCTION
# ============================================================================

def get_transcript_by_type(transcript_type: str) -> dict:
    """
    Get sample transcript by type.

    Args:
        transcript_type: One of 'short', 'medium', 'long', 'mixed_sentiment', 'multi_speaker'

    Returns:
        Dictionary with transcript data
    """
    transcripts = {
        "short": SHORT_MEETING_TRANSCRIPT,
        "medium": MEDIUM_MEETING_TRANSCRIPT,
        "long": LONG_MEETING_TRANSCRIPT,
        "mixed_sentiment": MIXED_SENTIMENT_MEETING,
        "multi_speaker": MULTI_SPEAKER_MEETING
    }

    return transcripts.get(transcript_type, SHORT_MEETING_TRANSCRIPT)
