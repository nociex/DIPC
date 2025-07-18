#!/bin/bash

# Comprehensive test runner for Document Intelligence & Parsing Center
# This script runs all test suites across all components

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to run tests in a directory
run_tests() {
    local component=$1
    local test_type=$2
    local directory=$3
    
    print_status "Running $test_type tests for $component..."
    
    cd "$directory"
    
    if [ "$component" = "API" ]; then
        if [ "$test_type" = "unit" ]; then
            python run_tests.py unit --coverage
        elif [ "$test_type" = "integration" ]; then
            python run_tests.py integration
        elif [ "$test_type" = "performance" ]; then
            python run_tests.py performance
        elif [ "$test_type" = "security" ]; then
            python run_tests.py security
        elif [ "$test_type" = "load" ]; then
            python run_tests.py load
        fi
    elif [ "$component" = "Workers" ]; then
        python run_tests.py "$test_type" --coverage
    elif [ "$component" = "Frontend" ]; then
        if [ "$test_type" = "unit" ]; then
            npm test -- --coverage --watchAll=false
        elif [ "$test_type" = "integration" ]; then
            npm test -- --testPathPattern=integration --watchAll=false
        fi
    fi
    
    cd - > /dev/null
}

# Main execution
main() {
    echo "=========================================="
    echo "DIPC Comprehensive Test Suite"
    echo "=========================================="
    
    # Check if we're in the right directory
    if [ ! -f "docker-compose.yml" ]; then
        print_error "Please run this script from the project root directory"
        exit 1
    fi
    
    # Parse command line arguments
    TEST_SUITE=${1:-"all"}
    COMPONENT=${2:-"all"}
    
    print_status "Test Suite: $TEST_SUITE"
    print_status "Component: $COMPONENT"
    
    # Track test results
    TOTAL_TESTS=0
    PASSED_TESTS=0
    FAILED_TESTS=0
    
    # Function to run component tests
    run_component_tests() {
        local comp=$1
        local suite=$2
        
        case $comp in
            "api"|"API")
                if [ -d "api" ]; then
                    print_status "Testing API component..."
                    TOTAL_TESTS=$((TOTAL_TESTS + 1))
                    if run_tests "API" "$suite" "api"; then
                        PASSED_TESTS=$((PASSED_TESTS + 1))
                        print_success "API $suite tests passed"
                    else
                        FAILED_TESTS=$((FAILED_TESTS + 1))
                        print_error "API $suite tests failed"
                    fi
                else
                    print_warning "API directory not found"
                fi
                ;;
            "workers"|"Workers")
                if [ -d "workers" ]; then
                    print_status "Testing Workers component..."
                    TOTAL_TESTS=$((TOTAL_TESTS + 1))
                    if run_tests "Workers" "$suite" "workers"; then
                        PASSED_TESTS=$((PASSED_TESTS + 1))
                        print_success "Workers $suite tests passed"
                    else
                        FAILED_TESTS=$((FAILED_TESTS + 1))
                        print_error "Workers $suite tests failed"
                    fi
                else
                    print_warning "Workers directory not found"
                fi
                ;;
            "frontend"|"Frontend")
                if [ -d "frontend" ]; then
                    print_status "Testing Frontend component..."
                    TOTAL_TESTS=$((TOTAL_TESTS + 1))
                    if run_tests "Frontend" "$suite" "frontend"; then
                        PASSED_TESTS=$((PASSED_TESTS + 1))
                        print_success "Frontend $suite tests passed"
                    else
                        FAILED_TESTS=$((FAILED_TESTS + 1))
                        print_error "Frontend $suite tests failed"
                    fi
                else
                    print_warning "Frontend directory not found"
                fi
                ;;
        esac
    }
    
    # Execute tests based on parameters
    if [ "$COMPONENT" = "all" ]; then
        components=("api" "workers" "frontend")
    else
        components=("$COMPONENT")
    fi
    
    if [ "$TEST_SUITE" = "all" ]; then
        test_suites=("unit" "integration" "security")
        
        # Add performance and load tests with confirmation
        echo ""
        read -p "Run performance tests? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            test_suites+=("performance")
        fi
        
        echo ""
        read -p "Run load tests? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            test_suites+=("load")
        fi
    else
        test_suites=("$TEST_SUITE")
    fi
    
    # Run tests for each component and suite combination
    for component in "${components[@]}"; do
        for suite in "${test_suites[@]}"; do
            run_component_tests "$component" "$suite"
        done
    done
    
    # Generate summary report
    echo ""
    echo "=========================================="
    echo "TEST EXECUTION SUMMARY"
    echo "=========================================="
    echo "Total test suites run: $TOTAL_TESTS"
    echo "Passed: $PASSED_TESTS"
    echo "Failed: $FAILED_TESTS"
    
    if [ $FAILED_TESTS -eq 0 ]; then
        print_success "🎉 All tests passed!"
        echo ""
        echo "Coverage reports generated:"
        echo "  - API: api/htmlcov/index.html"
        echo "  - Workers: workers/htmlcov/index.html"
        echo "  - Frontend: frontend/coverage/lcov-report/index.html"
        exit 0
    else
        print_error "💥 $FAILED_TESTS test suite(s) failed"
        echo ""
        echo "Check the output above for detailed error information."
        exit 1
    fi
}

# Help function
show_help() {
    echo "Usage: $0 [TEST_SUITE] [COMPONENT]"
    echo ""
    echo "TEST_SUITE options:"
    echo "  unit        - Run unit tests only"
    echo "  integration - Run integration tests only"
    echo "  performance - Run performance tests only"
    echo "  security    - Run security tests only"
    echo "  load        - Run load tests only"
    echo "  all         - Run all test suites (default)"
    echo ""
    echo "COMPONENT options:"
    echo "  api         - Run API tests only"
    echo "  workers     - Run worker tests only"
    echo "  frontend    - Run frontend tests only"
    echo "  all         - Run tests for all components (default)"
    echo ""
    echo "Examples:"
    echo "  $0                    # Run all tests for all components"
    echo "  $0 unit               # Run unit tests for all components"
    echo "  $0 integration api    # Run integration tests for API only"
    echo "  $0 security           # Run security tests for all components"
}

# Check for help flag
if [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
    show_help
    exit 0
fi

# Run main function
main "$@"