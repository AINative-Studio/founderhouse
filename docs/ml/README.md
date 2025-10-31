# ML Documentation for Meeting Intelligence

## Overview

This directory contains comprehensive ML/AI strategy documentation for Sprint 3: Meeting & Communication Intelligence. All documents are production-ready and provide detailed specifications for implementing the meeting intelligence pipeline.

## Quick Start

**Start here:** Read [`ML_STRATEGY_SUMMARY.md`](./ML_STRATEGY_SUMMARY.md) for the complete architectural overview.

## Document Index

### 📋 Executive Summary
- **[ML_STRATEGY_SUMMARY.md](./ML_STRATEGY_SUMMARY.md)** - Complete ML architecture overview
  - System architecture
  - Component breakdown
  - Cost analysis ($0.052/meeting)
  - Implementation roadmap
  - Success criteria

### 🤖 Model Selection
- **[summarization_model_selection.md](./summarization_model_selection.md)** - Meeting summarization models
  - Comparison of 7 models (Claude, GPT-4o, GPT-4o-mini, DeepSeek, BART, T5, Llama)
  - Benchmark results on 50 test meetings
  - Hybrid multi-model routing strategy
  - Cost-quality tradeoffs
  - Recommendation: Claude 3.5 Sonnet (30%) + GPT-4o-mini (70%)

### 🎯 Extraction Pipelines
- **[action_item_extraction.md](./action_item_extraction.md)** - Action item extraction pipeline
  - Three-stage hybrid approach (rules + LLM + discovery)
  - Extraction patterns and regex rules
  - Validation strategies
  - Assignee and deadline extraction
  - Target: 88% F1 score

### 😊 Sentiment Analysis
- **[sentiment_analysis.md](./sentiment_analysis.md)** - Sentiment classification
  - Dual-layer architecture (RoBERTa + LLM)
  - Per-speaker sentiment analysis
  - Key moment detection (tension, agreement, confusion)
  - Sentiment trajectory over time
  - Target: 87% accuracy

### ✅ Quality Assurance
- **[accuracy_validation.md](./accuracy_validation.md)** - Validation strategy
  - Ground truth dataset creation (50 meetings)
  - Evaluation metrics (ROUGE, F1, accuracy)
  - Inter-annotator agreement protocols
  - Continuous monitoring in production
  - A/B testing framework

### 🔍 Vector Embeddings
- **[embedding_strategy.md](./embedding_strategy.md)** - Semantic search
  - Chunking strategy (semantic boundaries)
  - Model: text-embedding-3-small (1536 dims)
  - pgvector storage and retrieval
  - Use cases: search, Q&A, deduplication
  - Cost: $0.0013/meeting

### 💰 Cost Optimization
- **[cost_optimization.md](./cost_optimization.md)** - Cost management
  - 9 optimization strategies
  - Intelligent model routing
  - Token reduction techniques
  - Caching and batch processing
  - Budget monitoring and alerts
  - Result: 46% cost reduction

## Prompt Templates

Located in `/backend/app/prompts/`:

1. **[summarization_prompts.py](../../backend/app/prompts/summarization_prompts.py)**
   - 9 specialized prompts (board, investor, customer, team, 1-on-1, standup)
   - Model-specific optimization (Claude vs GPT-4o-mini)
   - Incremental summarization for long meetings

2. **[action_item_prompts.py](../../backend/app/prompts/action_item_prompts.py)**
   - Extraction, validation, enrichment prompts
   - Implicit action discovery
   - Deduplication and categorization

3. **[decision_prompts.py](../../backend/app/prompts/decision_prompts.py)**
   - Decision extraction and validation
   - Impact analysis
   - Board resolution formatting
   - Timeline and dependency extraction

4. **[sentiment_prompts.py](../../backend/app/prompts/sentiment_prompts.py)**
   - Meeting sentiment analysis
   - Per-speaker sentiment
   - Key moment detection
   - Stakeholder sentiment (investor/board)

## Key Metrics

### Performance Targets

| Component | Metric | Target | Expected |
|-----------|--------|--------|----------|
| **Summarization** | Factual Accuracy | ≥90% | 91% |
| | ROUGE-L F1 | ≥0.40 | 0.42 |
| **Action Items** | F1 Score | ≥85% | 88% |
| | Assignee Accuracy | ≥75% | 81% |
| **Sentiment** | Classification Accuracy | ≥85% | 87% |
| | Key Moment F1 | ≥70% | 75% |
| **Decisions** | Detection F1 | ≥82% | 85% |
| **Cost** | Per Meeting | <$0.20 | $0.052 |
| **Latency** | Summarization | <120s | ~20s |

### Cost Breakdown (Optimized)

```
Summarization:  $0.017 (33%)
Action Items:   $0.015 (29%)
Decisions:      $0.012 (23%)
Sentiment:      $0.008 (15%)
Embeddings:     $0.0003 (<1%)
─────────────────────────────
Total:          $0.052/meeting
```

## Implementation Phases

### Phase 1: MVP (Weeks 1-2)
- GPT-4o-mini summarization
- Rule-based action items
- Basic sentiment (RoBERTa)
- Embedding pipeline

**Goal:** 85% accuracy, <30s latency

### Phase 2: Enhancement (Week 3)
- Add Claude 3.5 for high-value meetings
- LLM validation for action items
- Decision extraction
- Cost optimization

**Goal:** 90% accuracy for priority meetings

### Phase 3: Optimization (Week 4)
- DeepSeek fallback
- Caching and batching
- Fine-tuned sentiment model
- Production monitoring

**Goal:** <$0.15 average cost

### Phase 4: Production (Ongoing)
- A/B testing
- User feedback integration
- Continuous optimization
- Scale to 100+ concurrent meetings

**Goal:** 93% accuracy, production-ready

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│                   Meeting Transcript                     │
│                    (10,000 words)                        │
└────────────────────┬────────────────────────────────────┘
                     ↓
         ┌───────────────────────┐
         │   Pre-processing       │
         │   • Filler removal     │
         │   • Compression (20%)  │
         └───────────┬───────────┘
                     ↓
         ┌───────────────────────┐
         │  Semantic Chunking     │
         │  • 400 word chunks     │
         │  • 50 word overlap     │
         └───────────┬───────────┘
                     ↓
         ┌───────────────────────┐
         │   Embedding Layer      │
         │   text-embedding-3     │
         │   → pgvector storage   │
         └───────────┬───────────┘
                     ↓
    ┌────────────────┴────────────────┐
    │                                  │
    ↓                                  ↓
┌───────────┐                  ┌─────────────┐
│ Summary   │                  │ Extraction  │
│ • Claude  │                  │ • Actions   │
│ • GPT-4o  │                  │ • Decisions │
│ 91% acc   │                  │ • Sentiment │
└───────────┘                  └─────────────┘
    │                                  │
    └────────────────┬─────────────────┘
                     ↓
         ┌───────────────────────┐
         │   Quality Validation   │
         │   • Factual check      │
         │   • Confidence score   │
         └───────────┬───────────┘
                     ↓
         ┌───────────────────────┐
         │   Database Storage     │
         │   • Supabase           │
         │   • Redis cache        │
         └───────────────────────┘
```

## Technology Stack

### ML Models
- **OpenAI:** GPT-4o-mini, text-embedding-3-small
- **Anthropic:** Claude 3.5 Sonnet
- **DeepSeek:** DeepSeek-V2 (fallback)
- **HuggingFace:** RoBERTa (sentiment)

### Infrastructure
- **Vector DB:** pgvector (Supabase)
- **Cache:** Redis
- **Database:** PostgreSQL (Supabase)
- **Hosting:** Railway

### Libraries
- **LLM:** openai, anthropic
- **Embeddings:** sentence-transformers
- **NLP:** spaCy, transformers
- **Evaluation:** rouge-score, scikit-learn

## Best Practices

### Prompt Engineering
1. **Be specific:** Clear instructions beat verbose explanations
2. **Use examples:** Few-shot learning improves accuracy
3. **Request structure:** JSON output is more token-efficient
4. **Validate outputs:** Always check confidence scores

### Cost Management
1. **Route intelligently:** Use expensive models only when needed
2. **Cache aggressively:** Never process the same thing twice
3. **Batch operations:** Reduce API overhead
4. **Monitor continuously:** Track costs in real-time

### Quality Assurance
1. **Ground truth first:** Build test datasets before deployment
2. **Multi-metric evaluation:** No single metric tells the full story
3. **Human-in-the-loop:** Automated metrics + human review
4. **Continuous monitoring:** Production accuracy matters most

## Resources

### External Documentation
- [OpenAI API Docs](https://platform.openai.com/docs)
- [Anthropic API Docs](https://docs.anthropic.com/)
- [pgvector Guide](https://github.com/pgvector/pgvector)
- [ROUGE Score Paper](https://aclanthology.org/W04-1013/)

### Internal References
- [Architecture Overview](../architecture.md)
- [Database Schema](../../datamodel.md)
- [Sprint Plan](../../sprint-plan.md)
- [PRD](../../prd.md)

## Contributing

When updating ML documentation:

1. **Maintain consistency:** Follow existing document structure
2. **Include benchmarks:** Always provide performance data
3. **Update costs:** Keep cost estimates current
4. **Document changes:** Note what changed and why
5. **Version control:** Increment version numbers

## Questions?

For questions about ML strategy:
- Technical implementation: Engineering team
- Cost projections: Finance team
- Quality metrics: QA team
- Product requirements: Product team

---

**Last Updated:** 2025-10-30
**Version:** 1.0
**Status:** ✅ Production Ready

**Total Documentation:** 7 strategy docs + 4 prompt files = 11 deliverables
**Total Pages:** ~150 pages of comprehensive ML documentation
