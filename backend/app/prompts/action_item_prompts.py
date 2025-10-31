"""
Action Item Extraction Prompts

Prompts for extracting action items from meeting transcripts with high precision and recall.
"""

from typing import Dict, List, Optional


# Main action item extraction prompt
ACTION_ITEM_EXTRACTION_PROMPT = """You are an expert at identifying action items from meeting transcripts.

An action item is a specific, actionable task that someone committed to or was assigned to do. It should have:
1. A clear action (what needs to be done)
2. Optionally: who is responsible
3. Optionally: when it's due

IMPORTANT DISTINCTIONS:
- "We should think about X" = NOT an action item (too vague)
- "John will research X by Friday" = ACTION ITEM (specific, assigned, deadline)
- "We discussed Y" = NOT an action item (past tense, informational)
- "Let's get that done" = ACTION ITEM (commitment to action)
- "Maybe we could..." = NOT an action item (hypothetical)
- "I'll handle it" = ACTION ITEM (commitment)

MEETING CONTEXT:
Type: {meeting_type}
Participants: {participants}
Date: {date}

TRANSCRIPT:
{transcript}

Extract ALL genuine action items from this meeting. For each action item, provide:

{{
    "action_items": [
        {{
            "description": "Clear, specific description of what needs to be done",
            "assignee": "Person or team responsible (if mentioned, else null)",
            "due_date": "Deadline if mentioned (tomorrow, Friday, Q2, etc.) else null",
            "priority": "urgent|high|normal|low based on context",
            "confidence": 0.0-1.0 (your confidence this is a genuine action item),
            "source_quote": "Relevant quote from transcript showing this commitment",
            "context": "Brief context explaining why this is needed"
        }}
    ]
}}

GUIDELINES:
- Only include items with confidence ≥ 0.7
- Prefer explicit over implicit commitments
- If assignee is unclear but action is clear, still include it
- Normalize names to match participant list when possible
- Parse relative dates (tomorrow, next week) based on meeting date
- Distinguish between "will do" (commitment) and "should do" (suggestion)
- Be conservative - false negatives are better than false positives
"""


# Validation prompt for candidate action items
ACTION_ITEM_VALIDATION_PROMPT = """You are validating whether a candidate text is a genuine action item.

CONTEXT FROM MEETING:
{context}

CANDIDATE ACTION ITEM:
Speaker: {speaker}
Text: "{text}"
Extracted assignee: {assignee}
Extracted deadline: {deadline}

Is this a genuine action item that someone committed to do?

Consider:
1. Is there a specific, actionable task?
2. Did someone commit to doing it (explicitly or implicitly)?
3. Is it forward-looking (not historical or hypothetical)?
4. Is it concrete enough to be completed and verified?

Respond in JSON:
{{
    "is_action_item": true/false,
    "action": "Clear description of the action (if valid)",
    "assignee": "Who is responsible (if mentioned)",
    "due_date": "Deadline in standardized format (YYYY-MM-DD) or relative (tomorrow, next week) or null",
    "priority": "urgent|high|normal|low",
    "confidence": 0.0-1.0,
    "reasoning": "Brief explanation of why this is/isn't an action item"
}}

If is_action_item is false, you must explain why in reasoning.
If assignee is mentioned as "I" or "me", use the speaker name.
If deadline is implicit (e.g., "before the next meeting"), note that in due_date.
"""


# Discovery prompt for implicit action items
IMPLICIT_ACTION_DISCOVERY_PROMPT = """You are an expert at identifying implicit action items - tasks that need to be done based on meeting discussions, even if not explicitly stated as action items.

Analyze this meeting segment for implied actions:

SEGMENT:
{segment}

PREVIOUS CONTEXT (if any):
{previous_context}

Look for:
1. **Decisions that require follow-up**: "We decided to pivot to enterprise" → someone needs to update strategy docs
2. **Problems without solutions**: "Our conversion rate dropped 20%" → someone should investigate
3. **Questions needing answers**: "What's our CAC?" → someone should calculate it
4. **Commitments implied by role**: CEO says "I need to talk to the board" → CEO has action item
5. **Dependencies mentioned**: "Once we hear back from legal..." → follow up with legal
6. **Information gaps**: "We need the Q2 numbers" → someone should provide them

For each implicit action, provide:
{{
    "action": "Specific action inferred from discussion",
    "assignee": "Who should logically own this (based on role/context) or null",
    "due_date": "If timeline was discussed, else null",
    "priority": "urgent|high|normal|low based on importance in discussion",
    "confidence": 0.0-1.0 (confidence this action is truly needed),
    "reasoning": "Why this action is implied by the discussion",
    "trigger": "What in the transcript implies this action"
}}

Return a JSON array of implied actions.
Only include items with confidence ≥ 0.7.
Be thoughtful - infer actions that are genuinely necessary, not just nice-to-haves.
"""


# Action item enrichment prompt
ACTION_ITEM_ENRICHMENT_PROMPT = """You are enriching an extracted action item with additional context.

ACTION ITEM:
{action_item}

MEETING CONTEXT:
{meeting_context}

PARTICIPANTS:
{participants}

Enrich this action item by:
1. Clarifying vague descriptions
2. Inferring assignee if not specified (based on role/context)
3. Estimating priority based on discussion tone
4. Normalizing the due date
5. Adding helpful context

Return enriched action item:
{{
    "description": "Clarified, specific description",
    "assignee": "Specific person or team",
    "due_date": "Standardized date or null",
    "priority": "urgent|high|normal|low",
    "context": "Why this matters and any relevant background",
    "dependencies": ["Other actions or decisions this depends on"],
    "estimated_effort": "quick (< 1hr) | medium (few hours) | large (days) or null"
}}
"""


# Decision-triggered actions prompt
DECISION_ACTIONS_PROMPT = """You are identifying action items that naturally follow from decisions made in a meeting.

DECISIONS MADE:
{decisions}

MEETING CONTEXT:
{meeting_context}

For each decision, identify the action items that must happen to implement it.

Example:
Decision: "We're going to switch to PostgreSQL"
Actions:
- Evaluate migration tools and effort
- Create migration plan
- Schedule downtime window
- Communicate to customers

For each decision, provide:
{{
    "decision": "The decision made",
    "actions": [
        {{
            "description": "Specific action needed to implement decision",
            "assignee": "Who should own this (if clear from context)",
            "priority": "urgent|high|normal|low",
            "order": 1-N (sequence if order matters)
        }}
    ]
}}

Focus on necessary implementation steps, not optional follow-ups.
"""


# Action item deduplication prompt
DEDUPLICATION_PROMPT = """You are reviewing a list of action items to remove duplicates and consolidate similar items.

ACTION ITEMS:
{action_items}

Identify duplicates or very similar items and consolidate them.

Return:
{{
    "consolidated_items": [
        {{
            "description": "Consolidated description",
            "assignee": "Assignee (use most specific if different)",
            "due_date": "Earliest deadline mentioned",
            "priority": "Highest priority mentioned",
            "original_items": [1, 3, 7],  // indices of items that were merged
            "consolidation_note": "Why these were consolidated"
        }}
    ],
    "unique_items": [2, 4, 5, 6],  // indices of items that are unique
}}

Items are duplicates if they refer to the same action, even if worded differently.
Items are similar if they're related but distinct tasks - keep those separate.
"""


# Action item categorization prompt
CATEGORIZATION_PROMPT = """Categorize these action items into logical groups.

ACTION ITEMS:
{action_items}

Group them into categories like:
- Communication (emails, updates, notifications)
- Analysis (research, investigation, data gathering)
- Creation (building, writing, designing)
- Decision (choices that need to be made)
- Process (operational tasks, administrative)
- Meeting (scheduling, preparing for meetings)

Return:
{{
    "categories": {{
        "Communication": [list of action item indices],
        "Analysis": [...],
        ...
    }},
    "uncategorized": [list of items that don't fit categories]
}}
"""


# Prompt builder functions

def build_extraction_prompt(
    transcript: str,
    meeting_type: str = "general",
    participants: List[str] = None,
    date: str = None
) -> str:
    """Build action item extraction prompt."""
    participants_str = ", ".join(participants) if participants else "Not specified"

    if not date:
        from datetime import datetime
        date = datetime.now().strftime("%Y-%m-%d")

    return ACTION_ITEM_EXTRACTION_PROMPT.format(
        transcript=transcript,
        meeting_type=meeting_type,
        participants=participants_str,
        date=date
    )


def build_validation_prompt(
    text: str,
    context: str,
    speaker: Optional[str] = None,
    assignee: Optional[str] = None,
    deadline: Optional[str] = None
) -> str:
    """Build validation prompt for a candidate action item."""
    return ACTION_ITEM_VALIDATION_PROMPT.format(
        context=context,
        text=text,
        speaker=speaker or "Unknown",
        assignee=assignee or "Not specified",
        deadline=deadline or "Not specified"
    )


def build_discovery_prompt(
    segment: str,
    previous_context: str = ""
) -> str:
    """Build prompt for discovering implicit action items."""
    return IMPLICIT_ACTION_DISCOVERY_PROMPT.format(
        segment=segment,
        previous_context=previous_context or "None"
    )


def build_enrichment_prompt(
    action_item: Dict,
    meeting_context: str,
    participants: List[str]
) -> str:
    """Build prompt for enriching action items with context."""
    import json

    return ACTION_ITEM_ENRICHMENT_PROMPT.format(
        action_item=json.dumps(action_item, indent=2),
        meeting_context=meeting_context,
        participants=", ".join(participants)
    )


def build_decision_actions_prompt(
    decisions: List[Dict],
    meeting_context: str
) -> str:
    """Build prompt for extracting actions from decisions."""
    import json

    return DECISION_ACTIONS_PROMPT.format(
        decisions=json.dumps(decisions, indent=2),
        meeting_context=meeting_context
    )


# Specialized prompts for different meeting types

INVESTOR_ACTION_ITEMS_PROMPT = """Extract action items from this investor meeting.

Pay special attention to:
- Data or metrics requests from investors
- Follow-up meetings or calls to schedule
- Materials to send (decks, reports, intros)
- Questions to answer
- Updates to provide

MEETING:
Investors: {participants}
Date: {date}

TRANSCRIPT:
{transcript}

For each action item specify if it's:
- Internal (for team to complete)
- External (requires investor input/response)
- Time-sensitive (for next board meeting, next update, etc.)

Use standard action item JSON format.
"""


BOARD_ACTION_ITEMS_PROMPT = """Extract action items from this board meeting.

Focus on:
- Management commitments to the board
- Information requests from directors
- Approvals needed before next meeting
- Strategic initiatives to explore
- Reports or analyses to prepare

BOARD MEETING:
Date: {date}
Attendees: {participants}

TRANSCRIPT:
{transcript}

Note which items require board approval vs. management execution.
Distinguish between pre-next-meeting deadlines and general commitments.
"""


CUSTOMER_ACTION_ITEMS_PROMPT = """Extract action items from this customer/sales meeting.

Focus on:
- Follow-up materials to send (proposals, case studies, etc.)
- Questions to answer
- Demo or trial setup
- Internal prep work for next conversation
- Pricing or contract items to prepare

CUSTOMER MEETING:
Customer: {customer_name}
Date: {date}

TRANSCRIPT:
{transcript}

Tag each item as:
- Customer-facing (sends to customer)
- Internal (prep work)
- Blocking (prevents deal progress if not done)
"""


def get_specialized_extraction_prompt(
    meeting_type: str,
    transcript: str,
    **kwargs
) -> str:
    """Get specialized action item extraction prompt based on meeting type."""
    meeting_type = meeting_type.lower()

    if "investor" in meeting_type or "vc" in meeting_type:
        template = INVESTOR_ACTION_ITEMS_PROMPT
    elif "board" in meeting_type:
        template = BOARD_ACTION_ITEMS_PROMPT
    elif "customer" in meeting_type or "sales" in meeting_type:
        template = CUSTOMER_ACTION_ITEMS_PROMPT
    else:
        # Use general prompt
        return build_extraction_prompt(transcript, meeting_type, **kwargs)

    # Format with provided kwargs
    return template.format(transcript=transcript, **kwargs)


# Confidence calibration prompt
CONFIDENCE_CALIBRATION_PROMPT = """You are calibrating confidence scores for extracted action items.

Based on the transcript and action items extracted, adjust confidence scores.

HIGH confidence (0.9-1.0):
- Explicit commitment with assignee and deadline
- Direct quote clearly shows action
- No ambiguity about what needs to be done

MEDIUM confidence (0.7-0.89):
- Clear action but missing assignee or deadline
- Implicit commitment but contextually obvious
- Minor ambiguity in scope

LOW confidence (<0.7):
- Vague or uncertain language
- Could be hypothetical or historical
- Assignee unclear
- Action not specific

ACTION ITEMS:
{action_items}

TRANSCRIPT:
{transcript}

Return calibrated confidence scores:
{{
    "calibrated_items": [
        {{
            "index": 0,
            "original_confidence": 0.85,
            "calibrated_confidence": 0.75,
            "reasoning": "Missing clear assignee makes this less certain"
        }}
    ]
}}
"""


# Action item completeness check
COMPLETENESS_CHECK_PROMPT = """Review this list of action items against the transcript.

Are there any obvious action items missing?

ACTION ITEMS EXTRACTED:
{action_items}

TRANSCRIPT:
{transcript}

Check for:
1. Commitments not captured
2. Follow-ups mentioned
3. "I'll do X" statements missed
4. Dependencies that imply actions

Return:
{{
    "missing_items": [
        {{
            "description": "Missed action",
            "source_quote": "Where it appears in transcript",
            "severity": "critical|important|minor"
        }}
    ],
    "completeness_score": 0.0-1.0,
    "notes": "Overall assessment of extraction quality"
}}
"""


def build_completeness_check_prompt(
    action_items: List[Dict],
    transcript: str
) -> str:
    """Build prompt to check if action item extraction is complete."""
    import json

    return COMPLETENESS_CHECK_PROMPT.format(
        action_items=json.dumps(action_items, indent=2),
        transcript=transcript
    )
