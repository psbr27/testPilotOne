"""
Mock NRF Server for Testing
===========================

Flask-based mock server that simulates NRF API endpoints:
- /nnrf-nfm/v1/nf-instances/ (PUT, GET, DELETE)
- Stateful behavior for registration/discovery scenarios
- Configurable responses based on test payloads
"""

import argparse
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from flask import Flask, Response, jsonify, request


class NRFMockServer:
    """
    Mock NRF server with stateful CRUD operations.

    Maintains an in-memory registry of NF instances and provides
    realistic responses for testing scenarios.
    """

    def __init__(self, payloads_dir: str = "test_payloads", port: int = 8081):
        self.app = Flask(__name__)
        self.port = port
        self.payloads_dir = Path(payloads_dir)

        # In-memory data store
        self.nf_registry: Dict[str, Dict] = {}
        self.response_payloads: Dict[str, Dict] = {}

        # Load test payloads
        self.load_response_payloads()

        # Setup routes
        self.setup_routes()

    def load_response_payloads(self):
        """Load all JSON payload files for responses."""
        if not self.payloads_dir.exists():
            print(f"Warning: Payloads directory {self.payloads_dir} not found")
            return

        for json_file in self.payloads_dir.glob("*.json"):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    payload_data = json.load(f)
                self.response_payloads[json_file.name] = payload_data
                print(f"Loaded payload: {json_file.name}")
            except Exception as e:
                print(f"Error loading {json_file.name}: {e}")

    def setup_routes(self):
        """Setup Flask routes for NRF API endpoints."""

        @self.app.route("/health", methods=["GET"])
        def health_check():
            """Health check endpoint."""
            return jsonify(
                {
                    "status": "healthy",
                    "server": "NRF Mock Server",
                    "timestamp": datetime.now().isoformat(),
                    "registered_nfs": len(self.nf_registry),
                }
            )

        @self.app.route("/nnrf-nfm/v1/nf-instances/", methods=["PUT"])
        def register_nf_instance():
            """Register a new NF instance."""
            return self.handle_nf_registration()

        @self.app.route("/nnrf-nfm/v1/nf-instances/", methods=["GET"])
        def get_nf_instances():
            """Get all or filtered NF instances."""
            return self.handle_nf_discovery()

        @self.app.route("/nnrf-nfm/v1/nf-instances/", methods=["DELETE"])
        def delete_nf_instance():
            """Delete an NF instance."""
            return self.handle_nf_deletion()

        @self.app.route("/mock/payload/<filename>", methods=["GET"])
        def get_test_payload(filename):
            """Get a specific test payload for debugging."""
            if filename in self.response_payloads:
                return jsonify(self.response_payloads[filename])
            return jsonify({"error": "Payload not found"}), 404

        @self.app.route("/mock/registry", methods=["GET"])
        def get_registry_state():
            """Get current registry state for debugging."""
            return jsonify(
                {"registry": self.nf_registry, "count": len(self.nf_registry)}
            )

        @self.app.route("/mock/reset", methods=["POST"])
        def reset_registry():
            """Reset the registry state."""
            self.nf_registry.clear()
            return jsonify({"message": "Registry reset", "count": 0})

    def handle_nf_registration(self) -> Response:
        """
        Handle NF instance registration (PUT).

        Returns appropriate status codes based on request:
        - 201: Successful registration
        - 400: Bad request (validation errors)
        - 409: Conflict (duplicate registration)
        """
        try:
            # Get request payload
            payload = request.get_json()
            if not payload:
                return self.error_response(400, "Missing request payload")

            # Generate or extract NF instance ID
            nf_instance_id = payload.get("nfInstanceId", str(uuid.uuid4()))

            # Check for duplicate registration
            if nf_instance_id in self.nf_registry:
                # Update existing registration
                self.nf_registry[nf_instance_id].update(payload)
                self.nf_registry[nf_instance_id][
                    "lastUpdated"
                ] = datetime.now().isoformat()
                return jsonify(self.nf_registry[nf_instance_id]), 200

            # Register new NF instance
            nf_data = {
                **payload,
                "nfInstanceId": nf_instance_id,
                "nfStatus": "REGISTERED",
                "registeredAt": datetime.now().isoformat(),
                "lastUpdated": datetime.now().isoformat(),
            }

            self.nf_registry[nf_instance_id] = nf_data

            # Return success response
            return jsonify(nf_data), 201

        except Exception as e:
            return self.error_response(500, f"Internal server error: {str(e)}")

    def handle_nf_discovery(self) -> Response:
        """
        Handle NF instance discovery (GET).

        Returns registered NF instances, potentially filtered.
        Can return specific test payloads based on context.
        """
        try:
            # Check if we should return a specific test payload
            test_context = request.headers.get("X-Test-Context", "")

            if test_context and test_context in self.response_payloads:
                # Return specific test payload
                return jsonify(self.response_payloads[test_context])

            # Return current registry state
            if not self.nf_registry:
                return jsonify({"nfInstances": []}), 200

            # Build response with all registered instances
            response_data = {
                "nfInstances": list(self.nf_registry.values()),
                "totalCount": len(self.nf_registry),
            }

            return jsonify(response_data), 200

        except Exception as e:
            return self.error_response(500, f"Internal server error: {str(e)}")

    def handle_nf_deletion(self) -> Response:
        """
        Handle NF instance deletion (DELETE).

        Returns appropriate status codes:
        - 204: Successful deletion
        - 404: NF instance not found
        """
        try:
            # Extract NF instance ID from query params or path
            nf_instance_id = request.args.get("nfInstanceId")

            if not nf_instance_id:
                # If no specific ID, check if we're deleting all
                if request.args.get("deleteAll") == "true":
                    self.nf_registry.clear()
                    return "", 204
                return self.error_response(
                    400, "Missing nfInstanceId parameter"
                )

            # Delete specific instance
            if nf_instance_id in self.nf_registry:
                del self.nf_registry[nf_instance_id]
                return "", 204
            else:
                # Return 404 for non-existent instance (or test payload)
                if "reg_02_payload_02.json" in self.response_payloads:
                    return (
                        jsonify(
                            self.response_payloads["reg_02_payload_02.json"]
                        ),
                        404,
                    )
                return self.error_response(404, "NF instance not found")

        except Exception as e:
            return self.error_response(500, f"Internal server error: {str(e)}")

    def error_response(self, status_code: int, detail: str) -> Response:
        """
        Generate standardized error response.

        Args:
            status_code: HTTP status code
            detail: Error detail message

        Returns:
            JSON error response
        """
        error_data = {
            "title": self.get_error_title(status_code),
            "status": status_code,
            "detail": detail,
            "timestamp": datetime.now().isoformat(),
        }

        return jsonify(error_data), status_code

    def get_error_title(self, status_code: int) -> str:
        """Get error title for status code."""
        titles = {
            400: "Bad Request",
            401: "Unauthorized",
            404: "Not Found",
            409: "Conflict",
            500: "Internal Server Error",
        }
        return titles.get(status_code, "Error")

    def run(self, debug: bool = True, host: str = "0.0.0.0"):
        """Start the mock server."""
        print(f"🚀 Starting NRF Mock Server on {host}:{self.port}")
        print(f"📁 Payloads directory: {self.payloads_dir}")
        print(f"📦 Loaded {len(self.response_payloads)} test payloads")
        print("\n🔗 Available endpoints:")
        print(
            f"  - PUT/GET/DELETE: http://{host}:{self.port}/nnrf-nfm/v1/nf-instances/"
        )
        print(f"  - Health check: http://{host}:{self.port}/health")
        print(f"  - Registry state: http://{host}:{self.port}/mock/registry")
        print(f"  - Reset registry: POST http://{host}:{self.port}/mock/reset")
        print(
            "\n💡 Use X-Test-Context header to return specific test payloads"
        )

        self.app.run(host=host, port=self.port, debug=debug)


def main():
    """CLI entry point for mock server."""
    parser = argparse.ArgumentParser(description="NRF Mock Server for Testing")
    parser.add_argument(
        "--port",
        type=int,
        default=8081,
        help="Port to run server on (default: 8081)",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Host to bind to (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--payloads-dir",
        type=str,
        default="test_payloads",
        help="Directory containing test payload JSON files",
    )
    parser.add_argument(
        "--debug", action="store_true", help="Run in debug mode"
    )

    args = parser.parse_args()

    # Create and start server
    server = NRFMockServer(payloads_dir=args.payloads_dir, port=args.port)

    try:
        server.run(debug=args.debug, host=args.host)
    except KeyboardInterrupt:
        print("\n👋 Mock server stopped")


if __name__ == "__main__":
    main()
