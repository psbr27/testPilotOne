"""
Enhanced Response Validator
- Subset dict comparison
- Advanced pattern matching (substring, key-value, regex, JSONPath)
- Configurable partial match and ignore fields
"""

import json
import re
from typing import Any, Dict, List, Optional

from .json_match import compare_json_objects

try:
    from jsonpath_ng import parse as jsonpath_parse
except ImportError:
    jsonpath_parse = None


def _remove_ignored_fields(d, ignore_fields):
    if not ignore_fields or not isinstance(d, dict):
        return d
    return {
        k: (
            _remove_ignored_fields(v, ignore_fields)
            if isinstance(v, dict)
            else v
        )
        for k, v in d.items()
        if k not in ignore_fields
    }


def _is_subset_dict(expected, actual, partial=True):
    """
    If partial=True, checks if expected is a subset of actual.
    If partial=False, checks for strict equality (recursively).
    Handles arrays by checking if all expected elements have matches in actual.
    """
    # Handle None cases
    if expected is None:
        return actual is None
    if actual is None:
        return False

    # Handle dict comparison
    if isinstance(expected, dict) and isinstance(actual, dict):
        if partial:
            for k, v in expected.items():
                if k not in actual:
                    return False
                if not _is_subset_dict(v, actual[k], partial):
                    return False
            return True
        else:
            # Strict: keys and values must match exactly
            if set(expected.keys()) != set(actual.keys()):
                return False
            for k, v in expected.items():
                if not _is_subset_dict(v, actual[k], partial):
                    return False
            return True

    # Handle list/array comparison
    elif isinstance(expected, list) and isinstance(actual, list):
        if partial:
            # For partial match, check if all expected items have a matching item in actual
            for exp_item in expected:
                found_match = False
                for act_item in actual:
                    if _is_subset_dict(exp_item, act_item, partial):
                        found_match = True
                        break
                if not found_match:
                    return False
            return True
        else:
            # Strict equality for lists
            if len(expected) != len(actual):
                return False
            # Note: This assumes order matters for strict comparison
            for i, exp_item in enumerate(expected):
                if not _is_subset_dict(exp_item, actual[i], partial):
                    return False
            return True

    # Handle primitive types
    else:
        return expected == actual


def _dict_diff(expected, actual):
    diff = {}
    for k, v in expected.items():
        if k not in actual:
            diff[k] = {"expected": v, "actual": None}
        elif isinstance(v, dict) and isinstance(actual[k], dict):
            subdiff = _dict_diff(v, actual[k])
            if subdiff:
                diff[k] = subdiff
        elif v != actual[k]:
            diff[k] = {"expected": v, "actual": actual[k]}
    return diff if diff else None


def _search_nested_key_value(d, key_path, expected_value):
    """
    Search for a key-value pair in a nested structure.
    Supports dot notation for nested keys and searches recursively.
    Uses flexible matching: exact match first, then substring match for strings.
    """
    keys = key_path.split(".")

    def flexible_match(actual_value, expected_value):
        """Check if expected value matches actual value (exact or substring)"""
        # Exact match first
        if actual_value == expected_value:
            return True

        # For strings, check if expected is a substring of actual
        if isinstance(actual_value, str) and isinstance(expected_value, str):
            return expected_value in actual_value

        # For numbers, try string representation substring match
        if isinstance(actual_value, (int, float)) and isinstance(
            expected_value, str
        ):
            return expected_value in str(actual_value)

        return False

    def search_in_dict_or_list(obj, keys_remaining):
        if not keys_remaining:
            return flexible_match(obj, expected_value)

        current_key = keys_remaining[0]
        remaining_keys = keys_remaining[1:]

        if isinstance(obj, dict):
            # Direct path search
            if current_key in obj:
                if remaining_keys:
                    return search_in_dict_or_list(
                        obj[current_key], remaining_keys
                    )
                else:
                    return flexible_match(obj[current_key], expected_value)

            # If direct path not found, search recursively in all values
            for value in obj.values():
                if isinstance(value, (dict, list)):
                    if search_in_dict_or_list(value, keys_remaining):
                        return True

        elif isinstance(obj, list):
            # Search in each item of the list
            for item in obj:
                if search_in_dict_or_list(item, keys_remaining):
                    return True

        return False

    return search_in_dict_or_list(d, keys)


def _list_dict_match(expected, actual_list, ignore_fields):
    """Return True if any dict in actual_list is a superset of expected."""
    for item in actual_list:
        if isinstance(item, dict):
            if _is_subset_dict(
                _remove_ignored_fields(expected, ignore_fields),
                _remove_ignored_fields(item, ignore_fields),
            ):
                return True
    return False


def _list_dicts_match(expected_list, actual_list, ignore_fields):
    """Return True if every dict in expected_list is a subset of at least one dict in actual_list."""
    for exp in expected_list:
        if not _list_dict_match(exp, actual_list, ignore_fields):
            return False
    return True


def _deep_array_search(obj, pattern_array):
    """
    Search for pattern array elements deeply within a nested structure.
    Returns True if all elements in pattern_array are found somewhere in obj.
    """

    def find_value_in_structure(obj, target_value):
        """Recursively search for a value in a nested structure"""
        if obj == target_value:
            return True

        if isinstance(obj, dict):
            for value in obj.values():
                if find_value_in_structure(value, target_value):
                    return True
        elif isinstance(obj, list):
            for item in obj:
                if find_value_in_structure(item, target_value):
                    return True

        return False

    # Check if all pattern elements exist somewhere in the structure
    for pattern_element in pattern_array:
        if not find_value_in_structure(obj, pattern_element):
            return False

    return True


def validate_response_enhanced(
    pattern_match: Optional[str],
    response_headers: Optional[dict],
    response_body: Optional[Any],
    response_payload: Optional[dict],
    logger,
    config: Optional[dict] = None,
    args=None,
    sheet_name: Optional[str] = None,
    row_idx: Optional[int] = None,
    raw_output: Optional[str] = None,
) -> dict:
    logger.debug("Starting enhanced response validation.")
    dict_match = None
    differences = None
    ignore_fields = (config or {}).get(
        "ignore_fields", []
    )  # for now we are not using this
    partial_dict_match = (config or {}).get("partial_dict_match", True)
    ignore_array_order = (config or {}).get(
        "ignore_array_order", True
    )  # Default to order-independent

    # Parse actual response if it's a string
    actual = response_body
    if isinstance(response_body, str):
        try:
            actual = json.loads(response_body)
            logger.debug(
                "Parsed response_body string to dict/list for comparison."
            )
        except Exception:
            actual = response_body  # fallback to string
            logger.debug(
                "Failed to parse response_body as JSON; using as string."
            )

    # check if response_payload is a str
    if isinstance(response_payload, str):
        try:
            response_payload = json.loads(response_payload)
            logger.debug(
                "Parsed response_payload string to dict/list for comparison."
            )
        except Exception:
            response_payload = response_payload  # fallback to string

    # Step 1: Dict/list comparison
    if isinstance(actual, dict) and isinstance(pattern_match, dict):
        logger.debug(
            "Performing dict comparison using pattern_match as expected."
        )
        expected = _remove_ignored_fields(pattern_match, ignore_fields)
        actual_clean = _remove_ignored_fields(actual, ignore_fields)
        dict_match = _is_subset_dict(
            expected, actual_clean, partial=partial_dict_match
        )
        differences = (
            None if dict_match else _dict_diff(expected, actual_clean)
        )
        logger.debug(
            f"Dict comparison result: {dict_match}, differences: {differences}"
        )
    elif isinstance(response_payload, dict):
        logger.debug(
            "Performing dict comparison using response_payload as expected."
        )
        expected = _remove_ignored_fields(response_payload, ignore_fields)
        actual_clean = _remove_ignored_fields(actual, ignore_fields)
        # dict_match = _is_subset_dict(expected, actual_clean, partial=partial_dict_match)
        if (
            partial_dict_match
            and expected is not None
            and actual_clean is not None
        ):
            dict_match_result = compare_json_objects(
                expected,
                actual_clean,
                "structure_and_values",
                ignore_array_order=ignore_array_order,
            )
            differences = (
                dict_match_result["missing_details"]
                if not dict_match
                else None
            )
            if dict_match_result["match_percentage"] > 50:
                dict_match = True
            else:
                dict_match = False
        logger.info(
            f"Response payload matches actual with {dict_match_result['match_percentage']}% confidence."
        )
        logger.debug(
            f"Dict comparison result: {dict_match}, differences: {differences}"
        )
    elif isinstance(actual, list) and isinstance(response_payload, dict):
        logger.debug(
            "Actual is a list, expected is a dict. Checking if any item in actual matches expected."
        )
        dict_match = (
            _list_dict_match(response_payload, actual, ignore_fields)
            if partial_dict_match
            else response_payload in actual
        )
        differences = (
            None
            if dict_match
            else f"No item in actual list matched expected dict."
        )
        logger.debug(
            f"List[dict] comparison result: {dict_match}, differences: {differences}"
        )
    elif isinstance(actual, list) and isinstance(response_payload, list):
        logger.debug(
            "Both actual and expected are lists. Checking if all expected dicts are present in actual list."
        )
        dict_match = (
            _list_dicts_match(response_payload, actual, ignore_fields)
            if partial_dict_match
            else all(exp in actual for exp in response_payload)
        )
        differences = (
            None
            if dict_match
            else f"Not all expected dicts found in actual list."
        )
        logger.debug(
            f"List[List[dict]] comparison result: {dict_match}, differences: {differences}"
        )
    else:
        logger.debug(
            "No dict/list comparison performed (no expected dict/list provided)."
        )

    # Step 2: Pattern matching (body and headers)
    pattern_matches = []
    pattern_match_overall = False
    # Preserve original string format for substring matching, use compact format for consistency
    # Prefer raw_output if available, otherwise use compact JSON format
    if raw_output:
        actual_str = raw_output
        logger.debug("Using raw_output for pattern matching")
    else:
        actual_str = (
            json.dumps(actual, separators=(",", ":"), ensure_ascii=False)
            if isinstance(actual, (dict, list))
            else str(actual)
        )
    headers_str = (
        json.dumps(response_headers, separators=(",", ":"), ensure_ascii=False)
        if isinstance(response_headers, dict)
        else str(response_headers)
    )

    if not pattern_match or (
        isinstance(pattern_match, str) and pattern_match.strip() == ""
    ):
        # no pattern match provided or empty pattern
        pattern_match_overall = None
        logger.debug("No pattern matching criteria provided (empty or None)")
    elif pattern_match and isinstance(pattern_match, str):
        logger.debug(f"Starting pattern matching for pattern: {pattern_match}")
        # Check if actual_str contains multiple JSON log lines (kubectl logs format)
        if isinstance(actual_str, str) and actual_str.startswith('{"'):
            # Try to parse as multiple JSON lines (common in kubectl logs)
            log_lines = []
            for line in actual_str.split("\n"):
                line = line.strip()
                if line.startswith("{") and line.endswith("}"):
                    try:
                        log_entry = json.loads(line)
                        log_lines.append(log_entry)
                    except json.JSONDecodeError:
                        continue

            # If we found JSON log entries, search within them
            if log_lines:
                logger.debug(
                    f"Found {len(log_lines)} JSON log entries to search"
                )
                for log_entry in log_lines:
                    log_str = json.dumps(
                        log_entry, separators=(",", ":"), ensure_ascii=False
                    )
                    if pattern_match in log_str:
                        logger.debug(
                            f"Pattern found in log entry: {log_str[:200]}..."
                        )
                        break

        # check if actual_str is a list
        if isinstance(actual_str, list):
            for item in actual_str:
                if isinstance(item, dict):
                    item_str = json.dumps(item, ensure_ascii=False)
                    if pattern_match in item_str:
                        actual_str = item_str
                        break
                elif isinstance(item, str):
                    if pattern_match in item:
                        actual_str = item
                        break

        # 2.1 Substring search (with flexible matching for trailing spaces)
        found_body = pattern_match in actual_str
        found_headers = pattern_match in headers_str

        # If exact match fails, try without trailing/leading spaces for log patterns
        if not found_body and not found_headers:
            pattern_trimmed = pattern_match.strip()
            if pattern_trimmed != pattern_match:
                found_body = pattern_trimmed in actual_str
                found_headers = pattern_trimmed in headers_str
                if found_body or found_headers:
                    logger.debug(f"Pattern found after trimming whitespace")

        # If still not found, try removing surrounding quotes from pattern
        if not found_body and not found_headers:
            if (
                pattern_match.startswith('"') and pattern_match.endswith('"')
            ) or (
                pattern_match.startswith("'") and pattern_match.endswith("'")
            ):
                pattern_no_quotes = pattern_match[1:-1]
                found_body = pattern_no_quotes in actual_str
                found_headers = pattern_no_quotes in headers_str
                if found_body or found_headers:
                    logger.debug(f"Pattern found after removing quotes")
        found = found_body or found_headers
        details = f"Pattern found in: "
        if found_body:
            details += "body "
        if found_headers:
            details += "headers"
        if not found:
            details = "Pattern not found in body or headers"
        logger.debug(
            f"Substring search: found_body={found_body}, found_headers={found_headers}"
        )
        pattern_matches.append(
            {"type": "substring", "result": found, "details": details.strip()}
        )
        if found:
            pattern_match_overall = True
        else:
            # 2.2 Key-value search (dot notation for body, flat for headers)
            found_kv_body = False
            found_kv_headers = False
            if ":" in pattern_match or "=" in pattern_match:
                # Skip key-value parsing for JSON string patterns
                if pattern_match.strip().startswith(
                    "{"
                ) and pattern_match.strip().endswith("}"):
                    logger.debug(
                        "Skipping key-value parsing for JSON string pattern"
                    )
                elif pattern_match.strip().startswith(
                    "["
                ) and pattern_match.strip().endswith("]"):
                    logger.debug(
                        "Skipping key-value parsing for JSON array pattern"
                    )
                else:
                    sep = ":" if ":" in pattern_match else "="
                    key, val = pattern_match.split(sep, 1)
                    key = key.strip().strip('"')
                    val = val.strip().strip('"')
                    # Try to parse as JSON, but also keep original string for comparison
                    val_original = val
                    try:
                        val_json = json.loads(val)
                    except Exception:
                        val_json = val

                    # For body: check all dicts in list, or just dict
                    if isinstance(actual, dict):
                        # Try with parsed value first
                        found_kv_body = _search_nested_key_value(
                            actual, key, val_json
                        )
                        # If not found and value was parsed differently, try with original string
                        if not found_kv_body and val_json != val_original:
                            found_kv_body = _search_nested_key_value(
                                actual, key, val_original
                            )

                        # Also search in all nested arrays within the dict
                        if not found_kv_body:
                            for k, v in actual.items():
                                if isinstance(v, list):
                                    for item in v:
                                        if isinstance(
                                            item, dict
                                        ) and _search_nested_key_value(
                                            item, key, val_json
                                        ):
                                            found_kv_body = True
                                            break
                                        if (
                                            not found_kv_body
                                            and val_json != val_original
                                            and isinstance(item, dict)
                                        ):
                                            if _search_nested_key_value(
                                                item, key, val_original
                                            ):
                                                found_kv_body = True
                                                break
                                    if found_kv_body:
                                        break
                    elif isinstance(actual, list):
                        found_kv_body = any(
                            _search_nested_key_value(item, key, val_json)
                            or (
                                val_json != val_original
                                and _search_nested_key_value(
                                    item, key, val_original
                                )
                            )
                            for item in actual
                            if isinstance(item, dict)
                        )
                    if isinstance(response_headers, dict):
                        found_kv_headers = (
                            response_headers.get(key) == val_json
                        )  # entire string
                        # check substring
                        if found_kv_headers is False:
                            if key in response_headers:
                                found_kv_headers = val_json in str(
                                    response_headers[key]
                                )
                    found_kv = found_kv_body or found_kv_headers
                    details = f"Key-value found in: "
                    if found_kv_body:
                        details += "body "
                    if found_kv_headers:
                        details += "headers"
                    if not found_kv:
                        details = "Key-value not found in body or headers"
                    logger.debug(
                        f"Key-value search: key={key}, value={val_json}, found_body={found_kv_body}, found_headers={found_kv_headers}"
                    )
                    pattern_matches.append(
                        {
                            "type": "key-value",
                            "result": found_kv,
                            "details": details.strip(),
                        }
                    )
                    if found_kv:
                        pattern_match_overall = True

            # 2.3 Regex search
            try:
                regex = re.compile(pattern_match)
                found_regex_body = bool(regex.search(actual_str))
                found_regex_headers = bool(regex.search(headers_str))
                found_regex = found_regex_body or found_regex_headers
            except Exception as e:
                found_regex = False
                found_regex_body = found_regex_headers = False
                logger.debug(f"Regex search error: {e}")
            details = f"Regex found in: "
            if found_regex_body:
                details += "body "
            if found_regex_headers:
                details += "headers"
            if not found_regex:
                details = "Regex not found in body or headers"
            logger.debug(
                f"Regex search: found_body={found_regex_body}, found_headers={found_regex_headers}"
            )
            pattern_matches.append(
                {
                    "type": "regex",
                    "result": found_regex,
                    "details": details.strip(),
                }
            )
            if found_regex:
                pattern_match_overall = True

            # 2.4 JSONPath search (only for body and headers if dict/list)
            found_jsonpath_body = False
            found_jsonpath_headers = False
            jsonpath_details = ""
            if jsonpath_parse:
                if isinstance(actual, (dict, list)):
                    try:
                        expr = jsonpath_parse(pattern_match)
                        matches = [match.value for match in expr.find(actual)]
                        found_jsonpath_body = len(matches) > 0
                        jsonpath_details += (
                            f"Body matches: {matches} "
                            if found_jsonpath_body
                            else ""
                        )
                    except Exception as e:
                        jsonpath_details += f"Body error: {e} "
                        logger.debug(f"JSONPath search (body) error: {e}")
                if isinstance(response_headers, dict):
                    try:
                        expr = jsonpath_parse(pattern_match)
                        matches = [
                            match.value
                            for match in expr.find(response_headers)
                        ]
                        found_jsonpath_headers = len(matches) > 0
                        jsonpath_details += (
                            f"Headers matches: {matches}"
                            if found_jsonpath_headers
                            else ""
                        )
                    except Exception as e:
                        jsonpath_details += f"Headers error: {e}"
                        logger.debug(f"JSONPath search (headers) error: {e}")
            else:
                jsonpath_details = "jsonpath-ng not installed or neither body nor headers is a dict/list"
                logger.debug(
                    "jsonpath-ng not installed or neither body nor headers is a dict/list"
                )
            found_jsonpath = found_jsonpath_body or found_jsonpath_headers
            if not found_jsonpath:
                jsonpath_details = (
                    jsonpath_details or "No JSONPath match in body or headers"
                )
            logger.debug(
                f"JSONPath search: found_body={found_jsonpath_body}, found_headers={found_jsonpath_headers}"
            )
            pattern_matches.append(
                {
                    "type": "jsonpath",
                    "result": found_jsonpath,
                    "details": jsonpath_details.strip(),
                }
            )
            if found_jsonpath:
                pattern_match_overall = True

            # 2.5 if both response_body and pattern_match are dicts, check if pattern_match is a subset of response_body
            if isinstance(actual, (dict, list)) and isinstance(
                pattern_match, str
            ):
                # Check if pattern_match is a JSON string
                if pattern_match.strip().startswith(
                    "{"
                ) or pattern_match.strip().startswith("["):
                    try:
                        pattern_json = json.loads(pattern_match)

                        # Use raw_output if available for more accurate comparison
                        comparison_target = actual
                        if raw_output:
                            try:
                                comparison_target = json.loads(raw_output)
                                logger.debug(
                                    "Section 2.5: Using raw_output for JSON comparison"
                                )
                            except Exception as raw_parse_error:
                                logger.debug(
                                    f"Section 2.5: Failed to parse raw_output, using actual: {raw_parse_error}"
                                )

                        # For pattern matching, use subset logic instead of percentages
                        # Pattern should be a subset of the response (binary check)
                        if isinstance(pattern_json, dict) and isinstance(
                            comparison_target, dict
                        ):
                            pattern_match_overall = _is_subset_dict(
                                pattern_json, comparison_target, partial=True
                            )
                            logger.debug(
                                f"Section 2.5: JSON object pattern subset check: {pattern_match_overall}"
                            )
                        elif isinstance(pattern_json, list) and isinstance(
                            comparison_target, list
                        ):
                            # First check if it's a simple value array like ["tag1"]
                            all_primitives = all(
                                isinstance(
                                    item, (str, int, float, bool, type(None))
                                )
                                for item in pattern_json
                            )
                            if all_primitives:
                                # For primitive arrays, do deep search
                                pattern_match_overall = _deep_array_search(
                                    comparison_target, pattern_json
                                )
                                logger.debug(
                                    f"Section 2.5: Primitive array deep search: {pattern_match_overall}"
                                )
                            else:
                                # For arrays of objects, check subset relationship
                                pattern_match_overall = _is_subset_dict(
                                    pattern_json,
                                    comparison_target,
                                    partial=True,
                                )
                                logger.debug(
                                    f"Section 2.5: JSON array pattern subset check: {pattern_match_overall}"
                                )
                        elif isinstance(pattern_json, dict) and isinstance(
                            comparison_target, list
                        ):
                            # Pattern is dict, target is list - check if pattern matches any item
                            pattern_match_overall = _list_dict_match(
                                pattern_json, comparison_target, ignore_fields
                            )
                            logger.debug(
                                f"Section 2.5: JSON dict pattern in array check: {pattern_match_overall}"
                            )
                        elif isinstance(pattern_json, list):
                            # Pattern is array but target might be nested - search deeply
                            pattern_match_overall = _deep_array_search(
                                comparison_target, pattern_json
                            )
                            logger.debug(
                                f"Section 2.5: Deep array search: {pattern_match_overall}"
                            )
                        else:
                            # Direct value comparison for primitives
                            pattern_match_overall = (
                                (pattern_json in comparison_target)
                                if isinstance(comparison_target, (list, str))
                                else (pattern_json == comparison_target)
                            )
                            logger.debug(
                                f"Section 2.5: Direct value comparison: {pattern_match_overall}"
                            )
                    except Exception as e:
                        logger.debug(
                            f"Section 2.5: Failed to parse pattern as JSON: {e}"
                        )

    # Compose user-friendly summary
    if dict_match is True and pattern_match_overall is True:
        summary = "✅ Test PASSED: Response structure and content match expectations."
    elif dict_match is True and pattern_match_overall is False:
        summary = "⚠️ Test PARTIAL: Response structure is correct, but expected text/pattern was not found."
        logger.info(f"Pattern matches: {pattern_matches}")
    elif dict_match is True and pattern_match_overall is None:
        summary = "✅ Test PASSED: Response structure matches expected format."
    elif dict_match is False and pattern_match_overall is True:
        summary = "⚠️ Test PARTIAL: Expected text/pattern found, but response structure differs from expected."
        logger.info(f"Differences Found: {differences}")
    elif dict_match is False and pattern_match_overall is False:
        summary = "❌ Test FAILED: Response structure is incorrect AND expected text/pattern was not found."
        logger.info(f"Differences: {differences}")
        logger.info(f"Pattern matches: {pattern_matches}")
    elif dict_match is False and pattern_match_overall is None:
        summary = "❌ Test FAILED: Response structure does not match expected format."
        logger.info(f"Differences Found: {differences}")
    elif dict_match is None and pattern_match_overall is True:
        summary = "✅ Test PASSED: Expected text/pattern found in response."
    elif dict_match is None and pattern_match_overall is False:
        summary = (
            "❌ Test FAILED: Expected text/pattern was not found in response."
        )
    elif dict_match is None and pattern_match_overall is None:
        summary = "⚪ Test SKIPPED: No validation criteria provided."
    else:
        summary = "⚪ Test SKIPPED: No validation criteria provided."

    logger.debug(f"Validation summary: {summary}")
    return {
        "dict_match": dict_match,
        "differences": differences,
        "pattern_matches": pattern_matches,
        "pattern_match_overall": pattern_match_overall,
        "summary": summary,
    }
