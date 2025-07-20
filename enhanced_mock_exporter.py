#!/usr/bin/env python3
"""
Enhanced Mock Data Exporter for TestPilot
==========================================

Creates enhanced mock data files with explicit sheet names, test names, and structured
endpoint information for easier mock server mapping and debugging.

Features:
- Extracts sheet name and test name from test results
- Parses commands into structured endpoint data
- Includes step numbers for multi-step tests
- Provides clean endpoint/query parameter separation
- Maintains backward compatibility with original format
"""

import json
import re
import shlex
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qs, urlparse


class EnhancedMockExporter:
    """Enhanced mock data exporter with structured metadata."""

    def __init__(self):
        self.step_counters = {}  # Track step numbers per test

    def parse_curl_command(self, command: str) -> Dict[str, Any]:
        """Parse kubectl curl command into structured data."""
        if not command or "curl" not in command:
            return {}

        try:
            # Extract method
            method_match = re.search(r"-X\s+(\w+)", command)
            method = method_match.group(1) if method_match else "GET"

            # Extract URL (stop at quotes or whitespace)
            url_match = re.search(r"http://[^\s'\"]+", command)
            if not url_match:
                url_match = re.search(r"https://[^\s'\"]+", command)

            if not url_match:
                return {"method": method}

            full_url = url_match.group(0)
            parsed_url = urlparse(full_url)

            # Parse endpoint and query parameters
            endpoint = parsed_url.path
            query_params = {}
            if parsed_url.query:
                query_params = parse_qs(parsed_url.query)
                # Convert lists to single values for simplicity
                query_params = {
                    k: v[0] if len(v) == 1 else v
                    for k, v in query_params.items()
                }

            # Extract headers
            headers = {}
            header_matches = re.findall(r"-H\s+'([^']+)'", command)
            if not header_matches:
                header_matches = re.findall(r'-H\s+"([^"]+)"', command)

            for header in header_matches:
                if ":" in header:
                    key, value = header.split(":", 1)
                    headers[key.strip()] = value.strip()

            # Extract payload
            payload = None
            payload_match = re.search(r"-d\s+'([^']+)'", command)
            if not payload_match:
                payload_match = re.search(r'-d\s+"([^"]+)"', command)
            if payload_match:
                payload_str = payload_match.group(1)
                try:
                    payload = json.loads(payload_str)
                except json.JSONDecodeError:
                    payload = payload_str

            return {
                "method": method,
                "endpoint": endpoint,
                "query_params": query_params,
                "headers": headers,
                "request_payload": payload,
                "full_url": full_url,
                "host": parsed_url.netloc,
            }

        except Exception as e:
            print(f"⚠️  Error parsing command: {e}")
            return {"method": "GET"}

    def get_step_number(self, sheet_name: str, test_name: str) -> int:
        """Get and increment step number for a test."""
        key = f"{sheet_name}::{test_name}"
        if key not in self.step_counters:
            self.step_counters[key] = 0
        self.step_counters[key] += 1
        return self.step_counters[key]

    def enhance_test_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance a single test result with structured metadata."""
        # Extract basic metadata
        sheet_name = result.get("sheet", "unknown")
        test_name = result.get("test_name", "unknown")
        step_number = self.get_step_number(sheet_name, test_name)

        # Parse command into structured data
        command = result.get("command", "")
        parsed_command = self.parse_curl_command(command)

        # Parse response
        output = result.get("output", "")
        error = result.get("error", "")
        expected_response = self.parse_response(
            output, result.get("status"), error
        )

        # Build enhanced result
        enhanced = {
            # Enhanced metadata
            "sheet_name": sheet_name,
            "test_name": test_name,
            "step_number": step_number,
            # Structured request data
            "request": {
                "method": parsed_command.get("method", "GET"),
                "endpoint": parsed_command.get("endpoint", ""),
                "query_params": parsed_command.get("query_params", {}),
                "headers": parsed_command.get("headers", {}),
                "payload": parsed_command.get("request_payload"),
                "host": parsed_command.get("host", ""),
                "full_url": parsed_command.get("full_url", ""),
            },
            # Expected response
            "expected_response": expected_response,
            # Test execution metadata
            "execution": {
                "host": result.get("host", ""),
                "passed": result.get("passed", False),
                "duration": result.get("duration", 0),
                "timestamp": result.get("timestamp", ""),
                "status": result.get("status", "UNKNOWN"),
            },
            # Original data (for backward compatibility)
            "original": {
                "command": command,
                "output": output,
                "error": result.get("error", ""),
                "method": result.get("method", ""),
            },
        }

        return enhanced

    def parse_response(
        self, output: str, status: str, error: str = ""
    ) -> Dict[str, Any]:
        """Parse response output into structured format with actual HTTP status code."""
        # Extract actual HTTP status code from error message (like response_parser.py does)
        actual_status_code = self.extract_http_status_from_error(error)

        # Default to generic codes if no actual status found
        if actual_status_code is None:
            actual_status_code = 200 if status == "PASS" else 400

        response = {
            "status_code": actual_status_code,
            "body": None,
            "headers": {"Content-Type": "application/json"},
        }

        if output:
            try:
                # Try to parse as JSON
                response["body"] = json.loads(output)

                # Extract status code from JSON body if present (but prefer HTTP status)
                if (
                    isinstance(response["body"], dict)
                    and "status" in response["body"]
                    and actual_status_code
                    in [200, 400]  # Only use body status for generic codes
                ):
                    response["status_code"] = response["body"]["status"]

            except json.JSONDecodeError:
                # Keep as string if not JSON
                response["body"] = output
                response["headers"]["Content-Type"] = "text/plain"

        return response

    def extract_http_status_from_error(self, error: str) -> Optional[int]:
        """Extract actual HTTP status code from curl error output."""
        if not error:
            return None

        # Find HTTP/2 or HTTP/1.1 status line (like response_parser.py does)
        import re

        match = re.search(r"< HTTP/[12](?:\.\d)? (\d{3})", error)
        if match:
            return int(match.group(1))

        # Also try without the < prefix
        match = re.search(r"HTTP/[12](?:\.\d)? (\d{3})", error)
        if match:
            return int(match.group(1))

        return None

    def export_enhanced_mock_data(
        self, input_file: str, output_file: Optional[str] = None
    ) -> str:
        """Export enhanced mock data from test results."""

        if not output_file:
            input_path = Path(input_file)
            output_file = str(
                input_path.with_name(f"enhanced_{input_path.name}")
            )

        print(f"📁 Loading test results from {input_file}")

        try:
            with open(input_file, "r") as f:
                data = json.load(f)
        except Exception as e:
            print(f"❌ Error loading input file: {e}")
            return ""

        results = data.get("results", [])
        print(f"📊 Processing {len(results)} test results")

        # Reset step counters
        self.step_counters = {}

        # Enhance each result
        enhanced_results = []
        for result in results:
            enhanced = self.enhance_test_result(result)
            enhanced_results.append(enhanced)

        # Create enhanced data structure
        enhanced_data = {
            "metadata": {
                "export_timestamp": datetime.now().isoformat(),
                "source_file": input_file,
                "enhanced_version": "1.0",
                "total_tests": len(enhanced_results),
                "unique_sheets": len(
                    set(r["sheet_name"] for r in enhanced_results)
                ),
                "unique_tests": len(
                    set(
                        f"{r['sheet_name']}::{r['test_name']}"
                        for r in enhanced_results
                    )
                ),
            },
            "original_summary": data.get("summary", {}),
            "enhanced_results": enhanced_results,
        }

        # Write enhanced data
        print(f"📤 Exporting enhanced data to {output_file}")

        try:
            with open(output_file, "w") as f:
                json.dump(enhanced_data, f, indent=2)
        except Exception as e:
            print(f"❌ Error writing output file: {e}")
            return ""

        # Print summary
        sheets = {}
        for result in enhanced_results:
            sheet = result["sheet_name"]
            if sheet not in sheets:
                sheets[sheet] = []
            sheets[sheet].append(result["test_name"])

        print(f"✅ Enhanced mock data exported successfully!")
        print(f"📋 Summary:")
        print(f"   📄 {len(sheets)} sheets processed")
        print(f"   🧪 {len(enhanced_results)} total test steps")
        print(f"   📂 Output: {output_file}")

        print(f"\n📊 Sheets processed:")
        for sheet, tests in sheets.items():
            unique_tests = set(tests)
            print(
                f"   🔹 {sheet}: {len(unique_tests)} tests, {len(tests)} steps"
            )

        return output_file


def main():
    """CLI entry point for enhanced mock exporter."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Enhanced Mock Data Exporter for TestPilot"
    )
    parser.add_argument("input_file", help="Input test results JSON file")
    parser.add_argument(
        "-o",
        "--output",
        help="Output enhanced mock data file (default: enhanced_<input>)",
    )

    args = parser.parse_args()

    exporter = EnhancedMockExporter()
    output_file = exporter.export_enhanced_mock_data(
        args.input_file, args.output
    )

    if output_file:
        print(f"\n🎉 Enhanced mock data ready for use!")
        print(f"🔗 Use with mock server: --data-file {output_file}")


if __name__ == "__main__":
    main()
