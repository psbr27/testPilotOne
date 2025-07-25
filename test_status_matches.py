#!/usr/bin/env python3
"""
Test script to verify status_matches function behavior
"""

import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from testpilot.core.validation_engine import status_matches


def test_status_matches():
    print("🧪 Testing status_matches function")

    # Test cases: (expected, actual, should_pass, description)
    test_cases = [
        # Exact matches
        (200, 200, True, "Exact match: 200 == 200"),
        ("200", 200, True, "String to int exact match: '200' == 200"),
        (200, "200", True, "Int to string exact match: 200 == '200'"),
        # Wildcard patterns - uppercase
        ("4XX", 400, True, "4XX should match 400"),
        ("4XX", 402, True, "4XX should match 402"),
        ("4XX", 404, True, "4XX should match 404"),
        ("4XX", 499, True, "4XX should match 499"),
        ("4XX", 500, False, "4XX should NOT match 500"),
        ("4XX", 399, False, "4XX should NOT match 399"),
        # Wildcard patterns - lowercase (current issue)
        ("4xx", 400, True, "4xx should match 400 (case insensitive)"),
        ("4xx", 402, True, "4xx should match 402 (case insensitive)"),
        ("4xx", 404, True, "4xx should match 404 (case insensitive)"),
        ("4xx", 499, True, "4xx should match 499 (case insensitive)"),
        ("4xx", 500, False, "4xx should NOT match 500"),
        ("4xx", 399, False, "4xx should NOT match 399"),
        # Other wildcards
        ("2XX", 200, True, "2XX should match 200"),
        ("2xx", 200, True, "2xx should match 200 (case insensitive)"),
        ("5XX", 500, True, "5XX should match 500"),
        ("5xx", 503, True, "5xx should match 503 (case insensitive)"),
        # Range patterns
        ("400-404", 402, True, "Range 400-404 should match 402"),
        ("400-404", 405, False, "Range 400-404 should NOT match 405"),
        # Edge cases
        (None, 200, False, "None expected should not match"),
        ("4XX", None, False, "None actual should not match"),
        ("invalid", 200, False, "Invalid pattern should not match"),
    ]

    passed = 0
    failed = 0

    for expected, actual, should_pass, description in test_cases:
        try:
            result = status_matches(expected, actual)
            if result == should_pass:
                print(f"✅ PASS: {description}")
                passed += 1
            else:
                print(f"❌ FAIL: {description}")
                print(f"   Expected: {should_pass}, Got: {result}")
                failed += 1
        except Exception as e:
            print(f"💥 ERROR: {description}")
            print(f"   Exception: {e}")
            failed += 1

    print(f"\n📊 Results: {passed} passed, {failed} failed")

    if failed > 0:
        print("\n⚠️  Issues found with status_matches function!")
        return False
    else:
        print("\n🎉 All tests passed!")
        return True


if __name__ == "__main__":
    test_status_matches()
