#!/usr/bin/env python3
"""
Focused test for pattern matching issues with raw_output in validate_response_enhanced
"""

import json
import logging
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "src"))
from testpilot.core.enhanced_response_validator import (
    validate_response_enhanced,
)

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def test_pattern_matching_issues():
    """Test cases focused on pattern matching problems with raw_output"""

    print("=" * 80)
    print("PATTERN MATCHING FOCUSED TESTS - RAW OUTPUT ISSUES")
    print("=" * 80)

    # Test 1: Nested key-value pattern matching failure
    print("Test 1: Nested key-value pattern matching (FAILING)")
    response_body = {
        "nfProfile": {
            "nfInstanceId": "nested-instance",
            "nfType": "SMF",
            "status": {"health": "OK", "code": 200},
        }
    }

    raw_output = '{"nfProfile":{"nfInstanceId":"nested-instance","nfType":"SMF","status":{"health":"OK","code":200}}}'
    pattern_match = "status.code:200"

    result = validate_response_enhanced(
        pattern_match=pattern_match,
        response_headers={"content-type": "application/json"},
        response_body=response_body,
        response_payload=None,
        logger=logger,
    )

    print(f"Pattern Match Overall: {result['pattern_match_overall']}")
    print(f"Pattern Matches: {result['pattern_matches']}")
    print(f"Expected: Should find status.code:200 in nested structure")
    print("-" * 80)

    # Test 2: Direct key matching vs nested key matching
    print("Test 2: Direct vs nested key matching")
    response_body = {"status": {"code": 200, "message": "OK"}}
    raw_output = '{"status":{"code":200,"message":"OK"}}'

    # This should work
    pattern_match = "code:200"
    result1 = validate_response_enhanced(
        pattern_match=pattern_match,
        response_headers={"content-type": "application/json"},
        response_body=response_body,
        response_payload=None,
        logger=logger,
    )

    # This should work but doesn't
    pattern_match = "status.code:200"
    result2 = validate_response_enhanced(
        pattern_match=pattern_match,
        response_headers={"content-type": "application/json"},
        response_body=response_body,
        response_payload=None,
        logger=logger,
    )

    print(f"Direct 'code:200': {result1['pattern_match_overall']}")
    print(f"Nested 'status.code:200': {result2['pattern_match_overall']}")
    print(
        f"Issue: Nested key-value matching fails in _search_nested_key_value function"
    )
    print("-" * 80)

    # Test 3: Pattern matching with JSON string vs parsed object
    print("Test 3: JSON string response body pattern matching")

    # JSON as string - should work
    response_body_str = '{"nfType":"UDM","nfStatus":"REGISTERED","priority":1}'
    result_str = validate_response_enhanced(
        pattern_match="nfType:UDM",
        response_headers={"content-type": "application/json"},
        response_body=response_body_str,
        response_payload=None,
        logger=logger,
    )

    # JSON as parsed object - should work
    response_body_obj = {
        "nfType": "UDM",
        "nfStatus": "REGISTERED",
        "priority": 1,
    }
    result_obj = validate_response_enhanced(
        pattern_match="nfType:UDM",
        response_headers={"content-type": "application/json"},
        response_body=response_body_obj,
        response_payload=None,
        logger=logger,
    )

    print(f"String response body: {result_str['pattern_match_overall']}")
    print(f"Object response body: {result_obj['pattern_match_overall']}")
    print(f"Both should work but may have different behavior")
    print("-" * 80)

    # Test 4: Pattern matching in arrays - raw_output focus
    print("Test 4: Pattern matching in array responses")

    response_body = [
        {"nfInstanceId": "id1", "nfType": "UDM", "status": "ACTIVE"},
        {"nfInstanceId": "id2", "nfType": "AMF", "status": "INACTIVE"},
    ]
    raw_output = '[{"nfInstanceId":"id1","nfType":"UDM","status":"ACTIVE"},{"nfInstanceId":"id2","nfType":"AMF","status":"INACTIVE"}]'

    # Should find UDM in array
    result = validate_response_enhanced(
        pattern_match="nfType:UDM",
        response_headers={"content-type": "application/json"},
        response_body=response_body,
        response_payload=None,
        logger=logger,
    )

    print(
        f"Array pattern match 'nfType:UDM': {result['pattern_match_overall']}"
    )
    print(f"Pattern matches: {result['pattern_matches']}")
    print("-" * 80)

    # Test 5: Section 2.5 pattern matching issue (JSON string pattern_match)
    print("Test 5: Section 2.5 pattern matching - JSON string as pattern")

    response_body = {
        "nfInstanceId": "test123",
        "nfType": "UDM",
        "nfStatus": "REGISTERED",
    }
    pattern_match = (
        '{"nfType":"UDM","nfStatus":"REGISTERED"}'  # JSON string as pattern
    )

    result = validate_response_enhanced(
        pattern_match=pattern_match,
        response_headers={"content-type": "application/json"},
        response_body=response_body,
        response_payload=None,
        logger=logger,
    )

    print(f"JSON pattern match: {result['pattern_match_overall']}")
    print(f"Pattern matches: {result['pattern_matches']}")
    print(f"Section 2.5 should handle this case (lines 438-461)")
    print("-" * 80)

    # Test 6: Empty pattern_match handling
    print("Test 6: Empty pattern_match handling")

    response_body = {"result": "success"}
    raw_output = '{"result":"success"}'

    result = validate_response_enhanced(
        pattern_match="",  # Empty pattern
        response_headers={"content-type": "application/json"},
        response_body=response_body,
        response_payload=None,
        logger=logger,
    )

    print(f"Empty pattern result: {result['pattern_match_overall']}")
    print(f"Should be None (no pattern provided)")
    print("-" * 80)


if __name__ == "__main__":
    test_pattern_matching_issues()
