#!/usr/bin/env python3
"""
Audit Engine for TestPilot - Provides 100% pattern matching validation
and comprehensive audit trail generation for compliance testing.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

# Import with fallback for logger
try:
    from ..utils.logger import get_logger

    logger = get_logger("TestPilot.Audit")
except ImportError:
    import logging

    logger = logging.getLogger("TestPilot.Audit")

# Import pattern matching with fallback
try:
    from ..utils.pattern_match import (
        check_json_pattern_match,
        enhance_collect_differences,
    )
except ImportError:
    # Provide basic fallback implementations
    def enhance_collect_differences(expected, actual):
        """Fallback difference collection"""
        differences = []
        if expected != actual:
            differences.append(("mismatch", "root", expected, actual))
        return differences

    def check_json_pattern_match(expected, actual, partial_match=False):
        """Fallback pattern matching"""
        import json

        try:
            if isinstance(expected, str):
                expected = json.loads(expected)
            if isinstance(actual, str):
                actual = json.loads(actual)
            match = expected == actual
            return match, {
                "diffs": [],
                "matches": [],
                "overall_match_percent": 100 if match else 0,
            }
        except json.JSONDecodeError:
            return False, {
                "diffs": [("error", "json_parse", "Invalid JSON", None)],
                "matches": [],
                "overall_match_percent": 0,
            }


class AuditEngine:
    """
    Audit Engine that enforces 100% pattern matching and generates
    comprehensive audit trails for compliance testing.
    """

    def __init__(self):
        self.audit_results = []
        self.strict_mode = True  # Always enforce 100% matching in audit mode

    def validate_response(
        self,
        test_name: str,
        expected_pattern: str,
        actual_response: str,
        http_method_expected: str = None,
        http_method_actual: str = None,
        status_code_expected: int = None,
        status_code_actual: int = None,
        request_details: Dict = None,
    ) -> Dict[str, Any]:
        """
        Perform 100% strict validation of response against expected pattern.

        Args:
            test_name: Name of the test being executed
            expected_pattern: Expected JSON pattern from Excel
            actual_response: Actual server response
            http_method_expected: Expected HTTP method
            http_method_actual: Actual HTTP method used
            status_code_expected: Expected HTTP status code
            status_code_actual: Actual HTTP status code
            request_details: Additional request metadata

        Returns:
            Dict containing comprehensive audit results
        """
        audit_result = {
            "test_name": test_name,
            "timestamp": datetime.utcnow().isoformat(),
            "validation_type": "STRICT_100_PERCENT",
            "expected_pattern": expected_pattern,
            "actual_response": actual_response,
            "http_method_expected": http_method_expected,
            "http_method_actual": http_method_actual,
            "status_code_expected": status_code_expected,
            "status_code_actual": status_code_actual,
            "request_details": request_details or {},
            "differences": [],
            "http_validation_errors": [],
            "json_validation_errors": [],
            "overall_result": "UNKNOWN",
        }

        try:
            # Step 1: HTTP Method Validation
            http_method_valid = self._validate_http_method(
                http_method_expected, http_method_actual, audit_result
            )

            # Step 2: HTTP Status Code Validation
            status_code_valid = self._validate_status_code(
                status_code_expected, status_code_actual, audit_result
            )

            # Step 3: JSON Structure Validation
            json_structure_valid = self._validate_json_structure(
                actual_response, audit_result
            )

            # Step 4: 100% Pattern Matching Validation
            pattern_match_valid = self._validate_pattern_match(
                expected_pattern, actual_response, audit_result
            )

            # Step 5: Overall Result Determination
            overall_valid = (
                http_method_valid
                and status_code_valid
                and json_structure_valid
                and pattern_match_valid
            )

            # Only set the result if it hasn't been set to ERROR by a sub-method
            if audit_result["overall_result"] != "ERROR":
                audit_result["overall_result"] = (
                    "PASS" if overall_valid else "FAIL"
                )

            # Log result
            if overall_valid:
                logger.info(
                    f"✅ AUDIT PASS: {test_name} - 100% validation successful"
                )
            else:
                logger.warning(
                    f"❌ AUDIT FAIL: {test_name} - Validation failures detected"
                )

        except Exception as e:
            logger.error(f"Audit validation error for {test_name}: {e}")
            audit_result["overall_result"] = "ERROR"
            audit_result["json_validation_errors"].append(
                f"Validation exception: {str(e)}"
            )

        # Store result for batch export
        self.audit_results.append(audit_result)
        return audit_result

    def _validate_http_method(
        self, expected: str, actual: str, audit_result: Dict
    ) -> bool:
        """Validate HTTP method matches exactly."""
        if expected is None or actual is None:
            if expected != actual:
                audit_result["http_validation_errors"].append(
                    f"HTTP method mismatch: expected '{expected}', got '{actual}'"
                )
                return False
            return True

        if expected.upper() != actual.upper():
            audit_result["http_validation_errors"].append(
                f"HTTP method mismatch: expected '{expected}', got '{actual}'"
            )
            return False
        return True

    def _validate_status_code(
        self, expected: int, actual: int, audit_result: Dict
    ) -> bool:
        """Validate HTTP status code matches exactly."""
        if expected is None or actual is None:
            if expected != actual:
                audit_result["http_validation_errors"].append(
                    f"Status code mismatch: expected '{expected}', got '{actual}'"
                )
                return False
            return True

        if expected != actual:
            audit_result["http_validation_errors"].append(
                f"Status code mismatch: expected {expected}, got {actual}"
            )
            return False
        return True

    def _validate_json_structure(
        self, response: str, audit_result: Dict
    ) -> bool:
        """Validate that response is valid JSON."""
        # Empty strings should be treated as ERROR (system error)
        if response == "":
            audit_result["json_validation_errors"].append(
                "Invalid JSON structure: Empty response"
            )
            audit_result["overall_result"] = "ERROR"
            return False
        try:
            json.loads(response)
            return True
        except json.JSONDecodeError as e:
            audit_result["json_validation_errors"].append(
                f"Invalid JSON structure: {str(e)}"
            )
            return False

    def _validate_pattern_match(
        self, expected_pattern: str, actual_response: str, audit_result: Dict
    ) -> bool:
        """
        Perform 100% strict pattern matching validation.
        No partial matches allowed in audit mode.
        """
        try:
            # Parse JSON strings
            if isinstance(expected_pattern, str):
                expected_dict = json.loads(expected_pattern)
            else:
                expected_dict = expected_pattern

            if isinstance(actual_response, str):
                actual_dict = json.loads(actual_response)
            else:
                actual_dict = actual_response

            # Use strict pattern matching (partial_match=False)
            match_result, match_details = check_json_pattern_match(
                expected_dict, actual_dict, partial_match=False
            )

            # Collect all differences for audit trail using strict comparison
            differences = self._strict_collect_differences(
                expected_dict, actual_dict
            )

            # Format differences for audit report
            formatted_differences = []
            for diff_type, key_path, expected_val, actual_val in differences:
                formatted_differences.append(
                    {
                        "type": diff_type,
                        "field_path": key_path,
                        "expected_value": expected_val,
                        "actual_value": actual_val,
                    }
                )

            audit_result["differences"] = formatted_differences
            audit_result["match_percentage"] = match_details.get(
                "overall_match_percent", 0
            )

            # In audit mode, only 100% matches are acceptable
            if not match_result or len(differences) > 0:
                audit_result["json_validation_errors"].append(
                    f"Pattern match failed: {len(differences)} differences found"
                )
                return False

            return True

        except Exception as e:
            audit_result["json_validation_errors"].append(
                f"Pattern matching error: {str(e)}"
            )
            return False

    def _strict_collect_differences(
        self, expected: Any, actual: Any, parent_key: str = ""
    ) -> List[Tuple[str, str, Any, Any]]:
        """
        Strict difference collection that respects array order for audit mode.
        Unlike the standard enhance_collect_differences, this treats arrays as ordered.
        """
        diffs = []

        if isinstance(expected, dict) and isinstance(actual, dict):
            # Check for missing keys
            for key in expected:
                full_key = f"{parent_key}.{key}" if parent_key else key
                if key not in actual:
                    diffs.append(("missing", full_key, expected[key], None))
                else:
                    diffs.extend(
                        self._strict_collect_differences(
                            expected[key], actual[key], full_key
                        )
                    )

            # Check for extra keys
            for key in actual:
                if key not in expected:
                    full_key = f"{parent_key}.{key}" if parent_key else key
                    diffs.append(("extra", full_key, None, actual[key]))

        elif isinstance(expected, list) and isinstance(actual, list):
            # Strict array comparison - order matters
            max_len = max(len(expected), len(actual))
            for i in range(max_len):
                sub_key = f"{parent_key}[{i}]" if parent_key else f"[{i}]"

                if i >= len(expected):
                    diffs.append(("extra", sub_key, None, actual[i]))
                elif i >= len(actual):
                    diffs.append(("missing", sub_key, expected[i], None))
                else:
                    diffs.extend(
                        self._strict_collect_differences(
                            expected[i], actual[i], sub_key
                        )
                    )

        elif expected != actual:
            diffs.append(("mismatch", parent_key or "root", expected, actual))

        return diffs

    def generate_audit_summary(self) -> Dict[str, Any]:
        """Generate comprehensive audit summary."""
        total_tests = len(self.audit_results)
        passed_tests = len(
            [r for r in self.audit_results if r["overall_result"] == "PASS"]
        )
        failed_tests = len(
            [r for r in self.audit_results if r["overall_result"] == "FAIL"]
        )
        error_tests = len(
            [r for r in self.audit_results if r["overall_result"] == "ERROR"]
        )

        return {
            "audit_mode": "STRICT_100_PERCENT",
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "error_tests": error_tests,
            "pass_rate": (
                (passed_tests / total_tests * 100) if total_tests > 0 else 0
            ),
            "compliance_status": (
                "COMPLIANT"
                if failed_tests == 0 and error_tests == 0
                else "NON_COMPLIANT"
            ),
            "generated_at": datetime.utcnow().isoformat(),
        }

    def get_audit_results(self) -> List[Dict[str, Any]]:
        """Get all audit results for export."""
        return self.audit_results

    def clear_results(self):
        """Clear stored audit results."""
        self.audit_results = []
