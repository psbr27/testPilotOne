#!/usr/bin/env python3
"""
Unit tests for ValidationEngine
===============================

Tests the 3-layer validation system:
1. HTTP status code validation
2. Response payload comparison
3. Pattern matching
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from src.testpilot.core.validation_engine import (
    ValidationEngine,
    ValidationResult,
)


class TestValidationEngine(unittest.TestCase):
    """Test cases for ValidationEngine."""

    def setUp(self):
        """Set up test fixtures."""
        # Create temporary directory for test payloads
        self.temp_dir = tempfile.mkdtemp()
        self.payloads_dir = Path(self.temp_dir)

        # Create sample payload file
        sample_payload = {
            "nfInstanceId": "test-123",
            "nfType": "SMF",
            "nfStatus": "REGISTERED",
            "message": "Registration successful",
        }

        payload_file = self.payloads_dir / "test_payload.json"
        with open(payload_file, "w") as f:
            json.dump(sample_payload, f)

        # Initialize validation engine
        self.validator = ValidationEngine(payloads_dir=str(self.payloads_dir))

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_http_status_validation_success(self):
        """Test successful HTTP status validation."""
        result = self.validator.validate_step(
            response_text='{"success": true}',
            actual_status=200,
            expected_status=200,
        )

        self.assertTrue(result.passed)
        self.assertTrue(result.http_status_match)
        self.assertEqual(result.actual_status, 200)
        self.assertEqual(result.expected_status, 200)

    def test_http_status_validation_failure(self):
        """Test failed HTTP status validation."""
        result = self.validator.validate_step(
            response_text='{"error": "Not found"}',
            actual_status=404,
            expected_status=200,
        )

        self.assertFalse(result.passed)
        self.assertFalse(result.http_status_match)
        self.assertIn("HTTP status mismatch", result.fail_reason)

    def test_http_status_excel_float_handling(self):
        """Test handling of Excel float formatting for status codes."""
        result = self.validator.validate_step(
            response_text='{"success": true}',
            actual_status=201,
            expected_status="201.0",  # Excel sometimes formats as float
        )

        self.assertTrue(result.passed)
        self.assertTrue(result.http_status_match)

    def test_payload_validation_success(self):
        """Test successful payload validation."""
        response_json = {
            "nfInstanceId": "test-123",
            "nfType": "SMF",
            "nfStatus": "REGISTERED",
            "message": "Registration successful",
        }

        result = self.validator.validate_step(
            response_text=json.dumps(response_json),
            actual_status=200,
            expected_status=200,
            response_payload="test_payload.json",
        )

        self.assertTrue(result.passed)
        self.assertTrue(result.payload_match)

    def test_payload_validation_failure(self):
        """Test failed payload validation."""
        response_json = {
            "nfInstanceId": "different-123",  # Different ID
            "nfType": "SMF",
            "nfStatus": "REGISTERED",
        }

        result = self.validator.validate_step(
            response_text=json.dumps(response_json),
            actual_status=200,
            expected_status=200,
            response_payload="test_payload.json",
        )

        self.assertFalse(result.passed)
        self.assertIn("Response structure does not match", result.fail_reason)

    def test_pattern_matching_string_success(self):
        """Test successful string pattern matching."""
        response_text = '{"message": "Operation completed successfully"}'

        result = self.validator.validate_step(
            response_text=response_text,
            actual_status=200,
            expected_status=200,
            pattern_match="Operation completed",
        )

        self.assertTrue(result.passed)
        self.assertTrue(result.pattern_match)
        self.assertTrue(result.pattern_found)

    def test_pattern_matching_string_failure(self):
        """Test failed string pattern matching."""
        response_text = '{"message": "Operation failed"}'

        result = self.validator.validate_step(
            response_text=response_text,
            actual_status=200,
            expected_status=200,
            pattern_match="Operation completed",
        )

        self.assertFalse(result.passed)
        self.assertFalse(result.pattern_found)
        self.assertIn(
            "Expected text/pattern was not found", result.fail_reason
        )

    def test_pattern_matching_json_success(self):
        """Test successful JSON pattern matching."""
        response_text = """
        {
            "nfInstanceId": "test-123",
            "nfType": "SMF",
            "nfStatus": "REGISTERED",
            "additionalData": "some value"
        }
        """

        json_pattern = '{"nfType": "SMF", "nfStatus": "REGISTERED"}'

        result = self.validator.validate_step(
            response_text=response_text,
            actual_status=200,
            expected_status=200,
            pattern_match=json_pattern,
        )

        self.assertTrue(result.passed)
        self.assertTrue(result.pattern_match)
        self.assertTrue(result.pattern_found)

    def test_excel_pattern_cleaning(self):
        """Test cleaning of Excel _x000D_ formatting."""
        excel_pattern = 'nfType": "SMF",_x000D_\n"nfStatus": "REGISTERED"'

        cleaned = self.validator.clean_excel_pattern(excel_pattern)

        self.assertNotIn("_x000D_", cleaned)
        self.assertIn("nfType", cleaned)
        self.assertIn("nfStatus", cleaned)

    def test_combined_validation_all_pass(self):
        """Test all three validation layers passing."""
        response_json = {
            "nfInstanceId": "test-123",
            "nfType": "SMF",
            "nfStatus": "REGISTERED",
            "message": "Registration successful",
        }

        result = self.validator.validate_step(
            response_text=json.dumps(response_json),
            actual_status=200,
            expected_status=200,
            response_payload="test_payload.json",
            pattern_match="Registration successful",
        )

        self.assertTrue(result.passed)
        self.assertTrue(result.http_status_match)
        self.assertTrue(result.payload_match)
        self.assertTrue(result.pattern_match)

    def test_validation_short_circuit_on_status_fail(self):
        """Test that validation short-circuits on status code failure."""
        result = self.validator.validate_step(
            response_text='{"error": "Not found"}',
            actual_status=404,
            expected_status=200,
            response_payload="test_payload.json",
            pattern_match="success",
        )

        self.assertFalse(result.passed)
        self.assertFalse(result.http_status_match)
        # Other validations should not be attempted
        self.assertFalse(result.payload_match)
        self.assertFalse(result.pattern_match)

    def test_missing_payload_file(self):
        """Test handling of missing payload file."""
        result = self.validator.validate_step(
            response_text='{"test": "data"}',
            actual_status=200,
            expected_status=200,
            response_payload="nonexistent.json",
        )

        self.assertFalse(result.passed)
        self.assertIn("Response payload mismatch", result.fail_reason)

    def test_invalid_json_response(self):
        """Test handling of invalid JSON in response."""
        result = self.validator.validate_step(
            response_text="Invalid JSON{",
            actual_status=200,
            expected_status=200,
            response_payload="test_payload.json",
        )

        self.assertFalse(result.passed)
        self.assertIn("Invalid JSON", result.fail_reason)


if __name__ == "__main__":
    unittest.main()
