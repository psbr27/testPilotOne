#!/usr/bin/env python3
"""
Unit Tests for Pod Mode Functionality

Tests the pod mode detection, configuration loading, command execution,
and integration with the audit module.
"""

import json
import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, Mock, mock_open, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.testpilot.audit.audit_engine import AuditEngine
from src.testpilot.audit.audit_processor import (
    process_single_step_audit_pod_mode,
)
from src.testpilot.audit.pod_mode import PodModeManager
from src.testpilot.core.test_result import TestFlow, TestStep


class TestPodModeManager(unittest.TestCase):
    """Test suite for PodModeManager"""

    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.pod_manager = PodModeManager(config_dir=self.temp_dir)
        # Reset cached values
        self.pod_manager._is_pod_mode = None
        self.pod_manager._resources_map = None

    def tearDown(self):
        """Clean up temporary files"""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    # =================================================================
    # POD MODE DETECTION TESTS
    # =================================================================

    @patch.dict(os.environ, {}, clear=True)
    def test_non_pod_mode_detection(self):
        """Test detection of non-pod mode (standard environment)"""
        # Clear all environment variables that might indicate pod mode
        with patch("os.path.exists", return_value=False):
            is_pod = self.pod_manager.is_pod_mode()
            self.assertFalse(is_pod)

    @patch.dict(
        os.environ, {"KUBERNETES_SERVICE_HOST": "10.96.0.1"}, clear=True
    )
    def test_kubernetes_environment_detection(self):
        """Test detection via Kubernetes environment variables"""
        is_pod = self.pod_manager.is_pod_mode()
        self.assertTrue(is_pod)

    @patch.dict(
        os.environ,
        {"JENKINS_URL": "http://jenkins.example.com", "BUILD_NUMBER": "123"},
        clear=True,
    )
    def test_jenkins_environment_detection(self):
        """Test detection via Jenkins environment variables"""
        is_pod = self.pod_manager.is_pod_mode()
        self.assertTrue(is_pod)

    @patch("os.path.exists")
    def test_container_environment_detection(self, mock_exists):
        """Test detection via container indicators"""
        # Mock .dockerenv existence
        mock_exists.side_effect = lambda path: path == "/.dockerenv"
        is_pod = self.pod_manager.is_pod_mode()
        self.assertTrue(is_pod)

    @patch("os.path.exists")
    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data="1:name=systemd:/docker/abc123",
    )
    def test_cgroup_container_detection(self, mock_file, mock_exists):
        """Test detection via cgroup information"""
        mock_exists.side_effect = lambda path: path == "/proc/1/cgroup"
        is_pod = self.pod_manager.is_pod_mode()
        self.assertTrue(is_pod)

    @patch("os.path.exists")
    def test_pod_specific_files_detection(self, mock_exists):
        """Test detection via pod-specific mounted files"""
        mock_exists.side_effect = (
            lambda path: path == "/var/run/secrets/kubernetes.io"
        )
        is_pod = self.pod_manager.is_pod_mode()
        self.assertTrue(is_pod)

    # =================================================================
    # RESOURCES MAP TESTS
    # =================================================================

    def test_resources_map_loading_non_pod_mode(self):
        """Test that resources_map is not required in non-pod mode"""
        with patch.object(self.pod_manager, "is_pod_mode", return_value=False):
            resources_map = self.pod_manager.load_resources_map()
            self.assertEqual(resources_map, {})

    def test_resources_map_missing_in_pod_mode(self):
        """Test error when resources_map.json is missing in pod mode"""
        with patch.object(self.pod_manager, "is_pod_mode", return_value=True):
            with self.assertRaises(FileNotFoundError) as context:
                self.pod_manager.load_resources_map()
            self.assertIn(
                "resources_map.json not found", str(context.exception)
            )

    def test_resources_map_invalid_json(self):
        """Test error when resources_map.json contains invalid JSON"""
        resources_path = os.path.join(self.temp_dir, "resources_map.json")
        with open(resources_path, "w") as f:
            f.write("invalid json {")

        with patch.object(self.pod_manager, "is_pod_mode", return_value=True):
            with self.assertRaises(ValueError) as context:
                self.pod_manager.load_resources_map()
            self.assertIn("Invalid JSON", str(context.exception))

    def test_resources_map_empty_file(self):
        """Test error when resources_map.json is empty"""
        resources_path = os.path.join(self.temp_dir, "resources_map.json")
        with open(resources_path, "w") as f:
            f.write("{}")

        with patch.object(self.pod_manager, "is_pod_mode", return_value=True):
            with self.assertRaises(ValueError) as context:
                self.pod_manager.load_resources_map()
            self.assertIn(
                "resources_map.json is empty", str(context.exception)
            )

    def test_resources_map_valid_loading(self):
        """Test successful loading of valid resources_map.json"""
        test_resources = {
            "service1": "http://service1:8080",
            "service2": "http://service2:8081",
        }
        resources_path = os.path.join(self.temp_dir, "resources_map.json")
        with open(resources_path, "w") as f:
            json.dump(test_resources, f)

        with patch.object(self.pod_manager, "is_pod_mode", return_value=True):
            resources_map = self.pod_manager.load_resources_map()
            self.assertEqual(resources_map, test_resources)

    # =================================================================
    # PLACEHOLDER RESOLUTION TESTS
    # =================================================================

    def test_placeholder_resolution_non_pod_mode(self):
        """Test that placeholders are not resolved in non-pod mode"""
        with patch.object(self.pod_manager, "is_pod_mode", return_value=False):
            command = "curl -X GET {{service_url}}/api/v1/users"
            resolved = self.pod_manager.resolve_placeholders(command)
            self.assertEqual(resolved, command)  # Should be unchanged

    def test_placeholder_resolution_pod_mode(self):
        """Test placeholder resolution in pod mode"""
        test_resources = {
            "service_url": "http://user-service:8080",
            "api_version": "v2",
        }
        resources_path = os.path.join(self.temp_dir, "resources_map.json")
        with open(resources_path, "w") as f:
            json.dump(test_resources, f)

        with patch.object(self.pod_manager, "is_pod_mode", return_value=True):
            command = "curl -X GET {{service_url}}/api/${api_version}/users"
            resolved = self.pod_manager.resolve_placeholders(command)
            expected = "curl -X GET http://user-service:8080/api/v2/users"
            self.assertEqual(resolved, expected)

    def test_placeholder_resolution_multiple_formats(self):
        """Test resolution of different placeholder formats"""
        test_resources = {
            "base_url": "http://api.test.com",
            "user_id": "test-123",
        }
        resources_path = os.path.join(self.temp_dir, "resources_map.json")
        with open(resources_path, "w") as f:
            json.dump(test_resources, f)

        with patch.object(self.pod_manager, "is_pod_mode", return_value=True):
            command = (
                "curl {{base_url}}/users/${user_id} -H 'X-User: $USER_ID'"
            )
            resolved = self.pod_manager.resolve_placeholders(command)
            expected = (
                "curl http://api.test.com/users/test-123 -H 'X-User: test-123'"
            )
            self.assertEqual(resolved, expected)

    # =================================================================
    # CURL COMMAND VALIDATION TESTS
    # =================================================================

    def test_valid_curl_command_detection(self):
        """Test detection of valid curl commands"""
        valid_commands = [
            "curl -X GET http://api.test.com/users",
            'curl --request POST http://api.test.com/users -d \'{"name": "test"}\'',
            "curl -H 'Content-Type: application/json' http://api.test.com",
            "curl https://secure.api.com/endpoint",
        ]

        for command in valid_commands:
            with self.subTest(command=command):
                is_valid = self.pod_manager.is_valid_curl_command(command)
                self.assertTrue(
                    is_valid, f"Command should be valid: {command}"
                )

    def test_invalid_curl_command_detection(self):
        """Test detection of invalid curl commands"""
        invalid_commands = [
            "",
            "   ",
            "echo 'not a curl command'",
            "wget http://example.com",
            "curl",  # No arguments
            "not-curl -X GET http://api.test.com",
        ]

        for command in invalid_commands:
            with self.subTest(command=command):
                is_valid = self.pod_manager.is_valid_curl_command(command)
                self.assertFalse(
                    is_valid, f"Command should be invalid: {command}"
                )

    # =================================================================
    # CURL COMMAND EXECUTION TESTS
    # =================================================================

    @patch("subprocess.run")
    def test_curl_command_execution_success(self, mock_run):
        """Test successful curl command execution"""
        # Mock successful subprocess result
        mock_result = Mock()
        mock_result.stdout = '{"status": "success", "data": {"id": 123}}'
        mock_result.stderr = ""
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        test_resources = {"service_url": "http://api.test.com"}
        resources_path = os.path.join(self.temp_dir, "resources_map.json")
        with open(resources_path, "w") as f:
            json.dump(test_resources, f)

        with patch.object(self.pod_manager, "is_pod_mode", return_value=True):
            command = "curl -X GET {{service_url}}/users"
            stdout, stderr, return_code = (
                self.pod_manager.execute_curl_command(command)
            )

            self.assertEqual(
                stdout, '{"status": "success", "data": {"id": 123}}'
            )
            self.assertEqual(stderr, "")
            self.assertEqual(return_code, 0)

    @patch("subprocess.run")
    def test_curl_command_execution_failure(self, mock_run):
        """Test curl command execution failure"""
        # Mock failed subprocess result
        mock_result = Mock()
        mock_result.stdout = ""
        mock_result.stderr = "curl: (7) Failed to connect"
        mock_result.returncode = 7
        mock_run.return_value = mock_result

        test_resources = {"service_url": "http://api.test.com"}
        resources_path = os.path.join(self.temp_dir, "resources_map.json")
        with open(resources_path, "w") as f:
            json.dump(test_resources, f)

        with patch.object(self.pod_manager, "is_pod_mode", return_value=True):
            command = "curl -X GET {{service_url}}/users"
            stdout, stderr, return_code = (
                self.pod_manager.execute_curl_command(command)
            )

            self.assertEqual(stdout, "")
            self.assertEqual(stderr, "curl: (7) Failed to connect")
            self.assertEqual(return_code, 7)

    def test_curl_execution_non_pod_mode_error(self):
        """Test that curl execution fails in non-pod mode"""
        with patch.object(self.pod_manager, "is_pod_mode", return_value=False):
            with self.assertRaises(RuntimeError) as context:
                self.pod_manager.execute_curl_command("curl http://test.com")
            self.assertIn("only available in pod mode", str(context.exception))

    def test_curl_execution_invalid_command_error(self):
        """Test that invalid curl commands raise ValueError"""
        with patch.object(self.pod_manager, "is_pod_mode", return_value=True):
            with self.assertRaises(ValueError) as context:
                self.pod_manager.execute_curl_command("not a curl command")
            self.assertIn("Invalid curl command", str(context.exception))

    # =================================================================
    # OUTPUT DIRECTORY TESTS
    # =================================================================

    @patch.dict(os.environ, {"WORKSPACE": "/jenkins/workspace"}, clear=True)
    def test_pod_mode_output_directory(self):
        """Test output directory in pod mode"""
        with patch.object(self.pod_manager, "is_pod_mode", return_value=True):
            with patch("os.makedirs") as mock_makedirs:
                output_dir = self.pod_manager.get_output_directory("reports")
                expected = "/jenkins/workspace/reports"
                self.assertEqual(output_dir, expected)
                mock_makedirs.assert_called_once_with(expected, exist_ok=True)

    def test_non_pod_mode_output_directory(self):
        """Test output directory in non-pod mode"""
        with patch.object(self.pod_manager, "is_pod_mode", return_value=False):
            with patch("os.makedirs") as mock_makedirs:
                output_dir = self.pod_manager.get_output_directory("reports")
                self.assertEqual(output_dir, "reports")
                mock_makedirs.assert_called_once_with("reports", exist_ok=True)

    # =================================================================
    # LOGS FOLDER TESTS
    # =================================================================

    def test_logs_folder_creation_pod_mode(self):
        """Test that logs folder is not created in pod mode"""
        with patch.object(self.pod_manager, "is_pod_mode", return_value=True):
            should_create = self.pod_manager.should_create_logs_folder()
            self.assertFalse(should_create)

    def test_logs_folder_creation_non_pod_mode(self):
        """Test that logs folder is created in non-pod mode"""
        with patch.object(self.pod_manager, "is_pod_mode", return_value=False):
            should_create = self.pod_manager.should_create_logs_folder()
            self.assertTrue(should_create)

    # =================================================================
    # EXECUTION CONTEXT TESTS
    # =================================================================

    @patch.dict(
        os.environ,
        {
            "KUBERNETES_SERVICE_HOST": "10.96.0.1",
            "JENKINS_URL": "http://jenkins.test.com",
            "WORKSPACE": "/workspace",
            "POD_NAME": "test-pod-123",
            "POD_NAMESPACE": "default",
        },
        clear=True,
    )
    def test_execution_context_pod_mode(self):
        """Test execution context in pod mode"""
        test_resources = {"service": "http://test.com"}
        resources_path = os.path.join(self.temp_dir, "resources_map.json")
        with open(resources_path, "w") as f:
            json.dump(test_resources, f)

        with patch.object(self.pod_manager, "is_pod_mode", return_value=True):
            context = self.pod_manager.get_execution_context()

            self.assertTrue(context["pod_mode"])
            self.assertTrue(context["resources_map_exists"])
            self.assertEqual(context["resources_map_size"], 1)
            self.assertFalse(context["should_create_logs"])
            self.assertEqual(
                context["environment_variables"]["KUBERNETES_SERVICE_HOST"],
                "10.96.0.1",
            )
            self.assertEqual(
                context["environment_variables"]["POD_NAME"], "test-pod-123"
            )


class TestPodModeAuditIntegration(unittest.TestCase):
    """Test suite for pod mode integration with audit functionality"""

    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.audit_engine = AuditEngine()

        # Create test step and flow
        self.mock_step = TestStep(
            row_idx=1,
            method="GET",
            url="http://api.test.com/users",
            payload="",
            headers={"Content-Type": "application/json"},
            expected_status=200,
            pattern_match='{"status": "success", "users": []}',
            other_fields={
                "Command": "curl -X GET {{api_url}}/users",
                "Pattern_Match": '{"status": "success", "users": []}',
            },
        )
        self.mock_step.test_name = "test_user_list"

        self.mock_flow = TestFlow(
            test_name="user_management_flow",
            sheet="AuditSheet",
            steps=[self.mock_step],
        )

        # Test data
        self.target_hosts = ["test-host"]
        self.svc_maps = {"test-host": {"api": "user-service"}}
        self.placeholder_pattern = Mock()
        self.host_cli_map = {"test-host": "kubectl"}
        self.test_results = []
        self.mock_dashboard = Mock()
        self.mock_args = Mock()

        # Set up resources map
        test_resources = {"api_url": "http://user-service:8080"}
        resources_path = os.path.join(self.temp_dir, "resources_map.json")
        with open(resources_path, "w") as f:
            json.dump(test_resources, f)

    def tearDown(self):
        """Clean up temporary files"""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)
        self.audit_engine.clear_results()

    @patch("src.testpilot.audit.pod_mode.pod_mode_manager")
    @patch("subprocess.run")
    def test_pod_mode_audit_success(self, mock_run, mock_pod_manager):
        """Test successful audit processing in pod mode"""
        # Configure pod mode manager
        mock_pod_manager.is_pod_mode.return_value = True
        mock_pod_manager.is_valid_curl_command.return_value = True
        mock_pod_manager.execute_curl_command.return_value = (
            '{"status": "success", "users": []}',  # stdout
            "",  # stderr
            0,  # return_code
        )

        # Configure successful subprocess result
        mock_result = Mock()
        mock_result.stdout = '{"status": "success", "users": []}'
        mock_result.stderr = ""
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        # Execute pod mode audit
        process_single_step_audit_pod_mode(
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

        # Verify test result was created
        self.assertEqual(len(self.test_results), 1)
        test_result = self.test_results[0]
        self.assertEqual(test_result.test_name, "test_user_list")
        self.assertEqual(test_result.host, "pod-environment")
        self.assertTrue(test_result.passed)
        self.assertEqual(test_result.actual_status, 200)

        # Verify audit was performed
        audit_results = self.audit_engine.get_audit_results()
        self.assertEqual(len(audit_results), 1)
        self.assertEqual(audit_results[0]["overall_result"], "PASS")
        self.assertTrue(audit_results[0]["request_details"]["pod_mode"])

        # Verify dashboard was updated
        self.mock_dashboard.add_test_result.assert_called_once_with(
            test_result
        )

    @patch("src.testpilot.audit.pod_mode.pod_mode_manager")
    def test_pod_mode_audit_fallback_non_pod(self, mock_pod_manager):
        """Test fallback to standard audit when not in pod mode"""
        # Configure non-pod mode
        mock_pod_manager.is_pod_mode.return_value = False

        with patch(
            "src.testpilot.audit.audit_processor.process_single_step_audit"
        ) as mock_standard_audit:
            # Execute pod mode audit (should fallback)
            process_single_step_audit_pod_mode(
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

            # Verify standard audit was called
            mock_standard_audit.assert_called_once()

    @patch("src.testpilot.audit.pod_mode.pod_mode_manager")
    def test_pod_mode_audit_invalid_command(self, mock_pod_manager):
        """Test handling of invalid curl commands in pod mode"""
        # Configure pod mode but invalid command
        mock_pod_manager.is_pod_mode.return_value = True
        mock_pod_manager.is_valid_curl_command.return_value = False

        # Set invalid command
        self.mock_step.other_fields["Command"] = "not a curl command"

        # Execute pod mode audit
        process_single_step_audit_pod_mode(
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

        # Verify no test results or audit results were created
        self.assertEqual(len(self.test_results), 0)
        self.assertEqual(len(self.audit_engine.get_audit_results()), 0)

    @patch("src.testpilot.audit.pod_mode.pod_mode_manager")
    @patch("subprocess.run")
    def test_pod_mode_audit_pattern_mismatch(self, mock_run, mock_pod_manager):
        """Test audit override when pattern doesn't match in pod mode"""
        # Configure pod mode manager
        mock_pod_manager.is_pod_mode.return_value = True
        mock_pod_manager.is_valid_curl_command.return_value = True
        mock_pod_manager.execute_curl_command.return_value = (
            '{"status": "error", "message": "Not found"}',  # Different response
            "",
            0,
        )

        # Execute pod mode audit
        process_single_step_audit_pod_mode(
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

        # Verify test result was created but audit failed
        self.assertEqual(len(self.test_results), 1)
        test_result = self.test_results[0]
        self.assertFalse(test_result.passed)  # Should be overridden by audit
        self.assertFalse(test_result.pattern_found)
        self.assertIn("Pattern differences", test_result.fail_reason)

        # Verify audit detected the mismatch
        audit_results = self.audit_engine.get_audit_results()
        self.assertEqual(len(audit_results), 1)
        self.assertEqual(audit_results[0]["overall_result"], "FAIL")


if __name__ == "__main__":
    unittest.main(verbosity=2)
