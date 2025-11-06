# Insights Validation & Testing Framework

## Executive Summary

This document defines the validation methodology, test datasets, metrics dashboards, and continuous monitoring strategy for Sprint 4's Insights Engine. The framework ensures ≥85% anomaly detection F1, <5% false positive rate, ≥80% recommendation quality, and ≥90% briefing accuracy.

---

## 1. Validation Strategy

### 1.1 Three-Tier Approach

**Tier 1: Unit Testing (Component-Level)**
- Test each ML component in isolation
- Use synthetic data with known ground truth
- Fast feedback (<1 minute per test)

**Tier 2: Integration Testing (System-Level)**
- Test full pipeline with realistic data
- Validate data flow between components
- Catch integration bugs

**Tier 3: Production Validation (User-Level)**
- A/B testing with real founders
- Feedback collection and tracking
- Continuous monitoring

---

## 2. Test Datasets

### 2.1 Synthetic Anomaly Dataset

```python
def generate_synthetic_kpi_data(
    baseline=10000,
    length_days=180,
    trend_rate=0.02,  # 2% monthly growth
    seasonality_strength=0.1,
    noise_level=0.05,
    anomaly_count=10
):
    """
    Generate synthetic KPI time series with known anomalies.

    Returns:
        data: Time series
        true_anomalies: List of anomaly indices
        anomaly_types: Type of each anomaly
    """
    dates = pd.date_range(end=pd.Timestamp.now(), periods=length_days, freq='D')

    # Base trend
    trend = baseline * (1 + trend_rate/30) ** np.arange(length_days)

    # Weekly seasonality
    day_of_week = np.array([d.dayofweek for d in dates])
    seasonal = seasonality_strength * trend * np.sin(2 * np.pi * day_of_week / 7)

    # Noise
    noise = np.random.normal(0, noise_level * trend)

    # Combine
    data = trend + seasonal + noise

    # Inject anomalies
    true_anomalies = []
    anomaly_types = []
    anomaly_indices = np.random.choice(length_days, anomaly_count, replace=False)

    for idx in sorted(anomaly_indices):
        anomaly_type = np.random.choice(['spike', 'drop', 'level_shift'])

        if anomaly_type == 'spike':
            data[idx] *= np.random.uniform(1.5, 2.5)
        elif anomaly_type == 'drop':
            data[idx] *= np.random.uniform(0.3, 0.7)
        elif anomaly_type == 'level_shift':
            # Persistent shift
            shift = np.random.uniform(1.3, 1.8)
            data[idx:] *= shift

        true_anomalies.append(idx)
        anomaly_types.append(anomaly_type)

    return pd.Series(data, index=dates), true_anomalies, anomaly_types

# Generate test datasets
test_datasets = {
    'stable_growth': generate_synthetic_kpi_data(trend_rate=0.03, noise_level=0.02),
    'volatile': generate_synthetic_kpi_data(noise_level=0.15),
    'seasonal_strong': generate_synthetic_kpi_data(seasonality_strength=0.3),
    'declining': generate_synthetic_kpi_data(trend_rate=-0.02)
}
```

### 2.2 Historical Data with Labels

**Manual Labeling Process:**
1. Extract 6 months of real KPI data
2. Founder reviews and labels true anomalies
3. Mark false positives from previous detections
4. Annotate with context (product launch, marketing campaign, etc.)

**Labeled Dataset Structure:**
```python
labeled_data = {
    'timeseries': pd.DataFrame,  # KPI values over time
    'anomalies': [
        {
            'date': '2025-08-15',
            'kpi': 'mrr',
            'is_anomaly': True,
            'magnitude': 0.15,
            'explanation': 'Major customer churn',
            'should_alert': True
        },
        # ...
    ]
}
```

---

## 3. Validation Metrics

### 3.1 Anomaly Detection Metrics

```python
from sklearn.metrics import precision_score, recall_score, f1_score, roc_auc_score

def evaluate_anomaly_detector(predictions, ground_truth):
    """
    Calculate comprehensive metrics for anomaly detection.

    Args:
        predictions: Binary array (1=anomaly, 0=normal)
        ground_truth: Binary array (true labels)
    """
    # Basic metrics
    precision = precision_score(ground_truth, predictions)
    recall = recall_score(ground_truth, predictions)
    f1 = f1_score(ground_truth, predictions)

    # Confusion matrix
    tp = np.sum((predictions == 1) & (ground_truth == 1))
    fp = np.sum((predictions == 1) & (ground_truth == 0))
    tn = np.sum((predictions == 0) & (ground_truth == 0))
    fn = np.sum((predictions == 0) & (ground_truth == 1))

    # False positive rate
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0

    # Detection delay (how quickly do we catch anomalies?)
    delays = []
    for idx in np.where(ground_truth == 1)[0]:
        # Find first detection within 3 days
        detection_window = predictions[idx:idx+3]
        if np.any(detection_window == 1):
            delay = np.where(detection_window == 1)[0][0]
            delays.append(delay)

    avg_delay = np.mean(delays) if delays else None

    return {
        'precision': precision,
        'recall': recall,
        'f1_score': f1,
        'false_positive_rate': fpr,
        'true_positives': tp,
        'false_positives': fp,
        'true_negatives': tn,
        'false_negatives': fn,
        'avg_detection_delay_days': avg_delay,
        'detection_rate': len(delays) / np.sum(ground_truth) if np.sum(ground_truth) > 0 else 0
    }

# Target thresholds
TARGETS = {
    'precision': 0.90,
    'recall': 0.85,
    'f1_score': 0.87,
    'false_positive_rate': 0.05
}
```

### 3.2 Trend Analysis Validation

```python
def evaluate_trend_detector(predicted_trends, actual_trends):
    """
    Validate trend detection accuracy.

    Args:
        predicted_trends: List of ('up', 'down', 'flat')
        actual_trends: List of ground truth trends
    """
    # Direction accuracy
    correct = sum(p == a for p, a in zip(predicted_trends, actual_trends))
    direction_accuracy = correct / len(predicted_trends)

    # Confusion matrix for multi-class
    from sklearn.metrics import confusion_matrix, classification_report

    cm = confusion_matrix(actual_trends, predicted_trends, labels=['up', 'down', 'flat'])
    report = classification_report(actual_trends, predicted_trends, labels=['up', 'down', 'flat'])

    return {
        'direction_accuracy': direction_accuracy,
        'confusion_matrix': cm,
        'classification_report': report
    }
```

### 3.3 Recommendation Quality Metrics

```python
def evaluate_recommendations(recommendations, founder_actions):
    """
    Evaluate recommendation engine performance.

    Args:
        recommendations: List of generated recommendations
        founder_actions: List of actions taken (implemented, scheduled, dismissed, ignored)
    """
    # Acceptance rate (implemented or scheduled)
    accepted = [a in ['implemented', 'scheduled'] for a in founder_actions]
    acceptance_rate = np.mean(accepted)

    # Confidence calibration
    confidences = [r['confidence'] for r in recommendations]
    calibration_error = np.abs(np.mean(confidences) - acceptance_rate)

    # Impact tracking (for implemented recommendations)
    implemented_indices = [i for i, a in enumerate(founder_actions) if a == 'implemented']
    # Would need follow-up data to measure actual impact

    return {
        'acceptance_rate': acceptance_rate,
        'dismissed_rate': np.mean([a == 'dismissed' for a in founder_actions]),
        'ignored_rate': np.mean([a == 'ignored' for a in founder_actions]),
        'avg_confidence': np.mean(confidences),
        'confidence_calibration_error': calibration_error,
        'total_recommendations': len(recommendations),
        'implemented_count': len(implemented_indices)
    }
```

---

## 4. Backtesting Framework

### 4.1 Historical Backtesting

```python
def backtest_anomaly_detector(detector, historical_data, labeled_anomalies):
    """
    Simulate detector performance on historical data.

    Uses walk-forward validation: Train on past, test on future.
    """
    results = []

    # Start with minimum required history (30 days)
    min_history = 30

    for i in range(min_history, len(historical_data)):
        # Training window: all data up to current point
        train_data = historical_data.iloc[:i]

        # Current point to test
        current_value = historical_data.iloc[i]
        current_date = historical_data.index[i]

        # Detect anomaly
        prediction = detector.detect(current_value, train_data)

        # Ground truth
        true_label = any(
            anomaly['date'] == current_date
            for anomaly in labeled_anomalies
        )

        results.append({
            'date': current_date,
            'predicted': prediction['is_anomaly'],
            'actual': true_label,
            'confidence': prediction.get('confidence', 0.5),
            'value': current_value
        })

    # Evaluate
    predictions = np.array([r['predicted'] for r in results])
    ground_truth = np.array([r['actual'] for r in results])

    metrics = evaluate_anomaly_detector(predictions, ground_truth)

    return metrics, results
```

### 4.2 Cross-Validation for KPIs

```python
def cross_validate_by_kpi(detector, kpi_data_dict, labeled_anomalies_dict):
    """
    Validate detector across multiple KPIs.

    Args:
        kpi_data_dict: {'mrr': pd.Series, 'cac': pd.Series, ...}
        labeled_anomalies_dict: {'mrr': [...], 'cac': [...], ...}
    """
    results = {}

    for kpi_name, kpi_data in kpi_data_dict.items():
        print(f"Backtesting {kpi_name}...")

        metrics, detailed_results = backtest_anomaly_detector(
            detector,
            kpi_data,
            labeled_anomalies_dict[kpi_name]
        )

        results[kpi_name] = metrics

    # Aggregate metrics
    aggregate = {
        'avg_precision': np.mean([r['precision'] for r in results.values()]),
        'avg_recall': np.mean([r['recall'] for r in results.values()]),
        'avg_f1': np.mean([r['f1_score'] for r in results.values()]),
        'avg_fpr': np.mean([r['false_positive_rate'] for r in results.values()]),
        'per_kpi': results
    }

    return aggregate
```

---

## 5. A/B Testing Framework

### 5.1 Threshold Strategy Testing

```python
class ThresholdABTest:
    def __init__(self, test_name, variants):
        """
        Args:
            variants: Dict of threshold strategies to test
                e.g., {'static': StaticThresholds(), 'dynamic': DynamicThresholds()}
        """
        self.test_name = test_name
        self.variants = variants
        self.assignments = {}  # founder_id -> variant
        self.results = {v: {'detections': [], 'feedback': []} for v in variants}

    def assign_variant(self, founder_id):
        """Randomly assign founder to variant."""
        if founder_id not in self.assignments:
            self.assignments[founder_id] = np.random.choice(list(self.variants.keys()))
        return self.assignments[founder_id]

    def record_detection(self, founder_id, kpi, anomaly_result, founder_feedback):
        """
        Record detection and founder feedback.

        Args:
            founder_feedback: 'true_positive', 'false_positive', or 'missed'
        """
        variant = self.assignments[founder_id]

        self.results[variant]['detections'].append({
            'founder_id': founder_id,
            'kpi': kpi,
            'result': anomaly_result,
            'feedback': founder_feedback,
            'timestamp': datetime.now()
        })

    def analyze_results(self, min_samples=100):
        """Analyze A/B test results."""
        if any(len(r['detections']) < min_samples for r in self.results.values()):
            return {'status': 'insufficient_data', 'message': 'Need more samples'}

        analysis = {}

        for variant, data in self.results.items():
            detections = data['detections']

            tp = sum(1 for d in detections if d['feedback'] == 'true_positive')
            fp = sum(1 for d in detections if d['feedback'] == 'false_positive')

            precision = tp / (tp + fp) if (tp + fp) > 0 else 0
            fpr = fp / len(detections)

            analysis[variant] = {
                'precision': precision,
                'false_positive_rate': fpr,
                'total_detections': len(detections),
                'true_positives': tp,
                'false_positives': fp
            }

        # Statistical significance test
        from scipy.stats import chi2_contingency

        contingency_table = [
            [analysis[v]['true_positives'], analysis[v]['false_positives']]
            for v in self.variants.keys()
        ]

        chi2, p_value, dof, expected = chi2_contingency(contingency_table)

        return {
            'status': 'complete',
            'results': analysis,
            'statistical_significance': {
                'chi2': chi2,
                'p_value': p_value,
                'is_significant': p_value < 0.05
            },
            'winner': max(analysis.items(), key=lambda x: x[1]['precision'])[0]
        }
```

---

## 6. Continuous Monitoring

### 6.1 Real-Time Metrics Dashboard

```python
class InsightsMonitoringDashboard:
    def __init__(self):
        self.metrics_history = []

    def log_metrics(self):
        """Collect current metrics snapshot."""
        snapshot = {
            'timestamp': datetime.now(),

            # Anomaly detection
            'anomaly_detections_today': self.count_detections_today(),
            'false_positive_rate_7d': self.calculate_fpr_last_7_days(),
            'avg_detection_confidence': self.get_avg_confidence(),

            # Trends
            'trends_analyzed_today': self.count_trends_today(),
            'significant_trends': self.count_significant_trends(),

            # Recommendations
            'recommendations_generated': self.count_recommendations_today(),
            'acceptance_rate_7d': self.get_recommendation_acceptance_rate(),

            # Briefings
            'briefings_sent_today': self.count_briefings_today(),
            'briefing_open_rate': self.get_briefing_open_rate(),
            'avg_engagement_time': self.get_avg_engagement_time(),

            # System
            'avg_latency_ms': self.get_avg_latency(),
            'error_count': self.get_error_count(),
            'cost_today': self.get_cost_today()
        }

        self.metrics_history.append(snapshot)
        return snapshot

    def alert_if_degraded(self, snapshot):
        """Check if metrics have degraded below thresholds."""
        alerts = []

        if snapshot['false_positive_rate_7d'] > 0.07:
            alerts.append({
                'severity': 'high',
                'message': f"FPR elevated: {snapshot['false_positive_rate_7d']:.1%}",
                'action': 'Review threshold settings'
            })

        if snapshot['acceptance_rate_7d'] < 0.70:
            alerts.append({
                'severity': 'medium',
                'message': f"Low recommendation acceptance: {snapshot['acceptance_rate_7d']:.1%}",
                'action': 'Review recommendation quality'
            })

        if snapshot['avg_latency_ms'] > 5000:
            alerts.append({
                'severity': 'medium',
                'message': f"High latency: {snapshot['avg_latency_ms']:.0f}ms",
                'action': 'Check Prophet model caching'
            })

        return alerts
```

### 6.2 Weekly Performance Report

```python
def generate_weekly_report():
    """Generate automated weekly performance report."""
    report = {
        'period': 'last_7_days',
        'generated_at': datetime.now(),

        'anomaly_detection': {
            'total_detections': get_detection_count(days=7),
            'precision': calculate_precision(days=7),
            'recall': calculate_recall(days=7),
            'f1_score': calculate_f1(days=7),
            'false_positive_rate': calculate_fpr(days=7),
            'comparison_to_previous_week': calculate_week_over_week_change()
        },

        'recommendations': {
            'total_generated': get_recommendation_count(days=7),
            'acceptance_rate': get_acceptance_rate(days=7),
            'avg_time_to_action': get_avg_time_to_action(days=7),
            'top_categories': get_top_categories(days=7)
        },

        'briefings': {
            'total_sent': get_briefing_count(days=7),
            'open_rate': get_open_rate(days=7),
            'engagement_rate': get_engagement_rate(days=7),
            'avg_read_time': get_avg_read_time(days=7)
        },

        'cost_analysis': {
            'total_cost': get_total_cost(days=7),
            'cost_per_founder': get_cost_per_founder(days=7),
            'cost_breakdown': get_cost_breakdown(days=7)
        },

        'top_insights': get_most_impactful_insights(days=7, limit=5)
    }

    return report
```

---

## 7. Validation Checklist

### 7.1 Pre-Deployment Validation

- [ ] **Unit Tests Pass:** All component tests pass
- [ ] **Synthetic Data:** F1 ≥85%, FPR <5% on synthetic dataset
- [ ] **Historical Data:** F1 ≥80% on labeled historical data
- [ ] **Cross-KPI Validation:** Consistent performance across all KPIs
- [ ] **Latency Test:** <5 seconds for full pipeline
- [ ] **Cost Estimate:** Within $15/month per founder budget
- [ ] **Edge Cases:** Handles missing data, cold start, outliers
- [ ] **Integration Test:** End-to-end pipeline runs without errors

### 7.2 Post-Deployment Validation

- [ ] **Week 1:** Monitor FPR daily, target <7%
- [ ] **Week 2:** Collect founder feedback on recommendations
- [ ] **Week 3:** Achieve ≥75% recommendation acceptance
- [ ] **Week 4:** Briefing engagement rate ≥70%
- [ ] **Month 1:** F1 ≥85%, FPR <5%, acceptance ≥80%

---

## 8. Success Metrics Summary

| Metric | MVP Target | Production Target | Measurement Frequency |
|--------|------------|-------------------|----------------------|
| Anomaly Detection F1 | ≥85% | ≥90% | Weekly |
| False Positive Rate | <5% | <3% | Daily |
| Trend Direction Accuracy | ≥85% | ≥90% | Weekly |
| Root Cause Accuracy | ≥70% | ≥75% | Monthly (requires manual validation) |
| Recommendation Acceptance | ≥75% | ≥80% | Weekly |
| Briefing Relevance Score | ≥85% | ≥90% | Weekly (survey) |
| System Latency | <5s | <2s | Real-time |
| Cost per Founder/Month | <$15 | <$10 | Daily |

---

## References

1. Fawcett, T. (2006). "An introduction to ROC analysis"
2. Kohavi, R., & Longbotham, R. (2017). "Online Controlled Experiments and A/B Testing"
3. Provost, F., & Fawcett, T. (2013). "Data Science for Business"
