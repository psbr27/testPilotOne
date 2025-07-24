import json
import os
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
