#!/usr/bin/env python3
"""
Test script to debug pattern matching issue with JSON output
"""

import json
import logging
import os
import sys

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
from src.testpilot.core.enhanced_response_validator import (
    validate_response_enhanced,
)

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def test_pattern_matching():
    # Your actual JSON output
    json_output = '[{"svcName":"rcnltxekvzwcslf-y-or-x-107-nudr-drservice","metricsThresholdList":[{"metricsName":"svc_failure_count","levelThresholdList":[{"level":"L1","onsetValue":13000,"abatementValue":12500},{"level":"L2","onsetValue":14000,"abatementValue":13500},{"level":"L3","onsetValue":15000,"abatementValue":14500},{"level":"L4","onsetValue":16000,"abatementValue":15500}]},{"metricsName":"memory","levelThresholdList":[{"level":"L1","onsetValue":50,"abatementValue":45},{"level":"L2","onsetValue":70,"abatementValue":65},{"level":"L3","onsetValue":85,"abatementValue":82},{"level":"L4","onsetValue":90,"abatementValue":88}]},{"metricsName":"cpu","levelThresholdList":[{"level":"L1","onsetValue":65,"abatementValue":60},{"level":"L2","onsetValue":75,"abatementValue":70},{"level":"L3","onsetValue":80,"abatementValue":75},{"level":"L4","onsetValue":90,"abatementValue":85}]},{"metricsName":"svc_pending_count","levelThresholdList":[{"level":"L1","onsetValue":13000,"abatementValue":12500},{"level":"L2","onsetValue":14000,"abatementValue":13500},{"level":"L3","onsetValue":15000,"abatementValue":14500},{"level":"L4","onsetValue":16000,"abatementValue":15500}]}]}]'

    # Your pattern to match
    pattern_match = '"svcName":"rcnltxekvzwcslf-y-or-x-107-nudr-drservice"'

    print("🧪 Testing Pattern Matching")
    print(f"Pattern: {pattern_match}")
    print(f"JSON Output Length: {len(json_output)}")

    # Parse the JSON
    try:
        parsed_json = json.loads(json_output)
        print(f"✅ JSON parsed successfully")
        print(f"JSON Structure: {type(parsed_json)}")
        if isinstance(parsed_json, list):
            print(f"List length: {len(parsed_json)}")
            if len(parsed_json) > 0:
                print(f"First item type: {type(parsed_json[0])}")
                if isinstance(parsed_json[0], dict):
                    print(f"First item keys: {list(parsed_json[0].keys())}")
    except Exception as e:
        print(f"❌ JSON parsing failed: {e}")
        parsed_json = json_output

    # Test 1: Basic substring search
    print("\n🔍 Test 1: Basic substring search")
    found_in_string = pattern_match in json_output
    print(f"Pattern found in raw string: {found_in_string}")

    # Test 2: Search in parsed JSON string
    print("\n🔍 Test 2: Search in stringified parsed JSON")
    if isinstance(parsed_json, (dict, list)):
        json_str = json.dumps(parsed_json)
        found_in_parsed = pattern_match in json_str
        print(f"Pattern found in re-stringified JSON: {found_in_parsed}")

        # Check different JSON formatting
        compact_json = json.dumps(parsed_json, separators=(",", ":"))
        found_in_compact = pattern_match in compact_json
        print(f"Pattern found in compact JSON: {found_in_compact}")

        pretty_json = json.dumps(parsed_json, indent=2)
        found_in_pretty = pattern_match in pretty_json
        print(f"Pattern found in pretty JSON: {found_in_pretty}")

    # Test 3: Enhanced validator
    print("\n🔍 Test 3: Enhanced response validator")
    result = validate_response_enhanced(
        pattern_match=pattern_match,
        response_headers={},
        response_body=json_output,
        response_payload=json_output,
        logger=logger,
        config=None,
        args=None,
        sheet_name="test",
        row_idx=1,
    )

    print(f"Validation result: {result}")

    # Test 4: Individual pattern matching approaches
    print("\n🔍 Test 4: Manual pattern matching tests")

    # Test key-value approach
    if ":" in pattern_match:
        key, val = pattern_match.split(":", 1)
        key = key.strip().strip('"')
        val = val.strip().strip('"')
        print(f"Key-value approach: key='{key}', value='{val}'")

        if isinstance(parsed_json, list) and len(parsed_json) > 0:
            first_item = parsed_json[0]
            if isinstance(first_item, dict):
                key_exists = key in first_item
                value_matches = (
                    first_item.get(key) == val if key_exists else False
                )
                print(f"Key exists: {key_exists}")
                print(f"Value matches: {value_matches}")
                if key_exists:
                    print(f"Actual value: '{first_item[key]}'")

    # Test different pattern variations
    print("\n🔍 Test 5: Pattern variations")
    variations = [
        '"svcName":"rcnltxekvzwcslf-y-or-x-107-nudr-drservice"',
        'svcName":"rcnltxekvzwcslf-y-or-x-107-nudr-drservice',
        'svcName":"rcnltxekvzwcslf-y-or-x-107-nudr-drservice"',
        "rcnltxekvzwcslf-y-or-x-107-nudr-drservice",
        '"svcName": "rcnltxekvzwcslf-y-or-x-107-nudr-drservice"',
    ]

    for i, var in enumerate(variations):
        found = var in json_output
        print(f"Variation {i+1} '{var}': {found}")


def test_nrf_nf_instances_pattern():
    """Test pattern matching for NRF nf-instances with UUID pattern"""

    # NRF nf-instances JSON output with multiple href links
    nrf_json_output = '{"_links":{"item":[{"href":"http://nnrf-106.rcnltxek.rcn.nnrf.5gc.vzimstest.com:8081/nnrf-nfm/v1/nf-instances/ffb56d18-dc94-5bc0-aa71-751afcd6584f"},{"href":"http://nnrf-106.rcnltxek.rcn.nnrf.5gc.vzimstest.com:8081/nnrf-nfm/v1/nf-instances/e900932c-9048-45e8-badb-ea0239e4baec"},{"href":"http://nnrf-106.rcnltxek.rcn.nnrf.5gc.vzimstest.com:8081/nnrf-nfm/v1/nf-instances/e7f7d7a4-3279-42ed-9255-059684b1e8b6"},{"href":"http://nnrf-106.rcnltxek.rcn.nnrf.5gc.vzimstest.com:8081/nnrf-nfm/v1/nf-instances/e74dbc33-175c-5f23-9093-4d851429913a"},{"href":"http://nnrf-106.rcnltxek.rcn.nnrf.5gc.vzimstest.com:8081/nnrf-nfm/v1/nf-instances/e4f9d82a-ee7d-5d55-8524-9690c89f1bed"},{"href":"http://nnrf-106.rcnltxek.rcn.nnrf.5gc.vzimstest.com:8081/nnrf-nfm/v1/nf-instances/dc72c25c-a312-594f-b15e-a215cc53b50f"},{"href":"http://nnrf-106.rcnltxek.rcn.nnrf.5gc.vzimstest.com:8081/nnrf-nfm/v1/nf-instances/dc72c25c-a312-594f-b15e-a215cc53b50e"},{"href":"http://nnrf-106.rcnltxek.rcn.nnrf.5gc.vzimstest.com:8081/nnrf-nfm/v1/nf-instances/dbf2d4dd-5b3e-439c-8891-5807d095631c"},{"href":"http://nnrf-106.rcnltxek.rcn.nnrf.5gc.vzimstest.com:8081/nnrf-nfm/v1/nf-instances/da1327c0-7f71-4376-8e56-97efce7fcb06"},{"href":"http://nnrf-106.rcnltxek.rcn.nnrf.5gc.vzimstest.com:8081/nnrf-nfm/v1/nf-instances/bdc7b815-aeb5-44d0-a908-8b76d1c7d0c4"},{"href":"http://nnrf-106.rcnltxek.rcn.nnrf.5gc.vzimstest.com:8081/nnrf-nfm/v1/nf-instances/b83d8306-a0f5-4b50-98c6-aa40ee62d5f2"},{"href":"http://nnrf-106.rcnltxek.rcn.nnrf.5gc.vzimstest.com:8081/nnrf-nfm/v1/nf-instances/b085e15e-1b97-52e7-824d-ad970687b085"},{"href":"http://nnrf-106.rcnltxek.rcn.nnrf.5gc.vzimstest.com:8081/nnrf-nfm/v1/nf-instances/a840e072-409e-50e0-9bd9-f22739f3945f"},{"href":"http://nnrf-106.rcnltxek.rcn.nnrf.5gc.vzimstest.com:8081/nnrf-nfm/v1/nf-instances/a3dd1958-a50c-494e-90db-1bc597fcd013"},{"href":"http://nnrf-106.rcnltxek.rcn.nnrf.5gc.vzimstest.com:8081/nnrf-nfm/v1/nf-instances/a2745afe-57b1-527e-b7c8-a0ad92cbd672"},{"href":"http://nnrf-106.rcnltxek.rcn.nnrf.5gc.vzimstest.com:8081/nnrf-nfm/v1/nf-instances/94954fc3-7a33-4b3a-a52f-d316f4dbc098"},{"href":"http://nnrf-106.rcnltxek.rcn.nnrf.5gc.vzimstest.com:8081/nnrf-nfm/v1/nf-instances/91c9514d-e083-4dd6-a916-361abba1e3f9"},{"href":"http://nnrf-106.rcnltxek.rcn.nnrf.5gc.vzimstest.com:8081/nnrf-nfm/v1/nf-instances/85fd0144-7a9e-5d9d-b571-a4acf35f5514"},{"href":"http://nnrf-106.rcnltxek.rcn.nnrf.5gc.vzimstest.com:8081/nnrf-nfm/v1/nf-instances/801925c0-fb45-4309-8e42-9d41cd5fb907"},{"href":"http://nnrf-106.rcnltxek.rcn.nnrf.5gc.vzimstest.com:8081/nnrf-nfm/v1/nf-instances/69bec5b9-c0f5-4435-b624-609465de0ada"},{"href":"http://nnrf-106.rcnltxek.rcn.nnrf.5gc.vzimstest.com:8081/nnrf-nfm/v1/nf-instances/5cc3c865-5aca-538b-84aa-357bc210166d"},{"href":"http://nnrf-106.rcnltxek.rcn.nnrf.5gc.vzimstest.com:8081/nnrf-nfm/v1/nf-instances/453045f8-50b4-59bf-9227-ad16f6a86b74"},{"href":"http://nnrf-106.rcnltxek.rcn.nnrf.5gc.vzimstest.com:8081/nnrf-nfm/v1/nf-instances/41360975-3c10-42d6-9013-778bc46a58eb"},{"href":"http://nnrf-106.rcnltxek.rcn.nnrf.5gc.vzimstest.com:8081/nnrf-nfm/v1/nf-instances/40933c0a-138e-4459-a890-1c3897b5721d"},{"href":"http://nnrf-106.rcnltxek.rcn.nnrf.5gc.vzimstest.com:8081/nnrf-nfm/v1/nf-instances/3ba6fb48-829b-4379-a0d1-1271f463ec25"},{"href":"http://nnrf-106.rcnltxek.rcn.nnrf.5gc.vzimstest.com:8081/nnrf-nfm/v1/nf-instances/3938e4fd-e5a2-5dcb-be42-ede0ab84e008"},{"href":"http://nnrf-106.rcnltxek.rcn.nnrf.5gc.vzimstest.com:8081/nnrf-nfm/v1/nf-instances/32fad504-d5b1-5506-8690-b1ed099a80cf"},{"href":"http://nnrf-106.rcnltxek.rcn.nnrf.5gc.vzimstest.com:8081/nnrf-nfm/v1/nf-instances/04af1130-b21e-4611-bdd5-e4bbcc453e2b"},{"href":"http://nnrf-106.rcnltxek.rcn.nnrf.5gc.vzimstest.com:8081/nnrf-nfm/v1/nf-instances/0119292c-b593-4093-8153-a7157553804b"}],"self":{"href":"http://nnrf-106.rcnltxek.rcn.nnrf.5gc.vzimstest.com:8081/nnrf-nfm/v1/nf-instances"}}}'

    # Pattern to match - looking for specific UUID in the href links
    pattern_match = "0119292c-b593-4093-8153-a7157553804b"

    print("\n" + "=" * 60)
    print("🧪 Testing NRF nf-instances Pattern Matching")
    print(f"Pattern: {pattern_match}")
    print(f"JSON Output Length: {len(nrf_json_output)}")

    # Parse the JSON
    try:
        parsed_json = json.loads(nrf_json_output)
        print(f"✅ JSON parsed successfully")
        print(f"JSON Structure: {type(parsed_json)}")
        if isinstance(parsed_json, dict) and "_links" in parsed_json:
            items = parsed_json.get("_links", {}).get("item", [])
            print(f"Number of nf-instance items: {len(items)}")
    except Exception as e:
        print(f"❌ JSON parsing failed: {e}")
        parsed_json = nrf_json_output

    # Test 1: Basic substring search
    print("\n🔍 Test 1: Basic substring search")
    found_in_string = pattern_match in nrf_json_output
    print(f"UUID pattern found in raw string: {found_in_string}")

    # Test 2: Enhanced validator
    print("\n🔍 Test 2: Enhanced response validator")
    result = validate_response_enhanced(
        pattern_match=pattern_match,
        response_headers={},
        response_body=nrf_json_output,
        response_payload=None,
        logger=logger,
        config=None,
        args=None,
        sheet_name="NRF_test",
        row_idx=1,
    )

    print(f"Validation result: {result}")
    print(f"Summary: {result['summary']}")

    # Test 3: Check all pattern matching methods
    print("\n🔍 Test 3: Pattern matching method breakdown")
    if "pattern_matches" in result:
        for match_info in result["pattern_matches"]:
            print(
                f"  {match_info['type']}: {match_info['result']} - {match_info['details']}"
            )

    # Test 4: Verify the UUID is in the last href entry
    print("\n🔍 Test 4: Verify UUID location in JSON structure")
    if isinstance(parsed_json, dict):
        items = parsed_json.get("_links", {}).get("item", [])
        if items:
            last_item = items[-1]  # Should be the one with our UUID
            if "href" in last_item:
                href_url = last_item["href"]
                uuid_in_href = pattern_match in href_url
                print(f"UUID found in last href: {uuid_in_href}")
                print(f"Last href: {href_url}")

    return result


def test_profile_data_array_order():
    """Test profile-data with array order sensitivity issue"""

    print("\n" + "=" * 60)
    print("🧪 Testing Profile-Data Array Order Validation")

    # Expected response
    expected_response = '{"profile-data":{"accountID":["12345678912345678912345678"],"imsi":["302720603949999"],"msisdn":["19195229999"]},"slfGroupName":"IMSGrp1"}'

    # Actual response - same content but potentially different order
    actual_response = '{"profile-data":{"accountID":["12345678912345678912345678"],"imsi":["302720603949999"],"msisdn":["19195229999"]},"slfGroupName":"IMSGrp1"}'

    print(f"Expected: {expected_response}")
    print(f"Actual: {actual_response}")

    # Test 1: Exact match
    print("\n🔍 Test 1: Exact match validation")
    result1 = validate_response_enhanced(
        pattern_match=None,
        response_headers={},
        response_body=actual_response,
        response_payload=expected_response,
        logger=logger,
        config=None,
        args=None,
        sheet_name="ProfileDataTest",
        row_idx=1,
    )

    print(f"Result: {result1['summary']}")
    print(f"Dict Match: {result1['dict_match']}")

    # Test 2: Pattern matching for specific values
    print("\n🔍 Test 2: Pattern matching for accountID")
    result2 = validate_response_enhanced(
        pattern_match="12345678912345678912345678",
        response_headers={},
        response_body=actual_response,
        response_payload=None,
        logger=logger,
        config=None,
        args=None,
        sheet_name="ProfileDataTest",
        row_idx=2,
    )

    print(f"Result: {result2['summary']}")
    print(f"Pattern Found: {result2['pattern_match_overall']}")

    # Test 3: Array order sensitivity simulation
    # Simulate different order scenario (for arrays with multiple items)
    expected_multi = '{"profile-data":{"accountID":["12345678912345678912345678","98765432198765432198765432"],"imsi":["302720603949999","302720603948888"],"msisdn":["19195229999","19195228888"]},"slfGroupName":"IMSGrp1"}'
    actual_multi_diff_order = '{"profile-data":{"accountID":["98765432198765432198765432","12345678912345678912345678"],"imsi":["302720603948888","302720603949999"],"msisdn":["19195228888","19195229999"]},"slfGroupName":"IMSGrp1"}'

    print(
        "\n🔍 Test 3: Array order sensitivity (multiple items, different order)"
    )
    print("Expected arrays: [A, B] vs Actual arrays: [B, A]")

    result3 = validate_response_enhanced(
        pattern_match=None,
        response_headers={},
        response_body=actual_multi_diff_order,
        response_payload=expected_multi,
        logger=logger,
        config=None,
        args=None,
        sheet_name="ProfileDataTest",
        row_idx=3,
    )

    print(f"Result: {result3['summary']}")
    print(f"Dict Match: {result3['dict_match']}")

    if result3["dict_match"] is False:
        print("⚠️ ORDER SENSITIVITY ISSUE DETECTED!")
        print(
            "   Arrays with same elements but different order are failing validation"
        )
        print("   This confirms the issue you described")

    return result3


if __name__ == "__main__":
    # Run original test
    test_pattern_matching()

    # Run new NRF nf-instances test
    test_nrf_nf_instances_pattern()

    # Run profile data array order test
    test_profile_data_array_order()
