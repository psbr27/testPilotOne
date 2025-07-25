#!/usr/bin/env python3
"""
Debug script to see what curl_builder is generating
"""

import json
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from testpilot.utils.curl_builder import build_curl_command

# Test context
test_context = {
    "test_name": "test_5_1_6_SMF_Registration",
    "sheet": "NRFRegistration",
    "row_idx": 21,
    "session_id": "debug_session",
}

# Test payload with nfInstanceId
nf_id = "6faf1bbc-6e4a-4454-a507-a14ef8e1bc5a"
payload = {"nfInstanceId": nf_id, "nfType": "SMF", "nfStatus": "REGISTERED"}

base_url = "http://nrf:8081/nnrf-nfm/v1/nf-instances/"

print("🔍 Debug: Testing curl_builder with NRF")
print(f"  Base URL: {base_url}")
print(f"  nfInstanceId: {nf_id}")
print(f"  Test context: {test_context}")

curl_cmd, resolved_payload = build_curl_command(
    url=base_url, method="PUT", payload=payload, test_context=test_context
)

print(f"\n📋 Generated curl command:")
print(f"  {curl_cmd}")
print(f"\n📋 Resolved payload:")
print(f"  {resolved_payload}")

expected_url = f"{base_url}{nf_id}"
print(f"\n📋 Expected URL: {expected_url}")
print(f"📋 Expected in command: '{expected_url}'")

if expected_url in curl_cmd:
    print("✅ URL correctly modified with nfInstanceId")
else:
    print("❌ URL not modified - checking what's wrong...")
    print(f"  Looking for: {expected_url}")
    print(f"  In command: {curl_cmd}")

    # Check if NRF handling was triggered
    if "NRF handler" in curl_cmd or nf_id in curl_cmd:
        print("  NRF handler seems to have been called")
    else:
        print("  NRF handler may not have been triggered")

    # Check config
    try:
        with open("config/hosts.json", "r") as f:
            config = json.load(f)
            print(f"  Config nf_name: {config.get('nf_name')}")
    except:
        print("  Could not read config file")
