# Sprint 5: Implementation Guide

**Version:** 1.0
**Sprint:** 5 - Orchestration, Voice & Async Collaboration
**Status:** Architecture Complete - Ready for Implementation

---

## Overview

This guide provides step-by-step implementation instructions for Sprint 5 features based on the comprehensive architecture designed in:

- `/Users/aideveloper/Desktop/founderhouse-main/docs/sprint5_architecture.md`
- `/Users/aideveloper/Desktop/founderhouse-main/docs/sprint5_orchestration_details.md`
- `/Users/aideveloper/Desktop/founderhouse-main/docs/sprint5_discord_api_schemas.md`

---

## Implementation Checklist

### Phase 1: Foundation Setup (Week 1)

#### Database Migration
- [ ] Create `migrations/006_orchestration_voice.sql`
- [ ] Deploy schema to development environment
- [ ] Verify all tables and indexes created
- [ ] Test RLS policies with sample data
- [ ] Create seed data for agent graphs

**Files to create:**
- `migrations/006_orchestration_voice.sql` (copy from sprint5_discord_api_schemas.md)

#### Core Models
- [ ] Create `backend/app/models/agent_graph.py`
- [ ] Create `backend/app/models/graph_execution.py`
- [ ] Create `backend/app/models/agent_feedback.py`
- [ ] Create `backend/app/models/loom_video.py`
- [ ] Create `backend/app/models/discord_link.py`
- [ ] Update `backend/app/models/__init__.py`

**Example: `agent_graph.py`**
```python
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from uuid import UUID
from enum import Enum

class AgentType(str, Enum):
    ZEROBOOKS = "zerobooks"
    ZEROCRM = "zerocrm"
    ZEROSCHEDULE = "zeroschedule"
    VIDEO_SUMMARIZER = "video_summarizer"
    INSIGHT_GENERATOR = "insight_generator"
    BRIEFING_GENERATOR = "briefing_generator"
    TASK_ROUTER = "task_router"
    COMM_COMPOSER = "comm_composer"

class RoutingCondition(str, Enum):
    ALWAYS = "always"
    IF_SUCCESS = "if_success"
    IF_FAILURE = "if_failure"
    IF_CONDITION = "if_condition"
    PARALLEL = "parallel"

class AgentNodeDefinition(BaseModel):
    node_id: str
    agent_type: AgentType
    condition: RoutingCondition
    depends_on: List[str] = []
    timeout_seconds: int = 300
    retry_count: int = 3
    input_mapping: Dict[str, str]
    output_mapping: Dict[str, str]
    condition_expression: Optional[str] = None
    enable_reflection: bool = True
    reflection_prompt: Optional[str] = None

class AgentRoutingGraph(BaseModel):
    graph_id: UUID
    workspace_id: UUID
    name: str
    description: str
    nodes: List[AgentNodeDefinition]
    entry_node: str
    initial_state: Dict[str, Any] = {}
    created_at: str
    updated_at: str
    version: int = 1
```

---

### Phase 2: AgentFlow Orchestration (Week 1-2)

#### Agent Registry
- [ ] Create `backend/app/orchestration/agent_registry.py`
- [ ] Implement agent type to class mapping
- [ ] Add agent discovery mechanism

**File**: `backend/app/orchestration/agent_registry.py`
```python
from typing import Dict, Type
from app.orchestration.base_agent import BaseAgent
from app.models.agent_graph import AgentType

class AgentRegistry:
    """Central registry for all agents"""

    _agents: Dict[AgentType, Type[BaseAgent]] = {}

    @classmethod
    def register(cls, agent_type: AgentType):
        """Decorator to register an agent"""
        def wrapper(agent_class: Type[BaseAgent]):
            cls._agents[agent_type] = agent_class
            return agent_class
        return wrapper

    @classmethod
    def get_agent(cls, agent_type: AgentType) -> BaseAgent:
        """Get agent instance by type"""
        agent_class = cls._agents.get(agent_type)
        if not agent_class:
            raise ValueError(f"No agent registered for type: {agent_type}")
        return agent_class()

    @classmethod
    def list_agents(cls) -> List[AgentType]:
        """List all registered agent types"""
        return list(cls._agents.keys())
```

#### Base Agent Interface
- [ ] Create `backend/app/orchestration/base_agent.py`
- [ ] Define abstract methods all agents must implement

**File**: `backend/app/orchestration/base_agent.py`
```python
from abc import ABC, abstractmethod
from typing import Dict, Any
from uuid import UUID

class BaseAgent(ABC):
    """Base class for all specialized agents"""

    @abstractmethod
    async def execute(
        self,
        workspace_id: UUID,
        founder_id: UUID,
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute agent logic

        Args:
            workspace_id: Workspace context
            founder_id: Founder context
            input_data: Input parameters

        Returns:
            Agent output dictionary
        """
        pass

    @abstractmethod
    def get_output_schema(self) -> Dict[str, Any]:
        """Return expected output schema"""
        pass

    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """Validate input data"""
        return True
```

#### Routing Engine
- [ ] Create `backend/app/orchestration/routing_engine.py`
- [ ] Implement DAG building and execution
- [ ] Add state management
- [ ] Implement retry logic

**Key methods to implement:**
- `build_dag(graph)` - Convert graph to NetworkX DAG
- `execute_graph(graph, founder_id, request_id)` - Main execution loop
- `should_execute_node(node_def, state)` - Conditional logic
- `execute_agent_node(node_def, state)` - Single agent execution

#### Reflection Agent
- [ ] Create `backend/app/orchestration/reflection_agent.py`
- [ ] Implement output validation
- [ ] Implement self-correction loop
- [ ] Add hallucination detection

**Key methods:**
- `validate_and_correct(agent_type, input, output, context)`
- `validate_output(agent_type, output, input, context)`
- `detect_hallucinations(output, input, context)`
- `self_correct(agent_type, input, flawed_output, issues)`

#### Feedback System
- [ ] Create `backend/app/orchestration/feedback_collector.py`
- [ ] Create `backend/app/orchestration/learning_engine.py`
- [ ] Implement feedback storage
- [ ] Implement routing optimization

---

### Phase 3: Specialized Agents (Week 2-3)

#### ZeroBooks Agent
- [ ] Create `backend/app/agents/zerobooks_agent.py`
- [ ] Integrate with ZeroBooks MCP connector
- [ ] Implement financial query logic
- [ ] Add output schema definition

**Example structure:**
```python
from app.orchestration.base_agent import BaseAgent
from app.orchestration.agent_registry import AgentRegistry
from app.models.agent_graph import AgentType

@AgentRegistry.register(AgentType.ZEROBOOKS)
class ZeroBooksAgent(BaseAgent):
    async def execute(self, workspace_id, founder_id, input_data):
        # Get ZeroBooks connector
        connector = get_mcp_client('zerobooks')

        # Extract query parameters
        query = input_data.get('query')
        date_range = input_data.get('date_range')

        # Call ZeroBooks API
        result = await connector.call_tool(
            name='zerobooks.get_financials',
            arguments={
                'workspace_id': str(workspace_id),
                'query': query,
                'start_date': date_range['start'],
                'end_date': date_range['end']
            }
        )

        return {
            'financial_data': result.get('data'),
            'period': date_range,
            'metrics': result.get('metrics')
        }

    def get_output_schema(self):
        return {
            'required': ['financial_data', 'period'],
            'properties': {
                'financial_data': {'type': 'dict'},
                'period': {'type': 'dict'},
                'metrics': {'type': 'dict'}
            }
        }
```

#### Other Agents to Implement
- [ ] `backend/app/agents/zerocrm_agent.py` - CRM queries
- [ ] `backend/app/agents/zeroschedule_agent.py` - Calendar operations
- [ ] `backend/app/agents/video_summarizer_agent.py` - Loom processing
- [ ] `backend/app/agents/insight_generator_agent.py` - Use existing insights service
- [ ] `backend/app/agents/briefing_generator_agent.py` - Use existing briefing service
- [ ] `backend/app/agents/task_router_agent.py` - Task creation/routing
- [ ] `backend/app/agents/comm_composer_agent.py` - Email/message drafting

---

### Phase 4: Voice Command Integration (Week 3)

#### ZeroVoice Connector
- [ ] Create `backend/app/connectors/zerovoice_connector.py` (if not exists)
- [ ] Implement speech-to-text
- [ ] Implement text-to-speech
- [ ] Add intent classification

#### Voice Processor
- [ ] Create `backend/app/services/voice_command_processor.py`
- [ ] Implement voice command pipeline
- [ ] Add intent extraction
- [ ] Integrate with AgentFlow

#### API Endpoints
- [ ] Add `POST /api/v1/voice/process` endpoint
- [ ] Add `POST /api/v1/voice/synthesize` endpoint
- [ ] Add WebSocket endpoint for streaming

**File**: `backend/app/api/v1/voice.py`
```python
from fastapi import APIRouter, UploadFile, File, Depends
from app.services.voice_command_processor import VoiceCommandProcessor

router = APIRouter(prefix="/voice", tags=["voice"])

@router.post("/process")
async def process_voice_command(
    audio: UploadFile = File(...),
    workspace_id: UUID = Depends(get_workspace_id),
    founder_id: UUID = Depends(get_founder_id)
):
    """Process voice command"""
    processor = VoiceCommandProcessor()

    audio_data = await audio.read()

    result = await processor.process_voice_command(
        audio_stream=audio_data,
        founder_id=founder_id,
        workspace_id=workspace_id
    )

    return result
```

---

### Phase 5: Loom Video Processing (Week 3-4)

#### Loom Connector
- [ ] Update `backend/app/connectors/loom_connector.py`
- [ ] Add video metadata fetching
- [ ] Add transcript extraction

#### Video Processor
- [ ] Create `backend/app/services/loom_video_processor.py`
- [ ] Implement video ingestion pipeline
- [ ] Add transcript chunking
- [ ] Implement summarization
- [ ] Add action item extraction

#### Background Tasks
- [ ] Create `backend/app/tasks/video_processing.py`
- [ ] Add Celery/APScheduler task for async processing
- [ ] Implement job status tracking

**File**: `backend/app/tasks/video_processing.py`
```python
from celery import shared_task
from app.services.loom_video_processor import LoomVideoProcessor

@shared_task
def process_loom_video_task(
    video_url: str,
    workspace_id: str,
    founder_id: str,
    requested_by: str
):
    """Background task to process Loom video"""
    processor = LoomVideoProcessor()

    result = await processor.process_loom_video(
        video_url=video_url,
        workspace_id=UUID(workspace_id),
        founder_id=UUID(founder_id),
        requested_by=UUID(requested_by)
    )

    return result
```

#### API Endpoints
- [ ] Add `POST /api/v1/videos/loom/process` endpoint
- [ ] Add `GET /api/v1/videos/loom/{video_id}/summary` endpoint
- [ ] Add job status endpoint

---

### Phase 6: Discord Bot (Week 4)

#### Bot Application
- [ ] Create `backend/discord_bot/bot.py`
- [ ] Implement slash commands
- [ ] Add scheduled briefing delivery
- [ ] Implement rich embeds

#### Commands to Implement
- [ ] `/brief` - Get briefing (morning/evening/investor)
- [ ] `/ask` - Query AI Chief of Staff
- [ ] `/kpis` - View metrics
- [ ] `/schedule` - View calendar
- [ ] `/setup` - Link Discord account

#### Webhook Server
- [ ] Create `backend/discord_bot/webhook_server.py`
- [ ] Add backend-to-Discord message delivery
- [ ] Implement signature verification

#### Deployment
- [ ] Set up Discord application in Discord Developer Portal
- [ ] Configure bot permissions
- [ ] Deploy bot to server
- [ ] Set up monitoring

---

### Phase 7: API Endpoints (Week 4-5)

#### Orchestration Endpoints
- [ ] `POST /api/v1/orchestration/graphs/execute`
- [ ] `POST /api/v1/orchestration/graphs`
- [ ] `GET /api/v1/orchestration/executions/{request_id}`
- [ ] `POST /api/v1/orchestration/feedback`

**File**: `backend/app/api/v1/orchestration.py`
```python
from fastapi import APIRouter, Depends, HTTPException
from app.orchestration.routing_engine import AgentRoutingEngine
from app.models.agent_graph import AgentRoutingGraph

router = APIRouter(prefix="/orchestration", tags=["orchestration"])

@router.post("/graphs/execute")
async def execute_agent_graph(
    request: GraphExecutionRequest,
    workspace_id: UUID = Depends(get_workspace_id),
    founder_id: UUID = Depends(get_founder_id)
):
    """Execute agent routing graph"""

    # Load graph
    graph = await get_agent_graph(request.graph_id)

    # Execute
    engine = AgentRoutingEngine()
    result = await engine.execute_graph(
        graph=graph,
        founder_id=founder_id,
        request_id=uuid.uuid4()
    )

    return {
        "request_id": str(request_id),
        "status": "completed",
        "final_state": result
    }
```

#### Discord Endpoints
- [ ] `POST /api/v1/discord/link`
- [ ] `GET /api/v1/discord/subscriptions`
- [ ] `POST /api/v1/discord/webhook/message`

---

### Phase 8: Background Tasks (Week 5)

#### Task Scheduler Setup
- [ ] Configure Celery or APScheduler
- [ ] Set up Redis for task queue
- [ ] Configure beat schedule

#### Scheduled Tasks
- [ ] Create `backend/app/tasks/orchestration_cleanup.py`
  - Clean up old execution logs
  - Archive completed graph states

- [ ] Create `backend/app/tasks/discord_briefing_delivery.py`
  - Check for scheduled briefings
  - Deliver at user's local time

- [ ] Create `backend/app/tasks/feedback_learning.py`
  - Process feedback queue
  - Update routing preferences
  - Refine agent prompts

**Example task:**
```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

@scheduler.scheduled_job('cron', hour='*/1')  # Every hour
async def check_discord_briefings():
    """Check and deliver scheduled Discord briefings"""
    # Implementation from sprint5_discord_api_schemas.md
    pass

scheduler.start()
```

---

## Testing Strategy

### Unit Tests

#### Test Files to Create
- [ ] `tests/unit/test_routing_engine.py`
- [ ] `tests/unit/test_reflection_agent.py`
- [ ] `tests/unit/test_zerobooks_agent.py`
- [ ] `tests/unit/test_voice_processor.py`
- [ ] `tests/unit/test_loom_processor.py`

**Example: `test_routing_engine.py`**
```python
import pytest
from app.orchestration.routing_engine import AgentRoutingEngine
from app.models.agent_graph import AgentRoutingGraph, AgentNodeDefinition

@pytest.mark.asyncio
async def test_simple_graph_execution():
    """Test execution of a simple 2-node graph"""

    graph = AgentRoutingGraph(
        graph_id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        name="Test Graph",
        description="Simple test",
        nodes=[
            AgentNodeDefinition(
                node_id="node1",
                agent_type=AgentType.ZEROBOOKS,
                condition=RoutingCondition.ALWAYS,
                depends_on=[],
                input_mapping={"query": "state.query"},
                output_mapping={"result": "state.result"}
            ),
            AgentNodeDefinition(
                node_id="node2",
                agent_type=AgentType.INSIGHT_GENERATOR,
                condition=RoutingCondition.IF_SUCCESS,
                depends_on=["node1"],
                input_mapping={"data": "state.result"},
                output_mapping={"insights": "state.insights"}
            )
        ],
        entry_node="node1",
        initial_state={"query": "revenue this month"}
    )

    engine = AgentRoutingEngine()
    result = await engine.execute_graph(
        graph=graph,
        founder_id=uuid.uuid4(),
        request_id=uuid.uuid4()
    )

    assert "insights" in result
```

### Integration Tests

- [ ] `tests/integration/test_voice_to_agent_flow.py`
- [ ] `tests/integration/test_loom_end_to_end.py`
- [ ] `tests/integration/test_discord_commands.py`
- [ ] `tests/integration/test_feedback_learning.py`

### E2E Tests

- [ ] `tests/e2e/test_voice_command_complete_flow.py`
  - Record voice → Process → Execute agents → Get response

- [ ] `tests/e2e/test_loom_video_summary_flow.py`
  - Submit video URL → Process → Extract transcript → Summarize

- [ ] `tests/e2e/test_discord_briefing_flow.py`
  - Generate briefing → Format → Deliver to Discord → Verify receipt

---

## Deployment Checklist

### Environment Setup
- [ ] Add environment variables:
  - `ZEROVOICE_API_KEY`
  - `LOOM_API_KEY`
  - `DISCORD_BOT_TOKEN`
  - `DISCORD_WEBHOOK_SECRET`
  - `CELERY_BROKER_URL`
  - `CELERY_RESULT_BACKEND`

### Database
- [ ] Run migration 006 in staging
- [ ] Verify all tables created
- [ ] Test RLS policies
- [ ] Run migration 006 in production

### Services
- [ ] Deploy updated FastAPI backend
- [ ] Deploy Discord bot application
- [ ] Deploy Celery workers
- [ ] Deploy Celery beat scheduler

### Monitoring
- [ ] Set up logging for orchestration events
- [ ] Add Prometheus metrics:
  - `agent_execution_duration_seconds`
  - `graph_execution_success_rate`
  - `voice_command_processing_time`
  - `loom_video_processing_duration`
- [ ] Configure alerts for failures

### Documentation
- [ ] Update API documentation (OpenAPI/Swagger)
- [ ] Create user guide for Discord bot
- [ ] Document voice command syntax
- [ ] Create admin guide for graph management

---

## Success Criteria

### Functional Requirements
- [ ] Agent routing graphs execute successfully
- [ ] Conditional routing works correctly
- [ ] Reflection catches and corrects errors
- [ ] Voice commands route to correct agents
- [ ] Loom videos are summarized within 5 minutes
- [ ] Discord briefings deliver on schedule
- [ ] User feedback is collected and applied

### Performance Requirements
- [ ] Agent routing latency < 500ms
- [ ] Voice command end-to-end < 5 seconds
- [ ] Loom processing < 5 minutes for 30-min video
- [ ] Discord delivery < 10 seconds
- [ ] Graph execution supports 3+ agent chains

### Quality Requirements
- [ ] Voice intent accuracy > 95%
- [ ] Reflection catches > 80% of errors
- [ ] Feedback convergence within 7 days
- [ ] Zero data leakage between workspaces (RLS)

---

## Troubleshooting Guide

### Common Issues

**Issue: Graph execution hangs**
- Check: Node timeouts configured correctly
- Check: No circular dependencies in graph
- Check: All dependent agents are registered

**Issue: Voice commands not routing correctly**
- Check: Intent patterns seeded in database
- Check: Vector embeddings generated
- Check: Similarity threshold appropriate (0.85)

**Issue: Discord bot not delivering briefings**
- Check: User timezone configured correctly
- Check: Scheduled task running (APScheduler/Celery)
- Check: Discord user linked to workspace

**Issue: Loom videos failing to process**
- Check: Loom API credentials valid
- Check: Video is accessible (not private)
- Check: Celery worker running
- Check: Redis connection established

---

## Additional Resources

### Architecture Documents
1. Main Architecture: `docs/sprint5_architecture.md`
2. Orchestration Details: `docs/sprint5_orchestration_details.md`
3. Discord & APIs: `docs/sprint5_discord_api_schemas.md`

### Code References
- Existing connectors: `backend/app/connectors/`
- Existing services: `backend/app/services/`
- Existing models: `backend/app/models/`
- Migration patterns: `migrations/001_initial_schema.sql`

### External Documentation
- Discord.py: https://discordpy.readthedocs.io/
- LangChain: https://python.langchain.com/docs/
- NetworkX: https://networkx.org/documentation/
- Celery: https://docs.celeryproject.org/

---

**Implementation Guide Version:** 1.0
**Last Updated:** 2025-11-05
**Status:** Ready for Development
