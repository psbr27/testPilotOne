#!/usr/bin/env python3
"""
Mock Integration for TestPilot
==============================

Provides integration utilities for replacing SSH execution with mock server responses.
Includes command parsing and response formatting to work with existing validation logic.

Features:
- Parse kubectl exec curl commands to extract HTTP details
- Send HTTP requests to mock server
- Format mock responses to match curl -v output format
- Seamless integration with existing TestPilot validation
"""

import json
import re
import time
from typing import Dict, Optional, Tuple
from urllib.parse import parse_qs, urlparse

import requests


class MockCommandParser:
    """
    Parses kubectl exec curl commands to extract HTTP request details.

    Handles various kubectl/oc command formats and extracts:
    - HTTP method (GET, POST, PUT, DELETE)
    - URL and endpoint path
    - Headers
    - Request payload
    """

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
        error_lines.append("> Host: localhost:8081\\r\\n")
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
    """

    def __init__(self, mock_server_url: str = "http://localhost:8081"):
        self.mock_server_url = mock_server_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "TestPilot-Mock/1.0"})

    def execute_mock_command(
        self, command: str, host: str
    ) -> Tuple[str, str, float]:
        """
        Execute a kubectl curl command against mock server.

        Args:
            command: kubectl exec curl command string
            host: Target host (used for logging)

        Returns:
            Tuple of (output, error, duration) matching execute_command format
        """
        start_time = time.time()

        # Parse command to extract HTTP details
        url, method, headers, payload = (
            MockCommandParser.parse_kubectl_curl_command(command)
        )

        if not url or not method:
            duration = time.time() - start_time
            return MockResponseFormatter.format_error_response(
                "Failed to parse kubectl curl command"
            )

        try:
            # Extract endpoint for mock server
            endpoint = MockCommandParser.extract_endpoint_from_url(url)
            mock_url = (
                f"{self.mock_server_url}/{endpoint}"
                if endpoint
                else self.mock_server_url
            )

            print(f"🔄 Mock request: {method} {mock_url}")

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
                f"✅ Mock response: {response.status_code} ({duration:.3f}s)"
            )

            return output, error, duration

        except requests.RequestException as e:
            duration = time.time() - start_time
            print(f"❌ Mock request failed: {e}")
            return MockResponseFormatter.format_error_response(str(e))
        except Exception as e:
            duration = time.time() - start_time
            print(f"💥 Unexpected error: {e}")
            return MockResponseFormatter.format_error_response(
                f"Unexpected error: {e}"
            )

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
