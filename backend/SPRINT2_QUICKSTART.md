# Sprint 2 Quick Start Guide

## Getting Started with MCP Integration Framework

This guide will help you quickly set up and test the Sprint 2 MCP Integration Framework.

---

## Prerequisites

1. **Sprint 1 Complete**
   - Database schema created
   - Supabase configured
   - Backend running

2. **OAuth App Credentials**
   - At least one OAuth app configured (Zoom, Slack, etc.)
   - Redirect URIs configured correctly

---

## Installation

### 1. Install New Dependencies

```bash
cd /Users/aideveloper/Desktop/founderhouse-main/backend
pip install -r requirements.txt
```

New packages installed:
- `authlib==1.3.0` - OAuth library
- `oauthlib==3.2.2` - OAuth utilities
- `apscheduler==3.10.4` - Background task scheduling

### 2. Update Environment Variables

Copy the new variables from `.env.example` to your `.env`:

```bash
# OAuth Credentials (add at least one)
ZOOM_CLIENT_ID=your_zoom_client_id
ZOOM_CLIENT_SECRET=your_zoom_client_secret

# Background Tasks
ENABLE_HEALTH_CHECKS=true
HEALTH_CHECK_INTERVAL_HOURS=6
```

### 3. Start the Backend

```bash
cd /Users/aideveloper/Desktop/founderhouse-main/backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

You should see:
```
INFO:     Integration health check scheduler initialized
INFO:     Scheduled integration health checks every 6 hours
```

---

## Testing the Features

### 1. Test OAuth Flow (Zoom Example)

#### Step 1: Get Authorization URL

```bash
curl -X POST "http://localhost:8000/api/v1/oauth/zoom/authorize" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json"
```

Response:
```json
{
  "authorization_url": "https://zoom.us/oauth/authorize?client_id=...",
  "state": "abc123...",
  "platform": "zoom"
}
```

#### Step 2: Visit Authorization URL
- Copy the `authorization_url` from the response
- Open it in a browser
- Grant permissions on Zoom
- You'll be redirected back to the callback URL
- The integration will be created automatically

### 2. Test Connector Directly

Create a test script `/Users/aideveloper/Desktop/founderhouse-main/backend/test_connector.py`:

```python
import asyncio
from app.connectors.connector_registry import get_connector

async def test_zoom():
    credentials = {
        "access_token": "your_zoom_access_token"
    }

    async with get_connector("zoom", credentials) as connector:
        # Test connection
        result = await connector.test_connection()
        print(f"Connection: {result.status}")

        # List meetings
        meetings = await connector.list_meetings()
        print(f"Meetings: {meetings.data}")

if __name__ == "__main__":
    asyncio.run(test_zoom())
```

Run it:
```bash
cd /Users/aideveloper/Desktop/founderhouse-main/backend
python test_connector.py
```

### 3. Test Health Dashboard

```bash
curl -X GET "http://localhost:8000/api/v1/integrations/health-dashboard" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

Response:
```json
{
  "workspace_id": "...",
  "summary": {
    "total_integrations": 2,
    "healthy": 1,
    "unhealthy": 1,
    "success_rate": 50.0
  },
  "platform_health": {
    "zoom": {
      "total": 1,
      "healthy": 1,
      "unhealthy": 0
    }
  },
  "recent_errors": []
}
```

### 4. Test Manual Health Check

```bash
curl -X GET "http://localhost:8000/api/v1/integrations/INTEGRATION_ID/health" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

---

## Running Tests

### Run All Tests
```bash
cd /Users/aideveloper/Desktop/founderhouse-main/backend
pytest tests/ -v
```

### Run Specific Test Files
```bash
# Connector tests
pytest tests/test_connectors.py -v

# OAuth service tests
pytest tests/test_oauth_service.py -v

# Health check tests
pytest tests/test_health_check_service.py -v
```

### Test Coverage
```bash
pytest tests/ --cov=app --cov-report=html
```

View coverage report:
```bash
open htmlcov/index.html
```

---

## Configuration Options

### Health Check Interval

Change health check frequency in `.env`:

```bash
# Check every 3 hours instead of 6
HEALTH_CHECK_INTERVAL_HOURS=3
```

### Disable Health Checks

```bash
ENABLE_HEALTH_CHECKS=false
```

### Debug Logging

Enable detailed logging:

```bash
LOG_LEVEL=DEBUG
```

---

## Common Use Cases

### 1. Add a New Integration

**Via API:**
```bash
curl -X POST "http://localhost:8000/api/v1/integrations/connect" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "platform": "slack",
    "connection_type": "mcp",
    "credentials": {
      "access_token": "xoxb-your-token"
    }
  }'
```

**Via OAuth:**
1. POST to `/api/v1/oauth/slack/authorize`
2. Redirect user to returned URL
3. User grants permissions
4. Integration created automatically

### 2. List All Integrations

```bash
curl -X GET "http://localhost:8000/api/v1/integrations" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### 3. Check Integration Status

```bash
curl -X GET "http://localhost:8000/api/v1/integrations/status" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### 4. Refresh OAuth Token

```bash
curl -X POST "http://localhost:8000/api/v1/oauth/zoom/refresh?integration_id=INTEGRATION_ID" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### 5. Disconnect Integration

```bash
curl -X DELETE "http://localhost:8000/api/v1/integrations/INTEGRATION_ID" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

---

## Supported Platforms

| Platform | OAuth Support | API Type | Credentials Required |
|----------|--------------|----------|---------------------|
| Zoom | ✅ Yes | REST | Client ID + Secret |
| Slack | ✅ Yes | REST | Access Token |
| Discord | ✅ Yes | REST | Bot Token / OAuth |
| Outlook | ✅ Yes | Graph API | Client ID + Secret |
| Monday | ✅ Yes | GraphQL | API Token |
| Notion | ✅ Yes | REST | Access Token |
| Gmail | ✅ Yes | REST | Client ID + Secret |
| Loom | ✅ Yes | REST | API Key / OAuth |
| Fireflies | ❌ No | GraphQL | API Key |
| Otter | ❌ No | REST | API Key |
| Granola | ❌ No | REST | API Key |
| ZeroDB | ❌ No | PostgreSQL | DB Credentials |
| ZeroVoice | ❌ No | Twilio | Account SID + Token |

---

## API Documentation

### Interactive Docs

Visit: http://localhost:8000/docs

Features:
- Try out all endpoints
- View request/response schemas
- Test OAuth flows
- See example requests

### ReDoc

Visit: http://localhost:8000/redoc

Alternative documentation with:
- Cleaner layout
- Easier navigation
- Printer-friendly format

---

## Monitoring & Debugging

### Check Application Logs

```bash
# In development
tail -f logs/app.log

# Check for errors
grep "ERROR" logs/app.log

# Check health checks
grep "health_check" logs/app.log
```

### View Database Events

Query ops.events table:

```sql
SELECT * FROM ops.events
WHERE event_type = 'integration_health_check'
ORDER BY created_at DESC
LIMIT 10;
```

### Check Scheduler Status

The scheduler logs on startup:
```
INFO: Scheduled integration health checks every 6 hours
```

---

## Troubleshooting

### Issue: OAuth Callback Not Working

**Problem:** Redirect doesn't work after authorization

**Solution:**
1. Check redirect URI in OAuth app settings matches:
   ```
   http://localhost:8000/api/v1/oauth/{platform}/callback
   ```
2. Verify CORS settings in `config.py`
3. Check state parameter hasn't expired

### Issue: Health Checks Failing

**Problem:** All integrations showing as unhealthy

**Solution:**
1. Check credentials are still valid
2. Verify network connectivity to platforms
3. Review rate limiting status
4. Check platform API status pages

### Issue: Background Tasks Not Running

**Problem:** Health checks not executing

**Solution:**
1. Verify `ENABLE_HEALTH_CHECKS=true` in `.env`
2. Check application startup logs
3. Ensure APScheduler is installed
4. Check for scheduler initialization errors

### Issue: Import Errors

**Problem:** Cannot import new modules

**Solution:**
```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall

# Clear Python cache
find . -type d -name __pycache__ -exec rm -r {} +
```

---

## Performance Optimization

### Reduce Health Check Load

For development, reduce check frequency:
```bash
HEALTH_CHECK_INTERVAL_HOURS=24
```

Or disable:
```bash
ENABLE_HEALTH_CHECKS=false
```

### Connection Pooling

Connectors automatically pool HTTP connections. Adjust timeout in connector:

```python
connector = ZoomConnector(credentials, config={"timeout": 30})
```

### Concurrent Health Checks

Health checks run concurrently by default. Configure concurrency in `integration_health.py`.

---

## Next Steps

1. **Configure OAuth Apps**
   - Set up OAuth apps for platforms you want to use
   - Add credentials to `.env`

2. **Test Integration Flow**
   - Connect at least one platform
   - Verify OAuth flow works end-to-end
   - Check health dashboard shows correct status

3. **Customize Health Checks**
   - Adjust check interval as needed
   - Configure alerting for failures
   - Set up monitoring dashboard

4. **Prepare for Sprint 3**
   - Meeting intelligence features
   - Communication aggregation
   - Frontend integration

---

## Support

### Documentation
- Full delivery doc: `/Users/aideveloper/Desktop/founderhouse-main/backend/SPRINT2_DELIVERY.md`
- API docs: http://localhost:8000/docs

### Testing
- Unit tests: `/Users/aideveloper/Desktop/founderhouse-main/backend/tests/`
- Run: `pytest tests/ -v`

### Code Location
All Sprint 2 code is in:
- `/Users/aideveloper/Desktop/founderhouse-main/backend/app/`

---

## Success Checklist

- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] Environment variables configured
- [ ] Backend starts without errors
- [ ] Health check scheduler initializes
- [ ] Can generate OAuth authorization URL
- [ ] Can test connector directly
- [ ] Health dashboard returns data
- [ ] All tests pass (`pytest tests/ -v`)
- [ ] API documentation accessible

---

**Congratulations! You're ready to use the MCP Integration Framework.**

For detailed information, see `SPRINT2_DELIVERY.md`.
