import json
import logging
import re
from typing import Any, Dict, Optional, Tuple, Union

import jsondiff
import pandas as pd

from . import parse_instant_utils as piu
from .parse_utils import extract_request_json_manual

logger = logging.getLogger("TestPilot.ResponseParser")


def parse_curl_output(output: str, error: str) -> dict:
    """
    Parse curl or kubectl exec output and error to extract HTTP status, headers, payload, and reason.
    """
    logger.debug(
        "Parsing curl output. Raw output length: %d, error: %s",
        len(output or ""),
        error,
    )
    response = output or ""
    if not response:
        response = error or ""
    result = {"raw_output": output, "error": error, "reason": None}
    # Find HTTP/2 status line
    match = re.search(r"< HTTP/[12](?:\.\d)? (\d{3})", response)
    if match:
        result["http_status"] = int(match.group(1))
        logger.debug(f"Extracted HTTP status: {result['http_status']}")
    else:
        logger.debug("No HTTP status found in response. Trying on error")
        match = re.search(r"HTTP/[12](?:\.\d)? (\d{3})", error)
        if match:
            result["http_status"] = int(match.group(1))
            logger.debug(
                f"Extracted HTTP status from error: {result['http_status']}"
            )
    if "http_status" not in result:
        result["http_status"] = None
        logger.debug("No HTTP status found in either output or error.")
    # Extract headers
    headers = {}
    # assuming headers are always present in error
    if error:
        for line in error.splitlines():
            if line.startswith("< "):
                header_line = line[2:].strip()
                if ":" in header_line:
                    k, v = header_line.split(":", 1)
                    headers[k.strip().lower()] = v.strip()
                    logger.debug(
                        f"Header found: {k.strip().lower()} = {v.strip()}"
                    )
        result["headers"] = headers

    if result.get("headers", None):
        logger.debug(f"Extracted Headers ==> {result['headers']}")

    # print headers information if headers are present
    if headers:
        logger.debug(f"Extracted {len(headers)} headers from response.")
        for k, v in headers.items():
            logger.debug(f"Header: {k} = {v}")
    else:
        logger.debug("No headers found in response.")
    # Extract JSON response payload if present (after headers)
    # Find the last header line and try to parse what's after
    payload = None
    lines = response.splitlines()
    header_end_idx = None
    for i, line in enumerate(lines):
        if line.strip() == "<" or (
            line.startswith("< ") and line.strip() == "<"
        ):
            header_end_idx = i
    if header_end_idx is not None and header_end_idx + 1 < len(lines):
        # Join everything after the last header as payload
        possible_json = "\n".join(lines[header_end_idx + 1 :]).strip()
        logger.debug(
            f"Attempting to parse payload after header at line {header_end_idx}."
        )
        if possible_json:
            try:
                payload = json.loads(possible_json)
                logger.debug("Parsed JSON payload successfully.")
            except Exception as e:
                logger.debug(
                    f"Failed to parse JSON payload: {e}. Using raw payload."
                )
                payload = possible_json
    result["response_payload"] = payload
    # Reason: look for first line with 'Reason:'
    reason_match = re.search(r"Reason:\s*(.*)", response)
    if reason_match:
        result["reason"] = reason_match.group(1).strip()
        logger.debug(f"Found Reason in response: {result['reason']}")
    logger.debug(
        f"parse_curl_output result summary: status={result.get('http_status')}, headers={len(headers)}, payload={'present' if payload else 'none'}"
    )

    # if status is None, Payload is None and headers are emtpy consider it
    # is kubectl logs output
    if result["http_status"] is None and not payload and not headers:
        logger.debug(
            "No HTTP status, payload, or headers found. This may be kubectl logs output."
        )
        result["is_kubectl_logs"] = True
    return result


def check_pod_logs(output, pattern_match):
    if not output:
        return False

    # Method 1: JSON parsing approach (more robust)
    if pattern_match.startswith('"level'):
        # Extract the level value from pattern like '"level":"DEBUG"'
        try:
            # Parse the pattern as JSON fragment
            level_to_find = pattern_match.split(":")[1].strip().strip('"')

            for line in output.strip().split("\n"):
                try:
                    log_entry = json.loads(line)
                    if log_entry.get("level") == level_to_find:
                        return True
                except json.JSONDecodeError:
                    continue
        except (IndexError, ValueError):
            pass
    elif pattern_match.startswith('"request') or pattern_match.startswith(
        '"instant'
    ):
        # Example pattern: '"request":"{"profile-data":{"accountID":["12345678912345678912345678"],"imsi":["302720603942144"],"msisdn":["19195225555"]},"slfGroupName":"IMSGrp1"}"}'
        pattern_json = extract_request_json_manual(pattern_match)
        if pattern_json is None:
            logger.debug(
                f"Failed to extract JSON from pattern_match, trying flexibe log patern: {pattern_match}"
            )
            # trying with flexible log pattern
            # Test the regex extraction
            info = piu.extract_log_info_regex(pattern_match)
            logger.debug(f"Level: {info['level']}")
            logger.debug(f"Logger: {info['loggerName']}")
            logger.debug(
                f"Message (first 100 chars): {info['message'][:100]}..."
            )

            result = piu.check_flexible_log_pattern_v3(output, pattern_match)
            if result:
                logger.debug(
                    f"Pattern match found in pod logs for pattern: {pattern_match}"
                )
                return True
            logger.error(
                f"Failed to extract JSON from pattern_match: {pattern_match}"
            )
            return False
        for line in output.strip().split("\n"):
            try:
                log_entry = json.loads(line)
                # Check if pattern_match is found in log_entry
                # find subset of pattern_match in log_entry
                if isinstance(log_entry, dict) and pattern_json is not None:
                    if all(
                        log_entry.get(k) == v for k, v in pattern_json.items()
                    ):
                        return True
            except json.JSONDecodeError:
                continue
        # if pattern_match is not found print detailed report
        logger.error(
            f"Pattern match not found in pod logs for pattern: {pattern_match}"
        )
    return False


def _validate_get_method_comparison(
    response_payload: Any,
    server_output: Any,
    compare_with_payload: Any,
    compare_with_key: Optional[str],
) -> Tuple[bool, Optional[str]]:
    """Validate GET method response against reference payload."""
    try:
        ref_payload = compare_with_payload
        if isinstance(ref_payload, str):
            ref_payload = json.loads(ref_payload)

        # If response_payload is None, compare with server_output
        if response_payload is None:
            # check server_output is a string if so convert to JSON
            if isinstance(server_output, str):
                try:
                    server_output = json.loads(server_output)
                except json.JSONDecodeError:
                    logger.debug(
                        "server_output is not valid JSON, using as-is"
                    )
            diff_result = jsondiff.diff(server_output, ref_payload)
        else:
            diff_result = jsondiff.diff(response_payload, ref_payload)

        if diff_result:
            fail_reason = f"GET response does not match {compare_with_key or 'reference payload'}. Diff: {diff_result}"
            return False, fail_reason
        else:
            logger.debug(
                f"GET response matches {compare_with_key or 'reference payload'}."
            )
            return True, None
    except Exception as e:
        logger.error(f"Workflow compare failed: {e}")
        return False, f"Workflow compare error: {e}"


def _validate_status_code(
    actual_status: Optional[int], expected_status: Any, method: Optional[str]
) -> Tuple[bool, Optional[str]]:
    """Validate HTTP status code against expected value."""
    if expected_status is None or pd.isna(expected_status):
        return True, None

    try:
        expected_status_int = int(expected_status)
        actual_status_int = int(actual_status or 0)

        # For PUT, accept both 200 and 201 as pass if expected is either
        logger.debug(
            f"{method} Comparing actual status {actual_status_int} with expected status {expected_status_int}"
        )

        if method and method.upper() == "PUT":
            if (expected_status_int in (200, 201)) and (
                actual_status_int in (200, 201)
            ):
                return True, None
            elif actual_status_int != expected_status_int:
                return (
                    False,
                    f"Status mismatch: {actual_status_int} vs {expected_status_int}",
                )
        else:
            if actual_status_int != expected_status_int:
                return (
                    False,
                    f"Status mismatch: {actual_status_int} vs {expected_status_int}",
                )

        return True, None
    except Exception:
        return (
            False,
            f"Unable to compare status: {actual_status} vs {expected_status}",
        )


def _parse_pattern_as_json(
    pattern_match: Any,
) -> Tuple[Optional[Union[dict, list]], bool]:
    """Try to parse pattern_match as JSON."""
    if isinstance(pattern_match, (dict, list)):
        return pattern_match, True
    elif isinstance(pattern_match, str):
        pattern_match_str = pattern_match.strip()
        if (
            pattern_match_str.startswith("{")
            and pattern_match_str.endswith("}")
        ) or (
            pattern_match_str.startswith("[")
            and pattern_match_str.endswith("]")
        ):
            try:
                return json.loads(pattern_match_str), True
            except Exception as e:
                logger.debug(
                    f"pattern_match looks like JSON but failed to parse: {e}"
                )
    return None, False


def _validate_pattern_match(
    pattern_match: Any,
    output: Optional[str],
    response_payload: Any,
    compare_with_payload: Any,
    is_kubectl_logs: bool,
) -> Tuple[bool, Optional[str], Optional[bool]]:
    """Validate pattern matching in output or response payload."""
    if not pattern_match:
        return True, None, None

    pattern_json, pattern_json_valid = _parse_pattern_as_json(pattern_match)
    pattern_found = None

    # Use JSON diff if both are JSON
    if pattern_json_valid and isinstance(response_payload, (dict, list)):
        diff_result = jsondiff.diff(response_payload, pattern_json)
        pattern_found = not diff_result
        logger.debug(f"Pattern JSON diff: {diff_result}")
        if not pattern_found:
            return (
                False,
                f"Pattern JSON not found in response. Diff: {diff_result}",
                pattern_found,
            )
    else:
        # Convert output to string if needed
        if isinstance(output, (dict, list)):
            output = json.dumps(output, ensure_ascii=False)

        # Check in output first
        pattern_found = check_pod_logs(output, pattern_match)
        logger.debug(f"Pattern search in output: found={pattern_found}")

        # Check in response payload if not found
        if not pattern_found and response_payload is not None:
            pattern_found = str(pattern_match) in str(response_payload)
            logger.debug(
                f"Pattern search in response_payload: found={pattern_found}"
            )

        # Check in compare_with_payload if still not found
        if not pattern_found and compare_with_payload is not None:
            compare_payload_str = (
                json.dumps(compare_with_payload, ensure_ascii=False)
                if isinstance(compare_with_payload, (dict, list))
                else str(compare_with_payload)
            )
            pattern_found = str(pattern_match) in compare_payload_str
            if pattern_found:
                logger.debug(
                    f"Pattern '{pattern_match}' found in compare_with_payload"
                )

        # Final check for kubectl logs
        if not pattern_found and is_kubectl_logs and output:
            pattern_found = check_pod_logs(output, pattern_match)
            logger.debug(
                f"Pattern search in kubectl logs output: found={pattern_found}"
            )

        if not pattern_found:
            return (
                False,
                f"Pattern '{pattern_match}' not found in response",
                pattern_found,
            )

    return True, None, pattern_found


def validate_test_result(
    parsed,
    expected_status=None,
    pattern_match=None,
    output=None,
    error=None,
    compare_with_payload=None,
    compare_with_key=None,
    method=None,
):
    """
    Validate parsed response against expected status and/or pattern_match substring.
    Optionally, compare response payload to a reference payload (workflow-aware).
    Returns: passed (bool), fail_reason (str or None), pattern_found (bool or None)
    """
    logger.debug(
        f"Validating test result: expected_status={expected_status}, pattern_match={pattern_match}"
    )

    # Extract data from parsed response
    actual_status = parsed.get("http_status")
    response_payload = parsed.get("response_payload")
    server_output = parsed.get("raw_output")
    is_kubectl_logs = parsed.get("is_kubectl_logs", False)

    logger.debug(f"Actual HTTP status: {actual_status}")

    passed = True
    fail_reason = None
    pattern_found = None

    # Step 1: Validate GET method comparison if applicable
    if method and method.upper() == "GET" and compare_with_payload is not None:
        passed, fail_reason = _validate_get_method_comparison(
            response_payload,
            server_output,
            compare_with_payload,
            compare_with_key,
        )
        if not passed:
            return passed, fail_reason, pattern_found

    # Step 2: Validate status code
    status_passed, status_fail_reason = _validate_status_code(
        actual_status, expected_status, method
    )
    if not status_passed:
        return status_passed, status_fail_reason, pattern_found

    # Step 3: Validate pattern matching
    if pattern_match:
        pattern_passed, pattern_fail_reason, pattern_found = (
            _validate_pattern_match(
                pattern_match,
                output,
                response_payload,
                compare_with_payload,
                is_kubectl_logs,
            )
        )
        if not pattern_passed:
            passed = False
            fail_reason = pattern_fail_reason

    # Step 4: Check for errors
    if error:
        passed = False
        fail_reason = fail_reason or error

    return passed, fail_reason, pattern_found
