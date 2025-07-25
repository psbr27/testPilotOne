#!/usr/bin/env python3
"""
Test script for array order-independent JSON validation
Tests the scenario where arrays contain same elements but in different order
"""

import json
import logging
import os
import sys

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
from src.testpilot.core.enhanced_response_validator import (
    validate_response_enhanced,
)

# Setup logging
logging.basicConfig(level=logging.INFO)  # Set to INFO to reduce noise
logger = logging.getLogger(__name__)


def test_array_order_scenarios():
    """Test various scenarios with arrays that have same content but different order"""

    print("🧪 Testing Array Order-Independent JSON Validation")
    print("=" * 70)

    # Base expected response (original order)
    expected_response = {
        "profile-data": {
            "accountID": ["12345678912345678912345678"],
            "imsi": ["302720603949999"],
            "msisdn": ["19195229999"],
        },
        "slfGroupName": "IMSGrp1",
    }

    # Test scenarios with different array orders and lengths
    test_scenarios = [
        {
            "name": "Exact Match - Same Order",
            "description": "Arrays have same elements in same order",
            "actual_response": {
                "profile-data": {
                    "accountID": ["12345678912345678912345678"],
                    "imsi": ["302720603949999"],
                    "msisdn": ["19195229999"],
                },
                "slfGroupName": "IMSGrp1",
            },
            "expected_result": "PASS",
        },
        {
            "name": "Single Item Arrays - Different Order",
            "description": "Single item arrays in different field order",
            "actual_response": {
                "slfGroupName": "IMSGrp1",
                "profile-data": {
                    "msisdn": ["19195229999"],
                    "accountID": ["12345678912345678912345678"],
                    "imsi": ["302720603949999"],
                },
            },
            "expected_result": "PASS",
        },
        {
            "name": "Multiple Items - Same Order",
            "description": "Multiple items in arrays, same order",
            "actual_response": {
                "profile-data": {
                    "accountID": [
                        "12345678912345678912345678",
                        "98765432198765432198765432",
                    ],
                    "imsi": ["302720603949999", "302720603948888"],
                    "msisdn": ["19195229999", "19195228888"],
                },
                "slfGroupName": "IMSGrp1",
            },
            "expected_result": "PASS",
        },
        {
            "name": "Multiple Items - Different Order",
            "description": "Multiple items in arrays, different order - THIS IS THE MAIN ISSUE",
            "actual_response": {
                "profile-data": {
                    "accountID": [
                        "98765432198765432198765432",
                        "12345678912345678912345678",
                    ],  # Reversed
                    "imsi": ["302720603948888", "302720603949999"],  # Reversed
                    "msisdn": ["19195228888", "19195229999"],  # Reversed
                },
                "slfGroupName": "IMSGrp1",
            },
            "expected_result": "SHOULD_PASS_BUT_MIGHT_FAIL",
        },
        {
            "name": "Partial Match",
            "description": "Expected elements are subset of actual",
            "actual_response": {
                "profile-data": {
                    "accountID": [
                        "12345678912345678912345678",
                        "98765432198765432198765432",
                        "11111111111111111111111111",
                    ],
                    "imsi": ["302720603949999", "302720603948888"],
                    "msisdn": ["19195229999", "19195228888", "19195227777"],
                },
                "slfGroupName": "IMSGrp1",
            },
            "expected_result": "PASS",
        },
        {
            "name": "Missing Elements",
            "description": "Some expected elements are missing",
            "actual_response": {
                "profile-data": {
                    "accountID": [
                        "98765432198765432198765432"
                    ],  # Missing the expected one
                    "imsi": ["302720603949999"],
                    "msisdn": ["19195228888"],  # Different from expected
                },
                "slfGroupName": "IMSGrp1",
            },
            "expected_result": "FAIL",
        },
    ]

    # Set up expected for multiple items scenario
    expected_multiple = {
        "profile-data": {
            "accountID": [
                "12345678912345678912345678",
                "98765432198765432198765432",
            ],
            "imsi": ["302720603949999", "302720603948888"],
            "msisdn": ["19195229999", "19195228888"],
        },
        "slfGroupName": "IMSGrp1",
    }

    # Run tests
    results = []
    for i, scenario in enumerate(test_scenarios, 1):
        print(f"\n🔍 Test {i}: {scenario['name']}")
        print(f"Description: {scenario['description']}")

        # Use appropriate expected response based on scenario
        if "Multiple Items" in scenario["name"]:
            expected = expected_multiple
        else:
            expected = expected_response

        # Convert to JSON strings for testing
        actual_json = json.dumps(scenario["actual_response"])
        expected_json = json.dumps(expected)

        # Test with enhanced response validator
        result = validate_response_enhanced(
            pattern_match=None,  # Focus on structure comparison
            response_headers={},
            response_body=actual_json,
            response_payload=expected_json,
            logger=logger,
            config=None,
            args=None,
            sheet_name="ArrayOrderTest",
            row_idx=i,
        )

        # Analyze results
        dict_match = result["dict_match"]
        summary = result["summary"]
        match_percentage = getattr(logger, "_last_match_percentage", None)

        # Extract match percentage from logs if available
        try:
            # This is a bit hacky, but we'll capture it from the result info
            if "differences" in result and result["differences"]:
                match_percentage = "< 50% (failed)"
            else:
                match_percentage = (
                    "> 50% (passed)" if dict_match else "< 50% (failed)"
                )
        except:
            match_percentage = "Unknown"

        results.append(
            {
                "scenario": scenario["name"],
                "expected": scenario["expected_result"],
                "actual": "PASS" if dict_match else "FAIL",
                "summary": summary,
                "match_percentage": match_percentage,
            }
        )

        # Print results
        status_icon = "✅" if dict_match else "❌"
        print(f"{status_icon} Result: {'PASS' if dict_match else 'FAIL'}")
        print(f"Summary: {summary}")

        if result["differences"]:
            print(f"Differences: {result['differences']}")

    # Summary report
    print("\n" + "=" * 70)
    print("📊 SUMMARY REPORT")
    print("=" * 70)

    for result in results:
        status_icon = "✅" if result["actual"] == "PASS" else "❌"
        issue_marker = (
            "⚠️ ORDER ISSUE"
            if (
                result["expected"] == "SHOULD_PASS_BUT_MIGHT_FAIL"
                and result["actual"] == "FAIL"
            )
            else ""
        )
        print(
            f"{status_icon} {result['scenario']}: {result['actual']} {issue_marker}"
        )

        if issue_marker:
            print(f"   🔍 This demonstrates the array order sensitivity issue")
            print(f"   📝 Match percentage: {result['match_percentage']}")

    # Identify the core issue
    order_issue = any(
        r["expected"] == "SHOULD_PASS_BUT_MIGHT_FAIL" and r["actual"] == "FAIL"
        for r in results
    )

    if order_issue:
        print(f"\n🎯 IDENTIFIED ISSUE:")
        print(
            f"   The JSON comparison fails when arrays have same elements in different order."
        )
        print(f"   This is because the current comparison is order-sensitive.")
        print(
            f"   Recommendation: Implement order-independent array comparison."
        )
    else:
        print(f"\n🎉 All tests behaved as expected!")

    return results


def test_profile_data_pattern():
    """Test the specific profile-data pattern matching from your example"""

    print("\n" + "=" * 70)
    print("🧪 Testing Specific Profile-Data Pattern Matching")
    print("=" * 70)

    # Your specific JSON output
    profile_json_output = '{"profile-data":{"accountID":["12345678912345678912345678"],"imsi":["302720603949999"],"msisdn":["19195229999"]},"slfGroupName":"IMSGrp1"}'

    # Test different patterns
    test_patterns = [
        "12345678912345678912345678",  # accountID value
        "302720603949999",  # imsi value
        "19195229999",  # msisdn value
        "IMSGrp1",  # slfGroupName value
        '"accountID":["12345678912345678912345678"]',  # Full accountID structure
        "profile-data",  # Key name
    ]

    print(f"JSON Output: {profile_json_output[:100]}...")

    for i, pattern in enumerate(test_patterns, 1):
        print(f"\n🔍 Pattern Test {i}: '{pattern}'")

        result = validate_response_enhanced(
            pattern_match=pattern,
            response_headers={},
            response_body=profile_json_output,
            response_payload=None,
            logger=logger,
            config=None,
            args=None,
            sheet_name="ProfileDataTest",
            row_idx=i,
        )

        pattern_found = result["pattern_match_overall"]
        status_icon = "✅" if pattern_found else "❌"
        print(f"{status_icon} Pattern Found: {pattern_found}")
        print(f"Summary: {result['summary']}")

        if "pattern_matches" in result:
            for match_info in result["pattern_matches"]:
                if match_info["result"]:
                    print(
                        f"   ✅ {match_info['type']}: {match_info['details']}"
                    )


if __name__ == "__main__":
    # Run array order tests
    test_array_order_scenarios()

    # Run profile data pattern tests
    test_profile_data_pattern()
