#!/usr/bin/env python3
"""
Test the raw_output parameter fix for pattern matching
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


def test_raw_output_pattern_matching():
    """Test raw_output parameter for pattern matching"""

    print("=" * 80)
    print("RAW OUTPUT PATTERN MATCHING TEST")
    print("=" * 80)

    # Test with NRF registration data
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

    # Raw output from actual NRF test
    raw_output = '{"nfInstanceId":"1faf1bbc-6e4a-4454-a507-a14ef8e1bc5c","nfType":"UDM","nfStatus":"REGISTERED","heartBeatTimer":90,"fqdn":"UDM.d5g.oracle.com","interPlmnFqdn":"UDM-d5g.oracle.com","ipv4Addresses":["192.168.2.100","192.168.3.100","192.168.2.110","192.168.3.110"],"ipv6Addresses":["2001:0db8:85a3:0000:0000:8a2e:0370:7334"]}'

    # Test 1: Pattern matching using raw_output
    print("Test 1: Pattern matching with raw_output parameter")
    pattern_match = "UDM.d5g.oracle.com"

    result = validate_response_enhanced(
        pattern_match=pattern_match,
        response_headers={"content-type": "application/json"},
        response_body=response_body,
        response_payload=None,
        logger=logger,
        raw_output=raw_output,
    )

    print(f"Pattern Match Result: {result['pattern_match_overall']}")
    print(f"Summary: {result['summary']}")
    print("-" * 80)

    # Test 2: Pattern matching without raw_output
    print("Test 2: Pattern matching without raw_output parameter")

    result2 = validate_response_enhanced(
        pattern_match=pattern_match,
        response_headers={"content-type": "application/json"},
        response_body=response_body,
        response_payload=None,
        logger=logger,
        # No raw_output parameter
    )

    print(f"Pattern Match Result: {result2['pattern_match_overall']}")
    print(f"Summary: {result2['summary']}")
    print("-" * 80)

    # Test 3: Key-value pattern with raw_output
    print("Test 3: Key-value pattern with raw_output")
    pattern_match = "nfType:UDM"

    result3 = validate_response_enhanced(
        pattern_match=pattern_match,
        response_headers={"content-type": "application/json"},
        response_body=response_body,
        response_payload=None,
        logger=logger,
        raw_output=raw_output,
    )

    print(f"Pattern Match Result: {result3['pattern_match_overall']}")
    print(f"Summary: {result3['summary']}")
    print("-" * 80)

    # Test 4: JSON pattern matching with raw_output
    print("Test 4: JSON pattern matching with raw_output")
    pattern_match = '{"nfType":"UDM","nfStatus":"REGISTERED"}'

    result4 = validate_response_enhanced(
        pattern_match=pattern_match,
        response_headers={"content-type": "application/json"},
        response_body=response_body,
        response_payload=None,
        logger=logger,
        raw_output=raw_output,
    )

    print(f"Pattern Match Result: {result4['pattern_match_overall']}")
    print(f"Summary: {result4['summary']}")
    print("-" * 80)

    print("SUMMARY:")
    print(
        f"Test 1 (substring with raw_output): {'PASS' if result['pattern_match_overall'] else 'FAIL'}"
    )
    print(
        f"Test 2 (substring without raw_output): {'PASS' if result2['pattern_match_overall'] else 'FAIL'}"
    )
    print(
        f"Test 3 (key-value with raw_output): {'PASS' if result3['pattern_match_overall'] else 'FAIL'}"
    )
    print(
        f"Test 4 (JSON pattern with raw_output): {'PASS' if result4['pattern_match_overall'] else 'FAIL'}"
    )


if __name__ == "__main__":
    test_raw_output_pattern_matching()
