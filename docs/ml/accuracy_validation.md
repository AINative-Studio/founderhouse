# ML Accuracy Validation Strategy

## Executive Summary

This document defines the comprehensive validation strategy for all ML components in the Meeting Intelligence system. We establish ground truth datasets, evaluation metrics, testing protocols, and continuous monitoring to ensure ≥85-90% accuracy targets are consistently met.

## Validation Philosophy

### Core Principles

1. **Ground Truth First:** Establish high-quality labeled datasets before deployment
2. **Multi-Metric Evaluation:** No single metric tells the full story
3. **Human-in-the-Loop:** Automated metrics + human evaluation
4. **Continuous Validation:** Monitor accuracy in production, not just in development
5. **User Feedback Integration:** Users are the ultimate arbiters of quality

## Component-Specific Validation

### 1. Meeting Summarization

#### Target Metrics
- Factual correctness: ≥90%
- Completeness: ≥85% (captures key points)
- Coherence: ≥90% (well-structured, readable)
- Actionability: ≥85% (useful for decision-making)

#### Evaluation Methodology

**ROUGE Scores (Automated)**
```python
from rouge_score import rouge_scorer

def evaluate_summary_rouge(generated_summary: str, reference_summary: str) -> Dict:
    """
    Calculate ROUGE scores for summary quality
    """
    scorer = rouge_scorer.RougeScorer(['rouge1', 'rouge2', 'rougeL'], use_stemmer=True)
    scores = scorer.score(reference_summary, generated_summary)

    return {
        "rouge1_f1": scores['rouge1'].fmeasure,
        "rouge2_f1": scores['rouge2'].fmeasure,
        "rougeL_f1": scores['rougeL'].fmeasure,
        "avg_rouge": (scores['rouge1'].fmeasure +
                     scores['rouge2'].fmeasure +
                     scores['rougeL'].fmeasure) / 3
    }

# Targets:
# ROUGE-1 F1: ≥0.45
# ROUGE-2 F1: ≥0.20
# ROUGE-L F1: ≥0.40
```

**Factual Consistency (LLM-based)**
```python
FACTUAL_CONSISTENCY_PROMPT = """Compare this summary against the source transcript for factual accuracy.

TRANSCRIPT:
{transcript}

SUMMARY:
{summary}

Check each claim in the summary:
1. Is it supported by the transcript?
2. Is it accurately stated (no misrepresentation)?
3. Are numbers/dates/names correct?

Return JSON:
{{
    "factual_accuracy_score": 0.0-1.0,
    "total_claims": N,
    "accurate_claims": M,
    "inaccurate_claims": [
        {{
            "claim": "statement from summary",
            "issue": "not supported|misrepresented|incorrect detail",
            "evidence": "what the transcript actually says"
        }}
    ],
    "hallucinations": ["statements with no basis in transcript"],
    "omissions": ["critical information missing from summary"]
}}
"""

def validate_factual_consistency(summary: str, transcript: str) -> Dict:
    """Use LLM to validate factual accuracy"""
    prompt = FACTUAL_CONSISTENCY_PROMPT.format(
        transcript=transcript,
        summary=summary
    )
    return call_llm("gpt-4o-mini", prompt, response_format="json")
```

**Human Evaluation Protocol**

Create evaluation rubric for human reviewers:

| Dimension | Score 1 | Score 2 | Score 3 | Score 4 | Score 5 |
|-----------|---------|---------|---------|---------|---------|
| **Factual Accuracy** | Multiple errors | 1-2 errors | Mostly accurate | Very accurate | Perfect |
| **Completeness** | Missing key points | Some gaps | Covers main points | Comprehensive | Thorough |
| **Coherence** | Confusing | Hard to follow | Readable | Clear | Excellent |
| **Actionability** | Not useful | Limited use | Useful | Very useful | Extremely useful |
| **Conciseness** | Too brief | Somewhat brief | Appropriate | Slightly long | Too long |

```python
def calculate_human_eval_score(ratings: List[Dict]) -> Dict:
    """
    Aggregate human evaluation ratings
    """
    dimensions = ['factual_accuracy', 'completeness', 'coherence',
                  'actionability', 'conciseness']

    results = {}
    for dim in dimensions:
        scores = [r[dim] for r in ratings]
        results[dim] = {
            "mean": statistics.mean(scores),
            "std": statistics.stdev(scores) if len(scores) > 1 else 0,
            "median": statistics.median(scores),
            "pass_rate": sum(1 for s in scores if s >= 4) / len(scores)
        }

    # Overall score (weighted)
    weights = {
        'factual_accuracy': 0.30,
        'completeness': 0.25,
        'coherence': 0.20,
        'actionability': 0.20,
        'conciseness': 0.05
    }

    overall = sum(results[dim]["mean"] * weights[dim] for dim in dimensions)

    return {
        "dimension_scores": results,
        "overall_score": overall / 5.0,  # Normalize to 0-1
        "pass": overall / 5.0 >= 0.80  # 4.0/5.0 = 80%
    }
```

---

### 2. Action Item Extraction

#### Target Metrics
- Precision: ≥85% (few false positives)
- Recall: ≥85% (few missed items)
- F1 Score: ≥85%
- Assignee accuracy: ≥75%
- Deadline extraction: ≥70%

#### Evaluation Methodology

**Ground Truth Dataset Creation**

```python
@dataclass
class ActionItemLabel:
    description: str
    assignee: Optional[str]
    due_date: Optional[str]
    priority: str
    source_sentence: str
    is_explicit: bool  # vs. implicit

def create_ground_truth_dataset():
    """
    Label action items in 50 diverse meetings

    Process:
    1. Manual labeling by 2 independent annotators
    2. Resolve disagreements through discussion
    3. Calculate inter-annotator agreement (Cohen's kappa)
    4. Target: kappa ≥ 0.75 (substantial agreement)
    """
    pass
```

**Precision, Recall, F1 Calculation**

```python
def calculate_extraction_metrics(
    predicted_actions: List[ActionItem],
    ground_truth_actions: List[ActionItemLabel],
    similarity_threshold: float = 0.85
) -> Dict:
    """
    Calculate precision, recall, F1 for action item extraction

    Use semantic similarity to match predicted vs ground truth
    (exact string matching too strict)
    """
    from sentence_transformers import SentenceTransformer
    from sklearn.metrics.pairwise import cosine_similarity

    model = SentenceTransformer('all-MiniLM-L6-v2')

    # Encode descriptions
    pred_embeddings = model.encode([a.description for a in predicted_actions])
    gt_embeddings = model.encode([a.description for a in ground_truth_actions])

    # Calculate similarity matrix
    similarity_matrix = cosine_similarity(pred_embeddings, gt_embeddings)

    # Match predicted to ground truth
    true_positives = 0
    matched_gt = set()

    for i, pred in enumerate(predicted_actions):
        # Find best match in ground truth
        best_match_idx = similarity_matrix[i].argmax()
        best_similarity = similarity_matrix[i][best_match_idx]

        if best_similarity >= similarity_threshold and best_match_idx not in matched_gt:
            true_positives += 1
            matched_gt.add(best_match_idx)

    false_positives = len(predicted_actions) - true_positives
    false_negatives = len(ground_truth_actions) - true_positives

    precision = true_positives / len(predicted_actions) if predicted_actions else 0
    recall = true_positives / len(ground_truth_actions) if ground_truth_actions else 0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

    return {
        "true_positives": true_positives,
        "false_positives": false_positives,
        "false_negatives": false_negatives,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "pass": f1 >= 0.85
    }
```

**Assignee and Deadline Accuracy**

```python
def calculate_attribute_accuracy(
    predicted_actions: List[ActionItem],
    ground_truth_actions: List[ActionItemLabel],
    matched_pairs: List[Tuple[int, int]]
) -> Dict:
    """
    Calculate accuracy for assignee and deadline extraction
    """
    assignee_correct = 0
    assignee_total = 0
    deadline_correct = 0
    deadline_total = 0

    for pred_idx, gt_idx in matched_pairs:
        pred = predicted_actions[pred_idx]
        gt = ground_truth_actions[gt_idx]

        # Assignee accuracy (fuzzy match on names)
        if gt.assignee:
            assignee_total += 1
            if pred.assignee and normalize_name(pred.assignee) == normalize_name(gt.assignee):
                assignee_correct += 1

        # Deadline accuracy (normalized dates)
        if gt.due_date:
            deadline_total += 1
            if pred.due_date and dates_match(pred.due_date, gt.due_date):
                deadline_correct += 1

    return {
        "assignee_accuracy": assignee_correct / assignee_total if assignee_total > 0 else None,
        "deadline_accuracy": deadline_correct / deadline_total if deadline_total > 0 else None,
        "assignee_pass": (assignee_correct / assignee_total) >= 0.75 if assignee_total > 0 else True,
        "deadline_pass": (deadline_correct / deadline_total) >= 0.70 if deadline_total > 0 else True
    }
```

---

### 3. Sentiment Analysis

#### Target Metrics
- Overall sentiment accuracy: ≥85%
- Per-speaker sentiment: ≥80%
- Key moment detection precision: ≥75%
- Key moment detection recall: ≥70%

#### Evaluation Methodology

**Classification Accuracy**

```python
from sklearn.metrics import classification_report, confusion_matrix

def evaluate_sentiment_classification(
    predictions: List[str],
    ground_truth: List[str],
    labels: List[str] = ['positive', 'negative', 'neutral', 'mixed']
) -> Dict:
    """
    Evaluate sentiment classification accuracy
    """
    report = classification_report(
        ground_truth,
        predictions,
        labels=labels,
        output_dict=True,
        zero_division=0
    )

    cm = confusion_matrix(ground_truth, predictions, labels=labels)

    return {
        "accuracy": report['accuracy'],
        "macro_f1": report['macro avg']['f1-score'],
        "weighted_f1": report['weighted avg']['f1-score'],
        "per_class": {
            label: {
                "precision": report[label]['precision'],
                "recall": report[label]['recall'],
                "f1": report[label]['f1-score']
            }
            for label in labels
        },
        "confusion_matrix": cm.tolist(),
        "pass": report['accuracy'] >= 0.85
    }
```

**Key Moment Detection Evaluation**

```python
def evaluate_key_moment_detection(
    predicted_moments: List[Dict],
    ground_truth_moments: List[Dict],
    time_window: int = 60  # seconds
) -> Dict:
    """
    Evaluate key moment detection using temporal matching
    """
    # Match moments within time window
    true_positives = 0
    matched_gt = set()

    for pred in predicted_moments:
        for i, gt in enumerate(ground_truth_moments):
            if i in matched_gt:
                continue

            # Check if same type and within time window
            if (pred['type'] == gt['type'] and
                time_difference(pred['timestamp'], gt['timestamp']) <= time_window):
                true_positives += 1
                matched_gt.add(i)
                break

    false_positives = len(predicted_moments) - true_positives
    false_negatives = len(ground_truth_moments) - true_positives

    precision = true_positives / len(predicted_moments) if predicted_moments else 0
    recall = true_positives / len(ground_truth_moments) if ground_truth_moments else 0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "precision_pass": precision >= 0.75,
        "recall_pass": recall >= 0.70
    }
```

---

### 4. Decision Extraction

#### Target Metrics
- Decision detection precision: ≥85%
- Decision detection recall: ≥80%
- Decision clarity: ≥85% (human-rated)

#### Evaluation Methodology

Similar to action items, using semantic similarity matching and human evaluation.

---

## Test Dataset Strategy

### Dataset Composition

| Dataset Split | Size | Purpose |
|---------------|------|---------|
| **Development** | 20 meetings | Prompt engineering, tuning |
| **Validation** | 15 meetings | Model selection, hyperparameter tuning |
| **Test** | 15 meetings | Final evaluation, never used in development |
| **Production Monitor** | Ongoing | Continuous accuracy tracking |

**Total: 50 meetings across diverse types**

### Meeting Diversity Matrix

| Meeting Type | Count | Duration Range | Participants |
|--------------|-------|----------------|--------------|
| Board | 5 | 60-120 min | 5-10 |
| Investor | 8 | 30-60 min | 2-8 |
| Team Sync | 12 | 15-45 min | 3-15 |
| Customer/Sales | 10 | 30-90 min | 2-6 |
| Strategic | 8 | 60-120 min | 4-12 |
| 1-on-1 | 7 | 30-60 min | 2 |

### Labeling Protocol

```python
class LabelingGuidelines:
    """
    Guidelines for human annotators
    """

    # Meeting Summary
    SUMMARY_INSTRUCTIONS = """
    Create a reference summary including:
    1. 2-3 sentence executive summary
    2. List all key topics (5-10 items)
    3. List all decisions (with who/what/why)
    4. List all action items (with assignee/deadline if mentioned)
    5. Note any open questions
    6. Note any risks or concerns mentioned
    """

    # Action Items
    ACTION_ITEM_INSTRUCTIONS = """
    Label all action items where someone committed to do something.

    Include:
    - Explicit: "John will send the deck by Friday"
    - Implicit but clear: "I'll handle that" (context makes it clear)

    Exclude:
    - Vague: "We should think about X"
    - Historical: "We discussed Y"
    - Hypothetical: "Maybe we could try Z"

    For each action item, note:
    - Description (specific)
    - Assignee (if mentioned or clearly implied)
    - Deadline (if mentioned)
    - Priority (based on urgency signals)
    - Source quote
    """

    # Sentiment
    SENTIMENT_INSTRUCTIONS = """
    Label sentiment at multiple levels:

    1. Overall meeting: positive/negative/neutral/mixed
    2. Per speaker: emotion + engagement level
    3. Key moments: tension, agreement, confusion, breakthrough, concern

    Be objective - use evidence from transcript, not inference.
    """

    # Decisions
    DECISION_INSTRUCTIONS = """
    Label all firm decisions, not just discussions.

    Decision criteria:
    - Finality: "We will" not "We should"
    - Authority: Decision maker has authority
    - Clarity: What was decided is clear

    For each decision:
    - What was decided
    - Who decided
    - Why (rationale if discussed)
    - Alternatives considered
    """
```

### Inter-Annotator Agreement

```python
from sklearn.metrics import cohen_kappa_score

def calculate_inter_annotator_agreement(
    annotator1_labels: List,
    annotator2_labels: List
) -> Dict:
    """
    Calculate agreement between two annotators

    Target: Cohen's kappa ≥ 0.75 (substantial agreement)
    """
    kappa = cohen_kappa_score(annotator1_labels, annotator2_labels)

    agreement_level = (
        "poor" if kappa < 0.20 else
        "fair" if kappa < 0.40 else
        "moderate" if kappa < 0.60 else
        "substantial" if kappa < 0.80 else
        "almost perfect"
    )

    return {
        "kappa": kappa,
        "agreement_level": agreement_level,
        "pass": kappa >= 0.75
    }
```

---

## Continuous Monitoring in Production

### Real-Time Accuracy Tracking

```python
class AccuracyMonitor:
    """
    Monitor ML accuracy in production using user feedback
    """

    def track_user_feedback(self, meeting_id: str, component: str, feedback: Dict):
        """
        Collect user feedback on ML outputs

        Feedback types:
        - Thumbs up/down on summary
        - Manual edits to action items
        - Corrections to sentiment
        - Missing items reported
        """
        # Log to metrics database
        self.log_feedback(meeting_id, component, feedback)

        # Calculate rolling accuracy metrics
        self.update_rolling_metrics(component)

        # Alert if accuracy drops below threshold
        if self.get_recent_accuracy(component) < self.threshold:
            self.alert_degradation(component)

    def calculate_edit_distance_metric(self, original: str, edited: str) -> float:
        """
        User edits indicate quality - less editing = higher quality
        """
        from difflib import SequenceMatcher

        similarity = SequenceMatcher(None, original, edited).ratio()

        # Convert to edit rate (lower is better)
        edit_rate = 1 - similarity

        return edit_rate

    def get_rolling_metrics(self, component: str, window_days: int = 7) -> Dict:
        """
        Calculate rolling accuracy metrics over past N days
        """
        # Get recent feedback
        feedback = self.get_feedback(component, days=window_days)

        metrics = {
            "thumbs_up_rate": self.calculate_approval_rate(feedback),
            "average_edit_rate": self.calculate_avg_edit_rate(feedback),
            "missing_items_per_meeting": self.calculate_miss_rate(feedback),
            "hallucination_rate": self.calculate_hallucination_rate(feedback),
            "sample_size": len(feedback)
        }

        return metrics
```

### Alert Thresholds

```python
ACCURACY_ALERT_THRESHOLDS = {
    "summarization": {
        "thumbs_down_rate": 0.20,  # Alert if >20% thumbs down
        "high_edit_rate": 0.30,    # Alert if >30% content edited
        "factual_errors_reported": 0.10  # Alert if >10% have factual errors
    },
    "action_items": {
        "false_positive_rate": 0.15,  # Alert if >15% marked as not action items
        "missing_items_reported_rate": 0.20,  # Alert if >20% report missing items
        "low_confidence_rate": 0.40  # Alert if >40% have confidence <0.7
    },
    "sentiment": {
        "disagreement_rate": 0.25,  # Alert if >25% disagree with sentiment
        "low_usefulness_rate": 0.30  # Alert if >30% say not useful
    }
}
```

### Weekly Accuracy Reports

```python
def generate_weekly_accuracy_report() -> Dict:
    """
    Generate comprehensive accuracy report for all ML components
    """
    report = {
        "week_ending": datetime.now().isoformat(),
        "components": {}
    }

    for component in ["summarization", "action_items", "sentiment", "decisions"]:
        metrics = get_rolling_metrics(component, window_days=7)

        # Sample meetings for manual QA
        sample = sample_meetings_for_qa(component, n=10)

        # Calculate pass/fail
        passed = all(
            metrics[threshold] <= ACCURACY_ALERT_THRESHOLDS[component][threshold]
            for threshold in ACCURACY_ALERT_THRESHOLDS[component]
        )

        report["components"][component] = {
            "metrics": metrics,
            "status": "pass" if passed else "fail",
            "samples_for_qa": sample,
            "trends": calculate_trends(component, weeks=4)
        }

    return report
```

---

## A/B Testing Framework

### Prompt Optimization Testing

```python
class ABTest:
    """
    A/B test different prompts or models
    """

    def run_ab_test(
        self,
        variant_a: str,  # "Current prompt"
        variant_b: str,  # "New prompt"
        sample_size: int = 100,
        component: str = "summarization"
    ) -> Dict:
        """
        Run A/B test comparing two variants

        Randomly assign meetings to variant A or B
        Collect metrics and user feedback
        Calculate statistical significance
        """
        from scipy.stats import ttest_ind

        # Run both variants on same meetings
        results_a = []
        results_b = []

        for meeting in sample_meetings(sample_size):
            # Run both variants
            output_a = run_variant(meeting, variant_a)
            output_b = run_variant(meeting, variant_b)

            # Collect metrics
            results_a.append(evaluate_output(output_a, meeting))
            results_b.append(evaluate_output(output_b, meeting))

        # Calculate means
        mean_a = statistics.mean(results_a)
        mean_b = statistics.mean(results_b)

        # Statistical significance
        t_stat, p_value = ttest_ind(results_a, results_b)

        # Determine winner
        if p_value < 0.05:
            winner = "variant_b" if mean_b > mean_a else "variant_a"
            confidence = 1 - p_value
        else:
            winner = "no significant difference"
            confidence = 0

        return {
            "variant_a_mean": mean_a,
            "variant_b_mean": mean_b,
            "improvement": ((mean_b - mean_a) / mean_a) * 100,
            "p_value": p_value,
            "statistically_significant": p_value < 0.05,
            "winner": winner,
            "confidence": confidence,
            "recommendation": self.make_recommendation(winner, confidence)
        }
```

---

## Implementation Timeline

### Week 1: Ground Truth Creation
- Label 50 meetings across all dimensions
- Calculate inter-annotator agreement
- Resolve disagreements
- Finalize ground truth dataset

### Week 2: Baseline Evaluation
- Run all ML components on test set
- Calculate baseline metrics
- Identify failure modes
- Document baseline performance

### Week 3: Optimization
- Tune prompts based on failures
- A/B test variations
- Iterate until targets met
- Document winning approaches

### Week 4: Production Monitoring Setup
- Implement feedback collection
- Set up monitoring dashboard
- Configure alerts
- Begin continuous tracking

---

## Success Criteria

| Component | Metric | Target | Baseline | Status |
|-----------|--------|--------|----------|--------|
| **Summarization** | Factual Accuracy | ≥90% | TBD | ⏸️ Not Started |
| | ROUGE-L F1 | ≥0.40 | TBD | ⏸️ Not Started |
| | User Approval | ≥80% | TBD | ⏸️ Not Started |
| **Action Items** | F1 Score | ≥85% | TBD | ⏸️ Not Started |
| | Assignee Accuracy | ≥75% | TBD | ⏸️ Not Started |
| | Deadline Accuracy | ≥70% | TBD | ⏸️ Not Started |
| **Sentiment** | Classification Accuracy | ≥85% | TBD | ⏸️ Not Started |
| | Key Moment F1 | ≥70% | TBD | ⏸️ Not Started |
| **Decisions** | Detection F1 | ≥82% | TBD | ⏸️ Not Started |

**Overall Success:** All components meet or exceed targets on held-out test set.

---

**Document Version:** 1.0
**Last Updated:** 2025-10-30
**Author:** ML Research Team
**Status:** Ready for Implementation
