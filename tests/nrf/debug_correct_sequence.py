#!/usr/bin/env python3
"""
Debug the sequence test with correct payload format
"""

import json
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from testpilot.utils.curl_builder import build_curl_command

# Ensure NRF config
nrf_config = {
    "use_ssh": False,
    "pod_mode": False,
    "nf_name": "NRF",
    "connect_to": "tailgate",
}

os.makedirs("config", exist_ok=True)
with open("config/hosts.json", "w") as f:
    json.dump(nrf_config, f, indent=2)

# Clear previous state
from testpilot.utils.nrf import sequence_manager

sequence_manager._session_managers.clear()

base_url = "http://nrf:8081/nnrf-nfm/v1/nf-instances/"
test_context = {
    "test_name": "sequence_test",
    "sheet": "NRF",
    "row_idx": 1,
    "session_id": "sequence_session",
}

print("🔍 Debug: Correct sequence test with proper payload handling")

# PUT 1 - Pass payload as dict (should be serialized to JSON)
print("\n1. PUT seq-1 (dict payload)")
payload1 = {"nfInstanceId": "seq-1", "nfType": "SMF"}
cmd1, resolved1 = build_curl_command(
    base_url, "PUT", payload=payload1, test_context=test_context
)
print(f"   Resolved payload: {resolved1}")
print(f"   Command: {cmd1}")
print(f"   URL contains seq-1: {'seq-1' in cmd1}")

# PUT 1 - Pass payload as JSON string
print("\n1b. PUT seq-1 (JSON string payload)")
payload1_str = json.dumps({"nfInstanceId": "seq-1", "nfType": "SMF"})
cmd1b, resolved1b = build_curl_command(
    base_url, "PUT", payload=payload1_str, test_context=test_context
)
print(f"   Resolved payload: {resolved1b}")
print(f"   Command: {cmd1b}")
print(f"   URL contains seq-1: {'seq-1' in cmd1b}")

# Clear sessions for clean test
sequence_manager._session_managers.clear()

print("\n🔄 Fresh test with JSON string payloads:")

# PUT 1
print("\n1. PUT seq-1")
payload1 = json.dumps({"nfInstanceId": "seq-1", "nfType": "SMF"})
cmd1, _ = build_curl_command(
    base_url, "PUT", payload=payload1, test_context=test_context
)
seq1_result = f"{base_url}seq-1" in cmd1
print(f"   URL modified: {seq1_result}")
print(f"   Command: {cmd1}")

# GET 1
print("\n2. GET (should get seq-1)")
cmd2, _ = build_curl_command(base_url, "GET", test_context=test_context)
seq1_get_result = f"{base_url}seq-1" in cmd2
print(f"   URL has seq-1: {seq1_get_result}")
print(f"   Command: {cmd2}")

# Clean up
try:
    os.remove("config/hosts.json")
    os.rmdir("config")
except:
    pass
