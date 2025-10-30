# Database Migrations

**AI Chief of Staff - Sprint 1: Core Infrastructure & Data Foundation**

---

## Overview

This directory contains versioned SQL migrations for the AI Chief of Staff platform. All migrations are designed to be:

- **Idempotent:** Safe to run multiple times
- **Versioned:** Sequential execution order
- **Documented:** Comprehensive inline comments
- **Reversible:** Rollback procedures documented

---

## Migration Files

| File | Version | Description | Status |
|------|---------|-------------|--------|
| `001_initial_schema.sql` | 1.0 | Complete database schema with 7 domains | Ready |
| `002_rls_policies.sql` | 1.0 | Row-level security policies | Ready |

---

## Prerequisites

### Required PostgreSQL Extensions

```sql
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";    -- UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";     -- Encryption functions
CREATE EXTENSION IF NOT EXISTS "vector";       -- pgvector for embeddings
```

### System Requirements

- PostgreSQL 14+ (recommended: 15+)
- pgvector extension installed
- Supabase project (or self-hosted PostgreSQL with auth schema)
- Minimum 4GB RAM for vector indexes
- 20GB+ storage for production use

---

## Quick Start

### Option 1: Supabase Dashboard

1. Open your Supabase project
2. Navigate to **SQL Editor**
3. Create a new query
4. Copy contents of `001_initial_schema.sql`
5. Execute the query
6. Repeat for `002_rls_policies.sql`

### Option 2: Supabase CLI

```bash
# Install Supabase CLI
npm install -g supabase

# Login to Supabase
supabase login

# Link to your project
supabase link --project-ref your-project-ref

# Run migrations
supabase db push

# Or apply migrations manually
psql $DATABASE_URL -f migrations/001_initial_schema.sql
psql $DATABASE_URL -f migrations/002_rls_policies.sql
```

### Option 3: Direct PostgreSQL

```bash
# Using psql
psql -h your-host -U your-user -d your-database -f migrations/001_initial_schema.sql
psql -h your-host -U your-user -d your-database -f migrations/002_rls_policies.sql

# Using environment variable
export DATABASE_URL="postgresql://user:password@host:5432/dbname"
psql $DATABASE_URL -f migrations/001_initial_schema.sql
psql $DATABASE_URL -f migrations/002_rls_policies.sql
```

---

## Migration Details

### 001_initial_schema.sql

**Purpose:** Establish complete database schema for AI Chief of Staff

**Creates:**
- 7 domain schemas: `core`, `ops`, `comms`, `meetings`, `media`, `work`, `intel`
- 30 tables across all domains
- 12 custom enum types
- 80+ indexes (B-tree, IVFFlat, GIN)
- 3 utility views
- 5 helper functions
- Automatic triggers for `updated_at` columns

**Key Features:**
- Multi-tenant workspace isolation
- Vector embeddings (1536-dim) for semantic search
- Event sourcing infrastructure
- JSONB for flexible metadata
- Comprehensive constraints and checks

**Estimated Runtime:** 5-10 seconds

**Storage Impact:** ~100MB initial (grows with data)

### 002_rls_policies.sql

**Purpose:** Implement row-level security for multi-tenant isolation

**Creates:**
- 5 auth helper functions
- 120+ RLS policies across all tables
- Complete workspace isolation
- Role-based access control

**Security Model:**
- Users can only access workspaces they're members of
- Owners have full control
- Admins can manage workspace data
- Members have restricted access
- Service accounts for backend operations

**Estimated Runtime:** 10-15 seconds

**Performance Impact:** < 10ms query overhead

---

## Verification

### Post-Migration Checks

Run these queries to verify successful migration:

```sql
-- 1. Verify all schemas exist
SELECT schema_name
FROM information_schema.schemata
WHERE schema_name IN ('core', 'ops', 'comms', 'meetings', 'media', 'work', 'intel')
ORDER BY schema_name;
-- Expected: 7 rows

-- 2. Verify all tables created
SELECT schemaname, tablename
FROM pg_tables
WHERE schemaname IN ('core', 'ops', 'comms', 'meetings', 'media', 'work', 'intel')
ORDER BY schemaname, tablename;
-- Expected: 30 rows

-- 3. Verify pgvector extension
SELECT * FROM pg_extension WHERE extname = 'vector';
-- Expected: 1 row

-- 4. Verify vector columns exist
SELECT
  table_schema,
  table_name,
  column_name,
  udt_name
FROM information_schema.columns
WHERE udt_name = 'vector'
ORDER BY table_schema, table_name;
-- Expected: 5 rows (contacts, communications, transcript_chunks, media_chunks, insights)

-- 5. Verify RLS enabled
SELECT
  schemaname,
  tablename,
  rowsecurity
FROM pg_tables
WHERE schemaname IN ('core', 'ops', 'comms', 'meetings', 'media', 'work', 'intel')
  AND rowsecurity = true
ORDER BY schemaname, tablename;
-- Expected: 30 rows (all tables)

-- 6. Verify indexes created
SELECT
  schemaname,
  tablename,
  indexname,
  indexdef
FROM pg_indexes
WHERE schemaname IN ('core', 'ops', 'comms', 'meetings', 'media', 'work', 'intel')
ORDER BY schemaname, tablename;
-- Expected: 80+ rows

-- 7. Verify migration tracking
SELECT * FROM public.schema_migrations ORDER BY version;
-- Expected: 2 rows (versions '001' and '002')

-- 8. Test basic operations (as authenticated user)
-- Create workspace
INSERT INTO core.workspaces (name) VALUES ('Test Workspace') RETURNING id;

-- Create member
INSERT INTO core.members (workspace_id, user_id, role)
VALUES ('<workspace_id>', auth.uid(), 'owner');

-- Verify isolation works
SELECT * FROM core.workspaces;  -- Should only see your workspaces
```

---

## Rollback Procedures

### Rollback 002_rls_policies.sql

```sql
-- Disable RLS on all tables
DO $$
DECLARE
  r RECORD;
BEGIN
  FOR r IN
    SELECT schemaname, tablename
    FROM pg_tables
    WHERE schemaname IN ('core', 'ops', 'comms', 'meetings', 'media', 'work', 'intel')
  LOOP
    EXECUTE format('ALTER TABLE %I.%I DISABLE ROW LEVEL SECURITY', r.schemaname, r.tablename);
  END LOOP;
END $$;

-- Drop helper functions
DROP FUNCTION IF EXISTS auth.user_workspaces();
DROP FUNCTION IF EXISTS auth.has_workspace_role(uuid, core.role_type);
DROP FUNCTION IF EXISTS auth.is_workspace_admin(uuid);
DROP FUNCTION IF EXISTS auth.is_founder(uuid);
DROP FUNCTION IF EXISTS auth.get_founder_id(uuid);

-- Remove migration record
DELETE FROM public.schema_migrations WHERE version = '002';
```

### Rollback 001_initial_schema.sql

**WARNING:** This will delete all data. Only use in development.

```sql
-- Drop schemas (CASCADE removes all objects)
DROP SCHEMA IF EXISTS intel CASCADE;
DROP SCHEMA IF EXISTS work CASCADE;
DROP SCHEMA IF EXISTS media CASCADE;
DROP SCHEMA IF EXISTS meetings CASCADE;
DROP SCHEMA IF EXISTS comms CASCADE;
DROP SCHEMA IF EXISTS ops CASCADE;
DROP SCHEMA IF EXISTS core CASCADE;

-- Drop extensions (only if not used elsewhere)
-- DROP EXTENSION IF EXISTS vector;
-- DROP EXTENSION IF EXISTS pgcrypto;
-- DROP EXTENSION IF EXISTS "uuid-ossp";

-- Remove migration record
DELETE FROM public.schema_migrations WHERE version = '001';
```

---

## Troubleshooting

### Issue: "extension vector does not exist"

**Solution:**
```sql
-- Install pgvector extension first
CREATE EXTENSION vector;
```

If using Supabase, enable in **Database > Extensions** dashboard.

### Issue: "permission denied for schema auth"

**Solution:** Ensure you're running as a superuser or database owner. For Supabase, use the SQL Editor as the `postgres` role.

### Issue: RLS policies prevent data access

**Solution:**
```sql
-- Temporarily disable RLS for debugging
ALTER TABLE core.workspaces DISABLE ROW LEVEL SECURITY;

-- Check your user has proper workspace membership
SELECT * FROM core.members WHERE user_id = auth.uid();
```

### Issue: Slow vector queries

**Solution:**
```sql
-- Rebuild vector indexes
REINDEX INDEX idx_contacts_embedding;
REINDEX INDEX idx_comms_embedding;

-- Adjust IVFFlat probes
SET ivfflat.probes = 10;

-- Analyze tables
ANALYZE core.contacts;
ANALYZE comms.communications;
```

### Issue: Migration already applied

**Solution:** All migrations are idempotent and safe to re-run. They use:
- `CREATE ... IF NOT EXISTS`
- `DO $$ BEGIN ... EXCEPTION WHEN duplicate_object ...`
- `INSERT ... ON CONFLICT DO NOTHING`

---

## Performance Tuning

### Recommended PostgreSQL Settings

```sql
-- For vector operations
SET maintenance_work_mem = '2GB';        -- For index builds
SET work_mem = '256MB';                  -- For sorts and joins
SET shared_buffers = '4GB';              -- For caching
SET effective_cache_size = '12GB';       -- Total available RAM

-- For vector search
SET ivfflat.probes = 10;                 -- Balance speed/accuracy
```

### Index Maintenance

```sql
-- Rebuild vector indexes monthly
REINDEX INDEX CONCURRENTLY idx_contacts_embedding;
REINDEX INDEX CONCURRENTLY idx_comms_embedding;
REINDEX INDEX CONCURRENTLY idx_chunks_embedding;
REINDEX INDEX CONCURRENTLY idx_media_chunks_embedding;
REINDEX INDEX CONCURRENTLY idx_insights_embedding;

-- Update statistics
ANALYZE core.contacts;
ANALYZE comms.communications;
ANALYZE meetings.transcript_chunks;
ANALYZE media.media_chunks;
ANALYZE intel.insights;
```

---

## Testing

### Unit Tests

Create test fixtures:

```sql
-- Create test workspace
INSERT INTO core.workspaces (id, name)
VALUES ('00000000-0000-0000-0000-000000000001', 'Test Workspace');

-- Create test user membership
INSERT INTO core.members (workspace_id, user_id, role)
VALUES ('00000000-0000-0000-0000-000000000001', auth.uid(), 'owner');

-- Create test founder
INSERT INTO core.founders (workspace_id, user_id, display_name, email)
VALUES (
  '00000000-0000-0000-0000-000000000001',
  auth.uid(),
  'Test Founder',
  'test@example.com'
) RETURNING id;
```

### Integration Tests

```sql
-- Test workspace isolation
-- User A should not see User B's data
SELECT COUNT(*) FROM core.workspaces;  -- Should only see own workspace

-- Test RLS policies
-- Non-admin should not be able to delete workspace
DELETE FROM core.workspaces WHERE id = '...';  -- Should fail

-- Test vector search
-- Generate test embedding and search
SELECT * FROM core.contacts
WHERE embedding IS NOT NULL
ORDER BY embedding <=> '[0.1, 0.2, ...]'::vector
LIMIT 5;
```

---

## Monitoring

### Key Metrics to Track

```sql
-- Table sizes
SELECT
  schemaname,
  tablename,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS total_size
FROM pg_tables
WHERE schemaname IN ('core', 'ops', 'comms', 'meetings', 'media', 'work', 'intel')
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Index usage
SELECT
  schemaname,
  tablename,
  indexname,
  idx_scan,
  idx_tup_read,
  idx_tup_fetch
FROM pg_stat_user_indexes
WHERE schemaname IN ('core', 'ops', 'comms', 'meetings', 'media', 'work', 'intel')
ORDER BY idx_scan DESC;

-- Slow queries
SELECT
  query,
  calls,
  mean_exec_time,
  total_exec_time
FROM pg_stat_statements
WHERE query LIKE '%embedding%'
ORDER BY mean_exec_time DESC
LIMIT 20;
```

---

## Next Steps

After successful migration:

1. **Set up authentication:**
   - Configure Supabase Auth providers
   - Create initial workspace and user
   - Test RLS policies with real users

2. **Populate initial data:**
   - Create test contacts
   - Generate sample embeddings
   - Test vector search queries

3. **Backend integration:**
   - Implement FastAPI application
   - Set up MCP connectors
   - Create embedding generation pipeline

4. **Monitoring setup:**
   - Enable query logging
   - Set up performance dashboards
   - Configure alerts for slow queries

5. **Documentation:**
   - API documentation (OpenAPI)
   - Frontend integration guide
   - Admin runbooks

---

## Support

For issues or questions:

- Review `/docs/architecture.md` for system design
- Check `/docs/vector_search_guide.md` for query examples
- Open GitHub issue for bugs
- Contact system architect for schema questions

---

**Version:** 1.0
**Last Updated:** 2025-10-30
**Maintained By:** System Architect
