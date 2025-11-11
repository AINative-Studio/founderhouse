"""
Comprehensive tests for Recommendations API endpoints

Tests all recommendation-related endpoints with proper mocking.
Coverage target: 20 statements, 0% -> 80%+
"""
import pytest
from uuid import uuid4, UUID
from datetime import datetime
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi.testclient import TestClient

from app.main import app
from app.models.recommendation import (
    RecommendationType,
    RecommendationStatus,
    RecommendationPriority
)


@pytest.fixture
def client():
    """FastAPI test client"""
    return TestClient(app)


@pytest.fixture
def mock_recommendation_service():
    """Mock recommendation service"""
    with patch('app.api.v1.recommendations.get_recommendation_service') as mock:
        service = MagicMock()
        service.supabase = MagicMock()
        
        # Configure chained methods
        service.supabase.table.return_value = service.supabase
        service.supabase.select.return_value = service.supabase
        service.supabase.eq.return_value = service.supabase
        service.supabase.in_.return_value = service.supabase
        service.supabase.gte.return_value = service.supabase
        service.supabase.order.return_value = service.supabase
        service.supabase.range.return_value = service.supabase
        service.supabase.limit.return_value = service.supabase
        service.supabase.insert.return_value = service.supabase
        service.supabase.update.return_value = service.supabase
        service.supabase.execute.return_value = MagicMock(data=[])
        
        service.generate_recommendations = AsyncMock(return_value=[])
        
        mock.return_value = service
        yield service


@pytest.fixture
def sample_recommendation():
    """Sample recommendation data"""
    return {
        "id": str(uuid4()),
        "workspace_id": str(uuid4()),
        "founder_id": str(uuid4()),
        "recommendation_type": RecommendationType.PRODUCT.value,
        "title": "Optimize conversion funnel",
        "description": "Your conversion rate has dropped by 15%",
        "rationale": "Based on recent KPI analysis",
        "priority": RecommendationPriority.HIGH.value,
        "confidence_score": 0.85,
        "status": RecommendationStatus.PENDING.value,
        "impact_estimate": "high",
        "created_at": datetime.utcnow().isoformat()
    }


class TestListRecommendations:
    """Tests for listing recommendations"""
    
    def test_list_recommendations_success(self, client, mock_recommendation_service, sample_recommendation):
        """Test successful recommendation listing"""
        workspace_id = uuid4()
        
        mock_recommendation_service.supabase.execute.return_value = MagicMock(
            data=[sample_recommendation, sample_recommendation]
        )
        
        response = client.get(
            "/recommendations",
            params={"workspace_id": str(workspace_id)}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "recommendations" in data
        assert "total_count" in data
        assert data["total_count"] == 2
        
    def test_list_recommendations_with_filters(self, client, mock_recommendation_service, sample_recommendation):
        """Test listing with type and status filters"""
        workspace_id = uuid4()
        founder_id = uuid4()
        
        mock_recommendation_service.supabase.execute.return_value = MagicMock(
            data=[sample_recommendation]
        )
        
        response = client.get(
            "/recommendations",
            params={
                "workspace_id": str(workspace_id),
                "founder_id": str(founder_id),
                "recommendation_type": [RecommendationType.PRODUCT.value],
                "status": [RecommendationStatus.PENDING.value],
                "priority": [RecommendationPriority.HIGH.value],
                "min_confidence": 0.8
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["recommendations"]) == 1
        
    def test_list_recommendations_pagination(self, client, mock_recommendation_service, sample_recommendation):
        """Test recommendation listing pagination"""
        workspace_id = uuid4()
        
        recommendations = [sample_recommendation] * 25
        mock_recommendation_service.supabase.execute.return_value = MagicMock(
            data=recommendations
        )
        
        response = client.get(
            "/recommendations",
            params={
                "workspace_id": str(workspace_id),
                "limit": 10,
                "offset": 0
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 25
        assert data["has_more"] is True
        
    def test_list_recommendations_error(self, client, mock_recommendation_service):
        """Test listing with database error"""
        workspace_id = uuid4()
        
        mock_recommendation_service.supabase.execute.side_effect = Exception("Database error")
        
        response = client.get(
            "/recommendations",
            params={"workspace_id": str(workspace_id)}
        )
        
        assert response.status_code == 500


class TestGenerateRecommendations:
    """Tests for generating recommendations"""
    
    def test_generate_recommendations_success(self, client, mock_recommendation_service, sample_recommendation):
        """Test successful recommendation generation"""
        workspace_id = uuid4()
        founder_id = uuid4()
        
        mock_recommendation_service.generate_recommendations = AsyncMock(
            return_value=[sample_recommendation]
        )
        
        request_data = {
            "workspace_id": str(workspace_id),
            "founder_id": str(founder_id),
            "time_range_days": 30,
            "focus_areas": [RecommendationType.PRODUCT.value],
            "min_confidence": 0.7
        }
        
        response = client.post("/recommendations/generate", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["workspace_id"] == str(workspace_id)
        assert "recommendations" in data
        assert "analysis_summary" in data
        assert "generated_at" in data
        
    def test_generate_recommendations_with_options(self, client, mock_recommendation_service):
        """Test generation with custom options"""
        workspace_id = uuid4()
        founder_id = uuid4()
        
        mock_recommendation_service.generate_recommendations = AsyncMock(return_value=[])
        
        request_data = {
            "workspace_id": str(workspace_id),
            "founder_id": str(founder_id),
            "time_range_days": 7,
            "focus_areas": [RecommendationType.PRODUCT.value, RecommendationType.SALES.value],
            "min_confidence": 0.9
        }
        
        response = client.post("/recommendations/generate", json=request_data)
        
        assert response.status_code == 200
        
    def test_generate_recommendations_error(self, client, mock_recommendation_service):
        """Test generation with service error"""
        workspace_id = uuid4()
        founder_id = uuid4()
        
        mock_recommendation_service.generate_recommendations = AsyncMock(
            side_effect=Exception("LLM service unavailable")
        )
        
        request_data = {
            "workspace_id": str(workspace_id),
            "founder_id": str(founder_id),
            "time_range_days": 30
        }
        
        response = client.post("/recommendations/generate", json=request_data)
        
        assert response.status_code == 500


class TestSubmitFeedback:
    """Tests for recommendation feedback"""
    
    def test_submit_feedback_success(self, client, mock_recommendation_service):
        """Test successful feedback submission"""
        recommendation_id = uuid4()
        
        feedback_id = str(uuid4())
        mock_recommendation_service.supabase.insert.return_value.execute.return_value = MagicMock(
            data=[{"id": feedback_id}]
        )
        mock_recommendation_service.supabase.update.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": str(recommendation_id)}]
        )
        
        feedback_data = {
            "recommendation_id": str(recommendation_id),
            "was_implemented": True,
            "was_helpful": True,
            "rating": 5,
            "comment": "Great recommendation"
        }
        
        response = client.put(
            f"/recommendations/{recommendation_id}/feedback",
            json=feedback_data
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["feedback_id"] == feedback_id
        
    def test_submit_feedback_not_implemented(self, client, mock_recommendation_service):
        """Test feedback for non-implemented recommendation"""
        recommendation_id = uuid4()
        
        mock_recommendation_service.supabase.insert.return_value.execute.return_value = MagicMock(
            data=[{"id": str(uuid4())}]
        )
        
        feedback_data = {
            "recommendation_id": str(recommendation_id),
            "was_implemented": False,
            "was_helpful": False,
            "rating": 2,
            "comment": "Not relevant"
        }
        
        response = client.put(
            f"/recommendations/{recommendation_id}/feedback",
            json=feedback_data
        )
        
        assert response.status_code == 200
        
    def test_submit_feedback_error(self, client, mock_recommendation_service):
        """Test feedback submission with error"""
        recommendation_id = uuid4()
        
        mock_recommendation_service.supabase.insert.side_effect = Exception("Database error")
        
        feedback_data = {
            "recommendation_id": str(recommendation_id),
            "was_implemented": True,
            "was_helpful": True,
            "rating": 5
        }
        
        response = client.put(
            f"/recommendations/{recommendation_id}/feedback",
            json=feedback_data
        )
        
        assert response.status_code == 500


class TestImpactTracking:
    """Tests for recommendation impact tracking"""
    
    def test_get_impact_success(self, client, mock_recommendation_service):
        """Test successful impact data retrieval"""
        recommendation_id = uuid4()
        
        impact_data = {
            "id": str(uuid4()),
            "recommendation_id": str(recommendation_id),
            "measurement_date": datetime.utcnow().isoformat(),
            "metrics_before": {"revenue": 10000},
            "metrics_after": {"revenue": 12000},
            "improvement_percentage": 20.0,
            "roi_estimate": 2.5
        }
        
        mock_recommendation_service.supabase.execute.return_value = MagicMock(
            data=[impact_data]
        )
        
        response = client.get(f"/recommendations/{recommendation_id}/impact")
        
        assert response.status_code == 200
        data = response.json()
        assert data["recommendation_id"] == str(recommendation_id)
        assert data["improvement_percentage"] == 20.0
        
    def test_get_impact_not_found(self, client, mock_recommendation_service):
        """Test impact data when none exists"""
        recommendation_id = uuid4()
        
        mock_recommendation_service.supabase.execute.return_value = MagicMock(data=[])
        
        response = client.get(f"/recommendations/{recommendation_id}/impact")
        
        assert response.status_code == 404
        assert "No impact data found" in response.json()["detail"]
        
    def test_get_impact_error(self, client, mock_recommendation_service):
        """Test impact retrieval with error"""
        recommendation_id = uuid4()
        
        mock_recommendation_service.supabase.execute.side_effect = Exception("Database error")
        
        response = client.get(f"/recommendations/{recommendation_id}/impact")
        
        assert response.status_code == 500


# Summary comment
"""
Test Coverage Summary:
- List recommendations: 4 tests (success, filters, pagination, error)
- Generate recommendations: 3 tests (success, options, error)
- Submit feedback: 3 tests (success, not implemented, error)
- Impact tracking: 3 tests (success, not found, error)

Total: 13 tests covering recommendations.py (20 statements)
Expected coverage improvement: 0% -> 80%+
"""
