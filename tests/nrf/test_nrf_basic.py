#!/usr/bin/env python3
"""
Basic test script to verify NRF implementation works
"""

import json
import os
import sys

# Add src to path so we can import testpilot modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

try:
    from testpilot.utils.nrf.instance_tracker import (
        CleanupPolicy,
        NRFInstanceTracker,
    )
    from testpilot.utils.nrf.sequence_manager import (
        get_global_diagnostic_report,
        handle_nrf_operation,
    )

    print("✅ NRF modules import successfully")

    # Test 1: Basic instance tracker functionality
    print("\n🧪 Test 1: Basic Instance Tracker")
    tracker = NRFInstanceTracker()

    test_context = {
        "test_name": "test_5_1_6_SMF_Registration",
        "sheet": "NRFRegistration",
        "row_idx": 21,
        "session_id": "test_session",
    }

    nf_id = "6faf1bbc-6e4a-4454-a507-a14ef8e1bc5a"

    # Test PUT operation
    tracker.handle_put_operation(test_context, nf_id)
    assert len(tracker.active_stack) == 1
    assert tracker.active_stack[0] == nf_id
    print("  ✅ PUT operation creates and tracks instance")

    # Test GET operation
    retrieved_id = tracker.get_active_instance_id(test_context)
    assert retrieved_id == nf_id
    print("  ✅ GET operation retrieves correct instance")

    # Test DELETE operation
    deleted_id = tracker.handle_delete_operation(test_context)
    assert deleted_id == nf_id
    assert len(tracker.active_stack) == 0
    print("  ✅ DELETE operation removes instance from stack")

    # Test 2: Sequence manager functionality
    print("\n🧪 Test 2: Sequence Manager")

    payload = json.dumps(
        {"nfInstanceId": nf_id, "nfType": "SMF", "nfStatus": "REGISTERED"}
    )

    base_url = "http://nrf:8081/nnrf-nfm/v1/nf-instances/"

    # Test PUT
    result = handle_nrf_operation(
        url=base_url,
        method="PUT",
        payload=payload,
        test_context=test_context,
        nf_name="NRF",
    )
    expected_url = f"{base_url}{nf_id}"
    assert result == expected_url
    print("  ✅ PUT operation returns URL with nfInstanceId")

    # Test GET
    result = handle_nrf_operation(
        url=base_url,
        method="GET",
        payload=None,
        test_context=test_context,
        nf_name="NRF",
    )
    assert result == expected_url
    print("  ✅ GET operation uses tracked instance")

    # Test DELETE
    result = handle_nrf_operation(
        url=base_url,
        method="DELETE",
        payload=None,
        test_context=test_context,
        nf_name="NRF",
    )
    assert result == expected_url
    print("  ✅ DELETE operation removes tracked instance")

    # Test 3: Complex sequence (PUT-GET-PUT-GET-DELETE-PUT)
    print("\n🧪 Test 3: Complex Sequence")

    # Reset for clean test
    from testpilot.utils.nrf import sequence_manager

    sequence_manager._session_managers.clear()

    # PUT 1
    payload1 = json.dumps({"nfInstanceId": "id-1"})
    result1 = handle_nrf_operation(
        base_url, "PUT", payload1, test_context, "NRF"
    )
    assert result1 == f"{base_url}id-1"

    # GET 1
    result2 = handle_nrf_operation(base_url, "GET", None, test_context, "NRF")
    assert result2 == f"{base_url}id-1"

    # PUT 2
    payload2 = json.dumps({"nfInstanceId": "id-2"})
    result3 = handle_nrf_operation(
        base_url, "PUT", payload2, test_context, "NRF"
    )
    assert result3 == f"{base_url}id-2"

    # GET 2 (should get most recent from same test)
    result4 = handle_nrf_operation(base_url, "GET", None, test_context, "NRF")
    assert result4 == f"{base_url}id-2"

    # DELETE 2
    result5 = handle_nrf_operation(
        base_url, "DELETE", None, test_context, "NRF"
    )
    assert result5 == f"{base_url}id-2"

    # PUT 3
    payload3 = json.dumps({"nfInstanceId": "id-3"})
    result6 = handle_nrf_operation(
        base_url, "PUT", payload3, test_context, "NRF"
    )
    assert result6 == f"{base_url}id-3"

    print("  ✅ Complex sequence (PUT-GET-PUT-GET-DELETE-PUT) works correctly")

    # Test 4: Diagnostic reporting
    print("\n🧪 Test 4: Diagnostic Reporting")

    report = get_global_diagnostic_report()
    assert report["total_sessions"] == 1
    assert "test_session" in report["sessions"]
    print("  ✅ Diagnostic reporting works")

    print("\n🎉 All tests passed! NRF implementation is working correctly.")

    # Show final diagnostic report
    print("\n📊 Final Diagnostic Report:")
    session_report = report["sessions"]["test_session"]
    print(f"  Active instances: {session_report['active_instances']}")
    print(f"  Total created: {session_report['total_instances_created']}")
    print(f"  Active stack: {session_report.get('stack_trace', 'N/A')}")

except ImportError as e:
    print(f"❌ Import error: {e}")
    raise
except AssertionError as e:
    print(f"❌ Test failed: {e}")
    raise
except Exception as e:
    print(f"❌ Unexpected error: {e}")
    raise
