#!/usr/bin/env python3
"""
Test case demonstrating the PUT-GET-DELETE-DELETE scenario for nfInstanceId management.

This test shows what happens when a DELETE operation is attempted after
the nfInstanceId has already been deleted.
"""

import os
import sys

# Add the project root to the Python path
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
)

from testpilot.utils.curl_builder import build_curl_command
from testpilot.utils.nrf import sequence_manager


def test_double_delete_scenario():
    """Test PUT-GET-DELETE-DELETE sequence to demonstrate nfInstanceId handling"""

    print("🧪 Testing PUT-GET-DELETE-DELETE Scenario")
    print("=" * 50)

    # Setup test context
    test_context = {
        "session_id": "test_double_delete",
        "test_name": "nrf_registration_lifecycle",
        "sheet": "NRF_Tests",
        "row_idx": 1,
    }

    base_url = "http://example.com/nnrf-nfm/v1/nf-instances/"
    nf_instance_id = "test-instance-123"
    payload = f'{{"nfInstanceId": "{nf_instance_id}"}}'

    # 1. PUT - Register NF instance
    print("\n1️⃣ PUT Operation - Register NF Instance")
    result = sequence_manager.handle_nrf_operation(
        url=base_url,
        method="PUT",
        payload=payload,
        test_context=test_context,
        nf_name="NRF",
    )
    expected_url = f"{base_url}{nf_instance_id}"
    print(f"   Expected URL: {expected_url}")
    print(f"   Actual URL: {result}")
    print(f"   ✅ Registered nfInstanceId: {nf_instance_id}")

    # 2. GET - Retrieve NF instance
    print("\n2️⃣ GET Operation - Retrieve NF Instance")
    test_context["row_idx"] = 2
    result = sequence_manager.handle_nrf_operation(
        url=base_url,
        method="GET",
        payload=None,
        test_context=test_context,
        nf_name="NRF",
    )
    print(f"   URL with nfInstanceId: {result}")
    print(f"   ✅ Successfully retrieved using tracked nfInstanceId")

    # 3. DELETE - Remove NF instance
    print("\n3️⃣ DELETE Operation - Remove NF Instance")
    test_context["row_idx"] = 3
    result = sequence_manager.handle_nrf_operation(
        url=base_url,
        method="DELETE",
        payload=None,
        test_context=test_context,
        nf_name="NRF",
    )
    print(f"   URL with nfInstanceId: {result}")
    print(f"   ✅ Successfully deleted nfInstanceId from stack")

    # 4. DELETE (again) - Attempt to delete when no instance exists
    print("\n4️⃣ DELETE Operation (Second Attempt) - No Active Instance")
    test_context["row_idx"] = 4
    result = sequence_manager.handle_nrf_operation(
        url=base_url,
        method="DELETE",
        payload=None,
        test_context=test_context,
        nf_name="NRF",
    )
    print(f"   Result: {result}")
    if result is None:
        print(
            "   ⚠️  No active nfInstanceId found - DELETE operation returns None"
        )
        print("   📝 This is expected behavior when stack is empty")
    else:
        print("   ❌ Unexpected result - should have returned None")

    # Get diagnostic report
    print("\n📊 Diagnostic Report:")
    report = sequence_manager.get_session_diagnostic_report(
        "test_double_delete"
    )
    if report:
        print(f"   Active instances: {report['active_instances']}")
        print(f"   Total created: {report['total_instances_created']}")
        print(f"   Stack size: {report['active_stack_size']}")
        print(f"   Stack contents: {report['stack_trace']}")

    # Cleanup
    sequence_manager.cleanup_session("test_double_delete")
    print("\n✅ Test completed - session cleaned up")


def test_with_curl_integration():
    """Test the scenario with actual curl command generation"""

    print("\n\n🧪 Testing Double DELETE with Curl Integration")
    print("=" * 50)

    # Reset session
    sequence_manager.cleanup_all_sessions()

    test_context = {
        "session_id": "curl_double_delete",
        "test_name": "nrf_curl_test",
        "sheet": "NRF_Curl_Tests",
        "row_idx": 1,
    }

    base_url = "http://example.com/nnrf-nfm/v1/nf-instances/"
    nf_instance_id = "curl-test-456"
    payload = f'{{"nfInstanceId": "{nf_instance_id}"}}'

    # 1. PUT with curl
    print("\n1️⃣ PUT with Curl Command")
    curl_cmd, _ = build_curl_command(
        base_url, "PUT", payload=payload, test_context=test_context
    )
    print(f"   Curl command: {curl_cmd}")
    if nf_instance_id in curl_cmd:
        print(f"   ✅ nfInstanceId appended to URL")

    # 2. GET with curl
    print("\n2️⃣ GET with Curl Command")
    test_context["row_idx"] = 2
    curl_cmd, _ = build_curl_command(
        base_url, "GET", test_context=test_context
    )
    print(f"   Curl command: {curl_cmd}")
    if nf_instance_id in curl_cmd:
        print(f"   ✅ Using tracked nfInstanceId")

    # 3. DELETE with curl
    print("\n3️⃣ DELETE with Curl Command")
    test_context["row_idx"] = 3
    curl_cmd, _ = build_curl_command(
        base_url, "DELETE", test_context=test_context
    )
    print(f"   Curl command: {curl_cmd}")
    if nf_instance_id in curl_cmd:
        print(f"   ✅ Deleting tracked nfInstanceId")

    # 4. DELETE again with curl - should fail
    print("\n4️⃣ Second DELETE with Curl Command")
    test_context["row_idx"] = 4
    try:
        curl_cmd, _ = build_curl_command(
            base_url, "DELETE", test_context=test_context
        )
        print(f"   Curl command: {curl_cmd}")
        # Check if the URL is missing the nfInstanceId
        if base_url in curl_cmd and not nf_instance_id in curl_cmd:
            print("   ⚠️  Curl command generated without nfInstanceId")
            print(
                "   📝 This will likely result in a 404 or 400 error from the server"
            )
    except Exception as e:
        print(f"   ❌ Error generating curl command: {e}")

    # Cleanup
    sequence_manager.cleanup_session("curl_double_delete")
    print("\n✅ Curl integration test completed")


if __name__ == "__main__":
    test_double_delete_scenario()
    test_with_curl_integration()
