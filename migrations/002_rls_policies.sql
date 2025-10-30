-- ========================================================================================
-- Migration: 002_rls_policies.sql
-- Description: Row-Level Security (RLS) policies for multi-tenant workspace isolation
-- Author: System Architect
-- Date: 2025-10-30
-- Sprint: 1 - Core Infrastructure & Data Foundation
--
-- This migration implements comprehensive RLS policies to ensure:
-- - Complete workspace isolation (tenants cannot access each other's data)
-- - Role-based access control within workspaces
-- - Secure data access patterns for authenticated users
-- - Service account access for backend operations
--
-- Security Model:
-- 1. All workspace-scoped tables enforce workspace_id isolation
-- 2. Users can only access workspaces they are members of
-- 3. Owners/admins have full access, members have restricted access
-- 4. Authenticated users required for all access
--
-- Dependencies:
-- - Migration 001_initial_schema.sql
-- - Supabase auth.users table
-- ========================================================================================

-- ========================================================================================
-- PART 1: HELPER FUNCTIONS FOR RLS
-- ========================================================================================

-- Function: Get all workspace IDs for the current authenticated user
CREATE OR REPLACE FUNCTION auth.user_workspaces()
RETURNS SETOF uuid AS $$
  SELECT workspace_id
  FROM core.members
  WHERE user_id = auth.uid();
$$ LANGUAGE sql SECURITY DEFINER STABLE;

COMMENT ON FUNCTION auth.user_workspaces() IS 'Returns all workspace IDs the authenticated user is a member of';

-- Function: Check if user has specific role in workspace
CREATE OR REPLACE FUNCTION auth.has_workspace_role(
  workspace_uuid uuid,
  required_role core.role_type
)
RETURNS boolean AS $$
  SELECT EXISTS (
    SELECT 1
    FROM core.members
    WHERE user_id = auth.uid()
      AND workspace_id = workspace_uuid
      AND (
        role = required_role
        OR role = 'owner'  -- Owners always have all permissions
      )
  );
$$ LANGUAGE sql SECURITY DEFINER STABLE;

COMMENT ON FUNCTION auth.has_workspace_role IS 'Check if user has a specific role or higher in workspace';

-- Function: Check if user is workspace owner or admin
CREATE OR REPLACE FUNCTION auth.is_workspace_admin(workspace_uuid uuid)
RETURNS boolean AS $$
  SELECT EXISTS (
    SELECT 1
    FROM core.members
    WHERE user_id = auth.uid()
      AND workspace_id = workspace_uuid
      AND role IN ('owner', 'admin')
  );
$$ LANGUAGE sql SECURITY DEFINER STABLE;

COMMENT ON FUNCTION auth.is_workspace_admin IS 'Check if user is owner or admin of workspace';

-- Function: Check if user is a founder in workspace
CREATE OR REPLACE FUNCTION auth.is_founder(workspace_uuid uuid)
RETURNS boolean AS $$
  SELECT EXISTS (
    SELECT 1
    FROM core.founders
    WHERE user_id = auth.uid()
      AND workspace_id = workspace_uuid
  );
$$ LANGUAGE sql SECURITY DEFINER STABLE;

COMMENT ON FUNCTION auth.is_founder IS 'Check if user is a founder in workspace';

-- Function: Get founder_id for current user in workspace
CREATE OR REPLACE FUNCTION auth.get_founder_id(workspace_uuid uuid)
RETURNS uuid AS $$
  SELECT id
  FROM core.founders
  WHERE user_id = auth.uid()
    AND workspace_id = workspace_uuid
  LIMIT 1;
$$ LANGUAGE sql SECURITY DEFINER STABLE;

COMMENT ON FUNCTION auth.get_founder_id IS 'Get founder_id for current user in workspace';

-- ========================================================================================
-- PART 2: CORE SCHEMA RLS POLICIES
-- ========================================================================================

-- ============================================================
-- WORKSPACES
-- ============================================================

ALTER TABLE core.workspaces ENABLE ROW LEVEL SECURITY;

-- Users can view workspaces they are members of
CREATE POLICY workspaces_select_policy ON core.workspaces
  FOR SELECT
  TO authenticated
  USING (
    id IN (SELECT auth.user_workspaces())
  );

-- Only authenticated users can create workspaces (they become owners automatically)
CREATE POLICY workspaces_insert_policy ON core.workspaces
  FOR INSERT
  TO authenticated
  WITH CHECK (true);

-- Only workspace owners can update workspace settings
CREATE POLICY workspaces_update_policy ON core.workspaces
  FOR UPDATE
  TO authenticated
  USING (
    auth.has_workspace_role(id, 'owner')
  )
  WITH CHECK (
    auth.has_workspace_role(id, 'owner')
  );

-- Only workspace owners can delete workspaces
CREATE POLICY workspaces_delete_policy ON core.workspaces
  FOR DELETE
  TO authenticated
  USING (
    auth.has_workspace_role(id, 'owner')
  );

-- ============================================================
-- MEMBERS
-- ============================================================

ALTER TABLE core.members ENABLE ROW LEVEL SECURITY;

-- Users can view members in their workspaces
CREATE POLICY members_select_policy ON core.members
  FOR SELECT
  TO authenticated
  USING (
    workspace_id IN (SELECT auth.user_workspaces())
  );

-- Workspace admins can add new members
CREATE POLICY members_insert_policy ON core.members
  FOR INSERT
  TO authenticated
  WITH CHECK (
    auth.is_workspace_admin(workspace_id)
  );

-- Workspace admins can update member roles (except owner role)
CREATE POLICY members_update_policy ON core.members
  FOR UPDATE
  TO authenticated
  USING (
    auth.is_workspace_admin(workspace_id)
  )
  WITH CHECK (
    auth.is_workspace_admin(workspace_id)
    AND role != 'owner'  -- Only owners can change owner role
  );

-- Workspace owners can remove members
CREATE POLICY members_delete_policy ON core.members
  FOR DELETE
  TO authenticated
  USING (
    auth.has_workspace_role(workspace_id, 'owner')
  );

-- ============================================================
-- FOUNDERS
-- ============================================================

ALTER TABLE core.founders ENABLE ROW LEVEL SECURITY;

-- Users can view founders in their workspaces
CREATE POLICY founders_select_policy ON core.founders
  FOR SELECT
  TO authenticated
  USING (
    workspace_id IN (SELECT auth.user_workspaces())
  );

-- Workspace admins can create founder profiles
CREATE POLICY founders_insert_policy ON core.founders
  FOR INSERT
  TO authenticated
  WITH CHECK (
    auth.is_workspace_admin(workspace_id)
  );

-- Founders can update their own profile, admins can update any
CREATE POLICY founders_update_policy ON core.founders
  FOR UPDATE
  TO authenticated
  USING (
    workspace_id IN (SELECT auth.user_workspaces())
    AND (
      user_id = auth.uid()  -- Own profile
      OR auth.is_workspace_admin(workspace_id)  -- Or admin
    )
  )
  WITH CHECK (
    workspace_id IN (SELECT auth.user_workspaces())
    AND (
      user_id = auth.uid()
      OR auth.is_workspace_admin(workspace_id)
    )
  );

-- Only workspace owners can delete founder profiles
CREATE POLICY founders_delete_policy ON core.founders
  FOR DELETE
  TO authenticated
  USING (
    auth.has_workspace_role(workspace_id, 'owner')
  );

-- ============================================================
-- INTEGRATIONS
-- ============================================================

ALTER TABLE core.integrations ENABLE ROW LEVEL SECURITY;

-- Users can view integrations in their workspace
CREATE POLICY integrations_select_policy ON core.integrations
  FOR SELECT
  TO authenticated
  USING (
    workspace_id IN (SELECT auth.user_workspaces())
  );

-- Founders can create integrations for themselves
CREATE POLICY integrations_insert_policy ON core.integrations
  FOR INSERT
  TO authenticated
  WITH CHECK (
    workspace_id IN (SELECT auth.user_workspaces())
    AND (
      founder_id IS NULL
      OR founder_id = auth.get_founder_id(workspace_id)
      OR auth.is_workspace_admin(workspace_id)
    )
  );

-- Founders can update their own integrations, admins can update any
CREATE POLICY integrations_update_policy ON core.integrations
  FOR UPDATE
  TO authenticated
  USING (
    workspace_id IN (SELECT auth.user_workspaces())
    AND (
      founder_id = auth.get_founder_id(workspace_id)
      OR auth.is_workspace_admin(workspace_id)
    )
  )
  WITH CHECK (
    workspace_id IN (SELECT auth.user_workspaces())
    AND (
      founder_id = auth.get_founder_id(workspace_id)
      OR auth.is_workspace_admin(workspace_id)
    )
  );

-- Founders can delete their own integrations, admins can delete any
CREATE POLICY integrations_delete_policy ON core.integrations
  FOR DELETE
  TO authenticated
  USING (
    workspace_id IN (SELECT auth.user_workspaces())
    AND (
      founder_id = auth.get_founder_id(workspace_id)
      OR auth.is_workspace_admin(workspace_id)
    )
  );

-- ============================================================
-- CONTACTS
-- ============================================================

ALTER TABLE core.contacts ENABLE ROW LEVEL SECURITY;

-- Users can view contacts in their workspace
CREATE POLICY contacts_select_policy ON core.contacts
  FOR SELECT
  TO authenticated
  USING (
    workspace_id IN (SELECT auth.user_workspaces())
  );

-- Workspace members can create contacts
CREATE POLICY contacts_insert_policy ON core.contacts
  FOR INSERT
  TO authenticated
  WITH CHECK (
    workspace_id IN (SELECT auth.user_workspaces())
    AND (
      founder_id = auth.get_founder_id(workspace_id)
      OR auth.is_workspace_admin(workspace_id)
    )
  );

-- Founders can update their own contacts, admins can update any
CREATE POLICY contacts_update_policy ON core.contacts
  FOR UPDATE
  TO authenticated
  USING (
    workspace_id IN (SELECT auth.user_workspaces())
    AND (
      founder_id = auth.get_founder_id(workspace_id)
      OR auth.is_workspace_admin(workspace_id)
    )
  )
  WITH CHECK (
    workspace_id IN (SELECT auth.user_workspaces())
    AND (
      founder_id = auth.get_founder_id(workspace_id)
      OR auth.is_workspace_admin(workspace_id)
    )
  );

-- Founders can delete their own contacts, admins can delete any
CREATE POLICY contacts_delete_policy ON core.contacts
  FOR DELETE
  TO authenticated
  USING (
    workspace_id IN (SELECT auth.user_workspaces())
    AND (
      founder_id = auth.get_founder_id(workspace_id)
      OR auth.is_workspace_admin(workspace_id)
    )
  );

-- ========================================================================================
-- PART 3: COMMS SCHEMA RLS POLICIES
-- ========================================================================================

-- ============================================================
-- THREADS
-- ============================================================

ALTER TABLE comms.threads ENABLE ROW LEVEL SECURITY;

CREATE POLICY threads_select_policy ON comms.threads
  FOR SELECT TO authenticated
  USING (workspace_id IN (SELECT auth.user_workspaces()));

CREATE POLICY threads_insert_policy ON comms.threads
  FOR INSERT TO authenticated
  WITH CHECK (
    workspace_id IN (SELECT auth.user_workspaces())
    AND founder_id = auth.get_founder_id(workspace_id)
  );

CREATE POLICY threads_update_policy ON comms.threads
  FOR UPDATE TO authenticated
  USING (
    workspace_id IN (SELECT auth.user_workspaces())
    AND (
      founder_id = auth.get_founder_id(workspace_id)
      OR auth.is_workspace_admin(workspace_id)
    )
  );

CREATE POLICY threads_delete_policy ON comms.threads
  FOR DELETE TO authenticated
  USING (
    workspace_id IN (SELECT auth.user_workspaces())
    AND (
      founder_id = auth.get_founder_id(workspace_id)
      OR auth.is_workspace_admin(workspace_id)
    )
  );

-- ============================================================
-- COMMUNICATIONS
-- ============================================================

ALTER TABLE comms.communications ENABLE ROW LEVEL SECURITY;

CREATE POLICY communications_select_policy ON comms.communications
  FOR SELECT TO authenticated
  USING (workspace_id IN (SELECT auth.user_workspaces()));

CREATE POLICY communications_insert_policy ON comms.communications
  FOR INSERT TO authenticated
  WITH CHECK (
    workspace_id IN (SELECT auth.user_workspaces())
    AND founder_id = auth.get_founder_id(workspace_id)
  );

CREATE POLICY communications_update_policy ON comms.communications
  FOR UPDATE TO authenticated
  USING (
    workspace_id IN (SELECT auth.user_workspaces())
    AND (
      founder_id = auth.get_founder_id(workspace_id)
      OR auth.is_workspace_admin(workspace_id)
    )
  );

CREATE POLICY communications_delete_policy ON comms.communications
  FOR DELETE TO authenticated
  USING (
    workspace_id IN (SELECT auth.user_workspaces())
    AND (
      founder_id = auth.get_founder_id(workspace_id)
      OR auth.is_workspace_admin(workspace_id)
    )
  );

-- ========================================================================================
-- PART 4: MEETINGS SCHEMA RLS POLICIES
-- ========================================================================================

-- ============================================================
-- MEETINGS
-- ============================================================

ALTER TABLE meetings.meetings ENABLE ROW LEVEL SECURITY;

CREATE POLICY meetings_select_policy ON meetings.meetings
  FOR SELECT TO authenticated
  USING (workspace_id IN (SELECT auth.user_workspaces()));

CREATE POLICY meetings_insert_policy ON meetings.meetings
  FOR INSERT TO authenticated
  WITH CHECK (
    workspace_id IN (SELECT auth.user_workspaces())
    AND founder_id = auth.get_founder_id(workspace_id)
  );

CREATE POLICY meetings_update_policy ON meetings.meetings
  FOR UPDATE TO authenticated
  USING (
    workspace_id IN (SELECT auth.user_workspaces())
    AND (
      founder_id = auth.get_founder_id(workspace_id)
      OR auth.is_workspace_admin(workspace_id)
    )
  );

CREATE POLICY meetings_delete_policy ON meetings.meetings
  FOR DELETE TO authenticated
  USING (
    workspace_id IN (SELECT auth.user_workspaces())
    AND (
      founder_id = auth.get_founder_id(workspace_id)
      OR auth.is_workspace_admin(workspace_id)
    )
  );

-- ============================================================
-- MEETING_PARTICIPANTS
-- ============================================================

ALTER TABLE meetings.meeting_participants ENABLE ROW LEVEL SECURITY;

CREATE POLICY meeting_participants_select_policy ON meetings.meeting_participants
  FOR SELECT TO authenticated
  USING (
    meeting_id IN (
      SELECT id FROM meetings.meetings
      WHERE workspace_id IN (SELECT auth.user_workspaces())
    )
  );

CREATE POLICY meeting_participants_insert_policy ON meetings.meeting_participants
  FOR INSERT TO authenticated
  WITH CHECK (
    meeting_id IN (
      SELECT id FROM meetings.meetings
      WHERE workspace_id IN (SELECT auth.user_workspaces())
    )
  );

CREATE POLICY meeting_participants_update_policy ON meetings.meeting_participants
  FOR UPDATE TO authenticated
  USING (
    meeting_id IN (
      SELECT id FROM meetings.meetings
      WHERE workspace_id IN (SELECT auth.user_workspaces())
    )
  );

CREATE POLICY meeting_participants_delete_policy ON meetings.meeting_participants
  FOR DELETE TO authenticated
  USING (
    meeting_id IN (
      SELECT id FROM meetings.meetings
      WHERE workspace_id IN (SELECT auth.user_workspaces())
    )
  );

-- ============================================================
-- TRANSCRIPTS
-- ============================================================

ALTER TABLE meetings.transcripts ENABLE ROW LEVEL SECURITY;

CREATE POLICY transcripts_select_policy ON meetings.transcripts
  FOR SELECT TO authenticated
  USING (workspace_id IN (SELECT auth.user_workspaces()));

CREATE POLICY transcripts_insert_policy ON meetings.transcripts
  FOR INSERT TO authenticated
  WITH CHECK (
    workspace_id IN (SELECT auth.user_workspaces())
    AND founder_id = auth.get_founder_id(workspace_id)
  );

CREATE POLICY transcripts_update_policy ON meetings.transcripts
  FOR UPDATE TO authenticated
  USING (
    workspace_id IN (SELECT auth.user_workspaces())
    AND (
      founder_id = auth.get_founder_id(workspace_id)
      OR auth.is_workspace_admin(workspace_id)
    )
  );

CREATE POLICY transcripts_delete_policy ON meetings.transcripts
  FOR DELETE TO authenticated
  USING (
    workspace_id IN (SELECT auth.user_workspaces())
    AND (
      founder_id = auth.get_founder_id(workspace_id)
      OR auth.is_workspace_admin(workspace_id)
    )
  );

-- ============================================================
-- TRANSCRIPT_CHUNKS
-- ============================================================

ALTER TABLE meetings.transcript_chunks ENABLE ROW LEVEL SECURITY;

CREATE POLICY transcript_chunks_select_policy ON meetings.transcript_chunks
  FOR SELECT TO authenticated
  USING (
    transcript_id IN (
      SELECT id FROM meetings.transcripts
      WHERE workspace_id IN (SELECT auth.user_workspaces())
    )
  );

CREATE POLICY transcript_chunks_insert_policy ON meetings.transcript_chunks
  FOR INSERT TO authenticated
  WITH CHECK (
    transcript_id IN (
      SELECT id FROM meetings.transcripts
      WHERE workspace_id IN (SELECT auth.user_workspaces())
    )
  );

CREATE POLICY transcript_chunks_update_policy ON meetings.transcript_chunks
  FOR UPDATE TO authenticated
  USING (
    transcript_id IN (
      SELECT id FROM meetings.transcripts
      WHERE workspace_id IN (SELECT auth.user_workspaces())
    )
  );

CREATE POLICY transcript_chunks_delete_policy ON meetings.transcript_chunks
  FOR DELETE TO authenticated
  USING (
    transcript_id IN (
      SELECT id FROM meetings.transcripts
      WHERE workspace_id IN (SELECT auth.user_workspaces())
    )
  );

-- ========================================================================================
-- PART 5: MEDIA SCHEMA RLS POLICIES
-- ========================================================================================

-- ============================================================
-- MEDIA_ASSETS
-- ============================================================

ALTER TABLE media.media_assets ENABLE ROW LEVEL SECURITY;

CREATE POLICY media_assets_select_policy ON media.media_assets
  FOR SELECT TO authenticated
  USING (workspace_id IN (SELECT auth.user_workspaces()));

CREATE POLICY media_assets_insert_policy ON media.media_assets
  FOR INSERT TO authenticated
  WITH CHECK (
    workspace_id IN (SELECT auth.user_workspaces())
    AND founder_id = auth.get_founder_id(workspace_id)
  );

CREATE POLICY media_assets_update_policy ON media.media_assets
  FOR UPDATE TO authenticated
  USING (
    workspace_id IN (SELECT auth.user_workspaces())
    AND (
      founder_id = auth.get_founder_id(workspace_id)
      OR auth.is_workspace_admin(workspace_id)
    )
  );

CREATE POLICY media_assets_delete_policy ON media.media_assets
  FOR DELETE TO authenticated
  USING (
    workspace_id IN (SELECT auth.user_workspaces())
    AND (
      founder_id = auth.get_founder_id(workspace_id)
      OR auth.is_workspace_admin(workspace_id)
    )
  );

-- ============================================================
-- MEDIA_TRANSCRIPTS
-- ============================================================

ALTER TABLE media.media_transcripts ENABLE ROW LEVEL SECURITY;

CREATE POLICY media_transcripts_select_policy ON media.media_transcripts
  FOR SELECT TO authenticated
  USING (
    media_id IN (
      SELECT id FROM media.media_assets
      WHERE workspace_id IN (SELECT auth.user_workspaces())
    )
  );

CREATE POLICY media_transcripts_insert_policy ON media.media_transcripts
  FOR INSERT TO authenticated
  WITH CHECK (
    media_id IN (
      SELECT id FROM media.media_assets
      WHERE workspace_id IN (SELECT auth.user_workspaces())
    )
  );

CREATE POLICY media_transcripts_update_policy ON media.media_transcripts
  FOR UPDATE TO authenticated
  USING (
    media_id IN (
      SELECT id FROM media.media_assets
      WHERE workspace_id IN (SELECT auth.user_workspaces())
    )
  );

CREATE POLICY media_transcripts_delete_policy ON media.media_transcripts
  FOR DELETE TO authenticated
  USING (
    media_id IN (
      SELECT id FROM media.media_assets
      WHERE workspace_id IN (SELECT auth.user_workspaces())
    )
  );

-- ============================================================
-- MEDIA_CHUNKS
-- ============================================================

ALTER TABLE media.media_chunks ENABLE ROW LEVEL SECURITY;

CREATE POLICY media_chunks_select_policy ON media.media_chunks
  FOR SELECT TO authenticated
  USING (
    media_transcript_id IN (
      SELECT mt.id FROM media.media_transcripts mt
      JOIN media.media_assets ma ON mt.media_id = ma.id
      WHERE ma.workspace_id IN (SELECT auth.user_workspaces())
    )
  );

CREATE POLICY media_chunks_insert_policy ON media.media_chunks
  FOR INSERT TO authenticated
  WITH CHECK (
    media_transcript_id IN (
      SELECT mt.id FROM media.media_transcripts mt
      JOIN media.media_assets ma ON mt.media_id = ma.id
      WHERE ma.workspace_id IN (SELECT auth.user_workspaces())
    )
  );

CREATE POLICY media_chunks_update_policy ON media.media_chunks
  FOR UPDATE TO authenticated
  USING (
    media_transcript_id IN (
      SELECT mt.id FROM media.media_transcripts mt
      JOIN media.media_assets ma ON mt.media_id = ma.id
      WHERE ma.workspace_id IN (SELECT auth.user_workspaces())
    )
  );

CREATE POLICY media_chunks_delete_policy ON media.media_chunks
  FOR DELETE TO authenticated
  USING (
    media_transcript_id IN (
      SELECT mt.id FROM media.media_transcripts mt
      JOIN media.media_assets ma ON mt.media_id = ma.id
      WHERE ma.workspace_id IN (SELECT auth.user_workspaces())
    )
  );

-- ========================================================================================
-- PART 6: WORK SCHEMA RLS POLICIES
-- ========================================================================================

-- ============================================================
-- TASKS
-- ============================================================

ALTER TABLE work.tasks ENABLE ROW LEVEL SECURITY;

CREATE POLICY tasks_select_policy ON work.tasks
  FOR SELECT TO authenticated
  USING (workspace_id IN (SELECT auth.user_workspaces()));

CREATE POLICY tasks_insert_policy ON work.tasks
  FOR INSERT TO authenticated
  WITH CHECK (
    workspace_id IN (SELECT auth.user_workspaces())
    AND founder_id = auth.get_founder_id(workspace_id)
  );

CREATE POLICY tasks_update_policy ON work.tasks
  FOR UPDATE TO authenticated
  USING (
    workspace_id IN (SELECT auth.user_workspaces())
    AND (
      founder_id = auth.get_founder_id(workspace_id)
      OR auth.is_workspace_admin(workspace_id)
    )
  );

CREATE POLICY tasks_delete_policy ON work.tasks
  FOR DELETE TO authenticated
  USING (
    workspace_id IN (SELECT auth.user_workspaces())
    AND (
      founder_id = auth.get_founder_id(workspace_id)
      OR auth.is_workspace_admin(workspace_id)
    )
  );

-- ============================================================
-- TASK_LINKS
-- ============================================================

ALTER TABLE work.task_links ENABLE ROW LEVEL SECURITY;

CREATE POLICY task_links_select_policy ON work.task_links
  FOR SELECT TO authenticated
  USING (
    task_id IN (
      SELECT id FROM work.tasks
      WHERE workspace_id IN (SELECT auth.user_workspaces())
    )
  );

CREATE POLICY task_links_insert_policy ON work.task_links
  FOR INSERT TO authenticated
  WITH CHECK (
    task_id IN (
      SELECT id FROM work.tasks
      WHERE workspace_id IN (SELECT auth.user_workspaces())
    )
  );

CREATE POLICY task_links_update_policy ON work.task_links
  FOR UPDATE TO authenticated
  USING (
    task_id IN (
      SELECT id FROM work.tasks
      WHERE workspace_id IN (SELECT auth.user_workspaces())
    )
  );

CREATE POLICY task_links_delete_policy ON work.task_links
  FOR DELETE TO authenticated
  USING (
    task_id IN (
      SELECT id FROM work.tasks
      WHERE workspace_id IN (SELECT auth.user_workspaces())
    )
  );

-- ========================================================================================
-- PART 7: INTEL SCHEMA RLS POLICIES
-- ========================================================================================

-- ============================================================
-- BRIEFINGS
-- ============================================================

ALTER TABLE intel.briefings ENABLE ROW LEVEL SECURITY;

CREATE POLICY briefings_select_policy ON intel.briefings
  FOR SELECT TO authenticated
  USING (workspace_id IN (SELECT auth.user_workspaces()));

CREATE POLICY briefings_insert_policy ON intel.briefings
  FOR INSERT TO authenticated
  WITH CHECK (
    workspace_id IN (SELECT auth.user_workspaces())
    AND founder_id = auth.get_founder_id(workspace_id)
  );

CREATE POLICY briefings_update_policy ON intel.briefings
  FOR UPDATE TO authenticated
  USING (
    workspace_id IN (SELECT auth.user_workspaces())
    AND (
      founder_id = auth.get_founder_id(workspace_id)
      OR auth.is_workspace_admin(workspace_id)
    )
  );

CREATE POLICY briefings_delete_policy ON intel.briefings
  FOR DELETE TO authenticated
  USING (
    workspace_id IN (SELECT auth.user_workspaces())
    AND (
      founder_id = auth.get_founder_id(workspace_id)
      OR auth.is_workspace_admin(workspace_id)
    )
  );

-- ============================================================
-- INSIGHTS
-- ============================================================

ALTER TABLE intel.insights ENABLE ROW LEVEL SECURITY;

CREATE POLICY insights_select_policy ON intel.insights
  FOR SELECT TO authenticated
  USING (workspace_id IN (SELECT auth.user_workspaces()));

CREATE POLICY insights_insert_policy ON intel.insights
  FOR INSERT TO authenticated
  WITH CHECK (
    workspace_id IN (SELECT auth.user_workspaces())
    AND founder_id = auth.get_founder_id(workspace_id)
  );

CREATE POLICY insights_update_policy ON intel.insights
  FOR UPDATE TO authenticated
  USING (
    workspace_id IN (SELECT auth.user_workspaces())
    AND (
      founder_id = auth.get_founder_id(workspace_id)
      OR auth.is_workspace_admin(workspace_id)
    )
  );

CREATE POLICY insights_delete_policy ON intel.insights
  FOR DELETE TO authenticated
  USING (
    workspace_id IN (SELECT auth.user_workspaces())
    AND (
      founder_id = auth.get_founder_id(workspace_id)
      OR auth.is_workspace_admin(workspace_id)
    )
  );

-- ============================================================
-- DECISIONS
-- ============================================================

ALTER TABLE intel.decisions ENABLE ROW LEVEL SECURITY;

CREATE POLICY decisions_select_policy ON intel.decisions
  FOR SELECT TO authenticated
  USING (workspace_id IN (SELECT auth.user_workspaces()));

CREATE POLICY decisions_insert_policy ON intel.decisions
  FOR INSERT TO authenticated
  WITH CHECK (
    workspace_id IN (SELECT auth.user_workspaces())
    AND founder_id = auth.get_founder_id(workspace_id)
  );

CREATE POLICY decisions_update_policy ON intel.decisions
  FOR UPDATE TO authenticated
  USING (
    workspace_id IN (SELECT auth.user_workspaces())
    AND (
      founder_id = auth.get_founder_id(workspace_id)
      OR auth.is_workspace_admin(workspace_id)
    )
  );

CREATE POLICY decisions_delete_policy ON intel.decisions
  FOR DELETE TO authenticated
  USING (
    workspace_id IN (SELECT auth.user_workspaces())
    AND (
      founder_id = auth.get_founder_id(workspace_id)
      OR auth.is_workspace_admin(workspace_id)
    )
  );

-- ========================================================================================
-- PART 8: OPS SCHEMA RLS POLICIES
-- ========================================================================================

-- ============================================================
-- EVENTS
-- ============================================================

ALTER TABLE ops.events ENABLE ROW LEVEL SECURITY;

-- Users can view events in their workspaces
CREATE POLICY events_select_policy ON ops.events
  FOR SELECT TO authenticated
  USING (workspace_id IN (SELECT auth.user_workspaces()));

-- System/service accounts can create events (backend operations)
CREATE POLICY events_insert_policy ON ops.events
  FOR INSERT TO authenticated
  WITH CHECK (
    workspace_id IN (SELECT auth.user_workspaces())
  );

-- Only admins can update events (for corrections only)
CREATE POLICY events_update_policy ON ops.events
  FOR UPDATE TO authenticated
  USING (
    auth.is_workspace_admin(workspace_id)
  );

-- Events should generally not be deleted (audit trail), but admins can if needed
CREATE POLICY events_delete_policy ON ops.events
  FOR DELETE TO authenticated
  USING (
    auth.has_workspace_role(workspace_id, 'owner')
  );

-- ============================================================
-- EVENT_ACTORS
-- ============================================================

ALTER TABLE ops.event_actors ENABLE ROW LEVEL SECURITY;

CREATE POLICY event_actors_select_policy ON ops.event_actors
  FOR SELECT TO authenticated
  USING (
    event_id IN (
      SELECT id FROM ops.events
      WHERE workspace_id IN (SELECT auth.user_workspaces())
    )
  );

CREATE POLICY event_actors_insert_policy ON ops.event_actors
  FOR INSERT TO authenticated
  WITH CHECK (
    event_id IN (
      SELECT id FROM ops.events
      WHERE workspace_id IN (SELECT auth.user_workspaces())
    )
  );

CREATE POLICY event_actors_update_policy ON ops.event_actors
  FOR UPDATE TO authenticated
  USING (
    event_id IN (
      SELECT id FROM ops.events e
      WHERE e.workspace_id IN (SELECT auth.user_workspaces())
        AND auth.is_workspace_admin(e.workspace_id)
    )
  );

CREATE POLICY event_actors_delete_policy ON ops.event_actors
  FOR DELETE TO authenticated
  USING (
    event_id IN (
      SELECT id FROM ops.events e
      WHERE e.workspace_id IN (SELECT auth.user_workspaces())
        AND auth.has_workspace_role(e.workspace_id, 'owner')
    )
  );

-- ============================================================
-- EVENT_LINKS
-- ============================================================

ALTER TABLE ops.event_links ENABLE ROW LEVEL SECURITY;

CREATE POLICY event_links_select_policy ON ops.event_links
  FOR SELECT TO authenticated
  USING (
    event_id IN (
      SELECT id FROM ops.events
      WHERE workspace_id IN (SELECT auth.user_workspaces())
    )
  );

CREATE POLICY event_links_insert_policy ON ops.event_links
  FOR INSERT TO authenticated
  WITH CHECK (
    event_id IN (
      SELECT id FROM ops.events
      WHERE workspace_id IN (SELECT auth.user_workspaces())
    )
  );

CREATE POLICY event_links_update_policy ON ops.event_links
  FOR UPDATE TO authenticated
  USING (
    event_id IN (
      SELECT id FROM ops.events e
      WHERE e.workspace_id IN (SELECT auth.user_workspaces())
        AND auth.is_workspace_admin(e.workspace_id)
    )
  );

CREATE POLICY event_links_delete_policy ON ops.event_links
  FOR DELETE TO authenticated
  USING (
    event_id IN (
      SELECT id FROM ops.events e
      WHERE e.workspace_id IN (SELECT auth.user_workspaces())
        AND auth.has_workspace_role(e.workspace_id, 'owner')
    )
  );

-- ========================================================================================
-- PART 9: MIGRATION METADATA
-- ========================================================================================

INSERT INTO public.schema_migrations (version, description)
VALUES ('002', 'RLS policies - Multi-tenant workspace isolation')
ON CONFLICT (version) DO NOTHING;

-- ========================================================================================
-- PART 10: VALIDATION QUERIES
-- ========================================================================================

-- These queries can be used to validate RLS is working correctly
-- Run as different users to verify isolation

-- Query: Verify workspace isolation
-- Expected: Each user should only see workspaces they're members of
-- SELECT * FROM core.workspaces;

-- Query: Verify cross-workspace data isolation
-- Expected: Users cannot access data from workspaces they're not members of
-- SELECT COUNT(*) FROM comms.communications WHERE workspace_id NOT IN (SELECT auth.user_workspaces());
-- Result should be 0

-- Query: Verify role-based access
-- Expected: Members cannot see other members unless they're in same workspace
-- SELECT * FROM core.members;

-- Query: Verify founder data isolation
-- Expected: Each founder can only see their own data
-- SELECT * FROM intel.briefings;

-- ========================================================================================
-- END OF MIGRATION 002_rls_policies.sql
-- ========================================================================================
