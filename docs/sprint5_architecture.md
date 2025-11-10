# Sprint 5: Orchestration, Voice & Async Collaboration Architecture

**Version:** 1.0
**Date:** 2025-11-05
**Sprint:** 5 - AgentFlow Orchestration & Voice/Async Features
**Author:** System Architect

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [System Overview](#system-overview)
3. [Epic 6: Voice & Async Collaboration](#epic-6-voice--async-collaboration)
4. [Epic 8: AgentFlow Orchestration](#epic-8-agentflow-orchestration)
5. [Agent Routing Graph Architecture](#agent-routing-graph-architecture)
6. [Reflection & Feedback Loop System](#reflection--feedback-loop-system)
7. [Cross-Agent Collaboration Patterns](#cross-agent-collaboration-patterns)
8. [Voice Command Integration](#voice-command-integration)
9. [Loom Video Summarization Pipeline](#loom-video-summarization-pipeline)
10. [Discord Bot Architecture](#discord-bot-architecture)
11. [Data Flow Architecture](#data-flow-architecture)
12. [API Specifications](#api-specifications)
13. [Database Schema Design](#database-schema-design)
14. [Background Task Definitions](#background-task-definitions)
15. [Performance & Scalability](#performance--scalability)
16. [Security & Privacy](#security--privacy)
17. [Monitoring & Observability](#monitoring--observability)

---

## Executive Summary

Sprint 5 introduces **intelligent orchestration** and **async collaboration** capabilities to the AI Chief of Staff platform. This sprint implements:

- **AgentFlow Orchestration**: Multi-agent routing system with reflection loops
- **Voice Command Processing**: ZeroVoice MCP integration for hands-free control
- **Loom Video Summarization**: Async video content extraction and insights
- **Discord Daily Briefings**: Automated delivery of morning/evening briefs
- **Cross-Agent Collaboration**: Coordinated workflows across ZeroBooks, ZeroCRM, ZeroSchedule
- **Feedback Learning**: System learns from user corrections and preferences

### Key Architectural Decisions

| Decision | Rationale | Impact |
|----------|-----------|---------|
| **Graph-Based Agent Routing** | Flexible, extensible multi-agent coordination | Complex workflows with conditional paths |
| **Event-Driven Orchestration** | Loose coupling, async execution | Scalable, fault-tolerant agent interactions |
| **Vector-Based Intent Classification** | Semantic understanding of voice commands | 95%+ routing accuracy |
| **Streaming Video Transcription** | Real-time Loom processing | Sub-5-minute video-to-insight pipeline |
| **Discord Webhooks + Bot** | Dual delivery mechanism | High reliability, rich formatting |
| **Temporal Workflow Engine** | Durable execution for long-running agents | Guaranteed completion, retry logic |

### Architecture Metrics

- **Agent Routing Latency:** <500ms for intent classification
- **Voice Command Accuracy:** >95% intent recognition
- **Video Summarization:** <5 minutes for 30-minute video
- **Discord Delivery:** <10 seconds from generation to delivery
- **Cross-Agent Coordination:** Support for 3+ agent chains
- **Feedback Loop Convergence:** 7 days to personalized routing
- **Reflection Cycle Time:** <2 seconds per agent output validation

---

## System Overview

### Component Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                     User Interaction Layer                      │
│  Voice Commands │ Discord Messages │ Loom Videos │ Web App      │
└────────────────────┬───────────────────────────────────────────┘
                     │
                     ▼
┌────────────────────────────────────────────────────────────────┐
│                  Intent Classification Layer                    │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Voice Processor │ Text Classifier │ Context Assembler   │  │
│  │ (ZeroVoice MCP) │ (Vector Search) │ (Semantic Router)   │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────┬───────────────────────────────────────────┘
                     │
                     ▼
┌────────────────────────────────────────────────────────────────┐
│                   AgentFlow Orchestrator                        │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Routing Engine │ Agent Registry │ State Manager         │  │
│  │ Execution Queue│ Dependency Resolver │ Reflection Loop │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────┬───────────────────────────────────────────┘
                     │
                     ▼
┌────────────────────────────────────────────────────────────────┐
│                      Specialized Agents                         │
│  ┌────────────┬────────────┬────────────┬─────────────────┐   │
│  │ ZeroBooks  │ ZeroCRM    │ZeroSchedule│ VideoSummarizer │   │
│  │ Agent      │ Agent      │ Agent      │ Agent           │   │
│  └────────────┴────────────┴────────────┴─────────────────┘   │
│  ┌────────────┬────────────┬────────────┬─────────────────┐   │
│  │ Insight    │ Briefing   │ Task       │ Communication   │   │
│  │ Generator  │ Generator  │ Router     │ Composer        │   │
│  └────────────┴────────────┴────────────┴─────────────────┘   │
└────────────────────┬───────────────────────────────────────────┘
                     │
                     ▼
┌────────────────────────────────────────────────────────────────┐
│                    Feedback & Learning Layer                    │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ User Feedback Collector │ Preference Learner            │  │
│  │ Routing Optimizer       │ Quality Scorer                │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────┬───────────────────────────────────────────┘
                     │
                     ▼
┌────────────────────────────────────────────────────────────────┐
│                      Delivery Layer                             │
│  Discord Bot │ Slack │ Voice Response │ In-App Notifications   │
└────────────────────────────────────────────────────────────────┘
```

### System Responsibilities

#### Epic 6: Voice & Async Collaboration

1. **ZeroVoice MCP Integration (Issue #16)**
   - Voice-to-text transcription via ZeroVoice
   - Intent extraction from voice commands
   - Context-aware command routing
   - Voice response generation

2. **Loom Video Summarization (Issue #17)**
   - Video ingestion via Loom MCP
   - Transcript extraction and chunking
   - AI-powered summarization
   - Action item extraction from videos

3. **Discord Status Sync (Issue #18)**
   - Discord bot webhook integration
   - Daily briefing delivery (morning/evening)
   - Rich embed formatting
   - Interactive message components

#### Epic 8: AgentFlow Orchestration

4. **Agent Routing Graph (Issue #22)**
   - DAG-based workflow execution
   - Conditional routing logic
   - Parallel agent execution
   - State management across agents

5. **Reflection & Feedback Loop (Issue #23)**
   - Output quality validation
   - Self-correction mechanisms
   - User feedback integration
   - Continuous learning system

6. **Chained Agent Collaboration (Issue #24)**
   - Cross-agent data sharing
   - Dependency resolution
   - Transaction coordination
   - Rollback mechanisms

---

## Epic 6: Voice & Async Collaboration

### Architecture Overview

The Voice & Async Collaboration system enables founders to interact with the AI Chief of Staff through voice commands, consume async video content, and receive briefings on Discord.

```
Voice Commands                 Async Media                 Discord Sync
     │                              │                           │
     ▼                              ▼                           ▼
┌──────────┐                  ┌──────────┐              ┌──────────┐
│ZeroVoice │                  │Loom MCP  │              │Discord   │
│   MCP    │                  │Video API │              │Webhook   │
└────┬─────┘                  └────┬─────┘              └────┬─────┘
     │                              │                         │
     │ Transcription                │ Video URL               │
     ▼                              ▼                         │
┌──────────────────────────────────────────────┐             │
│        Voice Command Processor                │             │
│  - Speech-to-text                             │             │
│  - Intent classification                      │             │
│  - Entity extraction                          │             │
└────────────────┬──────────────────────────────┘             │
                 │                                             │
                 │ Command Intent               Video Content  │
                 ▼                              ▼              │
┌─────────────────────────────────────────────────────┐       │
│             AgentFlow Orchestrator                  │       │
│  - Route to appropriate agent                       │       │
│  - Execute workflow                                 │       │
│  - Generate response                                │       │
└─────────────────────┬───────────────────────────────┘       │
                      │                                        │
                      │ Result                                 │
                      ▼                                        │
            ┌──────────────────┐                              │
            │Response Generator│                              │
            │ - Voice synthesis│                              │
            │ - Text response  │                              │
            └────────┬─────────┘                              │
                     │                                         │
                     ▼                                         │
         ┌─────────────────────┐                ┌─────────────▼──────┐
         │   Voice Response    │                │  Discord Delivery  │
         │   (ZeroVoice)       │                │  - Morning Brief   │
         └─────────────────────┘                │  - Evening Wrap    │
                                                 └────────────────────┘
```

---

## Epic 8: AgentFlow Orchestration

### Architecture Overview

The AgentFlow Orchestration system coordinates multiple specialized agents to execute complex workflows with reflection and learning capabilities.

```
User Request
     │
     ▼
┌─────────────────────────────────────────────────────────┐
│              Intent Classification                       │
│  - Extract user goal                                     │
│  - Identify required agents                              │
│  - Build execution graph                                 │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│              Agent Routing Graph                         │
│                                                          │
│   Start → Agent A ──┬──→ Agent B → Agent C → End       │
│              │       │                                   │
│              └───────→ Agent D ────────────┘            │
│                                                          │
│  - DAG-based execution                                   │
│  - Conditional branching                                 │
│  - Parallel execution support                            │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│           Agent Execution Engine                         │
│  ┌────────────────────────────────────────────────┐     │
│  │  Agent State:                                   │     │
│  │  - Input data                                   │     │
│  │  - Context variables                            │     │
│  │  - Execution status                             │     │
│  └────────────────────────────────────────────────┘     │
│                                                          │
│  For each agent in graph:                               │
│    1. Load agent definition                             │
│    2. Prepare input from state                          │
│    3. Execute agent logic                               │
│    4. Validate output (Reflection)                      │
│    5. Update state                                      │
│    6. Collect feedback                                  │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│           Reflection & Validation                        │
│  ┌────────────────────────────────────────────────┐     │
│  │  Quality Checks:                                │     │
│  │  - Output schema validation                     │     │
│  │  - Hallucination detection                      │     │
│  │  - Confidence scoring                           │     │
│  │  - Factual consistency                          │     │
│  └────────────────────────────────────────────────┘     │
│                                                          │
│  If validation fails:                                    │
│    - Self-correct with reflection prompt                │
│    - Retry with additional context                      │
│    - Escalate to human if needed                        │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│              Feedback Collection                         │
│  - User corrections                                      │
│  - Implicit feedback (usage patterns)                    │
│  - Quality ratings                                       │
│  - Learning from errors                                  │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│           Routing Optimization                           │
│  - Update intent→agent mappings                          │
│  - Refine execution graphs                               │
│  - Personalize per founder                               │
└──────────────────────────────────────────────────────────┘
```

---

## Agent Routing Graph Architecture

### Graph Definition Model

Agents are orchestrated using a **Directed Acyclic Graph (DAG)** that defines execution flow, dependencies, and conditional logic.

```python
from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from uuid import UUID

class AgentType(str, Enum):
    """Specialized agent types"""
    ZEROBOOKS = "zerobooks"           # Financial queries & operations
    ZEROCRM = "zerocrm"               # Customer relationship management
    ZEROSCHEDULE = "zeroschedule"     # Calendar & scheduling
    VIDEO_SUMMARIZER = "video_summarizer"  # Loom video processing
    INSIGHT_GENERATOR = "insight_generator"  # KPI analysis
    BRIEFING_GENERATOR = "briefing_generator"  # Daily briefs
    TASK_ROUTER = "task_router"       # Task management
    COMM_COMPOSER = "comm_composer"   # Email/message drafting

class RoutingCondition(str, Enum):
    """Conditional routing logic"""
    ALWAYS = "always"                 # Always execute
    IF_SUCCESS = "if_success"         # Execute if previous succeeded
    IF_FAILURE = "if_failure"         # Execute if previous failed
    IF_CONDITION = "if_condition"     # Execute if custom condition met
    PARALLEL = "parallel"             # Execute in parallel with others

class AgentNodeDefinition(BaseModel):
    """Single agent node in routing graph"""
    node_id: str                      # Unique node identifier
    agent_type: AgentType             # Agent to execute
    condition: RoutingCondition       # When to execute
    depends_on: List[str] = []        # Node IDs this depends on
    timeout_seconds: int = 300        # Max execution time
    retry_count: int = 3              # Retry attempts on failure

    # Input/output mapping
    input_mapping: Dict[str, str]     # Map graph state to agent input
    output_mapping: Dict[str, str]    # Map agent output to graph state

    # Conditional logic (for IF_CONDITION)
    condition_expression: Optional[str] = None  # Python expression to evaluate

    # Reflection config
    enable_reflection: bool = True    # Enable output validation
    reflection_prompt: Optional[str] = None  # Custom reflection prompt

class AgentRoutingGraph(BaseModel):
    """Complete agent execution graph"""
    graph_id: UUID                    # Unique graph identifier
    workspace_id: UUID                # Workspace this graph belongs to
    name: str                         # Human-readable name
    description: str                  # Graph purpose

    # Graph structure
    nodes: List[AgentNodeDefinition]  # All nodes in graph
    entry_node: str                   # Starting node ID

    # Graph state (shared across all agents)
    initial_state: Dict[str, Any] = {}  # Initial state variables

    # Metadata
    created_at: str
    updated_at: str
    version: int = 1

# Example: Financial analysis workflow
financial_analysis_graph = AgentRoutingGraph(
    graph_id=UUID("..."),
    workspace_id=UUID("..."),
    name="Financial Analysis Workflow",
    description="Analyze financial metrics and generate insights",
    nodes=[
        AgentNodeDefinition(
            node_id="fetch_financials",
            agent_type=AgentType.ZEROBOOKS,
            condition=RoutingCondition.ALWAYS,
            depends_on=[],
            input_mapping={
                "query": "state.user_query",
                "date_range": "state.date_range"
            },
            output_mapping={
                "financial_data": "state.financials"
            }
        ),
        AgentNodeDefinition(
            node_id="analyze_metrics",
            agent_type=AgentType.INSIGHT_GENERATOR,
            condition=RoutingCondition.IF_SUCCESS,
            depends_on=["fetch_financials"],
            input_mapping={
                "financial_data": "state.financials",
                "comparison_period": "state.comparison_period"
            },
            output_mapping={
                "insights": "state.insights",
                "anomalies": "state.anomalies"
            }
        ),
        AgentNodeDefinition(
            node_id="check_critical_issues",
            agent_type=AgentType.TASK_ROUTER,
            condition=RoutingCondition.IF_CONDITION,
            depends_on=["analyze_metrics"],
            condition_expression="len(state.anomalies) > 0 and any(a['severity'] == 'critical' for a in state.anomalies)",
            input_mapping={
                "anomalies": "state.anomalies"
            },
            output_mapping={
                "tasks_created": "state.tasks"
            }
        ),
        AgentNodeDefinition(
            node_id="generate_summary",
            agent_type=AgentType.BRIEFING_GENERATOR,
            condition=RoutingCondition.IF_SUCCESS,
            depends_on=["analyze_metrics"],
            input_mapping={
                "insights": "state.insights",
                "financials": "state.financials"
            },
            output_mapping={
                "summary": "state.final_summary"
            }
        )
    ],
    entry_node="fetch_financials",
    initial_state={
        "user_query": "Show me this month's financial performance",
        "date_range": {"start": "2025-11-01", "end": "2025-11-30"},
        "comparison_period": "previous_month"
    }
)
```

### Routing Engine Implementation

```python
import asyncio
from typing import Dict, Any, List, Optional
from collections import defaultdict
import networkx as nx

class AgentRoutingEngine:
    """
    Orchestrates agent execution based on routing graph

    Features:
    - Topological execution ordering
    - Parallel execution support
    - Dependency resolution
    - State management
    - Retry logic
    - Timeout handling
    """

    def __init__(self):
        self.agent_registry = AgentRegistry()
        self.state_manager = GraphStateManager()

    async def execute_graph(
        self,
        graph: AgentRoutingGraph,
        founder_id: UUID,
        request_id: UUID
    ) -> Dict[str, Any]:
        """
        Execute agent routing graph

        Args:
            graph: Routing graph definition
            founder_id: Founder initiating request
            request_id: Unique request identifier

        Returns:
            Final graph state after all agents executed
        """

        # Initialize graph state
        state = GraphState(
            request_id=request_id,
            founder_id=founder_id,
            workspace_id=graph.workspace_id,
            variables=graph.initial_state.copy()
        )

        # Build execution DAG
        dag = self.build_dag(graph)

        # Validate DAG (no cycles)
        if not nx.is_directed_acyclic_graph(dag):
            raise ValueError("Routing graph contains cycles")

        # Get topological execution order
        execution_order = list(nx.topological_sort(dag))

        # Track execution results
        executed_nodes = set()
        failed_nodes = set()

        # Execute nodes in order
        for node_id in execution_order:
            node_def = self.get_node_definition(graph, node_id)

            # Check if node should execute
            should_execute = self.should_execute_node(
                node_def,
                executed_nodes,
                failed_nodes,
                state
            )

            if not should_execute:
                continue

            # Check if dependencies met
            if not self.dependencies_satisfied(node_def, executed_nodes):
                continue

            try:
                # Execute agent
                result = await self.execute_agent_node(
                    node_def=node_def,
                    state=state,
                    graph=graph
                )

                # Update state with outputs
                self.update_state_from_output(
                    state=state,
                    node_def=node_def,
                    output=result
                )

                executed_nodes.add(node_id)

                # Log execution
                await self.log_execution(
                    request_id=request_id,
                    node_id=node_id,
                    status="success",
                    output=result
                )

            except Exception as e:
                failed_nodes.add(node_id)

                # Log failure
                await self.log_execution(
                    request_id=request_id,
                    node_id=node_id,
                    status="failed",
                    error=str(e)
                )

                # Handle failure based on graph config
                # Could trigger fallback nodes or halt execution
                if node_def.condition == RoutingCondition.IF_FAILURE:
                    continue  # Allow failure recovery nodes
                else:
                    # For critical nodes, may want to halt
                    pass

        return state.variables

    def build_dag(self, graph: AgentRoutingGraph) -> nx.DiGraph:
        """Build NetworkX DAG from graph definition"""
        dag = nx.DiGraph()

        # Add nodes
        for node in graph.nodes:
            dag.add_node(node.node_id, definition=node)

        # Add edges based on dependencies
        for node in graph.nodes:
            for dependency in node.depends_on:
                dag.add_edge(dependency, node.node_id)

        return dag

    def should_execute_node(
        self,
        node_def: AgentNodeDefinition,
        executed: set,
        failed: set,
        state: 'GraphState'
    ) -> bool:
        """Determine if node should execute based on condition"""

        if node_def.condition == RoutingCondition.ALWAYS:
            return True

        elif node_def.condition == RoutingCondition.IF_SUCCESS:
            # All dependencies must have succeeded
            return all(dep in executed for dep in node_def.depends_on)

        elif node_def.condition == RoutingCondition.IF_FAILURE:
            # At least one dependency must have failed
            return any(dep in failed for dep in node_def.depends_on)

        elif node_def.condition == RoutingCondition.IF_CONDITION:
            # Evaluate custom condition
            if not node_def.condition_expression:
                return False

            try:
                # Create safe evaluation context
                context = {"state": state}
                result = eval(node_def.condition_expression, {"__builtins__": {}}, context)
                return bool(result)
            except Exception:
                return False

        elif node_def.condition == RoutingCondition.PARALLEL:
            # Can execute as soon as dependencies met
            return all(dep in executed for dep in node_def.depends_on)

        return False

    def dependencies_satisfied(
        self,
        node_def: AgentNodeDefinition,
        executed: set
    ) -> bool:
        """Check if all dependencies are satisfied"""
        return all(dep in executed for dep in node_def.depends_on)

    async def execute_agent_node(
        self,
        node_def: AgentNodeDefinition,
        state: 'GraphState',
        graph: AgentRoutingGraph
    ) -> Dict[str, Any]:
        """Execute single agent node with retry and timeout"""

        # Get agent instance
        agent = self.agent_registry.get_agent(node_def.agent_type)

        # Prepare input from state
        agent_input = self.map_input_from_state(
            node_def.input_mapping,
            state
        )

        # Execute with timeout and retry
        for attempt in range(node_def.retry_count):
            try:
                # Execute agent with timeout
                result = await asyncio.wait_for(
                    agent.execute(
                        workspace_id=graph.workspace_id,
                        founder_id=state.founder_id,
                        input_data=agent_input
                    ),
                    timeout=node_def.timeout_seconds
                )

                # Reflection/validation if enabled
                if node_def.enable_reflection:
                    validated_result = await self.validate_output(
                        agent=agent,
                        output=result,
                        reflection_prompt=node_def.reflection_prompt
                    )
                    if validated_result:
                        result = validated_result

                return result

            except asyncio.TimeoutError:
                if attempt < node_def.retry_count - 1:
                    # Retry with exponential backoff
                    await asyncio.sleep(2 ** attempt)
                    continue
                else:
                    raise

            except Exception as e:
                if attempt < node_def.retry_count - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
                else:
                    raise

    def map_input_from_state(
        self,
        input_mapping: Dict[str, str],
        state: 'GraphState'
    ) -> Dict[str, Any]:
        """Map graph state to agent input"""
        agent_input = {}

        for agent_key, state_path in input_mapping.items():
            # State path format: "state.variable_name" or "state.nested.path"
            if state_path.startswith("state."):
                var_path = state_path[6:]  # Remove "state." prefix
                value = self.get_nested_value(state.variables, var_path)
                agent_input[agent_key] = value

        return agent_input

    def update_state_from_output(
        self,
        state: 'GraphState',
        node_def: AgentNodeDefinition,
        output: Dict[str, Any]
    ):
        """Update graph state from agent output"""
        for agent_key, state_path in node_def.output_mapping.items():
            if state_path.startswith("state."):
                var_path = state_path[6:]
                value = output.get(agent_key)
                self.set_nested_value(state.variables, var_path, value)

    async def validate_output(
        self,
        agent: 'BaseAgent',
        output: Dict[str, Any],
        reflection_prompt: Optional[str]
    ) -> Optional[Dict[str, Any]]:
        """
        Validate agent output using reflection

        Returns corrected output if validation fails, None if output is valid
        """
        # This will be implemented in Reflection section
        pass
```

### Graph State Management

```python
from dataclasses import dataclass, field
from typing import Dict, Any
from uuid import UUID
import json

@dataclass
class GraphState:
    """
    Shared state across all agents in execution graph

    Variables are accessible via dot notation: state.variable_name
    """
    request_id: UUID
    founder_id: UUID
    workspace_id: UUID
    variables: Dict[str, Any] = field(default_factory=dict)

    def get(self, key: str, default=None) -> Any:
        """Get variable by key"""
        return self.variables.get(key, default)

    def set(self, key: str, value: Any):
        """Set variable"""
        self.variables[key] = value

    def to_dict(self) -> Dict[str, Any]:
        """Serialize state"""
        return {
            "request_id": str(self.request_id),
            "founder_id": str(self.founder_id),
            "workspace_id": str(self.workspace_id),
            "variables": self.variables
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GraphState':
        """Deserialize state"""
        return cls(
            request_id=UUID(data["request_id"]),
            founder_id=UUID(data["founder_id"]),
            workspace_id=UUID(data["workspace_id"]),
            variables=data["variables"]
        )

class GraphStateManager:
    """Persist and retrieve graph execution state"""

    async def save_state(
        self,
        request_id: UUID,
        state: GraphState,
        checkpoint_name: str = "latest"
    ):
        """Save graph state to database"""
        await db.execute(
            """
            INSERT INTO orchestration.graph_states (
                request_id,
                checkpoint_name,
                state_data,
                created_at
            ) VALUES ($1, $2, $3, now())
            ON CONFLICT (request_id, checkpoint_name)
            DO UPDATE SET
                state_data = $3,
                updated_at = now()
            """,
            request_id,
            checkpoint_name,
            json.dumps(state.to_dict())
        )

    async def load_state(
        self,
        request_id: UUID,
        checkpoint_name: str = "latest"
    ) -> Optional[GraphState]:
        """Load graph state from database"""
        result = await db.fetchrow(
            """
            SELECT state_data
            FROM orchestration.graph_states
            WHERE request_id = $1
              AND checkpoint_name = $2
            """,
            request_id,
            checkpoint_name
        )

        if result:
            data = json.loads(result['state_data'])
            return GraphState.from_dict(data)

        return None
```

---

*[Document continues with remaining sections...]*

This is part 1 of the architecture document. Would you like me to continue with the remaining sections?
