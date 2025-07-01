import json
from typing import Any, Dict, List, Optional

import pandas as pd

from curl_builder import build_curl_command, build_ssh_k8s_curl_command


def _build_command_for_host(
    row: pd.Series,
    host: str,
    svc_map: Dict[str, str],
    placeholder_pattern,
    namespace: Optional[str],
    use_ssh: bool,
    substitute_placeholders_func,
) -> str:
    """Build command for a specific host, handling both SSH and non-SSH cases."""
    import logging

    logger = logging.getLogger("TestPilot")

    command = row.get("Command")
    request_payload = row.get("Request Payload") if "Request Payload" in row else None
    method = row.get("Method", "GET") if "Method" in row else "GET"
    url = row.get("URL") if "URL" in row else None
    headers = {}

    if "Headers" in row and pd.notna(row["Headers"]):
        try:
            headers = json.loads(row["Headers"])
        except Exception:
            headers = {}

    if url:
        try:
            # Substitute placeholders in URL, headers, and payload
            substituted_url = substitute_placeholders_func(
                url, svc_map, placeholder_pattern
            )
            substituted_headers = {
                k: substitute_placeholders_func(str(v), svc_map, placeholder_pattern)
                for k, v in headers.items()
            }
            substituted_payload = (
                substitute_placeholders_func(
                    request_payload, svc_map, placeholder_pattern
                )
                if request_payload
                else None
            )

            # Build command based on SSH or non-SSH mode
            if use_ssh:
                container = "appinfo"  # TODO: Make this configurable
                ssh_cmd, _ = build_ssh_k8s_curl_command(
                    namespace=namespace or "default",
                    container=container,
                    url=substituted_url,
                    method=method,
                    headers=substituted_headers,
                    payload=substituted_payload,
                    payloads_folder="payloads",
                )
                return ssh_cmd
            else:
                curl_cmd, _ = build_curl_command(
                    url=substituted_url,
                    method=method,
                    headers=substituted_headers,
                    payload=substituted_payload,
                    payloads_folder="payloads",
                )
                return curl_cmd
        except Exception as e:
            logger.error(f"[DRY RUN] Failed to build command: {e}")
            return f"[ERROR] {e}"
    else:
        # No URL, just substitute placeholders in command
        return substitute_placeholders_func(command, svc_map, placeholder_pattern)


def _create_dry_run_result(
    sheet: str, test_name: str, host: str, command: str, method: str = "GET"
) -> Dict[str, Any]:
    """Create a dry run result dictionary."""
    return {
        "sheet": sheet,
        "test_name": test_name,
        "host": host,
        "duration": 0.0,
        "result": "DRY-RUN",
        "command": command,
        "method": method,
    }


def _convert_to_result_object(result: Dict[str, Any]):
    """Convert dictionary to anonymous object for table display."""
    return type(
        "DryRunResult",
        (),
        {
            "sheet": result["sheet"],
            "test_name": result["test_name"],
            "host": result["host"],
            "passed": False,
            "duration": result["duration"],
            "result": result["result"],
            "command": result["command"],
            "method": result.get("method", "GET"),  # Default to GET if missing
        },
    )


def dry_run_commands(
    excel_parser,
    valid_sheets,
    connector,
    target_hosts,
    svc_maps,
    placeholder_pattern,
    show_table=True,
    display_mode="blessed",
):
    import logging
    from test_pilot import print_results_table, substitute_placeholders

    logger = logging.getLogger("TestPilot")
    logger.debug("--- DRY RUN MODE ENABLED ---")
    dry_run_results = []

    # Initialize dashboard if needed
    dashboard = None
    if show_table:
        try:
            from blessed_dashboard import create_blessed_dashboard
            
            if display_mode == "blessed":
                dashboard = create_blessed_dashboard(mode="full", max_visible_rows=20)
            elif display_mode == "progress":
                dashboard = create_blessed_dashboard(mode="progress")
            else:  # simple
                dashboard = create_blessed_dashboard(mode="simple")
            
            dashboard.start()
            
        except ImportError as e:
            logger.warning(f"Blessed dashboard not available: {e}")
            # Fallback to simple print-based display
            from console_table_fmt import LiveProgressTable
            dashboard = LiveProgressTable()
    for sheet in valid_sheets:
        df = excel_parser.get_sheet(sheet)
        logger.debug(f"Sheet '{sheet}' columns: {list(df.columns)}")
        if not df.empty:
            logger.debug(f"Sheet '{sheet}' first row: {df.iloc[0].to_dict()}")

        for row_idx, row in df.iterrows():
            command = row.get("Command")
            test_name = row.get("Test_Name", "") if "Test_Name" in row else ""
            method = (
                row.get("Method", "GET") if "Method" in row else "GET"
            )  # Extract method from row

            if pd.notna(command):
                # Determine hosts to process
                hosts_to_process = (
                    target_hosts
                    if connector.use_ssh
                    else [target_hosts[0] if target_hosts else "local"]
                )

                for host in hosts_to_process:
                    svc_map = svc_maps.get(host, {})

                    # Get namespace for SSH connections
                    namespace = None
                    if connector.use_ssh:
                        host_cfg = connector.get_host_config(host)
                        namespace = (
                            getattr(host_cfg, "namespace", None) if host_cfg else None
                        )

                    # Build command
                    substituted = _build_command_for_host(
                        row,
                        host,
                        svc_map,
                        placeholder_pattern,
                        namespace,
                        connector.use_ssh,
                        substitute_placeholders,
                    )

                    logger.debug(
                        f"[DRY RUN] Would run command on [{host}]: {substituted}"
                    )

                    # Create and store result with method
                    result = _create_dry_run_result(
                        sheet, test_name, host, substituted, method
                    )
                    dry_run_results.append(result)

                    # Update dashboard if enabled
                    if dashboard:
                        dashboard.add_result(_convert_to_result_object(result))
    
    # Print final summary if dashboard is enabled
    if dashboard:
        dashboard.print_final_summary()

    logger.debug("--- END DRY RUN ---")
    connector.close_all()
