import json
import logging
import os
import shlex
from typing import Dict, List, Optional, Tuple, Union

logger = logging.getLogger("CurlBuilder")


def build_curl_command(
    url: str,
    method: str = "GET",
    headers: Optional[Dict[str, str]] = None,
    payload: Optional[Union[str, Dict, List]] = None,
    payloads_folder: str = "payloads",
    extra_curl_args: Optional[List[str]] = None,
    direct_json_allowed: bool = True,
) -> Tuple[str, Optional[str]]:
    """
    Returns a tuple (curl_command_str, resolved_payload_str) for local execution.
    If payload is a filename (endswith .json), loads from payloads_folder.
    Otherwise, treats as direct JSON string (if allowed).
    """
    headers = headers or {}
    extra_curl_args = extra_curl_args or []
    resolved_payload = None
    payload_arg = ""

    # Handle payload
    if payload:
        if isinstance(payload, str) and payload.strip().endswith(".json"):
            payload_path = os.path.join(payloads_folder, payload.strip())
            if not os.path.isfile(payload_path):
                raise FileNotFoundError(f"Payload file not found: {payload_path}")
            try:
                with open(payload_path, "r", encoding="utf-8") as f:
                    resolved_payload = f.read().strip()
            except (IOError, OSError) as e:
                logger.error(f"Failed to read payload file {payload_path}: {e}")
                raise
        elif direct_json_allowed:
            # Try to pretty-print if valid JSON, else use as-is
            if isinstance(payload, (dict, list)):
                try:
                    resolved_payload = json.dumps(payload, separators=(",", ":"))
                except (TypeError, ValueError) as e:
                    logger.warning(f"Failed to serialize payload to JSON: {e}")
                    resolved_payload = str(payload)
            elif isinstance(payload, str):
                try:
                    # Validate and reformat JSON string
                    parsed = json.loads(payload)
                    resolved_payload = json.dumps(parsed, separators=(",", ":"))
                except (json.JSONDecodeError, TypeError) as e:
                    logger.debug(f"Payload is not valid JSON, using as-is: {e}")
                    resolved_payload = payload.strip()
            else:
                resolved_payload = str(payload)
        else:
            resolved_payload = None
        if resolved_payload and resolved_payload != 'nan':
            payload_arg = f"-d {shlex.quote(resolved_payload)}"

    # Fetch nf_name from config/hosts.json if available
    try:
        with open("config/hosts.json", "r", encoding="utf-8") as f:
            config = json.load(f)
            nf_name = config.get("nf_name", "SLF")
    except (IOError, OSError, json.JSONDecodeError) as e:
        logger.error(f"Failed to read or parse config/hosts.json: {e}")
        nf_name = "SLF"
        
    # if resolved_payload is true, then try to search for nfInstanceId 
    # in the payload, if that is found then append to safe_url
    if nf_name.lower() != "slf" and resolved_payload:
        parsed = json.loads(resolved_payload)
        nfInstanceId = None
        if isinstance(parsed, dict):
            nfInstanceId = parsed.get("nfInstanceId", None)
        elif isinstance(parsed, list):
            for item in parsed:
                if isinstance(item, dict) and "nfInstanceId" in item:
                    nfInstanceId = item["nfInstanceId"]
                    break
        # For other types, nfInstanceId remains None
        if nfInstanceId:
            url = f"{url}{nfInstanceId}"
            logger.debug(f"Appending nfInstanceId to URL: {nfInstanceId}")
    
    # Handle headers - escape each header value to prevent injection
    header_args = []
    for k, v in headers.items():
        # Escape both key and value for safety
        safe_header = f"{k}: {v}"
        header_args.append(f"-H {shlex.quote(safe_header)}")

    header_str = " ".join(header_args)
    if not header_str:
        header_str = (
            "-H 'Content-Type: application/json'"  # Default header if none provided
        )

    # Escape extra arguments if provided
    extra_args = ""
    if extra_curl_args:
        extra_args = " ".join(shlex.quote(arg) for arg in extra_curl_args)

    # Escape URL and method to prevent injection
    safe_url = shlex.quote(url)
    safe_method = shlex.quote(method)

    curl_cmd = f"curl -v --http2-prior-knowledge -X {safe_method} {safe_url} {header_str} {payload_arg} {extra_args}".strip()
    return curl_cmd, resolved_payload


def build_ssh_k8s_curl_command(
    namespace: str,
    container: str,
    url: str,
    method: str = "GET",
    headers: Optional[Dict[str, str]] = None,
    payload: Optional[Union[str, Dict, List]] = None,
    payloads_folder: str = "payloads",
    pod_pattern: str = "-[a-z0-9]+-[a-z0-9]+$",
    extra_curl_args: Optional[List[str]] = None,
) -> Tuple[str, Optional[str]]:
    """
    Returns a kubectl exec command that runs curl inside a pod via SSH.
    """
    curl_cmd, resolved_payload = build_curl_command(
        url,
        method=method,
        headers=headers,
        payload=payload,
        payloads_folder=payloads_folder,
        extra_curl_args=extra_curl_args,
    )
    # Find pod and exec curl inside - escape all user inputs
    safe_container = shlex.quote(container)
    safe_namespace = shlex.quote(namespace)

    # Build pod pattern safely
    pod_pattern = f"{container}-[a-z0-9]+-[a-z0-9]+$"
    safe_pod_pattern = shlex.quote(pod_pattern)

    # Build kubectl commands with proper escaping
    pod_find = f"kubectl get po -n {safe_namespace} | awk '{{print $1}}' | grep -E {safe_pod_pattern} | head -n 1"

    # Note: curl_cmd is already escaped from build_curl_command
    exec_cmd = f"{pod_find} | xargs -I{{}} kubectl exec -it {{}} -n {safe_namespace} -c {safe_container} -- {curl_cmd}"
    return exec_cmd, resolved_payload


def build_pod_mode(
    url: str,
    method: str = "GET",
    headers: Optional[Dict[str, str]] = None,
    payload: Optional[Union[str, Dict, List]] = None,
    payloads_folder: str = "payloads",
    extra_curl_args: Optional[List[str]] = None,
) -> Tuple[str, Optional[str]]:
    """
    This function is used to build curl command for pod mode
    so the final curl command will be curl command as it is from the excel file
    with out kubectl exec appended to the original curl command
    """
    
    curl_cmd, resolved_payload = build_curl_command(
        url,
        method=method,
        headers=headers,
        payload=payload,
        payloads_folder=payloads_folder,
        extra_curl_args=extra_curl_args,
    )
    return curl_cmd, resolved_payload
