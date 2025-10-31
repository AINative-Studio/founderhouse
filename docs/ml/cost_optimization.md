# ML Cost Optimization Strategy

## Executive Summary

This document outlines comprehensive cost optimization strategies for the Meeting Intelligence ML pipeline. Through intelligent model selection, caching, batching, and monitoring, we achieve a target cost of **<$0.20 per meeting** while maintaining ≥85% accuracy.

## Current Cost Baseline (Without Optimization)

### Per-Meeting Cost Breakdown (Unoptimized)

| Component | Model | Tokens | Cost |
|-----------|-------|--------|------|
| Summarization | Claude 3.5 Sonnet | 10K input + 500 output | $0.038 |
| Action Items (extraction) | GPT-4o-mini | 10K input + 200 output | $0.015 |
| Action Items (validation) | GPT-4o-mini | 20 calls × 200 tokens | $0.010 |
| Decisions | GPT-4o-mini | 10K input + 300 output | $0.020 |
| Sentiment (LLM layer) | GPT-4o-mini | 3 segments × 1K tokens | $0.009 |
| Sentiment (RoBERTa) | Local model | N/A | $0.005 |
| Embeddings | text-embedding-3-small | 13K tokens | $0.0003 |
| **TOTAL** | | | **$0.097** |

**Current baseline: ~$0.10 per meeting** (already below $0.50 target)

---

## Optimization Strategy

### 1. Intelligent Model Routing

**Principle:** Use expensive models only when necessary.

```python
class ModelRouter:
    """
    Route to appropriate model based on meeting characteristics
    """

    def select_summarization_model(self, meeting_metadata: Dict) -> str:
        """
        Choose model based on meeting value and complexity
        """
        # High-value meetings: Use best model
        if meeting_metadata["type"] in ["board", "investor", "strategic"]:
            return "claude-3.5-sonnet"

        # Complex meetings (many participants, long duration): Use good model
        if meeting_metadata["duration"] > 90 or len(meeting_metadata["participants"]) > 10:
            return "claude-3.5-sonnet"

        # Standard meetings: Use cost-effective model
        if meeting_metadata["type"] in ["team", "1on1", "standup"]:
            return "gpt-4o-mini"

        # Budget overflow: Use cheapest acceptable model
        if self.is_over_monthly_budget():
            return "deepseek-v2"

        # Default
        return "gpt-4o-mini"

    def select_action_extraction_model(self, candidate_count: int) -> str:
        """
        Choose validation model based on candidate count
        """
        # Few candidates: Use best model
        if candidate_count <= 5:
            return "gpt-4o-mini"

        # Many candidates: Use cheaper model
        if candidate_count > 20:
            return "deepseek-v2"

        return "gpt-4o-mini"
```

**Expected Savings:** 40-60% on high-volume, low-complexity meetings

---

### 2. Prompt Optimization (Token Reduction)

**Principle:** Use fewer tokens without sacrificing quality.

#### A. Transcript Compression

```python
def compress_transcript(transcript: str) -> str:
    """
    Remove filler words and redundant content

    Savings: 20-30% token reduction
    """
    # Remove filler words
    fillers = ["um", "uh", "like", "you know", "kind of", "sort of"]
    for filler in fillers:
        transcript = re.sub(rf'\b{filler}\b', '', transcript, flags=re.IGNORECASE)

    # Remove speaker attribution redundancy
    # Before: "John: Yeah, so... Mary: Right, and... John: Exactly..."
    # After: "John: Yeah, so... Mary: Right, and... Exactly..."
    transcript = compress_speaker_turns(transcript)

    # Remove cross-talk markers
    transcript = re.sub(r'\[crosstalk\]', '', transcript)
    transcript = re.sub(r'\[inaudible\]', '', transcript)

    # Normalize whitespace
    transcript = re.sub(r'\s+', ' ', transcript).strip()

    return transcript
```

**Expected Savings:** 20-30% token reduction = 20-30% cost reduction

#### B. Concise Prompts

```python
# BEFORE (verbose): 250 tokens
VERBOSE_PROMPT = """
You are an expert executive assistant with many years of experience in
summarizing business meetings for startup founders and executives. Your
task is to carefully analyze the following meeting transcript and create
a comprehensive yet concise summary that captures all the important
information including topics discussed, decisions made, action items,
and any other relevant details that the founder needs to know...
"""

# AFTER (concise): 80 tokens
CONCISE_PROMPT = """
Summarize this meeting transcript. Include:
- Key topics
- Decisions
- Action items
- Open questions
Format as structured bullet points.
"""

# Savings: 170 tokens per call
# At $0.003/1K tokens: ~$0.0005 per meeting
# At 1000 meetings: $0.50/month
```

**Expected Savings:** 10-15% on prompt overhead

#### C. Output Format Optimization

```python
# Request JSON output (structured, concise)
# vs. markdown/prose (verbose, token-heavy)

# BEFORE: Prose output (~500 tokens)
"""
## Executive Summary
This meeting focused primarily on three key areas. First, we discussed
the Q2 product roadmap and decided to prioritize the enterprise features...
[verbose output continues]
"""

# AFTER: JSON output (~300 tokens)
{
    "summary": "Q2 roadmap prioritizing enterprise features",
    "topics": ["Q2 roadmap", "Enterprise features", "Pricing"],
    "decisions": [{"decision": "Prioritize SSO", "owner": "Engineering"}],
    "actions": [{"action": "Draft pricing proposal", "assignee": "Sarah", "due": "Friday"}]
}

# Savings: ~40% on output tokens
```

**Expected Savings:** 30-40% on output token costs

---

### 3. Caching Strategy

**Principle:** Never process the same thing twice.

#### A. Transcript-Level Caching

```python
import hashlib
import json
from typing import Optional

class SummaryCache:
    """
    Cache meeting summaries to avoid re-processing
    """

    def get_cache_key(self, transcript: str, model: str, prompt: str) -> str:
        """
        Generate cache key from transcript + model + prompt
        """
        content = f"{transcript}:{model}:{prompt}"
        return hashlib.sha256(content.encode()).hexdigest()

    async def get_cached_summary(
        self,
        transcript: str,
        model: str,
        prompt: str
    ) -> Optional[Dict]:
        """
        Check if we've already summarized this exact transcript
        """
        cache_key = self.get_cache_key(transcript, model, prompt)

        # Check Redis cache (fast, in-memory)
        cached = await redis.get(f"summary:{cache_key}")
        if cached:
            return json.loads(cached)

        # Check database cache (permanent storage)
        cached_db = await db.query(
            "SELECT summary FROM cache.summaries WHERE cache_key = $1",
            cache_key
        )
        if cached_db:
            return cached_db[0]["summary"]

        return None

    async def cache_summary(
        self,
        transcript: str,
        model: str,
        prompt: str,
        summary: Dict
    ):
        """
        Cache summary for future use
        """
        cache_key = self.get_cache_key(transcript, model, prompt)

        # Redis: 7-day TTL
        await redis.setex(
            f"summary:{cache_key}",
            7 * 24 * 60 * 60,
            json.dumps(summary)
        )

        # Database: permanent
        await db.execute(
            "INSERT INTO cache.summaries (cache_key, summary) VALUES ($1, $2) ON CONFLICT DO NOTHING",
            cache_key,
            json.dumps(summary)
        )
```

**Use Cases:**
- Re-processing after bug fixes
- A/B testing different prompts on same meetings
- User requests "regenerate summary"

**Expected Savings:** 5-10% (for re-processed meetings)

#### B. Duplicate Meeting Detection

```python
async def detect_duplicate_meeting(
    new_transcript: str,
    meeting_metadata: Dict
) -> Optional[str]:
    """
    Detect if this meeting is a duplicate (same recording processed twice)

    Use embedding similarity to find near-exact matches
    """
    # Generate embedding for new meeting
    new_embedding = generate_embedding(new_transcript[:1000])  # First 1K chars

    # Search for very similar meetings (>0.95 similarity)
    similar_meetings = await semantic_search(
        embedding=new_embedding,
        threshold=0.95,
        filters={"date": meeting_metadata["date"]}
    )

    if similar_meetings:
        return similar_meetings[0]["meeting_id"]

    return None

# If duplicate found: reuse existing summary
if duplicate_id := await detect_duplicate_meeting(transcript, metadata):
    return await get_summary(duplicate_id)
```

**Expected Savings:** 100% cost avoidance on duplicates (~2-5% of meetings)

---

### 4. Batch Processing

**Principle:** Process multiple items in one API call.

#### A. Batch Embedding Generation

```python
# INEFFICIENT: Individual API calls
for chunk in chunks:
    embedding = await generate_embedding(chunk)  # 10 API calls
    # Cost: 10 × API overhead

# EFFICIENT: Batch API call
chunk_texts = [chunk.text for chunk in chunks]
embeddings = await generate_embeddings(chunk_texts)  # 1 API call
# Cost: 1 × API overhead

# Savings: ~15% (reduced API overhead)
```

#### B. Batch Action Item Validation

```python
# INEFFICIENT: Validate each candidate separately
for candidate in candidates:
    validated = await validate_action_item(candidate)

# EFFICIENT: Validate in batch
BATCH_VALIDATION_PROMPT = """
Validate each of these candidate action items:

{json array of candidates}

Return JSON array of validation results.
"""

validated_items = await validate_action_items_batch(candidates)

# Savings: 50% (one prompt instead of 20)
```

**Expected Savings:** 15-20% on multi-item processing

---

### 5. Selective Deep Analysis

**Principle:** Apply expensive analysis only when needed.

#### A. Conditional Implicit Action Discovery

```python
def should_run_implicit_discovery(meeting_metadata: Dict) -> bool:
    """
    Only run expensive implicit action discovery on high-value meetings
    """
    # Always run for high-stakes meetings
    if meeting_metadata["type"] in ["board", "investor", "strategic"]:
        return True

    # Run if meeting was long and complex
    if meeting_metadata["duration"] > 90 and len(meeting_metadata["participants"]) > 8:
        return True

    # Skip for routine meetings
    return False

# Savings: Skip $0.009 on 70% of meetings = $0.0063 per meeting average
```

#### B. Tiered Sentiment Analysis

```python
def select_sentiment_analysis_tier(meeting_metadata: Dict) -> str:
    """
    Choose sentiment analysis depth based on meeting importance
    """
    # Full analysis: RoBERTa + LLM key moments + emotional tone
    if meeting_metadata["type"] in ["board", "investor"]:
        return "full"

    # Medium analysis: RoBERTa + basic key moments
    if meeting_metadata["type"] in ["team", "strategic"]:
        return "medium"

    # Basic analysis: RoBERTa only
    return "basic"

# Savings on basic tier: $0.009 (skip LLM) × 40% of meetings = $0.0036
```

**Expected Savings:** 30-40% on analysis components

---

### 6. Model Selection by Time Sensitivity

**Principle:** Batch non-urgent work to use cheaper models.

```python
class ProcessingQueue:
    """
    Queue meetings for batch processing vs. real-time
    """

    async def process_meeting(self, meeting_id: str, priority: str):
        """
        Route to appropriate processing queue
        """
        if priority == "urgent":
            # Real-time processing with fast models
            await process_realtime(meeting_id, model="gpt-4o-mini")

        elif priority == "standard":
            # Process within 1 hour with balanced models
            await queue_for_processing(meeting_id, model="gpt-4o-mini", delay=0)

        elif priority == "batch":
            # Process overnight with cheapest models
            await queue_for_processing(meeting_id, model="deepseek-v2", delay=18*3600)

# Example:
# - Live investor call: urgent
# - Recorded team meeting: standard
# - Historical backfill: batch

# Savings: Use DeepSeek ($0.014) instead of GPT-4o-mini ($0.09) for 20% of meetings
# = $0.076 × 0.20 = $0.015 per meeting average
```

**Expected Savings:** 10-15% through delayed batch processing

---

### 7. Progressive Summarization

**Principle:** Start cheap, go deeper only if needed.

```python
async def progressive_summarization(transcript: str, meeting_metadata: Dict) -> Dict:
    """
    Start with cheap summary, optionally enhance
    """
    # Phase 1: Cheap summary with GPT-4o-mini
    basic_summary = await summarize(transcript, model="gpt-4o-mini")

    # Check if user/system needs deeper analysis
    if not requires_detailed_analysis(meeting_metadata, basic_summary):
        return basic_summary  # Save $0.025 by skipping Claude

    # Phase 2: Enhanced summary with Claude (only if needed)
    detailed_summary = await enhance_summary(basic_summary, transcript, model="claude-3.5-sonnet")

    return detailed_summary

def requires_detailed_analysis(metadata: Dict, basic_summary: Dict) -> bool:
    """
    Decide if detailed analysis is worth the cost
    """
    # High-value meeting types always get detailed
    if metadata["type"] in ["board", "investor"]:
        return True

    # If basic summary flags important decisions/risks
    if basic_summary.get("flags") and "critical" in basic_summary["flags"]:
        return True

    # If user has historically viewed details for this meeting type
    if get_user_preference(metadata["founder_id"], metadata["type"]) == "detailed":
        return True

    return False

# Savings: Only use Claude on ~30% of meetings instead of 100%
# = $0.025 × 0.70 = $0.0175 per meeting average
```

**Expected Savings:** 20-30% on summarization costs

---

### 8. Token Usage Monitoring

**Principle:** Measure and optimize continuously.

```python
class TokenTracker:
    """
    Track token usage and costs in real-time
    """

    async def log_llm_call(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        meeting_id: str,
        component: str
    ):
        """
        Log every LLM call for cost tracking
        """
        cost = self.calculate_cost(model, input_tokens, output_tokens)

        await db.execute("""
            INSERT INTO ops.llm_calls (
                meeting_id,
                component,
                model,
                input_tokens,
                output_tokens,
                cost,
                timestamp
            ) VALUES ($1, $2, $3, $4, $5, $6, NOW())
        """, meeting_id, component, model, input_tokens, output_tokens, cost)

        # Update rolling metrics
        await self.update_rolling_costs()

    async def get_cost_breakdown(self, timeframe: str = "week") -> Dict:
        """
        Analyze costs by component, model, meeting type
        """
        return await db.query("""
            SELECT
                component,
                model,
                COUNT(*) as calls,
                SUM(input_tokens) as total_input_tokens,
                SUM(output_tokens) as total_output_tokens,
                SUM(cost) as total_cost,
                AVG(cost) as avg_cost_per_call
            FROM ops.llm_calls
            WHERE timestamp > NOW() - INTERVAL '1 {timeframe}'
            GROUP BY component, model
            ORDER BY total_cost DESC
        """, timeframe=timeframe)

    async def identify_cost_anomalies(self):
        """
        Alert on unusual cost spikes
        """
        current_week_cost = await self.get_total_cost(days=7)
        previous_week_cost = await self.get_total_cost(days=14, offset=7)

        if current_week_cost > previous_week_cost * 1.5:
            await alert_cost_spike(current_week_cost, previous_week_cost)
```

**Value:** Identify and fix cost leaks quickly

---

### 9. Budget-Based Throttling

**Principle:** Stay within budget automatically.

```python
class BudgetManager:
    """
    Enforce monthly budget limits
    """

    MONTHLY_BUDGET = 200.00  # $200/month target

    async def check_budget_before_processing(self, estimated_cost: float) -> bool:
        """
        Check if we can afford to process this meeting
        """
        current_month_spend = await self.get_month_to_date_spend()

        if current_month_spend + estimated_cost > self.MONTHLY_BUDGET:
            # Budget exceeded
            return False

        return True

    async def get_remaining_budget_percentage(self) -> float:
        """
        Calculate how much budget is left this month
        """
        days_elapsed = datetime.now().day
        days_in_month = calendar.monthrange(datetime.now().year, datetime.now().month)[1]
        time_percentage = days_elapsed / days_in_month

        spend_percentage = await self.get_month_to_date_spend() / self.MONTHLY_BUDGET

        # If spending faster than time passing, we're over budget
        return (time_percentage - spend_percentage) / time_percentage

    async def adjust_processing_strategy(self):
        """
        Automatically switch to cheaper models if over budget
        """
        remaining_budget_pct = await self.get_remaining_budget_percentage()

        if remaining_budget_pct < 0.2:  # Less than 20% budget remaining
            # Switch to cheapest models
            config.default_summarization_model = "deepseek-v2"
            config.skip_implicit_actions = True
            config.sentiment_analysis_tier = "basic"

        elif remaining_budget_pct < 0.5:  # Less than 50% budget remaining
            # Switch to mid-tier models
            config.default_summarization_model = "gpt-4o-mini"
            config.skip_implicit_actions_for_routine = True
```

**Value:** Never exceed budget, automatically optimize

---

## Optimized Cost Projection

### Per-Meeting Cost (After Optimizations)

| Component | Optimization | Original Cost | Optimized Cost | Savings |
|-----------|--------------|---------------|----------------|---------|
| **Summarization** | Model routing (70% GPT-4o-mini, 30% Claude) | $0.038 | $0.017 | 55% |
| **Action Items** | Batch validation, rule pre-filter | $0.025 | $0.015 | 40% |
| **Decisions** | Conditional deep analysis | $0.020 | $0.012 | 40% |
| **Sentiment** | Tiered analysis | $0.014 | $0.008 | 43% |
| **Embeddings** | No change | $0.0003 | $0.0003 | 0% |
| **TOTAL** | | **$0.097** | **$0.052** | **46%** |

### Monthly Cost Projections

| Meetings/Month | Unoptimized | Optimized | Monthly Savings |
|----------------|-------------|-----------|-----------------|
| 100 | $9.70 | $5.20 | $4.50 (46%) |
| 500 | $48.50 | $26.00 | $22.50 (46%) |
| 1,000 | $97.00 | $52.00 | $45.00 (46%) |
| 5,000 | $485.00 | $260.00 | $225.00 (46%) |
| 10,000 | $970.00 | $520.00 | $450.00 (46%) |

**Result: $0.052 per meeting average (well below $0.20 target)**

---

## Cost Monitoring Dashboard

### Key Metrics to Track

```python
COST_METRICS = {
    "total_monthly_spend": {
        "target": 200.00,
        "alert_threshold": 180.00
    },
    "cost_per_meeting": {
        "target": 0.20,
        "alert_threshold": 0.25
    },
    "cost_per_component": {
        "summarization": {"target": 0.05},
        "action_items": {"target": 0.02},
        "sentiment": {"target": 0.01},
        "embeddings": {"target": 0.001}
    },
    "model_distribution": {
        "claude_3.5_sonnet_usage": {"target": "< 30%"},
        "gpt_4o_mini_usage": {"target": "60-80%"},
        "deepseek_usage": {"target": "10-20%"}
    },
    "token_efficiency": {
        "avg_input_tokens_per_meeting": {"target": "<12000"},
        "avg_output_tokens_per_meeting": {"target": "<600"}
    }
}
```

### Automated Reports

```python
async def generate_cost_report(period: str = "week") -> Dict:
    """
    Generate cost report for leadership
    """
    return {
        "period": period,
        "total_spend": await get_total_spend(period),
        "meetings_processed": await get_meeting_count(period),
        "cost_per_meeting": await get_avg_cost_per_meeting(period),
        "by_component": await get_cost_by_component(period),
        "by_model": await get_cost_by_model(period),
        "by_meeting_type": await get_cost_by_meeting_type(period),
        "optimization_savings": await calculate_optimization_savings(period),
        "budget_status": await get_budget_status(),
        "recommendations": await generate_cost_recommendations()
    }
```

---

## ROI Analysis

### Cost vs. Value

**Cost of ML processing: $0.052 per meeting**

**Value delivered:**
- Founder time saved: 15 min/meeting × $200/hr = $50
- Context retention: Priceless (compound value)
- Action item tracking: ~$10/meeting (admin time)
- Decision documentation: ~$20/meeting (prevents miscommunication)

**ROI: ~1,500x** ($60 value / $0.052 cost)

---

## Continuous Optimization Loop

```python
async def weekly_cost_optimization():
    """
    Automated weekly cost optimization routine
    """
    # 1. Analyze costs
    report = await generate_cost_report("week")

    # 2. Identify inefficiencies
    inefficiencies = await identify_cost_inefficiencies(report)

    # 3. Test optimizations
    for inefficiency in inefficiencies:
        if inefficiency["potential_savings"] > 5.00:  # $5+ savings/week
            await create_ab_test(inefficiency["optimization"])

    # 4. Apply winning optimizations
    winning_tests = await get_completed_ab_tests()
    for test in winning_tests:
        if test["cost_reduction"] > 0.10 and test["quality_maintained"]:
            await apply_optimization(test)

    # 5. Report results
    await send_optimization_report()
```

---

## Emergency Cost Reduction Playbook

If costs spike unexpectedly:

1. **Immediate (< 1 hour):**
   - Switch all meetings to GPT-4o-mini
   - Disable implicit action discovery
   - Set sentiment analysis to basic tier
   - Expected savings: 60%

2. **Short-term (< 1 day):**
   - Identify cost anomaly source
   - Fix bug or inefficiency
   - Restore normal processing

3. **Long-term (< 1 week):**
   - Implement additional optimizations
   - Update budget allocation
   - Revise cost targets

---

**Document Version:** 1.0
**Last Updated:** 2025-10-30
**Author:** ML Research Team
**Status:** Ready for Implementation
