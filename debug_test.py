#!/usr/bin/env python3
import argparse
import json
import logging
import sys

# Add the source directory to Python path
sys.path.insert(0, "/Users/sarathp/Documents/incubator/testPilotOne/src")

from testpilot.core.enhanced_response_validator import (
    validate_response_enhanced,
)

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def debug_test(test_name, row_index):
    # Load test data
    with open(
        "Users/sarathp/Documents/incubator/testPilotOne/test_results/test_results_slf_registration.json",
        "r",
    ) as f:
        data = json.load(f)

    # Find the specific test
    test_result = None
    for result in data["results"]:
        if result.get("test_name") == test_name:
            test_result = result
            # if row index is not matching
            json_row_index = result.get("row_index")
            if json_row_index != row_index:
                continue
            else:
                print(f"Found right test {test_name} {json_row_index}")
                break

    if not test_result:
        print(f"Test '{test_name}' not found!")
        print("Available tests:")
        test_names = [result.get("test_name") for result in data["results"]]
        for i, name in enumerate(sorted(test_names)[:10]):
            print(f"  {name}")
        if len(test_names) > 10:
            print(f"  ... and {len(test_names) - 10} more tests")
        return

    print(f"=== DEBUGGING {test_name} ===")
    print(f"Original result: {'PASS' if test_result['passed'] else 'FAIL'}")
    print(f"Sheet: {test_result.get('sheet')}")
    print()

    # Extract validation data safely
    pattern_match_data = test_result.get("pattern_match", {})
    response_body_data = test_result.get("response_body", {})

    pattern_match = pattern_match_data.get("raw_pattern_match", "")
    response_body = response_body_data.get("parsed_json")
    raw_output = response_body_data.get("raw_output", "")

    print(f"Pattern: {repr(pattern_match)}")
    print(f"Has pattern: {bool(pattern_match.strip())}")
    print(f"Raw output length: {len(raw_output)}")
    print(f"Response body type: {type(response_body).__name__}")
    print()

    # Show basic test info
    print("=== TEST DETAILS ===")
    print(
        f"Command: {test_result.get('command', 'N/A')[:100]}..."
        if len(test_result.get("command", "")) > 100
        else f"Command: {test_result.get('command', 'N/A')}"
    )
    print(f"Duration: {test_result.get('duration', 'N/A')}")
    print(
        f"HTTP Status: {'200 OK' if 'HTTP/2 200' in test_result.get('error', '') else 'Check error field'}"
    )
    print()

    # Manual pattern analysis
    if pattern_match.strip():
        print("=== PATTERN ANALYSIS ===")
        if pattern_match in raw_output:
            idx = raw_output.find(pattern_match)
            print(f"✅ Pattern found at position {idx}")
            context = raw_output[
                max(0, idx - 50) : idx + len(pattern_match) + 50
            ]
            print(f"Context: {repr(context)}")
        else:
            print("❌ Pattern NOT found")
            # Check for common components
            words = (
                pattern_match.replace('"', "")
                .replace(":", " ")
                .replace(",", " ")
                .split()
            )
            print("Checking pattern components:")
            for word in words:
                if len(word) > 3:  # Skip short words
                    print(f"  '{word}' in raw_output: {word in raw_output}")
    else:
        print("=== NO PATTERN TO MATCH ===")
        print(
            "Test has empty pattern - will be evaluated on response structure only"
        )

    print()

    # Run enhanced validation
    print("=== ENHANCED VALIDATION ===")
    validation_result = validate_response_enhanced(
        pattern_match=pattern_match if pattern_match.strip() else None,
        response_headers=test_result.get("response_headers"),
        response_body=response_body,
        response_payload=response_body,
        logger=logger,
        raw_output=raw_output,
    )

    print(
        f"Enhanced validation result: {validation_result['pattern_match_overall']}"
    )
    print(f"Dict match: {validation_result['dict_match']}")
    print(f"Summary: {validation_result['summary']}")

    if validation_result.get("pattern_matches"):
        print("\nPattern match attempts:")
        for match in validation_result["pattern_matches"]:
            print(f"  {match['type']}: {match['result']} - {match['details']}")

    # Analysis
    print(f"\n=== ANALYSIS ===")
    original_passed = test_result["passed"]
    enhanced_passed = validation_result.get(
        "pattern_match_overall"
    ) or validation_result.get("dict_match")

    if enhanced_passed is None:
        enhanced_passed = None  # No validation criteria

    if original_passed == False and enhanced_passed == True:
        print(
            "🔍 DISCREPANCY: Original test FAILED but enhanced validation PASSES!"
        )
        print(
            "   → This suggests the original test execution had an issue (false negative)."
        )
    elif original_passed == True and enhanced_passed == False:
        print(
            "🔍 DISCREPANCY: Original test PASSED but enhanced validation FAILS!"
        )
        print(
            "   → This suggests the enhanced validator found an issue the original missed."
        )
    elif enhanced_passed is None:
        print(
            "⚪ NO VALIDATION CRITERIA: Test has no pattern or expected response structure."
        )
        print("   → Cannot determine if test should pass or fail.")
    else:
        result_str = "PASS" if original_passed else "FAIL"
        print(
            f"✅ CONSISTENT: Both original and enhanced validation agree ({result_str})."
        )

    # Show raw output sample if it's interesting
    if raw_output and len(raw_output) < 500:
        print(f"\n=== RESPONSE SAMPLE ===")
        print(f"Raw output: {repr(raw_output)}")


def debug_all_tests():
    """Debug all tests in the file"""
    # Load test data
    with open(
        "/Users/sarathp/Documents/incubator/testPilotOne/test_results/test_results_slf_registration.json",
        "r",
    ) as f:
        data = json.load(f)

    print("=== DEBUGGING ALL TESTS ===")
    print(f"Total tests: {len(data['results'])}")
    print(
        f"Summary: {data['summary']['passed']} passed, {data['summary']['failed']} failed"
    )
    print()

    for i, result in enumerate(data["results"], 1):
        test_name = result.get("test_name")
        row_index = result.get("row_index")
        original_passed = result["passed"]

        print(f"--- Test {i}: {test_name} (row {row_index}) ---")
        print(f"Original result: {'PASS' if original_passed else 'FAIL'}")

        # Extract validation data
        pattern_match_data = result.get("pattern_match", {})
        response_body_data = result.get("response_body", {})

        pattern_match = pattern_match_data.get("raw_pattern_match", "")
        response_body = response_body_data.get("parsed_json")
        raw_output = response_body_data.get("raw_output", "")

        # Run enhanced validation
        validation_result = validate_response_enhanced(
            pattern_match=pattern_match if pattern_match.strip() else None,
            response_headers=result.get("response_headers"),
            response_body=response_body,
            response_payload=response_body,
            logger=logger,
            raw_output=raw_output,
        )

        enhanced_passed = validation_result.get(
            "pattern_match_overall"
        ) or validation_result.get("dict_match")
        dict_match = validation_result.get("dict_match")
        pattern_match_overall = validation_result.get("pattern_match_overall")

        print(f"Enhanced validation:")
        print(f"  - Dict match: {dict_match}")
        print(f"  - Pattern match: {pattern_match_overall}")
        print(
            f"  - Overall result: {'PASS' if enhanced_passed else 'FAIL' if enhanced_passed is False else 'NO_CRITERIA'}"
        )

        # Analysis
        if original_passed == False and enhanced_passed == True:
            print(
                "  🔍 DISCREPANCY: Original FAILED but enhanced validation PASSES (false negative)"
            )
        elif original_passed == True and enhanced_passed == False:
            print(
                "  🔍 DISCREPANCY: Original PASSED but enhanced validation FAILS (false positive)"
            )
        elif enhanced_passed is None:
            print(
                "  ⚪ NO VALIDATION CRITERIA: Cannot determine if test should pass or fail"
            )
        else:
            result_str = "PASS" if original_passed else "FAIL"
            print(f"  ✅ CONSISTENT: Both agree ({result_str})")

        print(f"  Response size: {len(raw_output)} bytes")
        print(f"  Has pattern: {bool(pattern_match.strip())}")
        print()


def main():
    parser = argparse.ArgumentParser(
        description="Debug test results from NFInstanceDiscovery-NRF file"
    )
    parser.add_argument(
        "test_name",
        nargs="?",
        help="Name of the test to debug (e.g., test_nf_discovery_nrf_1). If omitted, debug all tests.",
    )
    parser.add_argument(
        "row_index",
        nargs="?",
        help="Row index (required when test_name is provided)",
    )
    parser.add_argument(
        "--quiet", "-q", action="store_true", help="Reduce logging verbosity"
    )

    args = parser.parse_args()

    if args.quiet:
        logging.getLogger().setLevel(logging.WARNING)

    if not args.test_name:
        # No arguments provided - debug all tests
        debug_all_tests()
    else:
        # Specific test provided
        if not args.row_index:
            print("Error: row_index is required when test_name is provided")
            parser.print_help()
            return
        debug_test(args.test_name, args.row_index)


if __name__ == "__main__":
    main()
