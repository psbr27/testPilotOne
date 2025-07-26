#!/usr/bin/env python3
"""
Pod Mode Support for TestPilot Audit Module

Handles execution context detection and configuration for running testPilot
directly within a Jenkins pod environment, with specialized logic for:
- Pod vs non-pod mode detection
- Resources map configuration loading
- Simplified command execution
- Log management without local folder creation
"""

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..utils.logger import get_logger

logger = get_logger("TestPilot.Audit.PodMode")


class PodModeManager:
    """
    Manages pod mode execution context and configuration for audit module.
    """

    def __init__(self, config_dir: str = "config"):
        self.config_dir = config_dir
        self.resources_map_path = os.path.join(
            config_dir, "resources_map.json"
        )
        self._is_pod_mode = None
        self._resources_map = None
        self._namespace = None

    def is_pod_mode(self) -> bool:
        """
        Detect if testPilot is running in pod mode (inside a Jenkins pod).

        Returns:
            bool: True if running in pod mode, False otherwise
        """
        if self._is_pod_mode is not None:
            return self._is_pod_mode

        # Check multiple indicators for pod mode
        pod_indicators = [
            self._check_kubernetes_environment(),
            self._check_jenkins_environment(),
            self._check_container_environment(),
            self._check_pod_specific_files(),
        ]

        self._is_pod_mode = any(pod_indicators)

        if self._is_pod_mode:
            logger.info(
                "🏗️  Pod mode detected - Running inside Jenkins pod environment"
            )
        else:
            logger.info(
                "🖥️  Non-pod mode detected - Running in standard environment"
            )

        return self._is_pod_mode

    def _check_kubernetes_environment(self) -> bool:
        """Check for Kubernetes environment variables."""
        k8s_vars = [
            "KUBERNETES_SERVICE_HOST",
            "KUBERNETES_SERVICE_PORT",
            "KUBE_POD_NAME",
            "POD_NAME",
            "POD_NAMESPACE",
        ]
        return any(os.getenv(var) for var in k8s_vars)

    def _check_jenkins_environment(self) -> bool:
        """Check for Jenkins-specific environment variables."""
        jenkins_vars = ["JENKINS_URL", "BUILD_NUMBER", "JOB_NAME", "WORKSPACE"]
        return any(os.getenv(var) for var in jenkins_vars)

    def _check_container_environment(self) -> bool:
        """Check if running inside a container."""
        container_indicators = [
            os.path.exists("/.dockerenv"),
            os.path.exists("/proc/1/cgroup")
            and self._is_in_container_cgroup(),
        ]
        return any(container_indicators)

    def _is_in_container_cgroup(self) -> bool:
        """Check cgroup information for container indicators."""
        try:
            with open("/proc/1/cgroup", "r") as f:
                cgroup_content = f.read()
                return (
                    "docker" in cgroup_content or "kubepods" in cgroup_content
                )
        except (FileNotFoundError, PermissionError):
            return False

    def _check_pod_specific_files(self) -> bool:
        """Check for pod-specific mounted files."""
        pod_files = ["/var/run/secrets/kubernetes.io", "/etc/podinfo"]
        return any(os.path.exists(path) for path in pod_files)

    def load_resources_map(self) -> Dict[str, str]:
        """
        Load and validate resources_map.json for placeholder pattern resolution.

        Returns:
            Dict[str, str]: Resource mapping for placeholder resolution

        Raises:
            FileNotFoundError: If resources_map.json is not found in pod mode
            ValueError: If resources_map.json is invalid or empty
        """
        if self._resources_map is not None:
            return self._resources_map

        if not self.is_pod_mode():
            logger.debug("Non-pod mode: resources_map.json not required")
            return {}

        # In pod mode, resources_map.json is mandatory
        if not os.path.exists(self.resources_map_path):
            error_msg = (
                f"Pod mode detected but resources_map.json not found at {self.resources_map_path}. "
                "This file is mandatory for pod mode execution."
            )
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)

        try:
            with open(self.resources_map_path, "r") as f:
                self._resources_map = json.load(f)
        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON in resources_map.json: {e}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        if not self._resources_map:
            error_msg = "resources_map.json is empty. Configuration is mandatory for pod mode."
            logger.error(error_msg)
            raise ValueError(error_msg)

        logger.info(
            f"✅ Loaded resources_map.json with {len(self._resources_map)} resource mappings"
        )
        return self._resources_map

    def should_create_logs_folder(self) -> bool:
        """
        Determine if logs folder should be created.

        Returns:
            bool: False for pod mode (logs go to stdout/stderr), True for non-pod mode
        """
        return not self.is_pod_mode()

    def get_output_directory(self, default_dir: str = "audit_reports") -> str:
        """
        Get the appropriate output directory for audit reports.

        Args:
            default_dir: Default directory name

        Returns:
            str: Output directory path
        """
        if self.is_pod_mode():
            # In pod mode, use workspace or current directory
            workspace = os.getenv("WORKSPACE", os.getcwd())
            output_dir = os.path.join(workspace, default_dir)
        else:
            output_dir = default_dir

        os.makedirs(output_dir, exist_ok=True)
        return output_dir

    def resolve_placeholders(self, command: str) -> str:
        """
        Resolve placeholder patterns in commands using resources_map.json.

        Args:
            command: Command string with potential placeholders

        Returns:
            str: Command with resolved placeholders
        """
        if not self.is_pod_mode():
            return command

        resources_map = self.load_resources_map()
        resolved_command = command

        # Find and replace placeholders like {{service_name}}, ${SERVICE_NAME}, etc.
        placeholder_patterns = [
            r"\{\{(\w+)\}\}",  # {{placeholder}}
            r"\$\{(\w+)\}",  # ${placeholder}
            r"\$(\w+)",  # $placeholder
        ]

        for pattern in placeholder_patterns:
            matches = re.findall(pattern, resolved_command)
            for match in matches:
                placeholder_key = match.lower()
                if placeholder_key in resources_map:
                    # Replace all variations of this placeholder
                    variations = [
                        f"{{{{{match}}}}}",  # {{match}}
                        f"${{{match}}}",  # ${match}
                        f"${match}",  # $match
                        f"{{{{{match.upper()}}}}}",  # {{MATCH}}
                        f"${{{match.upper()}}}",  # ${MATCH}
                        f"${match.upper()}",  # $MATCH
                    ]

                    for variation in variations:
                        if variation in resolved_command:
                            resolved_command = resolved_command.replace(
                                variation, resources_map[placeholder_key]
                            )
                            logger.debug(
                                f"Resolved placeholder {variation} -> {resources_map[placeholder_key]}"
                            )

        return resolved_command

    def is_valid_curl_command(self, command: str) -> bool:
        """
        Check if a command is a valid curl command suitable for direct execution.

        Args:
            command: Command string to validate

        Returns:
            bool: True if it's a valid curl command, False otherwise
        """
        if not command or not command.strip():
            return False

        # Remove leading/trailing whitespace and check if it starts with curl
        clean_command = command.strip()
        if not clean_command.startswith("curl"):
            return False

        # Basic validation for curl command structure
        curl_indicators = [
            "-X",  # HTTP method
            "--request",
            "-H",  # Headers
            "--header",
            "-d",  # Data
            "--data",
            "http://",  # URLs
            "https://",
        ]

        # Command should have at least one of these indicators or a URL
        return any(indicator in clean_command for indicator in curl_indicators)

    def execute_curl_command(
        self, command: str, timeout: int = 30
    ) -> Tuple[str, str, int]:
        """
        Execute a curl command directly in pod mode.

        Args:
            command: Curl command to execute
            timeout: Command timeout in seconds

        Returns:
            Tuple[str, str, int]: (stdout, stderr, return_code)
        """
        if not self.is_pod_mode():
            raise RuntimeError(
                "Direct curl execution only available in pod mode"
            )

        if not self.is_valid_curl_command(command):
            raise ValueError(f"Invalid curl command: {command}")

        # Resolve placeholders
        resolved_command = self.resolve_placeholders(command)
        logger.info(f"🚀 Executing curl command: {resolved_command}")

        try:
            # Execute command with timeout
            result = subprocess.run(
                resolved_command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            logger.debug(
                f"Command completed with return code: {result.returncode}"
            )
            return result.stdout, result.stderr, result.returncode

        except subprocess.TimeoutExpired:
            error_msg = f"Command timed out after {timeout} seconds"
            logger.error(error_msg)
            return "", error_msg, -1
        except Exception as e:
            error_msg = f"Command execution failed: {e}"
            logger.error(error_msg)
            return "", error_msg, -1

    def get_execution_context(self) -> Dict[str, Any]:
        """
        Get comprehensive execution context information.

        Returns:
            Dict[str, Any]: Execution context details
        """
        context = {
            "pod_mode": self.is_pod_mode(),
            "config_dir": self.config_dir,
            "resources_map_path": self.resources_map_path,
            "resources_map_exists": os.path.exists(self.resources_map_path),
            "should_create_logs": self.should_create_logs_folder(),
            "environment_variables": {
                "KUBERNETES_SERVICE_HOST": os.getenv(
                    "KUBERNETES_SERVICE_HOST"
                ),
                "JENKINS_URL": os.getenv("JENKINS_URL"),
                "WORKSPACE": os.getenv("WORKSPACE"),
                "POD_NAME": os.getenv("POD_NAME"),
                "POD_NAMESPACE": os.getenv("POD_NAMESPACE"),
            },
        }

        if self.is_pod_mode():
            try:
                context["resources_map_size"] = len(self.load_resources_map())
            except (FileNotFoundError, ValueError):
                context["resources_map_size"] = 0

        return context

    def get_namespace(self) -> str:
        """
        Get the Kubernetes namespace for pod mode execution.

        In pod mode, the namespace is determined from (in order of priority):
        1. TESTPILOT_NAMESPACE environment variable
        2. TARGET_NAMESPACE environment variable (Jenkins parameter)
        3. NAMESPACE environment variable
        4. POD_NAMESPACE environment variable
        5. 'namespace' key in resources_map.json
        6. Default to 'default' namespace

        Returns:
            str: The namespace to use for Kubernetes operations
        """
        if self._namespace is not None:
            return self._namespace

        # Check environment variables in priority order
        namespace_env_vars = [
            "TESTPILOT_NAMESPACE",
            "TARGET_NAMESPACE",
            "NAMESPACE",
            "POD_NAMESPACE",
        ]

        for env_var in namespace_env_vars:
            namespace = os.getenv(env_var)
            if namespace:
                self._namespace = namespace
                logger.info(f"🎯 Using namespace '{namespace}' from {env_var}")
                return self._namespace

        # Check resources_map.json
        if self.is_pod_mode():
            try:
                resources = self.load_resources_map()
                if "namespace" in resources:
                    self._namespace = resources["namespace"]
                    logger.info(
                        f"🎯 Using namespace '{self._namespace}' from resources_map.json"
                    )
                    return self._namespace
            except (FileNotFoundError, ValueError):
                pass

        # Default namespace
        self._namespace = "default"
        logger.warning("⚠️  No namespace specified, using 'default' namespace")
        return self._namespace


# Global instance for easy access
pod_mode_manager = PodModeManager()
