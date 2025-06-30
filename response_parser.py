import re
import json
import jsondiff
import pandas as pd
import logging
from parse_utils import extract_request_json_manual
import parse_instant_utils as piu
logger = logging.getLogger("TestPilot.ResponseParser")

def parse_curl_output(output: str, error: str) -> dict:
    """
    Parse curl or kubectl exec output and error to extract HTTP status, headers, payload, and reason.
    """
    logger.debug("Parsing curl output. Raw output length: %d, error: %s", len(output or ""), error)
    response = output or ""
    if not response:
        response = error or ""
    result = {
        'raw_output': output,
        'error': error,
        'reason': None
    }
    # Find HTTP/2 status line
    match = re.search(r'< HTTP/[12](?:\.\d)? (\d{3})', response)
    if match:
        result['http_status'] = int(match.group(1))
        logger.debug(f"Extracted HTTP status: {result['http_status']}")
    else:
        logger.debug("No HTTP status found in response. Trying on error")
        match = re.search(r'HTTP/[12](?:\.\d)? (\d{3})', error)
        if match:
            result['http_status'] = int(match.group(1))
            logger.debug(f"Extracted HTTP status from error: {result['http_status']}")
    if 'http_status' not in result:
        result['http_status'] = None
        logger.debug("No HTTP status found in either output or error.") 
    # Extract headers
    headers = {}
    for line in response.splitlines():
        if line.startswith('< '):
            header_line = line[2:].strip()
            if ':' in header_line:
                k, v = header_line.split(':', 1)
                headers[k.strip().lower()] = v.strip()
                logger.debug(f"Header found: {k.strip().lower()} = {v.strip()}")
    result['headers'] = headers
    # Extract JSON response payload if present (after headers)
    # Find the last header line and try to parse what's after
    payload = None
    lines = response.splitlines()
    header_end_idx = None
    for i, line in enumerate(lines):
        if line.strip() == '<' or (line.startswith('< ') and line.strip() == '<'):
            header_end_idx = i
    if header_end_idx is not None and header_end_idx+1 < len(lines):
        # Join everything after the last header as payload
        possible_json = '\n'.join(lines[header_end_idx+1:]).strip()
        logger.debug(f"Attempting to parse payload after header at line {header_end_idx}.")
        if possible_json:
            try:
                payload = json.loads(possible_json)
                logger.debug("Parsed JSON payload successfully.")
            except Exception as e:
                logger.debug(f"Failed to parse JSON payload: {e}. Using raw payload.")
                payload = possible_json
    result['response_payload'] = payload
    # Reason: look for first line with 'Reason:'
    reason_match = re.search(r'Reason:\s*(.*)', response)
    if reason_match:
        result['reason'] = reason_match.group(1).strip()
        logger.debug(f"Found Reason in response: {result['reason']}")
    logger.info(
        f"parse_curl_output result summary: status={result.get('http_status')}, headers={len(headers)}, payload={'present' if payload else 'none'}"
    )
    
    # if status is None, Payload is None and headers are emtpy consider it
    # is kubectl logs output
    if result['http_status'] is None and not payload and not headers:
        logger.warning("No HTTP status, payload, or headers found. This may be kubectl logs output.")
        result['is_kubectl_logs'] = True
    return result


def check_pod_logs(output, pattern_match):
    if not output:
        return False
    
    # Method 1: JSON parsing approach (more robust)
    if pattern_match.startswith('"level'):
        # Extract the level value from pattern like '"level":"DEBUG"'
        try:
            # Parse the pattern as JSON fragment
            level_to_find = pattern_match.split(':')[1].strip().strip('"')
            
            for line in output.strip().split('\n'):
                try:
                    log_entry = json.loads(line)
                    if log_entry.get('level') == level_to_find:
                        return True
                except json.JSONDecodeError:
                    continue
        except (IndexError, ValueError):
            pass
    elif pattern_match.startswith('"request') or pattern_match.startswith('"instant'):
        # Example pattern: '"request":"{"profile-data":{"accountID":["12345678912345678912345678"],"imsi":["302720603942144"],"msisdn":["19195225555"]},"slfGroupName":"IMSGrp1"}"}'
        pattern_json = extract_request_json_manual(pattern_match)
        if pattern_json is None:
            logger.info(f"Failed to extract JSON from pattern_match, trying flexibe log patern: {pattern_match}")
            # trying with flexible log pattern
            # Test the regex extraction
            info = piu.extract_log_info_regex(pattern_match)
            logger.info(f"Level: {info['level']}")
            logger.info(f"Logger: {info['loggerName']}")
            logger.info(f"Message (first 100 chars): {info['message'][:100]}...")

            result = piu.check_flexible_log_pattern_v3(output, pattern_match)
            if result:
                logger.info(f"Pattern match found in pod logs for pattern: {pattern_match}")
                return True
            logger.error(f"Failed to extract JSON from pattern_match: {pattern_match}")
            return False
        for line in output.strip().split('\n'):
            try:
                log_entry = json.loads(line)
                # Check if pattern_match is found in log_entry
                # find subset of pattern_match in log_entry
                if isinstance(log_entry, dict) and pattern_json is not None:
                    if all(log_entry.get(k) == v for k, v in pattern_json.items()):
                        return True
            except json.JSONDecodeError:
                continue
        # if pattern_match is not found print detailed report
        logger.error(f"Pattern match not found in pod logs for pattern: {pattern_match}")
    return False

def validate_test_result(parsed, expected_status=None, pattern_match=None, output=None, error=None, compare_with_payload=None, compare_with_key=None, method=None):
    """
    Validate parsed response against expected status and/or pattern_match substring.
    Optionally, compare response payload to a reference payload (workflow-aware).
    Returns: passed (bool), fail_reason (str or None), pattern_found (bool or None)
    """
    logger.debug(f"Validating test result: expected_status={expected_status}, pattern_match={pattern_match}")
    actual_status = parsed.get("http_status")
    response_payload = parsed.get("response_payload")
    server_output = parsed.get("raw_output")
    logger.debug(f"Actual HTTP status: {actual_status}")
    passed = True
    fail_reason = None
    pattern_found = None
    # Workflow-aware GET/compare logic
    if method and method.upper() == "GET" and compare_with_payload is not None:
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
                        logger.debug("server_output is not valid JSON, using as-is")
                diff_result = jsondiff.diff(server_output, ref_payload)
            else:
                diff_result = jsondiff.diff(response_payload, ref_payload)
            if diff_result:
                passed = False
                fail_reason = f"GET response does not match {compare_with_key or 'reference payload'}. Diff: {diff_result}"
            else:
                logger.info(f"GET response matches {compare_with_key or 'reference payload'}.")
        except Exception as e:
            logger.error(f"Workflow compare failed: {e}")
            passed = False
            fail_reason = f"Workflow compare error: {e}"
    # Check status (handle NaN or non-int gracefully)
    if passed and expected_status is not None and pd.notna(expected_status):
        try:
            expected_status_int = int(expected_status)
            # For PUT, accept both 200 and 201 as pass if expected is either
            logger.info(f"{method} Comparing actual status {actual_status} with expected status {expected_status_int}")
            if method and method.upper() == "PUT":
                actual_status_int = int(actual_status or 0)
                if (expected_status_int in (200, 201)) and (actual_status_int in (200, 201)):
                    passed = True
                else:
                    passed = actual_status_int == expected_status_int
            else:
                passed = int(actual_status or 0) == expected_status_int
        except Exception:
            passed = False
            fail_reason = f"Unable to compare status: {actual_status} vs {expected_status}"
            return passed, fail_reason, pattern_found
    # Pattern matching: always search as substring in output, then payload
    if passed and pattern_match:
        # If pattern_match is a string that looks like JSON, try to parse it
        pattern_json = None
        pattern_json_valid = False
        if isinstance(pattern_match, (dict, list)):
            pattern_json = pattern_match
            pattern_json_valid = True
        elif isinstance(pattern_match, str):
            pattern_match_str = pattern_match.strip()
            if (pattern_match_str.startswith('{') and pattern_match_str.endswith('}')) or \
               (pattern_match_str.startswith('[') and pattern_match_str.endswith(']')):
                try:
                    pattern_json = json.loads(pattern_match_str)
                    pattern_json_valid = True
                except Exception as e:
                    logger.debug(f"pattern_match looks like JSON but failed to parse: {e}")
                    pattern_json_valid = False
        # Use JSON diff if both are JSON
        if pattern_json_valid and isinstance(response_payload, (dict, list)):
            diff_result = jsondiff.diff(response_payload, pattern_json)
            pattern_found = (not diff_result)
            logger.debug(f"Pattern JSON diff: {diff_result}")
            if not pattern_found:
                passed = False
                fail_reason = f"Pattern JSON not found in response. Diff: {diff_result}"
        else:
            # if output is a dict or list, convert to string for substring search
            if isinstance(output, (dict, list)):
                output = json.dumps(output, ensure_ascii=False)
            pattern_found = check_pod_logs(output, pattern_match)
            logger.debug(f"Pattern search in output: found={pattern_found}")
            if not pattern_found and response_payload is not None:
                pattern_found = str(pattern_match) in str(response_payload)
                logger.debug(f"Pattern search in response_payload: found={pattern_found}")
            if not pattern_found:
                passed = False
                fail_reason = f"Pattern '{pattern_match}' not found in response"
    
    # if pattern_found is false; we have to find response_payload and pattern_match 
    # both are present if so just find the pattern_match from response_payload
    logger.debug(f"Trying next validation if both response_payload and pattern_match found: passed={passed}, fail_reason={fail_reason}, pattern_found={pattern_found}")
    if not pattern_found and compare_with_payload is not None and pattern_match is not None:
        # check response payload is a dict if so convert to JSON 
        if isinstance(compare_with_payload, (dict, list)):
            compare_payload_str = json.dumps(compare_with_payload, ensure_ascii=False)
        else:
            compare_payload_str = str(compare_with_payload)
        # If pattern_match is a string then find this string in compare_payload_str
        pattern_found = str(pattern_match) in compare_payload_str
        if pattern_found:
            logger.debug(f"Pattern '{pattern_match}' found in compare_with_payload")
            passed = True
    
    # if only pattern_match presents for kubectl logs command
    logger.debug(f"Final validation for kubectl logs output: passed={passed}, fail_reason={fail_reason}, pattern_found={pattern_found}")
    if not pattern_found and output and pattern_match:
        # Check if this is kubectl logs output
        if parsed.get('is_kubectl_logs', False):
            pattern_found = check_pod_logs(output, pattern_match)
            logger.debug(f"Pattern search in kubectl logs output: found={pattern_found}")
            if not pattern_found:
                passed = False
                fail_reason = f"Pattern '{pattern_match}' not found in kubectl logs output"
    # Check error
    if error:
        passed = False
        fail_reason = fail_reason or error
    return passed, fail_reason, pattern_found

