#!/usr/bin/env python3
"""
Debug why ["tag1"] pattern is handled by regex
"""

import json
import logging
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "src"))
from testpilot.core.enhanced_response_validator import (
    validate_response_enhanced,
)

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def debug_array_pattern():
    """Debug array pattern matching"""

    response = [
        {"id": 1, "name": "item1", "tags": ["tag1", "tag2"]},
        {"id": 2, "name": "item2", "tags": ["tag3", "tag4"]},
        {"id": 3, "name": "item3", "tags": ["tag1", "tag5"]},
    ]

    pattern = '["tag1"]'

    print(f"Pattern: {pattern}")
    print(f"Response: {json.dumps(response)[:100]}...")

    # Check the pattern parsing
    print(f"\nPattern starts with '[': {pattern.strip().startswith('[')}")
    print(f"Pattern ends with ']': {pattern.strip().endswith(']')}")

    result = validate_response_enhanced(
        pattern_match=pattern,
        response_headers={"content-type": "application/json"},
        response_body=response,
        response_payload=None,
        logger=logger,
    )

    print(f"\nPattern match overall: {result['pattern_match_overall']}")
    print(f"Pattern matches: {result['pattern_matches']}")

    # Check if we reach section 2.5
    # The issue might be that regex returns True but doesn't set pattern_match_overall


if __name__ == "__main__":
    debug_array_pattern()
