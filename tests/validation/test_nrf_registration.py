#!/usr/bin/env python3
"""
Test file for NRF Registration validation using enhanced_response_validator
Tests corner cases found in the NRF registration test results
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


class TestNRFRegistrationValidation:
    """Test cases for NRF Registration validation using actual test data"""

    def test_successful_put_registration(self):
        """Test case 1: Successful PUT registration with mandatory parameters"""
        response_body = {
            "nfInstanceId": "1faf1bbc-6e4a-4454-a507-a14ef8e1bc5c",
            "nfType": "UDM",
            "nfStatus": "REGISTERED",
            "heartBeatTimer": 90,
            "fqdn": "UDM.d5g.oracle.com",
            "interPlmnFqdn": "UDM-d5g.oracle.com",
            "ipv4Addresses": [
                "192.168.2.100",
                "192.168.3.100",
                "192.168.2.110",
                "192.168.3.110",
            ],
            "ipv6Addresses": ["2001:0db8:85a3:0000:0000:8a2e:0370:7334"],
        }

        raw_output = '{"nfInstanceId":"1faf1bbc-6e4a-4454-a507-a14ef8e1bc5c","nfType":"UDM","nfStatus":"REGISTERED","heartBeatTimer":90,"fqdn":"UDM.d5g.oracle.com","interPlmnFqdn":"UDM-d5g.oracle.com","ipv4Addresses":["192.168.2.100","192.168.3.100","192.168.2.110","192.168.3.110"],"ipv6Addresses":["2001:0db8:85a3:0000:0000:8a2e:0370:7334"]}'

        pattern_match = ""

        expected_payload = {
            "nfInstanceId": "1faf1bbc-6e4a-4454-a507-a14ef8e1bc5c",
            "nfType": "UDM",
            "nfStatus": "REGISTERED",
        }

        result = validate_response_enhanced(
            pattern_match=pattern_match,
            response_headers={"content-type": "application/json"},
            response_body=response_body,
            response_payload=expected_payload,
            logger=logger,
            config={"partial_dict_match": True, "ignore_array_order": True},
        )

        print(f"Test 1 - Successful PUT Registration:")
        print(f"Dict Match: {result['dict_match']}")
        print(f"Pattern Match Overall: {result['pattern_match_overall']}")
        print(f"Summary: {result['summary']}")
        print(f"Differences: {result['differences']}")
        print("-" * 80)

        return result

    def test_method_not_allowed_error(self):
        """Test case 2: Method not allowed error (DELETE without instance ID)"""
        response_body = {
            "timestamp": "2025-07-22T19:12:29.422+00:00",
            "status": 405,
            "error": "Method Not Allowed",
            "path": "/nnrf-nfm/v1/nf-instances/",
        }

        raw_output = '{"timestamp":"2025-07-22T19:12:29.422+00:00","status":405,"error":"Method Not Allowed","path":"/nnrf-nfm/v1/nf-instances/"}'

        pattern_match = "Method Not Allowed"

        expected_payload = {"status": 405, "error": "Method Not Allowed"}

        result = validate_response_enhanced(
            pattern_match=pattern_match,
            response_headers={"content-type": "application/json"},
            response_body=response_body,
            response_payload=expected_payload,
            logger=logger,
            config={"partial_dict_match": True},
        )

        print(f"Test 2 - Method Not Allowed Error:")
        print(f"Dict Match: {result['dict_match']}")
        print(f"Pattern Match Overall: {result['pattern_match_overall']}")
        print(f"Summary: {result['summary']}")
        print(f"Differences: {result['differences']}")
        print("-" * 80)

        return result

    def test_bad_request_missing_mandatory(self):
        """Test case 3: Bad request with missing mandatory parameters"""
        response_body = {
            "title": "Bad Request",
            "status": 400,
            "detail": "NRF-d5g.oracle.com: Nnrf_NFManagement: Multiple attributes are missing or incorrect: ONRF-REG-REGN-E0021",
            "instance": "http://ocnrf-tailgate-ingressgateway.ocnrf:8080/nnrf-nfm/v1/nf-instances/2faf1bbc-6e4a-4454-a507-a14ef8e1bc5c",
            "cause": "MANDATORY_IE_MISSING",
            "invalidParams": [
                {"param": "nfStatus", "reason": "nfStatus should be present"},
                {"param": "nfType", "reason": "nfType should be present"},
            ],
        }

        raw_output = '{"title":"Bad Request","status":400,"detail":"NRF-d5g.oracle.com: Nnrf_NFManagement: Multiple attributes are missing or incorrect: ONRF-REG-REGN-E0021","instance":"http://ocnrf-tailgate-ingressgateway.ocnrf:8080/nnrf-nfm/v1/nf-instances/2faf1bbc-6e4a-4454-a507-a14ef8e1bc5c","cause":"MANDATORY_IE_MISSING","invalidParams":[{"param":"nfStatus","reason":"nfStatus should be present"},{"param":"nfType","reason":"nfType should be present"}]}'

        pattern_match = "MANDATORY_IE_MISSING"

        expected_payload = {"status": 400, "cause": "MANDATORY_IE_MISSING"}

        result = validate_response_enhanced(
            pattern_match=pattern_match,
            response_headers={"content-type": "application/problem+json"},
            response_body=response_body,
            response_payload=expected_payload,
            logger=logger,
            config={"partial_dict_match": True, "ignore_array_order": True},
        )

        print(f"Test 3 - Bad Request Missing Mandatory:")
        print(f"Dict Match: {result['dict_match']}")
        print(f"Pattern Match Overall: {result['pattern_match_overall']}")
        print(f"Summary: {result['summary']}")
        print(f"Differences: {result['differences']}")
        print("-" * 80)

        return result

    def test_empty_response_delete_success(self):
        """Test case 4: Empty response for successful DELETE (204)"""
        response_body = None
        raw_output = ""
        pattern_match = ""
        expected_payload = None

        result = validate_response_enhanced(
            pattern_match=pattern_match,
            response_headers={"content-type": "unknown"},
            response_body=response_body,
            response_payload=expected_payload,
            logger=logger,
            config={"partial_dict_match": True},
        )

        print(f"Test 4 - Empty Response DELETE Success:")
        print(f"Dict Match: {result['dict_match']}")
        print(f"Pattern Match Overall: {result['pattern_match_overall']}")
        print(f"Summary: {result['summary']}")
        print(f"Differences: {result['differences']}")
        print("-" * 80)

        return result

    def test_json_string_response_body(self):
        """Test case 5: Response body as JSON string instead of dict"""
        response_body = '{"nfInstanceId":"1faf1bbc-6e4a-4454-a507-a14ef8e1bc5c","nfType":"UDM","nfStatus":"REGISTERED","heartBeatTimer":90}'

        pattern_match = "REGISTERED"

        expected_payload = {"nfType": "UDM", "nfStatus": "REGISTERED"}

        result = validate_response_enhanced(
            pattern_match=pattern_match,
            response_headers={"content-type": "application/json"},
            response_body=response_body,
            response_payload=expected_payload,
            logger=logger,
            config={"partial_dict_match": True},
        )

        print(f"Test 5 - JSON String Response Body:")
        print(f"Dict Match: {result['dict_match']}")
        print(f"Pattern Match Overall: {result['pattern_match_overall']}")
        print(f"Summary: {result['summary']}")
        print(f"Differences: {result['differences']}")
        print("-" * 80)

        return result

    def test_key_value_pattern_matching(self):
        """Test case 6: Key-value pattern matching with colon separator"""
        response_body = {
            "nfInstanceId": "test-instance-123",
            "nfType": "AMF",
            "nfStatus": "REGISTERED",
            "priority": 1,
        }

        pattern_match = "nfType:AMF"
        expected_payload = None

        result = validate_response_enhanced(
            pattern_match=pattern_match,
            response_headers={"content-type": "application/json"},
            response_body=response_body,
            response_payload=expected_payload,
            logger=logger,
            config={"partial_dict_match": True},
        )

        print(f"Test 6 - Key-Value Pattern Matching:")
        print(f"Dict Match: {result['dict_match']}")
        print(f"Pattern Match Overall: {result['pattern_match_overall']}")
        print(f"Summary: {result['summary']}")
        print(f"Pattern matches: {result['pattern_matches']}")
        print("-" * 80)

        return result

    def test_nested_key_value_pattern(self):
        """Test case 7: Nested key-value pattern matching"""
        response_body = {
            "nfProfile": {
                "nfInstanceId": "nested-instance",
                "nfType": "SMF",
                "status": {"health": "OK", "code": 200},
            }
        }

        pattern_match = "status.code:200"
        expected_payload = None

        result = validate_response_enhanced(
            pattern_match=pattern_match,
            response_headers={"content-type": "application/json"},
            response_body=response_body,
            response_payload=expected_payload,
            logger=logger,
            config={"partial_dict_match": True},
        )

        print(f"Test 7 - Nested Key-Value Pattern:")
        print(f"Dict Match: {result['dict_match']}")
        print(f"Pattern Match Overall: {result['pattern_match_overall']}")
        print(f"Summary: {result['summary']}")
        print(f"Pattern matches: {result['pattern_matches']}")
        print("-" * 80)

        return result

    def test_array_response_dict_matching(self):
        """Test case 8: Array response with dict matching"""
        response_body = [
            {
                "nfInstanceId": "instance-1",
                "nfType": "UDM",
                "nfStatus": "REGISTERED",
            },
            {
                "nfInstanceId": "instance-2",
                "nfType": "AMF",
                "nfStatus": "REGISTERED",
            },
        ]

        pattern_match = ""
        expected_payload = {"nfType": "UDM", "nfStatus": "REGISTERED"}

        result = validate_response_enhanced(
            pattern_match=pattern_match,
            response_headers={"content-type": "application/json"},
            response_body=response_body,
            response_payload=expected_payload,
            logger=logger,
            config={"partial_dict_match": True},
        )

        print(f"Test 8 - Array Response Dict Matching:")
        print(f"Dict Match: {result['dict_match']}")
        print(f"Pattern Match Overall: {result['pattern_match_overall']}")
        print(f"Summary: {result['summary']}")
        print(f"Differences: {result['differences']}")
        print("-" * 80)

        return result


def run_all_tests():
    """Run all NRF registration validation tests"""
    print("=" * 80)
    print("NRF REGISTRATION VALIDATION TESTS")
    print("=" * 80)

    test_runner = TestNRFRegistrationValidation()

    tests = [
        test_runner.test_successful_put_registration,
        test_runner.test_method_not_allowed_error,
        test_runner.test_bad_request_missing_mandatory,
        test_runner.test_empty_response_delete_success,
        test_runner.test_json_string_response_body,
        test_runner.test_key_value_pattern_matching,
        test_runner.test_nested_key_value_pattern,
        test_runner.test_array_response_dict_matching,
    ]

    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"Test {test.__name__} failed with error: {e}")
            results.append(None)

    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)

    passed = sum(
        1
        for r in results
        if r
        and r["dict_match"] is not False
        and r["pattern_match_overall"] is not False
    )
    failed = len(results) - passed

    print(f"Total Tests: {len(results)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")

    return results


if __name__ == "__main__":
    run_all_tests()
