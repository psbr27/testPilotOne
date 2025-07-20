#!/usr/bin/env python3
"""
Mock Integration for TestPilot
==============================

Provides integration utilities for replacing SSH execution with mock server responses.
Includes command parsing and response formatting to work with existing validation logic.

Features:
- Parse kubectl exec curl commands to extract HTTP details
- Parse kubectl commands (logs, get, describe) for mock server routing
- Send HTTP requests to mock server
- Format mock responses to match curl -v output format
- Seamless integration with existing TestPilot validation
"""

import json
import re
import time
from typing import Dict, Optional, Tuple, Union
from urllib.parse import parse_qs, urlparse

import requests


class MockCommandParser:
    """
    Enhanced parser that handles both kubectl exec curl commands and kubectl commands.

    Supports:
    - kubectl exec curl commands → HTTP request details
    - kubectl logs commands → kubectl mock server routing
    - kubectl get commands → kubectl mock server routing
    - kubectl describe commands → kubectl mock server routing
    """

    @staticmethod
    def parse_command(
        command: str,
    ) -> Tuple[str, Dict]:
        """
        Parse any command and determine its type and parameters.

        Args:
            command: Full command string

        Returns:
            Tuple of (command_type, parsed_data)
            - command_type: "http" or "kubectl" or "unknown"
            - parsed_data: Dict with relevant parsed information
        """
        if not command:
            return "unknown", {}

        # Check for kubectl exec curl commands (HTTP type)
        if "curl" in command and (
            "kubectl exec" in command or "oc exec" in command
        ):
            url, method, headers, payload = (
                MockCommandParser.parse_kubectl_curl_command(command)
            )
            if url and method:
                return "http", {
                    "url": url,
                    "method": method,
                    "headers": headers,
                    "payload": payload,
                    "original_command": command,
                }

        # Check for pure kubectl commands
        if command.strip().startswith(("kubectl", "oc")):
            kubectl_data = MockCommandParser.parse_kubectl_command(command)
            if kubectl_data:
                return "kubectl", kubectl_data

        return "unknown", {"original_command": command}

    @staticmethod
    def parse_kubectl_command(command: str) -> Optional[Dict]:
        """
        Parse kubectl commands to extract mock server routing information.

        Args:
            command: kubectl command string

        Returns:
            Dict with kubectl command details or None if parsing fails
        """
        if not command:
            return None

        try:
            # Normalize command by removing extra whitespace
            normalized_cmd = " ".join(command.split())

            # Extract base kubectl operation
            if "kubectl logs" in normalized_cmd or "oc logs" in normalized_cmd:
                return MockCommandParser._parse_kubectl_logs(normalized_cmd)
            elif "kubectl get" in normalized_cmd or "oc get" in normalized_cmd:
                return MockCommandParser._parse_kubectl_get(normalized_cmd)
            elif (
                "kubectl describe" in normalized_cmd
                or "oc describe" in normalized_cmd
            ):
                return MockCommandParser._parse_kubectl_describe(
                    normalized_cmd
                )
            else:
                # Generic kubectl command
                return {
                    "kubectl_type": "generic",
                    "original_command": command,
                    "cli_type": (
                        "oc" if command.strip().startswith("oc") else "kubectl"
                    ),
                }

        except Exception as e:
            print(f"⚠️  Error parsing kubectl command: {e}")
            return None

    @staticmethod
    def _parse_kubectl_logs(command: str) -> Dict:
        """Parse kubectl logs command."""
        # Extract pod name/pattern
        pod_pattern = None
        namespace = None

        # Look for pod name after 'logs'
        logs_match = re.search(r"(kubectl|oc)\s+logs\s+([^\s]+)", command)
        if logs_match:
            pod_pattern = logs_match.group(2)

        # Look for namespace
        namespace_match = re.search(r"-n\s+([^\s]+)", command)
        if namespace_match:
            namespace = namespace_match.group(1)

        return {
            "kubectl_type": "logs",
            "pod_pattern": pod_pattern,
            "namespace": namespace,
            "original_command": command,
            "cli_type": (
                "oc" if command.strip().startswith("oc") else "kubectl"
            ),
        }

    @staticmethod
    def _parse_kubectl_get(command: str) -> Dict:
        """Parse kubectl get command."""
        # Extract resource type
        resource_type = None
        namespace = None

        # Look for resource after 'get'
        get_match = re.search(r"(kubectl|oc)\s+get\s+([^\s]+)", command)
        if get_match:
            resource_type = get_match.group(2)

        # Look for namespace
        namespace_match = re.search(r"-n\s+([^\s]+)", command)
        if namespace_match:
            namespace = namespace_match.group(1)

        return {
            "kubectl_type": "get",
            "resource_type": resource_type,
            "namespace": namespace,
            "original_command": command,
            "cli_type": (
                "oc" if command.strip().startswith("oc") else "kubectl"
            ),
        }

    @staticmethod
    def _parse_kubectl_describe(command: str) -> Dict:
        """Parse kubectl describe command."""
        # Extract resource type and name
        resource_type = None
        resource_name = None
        namespace = None

        # Look for resource after 'describe'
        describe_match = re.search(
            r"(kubectl|oc)\s+describe\s+([^\s]+)(?:\s+([^\s]+))?", command
        )
        if describe_match:
            resource_type = describe_match.group(2)
            resource_name = (
                describe_match.group(3) if describe_match.group(3) else None
            )

        # Look for namespace
        namespace_match = re.search(r"-n\s+([^\s]+)", command)
        if namespace_match:
            namespace = namespace_match.group(1)

        return {
            "kubectl_type": "describe",
            "resource_type": resource_type,
            "resource_name": resource_name,
            "namespace": namespace,
            "original_command": command,
            "cli_type": (
                "oc" if command.strip().startswith("oc") else "kubectl"
            ),
        }

    @staticmethod
    def parse_kubectl_curl_command(
        command: str,
    ) -> Tuple[Optional[str], Optional[str], Optional[Dict], Optional[str]]:
        """
        Parse kubectl exec curl command to extract HTTP request details.

        Args:
            command: Full kubectl exec curl command string

        Returns:
            Tuple of (url, method, headers, payload)
        """
        if not command or "curl" not in command:
            return None, None, None, None

        try:
            # Extract method (default GET)
            method_match = re.search(r"-X\s+(\w+)", command)
            method = method_match.group(1) if method_match else "GET"

            # Extract URL (stop at quotes or whitespace)
            url_match = re.search(r"http://[^\s'\"]+", command)
            if not url_match:
                # Try https as well
                url_match = re.search(r"https://[^\s'\"]+", command)

            if not url_match:
                return None, None, None, None

            url = url_match.group(0)

            # Extract headers
            headers = {}
            header_matches = re.findall(r"-H\s+'([^']+)'", command)
            if not header_matches:
                header_matches = re.findall(r'-H\s+"([^"]+)"', command)

            for header in header_matches:
                if ":" in header:
                    key, value = header.split(":", 1)
                    headers[key.strip()] = value.strip()

            # Add default content-type if not present
            if "Content-Type" not in headers and "content-type" not in headers:
                headers["Content-Type"] = "application/json"

            # Extract payload if present
            payload = None
            payload_match = re.search(r"-d\s+'([^']+)'", command)
            if not payload_match:
                payload_match = re.search(r'-d\s+"([^"]+)"', command)
            if payload_match:
                payload_str = payload_match.group(1)
                try:
                    # Try to parse as JSON
                    payload = json.loads(payload_str)
                except json.JSONDecodeError:
                    # Keep as string if not valid JSON
                    payload = payload_str

            return url, method, headers, payload

        except Exception as e:
            print(f"⚠️  Error parsing kubectl curl command: {e}")
            return None, None, None, None

    @staticmethod
    def extract_endpoint_from_url(url: str) -> str:
        """Extract endpoint path from full URL for mock server routing."""
        try:
            parsed = urlparse(url)
            endpoint = parsed.path.strip("/")
            if parsed.query:
                endpoint += f"?{parsed.query}"
            return endpoint
        except Exception:
            return ""


class MockResponseFormatter:
    """
    Formats mock server responses to match curl -v output format.

    Ensures compatibility with existing TestPilot validation logic by
    simulating the exact format expected from curl verbose output.
    """

    @staticmethod
    def format_response_to_curl_format(
        response: requests.Response, duration: float
    ) -> Tuple[str, str]:
        """
        Format HTTP response to match curl -v output format.

        Args:
            response: requests.Response object from mock server
            duration: Request duration in seconds

        Returns:
            Tuple of (output, error) matching curl format
        """
        # Extract response body
        output = response.text if response.text else ""

        # Build curl-style verbose error output (contains headers and status)
        error_lines = []

        # Add connection info
        error_lines.append("*   Trying 127.0.0.1...")
        error_lines.append("* TCP_NODELAY set")
        error_lines.append(
            "* Connected to localhost (127.0.0.1) port 8081 (#0)"
        )
        error_lines.append("* Using HTTP2, server supports multi-use")
        error_lines.append("* Connection state changed (HTTP/2 confirmed)")

        # Add request headers
        error_lines.append(
            f"> {response.request.method} {response.request.path_url} HTTP/2\\r\\n"
        )
        error_lines.append("> Host: localhost:8082\\r\\n")
        error_lines.append("> User-Agent: curl/7.61.1\\r\\n")
        error_lines.append("> Accept: */*\\r\\n")

        if hasattr(response.request, "headers"):
            for key, value in response.request.headers.items():
                if key.lower() not in ["host", "user-agent", "accept"]:
                    error_lines.append(f"> {key}: {value}\\r\\n")

        error_lines.append("> \\r\\n")

        # Add response status and headers
        error_lines.append(f"< HTTP/2 {response.status_code} \\r\\n")

        for key, value in response.headers.items():
            error_lines.append(f"< {key}: {value}\\r\\n")

        error_lines.append("< \\r\\n")

        # Add transfer info
        content_length = len(output) if output else 0
        error_lines.append(f"{{ [{content_length} bytes data]}}")
        error_lines.append(
            f"\\r100 {content_length:5}  100 {content_length:5}    0     0  {int(content_length/duration):5}      0 --:--:-- --:--:-- --:--:-- {int(content_length/duration):5}"
        )
        error_lines.append("* Connection #0 to host localhost left intact")

        error = "\\n".join(error_lines)

        return output, error

    @staticmethod
    def format_error_response(error_message: str) -> Tuple[str, str]:
        """Format error responses for failed requests."""
        output = ""
        error = f"curl: (7) Failed to connect to mock server: {error_message}"
        return output, error


class MockExecutor:
    """
    Executes mock requests and formats responses for TestPilot integration.

    Provides the main interface for replacing SSH execution with mock server calls.
    Supports both HTTP API calls and kubectl commands.
    """

    def __init__(self, mock_server_url: str = "http://localhost:8082"):
        self.mock_server_url = mock_server_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "TestPilot-Mock/1.0"})

    def execute_mock_command(
        self,
        command: str,
        host: str,
        sheet_name: str = None,
        test_name: str = None,
    ) -> Tuple[str, str, float]:
        """
        Execute any command against mock server (HTTP API or kubectl).

        Args:
            command: Command string (kubectl exec curl, kubectl logs, etc.)
            host: Target host (used for logging)
            sheet_name: Test sheet name for enhanced mock server targeting
            test_name: Test name for enhanced mock server targeting

        Returns:
            Tuple of (output, error, duration) matching execute_command format
        """
        start_time = time.time()

        # Parse command to determine type and extract details
        command_type, parsed_data = MockCommandParser.parse_command(command)

        if command_type == "http":
            return self._execute_http_mock(
                parsed_data, host, sheet_name, test_name, start_time
            )
        elif command_type == "kubectl":
            return self._execute_kubectl_mock(
                parsed_data, host, sheet_name, test_name, start_time
            )
        else:
            duration = time.time() - start_time
            return MockResponseFormatter.format_error_response(
                f"Unsupported command type: {command_type}"
            )

    def _execute_http_mock(
        self,
        parsed_data: Dict,
        host: str,
        sheet_name: str,
        test_name: str,
        start_time: float,
    ) -> Tuple[str, str, float]:
        """Execute HTTP API mock request."""
        try:
            url = parsed_data["url"]
            method = parsed_data["method"]
            headers = parsed_data["headers"] or {}
            payload = parsed_data["payload"]

            # Extract endpoint for mock server
            endpoint = MockCommandParser.extract_endpoint_from_url(url)
            mock_url = (
                f"{self.mock_server_url}/{endpoint}"
                if endpoint
                else self.mock_server_url
            )

            # Add sheet and test context for enhanced mock servers
            if sheet_name:
                headers["X-Test-Sheet"] = sheet_name
            if test_name:
                headers["X-Test-Name"] = test_name

            # Build enhanced URL display with sheet and test context
            enhanced_url_display = mock_url
            if sheet_name or test_name:
                context_parts = []
                if sheet_name:
                    context_parts.append(f"sheet={sheet_name}")
                if test_name:
                    context_parts.append(f"test={test_name}")
                # Use appropriate separator based on whether URL already has query params
                separator = "&" if "?" in mock_url else "?"
                enhanced_url_display += (
                    f"{separator}{{{' & '.join(context_parts)}}}"
                )

            print(f"🔄 Mock HTTP request: {method} {enhanced_url_display}")

            # Send request to mock server
            response = self.session.request(
                method=method,
                url=mock_url,
                headers=headers,
                json=payload,
                timeout=30,
            )

            duration = time.time() - start_time

            # Format response to curl format
            output, error = (
                MockResponseFormatter.format_response_to_curl_format(
                    response, duration
                )
            )

            print(
                f"✅ Mock HTTP response: {response.status_code} ({duration:.3f}s)"
            )

            return output, error, duration

        except requests.RequestException as e:
            duration = time.time() - start_time
            print(f"❌ Mock HTTP request failed: {e}")
            return MockResponseFormatter.format_error_response(str(e))
        except Exception as e:
            duration = time.time() - start_time
            print(f"💥 Unexpected HTTP error: {e}")
            return MockResponseFormatter.format_error_response(
                f"Unexpected error: {e}"
            )

    def _execute_kubectl_mock(
        self,
        parsed_data: Dict,
        host: str,
        sheet_name: str,
        test_name: str,
        start_time: float,
    ) -> Tuple[str, str, float]:
        """Execute kubectl command mock request."""
        try:
            kubectl_type = parsed_data["kubectl_type"]

            # Build mock server URL for kubectl commands
            mock_url = f"{self.mock_server_url}/mock/kubectl/{kubectl_type}"

            # Prepare parameters
            params = {"sheet": sheet_name, "test": test_name, "host": host}

            # Add kubectl-specific parameters
            if kubectl_type == "logs":
                if parsed_data.get("pod_pattern"):
                    params["pod_pattern"] = parsed_data["pod_pattern"]
                if parsed_data.get("namespace"):
                    params["namespace"] = parsed_data["namespace"]
            elif kubectl_type == "get":
                if parsed_data.get("resource_type"):
                    params["resource_type"] = parsed_data["resource_type"]
                if parsed_data.get("namespace"):
                    params["namespace"] = parsed_data["namespace"]
            elif kubectl_type == "describe":
                if parsed_data.get("resource_type"):
                    params["resource_type"] = parsed_data["resource_type"]
                if parsed_data.get("resource_name"):
                    params["resource_name"] = parsed_data["resource_name"]
                if parsed_data.get("namespace"):
                    params["namespace"] = parsed_data["namespace"]

            # Build display URL
            param_str = "&".join([f"{k}={v}" for k, v in params.items() if v])
            display_url = f"{mock_url}?{param_str}"

            print(
                f"🔄 Mock kubectl request: {kubectl_type.upper()} {display_url}"
            )

            # Send GET request to mock server
            response = self.session.get(
                mock_url,
                params=params,
                timeout=30,
            )

            duration = time.time() - start_time

            if response.status_code == 200:
                # Return response as kubectl output (no curl formatting needed)
                output = response.text
                error = ""
                print(
                    f"✅ Mock kubectl response: {response.status_code} ({duration:.3f}s)"
                )
                return output, error, duration
            else:
                error_msg = f"Mock kubectl server returned {response.status_code}: {response.text}"
                print(f"❌ Mock kubectl request failed: {error_msg}")
                return "", error_msg, duration

        except requests.RequestException as e:
            duration = time.time() - start_time
            print(f"❌ Mock kubectl request failed: {e}")
            return "", f"Mock kubectl request failed: {e}", duration
        except Exception as e:
            duration = time.time() - start_time
            print(f"💥 Unexpected kubectl error: {e}")
            return "", f"Unexpected kubectl error: {e}", duration

    def health_check(self) -> bool:
        """Check if mock server is running and responsive."""
        try:
            response = self.session.get(
                f"{self.mock_server_url}/health", timeout=5
            )
            return response.status_code == 200
        except Exception:
            return False


def test_command_parser():
    """Test the command parser with sample kubectl commands."""
    test_commands = [
        "kubectl get po -n ocnrfslf | awk '{print $1}' | grep -E 'nudr-config-[a-z0-9]+-[a-z0-9]+$' | head -n 1 | xargs -I{} kubectl exec -it {} -n ocnrfslf -c nudr-config -- curl -v --http2-prior-knowledge -X GET http://localhost:5001/nudr-config/v1/udr.global.cfg/GLOBAL -H 'Content-Type: application/json'",
        'kubectl get po -n ocnrfslf | awk \'{print $1}\' | grep -E \'appinfo-[a-z0-9]+-[a-z0-9]+$\' | head -n 1 | xargs -I{} kubectl exec -it {} -n ocnrfslf -c appinfo -- curl -v --http2-prior-knowledge -X PUT http://ocslf-ingressgateway-prov.ocnrfslf.svc.tailgate.lab.us.oracle.com:8081/slf-group-prov/v1/slf-group -H \'Content-Type: application/json\' -d \'{"slfGroupType":"ImsHss","nfGroupIDs":{"PCF":"pcfgroup-name1","AUSF":"ausfgroup-name1","NEF":"nefgroup-name1","UDM":"udmgroup-name1"},"slfGroupName":"IMSGrp1"}\'',
    ]

    parser = MockCommandParser()

    for i, command in enumerate(test_commands):
        print(f"\n🧪 Test {i+1}:")
        print(f"Command: {command[:100]}...")

        url, method, headers, payload = parser.parse_kubectl_curl_command(
            command
        )

        print(f"URL: {url}")
        print(f"Method: {method}")
        print(f"Headers: {headers}")
        print(f"Payload: {payload}")

        if url:
            endpoint = parser.extract_endpoint_from_url(url)
            print(f"Endpoint: {endpoint}")


if __name__ == "__main__":
    # Run tests
    test_command_parser()
