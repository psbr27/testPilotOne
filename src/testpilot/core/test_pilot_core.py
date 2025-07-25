# =============================================================================
# test_pilot_core.py
# =============================================================================

import copy
import json
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pprint import pprint
from typing import Any, Dict, List, Optional, Tuple, Union

import pandas as pd

from ..utils.curl_builder import build_ssh_k8s_curl_command
from ..utils.kubectl_logs_search import search_in_custom_output
from ..utils.logger import get_failure_logger, get_logger
from ..utils.myutils import (
    prettify_curl_output,
    replace_placeholder_in_command,
)
from ..utils.resource_map_utils import map_localhost_url
from ..utils.response_parser import parse_curl_output
from .test_result import TestFlow, TestResult, TestStep
from .validation_engine import ValidationContext, ValidationDispatcher

# Mock integration imports (lazy loaded to avoid issues if not available)
_mock_executor = None


def _extract_and_display_epoch_timestamps(raw_output: str) -> None:
    """Extract first and last epochSecond timestamps from kubectl logs output and display the difference."""
    from datetime import datetime

    # Get logger
    logger = get_logger("TestPilot.Core")

    try:
        # Pattern to match epochSecond in logs
        # Supports formats like: "epochSecond":1234567890, epochSecond: 1234567890, epochSecond=1234567890
        epoch_pattern = r'"?epochSecond"?\s*[=:]\s*"?(\d{10,})"?'

        # Find all epochSecond values
        matches = re.findall(epoch_pattern, raw_output)

        if matches and len(matches) >= 2:
            # Convert to integers and remove duplicates while preserving order
            epochs = []
            seen = set()
            for match in matches:
                epoch = int(match)
                if epoch not in seen:
                    epochs.append(epoch)
                    seen.add(epoch)

            if len(epochs) >= 2:
                first_epoch = epochs[0]
                last_epoch = epochs[-1]
                difference = last_epoch - first_epoch

                # Convert to human-readable format
                first_time = datetime.fromtimestamp(first_epoch)
                last_time = datetime.fromtimestamp(last_epoch)

                logger.info(
                    f"[CALLFLOW] First epochSecond: {first_epoch} ({first_time.strftime('%Y-%m-%d %H:%M:%S')})"
                )
                logger.info(
                    f"[CALLFLOW] Last epochSecond: {last_epoch} ({last_time.strftime('%Y-%m-%d %H:%M:%S')})"
                )
                logger.info(
                    f"[CALLFLOW] Time difference: {difference} seconds"
                )

                # Also show total unique timestamps found
                if len(epochs) > 2:
                    logger.info(
                        f"[CALLFLOW] Total unique timestamps found: {len(epochs)}"
                    )
            else:
                logger.info(
                    f"[CALLFLOW] Only one unique epochSecond found: {epochs[0]}"
                )
        elif matches and len(matches) == 1:
            logger.info(f"[CALLFLOW] Only one epochSecond found: {matches[0]}")
        else:
            logger.debug(
                "[CALLFLOW] No epochSecond timestamps found in kubectl logs output"
            )
    except Exception as e:
        logger.debug(f"[CALLFLOW] Failed to extract epoch timestamps: {e}")


def _load_response_payload_file(
    filename: str, payloads_dir: str = "payloads"
) -> str:
    """
    Load JSON file content for Response_Payload, similar to curl_builder.py logic.
    Used for NRF testing where Response_Payload references JSON files like 'reg_02_payload_01.json'.
    """
    logger = get_logger("TestPilotCore._load_response_payload_file")

    if not filename or not filename.strip().endswith(".json"):
        return filename

    payload_path = os.path.join(payloads_dir, filename.strip())
    if not os.path.isfile(payload_path):
        logger.warning(
            f"Response payload file not found: {payload_path}, using filename as-is"
        )
        return filename

    try:
        with open(payload_path, "r", encoding="utf-8") as f:
            content = f.read().strip()
            logger.debug(f"Loaded response payload from file: {payload_path}")
            return content
    except (IOError, OSError) as e:
        logger.warning(
            f"Failed to read response payload file {payload_path}: {e}, using filename as-is"
        )
        return filename


def get_mock_executor(mock_server_url: str):
    """Lazy load mock executor to avoid import issues."""
    global _mock_executor
    if _mock_executor is None:
        try:
            from ..mock.mock_integration import MockExecutor

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


def execute_kubectl_logs_parallel(
    kubectl_commands, host, connector, step, flow, show_table=False
):
    """Execute kubectl logs commands in parallel and return accumulated results."""
    if not kubectl_commands:
        return "", [], 0.0

    def execute_single_kubectl_command(command):
        """Execute a single kubectl logs command and return structured result."""
        try:
            output, error, duration = execute_command(command, host, connector)
            parsed_output = parse_curl_output(output, error)
            raw_output = parsed_output.get("raw_output", "")

            # Extract pod name for logging
            pod_name = None
            if command.startswith("kubectl logs") or command.startswith(
                "oc logs"
            ):
                parts = command.split()
                try:
                    pod_name = parts[2]
                except IndexError:
                    pod_name = None

            # Save kubectl logs if applicable
            if parsed_output.get("is_kubectl_logs"):
                save_kubectl_logs(
                    parsed_output.get("raw_output"),
                    host,
                    f"{step.row_idx}_{pod_name}" if pod_name else step.row_idx,
                    getattr(flow, "test_name", "unknown"),
                )

            if not show_table:
                logger.info(f"[CALLFLOW] Built command: {command}")
                logger.info(
                    f"[CALLFLOW] Executing kubectl logs command on host {host}..."
                )
                logger.debug(
                    f"[CALLFLOW] Command executed in {duration:.2f} seconds"
                )
                logger.info(f"[CALLFLOW] Output from server: {output}")
                if error:
                    logger.info(f"[CALLFLOW] HTTP Output from server: {error}")

                # Extract and display epochSecond timestamps for kubectl logs
                if raw_output:
                    _extract_and_display_epoch_timestamps(raw_output)

            return {
                "raw_output": raw_output,
                "pod_name": pod_name,
                "duration": duration,
                "success": True,
            }
        except Exception as e:
            logger.error(
                f"[CALLFLOW] Error executing kubectl command {command}: {e}"
            )
            return {
                "raw_output": "",
                "pod_name": None,
                "duration": 0.0,
                "success": False,
            }

    # Execute all kubectl logs commands in parallel
    accumulated_raw_output = ""
    pod_names = []
    total_duration = 0.0

    with ThreadPoolExecutor(
        max_workers=min(len(kubectl_commands), 10)
    ) as executor:
        future_to_command = {
            executor.submit(execute_single_kubectl_command, cmd): cmd
            for cmd in kubectl_commands
        }

        for future in as_completed(future_to_command):
            result = future.result()
            if result["success"]:
                accumulated_raw_output += result["raw_output"]
                pod_names.append(result["pod_name"])
                total_duration = max(total_duration, result["duration"])
            else:
                command = future_to_command[future]
                if not show_table:
                    logger.warning(
                        f"[CALLFLOW] Failed to execute kubectl command: {command}"
                    )

    return accumulated_raw_output, pod_names, total_duration


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
    if connector is not None and getattr(connector, "use_ssh", False):
        host_cfg = connector.get_host_config(host)
        return getattr(host_cfg, "namespace", None) if host_cfg else None
    else:
        try:
            # Look for config in project root first, then fallback to package directory
            config_path = os.path.join(os.getcwd(), "config", "hosts.json")
            if not os.path.exists(config_path):
                # Try absolute path from module location
                config_path = os.path.join(
                    os.path.dirname(
                        os.path.dirname(
                            os.path.dirname(os.path.dirname(__file__))
                        )
                    ),
                    "config",
                    "hosts.json",
                )

            with open(config_path, "r") as f:
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
    test_context: Optional[Dict[str, Any]] = None,
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
        logger.debug(f"Original URL: {safe_str(url)}")
        logger.debug(f"Service map for substitution: {svc_map}")
        substituted_url = replace_placeholder_in_command(
            safe_str(url), svc_map
        )
        logger.debug(f"Substituted URL: {substituted_url}")
        ssh_cmd, _ = build_ssh_k8s_curl_command(
            namespace=namespace or "default",
            container=pod_exec,
            url=substituted_url,
            method=method,
            headers={k: safe_str(v) for k, v in headers.items()},
            payload=safe_str(request_payload),
            payloads_folder="payloads",
            cli_type=cli_type,
            test_context=test_context,
        )
        return ssh_cmd
    except Exception as e:
        logger.error(f"Failed to build SSH curl command: {e}")
        return None


def build_kubectl_logs_command(
    command, namespace, connector, host, host_cli_map=None
):
    """Build kubectl logs command with dynamic pod name resolution and file-based capture."""
    match = re.search(r"\{([^}]+)\}", command)
    if not match:
        # If no placeholder, generate file-based capture command directly
        return _generate_logs_capture_command(
            command, namespace, connector, host
        )

    to_search_pod_name = match.group(1)

    # Check if we're in mock mode - if so, skip pod name resolution
    if (
        hasattr(connector, "execution_mode")
        and connector.execution_mode == "mock"
    ):
        logger.debug(
            f"Mock mode: skipping pod name resolution for '{to_search_pod_name}'"
        )
        # In mock mode, generate a mock pod name and return single command
        mock_pod_name = f"{to_search_pod_name}-mock123-abc456"
        mock_command = command.replace(
            f"{{{to_search_pod_name}}}", mock_pod_name
        )
        logger.debug(f"Mock mode: using mock pod name '{mock_pod_name}'")
        return [
            _generate_logs_capture_command(
                mock_command, namespace, connector, host
            )
        ]

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
    if connector is not None and getattr(connector, "use_ssh", False):
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

    # Filter out provgw pods using app.kubernetes.io/instance label when NF is SLF
    # Load config to check if this is an SLF deployment
    config_file = (
        getattr(connector, "config_file", "config/hosts.json")
        if connector
        else "config/hosts.json"
    )

    try:
        with open(config_file, "r") as f:
            config = json.load(f)
        nf_name = config.get("nf_name", "")

        # If this is SLF deployment, filter out provgw pods using label-based filtering
        if "SLF" in nf_name.upper():
            original_count = len(pod_names)
            filtered_pods = []

            for pod in pod_names:
                try:
                    # Get the app.kubernetes.io/instance label for the pod
                    label_command = f"{cli_type} get pod {pod} -o jsonpath='{{.metadata.labels.app\\.kubernetes\\.io/instance}}'"
                    if namespace:
                        label_command = f"{cli_type} get pod {pod} -n {namespace} -o jsonpath='{{.metadata.labels.app\\.kubernetes\\.io/instance}}'"

                    if connector is not None and getattr(
                        connector, "use_ssh", False
                    ):
                        # Use SSH to run the command on remote host
                        result = connector.run_command(label_command, [host])
                        res = result.get(host, {"output": "", "error": ""})
                        instance_label = res["output"].strip()
                        command_success = not res.get("error", "")
                    else:
                        # Run locally
                        result = subprocess.run(
                            label_command,
                            shell=True,
                            capture_output=True,
                            text=True,
                            timeout=10,
                        )
                        instance_label = result.stdout.strip()
                        command_success = result.returncode == 0

                    if command_success:
                        # Include pod if instance label is not "provgw" (slf pods return namespace)
                        if instance_label != "provgw":
                            filtered_pods.append(pod)
                    else:
                        # If kubectl command fails, include the pod to be safe
                        filtered_pods.append(pod)

                except (
                    subprocess.TimeoutExpired,
                    subprocess.SubprocessError,
                    Exception,
                ):
                    # If there's any error, include the pod to be safe
                    filtered_pods.append(pod)

            pod_names = filtered_pods
            filtered_count = len(pod_names)
            if original_count > filtered_count:
                logger.debug(
                    f"SLF deployment detected: Filtered out {original_count - filtered_count} "
                    f"provgw pods for '{to_search_pod_name}' search. Remaining pods: {pod_names}"
                )
    except Exception as e:
        logger.debug(f"Could not load config for provgw filtering: {e}")

    if not pod_names:
        logger.error(
            f"No pod found matching '{to_search_pod_name}' on host {host}"
        )
        return None

    # Generate file-based capture commands for each pod
    commands = []
    for pod_name in pod_names:
        resolved_command = command.replace(
            f"{{{to_search_pod_name}}}", pod_name
        )
        capture_command = _generate_logs_capture_command(
            resolved_command, namespace, connector, host
        )
        commands.append(capture_command)

    return commands


def _generate_logs_capture_command(base_command, namespace, connector, host):
    """Generate kubectl logs command with real-time capture using configurable --since duration."""
    # Load kubectl_logs_settings from config
    config_file = (
        getattr(connector, "config_file", "config/hosts.json")
        if connector
        else "config/hosts.json"
    )

    try:
        with open(config_file, "r") as f:
            config = json.load(f)
        kubectl_settings = config.get("kubectl_logs_settings", {})
        capture_duration = kubectl_settings.get("capture_duration", 30)
        since_duration = kubectl_settings.get("since_duration", "1s")
    except Exception as e:
        logger.warning(
            f"Failed to load kubectl_logs_settings: {e}, using defaults"
        )
        capture_duration = 30
        since_duration = "1s"

    # Check if this is a kubectl logs command
    if "logs" in base_command:
        # Remove any existing tail parameters to avoid conflicts
        parts = base_command.split()
        filtered_parts = []
        skip_next = False

        for i, part in enumerate(parts):
            if skip_next:
                skip_next = False
                continue
            if part == "--tail" or part.startswith("--tail="):
                if part == "--tail" and i + 1 < len(parts):
                    skip_next = True
                continue
            filtered_parts.append(part)

        # Reconstruct command without --tail
        base_command = " ".join(filtered_parts)

        # Add -f and --since flags with configurable duration
        follow_command = base_command.replace(
            "logs", f"logs -f --since={since_duration}", 1
        )

        # Create the capture command with background process
        capture_command = (
            f"{follow_command} & sleep {capture_duration}; kill $!"
        )

        logger.debug(
            f"Generated kubectl logs capture command with since={since_duration}, duration={capture_duration}s: {capture_command}"
        )
        return capture_command.strip()

    return base_command


def build_command_for_step(
    step_data,
    svc_map,
    placeholder_pattern,
    namespace,
    host_cli_map,
    host,
    connector,
    flow=None,
    step=None,
):  # host_cli_map now required
    """Build the appropriate command for a test step, with pod_mode support."""
    import json
    import os

    from ..utils.curl_builder import build_pod_mode

    url = step_data["url"]
    command = step_data["command"]

    # Check for pod_mode in config/hosts.json
    pod_mode = False
    # Look for config in project root first, then fallback to package directory
    config_paths = [
        os.path.join(
            os.getcwd(), "config", "hosts.json"
        ),  # Project root config
        os.path.join(
            os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            ),
            "config",
            "hosts.json",
        ),  # Absolute path from module
    ]

    config_found = False
    for config_path in config_paths:
        try:
            if os.path.exists(config_path):
                with open(config_path, "r") as f:
                    config = json.load(f)
                    pod_mode = config.get("pod_mode", False)
                    config_found = True
                    break
        except Exception as e:
            continue

    if not config_found:
        logger.warning(
            f"Could not read pod_mode from config: No valid config file found in {config_paths}"
        )

    # Create test context for NRF tracking
    test_context = None
    if flow and step:
        test_context = {
            "test_name": getattr(flow, "test_name", None),
            "sheet": getattr(flow, "sheet", None),
            "row_idx": getattr(step, "row_idx", None),
            "session_id": f"{getattr(flow, 'sheet', 'default')}_{getattr(flow, 'test_name', 'default')}",
        }
        logger.debug(f"Created test context: {test_context}")

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
            logger.debug(f"Pod mode - Original URL: {safe_str(url)}")
            logger.debug(f"Pod mode - Service map for substitution: {svc_map}")
            substituted_url = replace_placeholder_in_command(
                safe_str(url), svc_map
            )
            logger.debug(f"Pod mode - Substituted URL: {substituted_url}")
        curl_cmd, _ = build_pod_mode(
            substituted_url,
            method=method,
            headers=headers,
            payload=payload,
            payloads_folder=payloads_folder,
            extra_curl_args=extra_curl_args,
            test_context=test_context,
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
            test_context=test_context,
        )  # host_cli_map passed
    elif command and (
        command.startswith("kubectl") or command.startswith("oc")
    ):
        # update method to KUBECTL in step_data method
        step_data["method"] = "KUBECTL"
        return build_kubectl_logs_command(
            command, namespace, connector, host, host_cli_map
        )
    else:
        logger.warning(f"URL is required for command execution: {command}")
        return None


def execute_command(command, host, connector):
    """Execute a command and return output, error, and duration. Handles file-based kubectl logs."""
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

    if connector is not None and getattr(connector, "use_ssh", False):
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
        connector, "mock_server_url", "http://localhost:8082"
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

    # Get row index from connector if available
    row_idx = getattr(connector, "_current_row_idx", None)

    # Execute mock command
    try:
        return mock_executor.execute_mock_command(
            command, host, sheet_name, test_name, row_idx
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

    # Handle JSON file loading for Response_Payload (NRF scenario)
    if (
        response_payload
        and isinstance(response_payload, str)
        and response_payload.strip().endswith(".json")
    ):
        response_payload = _load_response_payload_file(
            response_payload.strip()
        )

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
        response_headers=response_headers,  # Add headers from HTTP response
        request_payload=request_payload,  # Add request payload for reference
        response_payload=response_payload,  # Add response payload from server
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
    parsed_output = {}
    output = None
    error = None
    pod_names = []

    for host in target_hosts:
        svc_map = svc_maps.get(host, {})
        namespace = resolve_namespace(connector, host)

        # Set sheet and test context for mock execution
        if (
            hasattr(connector, "execution_mode")
            and connector.execution_mode == "mock"
        ):
            connector._current_sheet = getattr(flow, "sheet", None)
            connector._current_test = getattr(flow, "test_name", None)
            connector._current_row_idx = getattr(step, "row_idx", None)
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
            flow=flow,
            step=step,
        )

        if isinstance(commands, str):
            commands = [commands]
        elif commands is None:
            commands = []

        accumulated_raw_output = ""
        duration = 0.0  # Initialize duration in case no commands are executed
        command = None  # Initialize command variable

        # Separate kubectl logs commands from other commands
        kubectl_commands = []
        other_commands = []

        # Filter out empty commands and separate by type
        for cmd in commands:
            if not cmd:
                if not show_table:
                    logger.warning(
                        f"[CALLFLOW] Command could not be built for host {host}, step {getattr(step, 'step_name', 'N/A')}. Skipping."
                    )
                continue

            if cmd.startswith("kubectl logs") or cmd.startswith("oc logs"):
                kubectl_commands.append(cmd)
            else:
                other_commands.append(cmd)

        # Execute kubectl logs commands in parallel if any exist
        if kubectl_commands:
            if not show_table:
                logger.info(
                    f"[CALLFLOW] Executing {len(kubectl_commands)} kubectl logs commands in parallel on host {host}..."
                )
                logger.info(
                    f"[CALLFLOW] Service map for host {host}: {svc_map}"
                )

            kubectl_raw_output, kubectl_pod_names, kubectl_duration = (
                execute_kubectl_logs_parallel(
                    kubectl_commands, host, connector, step, flow, show_table
                )
            )
            accumulated_raw_output += kubectl_raw_output
            pod_names.extend(kubectl_pod_names)
            duration = max(duration, kubectl_duration)

        # Execute other commands sequentially (preserve existing behavior)
        for command in other_commands:
            if not show_table:
                logger.info(f"[CALLFLOW] Built command: {command}")
                logger.info(
                    f"[CALLFLOW] Service map for host {host}: {svc_map}"
                )
                logger.info(f"[CALLFLOW] Executing command on host {host}...")

            output, error, cmd_duration = execute_command(
                command, host, connector
            )
            parsed_output = parse_curl_output(output, error)
            duration = max(duration, cmd_duration)

            # Get the raw_output and append to accumulated string
            raw_output = parsed_output.get("raw_output", "")
            accumulated_raw_output += raw_output

            # For non-kubectl commands, append None to pod_names to maintain consistency
            pod_names.append(None)

            if not show_table:
                logger.debug(
                    f"[CALLFLOW] Command executed in {cmd_duration:.2f} seconds"
                )
                logger.info(f"[CALLFLOW] Output from server: {output}")
                if error:
                    logger.info(f"[CALLFLOW] HTTP Output from server: {error}")

                # Add pattern match string to CALLFLOW output
                pattern = step.pattern_match
                if pattern:
                    logger.info(f"[CALLFLOW] Pattern to match: {pattern}")

        # update parsed_output with accumulated raw output
        parsed_output["raw_output"] = copy.copy(accumulated_raw_output)

        # Validate this pod's logs
        final_result = validate_and_create_result(
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
