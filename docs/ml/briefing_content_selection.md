# Briefing Content Selection & Prioritization

## Executive Summary

This document defines algorithms for intelligent content selection in Morning Briefs and Evening Wraps. The system prioritizes urgent tasks, critical anomalies, important meetings, and actionable insights while optimizing for founder attention (60-90 second read time).

**Goal:** Deliver the most relevant 5-7 items per briefing with ≥90% founder satisfaction on content relevance.

---

## 1. Briefing Types & Objectives

### 1.1 Morning Brief (8:00 AM)

**Purpose:** Prepare founder for the day ahead
**Read Time:** 60-90 seconds
**Content Mix:**
- Today's urgent tasks (2-3 items)
- Critical alerts or anomalies (0-2 items)
- Today's meetings with context (2-3 items)
- Top unread messages by importance (3-5 items)
- KPI snapshot (3-5 metrics)

### 1.2 Evening Wrap (6:00 PM)

**Purpose:** Daily retrospective and tomorrow preparation
**Read Time:** 60-90 seconds
**Content Mix:**
- Task completion summary (1 item)
- New insights generated today (1-2 items)
- Decisions made in meetings (1-2 items)
- Sentiment trajectory (1 item)
- Tomorrow's top priorities (2-3 items)

---

## 2. Content Scoring Framework

### 2.1 Universal Scoring Formula

```python
def calculate_content_score(item, context, briefing_type):
    """
    Score content item for inclusion in briefing (0-100).

    Components:
    - Urgency (35%): Time-sensitivity
    - Impact (25%): Business importance
    - Relevance (20%): Founder's role/focus
    - Freshness (10%): Recency of information
    - Actionability (10%): Clear next steps available
    """
    urgency_score = calculate_urgency(item, context)
    impact_score = calculate_impact(item, context)
    relevance_score = calculate_relevance(item, context)
    freshness_score = calculate_freshness(item)
    actionability_score = calculate_actionability(item)

    # Weighted combination
    total_score = (
        urgency_score * 0.35 +
        impact_score * 0.25 +
        relevance_score * 0.20 +
        freshness_score * 0.10 +
        actionability_score * 0.10
    ) * 100

    # Briefing-specific adjustments
    if briefing_type == 'morning':
        # Boost forward-looking items
        if item.get('category') in ['task', 'meeting', 'calendar']:
            total_score *= 1.15
    elif briefing_type == 'evening':
        # Boost retrospective items
        if item.get('category') in ['insight', 'decision', 'accomplishment']:
            total_score *= 1.15

    return min(total_score, 100)  # Cap at 100
```

---

## 3. Urgency Calculation

### 3.1 Urgency Scoring Algorithm

```python
def calculate_urgency(item, context):
    """
    Calculate urgency score (0-1) based on time-sensitivity.
    """
    item_type = item['type']

    if item_type == 'task':
        return calculate_task_urgency(item)
    elif item_type == 'anomaly':
        return calculate_anomaly_urgency(item)
    elif item_type == 'meeting':
        return calculate_meeting_urgency(item, context)
    elif item_type == 'message':
        return calculate_message_urgency(item)
    elif item_type == 'insight':
        return calculate_insight_urgency(item)
    else:
        return 0.5  # Default medium urgency

def calculate_task_urgency(task):
    """Task urgency based on due date and dependencies."""
    if not task.get('due_date'):
        return 0.4  # No due date = medium-low urgency

    due_date = pd.to_datetime(task['due_date'])
    now = pd.Timestamp.now()
    hours_until_due = (due_date - now).total_seconds() / 3600

    # Urgency mapping
    if hours_until_due < 4:
        urgency = 1.0  # Due in <4 hours
    elif hours_until_due < 24:
        urgency = 0.9  # Due today
    elif hours_until_due < 48:
        urgency = 0.7  # Due tomorrow
    elif hours_until_due < 168:  # 1 week
        urgency = 0.5
    else:
        urgency = 0.3

    # Boost if blocking others
    if task.get('blocks_other_tasks'):
        urgency = min(urgency * 1.3, 1.0)

    # Boost if high priority
    if task.get('priority') == 'critical':
        urgency = min(urgency * 1.2, 1.0)

    return urgency

def calculate_anomaly_urgency(anomaly):
    """Anomaly urgency based on severity and trend."""
    severity_map = {
        'critical': 1.0,
        'high': 0.8,
        'medium': 0.5,
        'low': 0.3
    }

    urgency = severity_map.get(anomaly.get('severity', 'medium'), 0.5)

    # Boost if accelerating
    if anomaly.get('acceleration') == 'accelerating':
        urgency = min(urgency * 1.3, 1.0)

    return urgency

def calculate_meeting_urgency(meeting, context):
    """Meeting urgency based on time until meeting and importance."""
    meeting_time = pd.to_datetime(meeting['start_time'])
    now = pd.Timestamp.now()
    hours_until = (meeting_time - now).total_seconds() / 3600

    # Time-based urgency
    if 0 < hours_until < 1:
        time_urgency = 1.0  # Starting within 1 hour
    elif 1 <= hours_until < 4:
        time_urgency = 0.9  # Today morning
    elif 4 <= hours_until < 24:
        time_urgency = 0.7  # Later today
    elif hours_until < 0:
        time_urgency = 0.2  # Already happened (low priority for morning brief)
    else:
        time_urgency = 0.4  # Future days

    # Importance-based boost
    if 'investor' in meeting.get('title', '').lower() or 'board' in meeting.get('title', '').lower():
        importance_boost = 1.3
    elif 'interview' in meeting.get('title', '').lower():
        importance_boost = 1.2
    elif meeting.get('attendee_count', 0) > 5:
        importance_boost = 1.1
    else:
        importance_boost = 1.0

    return min(time_urgency * importance_boost, 1.0)

def calculate_message_urgency(message):
    """Message urgency from NLP classification."""
    # Use pre-computed urgency from sentiment analysis
    urgency_keywords = ['urgent', 'asap', 'immediate', 'emergency', 'critical']

    base_urgency = message.get('urgency_score', 0.5)

    # Keyword boost
    content_lower = message.get('content', '').lower()
    if any(keyword in content_lower for keyword in urgency_keywords):
        base_urgency = min(base_urgency * 1.4, 1.0)

    # Sender importance boost
    if message.get('sender_type') in ['investor', 'board_member', 'cofounder']:
        base_urgency = min(base_urgency * 1.3, 1.0)

    return base_urgency
```

---

## 4. Impact Calculation

### 4.1 Business Impact Scoring

```python
def calculate_impact(item, context):
    """
    Calculate business impact score (0-1).
    """
    if item['type'] == 'anomaly':
        return calculate_anomaly_impact(item, context)
    elif item['type'] == 'task':
        return calculate_task_impact(item, context)
    elif item['type'] == 'insight':
        return calculate_insight_impact(item, context)
    elif item['type'] == 'decision':
        return 0.8  # Decisions are high impact
    else:
        return 0.5

def calculate_anomaly_impact(anomaly, context):
    """
    Impact based on affected KPI and magnitude.
    """
    # KPI importance weights
    kpi_weights = {
        'mrr': 1.0,
        'runway_months': 1.0,
        'churn_rate': 0.9,
        'cac': 0.9,
        'ltv': 0.85,
        'conversion_rate': 0.8,
        'burn_rate': 0.85,
        'active_users': 0.7
    }

    kpi = anomaly.get('kpi_name', '')
    weight = kpi_weights.get(kpi, 0.5)

    # Magnitude factor
    magnitude = abs(anomaly.get('magnitude', 0))
    if magnitude > 0.30:  # >30% change
        magnitude_factor = 1.0
    elif magnitude > 0.20:
        magnitude_factor = 0.8
    elif magnitude > 0.10:
        magnitude_factor = 0.6
    else:
        magnitude_factor = 0.4

    return weight * magnitude_factor

def calculate_task_impact(task, context):
    """
    Task impact based on category and business value.
    """
    category_impact = {
        'fundraising': 1.0,
        'revenue': 0.95,
        'product': 0.8,
        'hiring': 0.75,
        'operations': 0.6,
        'admin': 0.3
    }

    category = task.get('category', 'operations')
    base_impact = category_impact.get(category, 0.5)

    # Boost for OKR-linked tasks
    if task.get('linked_to_okr'):
        base_impact = min(base_impact * 1.3, 1.0)

    return base_impact

def calculate_insight_impact(insight, context):
    """
    Insight impact based on recommendation type and potential value.
    """
    if insight.get('category') == 'financial':
        return 0.9
    elif insight.get('category') == 'strategic':
        return 0.85
    elif insight.get('category') == 'operational':
        return 0.7
    else:
        return 0.6
```

---

## 5. Relevance Scoring

### 5.1 Founder-Specific Relevance

```python
def calculate_relevance(item, context):
    """
    Calculate relevance to founder's current focus (0-1).
    """
    founder_profile = context.get('founder_profile', {})
    current_focus = founder_profile.get('current_focus', [])  # e.g., ['fundraising', 'product']

    # Match item to focus areas
    item_tags = item.get('tags', [])
    matches = len(set(item_tags) & set(current_focus))
    max_matches = max(len(current_focus), 1)
    focus_alignment = matches / max_matches

    # Department/role relevance
    if item.get('department') in founder_profile.get('direct_reports', []):
        dept_relevance = 1.0
    else:
        dept_relevance = 0.7

    # Weighted combination
    relevance = focus_alignment * 0.6 + dept_relevance * 0.4

    return relevance
```

---

## 6. Morning Brief Selection

### 6.1 Morning Brief Content Algorithm

```python
def select_morning_brief_content(founder_id, context):
    """
    Select and prioritize content for morning brief.

    Returns:
        Structured brief with sections
    """
    all_items = []

    # Section 1: Today's Urgent Tasks
    tasks = get_todays_tasks(founder_id)
    for task in tasks:
        task['type'] = 'task'
        task['score'] = calculate_content_score(task, context, 'morning')
        all_items.append(task)

    # Section 2: Critical Alerts
    anomalies = get_recent_anomalies(founder_id, hours=24)
    for anomaly in anomalies:
        anomaly['type'] = 'anomaly'
        anomaly['score'] = calculate_content_score(anomaly, context, 'morning')
        all_items.append(anomaly)

    # Section 3: Today's Meetings
    meetings = get_todays_meetings(founder_id)
    for meeting in meetings:
        meeting['type'] = 'meeting'
        meeting['score'] = calculate_content_score(meeting, context, 'morning')
        # Add context from past meetings with same attendees
        meeting['context'] = get_meeting_context(meeting)
        all_items.append(meeting)

    # Section 4: Important Messages
    messages = get_unread_messages(founder_id, limit=20)
    for message in messages:
        message['type'] = 'message'
        message['score'] = calculate_content_score(message, context, 'morning')
        all_items.append(message)

    # Section 5: KPI Snapshot
    kpis = get_kpi_snapshot(founder_id)
    kpis['type'] = 'kpi_snapshot'
    kpis['score'] = 70  # Fixed moderate priority

    # Sort all items by score
    all_items.sort(key=lambda x: x['score'], reverse=True)

    # Select top items with diversity
    selected = apply_selection_rules(all_items, max_total=7, max_per_type={
        'task': 3,
        'anomaly': 2,
        'meeting': 3,
        'message': 5
    })

    # Structure brief
    brief = {
        'title': 'Morning Brief',
        'timestamp': datetime.now(),
        'sections': {
            'urgent_tasks': [item for item in selected if item['type'] == 'task'][:3],
            'critical_alerts': [item for item in selected if item['type'] == 'anomaly'][:2],
            'todays_meetings': [item for item in selected if item['type'] == 'meeting'][:3],
            'important_messages': [item for item in selected if item['type'] == 'message'][:5],
            'kpi_snapshot': kpis
        },
        'estimated_read_time': calculate_read_time(selected)
    }

    return brief

def apply_selection_rules(items, max_total, max_per_type):
    """
    Select items with diversity constraints.
    """
    selected = []
    type_counts = {t: 0 for t in max_per_type.keys()}

    for item in items:
        item_type = item['type']

        # Check constraints
        if len(selected) >= max_total:
            break
        if type_counts.get(item_type, 0) >= max_per_type.get(item_type, max_total):
            continue

        selected.append(item)
        type_counts[item_type] = type_counts.get(item_type, 0) + 1

    return selected
```

---

## 7. Evening Wrap Selection

### 7.1 Evening Wrap Content Algorithm

```python
def select_evening_wrap_content(founder_id, context):
    """
    Select and prioritize content for evening wrap.
    """
    all_items = []

    # Section 1: Today's Accomplishments
    completed_tasks = get_completed_tasks_today(founder_id)
    task_summary = {
        'type': 'accomplishment',
        'completed_count': len(completed_tasks),
        'top_completed': completed_tasks[:3],
        'score': 80
    }
    all_items.append(task_summary)

    # Section 2: New Insights
    insights = get_insights_generated_today(founder_id)
    for insight in insights:
        insight['type'] = 'insight'
        insight['score'] = calculate_content_score(insight, context, 'evening')
        all_items.append(insight)

    # Section 3: Decisions Made
    decisions = get_decisions_from_meetings_today(founder_id)
    for decision in decisions:
        decision['type'] = 'decision'
        decision['score'] = 85  # Decisions are always high priority
        all_items.append(decision)

    # Section 4: Sentiment Trajectory
    sentiment = calculate_daily_sentiment_summary(founder_id)
    sentiment['type'] = 'sentiment'
    sentiment['score'] = 70
    all_items.append(sentiment)

    # Section 5: Tomorrow's Priorities
    tomorrow_tasks = get_tomorrows_top_tasks(founder_id)
    for task in tomorrow_tasks[:3]:
        task['type'] = 'tomorrow_prep'
        task['score'] = calculate_content_score(task, context, 'evening')
        all_items.append(task)

    # Sort and select
    all_items.sort(key=lambda x: x['score'], reverse=True)
    selected = all_items[:7]

    brief = {
        'title': 'Evening Wrap',
        'timestamp': datetime.now(),
        'sections': {
            'accomplishments': task_summary,
            'insights': [item for item in selected if item['type'] == 'insight'][:2],
            'decisions': [item for item in selected if item['type'] == 'decision'][:2],
            'sentiment': sentiment,
            'tomorrow_prep': [item for item in selected if item['type'] == 'tomorrow_prep'][:3]
        },
        'estimated_read_time': calculate_read_time(selected)
    }

    return brief
```

---

## 8. Length Optimization

### 8.1 Read Time Calculation

```python
def calculate_read_time(content_items):
    """
    Estimate reading time for selected content.

    Average reading speed: 200 words per minute
    Target: 60-90 seconds = 200-300 words
    """
    total_words = 0

    for item in content_items:
        if item['type'] == 'task':
            total_words += 15  # Task title + context
        elif item['type'] == 'anomaly':
            total_words += 25  # Description + explanation
        elif item['type'] == 'meeting':
            total_words += 30  # Meeting + context
        elif item['type'] == 'message':
            total_words += 20  # Sender + summary
        elif item['type'] == 'insight':
            total_words += 40  # Recommendation summary
        elif item['type'] == 'kpi_snapshot':
            total_words += 30  # 5-6 KPIs with values

    read_time_seconds = (total_words / 200) * 60

    return {
        'estimated_seconds': int(read_time_seconds),
        'total_words': total_words,
        'within_target': 60 <= read_time_seconds <= 90
    }

def trim_to_target_length(content_items, target_seconds=75):
    """
    Remove lowest-priority items to fit target length.
    """
    current_time = calculate_read_time(content_items)['estimated_seconds']

    while current_time > target_seconds and len(content_items) > 3:
        # Remove lowest-scoring item
        lowest = min(content_items, key=lambda x: x['score'])
        content_items.remove(lowest)
        current_time = calculate_read_time(content_items)['estimated_seconds']

    return content_items
```

---

## 9. Personalization & Learning

### 9.1 Engagement-Based Personalization

```python
class BriefingPersonalizer:
    def __init__(self, founder_id):
        self.founder_id = founder_id
        self.engagement_history = self.load_engagement_history()

    def adjust_scores_by_engagement(self, items):
        """
        Adjust content scores based on historical engagement.
        """
        for item in items:
            item_type = item['type']
            category = item.get('category', 'general')

            # Get historical click-through rate for this type/category
            ctr = self.get_engagement_rate(item_type, category)

            # Adjust score
            engagement_multiplier = 0.8 + (ctr * 0.4)  # 0.8 to 1.2 range
            item['score'] *= engagement_multiplier

        return items

    def get_engagement_rate(self, item_type, category):
        """
        Calculate engagement rate for item type/category.
        """
        history = self.engagement_history.get((item_type, category), {'shown': 0, 'clicked': 0})

        if history['shown'] < 10:
            return 0.5  # Default until enough data

        return history['clicked'] / history['shown']

    def record_engagement(self, item_id, item_type, category, engaged):
        """
        Record user engagement with briefing item.
        """
        # Update database
        db.briefing_engagement.insert({
            'founder_id': self.founder_id,
            'item_id': item_id,
            'item_type': item_type,
            'category': category,
            'engaged': engaged,
            'timestamp': datetime.now()
        })
```

---

## 10. Format & Presentation

### 10.1 Content Formatting

```python
def format_briefing(brief_data):
    """
    Format briefing for display (Markdown).
    """
    output = f"# {brief_data['title']}\n"
    output += f"*{brief_data['timestamp'].strftime('%A, %B %d, %Y at %I:%M %p')}*\n\n"

    if brief_data['title'] == 'Morning Brief':
        output += format_morning_brief(brief_data)
    else:
        output += format_evening_wrap(brief_data)

    # Add footer
    read_time = brief_data.get('estimated_read_time', {}).get('estimated_seconds', 60)
    output += f"\n\n---\n*Estimated read time: {read_time} seconds*\n"

    return output

def format_morning_brief(brief):
    """Format morning brief sections."""
    output = ""

    # Urgent Tasks
    if brief['sections'].get('urgent_tasks'):
        output += "## 🎯 Today's Priorities\n\n"
        for task in brief['sections']['urgent_tasks']:
            output += f"- **{task['title']}** "
            if task.get('due_time'):
                output += f"(due {task['due_time']})"
            output += "\n"
        output += "\n"

    # Critical Alerts
    if brief['sections'].get('critical_alerts'):
        output += "## 🚨 Critical Alerts\n\n"
        for alert in brief['sections']['critical_alerts']:
            icon = '📈' if alert.get('direction') == 'up' else '📉'
            output += f"{icon} **{alert['kpi_name']}:** {alert['explanation']}\n"
        output += "\n"

    # Today's Meetings
    if brief['sections'].get('todays_meetings'):
        output += "## 📅 Today's Meetings\n\n"
        for meeting in brief['sections']['todays_meetings']:
            time_str = meeting['start_time'].strftime('%I:%M %p')
            output += f"**{time_str}** - {meeting['title']}\n"
            if meeting.get('context'):
                output += f"  *Context: {meeting['context']}*\n"
        output += "\n"

    # KPI Snapshot
    if brief['sections'].get('kpi_snapshot'):
        output += "## 📊 KPI Snapshot\n\n"
        kpis = brief['sections']['kpi_snapshot']
        for kpi_name, kpi_value in list(kpis.items())[:5]:
            trend_icon = get_trend_icon(kpis.get(f'{kpi_name}_trend'))
            output += f"{trend_icon} **{kpi_name}:** {format_kpi_value(kpi_value)}\n"

    return output
```

---

## 11. Implementation Roadmap

**Week 1:** Basic scoring and selection algorithms
**Week 2:** Morning brief and evening wrap structures
**Week 3:** Personalization and engagement tracking
**Week 4:** Length optimization and formatting
**Week 5+:** A/B testing and continuous improvement

---

## 12. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Content Relevance | ≥90% | Founder rating on usefulness |
| Read Time Accuracy | ±15 seconds | Actual vs estimated |
| Engagement Rate | ≥75% | % of items clicked/acted upon |
| Briefing Completeness | 100% | Generated daily without errors |
| Load Time | <2 seconds | Time to generate brief |

---

## References

1. Miller, G. A. (1956). "The Magical Number Seven, Plus or Minus Two"
2. Kahneman, D. (2011). "Thinking, Fast and Slow"
3. Newport, C. (2016). "Deep Work: Rules for Focused Success"
