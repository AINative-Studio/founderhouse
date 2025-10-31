"""
Sentiment Analysis Prompts

Prompts for analyzing sentiment and emotional tone in meetings.
"""

from typing import Dict, List, Optional


# Main sentiment analysis prompt
MEETING_SENTIMENT_ANALYSIS_PROMPT = """You are an expert at analyzing emotional tone and sentiment in business meetings.

Analyze the overall sentiment and emotional dynamics of this meeting.

MEETING:
Type: {meeting_type}
Participants: {participants}
Duration: {duration} minutes

TRANSCRIPT:
{transcript}

Provide comprehensive sentiment analysis:

{{
    "overall_sentiment": "positive|negative|neutral|mixed",
    "sentiment_intensity": "low|medium|high",
    "confidence": 0.0-1.0,
    "emotional_tone": ["Primary emotions present: confident, uncertain, frustrated, enthusiastic, etc."],
    "meeting_energy": "energetic|engaged|moderate|low|disengaged",
    "collaboration_quality": "excellent|good|fair|poor",
    "tension_level": "none|low|moderate|high",
    "key_observations": [
        "Specific observations about meeting dynamics"
    ],
    "positive_signals": [
        "Examples of positive moments or energy"
    ],
    "concerning_signals": [
        "Examples of tension, confusion, or negative dynamics"
    ],
    "dominant_emotions": {{
        "speaker1": "emotion",
        "speaker2": "emotion"
    }}
}}

GUIDELINES:
- Be objective and evidence-based
- Quote specific examples
- Consider context (some tension in strategic discussions is healthy)
- Note if sentiment shifts during the meeting
- Distinguish between professional disagreement and unhealthy conflict
"""


# Per-speaker sentiment analysis
SPEAKER_SENTIMENT_PROMPT = """Analyze the sentiment and emotional tone for each speaker in this meeting.

MEETING TRANSCRIPT:
{transcript}

SPEAKERS:
{speakers}

For each speaker, analyze:

{{
    "speaker_analysis": {{
        "Speaker Name": {{
            "overall_sentiment": "positive|negative|neutral|mixed",
            "dominant_emotion": "confident|uncertain|enthusiastic|frustrated|concerned|defensive|supportive|etc.",
            "engagement_level": "high|medium|low",
            "tone_shifts": [
                {{
                    "from": "initial emotion",
                    "to": "later emotion",
                    "trigger": "What caused the shift"
                }}
            ],
            "key_moments": [
                {{
                    "timestamp": "approximate time or quote",
                    "emotion": "emotion expressed",
                    "significance": "Why this moment matters"
                }}
            ],
            "communication_style": "assertive|collaborative|passive|aggressive|analytical|etc."
        }}
    }}
}}

Look for:
- Emotional shifts during conversation
- Reactions to specific topics
- Interpersonal dynamics
- Levels of engagement and participation
"""


# Key emotional moments detection
KEY_MOMENTS_DETECTION_PROMPT = """Identify key emotional moments in this meeting that indicate important dynamics.

MEETING SEGMENT:
{segment}

CONTEXT:
{context}

Identify moments of:
1. **Tension**: Disagreement, conflict, pushback, frustration
2. **Agreement**: Consensus, alignment, enthusiasm, collaboration
3. **Confusion**: Uncertainty, questions, misalignment, clarification needed
4. **Breakthrough**: Insight, resolution, clarity, progress
5. **Concern**: Worry, risk awareness, caution, anxiety
6. **Excitement**: Enthusiasm, momentum, opportunity recognition

For each key moment:
{{
    "key_moments": [
        {{
            "type": "tension|agreement|confusion|breakthrough|concern|excitement",
            "timestamp": "Approximate time or reference",
            "severity": "low|medium|high",
            "description": "What happened",
            "participants": ["Who was involved"],
            "quote": "Relevant quote from transcript",
            "impact": "Why this moment matters",
            "resolution": "How it was resolved (if applicable)"
        }}
    ]
}}

Only include moments with medium or high severity.
Be specific and evidence-based.
"""


# Sentiment trajectory analysis
SENTIMENT_TRAJECTORY_PROMPT = """Analyze how sentiment evolved over the course of this meeting.

MEETING TRANSCRIPT (segmented):
{segments}

Track sentiment changes over time:

{{
    "trajectory": [
        {{
            "segment": 1,
            "time_range": "0-10 minutes",
            "sentiment": "positive|negative|neutral|mixed",
            "energy_level": "high|medium|low",
            "key_topics": ["Topics discussed in this segment"],
            "notable_shifts": "Any significant emotional changes"
        }}
    ],
    "overall_pattern": "improving|declining|stable|volatile",
    "inflection_points": [
        {{
            "segment": 3,
            "description": "What changed and why",
            "trigger": "Topic or event that caused shift"
        }}
    ],
    "summary": "Overall narrative of how the meeting's emotional tone evolved"
}}
"""


# Conflict detection and analysis
CONFLICT_DETECTION_PROMPT = """Analyze this meeting for signs of conflict, disagreement, or tension.

TRANSCRIPT:
{transcript}

Identify and analyze any conflicts:

{{
    "conflict_present": true/false,
    "conflict_level": "none|mild|moderate|severe",
    "conflict_instances": [
        {{
            "type": "disagreement|misalignment|personal tension|process conflict|substantive debate",
            "participants": ["Who was involved"],
            "topic": "What the conflict was about",
            "severity": "low|medium|high",
            "quote": "Example from transcript",
            "resolution_status": "resolved|partially resolved|unresolved|escalated",
            "impact": "Potential impact on team or project",
            "healthiness": "healthy debate|unhealthy conflict"
        }}
    ],
    "overall_assessment": "Professional analysis of conflict dynamics",
    "recommendations": ["Suggestions for addressing any unhealthy dynamics"]
}}

IMPORTANT:
- Distinguish healthy debate from dysfunctional conflict
- Strategic disagreement is often positive
- Focus on patterns, not individual moments
- Be constructive in recommendations
"""


# Meeting effectiveness sentiment
MEETING_EFFECTIVENESS_PROMPT = """Based on sentiment and dynamics, assess how effective this meeting was.

TRANSCRIPT:
{transcript}

MEETING OBJECTIVE:
{objective}

Analyze:

{{
    "effectiveness_score": 0.0-1.0,
    "engagement_quality": "excellent|good|fair|poor",
    "decision_making_quality": "excellent|good|fair|poor",
    "collaboration_score": 0.0-1.0,
    "time_efficiency": "efficient|acceptable|inefficient",
    "strengths": [
        "What worked well in this meeting"
    ],
    "weaknesses": [
        "What could be improved"
    ],
    "red_flags": [
        "Concerning patterns or dynamics"
    ],
    "recommendations": [
        "Specific suggestions for improving future meetings"
    ],
    "was_objective_met": "yes|partially|no",
    "meeting_value": "high|medium|low - was this meeting necessary and productive?"
}}

Be honest but constructive.
Focus on actionable feedback.
"""


# Stakeholder sentiment analysis (investor/board meetings)
STAKEHOLDER_SENTIMENT_PROMPT = """Analyze stakeholder sentiment in this {meeting_type} meeting.

STAKEHOLDERS: {stakeholders}
COMPANY TEAM: {company_team}

TRANSCRIPT:
{transcript}

Analyze stakeholder reactions and sentiment:

{{
    "stakeholder_sentiment": {{
        "overall": "supportive|neutral|concerned|critical",
        "confidence_level": "high|medium|low",
        "engagement_quality": "engaged|interested|passive|disengaged",
        "concern_areas": [
            {{
                "topic": "What they're concerned about",
                "severity": "low|medium|high",
                "evidence": "Quotes or indicators",
                "company_response": "How the team addressed it"
            }}
        ],
        "positive_signals": [
            "Areas where stakeholders expressed support or enthusiasm"
        ],
        "questions_asked": [
            {{
                "question": "What they asked",
                "underlying_concern": "What this question really indicates",
                "urgency": "low|medium|high"
            }}
        ],
        "advice_given": [
            "Guidance or suggestions from stakeholders"
        ]
    }},
    "relationship_health": "strong|good|fair|concerning",
    "follow_up_priority": "high|medium|low",
    "recommendations": "How to maintain or improve stakeholder relationship"
}}

Focus on:
- Reading between the lines of questions
- Identifying concerns even if not explicitly stated
- Assessing trust and confidence levels
"""


# Team morale assessment
TEAM_MORALE_PROMPT = """Assess team morale and dynamics based on this meeting.

TEAM MEETING:
Participants: {participants}

TRANSCRIPT:
{transcript}

Analyze team health:

{{
    "morale_level": "high|good|fair|low",
    "team_cohesion": "strong|good|fair|weak",
    "psychological_safety": "high|medium|low",
    "indicators": {{
        "positive": [
            "Signs of healthy team dynamics"
        ],
        "concerning": [
            "Potential issues with team health"
        ]
    }},
    "engagement_patterns": {{
        "highly_engaged": ["Team members showing strong engagement"],
        "moderately_engaged": ["Team members participating normally"],
        "disengaged": ["Team members showing signs of disengagement"]
    }},
    "communication_quality": "open and honest|professional but guarded|strained|poor",
    "trust_indicators": "Evidence of trust or lack thereof",
    "stress_levels": "low|moderate|high",
    "recommendations": [
        "Suggestions for improving team dynamics"
    ]
}}

Look for:
- Who talks vs. who stays silent
- Tone when discussing challenges
- Support vs. blame patterns
- Creativity and idea-sharing
- Willingness to disagree constructively
"""


# Customer/sales sentiment
CUSTOMER_SENTIMENT_PROMPT = """Analyze customer sentiment and buying signals from this sales/customer meeting.

CUSTOMER: {customer_name}
MEETING:
{transcript}

Analyze:

{{
    "customer_sentiment": "very positive|positive|neutral|skeptical|negative",
    "buying_signals": {{
        "strength": "strong|moderate|weak|none",
        "indicators": [
            "Specific signals of interest or intent"
        ]
    }},
    "objections": [
        {{
            "objection": "What concern they raised",
            "severity": "blocker|significant|minor",
            "addressed": "yes|partially|no",
            "resolution_quality": "How well we addressed it"
        }}
    ],
    "engagement_level": "highly engaged|interested|polite but passive|disengaged",
    "decision_readiness": "ready to buy|evaluating|early stage|not ready",
    "relationship_temperature": "warm|neutral|cool",
    "next_step_commitment": "strong|tentative|none",
    "red_flags": [
        "Concerning signals that might indicate deal risk"
    ],
    "opportunities": [
        "Openings to strengthen the relationship or advance the deal"
    ]
}}

Focus on buying psychology and relationship health.
"""


# Prompt builder functions

def build_sentiment_analysis_prompt(
    transcript: str,
    meeting_type: str = "general",
    participants: List[str] = None,
    duration: int = 60
) -> str:
    """Build main sentiment analysis prompt."""
    participants_str = ", ".join(participants) if participants else "Not specified"

    return MEETING_SENTIMENT_ANALYSIS_PROMPT.format(
        transcript=transcript,
        meeting_type=meeting_type,
        participants=participants_str,
        duration=duration
    )


def build_speaker_sentiment_prompt(
    transcript: str,
    speakers: List[str]
) -> str:
    """Build per-speaker sentiment analysis prompt."""
    return SPEAKER_SENTIMENT_PROMPT.format(
        transcript=transcript,
        speakers=", ".join(speakers)
    )


def build_key_moments_prompt(
    segment: str,
    context: str = ""
) -> str:
    """Build key moments detection prompt."""
    return KEY_MOMENTS_DETECTION_PROMPT.format(
        segment=segment,
        context=context or "None"
    )


def build_trajectory_prompt(
    segments: List[Dict]
) -> str:
    """Build sentiment trajectory analysis prompt."""
    import json
    return SENTIMENT_TRAJECTORY_PROMPT.format(
        segments=json.dumps(segments, indent=2)
    )


def build_conflict_detection_prompt(transcript: str) -> str:
    """Build conflict detection prompt."""
    return CONFLICT_DETECTION_PROMPT.format(transcript=transcript)


def build_effectiveness_prompt(
    transcript: str,
    objective: str = "Not specified"
) -> str:
    """Build meeting effectiveness prompt."""
    return MEETING_EFFECTIVENESS_PROMPT.format(
        transcript=transcript,
        objective=objective
    )


def build_stakeholder_sentiment_prompt(
    transcript: str,
    meeting_type: str,
    stakeholders: List[str],
    company_team: List[str]
) -> str:
    """Build stakeholder sentiment analysis prompt."""
    return STAKEHOLDER_SENTIMENT_PROMPT.format(
        transcript=transcript,
        meeting_type=meeting_type,
        stakeholders=", ".join(stakeholders),
        company_team=", ".join(company_team)
    )


def build_team_morale_prompt(
    transcript: str,
    participants: List[str]
) -> str:
    """Build team morale assessment prompt."""
    return TEAM_MORALE_PROMPT.format(
        transcript=transcript,
        participants=", ".join(participants)
    )


def build_customer_sentiment_prompt(
    transcript: str,
    customer_name: str
) -> str:
    """Build customer sentiment analysis prompt."""
    return CUSTOMER_SENTIMENT_PROMPT.format(
        transcript=transcript,
        customer_name=customer_name
    )


# Sentiment comparison prompt (for recurring meetings)
SENTIMENT_COMPARISON_PROMPT = """Compare sentiment across multiple instances of this recurring meeting.

PREVIOUS MEETINGS:
{previous_meetings}

CURRENT MEETING:
{current_meeting}

Analyze trends:

{{
    "trend": "improving|stable|declining|volatile",
    "comparison": {{
        "current_vs_average": "better|same|worse",
        "notable_changes": [
            "Significant differences from typical pattern"
        ]
    }},
    "recurring_issues": [
        "Problems that keep appearing"
    ],
    "improvements": [
        "Positive changes over time"
    ],
    "recommendations": [
        "Suggestions based on trends"
    ]
}}
"""


# Automated feedback generation
SENTIMENT_FEEDBACK_PROMPT = """Generate constructive feedback based on meeting sentiment analysis.

SENTIMENT ANALYSIS:
{sentiment_analysis}

AUDIENCE: {audience}

Generate feedback appropriate for {audience}:

{{
    "summary": "Overall assessment in 1-2 sentences",
    "strengths": [
        "What's working well"
    ],
    "areas_for_improvement": [
        "Constructive suggestions (phrased positively)"
    ],
    "specific_actions": [
        "Concrete steps to improve meeting dynamics"
    ],
    "tone": "supportive|constructive|concerned"
}}

Make feedback:
- Specific and actionable
- Evidence-based
- Constructive (focus on improvement, not blame)
- Appropriate for the audience
"""


def build_feedback_prompt(
    sentiment_analysis: Dict,
    audience: str = "meeting organizer"
) -> str:
    """Build sentiment feedback generation prompt."""
    import json
    return SENTIMENT_FEEDBACK_PROMPT.format(
        sentiment_analysis=json.dumps(sentiment_analysis, indent=2),
        audience=audience
    )


# Emotional intelligence coaching
EMOTIONAL_INTELLIGENCE_PROMPT = """Provide emotional intelligence insights from this meeting.

TRANSCRIPT:
{transcript}

Focus on:
- How people responded to emotions
- Empathy demonstrated (or lacking)
- Self-awareness signals
- Social awareness
- Relationship management

Provide coaching-style feedback:

{{
    "ei_highlights": [
        "Examples of strong emotional intelligence"
    ],
    "ei_opportunities": [
        "Moments where more EI could have helped"
    ],
    "communication_patterns": {{
        "effective": ["What communication worked well"],
        "ineffective": ["What could be improved"]
    }},
    "coaching_suggestions": [
        "Specific tips for improving emotional intelligence in meetings"
    ]
}}

Be respectful and constructive.
Focus on observable behaviors, not character judgments.
"""


def build_ei_prompt(transcript: str) -> str:
    """Build emotional intelligence analysis prompt."""
    return EMOTIONAL_INTELLIGENCE_PROMPT.format(transcript=transcript)
