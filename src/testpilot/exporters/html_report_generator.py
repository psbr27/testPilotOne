"""
HTML Report Generator for Test Results
Provides functionality to generate interactive HTML reports for test results
"""

import json
import os
from datetime import datetime
from typing import Any, Dict, List

from .test_results_exporter import TestResultsExporter


class HTMLReportGenerator(TestResultsExporter):
    """Generate interactive HTML reports for test results"""

    def __init__(self, results_dir="test_results"):
        """Initialize with output directory"""
        super().__init__(results_dir)
        self.css_styles = self._get_css_styles()
        self.js_scripts = self._get_js_scripts()

    def _get_css_styles(self):
        """Return CSS styles for the HTML report"""
        return """
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background-color: #fff;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
        }
        h1 {
            color: #2c3e50;
            text-align: center;
            margin-bottom: 30px;
            padding-bottom: 10px;
            border-bottom: 2px solid #eee;
        }
        h2 {
            color: #34495e;
            margin-top: 30px;
            margin-bottom: 15px;
            padding-bottom: 5px;
            border-bottom: 1px solid #eee;
        }
        .summary {
            background-color: #f8f9fa;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
            display: flex;
            justify-content: space-between;
            flex-wrap: wrap;
        }
        .summary-item {
            text-align: center;
            padding: 10px;
            flex: 1;
            min-width: 120px;
        }
        .summary-item h3 {
            margin: 0;
            font-size: 16px;
            color: #555;
        }
        .summary-item p {
            margin: 5px 0 0;
            font-size: 24px;
            font-weight: bold;
        }
        .total { color: #2c3e50; }
        .passed { color: #27ae60; }
        .failed { color: #e74c3c; }

        .sheet-tab {
            border: 1px solid #ddd;
            border-radius: 5px;
            margin-bottom: 10px;
            overflow: hidden;
        }
        .sheet-header {
            background-color: #f1f1f1;
            padding: 12px 15px;
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-weight: bold;
        }
        .sheet-summary {
            display: flex;
            align-items: center;
            gap: 15px;
        }
        .chart-container {
            width: 120px;
            height: 120px;
            margin: 10px auto;
        }
        .sheet-stats {
            display: flex;
            gap: 20px;
            margin-bottom: 15px;
            padding: 10px;
            background-color: #f9f9f9;
            border-radius: 5px;
        }
        .sheet-header:hover {
            background-color: #e9e9e9;
        }
        .sheet-header .status-badge {
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: bold;
        }
        .status-pass {
            background-color: #d4edda;
            color: #155724;
        }
        .status-fail {
            background-color: #f8d7da;
            color: #721c24;
        }
        .status-mixed {
            background-color: #fff3cd;
            color: #856404;
        }
        .sheet-content {
            display: none;
            padding: 0;
        }
        .test-table {
            width: 100%;
            border-collapse: collapse;
        }
        .test-table th, .test-table td {
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        .test-table th {
            background-color: #f8f9fa;
            font-weight: 600;
        }
        .test-table tr:hover {
            background-color: #f5f5f5;
        }
        .test-row {
            cursor: pointer;
        }
        .test-row.failed {
            background-color: rgba(231, 76, 60, 0.05);
        }
        .test-row.passed {
            background-color: rgba(39, 174, 96, 0.05);
        }
        .test-details {
            display: none;
            padding: 15px;
            background-color: #f8f9fa;
            border-top: 1px solid #ddd;
        }
        .details-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
        }
        .detail-item {
            margin-bottom: 10px;
        }
        .detail-item h4 {
            margin: 0 0 5px 0;
            font-size: 14px;
            color: #555;
        }
        .detail-item pre {
            margin: 0;
            padding: 10px;
            background-color: #f1f1f1;
            border-radius: 4px;
            overflow: auto;
            max-height: 200px;
            font-family: monospace;
            font-size: 13px;
            white-space: pre-wrap;
        }
        .filter-options {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
        }
        .filter-btn {
            padding: 8px 15px;
            background-color: #f8f9fa;
            border: 1px solid #ddd;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
        }
        .filter-btn.active {
            background-color: #007bff;
            color: white;
            border-color: #007bff;
        }
        .timestamp {
            text-align: center;
            margin-top: 30px;
            color: #777;
            font-size: 12px;
        }
        .test-group {
            border: 1px solid #e0e0e0;
            border-radius: 4px;
            margin-bottom: 10px;
            overflow: hidden;
        }
        .test-group-header {
            background-color: #f5f5f5;
            padding: 10px 15px;
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-weight: 600;
        }
        .test-group-header:hover {
            background-color: #e8e8e8;
        }
        .test-group-header.passed {
            border-left: 4px solid #27ae60;
        }
        .test-group-header.failed {
            border-left: 4px solid #e74c3c;
        }
        .test-group-name {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .test-group-name.passed {
            color: #27ae60;
        }
        .test-group-name.failed {
            color: #e74c3c;
        }
        .test-group-content {
            display: none;
            padding: 0;
        }
        .test-steps-count {
            color: #666;
            font-size: 14px;
            font-weight: normal;
        }
        """

    def _get_js_scripts(self):
        """Return JavaScript for the HTML report"""
        return """
        document.addEventListener('DOMContentLoaded', function() {
            // Create pie charts for overall summary and each sheet
            createOverallPieChart();
            createSheetPieCharts();

            // Toggle sheet content
            document.querySelectorAll('.sheet-header').forEach(header => {
                header.addEventListener('click', function() {
                    const content = this.nextElementSibling;
                    if (content.style.display === 'block') {
                        content.style.display = 'none';
                    } else {
                        content.style.display = 'block';
                    }
                });
            });

            // Toggle test details
            document.querySelectorAll('.test-row').forEach(row => {
                row.addEventListener('click', function() {
                    const detailsId = this.getAttribute('data-details');
                    const details = document.getElementById(detailsId);
                    if (details.style.display === 'block') {
                        details.style.display = 'none';
                    } else {
                        details.style.display = 'block';
                    }
                });
            });

            // Toggle test group content
            document.querySelectorAll('.test-group-header').forEach(header => {
                header.addEventListener('click', function() {
                    const content = this.nextElementSibling;
                    if (content.style.display === 'block') {
                        content.style.display = 'none';
                    } else {
                        content.style.display = 'block';
                    }
                });
            });

            // Filter buttons
            document.querySelectorAll('.filter-btn').forEach(btn => {
                btn.addEventListener('click', function() {
                    const filter = this.getAttribute('data-filter');

                    // Update active button
                    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
                    this.classList.add('active');

                    // Filter rows
                    document.querySelectorAll('.test-row').forEach(row => {
                        if (filter === 'all') {
                            row.style.display = '';
                        } else if (filter === 'passed' && row.classList.contains('passed')) {
                            row.style.display = '';
                        } else if (filter === 'failed' && row.classList.contains('failed')) {
                            row.style.display = '';
                        } else {
                            row.style.display = 'none';
                        }
                    });
                });
            });
        });

        // Function to create the overall summary pie chart
        function createOverallPieChart() {
            const ctx = document.getElementById('overall-chart').getContext('2d');
            const passed = parseInt(document.getElementById('overall-passed').textContent);
            const failed = parseInt(document.getElementById('overall-failed').textContent);

            new Chart(ctx, {
                type: 'pie',
                data: {
                    labels: ['Passed', 'Failed'],
                    datasets: [{
                        data: [passed, failed],
                        backgroundColor: ['#27ae60', '#e74c3c'],
                        borderColor: ['#2ecc71', '#c0392b'],
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'bottom'
                        }
                    }
                }
            });

            // Create sheet comparison chart
            createSheetComparisonChart();
        }

        // Function to create pie charts for each sheet
        function createSheetPieCharts() {
            document.querySelectorAll('.sheet-chart').forEach(canvas => {
                const ctx = canvas.getContext('2d');
                const passed = parseInt(canvas.getAttribute('data-passed'));
                const failed = parseInt(canvas.getAttribute('data-failed'));

                new Chart(ctx, {
                    type: 'pie',
                    data: {
                        labels: ['Passed', 'Failed'],
                        datasets: [{
                            data: [passed, failed],
                            backgroundColor: ['#27ae60', '#e74c3c'],
                            borderColor: ['#2ecc71', '#c0392b'],
                            borderWidth: 1
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: {
                                display: false
                            }
                        }
                    }
                });
            });
        }

        // Function to create sheet comparison chart
        function createSheetComparisonChart() {
            const ctx = document.getElementById('sheet-comparison-chart').getContext('2d');

            // Collect data from all sheet tabs
            const sheetNames = [];
            const passedCounts = [];
            const failedCounts = [];

            document.querySelectorAll('.sheet-chart').forEach(canvas => {
                // Get the sheet name from the closest sheet-tab
                const sheetTab = canvas.closest('.sheet-tab');
                const sheetName = sheetTab.querySelector('.sheet-header .sheet-summary span').textContent;

                const passed = parseInt(canvas.getAttribute('data-passed'));
                const failed = parseInt(canvas.getAttribute('data-failed'));

                sheetNames.push(sheetName);
                passedCounts.push(passed);
                failedCounts.push(failed);
            });

            new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: sheetNames,
                    datasets: [
                        {
                            label: 'Passed',
                            data: passedCounts,
                            backgroundColor: '#27ae60',
                            borderColor: '#2ecc71',
                            borderWidth: 1
                        },
                        {
                            label: 'Failed',
                            data: failedCounts,
                            backgroundColor: '#e74c3c',
                            borderColor: '#c0392b',
                            borderWidth: 1
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        x: {
                            stacked: true,
                            title: {
                                display: true,
                                text: 'Sheet Name'
                            }
                        },
                        y: {
                            stacked: true,
                            beginAtZero: true,
                            title: {
                                display: true,
                                text: 'Number of Tests'
                            }
                        }
                    },
                    plugins: {
                        legend: {
                            position: 'top'
                        },
                        title: {
                            display: true,
                            text: 'Test Results by Sheet'
                        }
                    }
                }
            });
        }
        """

    def _extract_test_name(self, test_name: str) -> str:
        """Extract base test name by removing _<digits> suffix"""
        import re

        return re.sub(r"_\d+$", "", test_name)

    def export_to_html(
        self, test_results: List[Any], filename: str = None
    ) -> str:
        """Export test results to an interactive HTML report"""
        if not filename:
            filename = self._generate_filename("html")

        # Group results by sheet
        results_by_sheet = {}
        for result in test_results:
            sheet = getattr(result, "sheet", "Unknown")
            if sheet not in results_by_sheet:
                results_by_sheet[sheet] = []
            results_by_sheet[sheet].append(result)

        # Calculate summary statistics
        total_tests = len(test_results)
        passed_tests = sum(
            1 for r in test_results if getattr(r, "passed", False)
        )
        failed_tests = total_tests - passed_tests
        pass_rate = (
            (passed_tests / total_tests * 100) if total_tests > 0 else 0
        )

        # Generate timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Generate HTML content
        html_content = f"""<!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Test Results Report</title>
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
            <style>
            {self.css_styles}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Test Results Report</h1>
                <p style="text-align: center; color: #777; margin-top: -20px; margin-bottom: 30px; font-size: 14px;">
                    Generated on {timestamp}
                </p>

                <div class="summary">
                    <div class="summary-item">
                        <h3>Total Tests</h3>
                        <p class="total">{total_tests}</p>
                    </div>
                    <div class="summary-item">
                        <h3>Passed</h3>
                        <p class="passed" id="overall-passed">{passed_tests}</p>
                    </div>
                    <div class="summary-item">
                        <h3>Failed</h3>
                        <p class="failed" id="overall-failed">{failed_tests}</p>
                    </div>
                    <div class="summary-item">
                        <h3>Pass Rate</h3>
                        <p>{pass_rate:.1f}%</p>
                    </div>
                </div>

                <div class="chart-container" style="width: 200px; height: 200px; margin: 0 auto;">
                    <canvas id="overall-chart"></canvas>
                </div>

                <h2>Tests by Sheet</h2>
                <div class="chart-container" style="width: 100%; height: 300px; margin: 20px auto;">
                    <canvas id="sheet-comparison-chart"></canvas>
                </div>

                <div class="filter-options">
                    <button class="filter-btn active" data-filter="all">All Tests</button>
                    <button class="filter-btn" data-filter="passed">Passed Only</button>
                    <button class="filter-btn" data-filter="failed">Failed Only</button>
                </div>

                <h2>Results by Sheet</h2>
        """

        # Add sheet tabs
        for sheet_name, sheet_results in results_by_sheet.items():
            sheet_passed = sum(
                1 for r in sheet_results if getattr(r, "passed", False)
            )
            sheet_failed = len(sheet_results) - sheet_passed
            sheet_pass_rate = (
                (sheet_passed / len(sheet_results) * 100)
                if len(sheet_results) > 0
                else 0
            )

            # Group tests by test name (without _<digits>)
            tests_by_name = {}
            for result in sheet_results:
                test_name = getattr(result, "test_name", "Unknown")
                base_test_name = self._extract_test_name(test_name)
                if base_test_name not in tests_by_name:
                    tests_by_name[base_test_name] = []
                tests_by_name[base_test_name].append(result)

            # Determine sheet status
            if sheet_failed == 0:
                status_class = "status-pass"
                status_text = "PASS"
            elif sheet_passed == 0:
                status_class = "status-fail"
                status_text = "FAIL"
            else:
                status_class = "status-mixed"
                status_text = f"MIXED ({sheet_passed}/{len(sheet_results)})"

            html_content += f"""
                <div class="sheet-tab">
                    <div class="sheet-header">
                        <div class="sheet-summary">
                            <span>{sheet_name}</span>
                            <span class="status-badge {status_class}">{status_text}</span>
                        </div>
                    </div>
                    <div class="sheet-content">
                        <div class="sheet-stats">
                            <div class="chart-container">
                                <canvas class="sheet-chart" data-passed="{sheet_passed}" data-failed="{sheet_failed}"></canvas>
                            </div>
                            <div>
                                <p><strong>Total Tests:</strong> {len(sheet_results)}</p>
                                <p><strong>Passed:</strong> <span class="passed">{sheet_passed}</span></p>
                                <p><strong>Failed:</strong> <span class="failed">{sheet_failed}</span></p>
                                <p><strong>Pass Rate:</strong> {sheet_pass_rate:.1f}%</p>
                            </div>
                        </div>
                        <div class="test-groups">
            """

            # Add test groups for this sheet
            for test_name, test_results in tests_by_name.items():
                # Determine if all tests in this group passed
                all_passed = all(
                    getattr(r, "passed", False) for r in test_results
                )
                group_status = "passed" if all_passed else "failed"
                status_text = "PASS" if all_passed else "FAIL"

                html_content += f"""
                            <div class="test-group">
                                <div class="test-group-header {group_status}">
                                    <div class="test-group-name {group_status}">
                                        <span>{test_name}</span>
                                        <span class="test-steps-count">({len(test_results)} steps)</span>
                                    </div>
                                    <span class="status-badge {'status-pass' if all_passed else 'status-fail'}">{status_text}</span>
                                </div>
                                <div class="test-group-content">
                                    <table class="test-table">
                                        <thead>
                                            <tr>
                                                <th>Step</th>
                                                <th>Method</th>
                                                <th>Host</th>
                                                <th>Status</th>
                                                <th>Duration (s)</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                """

                # Add test rows for this group
                for i, result in enumerate(test_results):
                    step_name = getattr(result, "test_name", "Unknown")
                    method = getattr(result, "method", "GET")
                    host = getattr(result, "host", "Unknown")
                    passed = getattr(result, "passed", False)
                    duration = getattr(result, "duration", 0.0)
                    status = "PASS" if passed else "FAIL"
                    row_class = "passed" if passed else "failed"
                    details_id = f"details-{sheet_name.replace(' ', '-')}-{test_name.replace(' ', '-')}-{i}"

                    html_content += f"""
                                            <tr class="test-row {row_class}" data-details="{details_id}">
                                                <td class="test-name">{step_name}</td>
                                                <td class="method">{method}</td>
                                                <td class="host">{host}</td>
                                                <td><span class="status-badge {'status-pass' if passed else 'status-fail'}">{status}</span></td>
                                                <td>{duration:.2f}s</td>
                                            </tr>
                    """

                    # Add collapsible details section for this test
                    command = getattr(result, "command", "")
                    error = getattr(result, "error", "")
                    output = getattr(result, "output", "")
                    fail_reason = getattr(result, "fail_reason", "")
                    expected_status = getattr(result, "expected_status", "N/A")
                    actual_status = getattr(result, "actual_status", "N/A")
                    pattern_match = getattr(result, "pattern_match", "")
                    pattern_found = getattr(result, "pattern_found", "")

                    html_content += f"""
                                            <tr>
                                                <td colspan="5" class="test-details" id="{details_id}">
                                                    <div class="details-grid">
                                                        <div class="detail-item">
                                                            <h4>Command</h4>
                                                            <pre>{command}</pre>
                                                        </div>
                    """

                    if error:
                        html_content += f"""
                                                        <div class="detail-item">
                                                            <h4>Error</h4>
                                                            <pre>{error}</pre>
                                                        </div>
                        """

                    if fail_reason:
                        html_content += f"""
                                                        <div class="detail-item">
                                                            <h4>Failure Reason</h4>
                                                            <pre>{fail_reason}</pre>
                                                        </div>
                        """

                    # Add detailed comparison information if available
                    details = getattr(result, "details", None)
                    if details and not result.passed:
                        # Convert details to JSON-serializable format
                        def make_json_serializable(obj):
                            """Convert DeepDiff objects to JSON-serializable format"""
                            if hasattr(obj, "__dict__"):
                                # For objects with __dict__, convert to dict
                                return {
                                    k: make_json_serializable(v)
                                    for k, v in obj.__dict__.items()
                                }
                            elif hasattr(obj, "__iter__") and not isinstance(
                                obj, (str, bytes)
                            ):
                                # For iterables (including SetOrdered), convert to list
                                try:
                                    return [
                                        make_json_serializable(item)
                                        for item in obj
                                    ]
                                except (TypeError, RuntimeError):
                                    # If iteration fails, convert to string
                                    return str(obj)
                            elif isinstance(obj, dict):
                                return {
                                    k: make_json_serializable(v)
                                    for k, v in obj.items()
                                }
                            else:
                                # For basic types, return as-is
                                try:
                                    json.dumps(
                                        obj
                                    )  # Test if it's JSON serializable
                                    return obj
                                except (TypeError, ValueError):
                                    return str(obj)

                        try:
                            serializable_details = make_json_serializable(
                                details
                            )
                            details_json = json.dumps(
                                serializable_details, indent=2
                            )
                        except Exception as e:
                            # Fallback to string representation if JSON serialization fails
                            details_json = f"Error serializing details: {str(e)}\n\nDetails (string representation):\n{str(details)}"

                        html_content += f"""
                                                        <div class="detail-item" style="grid-column: span 2;">
                                                            <h4>Detailed Comparison</h4>
                                                            <pre>{details_json}</pre>
                                                        </div>
                        """

                    html_content += f"""
                                                        <div class="detail-item">
                                                            <h4>Expected Status</h4>
                                                            <pre>{expected_status}</pre>
                                                        </div>
                                                        <div class="detail-item">
                                                            <h4>Actual Status</h4>
                                                            <pre>{actual_status}</pre>
                                                        </div>
                    """

                    if pattern_match:
                        html_content += f"""
                                                        <div class="detail-item">
                                                            <h4>Pattern Match</h4>
                                                            <pre>{pattern_match}</pre>
                                                        </div>
                        """

                    if pattern_found:
                        html_content += f"""
                                                        <div class="detail-item">
                                                            <h4>Pattern Found</h4>
                                                            <pre>{pattern_found}</pre>
                                                        </div>
                        """

                    if output:
                        html_content += f"""
                                                        <div class="detail-item" style="grid-column: span 2;">
                                                            <h4>Output</h4>
                                                            <pre>{output}</pre>
                                                        </div>
                        """

                    html_content += """
                                                    </div>
                                                </td>
                                            </tr>
                    """

                html_content += """
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                """

            html_content += """
                        </div>
                    </div>
                </div>
            """

        # Close HTML document
        html_content += f"""
            </div>
            <script>
            {self.js_scripts}
            </script>
        </body>
        </html>
        """

        # Write HTML to file
        with open(filename, "w") as f:
            f.write(html_content)

        return filename
