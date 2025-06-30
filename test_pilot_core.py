# =============================================================================
# test_pilot_core.py (FIXED VERSION)
# =============================================================================

import json
import pandas as pd
import subprocess
import re
import time
from response_parser import parse_curl_output, validate_test_result
from test_result import TestResult
from curl_builder import build_ssh_k8s_curl_command
from logger import get_logger

logger = get_logger("TestPilot.Core")

def safe_str(val):

    if val is None or (isinstance(val, float) and pd.isna(val)):
        return ""
    return str(val)

def substitute_placeholders(command, svc_map, placeholder_pattern):

    def repl(match):
        key = match.group(1)
        return svc_map.get(key, match.group(0))
    return placeholder_pattern.sub(repl, command)

def extract_step_data(step):
    """Extract and prepare all data from a TestStep object."""
    command = step.other_fields.get("Command")
    from_excel_response_payload = step.other_fields.get("Response_Payload")
    expected_status = step.expected_status
    if expected_status is not None and pd.notna(expected_status):
        expected_status = int(expected_status)
    else:
        expected_status = None
    pattern_match = step.pattern_match
    if pattern_match is None or (isinstance(pattern_match, float) and pd.isna(pattern_match)):
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

def manage_workflow_context(flow, step_data):
    method = step_data["method"]
    request_payload = step_data["request_payload"]
    if method.upper() in ["PUT", "POST"]:
        # This needs to be handled differently - pass save_key in step_data
        save_key = step_data.get("save_key") or "put_payload"
        if request_payload:
            flow.context[save_key] = request_payload

def resolve_namespace(connector, host):
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
                        host_cfg.get("name") == connect_to or 
                        host_cfg.get("hostname") == connect_to
                    ):
                        return host_cfg.get("namespace")
            elif isinstance(hosts, dict) and connect_to:
                host_cfg = hosts.get(connect_to)
                if isinstance(host_cfg, dict):
                    return host_cfg.get("namespace")
        except Exception as e:
            logger.warning(f"Could not fetch namespace from config: {e}")
        return None

def build_url_based_command(step_data, svc_map, placeholder_pattern, namespace, host_cli_map, host):
    """Build curl command for URL-based API calls."""
    url = step_data["url"]
    method = step_data["method"]
    headers = step_data["headers"]
    request_payload = step_data["request_payload"]
    pod_exec = step_data["pod_exec"]
    
    try:
        substituted_url = substitute_placeholders(safe_str(url), svc_map, placeholder_pattern)
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
        find_pod = f"kubectl get pods -n {namespace} | grep '{to_search_pod_name}' | awk '{{print $1}}'"
    else:
        find_pod = f"kubectl get pods | grep '{to_search_pod_name}' | awk '{{print $1}}'"
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

def build_command_for_step(step_data, svc_map, placeholder_pattern, namespace, host_cli_map, host, connector):
    """Build the appropriate command for a test step."""
    url = step_data["url"]
    command = step_data["command"]
    if url:
        return build_url_based_command(step_data, svc_map, placeholder_pattern, namespace, host_cli_map, host)
    elif command and (command.startswith("kubectl") or command.startswith("oc")):
        return build_kubectl_logs_command(command, namespace, connector, host)
    else:
        logger.warning(f"URL is required for command execution: {command}")
        return None

def execute_command(command, host, connector):
    """Execute a command and return output, error, and duration."""
    if not command:
        return "", "Command build failed", 0.0
    logger.info(f"Running command on [{host}]: {command}")
    start_time = time.time()
    if connector.use_ssh:
        result = connector.run_command(command, [host])
        res = result.get(host, {"output": "", "error": ""})
        output = res["output"]
        error = res["error"]
    else:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        output = result.stdout.strip()
        error = result.stderr.strip()
    duration = time.time() - start_time
    return output, error, duration

def validate_and_create_result(step, flow, step_data, parsed_output, output, error, duration, host, command):
    """Validate test results and create TestResult object."""
    expected_status = step_data["expected_status"]
    pattern_match = step_data["pattern_match"]
    compare_with_key = step_data["compare_with_key"]
    from_excel_response_payload = step_data["from_excel_response_payload"]
    method = step_data["method"]
    
    passed, fail_reason, pattern_found = validate_test_result(
        parsed_output,
        expected_status=expected_status,
        pattern_match=pattern_match,
        output=output,
        compare_with_payload=(
            flow.context.get(compare_with_key) if compare_with_key 
            else from_excel_response_payload
        ),
        compare_with_key=compare_with_key,
        method=method,
    )
    
    test_result = TestResult(
        sheet=flow.sheet,
        row_idx=step.row_idx,
        host=host,
        command=command,
        output=output,
        error=error,
        expected_status=expected_status,
        actual_status=(
            parsed_output.get("status_code") if isinstance(parsed_output, dict) and "status_code" in parsed_output
            else None
        ),
        pattern_match=(
            str(pattern_match) if pd.notna(pattern_match) and pattern_match is not None
            else None
        ),
        pattern_found=pattern_found,
        passed=passed,
        fail_reason=fail_reason,
    )
    setattr(test_result, "test_name", flow.test_name)
    setattr(test_result, "duration", duration)
    setattr(test_result, "method", method)
    return test_result

def log_test_result(test_result, flow, step):
    """Log test result with appropriate level."""
    if not test_result.passed:
        logger.error(f"[FAIL][{flow.sheet}][row {step.row_idx}][{test_result.host}] Command: {test_result.command}")
        logger.error(f"Reason: {test_result.fail_reason}")
        logger.error(f"Output: {test_result.output}")
        logger.error(f"Error: {test_result.error}")
    else:
        logger.info(f"[PASS][{flow.sheet}][row {step.row_idx}][{test_result.host}] Command: {test_result.command}")

def process_single_step(step, flow, target_hosts, svc_maps, placeholder_pattern, connector, host_cli_map, test_results, show_table, print_results_table_func):
    step_data = extract_step_data(step)
    if step_data["command"] is None or pd.isna(step_data["command"]):
        return
    
    step_data["save_key"] = step.other_fields.get("Save_As")
    manage_workflow_context(flow, step_data)
    
    for host in target_hosts:
        svc_map = svc_maps.get(host, {})
        namespace = resolve_namespace(connector, host)
        command = build_command_for_step(
            step_data, svc_map, placeholder_pattern, namespace, host_cli_map, host, connector
        )
        if not command:
            continue
        output, error, duration = execute_command(command, host, connector)
        parsed_output = parse_curl_output(output, error)
        test_result = validate_and_create_result(
            step, flow, step_data, parsed_output, output, error, duration, host, command
        )
        test_results.append(test_result)
        step.result = test_result
        if show_table:
            print_results_table_func.add_result(test_result)
        log_test_result(test_result, flow, step)