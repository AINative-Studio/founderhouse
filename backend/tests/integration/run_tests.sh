#!/bin/bash

# ZeroDB Integration Test Runner
# Provides convenient commands to run integration tests

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Change to backend directory
cd "$(dirname "$0")/../.."

echo -e "${BLUE}======================================${NC}"
echo -e "${BLUE}ZeroDB Integration Test Runner${NC}"
echo -e "${BLUE}======================================${NC}\n"

# Check for .env file
if [ ! -f ".env" ]; then
    echo -e "${RED}ERROR: .env file not found!${NC}"
    echo -e "${YELLOW}Please create a .env file with ZeroDB credentials:${NC}"
    echo -e "  - ZERODB_EMAIL"
    echo -e "  - ZERODB_USERNAME"
    echo -e "  - ZERODB_PASSWORD"
    echo -e "  - ZERODB_API_KEY"
    echo -e "  - ZERODB_PROJECT_ID"
    echo -e "  - SECRET_KEY\n"
    exit 1
fi

# Function to run tests
run_tests() {
    local test_pattern="$1"
    local description="$2"

    echo -e "${BLUE}Running: ${description}${NC}"
    python3 -m pytest tests/integration/test_zerodb_integration.py${test_pattern} -v -m integration
}

# Parse command line arguments
case "${1:-all}" in
    all)
        echo -e "${GREEN}Running all integration tests...${NC}\n"
        python3 -m pytest tests/integration/test_zerodb_integration.py -v -m integration
        ;;

    auth)
        run_tests "::TestZeroDBAuthentication" "Authentication Tests"
        ;;

    memory)
        run_tests "::TestMemoryOperations" "Memory Operations Tests"
        ;;

    vector)
        run_tests "::TestVectorOperations" "Vector Operations Tests"
        ;;

    table)
        run_tests "::TestTableOperations" "Table Operations Tests"
        ;;

    event)
        run_tests "::TestEventOperations" "Event Operations Tests"
        ;;

    admin)
        run_tests "::TestAdminOperations" "Admin Operations Tests"
        ;;

    error)
        run_tests "::TestErrorHandling" "Error Handling Tests"
        ;;

    edge)
        run_tests "::TestEdgeCases" "Edge Case Tests"
        ;;

    coverage)
        echo -e "${GREEN}Running tests with coverage...${NC}\n"
        python3 -m pytest tests/integration/ --cov=app/zerodb_client --cov-report=term-missing --cov-report=html -v -m integration
        echo -e "\n${GREEN}Coverage report generated in htmlcov/index.html${NC}"
        ;;

    quick)
        echo -e "${GREEN}Running quick smoke tests...${NC}\n"
        python3 -m pytest tests/integration/test_zerodb_integration.py::TestZeroDBAuthentication -v -m integration
        ;;

    help|--help|-h)
        echo "Usage: ./run_tests.sh [OPTION]"
        echo ""
        echo "Options:"
        echo "  all       Run all integration tests (default)"
        echo "  auth      Run authentication tests only"
        echo "  memory    Run memory operation tests only"
        echo "  vector    Run vector operation tests only"
        echo "  table     Run table operation tests only"
        echo "  event     Run event operation tests only"
        echo "  admin     Run admin operation tests only"
        echo "  error     Run error handling tests only"
        echo "  edge      Run edge case tests only"
        echo "  coverage  Run tests with coverage report"
        echo "  quick     Run quick smoke tests"
        echo "  help      Show this help message"
        echo ""
        echo "Examples:"
        echo "  ./run_tests.sh all"
        echo "  ./run_tests.sh memory"
        echo "  ./run_tests.sh coverage"
        ;;

    *)
        echo -e "${RED}Unknown option: $1${NC}"
        echo "Run './run_tests.sh help' for usage information"
        exit 1
        ;;
esac

echo -e "\n${BLUE}======================================${NC}"
echo -e "${GREEN}Test execution complete!${NC}"
echo -e "${BLUE}======================================${NC}"
