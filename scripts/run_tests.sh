#!/bin/bash
# Test runner script for MCP Personal Assistant
# Provides comprehensive test execution with different test types

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
TEST_TYPE="all"
COVERAGE=true
VERBOSE=false
PARALLEL=true
GENERATE_REPORT=true
BENCHMARK=false

# Print usage information
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Test runner for MCP Personal Assistant"
    echo ""
    echo "OPTIONS:"
    echo "  -t, --type TYPE       Test type: unit|integration|performance|all (default: all)"
    echo "  -c, --no-coverage     Disable coverage reporting"
    echo "  -v, --verbose         Enable verbose output"
    echo "  -s, --serial          Run tests serially (disable parallelization)"
    echo "  -b, --benchmark       Run benchmark tests"
    echo "  -r, --no-report       Skip HTML report generation"
    echo "  -f, --fast            Fast mode (unit tests only, no coverage)"
    echo "  -h, --help            Show this help message"
    echo ""
    echo "EXAMPLES:"
    echo "  $0                    # Run all tests with coverage"
    echo "  $0 -t unit           # Run only unit tests"
    echo "  $0 -f                # Fast unit test run"
    echo "  $0 -b                # Run benchmarks"
    echo "  $0 -t performance -v # Verbose performance tests"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -t|--type)
            TEST_TYPE="$2"
            shift 2
            ;;
        -c|--no-coverage)
            COVERAGE=false
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -s|--serial)
            PARALLEL=false
            shift
            ;;
        -b|--benchmark)
            BENCHMARK=true
            shift
            ;;
        -r|--no-report)
            GENERATE_REPORT=false
            shift
            ;;
        -f|--fast)
            TEST_TYPE="unit"
            COVERAGE=false
            GENERATE_REPORT=false
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

# Validate test type
case $TEST_TYPE in
    unit|integration|performance|all)
        ;;
    *)
        echo -e "${RED}Error: Invalid test type '$TEST_TYPE'${NC}"
        usage
        exit 1
        ;;
esac

# Print configuration
echo -e "${BLUE}MCP Personal Assistant Test Runner${NC}"
echo -e "${BLUE}==================================${NC}"
echo "Test Type: $TEST_TYPE"
echo "Coverage: $COVERAGE"
echo "Verbose: $VERBOSE"
echo "Parallel: $PARALLEL"
echo "Benchmark: $BENCHMARK"
echo "Generate Report: $GENERATE_REPORT"
echo ""

# Check if we're in the right directory
if [[ ! -f "pytest.ini" ]]; then
    echo -e "${RED}Error: pytest.ini not found. Run this script from the project root.${NC}"
    exit 1
fi

# Create directories for test artifacts
mkdir -p junit htmlcov logs

# Set environment variables for testing
export ENVIRONMENT=testing
export AUTH_ENABLED=false
export LOG_LEVEL=WARNING
export PYTHONPATH="${PYTHONPATH}:${PWD}/src"

# Build pytest command
build_pytest_cmd() {
    local test_path=$1
    local extra_args=$2
    
    cmd="pytest"
    
    # Add test path
    cmd="$cmd $test_path"
    
    # Coverage options
    if [[ $COVERAGE == true ]]; then
        cmd="$cmd --cov=src --cov-report=term-missing --cov-report=xml --cov-report=html"
    fi
    
    # Verbose output
    if [[ $VERBOSE == true ]]; then
        cmd="$cmd -v -s"
    else
        cmd="$cmd --tb=short"
    fi
    
    # Parallel execution
    if [[ $PARALLEL == true ]]; then
        cmd="$cmd -n auto"
    fi
    
    # JUnit XML output
    cmd="$cmd --junitxml=junit/test-results-$(basename $test_path).xml"
    
    # Extra arguments
    if [[ -n $extra_args ]]; then
        cmd="$cmd $extra_args"
    fi
    
    echo $cmd
}

# Run unit tests
run_unit_tests() {
    echo -e "${YELLOW}Running Unit Tests...${NC}"
    
    cmd=$(build_pytest_cmd "tests/unit/" "--timeout=30")
    
    if [[ $COVERAGE == true ]]; then
        cmd="$cmd --cov-report=html:htmlcov/unit"
    fi
    
    echo "Command: $cmd"
    
    if eval $cmd; then
        echo -e "${GREEN}✓ Unit tests passed${NC}"
        return 0
    else
        echo -e "${RED}✗ Unit tests failed${NC}"
        return 1
    fi
}

# Run integration tests
run_integration_tests() {
    echo -e "${YELLOW}Running Integration Tests...${NC}"
    
    # Check for required services (optional)
    if command -v docker &> /dev/null; then
        echo "Docker available for integration tests"
    else
        echo "Warning: Docker not available, some integration tests may fail"
    fi
    
    cmd=$(build_pytest_cmd "tests/integration/" "--timeout=60")
    
    if [[ $COVERAGE == true ]]; then
        cmd="$cmd --cov-report=html:htmlcov/integration"
    fi
    
    echo "Command: $cmd"
    
    if eval $cmd; then
        echo -e "${GREEN}✓ Integration tests passed${NC}"
        return 0
    else
        echo -e "${RED}✗ Integration tests failed${NC}"
        return 1
    fi
}

# Run performance tests
run_performance_tests() {
    echo -e "${YELLOW}Running Performance Tests...${NC}"
    
    cmd=$(build_pytest_cmd "tests/performance/" "--timeout=120 -m performance")
    
    # Don't need coverage for performance tests
    cmd=$(echo $cmd | sed 's/--cov[^ ]*//g')
    
    echo "Command: $cmd"
    
    if eval $cmd; then
        echo -e "${GREEN}✓ Performance tests passed${NC}"
        return 0
    else
        echo -e "${RED}✗ Performance tests failed${NC}"
        return 1
    fi
}

# Run benchmark tests
run_benchmark_tests() {
    echo -e "${YELLOW}Running Benchmark Tests...${NC}"
    
    cmd="pytest tests/performance/ -m benchmark --benchmark-json=benchmark-results.json --benchmark-only --timeout=180"
    
    if [[ $VERBOSE == true ]]; then
        cmd="$cmd -v -s"
    fi
    
    echo "Command: $cmd"
    
    if eval $cmd; then
        echo -e "${GREEN}✓ Benchmark tests completed${NC}"
        
        # Check for performance regressions
        if [[ -f "scripts/check_performance_regression.py" ]]; then
            echo -e "${YELLOW}Checking for performance regressions...${NC}"
            if python scripts/check_performance_regression.py benchmark-results.json; then
                echo -e "${GREEN}✓ No performance regressions detected${NC}"
            else
                echo -e "${RED}⚠ Performance regressions detected${NC}"
                return 1
            fi
        fi
        
        return 0
    else
        echo -e "${RED}✗ Benchmark tests failed${NC}"
        return 1
    fi
}

# Generate test report
generate_report() {
    echo -e "${YELLOW}Generating Test Report...${NC}"
    
    # Combine coverage reports if multiple exist
    if [[ $COVERAGE == true ]]; then
        if [[ -f htmlcov/unit/index.html && -f htmlcov/integration/index.html ]]; then
            echo "Combining coverage reports..."
            # This is a simplified combination - in practice, you'd use coverage combine
            cp -r htmlcov/unit htmlcov/combined
        elif [[ -f htmlcov/unit/index.html ]]; then
            cp -r htmlcov/unit htmlcov/combined
        elif [[ -f htmlcov/integration/index.html ]]; then
            cp -r htmlcov/integration htmlcov/combined
        fi
        
        if [[ -d htmlcov/combined ]]; then
            echo -e "${GREEN}Coverage report available at: htmlcov/combined/index.html${NC}"
        fi
    fi
    
    # Generate test summary
    echo -e "${YELLOW}Test Summary:${NC}"
    if ls junit/test-results-*.xml 1> /dev/null 2>&1; then
        for result_file in junit/test-results-*.xml; do
            test_name=$(basename $result_file .xml | sed 's/test-results-//')
            if command -v xmllint &> /dev/null; then
                tests=$(xmllint --xpath "//testsuite/@tests" $result_file 2>/dev/null | sed 's/tests="\([^"]*\)"/\1/' || echo "?")
                failures=$(xmllint --xpath "//testsuite/@failures" $result_file 2>/dev/null | sed 's/failures="\([^"]*\)"/\1/' || echo "?")
                errors=$(xmllint --xpath "//testsuite/@errors" $result_file 2>/dev/null | sed 's/errors="\([^"]*\)"/\1/' || echo "?")
                echo "  $test_name: $tests tests, $failures failures, $errors errors"
            else
                echo "  $test_name: Results available in $result_file"
            fi
        done
    fi
}

# Main execution
main() {
    local exit_code=0
    local start_time=$(date +%s)
    
    case $TEST_TYPE in
        unit)
            run_unit_tests || exit_code=$?
            ;;
        integration)
            run_integration_tests || exit_code=$?
            ;;
        performance)
            run_performance_tests || exit_code=$?
            ;;
        all)
            echo -e "${BLUE}Running comprehensive test suite...${NC}"
            
            run_unit_tests || exit_code=$?
            
            if [[ $exit_code -eq 0 ]]; then
                run_integration_tests || exit_code=$?
            fi
            
            if [[ $exit_code -eq 0 ]]; then
                run_performance_tests || exit_code=$?
            fi
            ;;
    esac
    
    # Run benchmarks if requested
    if [[ $BENCHMARK == true ]]; then
        run_benchmark_tests || exit_code=$?
    fi
    
    # Generate report
    if [[ $GENERATE_REPORT == true ]]; then
        generate_report
    fi
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    echo ""
    echo -e "${BLUE}Test Execution Summary${NC}"
    echo -e "${BLUE}=====================${NC}"
    echo "Duration: ${duration}s"
    echo "Test Type: $TEST_TYPE"
    
    if [[ $exit_code -eq 0 ]]; then
        echo -e "Status: ${GREEN}PASSED${NC}"
    else
        echo -e "Status: ${RED}FAILED${NC}"
    fi
    
    echo ""
    echo "Artifacts generated:"
    echo "  - JUnit XML: junit/"
    if [[ $COVERAGE == true ]]; then
        echo "  - Coverage: htmlcov/"
    fi
    if [[ $BENCHMARK == true && -f benchmark-results.json ]]; then
        echo "  - Benchmarks: benchmark-results.json"
    fi
    
    return $exit_code
}

# Execute main function
main
exit $?