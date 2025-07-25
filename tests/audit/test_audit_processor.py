#!/usr/bin/env python3
"""
Comprehensive Unit Tests for AuditProcessor

Tests step execution and response parsing including:
- Command execution with SSH and local modes
- HTTP method extraction from curl commands
- Status code parsing from responses
- Response data handling and parsing
- Integration with AuditEngine
- Error handling and edge cases
"""

import json
import os
import subprocess
import sys
import unittest
from unittest.mock import MagicMock, Mock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.testpilot.audit.audit_engine import AuditEngine
from src.testpilot.audit.audit_processor import (
    _execute_step_command,
    _extract_http_method_from_command,
    _extract_status_code,
    process_single_step_audit,
)
from src.testpilot.core.test_result import TestResult


class TestAuditProcessor(unittest.TestCase):
    """Comprehensive test suite for AuditProcessor"""

    def setUp(self):
        """Set up test fixtures"""
        self.audit_engine = AuditEngine()

        # Mock step data
        self.mock_step = Mock()
        self.mock_step.other_fields = {
            "Pattern_Match": '{"status": "success", "data": {"id": 123}}',
            "Save_As": None,
            "Command": "curl -X GET http://test.com/api",
        }
        self.mock_step.method = "GET"
        self.mock_step.test_name = "test_audit_step"
        self.mock_step.expected_status = 200
        self.mock_step.url = "http://test.com/api"
        self.mock_step.headers = {}
        self.mock_step.payload = None
        self.mock_step.pattern_match = '{"status": "success"}'

        # Mock flow data
        self.mock_flow = Mock()
        self.mock_flow.context = {}

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
    # HTTP METHOD EXTRACTION TESTS
    # =================================================================

    def test_extract_http_method_get_explicit(self):
        """Test extracting GET method with -X flag"""
        command = "curl -X GET http://api.test/endpoint"
        method = _extract_http_method_from_command(command)
        self.assertEqual(method, "GET")

    def test_extract_http_method_post_explicit(self):
        """Test extracting POST method with -X flag"""
        command = "curl -X POST http://api.test/endpoint"
        method = _extract_http_method_from_command(command)
        self.assertEqual(method, "POST")

    def test_extract_http_method_request_flag(self):
        """Test extracting method with --request flag"""
        command = "curl --request PUT http://api.test/endpoint"
        method = _extract_http_method_from_command(command)
        self.assertEqual(method, "PUT")

    def test_extract_http_method_default_get(self):
        """Test default GET method when no method specified"""
        command = "curl http://api.test/endpoint"
        method = _extract_http_method_from_command(command)
        self.assertEqual(method, "GET")

    def test_extract_http_method_case_insensitive(self):
        """Test case insensitive method extraction"""
        command = "curl -x delete http://api.test/endpoint"
        method = _extract_http_method_from_command(command)
        self.assertEqual(method, "DELETE")

    def test_extract_http_method_empty_command(self):
        """Test empty command handling"""
        method = _extract_http_method_from_command("")
        self.assertEqual(method, "")

    def test_extract_http_method_non_curl_command(self):
        """Test non-curl command handling"""
        command = "wget http://api.test/endpoint"
        method = _extract_http_method_from_command(command)
        self.assertEqual(method, "")

    def test_extract_http_method_complex_curl(self):
        """Test complex curl command with multiple flags"""
        command = 'curl -H "Content-Type: application/json" -X PATCH -d \'{"data": "test"}\' http://api.test/endpoint'
        method = _extract_http_method_from_command(command)
        self.assertEqual(method, "PATCH")

    # =================================================================
    # STATUS CODE EXTRACTION TESTS
    # =================================================================

    def test_extract_status_code_http_header(self):
        """Test extracting status code from HTTP header"""
        output = 'HTTP/1.1 200 OK\nContent-Type: application/json\n\n{"result": "success"}'
        status = _extract_status_code(output)
        self.assertEqual(status, 200)

    def test_extract_status_code_json_response(self):
        """Test extracting status code from JSON response"""
        output = '{"status": 201, "message": "Created"}'
        status = _extract_status_code(output)
        self.assertEqual(status, 201)

    def test_extract_status_code_multiple_formats(self):
        """Test extracting status code with multiple format matches"""
        output = (
            'HTTP/1.1 404 Not Found\n{"status": 404, "error": "Not found"}'
        )
        status = _extract_status_code(output)
        self.assertEqual(status, 404)  # Should return first match

    def test_extract_status_code_no_match(self):
        """Test when no status code found"""
        output = "Some random output without status"
        status = _extract_status_code(output)
        self.assertIsNone(status)

    def test_extract_status_code_empty_output(self):
        """Test empty output handling"""
        status = _extract_status_code("")
        self.assertIsNone(status)

    def test_extract_status_code_malformed_http(self):
        """Test malformed HTTP response"""
        output = "HTTP/1.1 abc Not Valid"
        status = _extract_status_code(output)
        self.assertIsNone(status)

    def test_extract_status_code_various_formats(self):
        """Test various status code formats"""
        test_cases = [
            ("HTTP/2 500 Internal Server Error", 500),
            ('"status": 202', 202),
            ("status: 301", 301),
            ("HTTP 401", 401),
            ("Status Code: 204", None),  # Not in our patterns
        ]

        for output, expected in test_cases:
            with self.subTest(output=output):
                status = _extract_status_code(output)
                self.assertEqual(status, expected)

    # =================================================================
    # COMMAND EXECUTION TESTS
    # =================================================================

    @patch(
        "src.testpilot.audit.audit_processor.replace_placeholder_in_command"
    )
    @patch("src.testpilot.audit.audit_processor.map_localhost_url")
    @patch("src.testpilot.audit.audit_processor.parse_curl_output")
    @patch("subprocess.run")
    def test_execute_step_command_local_success(
        self, mock_subprocess, mock_parse, mock_map_url, mock_replace
    ):
        """Test successful local command execution"""
        # Setup mocks
        mock_replace.return_value = "curl -X GET http://api.test/endpoint"
        mock_map_url.return_value = "curl -X GET http://api.test/endpoint"
        mock_parse.return_value = {"parsed": "data"}

        mock_result = Mock()
        mock_result.stdout = '{"status": "success"}'
        mock_result.stderr = ""
        mock_subprocess.return_value = mock_result

        step_data = {
            "command": "curl -X GET http://api.test/endpoint",
            "test_name": "test_local_execution",
        }

        # Execute
        response_data = _execute_step_command(
            step_data,
            self.target_hosts,
            self.svc_maps,
            self.placeholder_pattern,
            None,
            self.host_cli_map,
            self.mock_args,
        )

        # Verify
        self.assertEqual(response_data["raw_output"], '{"status": "success"}')
        self.assertEqual(response_data["parsed_output"], {"parsed": "data"})
        self.assertEqual(response_data["http_method"], "GET")
        self.assertEqual(response_data["host"], "localhost")
        self.assertGreater(response_data["execution_time"], 0)

    @patch("src.testpilot.audit.audit_processor.build_ssh_k8s_curl_command")
    def test_execute_step_command_ssh_success(self, mock_build_ssh):
        """Test successful SSH command execution"""
        # Setup mocks
        mock_connector = Mock()
        mock_connector.run_command.return_value = {
            self.target_hosts[0]: {"output": '{"status": "success"}'}
        }
        mock_build_ssh.return_value = (
            "kubectl exec -it pod -- curl -X GET http://api.test/endpoint"
        )

        step_data = {
            "command": "curl -X GET http://api.test/endpoint",
            "test_name": "test_ssh_execution",
            "pod_exec": "test-pod",
        }

        # Execute
        response_data = _execute_step_command(
            step_data,
            self.target_hosts,
            self.svc_maps,
            self.placeholder_pattern,
            mock_connector,
            self.host_cli_map,
            self.mock_args,
        )

        # Verify
        self.assertEqual(response_data["raw_output"], '{"status": "success"}')
        self.assertEqual(response_data["host"], self.target_hosts[0])
        mock_connector.run_command.assert_called_once()

    @patch("subprocess.run")
    def test_execute_step_command_timeout_error(self, mock_subprocess):
        """Test command execution timeout handling"""
        mock_subprocess.side_effect = subprocess.TimeoutExpired("curl", 30)

        step_data = {
            "command": "curl -X GET http://slow-api.test/endpoint",
            "test_name": "test_timeout",
        }

        response_data = _execute_step_command(
            step_data,
            self.target_hosts,
            self.svc_maps,
            self.placeholder_pattern,
            None,
            self.host_cli_map,
            self.mock_args,
        )

        self.assertIn("Error:", response_data["raw_output"])
        self.assertGreater(response_data["execution_time"], 0)

    @patch("subprocess.run")
    def test_execute_step_command_generic_error(self, mock_subprocess):
        """Test generic command execution error handling"""
        mock_subprocess.side_effect = Exception("Command execution failed")

        step_data = {
            "command": "curl -X GET http://api.test/endpoint",
            "test_name": "test_error",
        }

        response_data = _execute_step_command(
            step_data,
            self.target_hosts,
            self.svc_maps,
            self.placeholder_pattern,
            None,
            self.host_cli_map,
            self.mock_args,
        )

        self.assertIn(
            "Error: Command execution failed", response_data["raw_output"]
        )

    # =================================================================
    # INTEGRATION TESTS WITH AUDIT ENGINE
    # =================================================================

    @patch("src.testpilot.audit.audit_processor.extract_step_data")
    @patch("src.testpilot.audit.audit_processor.manage_workflow_context")
    @patch("src.testpilot.audit.audit_processor._execute_step_command")
    def test_process_single_step_audit_success(
        self, mock_execute, mock_manage, mock_extract
    ):
        """Test successful single step audit processing"""
        # Setup mocks
        mock_extract.return_value = {
            "command": "curl -X GET http://api.test/endpoint",
            "test_name": "test_audit_step",
            "expected_status": 200,
        }

        mock_execute.return_value = {
            "raw_output": '{"status": "success", "data": {"id": 123}}',
            "parsed_output": {"status": "success", "data": {"id": 123}},
            "status_code": 200,
            "http_method": "GET",
            "host": "test-host",
            "execution_time": 0.5,
        }

        # Execute
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
            True,
            self.mock_dashboard,
            self.mock_args,
            1,
        )

        # Verify audit engine was called
        audit_results = self.audit_engine.get_audit_results()
        self.assertEqual(len(audit_results), 1)
        self.assertEqual(audit_results[0]["test_name"], "test_audit_step")
        self.assertEqual(audit_results[0]["overall_result"], "PASS")

        # Verify test result was created
        self.assertEqual(len(self.test_results), 1)
        self.assertTrue(self.test_results[0].passed)

    @patch("src.testpilot.audit.audit_processor.extract_step_data")
    @patch("src.testpilot.audit.audit_processor.manage_workflow_context")
    @patch("src.testpilot.audit.audit_processor._execute_step_command")
    def test_process_single_step_audit_failure(
        self, mock_execute, mock_manage, mock_extract
    ):
        """Test failed single step audit processing"""
        # Setup mocks for failure scenario
        mock_extract.return_value = {
            "command": "curl -X GET http://api.test/endpoint",
            "test_name": "test_audit_failure",
            "expected_status": 200,
        }

        mock_execute.return_value = {
            "raw_output": '{"status": "error", "data": {"id": 456}}',
            "parsed_output": {"status": "error", "data": {"id": 456}},
            "status_code": 400,
            "http_method": "POST",  # Different from expected
            "host": "test-host",
            "execution_time": 0.3,
        }

        # Execute
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
            True,
            self.mock_dashboard,
            self.mock_args,
            1,
        )

        # Verify audit engine recorded failure
        audit_results = self.audit_engine.get_audit_results()
        self.assertEqual(len(audit_results), 1)
        self.assertEqual(audit_results[0]["overall_result"], "FAIL")
        self.assertGreater(len(audit_results[0]["differences"]), 0)
        self.assertGreater(len(audit_results[0]["http_validation_errors"]), 0)

        # Verify test result shows failure
        self.assertEqual(len(self.test_results), 1)
        self.assertFalse(self.test_results[0].passed)

    @patch("src.testpilot.audit.audit_processor.extract_step_data")
    def test_process_single_step_audit_empty_command(self, mock_extract):
        """Test handling of empty command"""
        mock_extract.return_value = {
            "command": None,
            "test_name": "test_empty_command",
        }

        # Execute
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
            True,
            self.mock_dashboard,
            self.mock_args,
            1,
        )

        # Should return early without processing
        audit_results = self.audit_engine.get_audit_results()
        self.assertEqual(len(audit_results), 0)
        self.assertEqual(len(self.test_results), 0)

    @patch("src.testpilot.audit.audit_processor.extract_step_data")
    @patch("src.testpilot.audit.audit_processor.manage_workflow_context")
    @patch("src.testpilot.audit.audit_processor._execute_step_command")
    def test_process_single_step_audit_exception_handling(
        self, mock_execute, mock_manage, mock_extract
    ):
        """Test exception handling in step processing"""
        # Setup mocks
        mock_extract.return_value = {
            "command": "curl -X GET http://api.test/endpoint",
            "test_name": "test_exception_handling",
            "expected_status": 200,
        }

        mock_execute.side_effect = Exception("Simulated execution error")

        # Execute
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
            True,
            self.mock_dashboard,
            self.mock_args,
            1,
        )

        # Verify error was handled
        audit_results = self.audit_engine.get_audit_results()
        self.assertEqual(len(audit_results), 1)

        # Verify test result shows failure
        self.assertEqual(len(self.test_results), 1)
        self.assertFalse(self.test_results[0].passed)
        self.assertIn("Execution error", self.test_results[0].error_message)

    # =================================================================
    # EDGE CASES AND BOUNDARY CONDITIONS
    # =================================================================

    def test_extract_http_method_with_spaces(self):
        """Test HTTP method extraction with extra spaces"""
        command = "curl  -X   GET   http://api.test/endpoint"
        method = _extract_http_method_from_command(command)
        self.assertEqual(method, "GET")

    def test_extract_status_code_with_extra_text(self):
        """Test status code extraction with extra surrounding text"""
        output = "Some prefix text HTTP/1.1 201 Created some suffix text"
        status = _extract_status_code(output)
        self.assertEqual(status, 201)

    def test_extract_status_code_json_nested(self):
        """Test status code extraction from nested JSON"""
        output = '{"response": {"status": 404, "message": "Not found"}, "meta": {"timestamp": "2025-01-01"}}'
        status = _extract_status_code(output)
        self.assertEqual(status, 404)

    @patch("subprocess.run")
    def test_execute_step_command_stderr_handling(self, mock_subprocess):
        """Test handling of stderr output"""
        mock_result = Mock()
        mock_result.stdout = ""
        mock_result.stderr = "Error: Connection refused"
        mock_subprocess.return_value = mock_result

        step_data = {
            "command": "curl -X GET http://unreachable.test/endpoint",
            "test_name": "test_stderr",
        }

        response_data = _execute_step_command(
            step_data,
            self.target_hosts,
            self.svc_maps,
            self.placeholder_pattern,
            None,
            self.host_cli_map,
            self.mock_args,
        )

        self.assertEqual(
            response_data["raw_output"], "Error: Connection refused"
        )

    def test_execute_step_command_no_hosts(self):
        """Test command execution with no target hosts"""
        step_data = {
            "command": "curl -X GET http://api.test/endpoint",
            "test_name": "test_no_hosts",
        }

        response_data = _execute_step_command(
            step_data,
            [],
            self.svc_maps,
            self.placeholder_pattern,
            None,
            self.host_cli_map,
            self.mock_args,
        )

        # Should still execute locally
        self.assertEqual(response_data["host"], "localhost")

    def test_execute_step_command_placeholder_replacement(self):
        """Test placeholder replacement in commands"""
        with patch(
            "src.testpilot.audit.audit_processor.replace_placeholder_in_command"
        ) as mock_replace:
            mock_replace.return_value = (
                "curl -X GET http://actual-service.test/endpoint"
            )

            with patch("subprocess.run") as mock_subprocess:
                mock_result = Mock()
                mock_result.stdout = '{"result": "success"}'
                mock_result.stderr = ""
                mock_subprocess.return_value = mock_result

                step_data = {
                    "command": "curl -X GET http://{service}/endpoint",
                    "test_name": "test_placeholder",
                }

                response_data = _execute_step_command(
                    step_data,
                    self.target_hosts,
                    self.svc_maps,
                    self.placeholder_pattern,
                    None,
                    self.host_cli_map,
                    self.mock_args,
                )

                # Verify placeholder replacement was called
                mock_replace.assert_called_once()
                self.assertEqual(
                    response_data["raw_output"], '{"result": "success"}'
                )

    # =================================================================
    # DASHBOARD INTEGRATION TESTS
    # =================================================================

    @patch("src.testpilot.audit.audit_processor.extract_step_data")
    @patch("src.testpilot.audit.audit_processor.manage_workflow_context")
    @patch("src.testpilot.audit.audit_processor._execute_step_command")
    def test_dashboard_integration_success(
        self, mock_execute, mock_manage, mock_extract
    ):
        """Test dashboard integration for successful tests"""
        mock_extract.return_value = {
            "command": "curl -X GET http://api.test/endpoint",
            "test_name": "test_dashboard_success",
            "expected_status": 200,
        }

        mock_execute.return_value = {
            "raw_output": '{"status": "success", "data": {"id": 123}}',
            "parsed_output": {"status": "success", "data": {"id": 123}},
            "status_code": 200,
            "http_method": "GET",
            "host": "test-host",
            "execution_time": 0.1,
        }

        mock_dashboard = Mock()

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
            True,
            mock_dashboard,
            self.mock_args,
            1,
        )

        # Verify dashboard was updated
        mock_dashboard.add_test_result.assert_called_once()
        call_args = mock_dashboard.add_test_result.call_args
        test_result = call_args[0][0]
        self.assertIsInstance(test_result, TestResult)
        self.assertTrue(test_result.passed)

    @patch("src.testpilot.audit.audit_processor.extract_step_data")
    @patch("src.testpilot.audit.audit_processor.manage_workflow_context")
    @patch("src.testpilot.audit.audit_processor._execute_step_command")
    def test_dashboard_integration_failure(
        self, mock_execute, mock_manage, mock_extract
    ):
        """Test dashboard integration for failed tests"""
        mock_extract.return_value = {
            "command": "curl -X GET http://api.test/endpoint",
            "test_name": "test_dashboard_failure",
            "expected_status": 200,
        }

        mock_execute.return_value = {
            "raw_output": '{"status": "error"}',
            "parsed_output": {"status": "error"},
            "status_code": 500,
            "http_method": "GET",
            "host": "test-host",
            "execution_time": 0.2,
        }

        mock_dashboard = Mock()

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
            True,
            mock_dashboard,
            self.mock_args,
            1,
        )

        # Verify dashboard was updated with failure
        mock_dashboard.add_test_result.assert_called_once()
        call_args = mock_dashboard.add_test_result.call_args
        test_result = call_args[0][0]
        self.assertFalse(test_result.passed)

    def test_no_dashboard_handling(self):
        """Test graceful handling when no dashboard provided"""
        with patch(
            "src.testpilot.audit.audit_processor.extract_step_data"
        ) as mock_extract:
            mock_extract.return_value = {
                "command": "curl -X GET http://api.test/endpoint",
                "test_name": "test_no_dashboard",
                "expected_status": 200,
                "method": "GET",
                "url": "http://api.test/endpoint",
                "headers": {},
                "request_payload": None,
                "pattern_match": "",
                "pod_exec": None,
                "from_excel_response_payload": None,
                "compare_with_key": None,
            }

            with patch(
                "src.testpilot.audit.audit_processor._execute_step_command"
            ) as mock_execute:
                mock_execute.return_value = {
                    "raw_output": '{"status": "success", "data": {"id": 123}}',
                    "parsed_output": {
                        "status": "success",
                        "data": {"id": 123},
                    },
                    "status_code": 200,
                    "http_method": "GET",
                    "host": "test-host",
                    "execution_time": 0.1,
                }

                # Should not raise exception with None dashboard
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
                    True,
                    None,
                    self.mock_args,
                    1,
                )

                # Verify test still processed correctly
                self.assertEqual(len(self.test_results), 1)
                self.assertTrue(self.test_results[0].passed)


'''    @patch('src.testpilot.audit.audit_processor.build_ssh_k8s_curl_command')
    def test_execute_step_command_ssh_with_pod_exec(self, mock_build_ssh):
        """Test successful SSH command execution with pod_exec"""
        # Setup mocks
        mock_connector = Mock()
        mock_connector.run_command.return_value = {
            self.target_hosts[0]: {"output": '{"status": "success"}'}
        }
        mock_build_ssh.return_value = "kubectl exec -it test-pod -- curl -X GET http://api.test/endpoint"

        step_data = {
            "command": "curl -X GET http://api.test/endpoint",
            "test_name": "test_ssh_pod_exec",
            "pod_exec": "test-pod"
        }

        # Execute
        response_data = _execute_step_command(
            step_data, self.target_hosts, self.svc_maps,
            self.placeholder_pattern, mock_connector, self.host_cli_map, self.mock_args
        )

        # Verify
        mock_build_ssh.assert_called_once_with(
            step_data["command"], step_data["pod_exec"], "kubectl"
        )
        mock_connector.run_command.assert_called_once_with(
            "kubectl exec -it test-pod -- curl -X GET http://api.test/endpoint", self.target_hosts
        )
        self.assertEqual(response_data["raw_output"], '{"status": "success"}')


class TestAuditProcessorFallback(unittest.TestCase):
    """Test suite for AuditProcessor fallback implementations"""

    def setUp(self):
        """Set up test fixtures"""
        self.original_sys_modules = sys.modules.copy()
        # Remove modules to trigger fallbacks
        if 'src.testpilot.core.test_pilot_core' in sys.modules:
            del sys.modules['src.testpilot.core.test_pilot_core']
        if 'src.testpilot.utils.myutils' in sys.modules:
            del sys.modules['src.testpilot.utils.myutils']
        if 'src.testpilot.utils.response_parser' in sys.modules:
            del sys.modules['src.testpilot.utils.response_parser']

        # Re-import the module to use fallbacks
        from src.testpilot.audit.audit_processor import process_single_step_audit
        self.process_single_step_audit = process_single_step_audit

    def tearDown(self):
        """Clean up after tests"""
        sys.modules.clear()
        sys.modules.update(self.original_sys_modules)

    @patch('src.testpilot.audit.audit_processor._execute_step_command')
    def test_fallback_extract_step_data(self, mock_execute):
        """Test the fallback implementation of extract_step_data"""
        mock_step = Mock()
        mock_step.command = "test command"
        mock_step.test_name = "fallback_test"
        mock_step.other_fields = {}

        mock_execute.return_value = {"raw_output": "{}", "status_code": 200, "http_method": "GET"}

        # This should execute without error using the fallback
        self.process_single_step_audit(
            mock_step, Mock(), [], {}, Mock(), None, {}, [], AuditEngine(), False, None
        )


if __name__ == '__main__':
    unittest.main(verbosity=2)'''
