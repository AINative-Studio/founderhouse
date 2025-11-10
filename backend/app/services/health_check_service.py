"""
Health Check Service
Tests and monitors integration connections
"""
import logging
from typing import Dict, Any, List, Optional
from uuid import UUID
from datetime import datetime
import json

from sqlalchemy.orm import Session
from sqlalchemy import text
from fastapi import HTTPException, status

from app.models.integration import (
    IntegrationHealthCheck,
    IntegrationStatus,
    Platform
)
from app.connectors.connector_registry import get_connector, test_connector_connection
from app.services.oauth_service import OAuthService


logger = logging.getLogger(__name__)


class HealthCheckService:
    """Service for checking integration health"""

    def __init__(self, db: Session):
        """
        Initialize health check service

        Args:
            db: SQLAlchemy database session
        """
        self.db = db
        self.oauth_service = OAuthService(db)

    async def check_integration_health(
        self,
        integration_id: UUID,
        test_connection: bool = True
    ) -> IntegrationHealthCheck:
        """
        Check health of a single integration

        Args:
            integration_id: Integration UUID
            test_connection: Whether to actually test the connection

        Returns:
            IntegrationHealthCheck with current status

        Raises:
            HTTPException: If integration not found
        """
        try:
            # Get integration from database
            query = text('SELECT * FROM "core"."integrations" WHERE id = :id')
            result = self.db.execute(query, {"id": str(integration_id)})
            integration_row = result.fetchone()

            if not integration_row:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Integration {integration_id} not found"
                )

            integration = dict(integration_row._mapping)
            platform = Platform(integration["platform"])
            current_status = IntegrationStatus(integration["status"])

            # Initialize health check result
            is_healthy = False
            error_message = None
            metadata = {}

            if test_connection:
                # Decrypt credentials
                credentials_enc = integration.get("credentials_enc")
                if credentials_enc:
                    try:
                        # Decrypt credentials using the same method as integration_service
                        from app.services.integration_service import IntegrationService
                        service = IntegrationService(self.db)
                        credentials_bytes = bytes.fromhex(credentials_enc)
                        credentials = service._decrypt_credentials(credentials_bytes)
                    except Exception as e:
                        logger.error(f"Failed to decrypt credentials: {str(e)}")
                        credentials = {}
                else:
                    credentials = {}

                # Check OAuth token validity if applicable
                try:
                    from app.core.oauth_config import get_provider_for_platform
                    provider = get_provider_for_platform(platform.value)

                    if provider:
                        # This is an OAuth integration - check token validity
                        is_valid = await self.oauth_service.check_token_validity(
                            integration_id=integration_id,
                            auto_refresh=True
                        )

                        if not is_valid:
                            error_message = "OAuth token expired or invalid"
                            current_status = IntegrationStatus.ERROR
                        else:
                            is_healthy = True
                            metadata["token_status"] = "valid"
                    else:
                        # Non-OAuth integration - test connection directly
                        test_result = await test_connector_connection(
                            platform=platform.value,
                            credentials=credentials,
                            config=integration.get("metadata", {})
                        )

                        is_healthy = test_result.get("connected", False)
                        error_message = test_result.get("error")

                        if is_healthy:
                            current_status = IntegrationStatus.CONNECTED
                            metadata["last_successful_connection"] = datetime.utcnow().isoformat()
                        else:
                            current_status = IntegrationStatus.ERROR
                            metadata["last_failed_connection"] = datetime.utcnow().isoformat()

                except Exception as e:
                    logger.error(f"Connection test failed for {integration_id}: {str(e)}")
                    is_healthy = False
                    error_message = f"Connection test failed: {str(e)}"
                    current_status = IntegrationStatus.ERROR

                # Update integration status in database
                # Update metadata with health check results
                existing_metadata = integration.get("metadata", {})
                if existing_metadata is None:
                    existing_metadata = {}
                existing_metadata.update({
                    "last_health_check": datetime.utcnow().isoformat(),
                    "is_healthy": is_healthy,
                    **metadata
                })

                update_query = text('''
                    UPDATE "core"."integrations"
                    SET status = :status, updated_at = :updated_at, metadata = :metadata::jsonb
                    WHERE id = :id
                ''')
                self.db.execute(update_query, {
                    "status": current_status.value,
                    "updated_at": datetime.utcnow().isoformat(),
                    "metadata": json.dumps(existing_metadata),
                    "id": str(integration_id)
                })
                self.db.commit()

            else:
                # Just report current status without testing
                is_healthy = current_status == IntegrationStatus.CONNECTED
                if not is_healthy:
                    error_message = f"Integration status: {current_status.value}"

            # Log health check event
            await self._log_health_check_event(
                integration_id=integration_id,
                platform=platform,
                is_healthy=is_healthy,
                error_message=error_message
            )

            return IntegrationHealthCheck(
                integration_id=integration_id,
                platform=platform,
                status=current_status,
                is_healthy=is_healthy,
                last_checked=datetime.utcnow(),
                error_message=error_message,
                metadata=metadata
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error checking integration health: {str(e)}")
            return IntegrationHealthCheck(
                integration_id=integration_id,
                platform=platform if 'platform' in locals() else Platform.ZOOM,
                status=IntegrationStatus.ERROR,
                is_healthy=False,
                last_checked=datetime.utcnow(),
                error_message=str(e),
                metadata={}
            )

    async def check_all_integrations_health(
        self,
        workspace_id: UUID
    ) -> List[IntegrationHealthCheck]:
        """
        Check health of all integrations in a workspace

        Args:
            workspace_id: Workspace UUID

        Returns:
            List of health check results
        """
        try:
            # Get all integrations for workspace
            query = text('SELECT id FROM "core"."integrations" WHERE workspace_id = :workspace_id')
            result = self.db.execute(query, {"workspace_id": str(workspace_id)})
            integrations = result.fetchall()

            health_checks = []
            for integration in integrations:
                health_check = await self.check_integration_health(
                    integration_id=UUID(integration.id),
                    test_connection=True
                )
                health_checks.append(health_check)

            logger.info(
                f"Completed health checks for {len(health_checks)} integrations "
                f"in workspace {workspace_id}"
            )

            return health_checks

        except Exception as e:
            logger.error(f"Error checking all integrations health: {str(e)}")
            return []

    async def get_health_dashboard(
        self,
        workspace_id: UUID
    ) -> Dict[str, Any]:
        """
        Get health dashboard summary for workspace

        Args:
            workspace_id: Workspace UUID

        Returns:
            Dashboard summary with aggregated health metrics
        """
        try:
            health_checks = await self.check_all_integrations_health(workspace_id)

            # Calculate metrics
            total = len(health_checks)
            healthy = sum(1 for hc in health_checks if hc.is_healthy)
            unhealthy = sum(1 for hc in health_checks if not hc.is_healthy)
            success_rate = (healthy / total * 100) if total > 0 else 0

            # Group by status
            status_counts = {}
            for hc in health_checks:
                status = hc.status.value
                status_counts[status] = status_counts.get(status, 0) + 1

            # Group by platform
            platform_health = {}
            for hc in health_checks:
                platform = hc.platform.value
                if platform not in platform_health:
                    platform_health[platform] = {
                        "total": 0,
                        "healthy": 0,
                        "unhealthy": 0
                    }
                platform_health[platform]["total"] += 1
                if hc.is_healthy:
                    platform_health[platform]["healthy"] += 1
                else:
                    platform_health[platform]["unhealthy"] += 1

            # Get recent errors
            recent_errors = [
                {
                    "integration_id": str(hc.integration_id),
                    "platform": hc.platform.value,
                    "error": hc.error_message,
                    "checked_at": hc.last_checked.isoformat()
                }
                for hc in health_checks
                if hc.error_message
            ][:10]  # Limit to 10 most recent

            dashboard = {
                "workspace_id": str(workspace_id),
                "summary": {
                    "total_integrations": total,
                    "healthy": healthy,
                    "unhealthy": unhealthy,
                    "success_rate": round(success_rate, 2)
                },
                "status_breakdown": status_counts,
                "platform_health": platform_health,
                "recent_errors": recent_errors,
                "last_updated": datetime.utcnow().isoformat()
            }

            return dashboard

        except Exception as e:
            logger.error(f"Error generating health dashboard: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate health dashboard: {str(e)}"
            )

    async def _log_health_check_event(
        self,
        integration_id: UUID,
        platform: Platform,
        is_healthy: bool,
        error_message: Optional[str] = None
    ):
        """
        Log health check event to ops.events table

        Args:
            integration_id: Integration UUID
            platform: Platform
            is_healthy: Whether integration is healthy
            error_message: Optional error message
        """
        try:
            query = text('''
                INSERT INTO "ops"."events"
                (event_type, integration_id, platform, details, created_at)
                VALUES (:event_type, :integration_id, :platform, :details::jsonb, :created_at)
            ''')
            self.db.execute(query, {
                "event_type": "integration_health_check",
                "integration_id": str(integration_id),
                "platform": platform.value,
                "details": json.dumps({
                    "is_healthy": is_healthy,
                    "error_message": error_message,
                    "checked_at": datetime.utcnow().isoformat()
                }),
                "created_at": datetime.utcnow().isoformat()
            })
            self.db.commit()

        except Exception as e:
            # Don't fail health check if event logging fails
            logger.warning(f"Failed to log health check event: {str(e)}")

    async def get_integration_health_history(
        self,
        integration_id: UUID,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get health check history for an integration

        Args:
            integration_id: Integration UUID
            limit: Number of historical records to retrieve

        Returns:
            List of historical health check events
        """
        try:
            query = text('''
                SELECT * FROM "ops"."events"
                WHERE event_type = :event_type
                AND integration_id = :integration_id
                ORDER BY created_at DESC
                LIMIT :limit
            ''')
            result = self.db.execute(query, {
                "event_type": "integration_health_check",
                "integration_id": str(integration_id),
                "limit": limit
            })
            events = result.fetchall()

            return [dict(e._mapping) for e in events]

        except Exception as e:
            logger.error(f"Error fetching health history: {str(e)}")
            return []
