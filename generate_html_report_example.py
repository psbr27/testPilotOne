#!/usr/bin/env python3
"""
Example script to demonstrate HTML report generation
"""

import json
import os
import sys

from test_result import TestResult
from test_results_exporter import TestResultsExporter


def load_test_results_from_json(json_file):
    """Load test results from a JSON file and convert to TestResult objects"""
    with open(json_file, "r") as f:
        data = json.load(f)

    results = []
    for result_data in data.get("results", []):
        # Create a TestResult object
        result = TestResult(
            sheet=result_data.get("sheet", "Unknown"),
            row_idx=0,  # Default value
            host=result_data.get("host", "Unknown"),
            command=result_data.get("command", ""),
            output=result_data.get("output", ""),
            error=result_data.get("error", ""),
            expected_status=None,
            actual_status=None,
            pattern_match=None,
            pattern_found=None,
            passed=result_data.get("passed", False),
            fail_reason=None,
        )

        # Set additional attributes
        result.test_name = result_data.get("test_name", "Unknown Test")
        result.duration = result_data.get("duration", 0.0)
        result.method = result_data.get("method", "GET")

        # Add to results list
        results.append(result)

    return results


def create_sample_test_results():
    """Create sample test results for demonstration"""
    results = []

    # Sheet 1 - All passed
    for i in range(5):
        result = TestResult(
            sheet="Sheet1",
            row_idx=i,
            host="host1.example.com",
            command=f"curl -X GET https://api.example.com/endpoint{i}",
            output=f"Sample output for test {i}",
            error="",
            expected_status=200,
            actual_status=200,
            pattern_match="success",
            pattern_found=True,
            passed=True,
            fail_reason=None,
        )
        result.test_name = f"Test {i+1}"
        result.duration = 0.5 + (i * 0.1)
        result.method = "GET"
        results.append(result)

    # Sheet 2 - Mixed results
    for i in range(5):
        passed = i % 2 == 0
        result = TestResult(
            sheet="Sheet2",
            row_idx=i + 5,
            host="host2.example.com",
            command=f"curl -X POST https://api.example.com/data -d '{{'id': {i}'}}",
            output=f"Sample output for test {i+5}",
            error=(
                ""
                if passed
                else f"Error: Expected status 201 but got 400. Invalid data format."
            ),
            expected_status=201,
            actual_status=201 if passed else 400,
            pattern_match="created" if passed else "error",
            pattern_found=passed,
            passed=passed,
            fail_reason=None if passed else "Status code mismatch",
        )
        result.test_name = f"Data Creation {i+1}"
        result.duration = 1.0 + (i * 0.2)
        result.method = "POST"
        results.append(result)

    # Sheet 3 - All failed
    for i in range(3):
        result = TestResult(
            sheet="Sheet3",
            row_idx=i + 10,
            host="host3.example.com",
            command=f"curl -X DELETE https://api.example.com/resource/{i}",
            output="Connection refused",
            error=f"Failed to connect to host: Connection timed out",
            expected_status=204,
            actual_status=None,
            pattern_match=None,
            pattern_found=None,
            passed=False,
            fail_reason="Connection failed",
        )
        result.test_name = f"Resource Deletion {i+1}"
        result.duration = 3.0
        result.method = "DELETE"
        results.append(result)

    return results


def main():
    """Main function to generate HTML report"""
    # Create results directory if it doesn't exist
    results_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "test_results"
    )
    os.makedirs(results_dir, exist_ok=True)

    # Create exporter
    exporter = TestResultsExporter(results_dir)

    # Either load results from JSON or create sample results
    if len(sys.argv) > 1 and os.path.exists(sys.argv[1]):
        print(f"Loading test results from {sys.argv[1]}...")
        test_results = load_test_results_from_json(sys.argv[1])
    else:
        print(
            "No JSON file provided or file not found. Creating sample test results..."
        )
        test_results = create_sample_test_results()

    # Export to HTML
    html_file = exporter.export_to_html(test_results)
    print(f"HTML report generated: {html_file}")
    print("Opening report in browser...")


if __name__ == "__main__":
    main()
