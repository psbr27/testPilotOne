#!/usr/bin/env python3
"""Debug script to test mock server response loading logic."""

import json
import re
from typing import Dict
from urllib.parse import urlparse


def extract_request_info(command: str):
    """Extract endpoint, method, and payload from kubectl exec curl command."""
    if not command or "curl" not in command:
        return None, None, None

    try:
        # Extract method (default GET)
        method_match = re.search(r"-X\s+(\w+)", command)
        method = method_match.group(1) if method_match else "GET"

        # Extract URL (stop at quotes or whitespace)
        url_match = re.search(r"http://[^\s'\"]+", command)
        if not url_match:
            return None, None, None

        full_url = url_match.group(0)
        parsed_url = urlparse(full_url)

        # Clean up endpoint path
        endpoint = parsed_url.path.strip("/")
        if parsed_url.query:
            endpoint += f"?{parsed_url.query}"

        return endpoint, method, None

    except Exception as e:
        print(f"⚠️  Error parsing command: {e}")
        return None, None, None


def should_replace_response(existing: Dict, new_result: Dict) -> bool:
    """Determine if a new response should replace an existing one."""
    existing_sheet = existing.get("sheet", "")
    new_sheet = new_result.get("sheet", "")

    # Priority sheets should replace others
    priority_sheets = {"oAuthValidation-igw", "SLFGroups", "AutoCreateSubs"}

    if new_sheet in priority_sheets and existing_sheet not in priority_sheets:
        return True

    # Error sheets should not replace non-error sheets
    if (
        existing_sheet != "ErrorRespEnhancement"
        and new_sheet == "ErrorRespEnhancement"
    ):
        return False

    # PASS status should replace FAIL status
    if existing.get("status") == "FAIL" and new_result.get("status") == "PASS":
        return True

    return False


def debug_loading():
    """Debug the loading process for our problematic endpoint."""
    with open("mock_data/test_results_20250719_122220.json", "r") as f:
        data = json.load(f)

    real_responses = {}
    target_endpoint = "nudr-group-id-map/v1/nf-group-ids?subscriber-id=imsi-302720603940001&nf-type=UDM"
    target_key = f"GET:{target_endpoint}"

    print(f"🎯 Debugging loading for: {target_key}")
    print()

    # Process results as the server would
    results = data.get("results", [])

    # Sort to prioritize certain sheets
    priority_sheets = {"oAuthValidation-igw", "SLFGroups", "AutoCreateSubs"}

    sorted_results = sorted(
        results,
        key=lambda r: (
            r.get("sheet", "") not in priority_sheets,  # Priority sheets first
            r.get("sheet", "") == "ErrorRespEnhancement",  # Error sheets last
            r.get("status", "") == "FAIL",  # PASS status preferred over FAIL
        ),
    )

    loading_steps = []

    for i, result in enumerate(sorted_results):
        endpoint, method, payload = extract_request_info(
            result.get("command", "")
        )
        if endpoint and method:
            key = f"{method}:{endpoint}"

            if key == target_key:
                # This is our target endpoint
                step_info = {
                    "step": len(loading_steps) + 1,
                    "sheet": result.get("sheet"),
                    "test": result.get("test_name"),
                    "status": result.get("status"),
                    "output": result.get("output", "")[:100],
                    "action": "SKIP" if key in real_responses else "LOAD",
                }

                if key in real_responses:
                    # Check if we should replace
                    if should_replace_response(real_responses[key], result):
                        step_info["action"] = "REPLACE"
                        real_responses[key] = {
                            "output": result.get("output", ""),
                            "sheet": result.get("sheet", ""),
                            "test_name": result.get("test_name", ""),
                            "status": result.get("status", "PASS"),
                        }
                    else:
                        step_info["action"] = "SKIP"
                else:
                    # First time loading this key
                    real_responses[key] = {
                        "output": result.get("output", ""),
                        "sheet": result.get("sheet", ""),
                        "test_name": result.get("test_name", ""),
                        "status": result.get("status", "PASS"),
                    }

                loading_steps.append(step_info)

    print("📊 Loading sequence for target endpoint:")
    for step in loading_steps:
        action_icon = (
            "✅"
            if step["action"] == "LOAD"
            else "🔄" if step["action"] == "REPLACE" else "⏭️"
        )
        print(f"{action_icon} Step {step['step']}: {step['action']}")
        print(
            f"   Sheet: {step['sheet']} | Test: {step['test']} | Status: {step['status']}"
        )
        print(f"   Output: {step['output']}...")
        print()

    if target_key in real_responses:
        final = real_responses[target_key]
        print("🏆 FINAL RESULT:")
        print(
            f"   Sheet: {final['sheet']} | Test: {final['test_name']} | Status: {final['status']}"
        )
        print(f"   Output: {final['output']}")
    else:
        print("❌ Target key not found in final responses!")


if __name__ == "__main__":
    debug_loading()
