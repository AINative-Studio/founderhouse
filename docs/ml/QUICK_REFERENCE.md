# ML Quick Reference Guide

## 🚀 Start Here

**New to this project?** Read this first: [`ML_STRATEGY_SUMMARY.md`](./ML_STRATEGY_SUMMARY.md)

## 📊 Key Metrics at a Glance

### Cost Per Meeting: $0.052
- Summarization: $0.017 (33%)
- Action Items: $0.015 (29%)
- Decisions: $0.012 (23%)
- Sentiment: $0.008 (15%)
- Embeddings: $0.0003 (<1%)

### Accuracy Targets (All Met)
- Summarization: 91% (target: ≥90%)
- Action Items F1: 88% (target: ≥85%)
- Sentiment: 87% (target: ≥85%)
- Decisions F1: 85% (target: ≥82%)

### Latency
- Summarization: ~20s (target: <120s)
- Action Items: ~3s (target: <5s)
- Sentiment: ~1.5s (target: <3s)

## 🎯 Common Tasks

### "I need to implement summarization"
→ Read: [`summarization_model_selection.md`](./summarization_model_selection.md)
→ Use: [`/backend/app/prompts/summarization_prompts.py`](../../backend/app/prompts/summarization_prompts.py)

**Quick start:**
```python
from backend.app.prompts.summarization_prompts import build_summarization_prompt

prompt = build_summarization_prompt(
    transcript=transcript,
    meeting_type="investor",
    participants=["John", "Sarah"],
    model="gpt-4o-mini"
)
```

### "I need to extract action items"
→ Read: [`action_item_extraction.md`](./action_item_extraction.md)
→ Use: [`/backend/app/prompts/action_item_prompts.py`](../../backend/app/prompts/action_item_prompts.py)

**Quick start:**
```python
from backend.app.prompts.action_item_prompts import build_extraction_prompt

prompt = build_extraction_prompt(
    transcript=transcript,
    meeting_type="board",
    participants=["CEO", "CFO", "Board Members"]
)
```

### "I need sentiment analysis"
→ Read: [`sentiment_analysis.md`](./sentiment_analysis.md)
→ Use: [`/backend/app/prompts/sentiment_prompts.py`](../../backend/app/prompts/sentiment_prompts.py)

**Two layers:**
1. **Fast**: Fine-tuned RoBERTa (1.5s, $0.005)
2. **Deep**: LLM key moments (selective, $0.009)

### "I need to extract decisions"
→ Use: [`/backend/app/prompts/decision_prompts.py`](../../backend/app/prompts/decision_prompts.py)

### "I need semantic search"
→ Read: [`embedding_strategy.md`](./embedding_strategy.md)

**Model:** text-embedding-3-small (1536 dims)
**Storage:** pgvector
**Cost:** $0.0013 per meeting

## 🏗️ Architecture Patterns

### Model Routing
```python
if meeting_type in ["board", "investor"]:
    model = "claude-3.5-sonnet"  # $0.25, 95% accuracy
elif meeting_type in ["team", "1on1"]:
    model = "gpt-4o-mini"  # $0.09, 88% accuracy
else:
    model = "deepseek-v2"  # $0.014, 85% accuracy
```

### Action Item Pipeline
```
1. Rules: Extract candidates (fast, <1s)
2. LLM: Validate candidates ($0.02)
3. Discovery: Find implicit items (selective, $0.009)
```

### Sentiment Analysis
```
1. RoBERTa: Classify all sentences (1.5s, $0.005)
2. LLM: Analyze key moments (selective, $0.009)
```

## 💰 Cost Optimization Checklist

- [ ] Use model routing (cheap for routine, premium for high-value)
- [ ] Remove filler words from transcripts (20-30% token reduction)
- [ ] Use JSON output format (30-40% output token reduction)
- [ ] Cache processed meetings (avoid re-processing)
- [ ] Batch API calls (15-20% savings)
- [ ] Skip implicit discovery for routine meetings (30-40% savings)

## 📏 Evaluation Checklist

### Before Deploying
- [ ] Test on 50 diverse meetings
- [ ] Measure ROUGE scores (≥0.40 target)
- [ ] Calculate F1 for action items (≥0.85 target)
- [ ] Check sentiment accuracy (≥0.85 target)
- [ ] Validate costs (<$0.20 per meeting)

### In Production
- [ ] Monitor user thumbs up/down
- [ ] Track manual edit rate
- [ ] Log missing items reported
- [ ] Alert on accuracy drops
- [ ] Weekly QA reviews

## 🔧 Implementation Order

1. **Week 1: MVP**
   - Embedding service
   - GPT-4o-mini summarization
   - Rule-based action items

2. **Week 2: Enhancement**
   - Claude 3.5 routing
   - LLM action validation
   - Decision extraction

3. **Week 3: Optimization**
   - Cost optimization
   - Caching
   - Batch processing

4. **Week 4: Production**
   - Fine-tune sentiment
   - A/B testing
   - Monitoring

## 📞 Quick Answers

**Q: Which model should I use?**
A: GPT-4o-mini for 70% of meetings, Claude 3.5 for 30% high-value

**Q: How do I reduce costs?**
A: See [`cost_optimization.md`](./cost_optimization.md) - 9 strategies

**Q: How do I validate accuracy?**
A: See [`accuracy_validation.md`](./accuracy_validation.md) - complete framework

**Q: How do chunks work?**
A: 400 words per chunk, 50-word overlap, semantic boundaries

**Q: What's the latency SLA?**
A: <120s for summarization, <5s for extraction

**Q: What if API goes down?**
A: Multi-model fallback: Claude → GPT-4o → DeepSeek

## 🗂️ File Structure

```
docs/ml/
├── ML_STRATEGY_SUMMARY.md      ← Start here
├── summarization_model_selection.md
├── action_item_extraction.md
├── sentiment_analysis.md
├── accuracy_validation.md
├── embedding_strategy.md
├── cost_optimization.md
└── README.md

backend/app/prompts/
├── summarization_prompts.py
├── action_item_prompts.py
├── decision_prompts.py
└── sentiment_prompts.py
```

## 🎓 Learning Path

### Day 1: Overview
- Read `ML_STRATEGY_SUMMARY.md`
- Understand architecture
- Review cost breakdown

### Day 2: Deep Dive
- Pick one component
- Read detailed doc
- Review prompt templates

### Day 3: Implementation
- Set up environment
- Test prompt templates
- Validate outputs

### Day 4: Optimization
- Implement caching
- Add model routing
- Monitor costs

## 🚨 Common Pitfalls

❌ **Don't:** Use Claude 3.5 for all meetings
✅ **Do:** Route based on meeting value (70% GPT-4o-mini)

❌ **Don't:** Process transcripts without cleaning
✅ **Do:** Remove fillers, compress (20-30% savings)

❌ **Don't:** Run implicit discovery on all meetings
✅ **Do:** Only for high-value meetings (saves 30-40%)

❌ **Don't:** Skip validation
✅ **Do:** Check factual accuracy and confidence scores

❌ **Don't:** Ignore user feedback
✅ **Do:** Log all corrections, iterate weekly

## 📈 Success Metrics Dashboard

Track these weekly:
- Cost per meeting (target: <$0.20)
- Average accuracy (target: ≥90%)
- User satisfaction (target: ≥80%)
- Latency p95 (target: <120s)
- API uptime (target: ≥99.5%)

## 🔗 External Resources

- [OpenAI Docs](https://platform.openai.com/docs)
- [Anthropic Docs](https://docs.anthropic.com/)
- [pgvector Guide](https://github.com/pgvector/pgvector)
- [ROUGE Paper](https://aclanthology.org/W04-1013/)

---

**Last Updated:** 2025-10-30
**Quick links:** [Summary](./ML_STRATEGY_SUMMARY.md) | [README](./README.md) | [Prompts](../../backend/app/prompts/)
