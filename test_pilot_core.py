# =============================================================================
# test_pilot_core.py (FIXED VERSION)
# =============================================================================

import json
import re
import subprocess
import sys
import time
import os
from utils.resource_map_utils import map_localhost_url
from utils.myutils import prettify_curl_output, replace_placeholder_in_command
from utils.kubectl_logs_search import search_in_custom_output
from typing import Any, Dict, List, Optional, Tuple, Union

import pandas as pd

from curl_builder import build_ssh_k8s_curl_command
from logger import get_failure_logger, get_logger
from response_parser import parse_curl_output
from test_result import TestFlow, TestResult, TestStep
from validation_engine import ValidationContext, ValidationDispatcher

# Python 3.8+ compatibility for Pattern type
if sys.version_info >= (3, 9):
    PatternType = re.Pattern[str]
else:
    from typing import Pattern

    PatternType = Pattern[str]

logger = get_logger("TestPilot.Core")
failure_logger = get_failure_logger("TestPilot.Failures")


def save_kubectl_logs(raw_output, host, row_idx, test_name, dir_path="kubectl_logs"):
    os.makedirs(dir_path, exist_ok=True)
    safe_test_name = re.sub(r'[^a-zA-Z0-9_.-]', '_', str(test_name))
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
    if expected_status is not None and pd.notna(expected_status):
        expected_status = int(expected_status)
    else:
        expected_status = None
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
        )
        cli_type = host_cli_map.get(host, "kubectl") if host_cli_map else "kubectl"
        if cli_type == "oc":
            ssh_cmd = ssh_cmd.replace("kubectl", "oc")
        return ssh_cmd
    except Exception as e:
        logger.error(f"Failed to build SSH curl command: {e}")
        return None


def build_kubectl_logs_command(command, namespace, connector, host):
    """Build kubectl logs command with dynamic pod name resolution."""
    match = re.search(r"\{([^}]+)\}", command)
    if not match:
        return command
    to_search_pod_name = match.group(1)
    if namespace:
        find_pod = (
            f"kubectl get pods -n {namespace} | "
            f"grep '{to_search_pod_name}' | "
            f"awk 'NR==1 {{print $1}}'"
        )
    else:
        find_pod = (
            f"kubectl get pods | grep '{to_search_pod_name}' | awk 'NR==1 {{print $1}}'"
        )
    if connector.use_ssh:
        result = connector.run_command(find_pod, [host])
        res = result.get(host, {"output": "", "error": ""})
        pod_name = res["output"].strip()
    else:
        result = subprocess.run(find_pod, shell=True, capture_output=True, text=True)
        pod_name = result.stdout.strip()
    if not pod_name:
        logger.error(f"No pod found matching '{to_search_pod_name}' on host {host}")
        return None
    return command.replace(f"{{{to_search_pod_name}}}", pod_name)


def build_command_for_step(
    step_data, svc_map, placeholder_pattern, namespace, host_cli_map, host, connector
):
    """Build the appropriate command for a test step, with pod_mode support."""
    import os
    import json
    from curl_builder import build_pod_mode

    url = step_data["url"]
    command = step_data["command"]
    
    # Check for pod_mode in config/hosts.json
    pod_mode = False
    config_path = os.path.join(os.path.dirname(__file__), 'config', 'hosts.json')
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
            pod_mode = config.get('pod_mode', False)
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
            step_data, svc_map, placeholder_pattern, namespace, host_cli_map, host
        )
    elif command and (command.startswith("kubectl") or command.startswith("oc")):
        # update method to KUBECTL in step_data method
        step_data["method"] = "KUBCTL"
        return build_kubectl_logs_command(command, namespace, connector, host)
    else:
        logger.warning(f"URL is required for command execution: {command}")
        return None


def execute_command(command, host, connector):
    """Execute a command and return output, error, and duration."""
    if not command:
        return "", "Command build failed", 0.0
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
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        output = result.stdout.strip()
        error = result.stderr.strip()
    duration = time.time() - start_time
    logger.debug(f"Command executed in {duration:.2f} seconds on [{host}]")
    logger.debug(f"Output: {output}")
    if error:
        logger.debug(f"Error: {error}")
    return output, error, duration


def validate_and_create_result(
    step, flow, step_data, parsed_output, output, error, duration, host, command
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
    actual_status = parsed_output.get("http_status") or parsed_output.get("status_code")
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
        pattern_match=(str(pattern_match) if pattern_match is not None else None),
        pattern_found=result.details.get("pattern_found") if result.details else None,
        passed=result.passed,
        fail_reason=result.fail_reason,
        test_name=flow.test_name,
        duration=duration,
        method=method,
    )
    return test_result


def log_test_result(test_result: TestResult, flow: TestFlow, step: TestStep) -> None:
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
):
    step_data = extract_step_data(step)
    if step_data["command"] is None or pd.isna(step_data["command"]):
        return

    step_data["save_key"] = step.other_fields.get("Save_As")
    manage_workflow_context(flow, step_data)

    for host in target_hosts:
        svc_map = svc_maps.get(host, {})
        namespace = resolve_namespace(connector, host)
        if not show_table:
            logger.info(f"[CALLFLOW] Host: {host}")
            logger.info(f"[CALLFLOW] Step: {getattr(step, 'step_name', 'N/A')} (Flow: {getattr(flow, 'test_name', 'N/A')})")
            logger.info(f"[CALLFLOW] Substituting placeholders in command: {step_data['command']}")
        command = build_command_for_step(
            step_data,
            svc_map,
            placeholder_pattern,
            namespace,
            host_cli_map,
            host,
            connector,
        )
        if not command:
            if not show_table:
                logger.warning(f"[CALLFLOW] Command could not be built for host {host}, step {getattr(step, 'step_name', 'N/A')}. Skipping.")
            continue
        if not show_table:
            logger.info(f"[CALLFLOW] Built command: {command}")
            logger.info(f"[CALLFLOW] Executing command on host {host}...")
        output, error, duration = execute_command(command, host, connector)
        if not show_table:
            logger.info(f"[CALLFLOW] Command executed in {duration:.2f}s")
            if len(output) > 5000:
                logger.info(f"[CALLFLOW] Output: {search_in_custom_output(output, step_data['pattern_match'])}")
            else:
                logger.info(f"[CALLFLOW] Server Reponse: {output[:300]}" + ("..." if output and len(output) > 300 else ""))
            if error:
                logger.info(f"[CALLFLOW] Header response:: ") 
                prettify_curl_output(error)
        parsed_output = parse_curl_output(output, error)
        if parsed_output.get("is_kubectl_logs"):
            # save the response from server to a json file, including test name in filename
            save_kubectl_logs(
                parsed_output.get("raw_output"),
                host,
                step.row_idx,
                getattr(flow, "test_name", "unknown")
            )

        test_result = validate_and_create_result(
            step, flow, step_data, parsed_output, output, error, duration, host, command
        )
        test_results.append(test_result)
        step.result = test_result
        if not show_table:
            logger.info(f"[CALLFLOW] Result: {test_result.passed} | Expected: {step_data.get('expected_status', 'N/A')} | Actual: {getattr(test_result, 'actual_status', 'N/A')}")
        if show_table and dashboard is not None:
            dashboard.add_result(test_result)

        log_test_result(test_result, flow, step)
        # introduced delay between each test
        time.sleep(1)
