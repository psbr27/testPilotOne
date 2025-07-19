# validation_engine.py
"""
Validation Engine for TestPilot: Modular, rule-based validation for test steps.
"""
import json
import re
from dataclasses import dataclass
from typing import Any, Dict, Optional
import ast
import os
from deepdiff import DeepDiff

from logger import get_logger
from utils.myutils import compare_dicts_ignore_timestamp
import utils.parse_pattern_match as parse_pattern_match
<<<<<<< Updated upstream
=======
import utils.parse_key_strings as parse_key_strings

# --- Flexible Status Code Range Helper ---
def status_matches(expected, actual):
    """
    Returns True if actual status matches expected.
    - If expected is a string like '2XX', '3XX', etc., match any status in that range.
    - If expected is a string or int like '200', 200, match exactly.
    """
    if expected is None or actual is None:
        return False
    try:
        if isinstance(expected, str) and expected.endswith("XX") and len(expected) == 3 and expected[0].isdigit():
            base = int(expected[0])
            return 100 * base <= int(actual) < 100 * (base + 1)
        else:
            return int(expected) == int(actual)
    except Exception:
        return False
>>>>>>> Stashed changes

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
    return ValidationResult(True)


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
<<<<<<< Updated upstream
=======
    args: Optional[Any] = None
    sheet_name: Optional[str] = None  # Sheet name for enhanced pattern matching
    row_idx: Optional[int] = None  # Row index for enhanced pattern matching
>>>>>>> Stashed changes
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
                    False, fail_reason="Unknown error during payload comparison"
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
                    False, fail_reason="Unknown error during payload comparison"
                )

        result = match_patterns_in_headers_and_body(
            context.pattern_match,
            context.response_headers,
            context.response_body,
            logger,
<<<<<<< Updated upstream
=======
            args=context.args,  # Pass args
            sheet_name=context.sheet_name,  # Pass sheet name for enhanced pattern matching
            row_idx=context.row_idx,  # Pass row index for enhanced pattern matching
>>>>>>> Stashed changes
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
<<<<<<< Updated upstream
            self.logger.debug(
                f"Validation outcome: passed={result.passed}, reason={result.fail_reason}"
            )
            return result
        self.logger.warning("No matching validation rule implemented for this context")
=======
            if result is not None:
                self.logger.debug(
                    f"Validation outcome: passed={result.passed}, reason={result.fail_reason}"
                )
                return result


        #self.logger.warning("No matching validation rule implemented for this context")
>>>>>>> Stashed changes
        return ValidationResult(False, "No matching validation rule implemented yet")


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

<<<<<<< Updated upstream
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
=======
        # Check for enhanced pattern matches if sheet_name and row_idx are provided
        if context.sheet_name is not None and context.row_idx is not None:
            try:
                # increment row index to match 
                row_idx_adjusted = context.row_idx + 1  # Create a copy to avoid modifying the original
                enhanced_pattern = load_enhanced_pattern_matches(context.sheet_name, row_idx_adjusted)
                if enhanced_pattern:
                    logger.debug(f"Found enhanced pattern match for sheet '{context.sheet_name}' row {row_idx_adjusted}")
                    
                    # Process based on pattern_type
                    if enhanced_pattern.get("pattern_type") == "json_extracted":
                        pattern_data = enhanced_pattern.get("data", {})
                        body_str = str(context.response_body or "")
                        
                        # Try to find JSON objects in kubectl output lines
                        try:
                            lines = body_str.split("\n")
                            for line in lines:
                                line = line.strip()
                                if not line:
                                    continue
                                    
                                try:
                                    line_json = json.loads(line)
                                    # Check if all keys and values in pattern_data exist in line_json
                                    match_found = False
                                    expected_value = None
                                    for key, expected_value in pattern_data.items():
                                        if key in line_json:
                                            # exact match
                                            if line_json[key] == expected_value:
                                                match_found = True
                                                break   
                                            # substring match
                                            elif expected_value in line_json[key]:
                                                logger.info(f"Found phrase {expected_value} in {line_json[key]}")
                                                match_found = True
                                                break                                            
                                    if match_found:
                                        return ValidationResult(True)
                                except json.JSONDecodeError:
                                    # Not a JSON line, continue to next line
                                    continue
                        except Exception as e:
                            logger.error(f"Error processing kubectl output with enhanced pattern: {e}")
                            # Don't return here, continue to try other validation methods
            except Exception as e:
                logger.error(f"Error in enhanced pattern matching: {e}")
                # Continue to try other validation methods
        
        # If we reach here, either there was no enhanced pattern match or it failed
        # Fall back to default pattern matching or return failure
        logger.debug("No enhanced pattern match found or pattern matching failed")
        return ValidationResult(False, fail_reason="Pattern not found in kubectl logs")
>>>>>>> Stashed changes

        logger.debug(f"All patterns matched in kubectl output: {subpatterns}")
        return ValidationResult(True)


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
        result = match_patterns_in_headers_and_body(
            context.pattern_match,
            context.response_headers,
            context.response_body,
            logger,
<<<<<<< Updated upstream
=======
            args=context.args,  # Pass args
            sheet_name=context.sheet_name,  # Pass sheet name for enhanced pattern matching
            row_idx=context.row_idx,  # Pass row index for enhanced pattern matching
>>>>>>> Stashed changes
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
        result = match_patterns_in_headers_and_body(
            context.pattern_match,
            context.response_headers,
            context.response_body,
            logger,
<<<<<<< Updated upstream
=======
            args=context.args,  # Pass args
            sheet_name=context.sheet_name,  # Pass sheet name for enhanced pattern matching
            row_idx=context.row_idx,  # Pass row index for enhanced pattern matching
>>>>>>> Stashed changes
        )
        if result.passed is False:
            logger.debug(f"Pattern matching failed: {result.fail_reason}")
            return result

        return ValidationResult(True)


def load_enhanced_pattern_matches(sheet_name: str, row_idx: int) -> Optional[Dict]:
    """
    Load enhanced pattern matches from the JSON file based on sheet name and row index.
    Returns the converted_pattern if found, None otherwise.
    """
    try:
        # Find all pattern files in the patterns directory
        pattern_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "patterns")
        pattern_files = [f for f in os.listdir(pattern_dir) if f.endswith("enhanced_pattern_matches.json")]
        
        for file_name in pattern_files:
            file_path = os.path.join(pattern_dir, file_name)
            with open(file_path, 'r') as f:
                pattern_data = json.load(f)
                
            if "enhanced_patterns" in pattern_data:
                # Check if the sheet exists in the enhanced pattern matches
                if sheet_name in pattern_data["enhanced_patterns"]:
                    # Find the entry with matching row_number
                    for entry in pattern_data["enhanced_patterns"][sheet_name]:
                        if entry.get("row_number") == row_idx:
                            return entry.get("converted_pattern")
    except Exception as e:
        # Log error but continue with normal pattern matching
        logger = get_logger("ValidationEngine.EnhancedPatternMatcher")
        logger.error(f"Error loading enhanced pattern matches: {e}")
    
    return None


def match_patterns_in_headers_and_body(
    pattern: Optional[str],
    headers: Optional[Dict[str, Any]],
    body: Optional[Any],
    logger,
<<<<<<< Updated upstream
=======
    args=None,  # <-- add args parameter
    sheet_name: Optional[str] = None,  # Sheet name for enhanced pattern matching
    row_idx: Optional[int] = None,  # Row index for enhanced pattern matching
>>>>>>> Stashed changes
) -> ValidationResult:
    """
    Checks if the pattern exists in the response body or headers.
    Returns ValidationResult(True) if found, otherwise ValidationResult(False, reason).
    """
<<<<<<< Updated upstream

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
=======
    # Check for enhanced pattern matches if sheet_name and row_idx are provided
    enhanced_pattern = None
    if sheet_name is not None and row_idx is not None:
        # increment row index by 1 to match the row number in the JSON file
        row_idx += 1  # Adjust for 0-based index in Python
        enhanced_pattern = load_enhanced_pattern_matches(sheet_name, row_idx)
        if enhanced_pattern:
            logger.debug(f"Found enhanced pattern match for sheet '{sheet_name}' row {row_idx}")
            
            # Process based on pattern_type
            if enhanced_pattern.get("pattern_type") == "json_extracted":
                pattern_data = enhanced_pattern.get("data", {})
                body_str = str(body or "")
                try:
                    body_json = json.loads(body_str) if body_str else {}
                    
                    # Check if the response contains multiple items
                    if isinstance(body_json, list):
                        logger.info(f"Response contains a list of {len(body_json)} items")
                        # Process each item in the list against the pattern
                        for i, item in enumerate(body_json):
                            logger.debug(f"Checking pattern against item {i+1} of {len(body_json)}")
                            match, reason = _validate_pattern_data_in_body_json(pattern_data, item, logger)
                            if match:
                                logger.info(f"Pattern matched with item {i+1} in the list")
                                return ValidationResult(True)
                        # If we get here, no items matched
                        return ValidationResult(False, fail_reason="No items in the list matched the pattern")
                    elif isinstance(body_json, dict):
                        # Check if any top-level keys contain lists that might need to be checked
                        for key, value in body_json.items():
                            if isinstance(value, list) and len(value) > 0:
                                logger.info(f"Response contains a list of {len(value)} items in key '{key}'")
                        
                        # Proceed with normal validation
                        match, reason = _validate_pattern_data_in_body_json(pattern_data, body_json, logger)
                    else:
                        logger.warning(f"Response is neither a list nor a dictionary: {type(body_json)}")
                        match, reason = False, f"Unexpected response type: {type(body_json)}"
                        
                except json.JSONDecodeError:
                    logger.error("Invalid JSON format in response body")
                    return ValidationResult(False, fail_reason="Invalid JSON format in response body")
                
                return ValidationResult(match, fail_reason=reason if not match else None)
            elif enhanced_pattern.get("pattern_type") == "http_header":
                # fetch header name
                pattern_data = enhanced_pattern.get("data", "")
                if pattern_data:
                    # fetch the header name from pattern_data
                    header_name = pattern_data.get("header_name", "")
                    if header_name and headers:
                        # Check if the header exists in headers
                        if header_name in headers:
                            logger.debug(f"Enhanced pattern '{header_name}' found in headers")
                            return ValidationResult(True)
                        else:
                            logger.debug(f"Enhanced pattern '{header_name}' not found in headers")
                            return ValidationResult(False, fail_reason=f"Pattern '{header_name}' not found in headers")
                #TODO; we have to handle header value information if available in pattern_data
            elif enhanced_pattern.get("pattern_type") == "json_object":
                # Check if the pattern exists in the response body as a JSON object
                pattern_data = enhanced_pattern.get("data", {})
                # check if pattern_data is a dict or str
                if isinstance(pattern_data, str):
                    try:
                        pattern_data = json.loads(pattern_data)
                    except json.JSONDecodeError:
                        logger.debug("Invalid JSON format in pattern data")
                        pattern_data = parse_pattern_match.parse_pattern_match_string(pattern_data)
                        logger.debug(f"Pattern data parsed as string: {pattern_data}")

                body_str = str(body or "")
                try:
                    body_json = json.loads(body_str) if body_str else {}
                except json.JSONDecodeError:
                    logger.error("Invalid JSON format in response body")
                    return ValidationResult(False, fail_reason="Invalid JSON format in response body")
                
                match, reason = _validate_pattern_data_in_body_json(pattern_data, body_json, logger)
                # if there is no match in response body fall back to headers
                if not match and headers:
                    for key, value in pattern_data.items():
                        if key in headers and headers[key] == value:
                            logger.debug(f"Pattern '{key}' matched in headers")
                            return ValidationResult(True)
                    logger.debug(f"Pattern '{pattern_data}' not found in response body or headers")
                    return ValidationResult(False, fail_reason=f"Pattern '{pattern_data}' not found in response body or headers")

>>>>>>> Stashed changes

def _validate_pattern_data_in_body_json(pattern_data, body_json, logger):
    """
    Helper to check if all keys and values in pattern_data exist in body_json, supporting dot notation for nested keys.
    Returns ValidationResult.
    """
    match_found = True
    missing_keys = []
    value_mismatches = []

    for key, expected_value in pattern_data.items():
        # Handle nested keys with dot notation (e.g., "config.autoCreate")
        if '.' in key:
            parts = key.split('.')
            current = body_json
            for part in parts[:-1]:
                if part in current:
                    current = current[part]
                else:
                    match_found = False
                    missing_keys.append(key)
                    break
            if key not in missing_keys and parts[-1] in current:
                actual_value = current[parts[-1]]
                if actual_value != expected_value:
                    match_found = False
                    value_mismatches.append(f"{key}: expected '{expected_value}', got '{actual_value}'")
        else:
            if key in body_json:
                actual_value = body_json[key]
                if actual_value != expected_value:
                    match_found = False
                    value_mismatches.append(f"{key}: expected '{expected_value}', got '{actual_value}'")
            else:
<<<<<<< Updated upstream
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
=======
                match_found = False
                missing_keys.append(key)

    if match_found:
        logger.debug("Enhanced pattern matched in response payload")
        return True, ""
    else:
        fail_reason = ""
        if missing_keys:
            fail_reason += f"Missing keys: {missing_keys}. "
        if value_mismatches:
            fail_reason += f"Value mismatches: {value_mismatches}."
        return False, f"{fail_reason}"
    
    
>>>>>>> Stashed changes

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
