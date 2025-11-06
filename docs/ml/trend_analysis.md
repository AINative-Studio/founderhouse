# Trend Analysis for Business KPIs

## Executive Summary

This document defines comprehensive trend detection algorithms for the AI Chief of Staff's Insights Engine. We provide methods for identifying short-term (WoW), medium-term (MoM), and long-term (QoQ, YoY) trends with statistical significance testing, direction classification, trend strength scoring, and acceleration detection.

**Key Innovation:** Multi-timescale trend analysis with confidence scores and natural language explanations for founder briefings.

---

## 1. Trend Analysis Framework

### 1.1 Trend Types

| Trend Type | Timeframe | Use Case | Update Frequency |
|------------|-----------|----------|------------------|
| Short-term (WoW) | 7 days | Tactical decisions, immediate response | Daily |
| Medium-term (MoM) | 30 days | Strategic adjustments, planning | Weekly |
| Long-term (QoQ) | 90 days | Board reporting, investor updates | Monthly |
| Annual (YoY) | 365 days | Yearly performance, fundraising | Quarterly |
| Custom | Variable | Campaign analysis, experiments | On-demand |

### 1.2 Trend Properties

Each trend analysis provides:

```python
TrendResult = {
    'direction': str,  # 'up', 'down', 'flat', 'volatile'
    'magnitude': float,  # Percentage change
    'strength': float,  # Confidence score 0-1
    'significance': float,  # P-value
    'is_significant': bool,  # p < 0.05
    'acceleration': str,  # 'accelerating', 'decelerating', 'steady'
    'volatility': float,  # Standard deviation
    'explanation': str,  # Natural language summary
    'visual_indicator': str  # '📈', '📉', '➡️', '📊'
}
```

---

## 2. Short-Term Trends (Week-over-Week)

### 2.1 Simple Percentage Change

**Algorithm:**
```python
def calculate_wow_change(current_week, previous_week):
    """
    Calculate simple week-over-week percentage change.

    Args:
        current_week: Average value for current week (last 7 days)
        previous_week: Average value for previous week (7-14 days ago)

    Returns:
        Percentage change (e.g., 0.15 = 15% increase)
    """
    if previous_week == 0:
        return float('inf') if current_week > 0 else 0

    change = (current_week - previous_week) / previous_week
    return change

def classify_wow_trend(change, threshold=0.05):
    """
    Classify trend direction with threshold for 'flat'.

    Args:
        change: Percentage change
        threshold: Minimum change to consider significant (default 5%)

    Returns:
        'up', 'down', or 'flat'
    """
    if abs(change) < threshold:
        return 'flat'
    elif change > 0:
        return 'up'
    else:
        return 'down'
```

**Example:**
```python
# MRR trend
current_week_mrr = 45000  # Average daily MRR this week
previous_week_mrr = 42000

change = calculate_wow_change(current_week_mrr, previous_week_mrr)
# change = 0.0714 (7.14% increase)

direction = classify_wow_trend(change)
# direction = 'up'

explanation = f"MRR is trending {direction} by {abs(change)*100:.1f}% WoW"
# "MRR is trending up by 7.1% WoW"
```

**Strengths:**
- Simple, fast, interpretable
- Good for stable metrics

**Weaknesses:**
- Sensitive to single-day outliers
- No statistical significance test
- Doesn't account for seasonality

---

### 2.2 Rolling Average with Significance Testing

**Algorithm:**
```python
from scipy import stats

def calculate_wow_trend_with_significance(data, window=7):
    """
    Calculate WoW trend with statistical significance testing.

    Args:
        data: Pandas Series with datetime index
        window: Rolling window size (default 7 days)

    Returns:
        Dictionary with trend metrics and significance
    """
    # Split data into current and previous week
    current_week = data.tail(window)
    previous_week = data.iloc[-2*window:-window]

    # Calculate means
    current_mean = current_week.mean()
    previous_mean = previous_week.mean()

    # Percentage change
    if previous_mean != 0:
        pct_change = (current_mean - previous_mean) / previous_mean
    else:
        pct_change = 0

    # Statistical significance (two-sample t-test)
    t_stat, p_value = stats.ttest_ind(current_week, previous_week)

    # Trend strength (effect size - Cohen's d)
    pooled_std = np.sqrt(
        (current_week.std()**2 + previous_week.std()**2) / 2
    )
    cohens_d = (current_mean - previous_mean) / pooled_std if pooled_std > 0 else 0

    # Direction classification
    if abs(pct_change) < 0.05 or p_value > 0.05:
        direction = 'flat'
    elif pct_change > 0:
        direction = 'up'
    else:
        direction = 'down'

    # Strength interpretation
    strength_label = classify_effect_size(abs(cohens_d))

    return {
        'direction': direction,
        'magnitude': pct_change,
        'current_value': current_mean,
        'previous_value': previous_mean,
        'p_value': p_value,
        'is_significant': p_value < 0.05,
        'effect_size': cohens_d,
        'strength': strength_label,
        'explanation': generate_explanation(
            direction, pct_change, p_value, strength_label
        )
    }

def classify_effect_size(cohens_d):
    """
    Classify Cohen's d effect size.

    Reference: Cohen, J. (1988). Statistical Power Analysis
    """
    abs_d = abs(cohens_d)
    if abs_d < 0.2:
        return 'negligible'
    elif abs_d < 0.5:
        return 'small'
    elif abs_d < 0.8:
        return 'medium'
    else:
        return 'large'

def generate_explanation(direction, pct_change, p_value, strength):
    """
    Generate natural language explanation.
    """
    if direction == 'flat':
        return "No significant trend detected"

    direction_word = "up" if direction == 'up' else "down"
    magnitude = abs(pct_change) * 100

    if p_value < 0.001:
        confidence = "highly significant"
    elif p_value < 0.01:
        confidence = "very significant"
    elif p_value < 0.05:
        confidence = "significant"
    else:
        confidence = "not statistically significant"

    return f"Trending {direction_word} by {magnitude:.1f}% ({strength} effect, {confidence})"
```

**Example Output:**
```python
{
    'direction': 'up',
    'magnitude': 0.071,
    'current_value': 45000,
    'previous_value': 42000,
    'p_value': 0.023,
    'is_significant': True,
    'effect_size': 0.65,
    'strength': 'medium',
    'explanation': 'Trending up by 7.1% (medium effect, significant)'
}
```

**Benefits:**
- Statistical rigor
- Avoids false trends from noise
- Quantifies trend strength

---

### 2.3 Mann-Kendall Trend Test (Non-Parametric)

**Algorithm:**
```python
from scipy.stats import kendalltau

def mann_kendall_test(data):
    """
    Non-parametric trend test (doesn't assume normality).

    Args:
        data: Time series data

    Returns:
        Trend direction and significance
    """
    n = len(data)
    time_index = np.arange(n)

    # Calculate Kendall's tau correlation with time
    tau, p_value = kendalltau(time_index, data)

    # Determine trend
    if p_value > 0.05:
        trend = 'no_trend'
    elif tau > 0:
        trend = 'increasing'
    else:
        trend = 'decreasing'

    return {
        'trend': trend,
        'tau': tau,
        'p_value': p_value,
        'is_significant': p_value < 0.05,
        'explanation': f"{'Significant' if p_value < 0.05 else 'No significant'} {trend} trend (τ={tau:.3f}, p={p_value:.4f})"
    }
```

**Use Case:**
- When data is not normally distributed (e.g., churn rate, conversion rate)
- Presence of outliers
- Small sample sizes

**Benefits:**
- Robust to outliers
- No distribution assumptions
- Reliable for skewed data

---

## 3. Medium-Term Trends (Month-over-Month)

### 3.1 Linear Regression Trend

**Algorithm:**
```python
from sklearn.linear_model import LinearRegression

def calculate_mom_trend_regression(data, window=30):
    """
    Calculate MoM trend using linear regression.

    Args:
        data: Pandas Series with datetime index
        window: Window size (default 30 days)

    Returns:
        Trend slope, R-squared, and prediction
    """
    # Extract current month's data
    current_month = data.tail(window)

    # Prepare features (days since start)
    X = np.arange(len(current_month)).reshape(-1, 1)
    y = current_month.values

    # Fit linear regression
    model = LinearRegression()
    model.fit(X, y)

    slope = model.coef_[0]
    r_squared = model.score(X, y)

    # Calculate trend metrics
    start_value = current_month.iloc[0]
    end_value = current_month.iloc[-1]
    predicted_end = model.predict([[len(current_month)-1]])[0]

    # Percentage change over the month
    pct_change = (end_value - start_value) / start_value if start_value != 0 else 0

    # Trend direction
    if abs(slope) < start_value * 0.01 / window:  # Less than 1% change over period
        direction = 'flat'
    elif slope > 0:
        direction = 'increasing'
    else:
        direction = 'decreasing'

    # Trend quality (how linear is the trend?)
    if r_squared > 0.8:
        trend_quality = 'strong'
    elif r_squared > 0.5:
        trend_quality = 'moderate'
    else:
        trend_quality = 'weak'

    return {
        'direction': direction,
        'slope': slope,
        'pct_change': pct_change,
        'r_squared': r_squared,
        'trend_quality': trend_quality,
        'start_value': start_value,
        'end_value': end_value,
        'predicted_next': predicted_end + slope,  # Next day prediction
        'explanation': f"{direction.capitalize()} trend ({trend_quality} linearity, R²={r_squared:.2f})"
    }
```

**Example:**
```python
# Active users MoM trend
trend = calculate_mom_trend_regression(active_users_data, window=30)

# Output:
{
    'direction': 'increasing',
    'slope': 42.3,  # +42 users per day
    'pct_change': 0.28,  # 28% growth over the month
    'r_squared': 0.85,
    'trend_quality': 'strong',
    'start_value': 4500,
    'end_value': 5800,
    'predicted_next': 5842,
    'explanation': 'Increasing trend (strong linearity, R²=0.85)'
}
```

**Benefits:**
- Quantifies rate of change
- Provides predictions
- R² indicates trend reliability

---

### 3.2 Moving Average Crossover

**Algorithm:**
```python
def calculate_moving_average_crossover(data, short_window=7, long_window=30):
    """
    Detect trend changes using moving average crossover.

    Args:
        data: Time series data
        short_window: Short-term MA window (default 7 days)
        long_window: Long-term MA window (default 30 days)

    Returns:
        Trend direction and crossover signals
    """
    # Calculate moving averages
    short_ma = data.rolling(window=short_window).mean()
    long_ma = data.rolling(window=long_window).mean()

    # Current values
    current_short = short_ma.iloc[-1]
    current_long = long_ma.iloc[-1]

    # Previous values (to detect crossover)
    prev_short = short_ma.iloc[-2]
    prev_long = long_ma.iloc[-2]

    # Determine trend
    if current_short > current_long:
        trend = 'bullish'  # Short-term above long-term
    elif current_short < current_long:
        trend = 'bearish'
    else:
        trend = 'neutral'

    # Detect crossover (trend reversal signal)
    crossover = None
    if prev_short <= prev_long and current_short > current_long:
        crossover = 'golden_cross'  # Bullish signal
    elif prev_short >= prev_long and current_short < current_long:
        crossover = 'death_cross'  # Bearish signal

    # Calculate divergence (how far apart are the MAs?)
    divergence = abs(current_short - current_long) / current_long if current_long != 0 else 0

    # Trend strength
    if divergence > 0.10:
        strength = 'strong'
    elif divergence > 0.05:
        strength = 'moderate'
    else:
        strength = 'weak'

    return {
        'trend': trend,
        'crossover': crossover,
        'divergence': divergence,
        'strength': strength,
        'short_ma': current_short,
        'long_ma': current_long,
        'explanation': generate_ma_explanation(trend, crossover, strength)
    }

def generate_ma_explanation(trend, crossover, strength):
    if crossover == 'golden_cross':
        return f"⚠️ Bullish reversal detected - {strength} upward momentum"
    elif crossover == 'death_cross':
        return f"⚠️ Bearish reversal detected - {strength} downward momentum"
    else:
        return f"{trend.capitalize()} trend ({strength} momentum)"
```

**Use Case:**
- Detecting trend reversals
- Momentum indicators
- Trading-style analysis (borrowed from finance)

**Benefits:**
- Early warning of trend changes
- Visual interpretability
- Captures momentum shifts

---

## 4. Long-Term Trends (Quarter-over-Quarter)

### 4.1 Quarterly Growth Rate

**Algorithm:**
```python
def calculate_qoq_trend(data, quarters_back=2):
    """
    Calculate quarter-over-quarter growth trends.

    Args:
        data: Time series data with datetime index
        quarters_back: Number of quarters to analyze

    Returns:
        QoQ growth rates and trend trajectory
    """
    # Define quarter boundaries
    current_date = data.index[-1]
    quarters = []

    for i in range(quarters_back + 1):
        quarter_end = current_date - pd.DateOffset(months=3*i)
        quarter_start = quarter_end - pd.DateOffset(months=3)
        quarters.append((quarter_start, quarter_end))

    # Calculate quarterly means
    quarterly_means = []
    for start, end in quarters:
        quarter_data = data[start:end]
        if len(quarter_data) > 0:
            quarterly_means.append(quarter_data.mean())
        else:
            quarterly_means.append(None)

    quarterly_means.reverse()  # Chronological order

    # Calculate QoQ growth rates
    growth_rates = []
    for i in range(1, len(quarterly_means)):
        if quarterly_means[i-1] and quarterly_means[i]:
            growth = (quarterly_means[i] - quarterly_means[i-1]) / quarterly_means[i-1]
            growth_rates.append(growth)

    # Determine trajectory
    if len(growth_rates) >= 2:
        if all(g > 0 for g in growth_rates):
            trajectory = 'accelerating_growth'
        elif all(g < 0 for g in growth_rates):
            trajectory = 'accelerating_decline'
        elif growth_rates[-1] > growth_rates[-2]:
            trajectory = 'improving'
        elif growth_rates[-1] < growth_rates[-2]:
            trajectory = 'deteriorating'
        else:
            trajectory = 'stable'
    else:
        trajectory = 'insufficient_data'

    # Calculate CAGR (Compound Annual Growth Rate)
    if quarterly_means[0] and quarterly_means[-1]:
        periods = len(quarterly_means) - 1
        cagr = (quarterly_means[-1] / quarterly_means[0]) ** (4/periods) - 1  # Annualized
    else:
        cagr = None

    return {
        'quarterly_values': quarterly_means,
        'growth_rates': growth_rates,
        'latest_qoq': growth_rates[-1] if growth_rates else None,
        'trajectory': trajectory,
        'cagr': cagr,
        'explanation': generate_qoq_explanation(growth_rates, trajectory, cagr)
    }

def generate_qoq_explanation(growth_rates, trajectory, cagr):
    if not growth_rates:
        return "Insufficient quarterly data for trend analysis"

    latest_growth = growth_rates[-1] * 100

    if trajectory == 'accelerating_growth':
        return f"📈 Strong upward trajectory: {latest_growth:.1f}% QoQ growth (accelerating)"
    elif trajectory == 'accelerating_decline':
        return f"📉 Concerning downward trajectory: {latest_growth:.1f}% QoQ decline (accelerating)"
    elif trajectory == 'improving':
        return f"✅ Improving trend: {latest_growth:.1f}% QoQ (up from previous quarter)"
    elif trajectory == 'deteriorating':
        return f"⚠️ Deteriorating trend: {latest_growth:.1f}% QoQ (down from previous quarter)"
    else:
        return f"Stable growth pattern: {latest_growth:.1f}% QoQ"
```

**Example:**
```python
# MRR QoQ analysis
qoq = calculate_qoq_trend(mrr_data, quarters_back=3)

# Output:
{
    'quarterly_values': [120000, 145000, 178000, 215000],
    'growth_rates': [0.208, 0.228, 0.208],
    'latest_qoq': 0.208,
    'trajectory': 'accelerating_growth',
    'cagr': 0.79,  # 79% annualized growth
    'explanation': '📈 Strong upward trajectory: 20.8% QoQ growth (accelerating)'
}
```

---

### 4.2 Seasonal Decomposition for Long-Term Trends

**Algorithm:**
```python
from statsmodels.tsa.seasonal import seasonal_decompose

def analyze_long_term_trend_with_seasonality(data, period=7):
    """
    Decompose time series into trend, seasonal, and residual components.

    Args:
        data: Time series data (minimum 2 seasonal periods)
        period: Seasonal period (7 for weekly, 30 for monthly)

    Returns:
        Decomposed components and trend analysis
    """
    # Perform seasonal decomposition
    decomposition = seasonal_decompose(
        data,
        model='additive',  # or 'multiplicative'
        period=period,
        extrapolate_trend='freq'
    )

    trend = decomposition.trend
    seasonal = decomposition.seasonal
    residual = decomposition.resid

    # Analyze trend component
    trend_clean = trend.dropna()

    # Fit linear regression to trend
    X = np.arange(len(trend_clean)).reshape(-1, 1)
    y = trend_clean.values

    model = LinearRegression()
    model.fit(X, y)

    slope = model.coef_[0]
    r_squared = model.score(X, y)

    # Calculate trend direction
    if abs(slope) < trend_clean.mean() * 0.001:
        direction = 'flat'
    elif slope > 0:
        direction = 'increasing'
    else:
        direction = 'decreasing'

    # Seasonal strength
    seasonal_strength = np.var(seasonal.dropna()) / np.var(data.dropna())

    return {
        'trend_direction': direction,
        'trend_slope': slope,
        'trend_r_squared': r_squared,
        'seasonal_strength': seasonal_strength,
        'has_strong_seasonality': seasonal_strength > 0.2,
        'residual_volatility': np.std(residual.dropna()),
        'trend_values': trend,
        'seasonal_values': seasonal,
        'explanation': f"{direction.capitalize()} long-term trend (R²={r_squared:.2f}, seasonal strength={seasonal_strength:.2f})"
    }
```

**Benefits:**
- Separates underlying trend from seasonal noise
- Identifies true growth trajectory
- Useful for forecasting

---

## 5. Acceleration Detection

### 5.1 Second Derivative (Rate of Change of Change)

**Algorithm:**
```python
def detect_acceleration(data, window=7):
    """
    Detect if trend is accelerating or decelerating.

    Concept: Acceleration is the derivative of velocity (rate of change).

    Args:
        data: Time series data
        window: Window for calculating rates of change

    Returns:
        Acceleration metrics
    """
    # Calculate first derivative (velocity)
    velocity = data.diff(window)

    # Calculate second derivative (acceleration)
    acceleration = velocity.diff(window)

    # Current values
    current_acceleration = acceleration.iloc[-1]
    current_velocity = velocity.iloc[-1]

    # Classify acceleration
    acc_threshold = data.std() * 0.05  # 5% of standard deviation

    if abs(current_acceleration) < acc_threshold:
        acc_status = 'steady'
    elif current_acceleration > 0:
        acc_status = 'accelerating'
    else:
        acc_status = 'decelerating'

    # Determine overall trajectory
    if current_velocity > 0 and acc_status == 'accelerating':
        trajectory = 'rapid_growth'
    elif current_velocity > 0 and acc_status == 'decelerating':
        trajectory = 'slowing_growth'
    elif current_velocity < 0 and acc_status == 'accelerating':
        trajectory = 'rapid_decline'
    elif current_velocity < 0 and acc_status == 'decelerating':
        trajectory = 'recovery'
    else:
        trajectory = 'steady'

    return {
        'acceleration': current_acceleration,
        'velocity': current_velocity,
        'status': acc_status,
        'trajectory': trajectory,
        'explanation': generate_acceleration_explanation(trajectory, current_velocity, current_acceleration)
    }

def generate_acceleration_explanation(trajectory, velocity, acceleration):
    trajectories = {
        'rapid_growth': '🚀 Accelerating growth - momentum building',
        'slowing_growth': '⚠️ Growth slowing down - momentum decreasing',
        'rapid_decline': '⛔ Accelerating decline - urgent attention needed',
        'recovery': '✅ Decline slowing - signs of recovery',
        'steady': '➡️ Steady trajectory - no acceleration'
    }
    return trajectories.get(trajectory, 'Steady state')
```

**Example:**
```python
# Detect if user growth is accelerating
acc = detect_acceleration(active_users_data)

# Output:
{
    'acceleration': 15.2,
    'velocity': 42.3,
    'status': 'accelerating',
    'trajectory': 'rapid_growth',
    'explanation': '🚀 Accelerating growth - momentum building'
}
```

**Use Case:**
- Detect inflection points
- Early warning of trend reversals
- Momentum-based alerts

---

### 5.2 Growth Rate Momentum

**Algorithm:**
```python
def calculate_growth_momentum(data, short_window=7, long_window=30):
    """
    Calculate momentum by comparing short-term vs long-term growth rates.

    Args:
        data: Time series data
        short_window: Short-term window (default 7 days)
        long_window: Long-term window (default 30 days)

    Returns:
        Momentum metrics
    """
    # Calculate growth rates
    short_term_growth = (data.iloc[-1] - data.iloc[-short_window]) / data.iloc[-short_window]
    long_term_growth = (data.iloc[-1] - data.iloc[-long_window]) / data.iloc[-long_window]

    # Annualize growth rates for comparison
    short_term_annualized = (1 + short_term_growth) ** (365 / short_window) - 1
    long_term_annualized = (1 + long_term_growth) ** (365 / long_window) - 1

    # Momentum score
    momentum = short_term_annualized - long_term_annualized

    # Classification
    if abs(momentum) < 0.05:
        momentum_status = 'stable'
    elif momentum > 0.2:
        momentum_status = 'strong_positive'
    elif momentum > 0:
        momentum_status = 'positive'
    elif momentum < -0.2:
        momentum_status = 'strong_negative'
    else:
        momentum_status = 'negative'

    return {
        'short_term_growth': short_term_growth,
        'long_term_growth': long_term_growth,
        'short_term_annualized': short_term_annualized,
        'long_term_annualized': long_term_annualized,
        'momentum': momentum,
        'status': momentum_status,
        'explanation': f"{'Positive' if momentum > 0 else 'Negative'} momentum ({momentum*100:.1f}% difference in growth rates)"
    }
```

---

## 6. Volatility and Trend Stability

### 6.1 Volatility Metrics

**Algorithm:**
```python
def calculate_trend_volatility(data, window=30):
    """
    Calculate volatility metrics for trend stability assessment.

    Args:
        data: Time series data
        window: Window for volatility calculation

    Returns:
        Volatility metrics
    """
    recent_data = data.tail(window)

    # Standard deviation
    volatility = recent_data.std()

    # Coefficient of variation (normalized volatility)
    mean = recent_data.mean()
    cv = volatility / mean if mean != 0 else 0

    # Average True Range (ATR) - from finance
    high_low = recent_data.max() - recent_data.min()
    atr = high_low / window

    # Classify volatility
    if cv < 0.05:
        vol_level = 'very_low'
    elif cv < 0.15:
        vol_level = 'low'
    elif cv < 0.30:
        vol_level = 'moderate'
    elif cv < 0.50:
        vol_level = 'high'
    else:
        vol_level = 'very_high'

    # Trend reliability
    if vol_level in ['very_low', 'low']:
        reliability = 'high'
    elif vol_level == 'moderate':
        reliability = 'medium'
    else:
        reliability = 'low'

    return {
        'volatility': volatility,
        'coefficient_of_variation': cv,
        'atr': atr,
        'level': vol_level,
        'trend_reliability': reliability,
        'explanation': f"{vol_level.replace('_', ' ').capitalize()} volatility ({reliability} trend reliability)"
    }
```

---

## 7. Comprehensive Trend Summary

### 7.1 Multi-Timescale Trend Aggregation

**Algorithm:**
```python
def generate_comprehensive_trend_report(kpi_name, data):
    """
    Generate full trend analysis across all timescales.

    Args:
        kpi_name: Name of the KPI
        data: Time series data (minimum 90 days recommended)

    Returns:
        Comprehensive trend report
    """
    report = {
        'kpi_name': kpi_name,
        'analysis_date': datetime.now(),
        'data_points': len(data),
        'date_range': (data.index[0], data.index[-1])
    }

    # Short-term (WoW)
    if len(data) >= 14:
        report['wow'] = calculate_wow_trend_with_significance(data)

    # Medium-term (MoM)
    if len(data) >= 60:
        report['mom'] = calculate_mom_trend_regression(data, window=30)
        report['ma_crossover'] = calculate_moving_average_crossover(data)

    # Long-term (QoQ)
    if len(data) >= 180:
        report['qoq'] = calculate_qoq_trend(data, quarters_back=2)

    # Acceleration
    if len(data) >= 21:
        report['acceleration'] = detect_acceleration(data, window=7)

    # Volatility
    if len(data) >= 30:
        report['volatility'] = calculate_trend_volatility(data, window=30)

    # Overall assessment
    report['summary'] = generate_overall_summary(report)

    return report

def generate_overall_summary(report):
    """
    Synthesize multi-timescale trends into coherent summary.
    """
    summaries = []

    # Short-term
    if 'wow' in report and report['wow']['is_significant']:
        summaries.append(f"WoW: {report['wow']['explanation']}")

    # Medium-term
    if 'mom' in report:
        summaries.append(f"MoM: {report['mom']['explanation']}")

    # Long-term
    if 'qoq' in report and report['qoq']['latest_qoq']:
        summaries.append(f"QoQ: {report['qoq']['explanation']}")

    # Acceleration
    if 'acceleration' in report and report['acceleration']['status'] != 'steady':
        summaries.append(f"Momentum: {report['acceleration']['explanation']}")

    # Volatility warning
    if 'volatility' in report and report['volatility']['trend_reliability'] == 'low':
        summaries.append(f"⚠️ High volatility - trend less reliable")

    return ' | '.join(summaries) if summaries else "No significant trends detected"
```

**Example Output:**
```python
{
    'kpi_name': 'mrr',
    'analysis_date': '2025-10-30',
    'data_points': 180,
    'wow': {
        'direction': 'up',
        'magnitude': 0.071,
        'is_significant': True,
        'explanation': 'Trending up by 7.1% (medium effect, significant)'
    },
    'mom': {
        'direction': 'increasing',
        'pct_change': 0.28,
        'trend_quality': 'strong',
        'explanation': 'Increasing trend (strong linearity, R²=0.85)'
    },
    'qoq': {
        'latest_qoq': 0.208,
        'trajectory': 'accelerating_growth',
        'cagr': 0.79,
        'explanation': '📈 Strong upward trajectory: 20.8% QoQ growth (accelerating)'
    },
    'acceleration': {
        'status': 'accelerating',
        'trajectory': 'rapid_growth',
        'explanation': '🚀 Accelerating growth - momentum building'
    },
    'volatility': {
        'level': 'low',
        'trend_reliability': 'high'
    },
    'summary': 'WoW: Trending up by 7.1% (significant) | MoM: Increasing trend (strong) | QoQ: Strong upward trajectory (accelerating) | Momentum: Accelerating growth'
}
```

---

## 8. Visualization Recommendations

### 8.1 Suggested Charts per Trend Type

| Trend Analysis | Recommended Visualization | Purpose |
|----------------|--------------------------|---------|
| WoW Change | Bar chart (current vs previous week) | Show magnitude of change |
| MoM Trend | Line chart with linear regression | Show trajectory |
| QoQ Growth | Grouped bar chart by quarter | Compare quarterly performance |
| MA Crossover | Dual-line chart (short + long MA) | Show momentum shifts |
| Acceleration | Line chart with colored zones | Highlight acceleration phases |
| Volatility | Candlestick or Bollinger Bands | Show variance |
| Comprehensive | Multi-panel dashboard | All timescales together |

### 8.2 Visual Indicators

```python
TREND_ICONS = {
    'up': '📈',
    'down': '📉',
    'flat': '➡️',
    'volatile': '📊',
    'accelerating': '🚀',
    'decelerating': '⏬',
    'recovery': '✅',
    'declining': '⚠️'
}

def get_visual_indicator(trend_result):
    """
    Return appropriate icon for briefing display.
    """
    direction = trend_result['direction']
    if 'acceleration' in trend_result:
        if trend_result['acceleration']['status'] == 'accelerating' and direction == 'up':
            return TREND_ICONS['accelerating']
        elif trend_result['acceleration']['status'] == 'decelerating' and direction == 'down':
            return TREND_ICONS['recovery']

    return TREND_ICONS.get(direction, '📊')
```

---

## 9. Implementation Roadmap

### Phase 1: Basic Trends (Week 1)
- WoW percentage change
- MoM linear regression
- Simple direction classification
- **Deliverable:** Basic trend detection in briefings

### Phase 2: Statistical Rigor (Week 2)
- Significance testing (t-tests)
- Effect size calculation
- Mann-Kendall for non-parametric
- **Deliverable:** Reliable trend signals with confidence scores

### Phase 3: Advanced Analysis (Week 3)
- QoQ and YoY trends
- Acceleration detection
- Volatility metrics
- Moving average crossover
- **Deliverable:** Comprehensive multi-timescale reports

### Phase 4: Visualization & Explanations (Week 4)
- Natural language generation for trends
- Visual indicator selection
- Dashboard integration
- **Deliverable:** Founder-friendly trend summaries

---

## 10. Metrics and Validation

### 10.1 Accuracy Metrics

```python
def validate_trend_detection(predictions, actuals, threshold=0.05):
    """
    Validate trend detection accuracy.

    Args:
        predictions: Predicted trend directions
        actuals: Actual trend directions (ground truth)
        threshold: Minimum change to consider significant

    Returns:
        Accuracy metrics
    """
    correct = sum(p == a for p, a in zip(predictions, actuals))
    accuracy = correct / len(predictions)

    # Confusion matrix
    tp = sum(p == a == 'up' for p, a in zip(predictions, actuals))
    tn = sum(p == a == 'down' for p, a in zip(predictions, actuals))
    fp = sum(p == 'up' and a != 'up' for p, a in zip(predictions, actuals))
    fn = sum(p != 'up' and a == 'up' for p, a in zip(predictions, actuals))

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0

    return {
        'accuracy': accuracy,
        'precision': precision,
        'recall': recall,
        'f1_score': 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
    }
```

**Target Metrics:**
- Trend direction accuracy: ≥85%
- Significant trend detection precision: ≥90%
- False trend rate: <10%

---

## 11. Cost Analysis

### 11.1 Computational Cost

| Trend Method | Complexity | Time per KPI | Memory |
|--------------|------------|--------------|--------|
| Simple % Change | O(1) | <1ms | <1KB |
| Statistical Tests | O(n) | 5-10ms | <10KB |
| Linear Regression | O(n) | 10-20ms | <10KB |
| Seasonal Decomposition | O(n log n) | 50-200ms | ~100KB |
| Mann-Kendall | O(n²) | 20-50ms | <10KB |

**Total Cost per Founder:**
- 10 KPIs × 4 trend checks/day × 20ms = ~1 second CPU/day
- Cost: <$0.01/month per founder

---

## 12. Conclusion

**Recommended Implementation:**

1. **MVP (Sprint 4):**
   - WoW/MoM percentage change with significance testing
   - Linear regression for MoM trends
   - Basic direction classification
   - **Target:** 85%+ trend accuracy

2. **Production:**
   - Full multi-timescale analysis
   - Acceleration detection
   - Volatility-adjusted confidence
   - Natural language explanations
   - **Target:** 90%+ trend accuracy, <10% false trends

This comprehensive trend analysis framework provides founders with actionable insights across all relevant timescales while maintaining statistical rigor and computational efficiency.

---

## References

1. Hyndman, R. J., & Athanasopoulos, G. (2018). "Forecasting: Principles and Practice" (3rd ed.)
2. Mann, H. B. (1945). "Nonparametric Tests Against Trend"
3. Cleveland, R. B. et al. (1990). "STL: A Seasonal-Trend Decomposition Procedure Based on Loess"
4. Box, G. E. P., & Jenkins, G. M. (1976). "Time Series Analysis: Forecasting and Control"
5. Cohen, J. (1988). "Statistical Power Analysis for the Behavioral Sciences"
