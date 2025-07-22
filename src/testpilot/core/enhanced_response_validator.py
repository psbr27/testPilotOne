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
    """
    if not isinstance(expected, dict) or not isinstance(actual, dict):
        return expected == actual
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
    keys = key_path.split(".")
    current = d
    for k in keys[:-1]:
        if isinstance(current, dict) and k in current:
            current = current[k]
        else:
            return False
    last_key = keys[-1]
    if isinstance(current, dict) and last_key in current:
        return current[last_key] == expected_value
    return False


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
    actual_str = (
        json.dumps(actual, separators=(",", ":"))
        if isinstance(actual, (dict, list))
        else str(actual)
    )
    headers_str = (
        json.dumps(response_headers, separators=(",", ":"))
        if isinstance(response_headers, dict)
        else str(response_headers)
    )

    if not pattern_match:
        # no pattern match provided
        pattern_match_overall = None
    elif pattern_match and isinstance(pattern_match, str):
        logger.debug(f"Starting pattern matching for pattern: {pattern_match}")
        # check if actual_str is a list
        if isinstance(actual_str, list):
            for item in actual_str:
                if isinstance(item, dict):
                    item_str = json.dumps(item)
                    if pattern_match in item_str:
                        actual_str = item_str
                        break
                elif isinstance(item, str):
                    if pattern_match in item:
                        actual_str = item
                        break

        # 2.1 Substring search
        found_body = pattern_match in actual_str
        found_headers = pattern_match in headers_str
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
                sep = ":" if ":" in pattern_match else "="
                key, val = pattern_match.split(sep, 1)
                key = key.strip().strip('"')
                val = val.strip().strip('"')
                try:
                    val_json = json.loads(val)
                except Exception:
                    val_json = val
                # For body: check all dicts in list, or just dict
                if isinstance(actual, dict):
                    found_kv_body = _search_nested_key_value(
                        actual, key, val_json
                    )
                    if found_kv_body is False:
                        # check if a key is a substring in the body
                        if key in actual:
                            found_kv_body = val_json in str(actual[key])
                elif isinstance(actual, list):
                    found_kv_body = any(
                        _search_nested_key_value(item, key, val_json)
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
            if isinstance(actual, dict) and isinstance(pattern_match, str):
                # move pattern_match to json
                try:
                    pattern_match = json.loads(pattern_match)
                    #if _is_subset_dict(pattern_match, actual, partial=partial_dict_match):
                    pattern_match_result = compare_json_objects(
                            pattern_match if pattern_match is not None else "",
                            actual,
                            "structure_and_values",
                            ignore_array_order=ignore_array_order,
                    )
                    differences = (
                        pattern_match_result["missing_details"]
                        if not dict_match
                        else None
                    )
                    if pattern_match_result["match_percentage"] > 50:
                        pattern_match_overall = True
                    else:
                        pattern_match_overall =  False
                except Exception as e:
                    logger.error("2.5 pattern match not found {e}")

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
