#!/usr/bin/env python3
"""
Debug SLF vs NRF handling
"""

import json
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

# Clear any existing sessions first
from testpilot.utils.nrf import sequence_manager

sequence_manager._session_managers.clear()

from testpilot.utils.curl_builder import build_curl_command

# Set up SLF config
slf_config = {
    "use_ssh": False,
    "pod_mode": False,
    "nf_name": "SLF",  # Non-NRF
    "connect_to": "tailgate",
}

os.makedirs("config", exist_ok=True)
with open("config/hosts.json", "w") as f:
    json.dump(slf_config, f, indent=2)

# Test context
test_context = {
    "test_name": "test_slf_operation",
    "sheet": "SLFTest",
    "row_idx": 1,
    "session_id": "slf_session",
}

# Payload with nfInstanceId (should be ignored for SLF)
nf_id = "6faf1bbc-6e4a-4454-a507-a14ef8e1bc5a"
payload = {"nfInstanceId": nf_id, "nfType": "SMF", "nfStatus": "REGISTERED"}

slf_url = "http://slf:8080/api/test"

print("🔍 Debug: Testing SLF (non-NRF) handling")
print(f"  URL: {slf_url}")
print(f"  Payload contains nfInstanceId: {nf_id}")
print(f"  Config nf_name: SLF")

curl_cmd, resolved_payload = build_curl_command(
    url=slf_url, method="PUT", payload=payload, test_context=test_context
)

print(f"\n📋 Generated curl command:")
print(f"  {curl_cmd}")

# Check if nfInstanceId appears in URL (it shouldn't for SLF)
if nf_id in curl_cmd:
    print(
        f"❌ nfInstanceId found in curl command (shouldn't be there for SLF)"
    )
    print(f"  Looking for: {nf_id}")
else:
    print(f"✅ nfInstanceId correctly NOT in curl command for SLF")

# Check URL modification
if slf_url in curl_cmd:
    print(f"✅ Original SLF URL preserved: {slf_url}")
else:
    print(f"❌ SLF URL was modified unexpectedly")
