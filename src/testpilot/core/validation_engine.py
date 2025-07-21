def evaluate_validation_result(
    response_payload_match, pattern_match_overall, summary
):
    """
    Evaluate validation result based on response_payload_match and pattern_match_overall values.
    Returns a ValidationResult instance.
    """
    logger = get_logger("ValidationEngine.evaluate_validation_result")
    if response_payload_match is True and pattern_match_overall is True:
        return ValidationResult(True)
    elif response_payload_match is True and pattern_match_overall is False:
        logger.debug(f"Pattern matching failed: {summary}")
        return ValidationResult(False, fail_reason=summary)
    elif response_payload_match is True and pattern_match_overall is None:
        return ValidationResult(True)
    elif response_payload_match is False and pattern_match_overall is True:
        logger.debug(f"Server response payload comparison failed: {summary}")
        return ValidationResult(False, fail_reason=summary)
    elif response_payload_match is False and pattern_match_overall is False:
        logger.debug(
            f"Both server response payload comparison and pattern match failed: {summary}"
        )
        return ValidationResult(False, fail_reason=summary)
    elif response_payload_match is False and pattern_match_overall is None:
        logger.debug(
            f"Server response payload comparison failed, no pattern match performed: {summary}"
        )
        return ValidationResult(False, fail_reason=summary)
    elif response_payload_match is None and pattern_match_overall is True:
        return ValidationResult(True)
    elif response_payload_match is None and pattern_match_overall is False:
        logger.debug(
            f"No server response payload comparison performed, pattern match failed: {summary}"
        )
        return ValidationResult(False, fail_reason=summary)
    elif response_payload_match is None and pattern_match_overall is None:
        logger.debug(f"No validation performed: {summary}")
        return ValidationResult(False, fail_reason=summary)
    else:
        logger.debug(f"Unknown validation result: {summary}")
        return ValidationResult(False, fail_reason=summary)


# validation_engine.py
"""
Validation Engine for TestPilot: Modular, rule-based validation for test steps.
"""
import ast
import json
import os
import re
from dataclasses import dataclass
from typing import Any, Dict, Optional

from deepdiff import DeepDiff

from ..utils import parse_key_strings, parse_pattern_match
from ..utils import pattern_match as ppm
from ..utils.logger import get_logger
from ..utils.myutils import compare_dicts_ignore_timestamp
from .enhanced_response_validator import validate_response_enhanced


# --- Flexible Status Code Range Helper ---
def status_matches(expected, actual):
    """
    Returns True if actual status matches expected.
    - If expected is a string like '2XX', '3XX', '4XX', '5XX', etc., match any status in that range.
    - If expected is a string or int like '200', 200, match exactly.
    - Also supports specific ranges like '400-404' to match a specific range of status codes.
    """
    if expected is None or actual is None:
        return False

    try:
        # Convert actual to int for all comparisons
        actual_int = int(actual)

        # Handle range patterns like '4XX' for any 4XX status code
        if (
            isinstance(expected, str)
            and expected.endswith("XX")
            and len(expected) == 3
            and expected[0].isdigit()
        ):
            base = int(expected[0])
            return 100 * base <= actual_int < 100 * (base + 1)

        # Handle specific range pattern like '400-404'
        elif isinstance(expected, str) and "-" in expected:
            range_parts = expected.split("-")
            if (
                len(range_parts) == 2
                and range_parts[0].isdigit()
                and range_parts[1].isdigit()
            ):
                min_val = int(range_parts[0])
                max_val = int(range_parts[1])
                return min_val <= actual_int <= max_val

        # Handle exact match (either string or int)
        else:
            return actual_int == int(expected)

    except Exception as e:
        logger = get_logger("ValidationEngine.status_matches")
        logger.error(f"Error comparing status codes: {e}")
        return False


def check_diff(context: "ValidationContext") -> Optional["ValidationResult"]:
    try:
        # Attempt to parse if they are stringified JSON
        resp = context.response_body
        exp = context.response_payload

        # If both are strings, try direct string comparison first
        if isinstance(resp, str) and isinstance(exp, str):
            # Remove whitespace and normalize JSON strings
            resp_normalized = resp.strip()
            exp_normalized = exp.strip()

            # If the normalized strings are identical, return success immediately
            if resp_normalized == exp_normalized:
                return ValidationResult(True)

        # If direct comparison didn't match or they're not both strings, try JSON parsing
        if isinstance(resp, str):
            try:
                resp = json.loads(resp)
            except json.JSONDecodeError:
                # Not valid JSON, keep as string
                pass

        if isinstance(exp, str):
            try:
                exp = json.loads(exp)
            except json.JSONDecodeError:
                # Not valid JSON, keep as string
                pass
    except Exception as e:
        # Log the exception but continue with original values
        logger = get_logger("ValidationEngine.check_diff")
        logger.error(f"Error during JSON parsing: {e}")
        resp = context.response_body
        exp = context.response_payload

    # If we get here, either the strings didn't match exactly or we're comparing parsed objects
    try:
        # Add debug logging to see the actual values being compared
        logger = get_logger("ValidationEngine.check_diff")
        logger.debug(
            f"Comparing values: exp={exp} (type={type(exp)}), resp={resp} (type={type(resp)})"
        )

        # Try string normalization again if objects were parsed
        if not isinstance(exp, str) and not isinstance(resp, str):
            # Convert both to JSON strings for consistent comparison
            try:
                exp_json = json.dumps(exp, sort_keys=True)
                resp_json = json.dumps(resp, sort_keys=True)
                if exp_json == resp_json:
                    logger.debug(
                        "JSON string comparison passed after normalization"
                    )
                    return ValidationResult(True)
            except Exception as e:
                logger.debug(f"JSON string normalization failed: {e}")

        # Proceed with DeepDiff comparison
        diff = DeepDiff(exp, resp, ignore_order=True)
        if diff:
            detailed_differences = {
                "difference": diff.to_dict(),
                "expected": exp,
                "actual": resp,
                "expected_type": str(type(exp)),
                "actual_type": str(type(resp)),
            }
            logger.debug(f"DeepDiff found differences: {diff}")
            return ValidationResult(
                False,
                f"Response payload does not match expected payload.",
                details=detailed_differences,
            )
        return ValidationResult(True)
    except Exception as e:
        # If DeepDiff fails, fall back to direct equality check
        logger = get_logger("ValidationEngine.check_diff")
        logger.error(f"DeepDiff comparison failed: {e}")
        if resp == exp:
            return ValidationResult(True)
        return ValidationResult(
            False,
            f"Response payload does not match expected payload and comparison failed.",
        )


# --- Context and Result Data Classes ---


@dataclass
class ValidationContext:
    method: str
    request_payload: Optional[Any]
    expected_status: Optional[int]
    response_payload: Optional[Any]
    pattern_match: Optional[str]
    actual_status: Optional[int]
    response_body: Optional[Any]
    response_headers: Optional[Dict[str, Any]]
    is_kubectl: bool = False
    saved_payload: Optional[Any] = None
    args: Optional[Any] = None
    sheet_name: Optional[str] = (
        None  # Sheet name for enhanced pattern matching
    )
    row_idx: Optional[int] = None  # Row index for enhanced pattern matching
    # Add more as needed


@dataclass
class ValidationResult:
    passed: bool
    fail_reason: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


# --- Strategy Base ---


class ValidationStrategy:
    def validate(self, context: ValidationContext) -> ValidationResult:
        raise NotImplementedError


# --- Dispatcher Skeleton ---


class GetCompareWithPutValidator(ValidationStrategy):
    def validate(self, context: ValidationContext) -> ValidationResult:
        logger = get_logger("ValidationEngine.GetCompareWithPutValidator")
        if context.response_body == context.saved_payload:
            logger.debug("GET response matches saved PUT payload")
            return ValidationResult(True)
        logger.debug("GET response does not match saved PUT payload")

        # Create detailed comparison using DeepDiff
        try:
            resp = context.response_body
            saved = context.saved_payload
            if isinstance(resp, str) and resp.strip():
                resp = json.loads(resp)
            if isinstance(saved, str) and saved.strip():
                saved = json.loads(saved)

            diff = DeepDiff(saved, resp, ignore_order=True)
            if diff:
                detailed_differences = {
                    "expected": saved,
                    "actual": resp,
                    "difference": diff.to_dict(),
                }
                return ValidationResult(
                    False,
                    fail_reason="GET response does not match saved PUT payload",
                    details=detailed_differences,
                )
        except Exception as e:
            logger.debug(f"Error creating detailed comparison: {e}")

        return ValidationResult(
            False, fail_reason="GET response does not match saved PUT payload"
        )


class PutStatusAndPayloadValidator(ValidationStrategy):
    def validate(self, context: ValidationContext) -> ValidationResult:
        logger = get_logger("ValidationEngine.PutStatusAndPayloadValidator")
        if context.expected_status is None or context.actual_status is None:
            logger.debug("Expected status or actual status is None")
            return ValidationResult(
                False, fail_reason="Expected status or actual status is None"
            )
        if not status_matches(context.expected_status, context.actual_status):
            logger.debug(
                f"Status mismatch: {context.actual_status} != {context.expected_status} (range-aware)"
            )
            return ValidationResult(
                False,
                fail_reason=f"Status mismatch: {context.actual_status} != {context.expected_status}",
            )
        if context.response_body != context.response_payload:
            logger.debug(
                "Response body does not match response payload, running check_diff"
            )
            diff_result = check_diff(context)
            if diff_result is not None:
                logger.debug(f"Diff result: {diff_result.fail_reason}")
                return diff_result
            else:
                logger.debug("Unknown error during payload comparison")
                return ValidationResult(
                    False,
                    fail_reason="Unknown error during payload comparison",
                )
        logger.debug("PUT status and payload validation passed")
        return ValidationResult(True)


class PutStatusAndPatternValidator(ValidationStrategy):
    def validate(self, context: ValidationContext) -> ValidationResult:
        logger = get_logger("ValidationEngine.PutStatusAndPatternValidator")
        if context.expected_status is None or context.actual_status is None:
            logger.debug("Expected status or actual status is None")
            return ValidationResult(
                False, fail_reason="Expected status or actual status is None"
            )
        if not status_matches(context.expected_status, context.actual_status):
            logger.debug(
                f"Status mismatch: {context.actual_status} != {context.expected_status} (range-aware)"
            )
            return ValidationResult(
                False,
                fail_reason=f"Status mismatch: {context.actual_status} != {context.expected_status}",
            )
        found = False
        if context.pattern_match and context.pattern_match in str(
            context.response_body
        ):
            logger.debug(
                f"Pattern '{context.pattern_match}' found in response body"
            )
            found = True
        elif (
            context.pattern_match
            and context.response_headers
            and context.pattern_match in str(context.response_headers)
        ):
            logger.debug(
                f"Pattern '{context.pattern_match}' found in response headers"
            )
            found = True
        if not found:
            logger.debug(
                f"Pattern '{context.pattern_match}' not found in response body or headers"
            )
            return ValidationResult(
                False,
                fail_reason=f"Pattern '{context.pattern_match}' not found in response body or headers",
            )
        logger.debug("PUT status and pattern validation passed")
        return ValidationResult(True)


class PutStatusPayloadPatternValidator(ValidationStrategy):
    def validate(self, context: ValidationContext) -> ValidationResult:
        logger = get_logger(
            "ValidationEngine.PutStatusPayloadPatternValidator"
        )
        if context.expected_status is None or context.actual_status is None:
            logger.debug("Expected status or actual status is None")
            return ValidationResult(
                False, fail_reason="Expected status or actual status is None"
            )
        if not status_matches(context.expected_status, context.actual_status):
            logger.debug(
                f"Status mismatch: {context.actual_status} != {context.expected_status} (range-aware)"
            )
            return ValidationResult(
                False,
                fail_reason=f"Status mismatch: {context.actual_status} != {context.expected_status}",
            )
        if context.response_body != context.response_payload:
            logger.debug(
                "Response body does not match response payload, running check_diff"
            )
            diff_result = check_diff(context)
            if diff_result is not None:
                logger.debug(f"Diff result: {diff_result.fail_reason}")
                return diff_result
            else:
                logger.debug("Unknown error during payload comparison")
                return ValidationResult(
                    False,
                    fail_reason="Unknown error during payload comparison",
                )

        result = validate_response_enhanced(
            context.pattern_match,
            context.response_headers,
            context.response_body,
            context.response_payload,
            logger,
            args=context.args,  # Pass args
            sheet_name=context.sheet_name,  # Pass sheet name for enhanced pattern matching
            row_idx=context.row_idx,  # Pass row index for enhanced pattern matching
        )

        return evaluate_validation_result(
            result["dict_match"],  # Response payload comparison result
            result["pattern_match_overall"],
            result["summary"],
        )


class ValidationDispatcher:
    def __init__(self):
        self.logger = get_logger("ValidationEngine.Dispatcher")

    def dispatch(self, context: ValidationContext) -> ValidationResult:
        self.logger.debug(
            f"Dispatching validation for method={context.method}, is_kubectl={context.is_kubectl}, "
            f"expected_status={context.expected_status}, pattern_match={context.pattern_match}, "
            f"response_payload={'present' if context.response_payload else 'none'}, "
            f"saved_payload={'present' if context.saved_payload is not None else 'none'}"
        )
        # PUT rules
        if context.method.upper() == "PUT":
            if (
                context.expected_status
                and not context.response_payload
                and not context.pattern_match
            ):
                self.logger.debug("Selected strategy: put_status_only")
                result = VALIDATION_STRATEGIES["put_status_only"].validate(
                    context
                )
                self.logger.debug(
                    f"Validation outcome: passed={result.passed}, reason={result.fail_reason}"
                )
                return result
            if (
                context.expected_status
                and context.response_payload
                and not context.pattern_match
            ):
                self.logger.debug("Selected strategy: put_status_and_payload")
                result = VALIDATION_STRATEGIES[
                    "put_status_and_payload"
                ].validate(context)
                self.logger.debug(
                    f"Validation outcome: passed={result.passed}, reason={result.fail_reason}"
                )
                return result
            if (
                context.expected_status
                and context.pattern_match
                and not context.response_payload
            ):
                self.logger.debug("Selected strategy: put_status_and_pattern")
                result = VALIDATION_STRATEGIES[
                    "put_status_and_pattern"
                ].validate(context)
                self.logger.debug(
                    f"Validation outcome: passed={result.passed}, reason={result.fail_reason}"
                )
                return result
            if (
                context.expected_status
                and context.response_payload
                and context.pattern_match
            ):
                self.logger.debug(
                    "Selected strategy: put_status_payload_pattern"
                )
                result = VALIDATION_STRATEGIES[
                    "put_status_payload_pattern"
                ].validate(context)
                self.logger.debug(
                    f"Validation outcome: passed={result.passed}, reason={result.fail_reason}"
                )
                return result
        # GET rules
        if context.method.upper() == "GET":
            if context.saved_payload is not None:
                self.logger.debug(
                    "Selected strategy: get_compare_with_put (workflow-aware GET)"
                )
                result = VALIDATION_STRATEGIES[
                    "get_compare_with_put"
                ].validate(context)
                self.logger.debug(
                    f"Validation outcome: passed={result.passed}, reason={result.fail_reason}"
                )
                return result
            if (
                context.expected_status
                and context.response_payload
                and context.pattern_match
            ):
                self.logger.debug("Selected strategy: get_full")
                result = VALIDATION_STRATEGIES["get_full"].validate(context)
                self.logger.debug(
                    f"Validation outcome: passed={result.passed}, reason={result.fail_reason}"
                )
                return result
            if (
                context.expected_status
                and not context.response_payload
                and not context.pattern_match
            ):
                self.logger.debug("Selected strategy: get_status_only")
                result = VALIDATION_STRATEGIES["get_status_only"].validate(
                    context
                )
                self.logger.debug(
                    f"Validation outcome: passed={result.passed}, reason={result.fail_reason}"
                )
                return result
            if (
                context.expected_status
                and context.response_payload
                and not context.pattern_match
            ):
                self.logger.debug("Selected strategy: get_status_and_payload")
                result = VALIDATION_STRATEGIES[
                    "get_status_and_payload"
                ].validate(context)
                self.logger.debug(
                    f"Validation outcome: passed={result.passed}, reason={result.fail_reason}"
                )
                return result
            if (
                context.expected_status
                and context.pattern_match
                and not context.response_payload
            ):
                self.logger.debug("Selected strategy: get_status_and_pattern")
                result = VALIDATION_STRATEGIES[
                    "get_status_and_pattern"
                ].validate(context)
                self.logger.debug(
                    f"Validation outcome: passed={result.passed}, reason={result.fail_reason}"
                )
                return result
        # DELETE rules
        if context.method.upper() == "DELETE":
            if (
                context.expected_status
                and not context.response_payload
                and not context.pattern_match
            ):
                self.logger.debug("Selected strategy: delete_status_only")
                result = VALIDATION_STRATEGIES["delete_status_only"].validate(
                    context
                )
                self.logger.debug(
                    f"Validation outcome: passed={result.passed}, reason={result.fail_reason}"
                )
                return result
        # kubectl log validation
        if context.is_kubectl and context.pattern_match:
            self.logger.debug(
                "Selected strategy: kubectl_pattern (kubectl log validation)"
            )
            result = VALIDATION_STRATEGIES["kubectl_pattern"].validate(context)
            if result is not None:
                self.logger.debug(
                    f"Validation outcome: passed={result.passed}, reason={result.fail_reason}"
                )
                return result

        # self.logger.warning("No matching validation rule implemented for this context")
        return ValidationResult(
            False, "No matching validation rule implemented yet"
        )


# --- Example: One Strategy Implementation ---


class PutStatusOnlyValidator(ValidationStrategy):
    def validate(self, context: ValidationContext) -> ValidationResult:
        logger = get_logger("ValidationEngine.PutStatusOnlyValidator")
        if context.expected_status is None or context.actual_status is None:
            logger.debug("Expected status or actual status is None")
            return ValidationResult(
                False, fail_reason="Expected status or actual status is None"
            )
        if status_matches(context.expected_status, context.actual_status):
            logger.debug("PUT status only validation passed (range-aware)")
            return ValidationResult(True)
        logger.debug(
            f"Status mismatch: {context.actual_status} != {context.expected_status} (range-aware)"
        )
        return ValidationResult(
            False,
            fail_reason=f"Status mismatch: {context.actual_status} != {context.expected_status}",
        )


# --- Registry for strategies (to be expanded) ---

# Move all validator class definitions above this block so they are defined before use


class KubectlPatternValidator(ValidationStrategy):
    def validate(self, context: ValidationContext) -> ValidationResult:
        logger = get_logger("ValidationEngine.KubectlPatternValidator")

        # fetch the response body from server
        response_body = context.response_body
        if isinstance(response_body, str):
            try:
                response_body = json.loads(response_body)
                logger.debug(
                    "Parsed response_body string to dict/list for comparison."
                )
            except json.JSONDecodeError:
                response_body = response_body  # fallback to string

        # now split the lines using \n
        try:
            if response_body is not None:
                lines = response_body.split("\n")
                for line in lines:
                    result = validate_response_enhanced(
                        context.pattern_match,
                        context.response_headers,
                        line,  # Use each line as the response body
                        context.response_payload,
                        logger,
                        args=context.args,  # Pass args
                        sheet_name=context.sheet_name,  # Pass sheet name for enhanced pattern matching
                        row_idx=context.row_idx,  # Pass row index for enhanced pattern matching
                    )
                    if result["pattern_match_overall"] is True:
                        logger.info(
                            f"Pattern '{context.pattern_match}' found in line: {line}"
                        )
                        return ValidationResult(True)
            # If no pattern match found, return failure
            logger.debug(
                f"Pattern '{context.pattern_match}' not found in any line of response body"
            )
            return ValidationResult(
                False,
                fail_reason=f"Pattern '{context.pattern_match}' not found in any line of response body",
            )
        except Exception as e:
            logger.error(f"Error processing response body: {e}")
            return ValidationResult(
                False, fail_reason=f"Error processing response body: {e}"
            )


class GetFullValidator(ValidationStrategy):
    def validate(self, context: ValidationContext) -> ValidationResult:
        logger = get_logger("ValidationEngine.GetFullValidator")
        if context.expected_status is None or context.actual_status is None:
            logger.debug("Expected status or actual status is None")
            return ValidationResult(
                False, fail_reason="Expected status or actual status is None"
            )
        if not status_matches(context.expected_status, context.actual_status):
            logger.debug(
                f"Status mismatch: {context.actual_status} != {context.expected_status} (range-aware)"
            )
            return ValidationResult(
                False,
                fail_reason=f"Status mismatch: {context.actual_status} != {context.expected_status}",
            )
        # No need to check the response_payload here, as we are validating against the expected payload
        result = validate_response_enhanced(
            context.pattern_match,
            context.response_headers,
            context.response_body,
            context.response_payload,
            logger,
            args=context.args,  # Pass args
            sheet_name=context.sheet_name,  # Pass sheet name for enhanced pattern matching
            row_idx=context.row_idx,  # Pass row index for enhanced pattern matching
        )
        return evaluate_validation_result(
            result["dict_match"],  # Response payload comparison result
            result["pattern_match_overall"],
            result["summary"],
        )


class GetStatusOnlyValidator(ValidationStrategy):
    def validate(self, context: ValidationContext) -> ValidationResult:
        logger = get_logger("ValidationEngine.GetStatusOnlyValidator")
        if context.actual_status == context.expected_status:
            logger.debug("GET status only validation passed")
            return ValidationResult(True)
        logger.debug(
            f"Status mismatch: {context.actual_status} != {context.expected_status}"
        )
        return ValidationResult(
            False,
            fail_reason=f"Status mismatch: {context.actual_status} != {context.expected_status}",
        )


class GetStatusAndPayloadValidator(ValidationStrategy):
    def validate(self, context: ValidationContext) -> ValidationResult:
        logger = get_logger("ValidationEngine.GetStatusAndPayloadValidator")
        if context.actual_status != context.expected_status:
            logger.debug(
                f"Status mismatch: {context.actual_status} != {context.expected_status}"
            )
            return ValidationResult(
                False,
                fail_reason=f"Status mismatch: {context.actual_status} != {context.expected_status}",
            )

        results = validate_response_enhanced(
            context.pattern_match,
            context.response_headers,
            context.response_body,
            context.response_payload,
            logger,
            args=context.args,  # Pass args
            sheet_name=context.sheet_name,  # Pass sheet name for enhanced pattern matching
            row_idx=context.row_idx,  # Pass row index for enhanced pattern matching
        )
        response_payload_match = results[
            "dict_match"
        ]  # Response payload comparison result
        pattern_match_overall = results["pattern_match_overall"]
        summary = results["summary"]

        # Use reusable function for result evaluation
        return evaluate_validation_result(
            response_payload_match, pattern_match_overall, summary
        )


class GetStatusAndPatternValidator(ValidationStrategy):
    def validate(self, context: ValidationContext) -> ValidationResult:
        logger = get_logger("ValidationEngine.GetStatusAndPatternValidator")

        # Step 1: Check HTTP status
        if context.expected_status is None or context.actual_status is None:
            logger.debug("Expected status or actual status is None")
            return ValidationResult(
                False, fail_reason="Expected status or actual status is None"
            )
        if not status_matches(context.expected_status, context.actual_status):
            logger.debug(
                f"Status mismatch: {context.actual_status} != {context.expected_status} (range-aware)"
            )
            return ValidationResult(
                False,
                fail_reason=f"Status mismatch: {context.actual_status} != {context.expected_status}",
            )

        # Step 2: Normalize inputs
        # Use the reusable pattern matching function
        result = validate_response_enhanced(
            context.pattern_match,
            context.response_headers,
            context.response_body,
            context.response_payload,
            logger,
            args=context.args,  # Pass args
            sheet_name=context.sheet_name,  # Pass sheet name for enhanced pattern matching
            row_idx=context.row_idx,  # Pass row index for enhanced pattern matching
        )

        return evaluate_validation_result(
            result["dict_match"],  # Response payload comparison result
            result["pattern_match_overall"],
            result["summary"],
        )


def load_enhanced_pattern_matches(
    sheet_name: str, row_idx: int
) -> Optional[Dict]:
    """
    Load enhanced pattern matches from the JSON file based on sheet name and row index.
    Returns the converted_pattern if found, None otherwise.
    """
    try:
        # Find all pattern files in the patterns directory
        # Try multiple possible locations for patterns directory
        pattern_dirs = [
            os.path.join(
                os.getcwd(), "examples", "patterns"
            ),  # Project root patterns
            os.path.join(
                os.path.dirname(
                    os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
                ),
                "examples",
                "patterns",
            ),  # Absolute path from module
            os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "patterns"
            ),  # Legacy path
        ]

        pattern_files = []
        pattern_dir = None

        # Try each possible pattern directory
        for dir_path in pattern_dirs:
            if os.path.exists(dir_path) and os.path.isdir(dir_path):
                pattern_dir = dir_path
                try:
                    pattern_files = [
                        f
                        for f in os.listdir(pattern_dir)
                        if f.endswith("enhanced_pattern_matches.json")
                    ]
                    if (
                        pattern_files
                    ):  # If we found pattern files, break the loop
                        break
                except Exception:
                    continue

        for file_name in pattern_files:
            if pattern_dir is not None:
                file_path = os.path.join(pattern_dir, file_name)
                with open(file_path, "r") as f:
                    pattern_data = json.load(f)

                if "enhanced_patterns" in pattern_data:
                    # Check if the sheet exists in the enhanced pattern matches
                    if sheet_name in pattern_data["enhanced_patterns"]:
                        # Find the entry with matching row_number
                        for entry in pattern_data["enhanced_patterns"][
                            sheet_name
                        ]:
                            if entry.get("row_number") == row_idx:
                                return entry.get("converted_pattern")
    except Exception as e:
        # Log error but continue with normal pattern matching
        logger = get_logger("ValidationEngine.EnhancedPatternMatcher")
        logger.error(f"Error loading enhanced pattern matches: {e}")

    return None


# --- Pattern Matching Logic ---
# The following function is now replaced by validate_response_enhanced for migration.
# def match_patterns_in_headers_and_body(
#     pattern: Optional[str],
#     headers: Optional[Dict[str, Any]],
#     body: Optional[Any],
#     logger,
#     args=None,  # <-- add args parameter
#     sheet_name: Optional[str] = None,  # Sheet name for enhanced pattern matching
#     row_idx: Optional[int] = None,  # Row index for enhanced pattern matching
# ) -> ValidationResult:
#     ...

# Replace all usages of match_patterns_in_headers_and_body with validate_response_enhanced
# Example usage in validators:
# result = match_patterns_in_headers_and_body(...)
# becomes:
# result = validate_response_enhanced(pattern, headers, body, logger, config, args, sheet_name, row_idx)


class DeleteStatusOnlyValidator(ValidationStrategy):
    def validate(self, context: ValidationContext) -> ValidationResult:
        logger = get_logger("ValidationEngine.DeleteStatusOnlyValidator")
        if context.expected_status is None or context.actual_status is None:
            logger.debug("Expected status or actual status is None")
            return ValidationResult(
                False, fail_reason="Expected status or actual status is None"
            )
        if status_matches(context.expected_status, context.actual_status):
            logger.debug("DELETE status only validation passed (range-aware)")
            return ValidationResult(True)
        logger.debug(
            f"Status mismatch: {context.actual_status} != {context.expected_status} (range-aware)"
        )
        return ValidationResult(
            False,
            fail_reason=f"Status mismatch: {context.actual_status} != {context.expected_status}",
        )


VALIDATION_STRATEGIES = {
    "put_status_only": PutStatusOnlyValidator(),
    "put_status_and_payload": PutStatusAndPayloadValidator(),
    "put_status_and_pattern": PutStatusAndPatternValidator(),
    "put_status_payload_pattern": PutStatusPayloadPatternValidator(),
    "get_compare_with_put": GetCompareWithPutValidator(),
    "get_full": GetFullValidator(),
    "get_status_only": GetStatusOnlyValidator(),
    "get_status_and_payload": GetStatusAndPayloadValidator(),
    "get_status_and_pattern": GetStatusAndPatternValidator(),
    "kubectl_pattern": KubectlPatternValidator(),
    "delete_status_only": DeleteStatusOnlyValidator(),
    # Add more as we go
}
