# Infrastructure Summary - AI Chief of Staff

## Overview

This document provides a complete overview of the DevOps infrastructure setup for the AI Chief of Staff project.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        Developer Workstation                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  VS Code/IDE │  │  Docker      │  │  Make        │          │
│  │  + Python    │  │  Desktop     │  │  Commands    │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                          GitHub                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                     CI/CD Pipeline                        │  │
│  │  • Linting (Black, Flake8, MyPy)                          │  │
│  │  • Testing (Pytest + Coverage)                            │  │
│  │  • Security Scanning (Safety, Bandit, Trivy)              │  │
│  │  • Docker Build                                            │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                 ┌────────────┴────────────┐
                 ↓                          ↓
┌─────────────────────────┐  ┌─────────────────────────┐
│    Staging (Railway)    │  │  Production (Railway)   │
│  • Auto-deploy on main  │  │  • Manual deploy        │
│  • Health checks        │  │  • Comprehensive tests  │
│  • Smoke tests          │  │  • Monitoring           │
└─────────────────────────┘  └─────────────────────────┘
         │                              │
         ↓                              ↓
┌─────────────────────────┐  ┌─────────────────────────┐
│  Supabase (Database)    │  │  Supabase (Database)    │
│  • PostgreSQL 16        │  │  • PostgreSQL 16        │
│  • pgvector             │  │  • pgvector             │
│  • Staging data         │  │  • Production data      │
└─────────────────────────┘  └─────────────────────────┘
```

## Infrastructure Components

### 1. Containerization (Docker)

**Files:**
- `/Dockerfile` - Production-optimized multi-stage build
- `/docker-compose.yml` - Local development services
- `/.dockerignore` - Exclude unnecessary files from builds

**Services in docker-compose.yml:**
- **api** - FastAPI backend with hot reload
- **postgres** - PostgreSQL 16 + pgvector
- **redis** - Redis for caching and rate limiting
- **pgadmin** - Database management UI (optional)

**Key Features:**
- Multi-stage build for smaller images
- Non-root user for security
- Health checks for all services
- Volume persistence
- Network isolation

### 2. CI/CD Pipeline (GitHub Actions)

**Workflows:**

#### `.github/workflows/ci.yml` - Continuous Integration
Triggers: Push to main/develop, Pull Requests

Jobs:
1. **lint** - Code quality checks
   - Black (formatting)
   - isort (imports)
   - Flake8 (linting)
   - MyPy (type checking)

2. **test** - Unit & Integration tests
   - Pytest with coverage
   - Requires PostgreSQL + Redis
   - Coverage report upload

3. **security** - Security scanning
   - Safety (dependency vulnerabilities)
   - Bandit (security linting)

4. **build** - Docker image build
   - Build and push to GHCR
   - Trivy security scan
   - Layer caching

#### `.github/workflows/deploy-staging.yml` - Staging Deployment
Triggers: Push to main, Manual

Steps:
1. Deploy to Railway staging
2. Run database migrations
3. Health check verification
4. Smoke tests
5. Automatic rollback on failure

#### `.github/workflows/deploy-production.yml` - Production Deployment
Triggers: Release, Manual (with confirmation)

Steps:
1. Validation checks
2. Create backup point
3. Deploy to Railway production
4. Run migrations
5. Comprehensive health checks
6. Extended smoke tests
7. Deployment monitoring

### 3. Railway Configuration

**Files:**
- `/railway.json` - Railway deployment config (JSON format)
- `/railway.toml` - Railway deployment config (TOML format)
- `/.railway/railway-variables.md` - Environment variables documentation

**Configuration:**
- Dockerfile-based builds
- Health check endpoint: `/health`
- Auto-restart on failure (max 10 retries)
- Environment-specific settings

**Environments:**
- **Development** - Local development
- **Staging** - Pre-production testing
- **Production** - Live deployment

### 4. Environment Configuration

**Files:**
- `/.env.example` - Complete environment template with all variables
- `/.env.test` - Test environment configuration
- `/.env.production.example` - Production environment template

**Variable Categories:**
- Application configuration
- Supabase credentials
- Database settings
- Redis configuration
- Security keys
- CORS settings
- MCP integration credentials
- AI/LLM API keys
- Monitoring (Sentry, etc.)

### 5. Development Tools

**Makefile** (`/Makefile`)
Comprehensive task automation:
- `make setup` - Complete environment setup
- `make run-reload` - Run with auto-reload
- `make test` - Run tests
- `make test-cov` - Tests with coverage
- `make lint` - Run linters
- `make format` - Auto-format code
- `make docker-up` - Start Docker services
- `make docker-down` - Stop Docker services
- `make migrate` - Run migrations
- `make deploy-staging` - Deploy to staging
- `make deploy-production` - Deploy to production

**Pre-commit Hooks** (`/.pre-commit-config.yaml`)
Automatic checks before commits:
- Code formatting (Black)
- Import sorting (isort)
- Linting (Flake8)
- Security (detect-secrets)
- File quality checks

### 6. Testing Infrastructure

**Pytest Configuration** (`/pytest.ini`, `/pyproject.toml`)
- 80% coverage requirement
- Test categorization (unit, integration, e2e)
- Parallel test execution
- Coverage reporting (HTML, XML, terminal)

**Test Structure:**
```
tests/
├── __init__.py
├── conftest.py           # Pytest fixtures
├── test_main.py          # API endpoint tests
├── unit/                 # Unit tests
├── integration/          # Integration tests
└── e2e/                  # End-to-end tests
```

### 7. Code Quality Tools

**Configuration Files:**
- `/pyproject.toml` - Tool configuration (Black, isort, MyPy)
- `/.pre-commit-config.yaml` - Pre-commit hooks

**Tools:**
- **Black** - Code formatting (88 char line length)
- **isort** - Import sorting
- **Flake8** - Linting
- **MyPy** - Type checking
- **Pylint** - Additional linting

### 8. Documentation

**Files:**
- `/README.md` - Project overview and quickstart
- `/CONTRIBUTING.md` - Development guide and workflows
- `/DEPLOYMENT.md` - Comprehensive deployment guide
- `/INFRASTRUCTURE.md` - This file
- `/sprint-plan.md` - Sprint roadmap
- `/datamodel.md` - Database schema
- `/prd.md` - Product requirements

## Directory Structure

```
founderhouse/
├── .github/
│   └── workflows/
│       ├── ci.yml                    # CI pipeline
│       ├── deploy-staging.yml        # Staging deployment
│       └── deploy-production.yml     # Production deployment
├── .railway/
│   └── railway-variables.md          # Railway env vars docs
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                   # FastAPI application
│   │   ├── config.py                 # Configuration
│   │   ├── database.py               # Database connection
│   │   ├── api/                      # API endpoints
│   │   ├── core/                     # Core functionality
│   │   ├── models/                   # Database models
│   │   └── services/                 # Business logic
│   └── scripts/
│       ├── init-db.sql               # Database initialization
│       └── migrate.py                # Migration script
├── tests/
│   ├── __init__.py
│   ├── conftest.py                   # Pytest fixtures
│   ├── test_main.py                  # Main tests
│   ├── unit/                         # Unit tests
│   ├── integration/                  # Integration tests
│   └── e2e/                          # E2E tests
├── .dockerignore                     # Docker ignore patterns
├── .env.example                      # Environment template
├── .env.test                         # Test environment
├── .env.production.example           # Production template
├── .gitignore                        # Git ignore patterns
├── .pre-commit-config.yaml           # Pre-commit hooks
├── CONTRIBUTING.md                   # Development guide
├── DEPLOYMENT.md                     # Deployment guide
├── Dockerfile                        # Production container
├── INFRASTRUCTURE.md                 # This file
├── Makefile                          # Task automation
├── README.md                         # Project overview
├── docker-compose.yml                # Local dev services
├── pyproject.toml                    # Python tool config
├── pytest.ini                        # Pytest configuration
├── quickstart.sh                     # Quick setup script
├── railway.json                      # Railway config (JSON)
├── railway.toml                      # Railway config (TOML)
├── requirements.txt                  # Production deps
└── requirements-dev.txt              # Development deps
```

## Deployment Workflow

### Development Flow
```
1. Developer writes code
   ↓
2. Pre-commit hooks run (formatting, linting)
   ↓
3. Create feature branch
   ↓
4. Push to GitHub
   ↓
5. CI pipeline runs (lint, test, security)
   ↓
6. Create Pull Request
   ↓
7. Code review
   ↓
8. Merge to main
   ↓
9. Auto-deploy to staging
   ↓
10. Manual deploy to production (after testing)
```

### CI/CD Pipeline Flow
```
Push/PR → GitHub Actions
    ↓
┌───────────────────┐
│   Lint & Format   │
│  (Black, Flake8)  │
└───────────────────┘
    ↓
┌───────────────────┐
│   Run Tests       │
│  (Pytest + Cov)   │
└───────────────────┘
    ↓
┌───────────────────┐
│ Security Scan     │
│ (Safety, Bandit)  │
└───────────────────┘
    ↓
┌───────────────────┐
│  Build Docker     │
│  (Multi-stage)    │
└───────────────────┘
    ↓
┌───────────────────┐
│  Push to GHCR     │
└───────────────────┘
    ↓
┌───────────────────┐
│ Deploy to Railway │
│    (Staging)      │
└───────────────────┘
    ↓
┌───────────────────┐
│  Health Checks    │
└───────────────────┘
```

## Environment Variables

### Required for Local Development
```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_KEY=your-service-key
SECRET_KEY=generate-with-openssl
JWT_SECRET_KEY=generate-with-openssl
DATABASE_URL=postgresql://dev:dev@localhost:5432/founderhouse_dev
REDIS_URL=redis://localhost:6379/0
```

### Required for Railway Deployment
```env
# Auto-populated by Railway
PORT=${{PORT}}
DATABASE_URL=${{Postgres.DATABASE_URL}}
REDIS_URL=${{Redis.REDIS_URL}}

# Set manually
API_ENV=production
SECRET_KEY=<secure-random-key>
JWT_SECRET_KEY=<secure-random-key>
SUPABASE_URL=<production-url>
SUPABASE_ANON_KEY=<production-key>
SUPABASE_SERVICE_KEY=<production-service-key>
ALLOWED_ORIGINS=https://your-domain.com
```

## Security Features

1. **Secret Management**
   - Environment variables (never in code)
   - Railway variables (encrypted)
   - Pre-commit hooks detect secrets

2. **Container Security**
   - Non-root user
   - Multi-stage builds
   - Minimal base images
   - Security scanning (Trivy)

3. **Application Security**
   - CORS configuration
   - Rate limiting
   - Input validation
   - JWT authentication
   - RLS (Row Level Security)

4. **Dependency Security**
   - Safety checks (known vulnerabilities)
   - Bandit (code security)
   - Automated updates (Dependabot)

## Monitoring & Observability

### Health Checks
- `/health` - Basic health endpoint
- `/version` - Version information
- Railway built-in metrics

### Logging
- Structured logging (JSON format)
- Log levels (DEBUG, INFO, WARNING, ERROR)
- Request/response logging
- Error tracking (optional Sentry)

### Metrics
- Railway dashboard metrics
- CPU/Memory usage
- Request count
- Response times
- Error rates

## Scaling Considerations

### Current Setup
- Single instance per environment
- Suitable for MVP and initial users

### Future Scaling
- Horizontal scaling (multiple instances)
- Load balancing (Railway auto-scales)
- Database read replicas
- Redis cluster
- CDN for static assets

## Backup & Recovery

### Database Backups
- Supabase automatic backups
- Point-in-time recovery
- Manual backup scripts

### Deployment Rollback
- Railway deployment history
- Automated rollback on failure
- Manual rollback capability
- Database migration rollback

## Cost Optimization

### Development
- Free tier: Docker local
- Free tier: Supabase
- Free tier: GitHub Actions (2000 min/month)

### Staging
- Railway Hobby Plan: ~$5/month
- Supabase Free tier

### Production
- Railway Pro Plan: ~$20/month
- Supabase Pro Plan: ~$25/month
- Total estimate: ~$45-50/month

## Maintenance Tasks

### Daily
- Monitor error logs
- Check deployment status

### Weekly
- Review security alerts
- Update dependencies
- Review performance metrics

### Monthly
- Rotate secrets
- Database maintenance
- Cost optimization review
- Performance optimization

## Quick Commands Reference

```bash
# Development
make help                 # View all commands
make setup                # Initial setup
make run-reload           # Run with hot reload
make test-cov             # Test with coverage
make format               # Format code
make lint                 # Run linters

# Docker
make docker-up            # Start services
make docker-down          # Stop services
make docker-logs          # View logs
make docker-clean         # Clean everything

# Database
make migrate              # Run migrations
make docker-shell-db      # Open DB shell

# Deployment
make deploy-staging       # Deploy to staging
make deploy-production    # Deploy to production
railway logs              # View Railway logs
railway status            # Check status
```

## Troubleshooting

### Common Issues and Solutions

1. **Port already in use**
   ```bash
   # Find process using port
   lsof -i :8000
   # Kill process or change port
   ```

2. **Docker services won't start**
   ```bash
   # Check Docker is running
   docker info
   # Restart Docker Desktop
   # Clean and restart
   make docker-clean && make docker-up
   ```

3. **Tests failing**
   ```bash
   # Check test database
   make docker-logs-db
   # Reset test environment
   docker-compose down -v && docker-compose up -d
   ```

4. **Deployment fails**
   ```bash
   # Check Railway logs
   railway logs
   # Verify environment variables
   railway variables
   # Rollback if needed
   railway rollback
   ```

## Next Steps

1. Complete Sprint 1 implementation
2. Set up monitoring (Sentry)
3. Configure alerting
4. Implement metrics dashboard
5. Load testing
6. Performance optimization

## Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Docker Documentation](https://docs.docker.com/)
- [Railway Documentation](https://docs.railway.app/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Supabase Documentation](https://supabase.com/docs)

---

Last Updated: 2025-10-30
Version: 1.0.0
