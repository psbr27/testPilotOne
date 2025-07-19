"""
Mock Test Executor
==================

Executes Excel-driven test flows against mock NRF server.
Integrates with existing TestPilot Excel parsing and validation engine.
"""

import json
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import pandas as pd
import requests

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from excel_parser import ExcelParser, parse_excel_to_flows
from mock_testing.validation_engine import ValidationEngine, ValidationResult


@dataclass
class MockTestResult:
    """Result of a mock test step execution."""

    sheet: str
    test_name: str
    step_number: int
    method: str
    url: str
    expected_status: Optional[int]
    actual_status: int
    validation_result: ValidationResult
    response_text: str
    duration: float
    passed: bool
    error: Optional[str] = None


class MockTestExecutor:
    """
    Executes Excel-based test flows against mock NRF server.

    Features:
    - Reads test scenarios from Excel using existing TestPilot parser
    - Executes HTTP requests against mock server
    - Validates responses using 3-layer validation engine
    - Supports multi-step test flows with state management
    """

    def __init__(
        self,
        mock_server_url: str = "http://localhost:8081",
        payloads_dir: str = "test_payloads",
        timeout: int = 30,
    ):
        self.mock_server_url = mock_server_url.rstrip("/")
        self.payloads_dir = Path(payloads_dir)
        self.timeout = timeout

        # Initialize validation engine
        self.validator = ValidationEngine(payloads_dir=str(self.payloads_dir))

        # Test session for maintaining state
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Content-Type": "application/json",
                "User-Agent": "TestPilot-MockTesting/1.0",
            }
        )

    def execute_excel_tests(
        self,
        excel_file: str,
        sheet_name: Optional[str] = None,
        test_name: Optional[str] = None,
    ) -> List[MockTestResult]:
        """
        Execute tests from Excel file.

        Args:
            excel_file: Path to Excel file
            sheet_name: Specific sheet to test (None for all)
            test_name: Specific test to run (None for all)

        Returns:
            List of test results
        """
        print(f"📊 Loading tests from: {excel_file}")

        # Parse Excel file
        parser = ExcelParser(excel_file)
        valid_sheets = parser.list_valid_sheets()

        if sheet_name:
            if sheet_name not in valid_sheets:
                raise ValueError(
                    f"Sheet '{sheet_name}' not found. Available: {valid_sheets}"
                )
            valid_sheets = [sheet_name]

        print(f"📋 Processing sheets: {valid_sheets}")

        # Parse test flows
        all_flows = parse_excel_to_flows(parser, valid_sheets)

        # Filter by test name if specified
        if test_name:
            all_flows = [
                flow for flow in all_flows if flow.test_name == test_name
            ]
            if not all_flows:
                raise ValueError(f"Test '{test_name}' not found")

        print(f"🧪 Found {len(all_flows)} test flows")

        # Execute all test flows
        all_results = []
        for flow in all_flows:
            print(f"\n🔄 Executing test flow: {flow.test_name}")
            flow_results = self.execute_test_flow(flow)
            all_results.extend(flow_results)

        return all_results

    def execute_test_flow(self, flow) -> List[MockTestResult]:
        """
        Execute a single test flow (multiple steps).

        Args:
            flow: TestFlow object from Excel parser

        Returns:
            List of step results
        """
        results = []
        flow_context = {}

        print(f"  📝 Test: {flow.test_name} ({len(flow.steps)} steps)")

        for step_num, step in enumerate(flow.steps, 1):
            print(
                f"    Step {step_num}/{len(flow.steps)}: {step.method} {step.url}"
            )

            try:
                result = self.execute_test_step(
                    flow, step, step_num, flow_context
                )
                results.append(result)

                # Update flow context if step passed
                if result.passed:
                    # Store response for potential use in subsequent steps
                    flow_context[f"step_{step_num}_response"] = (
                        result.response_text
                    )
                else:
                    print(
                        f"    ❌ Step {step_num} failed: {result.validation_result.reason}"
                    )
                    # Continue with remaining steps even if one fails

            except Exception as e:
                # Handle execution errors
                error_result = MockTestResult(
                    sheet=flow.sheet,
                    test_name=flow.test_name,
                    step_number=step_num,
                    method=step.method,
                    url=step.url or "unknown",
                    expected_status=step.expected_status,
                    actual_status=0,
                    validation_result=ValidationResult(
                        passed=False, reason=f"Execution error: {e}"
                    ),
                    response_text="",
                    duration=0.0,
                    passed=False,
                    error=str(e),
                )
                results.append(error_result)
                print(f"    💥 Step {step_num} error: {e}")

        return results

    def execute_test_step(
        self, flow, step, step_number: int, context: Dict
    ) -> MockTestResult:
        """
        Execute a single test step.

        Args:
            flow: Parent test flow
            step: TestStep object
            step_number: Step number in flow
            context: Flow context for state sharing

        Returns:
            MockTestResult for this step
        """
        start_time = time.time()

        # Build request
        method = step.method.upper()
        url = self.build_request_url(step.url, context)
        headers = self.build_request_headers(step.headers, context)
        payload = self.build_request_payload(step.payload, context)

        # Add test context header for mock server
        response_payload = step.other_fields.get("Response_Payload", "")
        if (
            response_payload
            and not pd.isna(response_payload)
            and str(response_payload).strip()
        ):
            headers["X-Test-Context"] = str(response_payload).strip()

        # Also handle pattern_match in the header for better context
        pattern_match = step.pattern_match
        if (
            pattern_match
            and not pd.isna(pattern_match)
            and str(pattern_match).strip()
        ):
            headers["X-Pattern-Match"] = "true"

        try:
            # Execute HTTP request
            response = self.session.request(
                method=method,
                url=url,
                headers=headers,
                json=payload if payload else None,
                timeout=self.timeout,
            )

            duration = time.time() - start_time

            # Validate response
            validation_result = self.validator.validate_step(
                response_text=response.text,
                actual_status=response.status_code,
                expected_status=step.expected_status,
                response_payload=step.other_fields.get("Response_Payload"),
                pattern_match=step.pattern_match,
            )

            return MockTestResult(
                sheet=flow.sheet,
                test_name=flow.test_name,
                step_number=step_number,
                method=method,
                url=url,
                expected_status=step.expected_status,
                actual_status=response.status_code,
                validation_result=validation_result,
                response_text=response.text,
                duration=duration,
                passed=validation_result.passed,
            )

        except requests.RequestException as e:
            duration = time.time() - start_time

            return MockTestResult(
                sheet=flow.sheet,
                test_name=flow.test_name,
                step_number=step_number,
                method=method,
                url=url,
                expected_status=step.expected_status,
                actual_status=0,
                validation_result=ValidationResult(
                    passed=False, reason=f"Request failed: {e}"
                ),
                response_text="",
                duration=duration,
                passed=False,
                error=str(e),
            )

    def build_request_url(self, url: Optional[str], context: Dict) -> str:
        """
        Build request URL, replacing placeholders and making absolute.

        Args:
            url: URL from test step (may have placeholders)
            context: Flow context for placeholder resolution

        Returns:
            Complete absolute URL
        """
        if not url:
            return f"{self.mock_server_url}/nnrf-nfm/v1/nf-instances/"

        # Replace common placeholders
        processed_url = url
        processed_url = processed_url.replace(
            "{ocnrf-ingressgateway}", "localhost"
        )
        processed_url = processed_url.replace(
            ":8081", f":{urlparse(self.mock_server_url).port or 8081}"
        )

        # Make absolute if relative
        if not processed_url.startswith("http"):
            if processed_url.startswith("/"):
                processed_url = f"{self.mock_server_url}{processed_url}"
            else:
                processed_url = f"{self.mock_server_url}/{processed_url}"

        return processed_url

    def build_request_headers(
        self, headers: Any, context: Dict
    ) -> Dict[str, str]:
        """Build request headers from step data."""
        if isinstance(headers, dict):
            return headers
        elif isinstance(headers, str):
            try:
                return json.loads(headers)
            except json.JSONDecodeError:
                return {"Content-Type": "application/json"}
        else:
            return {"Content-Type": "application/json"}

    def build_request_payload(
        self, payload: Any, context: Dict
    ) -> Optional[Dict]:
        """
        Build request payload from step data.

        Can load from JSON file or use inline JSON.
        """
        if not payload or pd.isna(payload):
            return None

        # If payload is a filename, load from file
        if isinstance(payload, str) and payload.endswith(".json"):
            payload_file = self.payloads_dir / payload
            if payload_file.exists():
                try:
                    with open(payload_file, "r", encoding="utf-8") as f:
                        return json.load(f)
                except Exception as e:
                    print(
                        f"Warning: Could not load payload file {payload}: {e}"
                    )
                    return None

        # Try to parse as JSON
        if isinstance(payload, str):
            try:
                return json.loads(payload)
            except json.JSONDecodeError:
                return {"data": payload}  # Wrap as simple object

        return payload

    def print_results_summary(self, results: List[MockTestResult]):
        """Print a summary of test execution results."""
        if not results:
            print("No test results to display")
            return

        total_tests = len(results)
        passed_tests = sum(1 for r in results if r.passed)
        failed_tests = total_tests - passed_tests

        print(f"\n📊 Test Execution Summary")
        print(f"=" * 50)
        print(f"Total steps: {total_tests}")
        print(f"Passed: {passed_tests} ({passed_tests/total_tests*100:.1f}%)")
        print(f"Failed: {failed_tests} ({failed_tests/total_tests*100:.1f}%)")

        if failed_tests > 0:
            print(f"\n❌ Failed Tests:")
            for result in results:
                if not result.passed:
                    print(
                        f"  - {result.test_name} Step {result.step_number}: {result.validation_result.reason}"
                    )

        print(
            f"\n⏱️  Average step duration: {sum(r.duration for r in results)/total_tests:.2f}s"
        )

    def reset_mock_server(self):
        """Reset the mock server state."""
        try:
            response = self.session.post(f"{self.mock_server_url}/mock/reset")
            if response.status_code == 200:
                print("✅ Mock server state reset")
            else:
                print(
                    f"⚠️  Could not reset mock server: {response.status_code}"
                )
        except Exception as e:
            print(f"⚠️  Could not reset mock server: {e}")


def main():
    """CLI entry point for mock test executor."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Execute mock tests from Excel"
    )
    parser.add_argument(
        "--excel", required=True, help="Path to Excel file with test scenarios"
    )
    parser.add_argument(
        "--sheet", help="Specific sheet to test (default: all sheets)"
    )
    parser.add_argument(
        "--test", help="Specific test name to run (default: all tests)"
    )
    parser.add_argument(
        "--server",
        default="http://localhost:8081",
        help="Mock server URL (default: http://localhost:8081)",
    )
    parser.add_argument(
        "--payloads-dir",
        default="test_payloads",
        help="Directory with test payload files",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset mock server state before running tests",
    )

    args = parser.parse_args()

    # Create executor
    executor = MockTestExecutor(
        mock_server_url=args.server, payloads_dir=args.payloads_dir
    )

    try:
        # Reset server if requested
        if args.reset:
            executor.reset_mock_server()

        # Execute tests
        results = executor.execute_excel_tests(
            excel_file=args.excel, sheet_name=args.sheet, test_name=args.test
        )

        # Print summary
        executor.print_results_summary(results)

        # Exit with error code if any tests failed
        failed_count = sum(1 for r in results if not r.passed)
        if failed_count > 0:
            print(f"\n❌ {failed_count} test steps failed")
            sys.exit(1)
        else:
            print(f"\n✅ All {len(results)} test steps passed!")
            sys.exit(0)

    except Exception as e:
        print(f"💥 Error executing tests: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
