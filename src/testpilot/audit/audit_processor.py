#!/usr/bin/env python3
"""
Audit Step Processor for TestPilot - Wraps existing OTP workflow with
comprehensive audit validation and reporting.

Now includes pod mode support for simplified command execution when
running inside Jenkins pods.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..core.test_pilot_core import process_single_step
from ..utils.logger import get_logger
from .audit_engine import AuditEngine
from .pod_mode import pod_mode_manager

logger = get_logger("TestPilot.AuditProcessor")


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
    This function wraps the standard OTP process_single_step with audit-specific validation.
    """
    try:
        # Store original test results count to identify new results
        original_results_count = len(test_results)

        # Call the standard OTP process_single_step
        process_single_step(
            step=step,
            flow=flow,
            target_hosts=target_hosts,
            svc_maps=svc_maps,
            placeholder_pattern=placeholder_pattern,
            connector=connector,
            host_cli_map=host_cli_map,
            test_results=test_results,
            show_table=show_table,
            dashboard=dashboard,
            args=args,
            step_delay=step_delay,
        )

        # Get the test result that was just added
        if len(test_results) > original_results_count:
            test_result = test_results[-1]

            # Extract audit-specific data
            test_name = test_result.test_name or f"step_{step.row_idx}"
            pattern_match = getattr(
                step, "pattern_match", ""
            ) or step.other_fields.get("Pattern_Match", "")
            expected_status = getattr(step, "expected_status", 200)

            # Perform audit validation using the test result
            audit_result = audit_engine.validate_response(
                test_name=test_name,
                expected_pattern=pattern_match,
                actual_response=test_result.output,
                http_method_expected=getattr(step, "method", None),
                http_method_actual=test_result.method,
                status_code_expected=expected_status,
                status_code_actual=test_result.actual_status,
                request_details={
                    "command": test_result.command,
                    "host": test_result.host,
                    "execution_time": test_result.duration,
                    "row_idx": test_result.row_idx,
                    "sheet": test_result.sheet,
                },
            )

            # Update test result based on audit validation if it's stricter
            if audit_result["overall_result"] == "FAIL" and test_result.passed:
                # Audit found issues that standard validation missed
                error_messages = audit_result.get(
                    "http_validation_errors", []
                ) + audit_result.get("json_validation_errors", [])
                if audit_result.get("differences"):
                    error_messages.append(
                        f"Pattern differences: {len(audit_result['differences'])} found"
                    )

                test_result.passed = False
                test_result.pattern_found = False
                test_result.fail_reason = "; ".join(error_messages)
                test_result.error = test_result.fail_reason

                # Log the audit failure
                logger.warning(
                    f"❌ [AUDIT OVERRIDE] {test_name}: Audit validation failed despite OTP pass"
                )
                for error in error_messages:
                    logger.warning(f"   - {error}")

            # Log audit result
            if audit_result["overall_result"] == "PASS":
                logger.info(
                    f"✅ [AUDIT PASS] {test_name}: 100% validation successful"
                )
            elif audit_result["overall_result"] == "ERROR":
                logger.error(
                    f"❌ [AUDIT ERROR] {test_name}: System error during validation"
                )
    except Exception as e:
        # Log the error but don't create an audit result since the core process failed
        test_name = (
            getattr(step, "test_name", None)
            or f"step_{getattr(step, 'row_idx', 'unknown')}"
        )
        logger.error(
            f"❌ [AUDIT ERROR] {test_name}: Exception during audit processing: {e}"
        )


def process_single_step_audit_pod_mode(
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
    Process a single test step with pod mode execution strategy.

    In pod mode, this function:
    1. Uses direct curl command execution instead of kubectl exec
    2. Resolves placeholders using resources_map.json
    3. Skips complex command building logic
    4. Performs audit validation on results
    """
    if not pod_mode_manager.is_pod_mode():
        # Fall back to standard audit processing
        return process_single_step_audit(
            step,
            flow,
            target_hosts,
            svc_maps,
            placeholder_pattern,
            connector,
            host_cli_map,
            test_results,
            audit_engine,
            show_table,
            dashboard,
            args,
            step_delay,
        )

    try:
        # Store original test results count to identify new results
        original_results_count = len(test_results)

        # Extract command from step
        command = getattr(step, "other_fields", {}).get("Command", "")
        if not command:
            logger.warning(f"No command found in step {step.row_idx}")
            return

        # Validate and execute curl command directly
        if not pod_mode_manager.is_valid_curl_command(command):
            logger.error(
                f"Invalid curl command in step {step.row_idx}: {command}"
            )
            return

        # Execute command in pod mode
        stdout, stderr, return_code = pod_mode_manager.execute_curl_command(
            command
        )

        # Create test result from pod mode execution
        from ..core.test_result import TestResult

        test_result = TestResult(
            sheet=flow.sheet,
            row_idx=step.row_idx,
            host="pod-environment",  # Pod mode doesn't use traditional hosts
            command=command,
            output=stdout,
            error=stderr,
            expected_status=getattr(step, "expected_status", 200),
            actual_status=_extract_status_code_from_curl_output(
                stdout, stderr, return_code
            ),
            pattern_match=getattr(step, "pattern_match", "")
            or step.other_fields.get("Pattern_Match", ""),
            pattern_found=True if return_code == 0 and stdout else False,
            passed=return_code == 0,
            fail_reason=stderr if return_code != 0 else None,
            test_name=getattr(step, "test_name", None)
            or f"step_{step.row_idx}",
            duration=0.0,  # Pod mode execution timing handled separately
            method=_extract_http_method_from_command(command),
        )

        # Add result to test_results
        test_results.append(test_result)

        # Update dashboard if provided
        if dashboard:
            dashboard.add_test_result(test_result)

        # Perform audit validation
        test_name = test_result.test_name or f"step_{step.row_idx}"
        pattern_match = getattr(
            step, "pattern_match", ""
        ) or step.other_fields.get("Pattern_Match", "")
        expected_status = getattr(step, "expected_status", 200)

        audit_result = audit_engine.validate_response(
            test_name=test_name,
            expected_pattern=pattern_match,
            actual_response=test_result.output,
            http_method_expected=getattr(step, "method", None),
            http_method_actual=test_result.method,
            status_code_expected=expected_status,
            status_code_actual=test_result.actual_status,
            request_details={
                "command": test_result.command,
                "host": test_result.host,
                "execution_time": test_result.duration,
                "row_idx": test_result.row_idx,
                "sheet": test_result.sheet,
                "pod_mode": True,
                "return_code": return_code,
            },
        )

        # Update test result based on audit validation if it's stricter
        if audit_result["overall_result"] == "FAIL" and test_result.passed:
            # Audit found issues that standard validation missed
            error_messages = audit_result.get(
                "http_validation_errors", []
            ) + audit_result.get("json_validation_errors", [])
            if audit_result.get("differences"):
                error_messages.append(
                    f"Pattern differences: {len(audit_result['differences'])} found"
                )

            test_result.passed = False
            test_result.pattern_found = False
            test_result.fail_reason = "; ".join(error_messages)
            test_result.error = test_result.fail_reason

            # Log the audit failure
            logger.warning(
                f"❌ [AUDIT OVERRIDE] {test_name}: Audit validation failed despite pod execution success"
            )
            for error in error_messages:
                logger.warning(f"   - {error}")

        # Log audit result
        if audit_result["overall_result"] == "PASS":
            logger.info(
                f"✅ [AUDIT PASS - POD MODE] {test_name}: 100% validation successful"
            )
        elif audit_result["overall_result"] == "ERROR":
            logger.error(
                f"❌ [AUDIT ERROR - POD MODE] {test_name}: System error during validation"
            )
        elif audit_result["overall_result"] == "FAIL":
            logger.warning(
                f"⚠️ [AUDIT FAIL - POD MODE] {test_name}: Validation failures detected"
            )

    except Exception as e:
        # Log the error but don't create an audit result since the execution failed
        test_name = (
            getattr(step, "test_name", None)
            or f"step_{getattr(step, 'row_idx', 'unknown')}"
        )
        logger.error(
            f"❌ [AUDIT ERROR - POD MODE] {test_name}: Exception during pod mode processing: {e}"
        )


def _extract_status_code_from_curl_output(
    stdout: str, stderr: str, return_code: int
) -> Optional[int]:
    """
    Extract HTTP status code from curl output.

    Args:
        stdout: Command stdout
        stderr: Command stderr
        return_code: Process return code

    Returns:
        Optional[int]: HTTP status code if found, None otherwise
    """
    if return_code != 0:
        return None

    # Try to extract from HTTP response in stdout
    import re

    # Look for HTTP/1.1 200 OK pattern
    http_match = re.search(r"HTTP/\d\.\d\s+(\d{3})", stdout)
    if http_match:
        return int(http_match.group(1))

    # Look for JSON status field
    json_match = re.search(r'"status"\s*:\s*(\d{3})', stdout)
    if json_match:
        return int(json_match.group(1))

    # Default to 200 if command succeeded but no explicit status found
    return 200


def _extract_http_method_from_command(command: str) -> str:
    """Extract HTTP method from a curl command string."""
    import re

    if not command or not command.strip().startswith("curl"):
        return ""
    # Look for -X or --request
    match = re.search(r"(?:-X|--request)\s+(\w+)", command)
    if match:
        return match.group(1).upper()
    # Default to GET if curl and no method specified
    return "GET"


def _extract_status_code(output: str):
    """Extract status code from a response string (HTTP or JSON)."""
    import re

    if not output:
        return None
    # Try HTTP/1.1 200 OK
    match = re.search(r"HTTP/\d\.\d\s+(\d{3})", output)
    if match:
        return int(match.group(1))
    # Try JSON: {"status": 404}
    match = re.search(r'"status"\s*:\s*(\d{3})', output)
    if match:
        return int(match.group(1))
    return None
