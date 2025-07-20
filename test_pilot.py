#!/usr/bin/env python3
# TestPilot - Test automation framework
# Requires Python 3.8+

import sys

# Check Python version compatibility
if sys.version_info < (3, 8):
    print(
        f"Error: TestPilot requires Python 3.8 or higher. You are using Python {sys.version}"
    )
    sys.exit(1)

import argparse
import datetime
import json
import os
import platform
import re
import subprocess
import sys
import time

import pandas as pd
from tabulate import tabulate

from build_info import APP_VERSION, BUILD_DATE, BUILD_EPOCH
from console_table_fmt import LiveProgressTable
from dry_run import dry_run_commands
from excel_parser import ExcelParser, parse_excel_to_flows
from logger import get_logger

# Import pattern processing modules
from patterns.pattern_match_parser import PatternMatchParser
from patterns.pattern_to_dict_converter import (
    PatternToDictConverter,
    integrate_with_excel_parser,
)
from ssh_connector import SSHConnector
from test_pilot_core import process_single_step
from utils.config_resolver import load_config_with_env, mask_sensitive_data
from utils.myutils import set_pdb_trace

logger = get_logger("TestPilot")


def parse_args():
    parser = argparse.ArgumentParser(description="TestPilot")
    parser.add_argument(
        "--step-delay",
        type=float,
        default=1,
        help="Delay (in seconds) between each test step [default: 1]",
    )
    parser.add_argument(
        "-v",
        "--version",
        action="store_true",
        help="Show version and build info",
    )
    parser.add_argument(
        "--display-mode",
        choices=["blessed", "progress", "simple"],
        default="blessed",
        help="Display mode: blessed (full dashboard), progress (progress only), simple (basic) (default: blessed)",
    )
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
        "-s",
        "--sheet",
        type=str,
        help="Only run tests for the specified sheet name",
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
    parser.add_argument(
        "--execution-mode",
        choices=["production", "mock"],
        default="production",
        help="Test execution mode: production (SSH/kubectl) or mock (local mock server) (default: production)",
    )
    parser.add_argument(
        "--mock-server-url",
        default="http://localhost:8081",
        help="Mock server URL for mock execution mode (default: http://localhost:8081)",
    )
    parser.add_argument(
        "--mock-data-file",
        default="mock_data/test_results_20250719_122220.json",
        help="Real response data file for mock server (default: mock_data/test_results_20250719_122220.json)",
    )
    return parser.parse_args()


def load_config_and_targets(config_file):
    try:
        # Use the secure config loader
        data = load_config_with_env(config_file)

        # Check for sensitive data in config
        check_config_security(data)

    except FileNotFoundError:
        logger.error(f"Configuration file not found: {config_file}")
        logger.info("Please create a config file from the template:")
        logger.info(f"  cp {config_file}.template {config_file}")
        logger.info("  Then update it with your settings")
        sys.exit(1)
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)

    connect_to = data.get("connect_to")
    if isinstance(connect_to, str):
        target_hosts = [connect_to]
    elif isinstance(connect_to, list):
        target_hosts = connect_to
    else:
        target_hosts = []
    return data, target_hosts


def check_config_security(config):
    """Check configuration for potential security issues."""
    warnings = []

    # Check for hardcoded passwords
    for host in config.get("hosts", []):
        if host.get("password") and not host["password"].startswith("${"):
            warnings.append(
                f"Host '{host.get('name', 'unknown')}' has a hardcoded password"
            )

        # Check for hardcoded private key paths that might be committed
        key_file = host.get("key_file", "")
        if (
            key_file
            and not key_file.startswith("${")
            and not key_file.startswith("~")
        ):
            if any(
                pattern in key_file
                for pattern in ["config/", "keys/", ".ssh/"]
            ):
                warnings.append(
                    f"Host '{host.get('name', 'unknown')}' has a key file in project directory"
                )

    if warnings:
        logger.warning("🔒 Security warnings detected in configuration:")
        for warning in warnings:
            logger.warning(f"  - {warning}")
        logger.warning(
            "Consider using environment variables for sensitive data."
        )
        logger.warning("See docs/SECURE_CONFIGURATION.md for guidance.")


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
    logger.debug(
        f"Unique placeholders found in commands: {sorted(placeholders)}"
    )
    return placeholders, placeholder_pattern


def resolve_service_map_ssh(
    connector, target_hosts, placeholders, host_cli_map
):
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
            namespace = (
                getattr(host_cfg, "namespace", None) if host_cfg else None
            )
            if namespace:
                cli_type = (
                    host_cli_map.get(host, "kubectl")
                    if host_cli_map
                    else "kubectl"
                )
                kubectl_cmd = (
                    f"{cli_type} get virtualservices -n {namespace} -o json"
                )
            else:
                cli_type = (
                    host_cli_map.get(host, "kubectl")
                    if host_cli_map
                    else "kubectl"
                )
                kubectl_cmd = f"{cli_type} get virtualservices -A -o json"
            stdin, stdout, stderr = conn.exec_command(kubectl_cmd)
            out = stdout.read().decode()
            err = stderr.read().decode()
            if err:
                logger.error(f"kubectl error on host {host}: {err}")
                continue

            svc_json = json.loads(out)
            host_map = {}
            hosts = []

            # fetch all the hosts from the kubectl output
            for item in svc_json.get("items", []):
                name = item["spec"]["hosts"]
                ns = item["metadata"]["namespace"]
                if name not in hosts:
                    hosts.append(name)

            # compare hosts with placeholders
            for svc_host in hosts:
                for p in placeholders:
                    if isinstance(svc_host, list) and p in svc_host[0]:
                        host_map[p] = f"{svc_host}"
            svc_maps[host] = host_map
        except Exception as e:
            logger.error(f"Failed to resolve services on host {host}: {e}")

    # fallback to get services command if there are no virtual services
    for host in target_hosts:
        if not len(svc_maps[host]):
            cli_type = (
                host_cli_map.get(host, "kubectl")
                if host_cli_map
                else "kubectl"
            )
            kubectl_cmd = f"{cli_type} get svc -n {namespace} -o json"
            stdin, stdout, stderr = conn.exec_command(kubectl_cmd)
            out = stdout.read().decode()
            err = stderr.read().decode()
            svc_json = json.loads(out)
            host_map = {}
            for item in svc_json.get("items", []):
                name = item["metadata"]["name"]
                ns = item["metadata"]["namespace"]
                for p in placeholders:
                    if p in name:
                        host_map[p] = f"['{name}']"
            svc_maps[host] = host_map

    return svc_maps


def resolve_service_map_local(
    placeholders,
    target_hosts=None,
    host_cli_map=None,
    namespace=None,
    config_file="config/hosts.json",
):
    svc_maps = {}
    # If namespace is not provided, try to fetch from config using connect_to host
    if namespace is None:
        try:
            with open(config_file, "r") as f:
                data = json.load(f)
            connect_to = data.get("connect_to")
            hosts = data.get("hosts")
            pod_mode = data.get("pod_mode")
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
        if not pod_mode:
            # Construct kubectl command based on namespace
            if namespace:
                cli_type = (
                    host_cli_map.get("localhost", "kubectl")
                    if host_cli_map
                    else "kubectl"
                )
                kubectl_cmd = [
                    cli_type,
                    "get",
                    "virtualservices",
                    "-n",
                    namespace,
                    "-o",
                    "json",
                ]
            else:
                cli_type = (
                    host_cli_map.get("localhost", "kubectl")
                    if host_cli_map
                    else "kubectl"
                )
                kubectl_cmd = [cli_type, "get", "svc", "-A", "-o", "json"]
            logger.debug(
                f"Running local kubectl command: {' '.join(kubectl_cmd)}"
            )
            result = subprocess.run(
                kubectl_cmd,
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                logger.error(f"Local kubectl error: {result.stderr}")
                return {}

            svc_json = json.loads(result.stdout)
            host_map = {}
            hosts = []
            for item in svc_json.get("items", []):
                name = item["spec"]["hosts"]
                ns = item["metadata"]["namespace"]
                if name not in hosts:
                    hosts.append(name)

            # compare hosts with placeholders
            for svc_host in hosts:
                for p in placeholders:
                    # TODO may we dont need to check first svc_host[0] rather copy the whole thing
                    if isinstance(svc_host, list) and p in svc_host[0]:
                        host_map[p] = f"{svc_host}"
            svc_maps[connect_to] = host_map

        for host in target_hosts:
            if not len(svc_maps[host]):
                # In pod_mode, check for resource_map.json in config/
                resource_map_path = os.path.join(
                    os.path.dirname(config_file), "resource_map.json"
                )
                if os.path.isfile(resource_map_path):
                    try:
                        with open(resource_map_path, "r") as f:
                            svc_json = json.load(f)
                        logger.debug(
                            f"pod_mode enabled: using resource_map.json at {resource_map_path} for service maps."
                        )
                        svc_maps[connect_to] = svc_json
                    except Exception as e:
                        logger.error(
                            f"Failed to load resource_map.json: {e}. Falling back to local service map resolution."
                        )
                else:
                    logger.error(
                        "pod_mode enabled: resource_map.json not found, please add it to config/ directory."
                    )
                    sys.exit(1)

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
    """
    Print the test results as a table, adding an incremental 'Index' column per test.
    """
    if not test_results:
        print("No test results to display.")
        return
    try:
        from tabulate import tabulate

        # Add Index column as the first column
        table = []
        for idx, row in enumerate(test_results, 1):
            # If row is an object, convert to dict
            if not isinstance(row, dict):
                row = row.__dict__ if hasattr(row, "__dict__") else dict(row)
            row_with_index = {"Index": idx, **row}
            table.append(row_with_index)
        headers = table[0].keys()
        print(tabulate(table, headers=headers, tablefmt="grid"))
    except ImportError:
        # Fallback: simple print
        print("Index", *test_results[0].keys())
        for idx, row in enumerate(test_results, 1):
            if not isinstance(row, dict):
                row = row.__dict__ if hasattr(row, "__dict__") else dict(row)
            print(idx, *row.values())


def execute_flows(
    flows,
    connector,
    target_hosts,
    svc_maps,
    placeholder_pattern,
    host_cli_map=None,
    show_table=True,
    display_mode="blessed",
    userargs=None,
    step_delay=1,
):
    test_results = []
    dashboard = None

    if show_table:
        try:
            from print_table import PrintTableDashboard

            if display_mode == "blessed" or display_mode == "full":
                dashboard = PrintTableDashboard(mode="full")
            elif display_mode == "progress":
                dashboard = PrintTableDashboard(mode="progress")
            else:  # simple
                dashboard = PrintTableDashboard(mode="simple")

            dashboard.start()

        except ImportError as e:
            logger.warning(f"PrintTable dashboard not available: {e}")
            # Fallback to simple print-based display
            from console_table_fmt import LiveProgressTable

            dashboard = LiveProgressTable()

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
                dashboard,
                args=userargs,
                step_delay=step_delay,
            )
    # Print final summary if dashboard is present
    if dashboard:
        dashboard.print_final_summary()

    # Always print/export results summary, even if show_table is False
    connector.close_all()
    if test_results:
        # print_results_table(test_results)
        export_workflow_results(test_results, flows)


def export_workflow_results(test_results, flows):
    """
    Print workflow-level summary and export results/summary to Excel.
    Also supports exporting to CSV and JSON formats.
    """
    from collections import Counter
    from dataclasses import asdict

    import pandas as pd

    from test_results_exporter import TestResultsExporter

    # Original Excel export
    df_results = pd.DataFrame([asdict(r) for r in test_results])
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"test_results_{timestamp}.xlsx"
    df_results.to_excel(output_file, index=False)

    # Additional format exports
    exporter = TestResultsExporter()

    # Export to JSON
    json_file = exporter.export_to_json(test_results)

    # Export to CSV
    csv_file = exporter.export_to_csv(test_results)

    # Export summary report
    summary_file = exporter.export_summary_report(test_results)

    # Export HTML report
    html_file = exporter.export_to_html(test_results)

    # Log export information
    logger.debug(f"\nTest results exported to:")
    logger.debug(f"  - Excel: {output_file}")
    logger.debug(f"  - JSON: {json_file}")
    logger.debug(f"  - CSV: {csv_file}")
    logger.debug(f"  - Summary: {summary_file}")
    logger.debug(f"  - HTML: {html_file}")

    # Print HTML report path to console (more visible)
    print(f"\n📊 Interactive HTML report generated: {html_file}")
    print("   The report will open automatically in your default browser.")

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
        step_results = [
            step.result for step in flow.steps if hasattr(step, "result")
        ]
        c = Counter(getattr(r, "passed", False) for r in step_results)
        logger.debug(
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
        logger.debug(
            f"Workflow summary exported to {output_file} (sheet: Summary)"
        )
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
    """This is used in local functions like resolve_service_map_ssh"""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return ""
    return str(val)


def process_patterns(input_path):
    """
    Process patterns from Excel file and generate enhanced pattern matches JSON file.
    This function is integrated from patterns/pattern_main.py.

    Args:
        input_path (str): Path to the Excel file

    Returns:
        dict: Enhanced pattern data
    """
    logger.info("🚀 Processing patterns from Excel file...")

    try:
        # Step 1: Parse Excel file for pattern matches
        logger.debug("📊 Parsing Excel file for patterns...")
        parser = PatternMatchParser(input_path)
        raw_pattern_data = parser.extract_pattern_matches()

        # Step 2: Convert patterns to dictionaries
        logger.debug("🔄 Converting patterns to dictionaries...")
        enhanced_data = integrate_with_excel_parser(raw_pattern_data)

        # Step 3: Export results to patterns directory
        logger.debug("💾 Exporting enhanced pattern matches...")
        patterns_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "patterns"
        )
        os.makedirs(patterns_dir, exist_ok=True)

        # Create filename based on input Excel filename
        base_filename = os.path.splitext(os.path.basename(input_path))[0]
        output_file = os.path.join(
            patterns_dir, f"{base_filename}_enhanced_pattern_matches.json"
        )

        # Export the enhanced data
        with open(output_file, "w") as f:
            json.dump(enhanced_data, f, indent=2)
        logger.info(f"✅ Enhanced pattern matches exported to: {output_file}")

        # Create pattern type summary
        summary = create_pattern_summary(enhanced_data)
        summary_file = os.path.join(patterns_dir, "pattern_type_summary.json")
        with open(summary_file, "w") as f:
            json.dump(summary, f, indent=2)
        logger.debug(f"📊 Pattern type summary exported to: {summary_file}")

        return enhanced_data
    except Exception as e:
        logger.error(f"❌ Error processing patterns: {e}")
        return None


def create_pattern_summary(enhanced_data):
    """
    Create a summary of all unique pattern types and their frequencies.
    This function is integrated from patterns/pattern_main.py.
    """
    pattern_type_summary = {}
    enhanced_patterns = enhanced_data["enhanced_patterns"]

    for sheet_name, patterns in enhanced_patterns.items():
        for pattern_entry in patterns:
            converted = pattern_entry["converted_pattern"]
            pattern_type = converted["pattern_type"]

            if pattern_type not in pattern_type_summary:
                pattern_type_summary[pattern_type] = {
                    "count": 0,
                    "examples": [],
                    "sheets": set(),
                }

            pattern_type_summary[pattern_type]["count"] += 1
            pattern_type_summary[pattern_type]["sheets"].add(sheet_name)

            # Keep first 3 examples
            if len(pattern_type_summary[pattern_type]["examples"]) < 3:
                pattern_type_summary[pattern_type]["examples"].append(
                    {
                        "original": pattern_entry["pattern_match"],
                        "converted": converted["data"],
                    }
                )

    # Convert sets to lists for JSON serialization
    for pattern_type in pattern_type_summary:
        pattern_type_summary[pattern_type]["sheets"] = list(
            pattern_type_summary[pattern_type]["sheets"]
        )

    return pattern_type_summary


def main():

    # Early version check: allow -v/--version without requiring -i/-m
    if "-v" in sys.argv or "--version" in sys.argv:
        print(f"TestPilot Version: {APP_VERSION}")
        print(f"Build Unix Epoch: {BUILD_EPOCH}")
        print(f"Build Date (UTC): {BUILD_DATE}")
        print(f"Python: {platform.python_version()} ({platform.system()})")
        print(f"Platform: {platform.platform()}")
        print(f"pandas: {pandas.__version__}")
        print(f"tabulate: {tabulate.__version__}")
        # Config info
        config_file = "config/hosts.json"
        resource_map_path = os.path.join(
            os.path.dirname(config_file), "resource_map.json"
        )
        print(
            f"Config: {config_file} ({'found' if os.path.isfile(config_file) else 'not found'})"
        )
        print(
            f"Resource Map: {resource_map_path} ({'found' if os.path.isfile(resource_map_path) else 'not found'})"
        )
        # pod_mode/use_ssh/target_hosts
        pod_mode = use_ssh = None
        target_hosts = []
        try:
            with open(config_file, "r") as f:
                config = json.load(f)
                pod_mode = config.get("pod_mode", None)
                use_ssh = config.get("use_ssh", None)
                target_hosts = config.get("hosts", [])
        except Exception:
            pass
        print(f"pod_mode: {pod_mode}")
        print(f"use_ssh: {use_ssh}")
        print(
            f"Target hosts: {', '.join(h.get('name','') for h in target_hosts) if target_hosts else 'N/A'}"
        )
        sys.exit(0)

    args = parse_args()

    # Configure logging based on command line arguments
    global logger
    logger = get_logger(
        name="TestPilot",
        log_to_file=not args.no_file_logging,
        log_dir=args.log_dir,
    )
    logger.setLevel(args.log_level.upper())

    logger.debug(f"TestPilot started with args: {args}")
    logger.debug(f"Module specified: {args.module}")
    if not args.no_file_logging:
        logger.debug(f"Logs will be written to directory: {args.log_dir}")
    config_file = "config/hosts.json"

    # Only parse Excel and extract placeholders before dry-run
    excel_parser, valid_sheets = load_excel_and_sheets(args.input)

    if args.sheet:
        if args.sheet not in valid_sheets:
            logger.error(
                f"Sheet '{args.sheet}' not found in Excel file. Valid sheets: {valid_sheets}"
            )
            sys.exit(1)
        valid_sheets = [args.sheet]
        logger.debug(f"Running tests for sheet: {args.sheet}")

    # Process patterns from Excel file and generate enhanced pattern matches
    # This step has to be at the beginning where it processes and creates files
    # in the patterns folder, overwriting them each time the logic runs

    # Skip pattern processing in mock mode to improve performance
    if args.execution_mode == "mock":
        logger.info(
            "🎭 Skipping pattern processing in mock mode for faster execution"
        )
        enhanced_patterns = None
    else:
        logger.info("Processing patterns from Excel file...")
        enhanced_patterns = process_patterns(args.input)
        if enhanced_patterns:
            logger.info("Pattern processing completed successfully")
        else:
            logger.warning("Pattern processing failed or no patterns found")

    placeholders, placeholder_pattern = extract_placeholders(
        excel_parser, valid_sheets
    )
    logger.info(f"Patterns found from excel: {placeholders}")

    # Dummy hosts list for dry-run (use names from hosts.json)
    with open(config_file, "r") as f:
        config = json.load(f)
        target_hosts = config.get("hosts", [])
    if args.dry_run:
        show_table = not args.no_table
        # Use dummy mapping for dry-run: map each placeholder to a dummy value for each host
        dummy_map = {p: f"dummy-{p}" for p in placeholders}
        svc_maps = {
            host["name"] if isinstance(host, dict) else host: dummy_map
            for host in target_hosts
        }
        # Create a dummy host_cli_map for dry run
        dummy_host_cli_map = {
            host["name"] if isinstance(host, dict) else host: "kubectl"
            for host in target_hosts
        }
        dry_run_commands(
            excel_parser,
            valid_sheets,
            None,  # connector is not needed in dry-run
            target_hosts,
            svc_maps,
            placeholder_pattern,
            host_cli_map=dummy_host_cli_map,
            show_table=show_table,
            display_mode=args.display_mode,
        )
        sys.exit(0)

    # Check pod_mode and use_ssh compatibility
    pod_mode = False
    use_ssh = False
    try:
        with open(config_file, "r") as f:
            config = json.load(f)
            pod_mode = config.get("pod_mode", False)
            use_ssh = config.get("use_ssh", False)
    except Exception as e:
        logger.warning(f"Could not read pod_mode/use_ssh from config: {e}")
    if pod_mode and use_ssh:
        logger.error(
            "pod_mode and use_ssh cannot both be enabled. Please set use_ssh to false when pod_mode is true in config/hosts.json."
        )
        sys.exit(1)

    _, target_hosts = load_config_and_targets(config_file)
    logger.debug(f"Target hosts: {target_hosts}")

    connector = SSHConnector(config_file)

    # Add execution mode support to connector
    connector.execution_mode = args.execution_mode
    connector.mock_server_url = args.mock_server_url
    connector.mock_data_file = args.mock_data_file

    if args.execution_mode == "mock":
        logger.info(f"🎭 Mock execution mode enabled")
        logger.info(f"🔗 Mock server URL: {args.mock_server_url}")
        logger.info(f"📁 Mock data file: {args.mock_data_file}")
        # Skip SSH connections in mock mode
        logger.debug("Skipping SSH connections in mock mode")
    else:
        logger.debug("Production mode: establishing SSH connections")
        connector.connect_all(target_hosts)

    host_cli_map = {}
    if pod_mode:
        svc_maps = resolve_service_map_local(placeholders, host_cli_map)
    elif connector.use_ssh:
        if not connector.get_all_connections():
            logger.error(
                "No active SSH connections for service name resolution. Aborting."
            )
            sys.exit(1)
        # Detect kubectl/oc CLI per host
        for host in target_hosts:
            cli = detect_remote_cli(connector, host)
            host_cli_map[host] = cli
            logger.debug(f"Host {host} uses CLI: {cli}")
        svc_maps = resolve_service_map_ssh(
            connector, target_hosts, placeholders, host_cli_map
        )
    else:
        if len(target_hosts) > 1:
            logger.error(
                "Non-SSH mode supports only one target host. Aborting."
            )
            sys.exit(1)
        svc_maps = resolve_service_map_local(placeholders, target_hosts)

    logger.info(f"Service maps resolved: {svc_maps}")

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
        display_mode=args.display_mode,
        userargs=args,
        step_delay=args.step_delay,
    )


if __name__ == "__main__":
    main()
