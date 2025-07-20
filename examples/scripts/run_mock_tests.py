#!/usr/bin/env python3
"""
Mock Test Runner
================

Convenient script to run mock tests against Excel test scenarios.
Can start mock server automatically and execute tests.
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path

import requests


def check_server_health(server_url: str, timeout: int = 30) -> bool:
    """Check if mock server is running and healthy."""
    health_url = f"{server_url.rstrip('/')}/health"

    for _ in range(timeout):
        try:
            response = requests.get(health_url, timeout=2)
            if response.status_code == 200:
                return True
        except requests.RequestException:
            pass
        time.sleep(1)

    return False


def start_mock_server(
    port: int = 8081, payloads_dir: str = "test_payloads"
) -> subprocess.Popen:
    """Start the mock server in background."""
    cmd = [
        sys.executable,
        "-m",
        "testpilot.mock.enhanced_mock_server",
        "--port",
        str(port),
        "--payloads-dir",
        payloads_dir,
        "--host",
        "0.0.0.0",
    ]

    print(f"🚀 Starting mock server on port {port}...")
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
    )

    return process


def run_tests(excel_file: str, **kwargs) -> int:
    """Run mock tests using test executor."""
    cmd = [sys.executable, "-m", "testpilot.core.test_pilot_core"]

    # Add required arguments
    cmd.extend(["--excel", excel_file])

    # Add optional arguments
    for key, value in kwargs.items():
        if value is not None:
            if isinstance(value, bool):
                if value:  # Only add flag if True
                    cmd.append(f"--{key.replace('_', '-')}")
            else:
                cmd.extend([f"--{key.replace('_', '-')}", str(value)])

    print(f"🧪 Running tests: {' '.join(cmd)}")
    return subprocess.call(cmd)


def main():
    parser = argparse.ArgumentParser(
        description="Run mock tests with automatic server management"
    )

    # Test configuration
    parser.add_argument(
        "--excel", required=True, help="Path to Excel file with test scenarios"
    )
    parser.add_argument(
        "--sheet", help="Specific sheet to test (default: all sheets)"
    )
    parser.add_argument(
        "--test", help="Specific test name to run (default: all tests)"
    )

    # Server configuration
    parser.add_argument(
        "--port",
        type=int,
        default=8081,
        help="Port for mock server (default: 8081)",
    )
    parser.add_argument(
        "--payloads-dir",
        default="test_payloads",
        help="Directory with test payload files",
    )
    parser.add_argument(
        "--external-server",
        help="Use external server URL instead of starting local server",
    )

    # Execution options
    parser.add_argument(
        "--no-server",
        action="store_true",
        help="Don't start mock server (assume it's already running)",
    )
    parser.add_argument(
        "--keep-server",
        action="store_true",
        help="Keep server running after tests complete",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset mock server state before running tests",
    )

    args = parser.parse_args()

    # Determine server URL
    if args.external_server:
        server_url = args.external_server
        server_process = None
    else:
        server_url = f"http://localhost:{args.port}"
        server_process = None

    try:
        # Start server if needed
        if not args.no_server and not args.external_server:
            server_process = start_mock_server(args.port, args.payloads_dir)

            # Wait for server to be ready
            if not check_server_health(server_url):
                print("❌ Mock server failed to start or become healthy")
                return 1

            print("✅ Mock server is ready")

        # Check server is accessible
        elif not check_server_health(server_url, timeout=5):
            print(f"❌ Cannot reach server at {server_url}")
            print(
                "   Make sure the server is running or use --external-server"
            )
            return 1

        # Run tests
        test_kwargs = {
            "server": server_url,
            "sheet": args.sheet,
            "test": args.test,
            "payloads_dir": args.payloads_dir,
        }

        # Add reset flag only if True
        if args.reset:
            test_kwargs["reset"] = True

        # Remove None values
        test_kwargs = {k: v for k, v in test_kwargs.items() if v is not None}

        exit_code = run_tests(args.excel, **test_kwargs)

        if exit_code == 0:
            print("🎉 All tests completed successfully!")
        else:
            print(f"❌ Tests failed with exit code {exit_code}")

        return exit_code

    except KeyboardInterrupt:
        print("\n⚠️  Tests interrupted by user")
        return 130

    except Exception as e:
        print(f"💥 Error running tests: {e}")
        return 1

    finally:
        # Stop server if we started it
        if server_process and not args.keep_server:
            print("🛑 Stopping mock server...")
            server_process.terminate()
            try:
                server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server_process.kill()
                server_process.wait()
            print("✅ Mock server stopped")
        elif server_process and args.keep_server:
            print(f"🔄 Mock server still running on {server_url}")
            print("   Stop manually or use Ctrl+C")


if __name__ == "__main__":
    sys.exit(main())
