# Vector Embedding Strategy

## Executive Summary

This document defines the embedding strategy for storing and retrieving meeting transcripts, enabling semantic search, context-aware summarization, and intelligent information retrieval. We recommend using `text-embedding-3-small` from OpenAI for cost-effective, high-quality embeddings with pgvector for storage.

## Requirements

### Functional Requirements

1. **Semantic Search**
   - Find relevant meetings by topic, not just keywords
   - "What did we discuss about pricing?" → relevant meetings
   - Cross-meeting insights: "When did we last talk about this customer?"

2. **Context-Aware Summarization**
   - Retrieve relevant past context for better summaries
   - "In our last board meeting, we discussed X" → find context

3. **Duplicate Detection**
   - Identify similar or duplicate meetings
   - Prevent re-processing

4. **Recommendation**
   - "You might want to review these related meetings"
   - Surface relevant historical context

### Non-Functional Requirements

| Requirement | Target | Rationale |
|-------------|--------|-----------|
| Embedding latency | <2s for 10K words | Real-time processing |
| Search latency | <200ms for top-10 results | Interactive UX |
| Storage efficiency | <50MB per 100 meetings | Cost management |
| Recall@10 | ≥85% | Find relevant content |
| Cost per meeting | <$0.01 | Budget constraint |

## Embedding Model Selection

### Model Comparison

| Model | Dimensions | Cost per 1M tokens | Quality (MTEB) | Speed | Recommendation |
|-------|-----------|-------------------|----------------|-------|----------------|
| **text-embedding-3-small** | 1536 | $0.02 | 62.3% | Fast | ✅ Recommended |
| **text-embedding-3-large** | 3072 | $0.13 | 64.6% | Medium | High-value only |
| **text-embedding-ada-002** | 1536 | $0.10 | 61.0% | Fast | Legacy, more expensive |
| **all-MiniLM-L6-v2** (local) | 384 | $0 (infra) | 58.8% | Very fast | Privacy-sensitive |
| **e5-large-v2** (local) | 1024 | $0 (infra) | 62.5% | Medium | Self-hosted option |
| **jina-embeddings-v2-base** | 768 | $0.02 | 60.4% | Fast | Alternative API |

### Recommended: text-embedding-3-small

**Rationale:**
- Best cost-performance ratio ($0.02/1M tokens)
- High quality (62.3% MTEB score)
- Fast inference (~1s for 10K tokens)
- Native support for dimensions reduction (512, 768, 1536)
- Proven reliability from OpenAI

**Cost Analysis:**
```python
# Average meeting: 10,000 words = ~13,000 tokens
# Cost: 13,000 / 1,000,000 * $0.02 = $0.00026
# With chunking (5 chunks): $0.0013 per meeting

# 1,000 meetings/month: $1.30
# 10,000 meetings/month: $13.00
```

**When to Use text-embedding-3-large:**
- High-stakes searches (investor/board meeting retrieval)
- Complex multi-meeting analysis
- Better quality worth 6.5x cost premium

---

## Chunking Strategy

### Challenge: Context Window Limits

Embeddings work best on focused chunks, not entire documents.
- Transcript: 10,000 words (too long)
- Chunk: 300-500 words (optimal for embedding models)

### Semantic Chunking Approach

**Naive Approach (Don't Use):**
```python
# BAD: Fixed-size chunks break sentences/context
chunks = [text[i:i+500] for i in range(0, len(text), 500)]
```

**Recommended: Semantic Boundary Chunking**

```python
from typing import List
from dataclasses import dataclass

@dataclass
class TranscriptChunk:
    text: str
    chunk_index: int
    start_time: Optional[int]
    end_time: Optional[int]
    speaker: Optional[str]
    topic: Optional[str]

def chunk_transcript_semantically(
    transcript: str,
    target_chunk_size: int = 400,  # words
    overlap: int = 50  # words
) -> List[TranscriptChunk]:
    """
    Chunk transcript at semantic boundaries with overlap

    Strategy:
    1. Split by speaker turns (preserve speaker context)
    2. Split by topic shifts (use topic modeling)
    3. Ensure chunks are ~400 words
    4. Add 50-word overlap for context continuity
    """
    chunks = []

    # Step 1: Parse transcript into utterances
    utterances = parse_transcript_by_speaker(transcript)

    current_chunk = []
    current_word_count = 0

    for i, utterance in enumerate(utterances):
        utterance_words = len(utterance.text.split())

        # If adding this utterance exceeds target, create chunk
        if current_word_count + utterance_words > target_chunk_size and current_chunk:
            # Create chunk from current_chunk
            chunk_text = " ".join([u.text for u in current_chunk])

            chunks.append(TranscriptChunk(
                text=chunk_text,
                chunk_index=len(chunks),
                start_time=current_chunk[0].timestamp,
                end_time=current_chunk[-1].timestamp,
                speaker=current_chunk[0].speaker,
                topic=detect_topic(chunk_text)
            ))

            # Overlap: keep last N words
            overlap_utterances = get_last_n_words(current_chunk, overlap)
            current_chunk = overlap_utterances
            current_word_count = sum(len(u.text.split()) for u in current_chunk)

        current_chunk.append(utterance)
        current_word_count += utterance_words

    # Final chunk
    if current_chunk:
        chunks.append(TranscriptChunk(
            text=" ".join([u.text for u in current_chunk]),
            chunk_index=len(chunks),
            start_time=current_chunk[0].timestamp,
            end_time=current_chunk[-1].timestamp,
            speaker=current_chunk[0].speaker,
            topic=detect_topic(" ".join([u.text for u in current_chunk]))
        ))

    return chunks
```

### Chunk Metadata Enrichment

```python
def enrich_chunk_metadata(chunk: TranscriptChunk, meeting_metadata: Dict) -> Dict:
    """
    Add metadata to chunk for better filtering and context
    """
    return {
        "text": chunk.text,
        "chunk_index": chunk.chunk_index,
        "meeting_id": meeting_metadata["id"],
        "meeting_type": meeting_metadata["type"],
        "meeting_date": meeting_metadata["date"],
        "participants": meeting_metadata["participants"],
        "speaker": chunk.speaker,
        "start_time": chunk.start_time,
        "end_time": chunk.end_time,
        "topic": chunk.topic,
        "duration": chunk.end_time - chunk.start_time if chunk.end_time else None
    }
```

---

## Embedding Generation Pipeline

### Complete Pipeline

```python
import openai
from typing import List, Dict
import numpy as np

class EmbeddingPipeline:
    """
    Generate and store embeddings for meeting transcripts
    """

    def __init__(self, model: str = "text-embedding-3-small", dimensions: int = 1536):
        self.model = model
        self.dimensions = dimensions
        self.client = openai.OpenAI()

    def generate_embeddings(
        self,
        texts: List[str],
        batch_size: int = 100
    ) -> List[List[float]]:
        """
        Generate embeddings in batches for efficiency
        """
        all_embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]

            response = self.client.embeddings.create(
                model=self.model,
                input=batch,
                dimensions=self.dimensions  # Optional: reduce dimensions
            )

            embeddings = [item.embedding for item in response.data]
            all_embeddings.extend(embeddings)

        return all_embeddings

    def process_meeting(self, transcript: str, meeting_metadata: Dict) -> List[Dict]:
        """
        Complete pipeline: chunk → embed → prepare for storage
        """
        # Step 1: Chunk transcript
        chunks = chunk_transcript_semantically(transcript)

        # Step 2: Generate embeddings
        chunk_texts = [chunk.text for chunk in chunks]
        embeddings = self.generate_embeddings(chunk_texts)

        # Step 3: Prepare records for database
        records = []
        for chunk, embedding in zip(chunks, embeddings):
            metadata = enrich_chunk_metadata(chunk, meeting_metadata)

            records.append({
                "meeting_id": meeting_metadata["id"],
                "chunk_index": chunk.chunk_index,
                "content": chunk.text,
                "embedding": embedding,
                "metadata": metadata
            })

        return records
```

---

## Storage in pgvector

### Schema Design

```sql
-- Already exists in meetings.transcript_chunks
CREATE TABLE meetings.transcript_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transcript_id UUID NOT NULL REFERENCES meetings.transcripts(id),
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    embedding vector(1536),  -- pgvector type
    metadata JSONB,
    start_time INTEGER,
    end_time INTEGER,
    created_at TIMESTAMP DEFAULT NOW(),

    -- Indexes for performance
    UNIQUE(transcript_id, chunk_index)
);

-- Vector similarity index (HNSW for fast approximate search)
CREATE INDEX transcript_chunks_embedding_idx
ON meetings.transcript_chunks
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Metadata indexes for filtering
CREATE INDEX transcript_chunks_metadata_idx
ON meetings.transcript_chunks
USING GIN (metadata);
```

### Insertion

```python
async def store_embeddings(records: List[Dict]):
    """
    Store embeddings in pgvector
    """
    from supabase import create_client

    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

    # Batch insert
    for record in records:
        await supabase.table("meetings.transcript_chunks").insert({
            "transcript_id": record["meeting_id"],
            "chunk_index": record["chunk_index"],
            "content": record["content"],
            "embedding": record["embedding"],  # pgvector handles this
            "metadata": record["metadata"],
            "start_time": record["metadata"].get("start_time"),
            "end_time": record["metadata"].get("end_time")
        }).execute()
```

---

## Semantic Search

### Basic Similarity Search

```python
async def semantic_search(
    query: str,
    limit: int = 10,
    similarity_threshold: float = 0.7,
    filters: Optional[Dict] = None
) -> List[Dict]:
    """
    Search for relevant chunks using cosine similarity

    Args:
        query: Natural language search query
        limit: Number of results to return
        similarity_threshold: Minimum similarity score (0-1)
        filters: Metadata filters (meeting_type, date_range, participants, etc.)
    """
    # Generate query embedding
    query_embedding = generate_embeddings([query])[0]

    # Build SQL query
    sql = """
    SELECT
        id,
        transcript_id,
        content,
        metadata,
        1 - (embedding <=> %s::vector) AS similarity
    FROM meetings.transcript_chunks
    WHERE 1 - (embedding <=> %s::vector) > %s
    """

    params = [query_embedding, query_embedding, similarity_threshold]

    # Add metadata filters
    if filters:
        if "meeting_type" in filters:
            sql += " AND metadata->>'meeting_type' = %s"
            params.append(filters["meeting_type"])

        if "date_after" in filters:
            sql += " AND (metadata->>'meeting_date')::date >= %s"
            params.append(filters["date_after"])

        if "participants" in filters:
            sql += " AND metadata->'participants' @> %s::jsonb"
            params.append(json.dumps(filters["participants"]))

    sql += " ORDER BY similarity DESC LIMIT %s"
    params.append(limit)

    # Execute
    results = await execute_query(sql, params)

    return results
```

### Hybrid Search (Semantic + Keyword)

```python
async def hybrid_search(
    query: str,
    limit: int = 10,
    semantic_weight: float = 0.7,
    keyword_weight: float = 0.3
) -> List[Dict]:
    """
    Combine semantic (vector) and keyword (BM25) search

    Better for specific terms (names, dates) + conceptual queries
    """
    # Semantic search
    semantic_results = await semantic_search(query, limit=limit * 2)

    # Keyword search (PostgreSQL full-text search)
    keyword_results = await keyword_search(query, limit=limit * 2)

    # Combine and re-rank
    combined = {}

    for result in semantic_results:
        chunk_id = result["id"]
        combined[chunk_id] = {
            **result,
            "semantic_score": result["similarity"],
            "keyword_score": 0.0
        }

    for result in keyword_results:
        chunk_id = result["id"]
        if chunk_id in combined:
            combined[chunk_id]["keyword_score"] = result["rank"]
        else:
            combined[chunk_id] = {
                **result,
                "semantic_score": 0.0,
                "keyword_score": result["rank"]
            }

    # Calculate combined score
    for chunk_id in combined:
        semantic = combined[chunk_id]["semantic_score"]
        keyword = combined[chunk_id]["keyword_score"]
        combined[chunk_id]["combined_score"] = (
            semantic_weight * semantic +
            keyword_weight * keyword
        )

    # Sort by combined score
    ranked_results = sorted(
        combined.values(),
        key=lambda x: x["combined_score"],
        reverse=True
    )[:limit]

    return ranked_results
```

---

## Advanced Use Cases

### 1. Meeting Deduplication

```python
async def find_duplicate_meetings(
    new_meeting_id: str,
    similarity_threshold: float = 0.90
) -> List[Dict]:
    """
    Find potential duplicate or very similar meetings
    """
    # Get embeddings for new meeting
    new_chunks = await get_meeting_chunks(new_meeting_id)

    # Average embeddings for whole-meeting comparison
    new_embedding = np.mean([chunk["embedding"] for chunk in new_chunks], axis=0)

    # Search for similar meetings (by comparing averaged embeddings)
    similar_meetings = await find_similar_by_embedding(
        new_embedding,
        threshold=similarity_threshold,
        exclude_meeting_id=new_meeting_id
    )

    return similar_meetings
```

### 2. Cross-Meeting Context Retrieval

```python
async def get_historical_context(
    current_meeting_topic: str,
    meeting_type: Optional[str] = None,
    lookback_days: int = 90,
    limit: int = 5
) -> List[Dict]:
    """
    Find relevant context from past meetings on similar topics

    Use for context-aware summarization:
    "Based on previous discussions about pricing (3 meetings in last month)..."
    """
    filters = {
        "date_after": (datetime.now() - timedelta(days=lookback_days)).isoformat()
    }

    if meeting_type:
        filters["meeting_type"] = meeting_type

    relevant_chunks = await semantic_search(
        query=current_meeting_topic,
        limit=limit,
        filters=filters
    )

    return relevant_chunks
```

### 3. Topic Clustering

```python
from sklearn.cluster import KMeans
import numpy as np

async def cluster_meetings_by_topic(
    meeting_ids: List[str],
    n_clusters: int = 5
) -> Dict[int, List[str]]:
    """
    Group meetings into topic clusters

    Useful for:
    - "Related meetings" recommendations
    - Topic trend analysis
    - Dashboard organization
    """
    # Get all meeting embeddings (averaged)
    meeting_embeddings = []
    for meeting_id in meeting_ids:
        chunks = await get_meeting_chunks(meeting_id)
        avg_embedding = np.mean([c["embedding"] for c in chunks], axis=0)
        meeting_embeddings.append(avg_embedding)

    # Cluster
    kmeans = KMeans(n_clusters=n_clusters, random_state=42)
    cluster_labels = kmeans.fit_predict(np.array(meeting_embeddings))

    # Group meetings by cluster
    clusters = {}
    for meeting_id, cluster_id in zip(meeting_ids, cluster_labels):
        if cluster_id not in clusters:
            clusters[cluster_id] = []
        clusters[cluster_id].append(meeting_id)

    return clusters
```

### 4. Question Answering Over Meetings

```python
async def answer_question_from_meetings(
    question: str,
    meeting_filters: Optional[Dict] = None,
    top_k: int = 5
) -> str:
    """
    RAG (Retrieval-Augmented Generation) for meeting Q&A

    "What did we decide about pricing in the last board meeting?"
    → Retrieve relevant chunks → Generate answer with LLM
    """
    # Step 1: Retrieve relevant chunks
    relevant_chunks = await semantic_search(
        query=question,
        limit=top_k,
        filters=meeting_filters
    )

    # Step 2: Build context from chunks
    context = "\n\n".join([
        f"From {chunk['metadata']['meeting_type']} on {chunk['metadata']['meeting_date']}:\n{chunk['content']}"
        for chunk in relevant_chunks
    ])

    # Step 3: Generate answer with LLM
    prompt = f"""Answer this question based on the meeting context below.

Question: {question}

Context from meetings:
{context}

Answer:
"""

    answer = await call_llm("gpt-4o-mini", prompt)

    return answer
```

---

## Performance Optimization

### 1. Dimension Reduction

```python
# Trade quality for cost/speed
# text-embedding-3-small supports 512, 768, 1536 dimensions

# Full quality (default)
embedding_1536 = generate_embedding(text, dimensions=1536)

# Reduced (75% quality, 2x faster, less storage)
embedding_768 = generate_embedding(text, dimensions=768)

# Minimal (60% quality, 3x faster, 1/3 storage)
embedding_512 = generate_embedding(text, dimensions=512)
```

**Recommendation:** Start with 1536, reduce to 768 if needed for scale.

### 2. Caching

```python
from functools import lru_cache
import hashlib

@lru_cache(maxsize=1000)
def get_embedding_cached(text: str) -> List[float]:
    """
    Cache embeddings for frequently accessed content
    """
    text_hash = hashlib.md5(text.encode()).hexdigest()

    # Check Redis cache
    cached = redis.get(f"embedding:{text_hash}")
    if cached:
        return json.loads(cached)

    # Generate and cache
    embedding = generate_embedding(text)
    redis.setex(f"embedding:{text_hash}", 86400, json.dumps(embedding))

    return embedding
```

### 3. Batch Processing

```python
# GOOD: Batch API calls
texts = [chunk1, chunk2, chunk3, ...]
embeddings = generate_embeddings(texts)  # Single API call

# BAD: Individual calls
for text in texts:
    embedding = generate_embedding(text)  # Multiple API calls (slow + expensive)
```

---

## Monitoring & Quality Assurance

### Embedding Quality Metrics

```python
def evaluate_embedding_quality(test_queries: List[Dict]) -> Dict:
    """
    Evaluate embedding search quality

    Test queries: {
        "query": "What did we discuss about pricing?",
        "relevant_meeting_ids": ["meeting-123", "meeting-456"]
    }
    """
    metrics = {
        "recall_at_10": [],
        "mrr": [],  # Mean Reciprocal Rank
        "avg_similarity": []
    }

    for test in test_queries:
        results = semantic_search(test["query"], limit=10)
        retrieved_ids = [r["meeting_id"] for r in results]

        # Recall@10: fraction of relevant docs in top 10
        relevant_in_top10 = len(set(retrieved_ids) & set(test["relevant_meeting_ids"]))
        recall = relevant_in_top10 / len(test["relevant_meeting_ids"])
        metrics["recall_at_10"].append(recall)

        # MRR: 1/rank of first relevant result
        for i, doc_id in enumerate(retrieved_ids):
            if doc_id in test["relevant_meeting_ids"]:
                metrics["mrr"].append(1 / (i + 1))
                break

    return {
        "avg_recall_at_10": statistics.mean(metrics["recall_at_10"]),
        "avg_mrr": statistics.mean(metrics["mrr"]),
        "pass": statistics.mean(metrics["recall_at_10"]) >= 0.85
    }
```

---

## Cost Analysis

### Per-Meeting Cost Breakdown

```python
# Average meeting: 10,000 words = ~13,000 tokens
# Chunked into 5 chunks of ~2,600 tokens each

# Embedding cost:
# 13,000 tokens / 1,000,000 * $0.02 = $0.00026

# Storage cost (pgvector):
# 5 chunks * 1536 dims * 4 bytes = 30KB
# At $0.0001/KB/month = $0.003/month

# Total first month: $0.00026 + $0.003 = $0.00326
# Total ongoing: $0.003/month
```

### Monthly Projections

| Meetings/Month | Embedding Cost | Storage Cost | Total/Month |
|----------------|----------------|--------------|-------------|
| 100 | $0.026 | $0.30 | $0.33 |
| 1,000 | $0.26 | $3.00 | $3.26 |
| 10,000 | $2.60 | $30.00 | $32.60 |

**Conclusion:** Extremely cost-effective, even at scale.

---

**Document Version:** 1.0
**Last Updated:** 2025-10-30
**Author:** ML Research Team
**Status:** Ready for Implementation
