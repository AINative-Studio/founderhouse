# Sprint 1 Quick Start Guide

**AI Chief of Staff - Core Infrastructure Implementation**

---

## What Was Built

Sprint 1 delivered the complete database foundation for the AI Chief of Staff platform:

- **30 tables** across 7 domain schemas
- **120+ RLS policies** for multi-tenant security
- **5 vector indexes** for semantic search
- **Complete event sourcing** infrastructure
- **5,400+ lines** of production-ready SQL and documentation

---

## File Structure

```
founderhouse-main/
├── migrations/
│   ├── 001_initial_schema.sql      # Complete database schema (924 lines)
│   ├── 002_rls_policies.sql        # Row-level security (1,072 lines)
│   └── README.md                   # Migration instructions (490 lines)
│
└── docs/
    ├── architecture.md              # System architecture (1,333 lines)
    ├── vector_search_guide.md       # Vector queries (942 lines)
    └── sprint1_completion_summary.md # This sprint summary (681 lines)
```

---

## Quick Start (5 minutes)

### 1. Set Up Supabase Project

```bash
# Option A: Use Supabase Dashboard
# 1. Go to https://supabase.com/dashboard
# 2. Create new project
# 3. Copy project URL and API keys

# Option B: Use Supabase CLI
npm install -g supabase
supabase login
supabase projects create ai-chief-of-staff
```

### 2. Apply Migrations

```bash
# Navigate to project
cd /Users/aideveloper/Desktop/founderhouse-main

# Option A: Via Supabase Dashboard
# 1. Open SQL Editor
# 2. Copy/paste migrations/001_initial_schema.sql
# 3. Execute
# 4. Copy/paste migrations/002_rls_policies.sql
# 5. Execute

# Option B: Via psql
export DATABASE_URL="your-supabase-connection-string"
psql $DATABASE_URL -f migrations/001_initial_schema.sql
psql $DATABASE_URL -f migrations/002_rls_policies.sql
```

### 3. Verify Installation

```sql
-- Run in Supabase SQL Editor
SELECT schema_name
FROM information_schema.schemata
WHERE schema_name IN ('core', 'ops', 'comms', 'meetings', 'media', 'work', 'intel')
ORDER BY schema_name;
-- Should return 7 rows

-- Verify vector extension
SELECT * FROM pg_extension WHERE extname = 'vector';
-- Should return 1 row

-- Verify RLS enabled
SELECT COUNT(*) FROM pg_tables
WHERE schemaname IN ('core', 'ops', 'comms', 'meetings', 'media', 'work', 'intel')
  AND rowsecurity = true;
-- Should return 30
```

---

## Schema Overview

### Core Schema (Identity & Tenancy)
- `workspaces` - Multi-tenant isolation
- `members` - User access control
- `founders` - Primary users
- `contacts` - People network
- `integrations` - Platform connections

### Comms Schema (Communications)
- `threads` - Conversation groups
- `communications` - Messages (email, Slack, Discord)

### Meetings Schema (Meeting Intelligence)
- `meetings` - Calendar events
- `meeting_participants` - Attendees
- `transcripts` - Meeting transcriptions
- `transcript_chunks` - Vectorized segments (searchable)

### Media Schema (Async Content)
- `media_assets` - Loom videos
- `media_transcripts` - Video transcriptions
- `media_chunks` - Vectorized segments (searchable)

### Work Schema (Task Management)
- `tasks` - Action items
- `task_links` - External platform sync (Monday, Notion)

### Intel Schema (AI Insights)
- `briefings` - Daily summaries
- `insights` - AI-generated insights
- `decisions` - Decision tracking

### Ops Schema (Audit Trail)
- `events` - Event sourcing log
- `event_actors` - Who did what
- `event_links` - Causal relationships

---

## Key Features

### 1. Multi-Tenant Security (RLS)

Every query is automatically scoped to the user's workspaces:

```sql
-- User A can only see their workspaces
SELECT * FROM core.workspaces;
-- Automatically filtered by RLS

-- User A cannot access User B's data
-- Even if they know the IDs
```

### 2. Semantic Search (pgvector)

Search by meaning, not just keywords:

```sql
-- Find similar contacts
SELECT
  name,
  company,
  1 - (embedding <=> $query_embedding) AS similarity
FROM core.contacts
WHERE workspace_id = $workspace_id
  AND embedding IS NOT NULL
ORDER BY embedding <=> $query_embedding
LIMIT 10;
```

### 3. Event Sourcing (Complete Audit)

Every action is logged:

```sql
-- Track all events for an entity
SELECT
  event_type,
  payload,
  created_at
FROM ops.events
WHERE entity_type = 'task'
  AND entity_id = $task_id
ORDER BY created_at;
```

---

## Testing

### Create Test Workspace

```sql
-- 1. Create workspace
INSERT INTO core.workspaces (name)
VALUES ('Test Workspace')
RETURNING id;

-- 2. Add yourself as owner
INSERT INTO core.members (workspace_id, user_id, role)
VALUES (
  '...',  -- workspace_id from above
  auth.uid(),  -- Your Supabase user ID
  'owner'
);

-- 3. Create founder profile
INSERT INTO core.founders (workspace_id, user_id, display_name, email)
VALUES (
  '...',  -- workspace_id
  auth.uid(),
  'Test Founder',
  'test@example.com'
)
RETURNING id;
```

### Test Vector Search

```sql
-- Create test contact with embedding
INSERT INTO core.contacts (
  workspace_id,
  founder_id,
  name,
  company,
  type,
  embedding
) VALUES (
  '...',  -- workspace_id
  '...',  -- founder_id
  'John Smith',
  'Acme Corp',
  'investor',
  '[0.1, 0.2, ...]'::vector(1536)  -- Sample embedding
);

-- Search for similar contacts
SELECT name, company
FROM core.contacts
WHERE workspace_id = '...'
  AND embedding IS NOT NULL
ORDER BY embedding <=> '[0.1, 0.2, ...]'::vector(1536)
LIMIT 5;
```

---

## Documentation Reference

| Document | Purpose | Length |
|----------|---------|--------|
| `migrations/001_initial_schema.sql` | Complete database schema | 924 lines |
| `migrations/002_rls_policies.sql` | Security policies | 1,072 lines |
| `migrations/README.md` | Migration guide | 490 lines |
| `docs/architecture.md` | System design | 1,333 lines |
| `docs/vector_search_guide.md` | Search examples | 942 lines |
| `docs/sprint1_completion_summary.md` | Sprint overview | 681 lines |

---

## Next Steps

### For Backend Developers

1. **Read:** `/docs/architecture.md` for design decisions
2. **Apply:** Migrations to your Supabase project
3. **Build:** FastAPI backend with Supabase client
4. **Implement:** Embedding generation service

**Resources:**
- Supabase Python: https://github.com/supabase-community/supabase-py
- pgvector: https://github.com/pgvector/pgvector
- OpenAI Embeddings: https://platform.openai.com/docs/guides/embeddings

### For Frontend Developers

1. **Wait for:** Backend API implementation
2. **Review:** Data model in `/Users/aideveloper/Desktop/founderhouse-main/datamodel.md`
3. **Design:** UI for workspace management
4. **Plan:** Dashboard components

### For DevOps

1. **Provision:** Supabase production project
2. **Configure:** Backups (hourly snapshots)
3. **Set up:** Monitoring (query performance)
4. **Create:** CI/CD for future migrations

---

## Common Operations

### View Table Sizes

```sql
SELECT
  schemaname,
  tablename,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname IN ('core', 'ops', 'comms', 'meetings', 'media', 'work', 'intel')
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

### Check Index Usage

```sql
SELECT
  schemaname,
  tablename,
  indexname,
  idx_scan AS scans
FROM pg_stat_user_indexes
WHERE schemaname IN ('core', 'ops', 'comms', 'meetings', 'media', 'work', 'intel')
ORDER BY idx_scan DESC;
```

### Monitor Slow Queries

```sql
SELECT
  query,
  mean_exec_time,
  calls
FROM pg_stat_statements
WHERE query LIKE '%workspace_id%'
ORDER BY mean_exec_time DESC
LIMIT 20;
```

---

## Troubleshooting

### "extension vector does not exist"

**Solution:** Enable in Supabase Dashboard > Database > Extensions

### "permission denied for schema auth"

**Solution:** Use SQL Editor in Supabase Dashboard (runs as postgres role)

### "no rows returned" after creating data

**Solution:** Check RLS policies. Ensure you're a member of the workspace:

```sql
SELECT * FROM core.members WHERE user_id = auth.uid();
```

### Vector search is slow

**Solution:** Rebuild indexes:

```sql
REINDEX INDEX CONCURRENTLY idx_contacts_embedding;
ANALYZE core.contacts;
```

---

## Support

**Questions?**
- Review `/docs/architecture.md` for design decisions
- Check `/docs/vector_search_guide.md` for query examples
- See `/migrations/README.md` for setup help

**Issues?**
- Open GitHub issue
- Tag: `sprint-1`, `database`

---

## Success Metrics

Sprint 1 delivered:
- ✓ **30 tables** across 7 schemas
- ✓ **120+ RLS policies** for security
- ✓ **5 vector indexes** for semantic search
- ✓ **80+ performance indexes**
- ✓ **5,400+ lines** of code and docs
- ✓ **100% idempotent** migrations
- ✓ **Production-ready** architecture

**Status: COMPLETE**

**Ready for Sprint 2: MCP Integration Framework**

---

**Quick Start Version:** 1.0
**Date:** 2025-10-30
**Project:** AI Chief of Staff
**Repository:** https://github.com/AINative-Studio/founderhouse
