#!/usr/bin/env python3
"""
Test and fix _search_nested_key_value for deeper nesting issues
"""

import json
import logging
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "src"))
from testpilot.core.enhanced_response_validator import (
    _search_nested_key_value,
    validate_response_enhanced,
)

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def test_nested_key_value_issues():
    """Test the specific failing nested key-value patterns"""

    print("=" * 80)
    print("TESTING NESTED KEY-VALUE PATTERNS")
    print("=" * 80)

    # Test 1: metadata.version:1.0 (currently failing)
    print("\nTest 1: metadata.version:1.0")
    response1 = {
        "nfType": "UDM",
        "status": {"code": 200, "message": "OK"},
        "services": [
            {"name": "service1", "port": 8080},
            {"name": "service2", "port": 8081},
        ],
        "metadata": {"version": "1.0", "environment": "prod"},
    }

    # Direct test of _search_nested_key_value
    result = _search_nested_key_value(response1, "metadata.version", "1.0")
    print(f"Direct _search_nested_key_value result: {result}")

    # Full validation test
    result = validate_response_enhanced(
        pattern_match="metadata.version:1.0",
        response_headers={"content-type": "application/json"},
        response_body=response1,
        response_payload=None,
        logger=logger,
    )
    print(f"Pattern match result: {result['pattern_match_overall']}")
    print(f"Pattern matches: {result['pattern_matches']}")

    # Test 2: Deep nested key-value
    print("\n" + "-" * 80)
    print("Test 2: level5.target_value:deep_nested_value")
    response2 = {
        "level1": {
            "level2": {
                "level3": {
                    "level4": {
                        "level5": {
                            "target_value": "deep_nested_value",
                            "array": [1, 2, {"deep_array_object": "found_it"}],
                        }
                    }
                }
            }
        }
    }

    # Direct test
    result = _search_nested_key_value(
        response2, "level5.target_value", "deep_nested_value"
    )
    print(f"Direct _search_nested_key_value result: {result}")

    # Full validation test
    result = validate_response_enhanced(
        pattern_match="level5.target_value:deep_nested_value",
        response_headers={"content-type": "application/json"},
        response_body=response2,
        response_payload=None,
        logger=logger,
    )
    print(f"Pattern match result: {result['pattern_match_overall']}")

    # Test 3: Key-value in array elements
    print("\n" + "-" * 80)
    print("Test 3: name:service1 (in array)")
    response3 = {
        "nfType": "UDM",
        "services": [
            {"name": "service1", "port": 8080},
            {"name": "service2", "port": 8081},
        ],
    }

    # Direct test
    result = _search_nested_key_value(response3, "name", "service1")
    print(f"Direct _search_nested_key_value result: {result}")

    # Test accessing array element
    result = _search_nested_key_value(
        response3["services"], "name", "service1"
    )
    print(f"Direct array _search_nested_key_value result: {result}")

    # Full validation test
    result = validate_response_enhanced(
        pattern_match="name:service1",
        response_headers={"content-type": "application/json"},
        response_body=response3,
        response_payload=None,
        logger=logger,
    )
    print(f"Pattern match result: {result['pattern_match_overall']}")

    # Test 4: Complex nested path that should work
    print("\n" + "-" * 80)
    print("Test 4: services.name:service1 (nested array)")

    # Try with explicit path
    result = _search_nested_key_value(response3, "services.name", "service1")
    print(f"Direct nested array path result: {result}")


if __name__ == "__main__":
    test_nested_key_value_issues()
