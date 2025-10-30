# Deployment Guide - AI Chief of Staff

This guide covers the complete deployment process for the AI Chief of Staff platform.

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Prerequisites](#prerequisites)
- [Railway Setup](#railway-setup)
- [Environment Configuration](#environment-configuration)
- [Database Setup](#database-setup)
- [CI/CD Pipeline](#cicd-pipeline)
- [Deployment Process](#deployment-process)
- [Monitoring & Observability](#monitoring--observability)
- [Rollback Procedures](#rollback-procedures)
- [Troubleshooting](#troubleshooting)

## Architecture Overview

### Production Stack

```
┌─────────────────────────────────────────────────┐
│            Frontend (Future)                     │
│        Next.js / React / Vercel                  │
└─────────────────────────────────────────────────┘
                      │
                      ↓
┌─────────────────────────────────────────────────┐
│              API Gateway / CDN                   │
│                Railway / Cloudflare              │
└─────────────────────────────────────────────────┘
                      │
                      ↓
┌─────────────────────────────────────────────────┐
│            FastAPI Backend (Railway)             │
│  • Multi-tenant architecture                     │
│  • MCP integration layer                         │
│  • Event-driven processing                       │
└─────────────────────────────────────────────────┘
                      │
        ┌─────────────┴─────────────┐
        ↓                           ↓
┌──────────────┐           ┌──────────────┐
│  Supabase    │           │   Railway    │
│  PostgreSQL  │           │    Redis     │
│  + pgvector  │           │   (Cache)    │
└──────────────┘           └──────────────┘
```

## Prerequisites

### Required Accounts

1. **Railway Account** - [railway.app](https://railway.app)
2. **Supabase Account** - [supabase.com](https://supabase.com)
3. **GitHub Account** - For CI/CD

### Required Tools

```bash
# Railway CLI
curl -fsSL https://railway.app/install.sh | sh

# Docker Desktop
# Download from: https://www.docker.com/products/docker-desktop/

# Git
git --version
```

## Railway Setup

### 1. Create Railway Project

```bash
# Login to Railway
railway login

# Create new project
railway init

# Or link existing project
railway link
```

### 2. Add PostgreSQL Service

```bash
# Add PostgreSQL plugin
railway add --plugin postgresql

# Verify
railway status
```

### 3. Add Redis Service (Optional)

```bash
# Add Redis plugin
railway add --plugin redis

# Verify
railway status
```

### 4. Create Environments

Railway supports multiple environments:

- **Development**: For local development
- **Staging**: For pre-production testing
- **Production**: For live deployment

```bash
# Create staging environment
railway environment create staging

# Create production environment
railway environment create production

# Switch between environments
railway environment staging
railway environment production
```

## Environment Configuration

### Staging Environment Variables

Set these in Railway dashboard or via CLI:

```bash
# Switch to staging
railway environment staging

# Set variables
railway variables set API_ENV=staging
railway variables set SECRET_KEY=$(openssl rand -hex 32)
railway variables set JWT_SECRET_KEY=$(openssl rand -hex 32)
railway variables set SUPABASE_URL=https://your-project.supabase.co
railway variables set SUPABASE_ANON_KEY=your-staging-anon-key
railway variables set SUPABASE_SERVICE_KEY=your-staging-service-key
railway variables set ALLOWED_ORIGINS=https://staging.your-app.com
railway variables set LOG_LEVEL=DEBUG
railway variables set RATE_LIMIT_PER_MINUTE=100
```

### Production Environment Variables

```bash
# Switch to production
railway environment production

# Set variables
railway variables set API_ENV=production
railway variables set SECRET_KEY=$(openssl rand -hex 32)
railway variables set JWT_SECRET_KEY=$(openssl rand -hex 32)
railway variables set SUPABASE_URL=https://your-production-project.supabase.co
railway variables set SUPABASE_ANON_KEY=your-production-anon-key
railway variables set SUPABASE_SERVICE_KEY=your-production-service-key
railway variables set ALLOWED_ORIGINS=https://your-app.com
railway variables set LOG_LEVEL=INFO
railway variables set RATE_LIMIT_PER_MINUTE=200
railway variables set SENTRY_DSN=your-sentry-dsn

# Auto-populated by Railway
# DATABASE_URL=${{Postgres.DATABASE_URL}}
# REDIS_URL=${{Redis.REDIS_URL}}
# PORT=${{PORT}}
```

## Database Setup

### 1. Enable pgvector Extension

Connect to your Supabase project:

```sql
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Verify
SELECT * FROM pg_extension WHERE extname = 'vector';
```

### 2. Run Initial Migrations

```bash
# Connect to Railway
railway link

# Switch to staging
railway environment staging

# Run migrations
railway run python backend/scripts/migrate.py

# Or using Makefile
make migrate
```

### 3. Seed Initial Data (Optional)

```bash
# Run seed script
railway run python backend/scripts/seed.py
```

## CI/CD Pipeline

### GitHub Secrets Configuration

Set these secrets in your GitHub repository:

**Settings → Secrets and variables → Actions → New repository secret**

Required secrets:
```
RAILWAY_TOKEN=<your-railway-token>
RAILWAY_PROJECT_ID=<your-project-id>
PRODUCTION_API_KEY=<secure-api-key>
CODECOV_TOKEN=<optional-codecov-token>
```

To get Railway token:
```bash
# Login and get token
railway login
railway whoami

# Generate new token in Railway dashboard:
# Account Settings → Tokens → Create New Token
```

### Pipeline Overview

Our CI/CD pipeline (`.github/workflows/`) consists of:

1. **CI Pipeline** (`ci.yml`) - Runs on all PRs and pushes
   - Code linting (Black, Flake8, MyPy)
   - Unit & integration tests
   - Security scanning (Safety, Bandit, Trivy)
   - Docker image build
   - Coverage reporting

2. **Staging Deployment** (`deploy-staging.yml`) - Runs on main branch
   - Automatic deployment to staging
   - Database migrations
   - Health checks
   - Smoke tests
   - Automatic rollback on failure

3. **Production Deployment** (`deploy-production.yml`) - Manual trigger
   - Requires manual confirmation
   - Comprehensive smoke tests
   - Deployment monitoring
   - Rollback capability

### Triggering Deployments

**Staging (Automatic):**
```bash
# Merge to main branch
git checkout main
git merge feature/your-feature
git push origin main

# GitHub Actions will automatically deploy to staging
```

**Production (Manual):**
```bash
# Via GitHub Actions UI:
# Actions → Deploy to Production → Run workflow → Type "deploy" → Run

# Or create a release:
git tag -a v1.0.0 -m "Release v1.0.0"
git push origin v1.0.0
```

## Deployment Process

### Manual Deployment

#### Deploy to Staging

```bash
# Using Makefile
make deploy-staging

# Or manually
railway link
railway environment staging
railway up --detach

# Monitor deployment
railway logs
```

#### Deploy to Production

```bash
# Using Makefile (requires confirmation)
make deploy-production

# Or manually
railway link
railway environment production
railway up --detach

# Monitor deployment
railway logs
```

### Verify Deployment

```bash
# Check deployment status
railway status

# Test health endpoint
curl https://your-app.railway.app/health

# Test API
curl https://your-app.railway.app/version

# View logs
railway logs --tail 100
```

## Monitoring & Observability

### Railway Metrics

Railway provides built-in metrics:
- CPU usage
- Memory usage
- Network traffic
- Request count
- Response times

Access via: Railway Dashboard → Your Project → Metrics

### Health Checks

The application exposes health check endpoints:

```bash
# Basic health check
GET /health

# Detailed version info
GET /version
```

### Logging

Structured logging with different levels:

```python
# In code
import structlog
logger = structlog.get_logger()

logger.info("event_name", key1="value1", key2="value2")
logger.error("error_occurred", error=str(e))
```

View logs:
```bash
# Stream logs
railway logs

# Filter logs
railway logs | grep ERROR

# Last 100 lines
railway logs --tail 100
```

### Error Tracking (Sentry - Optional)

1. Sign up at [sentry.io](https://sentry.io)
2. Create new project
3. Get DSN
4. Set environment variable:
```bash
railway variables set SENTRY_DSN=https://your-dsn@sentry.io/project-id
```

## Rollback Procedures

### Automatic Rollback

The staging deployment workflow automatically rolls back on failure:
- Health check failures
- Migration errors
- Smoke test failures

### Manual Rollback

#### Via Railway Dashboard

1. Go to Railway Dashboard
2. Select your project
3. Click on "Deployments"
4. Select previous successful deployment
5. Click "Redeploy"

#### Via Railway CLI

```bash
# View deployment history
railway deployments

# Rollback to specific deployment
railway rollback <deployment-id>

# Or redeploy previous version
railway redeploy
```

### Database Rollback

```bash
# Downgrade one migration
railway run alembic downgrade -1

# Or using Makefile
make migrate-downgrade
```

## Troubleshooting

### Common Issues

#### 1. Deployment Fails

**Check build logs:**
```bash
railway logs --deployment <deployment-id>
```

**Common causes:**
- Missing environment variables
- Docker build errors
- Dependency conflicts

**Solution:**
```bash
# Verify environment variables
railway variables

# Check Dockerfile syntax
docker build -t test .

# Verify requirements.txt
pip install -r requirements.txt
```

#### 2. Health Check Fails

**Symptoms:**
- Deployment succeeds but service doesn't respond
- Health check endpoint returns 503/500

**Check:**
```bash
# View application logs
railway logs

# Check if service is running
railway status

# Test locally
docker-compose up
curl http://localhost:8000/health
```

**Common causes:**
- Port mismatch (ensure using $PORT)
- Database connection issues
- Missing dependencies

#### 3. Database Connection Issues

**Error:** `Connection refused` or `Cannot connect to database`

**Solution:**
```bash
# Verify DATABASE_URL is set
railway run env | grep DATABASE_URL

# Test connection
railway run python -c "import psycopg2; print('Connected')"

# Check Supabase status
# Visit: https://status.supabase.com/
```

#### 4. High Memory Usage

**Symptoms:**
- Service restarts frequently
- Out of memory errors

**Solution:**
```bash
# Check memory usage
railway status

# Optimize worker count in railway.toml
numReplicas = 1  # Reduce replicas

# Increase Railway plan if needed
```

#### 5. Slow Response Times

**Check:**
```bash
# Monitor metrics in Railway dashboard
# Check database query performance
# Review application logs for slow operations
```

**Solution:**
- Add database indexes
- Implement caching (Redis)
- Optimize queries
- Enable CDN

### Emergency Contacts

- **Railway Support**: https://railway.app/help
- **Supabase Support**: https://supabase.com/support
- **Project Team**: See CONTRIBUTING.md

### Debug Mode

Enable debug mode for troubleshooting:

```bash
# Staging only - never in production
railway variables set LOG_LEVEL=DEBUG
railway variables set DEBUG=true

# View detailed logs
railway logs --tail 200
```

## Performance Optimization

### Scaling

Railway auto-scales based on traffic, but you can configure:

```toml
# railway.toml
[environments.production]
numReplicas = 2  # Run 2 instances
```

### Caching

Implement Redis caching for:
- API responses
- Database queries
- Session data
- Rate limiting

### Database Optimization

- Add indexes on frequently queried columns
- Use connection pooling
- Implement query caching
- Monitor slow queries

## Security Checklist

- [ ] All secrets stored in Railway variables (not code)
- [ ] HTTPS enabled (automatic with Railway)
- [ ] CORS configured with specific origins
- [ ] Rate limiting enabled
- [ ] Database encryption at rest (Supabase default)
- [ ] Regular security scans (automated in CI)
- [ ] Dependency updates (Dependabot)
- [ ] Secret rotation schedule
- [ ] Access logs enabled
- [ ] Firewall rules configured

## Maintenance Windows

Schedule maintenance for:
- Database migrations
- Major version upgrades
- Infrastructure changes

Best practices:
- Announce 48h in advance
- Use staging for testing
- Perform during low-traffic hours
- Have rollback plan ready
- Monitor closely after changes

---

For development setup, see [CONTRIBUTING.md](./CONTRIBUTING.md)

For project overview, see [README.md](./README.md)
