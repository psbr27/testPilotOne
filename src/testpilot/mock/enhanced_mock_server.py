#!/usr/bin/env python3
"""
Enhanced Mock Server for TestPilot
==================================

An advanced mock server that uses structured enhanced mock data with explicit
sheet names, test names, and organized endpoint information for precise
mapping.

Features:
- Sheet-aware response mapping
- Test-aware step sequencing
- Query parameter matching
- Header-based response selection
- Fallback response strategies
- Enhanced debugging and introspection
"""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from flask import Flask, jsonify, request


class EnhancedMockServer:
    """
    Enhanced mock server using structured mock data with sheet/test metadata.

    Provides precise response mapping based on:
    - Primary: Sheet name and test name combination
    - Secondary: Endpoint and method matching
    - Tertiary: Query parameter matching
    - Fallback: Header-based selection and step sequencing
    """

    def __init__(
        self,
        enhanced_data_file: str = (
            "mock_data/enhanced_test_results_20250719_122220.json"
        ),
        port: int = 8082,
    ):
        self.app = Flask(__name__)
        self.port = port
        self.enhanced_data = {}

        # Primary mapping: sheet_name::test_name -> test data
        self.primary_mappings = {}

        # Secondary mappings for fallback
        self.response_mappings = {}
        self.sheet_mappings = {}
        self.test_mappings = {}

        self.request_count = 0
        self.test_sequences = {}  # Track step sequences

        # Load enhanced data
        self.load_enhanced_data(enhanced_data_file)

        # Setup routes
        self.setup_routes()

    def load_enhanced_data(self, file_path: str):
        """Load structured enhanced mock data."""
        try:
            with open(file_path, "r") as f:
                data = json.load(f)

            self.enhanced_data = data
            print(f"📁 Loading enhanced mock data from {file_path}")

            metadata = data.get("metadata", {})
            print(
                f"📊 Enhanced data version: "
                f"{metadata.get('enhanced_version', 'unknown')}"
            )
            print(f"📊 Total test steps: {metadata.get('total_tests', 0)}")
            print(f"📊 Unique sheets: {metadata.get('unique_sheets', 0)}")
            print(f"📊 Unique tests: {metadata.get('unique_tests', 0)}")

            # Handle both list and dictionary formats for enhanced_results
            enhanced_results = data.get("enhanced_results", [])
            if isinstance(enhanced_results, dict):
                # Convert dictionary format to list for processing
                results_list = []
                for test_name, test_data in enhanced_results.items():
                    # Ensure test_name is set in the data
                    if isinstance(test_data, dict):
                        test_data["test_name"] = test_name
                        results_list.append(test_data)
                enhanced_results = results_list
                print(
                    f"📋 Converted dictionary format with {len(enhanced_results)} tests"
                )

            # Index responses for fast lookup
            self.index_responses(enhanced_results)

        except Exception as e:
            print(f"❌ Error loading enhanced data: {e}")
            self.enhanced_data = {}

    def index_responses(self, results: List[Dict]):
        """Create indices for fast response lookup prioritizing sheet+test."""
        self.primary_mappings = {}
        self.response_mappings = {}
        self.sheet_mappings = {}
        self.test_mappings = {}

        for result in results:
            sheet_name = result.get("sheet_name", "unknown")
            test_name = result.get("test_name", "unknown")

            request_data = result.get("request", {})
            method = request_data.get("method", "GET")
            endpoint = request_data.get("endpoint", "")
            query_params = request_data.get("query_params", {})

            # PRIMARY MAPPING: sheet_name::test_name
            primary_key = f"{sheet_name}::{test_name}"
            if primary_key not in self.primary_mappings:
                self.primary_mappings[primary_key] = {
                    "sheet_name": sheet_name,
                    "test_name": test_name,
                    "steps": [],
                    "endpoints": {},
                    "test_metadata": {
                        "total_steps": 0,
                        "methods_used": set(),
                        "endpoints_used": set(),
                    },
                }

            # Add step to primary mapping
            self.primary_mappings[primary_key]["steps"].append(result)

            # Index by endpoint within test
            endpoint_key = f"{method}::{endpoint}"
            if (
                endpoint_key
                not in self.primary_mappings[primary_key]["endpoints"]
            ):
                self.primary_mappings[primary_key]["endpoints"][
                    endpoint_key
                ] = []
            self.primary_mappings[primary_key]["endpoints"][
                endpoint_key
            ].append(result)

            # Update metadata
            metadata = self.primary_mappings[primary_key]["test_metadata"]
            metadata["total_steps"] += 1
            metadata["methods_used"].add(method)
            metadata["endpoints_used"].add(endpoint)

            # SECONDARY MAPPINGS for backward compatibility and fallback
            secondary_keys = [
                f"{sheet_name}::{test_name}::{method}::{endpoint}",
                f"{sheet_name}::{method}::{endpoint}",
                f"{method}::{endpoint}",
                f"{method}::{endpoint}::{self.normalize_query_params(query_params)}",
            ]

            for key in secondary_keys:
                if key not in self.response_mappings:
                    self.response_mappings[key] = []
                self.response_mappings[key].append(result)

            # Sheet-specific index
            if sheet_name not in self.sheet_mappings:
                self.sheet_mappings[sheet_name] = []
            self.sheet_mappings[sheet_name].append(result)

            # Test-specific index
            test_key = f"{sheet_name}::{test_name}"
            if test_key not in self.test_mappings:
                self.test_mappings[test_key] = []
            self.test_mappings[test_key].append(result)

        # Convert sets to lists for JSON serialization
        for primary_key in self.primary_mappings:
            metadata = self.primary_mappings[primary_key]["test_metadata"]
            metadata["methods_used"] = list(metadata["methods_used"])
            metadata["endpoints_used"] = list(metadata["endpoints_used"])

        print(
            f"🎯 Primary mappings (sheet::test): {len(self.primary_mappings)}"
        )
        print(f"🔄 Secondary mappings: {len(self.response_mappings)}")
        print(f"📄 Sheet mappings: {len(self.sheet_mappings)}")
        print(f"🧪 Test mappings: {len(self.test_mappings)}")

    def normalize_query_params(self, params: Dict) -> str:
        """Normalize query parameters to a consistent string."""
        if not params:
            return ""
        sorted_params = sorted(params.items())
        return "&".join(f"{k}={v}" for k, v in sorted_params)

    def get_test_details(
        self, sheet_name: str, test_name: str
    ) -> Optional[Dict]:
        """Retrieve complete test details using sheet_name and test_name."""
        primary_key = f"{sheet_name}::{test_name}"
        return self.primary_mappings.get(primary_key)

    def get_test_by_name(self, test_name: str) -> Optional[Dict]:
        """Retrieve test details using just the test_name."""
        # Search through all primary mappings for matching test_name
        for primary_key, test_data in self.primary_mappings.items():
            if test_data["test_name"] == test_name:
                return test_data
        return None

    def get_all_tests_by_name(self, test_name: str) -> List[Dict]:
        """Retrieve all test details matching the test_name (in case of duplicates across sheets)."""
        matching_tests = []
        for primary_key, test_data in self.primary_mappings.items():
            if test_data["test_name"] == test_name:
                matching_tests.append(test_data)
        return matching_tests

    def find_best_response(
        self,
        method: str,
        endpoint: str,
        query_params: Dict = None,
        headers: Dict = None,
        target_sheet: str = None,
        target_test: str = None,
    ) -> Optional[Dict]:
        """Find the best matching response prioritizing sheet+test mapping."""

        query_params = query_params or {}
        headers = headers or {}

        # PRIMARY STRATEGY: Use sheet_name + test_name if available
        if target_sheet and target_test:
            test_details = self.get_test_details(target_sheet, target_test)
            if test_details:
                # Look for matching endpoint within this test
                endpoint_key = f"{method}::{endpoint}"
                endpoint_responses = test_details["endpoints"].get(
                    endpoint_key, []
                )

                if endpoint_responses:
                    # Return best match from this test's endpoints
                    return self.select_best_candidate(
                        endpoint_responses,
                        query_params,
                        headers,
                        target_sheet,
                        target_test,
                    )
                else:
                    # Return any response from this test as fallback
                    if test_details["steps"]:
                        print(
                            f"📋 Using fallback response from {target_sheet}::{target_test}"
                        )
                        return test_details["steps"][0]

        # ALTERNATIVE STRATEGY: Use just test_name if no sheet provided
        elif target_test:
            test_details = self.get_test_by_name(target_test)
            if test_details:
                # Look for matching endpoint within this test
                endpoint_key = f"{method}::{endpoint}"
                endpoint_responses = test_details["endpoints"].get(
                    endpoint_key, []
                )

                if endpoint_responses:
                    # Return best match from this test's endpoints
                    return self.select_best_candidate(
                        endpoint_responses,
                        query_params,
                        headers,
                        test_details["sheet_name"],
                        target_test,
                    )
                else:
                    # Return any response from this test as fallback
                    if test_details["steps"]:
                        sheet = test_details["sheet_name"]
                        print(
                            f"📋 Using fallback response from {sheet}::{target_test}"
                        )
                        return test_details["steps"][0]

        # SECONDARY STRATEGY: Use existing lookup mechanism
        lookup_keys = []

        if target_sheet and target_test:
            lookup_keys.append(
                f"{target_sheet}::{target_test}::{method}::{endpoint}"
            )

        if target_sheet:
            lookup_keys.append(f"{target_sheet}::{method}::{endpoint}")

        if query_params:
            query_str = self.normalize_query_params(query_params)
            lookup_keys.append(f"{method}::{endpoint}::{query_str}")

        lookup_keys.append(f"{method}::{endpoint}")

        # Try each lookup key
        for key in lookup_keys:
            if key in self.response_mappings:
                candidates = self.response_mappings[key]
                best_match = self.select_best_candidate(
                    candidates,
                    query_params,
                    headers,
                    target_sheet,
                    target_test,
                )
                if best_match:
                    return best_match

        return None

    def select_best_candidate(
        self,
        candidates: List[Dict],
        query_params: Dict,
        headers: Dict,
        target_sheet: str = None,
        target_test: str = None,
    ) -> Optional[Dict]:
        """Select the best candidate from multiple matches."""

        if not candidates:
            return None

        if len(candidates) == 1:
            return candidates[0]

        # Score candidates
        scored_candidates = []
        for candidate in candidates:
            score = 0

            # Prefer target sheet (highest priority)
            if target_sheet and candidate.get("sheet_name") == target_sheet:
                score += 100

            # Prefer target test (second highest priority)
            if target_test and candidate.get("test_name") == target_test:
                score += 50

            # Prefer matching query parameters
            candidate_query = candidate.get("request", {}).get(
                "query_params", {}
            )
            if query_params and candidate_query:
                matching_params = sum(
                    1
                    for k, v in query_params.items()
                    if candidate_query.get(k) == v
                )
                score += matching_params * 10

            # Prefer matching headers
            candidate_headers = candidate.get("request", {}).get("headers", {})
            if headers and candidate_headers:
                matching_headers = sum(
                    1
                    for k, v in headers.items()
                    if candidate_headers.get(k) == v
                )
                score += matching_headers * 5

            # Prefer PASS status
            if candidate.get("execution", {}).get("status") == "PASS":
                score += 20

            scored_candidates.append((score, candidate))

        # Return highest scoring candidate
        scored_candidates.sort(key=lambda x: x[0], reverse=True)
        return scored_candidates[0][1]

    def setup_routes(self):
        """Setup Flask routes."""

        @self.app.route("/health", methods=["GET"])
        def health_check():
            """Health check endpoint."""
            return jsonify(
                {
                    "status": "healthy",
                    "server": "Enhanced Mock Server",
                    "timestamp": datetime.now().isoformat(),
                    "primary_mappings": len(self.primary_mappings),
                    "secondary_mappings": len(self.response_mappings),
                    "sheets": len(self.sheet_mappings),
                    "tests": len(self.test_mappings),
                    "request_count": self.request_count,
                }
            )

        @self.app.route("/mock/sheets", methods=["GET"])
        def list_sheets():
            """List all available sheets."""
            return jsonify(
                {
                    "sheets": list(self.sheet_mappings.keys()),
                    "total": len(self.sheet_mappings),
                }
            )

        @self.app.route("/mock/tests", methods=["GET"])
        def list_tests():
            """List all available tests, optionally filtered by sheet."""
            sheet = request.args.get("sheet")
            if sheet:
                # Filter tests by sheet
                sheet_tests = {}
                for primary_key, test_data in self.primary_mappings.items():
                    if test_data["sheet_name"] == sheet:
                        sheet_tests[primary_key] = {
                            "sheet_name": test_data["sheet_name"],
                            "test_name": test_data["test_name"],
                            "metadata": test_data["test_metadata"],
                        }
                return jsonify(
                    {
                        "sheet": sheet,
                        "tests": sheet_tests,
                        "total": len(sheet_tests),
                    }
                )
            else:
                # Return all tests
                all_tests = {}
                for primary_key, test_data in self.primary_mappings.items():
                    all_tests[primary_key] = {
                        "sheet_name": test_data["sheet_name"],
                        "test_name": test_data["test_name"],
                        "metadata": test_data["test_metadata"],
                    }
                return jsonify(
                    {
                        "tests": all_tests,
                        "total": len(all_tests),
                    }
                )

        @self.app.route("/mock/test/<sheet_name>/<test_name>", methods=["GET"])
        def get_test_details_endpoint(sheet_name: str, test_name: str):
            """Get complete details for a specific test."""
            test_details = self.get_test_details(sheet_name, test_name)
            if test_details:
                return jsonify(test_details)
            else:
                return (
                    jsonify(
                        {"error": f"Test not found: {sheet_name}::{test_name}"}
                    ),
                    404,
                )

        @self.app.route(
            "/mock/test/<sheet_name>/<test_name>/steps", methods=["GET"]
        )
        def get_test_steps(sheet_name: str, test_name: str):
            """Get all steps for a specific test."""
            test_details = self.get_test_details(sheet_name, test_name)
            if test_details:
                return jsonify(
                    {
                        "sheet_name": sheet_name,
                        "test_name": test_name,
                        "steps": test_details["steps"],
                        "total_steps": len(test_details["steps"]),
                    }
                )
            else:
                return (
                    jsonify(
                        {"error": f"Test not found: {sheet_name}::{test_name}"}
                    ),
                    404,
                )

        @self.app.route("/mock/test/<test_name>", methods=["GET"])
        def get_test_by_name_endpoint(test_name: str):
            """Get test details using just the test name."""
            test_details = self.get_test_by_name(test_name)
            if test_details:
                return jsonify(test_details)
            else:
                return jsonify({"error": f"Test not found: {test_name}"}), 404

        @self.app.route("/mock/tests/<test_name>/all", methods=["GET"])
        def get_all_tests_by_name_endpoint(test_name: str):
            """Get all test details matching the test name (across all sheets)."""
            matching_tests = self.get_all_tests_by_name(test_name)
            if matching_tests:
                return jsonify(
                    {
                        "test_name": test_name,
                        "matching_tests": matching_tests,
                        "total_matches": len(matching_tests),
                    }
                )
            else:
                return (
                    jsonify(
                        {"error": f"No tests found with name: {test_name}"}
                    ),
                    404,
                )

        @self.app.route("/mock/mappings", methods=["GET"])
        def list_mappings():
            """List all response mappings."""
            return jsonify(
                {
                    "primary_mappings": list(self.primary_mappings.keys()),
                    "secondary_mappings": list(self.response_mappings.keys()),
                    "total_primary": len(self.primary_mappings),
                    "total_secondary": len(self.response_mappings),
                }
            )

        @self.app.route("/mock/kubectl/<kubectl_type>", methods=["GET"])
        def handle_kubectl_mock(kubectl_type):
            """Handle kubectl command mock requests."""
            return self.handle_kubectl_request(kubectl_type)

        @self.app.route(
            "/<path:path>", methods=["GET", "POST", "PUT", "DELETE", "PATCH"]
        )
        def handle_any_request(path):
            """Enhanced handler using structured data."""
            return self.handle_enhanced_request(path)

        @self.app.route("/", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
        def handle_root_request():
            """Handle requests to root path."""
            return self.handle_enhanced_request("")

    def handle_enhanced_request(self, path: str) -> Tuple[Any, int]:
        """Handle requests using enhanced structured data with primary mapping."""
        self.request_count += 1
        method = request.method

        # Build full endpoint path
        endpoint = f"/{path}" if path else "/"

        # Extract query parameters
        query_params = dict(request.args)

        # Extract headers
        headers = dict(request.headers)

        # Try to determine target sheet/test from headers or other context
        target_sheet = headers.get("X-Test-Sheet")
        target_test = headers.get("X-Test-Name")

        print(
            f"🔄 Enhanced Request #{self.request_count}: {method} {endpoint}"
        )
        if query_params:
            print(f"   📋 Query: {query_params}")
        if target_sheet:
            print(f"   📄 Target Sheet: {target_sheet}")
        if target_test:
            print(f"   🧪 Target Test: {target_test}")

        # Find best matching response using primary mapping strategy
        matching_response = self.find_best_response(
            method=method,
            endpoint=endpoint,
            query_params=query_params,
            headers=headers,
            target_sheet=target_sheet,
            target_test=target_test,
        )

        if matching_response:
            sheet = matching_response.get("sheet_name", "unknown")
            test = matching_response.get("test_name", "unknown")
            step = matching_response.get("step_number", 1)
            print(f"✅ Found match: {sheet}::{test} (step {step})")

            return self.format_enhanced_response(matching_response)
        else:
            print("🔧 No match found, generating generic response")
            return self.generate_generic_response(method, endpoint)

    def format_enhanced_response(self, response_data: Dict) -> Tuple[Any, int]:
        """Format response from enhanced data structure."""
        expected_response = response_data.get("expected_response", {})

        status_code = expected_response.get("status_code", 200)
        body = expected_response.get("body")

        if body is not None:
            if isinstance(body, (dict, list)):
                return jsonify(body), status_code
            else:
                # Return as plain text
                return str(body), status_code
        else:
            # Empty response
            return "", status_code

    def generate_generic_response(
        self, method: str, endpoint: str
    ) -> Tuple[Any, int]:
        """Generate a generic response for unmatched requests."""
        if method == "GET":
            return (
                jsonify(
                    {
                        "message": f"Enhanced mock response for GET {endpoint}",
                        "timestamp": datetime.now().isoformat(),
                        "available_sheets": list(self.sheet_mappings.keys())[
                            :5
                        ],
                        "primary_mappings": len(self.primary_mappings),
                    }
                ),
                200,
            )
        elif method in ["POST", "PUT"]:
            return "", 201
        elif method == "DELETE":
            return "", 204
        else:
            return jsonify({"error": f"Method {method} not implemented"}), 405

    def handle_kubectl_request(self, kubectl_type: str) -> Tuple[Any, int]:
        """Handle kubectl mock requests."""
        self.request_count += 1

        # Extract parameters
        sheet = request.args.get("sheet")
        test = request.args.get("test")
        pod_pattern = request.args.get("pod_pattern")
        namespace = request.args.get("namespace")
        resource_type = request.args.get("resource_type")
        resource_name = request.args.get("resource_name")

        print(
            f"🔄 kubectl Mock Request #{self.request_count}: {kubectl_type.upper()}"
        )
        if sheet:
            print(f"   📄 Sheet: {sheet}")
        if test:
            print(f"   🧪 Test: {test}")
        if pod_pattern:
            print(f"   🐳 Pod Pattern: {pod_pattern}")
        if namespace:
            print(f"   📦 Namespace: {namespace}")
        if resource_type:
            print(f"   🔧 Resource Type: {resource_type}")
        if resource_name:
            print(f"   📄 Resource Name: {resource_name}")

        # Find matching kubectl response in enhanced data
        matching_response = self.find_kubectl_response(
            kubectl_type=kubectl_type,
            sheet=sheet,
            test=test,
            pod_pattern=pod_pattern,
            namespace=namespace,
            resource_type=resource_type,
            resource_name=resource_name,
        )

        if matching_response:
            print(f"✅ Found kubectl match: {sheet}::{test}")
            return self.format_kubectl_response(matching_response)
        else:
            print("🔧 No kubectl match found, generating generic response")
            return self.generate_generic_kubectl_response(
                kubectl_type,
                namespace,
                pod_pattern,
                resource_type,
                resource_name,
            )

    def find_kubectl_response(
        self,
        kubectl_type: str,
        sheet: str = None,
        test: str = None,
        pod_pattern: str = None,
        namespace: str = None,
        resource_type: str = None,
        resource_name: str = None,
    ) -> Optional[Dict]:
        """Find matching kubectl response using primary mapping."""
        if not sheet or not test:
            return None

        # Use primary mapping to get test details
        test_details = self.get_test_details(sheet, test)
        if not test_details:
            return None

        # Look for kubectl responses in test steps
        for step in test_details["steps"]:
            request_data = step.get("request", {})
            execution = step.get("execution", {})

            # Check if this is a kubectl command
            if (
                request_data.get("method") == "KUBECTL"
                or "kubectl" in str(request_data.get("command", "")).lower()
            ):

                # Get the actual kubectl response from enhanced data
                kubectl_response = execution.get("response_body", "")

                if kubectl_response:
                    print(
                        "✅ Found actual kubectl response from enhanced data"
                    )
                    return {
                        "sheet_name": sheet,
                        "test_name": test,
                        "kubectl_type": kubectl_type,
                        "kubectl_response": kubectl_response,
                        "step_number": step.get("step_number"),
                        "original_command": request_data.get("command"),
                        "from_enhanced_data": True,
                    }

        # Generate mock kubectl data since no real data available
        print("🔧 No real kubectl data found, generating mock response")
        return {
            "sheet_name": sheet,
            "test_name": test,
            "kubectl_type": kubectl_type,
            "kubectl_response": self.generate_kubectl_mock_data(
                kubectl_type,
                namespace,
                pod_pattern,
                resource_type,
                resource_name,
            ),
            "resource_type": resource_type,
            "namespace": namespace,
            "pod_pattern": pod_pattern,
            "from_enhanced_data": False,
        }

    def generate_kubectl_mock_data(
        self,
        kubectl_type: str,
        namespace: str = None,
        pod_pattern: str = None,
        resource_type: str = None,
        resource_name: str = None,
    ) -> str:
        """Generate mock kubectl command output."""
        if kubectl_type == "logs":
            # Generate mock log entries
            return (
                '{"level":"INFO","loggerName":"com.oracle.ocslf",'
                '"message":"Mock log entry for testing",'
                '"timestamp":"2025-01-20T10:30:00.123Z"}\n'
                '{"level":"DEBUG","loggerName":"com.oracle.ocslf.service",'
                '"message":"Processing mock request",'
                '"timestamp":"2025-01-20T10:30:00.456Z"}\n'
                '{"level":"INFO","loggerName":"com.oracle.ocslf",'
                '"message":"Mock operation completed successfully",'
                '"timestamp":"2025-01-20T10:30:00.789Z"}'
            )

        elif kubectl_type == "get":
            if resource_type == "pods":
                # Generate mock pod list
                return (
                    "NAME                          READY   STATUS    RESTARTS   AGE\n"
                    "nudr-config-abc123-def456     1/1     Running   0          2d1h\n"
                    "appinfo-xyz789-mno345         1/1     Running   0          2d1h\n"
                    "slf-group-prov-qwe123-rty456  1/1     Running   0          2d1h"
                )
            elif resource_type == "services":
                return (
                    "NAME                TYPE        CLUSTER-IP      "
                    "EXTERNAL-IP   PORT(S)    AGE\n"
                    "kubernetes          ClusterIP   10.96.0.1       "
                    "<none>        443/TCP    30d\n"
                    "ocslf-service       ClusterIP   10.96.1.100     "
                    "<none>        8080/TCP   2d1h"
                )
            else:
                return (
                    f"NAME                          STATUS    AGE\n"
                    f"mock-{resource_type}-1        Active    2d1h\n"
                    f"mock-{resource_type}-2        Active    1d12h"
                )

        elif kubectl_type == "describe":
            # Generate mock describe output
            return (
                f"Name:         {resource_name or 'mock-pod-123'}\n"
                f"Namespace:    {namespace or 'default'}\n"
                f"Priority:     0\n"
                f"Node:         worker-node-1/10.0.1.100\n"
                f"Start Time:   Fri, 18 Jan 2025 08:30:00 +0000\n"
                f"Labels:       app=mock-app\n"
                f"              version=v1.0\n"
                f"Annotations:  kubernetes.io/created-by: mock-system\n"
                f"Status:       Running\n"
                f"IP:           10.244.1.100\n"
                f"Containers:\n"
                f"  mock-container:\n"
                f"    Container ID:   containerd://abc123def456\n"
                f"    Image:          mock-app:latest\n"
                f"    State:          Running\n"
                f"      Started:      Fri, 18 Jan 2025 08:30:15 +0000\n"
                f"    Ready:          True\n"
                f"    Restart Count:  0\n"
                f"Events:           <none>"
            )

        else:
            return f"Mock {kubectl_type} output for testing purposes"

    def format_kubectl_response(self, response_data: Dict) -> Tuple[str, int]:
        """Format kubectl response."""
        kubectl_output = response_data.get("kubectl_response", "")
        return kubectl_output, 200

    def generate_generic_kubectl_response(
        self,
        kubectl_type: str,
        namespace: str = None,
        pod_pattern: str = None,
        resource_type: str = None,
        resource_name: str = None,
    ) -> Tuple[str, int]:
        """Generate generic kubectl response when no match found."""
        mock_output = self.generate_kubectl_mock_data(
            kubectl_type, namespace, pod_pattern, resource_type, resource_name
        )
        return mock_output, 200

    def run(self, host: str = "0.0.0.0", debug: bool = False):
        """Start the enhanced mock server."""
        print(f"🚀 Starting Enhanced Mock Server on {host}:{self.port}")
        print(
            f"🎯 Primary mappings (sheet::test): {len(self.primary_mappings)}"
        )
        print(f"🔄 Secondary mappings: {len(self.response_mappings)}")
        print(f"📄 Available sheets: {len(self.sheet_mappings)}")
        print(f"🧪 Available tests: {len(self.test_mappings)}")
        print(f"🔗 Health check: http://{host}:{self.port}/health")
        print(f"📋 Sheets: http://{host}:{self.port}/mock/sheets")
        print(f"🧪 Tests: http://{host}:{self.port}/mock/tests")
        print(
            f"🔍 Test details: http://{host}:{self.port}/mock/test/<sheet>/<test>"
        )
        print(
            f"🎯 Test by name: http://{host}:{self.port}/mock/test/<test_name>"
        )
        print(
            f"🔍 All matching tests: http://{host}:{self.port}/mock/tests/<test_name>/all"
        )

        self.app.run(host=host, port=self.port, debug=debug)


def main():
    """CLI entry point for enhanced mock server."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Enhanced Mock Server for TestPilot"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8082,
        help="Port to run server on (default: 8082)",
    )
    parser.add_argument(
        "--host", default="0.0.0.0", help="Host to bind to (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--data-file",
        default="mock_data/enhanced_test_results_20250719_122220.json",
        help="Enhanced mock data file (default: enhanced_test_results.json)",
    )
    parser.add_argument(
        "--debug", action="store_true", help="Enable Flask debug mode"
    )

    args = parser.parse_args()

    # Create and start server
    server = EnhancedMockServer(
        enhanced_data_file=args.data_file, port=args.port
    )

    try:
        server.run(host=args.host, debug=args.debug)
    except KeyboardInterrupt:
        print("\n👋 Enhanced Mock Server stopped")


if __name__ == "__main__":
    main()
