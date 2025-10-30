-- ========================================================================================
-- Migration: 001_initial_schema.sql
-- Description: AI Chief of Staff - Core Infrastructure & Data Foundation
-- Author: System Architect
-- Date: 2025-10-30
-- Sprint: 1 - Core Infrastructure & Data Foundation
--
-- This migration establishes the complete multi-tenant database schema including:
-- - 7 domain schemas: core, ops, comms, meetings, media, work, intel
-- - pgvector extension for semantic search
-- - Multi-tenant workspace isolation
-- - Event sourcing infrastructure
-- - Comprehensive indexes for performance
--
-- Dependencies:
-- - PostgreSQL 14+
-- - pgvector extension
-- ========================================================================================

-- ========================================================================================
-- PART 1: EXTENSIONS & SCHEMAS
-- ========================================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "vector";

-- Create domain schemas for logical separation
CREATE SCHEMA IF NOT EXISTS core;      -- Core entities: workspaces, members, founders, contacts
CREATE SCHEMA IF NOT EXISTS ops;       -- Operations: events, audit trail
CREATE SCHEMA IF NOT EXISTS comms;     -- Communications: emails, slack, discord messages
CREATE SCHEMA IF NOT EXISTS meetings;  -- Meetings: zoom, calendars, transcripts
CREATE SCHEMA IF NOT EXISTS media;     -- Media assets: loom videos, recordings
CREATE SCHEMA IF NOT EXISTS work;      -- Work management: tasks, projects
CREATE SCHEMA IF NOT EXISTS intel;     -- Intelligence: briefings, insights, decisions

COMMENT ON SCHEMA core IS 'Core multi-tenant entities and master data';
COMMENT ON SCHEMA ops IS 'Operational event sourcing and audit trail';
COMMENT ON SCHEMA comms IS 'Cross-platform communication aggregation';
COMMENT ON SCHEMA meetings IS 'Meeting management and transcription';
COMMENT ON SCHEMA media IS 'Media asset management and transcription';
COMMENT ON SCHEMA work IS 'Task and work item tracking';
COMMENT ON SCHEMA intel IS 'AI-generated insights and briefings';

-- ========================================================================================
-- PART 2: ENUMS & TYPES
-- ========================================================================================

-- Core domain enums
DO $$ BEGIN
  -- Role types for workspace members
  CREATE TYPE core.role_type AS ENUM (
    'owner',      -- Full control over workspace
    'admin',      -- Administrative access
    'member',     -- Standard member access
    'viewer',     -- Read-only access
    'service'     -- Service account / API access
  );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  -- Integration connection status
  CREATE TYPE core.integration_status AS ENUM (
    'connected',  -- Active and working
    'error',      -- Connection error
    'revoked',    -- Access revoked by user
    'pending'     -- Awaiting authorization
  );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  -- Integration connection type
  CREATE TYPE core.connection_type AS ENUM (
    'mcp',        -- Model Context Protocol
    'api'         -- Direct API integration
  );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  -- Supported platform integrations
  CREATE TYPE core.platform_enum AS ENUM (
    'gmail',
    'outlook',
    'slack',
    'discord',
    'zoom',
    'loom',
    'fireflies',
    'otter',
    'monday',
    'notion',
    'granola',
    'zerodb',
    'zerovoice'
  );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  -- Priority levels
  CREATE TYPE core.priority_enum AS ENUM (
    'urgent',     -- Immediate attention required
    'high',       -- High priority
    'normal',     -- Standard priority
    'low'         -- Low priority
  );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  -- Communication source types
  CREATE TYPE comms.source_enum AS ENUM (
    'email',      -- Email (Gmail/Outlook)
    'slack',      -- Slack message
    'discord',    -- Discord message
    'system'      -- System-generated
  );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  -- Task status workflow
  CREATE TYPE work.task_status_enum AS ENUM (
    'todo',         -- Not started
    'in_progress',  -- Currently being worked on
    'blocked',      -- Blocked/waiting
    'done',         -- Completed
    'canceled'      -- Canceled/deprecated
  );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  -- Insight classification types
  CREATE TYPE intel.insight_type_enum AS ENUM (
    'kpi',              -- Key performance indicator
    'decision_hint',    -- Suggested decision
    'recommendation',   -- AI recommendation
    'risk',            -- Risk alert
    'anomaly'          -- Detected anomaly
  );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- ========================================================================================
-- PART 3: CORE SCHEMA - Multi-tenant Foundation
-- ========================================================================================

-- Workspaces: Top-level tenant isolation
CREATE TABLE IF NOT EXISTS core.workspaces (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name          text NOT NULL,
  settings      jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at    timestamptz NOT NULL DEFAULT now(),
  updated_at    timestamptz NOT NULL DEFAULT now(),

  CONSTRAINT workspaces_name_check CHECK (length(trim(name)) > 0)
);

CREATE INDEX idx_workspaces_created_at ON core.workspaces(created_at DESC);

COMMENT ON TABLE core.workspaces IS 'Top-level tenant isolation for multi-tenant architecture';
COMMENT ON COLUMN core.workspaces.settings IS 'Workspace configuration and preferences';

-- Members: User access to workspaces
CREATE TABLE IF NOT EXISTS core.members (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id  uuid NOT NULL REFERENCES core.workspaces(id) ON DELETE CASCADE,
  user_id       uuid NOT NULL,  -- References auth.users in Supabase
  role          core.role_type NOT NULL DEFAULT 'member',
  metadata      jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at    timestamptz NOT NULL DEFAULT now(),
  updated_at    timestamptz NOT NULL DEFAULT now(),

  CONSTRAINT members_unique_user_workspace UNIQUE (workspace_id, user_id)
);

CREATE INDEX idx_members_workspace_id ON core.members(workspace_id);
CREATE INDEX idx_members_user_id ON core.members(user_id);
CREATE INDEX idx_members_role ON core.members(workspace_id, role);

COMMENT ON TABLE core.members IS 'Workspace membership and role-based access control';
COMMENT ON COLUMN core.members.user_id IS 'Foreign key to Supabase auth.users';

-- Founders: Primary users tracked by the AI Chief of Staff
CREATE TABLE IF NOT EXISTS core.founders (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id  uuid NOT NULL REFERENCES core.workspaces(id) ON DELETE CASCADE,
  user_id       uuid NOT NULL,  -- References auth.users
  display_name  text,
  email         text,
  timezone      text DEFAULT 'UTC',
  preferences   jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at    timestamptz NOT NULL DEFAULT now(),
  updated_at    timestamptz NOT NULL DEFAULT now(),

  CONSTRAINT founders_unique_workspace_user UNIQUE (workspace_id, user_id),
  CONSTRAINT founders_email_format CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$')
);

CREATE INDEX idx_founders_workspace_id ON core.founders(workspace_id);
CREATE INDEX idx_founders_user_id ON core.founders(user_id);
CREATE INDEX idx_founders_email ON core.founders(email) WHERE email IS NOT NULL;

COMMENT ON TABLE core.founders IS 'Primary users being assisted by the AI Chief of Staff';
COMMENT ON COLUMN core.founders.preferences IS 'User preferences: briefing times, communication style, etc.';

-- Integrations: External platform connections
CREATE TABLE IF NOT EXISTS core.integrations (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id    uuid NOT NULL REFERENCES core.workspaces(id) ON DELETE CASCADE,
  founder_id      uuid REFERENCES core.founders(id) ON DELETE SET NULL,
  platform        core.platform_enum NOT NULL,
  connection_type core.connection_type NOT NULL DEFAULT 'mcp',
  status          core.integration_status NOT NULL DEFAULT 'pending',
  credentials_enc bytea,  -- Encrypted credentials (use Supabase Vault in production)
  metadata        jsonb NOT NULL DEFAULT '{}'::jsonb,
  connected_at    timestamptz,
  last_sync_at    timestamptz,
  error_message   text,
  created_at      timestamptz NOT NULL DEFAULT now(),
  updated_at      timestamptz NOT NULL DEFAULT now(),

  CONSTRAINT integrations_unique_platform UNIQUE (workspace_id, founder_id, platform)
);

CREATE INDEX idx_integrations_workspace_id ON core.integrations(workspace_id);
CREATE INDEX idx_integrations_workspace_platform ON core.integrations(workspace_id, platform);
CREATE INDEX idx_integrations_status ON core.integrations(status) WHERE status != 'connected';
CREATE INDEX idx_integrations_last_sync ON core.integrations(last_sync_at DESC) WHERE status = 'connected';

COMMENT ON TABLE core.integrations IS 'External platform integrations (MCP and API connections)';
COMMENT ON COLUMN core.integrations.credentials_enc IS 'Encrypted OAuth tokens and API keys';
COMMENT ON COLUMN core.integrations.metadata IS 'Platform-specific configuration and state';

-- Contacts: People tracked across communications
CREATE TABLE IF NOT EXISTS core.contacts (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id    uuid NOT NULL REFERENCES core.workspaces(id) ON DELETE CASCADE,
  founder_id      uuid NOT NULL REFERENCES core.founders(id) ON DELETE CASCADE,
  name            text NOT NULL,
  type            text,  -- 'investor', 'advisor', 'team', 'partner', 'customer'
  company         text,
  title           text,
  email           text,
  phone           text,
  context         jsonb NOT NULL DEFAULT '{}'::jsonb,
  tags            text[] DEFAULT '{}',
  embedding       vector(1536),  -- Semantic representation of contact context
  last_contacted  timestamptz,
  created_at      timestamptz NOT NULL DEFAULT now(),
  updated_at      timestamptz NOT NULL DEFAULT now(),

  CONSTRAINT contacts_name_check CHECK (length(trim(name)) > 0)
);

CREATE INDEX idx_contacts_workspace_founder ON core.contacts(workspace_id, founder_id);
CREATE INDEX idx_contacts_type ON core.contacts(workspace_id, type) WHERE type IS NOT NULL;
CREATE INDEX idx_contacts_email ON core.contacts(email) WHERE email IS NOT NULL;
CREATE INDEX idx_contacts_last_contacted ON core.contacts(workspace_id, founder_id, last_contacted DESC NULLS LAST);
CREATE INDEX idx_contacts_tags ON core.contacts USING GIN(tags);

-- Vector similarity search index for contacts
CREATE INDEX idx_contacts_embedding ON core.contacts
  USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100)
  WHERE embedding IS NOT NULL;

COMMENT ON TABLE core.contacts IS 'People network: investors, advisors, team members, customers';
COMMENT ON COLUMN core.contacts.embedding IS 'Vector embedding for semantic contact search (1536-dim for OpenAI ada-002)';
COMMENT ON COLUMN core.contacts.context IS 'Relationship history, notes, interaction summary';

-- ========================================================================================
-- PART 4: COMMS SCHEMA - Communication Aggregation
-- ========================================================================================

-- Threads: Conversation groupings across platforms
CREATE TABLE IF NOT EXISTS comms.threads (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id  uuid NOT NULL REFERENCES core.workspaces(id) ON DELETE CASCADE,
  founder_id    uuid NOT NULL REFERENCES core.founders(id) ON DELETE CASCADE,
  platform      core.platform_enum NOT NULL,
  external_id   text,  -- Platform-specific thread ID
  subject       text,
  participants  text[] DEFAULT '{}',
  metadata      jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at    timestamptz NOT NULL DEFAULT now(),
  updated_at    timestamptz NOT NULL DEFAULT now(),

  CONSTRAINT threads_unique_platform_external UNIQUE (workspace_id, platform, external_id)
);

CREATE INDEX idx_threads_workspace_founder ON comms.threads(workspace_id, founder_id);
CREATE INDEX idx_threads_platform ON comms.threads(workspace_id, platform);
CREATE INDEX idx_threads_updated_at ON comms.threads(updated_at DESC);

COMMENT ON TABLE comms.threads IS 'Conversation threads across email, Slack, Discord';
COMMENT ON COLUMN comms.threads.external_id IS 'Platform-specific thread/conversation identifier';

-- Communications: Individual messages
CREATE TABLE IF NOT EXISTS comms.communications (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id    uuid NOT NULL REFERENCES core.workspaces(id) ON DELETE CASCADE,
  founder_id      uuid NOT NULL REFERENCES core.founders(id) ON DELETE CASCADE,
  thread_id       uuid REFERENCES comms.threads(id) ON DELETE SET NULL,
  platform        core.platform_enum NOT NULL,
  source          comms.source_enum NOT NULL,
  external_id     text,  -- Platform message ID
  sender          text,
  sender_email    text,
  recipients      text[] DEFAULT '{}',
  subject         text,
  content         text,
  snippet         text,  -- First 280 chars for quick preview
  sentiment       jsonb,  -- {score: float, label: string, confidence: float}
  urgency         core.priority_enum,
  followup_needed boolean NOT NULL DEFAULT false,
  received_at     timestamptz,
  read_at         timestamptz,
  embedding       vector(1536),  -- Semantic content embedding
  raw             jsonb,  -- Full raw API response
  created_at      timestamptz NOT NULL DEFAULT now(),

  CONSTRAINT communications_unique_platform_external UNIQUE (workspace_id, platform, external_id)
);

CREATE INDEX idx_comms_workspace_founder ON comms.communications(workspace_id, founder_id);
CREATE INDEX idx_comms_platform_received ON comms.communications(workspace_id, platform, received_at DESC);
CREATE INDEX idx_comms_thread_id ON comms.communications(thread_id) WHERE thread_id IS NOT NULL;
CREATE INDEX idx_comms_followup ON comms.communications(workspace_id, founder_id, followup_needed)
  WHERE followup_needed = true;
CREATE INDEX idx_comms_unread ON comms.communications(workspace_id, founder_id, received_at DESC)
  WHERE read_at IS NULL;
CREATE INDEX idx_comms_urgency ON comms.communications(workspace_id, urgency)
  WHERE urgency IN ('urgent', 'high');

-- Vector similarity search for communications
CREATE INDEX idx_comms_embedding ON comms.communications
  USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100)
  WHERE embedding IS NOT NULL;

COMMENT ON TABLE comms.communications IS 'Unified inbox: emails, Slack messages, Discord messages';
COMMENT ON COLUMN comms.communications.embedding IS 'Vector embedding for semantic message search';
COMMENT ON COLUMN comms.communications.sentiment IS 'AI-analyzed sentiment: positive/negative/neutral with confidence';

-- ========================================================================================
-- PART 5: MEETINGS SCHEMA - Meeting Intelligence
-- ========================================================================================

-- Meetings: Calendar events and recorded meetings
CREATE TABLE IF NOT EXISTS meetings.meetings (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id  uuid NOT NULL REFERENCES core.workspaces(id) ON DELETE CASCADE,
  founder_id    uuid NOT NULL REFERENCES core.founders(id) ON DELETE CASCADE,
  platform      core.platform_enum NOT NULL,
  external_id   text,  -- Zoom meeting ID, calendar event ID
  title         text,
  description   text,
  agenda        text,
  start_time    timestamptz,
  end_time      timestamptz,
  duration_mins int GENERATED ALWAYS AS (
    EXTRACT(EPOCH FROM (end_time - start_time)) / 60
  ) STORED,
  location_url  text,  -- Zoom link, Google Meet link, etc.
  summary       text,  -- AI-generated meeting summary
  action_items  jsonb NOT NULL DEFAULT '[]'::jsonb,
  metadata      jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at    timestamptz NOT NULL DEFAULT now(),
  updated_at    timestamptz NOT NULL DEFAULT now(),

  CONSTRAINT meetings_unique_platform_external UNIQUE (workspace_id, platform, external_id),
  CONSTRAINT meetings_time_order CHECK (start_time IS NULL OR end_time IS NULL OR start_time <= end_time)
);

CREATE INDEX idx_meetings_workspace_founder ON meetings.meetings(workspace_id, founder_id);
CREATE INDEX idx_meetings_start_time ON meetings.meetings(workspace_id, founder_id, start_time DESC);
CREATE INDEX idx_meetings_platform ON meetings.meetings(workspace_id, platform);
CREATE INDEX idx_meetings_upcoming ON meetings.meetings(start_time)
  WHERE start_time >= now();

COMMENT ON TABLE meetings.meetings IS 'Calendar events and recorded meetings from Zoom, Google Calendar, Outlook';
COMMENT ON COLUMN meetings.meetings.action_items IS 'Array of extracted action items from meeting';

-- Meeting Participants: Who attended each meeting
CREATE TABLE IF NOT EXISTS meetings.meeting_participants (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  meeting_id    uuid NOT NULL REFERENCES meetings.meetings(id) ON DELETE CASCADE,
  contact_id    uuid REFERENCES core.contacts(id) ON DELETE SET NULL,
  name          text,
  email         text,
  role          text,  -- 'host', 'guest', 'speaker', 'attendee'
  joined_at     timestamptz,
  left_at       timestamptz,
  metadata      jsonb NOT NULL DEFAULT '{}'::jsonb,

  CONSTRAINT participant_time_order CHECK (joined_at IS NULL OR left_at IS NULL OR joined_at <= left_at)
);

CREATE INDEX idx_participants_meeting_id ON meetings.meeting_participants(meeting_id);
CREATE INDEX idx_participants_contact_id ON meetings.meeting_participants(contact_id) WHERE contact_id IS NOT NULL;

COMMENT ON TABLE meetings.meeting_participants IS 'Meeting attendance tracking and participant metadata';

-- Transcripts: Meeting transcriptions from various providers
CREATE TABLE IF NOT EXISTS meetings.transcripts (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id  uuid NOT NULL REFERENCES core.workspaces(id) ON DELETE CASCADE,
  founder_id    uuid NOT NULL REFERENCES core.founders(id) ON DELETE CASCADE,
  meeting_id    uuid REFERENCES meetings.meetings(id) ON DELETE CASCADE,
  provider      core.platform_enum NOT NULL,  -- 'zoom', 'fireflies', 'otter'
  external_id   text,  -- Provider's transcript ID
  title         text,
  url           text,
  language      text DEFAULT 'en',
  summary       jsonb NOT NULL DEFAULT '{}'::jsonb,  -- {tldr, bullets, themes}
  action_items  jsonb NOT NULL DEFAULT '[]'::jsonb,
  topics        text[] DEFAULT '{}',
  recorded_at   timestamptz,
  processed_at  timestamptz,
  metadata      jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at    timestamptz NOT NULL DEFAULT now(),

  CONSTRAINT transcripts_unique_provider_external UNIQUE (workspace_id, provider, external_id)
);

CREATE INDEX idx_transcripts_workspace_founder ON meetings.transcripts(workspace_id, founder_id);
CREATE INDEX idx_transcripts_meeting_id ON meetings.transcripts(meeting_id) WHERE meeting_id IS NOT NULL;
CREATE INDEX idx_transcripts_provider ON meetings.transcripts(workspace_id, provider);
CREATE INDEX idx_transcripts_recorded ON meetings.transcripts(workspace_id, founder_id, recorded_at DESC);
CREATE INDEX idx_transcripts_topics ON meetings.transcripts USING GIN(topics);

COMMENT ON TABLE meetings.transcripts IS 'Meeting transcripts from Zoom, Fireflies, Otter';
COMMENT ON COLUMN meetings.transcripts.summary IS 'AI-generated summary with TLDR, bullets, and key themes';

-- Transcript Chunks: Vectorized transcript segments for semantic search
CREATE TABLE IF NOT EXISTS meetings.transcript_chunks (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  transcript_id uuid NOT NULL REFERENCES meetings.transcripts(id) ON DELETE CASCADE,
  chunk_index   int NOT NULL,
  start_sec     int,
  end_sec       int,
  speaker       text,
  speaker_email text,
  text          text NOT NULL,
  embedding     vector(1536),
  metadata      jsonb NOT NULL DEFAULT '{}'::jsonb,

  CONSTRAINT chunks_unique_transcript_index UNIQUE (transcript_id, chunk_index),
  CONSTRAINT chunks_time_order CHECK (start_sec IS NULL OR end_sec IS NULL OR start_sec <= end_sec)
);

CREATE INDEX idx_chunks_transcript_id ON meetings.transcript_chunks(transcript_id);
CREATE INDEX idx_chunks_speaker ON meetings.transcript_chunks(transcript_id, speaker);

-- Vector similarity search for transcript chunks
CREATE INDEX idx_chunks_embedding ON meetings.transcript_chunks
  USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 200)
  WHERE embedding IS NOT NULL;

COMMENT ON TABLE meetings.transcript_chunks IS 'Chunked and vectorized transcript segments for semantic search';
COMMENT ON COLUMN meetings.transcript_chunks.embedding IS 'Vector embedding for semantic transcript search';

-- ========================================================================================
-- PART 6: MEDIA SCHEMA - Async Media Assets
-- ========================================================================================

-- Media Assets: Loom videos and other async media
CREATE TABLE IF NOT EXISTS media.media_assets (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id  uuid NOT NULL REFERENCES core.workspaces(id) ON DELETE CASCADE,
  founder_id    uuid NOT NULL REFERENCES core.founders(id) ON DELETE CASCADE,
  platform      core.platform_enum NOT NULL,  -- 'loom'
  external_id   text,
  title         text,
  description   text,
  url           text,
  thumbnail_url text,
  duration_secs int,
  recorded_at   timestamptz,
  metadata      jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at    timestamptz NOT NULL DEFAULT now(),

  CONSTRAINT media_unique_platform_external UNIQUE (workspace_id, platform, external_id)
);

CREATE INDEX idx_media_workspace_founder ON media.media_assets(workspace_id, founder_id);
CREATE INDEX idx_media_platform ON media.media_assets(workspace_id, platform);
CREATE INDEX idx_media_recorded ON media.media_assets(workspace_id, founder_id, recorded_at DESC);

COMMENT ON TABLE media.media_assets IS 'Async media assets: Loom videos, screen recordings';

-- Media Transcripts: Transcriptions of media assets
CREATE TABLE IF NOT EXISTS media.media_transcripts (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  media_id      uuid NOT NULL REFERENCES media.media_assets(id) ON DELETE CASCADE,
  provider      core.platform_enum NOT NULL,  -- 'loom', 'otter', 'fireflies'
  language      text DEFAULT 'en',
  summary       jsonb NOT NULL DEFAULT '{}'::jsonb,
  action_items  jsonb NOT NULL DEFAULT '[]'::jsonb,
  topics        text[] DEFAULT '{}',
  processed_at  timestamptz,
  metadata      jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at    timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_media_transcripts_media_id ON media.media_transcripts(media_id);
CREATE INDEX idx_media_transcripts_provider ON media.media_transcripts(provider);
CREATE INDEX idx_media_transcripts_topics ON media.media_transcripts USING GIN(topics);

COMMENT ON TABLE media.media_transcripts IS 'Transcriptions and summaries of media assets';

-- Media Chunks: Vectorized media transcript segments
CREATE TABLE IF NOT EXISTS media.media_chunks (
  id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  media_transcript_id uuid NOT NULL REFERENCES media.media_transcripts(id) ON DELETE CASCADE,
  chunk_index         int NOT NULL,
  start_sec           int,
  end_sec             int,
  speaker             text,
  text                text NOT NULL,
  embedding           vector(1536),
  metadata            jsonb NOT NULL DEFAULT '{}'::jsonb,

  CONSTRAINT media_chunks_unique_transcript_index UNIQUE (media_transcript_id, chunk_index),
  CONSTRAINT media_chunks_time_order CHECK (start_sec IS NULL OR end_sec IS NULL OR start_sec <= end_sec)
);

CREATE INDEX idx_media_chunks_transcript_id ON media.media_chunks(media_transcript_id);

-- Vector similarity search for media chunks
CREATE INDEX idx_media_chunks_embedding ON media.media_chunks
  USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 200)
  WHERE embedding IS NOT NULL;

COMMENT ON TABLE media.media_chunks IS 'Chunked and vectorized media transcript segments';
COMMENT ON COLUMN media.media_chunks.embedding IS 'Vector embedding for semantic media search';

-- ========================================================================================
-- PART 7: WORK SCHEMA - Task Management
-- ========================================================================================

-- Tasks: Action items and work tracking
CREATE TABLE IF NOT EXISTS work.tasks (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id  uuid NOT NULL REFERENCES core.workspaces(id) ON DELETE CASCADE,
  founder_id    uuid NOT NULL REFERENCES core.founders(id) ON DELETE CASCADE,
  title         text NOT NULL,
  description   text,
  platform      core.platform_enum,  -- 'monday', 'notion', NULL for internal
  priority      core.priority_enum DEFAULT 'normal',
  status        work.task_status_enum NOT NULL DEFAULT 'todo',
  due_date      timestamptz,
  completed_at  timestamptz,
  source_ref    jsonb,  -- {type: 'meeting', id: uuid} or {type: 'communication', id: uuid}
  assignee      text,
  tags          text[] DEFAULT '{}',
  metadata      jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at    timestamptz NOT NULL DEFAULT now(),
  updated_at    timestamptz NOT NULL DEFAULT now(),

  CONSTRAINT tasks_title_check CHECK (length(trim(title)) > 0),
  CONSTRAINT tasks_completed_status CHECK (
    (status = 'done' AND completed_at IS NOT NULL) OR
    (status != 'done' AND completed_at IS NULL)
  )
);

CREATE INDEX idx_tasks_workspace_founder ON work.tasks(workspace_id, founder_id);
CREATE INDEX idx_tasks_status ON work.tasks(workspace_id, founder_id, status);
CREATE INDEX idx_tasks_priority ON work.tasks(workspace_id, priority) WHERE status NOT IN ('done', 'canceled');
CREATE INDEX idx_tasks_due_date ON work.tasks(workspace_id, founder_id, due_date)
  WHERE due_date IS NOT NULL AND status NOT IN ('done', 'canceled');
CREATE INDEX idx_tasks_platform ON work.tasks(workspace_id, platform) WHERE platform IS NOT NULL;
CREATE INDEX idx_tasks_tags ON work.tasks USING GIN(tags);

COMMENT ON TABLE work.tasks IS 'Action items and tasks from meetings, emails, and manual entry';
COMMENT ON COLUMN work.tasks.source_ref IS 'Reference to originating entity (meeting, communication, etc.)';

-- Task Links: Sync with external platforms
CREATE TABLE IF NOT EXISTS work.task_links (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  task_id       uuid NOT NULL REFERENCES work.tasks(id) ON DELETE CASCADE,
  platform      core.platform_enum NOT NULL,
  external_id   text NOT NULL,
  url           text,
  sync_status   text DEFAULT 'synced',  -- 'synced', 'pending', 'error'
  last_synced   timestamptz,
  metadata      jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at    timestamptz NOT NULL DEFAULT now(),

  CONSTRAINT task_links_unique_platform_external UNIQUE (platform, external_id)
);

CREATE INDEX idx_task_links_task_id ON work.task_links(task_id);
CREATE INDEX idx_task_links_platform ON work.task_links(platform, external_id);
CREATE INDEX idx_task_links_sync_status ON work.task_links(sync_status) WHERE sync_status != 'synced';

COMMENT ON TABLE work.task_links IS 'Bidirectional sync with Monday.com, Notion, and other task platforms';

-- ========================================================================================
-- PART 8: INTEL SCHEMA - Insights & Briefings
-- ========================================================================================

-- Briefings: Daily summaries and reports
CREATE TABLE IF NOT EXISTS intel.briefings (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id  uuid NOT NULL REFERENCES core.workspaces(id) ON DELETE CASCADE,
  founder_id    uuid NOT NULL REFERENCES core.founders(id) ON DELETE CASCADE,
  kind          text NOT NULL,  -- 'morning', 'evening', 'weekly', 'custom'
  title         text,
  summary       text,
  sections      jsonb NOT NULL DEFAULT '[]'::jsonb,  -- Structured briefing sections
  insights      jsonb NOT NULL DEFAULT '[]'::jsonb,  -- Inline insights array
  period_start  timestamptz,
  period_end    timestamptz,
  generated_at  timestamptz NOT NULL DEFAULT now(),
  metadata      jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at    timestamptz NOT NULL DEFAULT now(),

  CONSTRAINT briefings_kind_check CHECK (kind IN ('morning', 'evening', 'weekly', 'custom'))
);

CREATE INDEX idx_briefings_workspace_founder ON intel.briefings(workspace_id, founder_id);
CREATE INDEX idx_briefings_kind ON intel.briefings(workspace_id, founder_id, kind, generated_at DESC);
CREATE INDEX idx_briefings_generated ON intel.briefings(workspace_id, founder_id, generated_at DESC);

COMMENT ON TABLE intel.briefings IS 'AI-generated daily briefings and periodic summaries';
COMMENT ON COLUMN intel.briefings.sections IS 'Structured sections: meetings, tasks, communications, KPIs';

-- Insights: AI-generated strategic insights
CREATE TABLE IF NOT EXISTS intel.insights (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id  uuid NOT NULL REFERENCES core.workspaces(id) ON DELETE CASCADE,
  founder_id    uuid NOT NULL REFERENCES core.founders(id) ON DELETE CASCADE,
  source        core.platform_enum,  -- 'granola', 'meetings', 'loom', etc.
  insight_type  intel.insight_type_enum NOT NULL,
  title         text,
  content       jsonb NOT NULL,  -- {summary, details, metrics, recommendations}
  confidence    double precision,  -- 0.0 to 1.0
  impact_score  double precision,  -- AI-assessed impact score
  embedding     vector(1536),  -- Semantic insight embedding
  status        text DEFAULT 'active',  -- 'active', 'dismissed', 'acted_on'
  dismissed_at  timestamptz,
  metadata      jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at    timestamptz NOT NULL DEFAULT now(),

  CONSTRAINT insights_confidence_range CHECK (confidence IS NULL OR (confidence >= 0 AND confidence <= 1)),
  CONSTRAINT insights_impact_range CHECK (impact_score IS NULL OR (impact_score >= 0 AND impact_score <= 1))
);

CREATE INDEX idx_insights_workspace_founder ON intel.insights(workspace_id, founder_id);
CREATE INDEX idx_insights_type ON intel.insights(workspace_id, insight_type, created_at DESC);
CREATE INDEX idx_insights_status ON intel.insights(workspace_id, founder_id, status, created_at DESC);
CREATE INDEX idx_insights_confidence ON intel.insights(workspace_id, confidence DESC)
  WHERE confidence IS NOT NULL AND status = 'active';

-- Vector similarity search for insights
CREATE INDEX idx_insights_embedding ON intel.insights
  USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100)
  WHERE embedding IS NOT NULL;

COMMENT ON TABLE intel.insights IS 'AI-generated strategic insights, KPIs, recommendations, and anomalies';
COMMENT ON COLUMN intel.insights.embedding IS 'Vector embedding for semantic insight search and clustering';

-- Decisions: Decision tracking and context
CREATE TABLE IF NOT EXISTS intel.decisions (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id    uuid NOT NULL REFERENCES core.workspaces(id) ON DELETE CASCADE,
  founder_id      uuid NOT NULL REFERENCES core.founders(id) ON DELETE CASCADE,
  title           text NOT NULL,
  context         text,
  options         jsonb NOT NULL DEFAULT '[]'::jsonb,  -- Array of decision options
  recommendation  text,
  chosen_option   text,
  confidence      double precision,
  rationale       text,
  taken           boolean NOT NULL DEFAULT false,
  taken_at        timestamptz,
  outcome         text,
  metadata        jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at      timestamptz NOT NULL DEFAULT now(),
  updated_at      timestamptz NOT NULL DEFAULT now(),

  CONSTRAINT decisions_confidence_range CHECK (confidence IS NULL OR (confidence >= 0 AND confidence <= 1))
);

CREATE INDEX idx_decisions_workspace_founder ON intel.decisions(workspace_id, founder_id);
CREATE INDEX idx_decisions_taken ON intel.decisions(workspace_id, founder_id, taken, created_at DESC);
CREATE INDEX idx_decisions_pending ON intel.decisions(workspace_id, founder_id, created_at DESC)
  WHERE taken = false;

COMMENT ON TABLE intel.decisions IS 'Decision tracking with AI recommendations and outcome tracking';
COMMENT ON COLUMN intel.decisions.options IS 'Array of decision options with pros/cons';

-- ========================================================================================
-- PART 9: OPS SCHEMA - Event Sourcing & Audit Trail
-- ========================================================================================

-- Events: Comprehensive event log for audit and replay
CREATE TABLE IF NOT EXISTS ops.events (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id  uuid NOT NULL REFERENCES core.workspaces(id) ON DELETE CASCADE,
  actor_type    text NOT NULL,  -- 'agent', 'user', 'system', 'integration'
  actor_id      uuid,  -- Member ID, agent ID, or integration ID
  event_type    text NOT NULL,  -- 'ingest', 'summarize', 'route_task', 'send_email', etc.
  entity_type   text,  -- 'communication', 'meeting', 'task', 'insight', 'briefing'
  entity_id     uuid,
  payload       jsonb NOT NULL,  -- Complete event data
  metadata      jsonb NOT NULL DEFAULT '{}'::jsonb,
  version       int DEFAULT 1,
  created_at    timestamptz NOT NULL DEFAULT now(),

  CONSTRAINT events_actor_type_check CHECK (actor_type IN ('agent', 'user', 'system', 'integration'))
);

CREATE INDEX idx_events_workspace ON ops.events(workspace_id, created_at DESC);
CREATE INDEX idx_events_type ON ops.events(workspace_id, event_type, created_at DESC);
CREATE INDEX idx_events_entity ON ops.events(entity_type, entity_id)
  WHERE entity_type IS NOT NULL AND entity_id IS NOT NULL;
CREATE INDEX idx_events_actor ON ops.events(actor_type, actor_id, created_at DESC)
  WHERE actor_id IS NOT NULL;

COMMENT ON TABLE ops.events IS 'Comprehensive event sourcing log for audit trail and replay';
COMMENT ON COLUMN ops.events.payload IS 'Complete event data including inputs, outputs, and state changes';

-- Event Actors: Multi-party event participation
CREATE TABLE IF NOT EXISTS ops.event_actors (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  event_id      uuid NOT NULL REFERENCES ops.events(id) ON DELETE CASCADE,
  role          text NOT NULL,  -- 'origin', 'on_behalf', 'target', 'cc'
  actor_type    text NOT NULL,  -- 'member', 'contact', 'agent', 'integration'
  actor_id      uuid NOT NULL,
  metadata      jsonb NOT NULL DEFAULT '{}'::jsonb,

  CONSTRAINT event_actors_unique UNIQUE (event_id, role, actor_type, actor_id)
);

CREATE INDEX idx_event_actors_event_id ON ops.event_actors(event_id);
CREATE INDEX idx_event_actors_actor ON ops.event_actors(actor_type, actor_id);

COMMENT ON TABLE ops.event_actors IS 'Multi-party participants in events (who triggered, who was affected)';

-- Event Links: Relationships between events and entities
CREATE TABLE IF NOT EXISTS ops.event_links (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  event_id      uuid NOT NULL REFERENCES ops.events(id) ON DELETE CASCADE,
  link_type     text NOT NULL,  -- 'caused', 'derived_from', 'references', 'updates'
  entity_type   text NOT NULL,  -- 'communication', 'meeting', 'task', etc.
  entity_id     uuid NOT NULL,
  metadata      jsonb NOT NULL DEFAULT '{}'::jsonb,

  CONSTRAINT event_links_unique UNIQUE (event_id, link_type, entity_type, entity_id)
);

CREATE INDEX idx_event_links_event_id ON ops.event_links(event_id);
CREATE INDEX idx_event_links_entity ON ops.event_links(entity_type, entity_id);

COMMENT ON TABLE ops.event_links IS 'Causal relationships between events and entities';

-- ========================================================================================
-- PART 10: UTILITY VIEWS
-- ========================================================================================

-- View: Pending follow-ups across all communication channels
CREATE OR REPLACE VIEW comms.v_pending_followups AS
SELECT
  c.*,
  t.subject AS thread_subject,
  co.name AS contact_name,
  co.company AS contact_company
FROM comms.communications c
LEFT JOIN comms.threads t ON c.thread_id = t.id
LEFT JOIN core.contacts co ON c.sender_email = co.email AND c.workspace_id = co.workspace_id
WHERE c.followup_needed = true
ORDER BY
  CASE c.urgency
    WHEN 'urgent' THEN 1
    WHEN 'high' THEN 2
    WHEN 'normal' THEN 3
    WHEN 'low' THEN 4
  END,
  c.received_at DESC;

COMMENT ON VIEW comms.v_pending_followups IS 'All communications requiring follow-up, prioritized by urgency';

-- View: Tasks due within next 72 hours
CREATE OR REPLACE VIEW work.v_tasks_due_soon AS
SELECT
  t.*,
  f.display_name AS founder_name,
  EXTRACT(EPOCH FROM (t.due_date - now())) / 3600 AS hours_until_due
FROM work.tasks t
JOIN core.founders f ON t.founder_id = f.id
WHERE t.status IN ('todo', 'in_progress')
  AND t.due_date IS NOT NULL
  AND t.due_date <= now() + interval '72 hours'
  AND t.due_date >= now()
ORDER BY t.due_date ASC, t.priority DESC;

COMMENT ON VIEW work.v_tasks_due_soon IS 'Tasks due within next 72 hours, ordered by due date';

-- View: Upcoming meetings in next 24 hours
CREATE OR REPLACE VIEW meetings.v_upcoming_meetings AS
SELECT
  m.*,
  f.display_name AS founder_name,
  ARRAY_AGG(DISTINCT p.name) FILTER (WHERE p.name IS NOT NULL) AS participant_names,
  COUNT(DISTINCT p.id) AS participant_count
FROM meetings.meetings m
JOIN core.founders f ON m.founder_id = f.id
LEFT JOIN meetings.meeting_participants p ON m.id = p.meeting_id
WHERE m.start_time >= now()
  AND m.start_time <= now() + interval '24 hours'
GROUP BY m.id, f.display_name
ORDER BY m.start_time ASC;

COMMENT ON VIEW meetings.v_upcoming_meetings IS 'Meetings scheduled for next 24 hours with participants';

-- ========================================================================================
-- PART 11: UTILITY FUNCTIONS
-- ========================================================================================

-- Function: Update updated_at timestamp automatically
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION update_updated_at_column() IS 'Trigger function to automatically update updated_at timestamp';

-- Apply updated_at trigger to relevant tables
CREATE TRIGGER update_workspaces_updated_at BEFORE UPDATE ON core.workspaces
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_members_updated_at BEFORE UPDATE ON core.members
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_founders_updated_at BEFORE UPDATE ON core.founders
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_integrations_updated_at BEFORE UPDATE ON core.integrations
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_contacts_updated_at BEFORE UPDATE ON core.contacts
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_threads_updated_at BEFORE UPDATE ON comms.threads
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_meetings_updated_at BEFORE UPDATE ON meetings.meetings
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_tasks_updated_at BEFORE UPDATE ON work.tasks
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_decisions_updated_at BEFORE UPDATE ON intel.decisions
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function: Generate snippet from content
CREATE OR REPLACE FUNCTION generate_snippet(content text, max_length int DEFAULT 280)
RETURNS text AS $$
BEGIN
  IF content IS NULL THEN
    RETURN NULL;
  END IF;

  IF length(content) <= max_length THEN
    RETURN content;
  END IF;

  RETURN substring(content from 1 for max_length) || '...';
END;
$$ LANGUAGE plpgsql IMMUTABLE;

COMMENT ON FUNCTION generate_snippet(text, int) IS 'Generate a snippet from content with max length';

-- Function: Vector similarity search helper
CREATE OR REPLACE FUNCTION search_similar_embeddings(
  query_embedding vector(1536),
  table_name text,
  match_threshold float DEFAULT 0.7,
  match_count int DEFAULT 10
)
RETURNS TABLE (
  id uuid,
  similarity float
) AS $$
BEGIN
  RETURN QUERY EXECUTE format('
    SELECT id, 1 - (embedding <=> $1) AS similarity
    FROM %I
    WHERE embedding IS NOT NULL
      AND 1 - (embedding <=> $1) > $2
    ORDER BY embedding <=> $1
    LIMIT $3
  ', table_name)
  USING query_embedding, match_threshold, match_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION search_similar_embeddings IS 'Generic vector similarity search across embedding tables';

-- ========================================================================================
-- PART 12: MIGRATION METADATA
-- ========================================================================================

-- Track migration version
CREATE TABLE IF NOT EXISTS public.schema_migrations (
  version       text PRIMARY KEY,
  description   text,
  applied_at    timestamptz NOT NULL DEFAULT now()
);

INSERT INTO public.schema_migrations (version, description)
VALUES ('001', 'Initial schema - Core infrastructure and data foundation')
ON CONFLICT (version) DO NOTHING;

-- ========================================================================================
-- END OF MIGRATION 001_initial_schema.sql
-- ========================================================================================
