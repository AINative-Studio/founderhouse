"""
Meeting Summarization Prompts

Optimized prompts for different models and meeting types.
"""

from typing import Dict, List, Optional


# Base summarization prompt template
BASE_SUMMARIZATION_PROMPT = """You are an expert executive assistant specializing in meeting summarization for startup founders and executives.

Your task is to analyze the following meeting transcript and create a comprehensive, actionable summary.

MEETING METADATA:
- Meeting Type: {meeting_type}
- Duration: {duration} minutes
- Participants: {participants}
- Date: {date}

TRANSCRIPT:
{transcript}

Please provide a structured summary in the following format:

## Executive Summary
(2-3 sentences capturing the essence of the meeting)

## Key Topics Discussed
(List 3-7 main topics with brief descriptions)

## Decisions Made
(List all decisions with context and who made them)

## Action Items
(Will be extracted separately, but note any obvious ones here)

## Open Questions
(Questions raised but not answered)

## Next Steps
(Concrete next steps or follow-up meetings needed)

## Important Context
(Any critical context, concerns, or risks mentioned)

GUIDELINES:
- Be concise but comprehensive
- Focus on outcomes and decisions, not process
- Use bullet points for clarity
- Highlight urgency when present
- Note any disagreements or concerns
- Preserve important quotes when relevant
"""


# Optimized for Claude 3.5 Sonnet (best quality)
CLAUDE_SUMMARIZATION_PROMPT = """You are a senior Chief of Staff with deep expertise in synthesizing complex business discussions into actionable intelligence.

Analyze this meeting transcript with the analytical rigor of a management consultant and the practical focus of an operator.

MEETING CONTEXT:
Type: {meeting_type}
Duration: {duration} minutes
Attendees: {participants}
Date: {date}

TRANSCRIPT:
{transcript}

Deliver a multi-layered summary optimized for executive decision-making:

# EXECUTIVE BRIEF (30-second read)
[2-3 sentences: What happened, what was decided, what's critical]

# STRATEGIC CONTEXT
[Why this meeting mattered, what problems it addresses, what it unlocks]

# KEY DISCUSSION THREADS

For each major topic:
**Topic:** [Name]
**Summary:** [What was discussed]
**Outcome:** [Decision, consensus, or open question]
**Implications:** [Why this matters, what it affects]

# DECISIONS & COMMITMENTS

For each decision:
- **Decision:** [Clear statement of what was decided]
- **Rationale:** [Why this decision was made]
- **Owner:** [Who is responsible for execution]
- **Impact:** [Expected outcomes or risks]

# ACTION REGISTER
[List will be populated by action extraction pipeline, but flag any critical dependencies here]

# OPEN THREADS & RISKS

**Unresolved Questions:**
[Questions that need answers before progress can continue]

**Concerns Raised:**
[Worries, risks, or objections voiced during discussion]

**Blockers:**
[Anything preventing forward momentum]

# FOLLOW-UP REQUIREMENTS
[What needs to happen next: meetings, analyses, decisions]

# MEETING DYNAMICS
[Notable: agreement level, energy, tension, engagement - be objective and factual]

ANALYSIS STANDARDS:
- Distinguish between decisions and discussions
- Capture implicit commitments (e.g., "I'll look into that" = commitment)
- Note when consensus was not reached
- Flag time-sensitive items
- Preserve nuance while being concise
- Use specific quotes only when they add critical context
- If something is ambiguous in the transcript, note it rather than inferring
"""


# Optimized for GPT-4o-mini (cost-effective)
GPT4O_MINI_SUMMARIZATION_PROMPT = """You are an expert meeting summarizer for startup executives.

Analyze this meeting transcript and create a clear, actionable summary.

Meeting Details:
- Type: {meeting_type}
- Duration: {duration} min
- Participants: {participants}
- Date: {date}

Transcript:
{transcript}

Create a structured summary:

## Summary (2-3 sentences)
[What was discussed, decided, and what happens next]

## Main Topics
[3-7 bullet points of key discussion areas]

## Decisions
[List each decision with who decided and why]

## Open Questions
[Questions raised that need answers]

## Next Steps
[What needs to happen after this meeting]

## Risks/Concerns
[Any issues, blockers, or concerns mentioned]

Guidelines:
- Be concise and specific
- Focus on actionable outcomes
- Note who is responsible for what
- Flag urgent items
- Use bullet points for clarity
"""


# Specialized: Investor Meeting
INVESTOR_MEETING_PROMPT = """You are a Chief of Staff specializing in investor relations.

Summarize this investor meeting with focus on:
1. Investor sentiment and concerns
2. Commitments made to investors
3. Questions that indicate investor priorities
4. Follow-up actions required

Meeting: {meeting_type}
Investors: {participants}
Date: {date}

Transcript:
{transcript}

## Investor Sentiment
[Overall tone and engagement level]

## Key Investor Questions/Concerns
[What investors asked about or expressed concern over]

## Company Updates Shared
[What we told investors - metrics, progress, plans]

## Commitments Made
[What we promised to deliver or share]

## Investor Feedback
[Advice, suggestions, or concerns they raised]

## Follow-Up Actions
[What we need to send or do for investors]

## Strategic Insights
[What we learned about investor priorities or concerns]

Be sensitive to investor concerns and precise about commitments.
"""


# Specialized: Board Meeting
BOARD_MEETING_PROMPT = """You are an experienced corporate secretary and Chief of Staff.

Create a board-grade summary of this meeting suitable for formal record-keeping and strategic review.

Board Meeting Details:
- Date: {date}
- Attendees: {participants}
- Duration: {duration} minutes

Transcript:
{transcript}

## Meeting Summary
[2-3 sentences: purpose, key outcomes, major decisions]

## Strategic Discussions

### [Topic 1]
- Discussion: [Key points raised]
- Board Input: [Director questions, concerns, or guidance]
- Resolution: [Outcome or next steps]

[Repeat for each strategic topic]

## Formal Decisions & Resolutions
[List each decision with sufficient detail for minutes]

## Management Reports
[Summarize each functional update presented]

## Board Guidance
[Strategic direction or recommendations from directors]

## Action Items for Management
[What the board requested or management committed to]

## Executive Session Notes
[If applicable, high-level summary only]

## Next Board Meeting Topics
[Issues to revisit or new items to add to agenda]

Maintain formality appropriate for board records while being actionable.
"""


# Specialized: Team Standup/Sync
TEAM_SYNC_PROMPT = """Summarize this team meeting quickly and clearly.

Meeting: {meeting_type}
Team: {participants}
Duration: {duration} min
Date: {date}

Transcript:
{transcript}

## What's Done
[Completed work mentioned]

## What's In Progress
[Current work and status]

## Blockers
[Issues preventing progress]

## Decisions
[Any decisions made]

## Action Items
[Who needs to do what]

## Questions/Discussion
[Important topics discussed]

Keep it brief - this is a quick sync summary.
"""


# Specialized: Customer/Sales Meeting
CUSTOMER_MEETING_PROMPT = """You are a sales operations expert. Summarize this customer/prospect meeting.

Meeting: {meeting_type}
Customer: {customer_name}
Attendees: {participants}
Date: {date}

Transcript:
{transcript}

## Customer Profile
[Key info learned about customer, their needs, challenges]

## Customer Requirements
[What they're looking for, must-haves, nice-to-haves]

## Our Pitch/Demo
[What we presented and how they responded]

## Customer Concerns/Objections
[Issues they raised, competitive concerns, blockers]

## Buying Signals
[Positive indicators, interest level, timeline]

## Next Steps
[Follow-up actions, timeline, decision process]

## Deal Health
[Overall assessment: strong/medium/weak and why]

## Action Items
[What we need to do to move this forward]

Focus on qualifying information and deal progression.
"""


# Specialized: 1-on-1
ONE_ON_ONE_PROMPT = """Summarize this 1-on-1 meeting between manager and direct report.

Meeting: 1-on-1
Participants: {participants}
Date: {date}

Transcript:
{transcript}

## Topics Discussed
[Main themes of the conversation]

## Direct Report Updates
[What they shared about their work, progress, challenges]

## Feedback Shared
[Any feedback given in either direction]

## Concerns/Issues
[Problems raised that need attention]

## Development/Growth
[Career discussions, skill development, goals]

## Action Items
[Commitments made by either party]

## Follow-Up
[What to revisit in next 1-on-1]

Keep this summary appropriately confidential and focused on outcomes.
"""


# Prompt selector function
def get_summarization_prompt(
    meeting_type: str,
    model: str = "claude-3.5-sonnet"
) -> str:
    """
    Select the appropriate prompt based on meeting type and model.

    Args:
        meeting_type: Type of meeting (board, investor, team, customer, 1on1, strategic, etc.)
        model: LLM model being used

    Returns:
        Appropriate prompt template
    """
    # Normalize meeting type
    meeting_type = meeting_type.lower().strip()

    # Select specialized prompt based on meeting type
    if "investor" in meeting_type or "vc" in meeting_type:
        base_prompt = INVESTOR_MEETING_PROMPT

    elif "board" in meeting_type:
        base_prompt = BOARD_MEETING_PROMPT

    elif "customer" in meeting_type or "sales" in meeting_type or "prospect" in meeting_type:
        base_prompt = CUSTOMER_MEETING_PROMPT

    elif "1on1" in meeting_type or "1-on-1" in meeting_type or "one on one" in meeting_type:
        base_prompt = ONE_ON_ONE_PROMPT

    elif "standup" in meeting_type or "sync" in meeting_type or "daily" in meeting_type:
        base_prompt = TEAM_SYNC_PROMPT

    else:
        # Default: select based on model
        if "claude" in model.lower():
            base_prompt = CLAUDE_SUMMARIZATION_PROMPT
        elif "gpt-4o-mini" in model.lower():
            base_prompt = GPT4O_MINI_SUMMARIZATION_PROMPT
        else:
            base_prompt = BASE_SUMMARIZATION_PROMPT

    return base_prompt


# Prompt builder
def build_summarization_prompt(
    transcript: str,
    meeting_type: str = "general",
    duration: int = 60,
    participants: List[str] = None,
    date: str = None,
    model: str = "claude-3.5-sonnet",
    custom_instructions: Optional[str] = None,
    **kwargs
) -> str:
    """
    Build a complete summarization prompt with all context.

    Args:
        transcript: Full meeting transcript
        meeting_type: Type of meeting
        duration: Meeting duration in minutes
        participants: List of participant names
        date: Meeting date
        model: LLM model to use
        custom_instructions: Additional custom instructions
        **kwargs: Additional metadata (customer_name, etc.)

    Returns:
        Complete formatted prompt
    """
    # Get appropriate prompt template
    template = get_summarization_prompt(meeting_type, model)

    # Format participants
    if participants:
        participants_str = ", ".join(participants)
    else:
        participants_str = "Not specified"

    # Format date
    if not date:
        from datetime import datetime
        date = datetime.now().strftime("%Y-%m-%d")

    # Build prompt with template
    prompt = template.format(
        transcript=transcript,
        meeting_type=meeting_type,
        duration=duration,
        participants=participants_str,
        date=date,
        **kwargs  # For specialized prompts (customer_name, etc.)
    )

    # Add custom instructions if provided
    if custom_instructions:
        prompt += f"\n\nADDITIONAL INSTRUCTIONS:\n{custom_instructions}"

    return prompt


# Quality validation prompt
SUMMARY_VALIDATION_PROMPT = """You are a quality assurance expert reviewing meeting summaries.

Evaluate this meeting summary against the original transcript:

TRANSCRIPT:
{transcript}

GENERATED SUMMARY:
{summary}

Check for:
1. Factual accuracy - are all statements grounded in the transcript?
2. Completeness - were any major topics or decisions missed?
3. Clarity - is the summary clear and well-organized?
4. Actionability - are next steps and action items clear?

Respond in JSON:
{{
    "factual_accuracy": 0.0-1.0,
    "completeness": 0.0-1.0,
    "clarity": 0.0-1.0,
    "actionability": 0.0-1.0,
    "overall_score": 0.0-1.0,
    "issues_found": ["list of any problems"],
    "missing_items": ["important items not included"],
    "hallucinations": ["statements not supported by transcript"],
    "recommendation": "accept|revise|reject"
}}
"""


# Incremental summarization (for long meetings)
INCREMENTAL_SUMMARY_PROMPT = """You are summarizing a segment of a longer meeting.

PREVIOUS CONTEXT:
{previous_summary}

CURRENT SEGMENT ({segment_number} of {total_segments}):
{current_segment}

Update the running summary with new information from this segment.

Maintain the same structure as before and add new:
- Topics discussed
- Decisions made
- Action items
- Open questions

Mark new items with [NEW] tag.
"""


def build_incremental_prompt(
    current_segment: str,
    previous_summary: str,
    segment_number: int,
    total_segments: int
) -> str:
    """Build prompt for incremental summarization of long meetings."""
    return INCREMENTAL_SUMMARY_PROMPT.format(
        previous_summary=previous_summary,
        current_segment=current_segment,
        segment_number=segment_number,
        total_segments=total_segments
    )
