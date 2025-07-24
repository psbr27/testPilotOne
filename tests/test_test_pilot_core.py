import json
import os
import re
from typing import Any, Dict
from unittest.mock import MagicMock, Mock, call, patch

import pandas as pd
import pytest

from src.testpilot.core.test_pilot_core import (
    _extract_and_display_epoch_timestamps,
    _load_response_payload_file,
    build_command_for_step,
    build_kubectl_logs_command,
    build_url_based_command,
    execute_command,
    execute_kubectl_logs_parallel,
    extract_step_data,
    manage_workflow_context,
    process_single_step,
    resolve_namespace,
)
from src.testpilot.core.test_result import TestFlow, TestResult, TestStep


class TestExtractStepData:
    """Test cases for extract_step_data function"""

    def test_extract_basic_step_data(self):
        """Test extraction of basic step data"""
        step = Mock(spec=TestStep)
        step.other_fields = {
            "Command": "curl http://example.com",
            "Response_Payload": '{"key": "value"}',
            "podExec": "my-pod",
            "Save_As": "response_1",
        }
        step.expected_status = 200
        step.pattern_match = "status.*ok"
        step.payload = '{"request": "data"}'
        step.method = "POST"
        step.url = "http://example.com/api"
        step.headers = {"Content-Type": "application/json"}

        result = extract_step_data(step)

        assert result["command"] == "curl http://example.com"
        assert result["from_excel_response_payload"] == '{"key": "value"}'
        assert result["expected_status"] == 200
        assert result["pattern_match"] == "status.*ok"
        assert result["pod_exec"] == "my-pod"
        assert result["request_payload"] == '{"request": "data"}'
        assert result["method"] == "POST"
        assert result["url"] == "http://example.com/api"
        assert result["headers"] == {"Content-Type": "application/json"}

    def test_extract_step_data_with_defaults(self):
        """Test extraction with default values"""
        step = Mock(spec=TestStep)
        step.other_fields = {}
        step.expected_status = None
        step.pattern_match = None
        step.payload = None
        step.method = None
        step.url = None
        step.headers = None

        result = extract_step_data(step)

        assert result["command"] is None
        assert result["from_excel_response_payload"] is None
        assert result["expected_status"] is None
        assert result["pattern_match"] == ""
        assert result["pod_exec"] is None
        assert result["request_payload"] is None
        assert result["method"] == "GET"
        assert result["url"] is None
        assert result["headers"] == {}

    def test_extract_step_data_with_string_headers(self):
        """Test extraction when headers is a JSON string"""
        step = Mock(spec=TestStep)
        step.other_fields = {}
        step.expected_status = None
        step.pattern_match = None
        step.payload = None
        step.method = None
        step.url = None
        step.headers = '{"Authorization": "Bearer token"}'

        result = extract_step_data(step)

        assert result["headers"] == {"Authorization": "Bearer token"}

    def test_extract_step_data_with_invalid_json_headers(self):
        """Test extraction when headers is invalid JSON string"""
        step = Mock(spec=TestStep)
        step.other_fields = {}
        step.expected_status = None
        step.pattern_match = None
        step.payload = None
        step.method = None
        step.url = None
        step.headers = "invalid json"

        result = extract_step_data(step)

        assert result["headers"] == {}

    def test_extract_step_data_with_nan_pattern_match(self):
        """Test extraction when pattern_match is NaN"""
        step = Mock(spec=TestStep)
        step.other_fields = {}
        step.expected_status = None
        step.pattern_match = float("nan")
        step.payload = None
        step.method = None
        step.url = None
        step.headers = None

        result = extract_step_data(step)

        assert result["pattern_match"] == ""


class TestManageWorkflowContext:
    """Test cases for manage_workflow_context function"""

    def test_manage_context_with_put_method(self):
        """Test context management for PUT method"""
        flow = Mock(spec=TestFlow)
        flow.context = {}

        step_data = {
            "method": "PUT",
            "request_payload": '{"update": "data"}',
            "save_key": "custom_key",
        }

        manage_workflow_context(flow, step_data)

        assert flow.context["custom_key"] == '{"update": "data"}'

    def test_manage_context_with_post_method(self):
        """Test context management for POST method"""
        flow = Mock(spec=TestFlow)
        flow.context = {}

        step_data = {
            "method": "POST",
            "request_payload": '{"create": "data"}',
            "save_key": None,
        }

        manage_workflow_context(flow, step_data)

        assert flow.context["put_payload"] == '{"create": "data"}'

    def test_manage_context_with_get_method(self):
        """Test context management for GET method (should not save)"""
        flow = Mock(spec=TestFlow)
        flow.context = {}

        step_data = {
            "method": "GET",
            "request_payload": '{"query": "data"}',
            "save_key": "custom_key",
        }

        manage_workflow_context(flow, step_data)

        assert len(flow.context) == 0

    def test_manage_context_with_empty_payload(self):
        """Test context management with empty payload"""
        flow = Mock(spec=TestFlow)
        flow.context = {}

        step_data = {
            "method": "PUT",
            "request_payload": None,
            "save_key": "custom_key",
        }

        manage_workflow_context(flow, step_data)

        assert "custom_key" not in flow.context


class TestResolveNamespace:
    """Test cases for resolve_namespace function"""

    def test_resolve_namespace_with_ssh_connector(self):
        """Test namespace resolution with SSH connector"""
        connector = Mock()
        connector.use_ssh = True
        host_cfg = Mock()
        host_cfg.namespace = "test-namespace"
        connector.get_host_config.return_value = host_cfg

        result = resolve_namespace(connector, "test-host")

        assert result == "test-namespace"
        connector.get_host_config.assert_called_once_with("test-host")

    def test_resolve_namespace_without_ssh(self):
        """Test namespace resolution without SSH (local config)"""
        connector = Mock()
        connector.use_ssh = False

        # Mock the config file reading
        mock_config = {
            "connect_to": "test-host",
            "hosts": {"test-host": {"namespace": "local-namespace"}},
        }

        with patch(
            "builtins.open", mock_open(read_data=json.dumps(mock_config))
        ):
            with patch("os.path.exists", return_value=True):
                result = resolve_namespace(connector, "test-host")

        assert result == "local-namespace"

    def test_resolve_namespace_with_missing_config(self):
        """Test namespace resolution when config is missing"""
        connector = Mock()
        connector.use_ssh = False

        with patch("os.path.exists", return_value=False):
            result = resolve_namespace(connector, "test-host")

        assert result is None


class TestBuildUrlBasedCommand:
    """Test cases for build_url_based_command function"""

    @patch("src.testpilot.core.test_pilot_core.build_ssh_k8s_curl_command")
    @patch("src.testpilot.core.test_pilot_core.replace_placeholder_in_command")
    def test_build_url_based_command_basic(self, mock_replace, mock_build_ssh):
        """Test basic URL-based command building"""
        step_data = {
            "url": "http://{{SERVICE}}/api",
            "method": "GET",
            "headers": {"Accept": "application/json"},
            "request_payload": None,
            "pod_exec": "test-pod",
        }
        svc_map = {"SERVICE": "my-service"}

        mock_replace.return_value = "http://my-service/api"
        mock_build_ssh.return_value = (
            "kubectl exec test-pod -- curl http://my-service/api",
            None,
        )

        result = build_url_based_command(
            step_data, svc_map, None, "default", None, "test-host"
        )

        assert result == "kubectl exec test-pod -- curl http://my-service/api"
        mock_replace.assert_called_once_with("http://{{SERVICE}}/api", svc_map)

    @patch("src.testpilot.core.test_pilot_core.build_ssh_k8s_curl_command")
    @patch("src.testpilot.core.test_pilot_core.replace_placeholder_in_command")
    def test_build_url_based_command_with_cli_type(
        self, mock_replace, mock_build_ssh
    ):
        """Test URL-based command building with custom CLI type"""
        step_data = {
            "url": "http://example.com/api",
            "method": "POST",
            "headers": {"Content-Type": "application/json"},
            "request_payload": '{"test": "data"}',
            "pod_exec": "test-pod",
        }
        host_cli_map = {"test-host": "oc"}

        mock_replace.return_value = "http://example.com/api"
        mock_build_ssh.return_value = (
            "oc exec test-pod -- curl -X POST http://example.com/api",
            None,
        )

        result = build_url_based_command(
            step_data, {}, None, "test-ns", host_cli_map, "test-host"
        )

        assert "oc" in mock_build_ssh.call_args[1]["cli_type"]


class TestBuildKubectlLogsCommand:
    """Test cases for build_kubectl_logs_command function"""

    def test_build_kubectl_logs_no_placeholder(self):
        """Test kubectl logs command without placeholder"""
        with patch(
            "src.testpilot.core.test_pilot_core._generate_logs_capture_command"
        ) as mock_generate:
            mock_generate.return_value = "kubectl logs my-pod > logs.txt"

            result = build_kubectl_logs_command(
                "kubectl logs my-pod", "default", None, "test-host"
            )

            assert result == "kubectl logs my-pod > logs.txt"

    def test_build_kubectl_logs_with_placeholder_mock_mode(self):
        """Test kubectl logs command with placeholder in mock mode"""
        connector = Mock()
        connector.execution_mode = "mock"

        with patch(
            "src.testpilot.core.test_pilot_core._generate_logs_capture_command"
        ) as mock_generate:
            mock_generate.return_value = (
                "kubectl logs test-pod-mock123-abc456 > logs.txt"
            )

            result = build_kubectl_logs_command(
                "kubectl logs {test-pod}", "default", connector, "test-host"
            )

            assert len(result) == 1
            assert "mock123-abc456" in result[0]

    @patch("subprocess.run")
    def test_build_kubectl_logs_with_placeholder_local(self, mock_run):
        """Test kubectl logs command with placeholder in local mode"""
        mock_run.return_value = Mock(stdout="test-pod-abc123\ntest-pod-def456")

        with patch(
            "src.testpilot.core.test_pilot_core._generate_logs_capture_command"
        ) as mock_generate:
            mock_generate.side_effect = [
                "kubectl logs test-pod-abc123 > logs1.txt",
                "kubectl logs test-pod-def456 > logs2.txt",
            ]

            result = build_kubectl_logs_command(
                "kubectl logs {test-pod}", "default", None, "test-host"
            )

            assert len(result) == 2
            assert "test-pod-abc123" in result[0]
            assert "test-pod-def456" in result[1]

    @patch("subprocess.run")
    @patch("builtins.open")
    def test_build_kubectl_logs_slf_provgw_filtering(
        self, mock_open, mock_run
    ):
        """Test kubectl logs command with SLF provgw filtering using instance labels"""
        # Mock config file for SLF deployment
        mock_config = {"nf_name": "SLF_TEST"}
        mock_file = Mock()
        mock_file.read.return_value = json.dumps(mock_config)
        mock_open.return_value.__enter__.return_value = mock_file

        # Mock pod list and kubectl get pod commands
        def mock_subprocess_side_effect(*args, **kwargs):
            if args and len(args) > 0:
                if (
                    isinstance(args[0], str)
                    and "get pods" in args[0]
                    and "grep" in args[0]
                ):
                    # Return mix of slf and provgw pods for the initial grep search
                    return Mock(
                        stdout="slf-ingressgateway-prov-abc123\nprovgw-prov-ingressgateway-def456\nslf-group-prov-ghi789",
                        returncode=0,
                    )
                elif isinstance(args[0], str) and "jsonpath=" in args[0]:
                    # Now using shell=True, so command is a string
                    if "slf-ingressgateway-prov-abc123" in args[0]:
                        return Mock(stdout="namespace", returncode=0)
                    elif "provgw-prov-ingressgateway-def456" in args[0]:
                        return Mock(stdout="provgw", returncode=0)
                    elif "slf-group-prov-ghi789" in args[0]:
                        return Mock(stdout="namespace", returncode=0)
            return Mock(stdout="", returncode=1)

        mock_run.side_effect = mock_subprocess_side_effect

        with patch(
            "src.testpilot.core.test_pilot_core._generate_logs_capture_command"
        ) as mock_generate:
            mock_generate.return_value = "kubectl logs pod > logs.txt"

            result = build_kubectl_logs_command(
                "kubectl logs {ingressgateway}", "default", None, "test-host"
            )

            # Should only include slf pods, not provgw pods
            assert len(result) == 2
            # Verify the correct pods were processed (mock_generate gets called for each filtered pod)
            assert mock_generate.call_count == 2
            # Verify that only slf pods were passed to _generate_logs_capture_command
            call_args_list = mock_generate.call_args_list
            pod_commands = [call[0][0] for call in call_args_list]
            assert (
                "kubectl logs slf-ingressgateway-prov-abc123" in pod_commands
            )
            assert "kubectl logs slf-group-prov-ghi789" in pod_commands
            # Verify provgw pod was filtered out
            assert all(
                "provgw-prov-ingressgateway-def456" not in cmd
                for cmd in pod_commands
            )

    @patch("builtins.open")
    def test_build_kubectl_logs_slf_provgw_filtering_ssh(self, mock_open):
        """Test kubectl logs command with SLF provgw filtering using instance labels via SSH"""
        # Mock config file for SLF deployment
        mock_config = {"nf_name": "SLF_TEST"}
        mock_file = Mock()
        mock_file.read.return_value = json.dumps(mock_config)
        mock_open.return_value.__enter__.return_value = mock_file

        # Mock SSH connector
        connector = Mock()
        connector.use_ssh = True

        def mock_run_command_side_effect(cmd, hosts):
            if "get pods" in cmd and "grep" in cmd:
                # Return mix of slf and provgw pods for the initial grep search
                return {
                    "test-host": {
                        "output": "slf-ingressgateway-prov-abc123\nprovgw-prov-ingressgateway-def456\nslf-group-prov-ghi789",
                        "error": "",
                    }
                }
            elif "jsonpath=" in cmd:
                if "slf-ingressgateway-prov-abc123" in cmd:
                    return {"test-host": {"output": "namespace", "error": ""}}
                elif "provgw-prov-ingressgateway-def456" in cmd:
                    return {"test-host": {"output": "provgw", "error": ""}}
                elif "slf-group-prov-ghi789" in cmd:
                    return {"test-host": {"output": "namespace", "error": ""}}
            return {"test-host": {"output": "", "error": "command not found"}}

        connector.run_command.side_effect = mock_run_command_side_effect

        with patch(
            "src.testpilot.core.test_pilot_core._generate_logs_capture_command"
        ) as mock_generate:
            mock_generate.return_value = "kubectl logs pod > logs.txt"

            result = build_kubectl_logs_command(
                "kubectl logs {ingressgateway}",
                "default",
                connector,
                "test-host",
            )

            # Should only include slf pods, not provgw pods
            assert len(result) == 2
            # Verify the correct pods were processed
            assert mock_generate.call_count == 2
            # Verify that only slf pods were passed to _generate_logs_capture_command
            call_args_list = mock_generate.call_args_list
            pod_commands = [call[0][0] for call in call_args_list]
            assert (
                "kubectl logs slf-ingressgateway-prov-abc123" in pod_commands
            )
            assert "kubectl logs slf-group-prov-ghi789" in pod_commands
            # Verify provgw pod was filtered out
            assert all(
                "provgw-prov-ingressgateway-def456" not in cmd
                for cmd in pod_commands
            )


class TestExecuteCommand:
    """Test cases for execute_command function"""

    def test_execute_command_empty(self):
        """Test execution with empty command"""
        result_output, result_error, duration = execute_command(
            "", "test-host", None
        )

        assert result_output == ""
        assert result_error == "Command build failed"
        assert duration == 0.0

    def test_execute_command_mock_mode(self):
        """Test execution in mock mode"""
        connector = Mock()
        connector.execution_mode = "mock"
        connector._current_sheet = "Sheet1"
        connector._current_test = "Test1"

        with patch(
            "src.testpilot.core.test_pilot_core.execute_mock_command"
        ) as mock_exec:
            mock_exec.return_value = ('{"status": "ok"}', "", 0.1)

            output, error, duration = execute_command(
                "curl http://example.com", "test-host", connector
            )

            assert output == '{"status": "ok"}'
            assert error == ""
            assert duration == 0.1

    @patch("subprocess.run")
    def test_execute_command_local(self, mock_run):
        """Test local command execution"""
        mock_run.return_value = Mock(stdout="Success", stderr="", returncode=0)

        output, error, duration = execute_command(
            "echo 'Success'", "localhost", None
        )

        assert output == "Success"
        assert error == ""
        assert duration > 0

    def test_execute_command_ssh(self):
        """Test SSH command execution"""
        connector = Mock()
        connector.use_ssh = True
        connector.run_command.return_value = {
            "test-host": {
                "output": "SSH Success",
                "error": "",
                "duration": 0.5,
            }
        }

        output, error, duration = execute_command(
            "ls -la", "test-host", connector
        )

        assert output == "SSH Success"
        assert error == ""
        assert (
            duration > 0
        )  # Duration is calculated by execute_command, not from mock


class TestExecuteKubectlLogsParallel:
    """Test cases for execute_kubectl_logs_parallel function"""

    @patch("src.testpilot.core.test_pilot_core.execute_command")
    @patch("src.testpilot.core.test_pilot_core.save_kubectl_logs")
    def test_execute_kubectl_logs_parallel_empty_commands(
        self, mock_save_logs, mock_execute
    ):
        """Test parallel execution with empty command list"""
        step = Mock()
        flow = Mock()

        result_output, pod_names, duration = execute_kubectl_logs_parallel(
            [], "test-host", None, step, flow
        )

        assert result_output == ""
        assert pod_names == []
        assert duration == 0.0
        mock_execute.assert_not_called()
        mock_save_logs.assert_not_called()

    @patch("src.testpilot.core.test_pilot_core.execute_command")
    @patch("src.testpilot.core.test_pilot_core.save_kubectl_logs")
    @patch("src.testpilot.core.test_pilot_core.parse_curl_output")
    @patch(
        "src.testpilot.core.test_pilot_core._extract_and_display_epoch_timestamps"
    )
    def test_execute_kubectl_logs_parallel_single_command_ssh(
        self, mock_timestamps, mock_parse, mock_save_logs, mock_execute
    ):
        """Test parallel execution with single kubectl command via SSH"""
        # Setup mocks
        mock_execute.return_value = ("kubectl log output", "", 1.5)
        mock_parse.return_value = {
            "raw_output": "kubectl log output",
            "is_kubectl_logs": True,
        }

        step = Mock()
        step.row_idx = 1
        flow = Mock()
        flow.test_name = "test_parallel"

        connector = Mock()
        connector.use_ssh = True

        commands = ["kubectl logs test-pod-123"]

        result_output, pod_names, duration = execute_kubectl_logs_parallel(
            commands, "test-host", connector, step, flow, show_table=True
        )

        # Verify results
        assert result_output == "kubectl log output"
        assert len(pod_names) == 1
        assert pod_names[0] == "test-pod-123"
        assert duration == 1.5

        # Verify execute_command was called correctly
        mock_execute.assert_called_once_with(
            "kubectl logs test-pod-123", "test-host", connector
        )

        # Verify kubectl logs were saved
        mock_save_logs.assert_called_once_with(
            "kubectl log output",
            "test-host",
            "1_test-pod-123",
            "test_parallel",
        )

    @patch("src.testpilot.core.test_pilot_core.execute_command")
    @patch("src.testpilot.core.test_pilot_core.save_kubectl_logs")
    @patch("src.testpilot.core.test_pilot_core.parse_curl_output")
    def test_execute_kubectl_logs_parallel_single_command_local(
        self, mock_parse, mock_save_logs, mock_execute
    ):
        """Test parallel execution with single kubectl command locally"""
        # Setup mocks
        mock_execute.return_value = ("local kubectl output", "", 0.8)
        mock_parse.return_value = {
            "raw_output": "local kubectl output",
            "is_kubectl_logs": True,
        }

        step = Mock()
        step.row_idx = 2
        flow = Mock()
        flow.test_name = "test_local"

        # No connector (local execution)
        connector = None

        commands = ["kubectl logs app-pod-456"]

        result_output, pod_names, duration = execute_kubectl_logs_parallel(
            commands, "localhost", connector, step, flow
        )

        # Verify results
        assert result_output == "local kubectl output"
        assert len(pod_names) == 1
        assert pod_names[0] == "app-pod-456"
        assert duration == 0.8

        # Verify execute_command was called correctly
        mock_execute.assert_called_once_with(
            "kubectl logs app-pod-456", "localhost", connector
        )

    @patch("src.testpilot.core.test_pilot_core.execute_command")
    @patch("src.testpilot.core.test_pilot_core.save_kubectl_logs")
    @patch("src.testpilot.core.test_pilot_core.parse_curl_output")
    def test_execute_kubectl_logs_parallel_multiple_commands(
        self, mock_parse, mock_save_logs, mock_execute
    ):
        """Test parallel execution with multiple kubectl commands"""

        # Setup mocks for multiple commands
        def mock_execute_side_effect(command, host, connector):
            if "pod1" in command:
                return ("logs from pod1", "", 1.0)
            elif "pod2" in command:
                return ("logs from pod2", "", 1.2)
            elif "pod3" in command:
                return ("logs from pod3", "", 0.9)
            return ("", "", 0.0)

        mock_execute.side_effect = mock_execute_side_effect
        mock_parse.return_value = {"raw_output": "", "is_kubectl_logs": True}

        # Mock parse_curl_output to return different outputs
        def mock_parse_side_effect(output, error):
            return {"raw_output": output, "is_kubectl_logs": True}

        mock_parse.side_effect = mock_parse_side_effect

        step = Mock()
        step.row_idx = 3
        flow = Mock()
        flow.test_name = "test_multiple"

        connector = Mock()
        connector.use_ssh = True

        commands = [
            "kubectl logs test-pod1",
            "kubectl logs test-pod2",
            "kubectl logs test-pod3",
        ]

        result_output, pod_names, duration = execute_kubectl_logs_parallel(
            commands, "test-host", connector, step, flow, show_table=True
        )

        # Verify results (order may vary due to parallel execution)
        assert "logs from pod1" in result_output
        assert "logs from pod2" in result_output
        assert "logs from pod3" in result_output
        assert len(pod_names) == 3
        assert "test-pod1" in pod_names
        assert "test-pod2" in pod_names
        assert "test-pod3" in pod_names
        assert duration == 1.2  # Should be max duration

        # Verify all commands were executed
        assert mock_execute.call_count == 3
        assert mock_save_logs.call_count == 3

    @patch("src.testpilot.core.test_pilot_core.execute_command")
    @patch("src.testpilot.core.test_pilot_core.save_kubectl_logs")
    @patch("src.testpilot.core.test_pilot_core.parse_curl_output")
    def test_execute_kubectl_logs_parallel_with_oc_commands(
        self, mock_parse, mock_save_logs, mock_execute
    ):
        """Test parallel execution with oc logs commands (OpenShift)"""
        # Setup mocks
        mock_execute.return_value = ("oc log output", "", 1.1)
        mock_parse.return_value = {
            "raw_output": "oc log output",
            "is_kubectl_logs": True,
        }

        step = Mock()
        step.row_idx = 4
        flow = Mock()
        flow.test_name = "test_oc"

        connector = Mock()
        connector.use_ssh = False

        commands = ["oc logs openshift-pod-789"]

        result_output, pod_names, duration = execute_kubectl_logs_parallel(
            commands, "openshift-host", connector, step, flow
        )

        # Verify results
        assert result_output == "oc log output"
        assert len(pod_names) == 1
        assert pod_names[0] == "openshift-pod-789"
        assert duration == 1.1

    @patch("src.testpilot.core.test_pilot_core.execute_command")
    def test_execute_kubectl_logs_parallel_command_failure(self, mock_execute):
        """Test parallel execution with command failures"""
        # Setup mock to raise exception
        mock_execute.side_effect = Exception("Command failed")

        step = Mock()
        step.row_idx = 5
        flow = Mock()
        flow.test_name = "test_failure"

        connector = Mock()

        commands = ["kubectl logs failing-pod"]

        result_output, pod_names, duration = execute_kubectl_logs_parallel(
            commands, "test-host", connector, step, flow, show_table=True
        )

        # Should handle failure gracefully
        assert result_output == ""
        assert pod_names == []
        assert duration == 0.0

    @patch("src.testpilot.core.test_pilot_core.execute_command")
    @patch("src.testpilot.core.test_pilot_core.save_kubectl_logs")
    @patch("src.testpilot.core.test_pilot_core.parse_curl_output")
    def test_execute_kubectl_logs_parallel_pod_name_extraction(
        self, mock_parse, mock_save_logs, mock_execute
    ):
        """Test pod name extraction from various kubectl command formats"""
        mock_execute.return_value = ("test output", "", 1.0)
        mock_parse.return_value = {
            "raw_output": "test output",
            "is_kubectl_logs": True,
        }

        step = Mock()
        step.row_idx = 6
        flow = Mock()
        flow.test_name = "test_extraction"

        connector = Mock()

        # Test various command formats
        test_cases = [
            ("kubectl logs simple-pod", "simple-pod"),
            ("kubectl logs complex-pod-123-abc", "complex-pod-123-abc"),
            ("oc logs openshift-pod", "openshift-pod"),
            ("kubectl logs", None),  # Missing pod name
        ]

        for idx, (command, expected_pod) in enumerate(test_cases):
            mock_execute.reset_mock()
            mock_save_logs.reset_mock()

            result_output, pod_names, duration = execute_kubectl_logs_parallel(
                [command], "test-host", connector, step, flow
            )

            assert len(pod_names) == 1
            assert pod_names[0] == expected_pod


class TestKubectlParallelIntegration:
    """Integration tests for kubectl parallel execution in main command flow"""

    @patch("src.testpilot.core.test_pilot_core.execute_kubectl_logs_parallel")
    @patch("src.testpilot.core.test_pilot_core.execute_command")
    @patch("src.testpilot.core.test_pilot_core.parse_curl_output")
    @patch("src.testpilot.core.test_pilot_core.build_command_for_step")
    @patch("src.testpilot.core.test_pilot_core.extract_step_data")
    @patch("src.testpilot.core.test_pilot_core.manage_workflow_context")
    @patch("src.testpilot.core.test_pilot_core.resolve_namespace")
    @patch("src.testpilot.core.test_pilot_core.validate_and_create_result")
    @patch("src.testpilot.core.test_pilot_core.log_test_result")
    def test_mixed_command_separation_and_execution(
        self,
        mock_log,
        mock_validate,
        mock_resolve,
        mock_manage,
        mock_extract,
        mock_build,
        mock_parse,
        mock_execute,
        mock_parallel,
    ):
        """Test that kubectl logs and other commands are properly separated and executed"""
        # Setup mocks
        mock_extract.return_value = {"command": "mixed_test"}
        mock_resolve.return_value = "default"
        mock_build.return_value = [
            "kubectl logs app-pod-1",
            "kubectl logs app-pod-2",
            "curl http://api.example.com/health",
            "oc logs openshift-pod",
        ]

        # Mock parallel execution results
        mock_parallel.return_value = (
            "kubectl logs output",
            ["app-pod-1", "app-pod-2", "openshift-pod"],
            2.5,
        )

        # Mock regular command execution
        mock_execute.return_value = ("curl health check output", "", 0.5)
        mock_parse.return_value = {"raw_output": "curl health check output"}

        # Mock validation
        mock_result = Mock()
        mock_result.passed = True
        mock_validate.return_value = mock_result

        # Create test objects
        step = Mock()
        step.other_fields = {}
        step.row_idx = 1
        step.step_name = "test_step"

        flow = Mock()
        flow.test_name = "integration_test"
        flow.sheet = "TestSheet"
        flow.context = {}

        connector = Mock()
        connector.use_ssh = True

        test_results = []

        # Execute
        process_single_step(
            step=step,
            flow=flow,
            target_hosts=["test-host"],
            svc_maps={"test-host": {}},
            placeholder_pattern=re.compile(r"\{\{(\w+)\}\}"),
            connector=connector,
            host_cli_map={"test-host": "kubectl"},
            test_results=test_results,
            show_table=True,
            dashboard=None,
        )

        # Verify that parallel execution was called with kubectl commands
        mock_parallel.assert_called_once_with(
            [
                "kubectl logs app-pod-1",
                "kubectl logs app-pod-2",
                "oc logs openshift-pod",
            ],
            "test-host",
            connector,
            step,
            flow,
            True,
        )

        # Verify that regular execution was called with non-kubectl command
        mock_execute.assert_called_once_with(
            "curl http://api.example.com/health", "test-host", connector
        )

        # Verify results were created
        assert len(test_results) == 1
        assert test_results[0] == mock_result

    @patch("src.testpilot.core.test_pilot_core.execute_kubectl_logs_parallel")
    @patch("src.testpilot.core.test_pilot_core.build_command_for_step")
    @patch("src.testpilot.core.test_pilot_core.extract_step_data")
    @patch("src.testpilot.core.test_pilot_core.manage_workflow_context")
    @patch("src.testpilot.core.test_pilot_core.resolve_namespace")
    def test_only_kubectl_commands_use_parallel_execution(
        self,
        mock_resolve,
        mock_manage,
        mock_extract,
        mock_build,
        mock_parallel,
    ):
        """Test that only kubectl logs commands trigger parallel execution"""
        # Setup mocks
        mock_extract.return_value = {"command": "kubectl_only_test"}
        mock_resolve.return_value = "default"
        mock_build.return_value = [
            "kubectl logs pod-1",
            "kubectl logs pod-2",
            "oc logs openshift-pod-3",
        ]

        mock_parallel.return_value = (
            "all kubectl logs",
            ["pod-1", "pod-2", "openshift-pod-3"],
            1.8,
        )

        # Create minimal test objects
        step = Mock()
        step.other_fields = {}
        step.row_idx = 2

        flow = Mock()
        flow.context = {}

        # Use show_table=True to suppress logging output during test
        with patch(
            "src.testpilot.core.test_pilot_core.validate_and_create_result"
        ) as mock_validate:
            mock_result = Mock()
            mock_result.passed = True
            mock_validate.return_value = mock_result

            test_results = []
            process_single_step(
                step=step,
                flow=flow,
                target_hosts=["kubectl-host"],
                svc_maps={"kubectl-host": {}},
                placeholder_pattern=re.compile(r"\{\{(\w+)\}\}"),
                connector=Mock(),
                host_cli_map={},
                test_results=test_results,
                show_table=True,
                dashboard=None,
            )

        # Verify parallel execution was called (since all commands are kubectl logs)
        mock_parallel.assert_called_once()

        # Verify all commands were passed to parallel execution
        args, kwargs = mock_parallel.call_args
        kubectl_commands = args[0]
        assert len(kubectl_commands) == 3
        assert "kubectl logs pod-1" in kubectl_commands
        assert "kubectl logs pod-2" in kubectl_commands
        assert "oc logs openshift-pod-3" in kubectl_commands


class TestProcessSingleStep:
    """Test cases for process_single_step function"""

    @patch("src.testpilot.core.test_pilot_core.extract_step_data")
    def test_process_single_step_skip_empty_command(self, mock_extract):
        """Test skipping step with empty command"""
        mock_extract.return_value = {"command": None}

        step = Mock()
        flow = Mock()

        result = process_single_step(
            step, flow, ["host1"], {}, None, None, {}, [], None, None
        )

        assert result is None

    @patch("src.testpilot.core.test_pilot_core.extract_step_data")
    @patch("src.testpilot.core.test_pilot_core.manage_workflow_context")
    @patch("src.testpilot.core.test_pilot_core.execute_command")
    @patch("src.testpilot.core.test_pilot_core.build_command_for_step")
    def test_process_single_step_basic_flow(
        self, mock_build, mock_execute, mock_manage, mock_extract
    ):
        """Test basic step processing flow"""
        # Setup mocks
        mock_extract.return_value = {
            "command": "curl http://example.com",
            "url": "http://example.com",
            "method": "GET",
            "expected_status": 200,
            "pattern_match": "",
            "from_excel_response_payload": None,
            "compare_with_key": None,
            "headers": {},
            "request_payload": None,
            "pod_exec": None,
        }
        mock_build.return_value = "kubectl exec pod -- curl http://example.com"
        mock_execute.return_value = ('{"status": "ok"}', "", 0.1)

        # Create test objects
        step = Mock()
        step.name = "Test Step"
        step.other_fields = {"Save_As": "response_1"}

        flow = Mock()
        flow.context = {}

        test_results = []

        # Execute
        process_single_step(
            step=step,
            flow=flow,
            target_hosts=["host1"],
            svc_maps={"host1": {}},
            placeholder_pattern=None,
            connector=None,
            host_cli_map={},
            test_results=test_results,
            show_table=None,
            dashboard=None,
        )

        # Verify workflow context was managed
        mock_manage.assert_called_once()

        # Verify command was built and executed
        mock_build.assert_called_once()
        mock_execute.assert_called_once()


class TestUtilityFunctions:
    """Test cases for utility functions"""

    def test_extract_epoch_timestamps(self):
        """Test epoch timestamp extraction"""
        raw_output = """
        {"epochSecond": 1609459200, "message": "Start"}
        {"epochSecond": 1609459260, "message": "End"}
        """

        with patch(
            "src.testpilot.core.test_pilot_core.get_logger"
        ) as mock_logger:
            logger = Mock()
            mock_logger.return_value = logger

            _extract_and_display_epoch_timestamps(raw_output)

            # Verify logging calls
            assert any(
                "First epochSecond: 1609459200" in str(call)
                for call in logger.info.call_args_list
            )
            assert any(
                "Last epochSecond: 1609459260" in str(call)
                for call in logger.info.call_args_list
            )
            assert any(
                "Time difference: 60 seconds" in str(call)
                for call in logger.info.call_args_list
            )

    def test_load_response_payload_file(self):
        """Test loading response payload from file"""
        with patch("os.path.isfile", return_value=True):
            with patch(
                "builtins.open", mock_open(read_data='{"test": "data"}')
            ):
                result = _load_response_payload_file("test.json")

                assert result == '{"test": "data"}'

    def test_load_response_payload_file_not_found(self):
        """Test loading response payload when file not found"""
        with patch("os.path.isfile", return_value=False):
            with patch(
                "src.testpilot.core.test_pilot_core.get_logger"
            ) as mock_logger:
                result = _load_response_payload_file("missing.json")

                assert result == "missing.json"


def mock_open(read_data=""):
    """Helper to create a mock for builtins.open"""
    import builtins
    from unittest.mock import mock_open as _mock_open

    return _mock_open(read_data=read_data)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
