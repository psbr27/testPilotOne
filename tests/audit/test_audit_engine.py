#!/usr/bin/env python3
"""
Comprehensive Unit Tests for AuditEngine

Tests all validation scenarios including:
- Sunny day cases (perfect matches)
- Rainy day cases (validation failures)
- Edge cases (malformed data, boundary conditions)
- HTTP validation
- JSON validation
- Pattern matching
"""

import json
import os
import sys
import unittest
from datetime import datetime
from unittest.mock import Mock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.testpilot.audit.audit_engine import AuditEngine


class TestAuditEngine(unittest.TestCase):
    """Comprehensive test suite for AuditEngine"""

    def setUp(self):
        """Set up test fixtures"""
        self.audit_engine = AuditEngine()

        # Test data fixtures
        self.valid_json_pattern = (
            '{"status": "success", "data": {"id": 123, "name": "test"}}'
        )
        self.valid_json_response = (
            '{"status": "success", "data": {"id": 123, "name": "test"}}'
        )

        self.partial_json_pattern = '{"status": "success"}'
        self.partial_json_response = (
            '{"status": "success", "data": {"id": 123}, "extra": "field"}'
        )

        self.invalid_json_pattern = '{"invalid": json}'
        self.malformed_json = '{"missing": "quote}'

        self.complex_pattern = """
        {
            "users": [
                {"id": 1, "name": "Alice", "active": true},
                {"id": 2, "name": "Bob", "active": false}
            ],
            "metadata": {
                "total": 2,
                "page": 1
            }
        }
        """

        self.complex_response_match = """
        {
            "users": [
                {"id": 1, "name": "Alice", "active": true},
                {"id": 2, "name": "Bob", "active": false}
            ],
            "metadata": {
                "total": 2,
                "page": 1
            }
        }
        """

        self.complex_response_mismatch = """
        {
            "users": [
                {"id": 1, "name": "Alice", "active": true},
                {"id": 3, "name": "Charlie", "active": true}
            ],
            "metadata": {
                "total": 3,
                "page": 1
            }
        }
        """

    def tearDown(self):
        """Clean up after tests"""
        self.audit_engine.clear_results()

    # =================================================================
    # SUNNY DAY TESTS - Perfect scenarios
    # =================================================================

    def test_perfect_match_validation_pass(self):
        """Test perfect JSON pattern match - should PASS"""
        result = self.audit_engine.validate_response(
            test_name="perfect_match_test",
            expected_pattern=self.valid_json_pattern,
            actual_response=self.valid_json_response,
            http_method_expected="GET",
            http_method_actual="GET",
            status_code_expected=200,
            status_code_actual=200,
        )

        self.assertEqual(result["overall_result"], "PASS")
        self.assertEqual(result["test_name"], "perfect_match_test")
        self.assertEqual(result["validation_type"], "STRICT_100_PERCENT")
        self.assertEqual(len(result["differences"]), 0)
        self.assertEqual(len(result["http_validation_errors"]), 0)
        self.assertEqual(len(result["json_validation_errors"]), 0)
        self.assertIn("timestamp", result)

    def test_complex_nested_perfect_match(self):
        """Test complex nested JSON perfect match"""
        result = self.audit_engine.validate_response(
            test_name="complex_perfect_match",
            expected_pattern=self.complex_pattern,
            actual_response=self.complex_response_match,
            http_method_expected="POST",
            http_method_actual="POST",
            status_code_expected=201,
            status_code_actual=201,
        )

        self.assertEqual(result["overall_result"], "PASS")
        self.assertEqual(len(result["differences"]), 0)

    def test_case_insensitive_http_methods(self):
        """Test case insensitive HTTP method validation"""
        result = self.audit_engine.validate_response(
            test_name="case_insensitive_http_test",
            expected_pattern=self.valid_json_pattern,
            actual_response=self.valid_json_response,
            http_method_expected="get",
            http_method_actual="GET",
            status_code_expected=200,
            status_code_actual=200,
        )

        self.assertEqual(result["overall_result"], "PASS")
        self.assertEqual(len(result["http_validation_errors"]), 0)

    # =================================================================
    # RAINY DAY TESTS - Validation failures
    # =================================================================

    def test_json_pattern_mismatch_fail(self):
        """Test JSON pattern mismatch - should FAIL"""
        different_response = (
            '{"status": "error", "data": {"id": 456, "name": "different"}}'
        )

        result = self.audit_engine.validate_response(
            test_name="pattern_mismatch_test",
            expected_pattern=self.valid_json_pattern,
            actual_response=different_response,
            http_method_expected="GET",
            http_method_actual="GET",
            status_code_expected=200,
            status_code_actual=200,
        )

        self.assertEqual(result["overall_result"], "FAIL")
        self.assertGreater(len(result["differences"]), 0)
        self.assertGreater(len(result["json_validation_errors"]), 0)

        # Check specific differences
        differences = result["differences"]
        diff_fields = [diff["field_path"] for diff in differences]
        self.assertIn("status", diff_fields)
        self.assertIn("data.id", diff_fields)
        self.assertIn("data.name", diff_fields)

    def test_http_method_mismatch_fail(self):
        """Test HTTP method mismatch - should FAIL"""
        result = self.audit_engine.validate_response(
            test_name="http_method_mismatch_test",
            expected_pattern=self.valid_json_pattern,
            actual_response=self.valid_json_response,
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

    def test_status_code_mismatch_fail(self):
        """Test HTTP status code mismatch - should FAIL"""
        result = self.audit_engine.validate_response(
            test_name="status_code_mismatch_test",
            expected_pattern=self.valid_json_pattern,
            actual_response=self.valid_json_response,
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

    def test_multiple_validation_failures(self):
        """Test multiple validation failures at once"""
        result = self.audit_engine.validate_response(
            test_name="multiple_failures_test",
            expected_pattern=self.valid_json_pattern,
            actual_response='{"status": "error"}',  # Different + missing data
            http_method_expected="GET",
            http_method_actual="DELETE",  # Wrong method
            status_code_expected=200,
            status_code_actual=500,  # Wrong status
        )

        self.assertEqual(result["overall_result"], "FAIL")
        self.assertGreater(len(result["http_validation_errors"]), 0)
        self.assertGreater(len(result["json_validation_errors"]), 0)
        self.assertGreater(len(result["differences"]), 0)

    def test_complex_nested_mismatch(self):
        """Test complex nested JSON with mismatches"""
        result = self.audit_engine.validate_response(
            test_name="complex_mismatch_test",
            expected_pattern=self.complex_pattern,
            actual_response=self.complex_response_mismatch,
            http_method_expected="POST",
            http_method_actual="POST",
            status_code_expected=201,
            status_code_actual=201,
        )

        self.assertEqual(result["overall_result"], "FAIL")
        self.assertGreater(len(result["differences"]), 0)

        # Check for specific nested differences
        differences = result["differences"]
        diff_fields = [diff["field_path"] for diff in differences]

        # Should detect user ID and name changes, total count change
        user_id_diffs = [f for f in diff_fields if "users" in f and "id" in f]
        self.assertTrue(len(user_id_diffs) > 0)

    # =================================================================
    # EDGE CASES - Boundary conditions and malformed data
    # =================================================================

    def test_malformed_json_pattern_fail(self):
        """Test malformed JSON pattern - should FAIL with JSON error"""
        result = self.audit_engine.validate_response(
            test_name="malformed_pattern_test",
            expected_pattern=self.malformed_json,
            actual_response=self.valid_json_response,
            http_method_expected="GET",
            http_method_actual="GET",
            status_code_expected=200,
            status_code_actual=200,
        )

        self.assertEqual(result["overall_result"], "FAIL")
        self.assertGreater(len(result["json_validation_errors"]), 0)
        self.assertIn(
            "Pattern matching error", result["json_validation_errors"][0]
        )

    def test_malformed_json_response_fail(self):
        """Test malformed JSON response - should FAIL with JSON error"""
        result = self.audit_engine.validate_response(
            test_name="malformed_response_test",
            expected_pattern=self.valid_json_pattern,
            actual_response=self.malformed_json,
            http_method_expected="GET",
            http_method_actual="GET",
            status_code_expected=200,
            status_code_actual=200,
        )

        self.assertEqual(result["overall_result"], "FAIL")
        self.assertGreater(len(result["json_validation_errors"]), 0)
        self.assertIn(
            "Invalid JSON structure", result["json_validation_errors"][0]
        )

    def test_empty_pattern_and_response(self):
        """Test empty pattern and response"""
        result = self.audit_engine.validate_response(
            test_name="empty_data_test",
            expected_pattern="",
            actual_response="",
            http_method_expected="GET",
            http_method_actual="GET",
            status_code_expected=200,
            status_code_actual=200,
        )

        # Empty strings should cause ERROR due to JSON parsing failure
        self.assertEqual(result["overall_result"], "ERROR")
        self.assertGreater(len(result["json_validation_errors"]), 0)

    def test_none_values_handling(self):
        """Test handling of None values in HTTP validation"""
        result = self.audit_engine.validate_response(
            test_name="none_values_test",
            expected_pattern=self.valid_json_pattern,
            actual_response=self.valid_json_response,
            http_method_expected=None,
            http_method_actual=None,
            status_code_expected=None,
            status_code_actual=None,
        )

        # None values should be treated as equal, JSON should pass
        self.assertEqual(result["overall_result"], "PASS")
        self.assertEqual(len(result["http_validation_errors"]), 0)

    def test_none_vs_value_mismatch(self):
        """Test None vs actual value mismatch"""
        result = self.audit_engine.validate_response(
            test_name="none_vs_value_test",
            expected_pattern=self.valid_json_pattern,
            actual_response=self.valid_json_response,
            http_method_expected=None,
            http_method_actual="GET",
            status_code_expected=200,
            status_code_actual=None,
        )

        self.assertEqual(result["overall_result"], "FAIL")
        self.assertGreater(len(result["http_validation_errors"]), 0)

    def test_large_json_objects(self):
        """Test handling of large JSON objects"""
        large_pattern = {
            "data": [{"id": i, "value": f"item_{i}"} for i in range(100)]
        }
        large_response = {
            "data": [{"id": i, "value": f"item_{i}"} for i in range(100)]
        }

        result = self.audit_engine.validate_response(
            test_name="large_json_test",
            expected_pattern=json.dumps(large_pattern),
            actual_response=json.dumps(large_response),
            http_method_expected="GET",
            http_method_actual="GET",
            status_code_expected=200,
            status_code_actual=200,
        )

        self.assertEqual(result["overall_result"], "PASS")

    def test_unicode_and_special_characters(self):
        """Test handling of Unicode and special characters"""
        unicode_pattern = '{"message": "Hello 世界! Special chars: @#$%^&*()", "emoji": "🚀"}'
        unicode_response = '{"message": "Hello 世界! Special chars: @#$%^&*()", "emoji": "🚀"}'

        result = self.audit_engine.validate_response(
            test_name="unicode_test",
            expected_pattern=unicode_pattern,
            actual_response=unicode_response,
            http_method_expected="POST",
            http_method_actual="POST",
            status_code_expected=200,
            status_code_actual=200,
        )

        self.assertEqual(result["overall_result"], "PASS")

    def test_array_order_sensitivity(self):
        """Test that array order is significant in strict mode"""
        pattern_ordered = '{"items": [1, 2, 3]}'
        response_reordered = '{"items": [3, 2, 1]}'

        result = self.audit_engine.validate_response(
            test_name="array_order_test",
            expected_pattern=pattern_ordered,
            actual_response=response_reordered,
            http_method_expected="GET",
            http_method_actual="GET",
            status_code_expected=200,
            status_code_actual=200,
        )

        # In strict audit mode, order should matter
        self.assertEqual(result["overall_result"], "FAIL")
        self.assertGreater(len(result["differences"]), 0)

    def test_nested_array_with_objects(self):
        """Test nested arrays with objects"""
        pattern = '{"users": [{"name": "Alice", "roles": ["admin", "user"]}, {"name": "Bob", "roles": ["user"]}]}'
        response_match = '{"users": [{"name": "Alice", "roles": ["admin", "user"]}, {"name": "Bob", "roles": ["user"]}]}'
        response_mismatch = '{"users": [{"name": "Alice", "roles": ["user", "admin"]}, {"name": "Bob", "roles": ["user"]}]}'

        # Test perfect match
        result_match = self.audit_engine.validate_response(
            test_name="nested_array_match_test",
            expected_pattern=pattern,
            actual_response=response_match,
            http_method_expected="GET",
            http_method_actual="GET",
            status_code_expected=200,
            status_code_actual=200,
        )
        self.assertEqual(result_match["overall_result"], "PASS")

        # Test array order mismatch (should fail in strict mode)
        result_mismatch = self.audit_engine.validate_response(
            test_name="nested_array_mismatch_test",
            expected_pattern=pattern,
            actual_response=response_mismatch,
            http_method_expected="GET",
            http_method_actual="GET",
            status_code_expected=200,
            status_code_actual=200,
        )
        self.assertEqual(result_mismatch["overall_result"], "FAIL")

    # =================================================================
    # AUDIT ENGINE STATE AND SUMMARY TESTS
    # =================================================================

    def test_audit_summary_generation(self):
        """Test audit summary generation"""
        # Add some test results
        self.audit_engine.validate_response(
            test_name="pass_test_1",
            expected_pattern=self.valid_json_pattern,
            actual_response=self.valid_json_response,
            http_method_expected="GET",
            http_method_actual="GET",
            status_code_expected=200,
            status_code_actual=200,
        )

        self.audit_engine.validate_response(
            test_name="fail_test_1",
            expected_pattern=self.valid_json_pattern,
            actual_response='{"status": "error"}',
            http_method_expected="GET",
            http_method_actual="POST",
            status_code_expected=200,
            status_code_actual=400,
        )

        summary = self.audit_engine.generate_audit_summary()

        self.assertEqual(summary["audit_mode"], "STRICT_100_PERCENT")
        self.assertEqual(summary["total_tests"], 2)
        self.assertEqual(summary["passed_tests"], 1)
        self.assertEqual(summary["failed_tests"], 1)
        self.assertEqual(summary["error_tests"], 0)
        self.assertEqual(summary["pass_rate"], 50.0)
        self.assertEqual(summary["compliance_status"], "NON_COMPLIANT")
        self.assertIn("generated_at", summary)

    def test_get_and_clear_results(self):
        """Test getting and clearing audit results"""
        # Add a test result
        self.audit_engine.validate_response(
            test_name="test_result",
            expected_pattern=self.valid_json_pattern,
            actual_response=self.valid_json_response,
        )

        # Get results
        results = self.audit_engine.get_audit_results()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["test_name"], "test_result")

        # Clear results
        self.audit_engine.clear_results()
        cleared_results = self.audit_engine.get_audit_results()
        self.assertEqual(len(cleared_results), 0)

    def test_multiple_tests_batch_processing(self):
        """Test processing multiple tests in batch"""
        test_cases = [
            (
                "batch_test_1",
                "PASS",
                self.valid_json_pattern,
                self.valid_json_response,
                "GET",
                "GET",
                200,
                200,
            ),
            (
                "batch_test_2",
                "FAIL",
                self.valid_json_pattern,
                '{"status": "error"}',
                "GET",
                "GET",
                200,
                200,
            ),
            (
                "batch_test_3",
                "FAIL",
                self.valid_json_pattern,
                self.valid_json_response,
                "GET",
                "POST",
                200,
                200,
            ),
            (
                "batch_test_4",
                "PASS",
                '{"simple": "test"}',
                '{"simple": "test"}',
                "POST",
                "POST",
                201,
                201,
            ),
        ]

        for (
            name,
            expected_result,
            pattern,
            response,
            method_exp,
            method_act,
            status_exp,
            status_act,
        ) in test_cases:
            result = self.audit_engine.validate_response(
                test_name=name,
                expected_pattern=pattern,
                actual_response=response,
                http_method_expected=method_exp,
                http_method_actual=method_act,
                status_code_expected=status_exp,
                status_code_actual=status_act,
            )
            self.assertEqual(
                result["overall_result"],
                expected_result,
                f"Test {name} failed",
            )

        # Check summary
        summary = self.audit_engine.generate_audit_summary()
        self.assertEqual(summary["total_tests"], 4)
        self.assertEqual(summary["passed_tests"], 2)
        self.assertEqual(summary["failed_tests"], 2)

    # =================================================================
    # ERROR HANDLING AND EXCEPTION TESTS
    # =================================================================

    def test_exception_handling_in_validation(self):
        """Test exception handling during validation"""
        with patch(
            "src.testpilot.audit.audit_engine.check_json_pattern_match"
        ) as mock_check:
            mock_check.side_effect = Exception("Simulated validation error")

            result = self.audit_engine.validate_response(
                test_name="exception_test",
                expected_pattern=self.valid_json_pattern,
                actual_response=self.valid_json_response,
                http_method_expected="GET",
                http_method_actual="GET",
                status_code_expected=200,
                status_code_actual=200,
            )

            self.assertEqual(result["overall_result"], "FAIL")
            self.assertGreater(len(result["json_validation_errors"]), 0)
            self.assertIn(
                "Pattern matching error", result["json_validation_errors"][0]
            )

    def test_json_parsing_exception_handling(self):
        """Test JSON parsing exception handling"""
        # This should trigger JSON parsing errors
        result = self.audit_engine.validate_response(
            test_name="json_parsing_exception_test",
            expected_pattern="definitely not json",
            actual_response="also not json",
            http_method_expected="GET",
            http_method_actual="GET",
            status_code_expected=200,
            status_code_actual=200,
        )

        self.assertEqual(result["overall_result"], "FAIL")
        self.assertGreater(len(result["json_validation_errors"]), 0)

    # =================================================================
    # PERFORMANCE AND STRESS TESTS
    # =================================================================

    def test_stress_test_many_validations(self):
        """Stress test with many validations"""
        num_tests = 50

        for i in range(num_tests):
            pattern = f'{{"test_id": {i}, "data": "test_data_{i}"}}'
            response = f'{{"test_id": {i}, "data": "test_data_{i}"}}'

            result = self.audit_engine.validate_response(
                test_name=f"stress_test_{i}",
                expected_pattern=pattern,
                actual_response=response,
                http_method_expected="GET",
                http_method_actual="GET",
                status_code_expected=200,
                status_code_actual=200,
            )

            self.assertEqual(result["overall_result"], "PASS")

        summary = self.audit_engine.generate_audit_summary()
        self.assertEqual(summary["total_tests"], num_tests)
        self.assertEqual(summary["passed_tests"], num_tests)
        self.assertEqual(summary["failed_tests"], 0)
        self.assertEqual(summary["pass_rate"], 100.0)

    def test_strict_collect_differences_extra_keys(self):
        """Test _strict_collect_differences with extra keys in actual response"""
        expected = {"a": 1}
        actual = {"a": 1, "b": 2}

        differences = self.audit_engine._strict_collect_differences(
            expected, actual
        )

        self.assertEqual(len(differences), 1)
        self.assertEqual(differences[0][0], "extra")
        self.assertEqual(differences[0][1], "b")
        self.assertEqual(differences[0][3], 2)


class TestAuditEngineFallback(unittest.TestCase):
    """Test suite for AuditEngine fallback implementations"""

    def setUp(self):
        """Set up test fixtures"""
        # Temporarily remove the imported modules to trigger fallback
        self.original_sys_modules = sys.modules.copy()
        if "src.testpilot.utils.pattern_match" in sys.modules:
            del sys.modules["src.testpilot.utils.pattern_match"]

        # Re-import AuditEngine to use the fallback implementations
        from src.testpilot.audit.audit_engine import AuditEngine

        self.audit_engine = AuditEngine()

    def tearDown(self):
        """Clean up after tests"""
        # Restore original modules
        sys.modules.clear()
        sys.modules.update(self.original_sys_modules)

    def test_fallback_enhance_collect_differences(self):
        """Test the fallback implementation of enhance_collect_differences"""
        expected = {"a": 1}
        actual = {"a": 2}
        # In fallback mode, this will call the basic `_strict_collect_differences`
        diffs = self.audit_engine._strict_collect_differences(expected, actual)
        self.assertNotEqual(diffs, [])
        self.assertEqual(len(diffs), 1)
        self.assertEqual(diffs[0][0], "mismatch")

    def test_fallback_check_json_pattern_match(self):
        """Test the fallback implementation of check_json_pattern_match"""
        expected = '{"a": 1}'
        actual = '{"a": 1}'
        audit_result = {}
        is_valid = self.audit_engine._validate_pattern_match(
            expected, actual, audit_result
        )
        self.assertTrue(is_valid)

    def test_fallback_check_json_pattern_mismatch(self):
        """Test the fallback implementation of check_json_pattern_match with a mismatch"""
        expected = '{"a": 1}'
        actual = '{"a": 2}'
        audit_result = {}
        is_valid = self.audit_engine._validate_pattern_match(
            expected, actual, audit_result
        )
        self.assertFalse(is_valid)


if __name__ == "__main__":
    unittest.main(verbosity=2)
