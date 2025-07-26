#!/usr/bin/env python3
"""
Integration Tests for Refactored Audit Functionality

Tests the audit module's integration with the core OTP workflow:
- Full audit flow with core process_single_step
- Report generation with AuditExporter
- End-to-end workflow validation
"""

import json
import os
import sys
import tempfile
import unittest
from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.testpilot.audit import AuditEngine, AuditExporter
from src.testpilot.audit.audit_processor import process_single_step_audit
from src.testpilot.core.test_result import TestFlow, TestResult, TestStep


class TestAuditIntegration(unittest.TestCase):
    """Integration tests for refactored audit functionality"""

    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.audit_engine = AuditEngine()
        self.audit_exporter = AuditExporter()

        # Mock components
        self.mock_connector = Mock()
        self.mock_dashboard = Mock()
        self.target_hosts = ["test-host"]
        self.svc_maps = {"test-host": {"api-service": "http://api.test"}}
        self.placeholder_pattern = Mock()
        self.host_cli_map = {"test-host": "kubectl"}
        self.mock_args = Mock(execution_mode="production")

        # Test flows
        self.test_flows = self.create_test_flows()

    def tearDown(self):
        """Clean up temporary files"""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)
        self.audit_engine.clear_results()

    def create_test_flows(self):
        """Create test flows for integration testing"""
        flows = []

        # Flow 1: Successful test
        flow1 = TestFlow(
            test_name="test_user_registration", sheet="AuditSheet", steps=[]
        )

        step1 = TestStep(
            row_idx=1,
            method="POST",
            url="http://api.test/users",
            payload='{"name": "test"}',
            headers={"Content-Type": "application/json"},
            expected_status=201,
            pattern_match='{"status": "created", "user": {"name": "test", "id": 123}}',
            other_fields={
                "Command": 'curl -X POST http://api.test/users -d \'{"name": "test"}\'',
                "podExec": "api-pod",
                "Pattern_Match": '{"status": "created", "user": {"name": "test", "id": 123}}',
            },
        )
        step1.test_name = "test_user_registration"
        flow1.steps.append(step1)
        flows.append(flow1)

        # Flow 2: Test with pattern mismatch
        flow2 = TestFlow(
            test_name="test_user_login", sheet="AuditSheet", steps=[]
        )

        step2 = TestStep(
            row_idx=2,
            method="POST",
            url="http://api.test/login",
            payload='{"user": "test", "pass": "123"}',
            headers={"Content-Type": "application/json"},
            expected_status=200,
            pattern_match='{"status": "success", "token": "abc123", "expires": 3600}',
            other_fields={
                "Command": 'curl -X POST http://api.test/login -d \'{"user": "test", "pass": "123"}\'',
                "podExec": "auth-pod",
                "Pattern_Match": '{"status": "success", "token": "abc123", "expires": 3600}',
            },
        )
        step2.test_name = "test_user_login"
        flow2.steps.append(step2)
        flows.append(flow2)

        return flows

    # =================================================================
    # INTEGRATION WITH CORE WORKFLOW
    # =================================================================

    @patch("src.testpilot.audit.audit_processor.process_single_step")
    def test_audit_workflow_with_core_integration(self, mock_core_process):
        """Test complete audit workflow using core process_single_step"""
        # Create mock test results that core would produce
        test_results = []

        def add_success_result(
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
            if flow.test_name == "test_user_registration":
                result = TestResult(
                    sheet="AuditSheet",
                    row_idx=1,
                    host="test-host",
                    command='curl -X POST http://api.test/users -d \'{"name": "test"}\'',
                    output='{"status": "created", "user": {"name": "test", "id": 123}}',
                    error="",
                    expected_status=201,
                    actual_status=201,
                    pattern_match='{"status": "created", "user": {"name": "test", "id": 123}}',
                    pattern_found=True,
                    passed=True,
                    fail_reason=None,
                    test_name="test_user_registration",
                    duration=0.2,
                    method="POST",
                )
            else:  # test_user_login with wrong response
                result = TestResult(
                    sheet="AuditSheet",
                    row_idx=2,
                    host="test-host",
                    command='curl -X POST http://api.test/login -d \'{"user": "test", "pass": "123"}\'',
                    output='{"status": "error", "message": "Invalid credentials"}',
                    error="",
                    expected_status=200,
                    actual_status=401,
                    pattern_match='{"status": "success", "token": "abc123", "expires": 3600}',
                    pattern_found=False,
                    passed=False,
                    fail_reason="Status code mismatch",
                    test_name="test_user_login",
                    duration=0.15,
                    method="POST",
                )
            test_results.append(result)

        mock_core_process.side_effect = add_success_result

        # Execute audit workflow
        for flow in self.test_flows:
            for step in flow.steps:
                process_single_step_audit(
                    step,
                    flow,
                    self.target_hosts,
                    self.svc_maps,
                    self.placeholder_pattern,
                    self.mock_connector,
                    self.host_cli_map,
                    test_results,
                    self.audit_engine,
                    False,
                    self.mock_dashboard,
                    self.mock_args,
                    1,
                )

        # Verify core was called for each step
        self.assertEqual(mock_core_process.call_count, 2)

        # Verify audit results
        audit_results = self.audit_engine.get_audit_results()
        self.assertEqual(len(audit_results), 2)

        # First test should pass audit
        self.assertEqual(
            audit_results[0]["test_name"], "test_user_registration"
        )
        self.assertEqual(audit_results[0]["overall_result"], "PASS")
        self.assertEqual(len(audit_results[0]["differences"]), 0)

        # Second test should fail audit
        self.assertEqual(audit_results[1]["test_name"], "test_user_login")
        self.assertEqual(audit_results[1]["overall_result"], "FAIL")
        self.assertGreater(len(audit_results[1]["differences"]), 0)
        self.assertGreater(len(audit_results[1]["http_validation_errors"]), 0)

        # Verify audit summary
        summary = self.audit_engine.generate_audit_summary()
        self.assertEqual(summary["total_tests"], 2)
        self.assertEqual(summary["passed_tests"], 1)
        self.assertEqual(summary["failed_tests"], 1)
        self.assertEqual(summary["compliance_status"], "NON_COMPLIANT")

    @patch("src.testpilot.audit.audit_processor.process_single_step")
    def test_audit_enhances_otp_validation(self, mock_core_process):
        """Test that audit enhances OTP validation with stricter checks"""

        # Mock OTP passing but audit should catch the difference
        def add_lenient_result(
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
            result = TestResult(
                sheet="AuditSheet",
                row_idx=1,
                host="test-host",
                command='curl -X POST http://api.test/users -d \'{"name": "test"}\'',
                output='{"status": "created", "user": {"name": "test", "id": 456}}',  # Wrong ID
                error="",
                expected_status=201,
                actual_status=201,
                pattern_match='{"status": "created", "user": {"name": "test", "id": 123}}',
                pattern_found=True,  # OTP might pass with partial match
                passed=True,
                fail_reason=None,
                test_name="test_user_registration",
                duration=0.2,
                method="POST",
            )
            test_results.append(result)

        mock_core_process.side_effect = add_lenient_result

        test_results = []
        process_single_step_audit(
            self.test_flows[0].steps[0],
            self.test_flows[0],
            self.target_hosts,
            self.svc_maps,
            self.placeholder_pattern,
            self.mock_connector,
            self.host_cli_map,
            test_results,
            self.audit_engine,
            False,
            self.mock_dashboard,
            self.mock_args,
            1,
        )

        # Verify audit caught the difference
        audit_results = self.audit_engine.get_audit_results()
        self.assertEqual(audit_results[0]["overall_result"], "FAIL")

        # Verify test result was updated
        self.assertFalse(test_results[0].passed)
        self.assertIn("Pattern differences", test_results[0].fail_reason)

    def test_audit_report_generation(self):
        """Test audit report generation with AuditExporter"""
        # Add some audit results
        self.audit_engine.validate_response(
            test_name="test1",
            expected_pattern='{"status": "ok"}',
            actual_response='{"status": "ok"}',
            http_method_expected="GET",
            http_method_actual="GET",
            status_code_expected=200,
            status_code_actual=200,
            request_details={
                "command": "curl http://test.com",
                "host": "test-host",
            },
        )

        self.audit_engine.validate_response(
            test_name="test2",
            expected_pattern='{"data": [1, 2, 3]}',
            actual_response='{"data": [3, 2, 1]}',  # Different order
            http_method_expected="GET",
            http_method_actual="GET",
            status_code_expected=200,
            status_code_actual=200,
        )

        # Generate audit summary
        summary = self.audit_engine.generate_audit_summary()

        # Export report (JSON fallback since we might not have pandas)
        report_path = self.audit_exporter.export_audit_results(
            self.audit_engine.get_audit_results(),
            summary,
            output_dir=self.temp_dir,
            force_json=True,  # Force JSON for testing
        )

        # Verify report was created
        self.assertTrue(os.path.exists(report_path))
        self.assertTrue(report_path.endswith(".json"))

        # Verify report content
        with open(report_path, "r") as f:
            report_data = json.load(f)

        self.assertEqual(len(report_data["audit_results"]), 2)
        self.assertEqual(report_data["audit_summary"]["total_tests"], 2)
        self.assertEqual(report_data["audit_summary"]["passed_tests"], 1)
        self.assertEqual(report_data["audit_summary"]["failed_tests"], 1)

    @patch("src.testpilot.audit.audit_processor.process_single_step")
    def test_audit_error_handling(self, mock_core_process):
        """Test audit handles errors gracefully"""
        # Mock core throwing an exception
        mock_core_process.side_effect = Exception("Command execution failed")

        test_results = []

        # Should not raise exception
        process_single_step_audit(
            self.test_flows[0].steps[0],
            self.test_flows[0],
            self.target_hosts,
            self.svc_maps,
            self.placeholder_pattern,
            self.mock_connector,
            self.host_cli_map,
            test_results,
            self.audit_engine,
            False,
            self.mock_dashboard,
            self.mock_args,
            1,
        )

        # Core was called and raised exception
        mock_core_process.assert_called_once()

        # No audit results since core failed
        self.assertEqual(len(self.audit_engine.get_audit_results()), 0)

    @patch("src.testpilot.audit.audit_processor.process_single_step")
    def test_audit_with_array_ordering(self, mock_core_process):
        """Test audit enforces strict array ordering"""
        # Create step with array pattern
        step = TestStep(
            row_idx=1,
            method="GET",
            url="http://test.com",
            payload="",
            headers={},
            expected_status=200,
            pattern_match='{"items": ["a", "b", "c"]}',
            other_fields={
                "Pattern_Match": '{"items": ["a", "b", "c"]}',
            },
        )
        step.test_name = "array_test"

        flow = TestFlow(
            test_name="array_test", sheet="AuditSheet", steps=[step]
        )

        def add_unordered_result(
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
            result = TestResult(
                sheet="AuditSheet",
                row_idx=1,
                host="test-host",
                command="curl http://test.com",
                output='{"items": ["c", "a", "b"]}',  # Different order
                error="",
                expected_status=200,
                actual_status=200,
                pattern_match='{"items": ["a", "b", "c"]}',
                pattern_found=True,  # OTP might not care about order
                passed=True,
                fail_reason=None,
                test_name="array_test",
                duration=0.1,
                method="GET",
            )
            test_results.append(result)

        mock_core_process.side_effect = add_unordered_result

        test_results = []
        process_single_step_audit(
            step,
            flow,
            self.target_hosts,
            self.svc_maps,
            self.placeholder_pattern,
            self.mock_connector,
            self.host_cli_map,
            test_results,
            self.audit_engine,
            False,
            self.mock_dashboard,
            self.mock_args,
            1,
        )

        # Verify audit caught array order difference
        audit_results = self.audit_engine.get_audit_results()
        self.assertEqual(audit_results[0]["overall_result"], "FAIL")

        # Check for array differences
        differences = audit_results[0]["differences"]
        array_diffs = [d for d in differences if "items[" in d["field_path"]]
        self.assertGreater(len(array_diffs), 0)

    def test_audit_dashboard_integration(self):
        """Test audit updates dashboard correctly"""
        mock_dashboard = Mock()

        with patch(
            "src.testpilot.audit.audit_processor.process_single_step"
        ) as mock_core:

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
                result = TestResult(
                    sheet="AuditSheet",
                    row_idx=1,
                    host="test-host",
                    command="curl http://test.com",
                    output='{"status": "ok"}',
                    error="",
                    expected_status=200,
                    actual_status=200,
                    pattern_match='{"status": "ok"}',
                    pattern_found=True,
                    passed=True,
                    fail_reason=None,
                    test_name="dashboard_test",
                    duration=0.1,
                    method="GET",
                )
                test_results.append(result)
                # Core would update dashboard
                if dashboard:
                    dashboard.add_test_result(result)

            mock_core.side_effect = add_result

            test_results = []
            step = self.test_flows[0].steps[0]
            step.pattern_match = '{"status": "ok"}'

            process_single_step_audit(
                step,
                self.test_flows[0],
                self.target_hosts,
                self.svc_maps,
                self.placeholder_pattern,
                self.mock_connector,
                self.host_cli_map,
                test_results,
                self.audit_engine,
                False,
                mock_dashboard,
                self.mock_args,
                1,
            )

            # Verify dashboard was called by core
            mock_dashboard.add_test_result.assert_called_once()


if __name__ == "__main__":
    unittest.main(verbosity=2)
