#!/usr/bin/env python3
"""
Enhanced Mock Server for TestPilot
==================================

An advanced mock server that uses structured enhanced mock data with explicit
sheet names, test names, and organized endpoint information for precise mapping.

Features:
- Sheet-aware response mapping
- Test-aware step sequencing
- Query parameter matching
- Header-based response selection
- Fallback response strategies
- Enhanced debugging and introspection
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qs, urlparse

from flask import Flask, jsonify, request


class EnhancedMockServer:
    """
    Enhanced mock server using structured mock data with sheet/test metadata.

    Provides precise response mapping based on:
    - Sheet name and test name
    - Endpoint and method matching
    - Query parameter matching
    - Header-based selection
    - Step sequencing within tests
    """

    def __init__(
        self,
        enhanced_data_file: str = "mock_data/enhanced_test_results_20250719_122220.json",
        port: int = 8082,
    ):
        self.app = Flask(__name__)
        self.port = port
        self.enhanced_data = {}
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
                f"📊 Enhanced data version: {metadata.get('enhanced_version', 'unknown')}"
            )
            print(f"📊 Total test steps: {metadata.get('total_tests', 0)}")
            print(f"📊 Unique sheets: {metadata.get('unique_sheets', 0)}")
            print(f"📊 Unique tests: {metadata.get('unique_tests', 0)}")

            # Index responses for fast lookup
            self.index_responses(data.get("enhanced_results", []))

        except Exception as e:
            print(f"❌ Error loading enhanced data: {e}")
            self.enhanced_data = {}

    def index_responses(self, results: List[Dict]):
        """Create indices for fast response lookup."""
        self.response_mappings = {}
        self.sheet_mappings = {}
        self.test_mappings = {}

        for result in results:
            sheet_name = result.get("sheet_name", "unknown")
            test_name = result.get("test_name", "unknown")
            step_number = result.get("step_number", 1)

            request_data = result.get("request", {})
            method = request_data.get("method", "GET")
            endpoint = request_data.get("endpoint", "")
            query_params = request_data.get("query_params", {})
            headers = request_data.get("headers", {})

            # Create multiple indexing keys for flexible lookup
            keys = [
                # Exact match with sheet and test
                f"{sheet_name}::{test_name}::{method}::{endpoint}",
                # Sheet + method + endpoint
                f"{sheet_name}::{method}::{endpoint}",
                # Just method + endpoint (fallback)
                f"{method}::{endpoint}",
                # With query parameters
                f"{method}::{endpoint}::{self.normalize_query_params(query_params)}",
            ]

            # Store in all indices
            for key in keys:
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

        print(f"🎯 Indexed {len(self.response_mappings)} response mappings")
        print(f"📄 Indexed {len(self.sheet_mappings)} sheets")
        print(f"🧪 Indexed {len(self.test_mappings)} tests")

    def normalize_query_params(self, params: Dict) -> str:
        """Normalize query parameters to a consistent string."""
        if not params:
            return ""
        sorted_params = sorted(params.items())
        return "&".join(f"{k}={v}" for k, v in sorted_params)

    def find_best_response(
        self,
        method: str,
        endpoint: str,
        query_params: Dict = None,
        headers: Dict = None,
        target_sheet: str = None,
        target_test: str = None,
    ) -> Optional[Dict]:
        """Find the best matching response using enhanced data."""

        query_params = query_params or {}
        headers = headers or {}

        # Build lookup keys in order of preference
        lookup_keys = []

        # 1. Exact match with target sheet and test
        if target_sheet and target_test:
            lookup_keys.append(
                f"{target_sheet}::{target_test}::{method}::{endpoint}"
            )

        # 2. Sheet-specific match
        if target_sheet:
            lookup_keys.append(f"{target_sheet}::{method}::{endpoint}")

        # 3. Method + endpoint + query params
        if query_params:
            query_str = self.normalize_query_params(query_params)
            lookup_keys.append(f"{method}::{endpoint}::{query_str}")

        # 4. Just method + endpoint
        lookup_keys.append(f"{method}::{endpoint}")

        # Try each lookup key
        for key in lookup_keys:
            if key in self.response_mappings:
                candidates = self.response_mappings[key]

                # If multiple candidates, apply additional filtering
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

            # Prefer target sheet
            if target_sheet and candidate.get("sheet_name") == target_sheet:
                score += 100

            # Prefer target test
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
                    "loaded_responses": len(self.response_mappings),
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
            """List all available tests."""
            sheet = request.args.get("sheet")
            if sheet and sheet in self.sheet_mappings:
                tests = set(r["test_name"] for r in self.sheet_mappings[sheet])
                return jsonify(
                    {"sheet": sheet, "tests": list(tests), "total": len(tests)}
                )
            else:
                return jsonify(
                    {
                        "tests": list(self.test_mappings.keys()),
                        "total": len(self.test_mappings),
                    }
                )

        @self.app.route("/mock/mappings", methods=["GET"])
        def list_mappings():
            """List all response mappings."""
            return jsonify(
                {
                    "mappings": list(self.response_mappings.keys()),
                    "total": len(self.response_mappings),
                }
            )

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
        """Handle requests using enhanced structured data."""
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

        # Find best matching response
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
            print(f"🔧 No match found, generating generic response")
            return self.generate_generic_response(method, endpoint)

    def format_enhanced_response(self, response_data: Dict) -> Tuple[Any, int]:
        """Format response from enhanced data structure."""
        expected_response = response_data.get("expected_response", {})

        status_code = expected_response.get("status_code", 200)
        body = expected_response.get("body")
        response_headers = expected_response.get("headers", {})

        if body is not None:
            if isinstance(body, dict) or isinstance(body, list):
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

    def run(self, host: str = "0.0.0.0", debug: bool = False):
        """Start the enhanced mock server."""
        print(f"🚀 Starting Enhanced Mock Server on {host}:{self.port}")
        print(f"📊 Loaded {len(self.response_mappings)} response mappings")
        print(f"📄 Available sheets: {len(self.sheet_mappings)}")
        print(f"🧪 Available tests: {len(self.test_mappings)}")
        print(f"🔗 Health check: http://{host}:{self.port}/health")
        print(f"📋 Sheets: http://{host}:{self.port}/mock/sheets")
        print(f"🧪 Tests: http://{host}:{self.port}/mock/tests")

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
        help="Enhanced mock data file (default: enhanced_test_results_20250719_122220.json)",
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
