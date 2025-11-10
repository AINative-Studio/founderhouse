"""
Agent Routing & Collaboration API Endpoints
Endpoints for routing tasks to agents and managing cross-agent collaboration
"""
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends, Query, Body, Path

from app.services.agent_routing_service import AgentRoutingService
from app.services.agent_collaboration_service import AgentCollaborationService
from app.models.agent_routing import (
    AgentRouteRequest,
    AgentTaskResponse,
    AgentCollaborationRequest,
    AgentCollaborationResponse,
    AgentType,
    AgentTaskStatus,
    AgentTaskPriority,
    AgentHealthStatus,
    AgentMetrics
)


router = APIRouter(prefix="/agents", tags=["Agent Orchestration"])


def get_routing_service() -> AgentRoutingService:
    """Dependency for agent routing service"""
    return AgentRoutingService()


def get_collaboration_service() -> AgentCollaborationService:
    """Dependency for agent collaboration service"""
    return AgentCollaborationService()


@router.post("/route", response_model=AgentTaskResponse)
async def route_task(
    request: AgentRouteRequest = Body(...),
    service: AgentRoutingService = Depends(get_routing_service)
):
    """
    Route a task to the appropriate agent

    Analyzes the task type and automatically selects the best agent to handle it.
    Tasks are queued and executed based on priority and dependencies.
    """
    try:
        result = await service.route_task(request)

        if not result:
            raise HTTPException(status_code=500, detail="Failed to route task")

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error routing task: {str(e)}")


@router.post("/collaborate", response_model=AgentCollaborationResponse)
async def initiate_collaboration(
    request: AgentCollaborationRequest = Body(...),
    service: AgentCollaborationService = Depends(get_collaboration_service)
):
    """
    Initiate cross-agent collaboration

    Coordinates multiple agents to work together on a complex objective.
    Agents share context and synthesize their outputs into a final result.
    """
    try:
        result = await service.initiate_collaboration(request)

        if not result:
            raise HTTPException(status_code=500, detail="Failed to initiate collaboration")

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error initiating collaboration: {str(e)}")


@router.get("/tasks/{task_id}", response_model=AgentTaskResponse)
async def get_task(
    task_id: UUID = Path(..., description="Task ID"),
    service: AgentRoutingService = Depends(get_routing_service)
):
    """
    Get task details by ID

    Returns full task information including status, assigned agent, and results.
    """
    try:
        task = await service.get_task(task_id)

        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        return task

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching task: {str(e)}")


@router.get("/tasks", response_model=List[AgentTaskResponse])
async def list_tasks(
    workspace_id: UUID = Query(..., description="Workspace ID"),
    founder_id: Optional[UUID] = Query(None, description="Filter by founder"),
    status: Optional[AgentTaskStatus] = Query(None, description="Filter by status"),
    assigned_agent: Optional[AgentType] = Query(None, description="Filter by agent"),
    limit: int = Query(50, le=100, description="Max number of tasks to return"),
    service: AgentRoutingService = Depends(get_routing_service)
):
    """
    List tasks with filters

    Returns paginated list of agent tasks with optional filtering.
    """
    try:
        tasks = await service.list_tasks(
            workspace_id=workspace_id,
            founder_id=founder_id,
            status=status,
            assigned_agent=assigned_agent,
            limit=limit
        )

        return tasks

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing tasks: {str(e)}")


@router.post("/tasks/{task_id}/cancel")
async def cancel_task(
    task_id: UUID = Path(..., description="Task ID"),
    service: AgentRoutingService = Depends(get_routing_service)
):
    """
    Cancel a queued or assigned task

    Cancels a task that hasn't started processing yet.
    """
    try:
        success = await service.cancel_task(task_id)

        if not success:
            raise HTTPException(status_code=400, detail="Task cannot be cancelled")

        return {"status": "cancelled", "task_id": str(task_id)}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error cancelling task: {str(e)}")


@router.post("/tasks/{task_id}/retry", response_model=AgentTaskResponse)
async def retry_task(
    task_id: UUID = Path(..., description="Task ID"),
    service: AgentRoutingService = Depends(get_routing_service)
):
    """
    Retry a failed task

    Requeues a failed task for execution if it hasn't exceeded max retries.
    """
    try:
        result = await service.retry_task(task_id)

        if not result:
            raise HTTPException(status_code=400, detail="Task cannot be retried")

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrying task: {str(e)}")


@router.get("/collaboration/{session_id}", response_model=AgentCollaborationResponse)
async def get_collaboration(
    session_id: UUID = Path(..., description="Collaboration session ID"),
    service: AgentCollaborationService = Depends(get_collaboration_service)
):
    """
    Get collaboration session details

    Returns information about a cross-agent collaboration session including outputs from all agents.
    """
    try:
        session = await service.get_collaboration(session_id)

        if not session:
            raise HTTPException(status_code=404, detail="Collaboration session not found")

        return session

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching collaboration: {str(e)}")


@router.get("/health/{agent_type}", response_model=AgentHealthStatus)
async def get_agent_health(
    agent_type: AgentType = Path(..., description="Agent type"),
    service: AgentRoutingService = Depends(get_routing_service)
):
    """
    Get agent health status

    Returns current health and availability status for a specific agent type.
    """
    try:
        health = await service.get_agent_health(agent_type)
        return health

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching agent health: {str(e)}")


@router.get("/metrics/{agent_type}", response_model=AgentMetrics)
async def get_agent_metrics(
    agent_type: AgentType = Path(..., description="Agent type"),
    service: AgentRoutingService = Depends(get_routing_service)
):
    """
    Get agent performance metrics

    Returns performance statistics for a specific agent type including success rate and processing times.
    """
    try:
        metrics = await service.get_agent_metrics(agent_type)
        return metrics

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching agent metrics: {str(e)}")
