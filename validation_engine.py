# validation_engine.py
"""
Validation Engine for TestPilot: Modular, rule-based validation for test steps.
"""
import json
import re
from dataclasses import dataclass
from typing import Any, Dict, Optional
import ast
from deepdiff import DeepDiff

from logger import get_logger
from utils.myutils import compare_dicts_ignore_timestamp
import utils.parse_pattern_match as parse_pattern_match

def check_diff(context: "ValidationContext") -> Optional["ValidationResult"]:
    try:
        # Attempt to parse if they are stringified JSON
        resp = context.response_body
        exp = context.response_payload
        if isinstance(resp, str):
            resp = json.loads(resp)
        if isinstance(exp, str):
            exp = json.loads(exp)
    except Exception:
        resp = context.response_body
        exp = context.response_payload

    diff = DeepDiff(exp, resp, ignore_order=True)
    if diff:
        return ValidationResult(
            False,
            f"Response payload does not match expected payload. Difference: {diff}",
        )
    return ValidationResult(True, "Response payload matches expected payload")


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
        return ValidationResult(False, fail_reason="GET response does not match saved PUT payload")


class PutStatusAndPayloadValidator(ValidationStrategy):
    def validate(self, context: ValidationContext) -> ValidationResult:
        logger = get_logger("ValidationEngine.PutStatusAndPayloadValidator")
        if context.method and context.method.upper() == "PUT":
            try:
                if context.expected_status is None or context.actual_status is None:
                    logger.debug("Expected status or actual status is None")
                    return ValidationResult(
                        False, fail_reason="Expected status or actual status is None"
                    )
                expected_status_int = int(context.expected_status)
                actual_status_int = int(context.actual_status)
                if (expected_status_int in (200, 201)) and (
                    actual_status_int in (200, 201)
                ):
                    logger.debug("PUT: Accepting both 200 and 201 as valid status")
                    pass  # continue to payload check
                elif actual_status_int != expected_status_int:
                    logger.debug(
                        f"Status mismatch: {actual_status_int} != {expected_status_int}"
                    )
                    return ValidationResult(
                        False,
                        fail_reason=f"Status mismatch: {actual_status_int} != {expected_status_int}",
                    )
            except Exception:
                logger.debug(
                    f"Unable to compare status: {context.actual_status} vs {context.expected_status}"
                )
                return ValidationResult(
                    False,
                    fail_reason=f"Unable to compare status: {context.actual_status} vs {context.expected_status}",
                )
        elif context.actual_status != context.expected_status:
            logger.debug(
                f"Status mismatch: {context.actual_status} != {context.expected_status}"
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
                    False, fail_reason="Unknown error during payload comparison"
                )
        logger.debug("PUT status and payload validation passed")
        return ValidationResult(True)


class PutStatusAndPatternValidator(ValidationStrategy):
    def validate(self, context: ValidationContext) -> ValidationResult:
        logger = get_logger("ValidationEngine.PutStatusAndPatternValidator")
        if context.method and context.method.upper() == "PUT":
            try:
                if context.expected_status is None or context.actual_status is None:
                    logger.debug("Expected status or actual status is None")
                    return ValidationResult(
                        False, fail_reason="Expected status or actual status is None"
                    )
                expected_status_int = int(context.expected_status)
                actual_status_int = int(context.actual_status)
                if (expected_status_int in (200, 201)) and (
                    actual_status_int in (200, 201)
                ):
                    logger.debug("PUT: Accepting both 200 and 201 as valid status")
                    pass  # continue to pattern check
                elif actual_status_int != expected_status_int:
                    logger.debug(
                        f"Status mismatch: {actual_status_int} != {expected_status_int}"
                    )
                    return ValidationResult(
                        False,
                        fail_reason=f"Status mismatch: {actual_status_int} != {expected_status_int}",
                    )
            except Exception:
                logger.debug(
                    f"Unable to compare status: {context.actual_status} vs {context.expected_status}"
                )
                return ValidationResult(
                    False,
                    fail_reason=f"Unable to compare status: {context.actual_status} vs {context.expected_status}",
                )
        elif context.actual_status != context.expected_status:
            logger.debug(
                f"Status mismatch: {context.actual_status} != {context.expected_status}"
            )
            return ValidationResult(
                False,
                fail_reason=f"Status mismatch: {context.actual_status} != {context.expected_status}",
            )
        found = False
        if context.pattern_match and context.pattern_match in str(
            context.response_body
        ):
            logger.debug(f"Pattern '{context.pattern_match}' found in response body")
            found = True
        elif (
            context.pattern_match
            and context.response_headers
            and context.pattern_match in str(context.response_headers)
        ):
            logger.debug(f"Pattern '{context.pattern_match}' found in response headers")
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
        logger = get_logger("ValidationEngine.PutStatusPayloadPatternValidator")
        if context.actual_status != context.expected_status:
            logger.debug(
                f"Status mismatch: {context.actual_status} != {context.expected_status}"
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
                    False, fail_reason="Unknown error during payload comparison"
                )

        result = match_patterns_in_headers_and_body(
            context.pattern_match,
            context.response_headers,
            context.response_body,
            logger,
        )
        if result.passed is False:
            logger.debug(f"Pattern matching failed: {result.fail_reason}")
            return result
        return ValidationResult(True)


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
                result = VALIDATION_STRATEGIES["put_status_only"].validate(context)
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
                result = VALIDATION_STRATEGIES["put_status_and_payload"].validate(
                    context
                )
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
                result = VALIDATION_STRATEGIES["put_status_and_pattern"].validate(
                    context
                )
                self.logger.debug(
                    f"Validation outcome: passed={result.passed}, reason={result.fail_reason}"
                )
                return result
            if (
                context.expected_status
                and context.response_payload
                and context.pattern_match
            ):
                self.logger.debug("Selected strategy: put_status_payload_pattern")
                result = VALIDATION_STRATEGIES["put_status_payload_pattern"].validate(
                    context
                )
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
                result = VALIDATION_STRATEGIES["get_compare_with_put"].validate(context)
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
                result = VALIDATION_STRATEGIES["get_status_only"].validate(context)
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
                result = VALIDATION_STRATEGIES["get_status_and_payload"].validate(
                    context
                )
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
                result = VALIDATION_STRATEGIES["get_status_and_pattern"].validate(
                    context
                )
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
                result = VALIDATION_STRATEGIES["delete_status_only"].validate(context)
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
            self.logger.debug(
                f"Validation outcome: passed={result.passed}, reason={result.fail_reason}"
            )
            return result
        self.logger.warning("No matching validation rule implemented for this context")
        return ValidationResult(False, "No matching validation rule implemented yet")


# --- Example: One Strategy Implementation ---


class PutStatusOnlyValidator(ValidationStrategy):
    def validate(self, context: ValidationContext) -> ValidationResult:
        logger = get_logger("ValidationEngine.PutStatusOnlyValidator")
        if context.method and context.method.upper() == "PUT":
            try:
                if context.expected_status is None or context.actual_status is None:
                    logger.debug("Expected status or actual status is None")
                    return ValidationResult(
                        False, fail_reason="Expected status or actual status is None"
                    )
                expected_status_int = int(context.expected_status)
                actual_status_int = int(context.actual_status)
                if (expected_status_int in (200, 201)) and (
                    actual_status_int in (200, 201)
                ):
                    logger.debug("PUT: Accepting both 200 and 201 as valid status")
                    return ValidationResult(True)
                elif actual_status_int != expected_status_int:
                    logger.debug(
                        f"Status mismatch: {actual_status_int} != {expected_status_int}"
                    )
                    return ValidationResult(
                        False,
                        fail_reason=f"Status mismatch: {actual_status_int} != {expected_status_int}",
                    )
            except Exception:
                logger.debug(
                    f"Unable to compare status: {context.actual_status} vs {context.expected_status}"
                )
                return ValidationResult(
                    False,
                    fail_reason=f"Unable to compare status: {context.actual_status} vs {context.expected_status}",
                )
        if context.actual_status == context.expected_status:
            logger.debug("PUT status only validation passed")
            return ValidationResult(True)
        logger.debug(
            f"Status mismatch: {context.actual_status} != {context.expected_status}"
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

        body_str = str(context.response_body or "")
        pattern_str = context.pattern_match.strip() if context.pattern_match else ""

        if not pattern_str:
            logger.debug("No pattern provided to validate")
            return ValidationResult(True)

        # Support comma-separated or newline-separated patterns
        subpatterns = [p.strip() for p in re.split(r"[\n,]+", pattern_str) if p.strip()]
        missing = []

        for pattern in subpatterns:
            if pattern not in body_str:
                missing.append(pattern)

        if missing:
            logger.debug(f"Patterns not found: {missing}")
            return ValidationResult(
                False, fail_reason=f"Patterns not found in kubectl output: {missing}"
            )

        logger.debug(f"All patterns matched in kubectl output: {subpatterns}")
        return ValidationResult(True)


class GetFullValidator(ValidationStrategy):
    def validate(self, context: ValidationContext) -> ValidationResult:
        logger = get_logger("ValidationEngine.GetFullValidator")
        if context.actual_status != context.expected_status:
            logger.debug(
                f"Status mismatch: {context.actual_status} != {context.expected_status}"
            )
            return ValidationResult(
                False,
                fail_reason=f"Status mismatch: {context.actual_status} != {context.expected_status}",
            )
        # No need to check the response_payload here, as we are validating against the expected payload
        result = match_patterns_in_headers_and_body(
            context.pattern_match,
            context.response_headers,
            context.response_body,
            logger,
        )
        if result.passed is False:
            logger.debug(f"Pattern matching failed: {result.fail_reason}")
            return result
        return ValidationResult(True)


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
                    False, fail_reason="Unknown error during payload comparison"
                )
        logger.debug("GET status and payload validation passed")
        return ValidationResult(True)


class GetStatusAndPatternValidator(ValidationStrategy):
    def validate(self, context: ValidationContext) -> ValidationResult:
        logger = get_logger("ValidationEngine.GetStatusAndPatternValidator")

        # Step 1: Check HTTP status
        if context.actual_status != context.expected_status:
            logger.debug(
                f"Status mismatch: {context.actual_status} != {context.expected_status}"
            )
            return ValidationResult(
                False,
                fail_reason=f"Status mismatch: {context.actual_status} != {context.expected_status}",
            )

        # Step 2: Normalize inputs
        # Use the reusable pattern matching function
        result = match_patterns_in_headers_and_body(
            context.pattern_match,
            context.response_headers,
            context.response_body,
            logger,
        )
        if result.passed is False:
            logger.debug(f"Pattern matching failed: {result.fail_reason}")
            return result

        return ValidationResult(True)


def match_patterns_in_headers_and_body(
    pattern: Optional[str],
    headers: Optional[Dict[str, Any]],
    body: Optional[Any],
    logger,
) -> ValidationResult:
    """
    Checks if the pattern exists in the response body or headers.
    Returns ValidationResult(True) if found, otherwise ValidationResult(False, reason).
    """

    # Step 2: Normalize inputs
    pattern_str = pattern.strip() if pattern else ""
    headers = headers or {}
    body_str = str(body or "")

    # Normalize headers to lowercase keys
    headers_dict = (
        {k.lower(): str(v) for k, v in headers.items()}
        if isinstance(headers, dict)
        else {}
    )

    def string_to_dict_regex(s):
        # Pattern to match key: value pairs
        pattern = r'([^:;]+):\s*"?([^";]+)"?'
        matches = re.findall(pattern, s)
        return {key.strip(): value.strip() for key, value in matches}

    patterns = parse_pattern_match.parse_pattern_match_string(pattern_str)
    # Normalize patterns to lowercase keys
    patterns = {k.lower(): str(v) for k, v in patterns.items()} if isinstance(patterns, dict) else {}

    if not patterns:
        logger.error("No patterns provided to validate")
        return ValidationResult(True)
    
    # compare patterns and headers_dict or body_str
    # if no headers and body_str is present then pass body_str as headers_dict
    if not headers and body_str:
        # convert body_str to a dict-like structure
        headers_dict = parse_pattern_match.parse_pattern_match_string(body_str)
 
    
    # compare to find the differences between patterns and headers_dict
    headers_val = {}
    for key, val in patterns.items():
        # if key is not found headers find in response from server
        if headers_dict.get(key) is not None:
            headers_val = string_to_dict_regex(headers_dict.get(key, "{}"))
            # if headers value is {} then check actual header dict and assign 
            if not headers_val and isinstance(headers_dict, dict):
                headers_val = headers_dict
        else:
            headers_val = parse_pattern_match.parse_pattern_match_string(body_str)
            if headers_val:
                headers_val = (
                        {k.lower(): str(v) for k, v in headers_val.items()}
                        if isinstance(headers_val, dict)
                        else {}
                        )

        # if the value itself is a dict in string format below logic 
        # converts str to dict
        if isinstance(val, str):
            try:
                val_dict = ast.literal_eval(val) if val.strip() else {}
            except Exception:
                val_dict = val

        # check the type of val_dict before calling compare_dicts_ignore_timestamp
        # if its other than dict dont pass it to compare_dicts_ignore_timestamp
        if not isinstance(val_dict, dict):
            # checking the length of patterns
            if len(patterns) == 1:
                result = compare_dicts_ignore_timestamp(patterns, headers_val)
            else:
                raise ValueError(
                    "Pattern value is not a dict, cannot compare with headers"
                )
        else:
            result = compare_dicts_ignore_timestamp(val_dict, headers_val)
            
        if result["equal"]:
            logger.debug("All patterns matched in headers")
            return ValidationResult(True)
        else:
            # keys only in dict1
            missing_patterns = result["only_in_dict1"]
            # keys only in dict2
            extra_headers = result["only_in_dict2"]
            # if there are keys present in dict1 and dict2 along with value differences
            # consider the validation failed
            if missing_patterns or extra_headers or result["value_differences"]:
                logger.debug(
                    f"Patterns not found in headers: {missing_patterns}, "
                    f"Extra headers: {extra_headers}, "
                    f"Common keys with value differences: {result['value_differences']}"
                )
                return ValidationResult(False, fail_reason=f"Patterns not found in headers: {missing_patterns}, Extra headers: {extra_headers}, Common keys with value differences: {result['value_differences']}")
            # If no missing patterns, extra headers, or value differences, consider it passed
            logger.info("All patterns matched in headers after comparison")
            return ValidationResult(True)

class DeleteStatusOnlyValidator(ValidationStrategy):
    def validate(self, context: ValidationContext) -> ValidationResult:
        logger = get_logger("ValidationEngine.DeleteStatusOnlyValidator")
        if context.actual_status == context.expected_status:
            logger.debug("DELETE status only validation passed")
            return ValidationResult(True)
        logger.debug(
            f"Status mismatch: {context.actual_status} != {context.expected_status}"
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
