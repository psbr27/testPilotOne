#!/usr/bin/env python3
"""
Demo script to test the new NF-style HTML report generator
"""

import argparse
import os
import sys
from datetime import datetime

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from testpilot.exporters.html_report_generator import HTMLReportGenerator


class MockTestResult:
    """Mock test result for demonstration"""

    def __init__(
        self,
        test_name,
        sheet,
        method="GET",
        host="example.com",
        passed=True,
        duration=1.5,
        command="",
        output="",
        pattern_match="",
        expected_status=200,
        actual_status=200,
        fail_reason="",
        error="",
        response_payload=None,
        response_headers=None,
        request_payload=None,
    ):
        self.test_name = test_name
        self.sheet = sheet
        self.method = method
        self.host = host
        self.passed = passed
        self.duration = duration
        self.command = command
        self.output = output
        self.pattern_match = pattern_match
        self.expected_status = expected_status
        self.actual_status = actual_status
        self.fail_reason = fail_reason
        self.error = error
        self.response_payload = response_payload
        self.Response_Payload = (
            response_payload  # Both forms for compatibility
        )
        self.response_headers = response_headers or {}
        self.request_payload = request_payload


def create_sample_test_results():
    """Create sample test results for demonstration"""
    results = []

    # Test Sheet 1 - AMF Registration Tests
    results.extend(
        [
            MockTestResult(
                test_name="test_ue_registration_1",
                sheet="AMF Registration Tests",
                method="POST",
                host="amf.5g-core.com",
                passed=True,
                command="curl -X POST https://amf.5g-core.com/namf-comm/v1/ue-registration",
                output="SSH execution output - command completed successfully",
                response_payload='{"result": "success", "ue_id": "123456789", "amf_id": "amf-001", "registration_status": "registered", "timestamp": "2024-01-15T10:30:45Z"}',
                response_headers={
                    "Content-Type": "application/json",
                    "Content-Length": "156",
                    "Server": "AMF/1.0",
                    "X-Request-ID": "req-12345",
                    "Date": "Mon, 15 Jan 2024 10:30:45 GMT",
                },
                pattern_match='"result": "success"',
                expected_status=201,
                actual_status=201,
            ),
            MockTestResult(
                test_name="test_ue_registration_2",
                sheet="AMF Registration Tests",
                method="GET",
                host="amf.5g-core.com",
                passed=True,
                command="curl -X GET https://amf.5g-core.com/namf-comm/v1/ue-context/123456789",
                output="SSH execution output - command completed successfully",
                response_payload='{"ue_id": "123456789", "state": "registered", "amf_id": "amf-001", "location": {"cell_id": "cell-789", "tracking_area": "ta-456"}}',
                response_headers={
                    "Content-Type": "application/json",
                    "Content-Length": "148",
                    "Server": "AMF/1.0",
                    "Cache-Control": "no-cache",
                    "X-Request-ID": "req-12346",
                    "Date": "Mon, 15 Jan 2024 10:30:46 GMT",
                },
                pattern_match='"state": "registered"',
                expected_status=200,
                actual_status=200,
            ),
        ]
    )

    # Test Sheet 2 - AMF Mobility Tests
    results.extend(
        [
            MockTestResult(
                test_name="test_handover_1",
                sheet="AMF Mobility Tests",
                method="PUT",
                host="amf.5g-core.com",
                passed=False,
                command="curl -X PUT https://amf.5g-core.com/namf-comm/v1/handover/123456789 -d @request.json",
                output="SSH execution error - HTTP 400 Bad Request",
                request_payload={
                    "ueId": "123456789",
                    "targetCell": {
                        "cellId": "cell-999",
                        "trackingArea": "ta-789",
                        "plmnId": "310-260",
                    },
                    "handoverType": "5G_TO_5G",
                    "sourceCell": {
                        "cellId": "cell-789",
                        "trackingArea": "ta-456",
                    },
                    "cause": "radioNetwork",
                },
                response_payload='{"error": "handover_failed", "reason": "target_cell_unavailable", "error_code": "AMF-ERR-002", "timestamp": "2024-01-15T10:30:47Z"}',
                response_headers={
                    "Content-Type": "application/problem+json",
                    "Content-Length": "132",
                    "Server": "AMF/1.0",
                    "X-Error-Code": "AMF-ERR-002",
                    "Date": "Mon, 15 Jan 2024 10:30:47 GMT",
                },
                pattern_match='"result": "success"',
                expected_status=200,
                actual_status=400,
                fail_reason="Handover failed - target cell unavailable",
            )
        ]
    )

    # Test Sheet 3 - Authentication Tests
    results.extend(
        [
            MockTestResult(
                test_name="test_authentication_1",
                sheet="Authentication Tests",
                method="POST",
                host="ausf.5g-core.com",
                passed=True,
                command="curl -X POST https://ausf.5g-core.com/nausf-auth/v1/authenticate",
                output='{"auth_result": "success", "auth_vector": "abcd1234", "ue_id": "123456789"}',
                pattern_match='"auth_result": "success"',
                expected_status=200,
                actual_status=200,
            ),
            MockTestResult(
                test_name="test_authentication_2",
                sheet="Authentication Tests",
                method="POST",
                host="ausf.5g-core.com",
                passed=True,
                command="curl -X POST https://ausf.5g-core.com/nausf-auth/v1/verify-auth",
                output='{"verification": "passed", "ue_id": "123456789"}',
                pattern_match='"verification": "passed"',
                expected_status=200,
                actual_status=200,
            ),
        ]
    )

    return results


def main():
    """Main function to demonstrate NF-style HTML generation"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="NF-Style HTML Report Generator Demo"
    )
    parser.add_argument(
        "-m",
        "--mode",
        choices=["otp", "audit", "config", "OTP", "AUDIT", "CONFIG"],
        default="OTP",
        help="Test mode: otp, audit, or config (default: otp)",
    )
    args = parser.parse_args()

    # Normalize test mode to uppercase
    test_mode = args.mode.upper()

    print(f"🎯 NF-Style HTML Report Generator Demo - {test_mode} Mode")
    print("=" * 50)

    # Create sample test results
    print("📊 Creating sample test results...")
    test_results = create_sample_test_results()
    print(
        f"   Created {len(test_results)} test results across {len(set(r.sheet for r in test_results))} sheets"
    )

    # Create HTML generator
    print("\n🏗️  Creating HTML generator...")
    html_generator = HTMLReportGenerator("test_results")

    # Load config to show current settings
    config = html_generator._load_config()
    use_nf_style = config.get("html_generator", {}).get("use_nf_style", False)
    print(f"   NF-style enabled: {use_nf_style}")

    if use_nf_style:
        system_info = config.get("system_under_test", {})
        print(f"   System Under Test: {system_info.get('nf_type', 'Unknown')}")

    # Generate both styles for comparison
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    print("\n📄 Generating HTML reports...")

    # Generate NF-style report
    nf_filename = (
        f"test_results/nf_style_{test_mode.lower()}_report_{timestamp}.html"
    )
    html_generator.export_to_nf_html(
        test_results, nf_filename, config, test_mode=test_mode
    )
    print(f"   ✅ NF-style {test_mode} report: {nf_filename}")

    # Generate standard report for comparison
    standard_filename = f"test_results/standard_report_{timestamp}.html"
    html_generator.export_to_html(test_results, standard_filename)
    print(f"   ✅ Standard report: {standard_filename}")

    print("\n🎉 Demo completed!")
    print(f"📁 Reports generated in: test_results/")
    print(f"🌐 Open the HTML files in your browser to see the difference:")
    print(f"   - NF Style: file://{os.path.abspath(nf_filename)}")
    print(f"   - Standard: file://{os.path.abspath(standard_filename)}")

    # Show summary
    total_tests = len(test_results)
    passed_tests = sum(1 for r in test_results if r.passed)
    failed_tests = total_tests - passed_tests

    print(f"\n📊 Test Results Summary:")
    print(f"   Total: {total_tests}")
    print(f"   Passed: {passed_tests}")
    print(f"   Failed: {failed_tests}")

    sheets = {}
    for result in test_results:
        if result.sheet not in sheets:
            sheets[result.sheet] = {"passed": 0, "failed": 0}
        if result.passed:
            sheets[result.sheet]["passed"] += 1
        else:
            sheets[result.sheet]["failed"] += 1

    print(f"\n📋 Results by Sheet:")
    for sheet_name, counts in sheets.items():
        status = "✅ PASSED" if counts["failed"] == 0 else "❌ FAILED"
        print(
            f"   {sheet_name}: {counts['passed']} passed, {counts['failed']} failed {status}"
        )


if __name__ == "__main__":
    # Ensure test_results directory exists
    os.makedirs("test_results", exist_ok=True)
    main()
