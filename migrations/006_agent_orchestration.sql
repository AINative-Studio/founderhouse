-- ========================================================================================
-- Migration: 006_agent_orchestration.sql
-- Description: AI Chief of Staff - Agent Orchestration & Workflow Engine Schema
-- Author: System Architect
-- Date: 2025-11-11
-- Sprint: 5 - Orchestration, Voice & Async Collaboration
--
-- This migration creates the database schema for:
-- - Multi-agent workflow orchestration (AgentFlow)
-- - Workflow execution tracking
-- - Agent task coordination
-- - Result aggregation
--
-- Dependencies:
-- - 001_initial_schema.sql
-- - 002_rls_policies.sql
-- - 003_mcp_extensions.sql
-- - 004_meeting_intelligence.sql
-- - 005_insights_briefings.sql
-- ========================================================================================

-- ========================================================================================
-- PART 1: SCHEMA & ENUMS
-- ========================================================================================

-- Create orchestration schema if not exists
CREATE SCHEMA IF NOT EXISTS orchestration;

-- Workflow status enum
DO $$ BEGIN
  CREATE TYPE orchestration.workflow_status AS ENUM (
    'queued',       -- Workflow queued for execution
    'running',      -- Workflow currently executing
    'completed',    -- Workflow completed successfully
    'failed',       -- Workflow failed
    'cancelled',    -- Workflow cancelled by user
    'timeout'       -- Workflow exceeded time limit
  );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- Workflow type enum
DO $$ BEGIN
  CREATE TYPE orchestration.workflow_type AS ENUM (
    'cos_task_insight',     -- CoS → Task → Insight (default Sprint 5 flow)
    'meeting_to_tasks',     -- Meeting analysis → Task creation
    'briefing_generation',  -- Data aggregation → Briefing
    'insight_pipeline',     -- Data → Analysis → Recommendations
    'custom'                -- Custom workflow graph
  );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- ========================================================================================
-- PART 2: WORKFLOW EXECUTION TABLES
-- ========================================================================================

-- Agent workflow executions
CREATE TABLE IF NOT EXISTS orchestration.agent_workflow_executions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID NOT NULL REFERENCES core.workspaces(id) ON DELETE CASCADE,
  founder_id UUID NOT NULL REFERENCES core.founders(id) ON DELETE CASCADE,

  -- Workflow configuration
  workflow_type orchestration.workflow_type NOT NULL DEFAULT 'cos_task_insight',
  objective TEXT NOT NULL,
  status orchestration.workflow_status NOT NULL DEFAULT 'queued',

  -- Execution data
  execution_steps JSONB DEFAULT '[]'::jsonb,
  aggregated_results JSONB DEFAULT '{}'::jsonb,
  error_message TEXT,

  -- Timing
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  started_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ,
  timeout_seconds INTEGER DEFAULT 300,

  -- Metadata
  metadata JSONB DEFAULT '{}'::jsonb,

  -- Indexes
  CONSTRAINT valid_timeout CHECK (timeout_seconds > 0 AND timeout_seconds <= 3600)
);

-- Create indexes for workflow executions
CREATE INDEX IF NOT EXISTS idx_workflow_executions_workspace
  ON orchestration.agent_workflow_executions(workspace_id);
CREATE INDEX IF NOT EXISTS idx_workflow_executions_founder
  ON orchestration.agent_workflow_executions(founder_id);
CREATE INDEX IF NOT EXISTS idx_workflow_executions_status
  ON orchestration.agent_workflow_executions(status);
CREATE INDEX IF NOT EXISTS idx_workflow_executions_created
  ON orchestration.agent_workflow_executions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_workflow_executions_type
  ON orchestration.agent_workflow_executions(workflow_type);

-- GIN index for searching execution steps
CREATE INDEX IF NOT EXISTS idx_workflow_executions_steps
  ON orchestration.agent_workflow_executions USING GIN(execution_steps);

-- ========================================================================================
-- PART 3: AGENT TASK TABLES (if not exists from previous sprints)
-- ========================================================================================

-- Agent task status enum
DO $$ BEGIN
  CREATE TYPE orchestration.agent_task_status AS ENUM (
    'queued',
    'assigned',
    'processing',
    'completed',
    'failed',
    'cancelled',
    'blocked'
  );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- Agent task priority enum
DO $$ BEGIN
  CREATE TYPE orchestration.agent_task_priority AS ENUM (
    'urgent',
    'high',
    'medium',
    'low'
  );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- Agent types enum
DO $$ BEGIN
  CREATE TYPE orchestration.agent_type AS ENUM (
    'meeting_analyst',
    'kpi_monitor',
    'briefing_generator',
    'recommendation_engine',
    'communication_handler',
    'task_manager',
    'research_assistant',
    'voice_processor'
  );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- Agent tasks table
CREATE TABLE IF NOT EXISTS orchestration.agent_tasks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID NOT NULL REFERENCES core.workspaces(id) ON DELETE CASCADE,
  founder_id UUID NOT NULL REFERENCES core.founders(id) ON DELETE CASCADE,

  -- Task details
  task_type TEXT NOT NULL,
  task_description TEXT NOT NULL,
  priority orchestration.agent_task_priority NOT NULL DEFAULT 'medium',
  status orchestration.agent_task_status NOT NULL DEFAULT 'queued',
  assigned_agent orchestration.agent_type,

  -- Data
  input_data JSONB DEFAULT '{}'::jsonb,
  output_data JSONB,
  context JSONB DEFAULT '{}'::jsonb,

  -- Error handling
  error_message TEXT,
  retry_count INTEGER DEFAULT 0,
  max_retries INTEGER DEFAULT 3,

  -- Dependencies
  dependencies UUID[] DEFAULT ARRAY[]::UUID[],

  -- Workflow association
  workflow_id UUID REFERENCES orchestration.agent_workflow_executions(id) ON DELETE SET NULL,

  -- Timing
  processing_time_ms INTEGER,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  started_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ,
  deadline TIMESTAMPTZ,

  -- Constraints
  CONSTRAINT valid_retry_count CHECK (retry_count >= 0 AND retry_count <= max_retries)
);

-- Create indexes for agent tasks
CREATE INDEX IF NOT EXISTS idx_agent_tasks_workspace
  ON orchestration.agent_tasks(workspace_id);
CREATE INDEX IF NOT EXISTS idx_agent_tasks_founder
  ON orchestration.agent_tasks(founder_id);
CREATE INDEX IF NOT EXISTS idx_agent_tasks_status
  ON orchestration.agent_tasks(status);
CREATE INDEX IF NOT EXISTS idx_agent_tasks_assigned_agent
  ON orchestration.agent_tasks(assigned_agent);
CREATE INDEX IF NOT EXISTS idx_agent_tasks_created
  ON orchestration.agent_tasks(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_agent_tasks_workflow
  ON orchestration.agent_tasks(workflow_id);

-- GIN indexes for JSON data
CREATE INDEX IF NOT EXISTS idx_agent_tasks_input
  ON orchestration.agent_tasks USING GIN(input_data);
CREATE INDEX IF NOT EXISTS idx_agent_tasks_output
  ON orchestration.agent_tasks USING GIN(output_data);

-- ========================================================================================
-- PART 4: AGENT COLLABORATION TABLES
-- ========================================================================================

-- Agent collaboration sessions
CREATE TABLE IF NOT EXISTS orchestration.agent_collaborations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID NOT NULL REFERENCES core.workspaces(id) ON DELETE CASCADE,
  founder_id UUID NOT NULL REFERENCES core.founders(id) ON DELETE CASCADE,

  -- Collaboration details
  primary_agent orchestration.agent_type NOT NULL,
  collaborating_agents orchestration.agent_type[] NOT NULL,
  objective TEXT NOT NULL,
  status orchestration.agent_task_status NOT NULL DEFAULT 'processing',

  -- Data
  shared_context JSONB DEFAULT '{}'::jsonb,
  agent_outputs JSONB DEFAULT '{}'::jsonb,
  final_result JSONB,
  error_message TEXT,

  -- Timing
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  completed_at TIMESTAMPTZ,

  -- Constraints
  CONSTRAINT valid_collaborating_agents CHECK (array_length(collaborating_agents, 1) > 0)
);

-- Create indexes for collaborations
CREATE INDEX IF NOT EXISTS idx_agent_collaborations_workspace
  ON orchestration.agent_collaborations(workspace_id);
CREATE INDEX IF NOT EXISTS idx_agent_collaborations_founder
  ON orchestration.agent_collaborations(founder_id);
CREATE INDEX IF NOT EXISTS idx_agent_collaborations_primary_agent
  ON orchestration.agent_collaborations(primary_agent);
CREATE INDEX IF NOT EXISTS idx_agent_collaborations_created
  ON orchestration.agent_collaborations(created_at DESC);

-- ========================================================================================
-- PART 5: ROW LEVEL SECURITY (RLS)
-- ========================================================================================

-- Enable RLS on workflow executions
ALTER TABLE orchestration.agent_workflow_executions ENABLE ROW LEVEL SECURITY;

-- Policy: Users can view workflows in their workspace
CREATE POLICY workflow_executions_select_policy ON orchestration.agent_workflow_executions
  FOR SELECT
  USING (
    workspace_id IN (
      SELECT id FROM core.workspaces
      WHERE id = workspace_id
    )
  );

-- Policy: Users can insert workflows in their workspace
CREATE POLICY workflow_executions_insert_policy ON orchestration.agent_workflow_executions
  FOR INSERT
  WITH CHECK (
    workspace_id IN (
      SELECT id FROM core.workspaces
      WHERE id = workspace_id
    )
  );

-- Policy: Users can update workflows in their workspace
CREATE POLICY workflow_executions_update_policy ON orchestration.agent_workflow_executions
  FOR UPDATE
  USING (
    workspace_id IN (
      SELECT id FROM core.workspaces
      WHERE id = workspace_id
    )
  );

-- Enable RLS on agent tasks
ALTER TABLE orchestration.agent_tasks ENABLE ROW LEVEL SECURITY;

-- Policy: Users can view tasks in their workspace
CREATE POLICY agent_tasks_select_policy ON orchestration.agent_tasks
  FOR SELECT
  USING (
    workspace_id IN (
      SELECT id FROM core.workspaces
      WHERE id = workspace_id
    )
  );

-- Policy: Users can insert tasks in their workspace
CREATE POLICY agent_tasks_insert_policy ON orchestration.agent_tasks
  FOR INSERT
  WITH CHECK (
    workspace_id IN (
      SELECT id FROM core.workspaces
      WHERE id = workspace_id
    )
  );

-- Policy: Users can update tasks in their workspace
CREATE POLICY agent_tasks_update_policy ON orchestration.agent_tasks
  FOR UPDATE
  USING (
    workspace_id IN (
      SELECT id FROM core.workspaces
      WHERE id = workspace_id
    )
  );

-- Enable RLS on collaborations
ALTER TABLE orchestration.agent_collaborations ENABLE ROW LEVEL SECURITY;

-- Policy: Users can view collaborations in their workspace
CREATE POLICY agent_collaborations_select_policy ON orchestration.agent_collaborations
  FOR SELECT
  USING (
    workspace_id IN (
      SELECT id FROM core.workspaces
      WHERE id = workspace_id
    )
  );

-- Policy: Users can insert collaborations in their workspace
CREATE POLICY agent_collaborations_insert_policy ON orchestration.agent_collaborations
  FOR INSERT
  WITH CHECK (
    workspace_id IN (
      SELECT id FROM core.workspaces
      WHERE id = workspace_id
    )
  );

-- ========================================================================================
-- PART 6: FUNCTIONS & TRIGGERS
-- ========================================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION orchestration.update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for agent_tasks updated_at
DROP TRIGGER IF EXISTS agent_tasks_updated_at ON orchestration.agent_tasks;
CREATE TRIGGER agent_tasks_updated_at
  BEFORE UPDATE ON orchestration.agent_tasks
  FOR EACH ROW
  EXECUTE FUNCTION orchestration.update_updated_at();

-- Function to auto-update workflow started_at
CREATE OR REPLACE FUNCTION orchestration.update_workflow_started_at()
RETURNS TRIGGER AS $$
BEGIN
  IF NEW.status = 'running' AND OLD.status != 'running' AND NEW.started_at IS NULL THEN
    NEW.started_at = NOW();
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for workflow started_at
DROP TRIGGER IF EXISTS workflow_started_at ON orchestration.agent_workflow_executions;
CREATE TRIGGER workflow_started_at
  BEFORE UPDATE ON orchestration.agent_workflow_executions
  FOR EACH ROW
  EXECUTE FUNCTION orchestration.update_workflow_started_at();

-- Function to auto-update workflow completed_at
CREATE OR REPLACE FUNCTION orchestration.update_workflow_completed_at()
RETURNS TRIGGER AS $$
BEGIN
  IF NEW.status IN ('completed', 'failed', 'cancelled', 'timeout')
     AND OLD.status NOT IN ('completed', 'failed', 'cancelled', 'timeout')
     AND NEW.completed_at IS NULL THEN
    NEW.completed_at = NOW();
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for workflow completed_at
DROP TRIGGER IF EXISTS workflow_completed_at ON orchestration.agent_workflow_executions;
CREATE TRIGGER workflow_completed_at
  BEFORE UPDATE ON orchestration.agent_workflow_executions
  FOR EACH ROW
  EXECUTE FUNCTION orchestration.update_workflow_completed_at();

-- ========================================================================================
-- PART 7: HELPER VIEWS
-- ========================================================================================

-- View: Active workflows
CREATE OR REPLACE VIEW orchestration.active_workflows AS
SELECT
  w.*,
  (w.completed_at - w.started_at) AS execution_duration,
  jsonb_array_length(w.execution_steps) AS step_count
FROM orchestration.agent_workflow_executions w
WHERE w.status IN ('queued', 'running');

-- View: Workflow statistics by type
CREATE OR REPLACE VIEW orchestration.workflow_stats_by_type AS
SELECT
  workflow_type,
  COUNT(*) AS total_executions,
  COUNT(*) FILTER (WHERE status = 'completed') AS completed,
  COUNT(*) FILTER (WHERE status = 'failed') AS failed,
  AVG(EXTRACT(EPOCH FROM (completed_at - started_at))) AS avg_duration_seconds,
  MAX(created_at) AS last_execution
FROM orchestration.agent_workflow_executions
GROUP BY workflow_type;

-- View: Agent task statistics
CREATE OR REPLACE VIEW orchestration.agent_task_stats AS
SELECT
  assigned_agent,
  COUNT(*) AS total_tasks,
  COUNT(*) FILTER (WHERE status = 'completed') AS completed,
  COUNT(*) FILTER (WHERE status = 'failed') AS failed,
  AVG(processing_time_ms) AS avg_processing_time_ms,
  MAX(created_at) AS last_task
FROM orchestration.agent_tasks
WHERE assigned_agent IS NOT NULL
GROUP BY assigned_agent;

-- ========================================================================================
-- PART 8: GRANTS
-- ========================================================================================

-- Grant usage on schema
GRANT USAGE ON SCHEMA orchestration TO authenticated;

-- Grant permissions on tables
GRANT SELECT, INSERT, UPDATE ON orchestration.agent_workflow_executions TO authenticated;
GRANT SELECT, INSERT, UPDATE ON orchestration.agent_tasks TO authenticated;
GRANT SELECT, INSERT, UPDATE ON orchestration.agent_collaborations TO authenticated;

-- Grant permissions on views
GRANT SELECT ON orchestration.active_workflows TO authenticated;
GRANT SELECT ON orchestration.workflow_stats_by_type TO authenticated;
GRANT SELECT ON orchestration.agent_task_stats TO authenticated;

-- ========================================================================================
-- END OF MIGRATION
-- ========================================================================================
