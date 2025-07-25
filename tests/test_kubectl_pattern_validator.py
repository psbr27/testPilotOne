"""
Unit tests for KubectlPatternValidator fix for 'dict' object split() error.

This test suite validates the fix for the issue where response_body was parsed
as JSON (converting to dict/list) but then split() was called on it, causing:
"'dict' object has no attribute 'split'" error.
"""

import json
import os
import sys
import unittest
from unittest.mock import Mock, mock_open, patch

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from testpilot.core.validation_engine import (
    KubectlPatternValidator,
    ValidationContext,
    ValidationResult,
)


class MockArgs:
    """Mock args object for testing."""

    def __init__(self, config_file="config/hosts.json"):
        self.config = config_file


class TestKubectlPatternValidator(unittest.TestCase):
    """Test cases for KubectlPatternValidator split() error fix."""

    def setUp(self):
        """Set up test fixtures."""
        self.validator = KubectlPatternValidator()
        self.mock_config = {
            "validation_settings": {"json_match_threshold": 50}
        }

    def _create_context(
        self,
        response_body,
        pattern_match="test_pattern",
        response_headers=None,
        response_payload=None,
    ):
        """Helper to create ValidationContext for testing."""
        context = Mock(spec=ValidationContext)
        context.response_body = response_body
        context.pattern_match = pattern_match
        context.response_headers = response_headers or {}
        context.response_payload = response_payload
        context.args = MockArgs()
        context.sheet_name = "test_sheet"
        context.row_idx = 1
        return context

    @patch(
        "builtins.open",
        mock_open(
            read_data='{"validation_settings": {"json_match_threshold": 50}}'
        ),
    )
    @patch("testpilot.core.validation_engine.validate_response_enhanced")
    def test_dict_response_body_no_split_error(self, mock_validate):
        """Test that dict response_body doesn't cause split() error (main fix)."""
        # Arrange: Create dict response body that would cause the original error
        dict_response_body = {
            "log": "test_pattern found in logs",
            "level": "info",
            "timestamp": "2024-01-01T10:00:00Z",
        }
        context = self._create_context(dict_response_body, "test_pattern")

        # Mock successful pattern match
        mock_validate.return_value = {"pattern_match_overall": True}

        # Act: This should NOT raise "'dict' object has no attribute 'split'" error
        result = self.validator.validate(context)

        # Assert: Validation should succeed without errors
        self.assertIsInstance(result, ValidationResult)
        self.assertTrue(result.passed)
        mock_validate.assert_called_once()

        # Verify the response_body was converted to string for pattern matching
        call_args = mock_validate.call_args[0]
        self.assertIsInstance(
            call_args[2], str
        )  # response_body should be stringified

    @patch(
        "builtins.open",
        mock_open(
            read_data='{"validation_settings": {"json_match_threshold": 50}}'
        ),
    )
    @patch("testpilot.core.validation_engine.validate_response_enhanced")
    def test_original_slf_registration_profile_error_scenario(
        self, mock_validate
    ):
        """Test the exact error scenario from SLFRegistrationProfile sheet step 3."""
        # Arrange: Reproduce the exact scenario that caused the original error
        # SLFRegistrationProfile sheet step 3: test_registration_profile_2
        # Response body was already parsed as dict when it reached the validator
        slf_response_body = {
            "nfInstanceId": "12345-abc-def",
            "nfType": "SLF",
            "nfStatus": "REGISTERED",
            "fqdn": "slf.example.com",
            "ipv4Addresses": ["192.168.1.100"],
            "priority": 1,
            "capacity": 100,
            "load": 0,
            "locality": "zone1",
            "nfServices": [
                {
                    "serviceInstanceId": "slf-service-1",
                    "serviceName": "nslf-lookup",
                    "versions": [
                        {"apiVersionInUri": "v1", "apiFullVersion": "1.0.0"}
                    ],
                    "scheme": "https",
                    "nfServiceStatus": "REGISTERED",
                }
            ],
        }

        context = self._create_context(slf_response_body, "REGISTERED")
        mock_validate.return_value = {"pattern_match_overall": True}

        # Act: This exact scenario previously caused:
        # "error processing response body: 'dict' object has no attribute to split"
        result = self.validator.validate(context)

        # Assert: Should now handle gracefully without AttributeError
        self.assertIsInstance(result, ValidationResult)
        self.assertTrue(result.passed)
        mock_validate.assert_called_once()

        # Verify the dict was converted to string for pattern matching
        call_args = mock_validate.call_args[0]
        response_body_arg = call_args[2]
        self.assertIsInstance(response_body_arg, str)
        self.assertIn(
            "REGISTERED", response_body_arg
        )  # Pattern should be findable in string

    @patch(
        "builtins.open",
        mock_open(
            read_data='{"validation_settings": {"json_match_threshold": 50}}'
        ),
    )
    @patch("testpilot.core.validation_engine.validate_response_enhanced")
    def test_string_response_body_line_by_line_processing(self, mock_validate):
        """Test normal string response_body processes line by line."""
        # Arrange: Multi-line string response body
        string_response_body = (
            "line1: some text\nline2: test_pattern found\nline3: more text"
        )
        context = self._create_context(string_response_body, "test_pattern")

        # Mock pattern match found on second line
        mock_validate.side_effect = [
            {"pattern_match_overall": False},  # line1
            {"pattern_match_overall": True},  # line2 (match found)
        ]

        # Act
        result = self.validator.validate(context)

        # Assert: Should find pattern and return success
        self.assertIsInstance(result, ValidationResult)
        self.assertTrue(result.passed)
        self.assertEqual(
            mock_validate.call_count, 2
        )  # Called twice (line1, line2)

    @patch(
        "builtins.open",
        mock_open(
            read_data='{"validation_settings": {"json_match_threshold": 50}}'
        ),
    )
    @patch("testpilot.core.validation_engine.validate_response_enhanced")
    def test_json_string_response_body_parsed_to_dict(self, mock_validate):
        """Test JSON string response_body that gets parsed to dict."""
        # Arrange: JSON string that will be parsed to dict
        json_response_body = '{"log": "test_pattern found", "level": "info"}'
        context = self._create_context(json_response_body, "test_pattern")

        # Mock successful pattern match
        mock_validate.return_value = {"pattern_match_overall": True}

        # Act: Should handle JSON->dict conversion gracefully
        result = self.validator.validate(context)

        # Assert: Should succeed without split() errors
        self.assertIsInstance(result, ValidationResult)
        self.assertTrue(result.passed)
        mock_validate.assert_called_once()

    @patch(
        "builtins.open",
        mock_open(
            read_data='{"validation_settings": {"json_match_threshold": 50}}'
        ),
    )
    @patch("testpilot.core.validation_engine.validate_response_enhanced")
    def test_list_response_body_no_split_error(self, mock_validate):
        """Test that list response_body doesn't cause split() error."""
        # Arrange: List response body
        list_response_body = [
            {"log": "entry1", "level": "info"},
            {"log": "test_pattern found", "level": "warn"},
        ]
        context = self._create_context(list_response_body, "test_pattern")

        # Mock successful pattern match
        mock_validate.return_value = {"pattern_match_overall": True}

        # Act
        result = self.validator.validate(context)

        # Assert: Should handle list without errors
        self.assertIsInstance(result, ValidationResult)
        self.assertTrue(result.passed)
        mock_validate.assert_called_once()

    @patch(
        "builtins.open",
        mock_open(
            read_data='{"validation_settings": {"json_match_threshold": 50}}'
        ),
    )
    @patch("testpilot.core.validation_engine.validate_response_enhanced")
    def test_none_response_body(self, mock_validate):
        """Test handling of None response_body."""
        # Arrange
        context = self._create_context(None, "test_pattern")

        # Act
        result = self.validator.validate(context)

        # Assert: Should handle None gracefully
        self.assertIsInstance(result, ValidationResult)
        # Note: None response body gets converted to string "None" and processed
        # This is the current behavior - it doesn't skip validation entirely
        mock_validate.assert_called_once()

    @patch(
        "builtins.open",
        mock_open(
            read_data='{"validation_settings": {"json_match_threshold": 50}}'
        ),
    )
    @patch("testpilot.core.validation_engine.validate_response_enhanced")
    def test_pattern_not_found_in_string_lines(self, mock_validate):
        """Test pattern not found in any line of string response."""
        # Arrange
        string_response_body = (
            "line1: no match\nline2: also no match\nline3: nothing here"
        )
        context = self._create_context(string_response_body, "missing_pattern")

        # Mock no pattern matches found
        mock_validate.return_value = {"pattern_match_overall": False}

        # Act
        result = self.validator.validate(context)

        # Assert: Should return failure
        self.assertIsInstance(result, ValidationResult)
        self.assertFalse(result.passed)
        self.assertIn("not found", result.fail_reason)
        # Should check all 3 lines
        self.assertEqual(mock_validate.call_count, 3)

    @patch(
        "builtins.open",
        mock_open(
            read_data='{"validation_settings": {"json_match_threshold": 50}}'
        ),
    )
    @patch("testpilot.core.validation_engine.validate_response_enhanced")
    def test_pattern_not_found_in_dict_response(self, mock_validate):
        """Test pattern not found in dict response."""
        # Arrange
        dict_response_body = {"log": "no match here", "level": "info"}
        context = self._create_context(dict_response_body, "missing_pattern")

        # Mock no pattern match
        mock_validate.return_value = {"pattern_match_overall": False}

        # Act
        result = self.validator.validate(context)

        # Assert: Should return failure
        self.assertIsInstance(result, ValidationResult)
        self.assertFalse(result.passed)
        self.assertIn("not found", result.fail_reason)

    @patch(
        "builtins.open",
        mock_open(
            read_data='{"validation_settings": {"json_match_threshold": 50}}'
        ),
    )
    @patch("testpilot.core.validation_engine.validate_response_enhanced")
    def test_invalid_json_string_fallback_to_string(self, mock_validate):
        """Test invalid JSON string falls back to string processing."""
        # Arrange: Invalid JSON that can't be parsed
        invalid_json = '{"invalid": json, missing quotes}'
        context = self._create_context(invalid_json, "json")

        # Mock pattern found
        mock_validate.return_value = {"pattern_match_overall": True}

        # Act: Should fallback to string processing
        result = self.validator.validate(context)

        # Assert: Should process as string (line by line)
        self.assertIsInstance(result, ValidationResult)
        self.assertTrue(result.passed)
        mock_validate.assert_called_once()

    @patch("testpilot.core.validation_engine.validate_response_enhanced")
    @patch("builtins.open", side_effect=FileNotFoundError("Config not found"))
    def test_config_loading_failure_uses_default(
        self, mock_open, mock_validate
    ):
        """Test that config loading failure uses default validation settings."""
        # Arrange
        dict_response_body = {"log": "test_pattern found"}
        context = self._create_context(dict_response_body, "test_pattern")

        # Mock successful pattern match
        mock_validate.return_value = {"pattern_match_overall": True}

        # Act: Should use default config when loading fails
        result = self.validator.validate(context)

        # Assert: Should still work with default config
        self.assertIsInstance(result, ValidationResult)
        self.assertTrue(result.passed)
        mock_validate.assert_called_once()

        # Verify default config was passed (json_match_threshold: 50)
        call_kwargs = mock_validate.call_args[1]
        self.assertEqual(call_kwargs["config"], {"json_match_threshold": 50})

    @patch(
        "builtins.open",
        mock_open(
            read_data='{"validation_settings": {"json_match_threshold": 75}}'
        ),
    )
    @patch("testpilot.core.validation_engine.validate_response_enhanced")
    def test_custom_validation_config_passed(self, mock_validate):
        """Test that custom validation config is properly loaded and passed."""
        # Arrange
        context = self._create_context({"log": "test"}, "test")
        mock_validate.return_value = {"pattern_match_overall": True}

        # Act
        result = self.validator.validate(context)

        # Assert: Custom config should be passed to validate_response_enhanced
        self.assertTrue(result.passed)
        call_kwargs = mock_validate.call_args[1]
        self.assertEqual(call_kwargs["config"], {"json_match_threshold": 75})

    @patch(
        "builtins.open",
        mock_open(
            read_data='{"validation_settings": {"json_match_threshold": 50}}'
        ),
    )
    @patch(
        "testpilot.core.validation_engine.validate_response_enhanced",
        side_effect=Exception("Validation error"),
    )
    def test_exception_handling_in_validation(self, mock_validate):
        """Test exception handling during validation process."""
        # Arrange
        context = self._create_context("test response", "test_pattern")

        # Act: Exception should be caught and handled
        result = self.validator.validate(context)

        # Assert: Should return failure with error message
        self.assertIsInstance(result, ValidationResult)
        self.assertFalse(result.passed)
        self.assertIn("Error processing response body", result.fail_reason)


if __name__ == "__main__":
    unittest.main()
