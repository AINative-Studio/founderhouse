"""
Comprehensive tests for Integration Service
Tests OAuth integrations, token refresh, status management, encryption, and error handling
Coverage target: 17% -> 75%+
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
from datetime import datetime, timedelta
from uuid import uuid4, UUID
import json
import base64
from cryptography.fernet import Fernet

from fastapi import HTTPException, status

from app.services.integration_service import IntegrationService
from app.models.integration import (
    IntegrationCreate,
    IntegrationUpdate,
    IntegrationResponse,
    IntegrationStatus,
    IntegrationHealthCheck,
    IntegrationStatusResponse,
    Platform,
    ConnectionType
)


def create_mock_integration_row(integration_id=None, workspace_id=None, founder_id=None,
                               platform="slack", status_val="connected", metadata=None):
    """Helper to create proper mock integration row"""
    if integration_id is None:
        integration_id = uuid4()
    if workspace_id is None:
        workspace_id = uuid4()

    mock_row = MagicMock()
    mock_row._mapping = {
        "id": str(integration_id),
        "workspace_id": str(workspace_id),
        "founder_id": str(founder_id) if founder_id else None,
        "platform": platform,
        "connection_type": "api",
        "status": status_val,
        "credentials_enc": "encrypted_data",
        "metadata": metadata or {},
        "connected_at": datetime.utcnow().isoformat() if status_val == "connected" else None,
        "updated_at": datetime.utcnow().isoformat()
    }
    return mock_row, integration_id, workspace_id


class TestIntegrationServiceSetup:
    """Tests for service initialization and encryption setup"""

    @pytest.fixture
    def mock_db(self):
        return MagicMock()

    @pytest.fixture
    def mock_settings(self):
        settings = MagicMock()
        settings.secret_key = "test-secret-key-for-testing-only-minimum-32-chars"
        return settings

    def test_service_initialization(self, mock_db, mock_settings):
        """Test service initialization"""
        with patch('app.services.integration_service.get_settings', return_value=mock_settings):
            service = IntegrationService(mock_db)
            assert service.db == mock_db
            assert service.settings == mock_settings
            assert hasattr(service, 'cipher')

    def test_encryption_key_generation(self, mock_db, mock_settings):
        """Test encryption key is properly initialized"""
        with patch('app.services.integration_service.get_settings', return_value=mock_settings):
            service = IntegrationService(mock_db)
            assert service.cipher is not None
            assert isinstance(service.cipher, Fernet)

    def test_encrypt_decrypt_credentials(self, mock_db, mock_settings):
        """Test credentials encryption and decryption"""
        with patch('app.services.integration_service.get_settings', return_value=mock_settings):
            service = IntegrationService(mock_db)

            credentials = {
                "access_token": "token123",
                "refresh_token": "refresh456",
                "expires_at": 1234567890
            }

            encrypted = service._encrypt_credentials(credentials)
            assert isinstance(encrypted, bytes)
            assert encrypted != json.dumps(credentials).encode()

            decrypted = service._decrypt_credentials(encrypted)
            assert decrypted == credentials

    def test_encrypt_empty_credentials(self, mock_db, mock_settings):
        """Test encrypting empty credentials"""
        with patch('app.services.integration_service.get_settings', return_value=mock_settings):
            service = IntegrationService(mock_db)

            credentials = {}
            encrypted = service._encrypt_credentials(credentials)
            decrypted = service._decrypt_credentials(encrypted)
            assert decrypted == {}

    def test_encrypt_complex_credentials(self, mock_db, mock_settings):
        """Test encrypting complex nested credentials"""
        with patch('app.services.integration_service.get_settings', return_value=mock_settings):
            service = IntegrationService(mock_db)

            credentials = {
                "client_id": "client123",
                "client_secret": "secret456",
                "scopes": ["read", "write", "admin"],
                "user_info": {
                    "name": "Test User",
                    "email": "test@example.com",
                    "settings": {
                        "auto_sync": True,
                        "rate_limit": 1000
                    }
                }
            }

            encrypted = service._encrypt_credentials(credentials)
            decrypted = service._decrypt_credentials(encrypted)
            assert decrypted == credentials

    def test_decrypt_invalid_credentials_raises_exception(self, mock_db, mock_settings):
        """Test decrypting corrupted credentials raises exception"""
        with patch('app.services.integration_service.get_settings', return_value=mock_settings):
            service = IntegrationService(mock_db)
            invalid_encrypted = b"invalid_encrypted_data"

            with pytest.raises(Exception):
                service._decrypt_credentials(invalid_encrypted)

    def test_encrypt_credentials_with_special_characters(self, mock_db, mock_settings):
        """Test encrypting credentials with special characters"""
        with patch('app.services.integration_service.get_settings', return_value=mock_settings):
            service = IntegrationService(mock_db)

            credentials = {
                "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9",
                "secret": "abc!@#$%^&*()_+-=[]{}|;:',.<>?/~`",
                "unicode": "你好世界🌍"
            }

            encrypted = service._encrypt_credentials(credentials)
            decrypted = service._decrypt_credentials(encrypted)
            assert decrypted == credentials


class TestCreateIntegration:
    """Tests for creating new integrations"""

    @pytest.fixture
    def mock_db(self):
        return MagicMock()

    @pytest.fixture
    def mock_settings(self):
        settings = MagicMock()
        settings.secret_key = "test-secret-key-for-testing-only-minimum-32-chars"
        return settings

    @pytest.fixture
    def service(self, mock_db, mock_settings):
        with patch('app.services.integration_service.get_settings', return_value=mock_settings):
            return IntegrationService(mock_db)

    @pytest.fixture
    def workspace_id(self):
        return uuid4()

    @pytest.fixture
    def founder_id(self):
        return uuid4()

    @pytest.mark.asyncio
    async def test_create_integration_success_connected(self, service, mock_db, workspace_id, founder_id):
        """Test successful integration creation with immediate connection"""
        integration_data = IntegrationCreate(
            workspace_id=workspace_id,
            founder_id=founder_id,
            platform=Platform.SLACK,
            connection_type=ConnectionType.API,
            credentials={"access_token": "xoxb-token123", "team_id": "T123456789"},
            metadata={"display_name": "Test Slack"}
        )

        mock_result_check = MagicMock()
        mock_result_check.fetchone.return_value = None

        mock_row, int_id, ws_id = create_mock_integration_row(
            workspace_id=workspace_id,
            founder_id=founder_id,
            platform="slack",
            status_val="connected",
            metadata={"display_name": "Test Slack"}
        )

        mock_result_insert = MagicMock()
        mock_result_insert.fetchone.return_value = mock_row

        mock_db.execute.side_effect = [
            mock_result_check,
            mock_result_insert,
            MagicMock()
        ]
        mock_db.commit = MagicMock()

        with patch.object(service, '_test_connection', new_callable=AsyncMock, return_value=True):
            result = await service.create_integration(integration_data)

        assert result.platform == "slack"
        assert result.workspace_id == workspace_id
        assert result.status == "connected"

    @pytest.mark.asyncio
    async def test_create_integration_duplicate_raises_conflict(self, service, mock_db, workspace_id, founder_id):
        """Test creating duplicate integration raises 409 conflict"""
        integration_data = IntegrationCreate(
            workspace_id=workspace_id,
            founder_id=founder_id,
            platform=Platform.SLACK,
            credentials={"access_token": "token", "team_id": "T123"}
        )

        mock_result = MagicMock()
        mock_result.fetchone.return_value = MagicMock(id="existing-123")
        mock_db.execute.return_value = mock_result

        with pytest.raises(HTTPException) as exc_info:
            await service.create_integration(integration_data)

        assert exc_info.value.status_code == status.HTTP_409_CONFLICT
        assert "already exists" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_create_integration_without_founder_id(self, service, mock_db, workspace_id):
        """Test creating workspace-level integration without founder_id"""
        integration_data = IntegrationCreate(
            workspace_id=workspace_id,
            founder_id=None,
            platform=Platform.ZOOM,
            credentials={"client_id": "zoom-client", "client_secret": "zoom-secret"}
        )

        mock_result_check = MagicMock()
        mock_result_check.fetchone.return_value = None

        mock_row, _, _ = create_mock_integration_row(
            workspace_id=workspace_id,
            founder_id=None,
            platform="zoom",
            status_val="connected"
        )

        mock_result_insert = MagicMock()
        mock_result_insert.fetchone.return_value = mock_row

        mock_db.execute.side_effect = [mock_result_check, mock_result_insert, MagicMock()]
        mock_db.commit = MagicMock()

        with patch.object(service, '_test_connection', new_callable=AsyncMock, return_value=True):
            result = await service.create_integration(integration_data)

        assert result.founder_id is None
        assert result.platform == "zoom"

    @pytest.mark.asyncio
    async def test_create_integration_connection_fails_sets_error_status(self, service, mock_db, workspace_id, founder_id):
        """Test integration with failed connection test sets ERROR status"""
        integration_data = IntegrationCreate(
            workspace_id=workspace_id,
            founder_id=founder_id,
            platform=Platform.SLACK,
            credentials={"access_token": "token", "team_id": "T123"}
        )

        mock_result_check = MagicMock()
        mock_result_check.fetchone.return_value = None

        mock_row, _, _ = create_mock_integration_row(
            workspace_id=workspace_id,
            founder_id=founder_id,
            status_val="error"
        )

        mock_result_insert = MagicMock()
        mock_result_insert.fetchone.return_value = mock_row

        mock_db.execute.side_effect = [mock_result_check, mock_result_insert, MagicMock()]
        mock_db.commit = MagicMock()

        with patch.object(service, '_test_connection', new_callable=AsyncMock,
                         side_effect=Exception("Connection failed")):
            result = await service.create_integration(integration_data)

        assert result.status == "error"

    @pytest.mark.asyncio
    async def test_create_integration_database_error_raises_500(self, service, mock_db, workspace_id, founder_id):
        """Test database error during creation raises 500"""
        integration_data = IntegrationCreate(
            workspace_id=workspace_id,
            founder_id=founder_id,
            platform=Platform.SLACK,
            credentials={"access_token": "token", "team_id": "T123"}
        )

        mock_db.execute.side_effect = Exception("Database connection error")

        with pytest.raises(HTTPException) as exc_info:
            await service.create_integration(integration_data)

        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    @pytest.mark.asyncio
    async def test_create_integration_insert_fails_raises_500(self, service, mock_db, workspace_id, founder_id):
        """Test insert returning None raises 500 error"""
        integration_data = IntegrationCreate(
            workspace_id=workspace_id,
            founder_id=founder_id,
            platform=Platform.SLACK,
            credentials={"access_token": "token", "team_id": "T123"}
        )

        mock_result_check = MagicMock()
        mock_result_check.fetchone.return_value = None

        mock_result_insert = MagicMock()
        mock_result_insert.fetchone.return_value = None

        mock_db.execute.side_effect = [mock_result_check, mock_result_insert]
        mock_db.commit = MagicMock()

        with pytest.raises(HTTPException) as exc_info:
            await service.create_integration(integration_data)

        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to create integration" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_create_integration_with_all_platforms(self, service, mock_db, workspace_id, founder_id):
        """Test creating integrations for all supported platforms"""
        platform_credentials = {
            Platform.SLACK: {"access_token": "token", "team_id": "T123"},
            Platform.ZOOM: {"client_id": "zoom-id", "client_secret": "zoom-secret"},
            Platform.DISCORD: {"bot_token": "discord-token"},
            Platform.MONDAY: {"api_token": "monday-token"},
            Platform.NOTION: {"access_token": "notion-token"}
        }

        for platform, creds in platform_credentials.items():
            integration_data = IntegrationCreate(
                workspace_id=workspace_id,
                founder_id=founder_id,
                platform=platform,
                credentials=creds
            )

            mock_result_check = MagicMock()
            mock_result_check.fetchone.return_value = None

            mock_row, _, _ = create_mock_integration_row(
                workspace_id=workspace_id,
                founder_id=founder_id,
                platform=platform.value,
                status_val="connected"
            )

            mock_result_insert = MagicMock()
            mock_result_insert.fetchone.return_value = mock_row

            mock_db.execute.side_effect = [mock_result_check, mock_result_insert, MagicMock()]
            mock_db.commit = MagicMock()

            with patch.object(service, '_test_connection', new_callable=AsyncMock, return_value=True):
                result = await service.create_integration(integration_data)
                assert result.platform == platform.value

    @pytest.mark.asyncio
    async def test_create_integration_with_metadata(self, service, mock_db, workspace_id, founder_id):
        """Test creating integration with rich metadata"""
        metadata = {
            "display_name": "My Integration",
            "tags": ["production", "critical"],
            "settings": {"auto_sync": True, "rate_limit": 500}
        }

        integration_data = IntegrationCreate(
            workspace_id=workspace_id,
            founder_id=founder_id,
            platform=Platform.DISCORD,
            credentials={"bot_token": "token123"},
            metadata=metadata
        )

        mock_result_check = MagicMock()
        mock_result_check.fetchone.return_value = None

        mock_row, _, _ = create_mock_integration_row(
            workspace_id=workspace_id,
            founder_id=founder_id,
            platform="discord",
            metadata=metadata
        )

        mock_result_insert = MagicMock()
        mock_result_insert.fetchone.return_value = mock_row

        mock_db.execute.side_effect = [mock_result_check, mock_result_insert, MagicMock()]
        mock_db.commit = MagicMock()

        with patch.object(service, '_test_connection', new_callable=AsyncMock, return_value=True):
            result = await service.create_integration(integration_data)
            assert result.metadata == metadata


class TestGetIntegration:
    """Tests for retrieving integrations"""

    @pytest.fixture
    def mock_db(self):
        return MagicMock()

    @pytest.fixture
    def mock_settings(self):
        settings = MagicMock()
        settings.secret_key = "test-secret-key-for-testing-only-minimum-32-chars"
        return settings

    @pytest.fixture
    def service(self, mock_db, mock_settings):
        with patch('app.services.integration_service.get_settings', return_value=mock_settings):
            return IntegrationService(mock_db)

    @pytest.mark.asyncio
    async def test_get_integration_by_id_success(self, service, mock_db):
        """Test retrieving integration by ID"""
        integration_id = uuid4()
        workspace_id = uuid4()

        mock_row, _, _ = create_mock_integration_row(integration_id=integration_id, workspace_id=workspace_id)

        mock_result = MagicMock()
        mock_result.fetchone.return_value = mock_row
        mock_db.execute.return_value = mock_result

        result = await service.get_integration(integration_id)

        assert str(result.id) == str(integration_id)
        assert result.platform == "slack"

    @pytest.mark.asyncio
    async def test_get_integration_not_found_raises_404(self, service, mock_db):
        """Test retrieving non-existent integration raises 404"""
        integration_id = uuid4()

        mock_result = MagicMock()
        mock_result.fetchone.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(HTTPException) as exc_info:
            await service.get_integration(integration_id)

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_integration_database_error(self, service, mock_db):
        """Test database error when retrieving integration"""
        integration_id = uuid4()
        mock_db.execute.side_effect = Exception("Database error")

        with pytest.raises(HTTPException) as exc_info:
            await service.get_integration(integration_id)

        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


class TestListIntegrations:
    """Tests for listing integrations"""

    @pytest.fixture
    def mock_db(self):
        return MagicMock()

    @pytest.fixture
    def mock_settings(self):
        settings = MagicMock()
        settings.secret_key = "test-secret-key-for-testing-only-minimum-32-chars"
        return settings

    @pytest.fixture
    def service(self, mock_db, mock_settings):
        with patch('app.services.integration_service.get_settings', return_value=mock_settings):
            return IntegrationService(mock_db)

    @pytest.mark.asyncio
    async def test_list_integrations_for_workspace(self, service, mock_db):
        """Test listing all integrations for workspace"""
        workspace_id = uuid4()

        rows = []
        for i, platform in enumerate(["slack", "zoom", "discord"]):
            mock_row, _, _ = create_mock_integration_row(workspace_id=workspace_id, platform=platform)
            rows.append(mock_row)

        mock_result = MagicMock()
        mock_result.fetchall.return_value = rows
        mock_db.execute.return_value = mock_result

        result = await service.list_integrations(workspace_id)

        assert len(result) == 3
        assert all(isinstance(r, IntegrationResponse) for r in result)
        assert all(r.workspace_id == workspace_id for r in result)

    @pytest.mark.asyncio
    async def test_list_integrations_with_founder_filter(self, service, mock_db):
        """Test listing integrations filtered by founder"""
        workspace_id = uuid4()
        founder_id = uuid4()

        mock_row, _, _ = create_mock_integration_row(workspace_id=workspace_id, founder_id=founder_id)

        mock_result = MagicMock()
        mock_result.fetchall.return_value = [mock_row]
        mock_db.execute.return_value = mock_result

        result = await service.list_integrations(workspace_id, founder_id=founder_id)

        assert len(result) == 1
        assert str(result[0].founder_id) == str(founder_id)

    @pytest.mark.asyncio
    async def test_list_integrations_with_platform_filter(self, service, mock_db):
        """Test listing integrations filtered by platform"""
        workspace_id = uuid4()

        mock_row, _, _ = create_mock_integration_row(workspace_id=workspace_id, platform="zoom")

        mock_result = MagicMock()
        mock_result.fetchall.return_value = [mock_row]
        mock_db.execute.return_value = mock_result

        result = await service.list_integrations(workspace_id, platform=Platform.ZOOM)

        assert len(result) == 1
        assert result[0].platform == "zoom"

    @pytest.mark.asyncio
    async def test_list_integrations_with_all_filters(self, service, mock_db):
        """Test listing integrations with all filters applied"""
        workspace_id = uuid4()
        founder_id = uuid4()

        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_db.execute.return_value = mock_result

        result = await service.list_integrations(workspace_id, founder_id=founder_id, platform=Platform.SLACK)

        assert result == []

    @pytest.mark.asyncio
    async def test_list_integrations_empty_workspace(self, service, mock_db):
        """Test listing integrations from workspace with no integrations"""
        workspace_id = uuid4()

        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_db.execute.return_value = mock_result

        result = await service.list_integrations(workspace_id)

        assert result == []

    @pytest.mark.asyncio
    async def test_list_integrations_database_error(self, service, mock_db):
        """Test database error when listing integrations"""
        workspace_id = uuid4()
        mock_db.execute.side_effect = Exception("Database error")

        with pytest.raises(HTTPException) as exc_info:
            await service.list_integrations(workspace_id)

        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    @pytest.mark.asyncio
    async def test_list_integrations_with_many_results(self, service, mock_db):
        """Test listing integrations with large result set"""
        workspace_id = uuid4()

        rows = []
        for i in range(100):
            mock_row, _, _ = create_mock_integration_row(workspace_id=workspace_id)
            rows.append(mock_row)

        mock_result = MagicMock()
        mock_result.fetchall.return_value = rows
        mock_db.execute.return_value = mock_result

        result = await service.list_integrations(workspace_id)

        assert len(result) == 100
        assert all(isinstance(r, IntegrationResponse) for r in result)


class TestUpdateIntegration:
    """Tests for updating integrations"""

    @pytest.fixture
    def mock_db(self):
        return MagicMock()

    @pytest.fixture
    def mock_settings(self):
        settings = MagicMock()
        settings.secret_key = "test-secret-key-for-testing-only-minimum-32-chars"
        return settings

    @pytest.fixture
    def service(self, mock_db, mock_settings):
        with patch('app.services.integration_service.get_settings', return_value=mock_settings):
            return IntegrationService(mock_db)

    @pytest.mark.asyncio
    async def test_update_integration_status(self, service, mock_db):
        """Test updating integration status"""
        integration_id = uuid4()

        update_data = IntegrationUpdate(status=IntegrationStatus.REVOKED)

        mock_row, _, _ = create_mock_integration_row(integration_id=integration_id, status_val="revoked")

        mock_result = MagicMock()
        mock_result.fetchone.return_value = mock_row
        mock_db.execute.return_value = mock_result
        mock_db.commit = MagicMock()

        result = await service.update_integration(integration_id, update_data)

        assert result.status == "revoked"
        assert str(result.id) == str(integration_id)

    @pytest.mark.asyncio
    async def test_update_integration_credentials(self, service, mock_db):
        """Test updating integration credentials"""
        integration_id = uuid4()

        new_credentials = {"access_token": "new-token", "refresh_token": "new-refresh"}
        update_data = IntegrationUpdate(credentials=new_credentials)

        mock_row, _, _ = create_mock_integration_row(integration_id=integration_id)

        mock_result = MagicMock()
        mock_result.fetchone.return_value = mock_row
        mock_db.execute.return_value = mock_result
        mock_db.commit = MagicMock()

        result = await service.update_integration(integration_id, update_data)

        assert str(result.id) == str(integration_id)

    @pytest.mark.asyncio
    async def test_update_integration_metadata(self, service, mock_db):
        """Test updating integration metadata"""
        integration_id = uuid4()

        new_metadata = {"display_name": "Updated Name", "tags": ["updated"]}
        update_data = IntegrationUpdate(metadata=new_metadata)

        mock_row, _, _ = create_mock_integration_row(integration_id=integration_id, metadata=new_metadata)

        mock_result = MagicMock()
        mock_result.fetchone.return_value = mock_row
        mock_db.execute.return_value = mock_result
        mock_db.commit = MagicMock()

        result = await service.update_integration(integration_id, update_data)

        assert result.metadata == new_metadata

    @pytest.mark.asyncio
    async def test_update_integration_all_fields(self, service, mock_db):
        """Test updating all integration fields"""
        integration_id = uuid4()

        update_data = IntegrationUpdate(
            status=IntegrationStatus.CONNECTED,
            credentials={"new_token": "token123"},
            metadata={"new_field": "value"}
        )

        mock_row, _, _ = create_mock_integration_row(integration_id=integration_id, metadata={"new_field": "value"})

        mock_result = MagicMock()
        mock_result.fetchone.return_value = mock_row
        mock_db.execute.return_value = mock_result
        mock_db.commit = MagicMock()

        result = await service.update_integration(integration_id, update_data)

        assert result.status == "connected"

    @pytest.mark.asyncio
    async def test_update_integration_no_fields_raises_400(self, service, mock_db):
        """Test updating with no fields raises 400 error"""
        integration_id = uuid4()
        update_data = IntegrationUpdate()

        with pytest.raises(HTTPException) as exc_info:
            await service.update_integration(integration_id, update_data)

        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "No fields to update" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_update_integration_not_found(self, service, mock_db):
        """Test updating non-existent integration"""
        integration_id = uuid4()
        update_data = IntegrationUpdate(status=IntegrationStatus.REVOKED)

        mock_result = MagicMock()
        mock_result.fetchone.return_value = None
        mock_db.execute.return_value = mock_result
        mock_db.commit = MagicMock()

        with pytest.raises(HTTPException) as exc_info:
            await service.update_integration(integration_id, update_data)

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_update_integration_database_error(self, service, mock_db):
        """Test database error during update"""
        integration_id = uuid4()
        update_data = IntegrationUpdate(status=IntegrationStatus.REVOKED)

        mock_db.execute.side_effect = Exception("Database error")

        with pytest.raises(HTTPException) as exc_info:
            await service.update_integration(integration_id, update_data)

        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    @pytest.mark.asyncio
    async def test_update_integration_preserves_unchanged_fields(self, service, mock_db):
        """Test update only changes specified fields"""
        integration_id = uuid4()
        workspace_id = uuid4()
        original_platform = "slack"

        update_data = IntegrationUpdate(status=IntegrationStatus.REVOKED)

        mock_row, _, _ = create_mock_integration_row(
            integration_id=integration_id,
            workspace_id=workspace_id,
            platform=original_platform,
            status_val="revoked"
        )

        mock_result = MagicMock()
        mock_result.fetchone.return_value = mock_row
        mock_db.execute.return_value = mock_result
        mock_db.commit = MagicMock()

        result = await service.update_integration(integration_id, update_data)

        assert result.platform == original_platform
        assert result.status == "revoked"


class TestDeleteIntegration:
    """Tests for deleting integrations"""

    @pytest.fixture
    def mock_db(self):
        return MagicMock()

    @pytest.fixture
    def mock_settings(self):
        settings = MagicMock()
        settings.secret_key = "test-secret-key-for-testing-only-minimum-32-chars"
        return settings

    @pytest.fixture
    def service(self, mock_db, mock_settings):
        with patch('app.services.integration_service.get_settings', return_value=mock_settings):
            return IntegrationService(mock_db)

    @pytest.mark.asyncio
    async def test_delete_integration_success(self, service, mock_db):
        """Test successful integration deletion"""
        integration_id = uuid4()

        mock_row, _, _ = create_mock_integration_row(integration_id=integration_id)

        mock_result = MagicMock()
        mock_result.fetchone.return_value = mock_row
        mock_db.execute.return_value = mock_result
        mock_db.commit = MagicMock()

        result = await service.delete_integration(integration_id)

        assert result is True
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_integration_not_found(self, service, mock_db):
        """Test deleting non-existent integration"""
        integration_id = uuid4()

        mock_result = MagicMock()
        mock_result.fetchone.return_value = None
        mock_db.execute.return_value = mock_result
        mock_db.commit = MagicMock()

        with pytest.raises(HTTPException) as exc_info:
            await service.delete_integration(integration_id)

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_delete_integration_database_error(self, service, mock_db):
        """Test database error during deletion"""
        integration_id = uuid4()
        mock_db.execute.side_effect = Exception("Database error")

        with pytest.raises(HTTPException) as exc_info:
            await service.delete_integration(integration_id)

        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    @pytest.mark.asyncio
    async def test_delete_multiple_integrations(self, service, mock_db):
        """Test deleting multiple integrations"""
        integration_ids = [uuid4() for _ in range(3)]

        for integration_id in integration_ids:
            mock_row, _, _ = create_mock_integration_row(integration_id=integration_id)

            mock_result = MagicMock()
            mock_result.fetchone.return_value = mock_row
            mock_db.execute.return_value = mock_result
            mock_db.commit = MagicMock()

            result = await service.delete_integration(integration_id)
            assert result is True


class TestIntegrationHealthCheck:
    """Tests for integration health checks"""

    @pytest.fixture
    def mock_db(self):
        return MagicMock()

    @pytest.fixture
    def mock_settings(self):
        settings = MagicMock()
        settings.secret_key = "test-secret-key-for-testing-only-minimum-32-chars"
        return settings

    @pytest.fixture
    def service(self, mock_db, mock_settings):
        with patch('app.services.integration_service.get_settings', return_value=mock_settings):
            return IntegrationService(mock_db)

    @pytest.mark.asyncio
    async def test_check_integration_health_connected(self, service, mock_db):
        """Test health check for connected integration"""
        integration_id = uuid4()

        mock_row, _, _ = create_mock_integration_row(integration_id=integration_id, status_val="connected")

        mock_result = MagicMock()
        mock_result.fetchone.return_value = mock_row
        mock_db.execute.return_value = mock_result

        result = await service.check_integration_health(integration_id)

        assert result.is_healthy is True
        assert result.error_message is None
        assert result.status == IntegrationStatus.CONNECTED

    @pytest.mark.asyncio
    async def test_check_integration_health_error_status(self, service, mock_db):
        """Test health check for integration with error status"""
        integration_id = uuid4()

        mock_row, _, _ = create_mock_integration_row(integration_id=integration_id, status_val="error")

        mock_result = MagicMock()
        mock_result.fetchone.return_value = mock_row
        mock_db.execute.return_value = mock_result

        result = await service.check_integration_health(integration_id)

        assert result.is_healthy is False
        assert result.error_message is not None
        assert "error" in result.error_message

    @pytest.mark.asyncio
    async def test_check_integration_health_pending_status(self, service, mock_db):
        """Test health check for integration with pending status"""
        integration_id = uuid4()

        mock_row, _, _ = create_mock_integration_row(integration_id=integration_id, status_val="pending")

        mock_result = MagicMock()
        mock_result.fetchone.return_value = mock_row
        mock_db.execute.return_value = mock_result

        result = await service.check_integration_health(integration_id)

        assert result.is_healthy is False
        assert result.status == IntegrationStatus.PENDING

    @pytest.mark.asyncio
    async def test_check_integration_health_not_found(self, service, mock_db):
        """Test health check for non-existent integration"""
        integration_id = uuid4()

        mock_result = MagicMock()
        mock_result.fetchone.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(HTTPException) as exc_info:
            await service.check_integration_health(integration_id)

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_check_integration_health_with_metadata(self, service, mock_db):
        """Test health check includes integration metadata"""
        integration_id = uuid4()
        metadata = {"api_version": "v2", "rate_limit": 1000}

        mock_row, _, _ = create_mock_integration_row(
            integration_id=integration_id,
            status_val="connected",
            metadata=metadata
        )

        mock_result = MagicMock()
        mock_result.fetchone.return_value = mock_row
        mock_db.execute.return_value = mock_result

        result = await service.check_integration_health(integration_id)

        assert result.metadata == metadata


class TestGetIntegrationStatus:
    """Tests for overall integration status"""

    @pytest.fixture
    def mock_db(self):
        return MagicMock()

    @pytest.fixture
    def mock_settings(self):
        settings = MagicMock()
        settings.secret_key = "test-secret-key-for-testing-only-minimum-32-chars"
        return settings

    @pytest.fixture
    def service(self, mock_db, mock_settings):
        with patch('app.services.integration_service.get_settings', return_value=mock_settings):
            return IntegrationService(mock_db)

    @pytest.mark.asyncio
    async def test_get_integration_status_multiple_integrations(self, service, mock_db):
        """Test getting status for workspace with multiple integrations"""
        workspace_id = uuid4()

        # Create proper integration responses
        mock_integrations = [
            MagicMock(spec=IntegrationResponse, id=uuid4(), workspace_id=workspace_id,
                     platform="slack", status="connected", metadata={}, connection_type="api",
                     founder_id=None, connected_at=datetime.utcnow(), updated_at=datetime.utcnow()),
            MagicMock(spec=IntegrationResponse, id=uuid4(), workspace_id=workspace_id,
                     platform="zoom", status="connected", metadata={}, connection_type="api",
                     founder_id=None, connected_at=datetime.utcnow(), updated_at=datetime.utcnow()),
            MagicMock(spec=IntegrationResponse, id=uuid4(), workspace_id=workspace_id,
                     platform="discord", status="error", metadata={}, connection_type="api",
                     founder_id=None, connected_at=None, updated_at=datetime.utcnow())
        ]

        with patch.object(service, 'list_integrations', new_callable=AsyncMock, return_value=mock_integrations):
            with patch.object(service, 'check_integration_health', new_callable=AsyncMock) as mock_health:
                health_responses = [
                    MagicMock(spec=IntegrationHealthCheck, status=IntegrationStatus.CONNECTED,
                             is_healthy=True, integration_id=mock_integrations[0].id, platform=Platform.SLACK,
                             last_checked=datetime.utcnow(), error_message=None, metadata={}),
                    MagicMock(spec=IntegrationHealthCheck, status=IntegrationStatus.CONNECTED,
                             is_healthy=True, integration_id=mock_integrations[1].id, platform=Platform.ZOOM,
                             last_checked=datetime.utcnow(), error_message=None, metadata={}),
                    MagicMock(spec=IntegrationHealthCheck, status=IntegrationStatus.ERROR,
                             is_healthy=False, integration_id=mock_integrations[2].id, platform=Platform.DISCORD,
                             last_checked=datetime.utcnow(), error_message="error", metadata={})
                ]
                mock_health.side_effect = health_responses

                result = await service.get_integration_status(workspace_id)

                assert result.workspace_id == workspace_id
                assert result.total_integrations == 3
                assert result.connected == 2
                assert result.error == 1

    @pytest.mark.asyncio
    async def test_get_integration_status_empty_workspace(self, service, mock_db):
        """Test status for workspace with no integrations"""
        workspace_id = uuid4()

        with patch.object(service, 'list_integrations', new_callable=AsyncMock, return_value=[]):
            result = await service.get_integration_status(workspace_id)

            assert result.workspace_id == workspace_id
            assert result.total_integrations == 0
            assert result.connected == 0
            assert result.error == 0
            assert result.pending == 0

    @pytest.mark.asyncio
    async def test_get_integration_status_all_connected(self, service, mock_db):
        """Test status when all integrations are connected"""
        workspace_id = uuid4()

        mock_integrations = [
            MagicMock(spec=IntegrationResponse, id=uuid4(), workspace_id=workspace_id,
                     platform="slack", status="connected", metadata={}, connection_type="api",
                     founder_id=None, connected_at=datetime.utcnow(), updated_at=datetime.utcnow()),
            MagicMock(spec=IntegrationResponse, id=uuid4(), workspace_id=workspace_id,
                     platform="slack", status="connected", metadata={}, connection_type="api",
                     founder_id=None, connected_at=datetime.utcnow(), updated_at=datetime.utcnow())
        ]

        with patch.object(service, 'list_integrations', new_callable=AsyncMock, return_value=mock_integrations):
            with patch.object(service, 'check_integration_health', new_callable=AsyncMock) as mock_health:
                health_responses = [
                    MagicMock(spec=IntegrationHealthCheck, status=IntegrationStatus.CONNECTED,
                             is_healthy=True, integration_id=mock_integrations[0].id, platform=Platform.SLACK,
                             last_checked=datetime.utcnow(), error_message=None, metadata={}),
                    MagicMock(spec=IntegrationHealthCheck, status=IntegrationStatus.CONNECTED,
                             is_healthy=True, integration_id=mock_integrations[1].id, platform=Platform.SLACK,
                             last_checked=datetime.utcnow(), error_message=None, metadata={})
                ]
                mock_health.side_effect = health_responses

                result = await service.get_integration_status(workspace_id)

                assert result.connected == 2
                assert result.error == 0
                assert result.pending == 0


class TestTokenRefresh:
    """Tests for token refresh flows"""

    @pytest.fixture
    def mock_db(self):
        return MagicMock()

    @pytest.fixture
    def mock_settings(self):
        settings = MagicMock()
        settings.secret_key = "test-secret-key-for-testing-only-minimum-32-chars"
        return settings

    @pytest.fixture
    def service(self, mock_db, mock_settings):
        with patch('app.services.integration_service.get_settings', return_value=mock_settings):
            return IntegrationService(mock_db)

    @pytest.mark.asyncio
    async def test_refresh_token_updates_credentials(self, service, mock_db):
        """Test that token refresh updates stored credentials"""
        integration_id = uuid4()

        new_credentials = {"access_token": "new_token", "refresh_token": "refresh_token", "expires_at": 2000000}
        update_data = IntegrationUpdate(credentials=new_credentials)

        mock_row, _, _ = create_mock_integration_row(integration_id=integration_id)

        mock_result = MagicMock()
        mock_result.fetchone.return_value = mock_row
        mock_db.execute.return_value = mock_result
        mock_db.commit = MagicMock()

        result = await service.update_integration(integration_id, update_data)

        assert str(result.id) == str(integration_id)
        assert mock_db.commit.called


class TestTestConnection:
    """Tests for connection testing"""

    @pytest.fixture
    def mock_db(self):
        return MagicMock()

    @pytest.fixture
    def mock_settings(self):
        settings = MagicMock()
        settings.secret_key = "test-secret-key-for-testing-only-minimum-32-chars"
        return settings

    @pytest.fixture
    def service(self, mock_db, mock_settings):
        with patch('app.services.integration_service.get_settings', return_value=mock_settings):
            return IntegrationService(mock_db)

    @pytest.mark.asyncio
    async def test_test_connection_zoom(self, service):
        """Test connection test for Zoom platform"""
        integration_id = uuid4()
        credentials = {"client_id": "zoom-id", "client_secret": "zoom-secret"}

        result = await service._test_connection(integration_id, Platform.ZOOM, credentials)
        assert result is True

    @pytest.mark.asyncio
    async def test_test_connection_slack(self, service):
        """Test connection test for Slack platform"""
        integration_id = uuid4()
        credentials = {"access_token": "xoxb-token"}

        result = await service._test_connection(integration_id, Platform.SLACK, credentials)
        assert result is True

    @pytest.mark.asyncio
    async def test_test_connection_discord(self, service):
        """Test connection test for Discord platform"""
        integration_id = uuid4()
        credentials = {"bot_token": "discord-token"}

        result = await service._test_connection(integration_id, Platform.DISCORD, credentials)
        assert result is True

    @pytest.mark.asyncio
    async def test_test_connection_all_platforms(self, service):
        """Test connection for all platforms"""
        integration_id = uuid4()
        platforms = [
            Platform.GMAIL, Platform.OUTLOOK, Platform.SLACK, Platform.DISCORD,
            Platform.ZOOM, Platform.LOOM, Platform.FIREFLIES, Platform.OTTER
        ]

        for platform in platforms:
            credentials = {"token": f"token-{platform.value}"}
            result = await service._test_connection(integration_id, platform, credentials)
            assert result is True


class TestEdgeCases:
    """Tests for edge cases and error scenarios"""

    @pytest.fixture
    def mock_db(self):
        return MagicMock()

    @pytest.fixture
    def mock_settings(self):
        settings = MagicMock()
        settings.secret_key = "test-secret-key-for-testing-only-minimum-32-chars"
        return settings

    @pytest.fixture
    def workspace_id(self):
        return uuid4()

    @pytest.fixture
    def service(self, mock_db, mock_settings):
        with patch('app.services.integration_service.get_settings', return_value=mock_settings):
            return IntegrationService(mock_db)

    @pytest.mark.asyncio
    async def test_create_integration_with_empty_metadata(self, service, mock_db, workspace_id):
        """Test creating integration with empty metadata dict"""
        integration_data = IntegrationCreate(
            workspace_id=workspace_id,
            founder_id=None,
            platform=Platform.SLACK,
            credentials={"access_token": "token", "team_id": "T123"},
            metadata={}
        )

        mock_result_check = MagicMock()
        mock_result_check.fetchone.return_value = None

        mock_row, _, _ = create_mock_integration_row(workspace_id=workspace_id, metadata={})

        mock_result_insert = MagicMock()
        mock_result_insert.fetchone.return_value = mock_row

        mock_db.execute.side_effect = [mock_result_check, mock_result_insert, MagicMock()]
        mock_db.commit = MagicMock()

        with patch.object(service, '_test_connection', new_callable=AsyncMock, return_value=True):
            result = await service.create_integration(integration_data)
            assert result.metadata is not None or result.metadata == {}

    @pytest.mark.asyncio
    async def test_concurrent_integration_creation_same_platform(self, service, mock_db, workspace_id):
        """Test handling of concurrent creation attempts for same platform"""
        integration_data = IntegrationCreate(
            workspace_id=workspace_id,
            founder_id=None,
            platform=Platform.SLACK,
            credentials={"access_token": "token", "team_id": "T123"}
        )

        mock_result_check = MagicMock()
        mock_result_check.fetchone.return_value = MagicMock(id="existing-int")
        mock_db.execute.return_value = mock_result_check

        with pytest.raises(HTTPException) as exc_info:
            await service.create_integration(integration_data)

        assert exc_info.value.status_code == status.HTTP_409_CONFLICT
