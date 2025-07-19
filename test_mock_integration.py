#!/usr/bin/env python3
"""
Test Mock Integration
====================

Test script to validate that the mock integration works end-to-end.
Tests the complete flow: CLI → Mock Server → Response Formatting → Validation

Usage:
    python3 test_mock_integration.py
"""

import subprocess
import sys
import time
from pathlib import Path


def start_mock_server():
    """Start the mock server in background."""
    print("🚀 Starting mock server...")

    try:
        # Start mock server in background
        process = subprocess.Popen(
            [
                sys.executable,
                "generic_mock_server.py",
                "--port",
                "8081",
                "--data-file",
                "mock_data/test_results_20250719_122220.json",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        # Give server time to start
        time.sleep(3)

        # Check if server started successfully
        if process.poll() is None:
            print(f"✅ Mock server started (PID: {process.pid})")
            return process
        else:
            stdout, stderr = process.communicate()
            print(f"❌ Mock server failed to start:")
            print(f"   stdout: {stdout.decode()}")
            print(f"   stderr: {stderr.decode()}")
            return None

    except Exception as e:
        print(f"❌ Error starting mock server: {e}")
        return None


def test_mock_server():
    """Test if mock server is responding."""
    try:
        import requests

        response = requests.get("http://localhost:8081/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Mock server health check passed")
            print(f"   📊 Loaded {data.get('loaded_responses', 0)} responses")
            print(f"   🔄 Request count: {data.get('request_count', 0)}")
            return True
        else:
            print(
                f"❌ Mock server health check failed: {response.status_code}"
            )
            return False
    except Exception as e:
        print(f"❌ Error testing mock server: {e}")
        return False


def test_command_parser():
    """Test the command parser independently."""
    print("\n🧪 Testing command parser...")

    try:
        from mock_integration import MockCommandParser

        # Sample command from your real data
        command = "kubectl get po -n ocnrfslf | awk '{print $1}' | grep -E 'nudr-config-[a-z0-9]+-[a-z0-9]+$' | head -n 1 | xargs -I{} kubectl exec -it {} -n ocnrfslf -c nudr-config -- curl -v --http2-prior-knowledge -X GET http://localhost:5001/nudr-config/v1/udr.global.cfg/GLOBAL -H 'Content-Type: application/json'"

        url, method, headers, payload = (
            MockCommandParser.parse_kubectl_curl_command(command)
        )

        if url and method:
            print(f"✅ Command parser working")
            print(f"   🎯 Method: {method}")
            print(f"   🔗 URL: {url}")
            print(f"   📋 Headers: {headers}")
            endpoint = MockCommandParser.extract_endpoint_from_url(url)
            print(f"   📍 Endpoint: {endpoint}")
            return True
        else:
            print(f"❌ Command parser failed to extract details")
            return False

    except Exception as e:
        print(f"❌ Error testing command parser: {e}")
        return False


def test_mock_request():
    """Test making a request through the mock executor."""
    print("\n🔄 Testing mock request execution...")

    try:
        from mock_integration import MockExecutor

        executor = MockExecutor("http://localhost:8081")

        # Test command
        command = "kubectl exec test-pod -- curl -v -X GET http://localhost:5001/nudr-config/v1/udr.global.cfg/GLOBAL -H 'Content-Type: application/json'"

        output, error, duration = executor.execute_mock_command(
            command, "test-host"
        )

        print(f"✅ Mock request executed")
        print(f"   ⏱️  Duration: {duration:.3f}s")
        print(f"   📤 Output length: {len(output)} chars")
        print(f"   📥 Error length: {len(error)} chars")

        if output or error:
            print(f"   📋 Has response data: ✅")
            return True
        else:
            print(f"   📋 No response data: ❌")
            return False

    except Exception as e:
        print(f"❌ Error testing mock request: {e}")
        return False


def test_with_testpilot():
    """Test integration with TestPilot CLI."""
    print("\n🎯 Testing TestPilot integration...")

    # Check if we have an Excel file to test with
    excel_files = list(Path(".").glob("*.xlsx"))
    if not excel_files:
        print("⚠️  No Excel files found for testing")
        return False

    excel_file = excel_files[0]
    print(f"📊 Using Excel file: {excel_file}")

    try:
        # Run TestPilot in mock mode with dry-run first
        cmd = [
            sys.executable,
            "test_pilot.py",
            "-i",
            str(excel_file),
            "-m",
            "otp",
            "--execution-mode",
            "mock",
            "--dry-run",
            "--log-level",
            "DEBUG",
        ]

        print(f"🧪 Running: {' '.join(cmd)}")

        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=30
        )

        if result.returncode == 0:
            print(f"✅ TestPilot mock integration working")
            print(f"   📤 Stdout: {len(result.stdout)} chars")
            print(f"   📥 Stderr: {len(result.stderr)} chars")

            # Check for mock mode indicators in output
            if (
                "Mock execution mode enabled" in result.stderr
                or "MOCK mode" in result.stderr
            ):
                print(f"   🎭 Mock mode detected in output: ✅")
                return True
            else:
                print(f"   🎭 Mock mode not detected in output: ⚠️")
                print(f"   First 500 chars of stderr: {result.stderr[:500]}")
                return False
        else:
            print(f"❌ TestPilot failed with return code: {result.returncode}")
            print(f"   Error: {result.stderr[:500]}")
            return False

    except subprocess.TimeoutExpired:
        print("❌ TestPilot test timed out")
        return False
    except Exception as e:
        print(f"❌ Error testing TestPilot integration: {e}")
        return False


def cleanup_mock_server(process):
    """Stop the mock server."""
    if process and process.poll() is None:
        print("\n🛑 Stopping mock server...")
        process.terminate()
        try:
            process.wait(timeout=5)
            print("✅ Mock server stopped")
        except subprocess.TimeoutExpired:
            print("⚠️  Force killing mock server...")
            process.kill()
            process.wait()


def main():
    """Run all integration tests."""
    print("🧪 TestPilot Mock Integration Test")
    print("=" * 50)

    # Check dependencies
    try:
        import flask
        import requests
    except ImportError as e:
        print(f"❌ Missing dependencies: {e}")
        print("📦 Please install: pip install requests flask")
        return False

    results = []
    mock_server_process = None

    try:
        # Test 1: Command Parser (doesn't need server)
        results.append(("Command Parser", test_command_parser()))

        # Test 2: Start Mock Server
        mock_server_process = start_mock_server()
        if mock_server_process:
            results.append(("Mock Server Start", True))

            # Test 3: Server Health Check
            results.append(("Mock Server Health", test_mock_server()))

            # Test 4: Mock Request Execution
            results.append(("Mock Request", test_mock_request()))

            # Test 5: TestPilot Integration
            results.append(("TestPilot Integration", test_with_testpilot()))
        else:
            results.append(("Mock Server Start", False))

    finally:
        # Cleanup
        if mock_server_process:
            cleanup_mock_server(mock_server_process)

    # Print results
    print("\n📊 Test Results:")
    print("=" * 50)

    passed = 0
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:25} {status}")
        if result:
            passed += 1

    print("=" * 50)
    print(f"📈 Overall: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! Mock integration is working!")
        return True
    else:
        print("⚠️  Some tests failed. Check the output above.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
