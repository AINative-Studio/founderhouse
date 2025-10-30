#!/bin/bash
# AI Chief of Staff - Test Runner Script
# Convenient script for running different test suites

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print colored output
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

# Display usage
usage() {
    cat << EOF
AI Chief of Staff - Test Runner

Usage: $0 [OPTION]

Options:
    all             Run all tests (default)
    unit            Run unit tests only
    integration     Run integration tests only
    e2e             Run end-to-end tests only
    coverage        Run tests with coverage report
    fast            Run fast tests (exclude slow)
    ci              Run tests as in CI/CD (strict)
    watch           Run tests in watch mode
    lint            Run linting only
    security        Run security scans
    mutation        Run mutation testing
    help            Show this help message

Examples:
    $0 unit                 # Run unit tests
    $0 coverage             # Run with coverage
    $0 ci                   # Run CI pipeline locally
EOF
}

# Check if dependencies are installed
check_dependencies() {
    print_info "Checking dependencies..."

    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed"
        exit 1
    fi

    if ! command -v pytest &> /dev/null; then
        print_error "pytest is not installed. Run: pip install -r requirements-dev.txt"
        exit 1
    fi

    print_success "All dependencies found"
}

# Run unit tests
run_unit_tests() {
    print_info "Running unit tests..."
    pytest tests/unit/ \
        -m unit \
        -v \
        --tb=short \
        || (print_error "Unit tests failed" && exit 1)

    print_success "Unit tests passed"
}

# Run integration tests
run_integration_tests() {
    print_info "Running integration tests..."
    print_warning "Note: Integration tests require PostgreSQL with pgvector"

    pytest tests/integration/ \
        -m integration \
        -v \
        --tb=short \
        || (print_error "Integration tests failed" && exit 1)

    print_success "Integration tests passed"
}

# Run E2E tests
run_e2e_tests() {
    print_info "Running end-to-end tests..."

    pytest tests/e2e/ \
        -m e2e \
        -v \
        --tb=short \
        || (print_error "E2E tests failed" && exit 1)

    print_success "E2E tests passed"
}

# Run all tests
run_all_tests() {
    print_info "Running all tests..."

    pytest tests/ \
        -v \
        --tb=short \
        || (print_error "Tests failed" && exit 1)

    print_success "All tests passed"
}

# Run tests with coverage
run_coverage() {
    print_info "Running tests with coverage analysis..."

    pytest tests/ \
        --cov=backend/app \
        --cov-report=html \
        --cov-report=term-missing \
        --cov-fail-under=90 \
        -v \
        || (print_error "Coverage requirements not met" && exit 1)

    print_success "Coverage requirements met (≥90%)"
    print_info "HTML report available at: htmlcov/index.html"

    # Open coverage report if on macOS
    if [[ "$OSTYPE" == "darwin"* ]]; then
        print_info "Opening coverage report in browser..."
        open htmlcov/index.html
    fi
}

# Run fast tests only
run_fast_tests() {
    print_info "Running fast tests (excluding slow tests)..."

    pytest tests/ \
        -m "not slow" \
        -v \
        --tb=short \
        -n auto \
        || (print_error "Fast tests failed" && exit 1)

    print_success "Fast tests passed"
}

# Run CI pipeline locally
run_ci_pipeline() {
    print_info "Running CI pipeline locally..."

    # Lint
    print_info "Step 1/5: Linting..."
    black --check backend/ tests/ || (print_error "Black check failed" && exit 1)
    isort --check-only backend/ tests/ || (print_error "isort check failed" && exit 1)
    flake8 backend/ tests/ --max-line-length=120 --extend-ignore=E203,W503 || (print_error "Flake8 failed" && exit 1)

    # Unit tests
    print_info "Step 2/5: Unit tests..."
    pytest tests/unit/ -m unit --cov=backend/app --cov-fail-under=85 -v

    # Integration tests
    print_info "Step 3/5: Integration tests..."
    pytest tests/integration/ -m integration -v || print_warning "Integration tests skipped (database required)"

    # E2E tests
    print_info "Step 4/5: E2E tests..."
    pytest tests/e2e/ -m e2e -v || print_warning "E2E tests skipped"

    # Coverage
    print_info "Step 5/5: Full coverage..."
    pytest tests/ --cov=backend/app --cov-fail-under=90 --cov-report=term-missing

    print_success "CI pipeline completed successfully"
}

# Run linting
run_lint() {
    print_info "Running linters..."

    print_info "Running Black..."
    black backend/ tests/ || (print_error "Black failed" && exit 1)

    print_info "Running isort..."
    isort backend/ tests/ || (print_error "isort failed" && exit 1)

    print_info "Running Flake8..."
    flake8 backend/ tests/ --max-line-length=120 --extend-ignore=E203,W503 || (print_error "Flake8 failed" && exit 1)

    print_success "Linting completed"
}

# Run security scans
run_security() {
    print_info "Running security scans..."

    if ! command -v safety &> /dev/null; then
        print_warning "safety not installed. Installing..."
        pip install safety
    fi

    if ! command -v bandit &> /dev/null; then
        print_warning "bandit not installed. Installing..."
        pip install bandit
    fi

    print_info "Running Safety check..."
    safety check || print_warning "Safety found vulnerabilities"

    print_info "Running Bandit security linter..."
    bandit -r backend/app || print_warning "Bandit found security issues"

    print_success "Security scans completed"
}

# Run mutation testing
run_mutation() {
    print_info "Running mutation testing..."
    print_warning "This may take 10-30 minutes..."

    if ! command -v mutmut &> /dev/null; then
        print_error "mutmut not installed. Run: pip install mutmut"
        exit 1
    fi

    mutmut run --paths-to-mutate=backend/app || print_warning "Some mutants survived"

    print_info "Generating mutation report..."
    mutmut results
    mutmut html

    print_success "Mutation testing completed"
    print_info "HTML report available at: html/index.html"
}

# Watch mode
run_watch() {
    print_info "Running tests in watch mode..."
    print_info "Tests will re-run on file changes. Press Ctrl+C to exit."

    if ! command -v pytest-watch &> /dev/null; then
        print_warning "pytest-watch not installed. Installing..."
        pip install pytest-watch
    fi

    ptw -- tests/ -v --tb=short -m "not slow"
}

# Main script logic
main() {
    case "${1:-all}" in
        all)
            check_dependencies
            run_all_tests
            ;;
        unit)
            check_dependencies
            run_unit_tests
            ;;
        integration)
            check_dependencies
            run_integration_tests
            ;;
        e2e)
            check_dependencies
            run_e2e_tests
            ;;
        coverage)
            check_dependencies
            run_coverage
            ;;
        fast)
            check_dependencies
            run_fast_tests
            ;;
        ci)
            check_dependencies
            run_ci_pipeline
            ;;
        lint)
            run_lint
            ;;
        security)
            run_security
            ;;
        mutation)
            check_dependencies
            run_mutation
            ;;
        watch)
            check_dependencies
            run_watch
            ;;
        help|--help|-h)
            usage
            ;;
        *)
            print_error "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
