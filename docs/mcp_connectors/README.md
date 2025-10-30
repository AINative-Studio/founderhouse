# MCP Connector Specifications

This directory contains detailed specifications for each MCP (Model Context Protocol) integration connector.

## Connector List

### Communication Platforms
- [Gmail MCP](./gmail_mcp.md) - Email integration via Google Gmail API
- [Outlook MCP](./outlook_mcp.md) - Email integration via Microsoft Graph API
- [Slack MCP](./slack_mcp.md) - Team messaging via Slack API
- [Discord MCP](./discord_mcp.md) - Community messaging via Discord API

### Meeting & Transcription Platforms
- [Zoom MCP](./zoom_mcp.md) - Video meetings and recordings
- [Fireflies MCP](./fireflies_mcp.md) - AI meeting transcription
- [Otter MCP](./otter_mcp.md) - Voice transcription and notes

### Media Platforms
- [Loom MCP](./loom_mcp.md) - Async video messaging

### Work Management
- [Monday MCP](./monday_mcp.md) - Project and task management
- [Notion MCP](./notion_mcp.md) - Knowledge base and documentation

### Analytics & Infrastructure
- [Granola MCP](./granola_mcp.md) - Business KPIs and metrics
- [ZeroDB MCP](./zerodb_mcp.md) - Vector memory and embeddings
- [ZeroVoice MCP](./zerovoice_mcp.md) - Voice-to-text processing

## Specification Template

Each connector specification includes:

1. **Platform Overview** - What the platform does and integration value
2. **OAuth Configuration** - Authorization flow details
3. **API Endpoints** - Key endpoints used
4. **Scopes & Permissions** - Required OAuth scopes
5. **Webhook Configuration** - Real-time event delivery
6. **Rate Limiting** - Platform-specific limits
7. **Data Models** - How data maps to our schema
8. **Error Handling** - Platform-specific error scenarios
9. **Testing Strategy** - How to test the integration

## Implementation Priority

### Sprint 2 (Current)
1. Zoom MCP - Primary meeting source
2. Slack MCP - Team communication
3. Gmail MCP - Email aggregation
4. Monday MCP - Task management

### Sprint 3
5. Fireflies MCP - Meeting transcription
6. Outlook MCP - Email aggregation
7. Discord MCP - Community communication
8. Loom MCP - Async video

### Sprint 4+
9. Otter MCP - Additional transcription
10. Notion MCP - Documentation
11. Granola MCP - KPIs
12. ZeroDB MCP - Vector memory
13. ZeroVoice MCP - Voice processing

## Common Patterns

### Authentication Flow
All connectors follow OAuth 2.0 Authorization Code Flow with PKCE:
```
User → Initiate → OAuth Provider → Callback → Token Exchange → Encrypted Storage
```

### Webhook Pattern
Platforms supporting webhooks:
```
Register Webhook → Receive Events → Verify Signature → Process → Acknowledge
```

### Polling Pattern
Platforms without webhooks:
```
Scheduled Job → Fetch Since Last Sync → Process New Items → Update Cursor
```

### Error Recovery
All connectors implement:
- Exponential backoff retry (3 attempts)
- Circuit breaker (5 failures)
- Automatic token refresh
- Health check monitoring

## Development Guidelines

1. **Use Connector Base Class** - All connectors inherit from `MCPConnector`
2. **Implement Standard Interface** - Required methods: `authorize`, `refresh_token`, `health_check`, `disconnect`
3. **Log All Events** - Every integration action logged to `ops.events`
4. **Encrypt Credentials** - All tokens encrypted with AES-256-GCM
5. **Test Coverage** - Minimum 80% test coverage per connector
6. **Documentation** - Update this README when adding new connectors

## Security Considerations

- Minimum necessary OAuth scopes
- Token encryption at rest (AES-256-GCM)
- Webhook signature verification
- Rate limiting enforcement
- Circuit breaker protection
- Audit logging

## Support & Troubleshooting

For connector issues:
1. Check health status in database: `mcp.v_integration_health_summary`
2. Review error logs: `mcp.integration_errors`
3. Verify OAuth scopes match requirements
4. Check rate limit status: `mcp.rate_limits`
5. Review webhook delivery: `mcp.webhook_events`
