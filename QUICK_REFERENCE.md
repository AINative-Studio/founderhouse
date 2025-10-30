# Quick Reference - AI Chief of Staff DevOps

## Instant Start

```bash
# Clone and setup
git clone https://github.com/AINative-Studio/founderhouse.git
cd founderhouse
cp .env.example .env

# Option 1: Docker (Recommended)
make docker-up
open http://localhost:8000/docs

# Option 2: Local
make setup
make run-reload
```

## Essential Commands

### Development
```bash
make help              # View all commands
make setup             # Complete setup
make run-reload        # Run with auto-reload
make test              # Run tests
make test-cov          # Tests with coverage
make format            # Format code
make lint              # Run linters
```

### Docker
```bash
make docker-up         # Start services
make docker-down       # Stop services
make docker-logs       # View logs
make docker-shell-db   # Database shell
```

### Deployment
```bash
make deploy-staging         # Deploy to staging
make deploy-production      # Deploy to production (requires confirmation)
railway logs                # View Railway logs
railway status              # Check deployment status
```

## Environment Variables

```env
# Required - Get from Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_KEY=your-service-key

# Required - Generate
SECRET_KEY=$(openssl rand -hex 32)
JWT_SECRET_KEY=$(openssl rand -hex 32)

# Local Development
DATABASE_URL=postgresql://dev:dev@localhost:5432/founderhouse_dev
REDIS_URL=redis://localhost:6379/0
```

## Service URLs

| Service | Local URL | Description |
|---------|-----------|-------------|
| API | http://localhost:8000 | FastAPI backend |
| API Docs | http://localhost:8000/docs | Swagger UI |
| ReDoc | http://localhost:8000/redoc | Alternative docs |
| PostgreSQL | localhost:5432 | Database |
| Redis | localhost:6379 | Cache |
| pgAdmin | http://localhost:5050 | DB admin (optional) |

## GitHub Actions

### CI Pipeline
- **Triggers**: Push, Pull Request
- **Checks**: Lint → Test → Security → Build

### Staging Deployment
- **Trigger**: Push to main
- **Flow**: Deploy → Migrate → Health Check → Smoke Test

### Production Deployment
- **Trigger**: Release or Manual
- **Confirmation**: Required
- **Flow**: Validate → Deploy → Migrate → Extended Tests

## GitHub Secrets Needed

```
RAILWAY_TOKEN=<get-from-railway-dashboard>
RAILWAY_PROJECT_ID=<your-railway-project-id>
PRODUCTION_API_KEY=<generate-secure-key>
```

## Common Tasks

### First Time Setup
```bash
# 1. Copy environment
cp .env.example .env

# 2. Edit .env with your credentials
vim .env

# 3. Start services
make docker-up

# 4. Verify
curl http://localhost:8000/health
```

### Running Tests
```bash
# All tests with coverage
make test-cov

# Watch mode
make test-watch

# Specific test
pytest tests/test_main.py -v
```

### Code Quality
```bash
# Format code
make format

# Run linters
make lint

# Type check
make type-check

# All checks
make quality
```

### Database
```bash
# Run migrations
make migrate

# Create migration
make migrate-create MESSAGE="add user table"

# Database shell
make docker-shell-db
```

### Deployment

#### Deploy to Staging
```bash
# Automatic via GitHub
git push origin main

# Or manual via Railway
make deploy-staging
```

#### Deploy to Production
```bash
# Via GitHub Actions
# Actions → Deploy to Production → Type "deploy" → Run

# Or via Make (requires confirmation)
make deploy-production
```

## Troubleshooting

### Port Already in Use
```bash
lsof -i :8000
kill -9 <PID>
```

### Docker Issues
```bash
# Restart Docker Desktop
# Then:
make docker-clean
make docker-up
```

### Tests Failing
```bash
# Check test database
make docker-logs-db

# Reset
docker-compose down -v
docker-compose up -d
```

### Deployment Fails
```bash
# Check logs
railway logs

# Verify variables
railway variables

# Rollback
railway rollback
```

## File Locations

```
Key Configuration Files:
├── Dockerfile                    # Production container
├── docker-compose.yml            # Local development
├── Makefile                      # All commands
├── .env.example                  # Environment template
├── railway.toml                  # Railway config
├── pytest.ini                    # Test configuration
├── pyproject.toml                # Tool configuration
└── .github/workflows/            # CI/CD pipelines
    ├── ci.yml                    # Continuous integration
    ├── deploy-staging.yml        # Staging deployment
    └── deploy-production.yml     # Production deployment

Documentation:
├── README.md                     # Project overview
├── CONTRIBUTING.md               # Development guide
├── DEPLOYMENT.md                 # Deployment guide
├── INFRASTRUCTURE.md             # Infrastructure details
└── DEVOPS_SETUP_SUMMARY.md       # Complete summary
```

## Health Checks

```bash
# Local
curl http://localhost:8000/health

# Staging
curl https://your-staging-app.railway.app/health

# Production
curl https://your-app.railway.app/health
```

## Logs

```bash
# Local Docker
make docker-logs
make docker-logs-api
make docker-logs-db

# Railway
railway logs
railway logs --tail 100
```

## Railway CLI

```bash
# Install
curl -fsSL https://railway.app/install.sh | sh

# Login
railway login

# Link project
railway link

# Set variables
railway variables set KEY=value

# Deploy
railway up

# Shell
railway shell
```

## Coverage Requirements

- **Minimum**: 80%
- **Check**: `make test-cov`
- **Report**: Open `htmlcov/index.html`

## Pre-commit Hooks

```bash
# Install
pre-commit install

# Run manually
pre-commit run --all-files

# Skip (emergency only)
git commit --no-verify
```

## Docker Quick Reference

```bash
# Start
docker-compose up -d

# Stop
docker-compose down

# Rebuild
docker-compose build

# Logs
docker-compose logs -f

# Shell
docker-compose exec api bash
docker-compose exec postgres psql -U dev

# Clean
docker-compose down -v
docker system prune -a
```

## Testing Markers

```bash
pytest -m unit              # Unit tests only
pytest -m integration       # Integration tests only
pytest -m "not slow"        # Skip slow tests
pytest -k test_health       # Specific test
```

## Environment Switching

```bash
# Development (local)
export API_ENV=development

# Testing
export API_ENV=testing

# Staging
railway environment staging

# Production
railway environment production
```

## Security

```bash
# Generate secure keys
openssl rand -hex 32

# Check for secrets
detect-secrets scan

# Security audit
make security-check
```

## Performance

```bash
# Multiple workers
make run-workers

# Parallel tests
make test-fast

# Cache clear
docker-compose restart redis
```

## Monitoring

```bash
# API health
make health

# Railway metrics
railway status

# View variables
railway variables
```

## Useful Links

- **Docs**: http://localhost:8000/docs
- **Railway**: https://railway.app
- **Supabase**: https://app.supabase.com
- **GitHub**: https://github.com/AINative-Studio/founderhouse

## Support

- **Issues**: GitHub Issues
- **Docs**: See CONTRIBUTING.md
- **Help**: `make help`

---

**Quick Reference Version**: 1.0.0
**Last Updated**: 2025-10-30
