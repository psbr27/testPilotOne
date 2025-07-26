#!/usr/bin/env python3
"""
Unit Tests for Refactored AuditProcessor

Tests the audit processor's integration with the core OTP workflow:
- Wrapping of core process_single_step functionality
- Audit-specific validation enhancements
- Integration with AuditEngine
- Proper mocking of dependencies
"""

import json
import os
import sys
import unittest
from unittest.mock import MagicMock, Mock, call, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.testpilot.audit.audit_engine import AuditEngine
from src.testpilot.audit.audit_processor import process_single_step_audit
from src.testpilot.core.test_result import TestResult


class TestAuditProcessor(unittest.TestCase):
    """Test suite for the refactored AuditProcessor"""

    def setUp(self):
        """Set up test fixtures"""
        self.audit_engine = AuditEngine()

        # Mock step data
        self.mock_step = Mock()
        self.mock_step.other_fields = {
            "Pattern_Match": '{"status": "success", "data": {"id": 123}}',
            "Save_As": None,
        }
        self.mock_step.row_idx = 1
        self.mock_step.method = "GET"
        self.mock_step.test_name = "test_audit_step"
        self.mock_step.expected_status = 200
        self.mock_step.pattern_match = (
            '{"status": "success", "data": {"id": 123}}'
        )

        # Mock flow data
        self.mock_flow = Mock()
        self.mock_flow.context = {}
        self.mock_flow.test_name = "test_flow"
        self.mock_flow.sheet = "audit_sheet"

        # Mock dashboard
        self.mock_dashboard = Mock()

        # Test data
        self.target_hosts = ["test-host"]
        self.svc_maps = {"test-host": {"service": "test-service"}}
        self.placeholder_pattern = Mock()
        self.host_cli_map = {"test-host": "kubectl"}
        self.test_results = []

        # Mock args
        self.mock_args = Mock()
        self.mock_args.execution_mode = "production"

    def tearDown(self):
        """Clean up after tests"""
        self.audit_engine.clear_results()

    # =================================================================
    # INTEGRATION WITH CORE PROCESS_SINGLE_STEP
    # =================================================================

    @patch("src.testpilot.audit.audit_processor.process_single_step")
    def test_process_single_step_audit_wraps_core_successfully(
        self, mock_core_process
    ):
        """Test that audit processor properly wraps core process_single_step"""
        # Create a mock test result that core would produce
        mock_test_result = TestResult(
            sheet="audit_sheet",
            row_idx=1,
            host="test-host",
            command="curl -X GET http://api.test/endpoint",
            output='{"status": "success", "data": {"id": 123}}',
            error="",
            expected_status=200,
            actual_status=200,
            pattern_match='{"status": "success", "data": {"id": 123}}',
            pattern_found=True,
            passed=True,
            fail_reason=None,
            test_name="test_audit_step",
            duration=0.5,
            method="GET",
        )

        # Configure mock to add result to test_results
        def add_result(
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
            args,
            step_delay,
        ):
            test_results.append(mock_test_result)

        mock_core_process.side_effect = add_result

        # Execute audit process
        process_single_step_audit(
            self.mock_step,
            self.mock_flow,
            self.target_hosts,
            self.svc_maps,
            self.placeholder_pattern,
            None,
            self.host_cli_map,
            self.test_results,
            self.audit_engine,
            False,
            self.mock_dashboard,
            self.mock_args,
            1,
        )

        # Verify core process_single_step was called with correct parameters
        mock_core_process.assert_called_once_with(
            step=self.mock_step,
            flow=self.mock_flow,
            target_hosts=self.target_hosts,
            svc_maps=self.svc_maps,
            placeholder_pattern=self.placeholder_pattern,
            connector=None,
            host_cli_map=self.host_cli_map,
            test_results=self.test_results,
            show_table=False,
            dashboard=self.mock_dashboard,
            args=self.mock_args,
            step_delay=1,
        )

        # Verify audit engine processed the result
        audit_results = self.audit_engine.get_audit_results()
        self.assertEqual(len(audit_results), 1)
        self.assertEqual(audit_results[0]["test_name"], "test_audit_step")
        self.assertEqual(audit_results[0]["overall_result"], "PASS")

    @patch("src.testpilot.audit.audit_processor.process_single_step")
    def test_audit_overrides_otp_pass_when_pattern_mismatch(
        self, mock_core_process
    ):
        """Test that audit can override OTP pass when it detects pattern mismatch"""
        # Create a test result where OTP thinks it passed but pattern doesn't match
        mock_test_result = TestResult(
            sheet="audit_sheet",
            row_idx=1,
            host="test-host",
            command="curl -X GET http://api.test/endpoint",
            output='{"status": "error", "data": {"id": 456}}',  # Different from expected
            error="",
            expected_status=200,
            actual_status=200,
            pattern_match='{"status": "success", "data": {"id": 123}}',
            pattern_found=True,  # OTP might have passed it
            passed=True,  # OTP passed
            fail_reason=None,
            test_name="test_audit_step",
            duration=0.5,
            method="GET",
        )

        def add_result(
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
            args,
            step_delay,
        ):
            test_results.append(mock_test_result)

        mock_core_process.side_effect = add_result

        # Execute audit process
        process_single_step_audit(
            self.mock_step,
            self.mock_flow,
            self.target_hosts,
            self.svc_maps,
            self.placeholder_pattern,
            None,
            self.host_cli_map,
            self.test_results,
            self.audit_engine,
            False,
            self.mock_dashboard,
            self.mock_args,
            1,
        )

        # Verify audit detected the mismatch and failed the test
        audit_results = self.audit_engine.get_audit_results()
        self.assertEqual(len(audit_results), 1)
        self.assertEqual(audit_results[0]["overall_result"], "FAIL")

        # Verify test result was updated to fail
        self.assertFalse(self.test_results[0].passed)
        self.assertFalse(self.test_results[0].pattern_found)
        self.assertIsNotNone(self.test_results[0].fail_reason)
        self.assertIn("Pattern differences", self.test_results[0].fail_reason)

    @patch("src.testpilot.audit.audit_processor.process_single_step")
    def test_audit_validates_http_method_mismatch(self, mock_core_process):
        """Test that audit validates HTTP method mismatches"""
        # Mock step expects GET but command uses POST
        self.mock_step.method = "GET"

        mock_test_result = TestResult(
            sheet="audit_sheet",
            row_idx=1,
            host="test-host",
            command="curl -X POST http://api.test/endpoint",
            output='{"status": "success", "data": {"id": 123}}',
            error="",
            expected_status=200,
            actual_status=200,
            pattern_match='{"status": "success", "data": {"id": 123}}',
            pattern_found=True,
            passed=True,
            fail_reason=None,
            test_name="test_audit_step",
            duration=0.5,
            method="POST",  # Actual method is POST
        )

        def add_result(
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
            args,
            step_delay,
        ):
            test_results.append(mock_test_result)

        mock_core_process.side_effect = add_result

        # Execute audit process
        process_single_step_audit(
            self.mock_step,
            self.mock_flow,
            self.target_hosts,
            self.svc_maps,
            self.placeholder_pattern,
            None,
            self.host_cli_map,
            self.test_results,
            self.audit_engine,
            False,
            self.mock_dashboard,
            self.mock_args,
            1,
        )

        # Verify audit detected HTTP method mismatch
        audit_results = self.audit_engine.get_audit_results()
        self.assertEqual(len(audit_results), 1)
        self.assertEqual(audit_results[0]["overall_result"], "FAIL")
        self.assertIn(
            "HTTP method mismatch",
            str(audit_results[0]["http_validation_errors"]),
        )

    @patch("src.testpilot.audit.audit_processor.process_single_step")
    def test_audit_validates_status_code_mismatch(self, mock_core_process):
        """Test that audit validates status code mismatches"""
        mock_test_result = TestResult(
            sheet="audit_sheet",
            row_idx=1,
            host="test-host",
            command="curl -X GET http://api.test/endpoint",
            output='{"status": "success", "data": {"id": 123}}',
            error="",
            expected_status=200,
            actual_status=404,  # Different from expected
            pattern_match='{"status": "success", "data": {"id": 123}}',
            pattern_found=True,
            passed=False,  # OTP already caught this
            fail_reason="Status code mismatch",
            test_name="test_audit_step",
            duration=0.5,
            method="GET",
        )

        def add_result(
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
            args,
            step_delay,
        ):
            test_results.append(mock_test_result)

        mock_core_process.side_effect = add_result

        # Execute audit process
        process_single_step_audit(
            self.mock_step,
            self.mock_flow,
            self.target_hosts,
            self.svc_maps,
            self.placeholder_pattern,
            None,
            self.host_cli_map,
            self.test_results,
            self.audit_engine,
            False,
            self.mock_dashboard,
            self.mock_args,
            1,
        )

        # Verify audit also detected the status code mismatch
        audit_results = self.audit_engine.get_audit_results()
        self.assertEqual(len(audit_results), 1)
        self.assertEqual(audit_results[0]["overall_result"], "FAIL")
        self.assertIn(
            "Status code mismatch",
            str(audit_results[0]["http_validation_errors"]),
        )

    @patch("src.testpilot.audit.audit_processor.process_single_step")
    def test_no_test_result_added_by_core(self, mock_core_process):
        """Test handling when core doesn't add a test result (e.g., empty command)"""
        # Core doesn't add any result
        mock_core_process.return_value = None

        # Execute audit process
        process_single_step_audit(
            self.mock_step,
            self.mock_flow,
            self.target_hosts,
            self.svc_maps,
            self.placeholder_pattern,
            None,
            self.host_cli_map,
            self.test_results,
            self.audit_engine,
            False,
            self.mock_dashboard,
            self.mock_args,
            1,
        )

        # Verify no audit was performed
        audit_results = self.audit_engine.get_audit_results()
        self.assertEqual(len(audit_results), 0)
        self.assertEqual(len(self.test_results), 0)

    @patch("src.testpilot.audit.audit_processor.process_single_step")
    def test_audit_handles_invalid_json_response(self, mock_core_process):
        """Test audit handling of invalid JSON in response"""
        mock_test_result = TestResult(
            sheet="audit_sheet",
            row_idx=1,
            host="test-host",
            command="curl -X GET http://api.test/endpoint",
            output="Invalid JSON response {not valid}",
            error="",
            expected_status=200,
            actual_status=200,
            pattern_match='{"status": "success"}',
            pattern_found=False,
            passed=False,
            fail_reason="Invalid JSON",
            test_name="test_audit_step",
            duration=0.5,
            method="GET",
        )

        def add_result(
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
            args,
            step_delay,
        ):
            test_results.append(mock_test_result)

        mock_core_process.side_effect = add_result

        # Execute audit process
        process_single_step_audit(
            self.mock_step,
            self.mock_flow,
            self.target_hosts,
            self.svc_maps,
            self.placeholder_pattern,
            None,
            self.host_cli_map,
            self.test_results,
            self.audit_engine,
            False,
            self.mock_dashboard,
            self.mock_args,
            1,
        )

        # Verify audit detected JSON validation error
        audit_results = self.audit_engine.get_audit_results()
        self.assertEqual(len(audit_results), 1)
        self.assertEqual(audit_results[0]["overall_result"], "ERROR")
        self.assertTrue(len(audit_results[0]["json_validation_errors"]) > 0)

    @patch("src.testpilot.audit.audit_processor.process_single_step")
    def test_audit_with_empty_pattern_match(self, mock_core_process):
        """Test audit behavior when no pattern match is specified"""
        # Clear pattern match
        self.mock_step.pattern_match = ""
        self.mock_step.other_fields["Pattern_Match"] = ""

        mock_test_result = TestResult(
            sheet="audit_sheet",
            row_idx=1,
            host="test-host",
            command="curl -X GET http://api.test/endpoint",
            output='{"any": "response"}',
            error="",
            expected_status=200,
            actual_status=200,
            pattern_match="",
            pattern_found=True,
            passed=True,
            fail_reason=None,
            test_name="test_audit_step",
            duration=0.5,
            method="GET",
        )

        def add_result(
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
            args,
            step_delay,
        ):
            test_results.append(mock_test_result)

        mock_core_process.side_effect = add_result

        # Execute audit process
        process_single_step_audit(
            self.mock_step,
            self.mock_flow,
            self.target_hosts,
            self.svc_maps,
            self.placeholder_pattern,
            None,
            self.host_cli_map,
            self.test_results,
            self.audit_engine,
            False,
            self.mock_dashboard,
            self.mock_args,
            1,
        )

        # Verify audit passes when no pattern to match
        audit_results = self.audit_engine.get_audit_results()
        self.assertEqual(len(audit_results), 1)
        self.assertEqual(audit_results[0]["overall_result"], "PASS")

    @patch("src.testpilot.audit.audit_processor.process_single_step")
    def test_audit_preserves_test_result_metadata(self, mock_core_process):
        """Test that audit preserves all test result metadata"""
        mock_test_result = TestResult(
            sheet="audit_sheet",
            row_idx=5,
            host="prod-host",
            command="curl -X PUT http://api.test/endpoint",
            output='{"status": "success", "data": {"id": 123}}',
            error="",
            expected_status=200,
            actual_status=200,
            pattern_match='{"status": "success", "data": {"id": 123}}',
            pattern_found=True,
            passed=True,
            fail_reason=None,
            test_name="complex_test",
            duration=1.23,
            method="PUT",
        )

        def add_result(
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
            args,
            step_delay,
        ):
            test_results.append(mock_test_result)

        mock_core_process.side_effect = add_result

        # Execute audit process
        process_single_step_audit(
            self.mock_step,
            self.mock_flow,
            self.target_hosts,
            self.svc_maps,
            self.placeholder_pattern,
            None,
            self.host_cli_map,
            self.test_results,
            self.audit_engine,
            False,
            self.mock_dashboard,
            self.mock_args,
            1,
        )

        # Verify audit preserved all metadata in its validation
        audit_results = self.audit_engine.get_audit_results()
        self.assertEqual(len(audit_results), 1)
        audit_result = audit_results[0]

        # Check request details were preserved
        self.assertEqual(
            audit_result["request_details"]["command"],
            "curl -X PUT http://api.test/endpoint",
        )
        self.assertEqual(audit_result["request_details"]["host"], "prod-host")
        self.assertEqual(
            audit_result["request_details"]["execution_time"], 1.23
        )
        self.assertEqual(audit_result["request_details"]["row_idx"], 5)
        self.assertEqual(
            audit_result["request_details"]["sheet"], "audit_sheet"
        )

    @patch("src.testpilot.audit.audit_processor.process_single_step")
    def test_audit_logs_appropriate_messages(self, mock_core_process):
        """Test that audit logs appropriate messages for pass/fail/error"""
        mock_test_result = TestResult(
            sheet="audit_sheet",
            row_idx=1,
            host="test-host",
            command="curl -X GET http://api.test/endpoint",
            output='{"status": "success", "data": {"id": 123}}',
            error="",
            expected_status=200,
            actual_status=200,
            pattern_match='{"status": "success", "data": {"id": 123}}',
            pattern_found=True,
            passed=True,
            fail_reason=None,
            test_name="test_audit_step",
            duration=0.5,
            method="GET",
        )

        def add_result(
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
            args,
            step_delay,
        ):
            test_results.append(mock_test_result)

        mock_core_process.side_effect = add_result

        with patch(
            "src.testpilot.audit.audit_processor.logger"
        ) as mock_logger:
            # Execute audit process
            process_single_step_audit(
                self.mock_step,
                self.mock_flow,
                self.target_hosts,
                self.svc_maps,
                self.placeholder_pattern,
                None,
                self.host_cli_map,
                self.test_results,
                self.audit_engine,
                False,
                self.mock_dashboard,
                self.mock_args,
                1,
            )

            # Verify appropriate log messages
            mock_logger.info.assert_called_with(
                "✅ [AUDIT PASS] test_audit_step: 100% validation successful"
            )

    @patch("src.testpilot.audit.audit_processor.process_single_step")
    def test_audit_error_handling(self, mock_core_process):
        """Test audit handles errors in response data"""
        mock_test_result = TestResult(
            sheet="audit_sheet",
            row_idx=1,
            host="test-host",
            command="curl -X GET http://api.test/endpoint",
            output="",  # Empty response
            error="Connection timeout",
            expected_status=200,
            actual_status=None,
            pattern_match='{"status": "success"}',
            pattern_found=False,
            passed=False,
            fail_reason="Connection timeout",
            test_name="test_audit_step",
            duration=30.0,
            method="GET",
        )

        def add_result(
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
            args,
            step_delay,
        ):
            test_results.append(mock_test_result)

        mock_core_process.side_effect = add_result

        with patch(
            "src.testpilot.audit.audit_processor.logger"
        ) as mock_logger:
            # Execute audit process
            process_single_step_audit(
                self.mock_step,
                self.mock_flow,
                self.target_hosts,
                self.svc_maps,
                self.placeholder_pattern,
                None,
                self.host_cli_map,
                self.test_results,
                self.audit_engine,
                False,
                self.mock_dashboard,
                self.mock_args,
                1,
            )

            # Verify audit detected error condition
            audit_results = self.audit_engine.get_audit_results()
            self.assertEqual(len(audit_results), 1)
            self.assertEqual(audit_results[0]["overall_result"], "ERROR")

            # Verify error was logged
            mock_logger.error.assert_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
