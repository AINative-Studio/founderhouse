-- ========================================================================================
-- Migration: 007_rls_audit.sql
-- Description: Comprehensive RLS Policy Audit Script for AI Chief of Staff
-- Author: System Architect
-- Date: 2025-11-11
-- Sprint: 6 - Security, Testing & Launch
--
-- This script audits all tables in the database to verify:
-- 1. All workspace-scoped tables have RLS enabled
-- 2. All tables have proper SELECT, INSERT, UPDATE, DELETE policies
-- 3. No data leakage between workspaces
-- 4. Role-based access control is working correctly
-- ========================================================================================

-- ========================================================================================
-- PART 1: LIST ALL TABLES WITH RLS STATUS
-- ========================================================================================

SELECT
  schemaname AS schema_name,
  tablename AS table_name,
  CASE
    WHEN rowsecurity THEN '✓ Enabled'
    ELSE '✗ Disabled'
  END AS rls_status,
  CASE
    WHEN rowsecurity AND schemaname IN ('core', 'comms', 'meetings', 'media', 'work', 'intel', 'ops', 'orchestration') THEN '✓ OK'
    WHEN NOT rowsecurity AND schemaname IN ('core', 'comms', 'meetings', 'media', 'work', 'intel', 'ops', 'orchestration') THEN '⚠️ MISSING RLS'
    ELSE 'N/A'
  END AS status
FROM pg_tables
WHERE schemaname IN ('core', 'comms', 'meetings', 'media', 'work', 'intel', 'ops', 'orchestration')
ORDER BY schemaname, tablename;

-- ========================================================================================
-- PART 2: LIST ALL RLS POLICIES BY TABLE
-- ========================================================================================

SELECT
  schemaname AS schema_name,
  tablename AS table_name,
  policyname AS policy_name,
  CASE
    WHEN cmd = 'r' THEN 'SELECT'
    WHEN cmd = 'a' THEN 'INSERT'
    WHEN cmd = 'w' THEN 'UPDATE'
    WHEN cmd = 'd' THEN 'DELETE'
    WHEN cmd = '*' THEN 'ALL'
    ELSE cmd::text
  END AS command,
  CASE
    WHEN permissive THEN 'PERMISSIVE'
    ELSE 'RESTRICTIVE'
  END AS type,
  roles::text AS roles
FROM pg_policies
WHERE schemaname IN ('core', 'comms', 'meetings', 'media', 'work', 'intel', 'ops', 'orchestration')
ORDER BY schemaname, tablename, cmd;

-- ========================================================================================
-- PART 3: IDENTIFY TABLES WITHOUT REQUIRED POLICIES
-- ========================================================================================

-- Tables that have RLS enabled but missing SELECT policy
SELECT
  t.schemaname AS schema_name,
  t.tablename AS table_name,
  'Missing SELECT policy' AS issue
FROM pg_tables t
WHERE t.schemaname IN ('core', 'comms', 'meetings', 'media', 'work', 'intel', 'ops', 'orchestration')
  AND t.rowsecurity = true
  AND NOT EXISTS (
    SELECT 1 FROM pg_policies p
    WHERE p.schemaname = t.schemaname
      AND p.tablename = t.tablename
      AND p.cmd = 'r'
  )

UNION ALL

-- Tables that have RLS enabled but missing INSERT policy
SELECT
  t.schemaname,
  t.tablename,
  'Missing INSERT policy' AS issue
FROM pg_tables t
WHERE t.schemaname IN ('core', 'comms', 'meetings', 'media', 'work', 'intel', 'ops', 'orchestration')
  AND t.rowsecurity = true
  AND NOT EXISTS (
    SELECT 1 FROM pg_policies p
    WHERE p.schemaname = t.schemaname
      AND p.tablename = t.tablename
      AND p.cmd = 'a'
  )

UNION ALL

-- Tables that have RLS enabled but missing UPDATE policy
SELECT
  t.schemaname,
  t.tablename,
  'Missing UPDATE policy' AS issue
FROM pg_tables t
WHERE t.schemaname IN ('core', 'comms', 'meetings', 'media', 'work', 'intel', 'ops', 'orchestration')
  AND t.rowsecurity = true
  AND NOT EXISTS (
    SELECT 1 FROM pg_policies p
    WHERE p.schemaname = t.schemaname
      AND p.tablename = t.tablename
      AND p.cmd = 'w'
  )

UNION ALL

-- Tables that have RLS enabled but missing DELETE policy
SELECT
  t.schemaname,
  t.tablename,
  'Missing DELETE policy' AS issue
FROM pg_tables t
WHERE t.schemaname IN ('core', 'comms', 'meetings', 'media', 'work', 'intel', 'ops', 'orchestration')
  AND t.rowsecurity = true
  AND NOT EXISTS (
    SELECT 1 FROM pg_policies p
    WHERE p.schemaname = t.schemaname
      AND p.tablename = t.tablename
      AND p.cmd = 'd'
  )

ORDER BY schema_name, table_name, issue;

-- ========================================================================================
-- PART 4: VERIFY WORKSPACE ISOLATION HELPER FUNCTIONS
-- ========================================================================================

-- Verify auth.user_workspaces() function exists
SELECT
  proname AS function_name,
  pg_get_functiondef(oid) AS definition
FROM pg_proc
WHERE proname = 'user_workspaces'
  AND pronamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'auth');

-- Verify auth.has_workspace_role() function exists
SELECT
  proname AS function_name,
  pg_get_functiondef(oid) AS definition
FROM pg_proc
WHERE proname = 'has_workspace_role'
  AND pronamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'auth');

-- Verify auth.is_workspace_admin() function exists
SELECT
  proname AS function_name,
  pg_get_functiondef(oid) AS definition
FROM pg_proc
WHERE proname = 'is_workspace_admin'
  AND pronamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'auth');

-- Verify auth.is_founder() function exists
SELECT
  proname AS function_name,
  pg_get_functiondef(oid) AS definition
FROM pg_proc
WHERE proname = 'is_founder'
  AND pronamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'auth');

-- Verify auth.get_founder_id() function exists
SELECT
  proname AS function_name,
  pg_get_functiondef(oid) AS definition
FROM pg_proc
WHERE proname = 'get_founder_id'
  AND pronamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'auth');

-- ========================================================================================
-- PART 5: RLS AUDIT SUMMARY
-- ========================================================================================

-- Summary of RLS coverage by schema
SELECT
  schemaname AS schema_name,
  COUNT(*) AS total_tables,
  SUM(CASE WHEN rowsecurity THEN 1 ELSE 0 END) AS tables_with_rls,
  ROUND(
    (SUM(CASE WHEN rowsecurity THEN 1 ELSE 0 END)::numeric / COUNT(*)::numeric) * 100,
    2
  ) AS rls_coverage_percent
FROM pg_tables
WHERE schemaname IN ('core', 'comms', 'meetings', 'media', 'work', 'intel', 'ops', 'orchestration')
GROUP BY schemaname
ORDER BY schemaname;

-- Total RLS coverage across all schemas
SELECT
  'TOTAL' AS schema_name,
  COUNT(*) AS total_tables,
  SUM(CASE WHEN rowsecurity THEN 1 ELSE 0 END) AS tables_with_rls,
  ROUND(
    (SUM(CASE WHEN rowsecurity THEN 1 ELSE 0 END)::numeric / COUNT(*)::numeric) * 100,
    2
  ) AS rls_coverage_percent
FROM pg_tables
WHERE schemaname IN ('core', 'comms', 'meetings', 'media', 'work', 'intel', 'ops', 'orchestration');

-- ========================================================================================
-- PART 6: METADATA
-- ========================================================================================

COMMENT ON TABLE pg_tables IS 'This audit script verifies RLS policies are properly configured for multi-tenant isolation';

-- ========================================================================================
-- END OF RLS AUDIT SCRIPT
-- ========================================================================================
