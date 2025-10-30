# MCP Connectors - Complete Summary

**Version:** 1.0
**Date:** 2025-10-30
**Sprint:** 2 - MCP Integration Framework

This document provides specifications for all 13 MCP platform connectors.

---

## 1. Gmail MCP

### Platform: Google Gmail
**API:** Gmail API v1
**OAuth Provider:** Google OAuth 2.0
**Documentation:** https://developers.google.com/gmail/api

### OAuth Scopes
```
https://www.googleapis.com/auth/gmail.readonly
https://www.googleapis.com/auth/gmail.send (optional)
https://www.googleapis.com/auth/gmail.modify
```

### Key Endpoints
- `GET /gmail/v1/users/me/messages` - List messages
- `GET /gmail/v1/users/me/messages/{id}` - Get message details
- `GET /gmail/v1/users/me/threads` - List threads
- `POST /gmail/v1/users/me/watch` - Setup push notifications

### Rate Limits
- 250 quota units per user per second
- 1 billion quota units per day per project

### Webhook Support
Gmail Pub/Sub push notifications via Cloud Pub/Sub

### Data Mapping
```python
gmail_message → comms.communications
gmail_thread → comms.threads
```

---

## 2. Outlook MCP

### Platform: Microsoft Outlook
**API:** Microsoft Graph API
**OAuth Provider:** Microsoft Identity Platform
**Documentation:** https://learn.microsoft.com/en-us/graph/api/

### OAuth Scopes
```
Mail.Read
Mail.Send
Mail.ReadWrite
User.Read
Calendars.Read
```

### Key Endpoints
- `GET /me/messages` - List messages
- `GET /me/messages/{id}` - Get message
- `GET /me/mailFolders/{id}/messages` - Folder messages
- `POST /subscriptions` - Create webhook subscription

### Rate Limits
- 10,000 requests per 10 minutes per app per user
- Uses throttling with retry-after headers

### Webhook Support
Microsoft Graph webhooks with subscription validation

### Data Mapping
```python
outlook_message → comms.communications
outlook_conversation → comms.threads
```

---

## 3. Slack MCP

### Platform: Slack
**API:** Slack Web API
**OAuth Provider:** Slack OAuth 2.0
**Documentation:** https://api.slack.com/

### OAuth Scopes
```
channels:history
channels:read
chat:write
groups:history
im:history
users:read
```

### Key Endpoints
- `GET /conversations.list` - List channels
- `GET /conversations.history` - Channel messages
- `POST /chat.postMessage` - Send message
- WebSocket RTM API for real-time

### Rate Limits
- Tier 1: 1+ request per minute
- Tier 2: 20+ requests per minute
- Tier 3: 50+ requests per minute
- Tier 4: 100+ requests per minute

### Webhook Support
Events API with request URL verification

### Data Mapping
```python
slack_message → comms.communications
slack_channel → comms.threads
```

---

## 4. Discord MCP

### Platform: Discord
**API:** Discord API v10
**OAuth Provider:** Discord OAuth2
**Documentation:** https://discord.com/developers/docs

### OAuth Scopes
```
identify
guilds
guilds.members.read
messages.read
```

### Key Endpoints
- `GET /users/@me/guilds` - List guilds
- `GET /channels/{channel.id}/messages` - Get messages
- `POST /channels/{channel.id}/messages` - Send message
- Gateway WebSocket for real-time events

### Rate Limits
- Global: 50 requests per second
- Per-route limits vary
- Uses X-RateLimit headers

### Webhook Support
Discord Webhooks with signature verification

### Data Mapping
```python
discord_message → comms.communications
discord_channel → comms.threads
```

---

## 5. Zoom MCP

### Platform: Zoom Video Communications
**See:** [zoom_mcp.md](./zoom_mcp.md) for full specification

### Quick Reference
- **OAuth Scopes:** meeting:read, recording:read
- **Rate Limits:** 10 req/sec per user
- **Webhooks:** meeting.ended, recording.completed
- **Key Data:** meetings, recordings, transcripts

---

## 6. Fireflies MCP

### Platform: Fireflies.ai
**API:** Fireflies GraphQL API
**OAuth Provider:** Fireflies OAuth (or API key)
**Documentation:** https://docs.fireflies.ai/

### Authentication
API Key based (not OAuth)
```
X-API-Key: your_api_key
```

### Key Endpoints (GraphQL)
```graphql
query {
  transcripts(limit: 10) {
    id
    title
    date
    duration
    sentences {
      text
      speaker_name
      start_time
    }
  }
}
```

### Webhook Support
Fireflies webhooks for transcript completion

### Data Mapping
```python
fireflies_transcript → meetings.transcripts
fireflies_sentence → meetings.transcript_chunks
```

---

## 7. Otter MCP

### Platform: Otter.ai
**API:** Otter API
**OAuth Provider:** Otter OAuth 2.0
**Documentation:** https://otter.ai/developer

### OAuth Scopes
```
otter.speech:read
otter.speech:write
```

### Key Endpoints
- `GET /api/v1/speeches` - List speeches
- `GET /api/v1/speeches/{id}` - Get transcript
- `GET /api/v1/speeches/{id}/paragraphs` - Transcript chunks

### Rate Limits
- 100 requests per hour (free tier)
- 1000 requests per hour (paid tier)

### Data Mapping
```python
otter_speech → meetings.transcripts
otter_paragraph → meetings.transcript_chunks
```

---

## 8. Loom MCP

### Platform: Loom
**API:** Loom API
**OAuth Provider:** Loom OAuth 2.0
**Documentation:** https://dev.loom.com/

### OAuth Scopes
```
video:read
video:write (optional)
```

### Key Endpoints
- `GET /api/v1/videos` - List videos
- `GET /api/v1/videos/{id}` - Video details
- `GET /api/v1/videos/{id}/transcript` - Get transcript

### Rate Limits
- 60 requests per minute per user
- 1000 requests per hour per user

### Webhook Support
Loom webhooks for video.created, video.shared

### Data Mapping
```python
loom_video → media.media_assets
loom_transcript → media.media_transcripts
```

---

## 9. Monday MCP

### Platform: Monday.com
**API:** Monday GraphQL API
**OAuth Provider:** Monday OAuth 2.0
**Documentation:** https://developer.monday.com/

### OAuth Scopes
```
boards:read
boards:write
workspaces:read
```

### Key Endpoints (GraphQL)
```graphql
mutation {
  create_item(
    board_id: 123,
    item_name: "New Task",
    column_values: "{\"status\": \"Working on it\"}"
  ) {
    id
  }
}

query {
  boards {
    id
    name
    items {
      id
      name
      column_values {
        id
        text
      }
    }
  }
}
```

### Rate Limits
- 60 requests per minute per app
- Complexity-based rate limiting

### Webhook Support
Monday webhooks for item updates

### Data Mapping
```python
monday_item → work.tasks
monday_board_id → work.task_links.external_id
```

---

## 10. Notion MCP

### Platform: Notion
**API:** Notion API
**OAuth Provider:** Notion OAuth 2.0
**Documentation:** https://developers.notion.com/

### OAuth Scopes
```
read_content
update_content
insert_content
```

### Key Endpoints
- `POST /v1/search` - Search pages
- `GET /v1/pages/{page_id}` - Get page
- `POST /v1/pages` - Create page
- `PATCH /v1/pages/{page_id}` - Update page
- `GET /v1/blocks/{block_id}/children` - Get page content

### Rate Limits
- 3 requests per second average
- Burst up to 10 requests

### Data Mapping
```python
notion_page → work.tasks (for task databases)
notion_page → intel.briefings (for briefing pages)
```

---

## 11. Granola MCP

### Platform: Granola
**API:** Granola API (custom)
**Authentication:** API Key
**Documentation:** (Internal/Custom)

### Authentication
```
Authorization: Bearer <api_key>
```

### Key Endpoints
- `GET /api/v1/metrics` - KPI metrics
- `GET /api/v1/metrics/{metric_id}` - Specific metric
- `GET /api/v1/metrics/timeseries` - Time series data

### Data Mapping
```python
granola_metric → intel.insights (insight_type='kpi')
```

---

## 12. ZeroDB MCP

### Platform: ZeroDB (Vector Database)
**API:** ZeroDB API
**Authentication:** API Key
**Purpose:** Embedding storage and semantic search

### Key Operations
- `POST /embeddings` - Store embeddings
- `POST /search` - Semantic search
- `GET /embeddings/{id}` - Retrieve embedding

### Data Mapping
```python
# Embeddings stored in both ZeroDB and local tables
# ZeroDB acts as distributed vector store
local_embedding → zerodb_embedding (sync)
```

---

## 13. ZeroVoice MCP

### Platform: ZeroVoice (Twilio-based)
**API:** Twilio Voice API
**OAuth Provider:** Twilio Auth Token
**Documentation:** https://www.twilio.com/docs/voice

### Authentication
```
Account SID + Auth Token
```

### Key Endpoints
- `POST /2010-04-01/Accounts/{AccountSid}/Calls` - Make call
- `GET /2010-04-01/Accounts/{AccountSid}/Calls/{CallSid}` - Call status
- Webhook callbacks for call events

### Webhook Support
Twilio webhooks for call status, recording

### Data Mapping
```python
twilio_call → media.media_assets
twilio_transcription → media.media_transcripts
```

---

## Connector Implementation Matrix

| Platform | OAuth | Webhooks | Rate Limit | Priority | Status |
|----------|-------|----------|------------|----------|--------|
| Zoom | OAuth 2.0 | ✓ | 10/sec | P0 | Sprint 2 |
| Slack | OAuth 2.0 | ✓ | Tiered | P0 | Sprint 2 |
| Gmail | OAuth 2.0 | ✓ Pub/Sub | 250/sec | P0 | Sprint 2 |
| Monday | OAuth 2.0 | ✓ | 60/min | P0 | Sprint 2 |
| Outlook | OAuth 2.0 | ✓ | 10k/10min | P1 | Sprint 3 |
| Discord | OAuth 2.0 | ✓ | 50/sec | P1 | Sprint 3 |
| Fireflies | API Key | ✓ | N/A | P1 | Sprint 3 |
| Loom | OAuth 2.0 | ✓ | 60/min | P1 | Sprint 3 |
| Otter | OAuth 2.0 | ✗ | 100/hr | P2 | Sprint 4 |
| Notion | OAuth 2.0 | ✗ | 3/sec | P2 | Sprint 4 |
| Granola | API Key | ✗ | N/A | P2 | Sprint 4 |
| ZeroDB | API Key | ✗ | N/A | P2 | Sprint 4 |
| ZeroVoice | Auth Token | ✓ | N/A | P2 | Sprint 5 |

---

## Common Implementation Patterns

### Pattern 1: OAuth Connector
Used by: Zoom, Slack, Gmail, Outlook, Monday, Notion, Loom, Otter, Discord

```python
class OAuthConnector(MCPConnector):
    async def authorize(self, auth_code: str) -> dict:
        # Exchange code for tokens
        pass

    async def refresh_token(self, refresh_token: str) -> dict:
        # Refresh access token
        pass

    async def health_check(self) -> dict:
        # Test API connection
        pass
```

### Pattern 2: API Key Connector
Used by: Fireflies, Granola, ZeroDB

```python
class APIKeyConnector(MCPConnector):
    async def authorize(self, api_key: str) -> dict:
        # Store and verify API key
        pass

    async def health_check(self) -> dict:
        # Test API with key
        pass
```

### Pattern 3: Webhook Receiver
Used by: Zoom, Slack, Gmail, Outlook, Monday, Loom, Discord, Fireflies, ZeroVoice

```python
class WebhookConnector(MCPConnector):
    async def register_webhook(self, callback_url: str) -> str:
        # Register webhook with platform
        pass

    async def verify_webhook(self, request: Request) -> bool:
        # Verify webhook signature
        pass

    async def process_webhook(self, payload: dict) -> None:
        # Process incoming webhook event
        pass
```

---

## Security Considerations

### All Connectors Must:
1. Encrypt credentials at rest (AES-256-GCM)
2. Use HTTPS for all API calls
3. Verify webhook signatures
4. Implement rate limiting
5. Log all integration events
6. Handle token refresh automatically
7. Implement circuit breaker pattern
8. Provide health check endpoint

### Platform-Specific Security:
- **Gmail/Outlook:** OAuth with offline_access scope
- **Slack/Discord:** Verify request signatures
- **Zoom:** Validate webhook secret token
- **API Key platforms:** Rotate keys every 90 days

---

## Testing Requirements

### Each Connector Must Have:
1. Unit tests (>80% coverage)
2. OAuth flow tests
3. API endpoint mocks
4. Webhook verification tests
5. Rate limit handling tests
6. Error recovery tests
7. Integration tests (with test accounts)

### Test Template:
```python
@pytest.mark.asyncio
async def test_platform_oauth_flow():
    """Test OAuth authorization flow"""
    pass

@pytest.mark.asyncio
async def test_platform_data_fetch():
    """Test data fetching"""
    pass

@pytest.mark.asyncio
async def test_platform_webhook_verification():
    """Test webhook signature verification"""
    pass

@pytest.mark.asyncio
async def test_platform_rate_limiting():
    """Test rate limit handling"""
    pass

@pytest.mark.asyncio
async def test_platform_error_recovery():
    """Test error recovery"""
    pass
```

---

## Deployment Checklist

For each connector:
- [ ] OAuth credentials configured (dev, staging, prod)
- [ ] Webhook URLs registered with platform
- [ ] Rate limits configured in application
- [ ] Circuit breaker thresholds set
- [ ] Health check schedule configured
- [ ] Error alerts configured
- [ ] Documentation complete
- [ ] Tests passing (>80% coverage)
- [ ] Security review completed
- [ ] Monitored in production

---

## Monitoring & Observability

### Metrics to Track (per connector):
- OAuth success rate
- Token refresh success rate
- API request latency (p50, p95, p99)
- API error rate
- Webhook delivery success rate
- Data sync lag
- Health check status
- Circuit breaker state

### Dashboards:
1. **Integration Health Dashboard** - Real-time status of all integrations
2. **OAuth Flow Dashboard** - OAuth success/failure rates
3. **API Performance Dashboard** - Latency and error rates
4. **Webhook Dashboard** - Delivery success and processing time

---

## Support & Troubleshooting

### Common Issues:

**OAuth Failures:**
- Check redirect URI matches exactly
- Verify OAuth scopes are correct
- Ensure app credentials are valid
- Check user has permissions

**API Errors:**
- Check rate limits
- Verify authentication tokens
- Review API version compatibility
- Check for platform outages

**Webhook Issues:**
- Verify callback URL is accessible
- Check signature verification logic
- Ensure webhook is registered
- Review event subscription settings

### Debug Queries:
```sql
-- Check integration health
SELECT * FROM mcp.v_integration_health_summary
WHERE platform = 'zoom';

-- View recent errors
SELECT * FROM mcp.integration_errors
WHERE integration_id = '<id>'
ORDER BY created_at DESC;

-- Check webhook delivery
SELECT * FROM mcp.webhook_events
WHERE integration_id = '<id>'
AND processed = false;
```

---

**Document Version:** 1.0
**Last Updated:** 2025-10-30
**Maintained By:** Integration Team
