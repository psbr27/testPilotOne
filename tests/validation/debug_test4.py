#!/usr/bin/env python3
"""
Debug Test 4 failure - JSON pattern matching
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


def debug_test4():
    """Debug why Test 4 is failing"""

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

    pattern_match = '{"nfType":"UDM","nfStatus":"REGISTERED"}'

    print("DEBUG: Test 4 Analysis")
    print("=" * 50)
    print(f"Pattern: {pattern_match}")
    print(f"Raw Output: {raw_output}")
    print("=" * 50)

    result = validate_response_enhanced(
        pattern_match=pattern_match,
        response_headers={"content-type": "application/json"},
        response_body=response_body,
        response_payload=None,
        logger=logger,
        raw_output=raw_output,
    )

    print(f"Result: {result['pattern_match_overall']}")
    print(f"Pattern Matches: {result['pattern_matches']}")

    # Let's test if the issue is with section 2.5
    print("\n" + "=" * 50)
    print("MANUAL TEST - Does pattern exist in raw_output?")
    print("=" * 50)

    # Test basic substring search
    if "nfType" in raw_output and "UDM" in raw_output:
        print("✓ nfType and UDM found in raw_output")
    else:
        print("✗ nfType or UDM NOT found in raw_output")

    if "nfStatus" in raw_output and "REGISTERED" in raw_output:
        print("✓ nfStatus and REGISTERED found in raw_output")
    else:
        print("✗ nfStatus or REGISTERED NOT found in raw_output")

    # Test JSON pattern as substring
    if pattern_match in raw_output:
        print("✓ Exact JSON pattern found as substring in raw_output")
    else:
        print("✗ Exact JSON pattern NOT found as substring in raw_output")
        # Let's see what's different
        import difflib

        print("Checking character by character...")
        raw_parsed = json.loads(raw_output)
        pattern_parsed = json.loads(pattern_match)
        print(f"Pattern parsed: {pattern_parsed}")
        print(f"Raw contains nfType: {raw_parsed.get('nfType')}")
        print(f"Raw contains nfStatus: {raw_parsed.get('nfStatus')}")


if __name__ == "__main__":
    debug_test4()
