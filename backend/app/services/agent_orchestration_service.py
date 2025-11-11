"""
Agent Orchestration Service
Service for orchestrating multi-agent workflows using Directed Acyclic Graphs (DAG)
Implements Sprint 5 AgentFlow: CoS → TaskAgent → InsightAgent routing
"""
import logging
import asyncio
from typing import Optional, List, Dict, Any, Tuple
from uuid import UUID, uuid4
from datetime import datetime

from app.models.agent_routing import (
    AgentType,
    AgentTaskStatus,
    AgentTaskPriority,
    AgentRouteRequest,
    AgentTaskResponse
)
from app.services.agent_routing_service import AgentRoutingService
from app.database import get_db_context
from sqlalchemy import text


logger = logging.getLogger(__name__)


class AgentOrchestrationService:
    """
    Service for orchestrating multi-agent workflows

    Implements DAG-based routing for complex multi-step agent tasks:
    - CoS Agent (Briefing Generator) → Task Manager → Insight/Recommendation Engine
    - Result aggregation from multiple agents
    - Workflow state management
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.routing_service = AgentRoutingService()

        # Define workflow graphs
        self.workflow_graphs = {
            "cos_task_insight": self._build_cos_task_insight_graph(),
            "default": self._build_default_graph()
        }

    def _build_cos_task_insight_graph(self) -> Dict[str, Any]:
        """
        Build CoS → Task → Insight workflow graph

        This is the core Sprint 5 workflow:
        1. Briefing Generator (CoS) analyzes input and creates summary
        2. Task Manager creates tasks from CoS output
        3. Recommendation Engine generates insights from tasks

        Returns:
            DAG structure with nodes and edges
        """
        return {
            "nodes": [
                {
                    "id": "cos_agent",
                    "agent_type": AgentType.BRIEFING_GENERATOR,
                    "description": "Chief of Staff - Analyzes input and creates briefing"
                },
                {
                    "id": "task_agent",
                    "agent_type": AgentType.TASK_MANAGER,
                    "description": "Task Manager - Creates actionable tasks"
                },
                {
                    "id": "insight_agent",
                    "agent_type": AgentType.RECOMMENDATION_ENGINE,
                    "description": "Insight Engine - Generates recommendations"
                }
            ],
            "edges": [
                {
                    "from": AgentType.BRIEFING_GENERATOR,
                    "to": AgentType.TASK_MANAGER,
                    "data_mapping": {
                        "summary": "briefing_summary",
                        "key_points": "action_items"
                    }
                },
                {
                    "from": AgentType.TASK_MANAGER,
                    "to": AgentType.RECOMMENDATION_ENGINE,
                    "data_mapping": {
                        "tasks_created": "task_count",
                        "task_ids": "related_tasks"
                    }
                }
            ]
        }

    def _build_default_graph(self) -> Dict[str, Any]:
        """
        Build default single-agent workflow graph

        Fallback for unknown workflow types
        """
        return {
            "nodes": [
                {
                    "id": "default_agent",
                    "agent_type": AgentType.TASK_MANAGER,
                    "description": "Default task handler"
                }
            ],
            "edges": []
        }

    def get_workflow_graph(self, workflow_type: str) -> Dict[str, Any]:
        """
        Get workflow graph for a given type

        Args:
            workflow_type: Type of workflow (e.g., "cos_task_insight")

        Returns:
            Workflow graph with nodes and edges
        """
        return self.workflow_graphs.get(workflow_type, self.workflow_graphs["default"])

    def validate_workflow_graph(self, graph: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Validate workflow graph is a valid DAG

        Checks:
        - No cycles
        - All edges reference valid nodes
        - At least one node exists

        Args:
            graph: Workflow graph to validate

        Returns:
            (is_valid, error_message)
        """
        if not graph.get("nodes"):
            return False, "Graph must have at least one node"

        nodes = graph["nodes"]
        edges = graph.get("edges", [])

        # Build adjacency list
        adj_list = {node["agent_type"]: [] for node in nodes}
        node_types = set(node["agent_type"] for node in nodes)

        # Add edges
        for edge in edges:
            from_type = edge["from"]
            to_type = edge["to"]

            # Validate edge references exist
            if from_type not in node_types or to_type not in node_types:
                return False, f"Edge references non-existent node: {from_type} -> {to_type}"

            adj_list[from_type].append(to_type)

        # Check for cycles using DFS
        visited = set()
        rec_stack = set()

        def has_cycle(node_type: AgentType) -> bool:
            """DFS to detect cycles"""
            visited.add(node_type)
            rec_stack.add(node_type)

            for neighbor in adj_list.get(node_type, []):
                if neighbor not in visited:
                    if has_cycle(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True

            rec_stack.remove(node_type)
            return False

        # Check each node for cycles
        for node_type in adj_list:
            if node_type not in visited:
                if has_cycle(node_type):
                    return False, "Graph contains cycle - must be a DAG"

        return True, None

    async def orchestrate_workflow(
        self,
        workspace_id: UUID,
        founder_id: UUID,
        objective: str,
        input_data: Dict[str, Any],
        workflow_type: str = "cos_task_insight",
        timeout_seconds: int = 300
    ) -> Dict[str, Any]:
        """
        Orchestrate a multi-agent workflow

        Args:
            workspace_id: Workspace ID
            founder_id: Founder ID
            objective: High-level objective for the workflow
            input_data: Input data for the workflow
            workflow_type: Type of workflow to execute
            timeout_seconds: Maximum execution time

        Returns:
            Workflow execution result with aggregated outputs
        """
        workflow_id = uuid4()

        try:
            # Get workflow graph
            graph = self.get_workflow_graph(workflow_type)

            # Validate graph
            is_valid, error = self.validate_workflow_graph(graph)
            if not is_valid:
                self.logger.error(f"Invalid workflow graph: {error}")
                return {
                    "workflow_id": workflow_id,
                    "status": "failed",
                    "error": f"Invalid workflow: {error}"
                }

            self.logger.info(f"Starting workflow {workflow_id} of type {workflow_type}")

            # Execute workflow with timeout
            try:
                execution_steps = await asyncio.wait_for(
                    self._execute_workflow_graph(
                        workspace_id=workspace_id,
                        founder_id=founder_id,
                        graph=graph,
                        objective=objective,
                        input_data=input_data
                    ),
                    timeout=timeout_seconds
                )
            except asyncio.TimeoutError:
                self.logger.error(f"Workflow {workflow_id} timed out after {timeout_seconds}s")
                return {
                    "workflow_id": workflow_id,
                    "status": "failed",
                    "error": f"Workflow execution timeout after {timeout_seconds} seconds",
                    "execution_steps": []
                }

            # Aggregate results
            aggregated_results = self.aggregate_results(execution_steps)

            # Determine final status
            failed_steps = [s for s in execution_steps if s.get("status") == "failed"]
            final_status = "failed" if failed_steps else "completed"

            result = {
                "workflow_id": workflow_id,
                "workflow_type": workflow_type,
                "status": final_status,
                "execution_steps": execution_steps,
                "aggregated_results": aggregated_results,
                "created_at": datetime.utcnow().isoformat()
            }

            if failed_steps:
                result["error"] = f"{len(failed_steps)} agent(s) failed during execution"

            # Save workflow execution
            await self.save_workflow_execution(
                workspace_id=workspace_id,
                founder_id=founder_id,
                objective=objective,
                execution_data=result
            )

            self.logger.info(f"Workflow {workflow_id} completed with status: {final_status}")

            return result

        except Exception as e:
            self.logger.error(f"Error orchestrating workflow: {str(e)}")
            return {
                "workflow_id": workflow_id,
                "status": "failed",
                "error": str(e),
                "execution_steps": []
            }

    async def _execute_workflow_graph(
        self,
        workspace_id: UUID,
        founder_id: UUID,
        graph: Dict[str, Any],
        objective: str,
        input_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Execute workflow graph in topological order

        Args:
            workspace_id: Workspace ID
            founder_id: Founder ID
            graph: Workflow graph
            objective: Workflow objective
            input_data: Initial input data

        Returns:
            List of execution steps with outputs
        """
        nodes = graph["nodes"]
        edges = graph.get("edges", [])

        # Build execution order (topological sort)
        execution_order = self._topological_sort(nodes, edges)

        # Track execution context
        context = {
            "objective": objective,
            "input_data": input_data,
            "agent_outputs": {}
        }

        execution_steps = []

        # Execute each node in order
        for node in execution_order:
            # Check if previous steps failed
            if any(step.get("status") == "failed" for step in execution_steps):
                # Skip remaining steps if a previous step failed
                execution_steps.append({
                    "agent_type": node["agent_type"],
                    "status": "skipped",
                    "reason": "Previous agent failed"
                })
                continue

            # Execute agent step
            step_result = await self.execute_agent_step(
                workspace_id=workspace_id,
                founder_id=founder_id,
                node=node,
                context=context
            )

            execution_steps.append(step_result)

            # Update context with agent output
            if step_result.get("status") == "completed":
                context["agent_outputs"][node["agent_type"]] = step_result.get("output", {})

        return execution_steps

    def _topological_sort(
        self,
        nodes: List[Dict[str, Any]],
        edges: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Topological sort of workflow graph

        Args:
            nodes: List of nodes
            edges: List of edges

        Returns:
            Nodes in execution order
        """
        # Build adjacency list and in-degree count
        adj_list = {node["agent_type"]: [] for node in nodes}
        in_degree = {node["agent_type"]: 0 for node in nodes}
        node_map = {node["agent_type"]: node for node in nodes}

        for edge in edges:
            adj_list[edge["from"]].append(edge["to"])
            in_degree[edge["to"]] += 1

        # Find nodes with no incoming edges
        queue = [node_type for node_type in in_degree if in_degree[node_type] == 0]
        result = []

        while queue:
            current = queue.pop(0)
            result.append(node_map[current])

            # Reduce in-degree for neighbors
            for neighbor in adj_list[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        return result

    async def execute_agent_step(
        self,
        workspace_id: UUID,
        founder_id: UUID,
        node: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a single agent step

        Args:
            workspace_id: Workspace ID
            founder_id: Founder ID
            node: Node to execute
            context: Execution context with previous outputs

        Returns:
            Step execution result
        """
        agent_type = node["agent_type"]

        try:
            self.logger.info(f"Executing agent: {agent_type.value}")

            # Prepare input for this agent
            agent_input = self._prepare_agent_input(
                agent_type=agent_type,
                context=context
            )

            # Route task to agent
            route_request = AgentRouteRequest(
                workspace_id=workspace_id,
                founder_id=founder_id,
                task_type=f"orchestration_{agent_type.value}",
                task_description=f"{context.get('objective', 'Execute workflow step')}",
                priority=AgentTaskPriority.HIGH,
                preferred_agent=agent_type,
                input_data=agent_input,
                context=context
            )

            task = await self.routing_service.route_task(route_request)

            if not task:
                return {
                    "agent_type": agent_type,
                    "status": "failed",
                    "error": "Failed to route task to agent"
                }

            # Wait for task completion
            completed_task = await self.wait_for_task_completion(
                task_id=task.id,
                timeout_seconds=60
            )

            if completed_task.status == AgentTaskStatus.COMPLETED:
                return {
                    "agent_type": agent_type,
                    "task_id": str(completed_task.id),
                    "status": "completed",
                    "output": completed_task.output_data or {},
                    "processing_time_ms": completed_task.processing_time_ms
                }
            else:
                return {
                    "agent_type": agent_type,
                    "task_id": str(completed_task.id),
                    "status": "failed",
                    "error": completed_task.error_message or "Agent task failed"
                }

        except Exception as e:
            self.logger.error(f"Error executing agent {agent_type.value}: {str(e)}")
            return {
                "agent_type": agent_type,
                "status": "failed",
                "error": str(e)
            }

    def _prepare_agent_input(
        self,
        agent_type: AgentType,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Prepare input data for an agent based on context

        Args:
            agent_type: Type of agent
            context: Execution context

        Returns:
            Input data for agent
        """
        agent_input = {
            "objective": context.get("objective", ""),
            **context.get("input_data", {})
        }

        # Add previous agent outputs
        agent_outputs = context.get("agent_outputs", {})
        if agent_outputs:
            agent_input["previous_outputs"] = agent_outputs

        return agent_input

    async def wait_for_task_completion(
        self,
        task_id: UUID,
        timeout_seconds: int = 60,
        poll_interval: float = 1.0
    ) -> AgentTaskResponse:
        """
        Wait for an agent task to complete

        Args:
            task_id: Task ID to wait for
            timeout_seconds: Maximum wait time
            poll_interval: Polling interval in seconds

        Returns:
            Completed task
        """
        start_time = asyncio.get_event_loop().time()

        while True:
            # Check timeout
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > timeout_seconds:
                raise asyncio.TimeoutError(f"Task {task_id} did not complete within {timeout_seconds}s")

            # Get task status
            task = await self.routing_service.get_task(task_id)

            if not task:
                raise ValueError(f"Task {task_id} not found")

            # Check if completed
            if task.status in [AgentTaskStatus.COMPLETED, AgentTaskStatus.FAILED, AgentTaskStatus.CANCELLED]:
                return task

            # Wait before next poll
            await asyncio.sleep(poll_interval)

    def aggregate_results(self, execution_steps: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Aggregate results from multiple agent executions

        Args:
            execution_steps: List of execution step results

        Returns:
            Aggregated results with summary
        """
        total_agents = len(execution_steps)
        successful_agents = len([s for s in execution_steps if s.get("status") == "completed"])
        failed_agents = len([s for s in execution_steps if s.get("status") == "failed"])
        skipped_agents = len([s for s in execution_steps if s.get("status") == "skipped"])

        # Collect all outputs
        agent_outputs = {}
        errors = []

        for step in execution_steps:
            agent_type = step.get("agent_type")
            if step.get("status") == "completed":
                agent_outputs[agent_type.value] = step.get("output", {})
            elif step.get("status") == "failed":
                errors.append({
                    "agent": agent_type.value,
                    "error": step.get("error", "Unknown error")
                })

        # Calculate total processing time
        total_processing_time = sum(
            step.get("processing_time_ms", 0)
            for step in execution_steps
            if step.get("processing_time_ms")
        )

        return {
            "summary": f"Executed {total_agents} agents: {successful_agents} successful, "
                      f"{failed_agents} failed, {skipped_agents} skipped",
            "total_agents": total_agents,
            "successful_agents": successful_agents,
            "failed_agents": failed_agents,
            "skipped_agents": skipped_agents,
            "agent_outputs": agent_outputs,
            "errors": errors if errors else None,
            "total_processing_time_ms": total_processing_time
        }

    async def save_workflow_execution(
        self,
        workspace_id: UUID,
        founder_id: UUID,
        objective: str,
        execution_data: Dict[str, Any]
    ) -> UUID:
        """
        Save workflow execution to database

        Args:
            workspace_id: Workspace ID
            founder_id: Founder ID
            objective: Workflow objective
            execution_data: Execution result data

        Returns:
            Workflow execution ID
        """
        try:
            async with get_db_context() as db:
                result = await db.execute(
                    text("""
                        INSERT INTO agent_workflow_executions
                        (workspace_id, founder_id, workflow_type, objective, status,
                         execution_steps, aggregated_results, created_at)
                        VALUES (:workspace_id, :founder_id, :workflow_type, :objective, :status,
                                :execution_steps, :aggregated_results, NOW())
                        RETURNING id
                    """),
                    {
                        "workspace_id": str(workspace_id),
                        "founder_id": str(founder_id),
                        "workflow_type": execution_data.get("workflow_type", "unknown"),
                        "objective": objective,
                        "status": execution_data.get("status", "unknown"),
                        "execution_steps": execution_data.get("execution_steps", []),
                        "aggregated_results": execution_data.get("aggregated_results", {})
                    }
                )
                await db.commit()
                row = result.fetchone()
                return row.id
        except Exception as e:
            self.logger.error(f"Error saving workflow execution: {str(e)}")
            # Return a generated ID even if save fails
            return uuid4()

    async def get_workflow_execution(self, workflow_id: UUID) -> Optional[Dict[str, Any]]:
        """
        Get workflow execution by ID

        Args:
            workflow_id: Workflow execution ID

        Returns:
            Workflow execution data
        """
        try:
            async with get_db_context() as db:
                result = await db.execute(
                    text("SELECT * FROM agent_workflow_executions WHERE id = :id"),
                    {"id": str(workflow_id)}
                )
                row = result.fetchone()

                if not row:
                    return None

                return {
                    "id": row.id,
                    "workspace_id": UUID(row.workspace_id),
                    "founder_id": UUID(row.founder_id),
                    "workflow_type": row.workflow_type,
                    "objective": row.objective,
                    "status": row.status,
                    "execution_steps": row.execution_steps or [],
                    "aggregated_results": row.aggregated_results or {},
                    "created_at": row.created_at,
                    "completed_at": row.completed_at
                }
        except Exception as e:
            self.logger.error(f"Error getting workflow execution: {str(e)}")
            return None
