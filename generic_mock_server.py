#!/usr/bin/env python3
"""
Generic Mock Server for TestPilot
================================

A generic HTTP mock server that simulates real server behavior using actual response data.
Loads responses from real test results and provides realistic API simulation.

Features:
- Generic endpoint handling (any path, any method)
- Real response data from actual test runs
- Stateful behavior (maintains server state like real APIs)
- Curl-compatible response formatting
- Dynamic response generation for unknown endpoints
"""

import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qs, urlparse

from flask import Flask, jsonify, request


class GenericMockServer:
    """
    Generic mock server that simulates real API behavior using actual response data.

    Features:
    - Loads real response data from TestPilot test results
    - Handles any HTTP method on any endpoint
    - Maintains stateful behavior like real servers
    - Returns realistic responses based on actual data
    """

    def __init__(
        self,
        real_responses_file: str = "mock_data/test_results_20250719_122220.json",
        port: int = 8081,
    ):
        self.app = Flask(__name__)
        self.port = port
        self.real_responses = {}
        self.endpoint_patterns = {}
        self.state = {}  # In-memory state like real server
        self.request_count = 0

        # Load real response data
        self.load_real_responses(real_responses_file)

        # Setup routes
        self.setup_routes()

    def load_real_responses(self, file_path: str):
        """Load real server responses and index them by endpoint patterns."""
        try:
            with open(file_path, "r") as f:
                data = json.load(f)

            print(f"📁 Loading real responses from {file_path}")
            print(f"📊 Found {len(data.get('results', []))} real test results")

            # Index responses by endpoint + method for fast lookup
            for result in data.get("results", []):
                endpoint, method, payload = self.extract_request_info(
                    result.get("command", "")
                )
                if endpoint and method:
                    key = f"{method}:{endpoint}"
                    self.real_responses[key] = {
                        "output": result.get("output", ""),
                        "error": result.get("error", ""),
                        "status": result.get("status", "PASS"),
                        "method": method,
                        "endpoint": endpoint,
                        "test_name": result.get("test_name", ""),
                        "sheet": result.get("sheet", ""),
                    }

                    # Store endpoint patterns for fuzzy matching
                    pattern = self.create_endpoint_pattern(endpoint)
                    self.endpoint_patterns[pattern] = key

            print(
                f"🎯 Indexed {len(self.real_responses)} unique endpoint-method combinations"
            )

            # Debug: print some examples
            example_keys = list(self.real_responses.keys())[:5]
            for key in example_keys:
                print(f"   📋 {key}")

        except Exception as e:
            print(f"❌ Error loading real responses: {e}")
            # Continue with empty responses - will generate generic ones
            self.real_responses = {}

    def extract_request_info(
        self, command: str
    ) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Extract endpoint, method, and payload from kubectl exec curl command."""
        if not command or "curl" not in command:
            return None, None, None

        try:
            # Extract method (default GET)
            method_match = re.search(r"-X\s+(\w+)", command)
            method = method_match.group(1) if method_match else "GET"

            # Extract URL
            url_match = re.search(r"http://[^\s]+", command)
            if not url_match:
                return None, None, None

            full_url = url_match.group(0)
            parsed_url = urlparse(full_url)

            # Clean up endpoint path
            endpoint = parsed_url.path.strip("/")
            if parsed_url.query:
                endpoint += f"?{parsed_url.query}"

            # Extract payload if present
            payload = None
            payload_match = re.search(r"-d\s+'([^']+)'", command)
            if not payload_match:
                payload_match = re.search(r'-d\s+"([^"]+)"', command)
            if payload_match:
                payload = payload_match.group(1)

            return endpoint, method, payload

        except Exception as e:
            print(f"⚠️  Error parsing command: {e}")
            return None, None, None

    def create_endpoint_pattern(self, endpoint: str) -> str:
        """Create a regex pattern for endpoint matching."""
        # Replace dynamic parts with wildcards
        pattern = endpoint
        pattern = re.sub(r"/[a-f0-9-]{36}", "/{{uuid}}", pattern)  # UUIDs
        pattern = re.sub(r"/\d+", "/{{id}}", pattern)  # Numeric IDs
        pattern = re.sub(
            r"\?.*", "", pattern
        )  # Remove query params for pattern
        return pattern

    def find_matching_response(
        self, method: str, endpoint: str
    ) -> Optional[Dict]:
        """Find a matching response using exact match or pattern matching."""
        # Try exact match first
        exact_key = f"{method}:{endpoint}"
        if exact_key in self.real_responses:
            return self.real_responses[exact_key]

        # Try pattern matching
        clean_endpoint = re.sub(r"\?.*", "", endpoint)  # Remove query params

        for pattern, response_key in self.endpoint_patterns.items():
            if self.endpoint_matches_pattern(clean_endpoint, pattern):
                return self.real_responses[response_key]

        # Try method-agnostic matching (any method for same endpoint)
        for key, response in self.real_responses.items():
            if key.endswith(f":{endpoint}") or key.endswith(
                f":{clean_endpoint}"
            ):
                return response

        return None

    def endpoint_matches_pattern(self, endpoint: str, pattern: str) -> bool:
        """Check if endpoint matches a pattern."""
        # Convert pattern to regex
        regex_pattern = pattern.replace("{{uuid}}", "[a-f0-9-]{36}")
        regex_pattern = regex_pattern.replace("{{id}}", r"\d+")
        regex_pattern = f"^{regex_pattern}$"

        return bool(re.match(regex_pattern, endpoint))

    def setup_routes(self):
        """Setup Flask routes for handling any request."""

        @self.app.route("/health", methods=["GET"])
        def health_check():
            """Health check endpoint."""
            return jsonify(
                {
                    "status": "healthy",
                    "server": "Generic Mock Server",
                    "timestamp": datetime.now().isoformat(),
                    "loaded_responses": len(self.real_responses),
                    "request_count": self.request_count,
                }
            )

        @self.app.route("/mock/responses", methods=["GET"])
        def list_responses():
            """Debug endpoint to list all loaded responses."""
            return jsonify(
                {
                    "responses": list(self.real_responses.keys()),
                    "patterns": list(self.endpoint_patterns.keys()),
                    "total": len(self.real_responses),
                }
            )

        @self.app.route("/mock/state", methods=["GET"])
        def get_state():
            """Debug endpoint to view current server state."""
            return jsonify(
                {"state": self.state, "request_count": self.request_count}
            )

        @self.app.route("/mock/reset", methods=["POST"])
        def reset_state():
            """Reset server state."""
            self.state.clear()
            self.request_count = 0
            return jsonify(
                {
                    "message": "State reset",
                    "timestamp": datetime.now().isoformat(),
                }
            )

        @self.app.route(
            "/<path:path>", methods=["GET", "POST", "PUT", "DELETE", "PATCH"]
        )
        def handle_any_request(path):
            """Generic handler for any HTTP request."""
            return self.handle_generic_request(path)

        @self.app.route("/", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
        def handle_root_request():
            """Handle requests to root path."""
            return self.handle_generic_request("")

    def handle_generic_request(self, path: str) -> Tuple[Any, int]:
        """Handle any HTTP request generically."""
        self.request_count += 1
        method = request.method
        full_path = path

        # Add query parameters to path
        if request.query_string:
            full_path += f"?{request.query_string.decode()}"

        print(f"🔄 Request #{self.request_count}: {method} /{full_path}")

        # Find matching response from real data
        matching_response = self.find_matching_response(method, full_path)

        if matching_response:
            print(f"✅ Found real response for {method} /{full_path}")
            return self.format_real_response(
                matching_response, method, full_path
            )
        else:
            print(f"🔧 Generating response for {method} /{full_path}")
            return self.generate_generic_response(method, full_path)

    def format_real_response(
        self, response_data: Dict, method: str, path: str
    ) -> Tuple[Any, int]:
        """Format a real response for return."""
        output = response_data.get("output", "")
        status = response_data.get("status", "PASS")

        # Try to parse output as JSON
        try:
            if output:
                json_output = json.loads(output)
                return jsonify(json_output), 200 if status == "PASS" else 400
            else:
                # Empty response (like 201 Created)
                return "", 201 if method in ["PUT", "POST"] else 204
        except json.JSONDecodeError:
            # Return as plain text if not JSON
            return output, 200 if status == "PASS" else 400

    def generate_generic_response(
        self, method: str, path: str
    ) -> Tuple[Any, int]:
        """Generate a generic response for unknown endpoints."""
        if method == "GET":
            return (
                jsonify(
                    {
                        "message": f"Mock response for GET /{path}",
                        "timestamp": datetime.now().isoformat(),
                        "data": [],
                    }
                ),
                200,
            )
        elif method == "POST":
            # Simulate creation
            resource_id = f"mock-{int(time.time())}"
            self.state[resource_id] = request.get_json() or {}
            return jsonify({"id": resource_id, "created": True}), 201
        elif method == "PUT":
            # Simulate update/creation
            resource_id = f"mock-{int(time.time())}"
            self.state[resource_id] = request.get_json() or {}
            return "", 201
        elif method == "DELETE":
            # Simulate deletion
            return "", 204
        else:
            return jsonify({"error": f"Method {method} not implemented"}), 405

    def run(self, host: str = "0.0.0.0", debug: bool = False):
        """Start the mock server."""
        print(f"🚀 Starting Generic Mock Server on {host}:{self.port}")
        print(f"📊 Loaded {len(self.real_responses)} real responses")
        print(f"🔗 Health check: http://{host}:{self.port}/health")
        print(f"🐛 Debug responses: http://{host}:{self.port}/mock/responses")

        self.app.run(host=host, port=self.port, debug=debug)


def main():
    """CLI entry point for the generic mock server."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Generic Mock Server for TestPilot"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8081,
        help="Port to run server on (default: 8081)",
    )
    parser.add_argument(
        "--host", default="0.0.0.0", help="Host to bind to (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--data-file",
        default="mock_data/test_results_20250719_122220.json",
        help="Real response data file (default: mock_data/test_results_20250719_122220.json)",
    )
    parser.add_argument(
        "--debug", action="store_true", help="Enable Flask debug mode"
    )

    args = parser.parse_args()

    # Create and start server
    server = GenericMockServer(
        real_responses_file=args.data_file, port=args.port
    )

    try:
        server.run(host=args.host, debug=args.debug)
    except KeyboardInterrupt:
        print("\n👋 Generic Mock Server stopped")


if __name__ == "__main__":
    main()
