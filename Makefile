.PHONY: help setup install install-dev test test-watch test-cov lint format type-check migrate docker-build docker-up docker-down docker-logs docker-clean run run-reload clean deploy-staging deploy-production railway-link railway-status

# Default target
.DEFAULT_GOAL := help

# Variables
PYTHON := python3
PIP := pip3
PYTEST := pytest
BLACK := black
FLAKE8 := flake8
MYPY := mypy
ISORT := isort

# Paths
SRC_DIR := backend
TEST_DIR := tests
COVERAGE_DIR := htmlcov

# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m # No Color

##@ Help

help: ## Display this help message
	@echo "$(BLUE)AI Chief of Staff - Development Commands$(NC)"
	@echo ""
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make $(GREEN)<target>$(NC)\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2 } /^##@/ { printf "\n$(BLUE)%s$(NC)\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

##@ Setup & Installation

setup: install install-dev ## Complete development environment setup
	@echo "$(GREEN)Environment setup complete!$(NC)"
	@echo "$(YELLOW)Don't forget to copy .env.example to .env and configure it$(NC)"

install: ## Install production dependencies
	@echo "$(BLUE)Installing production dependencies...$(NC)"
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

install-dev: ## Install development dependencies
	@echo "$(BLUE)Installing development dependencies...$(NC)"
	$(PIP) install -r requirements-dev.txt
	@echo "$(GREEN)Installing pre-commit hooks...$(NC)"
	pre-commit install || echo "$(YELLOW)pre-commit not installed, skipping hooks$(NC)"

##@ Development

run: ## Run FastAPI development server (basic)
	@echo "$(BLUE)Starting FastAPI server...$(NC)"
	uvicorn $(SRC_DIR).app.main:app --host 0.0.0.0 --port 8000

run-reload: ## Run FastAPI with auto-reload
	@echo "$(BLUE)Starting FastAPI server with auto-reload...$(NC)"
	uvicorn $(SRC_DIR).app.main:app --host 0.0.0.0 --port 8000 --reload

run-workers: ## Run FastAPI with multiple workers
	@echo "$(BLUE)Starting FastAPI server with 4 workers...$(NC)"
	uvicorn $(SRC_DIR).app.main:app --host 0.0.0.0 --port 8000 --workers 4

##@ Testing

test: ## Run all tests
	@echo "$(BLUE)Running tests...$(NC)"
	$(PYTEST) $(TEST_DIR) -v

test-watch: ## Run tests in watch mode
	@echo "$(BLUE)Running tests in watch mode...$(NC)"
	$(PYTEST) $(TEST_DIR) -v -f

test-cov: ## Run tests with coverage report
	@echo "$(BLUE)Running tests with coverage...$(NC)"
	$(PYTEST) $(TEST_DIR) -v \
		--cov=$(SRC_DIR) \
		--cov-report=html \
		--cov-report=term-missing \
		--cov-report=xml \
		--cov-fail-under=80

test-unit: ## Run unit tests only
	@echo "$(BLUE)Running unit tests...$(NC)"
	$(PYTEST) $(TEST_DIR)/unit -v

test-integration: ## Run integration tests only
	@echo "$(BLUE)Running integration tests...$(NC)"
	$(PYTEST) $(TEST_DIR)/integration -v

test-fast: ## Run tests in parallel (fast)
	@echo "$(BLUE)Running tests in parallel...$(NC)"
	$(PYTEST) $(TEST_DIR) -v -n auto

coverage-report: test-cov ## Generate and open coverage report
	@echo "$(GREEN)Opening coverage report...$(NC)"
	open $(COVERAGE_DIR)/index.html || xdg-open $(COVERAGE_DIR)/index.html

##@ Code Quality

lint: ## Run all linters
	@echo "$(BLUE)Running linters...$(NC)"
	@echo "$(YELLOW)Running Flake8...$(NC)"
	$(FLAKE8) $(SRC_DIR) $(TEST_DIR) --max-line-length=88 --extend-ignore=E203,W503 || true
	@echo "$(YELLOW)Running Black check...$(NC)"
	$(BLACK) --check $(SRC_DIR) $(TEST_DIR) || true
	@echo "$(YELLOW)Running isort check...$(NC)"
	$(ISORT) --check-only $(SRC_DIR) $(TEST_DIR) || true

format: ## Auto-format code with Black and isort
	@echo "$(BLUE)Formatting code...$(NC)"
	$(BLACK) $(SRC_DIR) $(TEST_DIR)
	$(ISORT) $(SRC_DIR) $(TEST_DIR)
	@echo "$(GREEN)Code formatting complete!$(NC)"

type-check: ## Run type checking with MyPy
	@echo "$(BLUE)Running type checks...$(NC)"
	$(MYPY) $(SRC_DIR) --ignore-missing-imports

quality: format lint type-check ## Run all code quality checks
	@echo "$(GREEN)All quality checks complete!$(NC)"

##@ Database

migrate: ## Run database migrations
	@echo "$(BLUE)Running database migrations...$(NC)"
	$(PYTHON) $(SRC_DIR)/scripts/migrate.py

migrate-create: ## Create new migration (use MESSAGE="description")
	@echo "$(BLUE)Creating new migration: $(MESSAGE)$(NC)"
	alembic revision --autogenerate -m "$(MESSAGE)"

migrate-upgrade: ## Upgrade database to latest
	@echo "$(BLUE)Upgrading database...$(NC)"
	alembic upgrade head

migrate-downgrade: ## Downgrade database by one revision
	@echo "$(BLUE)Downgrading database...$(NC)"
	alembic downgrade -1

migrate-history: ## Show migration history
	@echo "$(BLUE)Migration history:$(NC)"
	alembic history

##@ Docker

docker-build: ## Build Docker images
	@echo "$(BLUE)Building Docker images...$(NC)"
	docker-compose build

docker-up: ## Start all Docker services
	@echo "$(BLUE)Starting Docker services...$(NC)"
	docker-compose up -d
	@echo "$(GREEN)Services started! Access:$(NC)"
	@echo "  API: http://localhost:8000"
	@echo "  PostgreSQL: localhost:5432"
	@echo "  Redis: localhost:6379"
	@echo "  pgAdmin: http://localhost:5050 (with --profile tools)"

docker-down: ## Stop all Docker services
	@echo "$(BLUE)Stopping Docker services...$(NC)"
	docker-compose down

docker-restart: docker-down docker-up ## Restart all Docker services

docker-logs: ## Follow Docker logs
	docker-compose logs -f

docker-logs-api: ## Follow API container logs
	docker-compose logs -f api

docker-logs-db: ## Follow database container logs
	docker-compose logs -f postgres

docker-ps: ## Show running Docker containers
	docker-compose ps

docker-shell-api: ## Open shell in API container
	docker-compose exec api /bin/bash

docker-shell-db: ## Open PostgreSQL shell
	docker-compose exec postgres psql -U dev -d founderhouse_dev

docker-clean: ## Remove all Docker containers, volumes, and images
	@echo "$(RED)Warning: This will remove all containers, volumes, and images!$(NC)"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker-compose down -v --rmi all; \
		echo "$(GREEN)Cleanup complete!$(NC)"; \
	fi

docker-clean-volumes: ## Remove Docker volumes only
	@echo "$(YELLOW)Removing Docker volumes...$(NC)"
	docker-compose down -v

docker-pgadmin: ## Start services with pgAdmin
	@echo "$(BLUE)Starting services with pgAdmin...$(NC)"
	docker-compose --profile tools up -d

##@ Railway Deployment

railway-link: ## Link to Railway project
	@echo "$(BLUE)Linking to Railway project...$(NC)"
	railway link

railway-status: ## Show Railway deployment status
	@echo "$(BLUE)Railway deployment status:$(NC)"
	railway status

railway-logs: ## Stream Railway logs
	@echo "$(BLUE)Streaming Railway logs...$(NC)"
	railway logs

railway-vars: ## List Railway environment variables
	@echo "$(BLUE)Railway environment variables:$(NC)"
	railway variables

railway-shell: ## Open Railway shell
	@echo "$(BLUE)Opening Railway shell...$(NC)"
	railway shell

deploy-staging: ## Deploy to Railway staging
	@echo "$(BLUE)Deploying to staging...$(NC)"
	railway link
	railway environment staging
	railway up --detach
	@echo "$(GREEN)Deployed to staging!$(NC)"

deploy-production: ## Deploy to Railway production (with confirmation)
	@echo "$(RED)Warning: This will deploy to PRODUCTION!$(NC)"
	@read -p "Are you sure? Type 'deploy' to confirm: " confirm; \
	if [ "$$confirm" = "deploy" ]; then \
		echo "$(BLUE)Deploying to production...$(NC)"; \
		railway link; \
		railway environment production; \
		railway up --detach; \
		echo "$(GREEN)Deployed to production!$(NC)"; \
	else \
		echo "$(YELLOW)Deployment cancelled.$(NC)"; \
	fi

##@ Utilities

clean: ## Clean temporary files and caches
	@echo "$(BLUE)Cleaning temporary files...$(NC)"
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf build/ dist/ $(COVERAGE_DIR)/ .coverage
	@echo "$(GREEN)Cleanup complete!$(NC)"

env-check: ## Check environment configuration
	@echo "$(BLUE)Checking environment configuration...$(NC)"
	@if [ ! -f .env ]; then \
		echo "$(RED).env file not found!$(NC)"; \
		echo "$(YELLOW)Copy .env.example to .env and configure it$(NC)"; \
		exit 1; \
	fi
	@echo "$(GREEN).env file exists$(NC)"
	@$(PYTHON) -c "from dotenv import load_dotenv; load_dotenv(); import os; print('SUPABASE_URL:', os.getenv('SUPABASE_URL', 'NOT SET'))"

security-check: ## Run security vulnerability checks
	@echo "$(BLUE)Running security checks...$(NC)"
	safety check || echo "$(YELLOW)Install safety: pip install safety$(NC)"
	bandit -r $(SRC_DIR) || echo "$(YELLOW)Install bandit: pip install bandit$(NC)"

deps-update: ## Update dependencies
	@echo "$(BLUE)Updating dependencies...$(NC)"
	$(PIP) list --outdated

deps-tree: ## Show dependency tree
	@echo "$(BLUE)Dependency tree:$(NC)"
	pipdeptree || echo "$(YELLOW)Install pipdeptree: pip install pipdeptree$(NC)"

version: ## Show version information
	@echo "$(BLUE)Version Information:$(NC)"
	@echo "Python: $$($(PYTHON) --version)"
	@echo "Pip: $$($(PIP) --version)"
	@echo "FastAPI: $$($(PIP) show fastapi | grep Version)"

health: ## Check API health
	@echo "$(BLUE)Checking API health...$(NC)"
	@curl -f http://localhost:8000/health || echo "$(RED)API not responding$(NC)"

##@ CI/CD

ci-test: install install-dev lint test-cov ## Run full CI pipeline locally
	@echo "$(GREEN)CI pipeline complete!$(NC)"

pre-commit: format lint test ## Run pre-commit checks
	@echo "$(GREEN)Pre-commit checks passed!$(NC)"

build-prod: ## Build production Docker image
	@echo "$(BLUE)Building production image...$(NC)"
	docker build -t founderhouse-api:latest .
	@echo "$(GREEN)Production image built!$(NC)"
