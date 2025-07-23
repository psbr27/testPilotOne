# =============================================================================
# Test Results Exporter Module
# Provides functionality to export test results in various formats
# =============================================================================

import csv
import json
import os
import webbrowser
from datetime import datetime
from typing import Any, Dict, List


class TestResultsExporter:
    """Export test results to various formats (CSV, JSON, etc.)"""

    def __init__(self, results_dir="test_results"):
        """Initialize exporter with output directory"""
        self.results_dir = results_dir
        self._ensure_directory_exists()

    def _ensure_directory_exists(self):
        """Create results directory if it doesn't exist"""
        if not os.path.exists(self.results_dir):
            os.makedirs(self.results_dir)

    def _generate_filename(self, format_type: str) -> str:
        """Generate timestamped filename"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return os.path.join(
            self.results_dir, f"test_results_{timestamp}.{format_type}"
        )

    def _extract_response_body(self, result: Any) -> Dict[str, Any]:
        """Extract response body information from Excel Response_Payload column"""
        # Get response payload directly from Excel column
        response_payload = getattr(
            result, "Response_Payload", None
        ) or getattr(result, "response_payload", "")

        response_body = {
            "raw_payload": str(response_payload) if response_payload else "",
            "parsed_json": None,
            "content_type": "unknown",
            "size_bytes": 0,
            "from_excel_column": True,
        }

        # Also include the output field for backward compatibility
        output = getattr(result, "output", "")
        if output:
            response_body["raw_output"] = output

        # Use Response_Payload if available, otherwise fall back to output
        content_to_analyze = response_payload if response_payload else output

        if content_to_analyze:
            response_body["size_bytes"] = len(str(content_to_analyze))
            try:
                import json

                parsed = json.loads(str(content_to_analyze))
                response_body["parsed_json"] = parsed
                response_body["content_type"] = "application/json"
            except (json.JSONDecodeError, TypeError):
                # Not JSON, check if it's HTML/XML
                content_str = str(content_to_analyze).strip()
                if content_str.startswith("<"):
                    response_body["content_type"] = (
                        "text/html"
                        if "<html" in content_str.lower()
                        else "text/xml"
                    )
                else:
                    response_body["content_type"] = "text/plain"

        # Extract status code from error if available
        error = getattr(result, "error", "")
        if error:
            import re

            status_match = re.search(r"HTTP/[12](?:\.\d)? (\d{3})", error)
            if status_match:
                response_body["status_code"] = int(status_match.group(1))

        return response_body

    def _extract_pattern_match(self, result: Any) -> Dict[str, Any]:
        """Extract pattern matching information from Excel Pattern_Match column"""
        # Get pattern match directly from Excel column
        pattern_match_value = getattr(
            result, "Pattern_Match", None
        ) or getattr(result, "pattern_match", "")

        pattern_match = {
            "raw_pattern_match": (
                str(pattern_match_value) if pattern_match_value else ""
            ),
            "matched": False,
            "pattern_type": None,
            "pattern_name": None,
            "match_details": [],
            "confidence_score": 0.0,
            "from_excel_column": True,
        }

        # Parse the pattern match value
        if pattern_match_value:
            pattern_str = str(pattern_match_value).strip().lower()

            # Simple parsing logic for common pattern formats
            if pattern_str in ["true", "yes", "1", "pass", "matched"]:
                pattern_match["matched"] = True
                pattern_match["confidence_score"] = 1.0
            elif pattern_str in ["false", "no", "0", "fail", "not matched"]:
                pattern_match["matched"] = False
            else:
                # Try to extract more detailed pattern information
                pattern_match["matched"] = True
                pattern_match["pattern_name"] = pattern_str
                pattern_match["confidence_score"] = 0.8

                # Infer pattern type from the value
                if any(
                    keyword in pattern_str
                    for keyword in ["api", "response", "json"]
                ):
                    pattern_match["pattern_type"] = "api_response"
                elif any(
                    keyword in pattern_str
                    for keyword in ["auth", "login", "token"]
                ):
                    pattern_match["pattern_type"] = "authentication"
                elif any(
                    keyword in pattern_str for keyword in ["user", "account"]
                ):
                    pattern_match["pattern_type"] = "user_management"
                elif any(
                    keyword in pattern_str
                    for keyword in ["subscription", "plan"]
                ):
                    pattern_match["pattern_type"] = "subscription"
                else:
                    pattern_match["pattern_type"] = "custom"

        return pattern_match

    def export_to_json(
        self, test_results: List[Any], filename: str = None
    ) -> str:
        """Export test results to JSON format with enhanced fields"""
        if not filename:
            filename = self._generate_filename("json")

        results_data = []
        for index, result in enumerate(test_results):
            result_dict = {
                "row_index": index + 1,  # 1-based indexing for readability
                "host": getattr(result, "host", ""),
                "sheet": getattr(result, "sheet", ""),
                "test_name": getattr(result, "test_name", ""),
                "method": getattr(result, "method", ""),
                "command": getattr(result, "command", ""),
                "passed": getattr(result, "passed", False),
                "duration": getattr(result, "duration", 0.0),
                "timestamp": getattr(result, "timestamp", ""),
                "error": getattr(result, "error", ""),
                "output": (
                    getattr(result, "output", "")
                    if hasattr(result, "output")
                    else ""
                ),
                "response_body": self._extract_response_body(result),
                "pattern_match": self._extract_pattern_match(result),
            }

            # Add dry-run status if applicable
            if (
                hasattr(result, "result")
                and getattr(result, "result", "") == "DRY-RUN"
            ):
                result_dict["status"] = "DRY-RUN"
            else:
                result_dict["status"] = (
                    "PASS" if result_dict["passed"] else "FAIL"
                )

            results_data.append(result_dict)

        # Add summary information with enhanced metrics
        passed_count = sum(
            1 for r in test_results if getattr(r, "passed", False)
        )
        failed_count = len(test_results) - passed_count

        # Calculate pattern matching statistics
        pattern_matched_count = sum(
            1
            for result_dict in results_data
            if result_dict["pattern_match"]["matched"]
        )

        # Calculate response body statistics
        json_responses = sum(
            1
            for result_dict in results_data
            if result_dict["response_body"]["content_type"]
            == "application/json"
        )

        total_response_size = sum(
            result_dict["response_body"]["size_bytes"]
            for result_dict in results_data
        )

        summary = {
            "total_tests": len(test_results),
            "passed": passed_count,
            "failed": failed_count,
            "success_rate": (
                round((passed_count / len(test_results)) * 100, 2)
                if test_results
                else 0
            ),
            "export_timestamp": datetime.now().isoformat(),
            "enhanced_fields": {
                "pattern_matching": {
                    "total_matched": pattern_matched_count,
                    "match_rate": (
                        round(
                            (pattern_matched_count / len(test_results)) * 100,
                            2,
                        )
                        if test_results
                        else 0
                    ),
                },
                "response_analysis": {
                    "json_responses": json_responses,
                    "total_response_size_bytes": total_response_size,
                    "avg_response_size_bytes": (
                        round(total_response_size / len(test_results), 2)
                        if test_results
                        else 0
                    ),
                },
            },
        }

        export_data = {"summary": summary, "results": results_data}

        with open(filename, "w") as f:
            json.dump(export_data, f, indent=2)

        return filename

    def export_to_csv(
        self, test_results: List[Any], filename: str = None
    ) -> str:
        """Export test results to CSV format with enhanced fields"""
        if not filename:
            filename = self._generate_filename("csv")

        headers = [
            "Row Index",
            "Host",
            "Sheet",
            "Test Name",
            "Method",
            "Status",
            "Duration (s)",
            "Timestamp",
            "Pattern Matched (Excel)",
            "Response Size (bytes)",
            "Content Type (Excel)",
            "Error Message",
        ]

        with open(filename, "w", newline="") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(headers)

            for index, result in enumerate(test_results):
                # Determine status
                if (
                    hasattr(result, "result")
                    and getattr(result, "result", "") == "DRY-RUN"
                ):
                    status = "DRY-RUN"
                else:
                    status = (
                        "PASS" if getattr(result, "passed", False) else "FAIL"
                    )

                # Extract enhanced field information
                response_body = self._extract_response_body(result)
                pattern_match = self._extract_pattern_match(result)

                row = [
                    index + 1,  # Row index (1-based)
                    getattr(result, "host", ""),
                    getattr(result, "sheet", ""),
                    getattr(result, "test_name", ""),
                    getattr(result, "method", ""),
                    status,
                    f"{getattr(result, 'duration', 0.0):.2f}",
                    getattr(result, "timestamp", ""),
                    "Yes" if pattern_match["matched"] else "No",
                    response_body["size_bytes"],
                    response_body["content_type"],
                    getattr(result, "error", "")[
                        :200
                    ],  # Limit error message length
                ]
                writer.writerow(row)

        return filename

    def export_summary_report(
        self, test_results: List[Any], filename: str = None
    ) -> str:
        """Export a summary report in text format"""
        if not filename:
            filename = self._generate_filename("txt")

        passed = sum(1 for r in test_results if getattr(r, "passed", False))
        failed = len(test_results) - passed

        with open(filename, "w") as f:
            f.write("=" * 80 + "\n")
            f.write("TEST EXECUTION SUMMARY REPORT\n")
            f.write("=" * 80 + "\n\n")

            f.write(
                f"Export Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            )
            f.write(f"Total Tests: {len(test_results)}\n")
            f.write(f"Passed: {passed}\n")
            f.write(f"Failed: {failed}\n")
            f.write(f"Success Rate: {(passed/len(test_results)*100):.1f}%\n\n")

            # Group results by host
            results_by_host = {}
            for result in test_results:
                host = getattr(result, "host", "Unknown")
                if host not in results_by_host:
                    results_by_host[host] = []
                results_by_host[host].append(result)

            f.write("RESULTS BY HOST:\n")
            f.write("-" * 80 + "\n")

            for host, host_results in results_by_host.items():
                host_passed = sum(
                    1 for r in host_results if getattr(r, "passed", False)
                )
                host_failed = len(host_results) - host_passed

                f.write(f"\nHost: {host}\n")
                f.write(
                    f"  Total: {len(host_results)}, Passed: {host_passed}, Failed: {host_failed}\n"
                )

                # List failed tests
                failed_tests = [
                    r for r in host_results if not getattr(r, "passed", False)
                ]
                if failed_tests:
                    f.write("  Failed Tests:\n")
                    for test in failed_tests:
                        f.write(
                            f"    - {getattr(test, 'test_name', 'Unknown')} "
                            f"({getattr(test, 'method', 'Unknown')})\n"
                        )

            f.write("\n" + "=" * 80 + "\n")

        return filename

    def export_to_html(
        self,
        test_results: List[Any],
        filename: str = None,
        open_browser: bool = False,
    ) -> str:
        """Export test results to HTML format and optionally open in browser"""
        if not filename:
            filename = self._generate_filename("html")

        # Import HTMLReportGenerator here to avoid circular imports
        from .html_report_generator import HTMLReportGenerator

        # Create HTML report generator
        html_generator = HTMLReportGenerator(self.results_dir)

        # Check config to determine which HTML style to use
        config = html_generator._load_config()
        use_nf_style = config.get("html_generator", {}).get(
            "use_nf_style", False
        )

        # Export using appropriate style
        if use_nf_style:
            html_file = html_generator.export_to_nf_html(
                test_results, filename, config
            )
        else:
            html_file = html_generator.export_to_html(test_results, filename)

        # Open in browser if requested
        if open_browser:
            webbrowser.open(f"file://{os.path.abspath(html_file)}")

        return html_file
