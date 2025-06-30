import os
import json
import logging

def build_curl_command(
    url,
    method="GET",
    headers=None,
    payload=None,
    payloads_folder="payloads",
    extra_curl_args=None,
    direct_json_allowed=True,
):
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
            with open(payload_path, "r", encoding="utf-8") as f:
                resolved_payload = f.read().strip()
        elif direct_json_allowed:
            # Try to pretty-print if valid JSON, else use as-is
            try:
                resolved_payload = json.dumps(json.loads(payload), separators=(",", ":"))
            except Exception:
                resolved_payload = payload.strip()
        else:
            resolved_payload = None
        if resolved_payload:
            payload_arg = f"-d '{resolved_payload}'"

    # Handle headers
    header_args = [f"-H '{k}: {v}'" for k, v in headers.items()]
    header_str = " ".join(header_args)
    if not header_str:
        header_str = "-H 'Content-Type: application/json'"  # Default header if none provided
    extra_args = " ".join(extra_curl_args)
    curl_cmd = f"curl -v --http2-prior-knowledge -X {method} '{url}' {header_str} {payload_arg} {extra_args}".strip()
    return curl_cmd, resolved_payload


def build_ssh_k8s_curl_command(
    namespace,
    container,
    url,
    method="GET",
    headers=None,
    payload=None,
    payloads_folder="payloads",
    pod_pattern="-[a-z0-9]+-[a-z0-9]+$",
    extra_curl_args=None
):
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
    # Find pod and exec curl inside
    pod_pattern = container + "-[a-z0-9]+-[a-z0-9]+$"
    pod_find = f"kubectl get po -n {namespace} | awk '{{print $1}}' | grep -E '{pod_pattern}'"
    exec_cmd = (
        f"{pod_find} | xargs -I{{}} kubectl exec -it {{}} -n {namespace} -c {container} -- {curl_cmd}"
    )
    return exec_cmd, resolved_payload
