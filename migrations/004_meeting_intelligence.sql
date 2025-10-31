-- ========================================================================================
-- Migration: 004_meeting_intelligence.sql
-- Description: AI Chief of Staff - Meeting Intelligence Extensions
-- Author: System Architect
-- Date: 2025-10-30
-- Sprint: 3 - Meeting & Communication Intelligence
--
-- This migration extends the database schema to support:
-- - Enhanced transcript processing status tracking
-- - Action item extraction and classification
-- - Decision logging and tracking
-- - Task derivation from meetings
-- - Summary versioning
-- - Processing pipeline state
--
-- Dependencies:
-- - 001_initial_schema.sql
-- - 002_rls_policies.sql
-- - 003_mcp_extensions.sql
-- ========================================================================================

-- ========================================================================================
-- PART 1: ENUMS FOR MEETING INTELLIGENCE
-- ========================================================================================

-- Processing status for transcripts
DO $$ BEGIN
  CREATE TYPE meetings.processing_status AS ENUM (
    'pending',        -- Awaiting processing
    'chunking',       -- Being chunked
    'embedding',      -- Generating embeddings
    'summarizing',    -- AI summarization in progress
    'extracting',     -- Extracting action items
    'completed',      -- Fully processed
    'failed'          -- Processing failed
  );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- Action item status
DO $$ BEGIN
  CREATE TYPE meetings.action_item_status AS ENUM (
    'detected',       -- AI detected, not yet routed
    'routed',         -- Routed to task system
    'task_created',   -- Monday task created
    'dismissed',      -- Marked as false positive
    'completed'       -- Underlying task completed
  );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- Classification confidence levels
DO $$ BEGIN
  CREATE TYPE meetings.confidence_level AS ENUM (
    'very_high',      -- 0.9 - 1.0
    'high',           -- 0.8 - 0.9
    'medium',         -- 0.7 - 0.8
    'low',            -- 0.5 - 0.7
    'very_low'        -- 0.0 - 0.5
  );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

COMMENT ON TYPE meetings.processing_status IS 'Transcript processing pipeline status';
COMMENT ON TYPE meetings.action_item_status IS 'Action item lifecycle status';
COMMENT ON TYPE meetings.confidence_level IS 'ML classification confidence levels';

-- ========================================================================================
-- PART 2: EXTEND EXISTING MEETINGS TABLES
-- ========================================================================================

-- Add processing tracking to transcripts table
ALTER TABLE meetings.transcripts
  ADD COLUMN IF NOT EXISTS processing_status meetings.processing_status DEFAULT 'pending',
  ADD COLUMN IF NOT EXISTS processing_started_at timestamptz,
  ADD COLUMN IF NOT EXISTS processing_completed_at timestamptz,
  ADD COLUMN IF NOT EXISTS processing_error text,
  ADD COLUMN IF NOT EXISTS chunk_count int DEFAULT 0,
  ADD COLUMN IF NOT EXISTS embedding_model text DEFAULT 'text-embedding-ada-002',
  ADD COLUMN IF NOT EXISTS summarization_model text,
  ADD COLUMN IF NOT EXISTS summarization_version int DEFAULT 1,
  ADD COLUMN IF NOT EXISTS participants jsonb DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS speaker_stats jsonb DEFAULT '{}'::jsonb,
  ADD COLUMN IF NOT EXISTS decisions jsonb DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS follow_ups jsonb DEFAULT '[]'::jsonb;

-- Add indexes for processing queries
CREATE INDEX IF NOT EXISTS idx_transcripts_processing_status
  ON meetings.transcripts(processing_status, processing_started_at)
  WHERE processing_status NOT IN ('completed', 'failed');

CREATE INDEX IF NOT EXISTS idx_transcripts_pending
  ON meetings.transcripts(workspace_id, created_at)
  WHERE processing_status = 'pending';

CREATE INDEX IF NOT EXISTS idx_transcripts_failed
  ON meetings.transcripts(workspace_id, created_at DESC)
  WHERE processing_status = 'failed';

COMMENT ON COLUMN meetings.transcripts.processing_status IS 'Current stage in processing pipeline';
COMMENT ON COLUMN meetings.transcripts.chunk_count IS 'Number of chunks generated';
COMMENT ON COLUMN meetings.transcripts.participants IS 'Array of participant objects with metadata';
COMMENT ON COLUMN meetings.transcripts.speaker_stats IS 'Speaking time and contribution stats per speaker';
COMMENT ON COLUMN meetings.transcripts.decisions IS 'Explicit decisions extracted from meeting';
COMMENT ON COLUMN meetings.transcripts.follow_ups IS 'Follow-up items and next steps';

-- ========================================================================================
-- PART 3: ACTION ITEMS TABLE
-- ========================================================================================

CREATE TABLE IF NOT EXISTS meetings.action_items (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id      uuid NOT NULL REFERENCES core.workspaces(id) ON DELETE CASCADE,
  founder_id        uuid NOT NULL REFERENCES core.founders(id) ON DELETE CASCADE,
  transcript_id     uuid NOT NULL REFERENCES meetings.transcripts(id) ON DELETE CASCADE,
  chunk_id          uuid REFERENCES meetings.transcript_chunks(id) ON DELETE SET NULL,

  -- Action item content
  action_text       text NOT NULL,
  context           text,

  -- Classification metadata
  confidence        double precision NOT NULL,
  confidence_level  meetings.confidence_level NOT NULL,
  classification_method text DEFAULT 'llm',  -- 'llm', 'pattern', 'hybrid'

  -- Assignment and scheduling
  assignee          text,
  assignee_email    text,
  assignee_confidence double precision,
  due_date          timestamptz,
  due_date_source   text,  -- 'explicit', 'inferred', 'default'
  priority          core.priority_enum DEFAULT 'normal',

  -- Lifecycle
  status            meetings.action_item_status DEFAULT 'detected',
  task_id           uuid REFERENCES work.tasks(id) ON DELETE SET NULL,
  dismissed_reason  text,
  dismissed_by      uuid,
  dismissed_at      timestamptz,

  -- Temporal tracking
  start_sec         int,
  end_sec           int,
  speaker           text,

  -- Metadata
  tags              text[] DEFAULT '{}',
  metadata          jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at        timestamptz NOT NULL DEFAULT now(),
  updated_at        timestamptz NOT NULL DEFAULT now(),

  CONSTRAINT action_items_confidence_range CHECK (confidence >= 0 AND confidence <= 1),
  CONSTRAINT action_items_assignee_confidence_range
    CHECK (assignee_confidence IS NULL OR (assignee_confidence >= 0 AND assignee_confidence <= 1)),
  CONSTRAINT action_items_time_order
    CHECK (start_sec IS NULL OR end_sec IS NULL OR start_sec <= end_sec)
);

CREATE INDEX idx_action_items_workspace_founder
  ON meetings.action_items(workspace_id, founder_id);

CREATE INDEX idx_action_items_transcript
  ON meetings.action_items(transcript_id, created_at DESC);

CREATE INDEX idx_action_items_status
  ON meetings.action_items(workspace_id, founder_id, status, created_at DESC);

CREATE INDEX idx_action_items_confidence
  ON meetings.action_items(workspace_id, confidence DESC)
  WHERE status = 'detected';

CREATE INDEX idx_action_items_assignee
  ON meetings.action_items(workspace_id, assignee)
  WHERE assignee IS NOT NULL AND status NOT IN ('dismissed', 'completed');

CREATE INDEX idx_action_items_task_id
  ON meetings.action_items(task_id)
  WHERE task_id IS NOT NULL;

CREATE INDEX idx_action_items_tags
  ON meetings.action_items USING GIN(tags);

COMMENT ON TABLE meetings.action_items IS 'AI-extracted action items from meeting transcripts';
COMMENT ON COLUMN meetings.action_items.confidence IS 'ML confidence score (0-1) for action item classification';
COMMENT ON COLUMN meetings.action_items.confidence_level IS 'Discretized confidence bucket';
COMMENT ON COLUMN meetings.action_items.assignee_confidence IS 'Confidence in assignee extraction';
COMMENT ON COLUMN meetings.action_items.due_date_source IS 'How due date was determined';
COMMENT ON COLUMN meetings.action_items.classification_method IS 'Method used for action item detection';

-- ========================================================================================
-- PART 4: DECISIONS TABLE
-- ========================================================================================

CREATE TABLE IF NOT EXISTS meetings.decisions (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id      uuid NOT NULL REFERENCES core.workspaces(id) ON DELETE CASCADE,
  founder_id        uuid NOT NULL REFERENCES core.founders(id) ON DELETE CASCADE,
  transcript_id     uuid NOT NULL REFERENCES meetings.transcripts(id) ON DELETE CASCADE,
  chunk_id          uuid REFERENCES meetings.transcript_chunks(id) ON DELETE SET NULL,

  -- Decision content
  decision_text     text NOT NULL,
  context           text,

  -- Decision metadata
  category          text,  -- 'strategic', 'tactical', 'technical', 'operational'
  alternatives      jsonb DEFAULT '[]'::jsonb,  -- Alternative options considered
  rationale         text,
  decided_by        text,
  decided_by_role   text,

  -- Impact assessment
  impact_score      double precision,  -- AI-assessed impact (0-1)
  confidence        double precision NOT NULL,

  -- Outcome tracking
  outcome           text,
  outcome_recorded_at timestamptz,
  was_successful    boolean,

  -- Temporal tracking
  start_sec         int,
  end_sec           int,

  -- Metadata
  tags              text[] DEFAULT '{}',
  metadata          jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at        timestamptz NOT NULL DEFAULT now(),
  updated_at        timestamptz NOT NULL DEFAULT now(),

  CONSTRAINT decisions_confidence_range CHECK (confidence >= 0 AND confidence <= 1),
  CONSTRAINT decisions_impact_range
    CHECK (impact_score IS NULL OR (impact_score >= 0 AND impact_score <= 1))
);

CREATE INDEX idx_decisions_workspace_founder
  ON meetings.decisions(workspace_id, founder_id);

CREATE INDEX idx_decisions_transcript
  ON meetings.decisions(transcript_id, created_at DESC);

CREATE INDEX idx_decisions_category
  ON meetings.decisions(workspace_id, category, created_at DESC)
  WHERE category IS NOT NULL;

CREATE INDEX idx_decisions_impact
  ON meetings.decisions(workspace_id, impact_score DESC)
  WHERE impact_score IS NOT NULL;

CREATE INDEX idx_decisions_tags
  ON meetings.decisions USING GIN(tags);

COMMENT ON TABLE meetings.decisions IS 'Explicit decisions extracted from meetings';
COMMENT ON COLUMN meetings.decisions.alternatives IS 'Array of alternative options that were considered';
COMMENT ON COLUMN meetings.decisions.impact_score IS 'AI-assessed impact score (0-1)';
COMMENT ON COLUMN meetings.decisions.was_successful IS 'Outcome assessment (filled later)';

-- ========================================================================================
-- PART 5: SUMMARY VERSIONS TABLE
-- ========================================================================================

CREATE TABLE IF NOT EXISTS meetings.summary_versions (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  transcript_id     uuid NOT NULL REFERENCES meetings.transcripts(id) ON DELETE CASCADE,
  version           int NOT NULL,

  -- Summary components
  tldr              text,
  key_points        jsonb DEFAULT '[]'::jsonb,
  narrative         text,

  -- Generation metadata
  model             text NOT NULL,  -- 'gpt-4', 'claude-3', etc.
  model_version     text,
  prompt_version    text,
  temperature       double precision,

  -- Quality metrics
  coherence_score   double precision,
  factuality_score  double precision,
  completeness_score double precision,

  -- Processing metadata
  tokens_input      int,
  tokens_output     int,
  processing_time_ms int,
  cost_usd          decimal(10, 6),

  -- Lifecycle
  generated_at      timestamptz NOT NULL DEFAULT now(),
  superseded_by     uuid REFERENCES meetings.summary_versions(id),
  is_active         boolean DEFAULT true,

  -- Feedback
  feedback_score    int,  -- 1-5 rating
  feedback_text     text,
  feedback_at       timestamptz,

  metadata          jsonb NOT NULL DEFAULT '{}'::jsonb,

  CONSTRAINT summary_versions_unique_transcript_version UNIQUE (transcript_id, version),
  CONSTRAINT summary_versions_feedback_range CHECK (feedback_score IS NULL OR (feedback_score >= 1 AND feedback_score <= 5))
);

CREATE INDEX idx_summary_versions_transcript
  ON meetings.summary_versions(transcript_id, version DESC);

CREATE INDEX idx_summary_versions_active
  ON meetings.summary_versions(transcript_id)
  WHERE is_active = true;

CREATE INDEX idx_summary_versions_model
  ON meetings.summary_versions(model, generated_at DESC);

COMMENT ON TABLE meetings.summary_versions IS 'Version history of AI-generated meeting summaries';
COMMENT ON COLUMN meetings.summary_versions.key_points IS 'Array of key bullet points';
COMMENT ON COLUMN meetings.summary_versions.superseded_by IS 'Points to newer version if superseded';
COMMENT ON COLUMN meetings.summary_versions.cost_usd IS 'LLM API cost for this summary';

-- ========================================================================================
-- PART 6: PROCESSING JOBS TABLE
-- ========================================================================================

CREATE TABLE IF NOT EXISTS meetings.processing_jobs (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  transcript_id     uuid NOT NULL REFERENCES meetings.transcripts(id) ON DELETE CASCADE,
  job_type          text NOT NULL,  -- 'chunking', 'embedding', 'summarization', 'extraction'
  status            text NOT NULL DEFAULT 'pending',

  -- Job execution
  started_at        timestamptz,
  completed_at      timestamptz,
  duration_ms       int,

  -- Progress tracking
  progress_current  int DEFAULT 0,
  progress_total    int,

  -- Error handling
  error_message     text,
  error_code        text,
  retry_count       int DEFAULT 0,
  max_retries       int DEFAULT 3,

  -- Dependencies
  depends_on        uuid REFERENCES meetings.processing_jobs(id),

  -- Results
  result_summary    jsonb DEFAULT '{}'::jsonb,

  metadata          jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at        timestamptz NOT NULL DEFAULT now(),

  CONSTRAINT processing_jobs_job_type_check
    CHECK (job_type IN ('chunking', 'embedding', 'summarization', 'extraction', 'routing')),
  CONSTRAINT processing_jobs_status_check
    CHECK (status IN ('pending', 'running', 'completed', 'failed', 'canceled'))
);

CREATE INDEX idx_processing_jobs_transcript
  ON meetings.processing_jobs(transcript_id, created_at DESC);

CREATE INDEX idx_processing_jobs_status
  ON meetings.processing_jobs(status, created_at)
  WHERE status IN ('pending', 'running');

CREATE INDEX idx_processing_jobs_failed
  ON meetings.processing_jobs(transcript_id, created_at DESC)
  WHERE status = 'failed';

COMMENT ON TABLE meetings.processing_jobs IS 'Async processing jobs for transcript pipeline';
COMMENT ON COLUMN meetings.processing_jobs.depends_on IS 'Job that must complete before this one starts';
COMMENT ON COLUMN meetings.processing_jobs.result_summary IS 'Summary of job results (counts, metrics)';

-- ========================================================================================
-- PART 7: TASK DERIVATION TABLE
-- ========================================================================================

-- Link between action items and created tasks
CREATE TABLE IF NOT EXISTS meetings.task_derivations (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  action_item_id    uuid NOT NULL REFERENCES meetings.action_items(id) ON DELETE CASCADE,
  task_id           uuid NOT NULL REFERENCES work.tasks(id) ON DELETE CASCADE,

  -- Derivation metadata
  derivation_method text NOT NULL,  -- 'automatic', 'manual', 'suggested'
  confidence        double precision,

  -- Transformations applied
  title_transformed boolean DEFAULT false,
  assignee_mapped   boolean DEFAULT false,
  due_date_adjusted boolean DEFAULT false,
  priority_adjusted boolean DEFAULT false,

  -- User actions
  user_edited       boolean DEFAULT false,
  user_approved     boolean,
  approved_by       uuid,
  approved_at       timestamptz,

  metadata          jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at        timestamptz NOT NULL DEFAULT now(),

  CONSTRAINT task_derivations_unique_action_task UNIQUE (action_item_id, task_id),
  CONSTRAINT task_derivations_method_check
    CHECK (derivation_method IN ('automatic', 'manual', 'suggested'))
);

CREATE INDEX idx_task_derivations_action_item
  ON meetings.task_derivations(action_item_id);

CREATE INDEX idx_task_derivations_task
  ON meetings.task_derivations(task_id);

CREATE INDEX idx_task_derivations_unapproved
  ON meetings.task_derivations(created_at DESC)
  WHERE user_approved IS NULL AND derivation_method = 'suggested';

COMMENT ON TABLE meetings.task_derivations IS 'Tracks derivation of tasks from action items';
COMMENT ON COLUMN meetings.task_derivations.derivation_method IS 'How task was created from action item';
COMMENT ON COLUMN meetings.task_derivations.user_approved IS 'Whether user explicitly approved the derivation';

-- ========================================================================================
-- PART 8: SPEAKER DIARIZATION TABLE
-- ========================================================================================

CREATE TABLE IF NOT EXISTS meetings.speakers (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  transcript_id     uuid NOT NULL REFERENCES meetings.transcripts(id) ON DELETE CASCADE,

  -- Speaker identification
  speaker_id        text NOT NULL,  -- Platform-specific speaker ID or name
  display_name      text,
  email             text,
  contact_id        uuid REFERENCES core.contacts(id) ON DELETE SET NULL,

  -- Speaking statistics
  total_speaking_time_sec int DEFAULT 0,
  segment_count     int DEFAULT 0,
  word_count        int DEFAULT 0,

  -- Participation metrics
  questions_asked   int DEFAULT 0,
  decisions_made    int DEFAULT 0,
  action_items_assigned int DEFAULT 0,

  -- Audio metadata
  avg_confidence    double precision,  -- Diarization confidence

  metadata          jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at        timestamptz NOT NULL DEFAULT now(),

  CONSTRAINT speakers_unique_transcript_speaker UNIQUE (transcript_id, speaker_id)
);

CREATE INDEX idx_speakers_transcript
  ON meetings.speakers(transcript_id);

CREATE INDEX idx_speakers_contact
  ON meetings.speakers(contact_id)
  WHERE contact_id IS NOT NULL;

CREATE INDEX idx_speakers_email
  ON meetings.speakers(email)
  WHERE email IS NOT NULL;

COMMENT ON TABLE meetings.speakers IS 'Speaker diarization and statistics per meeting';
COMMENT ON COLUMN meetings.speakers.avg_confidence IS 'Average speaker identification confidence';
COMMENT ON COLUMN meetings.speakers.questions_asked IS 'Number of questions posed by speaker';

-- ========================================================================================
-- PART 9: VIEWS FOR MEETING INTELLIGENCE
-- ========================================================================================

-- View: High-confidence action items awaiting routing
CREATE OR REPLACE VIEW meetings.v_pending_action_items AS
SELECT
  ai.*,
  t.title AS meeting_title,
  t.recorded_at AS meeting_date,
  f.display_name AS founder_name,
  w.name AS workspace_name
FROM meetings.action_items ai
JOIN meetings.transcripts t ON ai.transcript_id = t.id
JOIN core.founders f ON ai.founder_id = f.id
JOIN core.workspaces w ON ai.workspace_id = w.id
WHERE ai.status = 'detected'
  AND ai.confidence >= 0.8
ORDER BY ai.confidence DESC, ai.priority DESC, ai.created_at DESC;

COMMENT ON VIEW meetings.v_pending_action_items IS 'High-confidence action items ready for task creation';

-- View: Recent decisions by workspace
CREATE OR REPLACE VIEW meetings.v_recent_decisions AS
SELECT
  d.*,
  t.title AS meeting_title,
  t.recorded_at AS meeting_date,
  f.display_name AS founder_name,
  EXTRACT(EPOCH FROM (now() - d.created_at)) / 86400 AS days_ago
FROM meetings.decisions d
JOIN meetings.transcripts t ON d.transcript_id = t.id
JOIN core.founders f ON d.founder_id = f.id
WHERE d.created_at >= now() - interval '30 days'
ORDER BY d.created_at DESC, d.impact_score DESC NULLS LAST;

COMMENT ON VIEW meetings.v_recent_decisions IS 'Decisions made in last 30 days';

-- View: Processing pipeline status
CREATE OR REPLACE VIEW meetings.v_processing_pipeline AS
SELECT
  t.id AS transcript_id,
  t.title,
  t.provider,
  t.processing_status,
  t.chunk_count,
  t.created_at,
  t.processing_started_at,
  t.processing_completed_at,
  EXTRACT(EPOCH FROM (
    COALESCE(t.processing_completed_at, now()) - t.processing_started_at
  )) AS processing_duration_sec,
  (
    SELECT COUNT(*)
    FROM meetings.action_items ai
    WHERE ai.transcript_id = t.id
  ) AS action_items_count,
  (
    SELECT COUNT(*)
    FROM meetings.decisions d
    WHERE d.transcript_id = t.id
  ) AS decisions_count,
  (
    SELECT COUNT(*)
    FROM meetings.processing_jobs pj
    WHERE pj.transcript_id = t.id
      AND pj.status = 'failed'
  ) AS failed_jobs_count
FROM meetings.transcripts t
WHERE t.created_at >= now() - interval '7 days'
ORDER BY t.created_at DESC;

COMMENT ON VIEW meetings.v_processing_pipeline IS 'Pipeline status for recent transcripts';

-- View: Action item conversion metrics
CREATE OR REPLACE VIEW meetings.v_action_item_metrics AS
SELECT
  ai.workspace_id,
  w.name AS workspace_name,
  COUNT(*) AS total_action_items,
  COUNT(*) FILTER (WHERE ai.status = 'task_created') AS tasks_created,
  COUNT(*) FILTER (WHERE ai.status = 'dismissed') AS dismissed,
  COUNT(*) FILTER (WHERE ai.confidence >= 0.9) AS very_high_confidence,
  COUNT(*) FILTER (WHERE ai.confidence >= 0.8 AND ai.confidence < 0.9) AS high_confidence,
  COUNT(*) FILTER (WHERE ai.task_id IS NOT NULL) AS linked_to_tasks,
  ROUND(AVG(ai.confidence)::numeric, 3) AS avg_confidence,
  COUNT(*) FILTER (WHERE ai.status = 'task_created')::float /
    NULLIF(COUNT(*), 0) AS conversion_rate
FROM meetings.action_items ai
JOIN core.workspaces w ON ai.workspace_id = w.id
WHERE ai.created_at >= now() - interval '30 days'
GROUP BY ai.workspace_id, w.name
ORDER BY total_action_items DESC;

COMMENT ON VIEW meetings.v_action_item_metrics IS 'Action item performance metrics per workspace';

-- ========================================================================================
-- PART 10: FUNCTIONS FOR MEETING INTELLIGENCE
-- ========================================================================================

-- Function: Calculate confidence level from score
CREATE OR REPLACE FUNCTION meetings.calculate_confidence_level(
  confidence_score double precision
)
RETURNS meetings.confidence_level AS $$
BEGIN
  IF confidence_score >= 0.9 THEN
    RETURN 'very_high';
  ELSIF confidence_score >= 0.8 THEN
    RETURN 'high';
  ELSIF confidence_score >= 0.7 THEN
    RETURN 'medium';
  ELSIF confidence_score >= 0.5 THEN
    RETURN 'low';
  ELSE
    RETURN 'very_low';
  END IF;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

COMMENT ON FUNCTION meetings.calculate_confidence_level IS 'Convert confidence score to discrete level';

-- Function: Update processing status
CREATE OR REPLACE FUNCTION meetings.update_processing_status(
  p_transcript_id uuid,
  p_new_status meetings.processing_status,
  p_error_message text DEFAULT NULL
)
RETURNS void AS $$
BEGIN
  UPDATE meetings.transcripts
  SET
    processing_status = p_new_status,
    processing_started_at = CASE
      WHEN p_new_status NOT IN ('pending', 'failed', 'completed')
        AND processing_started_at IS NULL
      THEN now()
      ELSE processing_started_at
    END,
    processing_completed_at = CASE
      WHEN p_new_status IN ('completed', 'failed')
      THEN now()
      ELSE processing_completed_at
    END,
    processing_error = p_error_message
  WHERE id = p_transcript_id;

  -- Log event
  INSERT INTO ops.events (
    workspace_id,
    actor_type,
    actor_id,
    event_type,
    entity_type,
    entity_id,
    payload
  )
  SELECT
    workspace_id,
    'system',
    NULL,
    'transcript.processing_status_changed',
    'transcript',
    id,
    jsonb_build_object(
      'new_status', p_new_status,
      'error', p_error_message
    )
  FROM meetings.transcripts
  WHERE id = p_transcript_id;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION meetings.update_processing_status IS 'Update transcript processing status and log event';

-- Function: Create action item from extracted data
CREATE OR REPLACE FUNCTION meetings.create_action_item(
  p_transcript_id uuid,
  p_chunk_id uuid,
  p_action_text text,
  p_confidence double precision,
  p_assignee text DEFAULT NULL,
  p_due_date timestamptz DEFAULT NULL,
  p_priority core.priority_enum DEFAULT 'normal',
  p_metadata jsonb DEFAULT '{}'::jsonb
)
RETURNS uuid AS $$
DECLARE
  v_workspace_id uuid;
  v_founder_id uuid;
  v_action_item_id uuid;
BEGIN
  -- Get workspace and founder from transcript
  SELECT workspace_id, founder_id
  INTO v_workspace_id, v_founder_id
  FROM meetings.transcripts
  WHERE id = p_transcript_id;

  -- Insert action item
  INSERT INTO meetings.action_items (
    workspace_id,
    founder_id,
    transcript_id,
    chunk_id,
    action_text,
    confidence,
    confidence_level,
    assignee,
    due_date,
    priority,
    metadata
  ) VALUES (
    v_workspace_id,
    v_founder_id,
    p_transcript_id,
    p_chunk_id,
    p_action_text,
    p_confidence,
    meetings.calculate_confidence_level(p_confidence),
    p_assignee,
    p_due_date,
    p_priority,
    p_metadata
  ) RETURNING id INTO v_action_item_id;

  RETURN v_action_item_id;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION meetings.create_action_item IS 'Create action item with automatic metadata';

-- Function: Link action item to task
CREATE OR REPLACE FUNCTION meetings.link_action_to_task(
  p_action_item_id uuid,
  p_task_id uuid,
  p_derivation_method text DEFAULT 'automatic'
)
RETURNS uuid AS $$
DECLARE
  v_derivation_id uuid;
BEGIN
  -- Update action item status
  UPDATE meetings.action_items
  SET
    status = 'task_created',
    task_id = p_task_id,
    updated_at = now()
  WHERE id = p_action_item_id;

  -- Create derivation record
  INSERT INTO meetings.task_derivations (
    action_item_id,
    task_id,
    derivation_method
  ) VALUES (
    p_action_item_id,
    p_task_id,
    p_derivation_method
  ) RETURNING id INTO v_derivation_id;

  RETURN v_derivation_id;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION meetings.link_action_to_task IS 'Link action item to created task';

-- ========================================================================================
-- PART 11: TRIGGERS
-- ========================================================================================

-- Trigger: Auto-update action item timestamps
CREATE TRIGGER update_action_items_updated_at
  BEFORE UPDATE ON meetings.action_items
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_decisions_updated_at
  BEFORE UPDATE ON meetings.decisions
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

-- Trigger: Log action item status changes
CREATE OR REPLACE FUNCTION meetings.log_action_item_status_change()
RETURNS TRIGGER AS $$
BEGIN
  IF OLD.status IS DISTINCT FROM NEW.status THEN
    INSERT INTO ops.events (
      workspace_id,
      actor_type,
      event_type,
      entity_type,
      entity_id,
      payload
    ) VALUES (
      NEW.workspace_id,
      'system',
      'action_item.status_changed',
      'action_item',
      NEW.id,
      jsonb_build_object(
        'old_status', OLD.status,
        'new_status', NEW.status,
        'action_text', NEW.action_text,
        'task_id', NEW.task_id
      )
    );
  END IF;

  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER action_item_status_change_logger
  AFTER UPDATE ON meetings.action_items
  FOR EACH ROW
  EXECUTE FUNCTION meetings.log_action_item_status_change();

COMMENT ON FUNCTION meetings.log_action_item_status_change IS 'Log action item status changes to ops.events';

-- ========================================================================================
-- PART 12: PERFORMANCE OPTIMIZATION
-- ========================================================================================

-- Analyze tables for query optimization
ANALYZE meetings.action_items;
ANALYZE meetings.decisions;
ANALYZE meetings.summary_versions;
ANALYZE meetings.processing_jobs;
ANALYZE meetings.task_derivations;
ANALYZE meetings.speakers;

-- ========================================================================================
-- PART 13: MIGRATION METADATA
-- ========================================================================================

INSERT INTO public.schema_migrations (version, description)
VALUES ('004', 'Meeting Intelligence - Action Items, Decisions, Task Routing')
ON CONFLICT (version) DO NOTHING;

-- ========================================================================================
-- END OF MIGRATION 004_meeting_intelligence.sql
-- ========================================================================================
