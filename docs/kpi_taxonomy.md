# KPI Taxonomy & Definitions

**Version:** 1.0
**Date:** 2025-10-30
**Sprint:** 4 - Insights & Briefings Engine
**Author:** System Architect

---

## Table of Contents

1. [Overview](#overview)
2. [Revenue Metrics](#revenue-metrics)
3. [Customer Metrics](#customer-metrics)
4. [Growth Metrics](#growth-metrics)
5. [Financial Metrics](#financial-metrics)
6. [Sales Metrics](#sales-metrics)
7. [Product Metrics](#product-metrics)
8. [Marketing Metrics](#marketing-metrics)
9. [Data Sources](#data-sources)
10. [Update Frequencies](#update-frequencies)
11. [Alert Thresholds](#alert-thresholds)

---

## Overview

This document defines the standard KPI taxonomy for the AI Chief of Staff platform. All KPIs follow a consistent structure:

**Standard KPI Definition:**
- **Metric Name:** Standardized internal identifier
- **Label:** Human-readable display name
- **Category:** Primary category (revenue, customer, growth, etc.)
- **Description:** What the metric measures
- **Formula:** How it's calculated
- **Unit:** Unit of measurement
- **Data Source:** Where the data comes from
- **Update Frequency:** How often it updates
- **Valid Range:** Min/max acceptable values
- **Change Threshold:** Alert if change exceeds this %
- **Direction:** Is higher better? (↑) or worse? (↓)
- **Visualization:** Recommended chart type

---

## Revenue Metrics

### MRR (Monthly Recurring Revenue)

- **Metric Name:** `mrr`
- **Label:** Monthly Recurring Revenue
- **Category:** Revenue
- **Description:** Total predictable revenue generated from subscriptions each month
- **Formula:** Sum of all active subscription values normalized to monthly
  ```
  MRR = Σ (subscription_value / billing_period_months)
  ```
- **Unit:** USD
- **Data Source:** Granola MCP, ZeroBooks MCP
- **Update Frequency:** Daily (aggregated from subscription changes)
- **Valid Range:** $0 to unlimited
- **Change Threshold:** 100% (alert if doubles or halves)
- **Direction:** Higher is better ↑
- **Visualization:** Line chart with trend

**Subcategories:**
- **New MRR:** MRR from new customers this month
- **Expansion MRR:** Additional MRR from existing customers (upgrades)
- **Contraction MRR:** Lost MRR from downgrades
- **Churned MRR:** MRR lost from cancellations

**Calculation Example:**
```
Customer A: $100/month subscription = $100 MRR
Customer B: $1,200/year subscription = $100 MRR
Customer C: $300/quarter subscription = $100 MRR
Total MRR = $300
```

---

### ARR (Annual Recurring Revenue)

- **Metric Name:** `arr`
- **Label:** Annual Recurring Revenue
- **Category:** Revenue
- **Description:** Annualized version of MRR
- **Formula:** `ARR = MRR × 12`
- **Unit:** USD
- **Data Source:** Calculated from MRR
- **Update Frequency:** Daily
- **Valid Range:** $0 to unlimited
- **Change Threshold:** 100%
- **Direction:** Higher is better ↑
- **Visualization:** Line chart

---

### Total Revenue

- **Metric Name:** `revenue`
- **Label:** Total Revenue
- **Category:** Revenue
- **Description:** All revenue including recurring and one-time
- **Formula:**
  ```
  Total Revenue = MRR + One-time Revenue + Professional Services
  ```
- **Unit:** USD
- **Data Source:** ZeroBooks MCP (accounting data)
- **Update Frequency:** Daily
- **Valid Range:** $0 to unlimited
- **Change Threshold:** 100%
- **Direction:** Higher is better ↑
- **Visualization:** Stacked bar chart (by revenue type)

---

### Revenue Growth Rate

- **Metric Name:** `revenue_growth_rate`
- **Label:** Revenue Growth Rate
- **Category:** Revenue
- **Description:** Month-over-month revenue growth percentage
- **Formula:**
  ```
  Growth Rate = ((Revenue_current - Revenue_previous) / Revenue_previous) × 100
  ```
- **Unit:** Percent
- **Data Source:** Calculated from revenue metrics
- **Update Frequency:** Monthly
- **Valid Range:** -100% to 1000%
- **Change Threshold:** 50% (alert if growth rate changes significantly)
- **Direction:** Higher is better ↑
- **Visualization:** Line chart with zero baseline

**Interpretation:**
- **>20% MoM:** Hypergrowth
- **10-20% MoM:** Strong growth
- **5-10% MoM:** Healthy growth
- **<5% MoM:** Slow growth
- **Negative:** Declining revenue (red flag)

---

## Customer Metrics

### CAC (Customer Acquisition Cost)

- **Metric Name:** `cac`
- **Label:** Customer Acquisition Cost
- **Category:** Customer
- **Description:** Total sales and marketing cost to acquire one customer
- **Formula:**
  ```
  CAC = (Sales Expenses + Marketing Expenses) / New Customers Acquired
  ```
- **Unit:** USD
- **Data Source:** ZeroBooks MCP (expenses), Granola MCP (customer count)
- **Update Frequency:** Monthly
- **Valid Range:** $0 to $10,000
- **Change Threshold:** 200% (alert if CAC triples)
- **Direction:** Lower is better ↓
- **Visualization:** Line chart with target line

**Benchmarks by Business Model:**
- **B2B SaaS (SMB):** $200-$500
- **B2B SaaS (Mid-Market):** $500-$5,000
- **B2B SaaS (Enterprise):** $5,000-$50,000
- **B2C SaaS:** $50-$200

**Calculation Example:**
```
Sales salaries: $20,000/month
Marketing spend: $10,000/month
New customers: 30
CAC = ($20,000 + $10,000) / 30 = $1,000
```

---

### LTV (Customer Lifetime Value)

- **Metric Name:** `ltv`
- **Label:** Customer Lifetime Value
- **Category:** Customer
- **Description:** Average total revenue from a customer over their lifetime
- **Formula:**
  ```
  LTV = (ARPA × Gross Margin %) / Churn Rate

  Where:
  ARPA = Average Revenue Per Account (monthly)
  Gross Margin % = (Revenue - COGS) / Revenue
  Churn Rate = Monthly customer churn rate (as decimal)
  ```
- **Unit:** USD
- **Data Source:** Calculated from ARPA, margin, and churn
- **Update Frequency:** Monthly
- **Valid Range:** $0 to unlimited
- **Change Threshold:** 100%
- **Direction:** Higher is better ↑
- **Visualization:** Line chart

**Simplified Formula:**
```
LTV = ARPA / Churn Rate
(Assumes 100% gross margin for SaaS)
```

**Calculation Example:**
```
ARPA: $100/month
Gross Margin: 80%
Monthly Churn: 5% (0.05)

LTV = ($100 × 0.80) / 0.05 = $1,600
```

---

### LTV:CAC Ratio

- **Metric Name:** `ltv_cac_ratio`
- **Label:** LTV:CAC Ratio
- **Category:** Customer
- **Description:** Ratio of customer lifetime value to acquisition cost
- **Formula:** `LTV:CAC = LTV / CAC`
- **Unit:** Ratio (expressed as X:1)
- **Data Source:** Calculated from LTV and CAC
- **Update Frequency:** Monthly
- **Valid Range:** 0:1 to 20:1
- **Change Threshold:** 50%
- **Direction:** Higher is better ↑
- **Visualization:** Line chart with benchmark zones

**Interpretation:**
- **<1:1** - Losing money on each customer (critical)
- **1:1 to 2:1** - Not sustainable
- **2:1 to 3:1** - Acceptable but risky
- **3:1 to 5:1** - Healthy for early-stage
- **>5:1** - Excellent unit economics
- **>10:1** - May be under-investing in growth

---

### Churn Rate

- **Metric Name:** `churn_rate`
- **Label:** Monthly Churn Rate
- **Category:** Customer
- **Description:** Percentage of customers lost each month
- **Formula:**
  ```
  Churn Rate = (Customers Lost / Customers at Start of Period) × 100
  ```
- **Unit:** Percent
- **Data Source:** Granola MCP (customer data)
- **Update Frequency:** Monthly
- **Valid Range:** 0% to 100%
- **Change Threshold:** 50% (alert if churn increases significantly)
- **Direction:** Lower is better ↓
- **Visualization:** Line chart with target threshold

**Types of Churn:**
- **Customer Churn:** % of customers who cancel
- **Revenue Churn:** % of MRR lost (can be negative with expansion)
- **Gross Churn:** Total churn without considering expansion
- **Net Churn:** Churn minus expansion revenue

**Benchmarks:**
- **Consumer SaaS:** 5-7% monthly
- **SMB SaaS:** 3-5% monthly
- **Mid-Market SaaS:** 1-2% monthly
- **Enterprise SaaS:** <1% monthly

**Calculation Example:**
```
Customers at start: 1,000
Customers lost: 50
Churn Rate = (50 / 1,000) × 100 = 5%
```

---

### Retention Rate

- **Metric Name:** `retention_rate`
- **Label:** Customer Retention Rate
- **Category:** Customer
- **Description:** Percentage of customers retained over a period
- **Formula:** `Retention Rate = 100% - Churn Rate`
- **Unit:** Percent
- **Data Source:** Calculated from churn rate
- **Update Frequency:** Monthly
- **Valid Range:** 0% to 100%
- **Change Threshold:** 20%
- **Direction:** Higher is better ↑
- **Visualization:** Line chart

---

### NPS (Net Promoter Score)

- **Metric Name:** `nps`
- **Label:** Net Promoter Score
- **Category:** Customer
- **Description:** Customer satisfaction and likelihood to recommend
- **Formula:**
  ```
  NPS = % Promoters (9-10) - % Detractors (0-6)
  ```
- **Unit:** Score (-100 to +100)
- **Data Source:** Customer surveys, Granola MCP
- **Update Frequency:** Monthly or quarterly
- **Valid Range:** -100 to +100
- **Change Threshold:** 30%
- **Direction:** Higher is better ↑
- **Visualization:** Gauge chart with color zones

**Interpretation:**
- **70+:** World class
- **50-70:** Excellent
- **30-50:** Good
- **0-30:** Needs improvement
- **<0:** Critical issues

---

## Growth Metrics

### User Signups

- **Metric Name:** `signups`
- **Label:** User Signups
- **Category:** Growth
- **Description:** Number of new user registrations
- **Formula:** Count of new user accounts created
- **Unit:** Count
- **Data Source:** Granola MCP
- **Update Frequency:** Daily
- **Valid Range:** 0 to unlimited
- **Change Threshold:** 200%
- **Direction:** Higher is better ↑
- **Visualization:** Bar chart (daily) or line chart (trend)

---

### DAU (Daily Active Users)

- **Metric Name:** `dau`
- **Label:** Daily Active Users
- **Category:** Growth
- **Description:** Unique users who perform a key action each day
- **Formula:** Count of unique users active on a given day
- **Unit:** Count
- **Data Source:** Granola MCP (product analytics)
- **Update Frequency:** Daily
- **Valid Range:** 0 to unlimited
- **Change Threshold:** 100%
- **Direction:** Higher is better ↑
- **Visualization:** Line chart with 7-day moving average

**Key Actions Definition:**
- Login
- Core feature usage
- Content creation/consumption
- (Defined per product)

---

### MAU (Monthly Active Users)

- **Metric Name:** `mau`
- **Label:** Monthly Active Users
- **Category:** Growth
- **Description:** Unique users active in the last 30 days
- **Formula:** Count of unique users active in past 30 days
- **Unit:** Count
- **Data Source:** Granola MCP
- **Update Frequency:** Daily (rolling 30-day window)
- **Valid Range:** 0 to unlimited
- **Change Threshold:** 100%
- **Direction:** Higher is better ↑
- **Visualization:** Line chart

**Related Metric:**
- **DAU/MAU Ratio:** Stickiness measure (higher = more engagement)
  - 20%+ is excellent for most SaaS

---

### Conversion Rate

- **Metric Name:** `conversion_rate`
- **Label:** Conversion Rate
- **Category:** Growth
- **Description:** Percentage of visitors/trials that convert to paying customers
- **Formula:**
  ```
  Conversion Rate = (Paying Customers / Total Signups) × 100
  ```
- **Unit:** Percent
- **Data Source:** Granola MCP
- **Update Frequency:** Daily
- **Valid Range:** 0% to 100%
- **Change Threshold:** 50%
- **Direction:** Higher is better ↑
- **Visualization:** Line chart with funnel breakdown

**Typical Funnel:**
```
Visitor → Signup (10-20%)
Signup → Trial (50-70%)
Trial → Paid (10-40%)
Overall: 0.5% - 5%
```

---

### Activation Rate

- **Metric Name:** `activation_rate`
- **Label:** Activation Rate
- **Category:** Growth
- **Description:** Percentage of new signups who reach activation milestone
- **Formula:**
  ```
  Activation Rate = (Activated Users / New Signups) × 100
  ```
- **Unit:** Percent
- **Data Source:** Granola MCP
- **Update Frequency:** Daily
- **Valid Range:** 0% to 100%
- **Change Threshold:** 30%
- **Direction:** Higher is better ↑
- **Visualization:** Line chart

**Activation Milestone Examples:**
- Complete onboarding
- Create first project
- Invite team member
- Use core feature
- (Product-specific)

---

## Financial Metrics

### Burn Rate

- **Metric Name:** `burn_rate`
- **Label:** Monthly Burn Rate
- **Category:** Financial
- **Description:** Monthly cash consumption (expenses minus revenue)
- **Formula:**
  ```
  Burn Rate = Monthly Operating Expenses - Monthly Revenue
  ```
- **Unit:** USD
- **Data Source:** ZeroBooks MCP
- **Update Frequency:** Monthly
- **Valid Range:** $0 to unlimited
- **Change Threshold:** 100%
- **Direction:** Lower is better ↓
- **Visualization:** Line chart with runway projection

**Types:**
- **Gross Burn:** Total monthly expenses
- **Net Burn:** Expenses minus revenue (preferred metric)

---

### Runway

- **Metric Name:** `runway`
- **Label:** Cash Runway
- **Category:** Financial
- **Description:** Months of operation remaining at current burn rate
- **Formula:**
  ```
  Runway (months) = Cash Balance / Monthly Burn Rate
  ```
- **Unit:** Months
- **Data Source:** Calculated from cash balance and burn rate
- **Update Frequency:** Monthly
- **Valid Range:** 0 to 120 months
- **Change Threshold:** 50%
- **Direction:** Higher is better ↑
- **Visualization:** Line chart with alert threshold

**Interpretation:**
- **<3 months:** Critical - raise immediately
- **3-6 months:** Start fundraising now
- **6-12 months:** Comfortable, plan next raise
- **12-18 months:** Healthy
- **>18 months:** Very strong position

---

### Cash Balance

- **Metric Name:** `cash_balance`
- **Label:** Cash Balance
- **Category:** Financial
- **Description:** Total cash and cash equivalents
- **Formula:** Sum of all liquid assets (bank accounts + equivalents)
- **Unit:** USD
- **Data Source:** ZeroBooks MCP
- **Update Frequency:** Daily
- **Valid Range:** $0 to unlimited
- **Change Threshold:** 100%
- **Direction:** Higher is better ↑
- **Visualization:** Line chart with runway annotation

---

### Gross Margin

- **Metric Name:** `gross_margin`
- **Label:** Gross Margin
- **Category:** Financial
- **Description:** Gross profit as percentage of revenue
- **Formula:**
  ```
  Gross Margin = ((Revenue - COGS) / Revenue) × 100
  ```
- **Unit:** Percent
- **Data Source:** ZeroBooks MCP
- **Update Frequency:** Monthly
- **Valid Range:** 0% to 100%
- **Change Threshold:** 20%
- **Direction:** Higher is better ↑
- **Visualization:** Line chart

**Benchmarks:**
- **Pure SaaS:** 75-90%
- **SaaS + Services:** 60-75%
- **Hardware + Software:** 40-60%

---

### Operating Expenses

- **Metric Name:** `operating_expenses`
- **Label:** Operating Expenses
- **Category:** Financial
- **Description:** Total monthly operating costs
- **Formula:** Sum of all operating expenses
- **Unit:** USD
- **Data Source:** ZeroBooks MCP
- **Update Frequency:** Monthly
- **Valid Range:** $0 to unlimited
- **Change Threshold:** 100%
- **Direction:** Lower is better ↓ (but must support growth)
- **Visualization:** Stacked bar chart (by category)

**Categories:**
- R&D / Engineering
- Sales & Marketing
- General & Administrative
- Customer Success

---

## Sales Metrics

### Pipeline Value

- **Metric Name:** `pipeline_value`
- **Label:** Sales Pipeline Value
- **Category:** Sales
- **Description:** Total potential revenue in sales pipeline
- **Formula:** Sum of (Deal Value × Win Probability) for all open deals
- **Unit:** USD
- **Data Source:** Granola MCP (CRM data)
- **Update Frequency:** Daily
- **Valid Range:** $0 to unlimited
- **Change Threshold:** 100%
- **Direction:** Higher is better ↑
- **Visualization:** Line chart by pipeline stage

---

### Win Rate

- **Metric Name:** `win_rate`
- **Label:** Sales Win Rate
- **Category:** Sales
- **Description:** Percentage of opportunities that close successfully
- **Formula:**
  ```
  Win Rate = (Deals Won / Total Deals) × 100
  ```
- **Unit:** Percent
- **Data Source:** Granola MCP (CRM)
- **Update Frequency:** Weekly
- **Valid Range:** 0% to 100%
- **Change Threshold:** 30%
- **Direction:** Higher is better ↑
- **Visualization:** Line chart with benchmark

**Benchmarks:**
- **Enterprise B2B:** 15-30%
- **Mid-Market B2B:** 20-40%
- **SMB B2B:** 25-50%

---

### Average Deal Size

- **Metric Name:** `avg_deal_size`
- **Label:** Average Deal Size
- **Category:** Sales
- **Description:** Average contract value per closed deal
- **Formula:**
  ```
  Avg Deal Size = Total Deal Value / Number of Deals Closed
  ```
- **Unit:** USD
- **Data Source:** Granola MCP
- **Update Frequency:** Monthly
- **Valid Range:** $0 to unlimited
- **Change Threshold:** 100%
- **Direction:** Higher is better ↑
- **Visualization:** Line chart with distribution histogram

---

### Sales Cycle Length

- **Metric Name:** `sales_cycle`
- **Label:** Sales Cycle Length
- **Category:** Sales
- **Description:** Average time from lead to closed deal
- **Formula:** Average of (Close Date - Lead Created Date)
- **Unit:** Days
- **Data Source:** Granola MCP (CRM)
- **Update Frequency:** Monthly
- **Valid Range:** 0 to 365 days
- **Change Threshold:** 50%
- **Direction:** Lower is better ↓ (but not at expense of deal size)
- **Visualization:** Line chart with trend

**Benchmarks:**
- **SMB SaaS:** 30-60 days
- **Mid-Market SaaS:** 60-120 days
- **Enterprise SaaS:** 120-365+ days

---

## Product Metrics

### Feature Adoption Rate

- **Metric Name:** `feature_adoption_rate`
- **Label:** Feature Adoption Rate
- **Category:** Product
- **Description:** Percentage of users who use a specific feature
- **Formula:**
  ```
  Adoption Rate = (Users Using Feature / Total Users) × 100
  ```
- **Unit:** Percent
- **Data Source:** Granola MCP (product analytics)
- **Update Frequency:** Weekly
- **Valid Range:** 0% to 100%
- **Change Threshold:** 50%
- **Direction:** Higher is better ↑
- **Visualization:** Bar chart (by feature)

---

### User Engagement Score

- **Metric Name:** `engagement_score`
- **Label:** User Engagement Score
- **Category:** Product
- **Description:** Composite score measuring user activity level
- **Formula:** Weighted combination of:
  - Login frequency
  - Feature usage
  - Session duration
  - Actions per session
- **Unit:** Score (0-100)
- **Data Source:** Granola MCP
- **Update Frequency:** Daily
- **Valid Range:** 0 to 100
- **Change Threshold:** 30%
- **Direction:** Higher is better ↑
- **Visualization:** Distribution histogram

---

## Marketing Metrics

### Website Traffic

- **Metric Name:** `website_traffic`
- **Label:** Website Traffic
- **Category:** Marketing
- **Description:** Unique website visitors
- **Formula:** Count of unique visitors
- **Unit:** Count
- **Data Source:** Granola MCP (analytics)
- **Update Frequency:** Daily
- **Valid Range:** 0 to unlimited
- **Change Threshold:** 200%
- **Direction:** Higher is better ↑
- **Visualization:** Line chart

---

### Lead Generation Rate

- **Metric Name:** `lead_gen_rate`
- **Label:** Lead Generation Rate
- **Category:** Marketing
- **Description:** Rate of converting visitors to leads
- **Formula:**
  ```
  Lead Gen Rate = (Leads Generated / Website Visitors) × 100
  ```
- **Unit:** Percent
- **Data Source:** Granola MCP
- **Update Frequency:** Daily
- **Valid Range:** 0% to 100%
- **Change Threshold:** 50%
- **Direction:** Higher is better ↑
- **Visualization:** Line chart

---

### Cost Per Lead (CPL)

- **Metric Name:** `cpl`
- **Label:** Cost Per Lead
- **Category:** Marketing
- **Description:** Marketing cost to generate one qualified lead
- **Formula:**
  ```
  CPL = Marketing Spend / Leads Generated
  ```
- **Unit:** USD
- **Data Source:** ZeroBooks MCP (spend), Granola MCP (leads)
- **Update Frequency:** Monthly
- **Valid Range:** $0 to $1,000
- **Change Threshold:** 100%
- **Direction:** Lower is better ↓
- **Visualization:** Line chart by channel

---

## Data Sources

### Primary Sources

**Granola MCP:**
- Product analytics (users, engagement, features)
- CRM data (pipeline, deals, customers)
- Custom business metrics
- Integration with various platforms

**ZeroBooks MCP:**
- Financial data (revenue, expenses, cash flow)
- P&L statements
- Balance sheet
- Expense categorization

### Data Source Mapping

| KPI Category | Primary Source | Secondary Source | Update Method |
|--------------|---------------|------------------|---------------|
| Revenue | ZeroBooks MCP | Granola MCP | Daily sync |
| Customer | Granola MCP | - | Real-time |
| Growth | Granola MCP | - | Real-time |
| Financial | ZeroBooks MCP | - | Daily sync |
| Sales | Granola MCP | - | Real-time |
| Product | Granola MCP | - | Real-time |
| Marketing | Granola MCP | - | Real-time |

---

## Update Frequencies

| Frequency | KPIs | Update Schedule |
|-----------|------|----------------|
| **Real-time** | DAU, signups, engagement | Continuous (< 5 min lag) |
| **Hourly** | Website traffic, leads | Every hour |
| **Daily** | MRR, ARR, cash balance, pipeline | 00:00, 06:00, 12:00, 18:00 UTC |
| **Weekly** | Win rate, feature adoption | Monday 00:00 UTC |
| **Monthly** | Churn, LTV, CAC, runway, margin | 1st of month 00:00 UTC |
| **Quarterly** | NPS, strategic metrics | 1st of quarter 00:00 UTC |

### Ingestion Schedule

```
Granola MCP: Every 6 hours (00:00, 06:00, 12:00, 18:00 UTC)
ZeroBooks MCP: Every 6 hours (00:00, 06:00, 12:00, 18:00 UTC)
```

---

## Alert Thresholds

### Change Thresholds (% change that triggers alert)

| Metric | Minor (Yellow) | Major (Orange) | Critical (Red) |
|--------|---------------|----------------|----------------|
| MRR | >10% | >25% | >50% |
| Churn Rate | >20% | >50% | >100% |
| CAC | >50% | >100% | >200% |
| Runway | -20% | -30% | -50% |
| Burn Rate | >30% | >50% | >100% |
| Conversion Rate | -10% | -25% | -50% |
| Win Rate | -15% | -30% | -50% |

### Absolute Thresholds

| Metric | Warning | Critical |
|--------|---------|----------|
| Runway | <6 months | <3 months |
| Cash Balance | <$100k | <$50k |
| Churn Rate | >5%/month | >10%/month |
| LTV:CAC Ratio | <3:1 | <2:1 |
| Gross Margin | <60% | <50% |
| NPS | <20 | <0 |

---

## Custom KPIs

Workspaces can define custom KPIs specific to their business:

**Custom KPI Template:**
```json
{
  "metric_name": "custom_metric_name",
  "metric_label": "Human Readable Name",
  "category": "custom",
  "description": "What this metric measures",
  "formula": "How it's calculated",
  "unit": "USD|percent|count|...",
  "data_source": "custom_integration",
  "update_frequency": "daily|weekly|monthly",
  "min_value": 0,
  "max_value": null,
  "max_change_percent": 100,
  "is_higher_better": true,
  "chart_type": "line|bar|area"
}
```

**Examples:**
- Customer health score
- Feature usage index
- Support ticket volume
- API usage
- Infrastructure costs
- Time to first value

---

## Calculation Priority

When multiple data sources provide the same metric:

1. **Granola MCP** (primary for product/customer metrics)
2. **ZeroBooks MCP** (primary for financial metrics)
3. **Calculated** (derived from other metrics)
4. **Manual Entry** (fallback)

---

## Data Quality Rules

### Validation Rules

```python
VALIDATION_RULES = {
    'mrr': {
        'min': 0,
        'type': 'float',
        'unit': 'USD',
        'required': True
    },
    'churn_rate': {
        'min': 0,
        'max': 100,
        'type': 'float',
        'unit': 'percent',
        'required': True
    },
    'cac': {
        'min': 0,
        'max': 10000,
        'type': 'float',
        'unit': 'USD',
        'warn_if': lambda x: x > 1000  # Warn if CAC > $1k
    }
}
```

### Missing Data Handling

- **Recent missing:** Flag as stale, alert if >24h old
- **Historical gaps:** Interpolate if < 3 data points missing
- **Persistent missing:** Disable anomaly detection for that metric

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-10-30 | Initial taxonomy with 25 standard KPIs |

---

**Document Version:** 1.0
**Last Updated:** 2025-10-30
**Maintained By:** System Architect
