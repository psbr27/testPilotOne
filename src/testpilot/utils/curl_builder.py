import json
import logging
import os
import re
import shlex
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger("CurlBuilder")


def build_curl_command(
    url: str,
    method: str = "GET",
    headers: Optional[Dict[str, str]] = None,
    payload: Optional[Union[str, Dict, List]] = None,
    payloads_folder: str = "payloads",
    extra_curl_args: Optional[List[str]] = None,
    direct_json_allowed: bool = True,
    test_context: Optional[Dict[str, Any]] = None,
) -> Tuple[str, Optional[str]]:
    """
    Returns a tuple (curl_command_str, resolved_payload_str) for local execution.
    If payload is a filename (endswith .json), loads from payloads_folder.
    Otherwise, treats as direct JSON string (if allowed).

    Args:
        test_context: Optional test execution context for NRF tracking.
                     Should contain: test_name, sheet, row_idx, session_id
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
                raise FileNotFoundError(
                    f"Payload file not found: {payload_path}"
                )
            try:
                with open(payload_path, "r", encoding="utf-8") as f:
                    resolved_payload = f.read().strip()
            except (IOError, OSError) as e:
                logger.error(
                    f"Failed to read payload file {payload_path}: {e}"
                )
                raise
        elif direct_json_allowed:
            # Try to pretty-print if valid JSON, else use as-is
            if isinstance(payload, (dict, list)):
                try:
                    resolved_payload = json.dumps(
                        payload, separators=(",", ":")
                    )
                except (TypeError, ValueError) as e:
                    logger.warning(f"Failed to serialize payload to JSON: {e}")
                    resolved_payload = str(payload)
            elif isinstance(payload, str):
                try:
                    # Validate and reformat JSON string
                    parsed = json.loads(payload)
                    resolved_payload = json.dumps(
                        parsed, separators=(",", ":")
                    )
                except (json.JSONDecodeError, TypeError) as e:
                    logger.debug(
                        f"Payload is not valid JSON, using as-is: {e}"
                    )
                    resolved_payload = payload.strip()
            else:
                resolved_payload = str(payload)
        else:
            resolved_payload = None
        if resolved_payload and resolved_payload != "nan":
            payload_arg = f"-d {shlex.quote(resolved_payload)}"

    # Fetch nf_name from config/hosts.json if available
    nf_name = "SLF"  # Default value
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

    for config_path in config_paths:
        try:
            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    nf_name = config.get("nf_name", "SLF")
                    break
        except (IOError, OSError, json.JSONDecodeError) as e:
            continue

    # If we couldn't find or parse any config file, log the error
    if nf_name == "SLF":
        logger.debug(
            f"Using default nf_name 'SLF'. Could not find valid config in: {config_paths}"
        )

    # Handle NRF-specific operations
    nrf_variants = {"ocnrf", "nrf"}
    if nf_name.lower() in nrf_variants:
        try:
            # Import NRF handler only when needed (lazy import)
            from testpilot.utils.nrf import handle_nrf_operation

            # Delegate to NRF-specific handler
            modified_url = handle_nrf_operation(
                url=url,
                method=method,
                payload=resolved_payload,
                test_context=test_context,
                nf_name=nf_name,
            )

            if modified_url:
                url = modified_url
                logger.debug(f"NRF handler modified URL to: {url}")

        except ImportError as e:
            # Fallback to legacy behavior if NRF module not available
            logger.warning(
                f"NRF module not available, using legacy handling: {e}"
            )
            if resolved_payload and _should_apply_nf_instance_id_legacy(url):
                try:
                    parsed = json.loads(resolved_payload)
                    nfInstanceId = None
                    if isinstance(parsed, dict):
                        nfInstanceId = parsed.get("nfInstanceId", None)
                    elif isinstance(parsed, list):
                        for item in parsed:
                            if (
                                isinstance(item, dict)
                                and "nfInstanceId" in item
                            ):
                                nfInstanceId = item["nfInstanceId"]
                                break
                    if nfInstanceId:
                        url = f"{url}{nfInstanceId}"
                        logger.debug(
                            f"Legacy: Appending nfInstanceId to URL: {nfInstanceId}"
                        )
                except (json.JSONDecodeError, TypeError):
                    pass

    # Handle headers - escape each header value to prevent injection
    header_args = []
    for k, v in headers.items():
        # Escape both key and value for safety
        safe_header = f"{k}: {v}"
        header_args.append(f"-H {shlex.quote(safe_header)}")

    header_str = " ".join(header_args)
    if not header_str:
        header_str = "-H 'Content-Type: application/json'"  # Default header if none provided

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
    cli_type: str = "kubectl",
    test_context: Optional[Dict[str, Any]] = None,
) -> Tuple[str, Optional[str]]:
    """
    Returns a kubectl/oc exec command that runs curl inside a pod via SSH.

    Args:
        cli_type: The CLI tool to use ('kubectl' or 'oc'). Defaults to 'kubectl'.
        test_context: Optional test execution context for NRF tracking.
    """
    curl_cmd, resolved_payload = build_curl_command(
        url,
        method=method,
        headers=headers,
        payload=payload,
        payloads_folder=payloads_folder,
        extra_curl_args=extra_curl_args,
        test_context=test_context,
    )
    # Find pod and exec curl inside - escape all user inputs
    safe_container = shlex.quote(container)
    safe_namespace = shlex.quote(namespace)

    # Build pod pattern safely
    pod_pattern = f"{container}-[a-z0-9]+-[a-z0-9]+$"
    safe_pod_pattern = shlex.quote(pod_pattern)

    # Build kubectl/oc commands with proper escaping
    pod_find = f"{cli_type} get po -n {safe_namespace} | awk '{{print $1}}' | grep -E {safe_pod_pattern} | head -n 1"

    # Note: curl_cmd is already escaped from build_curl_command
    exec_cmd = f"{pod_find} | xargs -I{{}} {cli_type} exec -it {{}} -n {safe_namespace} -c {safe_container} -- {curl_cmd}"
    return exec_cmd, resolved_payload


def build_pod_mode(
    url: str,
    method: str = "GET",
    headers: Optional[Dict[str, str]] = None,
    payload: Optional[Union[str, Dict, List]] = None,
    payloads_folder: str = "payloads",
    extra_curl_args: Optional[List[str]] = None,
    test_context: Optional[Dict[str, Any]] = None,
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
        test_context=test_context,
    )
    return curl_cmd, resolved_payload


def _should_apply_nf_instance_id_legacy(url: str) -> bool:
    """
    Legacy validation for URL pattern to apply nfInstanceId.

    Rules:
    1. nfInstanceId shall be used only when the URL is nnrf-nfm/v1/nf-instances/
    2. nnrf-nfm/v1/nf-instances? don't add nfInstanceId when URL has '?'

    Args:
        url: The URL to validate

    Returns:
        True if nfInstanceId should be applied, False otherwise
    """
    # Check if URL contains the required NRF pattern
    if "nnrf-nfm/v1/nf-instances" not in url:
        return False

    # Rule 1a: Don't add nfInstanceId when URL has query parameters (?)
    if "?" in url:
        logger.debug(
            f"Legacy: URL contains query parameters, skipping nfInstanceId: {url}"
        )
        return False

    # Rule 1: Only apply to nnrf-nfm/v1/nf-instances/ URLs (must end with / or be exact match)
    if (
        url.endswith("nnrf-nfm/v1/nf-instances")
        or "nnrf-nfm/v1/nf-instances/" in url
    ):
        return True

    return False
