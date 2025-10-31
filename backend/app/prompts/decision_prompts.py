"""
Decision Extraction Prompts

Prompts for identifying and extracting decisions from meeting transcripts.
"""

from typing import Dict, List, Optional


# Main decision extraction prompt
DECISION_EXTRACTION_PROMPT = """You are an expert at identifying decisions made during meetings.

A decision is a resolved choice or commitment about what to do, not just a discussion topic.

WHAT IS A DECISION:
✓ "We're going with option A" - DECISION
✓ "Let's move forward with the new pricing" - DECISION
✓ "I'm approving the hire" - DECISION
✓ "We decided to push the launch to Q2" - DECISION

WHAT IS NOT A DECISION:
✗ "We should think about option A" - just discussion
✗ "What if we tried the new pricing?" - question/exploration
✗ "I'm leaning towards approving" - not final
✗ "We talked about pushing the launch" - discussion only

MEETING CONTEXT:
Type: {meeting_type}
Participants: {participants}
Date: {date}

TRANSCRIPT:
{transcript}

Extract all decisions made in this meeting. For each decision provide:

{{
    "decisions": [
        {{
            "decision": "Clear statement of what was decided",
            "decision_maker": "Person or group who made the decision",
            "category": "strategic|tactical|operational|personnel|financial|product",
            "rationale": "Why this decision was made (key reasoning)",
            "alternatives_considered": ["Other options that were discussed"],
            "impact": "Expected impact or importance of this decision",
            "implementation_timeline": "When this takes effect or gets implemented",
            "confidence": 0.0-1.0 (your confidence this is a genuine decision),
            "source_quote": "Quote from transcript showing the decision",
            "context": "Background context for understanding this decision",
            "reversible": true/false (can this decision be easily changed)
        }}
    ]
}}

GUIDELINES:
- Only include items with confidence ≥ 0.7
- Distinguish between tentative ("we're leaning toward...") and firm decisions
- Note if consensus was reached or if it was a unilateral decision
- Capture the rationale - this is critical for future context
- If multiple options were discussed, list them in alternatives_considered
"""


# Decision validation prompt
DECISION_VALIDATION_PROMPT = """Validate whether this is a genuine decision or just a discussion.

CANDIDATE DECISION:
Text: "{text}"
Speaker: {speaker}
Context: {context}

Is this a firm decision or just discussion/exploration?

Check for:
1. Finality language: "we will", "decided to", "going with", "approved"
2. vs. Tentative language: "we should", "let's explore", "what if", "maybe"
3. Authority: Does the speaker have authority to make this decision?
4. Consensus indicators: Did others agree or was there pushback?

Respond in JSON:
{{
    "is_decision": true/false,
    "decision": "Clear statement of what was decided (if valid)",
    "decision_maker": "Who decided",
    "finality": "firm|tentative|pending",
    "category": "strategic|tactical|operational|personnel|financial|product",
    "confidence": 0.0-1.0,
    "reasoning": "Why this is/isn't a decision"
}}

If this is tentative or pending additional input, note that in finality.
"""


# Decision impact analysis prompt
DECISION_IMPACT_ANALYSIS_PROMPT = """Analyze the potential impact of this decision.

DECISION:
{decision}

MEETING CONTEXT:
{meeting_context}

Analyze:
1. Scope: How many people/processes does this affect?
2. Timeline: Short-term or long-term impact?
3. Reversibility: How hard would it be to undo?
4. Dependencies: What else depends on this decision?
5. Risk: What could go wrong?

Return JSON:
{{
    "impact_level": "critical|high|medium|low",
    "affected_areas": ["product", "engineering", "sales", etc.],
    "timeline": "immediate|short-term (<3 months)|long-term (>3 months)",
    "reversibility": "easy|moderate|difficult|irreversible",
    "key_dependencies": ["What depends on this"],
    "risks": ["Potential negative outcomes"],
    "opportunities": ["Potential positive outcomes"],
    "estimated_impact": "Qualitative description of expected impact"
}}
"""


# Decision clustering prompt
DECISION_CLUSTERING_PROMPT = """Group related decisions into strategic themes.

DECISIONS:
{decisions}

Cluster these decisions into coherent strategic themes or initiatives.

Example:
Theme: "Product Strategy Shift"
Decisions:
- Pivoting to enterprise market
- Hiring enterprise sales lead
- Building SSO and RBAC features

Return:
{{
    "themes": [
        {{
            "theme": "Name of strategic theme",
            "description": "What this theme represents",
            "decisions": [0, 2, 5],  // indices of related decisions
            "importance": "critical|high|medium|low",
            "coherence": "How well these decisions support each other"
        }}
    ],
    "standalone_decisions": [1, 3, 4]  // decisions that don't cluster
}}
"""


# Decision extraction from specific discussion
FOCUSED_DECISION_EXTRACTION_PROMPT = """Extract the decision(s) from this specific discussion segment.

DISCUSSION TOPIC: {topic}

SEGMENT:
{segment}

What was decided about {topic}?

If a decision was made, provide:
{{
    "decision_made": true/false,
    "decision": "What was decided",
    "decision_maker": "Who decided",
    "reasoning": "Why this was decided",
    "next_steps": ["What happens next based on this decision"]
}}

If no decision was made, explain what's blocking it or what's needed.
"""


# Board resolution extraction (formal)
BOARD_RESOLUTION_PROMPT = """Extract formal board resolutions and decisions from this board meeting.

BOARD MEETING:
Date: {date}
Directors: {participants}

TRANSCRIPT:
{transcript}

Extract formal resolutions suitable for board minutes. For each:

{{
    "resolutions": [
        {{
            "resolution_number": "Sequential number for this meeting",
            "type": "approval|authorization|policy|appointment|other",
            "title": "Brief title of resolution",
            "full_text": "Formal resolution text",
            "moved_by": "Director who moved",
            "seconded_by": "Director who seconded",
            "vote_result": "unanimous|majority|opposed (if recorded)",
            "dissent": ["Directors who opposed or abstained"],
            "effective_date": "When this takes effect",
            "rationale": "Background and reasoning",
            "action_required": ["Management actions required to implement"]
        }}
    ]
}}

Use formal language appropriate for corporate records.
Include both formal resolutions and significant management decisions approved by the board.
"""


# Strategic vs tactical classification
DECISION_CLASSIFICATION_PROMPT = """Classify these decisions as strategic or tactical.

DECISIONS:
{decisions}

Strategic decisions:
- Long-term direction
- Market positioning
- Major resource allocation
- Fundamental changes
- High risk/reward

Tactical decisions:
- Near-term execution
- Operational details
- Process improvements
- Day-to-day choices
- Lower risk/impact

Return:
{{
    "strategic": [list of decision indices],
    "tactical": [list of decision indices],
    "hybrid": [
        {{
            "index": N,
            "reasoning": "Why this has both strategic and tactical elements"
        }}
    ]
}}
"""


# Decision dependencies extraction
DECISION_DEPENDENCIES_PROMPT = """Analyze dependencies between these decisions.

DECISIONS:
{decisions}

Identify:
1. Which decisions enable or block others
2. Which decisions must happen in sequence
3. Which decisions conflict or compete

Return:
{{
    "dependencies": [
        {{
            "decision": 0,  // index
            "depends_on": [2, 5],  // must happen after these
            "enables": [7, 8],  // allows these to proceed
            "blocks": [],  // prevents these
            "conflicts_with": []  // contradicts these
        }}
    ],
    "critical_path": [2, 0, 7, 8],  // optimal sequence
    "conflicts": [
        {{
            "decision_a": 1,
            "decision_b": 4,
            "conflict": "Description of how these conflict"
        }}
    ]
}}
"""


# Decision timeline extraction
DECISION_TIMELINE_PROMPT = """Create a timeline of when decisions take effect and when follow-up decisions are needed.

DECISIONS:
{decisions}

MEETING DATE: {date}

For each decision, determine:
- When it takes effect
- When it should be reviewed
- Upcoming decision points it creates

Return:
{{
    "timeline": [
        {{
            "date": "YYYY-MM-DD or relative (next week, Q2, etc.)",
            "event": "Decision takes effect | Review decision | Follow-up needed",
            "decision": 0,  // decision index
            "description": "What happens on this date"
        }}
    ],
    "immediate_actions": [decisions that take effect now],
    "pending_decisions": [
        {{
            "trigger": "What needs to happen first",
            "decision_needed": "What decision is pending"
        }}
    ]
}}
"""


# Prompt builder functions

def build_decision_extraction_prompt(
    transcript: str,
    meeting_type: str = "general",
    participants: List[str] = None,
    date: str = None
) -> str:
    """Build decision extraction prompt."""
    participants_str = ", ".join(participants) if participants else "Not specified"

    if not date:
        from datetime import datetime
        date = datetime.now().strftime("%Y-%m-%d")

    return DECISION_EXTRACTION_PROMPT.format(
        transcript=transcript,
        meeting_type=meeting_type,
        participants=participants_str,
        date=date
    )


def build_decision_validation_prompt(
    text: str,
    speaker: str,
    context: str
) -> str:
    """Build decision validation prompt."""
    return DECISION_VALIDATION_PROMPT.format(
        text=text,
        speaker=speaker,
        context=context
    )


def build_impact_analysis_prompt(
    decision: Dict,
    meeting_context: str
) -> str:
    """Build decision impact analysis prompt."""
    import json
    return DECISION_IMPACT_ANALYSIS_PROMPT.format(
        decision=json.dumps(decision, indent=2),
        meeting_context=meeting_context
    )


def build_board_resolution_prompt(
    transcript: str,
    date: str,
    participants: List[str]
) -> str:
    """Build board resolution extraction prompt."""
    return BOARD_RESOLUTION_PROMPT.format(
        transcript=transcript,
        date=date,
        participants=", ".join(participants)
    )


def build_focused_extraction_prompt(
    topic: str,
    segment: str
) -> str:
    """Build focused decision extraction for a specific topic."""
    return FOCUSED_DECISION_EXTRACTION_PROMPT.format(
        topic=topic,
        segment=segment
    )


# Decision quality assessment
DECISION_QUALITY_PROMPT = """Assess the quality of decision-making in this meeting.

DECISIONS:
{decisions}

TRANSCRIPT:
{transcript}

Evaluate:
1. Were alternatives properly considered?
2. Was sufficient context/data discussed?
3. Were risks identified?
4. Was there healthy debate or rubber-stamping?
5. Are decisions clear and actionable?

Return:
{{
    "decision_quality_score": 0.0-1.0,
    "strengths": ["What was done well"],
    "weaknesses": ["What could be improved"],
    "well_reasoned": [decision indices with strong rationale],
    "needs_more_analysis": [decision indices that seem rushed],
    "recommendations": ["How to improve decision-making process"]
}}
"""


# Decision communication template
DECISION_COMMUNICATION_PROMPT = """Create a clear communication of decisions made in this meeting.

DECISIONS:
{decisions}

AUDIENCE: {audience}

Create a concise summary suitable for communicating these decisions to {audience}.

Format:
{{
    "subject": "Subject line for email/message",
    "summary": "One paragraph summarizing all decisions",
    "detailed_decisions": [
        {{
            "decision": "What was decided",
            "why": "Reasoning",
            "impact": "Who/what this affects",
            "timeline": "When this happens",
            "action_required": "What people need to do"
        }}
    ],
    "next_steps": "What happens next",
    "questions": "How to ask questions or provide input"
}}

Tone: {tone}
"""


def build_decision_communication_prompt(
    decisions: List[Dict],
    audience: str = "team",
    tone: str = "professional but conversational"
) -> str:
    """Build decision communication prompt."""
    import json
    return DECISION_COMMUNICATION_PROMPT.format(
        decisions=json.dumps(decisions, indent=2),
        audience=audience,
        tone=tone
    )


# Specialized: Product decisions
PRODUCT_DECISION_PROMPT = """Extract product decisions from this meeting.

Focus on:
- Feature prioritization
- Roadmap changes
- Design decisions
- Technical architecture choices
- User experience decisions

TRANSCRIPT:
{transcript}

For each product decision:
{{
    "decision": "What was decided about the product",
    "rationale": "Why this approach",
    "user_impact": "How this affects users",
    "technical_implications": "Engineering considerations",
    "timeline": "When this ships",
    "alternatives": "Other options considered"
}}
"""


# Specialized: Hiring decisions
HIRING_DECISION_PROMPT = """Extract hiring and personnel decisions.

Focus on:
- Hiring approvals
- Role definitions
- Compensation decisions
- Team structure changes
- Performance decisions

TRANSCRIPT:
{transcript}

For each personnel decision:
{{
    "decision": "What was decided",
    "role": "Role or person affected",
    "rationale": "Why this decision",
    "timeline": "When this happens",
    "budget_impact": "Cost implications if mentioned",
    "approval_status": "approved|pending|conditional"
}}

Keep this confidential and professional.
"""


def get_specialized_decision_prompt(meeting_type: str) -> str:
    """Get specialized decision extraction prompt based on meeting type."""
    if "product" in meeting_type.lower():
        return PRODUCT_DECISION_PROMPT
    elif "hiring" in meeting_type.lower() or "personnel" in meeting_type.lower():
        return HIRING_DECISION_PROMPT
    elif "board" in meeting_type.lower():
        return BOARD_RESOLUTION_PROMPT
    else:
        return DECISION_EXTRACTION_PROMPT
