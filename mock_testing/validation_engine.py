"""
Validation Engine for Mock Testing Framework
============================================

Implements 3-layer validation:
1. HTTP Status Code (mandatory)
2. Response Payload comparison (if specified)
3. Pattern Match validation (if specified)
"""

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Union

import pandas as pd


@dataclass
class ValidationResult:
    """Result of a validation operation."""

    passed: bool
    reason: Optional[str] = None
    http_status_match: bool = False
    payload_match: bool = False
    pattern_match: bool = False
    expected_status: Optional[int] = None
    actual_status: Optional[int] = None
    pattern_found: Optional[bool] = None

    def fail(self, reason: str) -> "ValidationResult":
        """Mark validation as failed with reason."""
        self.passed = False
        self.reason = reason
        return self

    def pass_all(self) -> "ValidationResult":
        """Mark validation as passed."""
        self.passed = True
        self.reason = "All validations passed"
        return self


class ValidationEngine:
    """
    3-layer validation engine for mock testing.

    Validates test responses using:
    1. HTTP status code comparison
    2. JSON payload deep comparison
    3. Pattern matching in response text
    """

    def __init__(self, payloads_dir: str = "test_payloads"):
        self.payloads_dir = Path(payloads_dir)
        self.payloads_cache: Dict[str, Dict] = {}

    def validate_step(
        self,
        response_text: str,
        actual_status: int,
        expected_status: Optional[Union[int, str]],
        response_payload: Optional[str] = None,
        pattern_match: Optional[str] = None,
    ) -> ValidationResult:
        """
        Main validation method implementing 3-layer validation.

        Args:
            response_text: Raw response body text
            actual_status: HTTP status code from response
            expected_status: Expected HTTP status code
            response_payload: JSON file name for payload comparison
            pattern_match: Pattern string to search in response

        Returns:
            ValidationResult with validation outcome
        """
        try:
            expected_status_int = (
                int(float(expected_status)) if expected_status else None
            )
        except (ValueError, TypeError):
            expected_status_int = None

        result = ValidationResult(
            passed=False,
            actual_status=actual_status,
            expected_status=expected_status_int,
        )

        # Layer 1: HTTP Status Code (MANDATORY)
        if not self.validate_http_status(actual_status, expected_status):
            return result.fail(
                f"HTTP status mismatch. Expected: {expected_status}, "
                f"Actual: {actual_status}"
            )
        result.http_status_match = True

        # Layer 2: Response Payload (if specified)
        if response_payload and response_payload.strip():
            try:
                actual_json = json.loads(response_text)
                if not self.validate_response_payload(
                    actual_json, response_payload
                ):
                    return result.fail(
                        f"Response payload mismatch. Expected payload from: "
                        f"{response_payload}"
                    )
                result.payload_match = True
            except json.JSONDecodeError as e:
                return result.fail(f"Invalid JSON in response: {e}")

        # Layer 3: Pattern Match (if specified)
        if pattern_match and pattern_match.strip():
            pattern_found = self.validate_pattern_match(
                response_text, pattern_match
            )
            result.pattern_found = pattern_found
            if not pattern_found:
                return result.fail(
                    f"Pattern match failed. Pattern not found: "
                    f"{pattern_match[:100]}..."
                )
            result.pattern_match = True

        return result.pass_all()

    def validate_http_status(
        self, actual: int, expected: Optional[Union[int, str]]
    ) -> bool:
        """Validate HTTP status code."""
        if expected is None:
            return True

        try:
            expected_int = int(
                float(expected)
            )  # Handle Excel float formatting
            return actual == expected_int
        except (ValueError, TypeError):
            return False

    def validate_response_payload(
        self, actual_json: Dict[str, Any], expected_file: str
    ) -> bool:
        """
        Validate response payload against expected JSON file.

        Args:
            actual_json: Parsed JSON response
            expected_file: Filename of expected payload JSON

        Returns:
            True if payloads match, False otherwise
        """
        try:
            expected_json = self.load_payload_file(expected_file)
            return self.deep_json_compare(actual_json, expected_json)
        except Exception as e:
            print(f"Error validating payload: {e}")
            return False

    def validate_pattern_match(self, response_text: str, pattern: str) -> bool:
        """
        Validate pattern matching in response text.

        Handles Excel patterns with _x000D_ line breaks and supports:
        - String literal matching
        - JSON pattern matching
        - Regex pattern matching (if pattern starts with 'regex:')

        Args:
            response_text: Raw response text to search
            pattern: Pattern to match (from Excel)

        Returns:
            True if pattern found, False otherwise
        """
        # Clean Excel formatting
        cleaned_pattern = self.clean_excel_pattern(pattern)

        # Handle different pattern types
        if cleaned_pattern.startswith("regex:"):
            # Regex pattern matching
            regex_pattern = cleaned_pattern[6:]  # Remove 'regex:' prefix
            try:
                return bool(re.search(regex_pattern, response_text, re.DOTALL))
            except re.error:
                return False
        elif cleaned_pattern.startswith("{") and cleaned_pattern.endswith("}"):
            # JSON pattern matching - check if JSON snippet exists
            return self.json_pattern_match(response_text, cleaned_pattern)
        else:
            # Simple string matching
            return cleaned_pattern in response_text

    def clean_excel_pattern(self, pattern: str) -> str:
        """
        Clean Excel pattern formatting.

        Removes _x000D_ line breaks and normalizes whitespace.
        """
        if pd.isna(pattern):
            return ""

        cleaned = str(pattern)
        # Remove Excel line break encoding
        cleaned = cleaned.replace("_x000D_", "\n")
        # Normalize whitespace but preserve structure
        lines = [line.strip() for line in cleaned.split("\n")]
        return "\n".join(line for line in lines if line)

    def json_pattern_match(
        self, response_text: str, json_pattern: str
    ) -> bool:
        """
        Match JSON pattern within response text.

        Checks if the JSON pattern (partial or complete) exists within
        the response text structure.
        """
        try:
            # Try to parse both response and pattern as JSON
            response_json = json.loads(response_text)
            pattern_json = json.loads(json_pattern)

            # Check if pattern is subset of response
            return self.json_contains_pattern(response_json, pattern_json)
        except json.JSONDecodeError:
            # Fall back to string matching for malformed JSON
            return json_pattern in response_text

    def json_contains_pattern(
        self, response_obj: Any, pattern_obj: Any
    ) -> bool:
        """
        Recursively check if pattern exists in response JSON structure.
        """
        if isinstance(pattern_obj, dict) and isinstance(response_obj, dict):
            # Check if all pattern keys/values exist in response
            for key, value in pattern_obj.items():
                if key not in response_obj:
                    return False
                if not self.json_contains_pattern(response_obj[key], value):
                    return False
            return True
        elif isinstance(pattern_obj, list) and isinstance(response_obj, list):
            # Pattern list should be subset of response list
            for pattern_item in pattern_obj:
                found = any(
                    self.json_contains_pattern(response_item, pattern_item)
                    for response_item in response_obj
                )
                if not found:
                    return False
            return True
        else:
            # Direct value comparison
            return response_obj == pattern_obj

    def load_payload_file(self, filename: str) -> Dict[str, Any]:
        """
        Load JSON payload file with caching.

        Args:
            filename: Name of JSON file in payloads directory

        Returns:
            Parsed JSON data
        """
        if filename in self.payloads_cache:
            return self.payloads_cache[filename]

        file_path = self.payloads_dir / filename
        if not file_path.exists():
            raise FileNotFoundError(f"Payload file not found: {file_path}")

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                payload_data = json.load(f)
            self.payloads_cache[filename] = payload_data
            return payload_data
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in payload file {filename}: {e}")

    def deep_json_compare(self, actual: Any, expected: Any) -> bool:
        """
        Deep comparison of JSON structures.

        Handles nested objects, arrays, and different value types.
        """
        if type(actual) != type(expected):
            return False

        if isinstance(actual, dict):
            if set(actual.keys()) != set(expected.keys()):
                return False
            return all(
                self.deep_json_compare(actual[key], expected[key])
                for key in actual.keys()
            )
        elif isinstance(actual, list):
            if len(actual) != len(expected):
                return False
            return all(
                self.deep_json_compare(actual[i], expected[i])
                for i in range(len(actual))
            )
        else:
            return actual == expected
