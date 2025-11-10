"""
Agent Routing Service
Service for routing tasks to appropriate AI agents (AgentFlow orchestration)
Manages task queues, agent selection, and task execution
"""
import logging
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
import time

from app.models.agent_routing import (
    AgentRouteRequest,
    AgentTaskResponse,
    AgentTaskCreate,
    AgentTaskUpdate,
    AgentType,
    AgentTaskStatus,
    AgentTaskPriority,
    AgentHealthStatus,
    AgentMetrics
)
from app.database import get_db_context
from sqlalchemy import text


logger = logging.getLogger(__name__)


class AgentRoutingService:
    """Service for agent task routing and orchestration"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        # Agent routing rules: task_type -> preferred agent
        self.routing_rules = {
            "meeting_analysis": AgentType.MEETING_ANALYST,
            "kpi_analysis": AgentType.KPI_MONITOR,
            "generate_briefing": AgentType.BRIEFING_GENERATOR,
            "recommendation": AgentType.RECOMMENDATION_ENGINE,
            "communication": AgentType.COMMUNICATION_HANDLER,
            "task_management": AgentType.TASK_MANAGER,
            "research": AgentType.RESEARCH_ASSISTANT,
            "voice_processing": AgentType.VOICE_PROCESSOR,
        }

    async def route_task(
        self,
        request: AgentRouteRequest
    ) -> Optional[AgentTaskResponse]:
        """
        Route a task to the appropriate agent

        Args:
            request: Task routing request

        Returns:
            Created task with assigned agent
        """
        try:
            # Determine which agent should handle this task
            assigned_agent = request.preferred_agent or self._select_agent(
                task_type=request.task_type,
                priority=request.priority
            )

            # Create task record
            task_create = AgentTaskCreate(
                workspace_id=request.workspace_id,
                founder_id=request.founder_id,
                task_type=request.task_type,
                task_description=request.task_description,
                priority=request.priority,
                status=AgentTaskStatus.QUEUED,
                assigned_agent=assigned_agent,
                input_data=request.input_data,
                context=request.context or {},
                dependencies=request.dependencies,
                deadline=request.deadline
            )

            # Save to database
            async with get_db_context() as db:
                result = await db.execute(
                    text("""
                        INSERT INTO agent_tasks
                        (workspace_id, founder_id, task_type, task_description, priority, status,
                         assigned_agent, input_data, context, dependencies, deadline)
                        VALUES (:workspace_id, :founder_id, :task_type, :task_description, :priority,
                                :status, :assigned_agent, :input_data, :context, :dependencies, :deadline)
                        RETURNING *
                    """),
                    {
                        "workspace_id": str(task_create.workspace_id),
                        "founder_id": str(task_create.founder_id),
                        "task_type": task_create.task_type,
                        "task_description": task_create.task_description,
                        "priority": task_create.priority.value,
                        "status": task_create.status.value,
                        "assigned_agent": task_create.assigned_agent.value if task_create.assigned_agent else None,
                        "input_data": task_create.input_data,
                        "context": task_create.context,
                        "dependencies": [str(d) for d in task_create.dependencies],
                        "deadline": task_create.deadline
                    }
                )
                await db.commit()
                row = result.fetchone()

            task = await self._build_task_response(row)

            # If high priority and no dependencies, start immediately
            if request.priority == AgentTaskPriority.URGENT and not request.dependencies:
                await self._execute_task(task.id)

            self.logger.info(f"Routed task {task.id} to agent {assigned_agent.value}")
            return task

        except Exception as e:
            self.logger.error(f"Error routing task: {str(e)}")
            return None

    async def get_task(self, task_id: UUID) -> Optional[AgentTaskResponse]:
        """Get task by ID"""
        try:
            async with get_db_context() as db:
                result = await db.execute(
                    text("SELECT * FROM agent_tasks WHERE id = :id"),
                    {"id": str(task_id)}
                )
                row = result.fetchone()

                if not row:
                    return None

                return await self._build_task_response(row)

        except Exception as e:
            self.logger.error(f"Error getting task: {str(e)}")
            return None

    async def list_tasks(
        self,
        workspace_id: UUID,
        founder_id: Optional[UUID] = None,
        status: Optional[AgentTaskStatus] = None,
        assigned_agent: Optional[AgentType] = None,
        limit: int = 50
    ) -> List[AgentTaskResponse]:
        """List tasks with filters"""
        try:
            query = "SELECT * FROM agent_tasks WHERE workspace_id = :workspace_id"
            params = {"workspace_id": str(workspace_id)}

            if founder_id:
                query += " AND founder_id = :founder_id"
                params["founder_id"] = str(founder_id)

            if status:
                query += " AND status = :status"
                params["status"] = status.value

            if assigned_agent:
                query += " AND assigned_agent = :assigned_agent"
                params["assigned_agent"] = assigned_agent.value

            query += " ORDER BY created_at DESC LIMIT :limit"
            params["limit"] = limit

            async with get_db_context() as db:
                result = await db.execute(text(query), params)
                rows = result.fetchall()

                tasks = []
                for row in rows:
                    tasks.append(await self._build_task_response(row))

                return tasks

        except Exception as e:
            self.logger.error(f"Error listing tasks: {str(e)}")
            return []

    async def cancel_task(self, task_id: UUID) -> bool:
        """Cancel a task"""
        try:
            async with get_db_context() as db:
                result = await db.execute(
                    text("""
                        UPDATE agent_tasks
                        SET status = :status, updated_at = NOW()
                        WHERE id = :id AND status IN (:queued, :assigned)
                    """),
                    {
                        "id": str(task_id),
                        "status": AgentTaskStatus.CANCELLED.value,
                        "queued": AgentTaskStatus.QUEUED.value,
                        "assigned": AgentTaskStatus.ASSIGNED.value
                    }
                )
                await db.commit()
                return result.rowcount > 0

        except Exception as e:
            self.logger.error(f"Error cancelling task: {str(e)}")
            return False

    async def retry_task(self, task_id: UUID) -> Optional[AgentTaskResponse]:
        """Retry a failed task"""
        try:
            task = await self.get_task(task_id)
            if not task:
                return None

            if task.status != AgentTaskStatus.FAILED:
                raise ValueError("Only failed tasks can be retried")

            if task.retry_count >= task.max_retries:
                raise ValueError("Maximum retries exceeded")

            # Update task status
            async with get_db_context() as db:
                await db.execute(
                    text("""
                        UPDATE agent_tasks
                        SET status = :status, retry_count = retry_count + 1,
                            error_message = NULL, updated_at = NOW()
                        WHERE id = :id
                    """),
                    {
                        "id": str(task_id),
                        "status": AgentTaskStatus.QUEUED.value
                    }
                )
                await db.commit()

            # Execute task
            await self._execute_task(task_id)

            return await self.get_task(task_id)

        except Exception as e:
            self.logger.error(f"Error retrying task: {str(e)}")
            return None

    async def get_agent_health(self, agent_type: AgentType) -> AgentHealthStatus:
        """Get health status for an agent"""
        try:
            async with get_db_context() as db:
                # Get current load
                result = await db.execute(
                    text("""
                        SELECT COUNT(*) as count
                        FROM agent_tasks
                        WHERE assigned_agent = :agent
                        AND status = :status
                    """),
                    {
                        "agent": agent_type.value,
                        "status": AgentTaskStatus.PROCESSING.value
                    }
                )
                row = result.fetchone()
                current_load = row[0] if row else 0

                # Get success rate
                result = await db.execute(
                    text("""
                        SELECT
                            COUNT(*) FILTER (WHERE status = :completed) as successful,
                            COUNT(*) as total
                        FROM agent_tasks
                        WHERE assigned_agent = :agent
                        AND created_at > NOW() - INTERVAL '24 hours'
                    """),
                    {
                        "agent": agent_type.value,
                        "completed": AgentTaskStatus.COMPLETED.value
                    }
                )
                row = result.fetchone()
                success_rate = (row[0] / row[1]) if row and row[1] > 0 else 1.0

                return AgentHealthStatus(
                    agent_type=agent_type,
                    is_available=current_load < 10,  # Max 10 concurrent tasks
                    current_load=current_load,
                    max_capacity=10,
                    success_rate=success_rate,
                    last_health_check=datetime.utcnow()
                )

        except Exception as e:
            self.logger.error(f"Error getting agent health: {str(e)}")
            return AgentHealthStatus(
                agent_type=agent_type,
                is_available=False,
                current_load=0,
                success_rate=0.0
            )

    async def get_agent_metrics(self, agent_type: AgentType) -> AgentMetrics:
        """Get performance metrics for an agent"""
        try:
            async with get_db_context() as db:
                result = await db.execute(
                    text("""
                        SELECT
                            COUNT(*) as total,
                            COUNT(*) FILTER (WHERE status = :completed) as successful,
                            COUNT(*) FILTER (WHERE status = :failed) as failed,
                            AVG(processing_time_ms) as avg_time,
                            COUNT(*) FILTER (WHERE status IN (:queued, :assigned)) as queue_depth
                        FROM agent_tasks
                        WHERE assigned_agent = :agent
                    """),
                    {
                        "agent": agent_type.value,
                        "completed": AgentTaskStatus.COMPLETED.value,
                        "failed": AgentTaskStatus.FAILED.value,
                        "queued": AgentTaskStatus.QUEUED.value,
                        "assigned": AgentTaskStatus.ASSIGNED.value
                    }
                )
                row = result.fetchone()

                return AgentMetrics(
                    agent_type=agent_type,
                    total_tasks_processed=row[0] if row else 0,
                    successful_tasks=row[1] if row else 0,
                    failed_tasks=row[2] if row else 0,
                    average_processing_time_ms=float(row[3]) if row and row[3] else 0.0,
                    current_queue_depth=row[4] if row else 0,
                    uptime_percentage=95.0  # Mock value
                )

        except Exception as e:
            self.logger.error(f"Error getting agent metrics: {str(e)}")
            return AgentMetrics(
                agent_type=agent_type,
                uptime_percentage=0.0
            )

    def _select_agent(
        self,
        task_type: str,
        priority: AgentTaskPriority
    ) -> Optional[AgentType]:
        """
        Select the best agent for a task

        Args:
            task_type: Type of task
            priority: Task priority

        Returns:
            Selected agent type
        """
        # Check routing rules
        if task_type in self.routing_rules:
            return self.routing_rules[task_type]

        # Default to task manager
        return AgentType.TASK_MANAGER

    async def _execute_task(self, task_id: UUID):
        """
        Execute a task

        This would typically be done by a background worker
        For now, we'll simulate execution
        """
        try:
            start_time = time.time()

            # Update status to processing
            async with get_db_context() as db:
                await db.execute(
                    text("""
                        UPDATE agent_tasks
                        SET status = :status, started_at = NOW(), updated_at = NOW()
                        WHERE id = :id
                    """),
                    {
                        "id": str(task_id),
                        "status": AgentTaskStatus.PROCESSING.value
                    }
                )
                await db.commit()

            # Get task
            task = await self.get_task(task_id)
            if not task:
                return

            # Execute based on agent type
            output_data = await self._execute_agent_logic(
                task.assigned_agent,
                task.input_data,
                task.context
            )

            processing_time_ms = int((time.time() - start_time) * 1000)

            # Update task as completed
            async with get_db_context() as db:
                await db.execute(
                    text("""
                        UPDATE agent_tasks
                        SET status = :status, output_data = :output_data,
                            processing_time_ms = :processing_time_ms,
                            completed_at = NOW(), updated_at = NOW()
                        WHERE id = :id
                    """),
                    {
                        "id": str(task_id),
                        "status": AgentTaskStatus.COMPLETED.value,
                        "output_data": output_data,
                        "processing_time_ms": processing_time_ms
                    }
                )
                await db.commit()

            self.logger.info(f"Completed task {task_id} in {processing_time_ms}ms")

        except Exception as e:
            self.logger.error(f"Error executing task: {str(e)}")
            # Update task as failed
            async with get_db_context() as db:
                await db.execute(
                    text("""
                        UPDATE agent_tasks
                        SET status = :status, error_message = :error, updated_at = NOW()
                        WHERE id = :id
                    """),
                    {
                        "id": str(task_id),
                        "status": AgentTaskStatus.FAILED.value,
                        "error": str(e)
                    }
                )
                await db.commit()

    async def _execute_agent_logic(
        self,
        agent_type: Optional[AgentType],
        input_data: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute agent-specific logic

        In production, this would delegate to actual AI agents
        For now, return mock results
        """
        return {
            "agent": agent_type.value if agent_type else "unknown",
            "status": "completed",
            "result": "Task completed successfully",
            "data": input_data
        }

    async def _build_task_response(self, row) -> AgentTaskResponse:
        """Build task response from database row"""
        return AgentTaskResponse(
            id=row.id,
            workspace_id=UUID(row.workspace_id),
            founder_id=UUID(row.founder_id),
            task_type=row.task_type,
            task_description=row.task_description,
            priority=AgentTaskPriority(row.priority),
            status=AgentTaskStatus(row.status),
            assigned_agent=AgentType(row.assigned_agent) if row.assigned_agent else None,
            input_data=row.input_data or {},
            output_data=row.output_data,
            context=row.context or {},
            error_message=row.error_message,
            retry_count=row.retry_count,
            max_retries=row.max_retries,
            dependencies=[UUID(d) for d in (row.dependencies or [])],
            processing_time_ms=row.processing_time_ms,
            created_at=row.created_at,
            updated_at=row.updated_at,
            started_at=row.started_at,
            completed_at=row.completed_at,
            deadline=row.deadline
        )
