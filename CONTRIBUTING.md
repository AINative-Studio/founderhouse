# Contributing to AI Chief of Staff

Thank you for your interest in contributing to the AI Chief of Staff project! This guide will help you get started with local development, testing, and deployment.

## Table of Contents

- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Running the Application](#running-the-application)
- [Testing](#testing)
- [Code Quality](#code-quality)
- [Database Migrations](#database-migrations)
- [Docker Development](#docker-development)
- [Deployment](#deployment)
- [Contributing Guidelines](#contributing-guidelines)

## Getting Started

### Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.11+** - [Download](https://www.python.org/downloads/)
- **Docker Desktop** - [Download](https://www.docker.com/products/docker-desktop/)
- **Git** - [Download](https://git-scm.com/downloads)
- **PostgreSQL 16** (optional, for local development without Docker)
- **Redis** (optional, for local development without Docker)

### Repository Setup

1. Clone the repository:
```bash
git clone https://github.com/AINative-Studio/founderhouse.git
cd founderhouse
```

2. Create and configure your environment file:
```bash
cp .env.example .env
```

3. Edit `.env` and fill in your configuration values (see [Environment Configuration](#environment-configuration))

## Development Setup

### Option 1: Using Make (Recommended)

We provide a comprehensive Makefile for all common tasks:

```bash
# Complete setup (installs all dependencies)
make setup

# View all available commands
make help
```

### Option 2: Manual Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install
```

## Environment Configuration

### Required Environment Variables

1. **Supabase Configuration**
   - Sign up at [supabase.com](https://supabase.com)
   - Create a new project
   - Get your credentials from Project Settings > API

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_KEY=your-service-role-key
```

2. **Security Keys**

Generate secure keys:
```bash
# Generate SECRET_KEY
openssl rand -hex 32

# Generate JWT_SECRET_KEY
openssl rand -hex 32
```

3. **Database Configuration** (for local development)
```env
DATABASE_URL=postgresql://dev:dev@localhost:5432/founderhouse_dev
REDIS_URL=redis://localhost:6379/0
```

## Running the Application

### Using Docker (Recommended for Development)

```bash
# Start all services (API, PostgreSQL, Redis)
make docker-up

# View logs
make docker-logs

# Access services:
# - API: http://localhost:8000
# - API Docs: http://localhost:8000/docs
# - PostgreSQL: localhost:5432
# - Redis: localhost:6379

# Stop services
make docker-down
```

### Running Locally (Without Docker)

```bash
# Start the development server with auto-reload
make run-reload

# Or manually:
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:
- API: http://localhost:8000
- Interactive API docs: http://localhost:8000/docs
- ReDoc documentation: http://localhost:8000/redoc

## Testing

### Running Tests

```bash
# Run all tests
make test

# Run tests with coverage
make test-cov

# Run tests in watch mode (re-runs on file changes)
make test-watch

# Run only unit tests
make test-unit

# Run only integration tests
make test-integration

# Run tests in parallel (faster)
make test-fast
```

### Test Coverage

We aim for 80%+ test coverage. Coverage reports are generated in `htmlcov/`.

```bash
# Generate and view coverage report
make coverage-report
```

### Writing Tests

- Place unit tests in `tests/unit/`
- Place integration tests in `tests/integration/`
- Use pytest fixtures for common setup
- Mock external services (Supabase, APIs, etc.)

Example test:
```python
# tests/unit/test_example.py
import pytest
from backend.app.services.example import ExampleService

def test_example_service():
    service = ExampleService()
    result = service.process_data("test")
    assert result == "processed: test"
```

## Code Quality

### Linting and Formatting

We use multiple tools to maintain code quality:

```bash
# Auto-format code (Black + isort)
make format

# Run all linters
make lint

# Run type checking
make type-check

# Run all quality checks
make quality
```

### Pre-commit Hooks

Pre-commit hooks automatically run on every commit:

```bash
# Install hooks
pre-commit install

# Run manually on all files
pre-commit run --all-files
```

### Code Style Guidelines

- **Black** for code formatting (88 character line length)
- **isort** for import sorting
- **Flake8** for linting
- **MyPy** for type checking
- Follow PEP 8 conventions
- Add type hints to all functions
- Write docstrings for public APIs

## Database Migrations

We use Alembic for database migrations.

### Creating Migrations

```bash
# Create a new migration
make migrate-create MESSAGE="add user table"

# Or manually:
alembic revision --autogenerate -m "add user table"
```

### Running Migrations

```bash
# Upgrade to latest
make migrate-upgrade

# Or manually:
alembic upgrade head
```

### Migration Best Practices

1. Always review auto-generated migrations
2. Test migrations on a copy of production data
3. Include both upgrade and downgrade logic
4. Keep migrations small and focused
5. Never edit applied migrations

## Docker Development

### Building Images

```bash
# Build all services
make docker-build

# Build production image
make build-prod
```

### Database Management

```bash
# Open PostgreSQL shell
make docker-shell-db

# View database logs
make docker-logs-db

# Start with pgAdmin (database management UI)
make docker-pgadmin
# Access at: http://localhost:5050
# Email: admin@founderhouse.dev
# Password: admin
```

### Docker Cleanup

```bash
# Remove containers and volumes
make docker-clean-volumes

# Complete cleanup (containers, volumes, images)
make docker-clean
```

## Deployment

### Railway Deployment

#### Initial Setup

1. Install Railway CLI:
```bash
curl -fsSL https://railway.app/install.sh | sh
```

2. Login and link project:
```bash
railway login
make railway-link
```

3. Set environment variables:
```bash
railway variables set SUPABASE_URL=https://your-project.supabase.co
railway variables set SECRET_KEY=$(openssl rand -hex 32)
# ... set other variables
```

#### Deploying to Staging

```bash
# Deploy to staging
make deploy-staging

# Check deployment status
make railway-status

# View logs
make railway-logs
```

#### Deploying to Production

```bash
# Deploy to production (requires confirmation)
make deploy-production
```

### GitHub Actions CI/CD

Our CI/CD pipeline automatically:

1. **On Pull Requests & Pushes:**
   - Runs linting (Black, Flake8, MyPy)
   - Runs all tests with coverage
   - Runs security scans
   - Builds Docker image
   - Uploads coverage reports

2. **On Main Branch Push:**
   - Deploys to Railway staging
   - Runs database migrations
   - Performs health checks

3. **On Release:**
   - Deploys to production
   - Comprehensive smoke tests
   - Deployment monitoring

### Required GitHub Secrets

Set these in your GitHub repository settings (Settings > Secrets):

```
RAILWAY_TOKEN=your-railway-token
RAILWAY_PROJECT_ID=your-project-id
PRODUCTION_API_KEY=your-production-api-key
CODECOV_TOKEN=your-codecov-token (optional)
```

## Contributing Guidelines

### Workflow

1. **Create a feature branch:**
```bash
git checkout -b feature/your-feature-name
```

2. **Make your changes:**
   - Write code following our style guidelines
   - Add tests for new functionality
   - Update documentation as needed

3. **Run quality checks:**
```bash
make pre-commit
```

4. **Commit your changes:**
```bash
git add .
git commit -m "feat: add new feature"
```

5. **Push and create a Pull Request:**
```bash
git push origin feature/your-feature-name
```

### Commit Message Convention

We follow [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `style:` - Code style changes (formatting, etc.)
- `refactor:` - Code refactoring
- `test:` - Adding or updating tests
- `chore:` - Maintenance tasks

Examples:
```
feat: add meeting summarization endpoint
fix: resolve database connection timeout
docs: update API documentation
test: add integration tests for auth
```

### Pull Request Guidelines

1. **Title:** Use conventional commit format
2. **Description:**
   - Describe what changes you made and why
   - Link related issues
   - Include screenshots for UI changes
3. **Tests:** Ensure all tests pass
4. **Documentation:** Update docs if needed
5. **Review:** Request review from maintainers

### Code Review Process

1. All PRs require at least one approval
2. All CI checks must pass
3. Code coverage must not decrease
4. Security scans must pass
5. Maintainers will review within 48 hours

## Troubleshooting

### Common Issues

**Docker services won't start:**
```bash
# Check if ports are already in use
lsof -i :8000  # API port
lsof -i :5432  # PostgreSQL port
lsof -i :6379  # Redis port

# Stop conflicting services or change ports in docker-compose.override.yml
```

**Database connection errors:**
```bash
# Verify database is running
make docker-ps

# Check database logs
make docker-logs-db

# Restart database
docker-compose restart postgres
```

**Import errors:**
```bash
# Ensure you're in the virtual environment
source venv/bin/activate

# Reinstall dependencies
make install
```

**Tests failing:**
```bash
# Run tests with verbose output
pytest -vv

# Check test database
make docker-shell-db
\l  # List databases
```

## Getting Help

- **Documentation:** Check the [API documentation](http://localhost:8000/docs)
- **Issues:** [GitHub Issues](https://github.com/AINative-Studio/founderhouse/issues)
- **Discussions:** [GitHub Discussions](https://github.com/AINative-Studio/founderhouse/discussions)
- **Sprint Plan:** See [sprint-plan.md](./sprint-plan.md) for project roadmap

## License

By contributing, you agree that your contributions will be licensed under the project's license.

---

Thank you for contributing to AI Chief of Staff! 🚀
