#!/usr/bin/env python3
"""
Test and fix array subset matching in JSON patterns
"""

import json
import logging
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "src"))
from testpilot.core.enhanced_response_validator import (
    _is_subset_dict,
    validate_response_enhanced,
)

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def test_array_subset_matching():
    """Test array subset matching issues"""

    print("=" * 80)
    print("TESTING ARRAY SUBSET MATCHING IN JSON PATTERNS")
    print("=" * 80)

    # Test 1: Array with object subset (currently failing)
    print("\nTest 1: Array with object subset")
    response1 = {
        "nfInstanceId": "uuid-123",
        "nfType": "UDM",
        "nfStatus": "REGISTERED",
        "heartBeatTimer": 90,
        "plmnList": [{"mcc": "001", "mnc": "01"}],
        "services": {
            "nudm-sdm": {"versions": ["v1", "v2"]},
            "nudm-uecm": {"versions": ["v1"]},
        },
    }

    pattern1 = '{"plmnList":[{"mcc":"001"}]}'

    result = validate_response_enhanced(
        pattern_match=pattern1,
        response_headers={"content-type": "application/json"},
        response_body=response1,
        response_payload=None,
        logger=logger,
    )

    print(f"Pattern: {pattern1}")
    print(f"Pattern match result: {result['pattern_match_overall']}")
    print(f"Pattern matches: {result['pattern_matches']}")

    # Let's debug the subset matching
    pattern_json = json.loads(pattern1)
    print(
        f"\nDirect subset test: {_is_subset_dict(pattern_json, response1, partial=True)}"
    )
    print(f"plmnList in response: {response1.get('plmnList')}")
    print(f"plmnList in pattern: {pattern_json.get('plmnList')}")

    # Test 2: JSON array pattern ["tag1"]
    print("\n" + "-" * 80)
    print("Test 2: JSON array pattern")
    response2 = [
        {"id": 1, "name": "item1", "tags": ["tag1", "tag2"]},
        {"id": 2, "name": "item2", "tags": ["tag3", "tag4"]},
        {"id": 3, "name": "item3", "tags": ["tag1", "tag5"]},
    ]

    pattern2 = '["tag1"]'

    result = validate_response_enhanced(
        pattern_match=pattern2,
        response_headers={"content-type": "application/json"},
        response_body=response2,
        response_payload=None,
        logger=logger,
    )

    print(f"Pattern: {pattern2}")
    print(f"Pattern match result: {result['pattern_match_overall']}")
    print(f"Expected: Should find 'tag1' in nested arrays")

    # Test 3: More complex array subset
    print("\n" + "-" * 80)
    print("Test 3: Complex nested array pattern")
    response3 = {
        "services": [
            {
                "name": "service1",
                "config": {"ports": [8080, 8081], "enabled": True},
            },
            {
                "name": "service2",
                "config": {"ports": [9090], "enabled": False},
            },
        ]
    }

    pattern3 = '{"services":[{"config":{"ports":[8080]}}]}'

    result = validate_response_enhanced(
        pattern_match=pattern3,
        response_headers={"content-type": "application/json"},
        response_body=response3,
        response_payload=None,
        logger=logger,
    )

    print(f"Pattern: {pattern3}")
    print(f"Pattern match result: {result['pattern_match_overall']}")
    print(f"Expected: Should match since 8080 is in the ports array")


if __name__ == "__main__":
    test_array_subset_matching()
