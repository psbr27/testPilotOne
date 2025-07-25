#!/usr/bin/env python3
"""
Audit Step Processor for TestPilot - Handles individual test step execution
with comprehensive audit validation and reporting.
"""

import json
import re
from typing import Any, Dict, List, Optional, Union

# Import pandas with fallback
try:
    import pandas as pd

    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

# Import dependencies with fallbacks
try:
    from ..core.test_pilot_core import (
        extract_step_data,
        manage_workflow_context,
    )

    CORE_AVAILABLE = True
except ImportError:
    CORE_AVAILABLE = False

    # Provide basic fallbacks
    def extract_step_data(step):
        return {
            "command": getattr(step, "command", None),
            "test_name": getattr(step, "test_name", "unknown_test"),
            "expected_status": getattr(step, "expected_status", 200),
            "method": getattr(step, "method", "GET"),
            "url": getattr(step, "url", ""),
            "headers": getattr(step, "headers", {}),
            "request_payload": getattr(step, "payload", None),
            "pattern_match": getattr(step, "pattern_match", ""),
            "pod_exec": (
                getattr(step, "other_fields", {}).get("podExec", None)
                if hasattr(step, "other_fields")
                else None
            ),
            "from_excel_response_payload": (
                getattr(step, "other_fields", {}).get("Response_Payload", None)
                if hasattr(step, "other_fields")
                else None
            ),
            "compare_with_key": (
                getattr(step, "other_fields", {}).get("Compare_With", None)
                if hasattr(step, "other_fields")
                else None
            ),
        }

    def manage_workflow_context(flow, step_data):
        pass


try:
    from ..utils.logger import get_logger

    logger = get_logger("TestPilot.AuditProcessor")
except ImportError:
    import logging

    logger = logging.getLogger("TestPilot.AuditProcessor")

try:
    from ..utils.myutils import replace_placeholder_in_command
    from ..utils.response_parser import parse_curl_output

    UTILS_AVAILABLE = True
except ImportError:
    UTILS_AVAILABLE = False

    # Provide basic fallbacks
    def replace_placeholder_in_command(command, svc_map):
        return command

    def parse_curl_output(output, error=""):
        return {"parsed": "data"}


from .audit_engine import AuditEngine

# Import additional functions that tests expect to be available
try:
    from ..utils.curl_builder import build_ssh_k8s_curl_command
    from ..utils.resource_map_utils import map_localhost_url
except ImportError:
    # Provide fallbacks if imports fail
    def map_localhost_url(url, resource_map=None):
        return url

    def build_ssh_k8s_curl_command(*args, **kwargs):
        return "echo 'command not available'", None


def process_single_step_audit(
    step,
    flow,
    target_hosts,
    svc_maps,
    placeholder_pattern,
    connector,
    host_cli_map,
    test_results,
    audit_engine: AuditEngine,
    show_table,
    dashboard,
    args=None,
    step_delay=1,
):
    """
    Process a single test step with comprehensive audit validation.
    This function extends the standard step processing with 100% pattern matching
    and detailed audit trail generation.
    """
    step_data = extract_step_data(step)
    if (
        step_data["command"] is None
        or (PANDAS_AVAILABLE and pd.isna(step_data["command"]))
        or step_data["command"] == ""
    ):
        return

    step_data["save_key"] = step.other_fields.get("Save_As")
    manage_workflow_context(flow, step_data)

    # Extract audit-specific data
    pattern_match = step.other_fields.get("Pattern_Match", "")
    expected_status = step_data.get("expected_status", 200)
    http_method = _extract_http_method_from_command(step_data["command"])

    # Get test name from flow or step
    test_name = getattr(step, "test_name", None) or getattr(
        flow, "test_name", f"step_{step.row_idx}"
    )
    logger.info(f"🔍 [AUDIT] Processing step: {test_name}")
    logger.debug(f"Expected pattern: {pattern_match}")

    # Execute the command and collect response
    try:
        response_data = _execute_step_command(
            step_data,
            target_hosts,
            svc_maps,
            placeholder_pattern,
            connector,
            host_cli_map,
            args,
        )

        # Perform audit validation
        audit_result = audit_engine.validate_response(
            test_name=test_name,
            expected_pattern=pattern_match,
            actual_response=response_data.get("raw_output", ""),
            http_method_expected=http_method,
            http_method_actual=response_data.get("http_method", ""),
            status_code_expected=expected_status,
            status_code_actual=response_data.get("status_code"),
            request_details={
                "command": step_data["command"],
                "pod_exec": step_data.get("pod_exec", ""),
                "host": response_data.get("host", ""),
                "execution_time": response_data.get("execution_time", 0),
            },
        )

        # Create test result for standard compatibility
        from ..core.test_result import TestResult

        error_message = (
            "; ".join(
                audit_result.get("http_validation_errors", [])
                + audit_result.get("json_validation_errors", [])
            )
            if audit_result["overall_result"] != "PASS"
            else None
        )

        test_result = TestResult(
            sheet=getattr(step, "other_fields", {}).get("sheet", "audit"),
            row_idx=getattr(step, "row_idx", 0),
            host=response_data.get("host", ""),
            command=step_data["command"],
            output=response_data.get("raw_output", ""),
            error=error_message or "",
            expected_status=expected_status,
            actual_status=response_data.get("status_code"),
            pattern_match=step_data.get("pattern_match", ""),
            pattern_found=audit_result["overall_result"] == "PASS",
            passed=audit_result["overall_result"] == "PASS",
            fail_reason=error_message,
            test_name=test_name,
            duration=response_data.get("execution_time", 0),
            method=_extract_http_method_from_command(step_data["command"]),
        )

        # Store result and update dashboard
        step.result = test_result
        test_results.append(test_result)

        if dashboard:
            dashboard.add_test_result(test_result)

        # Log audit result
        if audit_result["overall_result"] == "PASS":
            logger.info(
                f"✅ [AUDIT PASS] {test_name}: 100% validation successful"
            )
        else:
            logger.warning(
                f"❌ [AUDIT FAIL] {test_name}: Validation failures detected"
            )
            for error in audit_result.get("http_validation_errors", []):
                logger.warning(f"   HTTP Error: {error}")
            for error in audit_result.get("json_validation_errors", []):
                logger.warning(f"   JSON Error: {error}")
            if audit_result.get("differences"):
                logger.warning(
                    f"   Pattern Differences: {len(audit_result['differences'])} found"
                )

    except Exception as e:
        logger.error(f"❌ [AUDIT ERROR] {test_name}: {str(e)}")

        # Create failed test result
        from ..core.test_result import TestResult

        error_message = f"Execution error: {str(e)}"

        test_result = TestResult(
            sheet=getattr(step, "other_fields", {}).get("sheet", "audit"),
            row_idx=getattr(step, "row_idx", 0),
            host="",
            command=step_data["command"],
            output="",
            error=error_message,
            expected_status=expected_status,
            actual_status=None,
            pattern_match=step_data.get("pattern_match", ""),
            pattern_found=False,
            passed=False,
            fail_reason=error_message,
            test_name=test_name,
            duration=0,
            method=_extract_http_method_from_command(step_data["command"]),
            error_message=error_message,
        )

        step.result = test_result
        test_results.append(test_result)

        if dashboard:
            dashboard.add_test_result(test_result)

        # Record audit error
        audit_engine.validate_response(
            test_name=test_name,
            expected_pattern=pattern_match,
            actual_response="",
            request_details={"error": str(e)},
        )


def _execute_step_command(
    step_data: Dict[str, Any],
    target_hosts: List[str],
    svc_maps: Dict[str, Any],
    placeholder_pattern,
    connector,
    host_cli_map: Dict[str, str],
    args,
) -> Dict[str, Any]:
    """
    Execute the command and return structured response data.
    """
    import time

    from ..utils.curl_builder import build_ssh_k8s_curl_command
    from ..utils.resource_map_utils import map_localhost_url

    start_time = time.time()

    # Replace placeholders in command
    command = step_data["command"]
    for host in target_hosts:
        if host in svc_maps:
            command = replace_placeholder_in_command(command, svc_maps[host])

    # Map localhost URLs if needed - try to get resource_map from first available svc_map
    resource_map = {}
    if svc_maps and target_hosts:
        first_host = target_hosts[0]
        if first_host in svc_maps:
            resource_map = svc_maps[first_host]

    # Only call map_localhost_url if command contains localhost
    if "localhost" in command:
        command = map_localhost_url(command, resource_map)

    response_data = {
        "raw_output": "",
        "parsed_output": {},
        "status_code": None,
        "http_method": "",
        "host": "",
        "execution_time": 0,
    }

    try:
        if connector and args and not args.execution_mode == "mock":
            # SSH execution
            if step_data.get("pod_exec"):
                # Build kubectl exec command
                cli_type = (
                    host_cli_map.get(target_hosts[0], "kubectl")
                    if host_cli_map
                    else "kubectl"
                )
                ssh_command = build_ssh_k8s_curl_command(
                    command, step_data["pod_exec"], cli_type
                )
                result = connector.run_command(ssh_command, target_hosts)

                if target_hosts and target_hosts[0] in result:
                    response_data["raw_output"] = result[target_hosts[0]].get(
                        "output", ""
                    )
                    response_data["host"] = target_hosts[0]
            else:
                # Direct SSH command
                result = connector.run_command(command, target_hosts)
                if target_hosts and target_hosts[0] in result:
                    response_data["raw_output"] = result[target_hosts[0]].get(
                        "output", ""
                    )
                    response_data["host"] = target_hosts[0]
        else:
            # Local execution or mock mode
            import subprocess

            result = subprocess.run(
                command, shell=True, capture_output=True, text=True, timeout=30
            )
            response_data["raw_output"] = result.stdout or result.stderr
            response_data["host"] = "localhost"

        # Parse response for additional data
        response_data["parsed_output"] = parse_curl_output(
            response_data["raw_output"], ""
        )
        response_data["status_code"] = _extract_status_code(
            response_data["raw_output"]
        )
        response_data["http_method"] = _extract_http_method_from_command(
            step_data["command"]
        )
        response_data["execution_time"] = time.time() - start_time

    except Exception as e:
        logger.error(f"Command execution failed: {e}")
        response_data["raw_output"] = f"Error: {str(e)}"
        response_data["execution_time"] = time.time() - start_time

    return response_data


def _extract_http_method_from_command(command: str) -> str:
    """Extract HTTP method from curl command with proper edge case handling."""
    if not command:
        return ""

    # Only process actual curl commands (case-insensitive)
    # Check if curl is a word boundary (not part of another word like "not_curl")
    if not re.search(r"\bcurl\b", command, re.IGNORECASE):
        return ""

    # Handle specific edge cases first

    # 1. Incomplete -X flag (e.g., "curl -X")
    if re.search(r"-X\s*$", command):
        return ""

    # 2. Incomplete --request flag (e.g., "curl --request")
    if re.search(r"--request\s*$", command):
        return ""

    # 3. Look for -X flag with quoted method
    match = re.search(r"-X\s+['\"]([^'\"]*)['\"]", command, re.IGNORECASE)
    if match:
        method = match.group(1).strip()
        # Return empty string for empty quotes or return the exact content
        return method if method else ""

    # 4. Look for -X flag without quotes (but not at end)
    match = re.search(r"-X\s+(\S+)", command, re.IGNORECASE)
    if match:
        method = match.group(1).strip()
        return method.upper() if method else ""

    # 5. Look for --request=METHOD format
    match = re.search(r"--request\s*=\s*(\S+)", command, re.IGNORECASE)
    if match:
        method = match.group(1).strip()
        return method.upper() if method else ""

    # 6. Look for --request METHOD format (with space)
    match = re.search(r"--request\s+(\S+)", command, re.IGNORECASE)
    if match:
        method = match.group(1).strip()
        return method.upper() if method else ""

    # 7. Look for --request with quoted method
    match = re.search(
        r"--request\s+['\"]([^'\"]*)['\"]", command, re.IGNORECASE
    )
    if match:
        method = match.group(1).strip()
        return method if method else ""

    # If it's a curl command with no method flags, default to GET
    return "GET"


def _extract_status_code(output: str) -> Optional[int]:
    """Extract HTTP status code from curl output with proper edge case handling."""
    if not output:
        return None

    # Look for HTTP status codes in various formats (order matters - most specific first)
    status_patterns = [
        r"HTTP/[\d\.]+\s+(\d{3,4})(?:\s|$)",  # HTTP/1.1 200 or HTTP/1.1 1000 (word boundary)
        r'"status":\s*(\d{3,4})(?:\D|$)',  # "status": 200 (followed by non-digit or end)
        r"status:\s*(\d{3,4})(?:\D|$)",  # status: 200 (followed by non-digit or end)
        r"status\s+is\s+(\d{3,4})(?:\D|$)",  # "The status is 418"
        r"status\s*=\s*(\d{3,4})(?:\D|$)",  # status=418
        r"HTTP\s+(\d{3,4})(?:\D|$)",  # HTTP 200
    ]

    for pattern in status_patterns:
        match = re.search(pattern, output, re.IGNORECASE)
        if match:
            try:
                status_code = int(match.group(1))
                # Accept any valid HTTP status code (including edge cases like 1000)
                if 100 <= status_code <= 9999:
                    return status_code
            except ValueError:
                continue

    return None
