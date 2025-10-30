-- ========================================================================================
-- Migration: 003_mcp_extensions.sql
-- Description: AI Chief of Staff - MCP Integration Framework Extensions
-- Author: System Architect
-- Date: 2025-10-30
-- Sprint: 2 - MCP Integration Framework
--
-- This migration extends the database schema to support:
-- - Enhanced OAuth token storage and encryption
-- - Health monitoring and status tracking
-- - Integration state management
-- - Webhook registration and event handling
-- - Rate limiting and circuit breaker state
--
-- Dependencies:
-- - 001_initial_schema.sql
-- - 002_rls_policies.sql
-- ========================================================================================

-- ========================================================================================
-- PART 1: CREATE MCP SCHEMA
-- ========================================================================================

CREATE SCHEMA IF NOT EXISTS mcp;

COMMENT ON SCHEMA mcp IS 'MCP integration framework: OAuth, health checks, webhooks';

-- ========================================================================================
-- PART 2: EXTEND CORE.INTEGRATIONS TABLE
-- ========================================================================================

-- Add new columns for enhanced token management
ALTER TABLE core.integrations
  ADD COLUMN IF NOT EXISTS last_health_check timestamptz,
  ADD COLUMN IF NOT EXISTS health_status text DEFAULT 'unknown',
  ADD COLUMN IF NOT EXISTS consecutive_failures int DEFAULT 0,
  ADD COLUMN IF NOT EXISTS circuit_breaker_state text DEFAULT 'closed',
  ADD COLUMN IF NOT EXISTS circuit_breaker_opened_at timestamptz,
  ADD COLUMN IF NOT EXISTS scopes text[],
  ADD COLUMN IF NOT EXISTS webhook_id text,
  ADD COLUMN IF NOT EXISTS sync_cursor text;

-- Add constraints
DO $$ BEGIN
  ALTER TABLE core.integrations
    ADD CONSTRAINT integrations_health_status_check
    CHECK (health_status IN ('healthy', 'degraded', 'unhealthy', 'unknown'));
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE core.integrations
    ADD CONSTRAINT integrations_circuit_state_check
    CHECK (circuit_breaker_state IN ('closed', 'open', 'half_open'));
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- Add indexes for health monitoring queries
CREATE INDEX IF NOT EXISTS idx_integrations_health_status
  ON core.integrations(health_status, last_health_check)
  WHERE status = 'connected';

CREATE INDEX IF NOT EXISTS idx_integrations_circuit_state
  ON core.integrations(circuit_breaker_state)
  WHERE circuit_breaker_state != 'closed';

CREATE INDEX IF NOT EXISTS idx_integrations_failures
  ON core.integrations(consecutive_failures DESC)
  WHERE consecutive_failures > 0;

COMMENT ON COLUMN core.integrations.last_health_check IS 'Timestamp of last health check';
COMMENT ON COLUMN core.integrations.health_status IS 'Current health status: healthy, degraded, unhealthy, unknown';
COMMENT ON COLUMN core.integrations.consecutive_failures IS 'Number of consecutive health check failures';
COMMENT ON COLUMN core.integrations.circuit_breaker_state IS 'Circuit breaker state: closed, open, half_open';
COMMENT ON COLUMN core.integrations.circuit_breaker_opened_at IS 'When circuit breaker opened';
COMMENT ON COLUMN core.integrations.scopes IS 'OAuth scopes granted for this integration';
COMMENT ON COLUMN core.integrations.webhook_id IS 'Platform-specific webhook registration ID';
COMMENT ON COLUMN core.integrations.sync_cursor IS 'Cursor for incremental sync (platform-specific)';

-- ========================================================================================
-- PART 3: HEALTH CHECK HISTORY
-- ========================================================================================

CREATE TABLE IF NOT EXISTS mcp.health_checks (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  integration_id    uuid NOT NULL REFERENCES core.integrations(id) ON DELETE CASCADE,
  status            text NOT NULL,  -- 'healthy', 'degraded', 'unhealthy'
  response_time_ms  double precision,
  error_message     text,
  error_code        text,
  checked_at        timestamptz NOT NULL DEFAULT now(),
  details           jsonb NOT NULL DEFAULT '{}'::jsonb,

  CONSTRAINT health_checks_status_check CHECK (status IN ('healthy', 'degraded', 'unhealthy'))
);

CREATE INDEX idx_health_checks_integration_id
  ON mcp.health_checks(integration_id, checked_at DESC);

CREATE INDEX idx_health_checks_status
  ON mcp.health_checks(status, checked_at DESC);

CREATE INDEX idx_health_checks_checked_at
  ON mcp.health_checks(checked_at DESC);

-- Partitioning by month (for future scalability)
-- CREATE TABLE mcp.health_checks_2025_10 PARTITION OF mcp.health_checks
--   FOR VALUES FROM ('2025-10-01') TO ('2025-11-01');

COMMENT ON TABLE mcp.health_checks IS 'Historical health check results for integrations';
COMMENT ON COLUMN mcp.health_checks.response_time_ms IS 'Health check response time in milliseconds';
COMMENT ON COLUMN mcp.health_checks.details IS 'Additional platform-specific health check data';

-- ========================================================================================
-- PART 4: OAUTH TOKEN METADATA
-- ========================================================================================

CREATE TABLE IF NOT EXISTS mcp.oauth_tokens (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  integration_id    uuid NOT NULL REFERENCES core.integrations(id) ON DELETE CASCADE,
  token_type        text NOT NULL,  -- 'access', 'refresh', 'api_key'
  expires_at        timestamptz,
  issued_at         timestamptz NOT NULL DEFAULT now(),
  refreshed_at      timestamptz,
  scopes            text[],
  metadata          jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at        timestamptz NOT NULL DEFAULT now(),

  CONSTRAINT oauth_tokens_token_type_check
    CHECK (token_type IN ('access', 'refresh', 'api_key'))
);

CREATE INDEX idx_oauth_tokens_integration_id
  ON mcp.oauth_tokens(integration_id, token_type);

CREATE INDEX idx_oauth_tokens_expires_at
  ON mcp.oauth_tokens(expires_at)
  WHERE expires_at IS NOT NULL AND expires_at > now();

-- Tokens expiring within 24 hours (for refresh scheduler)
CREATE INDEX idx_oauth_tokens_expiring_soon
  ON mcp.oauth_tokens(integration_id, expires_at)
  WHERE expires_at IS NOT NULL
    AND expires_at <= now() + interval '24 hours'
    AND expires_at > now();

COMMENT ON TABLE mcp.oauth_tokens IS 'OAuth token metadata (actual tokens encrypted in core.integrations)';
COMMENT ON COLUMN mcp.oauth_tokens.token_type IS 'Type of token: access, refresh, api_key';
COMMENT ON COLUMN mcp.oauth_tokens.refreshed_at IS 'Last time this token was refreshed';

-- ========================================================================================
-- PART 5: WEBHOOK REGISTRATIONS
-- ========================================================================================

CREATE TABLE IF NOT EXISTS mcp.webhooks (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  integration_id    uuid NOT NULL REFERENCES core.integrations(id) ON DELETE CASCADE,
  external_id       text,  -- Platform's webhook ID
  callback_url      text NOT NULL,
  events            text[] NOT NULL DEFAULT '{}',  -- Events subscribed to
  secret            text,  -- Webhook signing secret (encrypted)
  status            text NOT NULL DEFAULT 'active',
  last_received_at  timestamptz,
  registered_at     timestamptz NOT NULL DEFAULT now(),
  expires_at        timestamptz,
  metadata          jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at        timestamptz NOT NULL DEFAULT now(),

  CONSTRAINT webhooks_status_check CHECK (status IN ('active', 'paused', 'failed', 'expired'))
);

CREATE INDEX idx_webhooks_integration_id ON mcp.webhooks(integration_id);
CREATE INDEX idx_webhooks_status ON mcp.webhooks(status) WHERE status = 'active';

COMMENT ON TABLE mcp.webhooks IS 'Webhook registrations for real-time event delivery';
COMMENT ON COLUMN mcp.webhooks.events IS 'Array of event types this webhook is subscribed to';
COMMENT ON COLUMN mcp.webhooks.secret IS 'Encrypted webhook signing secret for verification';

-- ========================================================================================
-- PART 6: WEBHOOK EVENTS (RECEIVED)
-- ========================================================================================

CREATE TABLE IF NOT EXISTS mcp.webhook_events (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  webhook_id        uuid REFERENCES mcp.webhooks(id) ON DELETE SET NULL,
  integration_id    uuid NOT NULL REFERENCES core.integrations(id) ON DELETE CASCADE,
  event_type        text NOT NULL,
  payload           jsonb NOT NULL,
  signature         text,  -- Webhook signature for verification
  verified          boolean NOT NULL DEFAULT false,
  processed         boolean NOT NULL DEFAULT false,
  processed_at      timestamptz,
  error_message     text,
  received_at       timestamptz NOT NULL DEFAULT now(),
  created_at        timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_webhook_events_integration_id
  ON mcp.webhook_events(integration_id, received_at DESC);

CREATE INDEX idx_webhook_events_unprocessed
  ON mcp.webhook_events(received_at)
  WHERE processed = false;

CREATE INDEX idx_webhook_events_event_type
  ON mcp.webhook_events(integration_id, event_type, received_at DESC);

COMMENT ON TABLE mcp.webhook_events IS 'Incoming webhook events from integrated platforms';
COMMENT ON COLUMN mcp.webhook_events.verified IS 'Whether webhook signature was verified';
COMMENT ON COLUMN mcp.webhook_events.processed IS 'Whether event has been processed by application';

-- ========================================================================================
-- PART 7: RATE LIMITING STATE
-- ========================================================================================

CREATE TABLE IF NOT EXISTS mcp.rate_limits (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  integration_id    uuid NOT NULL REFERENCES core.integrations(id) ON DELETE CASCADE,
  endpoint          text NOT NULL,  -- API endpoint or operation
  limit_type        text NOT NULL,  -- 'per_minute', 'per_hour', 'per_day'
  max_requests      int NOT NULL,
  current_count     int NOT NULL DEFAULT 0,
  window_start      timestamptz NOT NULL DEFAULT now(),
  window_end        timestamptz NOT NULL,
  reset_at          timestamptz,
  metadata          jsonb NOT NULL DEFAULT '{}'::jsonb,

  CONSTRAINT rate_limits_unique_window
    UNIQUE (integration_id, endpoint, limit_type, window_start),
  CONSTRAINT rate_limits_limit_type_check
    CHECK (limit_type IN ('per_second', 'per_minute', 'per_hour', 'per_day'))
);

CREATE INDEX idx_rate_limits_integration_endpoint
  ON mcp.rate_limits(integration_id, endpoint, window_end)
  WHERE window_end > now();

CREATE INDEX idx_rate_limits_active_windows
  ON mcp.rate_limits(integration_id, reset_at)
  WHERE reset_at > now();

COMMENT ON TABLE mcp.rate_limits IS 'Rate limiting state per integration and endpoint';
COMMENT ON COLUMN mcp.rate_limits.window_start IS 'Start of current rate limit window';
COMMENT ON COLUMN mcp.rate_limits.window_end IS 'End of current rate limit window';
COMMENT ON COLUMN mcp.rate_limits.reset_at IS 'When rate limit resets (from platform headers)';

-- ========================================================================================
-- PART 8: SYNC JOBS AND STATE
-- ========================================================================================

CREATE TABLE IF NOT EXISTS mcp.sync_jobs (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  integration_id    uuid NOT NULL REFERENCES core.integrations(id) ON DELETE CASCADE,
  job_type          text NOT NULL,  -- 'full', 'incremental', 'backfill'
  status            text NOT NULL DEFAULT 'pending',
  started_at        timestamptz,
  completed_at      timestamptz,
  items_processed   int DEFAULT 0,
  items_total       int,
  cursor_start      text,
  cursor_end        text,
  error_message     text,
  metadata          jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at        timestamptz NOT NULL DEFAULT now(),

  CONSTRAINT sync_jobs_job_type_check
    CHECK (job_type IN ('full', 'incremental', 'backfill')),
  CONSTRAINT sync_jobs_status_check
    CHECK (status IN ('pending', 'running', 'completed', 'failed', 'canceled'))
);

CREATE INDEX idx_sync_jobs_integration_id
  ON mcp.sync_jobs(integration_id, created_at DESC);

CREATE INDEX idx_sync_jobs_status
  ON mcp.sync_jobs(status, created_at DESC)
  WHERE status IN ('pending', 'running');

CREATE INDEX idx_sync_jobs_active
  ON mcp.sync_jobs(integration_id, started_at DESC)
  WHERE status = 'running';

COMMENT ON TABLE mcp.sync_jobs IS 'Background sync jobs for data ingestion';
COMMENT ON COLUMN mcp.sync_jobs.cursor_start IS 'Starting cursor/offset for incremental sync';
COMMENT ON COLUMN mcp.sync_jobs.cursor_end IS 'Ending cursor/offset for incremental sync';

-- ========================================================================================
-- PART 9: INTEGRATION ERRORS LOG
-- ========================================================================================

CREATE TABLE IF NOT EXISTS mcp.integration_errors (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  integration_id    uuid NOT NULL REFERENCES core.integrations(id) ON DELETE CASCADE,
  error_type        text NOT NULL,
  error_code        text,
  error_message     text NOT NULL,
  stack_trace       text,
  context           jsonb NOT NULL DEFAULT '{}'::jsonb,
  recoverable       boolean NOT NULL DEFAULT true,
  retry_count       int DEFAULT 0,
  resolved_at       timestamptz,
  created_at        timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_integration_errors_integration_id
  ON mcp.integration_errors(integration_id, created_at DESC);

CREATE INDEX idx_integration_errors_unresolved
  ON mcp.integration_errors(created_at DESC)
  WHERE resolved_at IS NULL;

CREATE INDEX idx_integration_errors_type
  ON mcp.integration_errors(error_type, created_at DESC);

COMMENT ON TABLE mcp.integration_errors IS 'Detailed error log for integration failures';
COMMENT ON COLUMN mcp.integration_errors.error_type IS 'Classified error type (auth_expired, rate_limit, etc.)';
COMMENT ON COLUMN mcp.integration_errors.recoverable IS 'Whether error is automatically recoverable';

-- ========================================================================================
-- PART 10: VIEWS FOR MONITORING
-- ========================================================================================

-- View: Integration health summary
CREATE OR REPLACE VIEW mcp.v_integration_health_summary AS
SELECT
  i.id AS integration_id,
  i.workspace_id,
  i.founder_id,
  i.platform,
  i.status,
  i.health_status,
  i.consecutive_failures,
  i.circuit_breaker_state,
  i.last_health_check,
  hc.status AS latest_check_status,
  hc.response_time_ms AS latest_response_time,
  hc.checked_at AS latest_check_at,
  (
    SELECT COUNT(*)
    FROM mcp.health_checks hc2
    WHERE hc2.integration_id = i.id
      AND hc2.status = 'unhealthy'
      AND hc2.checked_at >= now() - interval '24 hours'
  ) AS failures_24h,
  (
    SELECT AVG(response_time_ms)
    FROM mcp.health_checks hc3
    WHERE hc3.integration_id = i.id
      AND hc3.checked_at >= now() - interval '24 hours'
  ) AS avg_response_time_24h
FROM core.integrations i
LEFT JOIN LATERAL (
  SELECT status, response_time_ms, checked_at
  FROM mcp.health_checks
  WHERE integration_id = i.id
  ORDER BY checked_at DESC
  LIMIT 1
) hc ON true
WHERE i.status IN ('connected', 'error', 'degraded');

COMMENT ON VIEW mcp.v_integration_health_summary IS 'Real-time integration health dashboard data';

-- View: Tokens expiring soon
CREATE OR REPLACE VIEW mcp.v_tokens_expiring_soon AS
SELECT
  ot.id AS token_id,
  ot.integration_id,
  i.platform,
  i.workspace_id,
  ot.token_type,
  ot.expires_at,
  EXTRACT(EPOCH FROM (ot.expires_at - now())) / 3600 AS hours_until_expiry,
  i.status AS integration_status
FROM mcp.oauth_tokens ot
JOIN core.integrations i ON ot.integration_id = i.id
WHERE ot.expires_at IS NOT NULL
  AND ot.expires_at <= now() + interval '48 hours'
  AND ot.expires_at > now()
  AND i.status = 'connected'
ORDER BY ot.expires_at ASC;

COMMENT ON VIEW mcp.v_tokens_expiring_soon IS 'OAuth tokens expiring within 48 hours';

-- View: Active sync jobs
CREATE OR REPLACE VIEW mcp.v_active_sync_jobs AS
SELECT
  sj.id AS job_id,
  sj.integration_id,
  i.platform,
  i.workspace_id,
  sj.job_type,
  sj.status,
  sj.started_at,
  sj.items_processed,
  sj.items_total,
  CASE
    WHEN sj.items_total > 0 THEN
      (sj.items_processed::float / sj.items_total::float * 100)::int
    ELSE 0
  END AS progress_percent,
  EXTRACT(EPOCH FROM (now() - sj.started_at)) AS duration_seconds
FROM mcp.sync_jobs sj
JOIN core.integrations i ON sj.integration_id = i.id
WHERE sj.status IN ('pending', 'running')
ORDER BY sj.started_at DESC;

COMMENT ON VIEW mcp.v_active_sync_jobs IS 'Currently running or pending sync jobs';

-- View: Recent integration errors
CREATE OR REPLACE VIEW mcp.v_recent_integration_errors AS
SELECT
  ie.id AS error_id,
  ie.integration_id,
  i.platform,
  i.workspace_id,
  i.founder_id,
  ie.error_type,
  ie.error_message,
  ie.recoverable,
  ie.retry_count,
  ie.resolved_at,
  ie.created_at,
  CASE
    WHEN ie.resolved_at IS NOT NULL THEN 'resolved'
    WHEN ie.recoverable = false THEN 'unrecoverable'
    WHEN ie.retry_count >= 3 THEN 'exhausted'
    ELSE 'pending'
  END AS error_status
FROM mcp.integration_errors ie
JOIN core.integrations i ON ie.integration_id = i.id
WHERE ie.created_at >= now() - interval '7 days'
ORDER BY ie.created_at DESC;

COMMENT ON VIEW mcp.v_recent_integration_errors IS 'Integration errors from last 7 days';

-- ========================================================================================
-- PART 11: FUNCTIONS FOR HEALTH MONITORING
-- ========================================================================================

-- Function: Record health check result
CREATE OR REPLACE FUNCTION mcp.record_health_check(
  p_integration_id uuid,
  p_status text,
  p_response_time_ms double precision DEFAULT NULL,
  p_error_message text DEFAULT NULL,
  p_details jsonb DEFAULT '{}'::jsonb
)
RETURNS uuid AS $$
DECLARE
  v_health_check_id uuid;
  v_consecutive_failures int;
  v_new_circuit_state text;
BEGIN
  -- Insert health check record
  INSERT INTO mcp.health_checks (
    integration_id,
    status,
    response_time_ms,
    error_message,
    details,
    checked_at
  ) VALUES (
    p_integration_id,
    p_status,
    p_response_time_ms,
    p_error_message,
    p_details,
    now()
  ) RETURNING id INTO v_health_check_id;

  -- Update integration health status
  IF p_status = 'healthy' THEN
    -- Reset failures on success
    UPDATE core.integrations
    SET
      health_status = 'healthy',
      consecutive_failures = 0,
      circuit_breaker_state = 'closed',
      circuit_breaker_opened_at = NULL,
      last_health_check = now()
    WHERE id = p_integration_id;

  ELSIF p_status = 'degraded' THEN
    -- Degraded but not failed
    UPDATE core.integrations
    SET
      health_status = 'degraded',
      last_health_check = now()
    WHERE id = p_integration_id;

  ELSE  -- unhealthy
    -- Increment failure counter
    SELECT consecutive_failures + 1
    INTO v_consecutive_failures
    FROM core.integrations
    WHERE id = p_integration_id;

    -- Determine circuit breaker state
    -- Open circuit after 5 consecutive failures
    IF v_consecutive_failures >= 5 THEN
      v_new_circuit_state := 'open';
    ELSE
      v_new_circuit_state := (
        SELECT circuit_breaker_state
        FROM core.integrations
        WHERE id = p_integration_id
      );
    END IF;

    UPDATE core.integrations
    SET
      health_status = 'unhealthy',
      consecutive_failures = v_consecutive_failures,
      circuit_breaker_state = v_new_circuit_state,
      circuit_breaker_opened_at = CASE
        WHEN v_new_circuit_state = 'open' AND circuit_breaker_state != 'open'
          THEN now()
        ELSE circuit_breaker_opened_at
      END,
      last_health_check = now(),
      status = CASE
        WHEN v_consecutive_failures >= 3 THEN 'error'
        ELSE status
      END,
      error_message = p_error_message
    WHERE id = p_integration_id;
  END IF;

  RETURN v_health_check_id;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION mcp.record_health_check IS 'Record health check and update integration status';

-- Function: Check if circuit breaker allows request
CREATE OR REPLACE FUNCTION mcp.can_execute_request(p_integration_id uuid)
RETURNS boolean AS $$
DECLARE
  v_circuit_state text;
  v_opened_at timestamptz;
BEGIN
  SELECT circuit_breaker_state, circuit_breaker_opened_at
  INTO v_circuit_state, v_opened_at
  FROM core.integrations
  WHERE id = p_integration_id;

  IF v_circuit_state = 'closed' THEN
    RETURN true;
  ELSIF v_circuit_state = 'open' THEN
    -- Check if timeout elapsed (5 minutes)
    IF v_opened_at IS NOT NULL AND
       now() >= v_opened_at + interval '5 minutes' THEN
      -- Move to half-open state
      UPDATE core.integrations
      SET circuit_breaker_state = 'half_open'
      WHERE id = p_integration_id;
      RETURN true;
    ELSE
      RETURN false;
    END IF;
  ELSIF v_circuit_state = 'half_open' THEN
    -- Allow one request to test
    RETURN true;
  ELSE
    RETURN false;
  END IF;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION mcp.can_execute_request IS 'Check if circuit breaker allows request execution';

-- Function: Update token expiry
CREATE OR REPLACE FUNCTION mcp.update_token_expiry(
  p_integration_id uuid,
  p_token_type text,
  p_expires_in int  -- seconds from now
)
RETURNS void AS $$
BEGIN
  INSERT INTO mcp.oauth_tokens (
    integration_id,
    token_type,
    expires_at,
    issued_at
  ) VALUES (
    p_integration_id,
    p_token_type,
    now() + (p_expires_in || ' seconds')::interval,
    now()
  )
  ON CONFLICT (integration_id, token_type)
  DO UPDATE SET
    expires_at = now() + (p_expires_in || ' seconds')::interval,
    refreshed_at = now();
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION mcp.update_token_expiry IS 'Update or create token expiry record';

-- ========================================================================================
-- PART 12: TRIGGERS
-- ========================================================================================

-- Trigger: Log integration state changes
CREATE OR REPLACE FUNCTION mcp.log_integration_state_change()
RETURNS TRIGGER AS $$
BEGIN
  IF (OLD.status IS DISTINCT FROM NEW.status) OR
     (OLD.health_status IS DISTINCT FROM NEW.health_status) THEN

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
      'system',
      NULL,
      'integration.state_change',
      'integration',
      NEW.id,
      jsonb_build_object(
        'platform', NEW.platform,
        'old_status', OLD.status,
        'new_status', NEW.status,
        'old_health', OLD.health_status,
        'new_health', NEW.health_status,
        'consecutive_failures', NEW.consecutive_failures,
        'circuit_state', NEW.circuit_breaker_state
      )
    );
  END IF;

  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER integration_state_change_logger
  AFTER UPDATE ON core.integrations
  FOR EACH ROW
  EXECUTE FUNCTION mcp.log_integration_state_change();

COMMENT ON FUNCTION mcp.log_integration_state_change IS 'Auto-log integration state changes to ops.events';

-- ========================================================================================
-- PART 13: INITIAL DATA
-- ========================================================================================

-- Platform OAuth configurations (placeholder - actual values from environment)
-- This would be populated by application configuration

-- ========================================================================================
-- PART 14: MIGRATION METADATA
-- ========================================================================================

INSERT INTO public.schema_migrations (version, description)
VALUES ('003', 'MCP Integration Framework Extensions')
ON CONFLICT (version) DO NOTHING;

-- ========================================================================================
-- END OF MIGRATION 003_mcp_extensions.sql
-- ========================================================================================
