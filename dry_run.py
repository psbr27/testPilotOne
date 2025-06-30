import json
import pandas as pd
from curl_builder import build_curl_command, build_ssh_k8s_curl_command

def dry_run_commands(
    excel_parser, valid_sheets, connector, target_hosts, svc_maps, placeholder_pattern, show_table=True
):
    import logging
    from test_pilot import substitute_placeholders, print_results_table
    logger = logging.getLogger("TestPilot")
    logger.info("--- DRY RUN MODE ENABLED ---")
    dry_run_results = []
    for sheet in valid_sheets:
        df = excel_parser.get_sheet(sheet)
        logger.debug(f"Sheet '{sheet}' columns: {list(df.columns)}")
        if not df.empty:
            logger.debug(f"Sheet '{sheet}' first row: {df.iloc[0].to_dict()}")
        for row_idx, row in df.iterrows():
            command = row.get("Command")
            test_name = row.get("Test_Name", "") if "Test_Name" in row else ""
            request_payload = (
                row.get("Request Payload") if "Request Payload" in row else None
            )
            method = row.get("Method", "GET") if "Method" in row else "GET"
            url = row.get("URL") if "URL" in row else None
            headers = {}
            if "Headers" in row and pd.notna(row["Headers"]):
                try:
                    headers = json.loads(row["Headers"])
                except Exception:
                    headers = {}
            if pd.notna(command):
                if connector.use_ssh:
                    for host in target_hosts:
                        svc_map = svc_maps.get(host, {})
                        host_cfg = connector.get_host_config(host)
                        namespace = (
                            getattr(host_cfg, "namespace", None) if host_cfg else None
                        )
                        container = "appinfo"
                        if url:
                            try:
                                substituted_url = substitute_placeholders(
                                    url, svc_map, placeholder_pattern
                                )
                                substituted_headers = {
                                    k: substitute_placeholders(str(v), svc_map, placeholder_pattern)
                                    for k, v in headers.items()
                                }
                                substituted_payload = substitute_placeholders(request_payload, svc_map, placeholder_pattern) if request_payload else None
                                ssh_cmd, _ = build_ssh_k8s_curl_command(
                                    namespace=namespace or "default",
                                    container=container,
                                    url=substituted_url,
                                    method=method,
                                    headers=substituted_headers,
                                    payload=substituted_payload,
                                    payloads_folder="payloads",
                                )
                                substituted = ssh_cmd
                            except Exception as e:
                                logger.error(
                                    f"[DRY RUN] Failed to build SSH curl command: {e}"
                                )
                                substituted = f"[ERROR] {e}"
                        else:
                            substituted = substitute_placeholders(
                                command, svc_map, placeholder_pattern
                            )
                        logger.debug(
                            f"[DRY RUN] Would run command on [{host}]: {substituted}"
                        )
                        dry_run_results.append(
                            {
                                "sheet": sheet,
                                "test_name": test_name,
                                "host": host,
                                "duration": 0.0,
                                "result": "DRY-RUN",
                                "command": substituted,
                            }
                        )
                        if show_table:
                            print_results_table(
                                [
                                    type(
                                        "DryRunResult",
                                        (),
                                        {
                                            "sheet": r["sheet"],
                                            "test_name": r["test_name"],
                                            "host": r["host"],
                                            "passed": False,
                                            "duration": r["duration"],
                                            "command": r["command"],
                                        },
                                    )
                                    for r in dry_run_results
                                ]
                            )
                else:
                    host = target_hosts[0] if target_hosts else "local"
                    svc_map = svc_maps.get(host, {})
                    if url:
                        try:
                            substituted_url = substitute_placeholders(
                                url, svc_map, placeholder_pattern
                            )
                            substituted_headers = {
                                k: substitute_placeholders(str(v), svc_map, placeholder_pattern)
                                for k, v in headers.items()
                            }
                            substituted_payload = substitute_placeholders(request_payload, svc_map, placeholder_pattern) if request_payload else None
                            curl_cmd, _ = build_curl_command(
                                url=substituted_url,
                                method=method,
                                headers=substituted_headers,
                                payload=substituted_payload,
                                payloads_folder="payloads",
                            )
                            substituted = curl_cmd
                        except Exception as e:
                            logger.error(f"[DRY RUN] Failed to build curl command: {e}")
                            substituted = f"[ERROR] {e}"
                    else:
                        substituted = substitute_placeholders(
                            command, svc_map, placeholder_pattern
                        )
                    logger.debug(
                        f"[DRY RUN] Would run command on [{host}]: {substituted}"
                    )
                    dry_run_results.append(
                        {
                            "sheet": sheet,
                            "test_name": test_name,
                            "host": host,
                            "duration": 0.0,
                            "result": "DRY-RUN",
                            "command": substituted,
                        }
                    )
                    print_results_table(
                        [
                            type(
                                "DryRunResult",
                                (),
                                {
                                    "sheet": r["sheet"],
                                    "test_name": r["test_name"],
                                    "host": r["host"],
                                    "passed": False,
                                    "duration": r["duration"],
                                    "command": r["command"],
                                },
                            )
                            for r in dry_run_results
                        ]
                    )
    logger.info("--- END DRY RUN ---")
    connector.close_all()
