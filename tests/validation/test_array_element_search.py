#!/usr/bin/env python3
"""
Test array element searching in key-value patterns
"""

import json
import logging
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "src"))
from testpilot.core.enhanced_response_validator import (
    validate_response_enhanced,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_array_element_searching():
    """Test array element searching that was previously failing"""

    print("=" * 80)
    print("TESTING ARRAY ELEMENT SEARCHING")
    print("=" * 80)

    # Test cases from comprehensive test that were failing
    test_cases = [
        {
            "name": "Key-value in array element (name:service1)",
            "pattern": "name:service1",
            "response": {
                "nfType": "UDM",
                "status": {"code": 200, "message": "OK"},
                "services": [
                    {"name": "service1", "port": 8080},
                    {"name": "service2", "port": 8081},
                ],
                "metadata": {"version": "1.0", "environment": "prod"},
            },
            "expected": True,
        },
        {
            "name": "Numeric value in array (port:8080)",
            "pattern": "port:8080",
            "response": {
                "nfType": "UDM",
                "status": {"code": 200, "message": "OK"},
                "services": [
                    {"name": "service1", "port": 8080},
                    {"name": "service2", "port": 8081},
                ],
                "metadata": {"version": "1.0", "environment": "prod"},
            },
            "expected": True,
        },
        {
            "name": "Key-value in mixed array (type:object)",
            "pattern": "type:object",
            "response": {
                "string_field": "simple_string",
                "mixed_array": [
                    "plain_string",
                    {"type": "object", "data": [1, 2, 3]},
                    [{"nested_array_object": "deep_value"}],
                ],
            },
            "expected": True,
        },
        {
            "name": "Deeply nested array value",
            "pattern": "deep_array_object:found_it",
            "response": {
                "level1": {
                    "level2": {
                        "level3": {
                            "level4": {
                                "level5": {
                                    "target_value": "deep_nested_value",
                                    "array": [
                                        1,
                                        2,
                                        {"deep_array_object": "found_it"},
                                    ],
                                }
                            }
                        }
                    }
                }
            },
            "expected": True,
        },
        {
            "name": "Array within array",
            "pattern": "nested_array_object:deep_value",
            "response": {
                "mixed_array": [
                    "plain_string",
                    {"type": "object", "data": [1, 2, 3]},
                    [{"nested_array_object": "deep_value"}],
                ]
            },
            "expected": True,
        },
    ]

    passed = 0
    failed = 0

    for test in test_cases:
        print(f"\nTest: {test['name']}")
        print(f"Pattern: {test['pattern']}")

        result = validate_response_enhanced(
            pattern_match=test["pattern"],
            response_headers={"content-type": "application/json"},
            response_body=test["response"],
            response_payload=None,
            logger=logger,
        )

        actual = result["pattern_match_overall"]
        success = actual == test["expected"]

        print(f"Expected: {test['expected']}, Got: {actual}")
        print(f"Result: {'✅ PASS' if success else '❌ FAIL'}")

        if success:
            passed += 1
        else:
            failed += 1
            print(f"Pattern matches: {result['pattern_matches']}")

    print(f"\n{'='*80}")
    print(
        f"SUMMARY: {passed} passed, {failed} failed out of {len(test_cases)} tests"
    )


if __name__ == "__main__":
    test_array_element_searching()
