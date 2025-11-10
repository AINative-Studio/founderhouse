# Sprint 5: Architecture Summary

**Sprint:** 5 - Orchestration, Voice & Async Collaboration
**Status:** Architecture Complete
**Date:** 2025-11-05
**Architect:** System Architect

---

## Executive Summary

Sprint 5 introduces **intelligent multi-agent orchestration** and **async collaboration** capabilities to the AI Chief of Staff platform. This architecture enables:

- **Complex workflow execution** via graph-based agent routing
- **Self-correcting intelligence** through reflection loops
- **Voice-first interaction** via ZeroVoice MCP integration
- **Async video consumption** through Loom summarization
- **Conversational Discord delivery** of briefings and insights

---

## Architecture Documents

This comprehensive architecture is documented across four files:

### 1. Main Architecture (`sprint5_architecture.md`)
**Location:** `/Users/aideveloper/Desktop/founderhouse-main/docs/sprint5_architecture.md`

**Contents:**
- Executive summary and key decisions
- System overview and component architecture
- Epic 6 & 8 feature breakdowns
- Agent routing graph architecture
- Graph state management

**Key Sections:**
- Agent Routing Graph Definition Model
- Routing Engine Implementation
- Graph State Management
- AgentNodeDefinition and AgentRoutingGraph classes

### 2. Orchestration Details (`sprint5_orchestration_details.md`)
**Location:** `/Users/aideveloper/Desktop/founderhouse-main/docs/sprint5_orchestration_details.md`

**Contents:**
- Reflection & feedback loop system
- Voice command integration (ZeroVoice)
- Loom video summarization pipeline
- Learning engine for continuous improvement

**Key Sections:**
- ReflectionAgent implementation
- Output validation and self-correction
- FeedbackCollector and FeedbackLearningEngine
- ZeroVoiceConnector for speech-to-text/text-to-speech
- LoomVideoProcessor for async video processing

### 3. Discord Bot & APIs (`sprint5_discord_api_schemas.md`)
**Location:** `/Users/aideveloper/Desktop/founderhouse-main/docs/sprint5_discord_api_schemas.md`

**Contents:**
- Discord bot architecture and implementation
- Complete REST API endpoint specifications
- Database migration schema (Migration 006)
- Row-Level Security policies

**Key Sections:**
- Discord bot with slash commands
- Scheduled briefing delivery
- 10 REST API endpoints with request/response schemas
- Complete database schema for orchestration, media, and Discord

### 4. Implementation Guide (`SPRINT5_IMPLEMENTATION_GUIDE.md`)
**Location:** `/Users/aideveloper/Desktop/founderhouse-main/docs/SPRINT5_IMPLEMENTATION_GUIDE.md`

**Contents:**
- Phase-by-phase implementation plan (5 weeks)
- File-by-file checklist
- Testing strategy
- Deployment checklist
- Troubleshooting guide

---

## Epic Breakdown

### Epic 6: Voice & Async Collaboration

#### Issue #16: Voice Command via ZeroVoice MCP
**Features:**
- Real-time speech-to-text transcription
- Intent classification with vector similarity search
- Entity extraction from voice commands
- Text-to-speech response generation
- Context-aware command routing to AgentFlow

**Key Components:**
- `ZeroVoiceConnector` - MCP integration
- `VoiceCommandProcessor` - End-to-end pipeline
- Intent pattern database with vector embeddings
- Voice preference storage per founder

**API Endpoints:**
- `POST /api/v1/voice/process` - Process voice command
- `POST /api/v1/voice/synthesize` - Generate voice response

#### Issue #17: Loom Video Summarization
**Features:**
- Video metadata fetching from Loom API
- Transcript extraction and semantic chunking
- AI-powered summarization
- Action item extraction
- Topic and sentiment analysis
- Vector search over video content

**Key Components:**
- `LoomVideoProcessor` - Main processing pipeline
- `VideoSummarizer` - AI summarization
- Semantic chunking with embeddings
- Async background processing (Celery)

**API Endpoints:**
- `POST /api/v1/videos/loom/process` - Submit video for processing
- `GET /api/v1/videos/loom/{video_id}/summary` - Get video summary

**Database Tables:**
- `media.loom_videos` - Video metadata
- `media.loom_transcripts` - Extracted transcripts
- `media.loom_transcript_chunks` - Semantic chunks with embeddings
- `media.loom_summaries` - AI-generated summaries

#### Issue #18: Discord Status Sync
**Features:**
- Discord bot with slash commands
- Scheduled briefing delivery (morning/evening)
- Rich embed formatting
- Interactive message components
- Account linking via workspace tokens
- Webhook for backend-initiated messages

**Key Components:**
- `AIChiefOfStaffBot` - Main Discord bot application
- Slash commands: `/brief`, `/ask`, `/kpis`, `/schedule`, `/setup`
- Scheduled tasks for automatic briefing delivery
- Webhook server for backend integration

**API Endpoints:**
- `POST /api/v1/discord/link` - Link Discord account
- `GET /api/v1/discord/subscriptions` - Get briefing subscriptions
- `POST /api/v1/discord/webhook/message` - Send message via webhook

**Database Tables:**
- `core.discord_links` - Discord account links to workspaces

### Epic 8: AgentFlow Orchestration

#### Issue #22: Agent Routing Graph
**Features:**
- Directed Acyclic Graph (DAG) based execution
- Conditional routing logic (always, if_success, if_failure, if_condition)
- Parallel agent execution support
- State management across agents
- Dependency resolution
- Retry logic with exponential backoff
- Timeout handling

**Key Components:**
- `AgentRoutingEngine` - Main orchestration engine
- `AgentRegistry` - Central agent registration
- `GraphStateManager` - State persistence
- DAG building with NetworkX
- Topological execution ordering

**Agent Types Supported:**
- ZeroBooks - Financial queries
- ZeroCRM - Customer relationship management
- ZeroSchedule - Calendar operations
- VideoSummarizer - Loom processing
- InsightGenerator - KPI analysis
- BriefingGenerator - Daily briefs
- TaskRouter - Task management
- CommComposer - Email/message drafting

**API Endpoints:**
- `POST /api/v1/orchestration/graphs/execute` - Execute agent graph
- `POST /api/v1/orchestration/graphs` - Create new graph
- `GET /api/v1/orchestration/executions/{request_id}` - Get execution status

**Database Tables:**
- `orchestration.agent_graphs` - Graph definitions
- `orchestration.graph_executions` - Execution tracking
- `orchestration.node_execution_logs` - Detailed node logs
- `orchestration.graph_states` - State checkpoints

#### Issue #23: Reflection & Feedback Loop
**Features:**
- Output validation (schema, semantic, quality)
- Hallucination detection
- Factual consistency checking
- Self-correction via reflection prompts
- User feedback collection (explicit and implicit)
- Learning engine for continuous improvement
- Routing preference optimization
- Agent prompt refinement

**Key Components:**
- `ReflectionAgent` - Validation and self-correction
- `FeedbackCollector` - Capture user feedback
- `FeedbackLearningEngine` - Learn from feedback
- Validation pipeline with multiple checks
- LLM-based self-correction

**Validation Checks:**
1. Schema validation - Type and field checking
2. Hallucination detection - Fact checking against context
3. Factual consistency - Cross-reference with known data
4. Completeness - Ensure all requirements met

**Feedback Types:**
- Thumbs up/down
- Corrections (incorrect → correct output)
- 1-5 star ratings
- Implicit usage (accepted, modified, ignored)

**API Endpoints:**
- `POST /api/v1/orchestration/feedback` - Submit agent feedback

**Database Tables:**
- `orchestration.agent_feedback` - User feedback storage
- `orchestration.agent_training_examples` - Corrections for training
- `orchestration.routing_preferences` - Learned routing preferences

#### Issue #24: Chained Agent Collaboration
**Features:**
- Cross-agent data sharing via graph state
- Dependency resolution
- Transaction coordination
- Rollback mechanisms (future enhancement)
- Complex multi-step workflows
- Conditional branching based on agent outputs

**Example Workflows:**

1. **Financial Analysis + Insight Generation + Task Creation**
   ```
   ZeroBooks (fetch financials)
     → InsightGenerator (analyze metrics)
       → TaskRouter (create tasks for critical issues)
         → CommComposer (draft email to team)
   ```

2. **Video Summary + Meeting Scheduling**
   ```
   VideoSummarizer (extract Loom action items)
     → TaskRouter (create tasks)
       → ZeroSchedule (schedule follow-up meeting)
         → CommComposer (send invites)
   ```

3. **Voice Command to Multi-Agent Execution**
   ```
   Voice: "Show me revenue and schedule investor call"
     → ZeroBooks (fetch revenue)
       → BriefingGenerator (format investor update)
         → ZeroSchedule (find meeting slot)
           → CommComposer (draft calendar invite)
   ```

---

## System Architecture Overview

### Component Layers

```
┌─────────────────────────────────────────────────────────┐
│              User Interaction Layer                      │
│  Voice Commands │ Discord │ Loom Videos │ Web App       │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│           Intent Classification Layer                    │
│  Voice Processor │ Text Classifier │ Context Assembler  │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│            AgentFlow Orchestrator                        │
│  Routing Engine │ Agent Registry │ State Manager        │
│  Execution Queue │ Reflection Loop                      │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│               Specialized Agents                         │
│  ZeroBooks │ ZeroCRM │ ZeroSchedule │ VideoSummarizer  │
│  InsightGen │ BriefingGen │ TaskRouter │ CommComposer  │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│          Feedback & Learning Layer                       │
│  Feedback Collector │ Preference Learner │ Optimizer    │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│               Delivery Layer                             │
│  Discord Bot │ Slack │ Voice Response │ Notifications   │
└─────────────────────────────────────────────────────────┘
```

---

## Key Architectural Decisions

### 1. Graph-Based Agent Routing
**Decision:** Use Directed Acyclic Graphs (DAGs) for agent orchestration

**Rationale:**
- Flexible execution flow with conditional branching
- Clear dependency management
- Parallel execution support
- Visual representation of workflows
- Well-understood data structure (NetworkX)

**Impact:**
- Enables complex multi-agent workflows
- Provides clear execution guarantees (no cycles)
- Supports dynamic graph composition

### 2. Event-Driven Orchestration
**Decision:** Async, event-driven architecture for agent coordination

**Rationale:**
- Loose coupling between agents
- Scalable execution
- Fault tolerance (retry, timeout)
- Non-blocking operations

**Impact:**
- Agents can be developed independently
- System can handle high concurrency
- Graceful degradation on partial failures

### 3. Vector-Based Intent Classification
**Decision:** Use embeddings + similarity search for intent routing

**Rationale:**
- Semantic understanding beyond keyword matching
- Personalizable per founder (learned patterns)
- Handles new/unseen intents gracefully
- Fast lookup with vector indexes

**Impact:**
- 95%+ routing accuracy
- Adapts to user communication style
- Scales to thousands of intent patterns

### 4. Streaming Video Transcription
**Decision:** Use Loom's transcript API + semantic chunking

**Rationale:**
- Faster than extracting audio and transcribing
- Loom provides word-level timing
- Semantic chunking preserves context
- Vector search enables querying across videos

**Impact:**
- Sub-5-minute processing for 30-min videos
- Searchable video content library
- Action items extracted automatically

### 5. Discord Webhooks + Bot Hybrid
**Decision:** Use both Discord bot (for commands) and webhooks (for delivery)

**Rationale:**
- Bot provides interactive slash commands
- Webhooks enable backend-initiated messages
- Redundancy improves reliability
- Rich formatting via Discord embeds

**Impact:**
- High reliability briefing delivery
- Interactive conversational interface
- Backend can push alerts proactively

### 6. Reflection Loop with LLM
**Decision:** Use LLM-based reflection for output validation

**Rationale:**
- Catches semantic errors (not just schema)
- Enables self-correction without human intervention
- Improves over time with feedback
- Reduces hallucinations

**Impact:**
- Higher output quality (80%+ error detection)
- Fewer false positives in insights
- Builds user trust in AI recommendations

---

## Database Schema Overview

### New Schemas
- `orchestration` - Agent routing and execution
- `media` - Loom video processing

### New Tables (Migration 006)

**Orchestration Tables:**
- `orchestration.agent_graphs` - Graph definitions (20 columns)
- `orchestration.graph_executions` - Execution tracking (16 columns)
- `orchestration.node_execution_logs` - Node-level logs (14 columns)
- `orchestration.agent_feedback` - User feedback (11 columns)
- `orchestration.agent_training_examples` - Corrections (8 columns)
- `orchestration.intent_patterns` - Voice/text intents with embeddings (10 columns)
- `orchestration.routing_preferences` - Learned routing (9 columns)
- `orchestration.graph_states` - State checkpoints (5 columns)

**Media Tables:**
- `media.loom_videos` - Video metadata (11 columns)
- `media.loom_transcripts` - Extracted transcripts (4 columns)
- `media.loom_transcript_chunks` - Semantic chunks with embeddings (7 columns)
- `media.loom_summaries` - AI summaries (7 columns)

**Core Tables:**
- `core.discord_links` - Discord account links (9 columns)

### Vector Indexes
- `orchestration.intent_patterns.embedding` - For intent similarity search
- `media.loom_transcript_chunks.embedding` - For video content search

### Row-Level Security
All new tables have RLS policies enforcing workspace isolation using existing `auth.user_workspaces()` function.

---

## API Endpoints Summary

Total new endpoints: **10**

### Orchestration (4 endpoints)
1. `POST /api/v1/orchestration/graphs/execute` - Execute graph
2. `POST /api/v1/orchestration/graphs` - Create graph
3. `GET /api/v1/orchestration/executions/{request_id}` - Get execution status
4. `POST /api/v1/orchestration/feedback` - Submit feedback

### Voice (2 endpoints)
5. `POST /api/v1/voice/process` - Process voice command
6. `POST /api/v1/voice/synthesize` - Text-to-speech

### Loom (2 endpoints)
7. `POST /api/v1/videos/loom/process` - Submit video
8. `GET /api/v1/videos/loom/{video_id}/summary` - Get summary

### Discord (2 endpoints)
9. `POST /api/v1/discord/link` - Link Discord account
10. `GET /api/v1/discord/subscriptions` - Get subscriptions

---

## Implementation Plan

### Phase 1: Foundation (Week 1)
- Database migration 006
- Core models
- Agent registry and base agent interface

### Phase 2: Orchestration (Week 1-2)
- Routing engine with DAG execution
- Reflection agent
- Feedback system

### Phase 3: Specialized Agents (Week 2-3)
- ZeroBooks agent
- ZeroCRM agent
- ZeroSchedule agent
- Video summarizer agent
- Other agents (insight, briefing, task, comm)

### Phase 4: Voice Integration (Week 3)
- ZeroVoice connector
- Voice command processor
- API endpoints

### Phase 5: Loom Processing (Week 3-4)
- Loom connector updates
- Video processor
- Background tasks
- API endpoints

### Phase 6: Discord Bot (Week 4)
- Bot application
- Slash commands
- Scheduled delivery
- Webhook server

### Phase 7: API Endpoints (Week 4-5)
- Orchestration endpoints
- Voice endpoints
- Loom endpoints
- Discord endpoints

### Phase 8: Background Tasks (Week 5)
- Celery/APScheduler setup
- Cleanup tasks
- Briefing delivery
- Feedback learning

---

## Performance Targets

| Metric | Target | Notes |
|--------|--------|-------|
| Agent routing latency | < 500ms | Intent to agent selection |
| Voice command E2E | < 5 sec | Audio to final response |
| Loom video processing | < 5 min | For 30-minute video |
| Discord delivery | < 10 sec | Generation to delivery |
| Cross-agent chains | 3+ agents | Sequential or parallel |
| Feedback convergence | 7 days | To personalized routing |
| Reflection cycle | < 2 sec | Per agent output validation |
| Voice intent accuracy | > 95% | Correct agent routing |

---

## Security Considerations

### Data Isolation
- Row-Level Security (RLS) on all tables
- Workspace-scoped access via `auth.user_workspaces()`
- No cross-workspace data leakage

### API Security
- JWT authentication for all endpoints
- Workspace validation on every request
- Rate limiting on voice/video processing
- Webhook signature verification for Discord

### Voice Privacy
- Audio data not stored (processed in-memory)
- Transcripts encrypted at rest
- User can delete voice interaction history

### Discord Security
- Token-based account linking
- Ephemeral token display (invisible to others)
- User can unlink account anytime

---

## Monitoring & Observability

### Prometheus Metrics
```python
# Agent execution
agent_execution_duration_seconds{agent_type, status}
agent_execution_total{agent_type, status}

# Graph execution
graph_execution_duration_seconds{graph_id}
graph_execution_success_rate{graph_id}

# Voice processing
voice_command_processing_time{intent}
voice_intent_accuracy{intent}

# Loom processing
loom_video_processing_duration{video_duration_bucket}
loom_summary_generation_time

# Discord delivery
discord_briefing_delivery_time{briefing_type}
discord_command_latency{command}

# Feedback
feedback_submission_rate{feedback_type}
feedback_quality_improvement{agent_type}
```

### Health Checks
- `/health/orchestration` - Routing engine status
- `/health/voice` - ZeroVoice MCP connection
- `/health/loom` - Loom API connection
- `/health/discord` - Discord bot status

### Alerts
- Graph execution failure rate > 10%
- Voice processing latency > 10 seconds
- Loom processing failures > 5%
- Discord bot disconnected
- Feedback processing queue backed up

---

## Dependencies

### Python Packages (add to requirements.txt)
```
# Orchestration
networkx>=3.0
celery>=5.3.0
redis>=4.5.0

# Discord
discord.py>=2.3.0

# Voice processing
# (ZeroVoice MCP client - internal)

# LLM
langchain>=0.1.0
anthropic>=0.25.0

# Existing dependencies
fastapi
asyncpg
sqlalchemy
pydantic
```

### External Services
- **ZeroVoice MCP** - Voice transcription and synthesis
- **Loom API** - Video metadata and transcripts
- **Discord API** - Bot and webhooks
- **Redis** - Task queue for Celery
- **PostgreSQL with pgvector** - Vector similarity search

---

## Testing Coverage

### Unit Tests (15+ test files)
- Routing engine
- Reflection agent
- Each specialized agent (8 agents)
- Voice processor
- Loom processor
- Feedback learning
- Discord formatting

### Integration Tests (10+ test files)
- Voice to agent flow
- Loom end-to-end
- Discord commands
- Feedback learning
- Graph execution with real agents

### E2E Tests (5+ test files)
- Complete voice command flow
- Complete Loom processing flow
- Complete Discord briefing flow
- Multi-agent chain execution
- Reflection and self-correction

---

## Success Criteria

### Functional
- ✅ Agent routing graphs execute successfully
- ✅ Conditional routing works correctly
- ✅ Reflection catches and corrects errors
- ✅ Voice commands route to correct agents
- ✅ Loom videos summarized within target time
- ✅ Discord briefings deliver on schedule
- ✅ User feedback collected and applied

### Performance
- ✅ Agent routing < 500ms
- ✅ Voice E2E < 5 seconds
- ✅ Loom processing < 5 minutes
- ✅ Discord delivery < 10 seconds
- ✅ Support for 3+ agent chains

### Quality
- ✅ Voice intent accuracy > 95%
- ✅ Reflection error detection > 80%
- ✅ Feedback convergence within 7 days
- ✅ Zero cross-workspace data leakage

---

## Next Steps

1. **Review Architecture** - Team reviews all documents
2. **Approve & Prioritize** - Product owner approves scope
3. **Implementation Kickoff** - Begin Phase 1 (Foundation)
4. **Sprint Planning** - Break into 2-week sprints if needed
5. **Daily Progress** - Track against implementation checklist

---

## Document Inventory

### Created Documents (4 files)

1. **Main Architecture**
   - Path: `docs/sprint5_architecture.md`
   - Size: ~15 KB
   - Focus: System overview, graph routing, state management

2. **Orchestration Details**
   - Path: `docs/sprint5_orchestration_details.md`
   - Size: ~25 KB
   - Focus: Reflection, voice, video processing

3. **Discord & APIs**
   - Path: `docs/sprint5_discord_api_schemas.md`
   - Size: ~30 KB
   - Focus: Discord bot, API specs, database schema

4. **Implementation Guide**
   - Path: `docs/SPRINT5_IMPLEMENTATION_GUIDE.md`
   - Size: ~20 KB
   - Focus: Step-by-step implementation plan

5. **Architecture Summary** (this document)
   - Path: `docs/SPRINT5_ARCHITECTURE_SUMMARY.md`
   - Size: ~10 KB
   - Focus: High-level overview and quick reference

**Total Documentation:** ~100 KB, ~3,500 lines

---

## Conclusion

Sprint 5 architecture provides a **comprehensive, production-ready design** for:

1. **Multi-agent orchestration** with graph-based routing
2. **Self-correcting intelligence** via reflection loops
3. **Voice-first interaction** through ZeroVoice
4. **Async video collaboration** with Loom
5. **Discord delivery** of briefings and responses

The architecture is:
- **Scalable** - Event-driven, async-first
- **Secure** - RLS policies, workspace isolation
- **Extensible** - New agents easily added via registry
- **Observable** - Comprehensive metrics and logging
- **Well-documented** - 100 KB of detailed specifications

**Status:** Ready for implementation. Estimated timeline: 5 weeks with 2-3 engineers.

---

**Architecture Version:** 1.0
**Date:** 2025-11-05
**Author:** System Architect
**Status:** ✅ COMPLETE
