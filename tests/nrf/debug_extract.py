#!/usr/bin/env python3
"""
Debug the nfInstanceId extraction
"""

import json
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from testpilot.utils.nrf.sequence_manager import _extract_nf_instance_id

# Test different payload formats
test_payloads = [
    # Dict payload (before serialization)
    {"nfInstanceId": "test-id-1"},
    # JSON string (after serialization)
    json.dumps({"nfInstanceId": "test-id-2"}),
    # Nested in nfProfile
    json.dumps({"nfProfile": {"nfInstanceId": "test-id-3"}}),
    # List format
    json.dumps([{"nfInstanceId": "test-id-4"}]),
    # No nfInstanceId
    json.dumps({"nfType": "SMF"}),
    # Invalid JSON
    "not-json",
    # None
    None,
    # Empty string
    "",
]

print("🔍 Testing nfInstanceId extraction:")

for i, payload in enumerate(test_payloads):
    print(f"\n{i+1}. Payload: {payload}")
    print(f"   Type: {type(payload)}")

    result = _extract_nf_instance_id(payload)
    print(f"   Extracted: {result}")

    if isinstance(payload, dict):
        # Also test after JSON serialization
        serialized = json.dumps(payload)
        result_serialized = _extract_nf_instance_id(serialized)
        print(f"   Serialized: {serialized}")
        print(f"   Extracted from serialized: {result_serialized}")
