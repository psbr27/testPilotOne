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
import pattern_match as ppm
from logger import get_logger
from utils.myutils import compare_dicts_ignore_timestamp
import utils.parse_pattern_match as parse_pattern_match
import utils.parse_key_strings as parse_key_strings


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
    args: Optional[Any] = None  # <-- Add args to context
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
        return ValidationResult(
            False, fail_reason="GET response does not match saved PUT payload"
        )


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
            args=context.args,  # Pass args
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
            if result is not None:
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

        # convert pattern_str to a dict
        pattern_dict = parse_pattern_match.parse_pattern_match_string(pattern_str)

        # if body_str is a string convert to json object
        if isinstance(body_str, str):
            try:
                # split body_str "\n"
                body_str = body_str.split("\n")
                for item in body_str:
                    if isinstance(item, str):
                        item = item.strip()
                        item_json = json.loads(item)
                        # fetch the keys from pattern_dict
                        keys_list = pattern_dict.keys()
                        for key in keys_list:
                            # use key to fetch the value from item_json
                            if key in item_json:
                                if item_json[key] == pattern_dict[key]:
                                    logger.debug(
                                        f"Pattern '{key}' matched in response body"
                                    )
                                    return ValidationResult(True)
                        # now check if the message has the pattern from item_json
                        # retrieve message from item_json
                        kubectl_message = {}
                        kubectl_message["message"] = item_json.get("message", "")
                        if kubectl_message:
                            message_dict = parse_key_strings.parse_log_string_to_dict(
                                kubectl_message
                            )
                            if message_dict:
                                # retrieve the headers from message_dict
                                logger.info(
                                    "Found User-Agent header in message_dict {message_dict}"
                                )
                                headers = message_dict.get("headers", {})
                                if headers:
                                    # retrieve user-agent from headers
                                    user_agent = headers.get(", User-Agent", "")
                                    for key in keys_list:
                                        # retrieve the value from pattern_dict
                                        pattern_user_agent = pattern_dict.get(key, "")
                                        if user_agent == pattern_user_agent:
                                            logger.debug(
                                                f"Pattern '{key}' matched in User-Agent header"
                                            )
                                            return ValidationResult(True)
                                        else:
                                            logger.debug(
                                                f"Pattern '{key}' did not match User-Agent header: {user_agent} != {pattern_user_agent}"
                                            )
                                            return ValidationResult(
                                                False,
                                                fail_reason=f"Pattern '{key}' did not match User-Agent header: {user_agent} != {pattern_user_agent}",
                                            )

            except json.JSONDecodeError:
                logger.error("Invalid JSON format in response body")
                return ValidationResult(
                    False, fail_reason="Invalid JSON format in response body"
                )
        else:
            # fail it here
            return ValidationResult(
                False, fail_reason="Response body is not a valid JSON object"
            )


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
            args=context.args,  # Pass args
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
            args=context.args,  # Pass args
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
    args=None,  # <-- add args parameter
) -> ValidationResult:
    """
    Checks if the pattern exists in the response body or headers.
    Returns ValidationResult(True) if found, otherwise ValidationResult(False, reason).
    """
    # Example usage:
    if args is not None and getattr(args, "module", None) == "audit":
        logger.debug("Audit module detected in match_patterns_in_headers_and_body")
        # for audit assume pattern_match is a dict and compare with response body
        pattern = str(pattern or "")
        if isinstance(pattern, str):
            # if pattern is a string and not a dict then
            # convert it to a JSON object for a comparison
            try:
                pattern_json = json.loads(pattern)
            except json.JSONDecodeError:
                logger.error("Invalid JSON format in pattern")
                return ValidationResult(
                    False, fail_reason="Invalid JSON format in pattern"
                )
        # now fetch response from body and compare with pattern
        body_str = str(body or "")
        if isinstance(body_str, str):
            try:
                body_json = json.loads(body_str)
            except json.JSONDecodeError:
                logger.error("Invalid JSON format in response body")
                return ValidationResult(
                    False, fail_reason="Invalid JSON format in response body"
                )
        pattern_match_for_response_payload, match_dict_payload = (
            ppm.check_json_pattern_match(
                pattern=pattern_json,
                response=body_json,
            )
        )
        logger.info(f"Pattern match result: {pattern_match_for_response_payload}")
        match_percentage = int(match_dict_payload.get("overall_match_percent", 0))
        if pattern_match_for_response_payload and match_percentage == 100:
            logger.debug("Pattern matched in response payload")
            return ValidationResult(True)
        else:
            return ValidationResult(
                False,
                fail_reason=f"Pattern did not match in response payload. Match percentage: {match_percentage}",
            )

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
    patterns = (
        {k.lower(): str(v) for k, v in patterns.items()}
        if isinstance(patterns, dict)
        else {}
    )

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
            if isinstance(body_str, str):
                # convert body_str to JSON object if it is a string
                body_json = {}
                try:
                    body_json = json.loads(body_str)
                except json.JSONDecodeError:
                    # catch the exception and do nothing
                    pass

            # if body_json is not empty then check if it a type <class, list>
            if isinstance(body_json, list):
                for item in body_json:
                    if isinstance(item, dict):
                        # lower keys
                        item = (
                            {k.lower(): str(v) for k, v in item.items()}
                            if isinstance(item, dict)
                            else {}
                        )
                        # use key and compare the values
                        if item[key] == val:
                            return ValidationResult(True)
                        else:
                            return ValidationResult(
                                False,
                                fail_reason=f"Pattern '{key}' did not match in response body: {item[key]} != {val}",
                            )

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
            # check if 3gpp headers are present if so then no need to compare just return True
            if "3gpp-sbi-lci" in key or "3gpp-sbi-oci" in key:
                # looks like a 3gpp header verification is required in response body
                # check if headers_val is a dict and has 3gpp key
                if headers_dict:
                    if headers_dict.get(key) is not None:
                        logger.debug("3gpp header found in response headers")
                        return ValidationResult(True)
                    else:
                        logger.debug("3gpp header not found in response headers")
                        return ValidationResult(
                            False,
                            fail_reason="3gpp header not found in response headers",
                        )
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
                return ValidationResult(
                    False,
                    fail_reason=f"Patterns not found in headers: {missing_patterns}, Extra headers: {extra_headers}, Common keys with value differences: {result['value_differences']}",
                )
            # If no missing patterns, extra headers, or value differences, consider it passed
            logger.info("All patterns matched in headers after comparison")
            return ValidationResult(True)
    # If the loop completes without returning, return a default ValidationResult
    logger.error(
        "Pattern matching did not return a result; returning failure by default"
    )
    return ValidationResult(
        False, fail_reason="Pattern matching did not return a result"
    )


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
