#!/bin/bash

# Quickstart script for AI Chief of Staff
# This script helps you get started with local development

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

# Check prerequisites
check_prerequisites() {
    print_header "Checking Prerequisites"

    # Check Python
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
        print_success "Python $PYTHON_VERSION installed"
    else
        print_error "Python 3.11+ is required but not installed"
        exit 1
    fi

    # Check Docker
    if command -v docker &> /dev/null; then
        DOCKER_VERSION=$(docker --version | cut -d' ' -f3 | sed 's/,//')
        print_success "Docker $DOCKER_VERSION installed"
    else
        print_warning "Docker not found - required for containerized development"
    fi

    # Check Docker Compose
    if command -v docker-compose &> /dev/null || docker compose version &> /dev/null; then
        print_success "Docker Compose installed"
    else
        print_warning "Docker Compose not found - required for containerized development"
    fi

    # Check Make
    if command -v make &> /dev/null; then
        print_success "Make installed"
    else
        print_warning "Make not found - you'll need to run commands manually"
    fi
}

# Setup environment
setup_environment() {
    print_header "Setting Up Environment"

    # Create .env if it doesn't exist
    if [ ! -f .env ]; then
        print_info "Creating .env file from template..."
        cp .env.example .env
        print_success ".env file created"
        print_warning "Please edit .env and configure your settings"
    else
        print_info ".env file already exists"
    fi
}

# Install dependencies
install_dependencies() {
    print_header "Installing Dependencies"

    print_info "Creating virtual environment..."
    python3 -m venv venv

    print_info "Activating virtual environment..."
    source venv/bin/activate

    print_info "Installing Python packages..."
    pip install --upgrade pip
    pip install -r requirements.txt
    pip install -r requirements-dev.txt

    print_success "Dependencies installed"
}

# Start Docker services
start_docker() {
    print_header "Starting Docker Services"

    if command -v docker &> /dev/null; then
        print_info "Building Docker images..."
        docker-compose build

        print_info "Starting services..."
        docker-compose up -d

        print_success "Docker services started"

        # Wait for services to be ready
        print_info "Waiting for services to be ready..."
        sleep 5

        # Check PostgreSQL
        if docker-compose exec -T postgres pg_isready -U dev > /dev/null 2>&1; then
            print_success "PostgreSQL is ready"
        else
            print_warning "PostgreSQL may not be ready yet"
        fi

        # Check Redis
        if docker-compose exec -T redis redis-cli ping > /dev/null 2>&1; then
            print_success "Redis is ready"
        else
            print_warning "Redis may not be ready yet"
        fi
    else
        print_warning "Docker not available - skipping container setup"
    fi
}

# Display next steps
show_next_steps() {
    print_header "Setup Complete!"

    echo ""
    print_info "Your AI Chief of Staff development environment is ready!"
    echo ""

    echo -e "${GREEN}Services Running:${NC}"
    echo "  • API: http://localhost:8000"
    echo "  • API Docs: http://localhost:8000/docs"
    echo "  • PostgreSQL: localhost:5432"
    echo "  • Redis: localhost:6379"
    echo ""

    echo -e "${YELLOW}Next Steps:${NC}"
    echo "  1. Edit .env and configure your API keys"
    echo "  2. Activate virtual environment: source venv/bin/activate"
    echo "  3. Run the API: make run-reload"
    echo "  4. Or use Docker: make docker-up"
    echo ""

    echo -e "${BLUE}Useful Commands:${NC}"
    echo "  • make help           - View all available commands"
    echo "  • make test           - Run tests"
    echo "  • make docker-logs    - View Docker logs"
    echo "  • make docker-down    - Stop Docker services"
    echo ""

    echo -e "${BLUE}Documentation:${NC}"
    echo "  • README.md           - Project overview"
    echo "  • CONTRIBUTING.md     - Development guide"
    echo "  • DEPLOYMENT.md       - Deployment guide"
    echo ""
}

# Main execution
main() {
    clear

    print_header "AI Chief of Staff - Quickstart Setup"
    echo ""

    check_prerequisites
    echo ""

    setup_environment
    echo ""

    # Ask user preference
    echo -e "${YELLOW}Choose setup method:${NC}"
    echo "  1) Docker (Recommended)"
    echo "  2) Local Python"
    echo "  3) Both"
    echo ""
    read -p "Enter choice [1-3]: " choice

    case $choice in
        1)
            start_docker
            ;;
        2)
            install_dependencies
            ;;
        3)
            install_dependencies
            echo ""
            start_docker
            ;;
        *)
            print_error "Invalid choice"
            exit 1
            ;;
    esac

    echo ""
    show_next_steps
}

# Run main
main
