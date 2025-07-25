#!/bin/bash

# Script to query test results using jq with sheet name support
# Usage: ./jq_command.sh <sheet_name_or_search_term> [command_number]
# Example: ./jq_command.sh "ServiceLogLevel" 1

# Function to convert sheet name to test pattern
convert_sheet_to_pattern() {
    local sheet="$1"
    case "$sheet" in
        "ServiceLogLevel"|"Service Log Level")
            echo "service_logs_level"
            ;;
        "oAuthValidation-igw"|"OAuth Validation IGW")
            echo "oauth_validation_igw"
            ;;
        "SBI_Correlation_Header"|"SBI Correlation Header")
            echo "sbi_correlation_header"
            ;;
        "UserAgent-Header-IGW"|"User Agent Header IGW")
            echo "user_agent_header_igw"
            ;;
        "UserAgent-Header-EGW"|"User Agent Header EGW")
            echo "user_agent_header_egw"
            ;;
        "Server-Header"|"Server Header")
            echo "server_header"
            ;;
        "Registration_Profile"|"Registration Profile")
            echo "registration_profile"
            ;;
        "Error_Response_Enhancement"|"Error Response Enhancement")
            echo "error_response_enh"
            ;;
        "Controlled_Shutdown"|"Controlled Shutdown")
            echo "controlled_shutdown"
            ;;
        "SLF_Registration_NRF"|"SLF Registration NRF")
            echo "slf_registration_nrf"
            ;;
        "Subscriber_Activity"|"Subscriber Activity")
            echo "subscriber_activity"
            ;;
        "LCIOCI_Header_IGW"|"LCIOCI Header IGW")
            echo "lcioci_header_igw"
            ;;
        "SBI_Overload_IGW"|"SBI Overload IGW")
            echo "sbi_overload_igw"
            ;;
        "Error_Codes_EGW"|"Error Codes EGW")
            echo "error_codes_egw"
            ;;
        "Error_Codes_IGW_Prov"|"Error Codes IGW Prov")
            echo "error_codes_igw_prov"
            ;;
        "Error_Codes_IGW_Sig"|"Error Codes IGW Sig")
            echo "error_codes_igw_sig"
            ;;
        "GrpId_Lookup_NRF"|"Group ID Lookup NRF")
            echo "grpid_lookup_nrf"
            ;;
        "Default_Group_ID"|"Default Group ID")
            echo "default_group_id"
            ;;
        "Auto_Create_Subs"|"Auto Create Subs")
            echo "auto_create_subs"
            ;;
        "NF_Scoring"|"NF Scoring")
            echo "nf_scoring"
            ;;
        *)
            # If no mapping found, return original (might be already a pattern)
            echo "$sheet"
            ;;
    esac
}

# Function to print summary
print_summary() {
    local term="$1"
    local json_file="$2"

    echo "\n=== SUMMARY FOR: $term ==="

    # Get counts
    local pass_count=$(cat "$json_file" | jq --arg term "$term" '[.results[] | select((.test_name | contains($term)) and (.status == "PASS"))] | length')
    local fail_count=$(cat "$json_file" | jq --arg term "$term" '[.results[] | select((.test_name | contains($term)) and (.status == "FAIL"))] | length')
    local total_count=$((pass_count + fail_count))

    echo "Total Tests: $total_count"
    echo "✅ PASS: $pass_count"
    echo "❌ FAIL: $fail_count"

    if [ $total_count -gt 0 ]; then
        local pass_percent=$(( (pass_count * 100) / total_count ))
        echo "📊 Pass Rate: $pass_percent%"
    fi

    echo "=================================="
}

if [ $# -eq 0 ]; then
    echo "Usage: $0 <sheet_name_or_search_term> [command_number]"
    echo "\nSupported Sheet Names:"
    echo "  - ServiceLogLevel"
    echo "  - oAuthValidation-igw"
    echo "  - SBI_Correlation_Header"
    echo "  - UserAgent-Header-IGW"
    echo "  - UserAgent-Header-EGW"
    echo "  - Server-Header"
    echo "  - Registration_Profile"
    echo "  - Error_Response_Enhancement"
    echo "  - Controlled_Shutdown"
    echo "  - SLF_Registration_NRF"
    echo "  - Subscriber_Activity"
    echo "  - And more..."
    echo "\nCommands:"
    echo "  1 - Basic status check with summary (default)"
    echo "  2 - Failed tests only"
    echo "  3 - Count tests by status"
    echo "  4 - Detailed view with failure reasons"
    echo "  5 - Summary only"
    exit 1
fi

INPUT_TERM="$1"
COMMAND="${2:-1}"
JSON_FILE="test_results_20250719_122220.json"

if [ ! -f "$JSON_FILE" ]; then
    echo "Error: $JSON_FILE not found"
    exit 1
fi

# Convert sheet name to search pattern
SEARCH_TERM=$(convert_sheet_to_pattern "$INPUT_TERM")

case $COMMAND in
    1)
        echo "Basic status check for: $INPUT_TERM (pattern: $SEARCH_TERM)"
        cat "$JSON_FILE" | jq --arg term "$SEARCH_TERM" '.results[] | select(.test_name | contains($term)) | {test_name: .test_name, status: .status}'
        print_summary "$SEARCH_TERM" "$JSON_FILE"
        ;;
    2)
        echo "Failed tests only for: $INPUT_TERM (pattern: $SEARCH_TERM)"
        cat "$JSON_FILE" | jq --arg term "$SEARCH_TERM" '.results[] | select(.test_name | contains($term) and .status == "FAIL") | {test_name: .test_name, status: .status}'
        print_summary "$SEARCH_TERM" "$JSON_FILE"
        ;;
    3)
        echo "Test count by status for: $INPUT_TERM (pattern: $SEARCH_TERM)"
        cat "$JSON_FILE" | jq --arg term "$SEARCH_TERM" '[.results[] | select(.test_name | contains($term))] | group_by(.status) | map({status: .[0].status, count: length})'
        ;;
    4)
        echo "Detailed view with failure reasons for: $INPUT_TERM (pattern: $SEARCH_TERM)"
        cat "$JSON_FILE" | jq --arg term "$SEARCH_TERM" '.results[] | select(.test_name | contains($term)) | {test_name: .test_name, status: .status, failure_reason: .failure_reason}'
        print_summary "$SEARCH_TERM" "$JSON_FILE"
        ;;
    5)
        print_summary "$SEARCH_TERM" "$JSON_FILE"
        ;;
    *)
        echo "Invalid command number: $COMMAND"
        echo "Valid options: 1, 2, 3, 4, 5"
        exit 1
        ;;
esac
