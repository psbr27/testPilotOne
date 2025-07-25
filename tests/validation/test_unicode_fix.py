#!/usr/bin/env python3
"""
Test and fix Unicode encoding in JSON serialization
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


def test_unicode_encoding():
    """Test Unicode encoding issues"""

    print("=" * 80)
    print("TESTING UNICODE ENCODING IN JSON SERIALIZATION")
    print("=" * 80)

    # Test case that was failing
    response = {
        "json_string": '{"nested":"value"}',
        "url": "https://example.com/path?param=value",
        "special_chars": "!@#$%^&*()",
        "unicode": "Hello 世界 🌍",
    }

    pattern = "🌍"

    print(f"Pattern: {pattern}")
    print(f"Response unicode field: {response['unicode']}")
    print(f"Pattern in response['unicode']: {pattern in response['unicode']}")

    # Check JSON serialization
    json_str = json.dumps(response, separators=(",", ":"))
    print(f"\nJSON serialized (default): {json_str}")
    print(f"Pattern in serialized: {pattern in json_str}")

    # Try with ensure_ascii=False
    json_str_unicode = json.dumps(
        response, separators=(",", ":"), ensure_ascii=False
    )
    print(f"\nJSON serialized (ensure_ascii=False): {json_str_unicode}")
    print(f"Pattern in unicode serialized: {pattern in json_str_unicode}")

    # Test the validation
    result = validate_response_enhanced(
        pattern_match=pattern,
        response_headers={"content-type": "application/json"},
        response_body=response,
        response_payload=None,
        logger=logger,
    )

    print(f"\nPattern match result: {result['pattern_match_overall']}")
    print(f"Pattern matches: {result['pattern_matches']}")

    # Test other Unicode scenarios
    print("\n" + "-" * 80)
    print("Additional Unicode tests:")

    test_cases = [
        {"pattern": "世界", "name": "Chinese characters"},
        {"pattern": "Hello 世界", "name": "Mixed ASCII and Unicode"},
        {"pattern": "!@#$%", "name": "Special characters (should work)"},
        {"pattern": "🌍", "name": "Emoji"},
    ]

    for test in test_cases:
        result = validate_response_enhanced(
            pattern_match=test["pattern"],
            response_headers={"content-type": "application/json"},
            response_body=response,
            response_payload=None,
            logger=logger,
        )
        print(f"\n{test['name']}: {test['pattern']}")
        print(f"Result: {result['pattern_match_overall']}")


if __name__ == "__main__":
    test_unicode_encoding()
