# =============================================================================
# test_pilot_core.py (FIXED VERSION)
# =============================================================================

import json
import os
import re
import subprocess
import sys
import time
from pprint import pprint
from typing import Any, Dict, List, Optional, Tuple, Union

import pandas as pd

from curl_builder import build_ssh_k8s_curl_command
from logger import get_failure_logger, get_logger
from response_parser import parse_curl_output
from test_result import TestFlow, TestResult, TestStep
from utils.kubectl_logs_search import search_in_custom_output
from utils.myutils import prettify_curl_output, replace_placeholder_in_command
from utils.resource_map_utils import map_localhost_url
from validation_engine import ValidationContext, ValidationDispatcher

# Mock integration imports (lazy loaded to avoid issues if not available)
_mock_executor = None


def get_mock_executor(mock_server_url: str):
    """Lazy load mock executor to avoid import issues."""
    global _mock_executor
    if _mock_executor is None:
        try:
            from mock_integration import MockExecutor

            _mock_executor = MockExecutor(mock_server_url)
            logger.debug(f"Initialized mock executor for {mock_server_url}")
        except ImportError as e:
            logger.error(f"Failed to import mock integration: {e}")
            _mock_executor = None
    return _mock_executor


# Python 3.8+ compatibility for Pattern type
if sys.version_info >= (3, 9):
    PatternType = re.Pattern[str]
else:
    from typing import Pattern

    PatternType = Pattern[str]

logger = get_logger("TestPilot.Core")
failure_logger = get_failure_logger("TestPilot.Failures")


def save_kubectl_logs(
    raw_output, host, row_idx, test_name, dir_path="kubectl_logs"
):
    os.makedirs(dir_path, exist_ok=True)
    safe_test_name = re.sub(r"[^a-zA-Z0-9_.-]", "_", str(test_name))
    filename = f"kubectl_logs_{host}_{safe_test_name}_{row_idx}.json"
    filepath = os.path.join(dir_path, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(raw_output, f, indent=2)


def safe_str(val: Any) -> str:

    if val is None or (isinstance(val, float) and pd.isna(val)):
        return ""
    return str(val)


def substitute_placeholders(
    command: str, svc_map: Dict[str, str], placeholder_pattern: PatternType
) -> str:
    """Substitute placeholders in command with values from service map."""

    def repl(match):
        key = match.group(1)
        # Always return a string, never None
        return str(svc_map.get(key, match.group(0)))

    return placeholder_pattern.sub(repl, command)


def extract_step_data(step: TestStep) -> Dict[str, Any]:
    """Extract and prepare all data from a TestStep object."""
    command = step.other_fields.get("Command")
    from_excel_response_payload = step.other_fields.get("Response_Payload")
    expected_status = step.expected_status
    # if expected_status is not None and pd.notna(expected_status):
    #     expected_status = int(expected_status)
    # else:
    #     expected_status = None
    pattern_match = step.pattern_match
    if pattern_match is None or (
        isinstance(pattern_match, float) and pd.isna(pattern_match)
    ):
        pattern_match = ""
    pod_exec = step.other_fields.get("podExec")
    request_payload = step.payload
    method = step.method or "GET"
    url = step.url
    headers = step.headers or {}
    if isinstance(headers, str):
        try:
            headers = json.loads(headers)
        except Exception:
            headers = {}
    compare_with_key = step.other_fields.get("Compare_With")
    return {
        "command": command,
        "from_excel_response_payload": from_excel_response_payload,
        "expected_status": expected_status,
        "pattern_match": pattern_match,
        "pod_exec": pod_exec,
        "request_payload": request_payload,
        "method": method,
        "url": url,
        "headers": headers,
        "compare_with_key": compare_with_key,
    }


def manage_workflow_context(flow: TestFlow, step_data: Dict[str, Any]) -> None:
    """Manage workflow context for storing payloads between steps."""
    method = step_data["method"]
    request_payload = step_data["request_payload"]
    if method.upper() in ["PUT", "POST"]:
        # This needs to be handled differently - pass save_key in step_data
        save_key = step_data.get("save_key") or "put_payload"
        if request_payload:
            flow.context[save_key] = request_payload


def resolve_namespace(connector, host: str) -> Optional[str]:
    """Resolve namespace for a given host."""
    if connector.use_ssh:
        host_cfg = connector.get_host_config(host)
        return getattr(host_cfg, "namespace", None) if host_cfg else None
    else:
        try:
            with open("config/hosts.json", "r") as f:
                data = json.load(f)
            connect_to = data.get("connect_to")
            hosts = data.get("hosts")
            if isinstance(hosts, list) and connect_to:
                for host_cfg in hosts:
                    if isinstance(host_cfg, dict) and (
                        host_cfg.get("name") == connect_to
                        or host_cfg.get("hostname") == connect_to
                    ):
                        return host_cfg.get("namespace")
            elif isinstance(hosts, dict) and connect_to:
                host_cfg = hosts.get(connect_to)
                if isinstance(host_cfg, dict):
                    return host_cfg.get("namespace")
        except Exception as e:
            logger.warning(f"Could not fetch namespace from config: {e}")
        return None


def build_url_based_command(
    step_data: Dict[str, Any],
    svc_map: Dict[str, str],
    placeholder_pattern: PatternType,
    namespace: Optional[str],
    host_cli_map: Optional[Dict[str, str]],
    host: str,
) -> Optional[str]:
    """Build curl command for URL-based API calls."""
    url = step_data["url"]
    method = step_data["method"]
    headers = step_data["headers"]
    request_payload = step_data["request_payload"]
    pod_exec = step_data["pod_exec"]

    # Get CLI type (kubectl or oc) from host_cli_map
    cli_type = "kubectl"
    if host_cli_map and host in host_cli_map:
        cli_type = host_cli_map[host]

    try:
        # substituted_url = substitute_placeholders(
        #     safe_str(url), svc_map, placeholder_pattern
        # )
        substituted_url = replace_placeholder_in_command(
            safe_str(url), svc_map
        )
        ssh_cmd, _ = build_ssh_k8s_curl_command(
            namespace=namespace or "default",
            container=pod_exec,
            url=substituted_url,
            method=method,
            headers={k: safe_str(v) for k, v in headers.items()},
            payload=safe_str(request_payload),
            payloads_folder="payloads",
            cli_type=cli_type,
        )
        return ssh_cmd
    except Exception as e:
        logger.error(f"Failed to build SSH curl command: {e}")
        return None


def build_kubectl_logs_command(
    command, namespace, connector, host, host_cli_map=None
):
    """Build kubectl logs command with dynamic pod name resolution. Handles multiple pod matches."""
    match = re.search(r"\{([^}]+)\}", command)
    if not match:
        return command
    to_search_pod_name = match.group(1)

    # Get CLI type (kubectl or oc) from host_cli_map
    cli_type = "kubectl"
    if host_cli_map and host in host_cli_map:
        cli_type = host_cli_map[host]

    # Build the CLI get pods command (without awk)
    if namespace:
        find_pod = (
            f"{cli_type} get pods -n {namespace} | "
            f"grep '{to_search_pod_name}' | awk '{{print $1}}'"
        )
    else:
        find_pod = f"{cli_type} get pods | grep '{to_search_pod_name}' | awk '{{print $1}}'"
    # Get all matching pod names
    if connector.use_ssh:
        result = connector.run_command(find_pod, [host])
        res = result.get(host, {"output": "", "error": ""})
        pod_names = [
            line.strip() for line in res["output"].splitlines() if line.strip()
        ]
    else:
        result = subprocess.run(
            find_pod, shell=True, capture_output=True, text=True
        )
        pod_names = [
            line.strip() for line in result.stdout.splitlines() if line.strip()
        ]
    if not pod_names:
        logger.error(
            f"No pod found matching '{to_search_pod_name}' on host {host}"
        )
        return None

    commands = [
        command.replace(f"{{{to_search_pod_name}}}", pod_name)
        for pod_name in pod_names
    ]
    return commands


def build_command_for_step(
    step_data,
    svc_map,
    placeholder_pattern,
    namespace,
    host_cli_map,
    host,
    connector,
):  # host_cli_map now required
    """Build the appropriate command for a test step, with pod_mode support."""
    import json
    import os

    from curl_builder import build_pod_mode

    url = step_data["url"]
    command = step_data["command"]

    # Check for pod_mode in config/hosts.json
    pod_mode = False
    config_path = os.path.join(
        os.path.dirname(__file__), "config", "hosts.json"
    )
    try:
        with open(config_path, "r") as f:
            config = json.load(f)
            pod_mode = config.get("pod_mode", False)
    except Exception as e:
        logger.warning(f"Could not read pod_mode from config: {e}")

    if pod_mode and url:
        # Use build_pod_mode to construct the command
        method = step_data.get("method", "KUBECTL")
        headers = step_data.get("headers")
        payload = step_data.get("request_payload")
        payloads_folder = step_data.get("payloads_folder", "payloads")
        extra_curl_args = step_data.get("extra_curl_args")

        # if localhost is in the url, replace it with the FQDN from resource_map.json
        if "localhost" in url:
            substituted_url = map_localhost_url(url, svc_map)
        else:
            # substituted_url = substitute_placeholders(
            #     safe_str(url), svc_map, placeholder_pattern
            # )
            substituted_url = replace_placeholder_in_command(
                safe_str(url), svc_map
            )
        curl_cmd, _ = build_pod_mode(
            substituted_url,
            method=method,
            headers=headers,
            payload=payload,
            payloads_folder=payloads_folder,
            extra_curl_args=extra_curl_args,
        )
        return curl_cmd
    elif url:
        return build_url_based_command(
            step_data,
            svc_map,
            placeholder_pattern,
            namespace,
            host_cli_map,
            host,
        )  # host_cli_map passed
    elif command and (
        command.startswith("kubectl") or command.startswith("oc")
    ):
        # update method to KUBECTL in step_data method
        step_data["method"] = "KUBCTL"
        return (
            build_kubectl_logs_command(
                command, namespace, connector, host, host_cli_map
            ),
            host_cli_map,
        )
    else:
        logger.warning(f"URL is required for command execution: {command}")
        return None


def execute_command(command, host, connector):
    """Execute a command and return output, error, and duration."""
    if not command:
        return "", "Command build failed", 0.0

    # Check for mock execution mode
    if (
        hasattr(connector, "execution_mode")
        and connector.execution_mode == "mock"
    ):
        logger.debug(f"Executing in MOCK mode on [{host}]: {command}")
        # Pass sheet context for enhanced mock servers
        sheet_name = getattr(connector, "_current_sheet", None)
        test_name = getattr(connector, "_current_test", None)
        return execute_mock_command(
            command, host, connector, sheet_name, test_name
        )

    # Original production execution
    logger.debug(f"Running command on [{host}]: {command}")
    start_time = time.time()
    if connector.use_ssh:
        # print *f"Executing command via SSH on {command} for host {host}")
        logger.debug(f"Executing command via SSH on {command}")
        result = connector.run_command(command, [host])
        res = result.get(host, {"output": "", "error": ""})
        output = res["output"]
        error = res["error"]
    else:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True
        )
        output = result.stdout.strip()
        error = result.stderr.strip()
    duration = time.time() - start_time
    logger.debug(f"Command executed in {duration:.2f} seconds on [{host}]")
    logger.debug(f"Output: {output}")
    if error:
        logger.debug(f"Error: {error}")
    return output, error, duration


def execute_mock_command(
    command, host, connector, sheet_name=None, test_name=None
):
    """Execute command in mock mode using mock server."""
    mock_server_url = getattr(
        connector, "mock_server_url", "http://localhost:8081"
    )

    # Get mock executor
    mock_executor = get_mock_executor(mock_server_url)
    if mock_executor is None:
        logger.error(
            "Mock executor not available, falling back to error response"
        )
        return "", "Mock execution failed: MockExecutor not available", 0.0

    # Check if mock server is running
    if not mock_executor.health_check():
        logger.warning(
            f"Mock server at {mock_server_url} not responding, attempting execution anyway"
        )

    # Execute mock command
    try:
        return mock_executor.execute_mock_command(
            command, host, sheet_name, test_name
        )
    except Exception as e:
        logger.error(f"Mock execution failed: {e}")
        return "", f"Mock execution failed: {e}", 0.0


def validate_and_create_result(
    step,
    flow,
    step_data,
    parsed_output,
    output,
    error,
    duration,
    host,
    command,
    args=None,
):
    """Validate test results and create TestResult object using modular validation engine."""
    expected_status = step_data["expected_status"]
    pattern_match = step_data["pattern_match"]
    compare_with_key = step_data["compare_with_key"]
    from_excel_response_payload = step_data["from_excel_response_payload"]
    method = step_data["method"]
    request_payload = step_data.get("request_payload")

    # Determine kubectl scenario
    is_kubectl = bool(step_data.get("is_kubectl", False)) or parsed_output.get(
        "is_kubectl_logs", False
    )

    # Determine saved_payload for GET/PUT workflow
    saved_payload = None
    if compare_with_key:
        saved_payload = flow.context.get(compare_with_key)

    # Use response_payload from Excel or parsed_output
    response_payload = (
        from_excel_response_payload
        if from_excel_response_payload is not None
        else parsed_output.get("response_payload")
    )
    if isinstance(response_payload, float) and pd.isna(response_payload):
        response_payload = None

    # Use actual_status and response_body from parsed_output
    actual_status = parsed_output.get("http_status") or parsed_output.get(
        "status_code"
    )
    response_body = parsed_output.get("raw_output")
    response_headers = parsed_output.get("headers")

    # Build ValidationContext
    context = ValidationContext(
        method=method,
        request_payload=request_payload,
        expected_status=expected_status,
        response_payload=response_payload,
        pattern_match=pattern_match,
        actual_status=actual_status,
        response_body=response_body,
        response_headers=response_headers,
        is_kubectl=is_kubectl,
        saved_payload=saved_payload,
        args=args,  # Pass args here
        sheet_name=flow.sheet,  # Pass sheet name for enhanced pattern matching
        row_idx=step.row_idx,  # Pass row index for enhanced pattern matching
    )

    # Dispatch validation
    dispatcher = ValidationDispatcher()
    result = dispatcher.dispatch(context)

    test_result = TestResult(
        sheet=flow.sheet,
        row_idx=step.row_idx,
        host=host,
        command=command,
        output=output,
        error=error,
        expected_status=expected_status,
        actual_status=actual_status,
        pattern_match=(
            str(pattern_match) if pattern_match is not None else None
        ),
        pattern_found=(
            result.details.get("pattern_found") if result.details else None
        ),
        passed=result.passed,
        fail_reason=result.fail_reason,
        test_name=flow.test_name,
        duration=duration,
        method=method,
        details=result.details,
    )
    return test_result


def log_test_result(
    test_result: TestResult, flow: TestFlow, step: TestStep
) -> None:
    """Log test result with appropriate level and structured failure logging."""
    if not test_result.passed:
        # Standard console/file logging
        logger.debug(
            f"[FAIL][{flow.sheet}][row {step.row_idx}][{test_result.host}] Command: {test_result.command}"
        )
        logger.debug(f"Reason: {test_result.fail_reason}")
        # logger.error(f"Output: {test_result.output}")
        # logger.error(f"Error: {test_result.error}")

        # Structured failure logging for automated analysis
        structured_failure = (
            f"SHEET={flow.sheet}|"
            f"ROW={step.row_idx}|"
            f"HOST={test_result.host}|"
            f"TEST_NAME={getattr(flow, 'test_name', 'Unknown')}|"
            f"COMMAND={test_result.command}|"
            f"REASON={test_result.fail_reason}|"
            f"EXPECTED_STATUS={test_result.expected_status}|"
            f"ACTUAL_STATUS={test_result.actual_status}|"
            f"PATTERN_MATCH={test_result.pattern_match}|"
            f"PATTERN_FOUND={test_result.pattern_found}|"
            f"OUTPUT_LENGTH={len(test_result.output) if test_result.output else 0}|"
            f"ERROR_LENGTH={len(test_result.error) if test_result.error else 0}"
        )
        failure_logger.error(structured_failure)
    else:
        logger.debug(
            f"[PASS][{flow.sheet}][row {step.row_idx}][{test_result.host}] Command: {test_result.command}"
        )


def process_single_step(
    step,
    flow,
    target_hosts,
    svc_maps,
    placeholder_pattern,
    connector,
    host_cli_map,
    test_results,
    show_table,
    dashboard,
    args=None,
    step_delay=1,
):
    step_data = extract_step_data(step)
    if step_data["command"] is None or pd.isna(step_data["command"]):
        return

    step_data["save_key"] = step.other_fields.get("Save_As")
    manage_workflow_context(flow, step_data)

    for host in target_hosts:
        svc_map = svc_maps.get(host, {})
        namespace = resolve_namespace(connector, host)

        # Set sheet and test context for mock execution
        if (
            hasattr(connector, "execution_mode")
            and connector.execution_mode == "mock"
        ):
            connector._current_sheet = getattr(flow, "sheet_name", None)
            connector._current_test = getattr(flow, "test_name", None)
        if not show_table:
            logger.info(f"[CALLFLOW] Host: {host}")
            color_cyan = "\033[96m"
            reset_code = "\033[0m"
            logger.info(
                f"{color_cyan}[CALLFLOW] Step: {getattr(step, 'step_name', 'N/A')} (Flow: {getattr(flow, 'test_name', 'N/A')}){reset_code}"
            )
            logger.info(
                f"[CALLFLOW] Substituting placeholders in command: {step_data['command']}"
            )

        # check if command is wait() if so it introduces a delay mentioned in wait(30)
        # sleep for mentioned time in wait() and continue to next step
        if step_data["command"].strip().lower().startswith("wait"):
            wait_str = step_data["command"]
            match = re.search(r"wait\((\d+)\)", wait_str, re.IGNORECASE)
            if match:
                number = match.group(1)
                time.sleep(int(number))
            continue

        commands = build_command_for_step(
            step_data,
            svc_map,
            placeholder_pattern,
            namespace,
            host_cli_map,
            host,
            connector,
        )

        if isinstance(commands, str):
            commands = [commands]
        elif commands is None:
            commands = []

        # --- Aggregate logic for multiple pod logs ---
        all_outputs = []
        all_errors = []
        all_parsed = []
        all_durations = []
        all_commands = []
        any_passed = False
        matched_pod = None
        matched_result = None
        matched_output = None
        matched_error = None
        matched_duration = None
        matched_command = None
        matched_parsed = None
        pod_names = []
        test_result = {}

        for command in commands:
            if not command:
                if not show_table:
                    logger.warning(
                        f"[CALLFLOW] Command could not be built for host {host}, step {getattr(step, 'step_name', 'N/A')}. Skipping."
                    )
                continue
            if not show_table:
                logger.info(f"[CALLFLOW] Built command: {command}")
                logger.info(f"[CALLFLOW] Executing command on host {host}...")
            output, error, duration = execute_command(command, host, connector)
            parsed_output = parse_curl_output(output, error)
            all_outputs.append(output)
            all_errors.append(error)
            all_parsed.append(parsed_output)
            all_durations.append(duration)
            all_commands.append(command)
            # Try to extract pod name for log file naming
            pod_name = None
            if command.startswith("kubectl logs") or command.startswith(
                "oc logs"
            ):
                parts = command.split()
                try:
                    pod_name = parts[2]
                except IndexError:
                    pod_name = None
            pod_names.append(pod_name)
            if parsed_output.get("is_kubectl_logs"):
                save_kubectl_logs(
                    parsed_output.get("raw_output"),
                    host,
                    f"{step.row_idx}_{pod_name}" if pod_name else step.row_idx,
                    getattr(flow, "test_name", "unknown"),
                )

            if not show_table:
                logger.debug(
                    f"[CALLFLOW] Command executed in {duration:.2f} seconds"
                )
                logger.info(f"[CALLFLOW] Output from server: {output}")
                if error:
                    logger.info(f"[CALLFLOW] HTTP Output from server: {error}")

                # Add pattern match string to CALLFLOW output
                pattern = step.pattern_match
                if pattern:
                    logger.info(f"[CALLFLOW] Pattern to match: {pattern}")
            # Validate this pod's logs
            test_result = validate_and_create_result(
                step,
                flow,
                step_data,
                parsed_output,
                output,
                error,
                duration,
                host,
                command,
                args,
            )
            if test_result.passed and not any_passed:
                any_passed = True
                matched_result = test_result
                matched_output = output
                matched_error = error
                matched_duration = duration
                matched_command = command

        # After all pods: create a single TestResult for the step
        if any_passed and matched_result:
            # Use the result from the passing pod
            final_result = matched_result
            final_result.passed = True
            final_result.fail_reason = None
            final_result.output = (
                matched_output if matched_output is not None else ""
            )
            final_result.error = (
                matched_error if matched_error is not None else ""
            )
            final_result.duration = (
                matched_duration if matched_duration is not None else 0.0
            )
            final_result.command = (
                matched_command if matched_command is not None else ""
            )
            # Optionally, add pod info to result
            # final_result.pattern_found = f"Matched pod: {matched_pod}"  # Removed: pattern_found expects bool or None
        else:
            #     # No pod matched; aggregate info
            final_result = validate_and_create_result(
                step,
                flow,
                step_data,
                all_parsed[-1] if all_parsed else {},
                "\n---\n".join(all_outputs),
                "\n---\n".join(all_errors),
                sum(all_durations) if all_durations else 0,
                host,
                ", ".join(all_commands),
                args,
            )
            final_result.passed = False
            # final_result.fail_reason = test_result.fail_reason
            # final_result.fail_reason = "Pattern not found in any pod logs"
            # final_result.pattern_found = f"Checked pods: {', '.join([str(p) for p in pod_names if p])}"  # Removed: pattern_found expects bool or None
        test_results.append(final_result)
        step.result = final_result
        if not show_table:
            status_str = "PASS" if final_result.passed else "FAIL"
            color_code = "\033[92m" if final_result.passed else "\033[91m"
            reset_code = "\033[0m"
            logger.info(
                f"[CALLFLOW] Result: {color_code}{status_str}{reset_code} | Expected: {step_data.get('expected_status', 'N/A')} | Actual: {getattr(final_result, 'actual_status', 'N/A')}"
            )
        if show_table and dashboard is not None:
            dashboard.add_result(final_result)
        log_test_result(final_result, flow, step)
        time.sleep(step_delay)
