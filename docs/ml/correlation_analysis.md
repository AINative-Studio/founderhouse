# Correlation Analysis for Multi-Metric KPIs

## Executive Summary

This document defines methods for detecting relationships between business KPIs, identifying leading/lagging indicators, inferring causal relationships, and performing root cause analysis. The goal is to provide founders with contextual insights beyond individual metric anomalies.

**Key Innovation:** Network-based correlation analysis that reveals hidden dependencies and enables predictive root cause identification.

---

## 1. Correlation Methods

### 1.1 Pearson Correlation (Linear Relationships)

```python
from scipy.stats import pearsonr

def calculate_pearson_correlation(kpi1, kpi2):
    """
    Calculate linear correlation between two KPIs.

    Returns:
        correlation coefficient (-1 to 1), p-value, strength
    """
    correlation, p_value = pearsonr(kpi1, kpi2)

    # Classify strength
    abs_corr = abs(correlation)
    if abs_corr < 0.3:
        strength = 'weak'
    elif abs_corr < 0.7:
        strength = 'moderate'
    else:
        strength = 'strong'

    direction = 'positive' if correlation > 0 else 'negative'

    return {
        'correlation': correlation,
        'p_value': p_value,
        'is_significant': p_value < 0.05,
        'strength': strength,
        'direction': direction,
        'explanation': f"{strength.capitalize()} {direction} correlation (r={correlation:.2f}, p={p_value:.4f})"
    }
```

**Use Cases:**
- CAC vs MRR (expect positive correlation)
- Churn Rate vs Customer Satisfaction (expect negative correlation)
- Marketing Spend vs Signups (expect positive correlation)

---

### 1.2 Spearman Correlation (Monotonic Relationships)

```python
from scipy.stats import spearmanr

def calculate_spearman_correlation(kpi1, kpi2):
    """
    Calculate rank-based correlation (robust to outliers and non-linear relationships).
    """
    correlation, p_value = spearmanr(kpi1, kpi2)

    return {
        'rho': correlation,
        'p_value': p_value,
        'is_significant': p_value < 0.05,
        'interpretation': 'monotonic' if abs(correlation) > 0.5 else 'weak_monotonic'
    }
```

**Advantages:**
- Robust to outliers
- Captures non-linear monotonic relationships
- Better for skewed distributions (churn, conversion rates)

---

### 1.3 Time-Lagged Correlation

```python
def calculate_lagged_correlation(leading_kpi, lagging_kpi, max_lag=14):
    """
    Find optimal time lag where leading KPI best predicts lagging KPI.

    Example: Marketing spend today → Signups in 3-7 days
    """
    correlations = []

    for lag in range(max_lag + 1):
        if lag > 0:
            lagged_series = lagging_kpi.shift(-lag)
        else:
            lagged_series = lagging_kpi

        # Remove NaN values
        mask = ~(leading_kpi.isna() | lagged_series.isna())
        if mask.sum() < 10:
            continue

        corr, p_value = pearsonr(leading_kpi[mask], lagged_series[mask])
        correlations.append({
            'lag': lag,
            'correlation': corr,
            'p_value': p_value
        })

    # Find best lag
    best = max(correlations, key=lambda x: abs(x['correlation']))

    return {
        'optimal_lag': best['lag'],
        'correlation_at_lag': best['correlation'],
        'p_value': best['p_value'],
        'all_lags': correlations,
        'explanation': f"Leading indicator with {best['lag']}-day lag (r={best['correlation']:.2f})"
    }
```

**Example Output:**
```python
# Marketing Spend → Signups
{
    'optimal_lag': 5,  # 5-day delay
    'correlation_at_lag': 0.78,
    'p_value': 0.001,
    'explanation': 'Leading indicator with 5-day lag (r=0.78)'
}
```

---

## 2. Granger Causality Testing

### 2.1 Detecting Causal Relationships

```python
from statsmodels.tsa.stattools import grangercausalitytests

def test_granger_causality(cause_series, effect_series, max_lag=7):
    """
    Test if one time series Granger-causes another.

    Interpretation: Does past values of X help predict Y beyond Y's own past?
    """
    # Prepare data
    data = pd.DataFrame({
        'effect': effect_series,
        'cause': cause_series
    }).dropna()

    # Run Granger causality test
    results = grangercausalitytests(data[['effect', 'cause']], max_lag, verbose=False)

    # Extract p-values for each lag
    p_values = []
    for lag in range(1, max_lag + 1):
        p_value = results[lag][0]['ssr_ftest'][1]  # F-test p-value
        p_values.append(p_value)

    # Overall causality assessment
    min_p = min(p_values)
    is_causal = min_p < 0.05
    best_lag = p_values.index(min_p) + 1

    return {
        'is_granger_causal': is_causal,
        'p_value': min_p,
        'best_lag': best_lag,
        'all_p_values': p_values,
        'explanation': f"{'Causal' if is_causal else 'No causal'} relationship detected (lag={best_lag}, p={min_p:.4f})"
    }
```

**Example:**
- Test if CAC changes Granger-cause churn rate changes
- Test if feature releases Granger-cause engagement changes

---

## 3. Network-Based Correlation Analysis

### 3.1 KPI Dependency Graph

```python
import networkx as nx

def build_kpi_correlation_network(kpi_data, significance_threshold=0.05, min_correlation=0.5):
    """
    Build a network graph of KPI dependencies.

    Nodes: KPIs
    Edges: Significant correlations
    Edge weights: Correlation strength
    """
    G = nx.DiGraph()
    kpi_names = kpi_data.columns

    # Add nodes
    for kpi in kpi_names:
        G.add_node(kpi)

    # Calculate pairwise correlations
    for i, kpi1 in enumerate(kpi_names):
        for kpi2 in kpi_names[i+1:]:
            # Pearson correlation
            corr_result = calculate_pearson_correlation(
                kpi_data[kpi1],
                kpi_data[kpi2]
            )

            if corr_result['is_significant'] and abs(corr_result['correlation']) >= min_correlation:
                # Test for Granger causality in both directions
                causality_1_to_2 = test_granger_causality(kpi_data[kpi1], kpi_data[kpi2])
                causality_2_to_1 = test_granger_causality(kpi_data[kpi2], kpi_data[kpi1])

                # Add directed edges based on causality
                if causality_1_to_2['is_granger_causal']:
                    G.add_edge(kpi1, kpi2,
                              weight=abs(corr_result['correlation']),
                              lag=causality_1_to_2['best_lag'],
                              correlation=corr_result['correlation'])

                if causality_2_to_1['is_granger_causal']:
                    G.add_edge(kpi2, kpi1,
                              weight=abs(corr_result['correlation']),
                              lag=causality_2_to_1['best_lag'],
                              correlation=corr_result['correlation'])

    return G

def identify_central_kpis(G):
    """
    Identify most influential KPIs using centrality metrics.
    """
    # PageRank: KPIs that influence many others
    pagerank = nx.pagerank(G)

    # Betweenness: KPIs that bridge different clusters
    betweenness = nx.betweenness_centrality(G)

    # Out-degree: KPIs that directly cause many others
    out_degree = dict(G.out_degree())

    return {
        'most_influential': max(pagerank, key=pagerank.get),
        'key_mediators': max(betweenness, key=betweenness.get),
        'primary_drivers': max(out_degree, key=out_degree.get),
        'pagerank_scores': pagerank,
        'betweenness_scores': betweenness
    }
```

**Example Network:**
```
Marketing Spend → CAC → LTV → Churn Rate
                     ↓
                  Signups → Conversion Rate → MRR
```

---

## 4. Root Cause Analysis

### 4.1 Anomaly Propagation Detection

```python
def detect_root_cause(anomaly_kpi, all_kpis, correlation_network, timestamp):
    """
    When an anomaly is detected, trace it back to potential root causes.

    Algorithm:
    1. Identify KPIs correlated with anomaly KPI
    2. Check which of those also have recent anomalies
    3. Use causal graph to determine propagation direction
    4. Rank root causes by influence and timing
    """
    G = correlation_network

    # Get all KPIs that influence the anomaly KPI (incoming edges)
    potential_causes = list(G.predecessors(anomaly_kpi))

    root_causes = []
    for cause_kpi in potential_causes:
        # Get edge attributes
        edge_data = G.get_edge_data(cause_kpi, anomaly_kpi)
        lag = edge_data['lag']
        correlation = edge_data['correlation']

        # Check if cause KPI had an anomaly around the expected lag time
        cause_history = all_kpis[cause_kpi]
        lagged_timestamp = timestamp - pd.Timedelta(days=lag)

        # Check for anomaly in cause KPI at lagged time
        cause_window = cause_history[lagged_timestamp - pd.Timedelta(days=2):
                                     lagged_timestamp + pd.Timedelta(days=2)]

        if len(cause_window) > 0:
            cause_anomaly_score = calculate_anomaly_score(cause_window)

            if cause_anomaly_score > 0.5:  # Threshold for considering it an anomaly
                root_causes.append({
                    'kpi': cause_kpi,
                    'lag': lag,
                    'correlation': correlation,
                    'anomaly_score': cause_anomaly_score,
                    'confidence': abs(correlation) * cause_anomaly_score,
                    'explanation': f"{cause_kpi} anomaly {lag} days ago (correlation: {correlation:.2f})"
                })

    # Rank by confidence
    root_causes.sort(key=lambda x: x['confidence'], reverse=True)

    return {
        'primary_cause': root_causes[0] if root_causes else None,
        'all_causes': root_causes,
        'explanation': generate_root_cause_explanation(anomaly_kpi, root_causes)
    }

def generate_root_cause_explanation(anomaly_kpi, root_causes):
    """
    Generate natural language root cause analysis.
    """
    if not root_causes:
        return f"{anomaly_kpi} anomaly detected, but no clear root cause identified."

    primary = root_causes[0]
    explanation = f"🔍 {anomaly_kpi} anomaly likely caused by {primary['kpi']} change {primary['lag']} days ago"

    if len(root_causes) > 1:
        secondary = root_causes[1]
        explanation += f" (also influenced by {secondary['kpi']})"

    return explanation
```

**Example:**
```
Anomaly detected: MRR down 15%
Root cause analysis:
  1. Churn Rate spike 7 days ago (correlation: -0.82, confidence: 0.91)
  2. Customer Satisfaction drop 14 days ago (correlation: 0.65, confidence: 0.73)

Explanation: "MRR anomaly likely caused by Churn Rate change 7 days ago (also influenced by Customer Satisfaction)"
```

---

## 5. Multi-Metric Correlation Patterns

### 5.1 Pattern Library

```python
CORRELATION_PATTERNS = {
    'healthy_growth': {
        'conditions': [
            ('mrr', 'increase'),
            ('cac', 'decrease'),
            ('ltv', 'increase'),
            ('churn_rate', 'decrease')
        ],
        'message': '✅ Healthy growth pattern: Efficient customer acquisition with strong retention',
        'severity': 'positive'
    },
    'inefficient_growth': {
        'conditions': [
            ('mrr', 'increase'),
            ('cac', 'increase'),
            ('burn_rate', 'increase')
        ],
        'message': '⚠️ Growth at high cost: Revenue increasing but unit economics deteriorating',
        'severity': 'warning'
    },
    'churn_crisis': {
        'conditions': [
            ('churn_rate', 'spike'),
            ('customer_satisfaction', 'decrease'),
            ('support_tickets', 'increase')
        ],
        'message': '🚨 Churn crisis: Multiple retention indicators declining',
        'severity': 'critical'
    },
    'product_market_fit': {
        'conditions': [
            ('conversion_rate', 'increase'),
            ('engagement', 'increase'),
            ('word_of_mouth', 'increase'),
            ('cac', 'decrease')
        ],
        'message': '🎯 Strong product-market fit signals detected',
        'severity': 'positive'
    }
}

def detect_correlation_patterns(current_kpis, historical_kpis):
    """
    Detect pre-defined multi-metric patterns.
    """
    detected_patterns = []

    for pattern_name, pattern_config in CORRELATION_PATTERNS.items():
        conditions_met = []

        for kpi_name, expected_direction in pattern_config['conditions']:
            if kpi_name in current_kpis:
                actual_direction = determine_kpi_direction(kpi_name, current_kpis, historical_kpis)
                matches = (actual_direction == expected_direction)
                conditions_met.append(matches)

        # Pattern detected if majority of conditions met
        if sum(conditions_met) >= len(conditions_met) * 0.75:
            detected_patterns.append({
                'pattern': pattern_name,
                'message': pattern_config['message'],
                'severity': pattern_config['severity'],
                'conditions_met': sum(conditions_met),
                'conditions_total': len(conditions_met)
            })

    return detected_patterns
```

---

## 6. Cross-Metric Anomaly Detection

### 6.1 Multivariate Anomaly Detection

```python
from sklearn.ensemble import IsolationForest

def detect_multivariate_anomalies(kpi_data, contamination=0.05):
    """
    Detect anomalies considering multiple KPIs simultaneously.

    Example: CAC increased 10% might be normal, but CAC up 10% + LTV down 8% is anomalous.
    """
    # Prepare feature matrix
    feature_matrix = kpi_data.values

    # Fit Isolation Forest
    model = IsolationForest(
        contamination=contamination,
        n_estimators=100,
        random_state=42
    )
    model.fit(feature_matrix)

    # Detect anomalies
    predictions = model.predict(feature_matrix)
    anomaly_scores = model.decision_function(feature_matrix)

    # Identify anomalous time periods
    anomalous_indices = np.where(predictions == -1)[0]

    # For each anomaly, identify which KPI combinations are unusual
    anomaly_explanations = []
    for idx in anomalous_indices:
        # Calculate contribution of each KPI to the anomaly
        contributions = calculate_feature_contributions(model, feature_matrix[idx])

        top_contributors = sorted(
            contributions.items(),
            key=lambda x: abs(x[1]),
            reverse=True
        )[:3]

        anomaly_explanations.append({
            'timestamp': kpi_data.index[idx],
            'anomaly_score': anomaly_scores[idx],
            'top_contributors': top_contributors,
            'explanation': f"Multivariate anomaly driven by {', '.join([k for k, v in top_contributors])}"
        })

    return anomaly_explanations

def calculate_feature_contributions(model, instance):
    """
    Calculate each feature's contribution to anomaly score.
    """
    # Use SHAP or simple perturbation analysis
    contributions = {}
    base_score = model.decision_function([instance])[0]

    for i, feature in enumerate(instance):
        # Perturb feature
        perturbed = instance.copy()
        perturbed[i] = np.median(model.estimators_[0].X_[:, i])  # Replace with median
        perturbed_score = model.decision_function([perturbed])[0]

        contributions[f'feature_{i}'] = base_score - perturbed_score

    return contributions
```

---

## 7. Leading/Lagging Indicator Identification

### 7.1 Automatic Discovery

```python
def identify_leading_indicators(target_kpi, all_kpis, max_lag=14):
    """
    Automatically discover which KPIs are leading indicators for target KPI.
    """
    leading_indicators = []

    for candidate_kpi in all_kpis.columns:
        if candidate_kpi == target_kpi:
            continue

        # Test time-lagged correlation
        lag_result = calculate_lagged_correlation(
            all_kpis[candidate_kpi],
            all_kpis[target_kpi],
            max_lag=max_lag
        )

        # Test Granger causality
        causality_result = test_granger_causality(
            all_kpis[candidate_kpi],
            all_kpis[target_kpi],
            max_lag=max_lag
        )

        # Combine results
        if (lag_result['correlation_at_lag'] > 0.5 and
            lag_result['p_value'] < 0.05 and
            causality_result['is_granger_causal']):

            leading_indicators.append({
                'indicator': candidate_kpi,
                'lag': lag_result['optimal_lag'],
                'correlation': lag_result['correlation_at_lag'],
                'p_value': causality_result['p_value'],
                'predictive_power': abs(lag_result['correlation_at_lag']) * (1 - causality_result['p_value'])
            })

    # Rank by predictive power
    leading_indicators.sort(key=lambda x: x['predictive_power'], reverse=True)

    return leading_indicators
```

**Example Output:**
```python
# Leading indicators for MRR:
[
    {'indicator': 'signups', 'lag': 7, 'correlation': 0.82, 'predictive_power': 0.79},
    {'indicator': 'trial_starts', 'lag': 14, 'correlation': 0.75, 'predictive_power': 0.71},
    {'indicator': 'engagement_score', 'lag': 3, 'correlation': 0.68, 'predictive_power': 0.65}
]
```

---

## 8. Recommendation: Correlation Analysis Pipeline

### MVP Implementation

```python
class CorrelationAnalysisEngine:
    def __init__(self, kpi_data):
        self.kpi_data = kpi_data
        self.correlation_network = None
        self.leading_indicators = {}

    def initialize(self):
        """Build correlation network and identify leading indicators."""
        self.correlation_network = build_kpi_correlation_network(self.kpi_data)

        for kpi in self.kpi_data.columns:
            self.leading_indicators[kpi] = identify_leading_indicators(kpi, self.kpi_data)

    def analyze_anomaly(self, anomaly_kpi, timestamp):
        """Comprehensive analysis when anomaly detected."""
        return {
            'root_cause': detect_root_cause(anomaly_kpi, self.kpi_data, self.correlation_network, timestamp),
            'correlation_patterns': detect_correlation_patterns(self.kpi_data.loc[timestamp], self.kpi_data),
            'multivariate_context': detect_multivariate_anomalies(self.kpi_data.loc[timestamp-pd.Timedelta(days=7):timestamp])
        }

    def get_predictive_insights(self, target_kpi):
        """Get leading indicators for proactive monitoring."""
        return self.leading_indicators.get(target_kpi, [])
```

---

## 9. Implementation Roadmap

**Week 1-2:** Pearson/Spearman correlations, time-lagged analysis
**Week 3:** Granger causality testing, network graph construction
**Week 4:** Root cause analysis, pattern detection
**Week 5+:** Multivariate anomaly detection, SHAP explanations

---

## 10. Success Metrics

- **Root Cause Accuracy:** ≥75% of detected root causes validated by founders
- **Leading Indicator Precision:** ≥80% of predicted anomalies materialize
- **Pattern Detection Recall:** ≥85% of known business patterns detected
- **Explanation Quality:** ≥90% founder satisfaction with correlation insights

---

## References

1. Granger, C. W. J. (1969). "Investigating Causal Relations by Econometric Models"
2. Pearl, J. (2009). "Causality: Models, Reasoning, and Inference"
3. Newman, M. E. J. (2010). "Networks: An Introduction"
