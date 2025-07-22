#!/usr/bin/env python3
"""
Debug the sequence test issue
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

print("🔍 Debug: Complex sequence test")

# PUT 1
print("\n1. PUT seq-1")
payload1 = {"nfInstanceId": "seq-1"}
cmd1, _ = build_curl_command(
    base_url, "PUT", payload=payload1, test_context=test_context
)
print(f"   Command: {cmd1}")
print(f"   Contains seq-1: {'seq-1' in cmd1}")

# GET 1
print("\n2. GET (should get seq-1)")
cmd2, _ = build_curl_command(base_url, "GET", test_context=test_context)
print(f"   Command: {cmd2}")
print(f"   Contains seq-1: {'seq-1' in cmd2}")

# PUT 2
print("\n3. PUT seq-2")
payload2 = {"nfInstanceId": "seq-2"}
cmd3, _ = build_curl_command(
    base_url, "PUT", payload=payload2, test_context=test_context
)
print(f"   Command: {cmd3}")
print(f"   Contains seq-2: {'seq-2' in cmd3}")

# GET 2 (should get most recent)
print("\n4. GET (should get seq-2)")
cmd4, _ = build_curl_command(base_url, "GET", test_context=test_context)
print(f"   Command: {cmd4}")
print(f"   Contains seq-2: {'seq-2' in cmd4}")

# DELETE 2
print("\n5. DELETE (should delete seq-2)")
cmd5, _ = build_curl_command(base_url, "DELETE", test_context=test_context)
print(f"   Command: {cmd5}")
print(f"   Contains seq-2: {'seq-2' in cmd5}")

# PUT 3
print("\n6. PUT seq-3")
payload3 = {"nfInstanceId": "seq-3"}
cmd6, _ = build_curl_command(
    base_url, "PUT", payload=payload3, test_context=test_context
)
print(f"   Command: {cmd6}")
print(f"   Contains seq-3: {'seq-3' in cmd6}")

# Check final state
from testpilot.utils.nrf.sequence_manager import get_global_diagnostic_report

report = get_global_diagnostic_report()
print(f"\n📊 Final state:")
print(
    f"   Active instances: {report['sessions']['sequence_session']['active_instances']}"
)
print(f"   Stack: {report['sessions']['sequence_session']['stack_trace']}")
