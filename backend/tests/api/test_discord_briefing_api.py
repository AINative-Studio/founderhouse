"""
Tests for Discord Briefing Schedule API Endpoints - Sprint 5
Tests schedule management endpoints for automated daily briefings
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
from uuid import uuid4
from datetime import datetime

from app.main import app
from app.models.briefing import BriefingType


client = TestClient(app)


@pytest.fixture
def mock_db():
    """Mock database session"""
    db = Mock()
    db.execute = Mock()
    db.commit = Mock()
    db.rollback = Mock()
    return db


@pytest.fixture
def sample_schedule_data():
    """Sample schedule data"""
    return {
        "workspace_id": str(uuid4()),
        "founder_id": str(uuid4()),
        "briefing_type": "morning",
        "discord_channel": "daily-briefings",
        "timezone": "America/Los_Angeles",
        "delivery_hour": 8,
        "mention_team": False,
        "is_active": True
    }


# ==================== Create Schedule Tests ====================

def test_create_briefing_schedule_success(mock_db, sample_schedule_data):
    """Test creating a new briefing schedule"""
    schedule_id = uuid4()
    mock_result = Mock()
    mock_row = (
        schedule_id,
        sample_schedule_data["workspace_id"],
        sample_schedule_data["founder_id"],
        sample_schedule_data["briefing_type"],
        sample_schedule_data["discord_channel"],
        sample_schedule_data["timezone"],
        sample_schedule_data["delivery_hour"],
        sample_schedule_data["mention_team"],
        sample_schedule_data["is_active"]
    )
    mock_result.fetchone.return_value = mock_row
    mock_db.execute.return_value = mock_result

    with patch('app.api.v1.discord.get_db', return_value=mock_db):
        response = client.post(
            "/api/v1/discord/briefing/schedule",
            json=sample_schedule_data
        )

    assert response.status_code == 200
    data = response.json()
    assert data["timezone"] == "America/Los_Angeles"
    assert data["delivery_hour"] == 8
    assert data["briefing_type"] == "morning"


def test_create_briefing_schedule_invalid_timezone(mock_db, sample_schedule_data):
    """Test creating schedule with invalid timezone fails"""
    sample_schedule_data["timezone"] = "Invalid/Timezone"

    with patch('app.api.v1.discord.get_db', return_value=mock_db):
        response = client.post(
            "/api/v1/discord/briefing/schedule",
            json=sample_schedule_data
        )

    assert response.status_code == 400
    assert "Invalid timezone" in response.json()["detail"]


def test_create_briefing_schedule_with_pst(mock_db, sample_schedule_data):
    """Test creating schedule with PST timezone"""
    sample_schedule_data["timezone"] = "America/Los_Angeles"
    schedule_id = uuid4()

    mock_result = Mock()
    mock_row = (
        schedule_id,
        sample_schedule_data["workspace_id"],
        sample_schedule_data["founder_id"],
        sample_schedule_data["briefing_type"],
        sample_schedule_data["discord_channel"],
        sample_schedule_data["timezone"],
        sample_schedule_data["delivery_hour"],
        sample_schedule_data["mention_team"],
        sample_schedule_data["is_active"]
    )
    mock_result.fetchone.return_value = mock_row
    mock_db.execute.return_value = mock_result

    with patch('app.api.v1.discord.get_db', return_value=mock_db):
        response = client.post(
            "/api/v1/discord/briefing/schedule",
            json=sample_schedule_data
        )

    assert response.status_code == 200
    data = response.json()
    assert data["timezone"] == "America/Los_Angeles"


def test_create_briefing_schedule_with_est(mock_db, sample_schedule_data):
    """Test creating schedule with EST timezone"""
    sample_schedule_data["timezone"] = "America/New_York"
    schedule_id = uuid4()

    mock_result = Mock()
    mock_row = (
        schedule_id,
        sample_schedule_data["workspace_id"],
        sample_schedule_data["founder_id"],
        sample_schedule_data["briefing_type"],
        sample_schedule_data["discord_channel"],
        sample_schedule_data["timezone"],
        sample_schedule_data["delivery_hour"],
        sample_schedule_data["mention_team"],
        sample_schedule_data["is_active"]
    )
    mock_result.fetchone.return_value = mock_row
    mock_db.execute.return_value = mock_result

    with patch('app.api.v1.discord.get_db', return_value=mock_db):
        response = client.post(
            "/api/v1/discord/briefing/schedule",
            json=sample_schedule_data
        )

    assert response.status_code == 200
    data = response.json()
    assert data["timezone"] == "America/New_York"


def test_create_briefing_schedule_invalid_hour(sample_schedule_data):
    """Test creating schedule with invalid hour fails validation"""
    sample_schedule_data["delivery_hour"] = 25  # Invalid hour

    response = client.post(
        "/api/v1/discord/briefing/schedule",
        json=sample_schedule_data
    )

    assert response.status_code == 422  # Validation error


def test_create_briefing_schedule_defaults(mock_db):
    """Test creating schedule with default values"""
    workspace_id = str(uuid4())
    founder_id = str(uuid4())
    schedule_id = uuid4()

    minimal_data = {
        "workspace_id": workspace_id,
        "founder_id": founder_id
    }

    mock_result = Mock()
    mock_row = (
        schedule_id,
        workspace_id,
        founder_id,
        "morning",
        "daily-briefings",
        "UTC",
        8,
        False,
        True
    )
    mock_result.fetchone.return_value = mock_row
    mock_db.execute.return_value = mock_result

    with patch('app.api.v1.discord.get_db', return_value=mock_db):
        response = client.post(
            "/api/v1/discord/briefing/schedule",
            json=minimal_data
        )

    assert response.status_code == 200
    data = response.json()
    assert data["briefing_type"] == "morning"
    assert data["discord_channel"] == "daily-briefings"
    assert data["timezone"] == "UTC"
    assert data["delivery_hour"] == 8


# ==================== Get Schedules Tests ====================

def test_get_briefing_schedules_success(mock_db):
    """Test retrieving briefing schedules for a workspace"""
    workspace_id = uuid4()

    mock_result = Mock()
    mock_rows = [
        (uuid4(), str(workspace_id), str(uuid4()), "morning",
         "daily-briefings", "America/Los_Angeles", 8, False, True),
        (uuid4(), str(workspace_id), str(uuid4()), "evening",
         "team-updates", "America/New_York", 18, True, True)
    ]
    mock_result.fetchall.return_value = mock_rows
    mock_db.execute.return_value = mock_result

    with patch('app.api.v1.discord.get_db', return_value=mock_db):
        response = client.get(f"/api/v1/discord/briefing/schedule/{workspace_id}")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["briefing_type"] == "morning"
    assert data[1]["briefing_type"] == "evening"


def test_get_briefing_schedules_empty(mock_db):
    """Test retrieving schedules when none exist"""
    workspace_id = uuid4()

    mock_result = Mock()
    mock_result.fetchall.return_value = []
    mock_db.execute.return_value = mock_result

    with patch('app.api.v1.discord.get_db', return_value=mock_db):
        response = client.get(f"/api/v1/discord/briefing/schedule/{workspace_id}")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 0


def test_get_briefing_schedules_multiple_timezones(mock_db):
    """Test retrieving schedules with different timezones"""
    workspace_id = uuid4()

    mock_result = Mock()
    mock_rows = [
        (uuid4(), str(workspace_id), str(uuid4()), "morning",
         "utc-brief", "UTC", 8, False, True),
        (uuid4(), str(workspace_id), str(uuid4()), "morning",
         "pst-brief", "America/Los_Angeles", 8, False, True),
        (uuid4(), str(workspace_id), str(uuid4()), "morning",
         "tokyo-brief", "Asia/Tokyo", 8, False, True)
    ]
    mock_result.fetchall.return_value = mock_rows
    mock_db.execute.return_value = mock_result

    with patch('app.api.v1.discord.get_db', return_value=mock_db):
        response = client.get(f"/api/v1/discord/briefing/schedule/{workspace_id}")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    timezones = [s["timezone"] for s in data]
    assert "UTC" in timezones
    assert "America/Los_Angeles" in timezones
    assert "Asia/Tokyo" in timezones


# ==================== Update Schedule Tests ====================

def test_update_briefing_schedule_activate(mock_db):
    """Test activating a briefing schedule"""
    schedule_id = uuid4()

    mock_result = Mock()
    mock_result.fetchone.return_value = (schedule_id,)
    mock_db.execute.return_value = mock_result

    with patch('app.api.v1.discord.get_db', return_value=mock_db):
        response = client.patch(
            f"/api/v1/discord/briefing/schedule/{schedule_id}",
            json=True
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["is_active"] is True


def test_update_briefing_schedule_deactivate(mock_db):
    """Test deactivating a briefing schedule"""
    schedule_id = uuid4()

    mock_result = Mock()
    mock_result.fetchone.return_value = (schedule_id,)
    mock_db.execute.return_value = mock_result

    with patch('app.api.v1.discord.get_db', return_value=mock_db):
        response = client.patch(
            f"/api/v1/discord/briefing/schedule/{schedule_id}",
            json=False
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["is_active"] is False


def test_update_briefing_schedule_not_found(mock_db):
    """Test updating non-existent schedule"""
    schedule_id = uuid4()

    mock_result = Mock()
    mock_result.fetchone.return_value = None
    mock_db.execute.return_value = mock_result

    with patch('app.api.v1.discord.get_db', return_value=mock_db):
        response = client.patch(
            f"/api/v1/discord/briefing/schedule/{schedule_id}",
            json=True
        )

    assert response.status_code == 404


# ==================== Delete Schedule Tests ====================

def test_delete_briefing_schedule_success(mock_db):
    """Test deleting a briefing schedule"""
    schedule_id = uuid4()

    mock_result = Mock()
    mock_result.fetchone.return_value = (schedule_id,)
    mock_db.execute.return_value = mock_result

    with patch('app.api.v1.discord.get_db', return_value=mock_db):
        response = client.delete(f"/api/v1/discord/briefing/schedule/{schedule_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"


def test_delete_briefing_schedule_not_found(mock_db):
    """Test deleting non-existent schedule"""
    schedule_id = uuid4()

    mock_result = Mock()
    mock_result.fetchone.return_value = None
    mock_db.execute.return_value = mock_result

    with patch('app.api.v1.discord.get_db', return_value=mock_db):
        response = client.delete(f"/api/v1/discord/briefing/schedule/{schedule_id}")

    assert response.status_code == 404


# ==================== Timezone Validation Tests ====================

def test_validate_common_timezones(mock_db, sample_schedule_data):
    """Test validation accepts common timezones"""
    common_timezones = [
        "America/Los_Angeles",
        "America/New_York",
        "America/Chicago",
        "Europe/London",
        "Europe/Paris",
        "Asia/Tokyo",
        "Australia/Sydney",
        "UTC"
    ]

    for tz in common_timezones:
        sample_schedule_data["timezone"] = tz
        schedule_id = uuid4()

        mock_result = Mock()
        mock_row = (
            schedule_id,
            sample_schedule_data["workspace_id"],
            sample_schedule_data["founder_id"],
            sample_schedule_data["briefing_type"],
            sample_schedule_data["discord_channel"],
            tz,
            sample_schedule_data["delivery_hour"],
            sample_schedule_data["mention_team"],
            sample_schedule_data["is_active"]
        )
        mock_result.fetchone.return_value = mock_row
        mock_db.execute.return_value = mock_result

        with patch('app.api.v1.discord.get_db', return_value=mock_db):
            response = client.post(
                "/api/v1/discord/briefing/schedule",
                json=sample_schedule_data
            )

        assert response.status_code == 200, f"Failed for timezone: {tz}"
        assert response.json()["timezone"] == tz


# ==================== Hour Range Tests ====================

def test_delivery_hour_valid_range(mock_db, sample_schedule_data):
    """Test all valid hours (0-23) are accepted"""
    for hour in range(24):
        sample_schedule_data["delivery_hour"] = hour
        schedule_id = uuid4()

        mock_result = Mock()
        mock_row = (
            schedule_id,
            sample_schedule_data["workspace_id"],
            sample_schedule_data["founder_id"],
            sample_schedule_data["briefing_type"],
            sample_schedule_data["discord_channel"],
            sample_schedule_data["timezone"],
            hour,
            sample_schedule_data["mention_team"],
            sample_schedule_data["is_active"]
        )
        mock_result.fetchone.return_value = mock_row
        mock_db.execute.return_value = mock_result

        with patch('app.api.v1.discord.get_db', return_value=mock_db):
            response = client.post(
                "/api/v1/discord/briefing/schedule",
                json=sample_schedule_data
            )

        assert response.status_code == 200, f"Failed for hour: {hour}"
        assert response.json()["delivery_hour"] == hour
