#!/usr/bin/env python3
"""
Mock Connector Wrapper
=====================

Provides an SSH connector-compatible interface for mock execution mode.
This allows mock execution to work with the existing execute_flows function.
"""

from typing import Dict, List, Optional

from .mock_integration import MockExecutor


class MockConnectorWrapper:
    """
    Wrapper around MockExecutor that provides SSH connector-compatible interface.
    This allows mock execution to work seamlessly with the existing test execution flow.
    """

    def __init__(self, mock_executor: MockExecutor):
        self.mock_executor = mock_executor
        self.use_ssh = False  # Mock mode doesn't use SSH
        self.connections: Dict[str, MockExecutor] = {}
        self.execution_mode = "mock"  # Set execution mode
        self.mock_server_url = getattr(
            mock_executor, "mock_server_url", "http://localhost:8082"
        )

    def setup_connections(self, config):
        """Mock implementation of setup_connections."""
        pass

    def connect_all(self, target_hosts: Optional[List[str]] = None):
        """Mock implementation of connect_all."""
        # Create mock connections for each host
        if target_hosts:
            for host in target_hosts:
                self.connections[host] = self.mock_executor

    def run_command(
        self, command: str, target_hosts: List[str], timeout: int = 30
    ) -> Dict[str, Dict]:
        """
        Mock implementation of run_command.
        Executes commands through the mock server instead of SSH.
        """
        results = {}
        for host in target_hosts:
            try:
                # Use mock executor to run the command
                output, error = self.mock_executor.execute_mock_command(
                    command
                )
                results[host] = {
                    "output": output,
                    "error": error,
                    "exit_code": 0 if not error else 1,
                }
            except Exception as e:
                results[host] = {"output": "", "error": str(e), "exit_code": 1}
        return results

    def get_connection(self, host_name: str):
        """Mock implementation of get_connection."""
        return self.connections.get(host_name, self.mock_executor)

    def get_all_connections(self) -> Dict[str, MockExecutor]:
        """Mock implementation of get_all_connections."""
        return self.connections

    def get_host_config(self, host_name: str):
        """Mock implementation of get_host_config."""

        # Return a mock host config object
        class MockHostConfig:
            def __init__(self):
                self.name = host_name
                self.hostname = "mock-host"
                self.username = "mock-user"
                self.namespace = "default"
                self.port = 22

        return MockHostConfig()

    def close_all(self):
        """Mock implementation of close_all."""
        self.connections.clear()

    def health_check(self) -> bool:
        """Check if mock server is healthy."""
        return self.mock_executor.health_check()
