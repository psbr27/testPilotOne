#!/usr/bin/env python3
"""
Basic Audit Tests - Dependency-Free Core Tests

Tests basic audit functionality without requiring heavy dependencies.
Focuses on core validation logic and essential functionality.
"""

import json
import os
import sys
import unittest
from datetime import datetime
from unittest.mock import Mock, patch

# Add project root to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

try:
    # Try to import audit modules with dependency checking
    from src.testpilot.audit.audit_engine import AuditEngine

    AUDIT_ENGINE_AVAILABLE = True
except ImportError as e:
    print(f"Warning: AuditEngine not available: {e}")
    AUDIT_ENGINE_AVAILABLE = False

try:
    from src.testpilot.audit.audit_exporter import AuditExporter

    AUDIT_EXPORTER_AVAILABLE = True
except ImportError as e:
    print(f"Warning: AuditExporter not available: {e}")
    AUDIT_EXPORTER_AVAILABLE = False


class TestBasicAuditFunctionality(unittest.TestCase):
    """Basic audit functionality tests without heavy dependencies"""

    def setUp(self):
        """Set up basic test fixtures"""
        if AUDIT_ENGINE_AVAILABLE:
            self.audit_engine = AuditEngine()

        self.simple_json_pattern = '{"status": "success", "id": 123}'
        self.simple_json_response = '{"status": "success", "id": 123}'
        self.different_json_response = '{"status": "error", "id": 456}'

    def tearDown(self):
        """Clean up after tests"""
        if AUDIT_ENGINE_AVAILABLE and hasattr(self, "audit_engine"):
            self.audit_engine.clear_results()

    @unittest.skipUnless(AUDIT_ENGINE_AVAILABLE, "AuditEngine not available")
    def test_audit_engine_initialization(self):
        """Test that AuditEngine can be initialized"""
        engine = AuditEngine()
        self.assertIsNotNone(engine)
        self.assertEqual(len(engine.get_audit_results()), 0)

    @unittest.skipUnless(AUDIT_ENGINE_AVAILABLE, "AuditEngine not available")
    def test_perfect_json_match(self):
        """Test perfect JSON pattern match"""
        result = self.audit_engine.validate_response(
            test_name="basic_perfect_match",
            expected_pattern=self.simple_json_pattern,
            actual_response=self.simple_json_response,
            http_method_expected="GET",
            http_method_actual="GET",
            status_code_expected=200,
            status_code_actual=200,
        )

        self.assertEqual(result["overall_result"], "PASS")
        self.assertEqual(result["test_name"], "basic_perfect_match")
        self.assertEqual(len(result["differences"]), 0)
        self.assertEqual(len(result["http_validation_errors"]), 0)

    @unittest.skipUnless(AUDIT_ENGINE_AVAILABLE, "AuditEngine not available")
    def test_json_pattern_mismatch(self):
        """Test JSON pattern mismatch detection"""
        result = self.audit_engine.validate_response(
            test_name="basic_pattern_mismatch",
            expected_pattern=self.simple_json_pattern,
            actual_response=self.different_json_response,
            http_method_expected="GET",
            http_method_actual="GET",
            status_code_expected=200,
            status_code_actual=200,
        )

        self.assertEqual(result["overall_result"], "FAIL")
        self.assertGreater(len(result["differences"]), 0)

    @unittest.skipUnless(AUDIT_ENGINE_AVAILABLE, "AuditEngine not available")
    def test_http_method_validation(self):
        """Test HTTP method validation"""
        result = self.audit_engine.validate_response(
            test_name="http_method_test",
            expected_pattern=self.simple_json_pattern,
            actual_response=self.simple_json_response,
            http_method_expected="GET",
            http_method_actual="POST",
            status_code_expected=200,
            status_code_actual=200,
        )

        self.assertEqual(result["overall_result"], "FAIL")
        self.assertGreater(len(result["http_validation_errors"]), 0)
        self.assertIn(
            "HTTP method mismatch", result["http_validation_errors"][0]
        )

    @unittest.skipUnless(AUDIT_ENGINE_AVAILABLE, "AuditEngine not available")
    def test_status_code_validation(self):
        """Test HTTP status code validation"""
        result = self.audit_engine.validate_response(
            test_name="status_code_test",
            expected_pattern=self.simple_json_pattern,
            actual_response=self.simple_json_response,
            http_method_expected="GET",
            http_method_actual="GET",
            status_code_expected=200,
            status_code_actual=404,
        )

        self.assertEqual(result["overall_result"], "FAIL")
        self.assertGreater(len(result["http_validation_errors"]), 0)
        self.assertIn(
            "Status code mismatch", result["http_validation_errors"][0]
        )

    @unittest.skipUnless(AUDIT_ENGINE_AVAILABLE, "AuditEngine not available")
    def test_audit_summary_generation(self):
        """Test audit summary generation"""
        # Add some test results
        self.audit_engine.validate_response(
            test_name="summary_test_pass",
            expected_pattern=self.simple_json_pattern,
            actual_response=self.simple_json_response,
            http_method_expected="GET",
            http_method_actual="GET",
            status_code_expected=200,
            status_code_actual=200,
        )

        self.audit_engine.validate_response(
            test_name="summary_test_fail",
            expected_pattern=self.simple_json_pattern,
            actual_response=self.different_json_response,
            http_method_expected="GET",
            http_method_actual="GET",
            status_code_expected=200,
            status_code_actual=200,
        )

        summary = self.audit_engine.generate_audit_summary()

        self.assertEqual(summary["total_tests"], 2)
        self.assertEqual(summary["passed_tests"], 1)
        self.assertEqual(summary["failed_tests"], 1)
        self.assertEqual(summary["pass_rate"], 50.0)
        self.assertEqual(summary["compliance_status"], "NON_COMPLIANT")

    @unittest.skipUnless(AUDIT_ENGINE_AVAILABLE, "AuditEngine not available")
    def test_invalid_json_handling(self):
        """Test handling of invalid JSON"""
        result = self.audit_engine.validate_response(
            test_name="invalid_json_test",
            expected_pattern='{"valid": "json"}',
            actual_response='{"invalid": json}',  # Invalid JSON
            http_method_expected="GET",
            http_method_actual="GET",
            status_code_expected=200,
            status_code_actual=200,
        )

        self.assertEqual(result["overall_result"], "ERROR")
        self.assertGreater(len(result["json_validation_errors"]), 0)

    def test_http_method_extraction_basic(self):
        """Test basic HTTP method extraction from commands"""
        from src.testpilot.audit.audit_processor import (
            _extract_http_method_from_command,
        )

        test_cases = [
            ("curl -X GET http://example.com", "GET"),
            ("curl -X POST http://example.com", "POST"),
            ("curl --request PUT http://example.com", "PUT"),
            ("curl http://example.com", "GET"),  # Default
            ("", ""),  # Empty
            ("not_curl -X POST", ""),  # Not curl
        ]

        for command, expected in test_cases:
            with self.subTest(command=command):
                result = _extract_http_method_from_command(command)
                self.assertEqual(result, expected)

    def test_status_code_extraction_basic(self):
        """Test basic status code extraction from responses"""
        from src.testpilot.audit.audit_processor import _extract_status_code

        test_cases = [
            ("HTTP/1.1 200 OK", 200),
            ('{"status": 404}', 404),
            ("HTTP/1.1 500 Internal Server Error", 500),
            ("No status here", None),
            ("", None),
        ]

        for output, expected in test_cases:
            with self.subTest(output=output):
                result = _extract_status_code(output)
                self.assertEqual(result, expected)

    def test_dependency_availability(self):
        """Test which audit dependencies are available"""
        dependencies = {
            "AuditEngine": AUDIT_ENGINE_AVAILABLE,
            "AuditExporter": AUDIT_EXPORTER_AVAILABLE,
        }

        print("\n🔍 Dependency Check:")
        for dep_name, available in dependencies.items():
            status = "✅ Available" if available else "❌ Missing"
            print(f"   {dep_name}: {status}")

        # At least basic functionality should be available
        if not AUDIT_ENGINE_AVAILABLE:
            self.skipTest(
                "Core audit functionality not available - check dependencies"
            )


class TestAuditIntegrationBasic(unittest.TestCase):
    """Basic integration tests without heavy dependencies"""

    @unittest.skipUnless(AUDIT_ENGINE_AVAILABLE, "AuditEngine not available")
    def test_end_to_end_basic_workflow(self):
        """Test basic end-to-end audit workflow"""
        engine = AuditEngine()

        # Simulate a simple audit workflow
        test_scenarios = [
            {
                "name": "api_call_success",
                "pattern": '{"result": "success", "data": {"id": 1}}',
                "response": '{"result": "success", "data": {"id": 1}}',
                "expected_result": "PASS",
            },
            {
                "name": "api_call_failure",
                "pattern": '{"result": "success"}',
                "response": '{"result": "error", "message": "Failed"}',
                "expected_result": "FAIL",
            },
        ]

        results = []
        for scenario in test_scenarios:
            result = engine.validate_response(
                test_name=scenario["name"],
                expected_pattern=scenario["pattern"],
                actual_response=scenario["response"],
                http_method_expected="GET",
                http_method_actual="GET",
                status_code_expected=200,
                status_code_actual=200,
            )
            results.append(result)
            self.assertEqual(
                result["overall_result"], scenario["expected_result"]
            )

        # Generate summary
        summary = engine.generate_audit_summary()
        self.assertEqual(summary["total_tests"], 2)
        self.assertEqual(summary["passed_tests"], 1)
        self.assertEqual(summary["failed_tests"], 1)

        # Verify results are accessible
        all_results = engine.get_audit_results()
        self.assertEqual(len(all_results), 2)


def run_basic_tests():
    """Run basic audit tests and return success status"""
    print("🔍 Running Basic Audit Tests (Dependency-Free)")
    print("=" * 60)

    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestBasicAuditFunctionality))
    suite.addTests(loader.loadTestsFromTestCase(TestAuditIntegrationBasic))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2, buffer=True)
    result = runner.run(suite)

    # Print summary
    print("\n" + "=" * 60)
    print("📊 Basic Test Summary:")
    print(f"   Tests Run: {result.testsRun}")
    print(f"   Failures: {len(result.failures)}")
    print(f"   Errors: {len(result.errors)}")
    print(f"   Skipped: {len(result.skipped)}")

    if result.wasSuccessful():
        print("✅ All basic tests passed!")
    else:
        print("⚠️ Some tests failed or had errors")
        if result.failures:
            print("\nFailures:")
            for test, traceback in result.failures:
                print(
                    f"   - {test}: {traceback.split('AssertionError:')[-1].strip()}"
                )
        if result.errors:
            print("\nErrors:")
            for test, traceback in result.errors:
                print(
                    f"   - {test}: {traceback.split('Exception:')[-1].strip()}"
                )

    print("=" * 60)

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_basic_tests()
    sys.exit(0 if success else 1)
