# =============================================================================
# Test Results Exporter Module
# Provides functionality to export test results in various formats
# =============================================================================

import csv
import json
import os
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
        return os.path.join(self.results_dir, f"test_results_{timestamp}.{format_type}")

    def export_to_json(self, test_results: List[Any], filename: str = None) -> str:
        """Export test results to JSON format"""
        if not filename:
            filename = self._generate_filename("json")

        results_data = []
        for result in test_results:
            result_dict = {
                "host": getattr(result, "host", ""),
                "sheet": getattr(result, "sheet", ""),
                "test_name": getattr(result, "test_name", ""),
                "method": getattr(result, "method", ""),
                "passed": getattr(result, "passed", False),
                "duration": getattr(result, "duration", 0.0),
                "timestamp": getattr(result, "timestamp", ""),
                "error": getattr(result, "error", ""),
                "output": (
                    getattr(result, "output", "")[:500]
                    if hasattr(result, "output")
                    else ""
                ),  # Limit output size
            }

            # Add dry-run status if applicable
            if hasattr(result, "result") and getattr(result, "result", "") == "DRY-RUN":
                result_dict["status"] = "DRY-RUN"
            else:
                result_dict["status"] = "PASS" if result_dict["passed"] else "FAIL"

            results_data.append(result_dict)

        # Add summary information
        summary = {
            "total_tests": len(test_results),
            "passed": sum(1 for r in test_results if getattr(r, "passed", False)),
            "failed": len(test_results)
            - sum(1 for r in test_results if getattr(r, "passed", False)),
            "export_timestamp": datetime.now().isoformat(),
        }

        export_data = {"summary": summary, "results": results_data}

        with open(filename, "w") as f:
            json.dump(export_data, f, indent=2)

        return filename

    def export_to_csv(self, test_results: List[Any], filename: str = None) -> str:
        """Export test results to CSV format"""
        if not filename:
            filename = self._generate_filename("csv")

        headers = [
            "Host",
            "Sheet",
            "Test Name",
            "Method",
            "Status",
            "Duration (s)",
            "Timestamp",
            "Error Message",
        ]

        with open(filename, "w", newline="") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(headers)

            for result in test_results:
                # Determine status
                if (
                    hasattr(result, "result")
                    and getattr(result, "result", "") == "DRY-RUN"
                ):
                    status = "DRY-RUN"
                else:
                    status = "PASS" if getattr(result, "passed", False) else "FAIL"

                row = [
                    getattr(result, "host", ""),
                    getattr(result, "sheet", ""),
                    getattr(result, "test_name", ""),
                    getattr(result, "method", ""),
                    status,
                    f"{getattr(result, 'duration', 0.0):.2f}",
                    getattr(result, "timestamp", ""),
                    getattr(result, "error", "")[:200],  # Limit error message length
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

            f.write(f"Export Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
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
