# Vector Search Implementation Guide

**Version:** 1.0
**Date:** 2025-10-30
**Sprint:** 1 - Core Infrastructure & Data Foundation

---

## Table of Contents

1. [Overview](#overview)
2. [Vector-Enabled Tables](#vector-enabled-tables)
3. [Basic Search Queries](#basic-search-queries)
4. [Advanced Search Patterns](#advanced-search-patterns)
5. [Hybrid Search Queries](#hybrid-search-queries)
6. [Multi-Source Semantic Search](#multi-source-semantic-search)
7. [Performance Optimization](#performance-optimization)
8. [Python Examples](#python-examples)
9. [Common Use Cases](#common-use-cases)

---

## Overview

The AI Chief of Staff platform uses **pgvector** for semantic search across multiple data types. All vector embeddings are 1536-dimensional (compatible with OpenAI's text-embedding-ada-002 model).

### Vector Search Benefits

- **Semantic Understanding:** Find conceptually similar content, not just keyword matches
- **Context Retrieval:** Surface relevant information across all data sources
- **Question Answering:** Enable natural language queries
- **Recommendation:** Suggest related content based on similarity

### Distance Metrics

The system uses **cosine distance** for all vector comparisons:

```sql
-- Cosine distance operator: <=>
-- Range: 0 (identical) to 2 (opposite direction)
embedding <=> query_vector

-- Convert to similarity score (0 to 1):
1 - (embedding <=> query_vector)
```

---

## Vector-Enabled Tables

### 1. Contacts (core.contacts)

**Purpose:** Semantic search over contact context and relationship history

```sql
-- Table structure
CREATE TABLE core.contacts (
  id            uuid PRIMARY KEY,
  workspace_id  uuid NOT NULL,
  founder_id    uuid NOT NULL,
  name          text NOT NULL,
  type          text,
  company       text,
  context       jsonb,  -- Relationship notes, history
  embedding     vector(1536),  -- Semantic representation
  ...
);

-- Index
CREATE INDEX idx_contacts_embedding ON core.contacts
  USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);
```

**Use Cases:**
- "Find all contacts related to fundraising"
- "Who have I talked to about product-market fit?"
- "Show me investors interested in AI"

### 2. Communications (comms.communications)

**Purpose:** Semantic search over emails, Slack, Discord messages

```sql
CREATE TABLE comms.communications (
  id              uuid PRIMARY KEY,
  workspace_id    uuid NOT NULL,
  founder_id      uuid NOT NULL,
  platform        core.platform_enum NOT NULL,
  content         text,
  embedding       vector(1536),
  ...
);

CREATE INDEX idx_comms_embedding ON comms.communications
  USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);
```

**Use Cases:**
- "Find all messages about the Q4 roadmap"
- "What did investors say about our metrics?"
- "Show me discussions about hiring"

### 3. Transcript Chunks (meetings.transcript_chunks)

**Purpose:** Semantic search within meeting transcripts

```sql
CREATE TABLE meetings.transcript_chunks (
  id            uuid PRIMARY KEY,
  transcript_id uuid NOT NULL,
  speaker       text,
  text          text NOT NULL,
  embedding     vector(1536),
  ...
);

CREATE INDEX idx_chunks_embedding ON meetings.transcript_chunks
  USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 200);
```

**Use Cases:**
- "What was discussed about pricing in board meetings?"
- "Find mentions of competitor XYZ across all meetings"
- "Show me action items assigned to Sarah"

### 4. Media Chunks (media.media_chunks)

**Purpose:** Semantic search within Loom videos and recordings

```sql
CREATE TABLE media.media_chunks (
  id                  uuid PRIMARY KEY,
  media_transcript_id uuid NOT NULL,
  text                text NOT NULL,
  embedding           vector(1536),
  ...
);

CREATE INDEX idx_media_chunks_embedding ON media.media_chunks
  USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 200);
```

**Use Cases:**
- "Find all Loom videos where I demoed the product"
- "What did I say about customer feedback in async updates?"

### 5. Insights (intel.insights)

**Purpose:** Semantic search over AI-generated insights

```sql
CREATE TABLE intel.insights (
  id            uuid PRIMARY KEY,
  workspace_id  uuid NOT NULL,
  founder_id    uuid NOT NULL,
  insight_type  intel.insight_type_enum NOT NULL,
  content       jsonb NOT NULL,
  embedding     vector(1536),
  ...
);

CREATE INDEX idx_insights_embedding ON intel.insights
  USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);
```

**Use Cases:**
- "Show me insights about revenue trends"
- "What risks have been identified recently?"
- "Find recommendations related to growth strategy"

---

## Basic Search Queries

### Query 1: Simple Similarity Search

Find the top 10 most similar contacts to a query:

```sql
-- Input: $1 = query_embedding (vector(1536))
--        $2 = workspace_id (uuid)

SELECT
  id,
  name,
  company,
  type,
  1 - (embedding <=> $1::vector) AS similarity_score
FROM core.contacts
WHERE workspace_id = $2
  AND embedding IS NOT NULL
ORDER BY embedding <=> $1::vector
LIMIT 10;
```

**Explanation:**
- `embedding <=> $1::vector`: Computes cosine distance
- `ORDER BY embedding <=> $1::vector`: Orders by distance (ascending = most similar first)
- `1 - (embedding <=> $1)`: Converts distance to similarity score (0-1 range)

### Query 2: Threshold-Based Search

Find all items with similarity above a threshold:

```sql
-- Input: $1 = query_embedding
--        $2 = workspace_id
--        $3 = min_similarity (e.g., 0.7)

SELECT
  id,
  name,
  company,
  1 - (embedding <=> $1::vector) AS similarity
FROM core.contacts
WHERE workspace_id = $2
  AND embedding IS NOT NULL
  AND 1 - (embedding <=> $1::vector) > $3
ORDER BY embedding <=> $1::vector
LIMIT 50;
```

**When to use:**
- Quality over quantity (only high-confidence matches)
- Filtering out noise
- Setting a minimum relevance bar

**Recommended thresholds:**
- `0.85+`: Very high similarity (near duplicates)
- `0.75-0.85`: High similarity (related concepts)
- `0.65-0.75`: Moderate similarity (broader context)
- `<0.65`: Low similarity (may be noise)

### Query 3: Ranked Search with Metadata

Combine similarity with metadata for rich results:

```sql
SELECT
  c.id,
  c.name,
  c.company,
  c.type,
  c.context->>'last_interaction' AS last_interaction,
  c.last_contacted,
  1 - (c.embedding <=> $1::vector) AS similarity
FROM core.contacts c
WHERE c.workspace_id = $2
  AND c.embedding IS NOT NULL
  AND 1 - (c.embedding <=> $1::vector) > 0.7
ORDER BY c.embedding <=> $1::vector
LIMIT 20;
```

---

## Advanced Search Patterns

### Pattern 1: Time-Windowed Semantic Search

Search within a specific time period:

```sql
-- Find similar communications in the last 30 days
SELECT
  id,
  platform,
  subject,
  snippet,
  received_at,
  1 - (embedding <=> $1::vector) AS similarity
FROM comms.communications
WHERE workspace_id = $2
  AND founder_id = $3
  AND received_at >= now() - interval '30 days'
  AND embedding IS NOT NULL
  AND 1 - (embedding <=> $1::vector) > 0.7
ORDER BY embedding <=> $1::vector
LIMIT 25;
```

### Pattern 2: Filtered Semantic Search

Apply business logic filters before semantic ranking:

```sql
-- Find similar high-priority communications
SELECT
  id,
  subject,
  sender,
  urgency,
  1 - (embedding <=> $1::vector) AS similarity
FROM comms.communications
WHERE workspace_id = $2
  AND founder_id = $3
  AND urgency IN ('urgent', 'high')
  AND followup_needed = true
  AND embedding IS NOT NULL
  AND 1 - (embedding <=> $1::vector) > 0.6
ORDER BY
  CASE urgency
    WHEN 'urgent' THEN 1
    WHEN 'high' THEN 2
  END,
  embedding <=> $1::vector
LIMIT 15;
```

**Optimization:** Filters are applied first, then vector search on smaller set.

### Pattern 3: Aggregated Semantic Search

Group similar items by category:

```sql
-- Find similar contacts grouped by type
SELECT
  type,
  COUNT(*) AS count,
  AVG(1 - (embedding <=> $1::vector)) AS avg_similarity,
  ARRAY_AGG(name ORDER BY embedding <=> $1::vector LIMIT 5) AS top_names
FROM core.contacts
WHERE workspace_id = $2
  AND embedding IS NOT NULL
  AND 1 - (embedding <=> $1::vector) > 0.7
GROUP BY type
ORDER BY avg_similarity DESC;
```

### Pattern 4: Speaker-Specific Transcript Search

Find what a specific person said about a topic:

```sql
-- What did the CEO say about pricing in meetings?
SELECT
  tc.id,
  tc.speaker,
  tc.text,
  t.title AS meeting_title,
  m.start_time AS meeting_date,
  1 - (tc.embedding <=> $1::vector) AS similarity
FROM meetings.transcript_chunks tc
JOIN meetings.transcripts t ON tc.transcript_id = t.id
JOIN meetings.meetings m ON t.meeting_id = m.id
WHERE m.workspace_id = $2
  AND tc.speaker ILIKE '%CEO%'  -- Flexible speaker matching
  AND tc.embedding IS NOT NULL
  AND 1 - (tc.embedding <=> $1::vector) > 0.75
ORDER BY tc.embedding <=> $1::vector
LIMIT 20;
```

---

## Hybrid Search Queries

Combine semantic search with traditional full-text search for best results.

### Hybrid Pattern 1: Vector + Keyword

```sql
-- Find communications matching keywords OR semantically similar
WITH keyword_matches AS (
  SELECT id, 0.95 AS score  -- High score for exact matches
  FROM comms.communications
  WHERE workspace_id = $2
    AND founder_id = $3
    AND (
      content ILIKE '%fundraising%'
      OR subject ILIKE '%fundraising%'
    )
),
semantic_matches AS (
  SELECT
    id,
    1 - (embedding <=> $1::vector) AS score
  FROM comms.communications
  WHERE workspace_id = $2
    AND founder_id = $3
    AND embedding IS NOT NULL
    AND 1 - (embedding <=> $1::vector) > 0.7
)
SELECT
  c.*,
  COALESCE(k.score, s.score, 0) AS match_score,
  CASE
    WHEN k.id IS NOT NULL THEN 'keyword'
    WHEN s.id IS NOT NULL THEN 'semantic'
  END AS match_type
FROM comms.communications c
LEFT JOIN keyword_matches k ON c.id = k.id
LEFT JOIN semantic_matches s ON c.id = s.id
WHERE (k.id IS NOT NULL OR s.id IS NOT NULL)
ORDER BY match_score DESC
LIMIT 30;
```

### Hybrid Pattern 2: Vector + JSON Path

Search JSONB fields combined with semantic similarity:

```sql
-- Find insights about specific KPIs with semantic context
SELECT
  i.id,
  i.title,
  i.content->>'summary' AS summary,
  i.content->'metrics' AS metrics,
  1 - (i.embedding <=> $1::vector) AS similarity
FROM intel.insights i
WHERE i.workspace_id = $2
  AND i.insight_type = 'kpi'
  AND i.content->'metrics' ? 'revenue'  -- Has 'revenue' key in metrics
  AND i.embedding IS NOT NULL
  AND 1 - (i.embedding <=> $1::vector) > 0.7
ORDER BY i.embedding <=> $1::vector
LIMIT 15;
```

### Hybrid Pattern 3: Vector + Array Containment

Combine tag/topic filtering with semantic search:

```sql
-- Find transcript chunks tagged with specific topics
SELECT
  tc.id,
  tc.text,
  t.title,
  t.topics,
  1 - (tc.embedding <=> $1::vector) AS similarity
FROM meetings.transcript_chunks tc
JOIN meetings.transcripts t ON tc.transcript_id = t.id
WHERE t.workspace_id = $2
  AND t.topics && ARRAY['product', 'roadmap']  -- Has any of these topics
  AND tc.embedding IS NOT NULL
  AND 1 - (tc.embedding <=> $1::vector) > 0.7
ORDER BY tc.embedding <=> $1::vector
LIMIT 25;
```

---

## Multi-Source Semantic Search

### Pattern: Unified Context Retrieval

Search across ALL vector-enabled tables simultaneously:

```sql
-- Find all content related to a query across entire system
WITH contact_matches AS (
  SELECT
    'contact' AS source_type,
    id AS source_id,
    name AS title,
    context->>'summary' AS snippet,
    1 - (embedding <=> $1::vector) AS similarity,
    created_at AS timestamp
  FROM core.contacts
  WHERE workspace_id = $2
    AND embedding IS NOT NULL
    AND 1 - (embedding <=> $1::vector) > 0.7
),
comm_matches AS (
  SELECT
    'communication' AS source_type,
    id AS source_id,
    subject AS title,
    snippet,
    1 - (embedding <=> $1::vector) AS similarity,
    received_at AS timestamp
  FROM comms.communications
  WHERE workspace_id = $2
    AND embedding IS NOT NULL
    AND 1 - (embedding <=> $1::vector) > 0.7
),
transcript_matches AS (
  SELECT
    'transcript_chunk' AS source_type,
    tc.id AS source_id,
    t.title,
    tc.text AS snippet,
    1 - (tc.embedding <=> $1::vector) AS similarity,
    t.recorded_at AS timestamp
  FROM meetings.transcript_chunks tc
  JOIN meetings.transcripts t ON tc.transcript_id = t.id
  WHERE t.workspace_id = $2
    AND tc.embedding IS NOT NULL
    AND 1 - (tc.embedding <=> $1::vector) > 0.7
),
media_matches AS (
  SELECT
    'media_chunk' AS source_type,
    mc.id AS source_id,
    ma.title,
    mc.text AS snippet,
    1 - (mc.embedding <=> $1::vector) AS similarity,
    ma.recorded_at AS timestamp
  FROM media.media_chunks mc
  JOIN media.media_transcripts mt ON mc.media_transcript_id = mt.id
  JOIN media.media_assets ma ON mt.media_id = ma.id
  WHERE ma.workspace_id = $2
    AND mc.embedding IS NOT NULL
    AND 1 - (mc.embedding <=> $1::vector) > 0.7
),
insight_matches AS (
  SELECT
    'insight' AS source_type,
    id AS source_id,
    title,
    content->>'summary' AS snippet,
    1 - (embedding <=> $1::vector) AS similarity,
    created_at AS timestamp
  FROM intel.insights
  WHERE workspace_id = $2
    AND embedding IS NOT NULL
    AND 1 - (embedding <=> $1::vector) > 0.7
)
SELECT * FROM contact_matches
UNION ALL
SELECT * FROM comm_matches
UNION ALL
SELECT * FROM transcript_matches
UNION ALL
SELECT * FROM media_matches
UNION ALL
SELECT * FROM insight_matches
ORDER BY similarity DESC
LIMIT 50;
```

**Use Cases:**
- "What do I know about customer X?"
- "Find everything related to our Q4 strategy"
- "Show me all context about competitor Y"

---

## Performance Optimization

### Optimization 1: Use Partial Indexes

Only index rows with embeddings:

```sql
CREATE INDEX idx_contacts_embedding ON core.contacts
  USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100)
  WHERE embedding IS NOT NULL;  -- Only index non-null embeddings
```

### Optimization 2: Limit Vector Search Scope

Apply filters BEFORE vector search:

```sql
-- GOOD: Filter first, then vector search
SELECT *
FROM comms.communications
WHERE workspace_id = $1  -- Indexed filter
  AND founder_id = $2    -- Indexed filter
  AND received_at >= $3  -- Indexed filter
  AND embedding IS NOT NULL
  AND 1 - (embedding <=> $4::vector) > 0.7
ORDER BY embedding <=> $4::vector
LIMIT 10;

-- BAD: Vector search on entire table
SELECT *
FROM comms.communications
WHERE embedding IS NOT NULL
  AND 1 - (embedding <=> $1::vector) > 0.7
  AND workspace_id = $2  -- Filter after vector search (slow!)
ORDER BY embedding <=> $1::vector
LIMIT 10;
```

### Optimization 3: Adjust IVFFlat Lists Parameter

Tune `lists` parameter based on table size:

```sql
-- Small table (< 10K vectors): lists = 100
CREATE INDEX idx_small_embedding ON small_table
  USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);

-- Medium table (10K-100K vectors): lists = 200
CREATE INDEX idx_medium_embedding ON medium_table
  USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 200);

-- Large table (100K-1M vectors): lists = 500-1000
CREATE INDEX idx_large_embedding ON large_table
  USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 1000);
```

**Formula:** `lists = sqrt(row_count)` (approximate guideline)

### Optimization 4: Set Probes for Query Time

Adjust search accuracy vs. speed:

```sql
-- Higher accuracy, slower (default: probes = lists / 2)
SET ivfflat.probes = 20;

-- Faster, lower recall
SET ivfflat.probes = 5;

-- Then run query
SELECT * FROM contacts
WHERE embedding IS NOT NULL
ORDER BY embedding <=> $1::vector
LIMIT 10;
```

### Optimization 5: Use EXPLAIN ANALYZE

Always profile vector search queries:

```sql
EXPLAIN ANALYZE
SELECT
  id,
  name,
  1 - (embedding <=> $1::vector) AS similarity
FROM core.contacts
WHERE workspace_id = $2
  AND embedding IS NOT NULL
  AND 1 - (embedding <=> $1::vector) > 0.7
ORDER BY embedding <=> $1::vector
LIMIT 10;
```

**Look for:**
- Index scan vs. sequential scan (want index scan)
- Number of rows scanned
- Query execution time

---

## Python Examples

### Example 1: Basic Semantic Search

```python
import openai
from supabase import create_client

# Initialize clients
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
openai.api_key = OPENAI_API_KEY

def semantic_search(query: str, workspace_id: str, limit: int = 10):
    """Search contacts using semantic similarity."""

    # Generate query embedding
    response = openai.embeddings.create(
        model="text-embedding-ada-002",
        input=query
    )
    query_embedding = response.data[0].embedding

    # Search database
    result = supabase.rpc(
        'search_contacts',
        {
            'query_embedding': query_embedding,
            'p_workspace_id': workspace_id,
            'match_threshold': 0.7,
            'match_count': limit
        }
    ).execute()

    return result.data

# Usage
results = semantic_search(
    query="investors interested in AI startups",
    workspace_id="123e4567-e89b-12d3-a456-426614174000"
)

for contact in results:
    print(f"{contact['name']} - Similarity: {contact['similarity']:.2f}")
```

### Example 2: Multi-Source Context Retrieval

```python
from typing import List, Dict

def retrieve_context(
    query: str,
    workspace_id: str,
    founder_id: str,
    sources: List[str] = ['contacts', 'communications', 'transcripts'],
    limit_per_source: int = 10
) -> Dict[str, List]:
    """Retrieve relevant context from multiple sources."""

    # Generate embedding once
    response = openai.embeddings.create(
        model="text-embedding-ada-002",
        input=query
    )
    query_embedding = response.data[0].embedding

    results = {}

    # Search each source
    if 'contacts' in sources:
        results['contacts'] = supabase.rpc(
            'search_contacts',
            {
                'query_embedding': query_embedding,
                'p_workspace_id': workspace_id,
                'match_threshold': 0.7,
                'match_count': limit_per_source
            }
        ).execute().data

    if 'communications' in sources:
        results['communications'] = supabase.rpc(
            'search_communications',
            {
                'query_embedding': query_embedding,
                'p_workspace_id': workspace_id,
                'p_founder_id': founder_id,
                'match_threshold': 0.7,
                'match_count': limit_per_source
            }
        ).execute().data

    if 'transcripts' in sources:
        results['transcript_chunks'] = supabase.rpc(
            'search_transcript_chunks',
            {
                'query_embedding': query_embedding,
                'p_workspace_id': workspace_id,
                'match_threshold': 0.7,
                'match_count': limit_per_source
            }
        ).execute().data

    return results

# Usage
context = retrieve_context(
    query="What was discussed about pricing strategy?",
    workspace_id="...",
    founder_id="..."
)

print(f"Found {len(context['contacts'])} contacts")
print(f"Found {len(context['communications'])} messages")
print(f"Found {len(context['transcript_chunks'])} transcript chunks")
```

### Example 3: Hybrid Search (Vector + Keyword)

```python
def hybrid_search(
    query: str,
    keywords: List[str],
    workspace_id: str,
    limit: int = 20
) -> List[Dict]:
    """Combine semantic and keyword search."""

    # Generate embedding
    response = openai.embeddings.create(
        model="text-embedding-ada-002",
        input=query
    )
    query_embedding = response.data[0].embedding

    # Build keyword filter
    keyword_filter = ' OR '.join([f"content.ilike.%{kw}%" for kw in keywords])

    # Execute hybrid search
    result = supabase.rpc(
        'hybrid_search_communications',
        {
            'query_embedding': query_embedding,
            'keywords': keywords,
            'p_workspace_id': workspace_id,
            'match_count': limit
        }
    ).execute()

    return result.data

# Usage
results = hybrid_search(
    query="fundraising discussions",
    keywords=["series A", "valuation", "term sheet"],
    workspace_id="..."
)
```

---

## Common Use Cases

### Use Case 1: Investor Relationship Context

**Goal:** Find all context about a specific investor before a meeting

```sql
-- Step 1: Find investor contact
SELECT id, name, embedding
FROM core.contacts
WHERE workspace_id = $1
  AND name ILIKE '%Alex Chen%'
  AND type = 'investor'
LIMIT 1;

-- Step 2: Find all similar context using investor's embedding
WITH investor_context AS (
  SELECT embedding FROM core.contacts WHERE id = $investor_id
)
SELECT
  'communication' AS source,
  subject AS title,
  snippet,
  received_at AS date,
  1 - (c.embedding <=> ic.embedding) AS similarity
FROM comms.communications c, investor_context ic
WHERE c.workspace_id = $1
  AND c.embedding IS NOT NULL
  AND 1 - (c.embedding <=> ic.embedding) > 0.75
ORDER BY c.embedding <=> ic.embedding
LIMIT 20;
```

### Use Case 2: Action Item Discovery

**Goal:** Find all action items related to a topic across meetings

```sql
-- Find meeting chunks with high similarity to "customer onboarding improvements"
SELECT
  tc.text,
  tc.speaker,
  t.title AS meeting_title,
  m.start_time AS meeting_date,
  t.action_items,
  1 - (tc.embedding <=> $1::vector) AS similarity
FROM meetings.transcript_chunks tc
JOIN meetings.transcripts t ON tc.transcript_id = t.id
JOIN meetings.meetings m ON t.meeting_id = m.id
WHERE m.workspace_id = $2
  AND tc.embedding IS NOT NULL
  AND 1 - (tc.embedding <=> $1::vector) > 0.75
  AND t.action_items IS NOT NULL
  AND jsonb_array_length(t.action_items) > 0
ORDER BY tc.embedding <=> $1::vector
LIMIT 15;
```

### Use Case 3: Knowledge Base Search

**Goal:** Answer a question using all available context

```sql
-- Multi-source search for "How does our pricing compare to competitors?"
-- (Use the multi-source query from earlier section)

-- Then in application layer, use LLM to synthesize answer:
-- context = fetch_from_db(query_embedding)
-- answer = llm.generate(context + question)
```

### Use Case 4: Similar Email Drafting

**Goal:** Find similar emails to use as templates

```sql
-- Find similar sent emails for a new draft
SELECT
  subject,
  content,
  recipients,
  1 - (embedding <=> $1::vector) AS similarity
FROM comms.communications
WHERE workspace_id = $2
  AND founder_id = $3
  AND platform IN ('gmail', 'outlook')
  AND sender ILIKE '%founder@company.com%'  -- Sent by founder
  AND embedding IS NOT NULL
  AND 1 - (embedding <=> $1::vector) > 0.8  -- High similarity only
ORDER BY embedding <=> $1::vector
LIMIT 5;
```

---

## Summary

### Best Practices

1. **Always filter by workspace_id first** (security + performance)
2. **Use appropriate similarity thresholds** (0.7+ for most use cases)
3. **Combine with metadata filters** for hybrid search
4. **Index only non-null embeddings** (partial indexes)
5. **Tune IVFFlat parameters** based on table size
6. **Profile with EXPLAIN ANALYZE** to optimize queries
7. **Use CTEs for complex multi-source searches**
8. **Cache embeddings** (don't regenerate for same query)

### Performance Targets

- **Search latency:** < 100ms for single-table queries
- **Multi-source search:** < 300ms for 5 tables
- **Recall rate:** > 95% with tuned parameters
- **Concurrent queries:** Support 100+ simultaneous searches

### Next Steps

1. Deploy migrations with vector indexes
2. Implement embedding generation pipeline
3. Create stored procedures for common searches
4. Set up monitoring for query performance
5. Build Python/TypeScript SDK wrappers

---

**Document Version:** 1.0
**Last Updated:** 2025-10-30
**Related Documents:**
- `/docs/architecture.md` - System architecture overview
- `/migrations/001_initial_schema.sql` - Schema implementation
