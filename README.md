# AI Chief of Staff

> An AI-powered Chief of Staff platform for founders, providing meeting intelligence, unified communications, insights, and autonomous task orchestration.

[![CI/CD Pipeline](https://github.com/AINative-Studio/founderhouse/actions/workflows/ci.yml/badge.svg)](https://github.com/AINative-Studio/founderhouse/actions)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109.0-009688.svg)](https://fastapi.tiangolo.com)

## Overview

AI Chief of Staff is a multi-tenant platform that acts as an intelligent assistant for startup founders, integrating with your entire workflow to provide:

- **Meeting Intelligence**: Automatic transcription, summarization, and action item extraction
- **Unified Inbox**: Aggregate communications from Slack, Discord, Email, and more
- **Insights Engine**: KPI tracking, trend detection, and automated briefings
- **Task Orchestration**: Multi-agent workflows with autonomous execution
- **Voice Interface**: Natural language commands via ZeroVoice MCP

## Architecture

Built with modern, scalable technologies:

- **Backend**: FastAPI (Python 3.11+)
- **Database**: Supabase (PostgreSQL 16 + pgvector)
- **Cache**: Redis
- **Deployment**: Railway
- **CI/CD**: GitHub Actions
- **Integrations**: MCP (Model Context Protocol) for Zoom, Slack, Discord, Outlook, Monday.com, and more

## Quick Start

### Prerequisites

- Python 3.11 or higher
- Docker Desktop
- Git

### Option 1: Docker (Recommended)

```bash
# Clone repository
git clone https://github.com/AINative-Studio/founderhouse.git
cd founderhouse

# Copy environment template
cp .env.example .env
# Edit .env with your configuration

# Start all services
make docker-up

# Access the API
open http://localhost:8000/docs
```

### Option 2: Local Development

```bash
# Clone repository
git clone https://github.com/AINative-Studio/founderhouse.git
cd founderhouse

# Setup environment
make setup

# Copy environment template
cp .env.example .env
# Edit .env with your configuration

# Run the application
make run-reload
```

### Verify Installation

```bash
# Check health
curl http://localhost:8000/health

# View API documentation
open http://localhost:8000/docs
```

## Documentation

- **[Sprint Plan](./sprint-plan.md)** - 6-sprint development roadmap
- **[Contributing Guide](./CONTRIBUTING.md)** - Development setup and guidelines
- **[Deployment Guide](./DEPLOYMENT.md)** - Production deployment instructions
- **[Data Model](./datamodel.md)** - Database schema and design
- **[Product Requirements](./prd.md)** - Detailed product specifications

## Features by Sprint

### Sprint 1: Infrastructure & Data Core (Current)
- Multi-tenant database with workspace isolation
- pgvector for semantic search
- Event sourcing foundation
- Health monitoring endpoints

### Sprint 2: MCP Integration Framework
- OAuth flows for Zoom, Slack, Discord, Outlook
- Integration health monitoring
- Secure credential management

### Sprint 3: Meeting & Communication Intelligence
- Zoom + Fireflies transcription pipeline
- Unified inbox aggregation
- Sentiment analysis
- Automatic task creation

### Sprint 4: Insights & Briefings
- KPI tracking (Granola integration)
- Morning/Evening briefing generation
- Investor report automation

### Sprint 5: Orchestration & Voice
- Multi-agent task routing
- Voice command interface
- Loom video summarization
- Discord briefing bot

### Sprint 6: Production Launch
- Security hardening
- CI/CD pipeline
- Performance optimization
- Monitoring & observability

## Development

### Common Commands

```bash
# View all available commands
make help

# Development
make run-reload          # Run with auto-reload
make test                # Run tests
make test-cov            # Run tests with coverage
make format              # Format code
make lint                # Run linters

# Docker
make docker-up           # Start services
make docker-down         # Stop services
make docker-logs         # View logs

# Database
make migrate             # Run migrations
make docker-shell-db     # Open database shell

# Deployment
make deploy-staging      # Deploy to staging
make deploy-production   # Deploy to production
```

### Testing

```bash
# Run all tests
make test

# Run with coverage
make test-cov

# Run specific test file
pytest tests/test_main.py -v

# Run integration tests only
make test-integration
```

### Code Quality

We maintain high code quality standards:

- **Black** for code formatting
- **isort** for import sorting
- **Flake8** for linting
- **MyPy** for type checking
- **Pytest** with 80%+ coverage requirement

```bash
# Run all quality checks
make quality
```

## Environment Configuration

Key environment variables (see `.env.example` for complete list):

```env
# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_KEY=your-service-key

# Database
DATABASE_URL=postgresql://dev:dev@localhost:5432/founderhouse_dev

# Security
SECRET_KEY=your-secret-key
JWT_SECRET_KEY=your-jwt-secret

# API
ALLOWED_ORIGINS=http://localhost:3000
```

## Deployment

### Railway (Production)

```bash
# Install Railway CLI
curl -fsSL https://railway.app/install.sh | sh

# Login and link project
railway login
railway link

# Set environment variables
railway variables set SUPABASE_URL=https://your-project.supabase.co

# Deploy
make deploy-production
```

See [DEPLOYMENT.md](./DEPLOYMENT.md) for comprehensive deployment guide.

## API Documentation

Once running, access interactive API documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI Schema**: http://localhost:8000/openapi.json

## Project Structure

```
founderhouse/
├── backend/
│   ├── app/
│   │   ├── api/           # API endpoints
│   │   ├── core/          # Core functionality
│   │   ├── models/        # Database models
│   │   ├── services/      # Business logic
│   │   └── main.py        # Application entry point
│   └── scripts/           # Utility scripts
├── tests/
│   ├── unit/              # Unit tests
│   ├── integration/       # Integration tests
│   └── e2e/               # End-to-end tests
├── .github/
│   └── workflows/         # CI/CD pipelines
├── docker-compose.yml     # Local development services
├── Dockerfile             # Production container
├── Makefile               # Development commands
└── requirements.txt       # Python dependencies
```

## Contributing

We welcome contributions! Please see our [Contributing Guide](./CONTRIBUTING.md) for details.

### Development Workflow

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests and linting (`make pre-commit`)
5. Commit your changes (`git commit -m 'feat: add amazing feature'`)
6. Push to your fork (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## Technology Stack

- **Backend Framework**: FastAPI
- **Language**: Python 3.11+
- **Database**: PostgreSQL 16 (Supabase)
- **Vector Store**: pgvector
- **Cache**: Redis
- **Container**: Docker
- **Deployment**: Railway
- **CI/CD**: GitHub Actions
- **Testing**: Pytest
- **Code Quality**: Black, Flake8, MyPy

## Integrations

Built with MCP (Model Context Protocol) for seamless integrations:

- **Meeting**: Zoom, Fireflies, Otter
- **Communication**: Slack, Discord, Outlook, Gmail
- **Project Management**: Monday.com, Notion
- **Analytics**: Granola
- **Video**: Loom
- **Voice**: ZeroVoice

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- **Documentation**: See `/docs` directory
- **Issues**: [GitHub Issues](https://github.com/AINative-Studio/founderhouse/issues)
- **Discussions**: [GitHub Discussions](https://github.com/AINative-Studio/founderhouse/discussions)

## Roadmap

See [sprint-plan.md](./sprint-plan.md) for the complete 6-sprint roadmap.

**Current Sprint**: Sprint 1 - Infrastructure & Data Core

**Next Up**: Sprint 2 - MCP Integration Framework

## Acknowledgments

Built with:
- [FastAPI](https://fastapi.tiangolo.com/)
- [Supabase](https://supabase.com/)
- [Railway](https://railway.app/)
- [MCP Protocol](https://modelcontextprotocol.io/)

---

Made with passion by the AINative Studio team
