# Insights Cost Optimization Strategy

## Executive Summary

This document defines cost optimization strategies for the Insights & Briefings Engine, targeting <$10/month per founder while maintaining ≥85% accuracy targets. Through intelligent caching, selective LLM usage, batch processing, and algorithmic optimization, we can reduce costs by 25-40% from baseline.

---

## 1. Baseline Cost Analysis

### 1.1 Cost Breakdown (Per Founder/Month)

| Component | Unit Cost | Frequency | Daily Cost | Monthly Cost | % of Total |
|-----------|-----------|-----------|------------|--------------|------------|
| **Anomaly Detection** | | | | | |
| - Modified Z-Score | $0 (compute) | 20 checks/day | $0 | $0 | 0% |
| - Prophet (per model fit) | $0.02 | 10 KPIs × 1x/day | $0.20 | $6.00 | 56% |
| - Isolation Forest | $0.01 | 1x/day | $0.01 | $0.30 | 3% |
| **Trend Analysis** | | | | | |
| - Statistical tests | $0 (compute) | 10 KPIs × 1x/day | $0 | $0 | 0% |
| - Linear regression | $0 (compute) | 10 KPIs × 1x/day | $0 | $0 | 0% |
| **Correlation Analysis** | | | | | |
| - Network computation | $0.05 | 2x/week | $0.014 | $0.42 | 4% |
| **Recommendations** | | | | | |
| - Rule evaluation | $0 (compute) | 2x/day | $0 | $0 | 0% |
| - Pattern matching | $0 (compute) | 2x/day | $0 | $0 | 0% |
| - LLM enrichment (GPT-4) | $0.05/rec | 8 recs/day | $0.40 | $12.00 | 112% |
| **Briefings** | | | | | |
| - Content scoring | $0 (compute) | 2x/day | $0 | $0 | 0% |
| - Formatting | $0 (compute) | 2x/day | $0 | $0 | 0% |
| **Infrastructure** | | | | | |
| - Database queries | $0.01/day | 1x/day | $0.01 | $0.30 | 3% |
| - API calls overhead | $0.01/day | 1x/day | $0.01 | $0.30 | 3% |
| **TOTAL (Baseline)** | | | **$0.67** | **$19.32** | **181%** |

**Issue:** Baseline exceeds $10 target by 93%. Primary cost drivers: Prophet ($6) and LLM enrichment ($12).

---

## 2. Optimization Strategies

### 2.1 Strategy 1: Intelligent Prophet Caching

**Problem:** Prophet refits models daily for all KPIs, even stable ones.

**Solution:** Cache Prophet models, only refit when needed.

```python
class SmartProphetCache:
    def __init__(self, max_age_days=7, refit_threshold=0.15):
        self.cache = {}  # kpi_name -> {model, last_fit, performance}
        self.max_age_days = max_age_days
        self.refit_threshold = refit_threshold

    def should_refit(self, kpi_name, recent_errors):
        """
        Decide if model needs refitting.

        Refit if:
        - Model doesn't exist
        - Model is >7 days old
        - Recent prediction errors >15% mean absolute error
        """
        if kpi_name not in self.cache:
            return True

        cache_entry = self.cache[kpi_name]
        age = (datetime.now() - cache_entry['last_fit']).days

        if age > self.max_age_days:
            return True

        # Check recent prediction accuracy
        if recent_errors:
            mae = np.mean(np.abs(recent_errors))
            if mae > self.refit_threshold:
                return True

        return False

    def get_or_fit(self, kpi_name, data):
        """
        Return cached model or fit new one.
        """
        recent_errors = self.get_recent_prediction_errors(kpi_name)

        if self.should_refit(kpi_name, recent_errors):
            # Refit model
            model = self.fit_prophet_model(data)
            self.cache[kpi_name] = {
                'model': model,
                'last_fit': datetime.now(),
                'prediction_errors': []
            }
            return model, 'fitted'
        else:
            # Use cached
            return self.cache[kpi_name]['model'], 'cached'

# Cost Impact
# - Before: 10 KPIs × $0.02 × 30 days = $6.00/month
# - After: 10 KPIs × $0.02 × 4 refits/month = $0.80/month
# - Savings: $5.20/month (87% reduction)
```

**Expected Savings:** $5.20/month per founder

---

### 2.2 Strategy 2: Selective LLM Enrichment

**Problem:** LLM enriches all recommendations, even low-priority ones.

**Solution:** Only enrich top-ranked recommendations.

```python
def generate_recommendations_optimized(context):
    """
    Generate recommendations with selective LLM enrichment.
    """
    # Stage 1: Rule-based + pattern-based (free)
    base_recommendations = []
    base_recommendations += rule_engine.evaluate(context)
    base_recommendations += pattern_recognizer.detect(context)

    # Stage 2: Rank by priority
    for rec in base_recommendations:
        rec['priority_score'] = calculate_priority_score(rec, context)

    base_recommendations.sort(key=lambda x: x['priority_score'], reverse=True)

    # Stage 3: Selective LLM enrichment
    enriched = []
    llm_budget = 3  # Only enrich top 3 recommendations per briefing

    for i, rec in enumerate(base_recommendations):
        if i < llm_budget and rec['priority_score'] > 70:
            # High-priority: Use GPT-4
            enriched_rec = llm_enrich(rec, model='gpt-4')
        elif rec['priority_score'] > 50:
            # Medium-priority: Use GPT-3.5-turbo (5x cheaper)
            enriched_rec = llm_enrich(rec, model='gpt-3.5-turbo')
        else:
            # Low-priority: Template-based only (free)
            enriched_rec = template_enrich(rec)

        enriched.append(enriched_rec)

    return enriched[:5]  # Top 5 only

# Cost Impact
# - Before: 8 recs/day × $0.05 (GPT-4) × 30 days = $12.00/month
# - After:
#   - 3 recs/day × $0.05 (GPT-4) = $4.50/month
#   - 2 recs/day × $0.01 (GPT-3.5) = $0.60/month
#   - 3 recs/day × $0 (template) = $0/month
# - Total After: $5.10/month
# - Savings: $6.90/month (58% reduction)
```

**Expected Savings:** $6.90/month per founder

---

### 2.3 Strategy 3: Batch Processing

**Problem:** Prophet models refit independently throughout the day.

**Solution:** Batch all model fitting to one off-peak job.

```python
# Before: Fit models on-demand during briefing generation
def generate_briefing_sync(founder_id):
    for kpi in kpis:
        prophet_model = fit_prophet(kpi_data)  # Blocks for 1-2 seconds
        anomaly = detect_with_prophet(kpi, prophet_model)
    # Total: 10 KPIs × 2s = 20 seconds latency

# After: Pre-compute models in batch job (e.g., 3 AM)
@scheduled_job(cron='0 3 * * *')  # Run at 3 AM daily
def batch_fit_prophet_models():
    """
    Fit all Prophet models for all founders in parallel.
    """
    all_founders = db.founders.find()

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = []
        for founder in all_founders:
            for kpi in founder['monitored_kpis']:
                future = executor.submit(fit_and_cache_prophet, founder['id'], kpi)
                futures.append(future)

        # Wait for all to complete
        for future in as_completed(futures):
            result = future.result()

def generate_briefing_async(founder_id):
    for kpi in kpis:
        prophet_model = load_cached_prophet(kpi)  # <1ms from Redis
        anomaly = detect_with_prophet(kpi, prophet_model)
    # Total: 10 KPIs × 1ms = 10ms latency

# Cost Impact: Same compute cost, but improves user experience
# Latency reduction: 20s → 10ms (2000x faster briefing generation)
```

**Cost Impact:** Neutral on cost, but 2000x latency improvement

---

### 2.4 Strategy 4: Tiered Anomaly Detection

**Problem:** Running full ensemble (Prophet + Isolation Forest) for every check is expensive.

**Solution:** Progressive escalation - start with cheap methods, escalate if needed.

```python
def detect_anomaly_tiered(kpi_name, current_value, history):
    """
    Three-tier anomaly detection with progressive escalation.

    Tier 1 (Free): Modified Z-Score (<1ms)
    Tier 2 (Cheap): Prophet from cache (~10ms, $0.002)
    Tier 3 (Expensive): Isolation Forest + root cause (~50ms, $0.05)
    """
    # Tier 1: Fast statistical check
    z_score_result = modified_z_score_detector(current_value, history)

    if z_score_result['z_score'] > 4.0:
        # Extreme outlier, very likely real anomaly
        return {
            'is_anomaly': True,
            'confidence': 0.95,
            'method': 'z_score',
            'tier': 1,
            'cost': 0
        }
    elif abs(z_score_result['z_score']) < 2.0:
        # Clearly not an anomaly
        return {
            'is_anomaly': False,
            'confidence': 0.90,
            'method': 'z_score',
            'tier': 1,
            'cost': 0
        }

    # Tier 2: Ambiguous case, check with Prophet
    prophet_model = load_cached_prophet(kpi_name)
    prophet_result = detect_with_prophet(current_value, prophet_model)

    if prophet_result['confidence'] > 0.85:
        # High confidence from Prophet, no need for multivariate check
        return {
            'is_anomaly': prophet_result['is_anomaly'],
            'confidence': prophet_result['confidence'],
            'method': 'prophet',
            'tier': 2,
            'cost': 0.002
        }

    # Tier 3: Still ambiguous, run full ensemble + root cause
    if prophet_result['is_anomaly']:
        isolation_result = isolation_forest_detector(all_kpis)
        root_cause = detect_root_cause(kpi_name, all_kpis, correlation_network)

        return {
            'is_anomaly': True,
            'confidence': 0.92,
            'method': 'ensemble',
            'root_cause': root_cause,
            'tier': 3,
            'cost': 0.05
        }

    # Not an anomaly
    return {
        'is_anomaly': False,
        'confidence': 0.80,
        'method': 'prophet',
        'tier': 2,
        'cost': 0.002
    }

# Cost Impact
# Assume tier distribution: 70% tier 1, 25% tier 2, 5% tier 3
# - Tier 1: 14 checks/day × $0 = $0
# - Tier 2: 5 checks/day × $0.002 = $0.01/day = $0.30/month
# - Tier 3: 1 check/day × $0.05 = $0.05/day = $1.50/month
# Total: $1.80/month (vs $6.00 baseline)
# Savings: $4.20/month (70% reduction)
```

**Expected Savings:** $4.20/month per founder

---

### 2.5 Strategy 5: LLM Response Caching

**Problem:** Similar recommendations get re-enriched with LLM.

**Solution:** Cache LLM responses for similar inputs.

```python
import hashlib

class LLMResponseCache:
    def __init__(self, redis_client, ttl=86400):
        self.redis = redis_client
        self.ttl = ttl  # 24 hours

    def get_cache_key(self, recommendation, context):
        """
        Generate cache key from recommendation + relevant context.
        """
        # Include only relevant context to increase cache hit rate
        cache_input = {
            'title': recommendation['title'],
            'category': recommendation['category'],
            'kpi_values': {
                k: round(v, 2)  # Round to reduce uniqueness
                for k, v in context['kpis'].items()
                if k in recommendation.get('relevant_kpis', [])
            },
            'company_stage': context.get('stage', 'unknown')
        }

        cache_str = json.dumps(cache_input, sort_keys=True)
        return hashlib.md5(cache_str.encode()).hexdigest()

    def get_cached_response(self, recommendation, context):
        """
        Retrieve cached LLM response if available.
        """
        cache_key = self.get_cache_key(recommendation, context)
        cached = self.redis.get(f"llm_rec:{cache_key}")

        if cached:
            return json.loads(cached)
        return None

    def cache_response(self, recommendation, context, llm_response):
        """
        Cache LLM response.
        """
        cache_key = self.get_cache_key(recommendation, context)
        self.redis.setex(
            f"llm_rec:{cache_key}",
            self.ttl,
            json.dumps(llm_response)
        )

def llm_enrich_with_cache(recommendation, context):
    """
    LLM enrichment with caching.
    """
    # Check cache first
    cached_response = llm_cache.get_cached_response(recommendation, context)

    if cached_response:
        return {
            **recommendation,
            **cached_response,
            'cached': True,
            'cost': 0
        }

    # Cache miss, call LLM
    llm_response = call_gpt4(build_prompt(recommendation, context))

    # Cache for future
    llm_cache.cache_response(recommendation, context, llm_response)

    return {
        **recommendation,
        **llm_response,
        'cached': False,
        'cost': 0.05
    }

# Cost Impact (assuming 30% cache hit rate)
# - Before: 8 recs/day × $0.05 = $0.40/day = $12.00/month
# - After: (8 recs × 0.70 hit rate) × $0.05 = $0.28/day = $8.40/month
# - Savings: $3.60/month (30% reduction)
```

**Expected Savings:** $3.60/month per founder

---

### 2.6 Strategy 6: Use GPT-3.5-Turbo for Simple Enrichments

**Problem:** GPT-4 is expensive ($0.05/call) for simple enrichments.

**Solution:** Use GPT-3.5-Turbo ($0.01/call) for non-critical recommendations.

```python
def select_llm_model(recommendation, context):
    """
    Choose appropriate LLM model based on recommendation complexity.

    GPT-4: Critical financial/strategic recommendations
    GPT-3.5-Turbo: Operational/tactical recommendations
    """
    priority_score = recommendation['priority_score']
    category = recommendation['category']

    # Use GPT-4 for high-stakes recommendations
    if category in ['financial', 'strategic'] and priority_score > 80:
        return 'gpt-4', 0.05

    # Use GPT-3.5-Turbo for everything else
    return 'gpt-3.5-turbo', 0.01

# Cost Impact (assuming 40% GPT-4, 60% GPT-3.5)
# - Before: 8 recs/day × $0.05 = $0.40/day = $12.00/month
# - After:
#   - 3.2 recs/day × $0.05 (GPT-4) = $0.16/day = $4.80/month
#   - 4.8 recs/day × $0.01 (GPT-3.5) = $0.048/day = $1.44/month
# - Total: $6.24/month
# - Savings: $5.76/month (48% reduction)
```

**Expected Savings:** $5.76/month per founder

---

## 3. Combined Optimization Impact

### 3.1 Optimized Cost Breakdown

| Strategy | Baseline Cost | Optimized Cost | Savings | Reduction % |
|----------|---------------|----------------|---------|-------------|
| Prophet caching | $6.00 | $0.80 | $5.20 | 87% |
| Selective LLM enrichment | $12.00 | $5.10 | $6.90 | 58% |
| Tiered anomaly detection | $6.00 | $1.80 | $4.20 | 70% |
| LLM response caching | - | - | $3.60 | 30% of LLM |
| GPT-3.5 for simple tasks | - | - | $5.76 | 48% of LLM |
| Other components | $1.02 | $1.02 | $0 | 0% |
| **TOTAL** | **$19.32** | **$6.92** | **$12.40** | **64%** |

**Note:** Some strategies overlap (e.g., selective enrichment + model selection), so actual combined savings may be slightly less.

### 3.2 Conservative Combined Estimate

Accounting for strategy overlap:

- **Prophet optimization:** $5.20 savings
- **LLM optimization (combined):** $7.50 savings (selective + caching + GPT-3.5)
- **Tiered detection:** $2.00 savings (partial overlap with Prophet caching)

**Total Optimized Cost:** ~$7.50/month per founder
**Savings from Baseline:** ~$11.80/month (61% reduction)
**Under Target:** ✅ $7.50 < $10.00

---

## 4. Implementation Priority

### Phase 1 (Week 1): Quick Wins
1. **Prophet caching** - 1 day implementation, $5.20 savings
2. **Selective LLM enrichment** - 1 day implementation, $6.90 savings
3. **GPT-3.5 for simple tasks** - 2 hours implementation, $5.76 savings

**Phase 1 Total Savings:** $12+ savings
**Phase 1 Cost:** $7-8/month per founder ✅

### Phase 2 (Week 2): Advanced Optimizations
4. **Tiered anomaly detection** - 2 days implementation, $4.20 savings
5. **LLM response caching** - 1 day implementation, $3.60 savings
6. **Batch processing** - 1 day implementation, latency improvement

**Phase 2 Total Savings:** Additional $4-5 savings (accounting for overlap)
**Phase 2 Cost:** $5-6/month per founder ✅

---

## 5. Monitoring & Alerts

### 5.1 Cost Monitoring Dashboard

```python
class CostMonitor:
    def __init__(self):
        self.daily_costs = []

    def track_operation(self, operation_type, cost):
        """
        Track cost of each operation.
        """
        db.cost_tracking.insert({
            'timestamp': datetime.now(),
            'operation_type': operation_type,
            'cost': cost,
            'founder_id': current_founder_id
        })

    def get_daily_cost_by_founder(self, founder_id, date=None):
        """
        Calculate total cost for founder on given day.
        """
        date = date or datetime.now().date()

        costs = db.cost_tracking.aggregate([
            {'$match': {
                'founder_id': founder_id,
                'timestamp': {
                    '$gte': datetime.combine(date, datetime.min.time()),
                    '$lt': datetime.combine(date + timedelta(days=1), datetime.min.time())
                }
            }},
            {'$group': {
                '_id': '$operation_type',
                'total_cost': {'$sum': '$cost'},
                'count': {'$sum': 1}
            }}
        ])

        return list(costs)

    def check_budget_alert(self, founder_id):
        """
        Alert if daily cost exceeds threshold.
        """
        daily_cost = sum(
            c['total_cost']
            for c in self.get_daily_cost_by_founder(founder_id)
        )

        monthly_projection = daily_cost * 30

        if monthly_projection > 12:  # $12/month threshold
            return {
                'alert': True,
                'message': f"Projected monthly cost: ${monthly_projection:.2f}",
                'daily_cost': daily_cost,
                'recommendation': 'Review optimization strategies'
            }

        return {'alert': False}
```

### 5.2 Cost Optimization Metrics

Track these metrics weekly:

- **Cache hit rate:** Target >60% for Prophet, >30% for LLM
- **Tier distribution:** Target 70% tier 1, 25% tier 2, 5% tier 3
- **LLM model mix:** Target 40% GPT-4, 60% GPT-3.5
- **Average cost per founder:** Target <$10/month
- **Cost per insight:** Target <$0.10

---

## 6. Future Optimizations

### 6.1 Phase 3 (Post-MVP)

**6.1.1 Self-Hosted Models**
- Replace Prophet with lighter time-series models (ARIMA, ETS)
- Host smaller LLMs locally (Llama 2, Mistral) for simple enrichments
- **Potential savings:** Additional 30-50% reduction
- **Trade-off:** Increased infrastructure complexity

**6.1.2 Incremental Prophet Updates**
- Instead of refitting full model, update incrementally with new data
- **Potential savings:** 50% reduction in Prophet costs
- **Complexity:** High (requires custom Prophet implementation)

**6.1.3 Shared Models Across Founders**
- Train population-level Prophet models for each KPI
- Personalize with small adjustments per founder
- **Potential savings:** 70% reduction in Prophet costs
- **Trade-off:** Slightly lower personalization

---

## 7. Cost-Benefit Analysis

### 7.1 ROI Calculation

**Founder Value:**
- Time saved: 5-10 hours/week on manual KPI monitoring
- Hourly founder rate: ~$200-500/hour
- Monthly value: $4,000-20,000

**System Cost:**
- Optimized: $7.50/month per founder
- Baseline: $19.32/month per founder

**ROI:**
- Optimized: 533x - 2,667x ROI
- Baseline: 207x - 1,035x ROI

**Conclusion:** Even at baseline cost, system provides massive ROI. Optimization reduces cost further while maintaining quality.

---

## 8. Summary & Recommendations

### 8.1 Recommended Implementation

1. **Start with Phase 1 optimizations** (Prophet caching + selective LLM)
   - Achieves ~$7.50/month cost (under target)
   - Minimal complexity
   - 1-2 days implementation

2. **Monitor for 2 weeks**
   - Track cost per founder
   - Measure cache hit rates
   - Validate accuracy maintained

3. **Add Phase 2 if needed**
   - Only if cost creeps above $10/month
   - Or if latency improvements needed

### 8.2 Key Takeaways

- **Prophet caching is the biggest win:** 87% cost reduction on largest component
- **LLM optimization is critical:** Selective enrichment + model selection saves $7+/month
- **Tiered detection reduces waste:** Avoid expensive methods when simple ones suffice
- **Caching compounds savings:** Both model caching and LLM response caching
- **Target achievable:** $7.50/month per founder (25% under budget)

---

## References

1. OpenAI Pricing: https://openai.com/pricing
2. AWS Lambda Pricing: https://aws.amazon.com/lambda/pricing/
3. Redis Caching Best Practices: https://redis.io/docs/manual/patterns/
