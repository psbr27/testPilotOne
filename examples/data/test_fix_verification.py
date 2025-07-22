#!/usr/bin/env python3
"""
Quick verification test to show the array order fix working
"""

import json
import os
import sys

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
from src.testpilot.core.json_match import compare_json_objects


def test_array_order_fix():
    """Demonstrate the array order fix"""

    print("🧪 Array Order Fix Verification")
    print("=" * 50)

    # Original - same order
    json1 = {
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

    # Same content, different order
    json2 = {
        "profile-data": {
            "accountID": [
                "98765432198765432198765432",
                "12345678912345678912345678",
            ],  # Reversed
            "imsi": ["302720603948888", "302720603949999"],  # Reversed
            "msisdn": ["19195228888", "19195229999"],  # Reversed
        },
        "slfGroupName": "IMSGrp1",
    }

    print("Expected (JSON1):")
    print(f"  accountID: {json1['profile-data']['accountID']}")
    print(f"  imsi: {json1['profile-data']['imsi']}")
    print(f"  msisdn: {json1['profile-data']['msisdn']}")

    print("\nActual (JSON2):")
    print(f"  accountID: {json2['profile-data']['accountID']}")
    print(f"  imsi: {json2['profile-data']['imsi']}")
    print(f"  msisdn: {json2['profile-data']['msisdn']}")

    # Test with order-independent comparison (new behavior)
    result_order_independent = compare_json_objects(
        json1, json2, "structure_and_values", ignore_array_order=True
    )

    # Test with order-sensitive comparison (old behavior)
    result_order_sensitive = compare_json_objects(
        json1, json2, "structure_and_values", ignore_array_order=False
    )

    print(f"\n📊 Results:")
    print(
        f"✅ Order-Independent Match: {result_order_independent['match_percentage']}% ({'PASS' if result_order_independent['match_percentage'] > 50 else 'FAIL'})"
    )
    print(
        f"❌ Order-Sensitive Match: {result_order_sensitive['match_percentage']}% ({'PASS' if result_order_sensitive['match_percentage'] > 50 else 'FAIL'})"
    )

    if (
        result_order_independent["match_percentage"] > 50
        and result_order_sensitive["match_percentage"] <= 50
    ):
        print(f"\n🎯 SUCCESS: The fix works!")
        print(f"   - Same content in different order now PASSES validation")
        print(f"   - Arrays are compared based on content, not position")
        return True
    else:
        print(f"\n❌ ISSUE: The fix may not be working correctly")
        return False


if __name__ == "__main__":
    test_array_order_fix()
