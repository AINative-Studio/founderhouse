"""
Comprehensive tests for Briefings API endpoints

Tests all briefing-related endpoints with proper mocking.
Coverage target: 9 statements, 0% -> 80%+
"""
import pytest
from uuid import uuid4
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi.testclient import TestClient

from app.main import app
from app.models.briefing import BriefingType, BriefingStatus


@pytest.fixture
def client():
    """FastAPI test client"""
    return TestClient(app)


@pytest.fixture
def mock_briefing_service():
    """Mock briefing service"""
    with patch('app.api.v1.briefings.get_briefing_service') as mock:
        service = MagicMock()
        service.supabase = MagicMock()
        
        # Configure chained methods
        service.supabase.table.return_value = service.supabase
        service.supabase.select.return_value = service.supabase
        service.supabase.eq.return_value = service.supabase
        service.supabase.in_.return_value = service.supabase
        service.supabase.gte.return_value = service.supabase
        service.supabase.lte.return_value = service.supabase
        service.supabase.order.return_value = service.supabase
        service.supabase.limit.return_value = service.supabase
        service.supabase.range.return_value = service.supabase
        service.supabase.upsert.return_value = service.supabase
        service.supabase.execute.return_value = MagicMock(data=[])
        
        service.generate_briefing = AsyncMock(return_value=None)
        
        mock.return_value = service
        yield service


@pytest.fixture
def sample_briefing():
    """Sample briefing data"""
    return {
        "id": str(uuid4()),
        "workspace_id": str(uuid4()),
        "founder_id": str(uuid4()),
        "briefing_type": BriefingType.MORNING.value,
        "title": "Morning Brief - Jan 10",
        "content": "Your daily briefing...",
        "summary": "3 meetings, 5 action items",
        "highlights": ["Revenue up 10%", "New feature launched"],
        "status": BriefingStatus.DELIVERED.value,
        "created_at": datetime.utcnow().isoformat()
    }


class TestGetLatestBriefing:
    """Tests for getting latest briefing"""
    
    def test_get_latest_briefing_success(self, client, mock_briefing_service, sample_briefing):
        """Test successful briefing retrieval"""
        founder_id = uuid4()
        workspace_id = uuid4()
        
        mock_briefing_service.supabase.execute.return_value = MagicMock(
            data=[sample_briefing]
        )
        
        response = client.get(
            f"/briefings/{founder_id}",
            params={"workspace_id": str(workspace_id)}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["briefing_type"] == BriefingType.MORNING.value
        
    def test_get_latest_briefing_with_type(self, client, mock_briefing_service, sample_briefing):
        """Test briefing retrieval with type filter"""
        founder_id = uuid4()
        workspace_id = uuid4()
        
        evening_briefing = {**sample_briefing, "briefing_type": BriefingType.EVENING.value}
        mock_briefing_service.supabase.execute.return_value = MagicMock(
            data=[evening_briefing]
        )
        
        response = client.get(
            f"/briefings/{founder_id}",
            params={
                "workspace_id": str(workspace_id),
                "briefing_type": BriefingType.EVENING.value
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["briefing_type"] == BriefingType.EVENING.value
        
    def test_get_latest_briefing_not_found(self, client, mock_briefing_service):
        """Test briefing retrieval when none exists"""
        founder_id = uuid4()
        workspace_id = uuid4()
        
        mock_briefing_service.supabase.execute.return_value = MagicMock(data=[])
        
        response = client.get(
            f"/briefings/{founder_id}",
            params={"workspace_id": str(workspace_id)}
        )
        
        assert response.status_code == 404


class TestGenerateBriefing:
    """Tests for generating briefings"""
    
    def test_generate_briefing_success(self, client, mock_briefing_service, sample_briefing):
        """Test successful briefing generation"""
        mock_briefing_service.generate_briefing = AsyncMock(return_value=sample_briefing)
        
        request_data = {
            "workspace_id": sample_briefing["workspace_id"],
            "founder_id": sample_briefing["founder_id"],
            "briefing_type": BriefingType.MORNING.value,
            "start_date": datetime.utcnow().isoformat(),
            "end_date": datetime.utcnow().isoformat()
        }
        
        response = client.post("/briefings/generate", json=request_data)
        
        assert response.status_code == 200
        
    def test_generate_briefing_failure(self, client, mock_briefing_service):
        """Test briefing generation failure"""
        mock_briefing_service.generate_briefing = AsyncMock(return_value=None)
        
        request_data = {
            "workspace_id": str(uuid4()),
            "founder_id": str(uuid4()),
            "briefing_type": BriefingType.EVENING.value
        }
        
        response = client.post("/briefings/generate", json=request_data)
        
        assert response.status_code == 500


class TestMorningBrief:
    """Tests for morning brief endpoint"""
    
    def test_get_morning_brief_existing(self, client, mock_briefing_service, sample_briefing):
        """Test getting existing morning brief"""
        workspace_id = uuid4()
        founder_id = uuid4()
        
        mock_briefing_service.supabase.execute.return_value = MagicMock(
            data=[sample_briefing]
        )
        
        response = client.get(
            "/briefings/morning",
            params={
                "workspace_id": str(workspace_id),
                "founder_id": str(founder_id)
            }
        )
        
        assert response.status_code == 200
        
    def test_get_morning_brief_generate_new(self, client, mock_briefing_service, sample_briefing):
        """Test generating new morning brief when none exists"""
        workspace_id = uuid4()
        founder_id = uuid4()
        
        # First call returns empty (no existing briefing)
        # Second call generates new one
        mock_briefing_service.supabase.execute.return_value = MagicMock(data=[])
        mock_briefing_service.generate_briefing = AsyncMock(return_value=sample_briefing)
        
        response = client.get(
            "/briefings/morning",
            params={
                "workspace_id": str(workspace_id),
                "founder_id": str(founder_id)
            }
        )
        
        assert response.status_code == 200


class TestEveningWrap:
    """Tests for evening wrap endpoint"""
    
    def test_get_evening_wrap_existing(self, client, mock_briefing_service, sample_briefing):
        """Test getting existing evening wrap"""
        workspace_id = uuid4()
        founder_id = uuid4()
        
        evening_briefing = {**sample_briefing, "briefing_type": BriefingType.EVENING.value}
        mock_briefing_service.supabase.execute.return_value = MagicMock(
            data=[evening_briefing]
        )
        
        response = client.get(
            "/briefings/evening",
            params={
                "workspace_id": str(workspace_id),
                "founder_id": str(founder_id)
            }
        )
        
        assert response.status_code == 200
        
    def test_get_evening_wrap_generate_new(self, client, mock_briefing_service, sample_briefing):
        """Test generating new evening wrap"""
        workspace_id = uuid4()
        founder_id = uuid4()
        
        evening_briefing = {**sample_briefing, "briefing_type": BriefingType.EVENING.value}
        mock_briefing_service.supabase.execute.return_value = MagicMock(data=[])
        mock_briefing_service.generate_briefing = AsyncMock(return_value=evening_briefing)
        
        response = client.get(
            "/briefings/evening",
            params={
                "workspace_id": str(workspace_id),
                "founder_id": str(founder_id)
            }
        )
        
        assert response.status_code == 200


class TestInvestorSummary:
    """Tests for investor summary endpoint"""
    
    def test_get_investor_summary_existing(self, client, mock_briefing_service, sample_briefing):
        """Test getting existing investor summary"""
        workspace_id = uuid4()
        founder_id = uuid4()
        
        investor_briefing = {**sample_briefing, "briefing_type": BriefingType.INVESTOR.value}
        mock_briefing_service.supabase.execute.return_value = MagicMock(
            data=[investor_briefing]
        )
        
        response = client.get(
            "/briefings/investor-weekly",
            params={
                "workspace_id": str(workspace_id),
                "founder_id": str(founder_id)
            }
        )
        
        assert response.status_code == 200


class TestScheduleBriefing:
    """Tests for briefing scheduling"""
    
    def test_schedule_briefing_success(self, client, mock_briefing_service):
        """Test successful briefing scheduling"""
        schedule_data = {
            "id": str(uuid4()),
            "workspace_id": str(uuid4()),
            "founder_id": str(uuid4()),
            "briefing_type": BriefingType.MORNING.value,
            "schedule": "0 8 * * *",  # 8 AM daily
            "timezone": "America/New_York",
            "delivery_channels": ["email", "discord"],
            "is_active": True
        }
        
        mock_briefing_service.supabase.execute.return_value = MagicMock(
            data=[schedule_data]
        )
        
        response = client.post("/briefings/schedule", json=schedule_data)
        
        assert response.status_code == 200


class TestListBriefings:
    """Tests for listing briefings"""
    
    def test_list_briefings_success(self, client, mock_briefing_service, sample_briefing):
        """Test successful briefing listing"""
        workspace_id = uuid4()
        
        briefings = [sample_briefing] * 3
        mock_briefing_service.supabase.execute.return_value = MagicMock(
            data=briefings
        )
        
        response = client.get(
            "/briefings/list",
            params={"workspace_id": str(workspace_id)}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 3
        
    def test_list_briefings_with_filters(self, client, mock_briefing_service, sample_briefing):
        """Test briefing listing with filters"""
        workspace_id = uuid4()
        founder_id = uuid4()
        
        mock_briefing_service.supabase.execute.return_value = MagicMock(
            data=[sample_briefing]
        )
        
        response = client.get(
            "/briefings/list",
            params={
                "workspace_id": str(workspace_id),
                "founder_id": str(founder_id),
                "briefing_type": [BriefingType.MORNING.value],
                "status": [BriefingStatus.DELIVERED.value]
            }
        )
        
        assert response.status_code == 200


# Summary comment
"""
Test Coverage Summary:
- Get latest briefing: 3 tests
- Generate briefing: 2 tests
- Morning brief: 2 tests
- Evening wrap: 2 tests
- Investor summary: 1 test
- Schedule briefing: 1 test
- List briefings: 2 tests

Total: 13 tests covering briefings.py (9 statements)
Expected coverage improvement: 0% -> 80%+
"""
