import json
import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger("ParseUtils")


# Method 1: Use regex to extract the JSON string after "request":
def extract_request_json_regex(pattern_match: str) -> Optional[Dict[str, Any]]:
    """Extract JSON from pattern using regex approach."""
    try:
        # Use regex to find the JSON string after "request":"
        match = re.search(r'"request":"(.+)"$', pattern_match)
        if match:
            json_str = match.group(1)
            return json.loads(json_str)
        return None
    except json.JSONDecodeError as e:
        logger.debug(f"Error parsing JSON with regex method: {e}")
        return None
    except (AttributeError, TypeError) as e:
        logger.debug(f"Invalid input for regex extraction: {e}")
        return None


# Method 2: Manual parsing approach
def extract_request_json_manual(pattern_match: str) -> Optional[Dict[str, Any]]:
    """Extract JSON from pattern using manual parsing approach."""
    if not isinstance(pattern_match, str):
        logger.debug("Invalid input: pattern_match must be a string")
        return None

    try:
        # Find the start of the JSON after "request":"
        start_marker = '"request":"'
        start_idx = pattern_match.find(start_marker)
        if start_idx == -1:
            return None

        start_idx += len(start_marker)

        # Find the matching closing quote by counting braces
        brace_count = 0
        end_idx = start_idx

        for i in range(start_idx, len(pattern_match)):
            char = pattern_match[i]
            if char == "{":
                brace_count += 1
            elif char == "}":
                brace_count -= 1
                if brace_count == 0:
                    end_idx = i + 1
                    break

        # Extract the JSON string
        json_str = pattern_match[start_idx:end_idx]
        return json.loads(json_str)

    except json.JSONDecodeError as e:
        logger.debug(f"Error parsing JSON with manual method: {e}")
        return None
    except (IndexError, ValueError) as e:
        logger.debug(f"Error in manual parsing logic: {e}")
        return None


# Method 3: Split approach (simplest)
def extract_request_json_split(pattern_match: str) -> Optional[Dict[str, Any]]:
    """Extract JSON from pattern using split approach."""
    if not isinstance(pattern_match, str):
        logger.debug("Invalid input: pattern_match must be a string")
        return None

    try:
        # Split on "request":" and take the second part, then remove the last quote
        parts = pattern_match.split('"request":"', 1)
        if len(parts) == 2:
            json_str = parts[1]
            # Check if there's a trailing quote and remove it
            if json_str.endswith('"'):
                json_str = json_str[:-1]
            return json.loads(json_str)
        return None
    except json.JSONDecodeError as e:
        logger.debug(f"Error parsing JSON with split method: {e}")
        return None
    except (IndexError, AttributeError) as e:
        logger.debug(f"Error in split parsing logic: {e}")
        return None


def check_flexible_log_pattern(output: str, pattern_match: str) -> bool:
    """Check if pattern matches in log output using flexible criteria."""
    if not output or not pattern_match:
        return False

    try:
        # Parse the pattern to extract key fields
        pattern_json = json.loads(pattern_match)

        search_criteria = {
            "level": pattern_json.get("level"),
            "loggerName": pattern_json.get("loggerName"),
            "message_keywords": pattern_json.get("message", "").split()[
                :5
            ],  # First 5 words
        }

        # Search each log line in output
        for line in output.strip().split("\n"):
            try:
                log_entry = json.loads(line)

                # Check level match
                if log_entry.get("level") == search_criteria["level"]:
                    # Check logger match
                    if log_entry.get("loggerName") == search_criteria["loggerName"]:
                        # Check if message contains key words
                        log_message = log_entry.get("message", "")
                        if any(
                            keyword in log_message
                            for keyword in search_criteria["message_keywords"][:3]
                        ):
                            return True

            except json.JSONDecodeError:
                continue

        return False

    except json.JSONDecodeError as e:
        logger.debug(f"Pattern is not valid JSON, falling back to string matching: {e}")
        # Fallback to simple string matching
        return pattern_match in output
    except (AttributeError, TypeError) as e:
        logger.debug(f"Error in pattern matching logic: {e}")
        return False
