#!/bin/bash

# JSON Test Results Filter Script
# Usage: ./json_filter.sh <json_file>

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to display header
show_header() {
    echo -e "${BLUE}======================================${NC}"
    echo -e "${BLUE}    JSON Test Results Filter Tool    ${NC}"
    echo -e "${BLUE}======================================${NC}"
    echo
}

# Function to validate JSON file
validate_file() {
    if [ ! -f "$1" ]; then
        echo -e "${RED}Error: File '$1' not found!${NC}"
        exit 1
    fi

    if ! jq empty "$1" 2>/dev/null; then
        echo -e "${RED}Error: '$1' is not a valid JSON file!${NC}"
        exit 1
    fi

    if ! jq -e '.results' "$1" >/dev/null 2>&1; then
        echo -e "${RED}Error: JSON file must contain 'results' array!${NC}"
        exit 1
    fi
}

# Function to display menu
show_menu() {
    echo -e "${YELLOW}Select a filter option:${NC}"
    echo
    echo "Basic Filtering:"
    echo "  1) Show all passed tests"
    echo "  2) Show all failed tests"
    echo "  3) Filter by host"
    echo "  4) Filter by HTTP method"
    echo "  5) Filter by sheet"
    echo
    echo "Field Extraction:"
    echo "  6) Show test names and status"
    echo "  7) Show test names of failed tests"
    echo "  8) Show duration and test name"
    echo
    echo "Duration Filtering:"
    echo "  9) Tests longer than specified duration"
    echo " 10) Tests faster than specified duration"
    echo
    echo "Combined Filters:"
    echo " 11) Failed tests by HTTP method"
    echo " 12) Tests with errors"
    echo
    echo "Statistics:"
    echo " 13) Count total tests"
    echo " 14) Count passed tests"
    echo " 15) Count failed tests"
    echo " 16) Calculate average duration"
    echo " 17) Show summary statistics"
    echo
    echo "Advanced:"
    echo " 18) Custom jq filter"
    echo " 19) Export filtered results to file"
    echo
    echo "  0) Exit"
    echo
    echo -n "Enter your choice [0-19]: "
}

# Function to get user input
get_input() {
    local prompt="$1"
    local var_name="$2"
    echo -n "$prompt"
    read -r "$var_name"
}

# Filter functions
filter_passed_tests() {
    echo -e "${GREEN}Passed Tests:${NC}"
    cat "$JSON_FILE" | jq '.results[] | select(.passed == true)'
}

filter_failed_tests() {
    echo -e "${RED}Failed Tests:${NC}"
    cat "$JSON_FILE" | jq '.results[] | select(.passed == false)'
}

filter_by_host() {
    get_input "Enter host name: " host
    echo -e "${GREEN}Tests for host '$host':${NC}"
    cat "$JSON_FILE" | jq --arg host "$host" '.results[] | select(.host == $host)'
}

filter_by_method() {
    get_input "Enter HTTP method (GET, POST, PUT, DELETE, etc.): " method
    echo -e "${GREEN}Tests with method '$method':${NC}"
    cat "$JSON_FILE" | jq --arg method "$method" '.results[] | select(.method == $method)'
}

filter_by_sheet() {
    get_input "Enter sheet name: " sheet
    echo -e "${GREEN}Tests for sheet '$sheet':${NC}"
    cat "$JSON_FILE" | jq --arg sheet "$sheet" '.results[] | select(.sheet == $sheet)'
}

show_test_names_status() {
    echo -e "${GREEN}Test Names and Status:${NC}"
    cat "$JSON_FILE" | jq '.results[] | {test_name, status}'
}

show_failed_test_names() {
    echo -e "${RED}Failed Test Names:${NC}"
    cat "$JSON_FILE" | jq -r '.results[] | select(.passed == false) | .test_name'
}

show_duration_test_name() {
    echo -e "${GREEN}Duration and Test Name:${NC}"
    cat "$JSON_FILE" | jq '.results[] | {test_name, duration}'
}

filter_by_duration_greater() {
    get_input "Enter minimum duration (seconds): " duration
    echo -e "${GREEN}Tests longer than ${duration}s:${NC}"
    cat "$JSON_FILE" | jq --argjson duration "$duration" '.results[] | select(.duration > $duration)'
}

filter_by_duration_less() {
    get_input "Enter maximum duration (seconds): " duration
    echo -e "${GREEN}Tests faster than ${duration}s:${NC}"
    cat "$JSON_FILE" | jq --argjson duration "$duration" '.results[] | select(.duration < $duration)'
}

filter_failed_by_method() {
    get_input "Enter HTTP method: " method
    echo -e "${RED}Failed tests with method '$method':${NC}"
    cat "$JSON_FILE" | jq --arg method "$method" '.results[] | select(.passed == false and .method == $method)'
}

filter_tests_with_errors() {
    echo -e "${YELLOW}Tests with errors:${NC}"
    cat "$JSON_FILE" | jq '.results[] | select(.error != "")'
}

count_total_tests() {
    local count=$(cat "$JSON_FILE" | jq '.results | length')
    echo -e "${BLUE}Total tests: $count${NC}"
}

count_passed_tests() {
    local count=$(cat "$JSON_FILE" | jq '[.results[] | select(.passed == true)] | length')
    echo -e "${GREEN}Passed tests: $count${NC}"
}

count_failed_tests() {
    local count=$(cat "$JSON_FILE" | jq '[.results[] | select(.passed == false)] | length')
    echo -e "${RED}Failed tests: $count${NC}"
}

calculate_average_duration() {
    local avg=$(cat "$JSON_FILE" | jq '[.results[].duration] | add / length')
    echo -e "${BLUE}Average duration: ${avg}s${NC}"
}

show_summary_stats() {
    echo -e "${BLUE}Summary Statistics:${NC}"
    echo "==================="
    local total=$(cat "$JSON_FILE" | jq '.results | length')
    local passed=$(cat "$JSON_FILE" | jq '[.results[] | select(.passed == true)] | length')
    local failed=$(cat "$JSON_FILE" | jq '[.results[] | select(.passed == false)] | length')
    local avg_duration=$(cat "$JSON_FILE" | jq '[.results[].duration] | add / length')
    local max_duration=$(cat "$JSON_FILE" | jq '[.results[].duration] | max')
    local min_duration=$(cat "$JSON_FILE" | jq '[.results[].duration] | min')

    printf "Total tests:      %d\n" "$total"
    printf "Passed tests:     %d (%.1f%%)\n" "$passed" "$(echo "$passed * 100 / $total" | bc -l)"
    printf "Failed tests:     %d (%.1f%%)\n" "$failed" "$(echo "$failed * 100 / $total" | bc -l)"
    printf "Average duration: %.3fs\n" "$avg_duration"
    printf "Max duration:     %.3fs\n" "$max_duration"
    printf "Min duration:     %.3fs\n" "$min_duration"
}

custom_jq_filter() {
    get_input "Enter custom jq filter (e.g., '.results[] | select(.duration > 1)'): " filter
    echo -e "${GREEN}Custom filter results:${NC}"
    cat "$JSON_FILE" | jq "$filter"
}

export_filtered_results() {
    get_input "Enter output filename: " output_file
    get_input "Enter jq filter: " filter

    cat "$JSON_FILE" | jq "$filter" > "$output_file"
    echo -e "${GREEN}Results exported to '$output_file'${NC}"
}

# Main execution function
main() {
    # Check if file argument is provided
    if [ $# -eq 0 ]; then
        echo -e "${RED}Usage: $0 <json_file>${NC}"
        echo "Example: $0 test_results.json"
        exit 1
    fi

    JSON_FILE="$1"

    # Validate the JSON file
    validate_file "$JSON_FILE"

    show_header
    echo -e "${GREEN}Processing file: $JSON_FILE${NC}"
    echo

    # Main menu loop
    while true; do
        show_menu
        read -r choice
        echo

        case $choice in
            1) filter_passed_tests ;;
            2) filter_failed_tests ;;
            3) filter_by_host ;;
            4) filter_by_method ;;
            5) filter_by_sheet ;;
            6) show_test_names_status ;;
            7) show_failed_test_names ;;
            8) show_duration_test_name ;;
            9) filter_by_duration_greater ;;
            10) filter_by_duration_less ;;
            11) filter_failed_by_method ;;
            12) filter_tests_with_errors ;;
            13) count_total_tests ;;
            14) count_passed_tests ;;
            15) count_failed_tests ;;
            16) calculate_average_duration ;;
            17) show_summary_stats ;;
            18) custom_jq_filter ;;
            19) export_filtered_results ;;
            0)
                echo -e "${BLUE}Goodbye!${NC}"
                exit 0
                ;;
            *)
                echo -e "${RED}Invalid option. Please try again.${NC}"
                ;;
        esac

        echo
        echo -e "${YELLOW}Press Enter to continue...${NC}"
        read -r
        clear
        show_header
        echo -e "${GREEN}Processing file: $JSON_FILE${NC}"
        echo
    done
}

# Check if jq is installed
if ! command -v jq &> /dev/null; then
    echo -e "${RED}Error: jq is not installed. Please install jq first.${NC}"
    echo "On Ubuntu/Debian: sudo apt-get install jq"
    echo "On macOS: brew install jq"
    exit 1
fi

# Check if bc is installed (for percentage calculations)
if ! command -v bc &> /dev/null; then
    echo -e "${YELLOW}Warning: bc is not installed. Some calculations may not work properly.${NC}"
    echo "On Ubuntu/Debian: sudo apt-get install bc"
    echo "On macOS: brew install bc"
fi

# Run main function with all arguments
main "$@"
