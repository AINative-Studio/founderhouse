# Zoom MCP Connector Specification

**Platform:** Zoom Video Communications
**Priority:** P0 (Critical - Primary meeting source)
**API Version:** v2
**Documentation:** https://developers.zoom.us/docs/api/

---

## Platform Overview

### Purpose
Zoom is the primary meeting platform integration for the AI Chief of Staff. It provides:
- Meeting recordings and metadata
- Live and recorded transcriptions
- Participant data
- Calendar integration
- Webhook notifications for real-time events

### Integration Value
- Automatic meeting ingestion
- Real-time transcript capture
- Action item extraction from meetings
- Meeting analytics and insights
- Participant tracking for relationship management

---

## OAuth Configuration

### OAuth Provider
**Provider:** Zoom OAuth 2.0
**Flow:** Authorization Code Flow with PKCE

### OAuth Endpoints
```
Authorization URL: https://zoom.us/oauth/authorize
Token URL: https://zoom.us/oauth/token
Revoke URL: https://zoom.us/oauth/revoke
```

### Required Scopes
```
meeting:read:admin          # Read meeting details
meeting:read:list_meetings  # List all meetings
recording:read:admin        # Access recordings
recording:read:list_recordings  # List recordings
user:read:admin             # Read user profile
webinar:read:admin          # Read webinar details
```

### Optional Scopes (Future)
```
meeting:write:admin         # Create meetings
cloud_recording:write:admin # Manage recordings
```

### OAuth Flow Implementation

```python
# 1. Authorization Request
auth_params = {
    "client_id": ZOOM_CLIENT_ID,
    "response_type": "code",
    "redirect_uri": "https://app.aicos.ai/integrations/callback/zoom",
    "state": generate_state_token(),
    "code_challenge": generate_code_challenge(),
    "code_challenge_method": "S256"
}
auth_url = f"https://zoom.us/oauth/authorize?{urlencode(auth_params)}"

# 2. Token Exchange
token_params = {
    "grant_type": "authorization_code",
    "code": authorization_code,
    "redirect_uri": redirect_uri,
    "code_verifier": code_verifier
}
headers = {
    "Authorization": f"Basic {base64(client_id:client_secret)}"
}
response = requests.post("https://zoom.us/oauth/token", data=token_params, headers=headers)

# 3. Token Response
{
    "access_token": "eyJ...",
    "token_type": "bearer",
    "expires_in": 3600,
    "scope": "meeting:read:admin recording:read:admin",
    "refresh_token": "eyJ..."
}
```

### Token Refresh
```python
refresh_params = {
    "grant_type": "refresh_token",
    "refresh_token": stored_refresh_token
}
response = requests.post("https://zoom.us/oauth/token", data=refresh_params, headers=headers)
```

---

## API Endpoints

### Base URL
```
https://api.zoom.us/v2
```

### Key Endpoints

#### 1. User Profile
```http
GET /users/me
```
**Purpose:** Health check and user verification
**Response:**
```json
{
    "id": "z8yAAAABBBCCDDD",
    "first_name": "John",
    "last_name": "Doe",
    "email": "john@example.com",
    "type": 2,
    "pmi": 1234567890,
    "timezone": "America/Los_Angeles"
}
```

#### 2. List Meetings
```http
GET /users/{userId}/meetings
```
**Query Parameters:**
- `type`: scheduled, live, upcoming
- `page_size`: 1-300 (default: 30)
- `next_page_token`: Pagination cursor

**Response:**
```json
{
    "page_count": 1,
    "page_size": 30,
    "total_records": 50,
    "next_page_token": "abc123",
    "meetings": [
        {
            "uuid": "abc123==",
            "id": 123456789,
            "host_id": "z8yAAAABBBCCDDD",
            "topic": "Product Strategy Meeting",
            "type": 2,
            "start_time": "2025-10-30T10:00:00Z",
            "duration": 60,
            "timezone": "America/Los_Angeles",
            "agenda": "Discuss Q4 roadmap",
            "created_at": "2025-10-25T12:00:00Z",
            "join_url": "https://zoom.us/j/123456789"
        }
    ]
}
```

#### 3. Get Meeting Details
```http
GET /meetings/{meetingId}
```
**Response:** Detailed meeting information including settings

#### 4. List Cloud Recordings
```http
GET /users/{userId}/recordings
```
**Query Parameters:**
- `from`: Start date (YYYY-MM-DD)
- `to`: End date (YYYY-MM-DD)
- `page_size`: 1-300
- `next_page_token`: Pagination

**Response:**
```json
{
    "from": "2025-10-01",
    "to": "2025-10-30",
    "page_count": 1,
    "page_size": 30,
    "total_records": 10,
    "next_page_token": "xyz789",
    "meetings": [
        {
            "uuid": "abc123==",
            "id": 123456789,
            "account_id": "account123",
            "host_id": "z8yAAAABBBCCDDD",
            "topic": "Product Strategy Meeting",
            "start_time": "2025-10-30T10:00:00Z",
            "duration": 60,
            "total_size": 157382782,
            "recording_count": 3,
            "recording_files": [
                {
                    "id": "recording123",
                    "meeting_id": "123456789",
                    "recording_start": "2025-10-30T10:00:00Z",
                    "recording_end": "2025-10-30T11:00:00Z",
                    "file_type": "MP4",
                    "file_size": 52460928,
                    "play_url": "https://zoom.us/rec/play/...",
                    "download_url": "https://zoom.us/rec/download/...",
                    "status": "completed",
                    "recording_type": "shared_screen_with_speaker_view"
                },
                {
                    "id": "transcript123",
                    "meeting_id": "123456789",
                    "recording_start": "2025-10-30T10:00:00Z",
                    "recording_end": "2025-10-30T11:00:00Z",
                    "file_type": "TRANSCRIPT",
                    "file_size": 125952,
                    "download_url": "https://zoom.us/rec/download/...",
                    "status": "completed",
                    "recording_type": "audio_transcript"
                }
            ]
        }
    ]
}
```

#### 5. Get Recording Transcript
```http
GET /meetings/{meetingId}/recordings/transcript
```
**Response:** VTT format transcript

---

## Webhook Configuration

### Webhook Events

Zoom supports webhooks for real-time notifications:

#### Event Types to Subscribe
```
meeting.created
meeting.updated
meeting.deleted
meeting.started
meeting.ended
recording.completed
recording.transcript_completed
```

### Webhook Registration
```http
POST /webhooks
```
**Request:**
```json
{
    "url": "https://app.aicos.ai/webhooks/zoom",
    "event_subscriptions": [
        "meeting.started",
        "meeting.ended",
        "recording.completed",
        "recording.transcript_completed"
    ],
    "secret_token": "your_webhook_secret"
}
```

### Webhook Payload Format
```json
{
    "event": "recording.completed",
    "event_ts": 1635446400000,
    "payload": {
        "account_id": "account123",
        "object": {
            "uuid": "abc123==",
            "id": 123456789,
            "host_id": "z8yAAAABBBCCDDD",
            "topic": "Product Strategy Meeting",
            "start_time": "2025-10-30T10:00:00Z",
            "duration": 60,
            "recording_files": [...]
        }
    }
}
```

### Webhook Verification
Zoom uses token-based verification:
```python
def verify_zoom_webhook(request):
    """Verify Zoom webhook signature"""
    # Zoom sends events with secret token
    event_data = request.json
    # Verify secret_token matches stored value
    return event_data.get('secret_token') == ZOOM_WEBHOOK_SECRET
```

---

## Rate Limiting

### Zoom API Limits
- **Per-user rate limit:** 10 requests per second
- **OAuth app rate limit:** Varies by plan
  - Free: 100 requests per day
  - Pro: 1000 requests per day
  - Business+: 10000 requests per day

### Rate Limit Headers
```http
X-RateLimit-Type: QPS
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 7
```

### Rate Limit Handling
```python
async def zoom_api_request(endpoint, params=None):
    """Execute Zoom API request with rate limiting"""
    await rate_limiter.acquire("zoom")

    response = await client.get(f"{BASE_URL}{endpoint}", params=params)

    # Check rate limit headers
    remaining = int(response.headers.get('X-RateLimit-Remaining', 0))
    if remaining < 2:
        # Approaching limit, slow down
        await asyncio.sleep(1)

    if response.status_code == 429:
        # Rate limited, wait and retry
        retry_after = int(response.headers.get('Retry-After', 60))
        await asyncio.sleep(retry_after)
        return await zoom_api_request(endpoint, params)

    return response
```

---

## Data Model Mapping

### Meeting → meetings.meetings
```python
def map_zoom_meeting_to_db(zoom_meeting: dict) -> dict:
    """Map Zoom meeting to database schema"""
    return {
        "platform": "zoom",
        "external_id": str(zoom_meeting["id"]),
        "title": zoom_meeting["topic"],
        "agenda": zoom_meeting.get("agenda"),
        "start_time": zoom_meeting["start_time"],
        "end_time": None,  # Calculate from start_time + duration
        "location_url": zoom_meeting.get("join_url"),
        "metadata": {
            "zoom_uuid": zoom_meeting["uuid"],
            "host_id": zoom_meeting["host_id"],
            "type": zoom_meeting["type"],
            "timezone": zoom_meeting.get("timezone"),
            "duration_mins": zoom_meeting.get("duration")
        }
    }
```

### Recording → meetings.transcripts
```python
def map_zoom_recording_to_db(recording: dict) -> dict:
    """Map Zoom recording to transcript schema"""
    transcript_file = next(
        (f for f in recording["recording_files"] if f["file_type"] == "TRANSCRIPT"),
        None
    )

    return {
        "provider": "zoom",
        "external_id": recording["uuid"],
        "title": recording["topic"],
        "url": transcript_file["download_url"] if transcript_file else None,
        "recorded_at": recording["start_time"],
        "metadata": {
            "recording_id": recording["id"],
            "duration_mins": recording["duration"],
            "file_size": transcript_file["file_size"] if transcript_file else 0,
            "recording_files": recording["recording_files"]
        }
    }
```

---

## Error Handling

### Common Error Codes

| Code | Meaning | Recovery Strategy |
|------|---------|-------------------|
| 124 | Invalid access token | Refresh token |
| 200 | No permission | Check OAuth scopes |
| 300 | Missing field | Validate request |
| 404 | Meeting not found | Skip or log |
| 429 | Rate limit | Exponential backoff |
| 500 | Zoom server error | Retry with backoff |

### Error Response Format
```json
{
    "code": 124,
    "message": "Invalid access token."
}
```

### Error Handling Implementation
```python
async def handle_zoom_error(response):
    """Classify and handle Zoom API errors"""
    if response.status_code == 401:
        raise IntegrationError(
            error_type=IntegrationErrorType.AUTH_EXPIRED,
            message="Zoom access token expired",
            platform="zoom",
            recoverable=True
        )
    elif response.status_code == 429:
        raise IntegrationError(
            error_type=IntegrationErrorType.RATE_LIMIT,
            message="Zoom rate limit exceeded",
            platform="zoom",
            recoverable=True,
            retry_after=int(response.headers.get('Retry-After', 60))
        )
    # ... handle other errors
```

---

## Testing Strategy

### Unit Tests
```python
@pytest.mark.asyncio
async def test_zoom_oauth_flow():
    """Test Zoom OAuth authorization flow"""
    connector = ZoomMCPConnector(integration_id="test", config=test_config)

    # Mock OAuth response
    with mock_zoom_oauth():
        tokens = await connector.authorize("test_auth_code")

    assert "access_token" in tokens
    assert "refresh_token" in tokens
    assert tokens["expires_in"] == 3600
```

### Integration Tests
```python
@pytest.mark.integration
async def test_fetch_zoom_recordings():
    """Test fetching Zoom recordings (requires test account)"""
    connector = await create_test_connector("zoom")

    recordings = await connector.fetch_recordings(
        from_date=datetime.now() - timedelta(days=7)
    )

    assert len(recordings) > 0
    assert all("recording_files" in r for r in recordings)
```

### Mock Data
```python
MOCK_ZOOM_RECORDING = {
    "uuid": "test123==",
    "id": 123456789,
    "topic": "Test Meeting",
    "start_time": "2025-10-30T10:00:00Z",
    "duration": 60,
    "recording_files": [
        {
            "id": "rec123",
            "file_type": "TRANSCRIPT",
            "download_url": "https://test.zoom.us/rec/download/..."
        }
    ]
}
```

---

## Implementation Checklist

- [ ] OAuth connector class implemented
- [ ] Token encryption/decryption
- [ ] Meeting list endpoint
- [ ] Recording fetch endpoint
- [ ] Transcript download and parsing
- [ ] Webhook registration
- [ ] Webhook verification
- [ ] Health check implementation
- [ ] Rate limiting enforcement
- [ ] Error handling and retry logic
- [ ] Unit tests (>80% coverage)
- [ ] Integration tests
- [ ] Documentation updates

---

## Deployment Configuration

### Environment Variables
```bash
ZOOM_CLIENT_ID=your_client_id
ZOOM_CLIENT_SECRET=your_client_secret
ZOOM_WEBHOOK_SECRET=your_webhook_secret
ZOOM_REDIRECT_URI=https://app.aicos.ai/integrations/callback/zoom
```

### Feature Flags
```python
ZOOM_FEATURES = {
    "webhook_enabled": True,
    "live_transcription": False,  # Future feature
    "auto_download_recordings": True,
    "max_recording_age_days": 90
}
```

---

## Monitoring & Alerts

### Key Metrics
- OAuth success rate
- Token refresh success rate
- API request latency (p50, p95, p99)
- Webhook delivery success rate
- Recording fetch success rate
- Transcript processing time

### Alerts
- OAuth failures > 5% in 1 hour
- Webhook delivery failures > 10% in 1 hour
- API latency p95 > 2 seconds
- Rate limit hits > 10 in 1 hour
- Circuit breaker opened

---

**Last Updated:** 2025-10-30
**Maintained By:** Integration Team
