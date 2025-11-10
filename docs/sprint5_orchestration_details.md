# Sprint 5: Orchestration Details - Reflection, Voice & Video

**Version:** 1.0
**Part:** 2 of Sprint 5 Architecture
**Focus:** Reflection Loop, Voice Commands, Loom Processing, Discord Integration

---

## Reflection & Feedback Loop System

### Architecture Overview

The Reflection & Feedback Loop system validates agent outputs, enables self-correction, and learns from user interactions to improve future performance.

```
Agent Output
     │
     ▼
┌─────────────────────────────────────────────┐
│         Output Validation Layer              │
│  ┌───────────────────────────────────────┐  │
│  │ Schema Validation                     │  │
│  │ - Type checking                       │  │
│  │ - Required fields                     │  │
│  │ - Format validation                   │  │
│  └───────────────────────────────────────┘  │
│  ┌───────────────────────────────────────┐  │
│  │ Semantic Validation                   │  │
│  │ - Hallucination detection             │  │
│  │ - Factual consistency                 │  │
│  │ - Context relevance                   │  │
│  └───────────────────────────────────────┘  │
│  ┌───────────────────────────────────────┐  │
│  │ Quality Scoring                       │  │
│  │ - Confidence score                    │  │
│  │ - Completeness score                  │  │
│  │ - Usefulness score                    │  │
│  └───────────────────────────────────────┘  │
└─────────────────┬───────────────────────────┘
                  │
                  ├─────> Valid ────> Return to User
                  │
                  ├─────> Invalid ───> Self-Correction
                  │                         │
                  │                         ▼
                  │              ┌──────────────────────┐
                  │              │ Reflection Agent     │
                  │              │ - Re-read context    │
                  │              │ - Identify errors    │
                  │              │ - Generate fix       │
                  │              └──────────┬───────────┘
                  │                         │
                  │ <───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────┐
│         User Feedback Collection             │
│  ┌───────────────────────────────────────┐  │
│  │ Explicit Feedback                     │  │
│  │ - Thumbs up/down                      │  │
│  │ - Corrections                         │  │
│  │ - Quality ratings                     │  │
│  └───────────────────────────────────────┘  │
│  ┌───────────────────────────────────────┐  │
│  │ Implicit Feedback                     │  │
│  │ - Usage patterns                      │  │
│  │ - Ignored recommendations             │  │
│  │ - Time to completion                  │  │
│  └───────────────────────────────────────┘  │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────┐
│           Learning & Optimization            │
│  - Update routing preferences                │
│  - Refine agent prompts                      │
│  - Adjust confidence thresholds              │
│  - Personalize per founder                   │
└──────────────────────────────────────────────┘
```

### Reflection Agent Implementation

```python
from typing import Dict, Any, Optional, Tuple
from langchain.chat_models import ChatAnthropic
from langchain.prompts import ChatPromptTemplate

class ReflectionAgent:
    """
    Validates and corrects agent outputs using reflection

    Implements self-correction loop:
    1. Validate output quality
    2. Identify specific issues
    3. Generate corrected output
    4. Re-validate
    """

    def __init__(self, llm_client):
        self.llm = llm_client

    async def validate_and_correct(
        self,
        agent_type: AgentType,
        original_input: Dict[str, Any],
        agent_output: Dict[str, Any],
        context: Dict[str, Any],
        max_iterations: int = 2
    ) -> Tuple[bool, Dict[str, Any], List[str]]:
        """
        Validate agent output and self-correct if needed

        Args:
            agent_type: Type of agent that produced output
            original_input: Original input to agent
            agent_output: Agent's output to validate
            context: Additional context for validation
            max_iterations: Max self-correction attempts

        Returns:
            (is_valid, corrected_output, issues_found)
        """

        issues_log = []
        current_output = agent_output
        iteration = 0

        while iteration < max_iterations:
            # Validate current output
            is_valid, issues = await self.validate_output(
                agent_type=agent_type,
                output=current_output,
                input_data=original_input,
                context=context
            )

            if is_valid:
                return True, current_output, issues_log

            # Record issues
            issues_log.extend(issues)

            # Attempt self-correction
            corrected = await self.self_correct(
                agent_type=agent_type,
                original_input=original_input,
                flawed_output=current_output,
                issues=issues,
                context=context
            )

            if not corrected:
                # Unable to self-correct
                return False, current_output, issues_log

            current_output = corrected
            iteration += 1

        # Max iterations reached
        return False, current_output, issues_log

    async def validate_output(
        self,
        agent_type: AgentType,
        output: Dict[str, Any],
        input_data: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Tuple[bool, List[str]]:
        """
        Validate agent output quality

        Returns:
            (is_valid, list_of_issues)
        """

        issues = []

        # 1. Schema validation
        schema_issues = self.validate_schema(agent_type, output)
        issues.extend(schema_issues)

        # 2. Hallucination detection
        hallucination_issues = await self.detect_hallucinations(
            output=output,
            input_data=input_data,
            context=context
        )
        issues.extend(hallucination_issues)

        # 3. Factual consistency
        consistency_issues = await self.check_factual_consistency(
            output=output,
            context=context
        )
        issues.extend(consistency_issues)

        # 4. Completeness check
        completeness_issues = self.check_completeness(
            agent_type=agent_type,
            output=output,
            input_data=input_data
        )
        issues.extend(completeness_issues)

        is_valid = len(issues) == 0

        return is_valid, issues

    def validate_schema(
        self,
        agent_type: AgentType,
        output: Dict[str, Any]
    ) -> List[str]:
        """Validate output matches expected schema"""
        issues = []

        # Get expected schema for agent type
        schema = self.get_output_schema(agent_type)

        # Check required fields
        for field in schema.get("required", []):
            if field not in output:
                issues.append(f"Missing required field: {field}")

        # Check field types
        for field, expected_type in schema.get("properties", {}).items():
            if field in output:
                actual_type = type(output[field]).__name__
                if actual_type != expected_type.get("type"):
                    issues.append(
                        f"Field '{field}' has type {actual_type}, "
                        f"expected {expected_type.get('type')}"
                    )

        return issues

    async def detect_hallucinations(
        self,
        output: Dict[str, Any],
        input_data: Dict[str, Any],
        context: Dict[str, Any]
    ) -> List[str]:
        """
        Detect hallucinations in output

        Hallucinations: Facts or data not present in input/context
        """

        issues = []

        # Use LLM to check for hallucinations
        prompt = ChatPromptTemplate.from_template("""
You are a validation agent. Check if the following output contains any hallucinations
(facts or data not present in the input or context).

Input Data:
{input_data}

Context:
{context}

Agent Output:
{output}

Analyze the output carefully. List any statements, facts, or data points that appear
in the output but are NOT supported by the input or context.

Return your analysis as a JSON list of hallucinations:
[
  {{
    "statement": "The hallucinated statement",
    "reason": "Why this is a hallucination"
  }}
]

If no hallucinations found, return: []
""")

        response = await self.llm.agenerate(
            [prompt.format(
                input_data=str(input_data),
                context=str(context),
                output=str(output)
            )]
        )

        # Parse response
        try:
            import json
            hallucinations = json.loads(response.generations[0][0].text)

            for h in hallucinations:
                issues.append(
                    f"Hallucination: {h['statement']} - {h['reason']}"
                )

        except Exception:
            pass

        return issues

    async def check_factual_consistency(
        self,
        output: Dict[str, Any],
        context: Dict[str, Any]
    ) -> List[str]:
        """
        Check if output is factually consistent with known data

        Cross-reference claims with database, KPI metrics, etc.
        """

        issues = []

        # Extract claims from output
        claims = self.extract_claims(output)

        # Verify each claim against context
        for claim in claims:
            is_consistent = await self.verify_claim(claim, context)
            if not is_consistent:
                issues.append(f"Inconsistent claim: {claim}")

        return issues

    def check_completeness(
        self,
        agent_type: AgentType,
        output: Dict[str, Any],
        input_data: Dict[str, Any]
    ) -> List[str]:
        """Check if output fully addresses the input request"""

        issues = []

        # Agent-specific completeness checks
        if agent_type == AgentType.BRIEFING_GENERATOR:
            # Briefing should have all required sections
            required_sections = ["summary", "key_highlights", "action_items"]
            for section in required_sections:
                if section not in output or not output[section]:
                    issues.append(f"Incomplete briefing: missing {section}")

        elif agent_type == AgentType.INSIGHT_GENERATOR:
            # Insight should have recommendation and confidence
            if "recommendation" not in output:
                issues.append("Insight missing recommendation")
            if "confidence" not in output:
                issues.append("Insight missing confidence score")

        # Generic completeness: check if output is substantive
        if not output or len(str(output)) < 50:
            issues.append("Output is too brief or empty")

        return issues

    async def self_correct(
        self,
        agent_type: AgentType,
        original_input: Dict[str, Any],
        flawed_output: Dict[str, Any],
        issues: List[str],
        context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Generate corrected output using reflection

        Prompt LLM to:
        1. Review the flawed output
        2. Understand the issues
        3. Generate corrected output
        """

        reflection_prompt = ChatPromptTemplate.from_template("""
You are a self-correction agent. Your task is to fix the issues in the previous output.

Original Input:
{original_input}

Context:
{context}

Previous Output (FLAWED):
{flawed_output}

Issues Found:
{issues}

Instructions:
1. Carefully review the flawed output
2. Understand each issue listed above
3. Generate a CORRECTED output that addresses all issues
4. Ensure the corrected output is factually accurate and complete
5. Return ONLY the corrected output in the same format as the original

Corrected Output:
""")

        response = await self.llm.agenerate(
            [reflection_prompt.format(
                original_input=str(original_input),
                context=str(context),
                flawed_output=str(flawed_output),
                issues="\n".join(f"- {issue}" for issue in issues)
            )]
        )

        try:
            # Parse corrected output
            corrected_text = response.generations[0][0].text
            # Attempt to parse as JSON if original output was JSON
            if isinstance(flawed_output, dict):
                import json
                corrected = json.loads(corrected_text)
                return corrected
            else:
                return {"corrected": corrected_text}

        except Exception as e:
            # Failed to generate correction
            return None

    def extract_claims(self, output: Dict[str, Any]) -> List[str]:
        """Extract factual claims from output"""
        # Simplified implementation
        claims = []
        for key, value in output.items():
            if isinstance(value, str) and len(value) > 20:
                claims.append(value)
        return claims

    async def verify_claim(
        self,
        claim: str,
        context: Dict[str, Any]
    ) -> bool:
        """Verify claim against context"""
        # Simplified: check if claim contains keywords from context
        context_str = str(context).lower()
        claim_lower = claim.lower()

        # Extract key terms from claim
        import re
        terms = re.findall(r'\b\w+\b', claim_lower)

        # Check if significant terms are in context
        matches = sum(1 for term in terms if term in context_str)
        match_ratio = matches / len(terms) if terms else 0

        return match_ratio > 0.3  # At least 30% match

    def get_output_schema(self, agent_type: AgentType) -> Dict[str, Any]:
        """Get expected output schema for agent type"""

        schemas = {
            AgentType.ZEROBOOKS: {
                "required": ["financial_data", "period"],
                "properties": {
                    "financial_data": {"type": "dict"},
                    "period": {"type": "dict"}
                }
            },
            AgentType.INSIGHT_GENERATOR: {
                "required": ["insights", "confidence"],
                "properties": {
                    "insights": {"type": "list"},
                    "confidence": {"type": "float"}
                }
            },
            AgentType.BRIEFING_GENERATOR: {
                "required": ["summary", "key_highlights", "action_items"],
                "properties": {
                    "summary": {"type": "str"},
                    "key_highlights": {"type": "list"},
                    "action_items": {"type": "list"}
                }
            }
        }

        return schemas.get(agent_type, {})
```

### Feedback Collection System

```python
from enum import Enum
from datetime import datetime
from typing import Optional
from uuid import UUID

class FeedbackType(str, Enum):
    THUMBS_UP = "thumbs_up"
    THUMBS_DOWN = "thumbs_down"
    CORRECTION = "correction"
    RATING = "rating"
    IMPLICIT_USAGE = "implicit_usage"

class UserFeedback(BaseModel):
    """User feedback on agent output"""
    feedback_id: UUID
    request_id: UUID              # Original request
    agent_type: AgentType         # Which agent
    feedback_type: FeedbackType
    rating: Optional[int] = None  # 1-5 rating
    correction: Optional[Dict[str, Any]] = None  # Corrected output
    comment: Optional[str] = None
    founder_id: UUID
    workspace_id: UUID
    created_at: datetime

class FeedbackCollector:
    """Collect and store user feedback on agent outputs"""

    async def record_feedback(
        self,
        request_id: UUID,
        agent_type: AgentType,
        feedback_type: FeedbackType,
        founder_id: UUID,
        workspace_id: UUID,
        rating: Optional[int] = None,
        correction: Optional[Dict] = None,
        comment: Optional[str] = None
    ) -> UUID:
        """Record user feedback"""

        feedback_id = uuid.uuid4()

        await db.execute(
            """
            INSERT INTO orchestration.agent_feedback (
                id,
                request_id,
                agent_type,
                feedback_type,
                rating,
                correction,
                comment,
                founder_id,
                workspace_id,
                created_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, now())
            """,
            feedback_id,
            request_id,
            agent_type.value,
            feedback_type.value,
            rating,
            json.dumps(correction) if correction else None,
            comment,
            founder_id,
            workspace_id
        )

        # Trigger learning pipeline
        await self.trigger_learning_update(feedback_id)

        return feedback_id

    async def record_implicit_feedback(
        self,
        request_id: UUID,
        agent_type: AgentType,
        founder_id: UUID,
        workspace_id: UUID,
        action: str,  # "accepted", "ignored", "modified"
        time_to_action: int  # seconds
    ):
        """Record implicit feedback from usage patterns"""

        # Infer quality from action
        implicit_rating = {
            "accepted": 5,
            "modified": 3,
            "ignored": 1
        }.get(action, 3)

        await self.record_feedback(
            request_id=request_id,
            agent_type=agent_type,
            feedback_type=FeedbackType.IMPLICIT_USAGE,
            founder_id=founder_id,
            workspace_id=workspace_id,
            rating=implicit_rating,
            comment=f"Action: {action}, Time: {time_to_action}s"
        )

class FeedbackLearningEngine:
    """Learn from feedback to improve agent performance"""

    async def process_feedback(self, feedback_id: UUID):
        """Process feedback and update system"""

        # Fetch feedback
        feedback = await self.get_feedback(feedback_id)

        # Update routing preferences
        await self.update_routing_preferences(feedback)

        # Refine agent prompts
        await self.refine_agent_prompts(feedback)

        # Update confidence thresholds
        await self.update_confidence_thresholds(feedback)

    async def update_routing_preferences(self, feedback: UserFeedback):
        """
        Update intent→agent routing based on feedback

        If user consistently rates ZeroBooks agent low for certain queries,
        route similar queries to different agent
        """

        # Get historical feedback for this agent type and founder
        historical = await db.fetch(
            """
            SELECT
                request_id,
                rating,
                feedback_type
            FROM orchestration.agent_feedback
            WHERE agent_type = $1
              AND founder_id = $2
              AND created_at >= now() - interval '30 days'
            ORDER BY created_at DESC
            LIMIT 100
            """,
            feedback.agent_type.value,
            feedback.founder_id
        )

        # Calculate average rating
        ratings = [f['rating'] for f in historical if f['rating']]
        if ratings:
            avg_rating = sum(ratings) / len(ratings)

            # If consistently low rated, adjust routing
            if avg_rating < 3.0:
                # Get original request intent
                request = await self.get_request(feedback.request_id)

                # Store preference to avoid this agent for similar intents
                await self.store_routing_preference(
                    founder_id=feedback.founder_id,
                    intent_pattern=request.get('intent_pattern'),
                    avoid_agent=feedback.agent_type,
                    reason=f"Low avg rating: {avg_rating:.2f}"
                )

    async def refine_agent_prompts(self, feedback: UserFeedback):
        """Refine agent prompts based on corrections"""

        if feedback.feedback_type == FeedbackType.CORRECTION and feedback.correction:
            # Extract patterns from correction
            # Use correction to create few-shot examples
            # Update agent prompt templates

            # Get original output
            request = await self.get_request(feedback.request_id)
            original_output = request.get('output')

            # Store as training example
            await db.execute(
                """
                INSERT INTO orchestration.agent_training_examples (
                    agent_type,
                    input_data,
                    incorrect_output,
                    corrected_output,
                    founder_id,
                    created_at
                ) VALUES ($1, $2, $3, $4, $5, now())
                """,
                feedback.agent_type.value,
                json.dumps(request.get('input')),
                json.dumps(original_output),
                json.dumps(feedback.correction),
                feedback.founder_id
            )
```

---

## Voice Command Integration

### ZeroVoice MCP Architecture

```python
from typing import Dict, Any, Optional
import asyncio

class ZeroVoiceConnector:
    """
    Connector for ZeroVoice MCP - Voice command processing

    Features:
    - Real-time speech-to-text
    - Intent extraction from voice
    - Context-aware routing
    - Voice response synthesis
    """

    def __init__(self, integration_id: str, workspace_id: str):
        self.integration_id = integration_id
        self.workspace_id = workspace_id
        self.mcp_client = get_mcp_client('zerovoice')

    async def process_voice_command(
        self,
        audio_stream: bytes,
        founder_id: UUID,
        context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Process voice command end-to-end

        Args:
            audio_stream: Audio data (WAV, MP3, etc.)
            founder_id: Founder issuing command
            context: Current context (location, recent activity, etc.)

        Returns:
            {
                "transcript": "Show me this week's revenue",
                "intent": "financial_query",
                "entities": {"metric": "revenue", "period": "this_week"},
                "confidence": 0.95,
                "agent_response": {...},
                "voice_response_url": "https://..."
            }
        """

        # 1. Speech-to-Text
        transcript_result = await self.speech_to_text(audio_stream)

        if not transcript_result['success']:
            return {
                "success": False,
                "error": "Failed to transcribe audio"
            }

        transcript = transcript_result['text']
        confidence = transcript_result['confidence']

        # 2. Intent Classification
        intent_result = await self.classify_intent(
            text=transcript,
            founder_id=founder_id,
            context=context
        )

        intent = intent_result['intent']
        entities = intent_result['entities']

        # 3. Route to AgentFlow
        agent_response = await self.route_to_agents(
            intent=intent,
            entities=entities,
            transcript=transcript,
            founder_id=founder_id,
            workspace_id=self.workspace_id
        )

        # 4. Generate voice response
        voice_response = await self.text_to_speech(
            text=agent_response.get('summary', 'Task completed'),
            voice_profile=await self.get_founder_voice_preference(founder_id)
        )

        return {
            "success": True,
            "transcript": transcript,
            "intent": intent,
            "entities": entities,
            "confidence": confidence,
            "agent_response": agent_response,
            "voice_response_url": voice_response['audio_url']
        }

    async def speech_to_text(
        self,
        audio_stream: bytes
    ) -> Dict[str, Any]:
        """
        Convert speech to text using ZeroVoice MCP

        Uses streaming transcription for low latency
        """

        response = await self.mcp_client.call_tool(
            name='zerovoice.transcribe',
            arguments={
                'audio_data': audio_stream,
                'language': 'en-US',
                'model': 'streaming',  # Real-time model
                'enable_punctuation': True,
                'enable_speaker_diarization': False
            }
        )

        return {
            "success": response.get('success', False),
            "text": response.get('transcript', ''),
            "confidence": response.get('confidence', 0.0),
            "words": response.get('words', [])  # Word-level timing
        }

    async def classify_intent(
        self,
        text: str,
        founder_id: UUID,
        context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Classify intent from transcribed text

        Uses hybrid approach:
        1. Vector similarity search for known intents
        2. LLM-based extraction for new/complex intents
        """

        # Get embedding of transcript
        transcript_embedding = await self.get_embedding(text)

        # Search for similar known intents
        known_intent = await self.search_known_intents(
            embedding=transcript_embedding,
            founder_id=founder_id,
            threshold=0.85
        )

        if known_intent:
            return known_intent

        # Fallback: LLM-based intent extraction
        llm_intent = await self.extract_intent_with_llm(
            text=text,
            context=context
        )

        # Store as new intent pattern
        await self.store_intent_pattern(
            text=text,
            embedding=transcript_embedding,
            intent=llm_intent,
            founder_id=founder_id
        )

        return llm_intent

    async def search_known_intents(
        self,
        embedding: List[float],
        founder_id: UUID,
        threshold: float = 0.85
    ) -> Optional[Dict[str, Any]]:
        """Search for similar intent patterns in database"""

        result = await db.fetchrow(
            """
            SELECT
                intent_type,
                entity_schema,
                1 - (embedding <=> $1::vector) AS similarity
            FROM orchestration.intent_patterns
            WHERE founder_id = $2
              AND 1 - (embedding <=> $1::vector) > $3
            ORDER BY embedding <=> $1::vector
            LIMIT 1
            """,
            embedding,
            founder_id,
            threshold
        )

        if result:
            return {
                "intent": result['intent_type'],
                "entities": result['entity_schema'],
                "confidence": result['similarity'],
                "source": "known_pattern"
            }

        return None

    async def extract_intent_with_llm(
        self,
        text: str,
        context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Extract intent using LLM"""

        from langchain.prompts import ChatPromptTemplate

        prompt = ChatPromptTemplate.from_template("""
Extract the intent and entities from the following voice command.

Voice Command: "{text}"

Context: {context}

Available Intents:
- financial_query: Query financial metrics (revenue, expenses, etc.)
- schedule_query: Ask about calendar/meetings
- task_create: Create a new task
- task_query: Ask about existing tasks
- insight_request: Request business insights
- email_draft: Draft an email
- crm_query: Query customer data
- video_summary: Summarize a video

Return JSON:
{{
  "intent": "intent_type",
  "entities": {{
    "key": "value"
  }},
  "confidence": 0.95
}}
""")

        # Use LLM to extract
        # ... LLM call implementation

        return {
            "intent": "financial_query",
            "entities": {"metric": "revenue", "period": "this_week"},
            "confidence": 0.90,
            "source": "llm_extraction"
        }

    async def route_to_agents(
        self,
        intent: str,
        entities: Dict[str, Any],
        transcript: str,
        founder_id: UUID,
        workspace_id: UUID
    ) -> Dict[str, Any]:
        """Route intent to appropriate agent via AgentFlow"""

        # Map intent to agent routing graph
        graph = await self.get_routing_graph_for_intent(intent)

        if not graph:
            # No specific graph, use default handler
            graph = await self.get_default_graph()

        # Prepare initial state
        initial_state = {
            "transcript": transcript,
            "intent": intent,
            "entities": entities,
            "founder_id": str(founder_id),
            "workspace_id": str(workspace_id)
        }

        # Execute graph
        orchestrator = AgentRoutingEngine()
        result = await orchestrator.execute_graph(
            graph=graph,
            founder_id=founder_id,
            request_id=uuid.uuid4()
        )

        return result

    async def text_to_speech(
        self,
        text: str,
        voice_profile: str = "default"
    ) -> Dict[str, Any]:
        """
        Convert text response to speech

        Returns URL to generated audio
        """

        response = await self.mcp_client.call_tool(
            name='zerovoice.synthesize',
            arguments={
                'text': text,
                'voice': voice_profile,
                'speed': 1.0,
                'pitch': 1.0,
                'format': 'mp3'
            }
        )

        return {
            "audio_url": response.get('audio_url'),
            "duration_seconds": response.get('duration'),
            "format": "mp3"
        }
```

---

## Loom Video Summarization Pipeline

### Architecture

```python
class LoomVideoProcessor:
    """
    Process Loom videos for async collaboration

    Pipeline:
    1. Fetch video from Loom MCP
    2. Extract transcript
    3. Chunk transcript semantically
    4. Generate summary
    5. Extract action items
    6. Store insights
    """

    def __init__(self):
        self.loom_connector = get_mcp_client('loom')
        self.summarizer = VideoSummarizer()

    async def process_loom_video(
        self,
        video_url: str,
        workspace_id: UUID,
        founder_id: UUID,
        requested_by: UUID
    ) -> Dict[str, Any]:
        """
        Complete Loom video processing pipeline

        Args:
            video_url: Loom video URL
            workspace_id: Workspace ID
            founder_id: Founder who owns video
            requested_by: User who requested processing

        Returns:
            {
                "video_id": "uuid",
                "title": "Product Demo",
                "duration_seconds": 1800,
                "transcript": {...},
                "summary": "...",
                "key_points": [...],
                "action_items": [...],
                "topics": [...],
                "sentiment": {...}
            }
        """

        # 1. Fetch video metadata
        video_meta = await self.fetch_video_metadata(video_url)

        # 2. Check if already processed
        existing = await self.get_existing_summary(video_meta['video_id'])
        if existing:
            return existing

        # 3. Extract transcript
        transcript = await self.extract_transcript(video_meta['video_id'])

        # 4. Chunk transcript semantically
        chunks = await self.chunk_transcript(transcript)

        # 5. Generate embeddings for chunks
        chunk_embeddings = await self.generate_chunk_embeddings(chunks)

        # 6. Generate summary
        summary = await self.summarizer.generate_summary(
            transcript=transcript,
            video_metadata=video_meta
        )

        # 7. Extract action items
        action_items = await self.extract_action_items(transcript)

        # 8. Extract topics
        topics = await self.extract_topics(transcript)

        # 9. Analyze sentiment
        sentiment = await self.analyze_sentiment(transcript)

        # 10. Store in database
        video_summary_id = await self.store_video_summary(
            workspace_id=workspace_id,
            founder_id=founder_id,
            video_metadata=video_meta,
            transcript=transcript,
            chunks=chunks,
            chunk_embeddings=chunk_embeddings,
            summary=summary,
            action_items=action_items,
            topics=topics,
            sentiment=sentiment
        )

        return {
            "video_id": video_summary_id,
            "title": video_meta['title'],
            "duration_seconds": video_meta['duration'],
            "transcript": transcript,
            "summary": summary,
            "key_points": summary.get('key_points', []),
            "action_items": action_items,
            "topics": topics,
            "sentiment": sentiment
        }

    async def fetch_video_metadata(self, video_url: str) -> Dict[str, Any]:
        """Fetch video metadata from Loom"""

        response = await self.loom_connector.call_tool(
            name='loom.get_video',
            arguments={'video_url': video_url}
        )

        return {
            "video_id": response['id'],
            "title": response['title'],
            "duration": response['duration'],
            "created_at": response['created_at'],
            "thumbnail_url": response['thumbnail_url'],
            "owner_email": response['owner']['email']
        }

    async def extract_transcript(self, video_id: str) -> Dict[str, Any]:
        """Extract transcript from Loom video"""

        response = await self.loom_connector.call_tool(
            name='loom.get_transcript',
            arguments={'video_id': video_id}
        )

        return {
            "text": response['transcript'],
            "words": response.get('words', []),  # Word-level timing
            "duration": response['duration']
        }

    async def chunk_transcript(
        self,
        transcript: Dict[str, Any],
        chunk_size: int = 1000,
        overlap: int = 200
    ) -> List[Dict[str, Any]]:
        """
        Chunk transcript semantically

        Uses sentence boundaries and timing info
        """

        from langchain.text_splitter import RecursiveCharacterTextSplitter

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=overlap,
            separators=["\n\n", "\n", ". ", " ", ""]
        )

        text = transcript['text']
        chunks = splitter.split_text(text)

        # Add timing info to chunks
        chunked_data = []
        for i, chunk in enumerate(chunks):
            chunked_data.append({
                "chunk_index": i,
                "text": chunk,
                "start_time": self.estimate_chunk_start_time(chunk, transcript),
                "end_time": self.estimate_chunk_end_time(chunk, transcript)
            })

        return chunked_data

    async def generate_summary(
        self,
        transcript: Dict[str, Any],
        video_metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate AI summary of video"""

        from langchain.chains.summarize import load_summarize_chain
        from langchain.docstore.document import Document

        # Create document
        doc = Document(
            page_content=transcript['text'],
            metadata={
                "title": video_metadata['title'],
                "duration": video_metadata['duration']
            }
        )

        # Summarize
        chain = load_summarize_chain(
            llm=self.llm,
            chain_type="map_reduce"
        )

        summary = await chain.arun([doc])

        # Extract key points
        key_points = await self.extract_key_points(transcript['text'])

        return {
            "summary": summary,
            "key_points": key_points,
            "length": "detailed" if len(summary) > 500 else "brief"
        }

    async def extract_action_items(
        self,
        transcript: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Extract action items from video transcript"""

        # Use LLM to extract action items
        # Similar to meeting action item extraction

        action_items = [
            {
                "description": "Follow up with customer about pricing",
                "assignee": None,
                "deadline": None,
                "timestamp": 450  # 7:30 in video
            }
        ]

        return action_items
```

---

*[Continuing with Discord Integration, API Specs, and Database Schemas in next section]*

This is a comprehensive architecture covering Reflection Loops, Voice Commands, and Loom Processing. Would you like me to continue with:
1. Discord Bot Architecture
2. API Endpoint Specifications
3. Database Migration Schemas
4. Or create a summary document?
