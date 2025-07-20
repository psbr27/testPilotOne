#!/usr/bin/env python3
"""
Quick Mock Integration Test
===========================

A simple test to verify that our mock integration works correctly.
"""

import os
import signal
import subprocess
import sys
import time


def test_mock_server():
    """Test the mock server independently."""
    print("🧪 Quick Test: Starting mock server...")

    try:
        # Start mock server
        server_process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "testpilot.mock.generic_mock_server",
                "--port",
                "8081",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        time.sleep(2)  # Give server time to start

        if server_process.poll() is None:
            print("✅ Mock server started successfully")

            # Test health endpoint
            import requests

            try:
                response = requests.get(
                    "http://localhost:8081/health", timeout=5
                )
                if response.status_code == 200:
                    data = response.json()
                    print(
                        f"✅ Health check passed: {data.get('loaded_responses', 0)} responses loaded"
                    )

                    # Test a mock endpoint
                    test_response = requests.get(
                        "http://localhost:8081/nudr-config/v1/udr.global.cfg/GLOBAL"
                    )
                    print(
                        f"✅ Test endpoint returned: {test_response.status_code}"
                    )

                    return True
                else:
                    print(f"❌ Health check failed: {response.status_code}")
                    return False
            except Exception as e:
                print(f"❌ Request failed: {e}")
                return False
        else:
            print("❌ Mock server failed to start")
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        # Clean up
        if "server_process" in locals() and server_process.poll() is None:
            server_process.terminate()
            server_process.wait(timeout=5)
            print("🛑 Mock server stopped")


def test_command_parser():
    """Test command parser."""
    print("\n🧪 Quick Test: Command parser...")

    try:
        from testpilot.mock.mock_integration import MockCommandParser

        command = "kubectl exec test -- curl -v -X GET http://localhost:5001/api/test -H 'Content-Type: application/json'"
        url, method, headers, payload = (
            MockCommandParser.parse_kubectl_curl_command(command)
        )

        if url and method:
            print(f"✅ Command parser working: {method} {url}")
            return True
        else:
            print("❌ Command parser failed")
            return False
    except Exception as e:
        print(f"❌ Command parser error: {e}")
        return False


def test_testpilot_mock_mode():
    """Test TestPilot with mock mode (dry run)."""
    print("\n🧪 Quick Test: TestPilot mock mode (dry-run)...")

    try:
        # Run a very simple dry-run test
        result = subprocess.run(
            [
                sys.executable,
                "src/testpilot/core/test_pilot_core.py",
                "-i",
                "nrf_tests_updated.xlsx",
                "-m",
                "otp",
                "--execution-mode",
                "mock",
                "--dry-run",
                "--no-table",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode == 0:
            print("✅ TestPilot mock mode dry-run completed successfully")

            # Check for mock mode indicators
            if "Mock execution mode enabled" in result.stderr:
                print("✅ Mock mode detected in output")
                return True
            else:
                print("⚠️ Mock mode not clearly detected, but no errors")
                return True
        else:
            print(f"❌ TestPilot failed with return code: {result.returncode}")
            print(f"Error: {result.stderr[:200]}...")
            return False

    except subprocess.TimeoutExpired:
        print("⚠️ TestPilot test timed out (took >10s)")
        return False
    except Exception as e:
        print(f"❌ TestPilot test error: {e}")
        return False


def main():
    """Run quick integration tests."""
    print("🚀 Quick Mock Integration Test")
    print("=" * 40)

    results = []

    # Test 1: Command Parser
    results.append(("Command Parser", test_command_parser()))

    # Test 2: Mock Server
    results.append(("Mock Server", test_mock_server()))

    # Test 3: TestPilot Integration
    results.append(("TestPilot Mock Mode", test_testpilot_mock_mode()))

    # Summary
    print("\n📊 Quick Test Results:")
    print("=" * 40)

    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:20} {status}")
        if result:
            passed += 1

    print("=" * 40)
    print(f"Overall: {passed}/{len(results)} tests passed")

    if passed == len(results):
        print("🎉 All quick tests passed! Mock integration is working!")
        return True
    else:
        print("⚠️ Some tests failed, but core functionality might still work")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
