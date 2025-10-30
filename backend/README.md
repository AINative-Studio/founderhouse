# AI Chief of Staff - Backend API

Production-ready FastAPI backend for the AI Chief of Staff project - Sprint 1.

## Overview

The AI Chief of Staff is a multi-agent executive operations system that acts as a founder's intelligent operator, synthesizing meetings, communications, documents, and metrics across dozens of tools through MCP (Model Context Protocol) servers.

### Tech Stack

- **Framework**: FastAPI 0.109+
- **Database**: Supabase (PostgreSQL + pgvector)
- **Authentication**: JWT + Supabase Auth
- **Vector Search**: pgvector (1536 dimensions)
- **Python**: 3.11+

## Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application entry point
│   ├── config.py            # Environment configuration (Pydantic)
│   ├── database.py          # Supabase client and connection management
│   ├── models/              # Pydantic models for request/response validation
│   │   ├── __init__.py
│   │   ├── workspace.py     # Workspace models
│   │   ├── founder.py       # Founder models
│   │   └── integration.py   # Integration models
│   ├── api/
│   │   ├── __init__.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── health.py    # Health check endpoints
│   │       ├── workspaces.py # Workspace management
│   │       └── integrations.py # Integration management
│   ├── core/
│   │   ├── __init__.py
│   │   ├── security.py      # Authentication & JWT handling
│   │   └── dependencies.py  # FastAPI dependency injection
│   └── services/            # Business logic layer
│       ├── __init__.py
│       ├── workspace_service.py
│       └── integration_service.py
├── requirements.txt
├── .env.example
└── README.md
```

## Features (Sprint 1)

### Core Infrastructure
- Multi-tenant workspace management with RLS
- Supabase connection with connection pooling
- Environment-based configuration
- Structured logging
- CORS and security middleware

### API Endpoints

#### Health & Monitoring
- `GET /health` - Comprehensive health check (database + system)
- `GET /version` - API version information
- `GET /ping` - Simple connectivity check

#### Workspaces
- `POST /api/v1/workspaces` - Create workspace
- `GET /api/v1/workspaces/{workspace_id}` - Get workspace details
- `GET /api/v1/workspaces` - List user workspaces
- `PATCH /api/v1/workspaces/{workspace_id}` - Update workspace
- `DELETE /api/v1/workspaces/{workspace_id}` - Delete workspace

#### Integrations
- `POST /api/v1/integrations/connect` - Connect MCP integration
- `GET /api/v1/integrations/status` - Get integration health status
- `GET /api/v1/integrations` - List integrations
- `GET /api/v1/integrations/{integration_id}` - Get integration details
- `GET /api/v1/integrations/{integration_id}/health` - Check integration health
- `PATCH /api/v1/integrations/{integration_id}` - Update integration
- `DELETE /api/v1/integrations/{integration_id}` - Disconnect integration
- `POST /api/v1/integrations/{integration_id}/refresh` - Refresh connection

### Security Features
- JWT Bearer token authentication
- Role-based access control (owner, admin, member, viewer)
- Workspace-level data isolation
- Encrypted credential storage (AES-256)
- Input validation and sanitization
- Rate limiting ready

## Setup Instructions

### Prerequisites

- Python 3.11 or higher
- Supabase account and project
- pip or poetry for package management

### 1. Clone Repository

```bash
git clone https://github.com/AINative-Studio/founderhouse.git
cd founderhouse/backend
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` and configure the following required variables:

```bash
# Supabase Configuration
SUPABASE_URL="https://your-project.supabase.co"
SUPABASE_KEY="your-anon-key"
SUPABASE_SERVICE_KEY="your-service-role-key"  # Optional, for admin operations

# Security
SECRET_KEY="your-secret-key-here"  # Generate with: openssl rand -hex 32

# Environment
ENVIRONMENT="development"
DEBUG=true
```

### 5. Set Up Supabase Database

#### Option A: Using Supabase Dashboard

1. Go to your Supabase project
2. Navigate to SQL Editor
3. Run the SQL from `/datamodel.md` to create schemas and tables

#### Option B: Using Supabase CLI

```bash
# Install Supabase CLI
npm install -g supabase

# Login and link project
supabase login
supabase link --project-ref your-project-ref

# Run migrations (if you create migration files)
supabase db push
```

### 6. Enable pgvector Extension

In Supabase SQL Editor:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### 7. Run the Application

#### Development Mode

```bash
# From backend directory
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Or:

```bash
python -m app.main
```

#### Production Mode

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 8. Access API Documentation

Once running, access:

- Interactive API docs: http://localhost:8000/docs
- Alternative docs: http://localhost:8000/redoc
- OpenAPI JSON: http://localhost:8000/openapi.json

## Configuration

### Environment Variables

All configuration is managed through environment variables. See `.env.example` for complete list.

#### Core Settings

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `SUPABASE_URL` | Supabase project URL | - | Yes |
| `SUPABASE_KEY` | Supabase anon key | - | Yes |
| `SECRET_KEY` | JWT secret key | - | Yes |
| `ENVIRONMENT` | Environment name | development | No |
| `DEBUG` | Debug mode | false | No |
| `ALLOWED_ORIGINS` | CORS origins (comma-separated) | localhost:3000 | No |

#### Integration Credentials

Configure credentials for MCP integrations:

- `ZOOM_CLIENT_ID`, `ZOOM_CLIENT_SECRET`
- `SLACK_CLIENT_ID`, `SLACK_CLIENT_SECRET`
- `DISCORD_BOT_TOKEN`
- `MONDAY_API_KEY`
- `NOTION_API_KEY`
- And more...

See `.env.example` for complete list.

## API Authentication

### JWT Token Format

All authenticated endpoints require a Bearer token:

```bash
Authorization: Bearer <jwt_token>
```

### Token Payload

```json
{
  "user_id": "uuid",
  "workspace_id": "uuid",
  "role": "owner|admin|member|viewer",
  "exp": 1234567890
}
```

### Creating a Token (Example)

```python
from app.core.security import create_access_token
from datetime import timedelta

token = create_access_token(
    data={
        "user_id": "user-uuid",
        "workspace_id": "workspace-uuid",
        "role": "admin"
    },
    expires_delta=timedelta(minutes=30)
)
```

## Testing

### Run Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-cov httpx

# Run tests
pytest

# With coverage
pytest --cov=app --cov-report=html
```

### Manual Testing with cURL

#### Health Check

```bash
curl http://localhost:8000/health
```

#### Create Workspace

```bash
curl -X POST http://localhost:8000/api/v1/workspaces \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "My Startup"}'
```

#### Connect Integration

```bash
curl -X POST http://localhost:8000/api/v1/integrations/connect \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "platform": "zoom",
    "connection_type": "mcp",
    "credentials": {
      "client_id": "your_client_id",
      "client_secret": "your_client_secret"
    }
  }'
```

## Database Schema

### Core Schemas

- `core.*` - Workspaces, founders, members, integrations, contacts
- `ops.*` - Event sourcing and audit logs
- `comms.*` - Communications (email, Slack, Discord) and threads
- `meetings.*` - Meetings, transcripts, participants
- `media.*` - Media assets (Loom videos) and transcripts
- `work.*` - Tasks and external task links
- `intel.*` - Briefings, insights, decisions

### Key Tables (Sprint 1)

- `core.workspaces` - Multi-tenant workspaces
- `core.members` - Workspace membership and roles
- `core.founders` - Founder profiles and preferences
- `core.integrations` - MCP and API integrations
- `ops.events` - Event sourcing for audit trail

See `/datamodel.md` for complete schema.

## Security Considerations

### Implemented

- JWT authentication with secure secret keys
- Role-based access control (RBAC)
- Encrypted credential storage (AES-256)
- Input validation with Pydantic
- CORS configuration
- SQL injection prevention (via Supabase client)
- Row-level security (RLS) ready

### TODO for Production

- [ ] Rate limiting implementation
- [ ] API key rotation mechanism
- [ ] Audit logging enhancement
- [ ] DDoS protection
- [ ] Input sanitization for XSS
- [ ] HTTPS enforcement
- [ ] Secrets management (AWS KMS / HashiCorp Vault)

## Deployment

### Railway

1. Install Railway CLI:
```bash
npm install -g @railway/cli
```

2. Login and initialize:
```bash
railway login
railway init
```

3. Set environment variables:
```bash
railway variables set SUPABASE_URL=...
railway variables set SUPABASE_KEY=...
# ... other variables
```

4. Deploy:
```bash
railway up
```

### Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Build and run:
```bash
docker build -t ai-chief-of-staff-api .
docker run -p 8000:8000 --env-file .env ai-chief-of-staff-api
```

## Troubleshooting

### Database Connection Issues

**Problem**: `Database health check failed`

**Solution**:
1. Verify Supabase URL and key in `.env`
2. Check Supabase project is active
3. Ensure RLS policies allow service role access
4. Check network connectivity

### Import Errors

**Problem**: `ModuleNotFoundError: No module named 'app'`

**Solution**:
```bash
# Ensure you're in the backend directory
cd backend

# Run with module syntax
python -m app.main
```

### Authentication Errors

**Problem**: `Invalid authentication credentials`

**Solution**:
1. Verify JWT token is valid
2. Check `SECRET_KEY` matches token creation
3. Ensure token hasn't expired
4. Verify Authorization header format: `Bearer <token>`

## Development Guidelines

### Code Style

- Follow PEP 8 style guide
- Use type hints for all functions
- Write docstrings for public functions
- Maximum line length: 100 characters

### Git Workflow

1. Create feature branch from `main`
2. Make changes with clear commit messages
3. Run tests before committing
4. Create pull request for review
5. Merge after approval

### Adding New Endpoints

1. Create Pydantic models in `app/models/`
2. Implement business logic in `app/services/`
3. Create API routes in `app/api/v1/`
4. Add tests in `tests/`
5. Update API documentation

## Sprint 1 Deliverables Checklist

- [x] Project structure and organization
- [x] FastAPI application with proper configuration
- [x] Supabase database connection
- [x] Health check endpoints
- [x] Workspace management endpoints
- [x] Integration management endpoints
- [x] JWT authentication and security
- [x] Pydantic models for validation
- [x] Service layer for business logic
- [x] Error handling and logging
- [x] CORS and middleware configuration
- [x] OpenAPI documentation
- [x] Environment configuration
- [x] README with setup instructions
- [ ] Unit tests (TODO: Sprint 1 completion)
- [ ] Integration tests (TODO: Sprint 1 completion)

## Next Steps (Sprint 2+)

- OAuth flows for integrations
- Token refresh mechanism
- Integration health check scheduler
- MCP connector implementations
- Meeting ingestion pipeline
- Communication aggregation
- Task synchronization

## Support

- **Documentation**: See `/prd.md` and `/sprint-plan.md`
- **Issues**: https://github.com/AINative-Studio/founderhouse/issues
- **Email**: support@ainative.studio

## License

See LICENSE file in repository root.

---

Built with FastAPI and Supabase for Sprint 1 of the AI Chief of Staff project.
