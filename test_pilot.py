#!/usr/bin/env python3
# TestPilot - Test automation framework
# Requires Python 3.8+

import sys

# Check Python version compatibility
if sys.version_info < (3, 8):
    print(f"Error: TestPilot requires Python 3.8 or higher. You are using Python {sys.version}")
    sys.exit(1)

from ssh_connector import SSHConnector
from logger import get_logger
import json
from excel_parser import ExcelParser
import argparse
import re
import datetime
import time
import pandas as pd
import os

from tabulate import tabulate
from console_table_fmt import LiveProgressTable

from dry_run import dry_run_commands
from excel_parser import parse_excel_to_flows


from test_pilot_core import (
    process_single_step,
)

logger = get_logger("TestPilot")


def parse_args():
    parser = argparse.ArgumentParser(description="TestPilot")
    parser.add_argument(
        "-i",
        "--input",
        type=str,
        required=True,
        help="Path to the Excel (.xlsx) file (required)",
    )
    parser.add_argument(
        "-m",
        "--module",
        type=str,
        required=True,
        choices=["otp", "config", "audit"],
        help="Module to use: otp, config, or audit (required)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="If set, only display the commands that would be executed without running them",
    )
    parser.add_argument(
        "-s", "--sheet", type=str, help="Only run tests for the specified sheet name"
    )
    parser.add_argument(
        "-t",
        "--test-name",
        type=str,
        help="Only run the test with this test name in the selected sheet (case sensitive)",
    )
    parser.add_argument(
        "--no-table",
        action="store_true",
        help="Disable table output (default: enabled)",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set log level (default: INFO)",
    )
    parser.add_argument(
        "--no-file-logging",
        action="store_true",
        help="Disable file logging (console only)",
    )
    parser.add_argument(
        "--log-dir",
        default="logs",
        help="Directory for log files (default: logs)",
    )
    return parser.parse_args()


def load_config_and_targets(config_file):
    with open(config_file, "r") as f:
        data = json.load(f)
    connect_to = data.get("connect_to")
    if isinstance(connect_to, str):
        target_hosts = [connect_to]
    elif isinstance(connect_to, list):
        target_hosts = connect_to
    else:
        target_hosts = []
    return data, target_hosts


def load_excel_and_sheets(input_path):
    excel_parser = ExcelParser(input_path)
    valid_sheets = excel_parser.list_valid_sheets()
    logger.debug(f"Valid sheets loaded: {valid_sheets}")
    return excel_parser, valid_sheets


def extract_placeholders(excel_parser, valid_sheets):
    placeholder_pattern = re.compile(r"\{([^}]+)\}")
    placeholders = set()
    for sheet in valid_sheets:
        df = excel_parser.get_sheet(sheet)
        for _, row in df.iterrows():
            command = row.get("Command")
            if pd.notna(command):
                matches = placeholder_pattern.findall(str(command))
                placeholders.update(matches)
    logger.info(f"Unique placeholders found in commands: {sorted(placeholders)}")
    return placeholders, placeholder_pattern


def resolve_service_map_ssh(connector, target_hosts, placeholders):
    svc_maps = {}
    for host in target_hosts:
        conn = connector.connections.get(host)
        if not conn:
            logger.error(
                f"No SSH connection available for host '{host}' (skipping service resolution)"
            )
            continue
        try:
            # Get namespace from host config if present
            host_cfg = connector.get_host_config(host)
            namespace = getattr(host_cfg, "namespace", None) if host_cfg else None
            if namespace:
                kubectl_cmd = f"kubectl get svc -n {namespace} -o json"
            else:
                kubectl_cmd = "kubectl get svc -A -o json"
            stdin, stdout, stderr = conn.exec_command(kubectl_cmd)
            out = stdout.read().decode()
            err = stderr.read().decode()
            if err:
                logger.error(f"kubectl error on host {host}: {err}")
                continue
            import json as _json

            svc_json = _json.loads(out)
            host_map = {}
            for item in svc_json.get("items", []):
                name = item["metadata"]["name"]
                ns = item["metadata"]["namespace"]
                for p in placeholders:
                    if p in name:
                        host_map[p] = f"{name}"
            svc_maps[host] = host_map
        except Exception as e:
            logger.error(f"Failed to resolve services on host {host}: {e}")
    return svc_maps


def resolve_service_map_local(
    placeholders, namespace=None, config_file="config/hosts.json"
):
    import subprocess, json as _json

    svc_maps = {}
    # If namespace is not provided, try to fetch from config using connect_to host
    if namespace is None:
        try:
            with open(config_file, "r") as f:
                data = json.load(f)
            connect_to = data.get("connect_to")
            hosts = data.get("hosts")
            namespace = None
            if isinstance(hosts, list) and connect_to:
                for host_cfg in hosts:
                    if isinstance(host_cfg, dict) and (
                        host_cfg.get("name") == connect_to
                        or host_cfg.get("hostname") == connect_to
                    ):
                        namespace = host_cfg.get("namespace")
                        break
            elif isinstance(hosts, dict) and connect_to:
                host_cfg = hosts.get(connect_to)
                if isinstance(host_cfg, dict):
                    namespace = host_cfg.get("namespace")
        except Exception as e:
            logger.warning(f"Could not fetch namespace from config: {e}")
            namespace = None

    try:
        # Construct kubectl command based on namespace
        if namespace:
            kubectl_cmd = ["kubectl", "get", "svc", "-n", namespace, "-o", "json"]
        else:
            kubectl_cmd = ["kubectl", "get", "svc", "-A", "-o", "json"]
        logger.debug(f"Running local kubectl command: {' '.join(kubectl_cmd)}")
        result = subprocess.run(
            kubectl_cmd,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            logger.error(f"Local kubectl error: {result.stderr}")
            return {}

        svc_json = _json.loads(result.stdout)
        host_map = {}
        for item in svc_json.get("items", []):
            name = item["metadata"]["name"]
            ns = item["metadata"]["namespace"]
            for p in placeholders:
                if p in name:
                    host_map[p] = f"{name}"
        svc_maps[connect_to] = host_map
    except Exception as e:
        logger.error(f"Failed to resolve services locally: {e}")
    return svc_maps


def substitute_placeholders(command, svc_map, placeholder_pattern):
    def repl(match):
        key = match.group(1)
        return svc_map.get(key, match.group(0))

    return placeholder_pattern.sub(repl, command)


def clear():
    os.system("cls" if os.name == "nt" else "clear")


def print_results_table(test_results):
    # Always show: Host, Sheet, Test Name, Method, Result, Duration (s)
    # headers = ["Host", "Sheet", "Test Name", "Method", "Result", "Duration (s)"]
    # table_data = []
    # for r in test_results:
    #     host = getattr(r, "host", "")
    #     sheet = getattr(r, "sheet", "")
    #     test_name = getattr(r, "test_name", "")
    #     method = getattr(r, "method", "") if hasattr(r, "method") else ""
    #     duration = f"{getattr(r, 'duration', 0.0):.2f}"
    #     # Result: DRY-RUN for dry-run, else PASS/FAIL
    #     if hasattr(r, "result") and getattr(r, "result", "") == "DRY-RUN":
    #         result = "DRY-RUN"
    #     else:
    #         result = "PASS" if getattr(r, "passed", False) else "FAIL"
    #     table_data.append([host, sheet, test_name, method, result, duration])
    # # clear()
    # time.sleep(1)
    # print(tabulate(table_data, headers=headers, tablefmt="github"))
    pass


def execute_flows(
    flows,
    connector,
    target_hosts,
    svc_maps,
    placeholder_pattern,
    host_cli_map=None,
    show_table=True,
):
    test_results = []

    # Initialize live progress table
    progress_table = LiveProgressTable() if show_table else None

    for flow in flows:
        for step in flow.steps:
            process_single_step(
                step,
                flow,
                target_hosts,
                svc_maps,
                placeholder_pattern,
                connector,
                host_cli_map,
                test_results,
                show_table,
                progress_table,  # Pass the function
            )
    # Print final summary
    if progress_table:
        progress_table.print_final_summary(test_results)

    # Cleanup and export results
    connector.close_all()
    if test_results:
        export_workflow_results(test_results, flows)


def export_workflow_results(test_results, flows):
    """
    Print workflow-level summary and export results/summary to Excel.
    """
    import pandas as pd
    from dataclasses import asdict
    from collections import Counter

    df_results = pd.DataFrame([asdict(r) for r in test_results])
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"test_results_{timestamp}.xlsx"
    df_results.to_excel(output_file, index=False)
    # Workflow-level summary
    logger.debug("\n===== WORKFLOW SUMMARY =====")
    logger.debug(
        f"Total test flows: {len([f for f in flows if pd.notna(f.test_name) and str(f.test_name).strip() != '' and str(f.test_name).lower() != 'nan'])}"
    )
    total_steps = sum(
        len(flow.steps)
        for flow in flows
        if pd.notna(flow.test_name)
        and str(flow.test_name).strip() != ""
        and str(flow.test_name).lower() != "nan"
    )
    logger.debug(f"Total steps: {total_steps}")
    n_pass = sum(1 for r in test_results if getattr(r, "passed", False))
    n_fail = sum(1 for r in test_results if not getattr(r, "passed", False))
    logger.debug(f"Total passed: {n_pass}")
    logger.debug(f"Total failed: {n_fail}")
    logger.debug("---------------------------")
    for flow in flows:
        if not (
            pd.notna(flow.test_name)
            and str(flow.test_name).strip() != ""
            and str(flow.test_name).lower() != "nan"
        ):
            continue
        step_results = [step.result for step in flow.steps if hasattr(step, "result")]
        c = Counter(getattr(r, "passed", False) for r in step_results)
        print(
            f"Flow: {flow.test_name} | Sheet: {flow.sheet} | Steps: {len(flow.steps)} | Passed: {c[True]} | Failed: {c[False]}"
        )
    # Optionally, export summary sheet
    try:
        summary_data = []
        for flow in flows:
            if not (
                pd.notna(flow.test_name)
                and str(flow.test_name).strip() != ""
                and str(flow.test_name).lower() != "nan"
            ):
                continue
            step_results = [
                step.result for step in flow.steps if hasattr(step, "result")
            ]
            c = Counter(getattr(r, "passed", False) for r in step_results)
            summary_data.append(
                {
                    "Test_Name": flow.test_name,
                    "Sheet": flow.sheet,
                    "Num_Steps": len(flow.steps),
                    "Num_Passed": c[True],
                    "Num_Failed": c[False],
                }
            )
        df_summary = pd.DataFrame(summary_data)
        with pd.ExcelWriter(
            output_file, mode="a", engine="openpyxl", if_sheet_exists="replace"
        ) as writer:
            df_summary.to_excel(writer, sheet_name="Summary", index=False)
        logger.debug(f"Workflow summary exported to {output_file} (sheet: Summary)")
    except Exception as e:
        logger.error(f"Could not export summary sheet: {e}")


def detect_remote_cli(connector, host):
    """
    Detect whether 'kubectl' or 'oc' is available on the remote host via SSH.
    Returns: 'kubectl', 'oc', or 'none'.
    """
    try:
        result = connector.run_command("which kubectl", [host])
        output = result.get(host, {}).get("output", "").strip()
        if output:
            return "kubectl"
        result = connector.run_command("which oc", [host])
        output = result.get(host, {}).get("output", "").strip()
        if output:
            return "oc"
    except Exception as e:
        print(f"Could not detect CLI on {host}: {e}")
    return "none"


def safe_str(val):
    """ This is used in local functions like resolve_service_map_ssh"""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return ""
    return str(val)


def main():
    args = parse_args()
    
    # Configure logging based on command line arguments
    global logger
    logger = get_logger(
        name="TestPilot",
        log_to_file=not args.no_file_logging,
        log_dir=args.log_dir
    )
    logger.setLevel(args.log_level.upper())
    
    logger.debug(f"TestPilot started with args: {args}")
    logger.info(f"Module specified: {args.module}")
    if not args.no_file_logging:
        logger.debug(f"Logs will be written to directory: {args.log_dir}")
    config_file = "config/hosts.json"
    _, target_hosts = load_config_and_targets(config_file)
    connector = SSHConnector(config_file)
    connector.connect_all(target_hosts)
    excel_parser, valid_sheets = load_excel_and_sheets(args.input)
    # Sheet filter support
    if args.sheet:
        if args.sheet not in valid_sheets:
            logger.error(
                f"Sheet '{args.sheet}' not found in Excel file. Valid sheets: {valid_sheets}"
            )
            return
        valid_sheets = [args.sheet]
        logger.info(f"Running tests for sheet: {args.sheet}")
    placeholders, placeholder_pattern = extract_placeholders(excel_parser, valid_sheets)
    host_cli_map = {}
    if connector.use_ssh:
        if not connector.get_all_connections():
            logger.error(
                "No active SSH connections for service name resolution. Aborting."
            )
            return
        # Detect kubectl/oc CLI per host
        for host in target_hosts:
            cli = detect_remote_cli(connector, host)
            host_cli_map[host] = cli
            logger.info(f"Host {host} uses CLI: {cli}")
        svc_maps = resolve_service_map_ssh(connector, target_hosts, placeholders)
    else:
        if len(target_hosts) > 1:
            logger.error("Non-SSH mode supports only one target host. Aborting.")
            return
        svc_maps = resolve_service_map_local(placeholders)
    logger.info(f"Service maps resolved: {svc_maps}")
    if args.dry_run:
        show_table = not args.no_table
        dry_run_commands(
            excel_parser,
            valid_sheets,
            connector,
            target_hosts,
            svc_maps,
            placeholder_pattern,
            show_table=show_table,
        )
        return

    show_table = not args.no_table

    flows = parse_excel_to_flows(excel_parser, valid_sheets)

    # Filter for a specific test name if provided
    if getattr(args, "test_name", None):
        filtered_flows = []
        for flow in flows:
            if hasattr(flow, "test_name") and flow.test_name == args.test_name:
                filtered_flows.append(flow)
        flows = filtered_flows

    execute_flows(
        flows,
        connector,
        target_hosts,
        svc_maps,
        placeholder_pattern,
        host_cli_map=host_cli_map,
        show_table=show_table,
    )


if __name__ == "__main__":
    main()
