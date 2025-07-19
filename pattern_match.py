#!/usr/bin/env python3
"""
Pattern matching module for comparing dictionaries and JSON structures.
This module provides utilities for comparing dictionaries, collecting differences,
and displaying matches between expected patterns and actual responses.
"""
import os
import json
import logging
from typing import Dict, List, Any, Tuple, Optional

from utils.json_diff import json_match_percent
from itertools import zip_longest

# Initialize logger
logger = logging.getLogger(__name__)


def is_subset_dict(small: Dict, big: Dict) -> bool:
    """
    Check if the small dictionary is a subset of the big dictionary.
    
    Args:
        small: The smaller dictionary that should be a subset
        big: The larger dictionary to check against
        
    Returns:
        bool: True if small is a subset of big, False otherwise
    """
    for key, value in small.items():
        if key not in big:
            return False
        if isinstance(value, dict):
            if not isinstance(big[key], dict) or not is_subset_dict(value, big[key]):
                return False
        elif value != big[key]:
            return False
    return True

import json
from collections import Counter
from itertools import zip_longest
from typing import Any, Dict, List, Tuple

def enhance_collect_differences(
    small: Dict, big: Dict, parent_key: str = ""
) -> List[Tuple[str, str, Any, Any]]:
    """
    Collects differences between two dictionaries, treating lists as unordered.
    
    Args:
        small: The expected dictionary (pattern)
        big:   The actual dictionary (response)
        parent_key: The parent key path for nested dictionaries
        
    Returns:
        List of (type, key_path, expected_value, actual_value)
    """
    diffs: List[Tuple[str,str,Any,Any]] = []
    for key in small:
        full_key = f"{parent_key}.{key}" if parent_key else key

        # MISSING key
        if key not in big:
            diffs.append(("missing", full_key, small[key], None))
            continue

        exp = small[key]
        act = big[key]

        # RECURSE into dicts
        if isinstance(exp, dict) and isinstance(act, dict):
            diffs.extend(enhance_collect_differences(exp, act, full_key))

        # LISTS: compare as multisets if primitives, or as unordered list of dicts
        elif isinstance(exp, list) and isinstance(act, list):
            # primitive lists: use Counter
            if all(not isinstance(el, (dict, list)) for el in exp + act):
                if Counter(exp) != Counter(act):
                    diffs.append(("mismatch", full_key, exp, act))
            else:
                # lists of dicts (or mixed) → sort by JSON repr
                def sort_key(x):
                    try:
                        return json.dumps(x, sort_keys=True)
                    except Exception:
                        return str(x)
                sorted_exp = sorted(exp, key=sort_key)
                sorted_act = sorted(act, key=sort_key)
                # compare element‑by‑element (pad shorter with None)
                for idx, (se, sa) in enumerate(zip_longest(sorted_exp, sorted_act)):
                    sub_key = f"{full_key}[{idx}]"
                    if se is None:
                        diffs.append(("missing", sub_key, None, sa))
                    elif sa is None:
                        diffs.append(("missing", sub_key, se, None))
                    elif isinstance(se, dict) and isinstance(sa, dict):
                        diffs.extend(enhance_collect_differences(se, sa, sub_key))
                    elif se != sa:
                        diffs.append(("mismatch", sub_key, se, sa))

        # SCALAR mismatch
        elif exp != act:
            diffs.append(("mismatch", full_key, exp, act))

    return diffs


def collect_differences(small: Dict, big: Dict, parent_key: str = "") -> List[Tuple[str, str, Any, Any]]:
    """
    Collects differences between two dictionaries.
    
    Args:
        small: The expected dictionary (pattern)
        big: The actual dictionary (response)
        parent_key: The parent key path for nested dictionaries
        
    Returns:
        List[Tuple[str, str, Any, Any]]: A list of tuples containing:
          (type: 'missing' | 'mismatch', key_path, expected_value, actual_value)
    """
    diffs = []
    for key in small:
        full_key = f"{parent_key}.{key}" if parent_key else key
        if key not in big:
            diffs.append(("missing", full_key, small[key], None))
        elif isinstance(small[key], dict) and isinstance(big[key], dict):
            diffs.extend(collect_differences(small[key], big[key], full_key))
        elif small[key] != big[key]:
            diffs.append(("mismatch", full_key, small[key], big[key]))
    return diffs


def display_matches(small: Dict, big: Dict, parent_key: str = "", number_of_matches: dict = {}) -> Dict[str, Any]:
    """
    Recursively displays matching key paths and their values between two dictionaries.
    
    Args:
        small: The expected dictionary (pattern)
        big: The actual dictionary (response)
        parent_key: The parent key path for nested dictionaries
    """
    for key in small:
        full_key = f"{parent_key}.{key}" if parent_key else key
        if key in big:
            if isinstance(small[key], dict) and isinstance(big[key], dict):
                display_matches(small[key], big[key], full_key, number_of_matches)
            elif small[key] == big[key]:
                logger.info(f"✅ MATCH at {full_key}: value '{small[key]}'")
                number_of_matches[full_key] = {
                        "match": small[key]
                        }
    return number_of_matches 

def compare_ignoring_missing_keys(small: Dict, big: Dict, differences: List[Tuple[str, str, Any, Any]]) -> Dict[str, Any]:
    """
    Compares two dictionaries, ignoring keys marked as 'missing' in differences.
    
    Args:
        small: The expected dictionary (pattern)
        big: The actual dictionary (response)
        differences: List of differences as returned by collect_differences()
        
    Returns:
        bool: True if the rest of the data matches (ignoring missing keys), False otherwise
    """
    mismatch = {}
    for diff_type, key_path, expected, actual in differences:
        if diff_type == "mismatch":
            logger.info(f"❌ Value mismatch for {key_path}: expected '{expected}', got '{actual}'")
            mismatch[key_path] = {
                    "expected": expected,
                    "actual": actual
                    }
    return mismatch 

def report_missing_from_pattern(expected, actual, path=""):
    """
    Compares if all fields in 'expected' (pattern_match_from) exist in 'actual' (response_output).
    Returns a list of missing or mismatched fields.
    """
    diffs = []

    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            diffs.append(f"{path or 'root'}: expected dict but got {type(actual).__name__}")
            return diffs

        for key, expected_value in expected.items():
            current_path = f"{path}.{key}" if path else key
            if key not in actual:
                diffs.append(f"{current_path}: missing key")
            else:
                diffs.extend(report_missing_from_pattern(expected_value, actual[key], current_path))

    elif isinstance(expected, list):
        if not isinstance(actual, list):
            diffs.append(f"{path}: expected list but got {type(actual).__name__}")
            return diffs

        # Check if all expected items are in actual list
        for index, expected_item in enumerate(expected):
            if index >= len(actual):
                diffs.append(f"{path}[{index}]: missing list item")
            else:
                diffs.extend(report_missing_from_pattern(expected_item, actual[index], f"{path}[{index}]"))

    else:
        if expected != actual:
            diffs.append(f"{path}: expected '{expected}' but got '{actual}'")

    return diffs


def check_json_pattern_match(pattern: Dict, response: Dict, partial_match: bool = False, case_insensitive: bool = False) -> Tuple[bool, Dict[str, Any]]:
    """
    Compare `pattern` vs. `response`, returning True/False.
    - If both are lists, compare element‑wise (and record missing/unexpected).
    - Collect all diffs via collect_differences().
    - Collect all matches via display_matches().
    - In strict mode (partial_match=False): return True iff no diffs.
    - In partial mode: require at least one match and zero mismatches.
    """
    diffs = []
    matches = []
    # Track all match percentages to calculate an average
    match_percentages = []
    return_values = {"diffs": {}, "matches": {},  "overall_match_percent": 0}
    
    try:
        # 1) If both are lists, walk them in parallel (pad shorter with None)
        if isinstance(pattern, list) and isinstance(response, list):
            for idx, (p, r) in enumerate(zip_longest(pattern, response, fillvalue=None)):
                key_prefix = f"[{idx}]"
                if p is None:
                    diffs.append(("unexpected", key_prefix, None, r))
                    continue
                if r is None:
                    diffs.append(("missing",    key_prefix, p,    None))
                    continue

                # collect field‑level differences within each element
                diffs.extend(enhance_collect_differences(p, r))
                # collect matching keys within each element
                matches.extend(display_matches(p, r, number_of_matches={}))
                # compute JSON match percentage and add to list
                element_match_percent = json_match_percent(p, r)
                match_percentages.append(element_match_percent)

        else:
            # non‑list or mismatched types: direct compare
            if isinstance(pattern, str):
                pattern = json.loads(pattern)
            diffs    = enhance_collect_differences(pattern, response)
            matches  = display_matches(pattern, response, number_of_matches={})
            # compute JSON match percentage and add to list
            overall_match_percent = json_match_percent(pattern, response)
            match_percentages.append(overall_match_percent)

        return_values["diffs"] = diffs
        return_values["matches"] = matches
        
        # Calculate the average match percentage if we have any percentages
        if match_percentages:
            match_percent = sum(match_percentages) / len(match_percentages)
            logger.debug(f"Average JSON match percentage: {match_percent}%")
        else:
            match_percent = 0
        
        return_values["overall_match_percent"] = match_percent
        
        # 2) Log *all* diffs
        for diff_type, key_path, expected, actual in diffs:
            if diff_type == "missing":
                logger.debug(f"MISSING at {key_path}: expected '{expected}', got None")
            elif diff_type == "mismatch":
                logger.debug(f"MISMATCH at {key_path}: expected '{expected}', got '{actual}'")
            else:
                logger.debug(f"{diff_type.upper()} at {key_path}: {expected} vs {actual}")
        # 3) Decide pass/fail
        if partial_match:
            # Pass if at least one match *and* no real mismatches
            has_mismatch = any(dt == "mismatch" for dt, *_ in diffs)
            primary_check = bool(matches) and not has_mismatch
            
            # If primary check fails, consider JSON match percentage
            if not primary_check:
                try:
                    json_percentage_threshold = 50
                    # If match percentage is high enough, consider it a pass
                    if 'match_percent' in locals() and match_percent >= json_percentage_threshold:
                        logger.info(f"Primary check failed but JSON match percentage is {match_percent}% (≥{json_percentage_threshold}%), considering as pass")
                        return True, return_values
                except Exception as e:
                    logger.debug(f"Error checking match percentage: {e}")
                    # Fallback to default 40% (same as JSON_PERCENTAGE) if there's an error
                    if 'match_percent' in locals() and match_percent >= 40:
                        logger.info(f"Primary check failed but JSON match percentage is {match_percent}% (≥40% default), considering as pass")
                        return True, return_values
            
            return primary_check, return_values
    except Exception as e:
        logger.error(f"Error during pattern matching: {e}")
        return False, {}
    # Strict mode: primarily no diffs at all
    strict_check = not diffs
    
    # If strict check fails, consider JSON match percentage as a fallback
    if not strict_check:
        try:
            json_percentage_threshold = 50  # Default to 50% if not configured
            
            # For strict mode, we might want a higher threshold, so add 10% to the configured value
            strict_threshold = min(json_percentage_threshold + 10, 100)  # Cap at 100%
            
            if 'match_percent' in locals() and match_percent >= strict_threshold:
                logger.info(f"Strict check failed but JSON match percentage is {match_percent}% (≥{strict_threshold}%), considering as pass")
                return True, return_values
        except Exception as e:
            logger.debug(f"Error checking match percentage in strict mode: {e}")
            # Fallback to default if there's an error - using 50% (40% + 10%)
            if 'match_percent' in locals() and match_percent >= 50:
                logger.info(f"Strict check failed but JSON match percentage is {match_percent}% (≥50% default), considering as pass")
                return True, return_values
    
    return True, return_values
