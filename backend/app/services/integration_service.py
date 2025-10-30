"""
Integration Service
Business logic for MCP and API integration management
"""
import logging
from typing import List, Dict, Any, Optional
from uuid import UUID
from datetime import datetime
import json

from supabase import Client
from fastapi import HTTPException, status
from cryptography.fernet import Fernet

from app.models.integration import (
    IntegrationCreate,
    IntegrationUpdate,
    IntegrationResponse,
    IntegrationStatus,
    IntegrationHealthCheck,
    IntegrationStatusResponse,
    Platform
)
from app.config import get_settings

logger = logging.getLogger(__name__)


class IntegrationService:
    """Service for integration management"""

    def __init__(self, db: Client):
        """
        Initialize integration service

        Args:
            db: Supabase database client
        """
        self.db = db
        self.settings = get_settings()

        # Initialize encryption for credentials
        # In production, use KMS or Supabase Vault
        self._init_encryption()

    def _init_encryption(self):
        """Initialize encryption key for credentials"""
        # Generate or load encryption key
        # In production, use environment variable or KMS
        key = self.settings.secret_key.encode()[:32].ljust(32, b'0')
        import base64
        key_b64 = base64.urlsafe_b64encode(key)
        self.cipher = Fernet(key_b64)

    def _encrypt_credentials(self, credentials: Dict[str, Any]) -> bytes:
        """
        Encrypt credentials

        Args:
            credentials: Credentials dictionary

        Returns:
            Encrypted credentials bytes
        """
        try:
            credentials_json = json.dumps(credentials)
            encrypted = self.cipher.encrypt(credentials_json.encode())
            return encrypted
        except Exception as e:
            logger.error(f"Error encrypting credentials: {str(e)}")
            raise

    def _decrypt_credentials(self, encrypted_credentials: bytes) -> Dict[str, Any]:
        """
        Decrypt credentials

        Args:
            encrypted_credentials: Encrypted credentials bytes

        Returns:
            Decrypted credentials dictionary
        """
        try:
            decrypted = self.cipher.decrypt(encrypted_credentials)
            return json.loads(decrypted.decode())
        except Exception as e:
            logger.error(f"Error decrypting credentials: {str(e)}")
            raise

    async def create_integration(
        self,
        integration: IntegrationCreate
    ) -> IntegrationResponse:
        """
        Create a new integration

        Args:
            integration: Integration creation data

        Returns:
            Created integration

        Raises:
            HTTPException: If creation fails
        """
        try:
            # Check for duplicate integration
            existing = self.db.table("core.integrations").select("id").match({
                "workspace_id": str(integration.workspace_id),
                "platform": integration.platform.value,
                "founder_id": str(integration.founder_id) if integration.founder_id else None
            }).execute()

            if existing.data:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Integration for {integration.platform} already exists"
                )

            # Encrypt credentials
            encrypted_creds = self._encrypt_credentials(integration.credentials)

            # Create integration
            integration_data = {
                "workspace_id": str(integration.workspace_id),
                "founder_id": str(integration.founder_id) if integration.founder_id else None,
                "platform": integration.platform.value,
                "connection_type": integration.connection_type.value,
                "status": IntegrationStatus.PENDING.value,
                "credentials_enc": encrypted_creds.hex(),  # Store as hex string
                "metadata": integration.metadata,
                "connected_at": None,
                "updated_at": datetime.utcnow().isoformat()
            }

            response = self.db.table("core.integrations").insert(integration_data).execute()

            if not response.data:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to create integration"
                )

            created = response.data[0]

            # Attempt to connect to the integration
            try:
                await self._test_connection(
                    created["id"],
                    integration.platform,
                    integration.credentials
                )

                # Update status to connected
                self.db.table("core.integrations").update({
                    "status": IntegrationStatus.CONNECTED.value,
                    "connected_at": datetime.utcnow().isoformat()
                }).eq("id", created["id"]).execute()

                created["status"] = IntegrationStatus.CONNECTED.value
                created["connected_at"] = datetime.utcnow().isoformat()

            except Exception as e:
                logger.warning(f"Connection test failed for integration {created['id']}: {str(e)}")
                # Keep status as PENDING or set to ERROR
                self.db.table("core.integrations").update({
                    "status": IntegrationStatus.ERROR.value
                }).eq("id", created["id"]).execute()
                created["status"] = IntegrationStatus.ERROR.value

            logger.info(f"Created integration {created['id']} for platform {integration.platform}")

            # Remove encrypted credentials from response
            created.pop("credentials_enc", None)
            return IntegrationResponse(**created)

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error creating integration: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create integration: {str(e)}"
            )

    async def _test_connection(
        self,
        integration_id: str,
        platform: Platform,
        credentials: Dict[str, Any]
    ) -> bool:
        """
        Test connection to integration platform

        Args:
            integration_id: Integration ID
            platform: Platform to test
            credentials: Platform credentials

        Returns:
            True if connection successful

        Raises:
            Exception: If connection fails
        """
        # Placeholder for actual connection testing
        # In production, implement actual API calls to each platform
        logger.info(f"Testing connection for {platform} integration {integration_id}")

        # Example: Test Zoom connection
        if platform == Platform.ZOOM:
            # Make API call to Zoom to verify credentials
            pass

        # Example: Test Slack connection
        elif platform == Platform.SLACK:
            # Make API call to Slack to verify token
            pass

        # Add more platform-specific tests
        return True

    async def get_integration(self, integration_id: UUID) -> IntegrationResponse:
        """
        Get integration by ID

        Args:
            integration_id: Integration UUID

        Returns:
            Integration data

        Raises:
            HTTPException: If integration not found
        """
        try:
            response = self.db.table("core.integrations").select("*").eq(
                "id", str(integration_id)
            ).execute()

            if not response.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Integration {integration_id} not found"
                )

            integration = response.data[0]
            # Remove encrypted credentials from response
            integration.pop("credentials_enc", None)

            return IntegrationResponse(**integration)

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error fetching integration: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to fetch integration"
            )

    async def list_integrations(
        self,
        workspace_id: UUID,
        founder_id: Optional[UUID] = None,
        platform: Optional[Platform] = None
    ) -> List[IntegrationResponse]:
        """
        List integrations for workspace

        Args:
            workspace_id: Workspace UUID
            founder_id: Optional founder ID filter
            platform: Optional platform filter

        Returns:
            List of integrations
        """
        try:
            query = self.db.table("core.integrations").select("*").eq(
                "workspace_id", str(workspace_id)
            )

            if founder_id:
                query = query.eq("founder_id", str(founder_id))

            if platform:
                query = query.eq("platform", platform.value)

            response = query.execute()

            # Remove encrypted credentials from responses
            for integration in response.data:
                integration.pop("credentials_enc", None)

            return [IntegrationResponse(**i) for i in response.data]

        except Exception as e:
            logger.error(f"Error listing integrations: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to list integrations"
            )

    async def update_integration(
        self,
        integration_id: UUID,
        integration_update: IntegrationUpdate
    ) -> IntegrationResponse:
        """
        Update integration

        Args:
            integration_id: Integration UUID
            integration_update: Update data

        Returns:
            Updated integration

        Raises:
            HTTPException: If update fails
        """
        try:
            update_data = integration_update.dict(exclude_unset=True)

            if not update_data:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No fields to update"
                )

            # Encrypt credentials if provided
            if "credentials" in update_data:
                encrypted_creds = self._encrypt_credentials(update_data["credentials"])
                update_data["credentials_enc"] = encrypted_creds.hex()
                del update_data["credentials"]

            update_data["updated_at"] = datetime.utcnow().isoformat()

            response = self.db.table("core.integrations").update(update_data).eq(
                "id", str(integration_id)
            ).execute()

            if not response.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Integration {integration_id} not found"
                )

            logger.info(f"Updated integration {integration_id}")

            updated = response.data[0]
            updated.pop("credentials_enc", None)
            return IntegrationResponse(**updated)

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error updating integration: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update integration"
            )

    async def delete_integration(self, integration_id: UUID) -> bool:
        """
        Delete integration

        Args:
            integration_id: Integration UUID

        Returns:
            True if deleted successfully

        Raises:
            HTTPException: If deletion fails
        """
        try:
            response = self.db.table("core.integrations").delete().eq(
                "id", str(integration_id)
            ).execute()

            if not response.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Integration {integration_id} not found"
                )

            logger.info(f"Deleted integration {integration_id}")
            return True

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error deleting integration: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete integration"
            )

    async def check_integration_health(
        self,
        integration_id: UUID
    ) -> IntegrationHealthCheck:
        """
        Check health of an integration

        Args:
            integration_id: Integration UUID

        Returns:
            Health check result
        """
        try:
            integration = await self.get_integration(integration_id)

            # Perform health check based on platform
            is_healthy = integration.status == IntegrationStatus.CONNECTED
            error_message = None if is_healthy else f"Integration status: {integration.status}"

            return IntegrationHealthCheck(
                integration_id=integration.id,
                platform=Platform(integration.platform),
                status=IntegrationStatus(integration.status),
                is_healthy=is_healthy,
                last_checked=datetime.utcnow(),
                error_message=error_message,
                metadata=integration.metadata
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error checking integration health: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to check integration health"
            )

    async def get_integration_status(
        self,
        workspace_id: UUID
    ) -> IntegrationStatusResponse:
        """
        Get overall integration status for workspace

        Args:
            workspace_id: Workspace UUID

        Returns:
            Integration status summary
        """
        try:
            integrations = await self.list_integrations(workspace_id)

            # Perform health checks on all integrations
            health_checks = []
            for integration in integrations:
                health_check = await self.check_integration_health(integration.id)
                health_checks.append(health_check)

            # Count by status
            connected = sum(1 for hc in health_checks if hc.status == IntegrationStatus.CONNECTED)
            error = sum(1 for hc in health_checks if hc.status == IntegrationStatus.ERROR)
            pending = sum(1 for hc in health_checks if hc.status == IntegrationStatus.PENDING)

            return IntegrationStatusResponse(
                workspace_id=workspace_id,
                total_integrations=len(integrations),
                connected=connected,
                error=error,
                pending=pending,
                integrations=health_checks
            )

        except Exception as e:
            logger.error(f"Error getting integration status: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to get integration status"
            )
