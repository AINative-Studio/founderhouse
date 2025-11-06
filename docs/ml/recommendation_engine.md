# Recommendation Engine for AI Chief of Staff

## Executive Summary

This document defines the ML pipeline for generating actionable recommendations from business insights, communication sentiment, meeting outcomes, and task completion data. The system combines rule-based triggers, pattern recognition, and LLM-based generation to provide context-aware strategic guidance.

**Goal:** Generate 3-5 high-quality, actionable recommendations per day with ≥80% founder acceptance rate.

---

## 1. Recommendation Taxonomy

### 1.1 Recommendation Types

| Type | Purpose | Urgency | Data Sources | Example |
|------|---------|---------|--------------|---------|
| **Operational** | Tactical day-to-day actions | High | KPIs, tasks, meetings | "Focus on customer retention - churn up 15%" |
| **Strategic** | Long-term planning decisions | Medium | Trends, patterns, investor comms | "Consider fundraising - runway < 12 months" |
| **Tactical** | Immediate action items | Urgent | Anomalies, escalations | "Schedule 1:1 with sales lead - conversion down 12%" |
| **Financial** | Budget and resource allocation | Medium | Burn rate, CAC, LTV | "Reduce marketing spend - CAC > 3x LTV" |
| **People** | Team and stakeholder management | Medium | Sentiment, meeting outcomes | "Check in with engineering - 3 missed deadlines this week" |
| **Product** | Feature and roadmap decisions | Low | User engagement, feedback | "Prioritize mobile app - 60% requests from mobile users" |

---

## 2. Recommendation Generation Pipeline

### 2.1 System Architecture

```
Data Sources → Signal Detection → Rule Matching → LLM Enrichment → Ranking → Delivery
     ↓              ↓                  ↓               ↓             ↓          ↓
  Granola      Anomalies         Trigger Rules    GPT-4 Context  Priority   Briefing
  Meetings     Trends            Domain Logic     Explanation    Scoring    Slack/Email
  Tasks        Correlations      Expert System    Action Items   Filtering
  Sentiment    Patterns
```

### 2.2 Multi-Stage Pipeline

```python
class RecommendationEngine:
    def __init__(self, llm_client):
        self.llm_client = llm_client
        self.rule_engine = RuleBasedEngine()
        self.pattern_recognizer = PatternRecognizer()
        self.ranker = RecommendationRanker()

    def generate_recommendations(self, founder_context):
        """
        Main pipeline for generating recommendations.

        Args:
            founder_context: Dict with KPIs, meetings, tasks, sentiment, etc.

        Returns:
            List of ranked recommendations
        """
        # Stage 1: Detect signals from data
        signals = self.detect_signals(founder_context)

        # Stage 2: Apply rule-based triggers
        rule_based_recs = self.rule_engine.evaluate(signals)

        # Stage 3: Pattern-based recommendations
        pattern_recs = self.pattern_recognizer.detect(founder_context)

        # Stage 4: LLM-based enrichment
        enriched_recs = self.enrich_with_llm(rule_based_recs + pattern_recs, founder_context)

        # Stage 5: Rank and filter
        final_recs = self.ranker.rank_recommendations(enriched_recs, founder_context)

        return final_recs[:5]  # Top 5 recommendations
```

---

## 3. Rule-Based Recommendation Triggers

### 3.1 Business-Critical Rules

```python
RECOMMENDATION_RULES = {
    'runway_critical': {
        'condition': lambda ctx: ctx['kpis']['runway_months'] < 6,
        'priority': 'critical',
        'category': 'financial',
        'template': {
            'title': 'Initiate Fundraising Process',
            'description': 'Runway is below 6 months ({runway_months:.1f} months remaining). '
                          'Historical data shows fundraising takes 3-6 months.',
            'action_items': [
                'Update investor deck with latest metrics',
                'Schedule conversations with existing investors',
                'Prepare financial projections for next 18 months',
                'Identify 20-30 target investors'
            ],
            'impact': 'critical',
            'effort': 'high',
            'timeline': 'Start immediately'
        }
    },

    'ltv_cac_unhealthy': {
        'condition': lambda ctx: ctx['kpis']['ltv'] / ctx['kpis']['cac'] < 3,
        'priority': 'high',
        'category': 'financial',
        'template': {
            'title': 'Optimize Unit Economics',
            'description': 'LTV:CAC ratio is {ltv_cac_ratio:.2f}, below healthy threshold of 3:1. '
                          'Current CAC: ${cac:,.0f}, LTV: ${ltv:,.0f}',
            'action_items': [
                'Audit marketing channel ROI - pause underperforming channels',
                'Analyze customer retention - identify churn reduction opportunities',
                'Consider pricing adjustments to improve LTV',
                'Review sales process efficiency'
            ],
            'impact': 'high',
            'effort': 'medium',
            'timeline': 'Next 2 weeks'
        }
    },

    'churn_spike': {
        'condition': lambda ctx: (ctx['kpis']['churn_rate'] > 0.10 and
                                 ctx['anomalies'].get('churn_rate', {}).get('magnitude', 0) > 0.25),
        'priority': 'critical',
        'category': 'operational',
        'template': {
            'title': 'Address Customer Churn Urgently',
            'description': 'Churn rate spiked to {churn_rate:.1f}% (up {churn_change:.1f}% from last month). '
                          'Immediate action required to prevent revenue impact.',
            'action_items': [
                'Contact recently churned customers for exit interviews',
                'Review recent product changes or service issues',
                'Check support ticket trends for recurring problems',
                'Schedule emergency team meeting to address root causes'
            ],
            'impact': 'critical',
            'effort': 'high',
            'timeline': 'Today'
        }
    },

    'conversion_declining': {
        'condition': lambda ctx: ctx['trends'].get('conversion_rate', {}).get('direction') == 'down' and
                                ctx['trends'].get('conversion_rate', {}).get('magnitude', 0) < -0.15,
        'priority': 'high',
        'category': 'operational',
        'template': {
            'title': 'Investigate Conversion Rate Drop',
            'description': 'Conversion rate down {conversion_change:.1f}% to {conversion_rate:.1f}%. '
                          'This impacts pipeline and revenue projections.',
            'action_items': [
                'Meet with sales lead to review pipeline quality',
                'Analyze recent lead sources - identify low-quality channels',
                'Review sales process changes or team capacity issues',
                'Consider sales training or enablement needs'
            ],
            'impact': 'high',
            'effort': 'medium',
            'timeline': 'This week'
        }
    },

    'negative_sentiment_trend': {
        'condition': lambda ctx: (ctx['sentiment']['team_sentiment_avg'] < -0.3 and
                                 ctx['sentiment']['trend'] == 'declining'),
        'priority': 'high',
        'category': 'people',
        'template': {
            'title': 'Address Team Morale',
            'description': 'Team sentiment has been declining (average score: {sentiment_score:.2f}). '
                          'Multiple negative indicators in recent communications.',
            'action_items': [
                'Schedule 1:1s with team leads to understand concerns',
                'Review recent decisions or changes that may have impacted morale',
                'Consider team meeting or all-hands to address issues',
                'Identify specific individuals who may need support'
            ],
            'impact': 'high',
            'effort': 'medium',
            'timeline': 'Next few days'
        }
    },

    'burn_rate_increasing': {
        'condition': lambda ctx: (ctx['trends'].get('burn_rate', {}).get('direction') == 'up' and
                                 ctx['kpis']['burn_rate'] / ctx['kpis']['revenue'] > 2),
        'priority': 'high',
        'category': 'financial',
        'template': {
            'title': 'Control Burn Rate',
            'description': 'Burn rate increased to ${burn_rate:,.0f}/month (burn multiple: {burn_multiple:.1f}x revenue). '
                          'At current rate, runway is {runway_months:.1f} months.',
            'action_items': [
                'Review all discretionary spending',
                'Identify cost reduction opportunities',
                'Consider hiring freeze until revenue improves',
                'Prepare budget scenarios for next quarter'
            ],
            'impact': 'high',
            'effort': 'medium',
            'timeline': 'This week'
        }
    },

    'missed_deadlines': {
        'condition': lambda ctx: ctx['tasks']['overdue_count'] >= 5 or
                                ctx['tasks']['overdue_pct'] > 0.30,
        'priority': 'medium',
        'category': 'operational',
        'template': {
            'title': 'Address Project Delays',
            'description': '{overdue_count} tasks overdue ({overdue_pct:.0%} of active tasks). '
                          'Consistent delays may indicate capacity or prioritization issues.',
            'action_items': [
                'Review project scope and timelines with team',
                'Identify blockers or resource constraints',
                'Reprioritize tasks - consider descoping low-value work',
                'Assess if additional resources needed'
            ],
            'impact': 'medium',
            'effort': 'medium',
            'timeline': 'This week'
        }
    },

    'successful_launch': {
        'condition': lambda ctx: (ctx['patterns'].get('product_launch_success') and
                                 ctx['anomalies'].get('signups', {}).get('magnitude', 0) > 0.30),
        'priority': 'low',
        'category': 'strategic',
        'template': {
            'title': 'Capitalize on Launch Momentum',
            'description': 'Strong positive signals after recent launch: '
                          'Signups up {signup_change:.1f}%, engagement up {engagement_change:.1f}%.',
            'action_items': [
                'Increase marketing spend while CAC is favorable',
                'Capture user testimonials and case studies',
                'Prepare press release or blog post',
                'Double down on successful acquisition channels'
            ],
            'impact': 'medium',
            'effort': 'low',
            'timeline': 'Next week'
        }
    }
}
```

### 3.2 Rule Evaluation Engine

```python
class RuleBasedEngine:
    def evaluate(self, context):
        """
        Evaluate all rules against current context.

        Returns:
            List of triggered recommendations
        """
        recommendations = []

        for rule_id, rule_config in RECOMMENDATION_RULES.items():
            try:
                if rule_config['condition'](context):
                    # Rule triggered, generate recommendation
                    rec = self.generate_from_rule(rule_id, rule_config, context)
                    recommendations.append(rec)
            except (KeyError, TypeError, ZeroDivisionError):
                # Handle missing data gracefully
                continue

        return recommendations

    def generate_from_rule(self, rule_id, rule_config, context):
        """
        Generate recommendation from triggered rule.
        """
        template = rule_config['template']

        # Fill in template with context values
        description = template['description'].format(**context.get('kpis', {}),
                                                     **context.get('trends', {}),
                                                     **context.get('sentiment', {}),
                                                     **context.get('tasks', {}))

        return {
            'id': f'rule_{rule_id}_{datetime.now().timestamp()}',
            'source': 'rule_based',
            'rule_id': rule_id,
            'category': rule_config['category'],
            'priority': rule_config['priority'],
            'title': template['title'],
            'description': description,
            'action_items': template['action_items'],
            'impact': template['impact'],
            'effort': template['effort'],
            'timeline': template['timeline'],
            'confidence': 0.95,  # Rule-based recommendations are high confidence
            'triggered_at': datetime.now()
        }
```

---

## 4. Pattern-Based Recommendations

### 4.1 Historical Pattern Recognition

```python
class PatternRecognizer:
    def __init__(self):
        self.historical_patterns = self.load_patterns()

    def detect(self, context):
        """
        Detect patterns in current context that match historical scenarios.
        """
        recommendations = []

        # Pattern: Stalled growth
        if self.detect_stalled_growth(context):
            recommendations.append({
                'title': 'Address Stalled Growth',
                'description': 'Revenue growth has plateaued for 2+ months. '
                              'Historical data shows this often precedes decline without intervention.',
                'action_items': [
                    'Conduct customer interviews to identify friction points',
                    'Review product roadmap - are you building what customers want?',
                    'Explore new acquisition channels or partnerships',
                    'Consider pricing experiments or new package tiers'
                ],
                'category': 'strategic',
                'priority': 'high',
                'confidence': 0.75
            })

        # Pattern: Efficient growth phase
        if self.detect_efficient_growth(context):
            recommendations.append({
                'title': 'Scale Marketing Investment',
                'description': 'Unit economics are strong (LTV:CAC > 3.5, payback < 6 months). '
                              'Good time to accelerate growth.',
                'action_items': [
                    'Increase marketing budget by 20-30%',
                    'Expand to new customer segments',
                    'Test new acquisition channels',
                    'Consider hiring additional sales reps'
                ],
                'category': 'strategic',
                'priority': 'medium',
                'confidence': 0.80
            })

        # Pattern: Pre-churn indicators
        if self.detect_prechurn_signals(context):
            recommendations.append({
                'title': 'Proactive Retention Outreach',
                'description': 'Several customers showing early warning signs of churn '
                              '(decreased engagement, support tickets, payment issues).',
                'action_items': [
                    'Identify at-risk accounts from engagement data',
                    'Launch proactive outreach campaign',
                    'Offer onboarding refresher or check-in calls',
                    'Consider loyalty incentives or upgrade paths'
                ],
                'category': 'operational',
                'priority': 'high',
                'confidence': 0.70
            })

        return recommendations

    def detect_stalled_growth(self, context):
        """Check if revenue growth has flatlined."""
        trends = context.get('trends', {})
        mrr_trend = trends.get('mrr', {})

        return (mrr_trend.get('direction') == 'flat' and
                mrr_trend.get('duration_weeks', 0) >= 8)

    def detect_efficient_growth(self, context):
        """Check for strong unit economics."""
        kpis = context.get('kpis', {})
        ltv = kpis.get('ltv', 0)
        cac = kpis.get('cac', 1)
        churn = kpis.get('churn_rate', 1)

        return (ltv / cac > 3.5 and
                churn < 0.05 and
                kpis.get('payback_months', 12) < 6)

    def detect_prechurn_signals(self, context):
        """Detect early warning signs of customer churn."""
        engagement = context.get('engagement', {})
        support = context.get('support', {})

        return (engagement.get('declining_users', 0) > 5 or
                support.get('unresolved_tickets_high_priority', 0) > 3)
```

---

## 5. LLM-Based Recommendation Enrichment

### 5.1 Prompt Engineering

```python
class LLMRecommendationEnricher:
    def __init__(self, llm_client):
        self.llm_client = llm_client

    def enrich_recommendations(self, base_recommendations, founder_context):
        """
        Use LLM to add context, refine action items, and personalize.
        """
        enriched = []

        for rec in base_recommendations:
            # Build contextual prompt
            prompt = self.build_enrichment_prompt(rec, founder_context)

            # Call LLM
            response = self.llm_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": RECOMMENDATION_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,  # Lower for consistency
                max_tokens=500
            )

            # Parse response
            enriched_rec = self.parse_llm_response(response, rec)
            enriched.append(enriched_rec)

        return enriched

    def build_enrichment_prompt(self, recommendation, context):
        """
        Build LLM prompt with full context.
        """
        prompt = f"""
You are an experienced startup advisor. A recommendation has been generated for a founder:

**Recommendation:** {recommendation['title']}
**Description:** {recommendation['description']}
**Category:** {recommendation['category']}

**Founder Context:**
- Company: {context['company_name']} ({context['industry']})
- Stage: {context['stage']} (raised {context['funding_raised']})
- Team size: {context['team_size']}
- Recent metrics:
  - MRR: ${context['kpis']['mrr']:,.0f} ({context['trends']['mrr']['direction']})
  - CAC: ${context['kpis']['cac']:,.0f}
  - Churn: {context['kpis']['churn_rate']:.1%}
  - Runway: {context['kpis']['runway_months']:.1f} months

**Recent Meetings:**
{context['recent_meeting_summaries']}

**Recent Communications Sentiment:**
{context['sentiment_summary']}

Please:
1. Refine the action items to be more specific and tactical for this founder
2. Add 1-2 sentences explaining WHY this matters now
3. Suggest relevant resources or templates they might need
4. Estimate impact if they act vs don't act

Keep the response concise and actionable.
"""
        return prompt

RECOMMENDATION_SYSTEM_PROMPT = """
You are an AI Chief of Staff for startup founders. Your role is to provide:
- Strategic, actionable recommendations
- Specific, concrete next steps
- Context-aware advice based on company stage and metrics
- Honest assessment of urgency and impact

Your recommendations should:
- Be clear and concise (2-3 sentences max for descriptions)
- Prioritize founder time (high-impact, feasible actions)
- Reference specific data points when relevant
- Avoid generic advice - tailor to this founder's situation

Output format (JSON):
{
  "refined_description": "...",
  "why_now": "...",
  "action_items": ["...", "..."],
  "resources": ["...", "..."],
  "impact_if_acted": "...",
  "risk_if_ignored": "..."
}
"""
```

---

## 6. Recommendation Ranking & Filtering

### 6.1 Priority Scoring Algorithm

```python
class RecommendationRanker:
    def rank_recommendations(self, recommendations, context):
        """
        Rank recommendations by relevance, urgency, and impact.
        """
        scored_recs = []

        for rec in recommendations:
            score = self.calculate_priority_score(rec, context)
            rec['priority_score'] = score
            scored_recs.append(rec)

        # Sort by priority score
        scored_recs.sort(key=lambda x: x['priority_score'], reverse=True)

        # Apply diversity filtering (don't overload one category)
        filtered = self.apply_diversity_filter(scored_recs)

        return filtered

    def calculate_priority_score(self, rec, context):
        """
        Calculate priority score (0-100).

        Components:
        - Urgency (40%): How time-sensitive is this?
        - Impact (30%): Business impact if acted on
        - Feasibility (20%): Can founder realistically do this?
        - Confidence (10%): How certain are we this is relevant?
        """
        # Urgency score
        urgency_map = {'critical': 1.0, 'high': 0.75, 'medium': 0.5, 'low': 0.25}
        urgency_score = urgency_map.get(rec.get('priority', 'medium'), 0.5)

        # Impact score
        impact_map = {'critical': 1.0, 'high': 0.8, 'medium': 0.5, 'low': 0.3}
        impact_score = impact_map.get(rec.get('impact', 'medium'), 0.5)

        # Feasibility score (inverse of effort)
        effort_map = {'low': 1.0, 'medium': 0.6, 'high': 0.3}
        feasibility_score = effort_map.get(rec.get('effort', 'medium'), 0.6)

        # Confidence score
        confidence_score = rec.get('confidence', 0.7)

        # Weighted combination
        priority_score = (
            urgency_score * 0.40 +
            impact_score * 0.30 +
            feasibility_score * 0.20 +
            confidence_score * 0.10
        ) * 100

        return priority_score

    def apply_diversity_filter(self, recommendations, max_per_category=2):
        """
        Ensure diversity of recommendation categories in final output.
        """
        filtered = []
        category_counts = {}

        for rec in recommendations:
            category = rec.get('category', 'general')
            count = category_counts.get(category, 0)

            if count < max_per_category:
                filtered.append(rec)
                category_counts[category] = count + 1

            if len(filtered) >= 5:  # Max 5 recommendations
                break

        return filtered
```

---

## 7. Confidence Calibration

### 7.1 Confidence Scoring

```python
def calculate_recommendation_confidence(rec, context):
    """
    Calculate confidence score (0-1) for recommendation quality.

    Factors:
    - Data completeness
    - Historical accuracy of similar recommendations
    - Statistical significance of underlying signals
    """
    confidence_factors = []

    # Data completeness
    required_data = rec.get('required_data', [])
    available_data = [key for key in required_data if key in context]
    data_completeness = len(available_data) / len(required_data) if required_data else 1.0
    confidence_factors.append(data_completeness)

    # Signal strength (for anomaly-based recommendations)
    if 'anomaly' in rec.get('source', ''):
        signal_strength = rec.get('anomaly_score', 0.7)
        confidence_factors.append(signal_strength)

    # Historical accuracy (if we have feedback data)
    if rec.get('rule_id'):
        historical_accuracy = get_rule_accuracy(rec['rule_id'])
        confidence_factors.append(historical_accuracy)

    # Average confidence
    overall_confidence = np.mean(confidence_factors)

    return overall_confidence

def get_rule_accuracy(rule_id):
    """
    Retrieve historical accuracy of this rule from feedback data.
    """
    # Query database for past recommendations from this rule
    # Return: (accepted_count / total_count)
    # Default to 0.75 if no history
    return 0.75
```

---

## 8. Impact Prediction & Tracking

### 8.1 Estimated Impact

```python
IMPACT_ESTIMATES = {
    'runway_critical': {
        'if_acted': 'Successfully close fundraising round, extend runway 12-24 months',
        'if_ignored': 'Risk running out of cash, forced shutdown or fire sale',
        'estimated_value': 1000000  # $1M+ value
    },
    'ltv_cac_unhealthy': {
        'if_acted': 'Improve unit economics by 20-30%, increase profit margin',
        'if_ignored': 'Unsustainable growth, burning cash on unprofitable customers',
        'estimated_value': 100000
    },
    'churn_spike': {
        'if_acted': 'Reduce churn by 30-50%, retain $50-100K MRR',
        'if_ignored': 'Accelerating revenue loss, damaged brand reputation',
        'estimated_value': 75000
    }
}
```

### 8.2 Recommendation Tracking

```python
class RecommendationTracker:
    def track_recommendation(self, rec_id, founder_action):
        """
        Track founder response to recommendation.

        Actions: 'implemented', 'scheduled', 'dismissed', 'needs_more_info'
        """
        db.recommendations.update(
            {'id': rec_id},
            {
                'founder_action': founder_action,
                'acted_at': datetime.now(),
                'status': 'completed' if founder_action == 'implemented' else 'pending'
            }
        )

    def calculate_acceptance_rate(self):
        """
        Calculate % of recommendations acted upon.
        """
        total = db.recommendations.count()
        acted = db.recommendations.count({'founder_action': {'$in': ['implemented', 'scheduled']}})

        return acted / total if total > 0 else 0
```

---

## 9. Implementation Roadmap

**Week 1-2:** Rule-based engine with top 8 critical rules
**Week 3:** Pattern recognition for common scenarios
**Week 4:** LLM enrichment pipeline with GPT-4
**Week 5:** Ranking, filtering, and tracking system
**Week 6+:** Continuous improvement from feedback

---

## 10. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Recommendation Acceptance Rate | ≥80% | % implemented or scheduled |
| Daily Recommendations | 3-5 | Count per founder per day |
| Confidence Calibration | ≥85% | Confidence matches actual acceptance |
| Actionability Score | ≥4/5 | Founder rating on clarity |
| Time to Action | <24h | Time from recommendation to action |

---

## 11. Cost Optimization

- **Rule-based recommendations:** $0 (deterministic)
- **Pattern recognition:** $0.01 per analysis (compute)
- **LLM enrichment:** $0.05 per recommendation (GPT-4 tokens)
- **Total per founder per day:** ~$0.20 (4 recs × $0.05)
- **Monthly cost:** ~$6/founder

**Optimization:** Only enrich top 5 ranked recommendations with LLM.

---

## References

1. Agrawal, A., et al. (2019). "Prediction Machines: The Simple Economics of AI"
2. OpenAI (2023). "GPT-4 Technical Report"
3. Silver, D., et al. (2016). "Mastering the game of Go with deep neural networks"
