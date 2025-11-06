"""
AI Chief of Staff - Mock KPI Time-Series Data
Sprint 4: Insights & Briefings Engine

Sample KPI time-series data for testing anomaly detection and trend analysis:
- Flat trend
- Growing trend
- Declining trend
- Seasonal pattern
- With anomalies
- With missing data
"""

from datetime import datetime, timedelta
from typing import Dict, List
import math


# ============================================================================
# TIME-SERIES GENERATORS
# ============================================================================

def generate_flat_trend(
    base_value: float = 10000.0,
    days: int = 30,
    noise: float = 0.01
) -> List[Dict]:
    """
    Generate flat trend with minimal noise.

    Args:
        base_value: Base metric value
        days: Number of days
        noise: Random noise factor (0.01 = 1%)

    Returns:
        List of {timestamp, value} dictionaries
    """
    import random
    data = []

    for i in range(days):
        timestamp = datetime.utcnow() - timedelta(days=days - i)
        # Add small random noise
        value = base_value * (1 + random.uniform(-noise, noise))
        data.append({
            "timestamp": timestamp.isoformat(),
            "value": round(value, 2)
        })

    return data


def generate_growing_trend(
    base_value: float = 10000.0,
    days: int = 30,
    growth_rate: float = 0.05,
    noise: float = 0.02
) -> List[Dict]:
    """
    Generate growing trend.

    Args:
        base_value: Starting metric value
        days: Number of days
        growth_rate: Total growth rate over period (0.05 = 5%)
        noise: Random noise factor

    Returns:
        List of {timestamp, value} dictionaries
    """
    import random
    data = []

    for i in range(days):
        timestamp = datetime.utcnow() - timedelta(days=days - i)
        # Linear growth with noise
        growth_factor = 1 + (growth_rate * i / days)
        noise_factor = 1 + random.uniform(-noise, noise)
        value = base_value * growth_factor * noise_factor
        data.append({
            "timestamp": timestamp.isoformat(),
            "value": round(value, 2)
        })

    return data


def generate_declining_trend(
    base_value: float = 10000.0,
    days: int = 30,
    decline_rate: float = 0.05,
    noise: float = 0.02
) -> List[Dict]:
    """
    Generate declining trend.

    Args:
        base_value: Starting metric value
        days: Number of days
        decline_rate: Total decline rate over period (0.05 = 5%)
        noise: Random noise factor

    Returns:
        List of {timestamp, value} dictionaries
    """
    import random
    data = []

    for i in range(days):
        timestamp = datetime.utcnow() - timedelta(days=days - i)
        # Linear decline with noise
        decline_factor = 1 - (decline_rate * i / days)
        noise_factor = 1 + random.uniform(-noise, noise)
        value = base_value * decline_factor * noise_factor
        data.append({
            "timestamp": timestamp.isoformat(),
            "value": round(value, 2)
        })

    return data


def generate_seasonal_pattern(
    base_value: float = 10000.0,
    days: int = 90,
    weekly_amplitude: float = 0.1,
    monthly_amplitude: float = 0.05,
    noise: float = 0.02
) -> List[Dict]:
    """
    Generate seasonal pattern with weekly and monthly cycles.

    Args:
        base_value: Base metric value
        days: Number of days
        weekly_amplitude: Amplitude of weekly cycle (0.1 = 10%)
        monthly_amplitude: Amplitude of monthly cycle (0.05 = 5%)
        noise: Random noise factor

    Returns:
        List of {timestamp, value} dictionaries
    """
    import random
    data = []

    for i in range(days):
        timestamp = datetime.utcnow() - timedelta(days=days - i)

        # Weekly seasonality (7-day cycle)
        weekly_factor = 1 + weekly_amplitude * math.sin(2 * math.pi * i / 7)

        # Monthly seasonality (30-day cycle)
        monthly_factor = 1 + monthly_amplitude * math.cos(2 * math.pi * i / 30)

        # Random noise
        noise_factor = 1 + random.uniform(-noise, noise)

        value = base_value * weekly_factor * monthly_factor * noise_factor
        data.append({
            "timestamp": timestamp.isoformat(),
            "value": round(value, 2)
        })

    return data


def generate_with_spike_anomaly(
    base_value: float = 10000.0,
    days: int = 30,
    anomaly_day: int = 15,
    spike_factor: float = 1.3,
    noise: float = 0.02
) -> List[Dict]:
    """
    Generate time-series with spike anomaly.

    Args:
        base_value: Base metric value
        days: Number of days
        anomaly_day: Day where spike occurs
        spike_factor: Spike multiplier (1.3 = 30% increase)
        noise: Random noise factor

    Returns:
        List of {timestamp, value} dictionaries
    """
    import random
    data = []

    for i in range(days):
        timestamp = datetime.utcnow() - timedelta(days=days - i)

        if i == anomaly_day:
            # Spike
            value = base_value * spike_factor
        else:
            # Normal with noise
            value = base_value * (1 + random.uniform(-noise, noise))

        data.append({
            "timestamp": timestamp.isoformat(),
            "value": round(value, 2)
        })

    return data


def generate_with_drop_anomaly(
    base_value: float = 10000.0,
    days: int = 30,
    anomaly_day: int = 15,
    drop_factor: float = 0.7,
    noise: float = 0.02
) -> List[Dict]:
    """
    Generate time-series with drop anomaly.

    Args:
        base_value: Base metric value
        days: Number of days
        anomaly_day: Day where drop occurs
        drop_factor: Drop multiplier (0.7 = 30% decrease)
        noise: Random noise factor

    Returns:
        List of {timestamp, value} dictionaries
    """
    import random
    data = []

    for i in range(days):
        timestamp = datetime.utcnow() - timedelta(days=days - i)

        if i == anomaly_day:
            # Drop
            value = base_value * drop_factor
        else:
            # Normal with noise
            value = base_value * (1 + random.uniform(-noise, noise))

        data.append({
            "timestamp": timestamp.isoformat(),
            "value": round(value, 2)
        })

    return data


def generate_with_multiple_anomalies(
    base_value: float = 10000.0,
    days: int = 60,
    anomaly_days: List[int] = None,
    noise: float = 0.02
) -> List[Dict]:
    """
    Generate time-series with multiple anomalies.

    Args:
        base_value: Base metric value
        days: Number of days
        anomaly_days: List of days with anomalies (default: [15, 30, 45])
        noise: Random noise factor

    Returns:
        List of {timestamp, value} dictionaries
    """
    import random
    if anomaly_days is None:
        anomaly_days = [15, 30, 45]

    data = []

    for i in range(days):
        timestamp = datetime.utcnow() - timedelta(days=days - i)

        if i in anomaly_days:
            # Random spike or drop
            anomaly_factor = random.choice([0.7, 1.3, 1.4, 0.6])
            value = base_value * anomaly_factor
        else:
            # Normal with noise
            value = base_value * (1 + random.uniform(-noise, noise))

        data.append({
            "timestamp": timestamp.isoformat(),
            "value": round(value, 2)
        })

    return data


def generate_with_missing_data(
    base_value: float = 10000.0,
    days: int = 30,
    missing_days: List[int] = None,
    noise: float = 0.02
) -> List[Dict]:
    """
    Generate time-series with missing data points.

    Args:
        base_value: Base metric value
        days: Number of days
        missing_days: List of days with missing data (default: [5, 10, 15, 20])
        noise: Random noise factor

    Returns:
        List of {timestamp, value} dictionaries with None for missing days
    """
    import random
    if missing_days is None:
        missing_days = [5, 10, 15, 20]

    data = []

    for i in range(days):
        timestamp = datetime.utcnow() - timedelta(days=days - i)

        if i in missing_days:
            # Missing data
            data.append({
                "timestamp": timestamp.isoformat(),
                "value": None
            })
        else:
            # Normal with noise
            value = base_value * (1 + random.uniform(-noise, noise))
            data.append({
                "timestamp": timestamp.isoformat(),
                "value": round(value, 2)
            })

    return data


def generate_volatile_pattern(
    base_value: float = 10000.0,
    days: int = 30,
    volatility: float = 0.15
) -> List[Dict]:
    """
    Generate highly volatile time-series.

    Args:
        base_value: Base metric value
        days: Number of days
        volatility: Volatility factor (0.15 = 15%)

    Returns:
        List of {timestamp, value} dictionaries
    """
    import random
    data = []

    for i in range(days):
        timestamp = datetime.utcnow() - timedelta(days=days - i)
        # High volatility
        value = base_value * (1 + random.uniform(-volatility, volatility))
        data.append({
            "timestamp": timestamp.isoformat(),
            "value": round(value, 2)
        })

    return data


# ============================================================================
# STANDARD METRIC DATASETS
# ============================================================================

# MRR (Monthly Recurring Revenue) - Typically growing
MRR_GROWING_30_DAYS = generate_growing_trend(
    base_value=50000.0,
    days=30,
    growth_rate=0.10,  # 10% growth
    noise=0.02
)

MRR_WITH_SPIKE = generate_with_spike_anomaly(
    base_value=50000.0,
    days=30,
    anomaly_day=15,
    spike_factor=1.25  # 25% spike
)

# CAC (Customer Acquisition Cost) - Should be declining or flat
CAC_DECLINING_30_DAYS = generate_declining_trend(
    base_value=500.0,
    days=30,
    decline_rate=0.05,  # 5% decline
    noise=0.03
)

CAC_WITH_SPIKE = generate_with_spike_anomaly(
    base_value=500.0,
    days=30,
    anomaly_day=20,
    spike_factor=1.30  # 30% spike (bad)
)

# Churn Rate - Should be low and stable
CHURN_FLAT_30_DAYS = generate_flat_trend(
    base_value=0.05,  # 5% churn
    days=30,
    noise=0.01
)

CHURN_WITH_SPIKE = generate_with_spike_anomaly(
    base_value=0.05,
    days=30,
    anomaly_day=18,
    spike_factor=1.40  # 40% spike (very bad)
)

# Conversion Rate - Typically stable with some volatility
CONVERSION_SEASONAL = generate_seasonal_pattern(
    base_value=0.15,  # 15% conversion
    days=90,
    weekly_amplitude=0.05,
    monthly_amplitude=0.03,
    noise=0.02
)

CONVERSION_WITH_DROP = generate_with_drop_anomaly(
    base_value=0.15,
    days=30,
    anomaly_day=12,
    drop_factor=0.70  # 30% drop
)

# Runway (months) - Should be stable or growing
RUNWAY_DECLINING = generate_declining_trend(
    base_value=18.0,  # 18 months
    days=60,
    decline_rate=0.15,  # 15% decline
    noise=0.02
)

RUNWAY_WITH_DROP = generate_with_drop_anomaly(
    base_value=18.0,
    days=60,
    anomaly_day=30,
    drop_factor=0.75  # 25% drop
)

# Burn Rate - Should be stable or declining
BURN_RATE_VOLATILE = generate_volatile_pattern(
    base_value=25000.0,
    days=30,
    volatility=0.20
)

BURN_RATE_WITH_SPIKE = generate_with_spike_anomaly(
    base_value=25000.0,
    days=30,
    anomaly_day=22,
    spike_factor=1.35  # 35% spike
)


# ============================================================================
# COMPREHENSIVE TEST DATASETS
# ============================================================================

COMPREHENSIVE_KPI_DATASET = {
    "mrr": {
        "normal": MRR_GROWING_30_DAYS,
        "with_anomaly": MRR_WITH_SPIKE,
    },
    "cac": {
        "normal": CAC_DECLINING_30_DAYS,
        "with_anomaly": CAC_WITH_SPIKE,
    },
    "churn_rate": {
        "normal": CHURN_FLAT_30_DAYS,
        "with_anomaly": CHURN_WITH_SPIKE,
    },
    "conversion_rate": {
        "normal": CONVERSION_SEASONAL,
        "with_anomaly": CONVERSION_WITH_DROP,
    },
    "runway_months": {
        "normal": generate_flat_trend(18.0, 60, 0.01),
        "with_anomaly": RUNWAY_WITH_DROP,
    },
    "burn_rate": {
        "normal": generate_flat_trend(25000.0, 30, 0.05),
        "with_anomaly": BURN_RATE_WITH_SPIKE,
    }
}


# Missing data scenarios
MISSING_DATA_SCENARIOS = {
    "sparse_missing": generate_with_missing_data(
        base_value=10000.0,
        days=30,
        missing_days=[5, 15, 25]
    ),
    "consecutive_missing": generate_with_missing_data(
        base_value=10000.0,
        days=30,
        missing_days=[10, 11, 12, 13]
    ),
    "heavy_missing": generate_with_missing_data(
        base_value=10000.0,
        days=30,
        missing_days=[i for i in range(0, 30, 3)]  # Every 3rd day missing
    )
}


# Multi-anomaly scenarios
MULTI_ANOMALY_DATASET = generate_with_multiple_anomalies(
    base_value=10000.0,
    days=60,
    anomaly_days=[10, 25, 40, 55],
    noise=0.02
)


# ============================================================================
# EDGE CASES
# ============================================================================

EDGE_CASES = {
    "all_zeros": [
        {"timestamp": (datetime.utcnow() - timedelta(days=30 - i)).isoformat(), "value": 0.0}
        for i in range(30)
    ],
    "all_same": [
        {"timestamp": (datetime.utcnow() - timedelta(days=30 - i)).isoformat(), "value": 10000.0}
        for i in range(30)
    ],
    "negative_values": [
        {"timestamp": (datetime.utcnow() - timedelta(days=30 - i)).isoformat(), "value": -100.0 * i}
        for i in range(30)
    ],
    "extreme_spike": generate_with_spike_anomaly(
        base_value=10000.0,
        days=30,
        anomaly_day=15,
        spike_factor=10.0  # 10x spike
    ),
    "single_data_point": [
        {"timestamp": datetime.utcnow().isoformat(), "value": 10000.0}
    ],
    "two_data_points": [
        {"timestamp": (datetime.utcnow() - timedelta(days=1)).isoformat(), "value": 10000.0},
        {"timestamp": datetime.utcnow().isoformat(), "value": 10100.0}
    ]
}
