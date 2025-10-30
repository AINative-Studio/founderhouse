"""
Integration Management Endpoints
MCP and API integrations for external platforms
"""
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from supabase import Client

from app.database import get_db
from app.core.security import get_current_user, AuthUser
from app.core.dependencies import get_workspace_id
from app.models.integration import (
    IntegrationConnectRequest,
    IntegrationResponse,
    IntegrationUpdate,
    IntegrationHealthCheck,
    IntegrationStatusResponse,
    IntegrationCreate,
    Platform
)
from app.services.integration_service import IntegrationService

router = APIRouter()


def get_integration_service(db: Client = Depends(get_db)) -> IntegrationService:
    """Dependency to get integration service instance"""
    return IntegrationService(db)


@router.post(
    "/connect",
    response_model=IntegrationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Connect Integration"
)
async def connect_integration(
    request: IntegrationConnectRequest,
    workspace_id: UUID = Depends(get_workspace_id),
    current_user: AuthUser = Depends(get_current_user),
    service: IntegrationService = Depends(get_integration_service)
):
    """
    Connect a new MCP or API integration

    Establishes a connection to an external platform (Zoom, Slack, Discord, etc.)
    and securely stores encrypted credentials.

    **Request Body:**
    - platform: Platform to connect (zoom, slack, discord, etc.)
    - connection_type: Connection method (mcp or api)
    - credentials: Platform-specific credentials (will be encrypted)
    - metadata: Optional additional metadata

    **Returns:**
    - Created integration with connection status

    **Security:**
    - Credentials are encrypted using AES-256 before storage
    - Only workspace members can create integrations

    **Example:**
    ```json
    {
      "platform": "zoom",
      "connection_type": "mcp",
      "credentials": {
        "client_id": "your_client_id",
        "client_secret": "your_client_secret"
      },
      "metadata": {
        "display_name": "My Zoom Account"
      }
    }
    ```
    """
    integration_create = IntegrationCreate(
        workspace_id=workspace_id,
        founder_id=None,  # Workspace-level integration
        platform=request.platform,
        connection_type=request.connection_type,
        credentials=request.credentials,
        metadata=request.metadata
    )

    return await service.create_integration(integration_create)


@router.get(
    "/status",
    response_model=IntegrationStatusResponse,
    summary="Get Integration Status"
)
async def get_integration_status(
    workspace_id: UUID = Depends(get_workspace_id),
    current_user: AuthUser = Depends(get_current_user),
    service: IntegrationService = Depends(get_integration_service)
):
    """
    Get overall integration health status for workspace

    Provides a comprehensive view of all integrations including:
    - Total integration count
    - Connected integrations
    - Failed integrations
    - Pending integrations
    - Individual health checks

    **Query Parameters:**
    - workspace_id: Workspace UUID (optional, defaults to user's workspace)

    **Returns:**
    - Integration status summary with health checks

    **Use Cases:**
    - Dashboard health monitoring
    - Troubleshooting integration issues
    - Verifying MCP connectivity
    """
    return await service.get_integration_status(workspace_id)


@router.get(
    "",
    response_model=List[IntegrationResponse],
    summary="List Integrations"
)
async def list_integrations(
    workspace_id: UUID = Depends(get_workspace_id),
    platform: Optional[Platform] = Query(None, description="Filter by platform"),
    current_user: AuthUser = Depends(get_current_user),
    service: IntegrationService = Depends(get_integration_service)
):
    """
    List all integrations for a workspace

    **Query Parameters:**
    - workspace_id: Workspace UUID
    - platform: Optional filter by platform (zoom, slack, etc.)

    **Returns:**
    - List of integration objects (credentials excluded)

    **Permissions:**
    - User must be a member of the workspace
    """
    return await service.list_integrations(
        workspace_id=workspace_id,
        platform=platform
    )


@router.get(
    "/{integration_id}",
    response_model=IntegrationResponse,
    summary="Get Integration"
)
async def get_integration(
    integration_id: UUID,
    current_user: AuthUser = Depends(get_current_user),
    service: IntegrationService = Depends(get_integration_service)
):
    """
    Get details of a specific integration

    **Path Parameters:**
    - integration_id: Integration UUID

    **Returns:**
    - Integration details (credentials excluded for security)

    **Permissions:**
    - User must have access to the workspace
    """
    return await service.get_integration(integration_id)


@router.get(
    "/{integration_id}/health",
    response_model=IntegrationHealthCheck,
    summary="Check Integration Health"
)
async def check_integration_health(
    integration_id: UUID,
    current_user: AuthUser = Depends(get_current_user),
    service: IntegrationService = Depends(get_integration_service)
):
    """
    Perform health check on a specific integration

    Tests the connection to the external platform and returns health status.

    **Path Parameters:**
    - integration_id: Integration UUID

    **Returns:**
    - Health check result with:
      - Connection status
      - Last check timestamp
      - Error message (if unhealthy)
      - Platform-specific metadata

    **Use Cases:**
    - Troubleshooting connection issues
    - Monitoring integration uptime
    - Verifying OAuth token validity
    """
    return await service.check_integration_health(integration_id)


@router.patch(
    "/{integration_id}",
    response_model=IntegrationResponse,
    summary="Update Integration"
)
async def update_integration(
    integration_id: UUID,
    integration_update: IntegrationUpdate,
    current_user: AuthUser = Depends(get_current_user),
    service: IntegrationService = Depends(get_integration_service)
):
    """
    Update integration configuration

    **Path Parameters:**
    - integration_id: Integration UUID

    **Request Body:**
    - status: Update connection status
    - credentials: Update credentials (will be re-encrypted)
    - metadata: Update metadata

    **Returns:**
    - Updated integration object

    **Permissions:**
    - User must be a workspace admin or owner
    """
    return await service.update_integration(integration_id, integration_update)


@router.delete(
    "/{integration_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Disconnect Integration"
)
async def disconnect_integration(
    integration_id: UUID,
    current_user: AuthUser = Depends(get_current_user),
    service: IntegrationService = Depends(get_integration_service)
):
    """
    Disconnect and remove an integration

    **Path Parameters:**
    - integration_id: Integration UUID

    **Actions:**
    - Revokes OAuth tokens (if applicable)
    - Removes stored credentials
    - Deletes integration record

    **Permissions:**
    - User must be a workspace admin or owner

    **Note:**
    - This does not revoke permissions on the external platform
    - User may need to manually revoke access in platform settings
    """
    await service.delete_integration(integration_id)
    return None


@router.post(
    "/{integration_id}/refresh",
    response_model=IntegrationResponse,
    summary="Refresh Integration Connection"
)
async def refresh_integration(
    integration_id: UUID,
    current_user: AuthUser = Depends(get_current_user),
    service: IntegrationService = Depends(get_integration_service)
):
    """
    Refresh integration connection and tokens

    Attempts to refresh OAuth tokens or re-establish MCP connection.

    **Path Parameters:**
    - integration_id: Integration UUID

    **Returns:**
    - Updated integration with new connection status

    **Use Cases:**
    - Recovering from expired OAuth tokens
    - Re-establishing failed MCP connections
    - Updating platform credentials
    """
    # Get integration and attempt reconnection
    integration = await service.get_integration(integration_id)

    # Perform health check which will attempt reconnection
    health_check = await service.check_integration_health(integration_id)

    if not health_check.is_healthy:
        # Update status to error
        await service.update_integration(
            integration_id,
            IntegrationUpdate(status=health_check.status)
        )

    return await service.get_integration(integration_id)


@router.get(
    "/health-dashboard",
    summary="Get Integration Health Dashboard"
)
async def get_health_dashboard(
    workspace_id: UUID = Depends(get_workspace_id),
    current_user: AuthUser = Depends(get_current_user),
    service: IntegrationService = Depends(get_integration_service)
):
    """
    Get comprehensive health dashboard for all integrations

    Provides aggregated health metrics and status across all integrations.

    **Query Parameters:**
    - workspace_id: Workspace UUID (optional, defaults to user's workspace)

    **Returns:**
    - Health dashboard with:
      - Total integration count
      - Healthy/unhealthy breakdown
      - Success rate
      - Per-platform health statistics
      - Recent errors

    **Use Cases:**
    - Monitoring dashboard
    - Integration status overview
    - Troubleshooting and diagnostics
    """
    from app.services.health_check_service import HealthCheckService
    from app.database import get_db

    db = next(get_db())
    health_service = HealthCheckService(db)

    dashboard = await health_service.get_health_dashboard(workspace_id)
    return dashboard
