#!/usr/bin/env python3
"""
Unit Tests for Refactored AuditEngine

Tests the audit engine's integration with utils.pattern_match:
- Use of check_json_pattern_match from utils
- Strict array ordering for audit compliance
- HTTP and status code validation
- JSON structure validation
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
    """Test suite for the refactored AuditEngine"""

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

        self.array_pattern = '{"items": [1, 2, 3], "count": 3}'
        self.array_response_ordered = '{"items": [1, 2, 3], "count": 3}'
        self.array_response_unordered = '{"items": [3, 1, 2], "count": 3}'

        self.complex_pattern = {
            "users": [
                {"id": 1, "name": "Alice", "active": True},
                {"id": 2, "name": "Bob", "active": False},
            ],
            "metadata": {"total": 2, "page": 1},
        }

    def tearDown(self):
        """Clean up after tests"""
        self.audit_engine.clear_results()

    # =================================================================
    # INTEGRATION WITH PATTERN MATCHING UTILITIES
    # =================================================================

    @patch("src.testpilot.audit.audit_engine.check_json_pattern_match")
    def test_uses_check_json_pattern_match_utility(self, mock_pattern_match):
        """Test that audit engine uses the utils.pattern_match.check_json_pattern_match"""
        # Configure mock
        mock_pattern_match.return_value = (
            True,
            {
                "diffs": [],
                "matches": {"status": "success"},
                "overall_match_percent": 100,
            },
        )

        # Execute validation
        result = self.audit_engine.validate_response(
            test_name="test_pattern_utility",
            expected_pattern=self.valid_json_pattern,
            actual_response=self.valid_json_response,
            http_method_expected="GET",
            http_method_actual="GET",
            status_code_expected=200,
            status_code_actual=200,
        )

        # Verify check_json_pattern_match was called with correct params
        mock_pattern_match.assert_called_once()
        call_args = mock_pattern_match.call_args
        self.assertEqual(
            call_args[0][0], json.loads(self.valid_json_pattern)
        )  # expected
        self.assertEqual(
            call_args[0][1], json.loads(self.valid_json_response)
        )  # actual
        self.assertFalse(
            call_args[1]["partial_match"]
        )  # Audit always uses strict mode

        # Verify result
        self.assertEqual(result["overall_result"], "PASS")

    def test_strict_array_ordering_enforcement(self):
        """Test that audit enforces strict array ordering (unlike standard pattern match)"""
        # Test with same array in different order
        result = self.audit_engine.validate_response(
            test_name="array_order_test",
            expected_pattern=self.array_pattern,
            actual_response=self.array_response_unordered,
            http_method_expected="GET",
            http_method_actual="GET",
            status_code_expected=200,
            status_code_actual=200,
        )

        # Should fail due to strict array ordering
        self.assertEqual(result["overall_result"], "FAIL")
        self.assertGreater(len(result["differences"]), 0)

        # Check that differences show array order mismatch
        differences = result["differences"]
        array_diffs = [
            d for d in differences if d["field_path"].startswith("items[")
        ]
        self.assertGreater(len(array_diffs), 0)

    def test_perfect_match_with_arrays(self):
        """Test perfect match when arrays are in correct order"""
        result = self.audit_engine.validate_response(
            test_name="array_order_perfect",
            expected_pattern=self.array_pattern,
            actual_response=self.array_response_ordered,
            http_method_expected="GET",
            http_method_actual="GET",
            status_code_expected=200,
            status_code_actual=200,
        )

        self.assertEqual(result["overall_result"], "PASS")
        self.assertEqual(len(result["differences"]), 0)

    def test_empty_pattern_validation(self):
        """Test validation when expected pattern is empty"""
        result = self.audit_engine.validate_response(
            test_name="empty_pattern_test",
            expected_pattern="",
            actual_response=self.valid_json_response,
            http_method_expected="GET",
            http_method_actual="GET",
            status_code_expected=200,
            status_code_actual=200,
        )

        # Should pass when no pattern to validate
        self.assertEqual(result["overall_result"], "PASS")

    def test_json_validation_error_handling(self):
        """Test handling of invalid JSON in expected pattern"""
        result = self.audit_engine.validate_response(
            test_name="invalid_json_test",
            expected_pattern='{"invalid": json}',
            actual_response=self.valid_json_response,
            http_method_expected="GET",
            http_method_actual="GET",
            status_code_expected=200,
            status_code_actual=200,
        )

        self.assertEqual(result["overall_result"], "ERROR")
        self.assertGreater(len(result["json_validation_errors"]), 0)
        self.assertIn(
            "Invalid expected pattern JSON",
            result["json_validation_errors"][0],
        )

    def test_empty_response_error(self):
        """Test that empty response is treated as ERROR"""
        result = self.audit_engine.validate_response(
            test_name="empty_response_test",
            expected_pattern=self.valid_json_pattern,
            actual_response="",
            http_method_expected="GET",
            http_method_actual="GET",
            status_code_expected=200,
            status_code_actual=200,
        )

        self.assertEqual(result["overall_result"], "ERROR")
        self.assertIn("Empty response", result["json_validation_errors"][0])

    def test_http_method_validation(self):
        """Test HTTP method validation logic"""
        # Test mismatch
        result = self.audit_engine.validate_response(
            test_name="http_method_test",
            expected_pattern=self.valid_json_pattern,
            actual_response=self.valid_json_response,
            http_method_expected="GET",
            http_method_actual="POST",
            status_code_expected=200,
            status_code_actual=200,
        )

        self.assertEqual(result["overall_result"], "FAIL")
        self.assertIn(
            "HTTP method mismatch", result["http_validation_errors"][0]
        )

        # Test case insensitive match
        result2 = self.audit_engine.validate_response(
            test_name="http_method_case_test",
            expected_pattern=self.valid_json_pattern,
            actual_response=self.valid_json_response,
            http_method_expected="get",
            http_method_actual="GET",
            status_code_expected=200,
            status_code_actual=200,
        )

        self.assertEqual(result2["overall_result"], "PASS")

    def test_status_code_validation(self):
        """Test status code validation logic"""
        result = self.audit_engine.validate_response(
            test_name="status_code_test",
            expected_pattern=self.valid_json_pattern,
            actual_response=self.valid_json_response,
            http_method_expected="GET",
            http_method_actual="GET",
            status_code_expected=200,
            status_code_actual=404,
        )

        self.assertEqual(result["overall_result"], "FAIL")
        self.assertIn(
            "Status code mismatch", result["http_validation_errors"][0]
        )

    def test_none_values_in_validation(self):
        """Test handling of None values in HTTP method and status code"""
        # Both None should pass
        result = self.audit_engine.validate_response(
            test_name="none_values_test",
            expected_pattern=self.valid_json_pattern,
            actual_response=self.valid_json_response,
            http_method_expected=None,
            http_method_actual=None,
            status_code_expected=None,
            status_code_actual=None,
        )

        self.assertEqual(result["overall_result"], "PASS")

        # One None should fail
        result2 = self.audit_engine.validate_response(
            test_name="partial_none_test",
            expected_pattern=self.valid_json_pattern,
            actual_response=self.valid_json_response,
            http_method_expected="GET",
            http_method_actual=None,
            status_code_expected=200,
            status_code_actual=None,
        )

        self.assertEqual(result2["overall_result"], "FAIL")

    def test_complex_nested_differences(self):
        """Test detection of differences in complex nested structures"""
        expected = json.dumps(self.complex_pattern)
        actual = json.dumps(
            {
                "users": [
                    {
                        "id": 1,
                        "name": "Alice",
                        "active": False,
                    },  # active changed
                    {
                        "id": 3,
                        "name": "Charlie",
                        "active": True,
                    },  # different user
                ],
                "metadata": {"total": 2, "page": 2},  # page changed
            }
        )

        result = self.audit_engine.validate_response(
            test_name="complex_diff_test",
            expected_pattern=expected,
            actual_response=actual,
            http_method_expected="POST",
            http_method_actual="POST",
            status_code_expected=200,
            status_code_actual=200,
        )

        self.assertEqual(result["overall_result"], "FAIL")
        differences = result["differences"]

        # Verify specific differences detected
        diff_paths = [d["field_path"] for d in differences]
        self.assertIn("users[0].active", diff_paths)
        self.assertIn("users[1].id", diff_paths)
        self.assertIn("users[1].name", diff_paths)
        self.assertIn("metadata.page", diff_paths)

    def test_extra_fields_detection(self):
        """Test detection of extra fields in actual response"""
        expected = '{"a": 1, "b": 2}'
        actual = '{"a": 1, "b": 2, "c": 3}'  # Extra field

        result = self.audit_engine.validate_response(
            test_name="extra_fields_test",
            expected_pattern=expected,
            actual_response=actual,
        )

        self.assertEqual(result["overall_result"], "FAIL")
        differences = result["differences"]
        extra_diffs = [d for d in differences if d["type"] == "extra"]
        self.assertEqual(len(extra_diffs), 1)
        self.assertEqual(extra_diffs[0]["field_path"], "c")

    def test_missing_fields_detection(self):
        """Test detection of missing fields in actual response"""
        expected = '{"a": 1, "b": 2, "c": 3}'
        actual = '{"a": 1, "b": 2}'  # Missing field

        result = self.audit_engine.validate_response(
            test_name="missing_fields_test",
            expected_pattern=expected,
            actual_response=actual,
        )

        self.assertEqual(result["overall_result"], "FAIL")
        differences = result["differences"]
        missing_diffs = [d for d in differences if d["type"] == "missing"]
        self.assertEqual(len(missing_diffs), 1)
        self.assertEqual(missing_diffs[0]["field_path"], "c")

    def test_audit_summary_generation(self):
        """Test audit summary generation"""
        # Add some test results
        self.audit_engine.validate_response(
            test_name="test1",
            expected_pattern=self.valid_json_pattern,
            actual_response=self.valid_json_response,
            http_method_expected="GET",
            http_method_actual="GET",
            status_code_expected=200,
            status_code_actual=200,
        )

        self.audit_engine.validate_response(
            test_name="test2",
            expected_pattern=self.valid_json_pattern,
            actual_response='{"status": "error"}',
            http_method_expected="GET",
            http_method_actual="GET",
            status_code_expected=200,
            status_code_actual=200,
        )

        self.audit_engine.validate_response(
            test_name="test3",
            expected_pattern=self.valid_json_pattern,
            actual_response="",  # Error case
        )

        # Generate summary
        summary = self.audit_engine.generate_audit_summary()

        self.assertEqual(summary["audit_mode"], "STRICT_100_PERCENT")
        self.assertEqual(summary["total_tests"], 3)
        self.assertEqual(summary["passed_tests"], 1)
        self.assertEqual(summary["failed_tests"], 1)
        self.assertEqual(summary["error_tests"], 1)
        self.assertAlmostEqual(summary["pass_rate"], 33.33, places=1)
        self.assertEqual(summary["compliance_status"], "NON_COMPLIANT")
        self.assertIn("generated_at", summary)

    def test_clear_results(self):
        """Test clearing audit results"""
        # Add a result
        self.audit_engine.validate_response(
            test_name="test_clear",
            expected_pattern=self.valid_json_pattern,
            actual_response=self.valid_json_response,
        )

        self.assertEqual(len(self.audit_engine.get_audit_results()), 1)

        # Clear results
        self.audit_engine.clear_results()
        self.assertEqual(len(self.audit_engine.get_audit_results()), 0)

    def test_request_details_preservation(self):
        """Test that request details are preserved in audit results"""
        request_details = {
            "command": "curl -X GET http://api.test",
            "host": "test-host",
            "execution_time": 1.23,
            "custom_field": "custom_value",
        }

        result = self.audit_engine.validate_response(
            test_name="request_details_test",
            expected_pattern=self.valid_json_pattern,
            actual_response=self.valid_json_response,
            request_details=request_details,
        )

        self.assertEqual(result["request_details"], request_details)

    @patch("src.testpilot.audit.audit_engine.logger")
    def test_logging_behavior(self, mock_logger):
        """Test that appropriate log messages are generated"""
        # Test PASS logging
        self.audit_engine.validate_response(
            test_name="log_pass_test",
            expected_pattern=self.valid_json_pattern,
            actual_response=self.valid_json_response,
            http_method_expected="GET",
            http_method_actual="GET",
            status_code_expected=200,
            status_code_actual=200,
        )

        mock_logger.info.assert_called_with(
            "\tAUDIT PASS: log_pass_test - 100% validation successful"
        )

        # Test FAIL logging
        self.audit_engine.validate_response(
            test_name="log_fail_test",
            expected_pattern=self.valid_json_pattern,
            actual_response='{"status": "error"}',
        )

        mock_logger.warning.assert_called_with(
            "\tAUDIT FAIL: log_fail_test - Validation failures detected"
        )

        # Test ERROR logging - simulate exception in overall validation
        with patch(
            "src.testpilot.audit.audit_engine.AuditEngine._validate_http_method"
        ) as mock_method:
            mock_method.side_effect = Exception("Test exception")

            self.audit_engine.validate_response(
                test_name="log_error_test",
                expected_pattern=self.valid_json_pattern,
                actual_response=self.valid_json_response,
            )

            mock_logger.error.assert_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
