#!/usr/bin/env python3
"""
Test script to verify curl_builder NRF integration
"""

import json
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

try:
    from testpilot.utils.curl_builder import build_curl_command

    print("✅ curl_builder imports successfully")

    # Test with NRF configuration
    print("\n🧪 Test 1: NRF Integration with test_context")

    # Create a test hosts.json for NRF
    config_dir = "config"
    os.makedirs(config_dir, exist_ok=True)

    nrf_config = {
        "use_ssh": False,
        "pod_mode": False,
        "nf_name": "NRF",  # Set to NRF to trigger NRF handling
        "connect_to": "tailgate",
        "hosts": [
            {
                "name": "tailgate",
                "hostname": "10.75.184.84",
                "username": "aziz.tejani",
                "namespace": "ocnrf",
            }
        ],
    }

    with open("config/hosts.json", "w") as f:
        json.dump(nrf_config, f, indent=2)

    # Test context
    test_context = {
        "test_name": "test_5_1_6_SMF_Registration",
        "sheet": "NRFRegistration",
        "row_idx": 21,
        "session_id": "curl_test_session",
    }

    # Test payload with nfInstanceId
    nf_id = "6faf1bbc-6e4a-4454-a507-a14ef8e1bc5a"
    payload = {
        "nfInstanceId": nf_id,
        "nfType": "SMF",
        "nfStatus": "REGISTERED",
    }

    base_url = "http://nrf:8081/nnrf-nfm/v1/nf-instances/"

    # Test PUT operation
    curl_cmd, resolved_payload = build_curl_command(
        url=base_url, method="PUT", payload=payload, test_context=test_context
    )

    # Should contain the nfInstanceId in URL
    expected_url = f"{base_url}{nf_id}"
    assert expected_url in curl_cmd
    print("  ✅ PUT operation: URL modified with nfInstanceId")
    print(f"    Generated command contains: {expected_url}")

    # Test GET operation (should use tracked instance)
    curl_cmd_get, _ = build_curl_command(
        url=base_url, method="GET", test_context=test_context
    )

    # Should still use the same nfInstanceId
    assert expected_url in curl_cmd_get
    print("  ✅ GET operation: Uses tracked nfInstanceId")

    # Test DELETE operation
    curl_cmd_delete, _ = build_curl_command(
        url=base_url, method="DELETE", test_context=test_context
    )

    # Should use the same nfInstanceId and remove from tracking
    assert expected_url in curl_cmd_delete
    print("  ✅ DELETE operation: Uses tracked nfInstanceId")

    print("\n🧪 Test 2: Non-NRF should not be affected")

    # Change config to SLF (non-NRF)
    slf_config = nrf_config.copy()
    slf_config["nf_name"] = "SLF"

    with open("config/hosts.json", "w") as f:
        json.dump(slf_config, f, indent=2)

    # SLF request should not modify URL
    curl_cmd_slf, _ = build_curl_command(
        url="http://slf:8080/api/test",
        method="PUT",
        payload=payload,  # Same payload but should be ignored
        test_context=test_context,
    )

    # Should NOT contain nfInstanceId in URL (only in payload)
    assert "slf:8080/api/test" in curl_cmd_slf
    # Check that URL wasn't modified (nfInstanceId not appended to URL)
    assert f"slf:8080/api/test{nf_id}" not in curl_cmd_slf
    print("  ✅ SLF (non-NRF) operations unchanged")

    print("\n🧪 Test 3: Backward compatibility (no test_context)")

    # Restore NRF config
    with open("config/hosts.json", "w") as f:
        json.dump(nrf_config, f, indent=2)

    # Call without test_context (should use legacy behavior)
    curl_cmd_legacy, _ = build_curl_command(
        url=base_url,
        method="PUT",
        payload=payload,
        test_context=None,  # No context - should use legacy
    )

    # Should still work (legacy behavior)
    assert expected_url in curl_cmd_legacy
    print("  ✅ Legacy behavior (no test_context) works")

    print("\n🧪 Test 4: Complex sequence through curl_builder")

    # Clear previous state
    from testpilot.utils.nrf import sequence_manager

    sequence_manager._session_managers.clear()

    # Test the full PUT-GET-PUT-GET-DELETE-PUT sequence
    sequence_results = []

    # PUT 1
    cmd1, _ = build_curl_command(
        base_url,
        "PUT",
        payload={"nfInstanceId": "seq-1"},
        test_context=test_context,
    )
    sequence_results.append(f"{base_url}seq-1" in cmd1)

    # GET 1
    cmd2, _ = build_curl_command(base_url, "GET", test_context=test_context)
    sequence_results.append(f"{base_url}seq-1" in cmd2)

    # PUT 2
    cmd3, _ = build_curl_command(
        base_url,
        "PUT",
        payload={"nfInstanceId": "seq-2"},
        test_context=test_context,
    )
    sequence_results.append(f"{base_url}seq-2" in cmd3)

    # GET 2 (should get most recent)
    cmd4, _ = build_curl_command(base_url, "GET", test_context=test_context)
    sequence_results.append(f"{base_url}seq-2" in cmd4)

    # DELETE 2
    cmd5, _ = build_curl_command(base_url, "DELETE", test_context=test_context)
    sequence_results.append(f"{base_url}seq-2" in cmd5)

    # PUT 3
    cmd6, _ = build_curl_command(
        base_url,
        "PUT",
        payload={"nfInstanceId": "seq-3"},
        test_context=test_context,
    )
    sequence_results.append(f"{base_url}seq-3" in cmd6)

    assert all(sequence_results), f"Sequence test failed: {sequence_results}"
    print("  ✅ Complex sequence through curl_builder works correctly")

    # Cleanup
    os.remove("config/hosts.json")

    print("\n🎉 All curl_builder integration tests passed!")

except Exception as e:
    print(f"❌ Test failed: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)
