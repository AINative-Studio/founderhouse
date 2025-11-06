-- ========================================================================================
-- Migration: 005_insights_briefings.sql
-- Description: AI Chief of Staff - Insights & Briefings Engine Schema
-- Author: System Architect
-- Date: 2025-10-30
-- Sprint: 4 - Insights & Briefings Engine
--
-- This migration creates the database schema for:
-- - KPI metrics with time-series support
-- - Anomaly detection and storage
-- - Strategic recommendations
-- - Automated briefing generation
-- - Pattern recognition and correlation tracking
--
-- Dependencies:
-- - 001_initial_schema.sql
-- - 002_rls_policies.sql
-- - 003_mcp_extensions.sql
-- - 004_meeting_intelligence.sql
-- ========================================================================================

-- ========================================================================================
-- PART 1: ENUMS & TYPES
-- ========================================================================================

-- KPI metric categories
DO $$ BEGIN
  CREATE TYPE intel.kpi_category AS ENUM (
    'revenue',      -- Revenue metrics (MRR, ARR, etc.)
    'customer',     -- Customer metrics (CAC, LTV, churn, etc.)
    'growth',       -- Growth metrics (signups, active users, conversion)
    'financial',    -- Financial metrics (burn rate, runway, margin)
    'sales',        -- Sales metrics (pipeline, win rate, deal size)
    'product',      -- Product metrics (engagement, feature adoption)
    'marketing'     -- Marketing metrics (traffic, leads, CPL)
  );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- Time granularity for metrics
DO $$ BEGIN
  CREATE TYPE intel.time_granularity AS ENUM (
    'hourly',
    'daily',
    'weekly',
    'monthly',
    'quarterly',
    'yearly'
  );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- Anomaly severity levels
DO $$ BEGIN
  CREATE TYPE intel.anomaly_severity AS ENUM (
    'low',
    'medium',
    'high',
    'critical'
  );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- Recommendation impact levels
DO $$ BEGIN
  CREATE TYPE intel.impact_level AS ENUM (
    'low',
    'medium',
    'high'
  );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- Recommendation urgency levels
DO $$ BEGIN
  CREATE TYPE intel.urgency_level AS ENUM (
    'low',
    'medium',
    'high',
    'urgent'
  );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- Recommendation status
DO $$ BEGIN
  CREATE TYPE intel.recommendation_status AS ENUM (
    'active',       -- New recommendation
    'viewed',       -- Founder has seen it
    'acted_on',     -- Founder took action
    'dismissed',    -- Founder dismissed it
    'expired'       -- Auto-expired due to age
  );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

COMMENT ON TYPE intel.kpi_category IS 'Categories for KPI metrics classification';
COMMENT ON TYPE intel.time_granularity IS 'Time granularity for metric aggregation';
COMMENT ON TYPE intel.anomaly_severity IS 'Severity levels for detected anomalies';
COMMENT ON TYPE intel.impact_level IS 'Business impact level for recommendations';
COMMENT ON TYPE intel.urgency_level IS 'Urgency level for recommendations';
COMMENT ON TYPE intel.recommendation_status IS 'Lifecycle status of recommendations';

-- ========================================================================================
-- PART 2: KPI METRICS TABLE (TIME-SERIES)
-- ========================================================================================

CREATE TABLE IF NOT EXISTS intel.kpi_metrics (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id      uuid NOT NULL REFERENCES core.workspaces(id) ON DELETE CASCADE,
  founder_id        uuid NOT NULL REFERENCES core.founders(id) ON DELETE CASCADE,

  -- Metric identification
  metric_name       text NOT NULL,                   -- e.g., 'mrr', 'cac', 'churn_rate'
  metric_category   intel.kpi_category NOT NULL,
  metric_label      text,                             -- Human-readable label

  -- Metric value
  value             double precision NOT NULL,
  unit              text NOT NULL,                    -- 'USD', 'percent', 'count', etc.

  -- Temporal context
  timestamp         timestamptz NOT NULL,             -- When this metric was measured
  granularity       intel.time_granularity NOT NULL DEFAULT 'daily',

  -- Data source
  source            core.platform_enum NOT NULL,      -- 'granola', 'zerobooks', etc.
  source_id         text,                             -- External ID from source system

  -- Change tracking
  previous_value    double precision,                 -- Previous value for comparison
  change_absolute   double precision,                 -- Absolute change from previous
  change_percent    double precision,                 -- Percentage change from previous

  -- Quality & metadata
  confidence        double precision,                 -- Data confidence (0-1)
  is_forecast       boolean NOT NULL DEFAULT false,   -- Is this a forecasted value?
  is_target         boolean NOT NULL DEFAULT false,   -- Is this a target/goal?
  metadata          jsonb NOT NULL DEFAULT '{}'::jsonb,

  -- Versioning
  version           int NOT NULL DEFAULT 1,
  created_at        timestamptz NOT NULL DEFAULT now(),
  updated_at        timestamptz NOT NULL DEFAULT now(),

  -- Constraints
  CONSTRAINT kpi_metrics_value_check CHECK (
    -- Don't allow NaN or Infinity
    value = value AND value <> 'Infinity'::double precision
  ),
  CONSTRAINT kpi_metrics_confidence_check CHECK (
    confidence IS NULL OR (confidence >= 0 AND confidence <= 1)
  ),
  CONSTRAINT kpi_metrics_unique_metric UNIQUE (
    workspace_id, metric_name, timestamp, granularity, source
  )
);

-- Indexes for time-series queries
CREATE INDEX idx_kpi_metrics_workspace_metric_time
  ON intel.kpi_metrics(workspace_id, metric_name, timestamp DESC);

CREATE INDEX idx_kpi_metrics_founder_metric_time
  ON intel.kpi_metrics(founder_id, metric_name, timestamp DESC);

CREATE INDEX idx_kpi_metrics_category_time
  ON intel.kpi_metrics(workspace_id, metric_category, timestamp DESC);

CREATE INDEX idx_kpi_metrics_source
  ON intel.kpi_metrics(source, timestamp DESC);

CREATE INDEX idx_kpi_metrics_timestamp
  ON intel.kpi_metrics(timestamp DESC);

-- Index for change detection
CREATE INDEX idx_kpi_metrics_significant_changes
  ON intel.kpi_metrics(workspace_id, metric_name, abs(change_percent) DESC)
  WHERE change_percent IS NOT NULL AND abs(change_percent) >= 10;

-- Partial index for forecasts
CREATE INDEX idx_kpi_metrics_forecasts
  ON intel.kpi_metrics(workspace_id, metric_name, timestamp)
  WHERE is_forecast = true;

COMMENT ON TABLE intel.kpi_metrics IS 'Time-series KPI metrics from Granola, ZeroBooks, and calculated sources';
COMMENT ON COLUMN intel.kpi_metrics.metric_name IS 'Standardized metric name from KPI taxonomy';
COMMENT ON COLUMN intel.kpi_metrics.timestamp IS 'When this metric value was measured or recorded';
COMMENT ON COLUMN intel.kpi_metrics.granularity IS 'Time granularity: hourly, daily, weekly, monthly';
COMMENT ON COLUMN intel.kpi_metrics.change_percent IS 'Percentage change from previous value';
COMMENT ON COLUMN intel.kpi_metrics.is_forecast IS 'True if this is a forecasted/projected value';

-- ========================================================================================
-- PART 3: KPI DEFINITIONS (TAXONOMY)
-- ========================================================================================

CREATE TABLE IF NOT EXISTS intel.kpi_definitions (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id      uuid REFERENCES core.workspaces(id) ON DELETE CASCADE,  -- NULL for global

  -- Metric identification
  metric_name       text NOT NULL,
  metric_label      text NOT NULL,
  category          intel.kpi_category NOT NULL,
  description       text,

  -- Calculation
  formula           text,                             -- Human-readable formula
  calculation_logic jsonb,                           -- Structured calculation logic

  -- Validation rules
  unit              text NOT NULL,
  min_value         double precision,
  max_value         double precision,
  max_change_percent double precision,              -- Alert if change exceeds this

  -- Display
  format_string     text,                            -- e.g., "$%.2f", "%.1f%%"
  chart_type        text,                            -- 'line', 'bar', 'area'
  is_higher_better  boolean,                         -- True if higher values are better

  -- Metadata
  tags              text[] DEFAULT '{}',
  metadata          jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at        timestamptz NOT NULL DEFAULT now(),
  updated_at        timestamptz NOT NULL DEFAULT now(),

  CONSTRAINT kpi_definitions_unique UNIQUE (workspace_id, metric_name)
);

CREATE INDEX idx_kpi_definitions_workspace ON intel.kpi_definitions(workspace_id);
CREATE INDEX idx_kpi_definitions_category ON intel.kpi_definitions(category);
CREATE INDEX idx_kpi_definitions_tags ON intel.kpi_definitions USING GIN(tags);

COMMENT ON TABLE intel.kpi_definitions IS 'KPI metric definitions and calculation rules';
COMMENT ON COLUMN intel.kpi_definitions.workspace_id IS 'NULL for global definitions, set for workspace-specific custom KPIs';
COMMENT ON COLUMN intel.kpi_definitions.formula IS 'Human-readable formula description';
COMMENT ON COLUMN intel.kpi_definitions.calculation_logic IS 'Structured calculation logic for automated computation';

-- ========================================================================================
-- PART 4: KPI AGGREGATIONS (MATERIALIZED VIEW)
-- ========================================================================================

-- Daily aggregations for fast queries
CREATE TABLE IF NOT EXISTS intel.kpi_metrics_daily_agg (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id      uuid NOT NULL REFERENCES core.workspaces(id) ON DELETE CASCADE,
  founder_id        uuid NOT NULL REFERENCES core.founders(id) ON DELETE CASCADE,
  metric_name       text NOT NULL,
  metric_category   intel.kpi_category NOT NULL,
  date              date NOT NULL,

  -- Aggregated values
  avg_value         double precision,
  min_value         double precision,
  max_value         double precision,
  sum_value         double precision,
  stddev_value      double precision,
  median_value      double precision,
  sample_count      int NOT NULL,

  -- Units and metadata
  unit              text NOT NULL,
  sources           text[] DEFAULT '{}',              -- List of source platforms

  computed_at       timestamptz NOT NULL DEFAULT now(),

  CONSTRAINT kpi_daily_agg_unique UNIQUE (workspace_id, metric_name, date)
);

CREATE INDEX idx_kpi_daily_agg_workspace_metric_date
  ON intel.kpi_metrics_daily_agg(workspace_id, metric_name, date DESC);

CREATE INDEX idx_kpi_daily_agg_founder_metric_date
  ON intel.kpi_metrics_daily_agg(founder_id, metric_name, date DESC);

COMMENT ON TABLE intel.kpi_metrics_daily_agg IS 'Pre-aggregated daily KPI metrics for fast querying';

-- ========================================================================================
-- PART 5: ANOMALIES TABLE
-- ========================================================================================

CREATE TABLE IF NOT EXISTS intel.anomalies (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id      uuid NOT NULL REFERENCES core.workspaces(id) ON DELETE CASCADE,
  founder_id        uuid NOT NULL REFERENCES core.founders(id) ON DELETE CASCADE,

  -- Linked KPI metric
  metric_id         uuid REFERENCES intel.kpi_metrics(id) ON DELETE CASCADE,
  metric_name       text NOT NULL,

  -- Anomaly details
  current_value     double precision NOT NULL,
  expected_value    double precision,
  deviation         double precision,                 -- Absolute deviation
  deviation_percent double precision,                 -- Percentage deviation

  -- Detection
  detection_methods text[] NOT NULL DEFAULT '{}',     -- ['z_score', 'iqr', 'stl', 'trend']
  confidence        double precision NOT NULL,        -- 0.0 to 1.0
  severity          intel.anomaly_severity NOT NULL,

  -- Timing
  detected_at       timestamptz NOT NULL DEFAULT now(),
  occurred_at       timestamptz NOT NULL,             -- When the anomaly occurred

  -- Context
  title             text,
  description       text,
  details           jsonb NOT NULL DEFAULT '{}'::jsonb,  -- Detection method details

  -- Status
  status            text NOT NULL DEFAULT 'active',   -- 'active', 'acknowledged', 'resolved', 'false_positive'
  acknowledged_at   timestamptz,
  acknowledged_by   uuid REFERENCES core.members(id),
  resolution_notes  text,

  -- Metadata
  metadata          jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at        timestamptz NOT NULL DEFAULT now(),

  CONSTRAINT anomalies_confidence_check CHECK (confidence >= 0 AND confidence <= 1),
  CONSTRAINT anomalies_status_check CHECK (
    status IN ('active', 'acknowledged', 'resolved', 'false_positive', 'suppressed')
  )
);

CREATE INDEX idx_anomalies_workspace_metric
  ON intel.anomalies(workspace_id, metric_name, occurred_at DESC);

CREATE INDEX idx_anomalies_founder
  ON intel.anomalies(founder_id, occurred_at DESC);

CREATE INDEX idx_anomalies_severity
  ON intel.anomalies(workspace_id, severity, occurred_at DESC)
  WHERE status = 'active';

CREATE INDEX idx_anomalies_active
  ON intel.anomalies(workspace_id, occurred_at DESC)
  WHERE status = 'active';

CREATE INDEX idx_anomalies_metric_id
  ON intel.anomalies(metric_id)
  WHERE metric_id IS NOT NULL;

COMMENT ON TABLE intel.anomalies IS 'Detected anomalies in KPI metrics using ensemble detection methods';
COMMENT ON COLUMN intel.anomalies.detection_methods IS 'Array of detection methods that flagged this anomaly';
COMMENT ON COLUMN intel.anomalies.confidence IS 'Detection confidence based on method agreement (0-1)';
COMMENT ON COLUMN intel.anomalies.details IS 'Method-specific detection details (z-scores, thresholds, etc.)';

-- ========================================================================================
-- PART 6: PATTERNS TABLE
-- ========================================================================================

CREATE TABLE IF NOT EXISTS intel.patterns (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id      uuid NOT NULL REFERENCES core.workspaces(id) ON DELETE CASCADE,
  founder_id        uuid NOT NULL REFERENCES core.founders(id) ON DELETE CASCADE,

  -- Pattern identification
  pattern_type      text NOT NULL,                    -- 'kpi_sentiment_correlation', 'kpi_meeting_correlation', etc.
  title             text NOT NULL,
  description       text,

  -- Pattern data
  source_entities   jsonb NOT NULL,                   -- Array of source entity references
  correlation_strength double precision NOT NULL,     -- 0.0 to 1.0
  confidence        double precision NOT NULL,        -- 0.0 to 1.0

  -- Temporal context
  period_start      timestamptz NOT NULL,
  period_end        timestamptz NOT NULL,
  detected_at       timestamptz NOT NULL DEFAULT now(),

  -- Details
  details           jsonb NOT NULL DEFAULT '{}'::jsonb,
  insights          text[],                           -- Key insights from pattern

  -- Status
  status            text NOT NULL DEFAULT 'active',   -- 'active', 'expired', 'dismissed'

  metadata          jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at        timestamptz NOT NULL DEFAULT now(),

  CONSTRAINT patterns_correlation_check CHECK (
    correlation_strength >= 0 AND correlation_strength <= 1
  ),
  CONSTRAINT patterns_confidence_check CHECK (
    confidence >= 0 AND confidence <= 1
  )
);

CREATE INDEX idx_patterns_workspace_type
  ON intel.patterns(workspace_id, pattern_type, detected_at DESC);

CREATE INDEX idx_patterns_founder
  ON intel.patterns(founder_id, detected_at DESC);

CREATE INDEX idx_patterns_active
  ON intel.patterns(workspace_id, detected_at DESC)
  WHERE status = 'active';

CREATE INDEX idx_patterns_period
  ON intel.patterns(workspace_id, period_start, period_end);

COMMENT ON TABLE intel.patterns IS 'Detected patterns across KPIs, communications, and meetings';
COMMENT ON COLUMN intel.patterns.source_entities IS 'References to entities involved in pattern (KPIs, communications, meetings)';
COMMENT ON COLUMN intel.patterns.correlation_strength IS 'Strength of correlation between entities (0-1)';

-- ========================================================================================
-- PART 7: RECOMMENDATIONS TABLE
-- ========================================================================================

CREATE TABLE IF NOT EXISTS intel.recommendations (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id      uuid NOT NULL REFERENCES core.workspaces(id) ON DELETE CASCADE,
  founder_id        uuid NOT NULL REFERENCES core.founders(id) ON DELETE CASCADE,

  -- Recommendation content
  title             text NOT NULL,
  summary           text NOT NULL,
  details           text,
  reasoning         text,

  -- Action items
  action_items      jsonb NOT NULL DEFAULT '[]'::jsonb,  -- Array of specific actions

  -- Scoring
  confidence        double precision NOT NULL,        -- LLM confidence (0-1)
  impact            intel.impact_level NOT NULL,
  urgency           intel.urgency_level NOT NULL,
  actionability_score double precision,               -- How concrete/actionable (0-1)
  impact_score      double precision,                 -- Estimated business impact (0-1)

  -- Data sources
  data_sources      text[] DEFAULT '{}',              -- ['kpi:mrr', 'pattern:churn_sentiment', etc.]
  linked_entities   jsonb NOT NULL DEFAULT '{}'::jsonb,  -- References to KPIs, anomalies, patterns

  -- Status tracking
  status            intel.recommendation_status NOT NULL DEFAULT 'active',
  viewed_at         timestamptz,
  acted_on_at       timestamptz,
  dismissed_at      timestamptz,
  dismissal_reason  text,

  -- Outcome tracking
  outcome           text,                              -- What happened after action
  outcome_impact    text,                              -- Measured impact of action

  -- Embedding for deduplication
  embedding         vector(1536),

  -- Metadata
  metadata          jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at        timestamptz NOT NULL DEFAULT now(),
  updated_at        timestamptz NOT NULL DEFAULT now(),
  expires_at        timestamptz,                       -- Auto-expire old recommendations

  CONSTRAINT recommendations_confidence_check CHECK (confidence >= 0 AND confidence <= 1),
  CONSTRAINT recommendations_actionability_check CHECK (
    actionability_score IS NULL OR (actionability_score >= 0 AND actionability_score <= 1)
  ),
  CONSTRAINT recommendations_impact_score_check CHECK (
    impact_score IS NULL OR (impact_score >= 0 AND impact_score <= 1)
  )
);

CREATE INDEX idx_recommendations_workspace_status
  ON intel.recommendations(workspace_id, status, created_at DESC);

CREATE INDEX idx_recommendations_founder
  ON intel.recommendations(founder_id, created_at DESC);

CREATE INDEX idx_recommendations_active
  ON intel.recommendations(workspace_id, impact, urgency, created_at DESC)
  WHERE status = 'active';

CREATE INDEX idx_recommendations_data_sources
  ON intel.recommendations USING GIN(data_sources);

-- Vector similarity search for deduplication
CREATE INDEX idx_recommendations_embedding
  ON intel.recommendations USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100)
  WHERE embedding IS NOT NULL;

COMMENT ON TABLE intel.recommendations IS 'AI-generated strategic recommendations based on patterns and anomalies';
COMMENT ON COLUMN intel.recommendations.action_items IS 'Array of specific, actionable steps';
COMMENT ON COLUMN intel.recommendations.data_sources IS 'References to data that informed this recommendation';
COMMENT ON COLUMN intel.recommendations.embedding IS 'Vector embedding for semantic deduplication';
COMMENT ON COLUMN intel.recommendations.actionability_score IS 'How concrete and executable (0-1)';
COMMENT ON COLUMN intel.recommendations.impact_score IS 'Estimated business impact (0-1)';

-- ========================================================================================
-- PART 8: EXTEND BRIEFINGS TABLE
-- ========================================================================================

-- Add new columns to existing intel.briefings table
ALTER TABLE intel.briefings
  ADD COLUMN IF NOT EXISTS delivery_channels text[] DEFAULT '{}',
  ADD COLUMN IF NOT EXISTS delivery_status jsonb NOT NULL DEFAULT '{}'::jsonb,
  ADD COLUMN IF NOT EXISTS delivered_at timestamptz,
  ADD COLUMN IF NOT EXISTS viewed_at timestamptz,
  ADD COLUMN IF NOT EXISTS preferences jsonb NOT NULL DEFAULT '{}'::jsonb;

-- Add index for delivery tracking
CREATE INDEX IF NOT EXISTS idx_briefings_delivery
  ON intel.briefings(workspace_id, founder_id, kind, delivered_at DESC);

CREATE INDEX IF NOT EXISTS idx_briefings_undelivered
  ON intel.briefings(workspace_id, kind, generated_at DESC)
  WHERE delivered_at IS NULL;

COMMENT ON COLUMN intel.briefings.delivery_channels IS 'Channels used for delivery: slack, discord, email';
COMMENT ON COLUMN intel.briefings.delivery_status IS 'Delivery status per channel';
COMMENT ON COLUMN intel.briefings.preferences IS 'Briefing-specific preferences and customizations';

-- ========================================================================================
-- PART 9: VIEWS FOR INSIGHTS DASHBOARD
-- ========================================================================================

-- View: Latest KPI values per metric
CREATE OR REPLACE VIEW intel.v_latest_kpis AS
SELECT DISTINCT ON (workspace_id, founder_id, metric_name)
  id,
  workspace_id,
  founder_id,
  metric_name,
  metric_category,
  metric_label,
  value,
  unit,
  timestamp,
  previous_value,
  change_percent,
  change_absolute,
  source,
  confidence
FROM intel.kpi_metrics
WHERE is_forecast = false
ORDER BY workspace_id, founder_id, metric_name, timestamp DESC;

COMMENT ON VIEW intel.v_latest_kpis IS 'Latest actual (non-forecast) KPI values per metric';

-- View: Active anomalies summary
CREATE OR REPLACE VIEW intel.v_active_anomalies AS
SELECT
  a.id,
  a.workspace_id,
  a.founder_id,
  a.metric_name,
  a.current_value,
  a.expected_value,
  a.deviation_percent,
  a.severity,
  a.confidence,
  a.detected_at,
  a.occurred_at,
  a.title,
  a.description,
  k.unit,
  k.metric_category
FROM intel.anomalies a
LEFT JOIN intel.kpi_metrics k ON a.metric_id = k.id
WHERE a.status = 'active'
ORDER BY a.severity DESC, a.occurred_at DESC;

COMMENT ON VIEW intel.v_active_anomalies IS 'Active anomalies with metric context';

-- View: Actionable recommendations
CREATE OR REPLACE VIEW intel.v_actionable_recommendations AS
SELECT
  r.id,
  r.workspace_id,
  r.founder_id,
  r.title,
  r.summary,
  r.action_items,
  r.confidence,
  r.impact,
  r.urgency,
  r.actionability_score,
  r.impact_score,
  r.data_sources,
  r.created_at,
  -- Priority score (weighted combination)
  (
    CASE r.impact
      WHEN 'high' THEN 0.5
      WHEN 'medium' THEN 0.3
      WHEN 'low' THEN 0.1
    END +
    CASE r.urgency
      WHEN 'urgent' THEN 0.4
      WHEN 'high' THEN 0.3
      WHEN 'medium' THEN 0.2
      WHEN 'low' THEN 0.1
    END +
    r.confidence * 0.1
  ) AS priority_score
FROM intel.recommendations r
WHERE r.status = 'active'
  AND r.actionability_score >= 0.5
  AND (r.expires_at IS NULL OR r.expires_at > now())
ORDER BY priority_score DESC, r.created_at DESC;

COMMENT ON VIEW intel.v_actionable_recommendations IS 'Active recommendations ranked by priority';

-- View: KPI trends (7-day comparison)
CREATE OR REPLACE VIEW intel.v_kpi_trends_7d AS
WITH latest AS (
  SELECT DISTINCT ON (workspace_id, metric_name)
    workspace_id,
    founder_id,
    metric_name,
    metric_category,
    value AS current_value,
    unit,
    timestamp AS current_timestamp
  FROM intel.kpi_metrics
  WHERE is_forecast = false
  ORDER BY workspace_id, metric_name, timestamp DESC
),
week_ago AS (
  SELECT DISTINCT ON (workspace_id, metric_name)
    workspace_id,
    metric_name,
    value AS week_ago_value,
    timestamp AS week_ago_timestamp
  FROM intel.kpi_metrics
  WHERE is_forecast = false
    AND timestamp <= now() - interval '7 days'
  ORDER BY workspace_id, metric_name, timestamp DESC
)
SELECT
  l.workspace_id,
  l.founder_id,
  l.metric_name,
  l.metric_category,
  l.current_value,
  w.week_ago_value,
  l.unit,
  l.current_timestamp,
  w.week_ago_timestamp,
  CASE
    WHEN w.week_ago_value IS NULL THEN NULL
    WHEN w.week_ago_value = 0 THEN NULL
    ELSE ((l.current_value - w.week_ago_value) / w.week_ago_value * 100)
  END AS wow_change_percent,
  CASE
    WHEN w.week_ago_value IS NULL THEN NULL
    ELSE l.current_value - w.week_ago_value
  END AS wow_change_absolute,
  CASE
    WHEN w.week_ago_value IS NULL THEN 'insufficient_data'
    WHEN abs((l.current_value - w.week_ago_value) / NULLIF(w.week_ago_value, 0) * 100) >= 10 THEN 'significant'
    ELSE 'stable'
  END AS trend_status
FROM latest l
LEFT JOIN week_ago w ON l.workspace_id = w.workspace_id AND l.metric_name = w.metric_name;

COMMENT ON VIEW intel.v_kpi_trends_7d IS 'Week-over-week KPI trends with significance flagging';

-- ========================================================================================
-- PART 10: FUNCTIONS FOR KPI PROCESSING
-- ========================================================================================

-- Function: Calculate KPI aggregations
CREATE OR REPLACE FUNCTION intel.refresh_kpi_daily_aggregations(
  p_workspace_id uuid DEFAULT NULL,
  p_date date DEFAULT CURRENT_DATE
)
RETURNS int AS $$
DECLARE
  v_rows_inserted int;
BEGIN
  -- Delete existing aggregations for the date
  DELETE FROM intel.kpi_metrics_daily_agg
  WHERE (p_workspace_id IS NULL OR workspace_id = p_workspace_id)
    AND date = p_date;

  -- Insert new aggregations
  INSERT INTO intel.kpi_metrics_daily_agg (
    workspace_id,
    founder_id,
    metric_name,
    metric_category,
    date,
    avg_value,
    min_value,
    max_value,
    sum_value,
    stddev_value,
    median_value,
    sample_count,
    unit,
    sources
  )
  SELECT
    workspace_id,
    founder_id,
    metric_name,
    metric_category,
    DATE(timestamp) AS date,
    AVG(value) AS avg_value,
    MIN(value) AS min_value,
    MAX(value) AS max_value,
    SUM(value) AS sum_value,
    STDDEV(value) AS stddev_value,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY value) AS median_value,
    COUNT(*) AS sample_count,
    -- Use the most common unit
    MODE() WITHIN GROUP (ORDER BY unit) AS unit,
    ARRAY_AGG(DISTINCT source::text) AS sources
  FROM intel.kpi_metrics
  WHERE (p_workspace_id IS NULL OR workspace_id = p_workspace_id)
    AND DATE(timestamp) = p_date
    AND is_forecast = false
  GROUP BY workspace_id, founder_id, metric_name, metric_category, DATE(timestamp);

  GET DIAGNOSTICS v_rows_inserted = ROW_COUNT;

  RETURN v_rows_inserted;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION intel.refresh_kpi_daily_aggregations IS 'Refresh daily KPI aggregations for specified workspace and date';

-- Function: Get KPI historical values for anomaly detection
CREATE OR REPLACE FUNCTION intel.get_kpi_history(
  p_workspace_id uuid,
  p_metric_name text,
  p_end_timestamp timestamptz,
  p_count int DEFAULT 30
)
RETURNS TABLE (
  timestamp timestamptz,
  value double precision
) AS $$
BEGIN
  RETURN QUERY
  SELECT
    k.timestamp,
    k.value
  FROM intel.kpi_metrics k
  WHERE k.workspace_id = p_workspace_id
    AND k.metric_name = p_metric_name
    AND k.timestamp <= p_end_timestamp
    AND k.is_forecast = false
  ORDER BY k.timestamp DESC
  LIMIT p_count;
END;
$$ LANGUAGE plpgsql STABLE;

COMMENT ON FUNCTION intel.get_kpi_history IS 'Get historical KPI values for anomaly detection algorithms';

-- Function: Find similar recommendations (for deduplication)
CREATE OR REPLACE FUNCTION intel.find_similar_recommendation(
  p_workspace_id uuid,
  p_embedding vector(1536),
  p_days int DEFAULT 7,
  p_threshold double precision DEFAULT 0.85
)
RETURNS TABLE (
  id uuid,
  title text,
  similarity double precision
) AS $$
BEGIN
  RETURN QUERY
  SELECT
    r.id,
    r.title,
    1 - (r.embedding <=> p_embedding) AS similarity
  FROM intel.recommendations r
  WHERE r.workspace_id = p_workspace_id
    AND r.embedding IS NOT NULL
    AND r.created_at >= now() - (p_days || ' days')::interval
    AND r.status IN ('active', 'viewed')
    AND 1 - (r.embedding <=> p_embedding) > p_threshold
  ORDER BY r.embedding <=> p_embedding
  LIMIT 1;
END;
$$ LANGUAGE plpgsql STABLE;

COMMENT ON FUNCTION intel.find_similar_recommendation IS 'Find semantically similar recommendations for deduplication';

-- ========================================================================================
-- PART 11: TRIGGERS
-- ========================================================================================

-- Trigger: Auto-update updated_at
CREATE TRIGGER update_kpi_metrics_updated_at
  BEFORE UPDATE ON intel.kpi_metrics
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_kpi_definitions_updated_at
  BEFORE UPDATE ON intel.kpi_definitions
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_recommendations_updated_at
  BEFORE UPDATE ON intel.recommendations
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

-- Trigger: Log recommendation status changes
CREATE OR REPLACE FUNCTION intel.log_recommendation_status_change()
RETURNS TRIGGER AS $$
BEGIN
  IF OLD.status IS DISTINCT FROM NEW.status THEN
    INSERT INTO ops.events (
      workspace_id,
      actor_type,
      actor_id,
      event_type,
      entity_type,
      entity_id,
      payload
    ) VALUES (
      NEW.workspace_id,
      'founder',
      NEW.founder_id,
      'recommendation.status_change',
      'recommendation',
      NEW.id,
      jsonb_build_object(
        'title', NEW.title,
        'old_status', OLD.status,
        'new_status', NEW.status,
        'impact', NEW.impact,
        'urgency', NEW.urgency
      )
    );
  END IF;

  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER recommendation_status_change_logger
  AFTER UPDATE ON intel.recommendations
  FOR EACH ROW
  EXECUTE FUNCTION intel.log_recommendation_status_change();

-- Trigger: Log anomaly acknowledgment
CREATE OR REPLACE FUNCTION intel.log_anomaly_acknowledgment()
RETURNS TRIGGER AS $$
BEGIN
  IF OLD.status IS DISTINCT FROM NEW.status AND NEW.status = 'acknowledged' THEN
    INSERT INTO ops.events (
      workspace_id,
      actor_type,
      actor_id,
      event_type,
      entity_type,
      entity_id,
      payload
    ) VALUES (
      NEW.workspace_id,
      'member',
      NEW.acknowledged_by,
      'anomaly.acknowledged',
      'anomaly',
      NEW.id,
      jsonb_build_object(
        'metric_name', NEW.metric_name,
        'severity', NEW.severity,
        'deviation_percent', NEW.deviation_percent
      )
    );
  END IF;

  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER anomaly_acknowledgment_logger
  AFTER UPDATE ON intel.anomalies
  FOR EACH ROW
  EXECUTE FUNCTION intel.log_anomaly_acknowledgment();

-- ========================================================================================
-- PART 12: INITIAL DATA - KPI DEFINITIONS
-- ========================================================================================

-- Insert standard KPI definitions (global, workspace_id = NULL)
INSERT INTO intel.kpi_definitions (
  workspace_id,
  metric_name,
  metric_label,
  category,
  description,
  unit,
  min_value,
  max_value,
  max_change_percent,
  format_string,
  chart_type,
  is_higher_better
) VALUES
  -- Revenue metrics
  (NULL, 'mrr', 'Monthly Recurring Revenue', 'revenue',
   'Total monthly recurring revenue from subscriptions', 'USD', 0, NULL, 100, '$%.2f', 'line', true),
  (NULL, 'arr', 'Annual Recurring Revenue', 'revenue',
   'Total annual recurring revenue (MRR × 12)', 'USD', 0, NULL, 100, '$%.2f', 'line', true),
  (NULL, 'revenue', 'Total Revenue', 'revenue',
   'Total revenue including one-time and recurring', 'USD', 0, NULL, 100, '$%.2f', 'line', true),
  (NULL, 'revenue_growth_rate', 'Revenue Growth Rate', 'revenue',
   'Month-over-month revenue growth rate', 'percent', -100, 1000, 50, '%.1f%%', 'line', true),

  -- Customer metrics
  (NULL, 'cac', 'Customer Acquisition Cost', 'customer',
   'Total sales and marketing cost per new customer', 'USD', 0, 10000, 200, '$%.2f', 'line', false),
  (NULL, 'ltv', 'Customer Lifetime Value', 'customer',
   'Average revenue per customer over lifetime', 'USD', 0, NULL, 100, '$%.2f', 'line', true),
  (NULL, 'ltv_cac_ratio', 'LTV:CAC Ratio', 'customer',
   'Lifetime value to customer acquisition cost ratio', 'ratio', 0, 20, 50, '%.1f:1', 'line', true),
  (NULL, 'churn_rate', 'Churn Rate', 'customer',
   'Percentage of customers lost per month', 'percent', 0, 100, 50, '%.1f%%', 'line', false),
  (NULL, 'retention_rate', 'Retention Rate', 'customer',
   'Percentage of customers retained per month', 'percent', 0, 100, 20, '%.1f%%', 'line', true),
  (NULL, 'nps', 'Net Promoter Score', 'customer',
   'Customer satisfaction and loyalty metric', 'score', -100, 100, 30, '%.0f', 'line', true),

  -- Growth metrics
  (NULL, 'signups', 'User Signups', 'growth',
   'New user registrations', 'count', 0, NULL, 200, '%.0f', 'bar', true),
  (NULL, 'dau', 'Daily Active Users', 'growth',
   'Unique active users per day', 'count', 0, NULL, 100, '%.0f', 'line', true),
  (NULL, 'mau', 'Monthly Active Users', 'growth',
   'Unique active users per month', 'count', 0, NULL, 100, '%.0f', 'line', true),
  (NULL, 'conversion_rate', 'Conversion Rate', 'growth',
   'Percentage of visitors who convert to customers', 'percent', 0, 100, 50, '%.1f%%', 'line', true),
  (NULL, 'activation_rate', 'Activation Rate', 'growth',
   'Percentage of signups who complete activation', 'percent', 0, 100, 30, '%.1f%%', 'line', true),

  -- Financial metrics
  (NULL, 'burn_rate', 'Burn Rate', 'financial',
   'Monthly cash burn (expenses - revenue)', 'USD', 0, NULL, 100, '$%.2f', 'line', false),
  (NULL, 'runway', 'Runway', 'financial',
   'Months of cash remaining at current burn rate', 'months', 0, 120, 50, '%.1f months', 'line', true),
  (NULL, 'cash_balance', 'Cash Balance', 'financial',
   'Current cash and cash equivalents', 'USD', 0, NULL, 100, '$%.2f', 'line', true),
  (NULL, 'gross_margin', 'Gross Margin', 'financial',
   'Gross profit as percentage of revenue', 'percent', 0, 100, 20, '%.1f%%', 'line', true),
  (NULL, 'operating_expenses', 'Operating Expenses', 'financial',
   'Total operating expenses', 'USD', 0, NULL, 100, '$%.2f', 'line', false),

  -- Sales metrics
  (NULL, 'pipeline_value', 'Pipeline Value', 'sales',
   'Total value of sales pipeline', 'USD', 0, NULL, 100, '$%.2f', 'line', true),
  (NULL, 'win_rate', 'Win Rate', 'sales',
   'Percentage of deals won', 'percent', 0, 100, 30, '%.1f%%', 'line', true),
  (NULL, 'avg_deal_size', 'Average Deal Size', 'sales',
   'Average value per closed deal', 'USD', 0, NULL, 100, '$%.2f', 'line', true),
  (NULL, 'sales_cycle', 'Sales Cycle Length', 'sales',
   'Average days from lead to close', 'days', 0, 365, 50, '%.0f days', 'line', false)
ON CONFLICT (workspace_id, metric_name) DO NOTHING;

-- ========================================================================================
-- PART 13: MIGRATION METADATA
-- ========================================================================================

INSERT INTO public.schema_migrations (version, description)
VALUES ('005', 'Insights & Briefings Engine - KPIs, Anomalies, Recommendations, Patterns')
ON CONFLICT (version) DO NOTHING;

-- ========================================================================================
-- END OF MIGRATION 005_insights_briefings.sql
-- ========================================================================================
