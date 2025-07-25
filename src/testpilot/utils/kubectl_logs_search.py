import json
import re


def search_pattern(output_string, pattern):
    """
    Search for a specific pattern in the output string.

    Args:
        output_string (str): The server output string to search in
        pattern (str): The regex pattern to search for

    Returns:
        list: List of matches found
    """
    try:
        matches = re.findall(pattern, output_string)
        return matches
    except re.error as e:
        print(f"Error in regex pattern: {e}")
        return []


def search_similar_patterns(
    output_string, base_pattern=r'User-Agent[:\s]*"[^"]*"'
):
    """
    Search for similar patterns in the output string.

    Args:
        output_string (str): The server output string to search in
        base_pattern (str): The base pattern to search for (default: User-Agent pattern)

    Returns:
        list: List of similar patterns found
    """
    try:
        matches = re.findall(base_pattern, output_string)
        return matches
    except re.error as e:
        print(f"Error in regex pattern: {e}")
        return []


def search_in_json_logs(output_string, search_term):
    """
    Parse JSON log entries and search for specific information.

    Args:
        output_string (str): The server output string containing JSON logs
        search_term (str): The term to search for in log messages

    Returns:
        dict: Dictionary containing search results
    """
    results = {"matching_entries": [], "total_entries": 0, "parsed_entries": 0}

    # Split the output into individual JSON entries
    log_entries = output_string.strip().split("\n")
    results["total_entries"] = len(log_entries)

    for entry in log_entries:
        if not entry.strip():
            continue

        try:
            # Parse each JSON log entry
            log_data = json.loads(entry)
            results["parsed_entries"] += 1

            # Check if the log message contains the search term
            message = log_data.get("message", "")
            if search_term in message:
                results["matching_entries"].append(
                    {
                        "timestamp": log_data.get("messageTimestamp", ""),
                        "level": log_data.get("level", ""),
                        "logger": log_data.get("loggerName", ""),
                        "message": message,
                    }
                )

        except json.JSONDecodeError:
            # Skip entries that are not valid JSON
            continue

    return results


def search_in_custom_output(output_string, pattern_match, case_sensitive=True):
    """
    Search for a specific pattern in the output string.

    Args:
        output_string (str): The server output string to search in
        pattern_match (str): The pattern to search for (can be regex or plain text)
        case_sensitive (bool): Whether the search should be case sensitive (default: True)

    Returns:
        dict: Dictionary containing search results with matches, count, and positions
    """
    result = {
        "pattern": pattern_match,
        "matches": [],
        "count": 0,
        "found": False,
        "positions": [],
    }

    try:
        # Set up regex flags
        flags = 0 if case_sensitive else re.IGNORECASE

        # Find all matches with their positions
        for match in re.finditer(pattern_match, output_string, flags):
            result["matches"].append(match.group())
            result["positions"].append(
                {
                    "start": match.start(),
                    "end": match.end(),
                    "match": match.group(),
                }
            )

        result["count"] = len(result["matches"])
        result["found"] = result["count"] > 0

        # Display results
        if result["found"]:
            print(
                f"✓ Pattern '{pattern_match}' found {result['count']} time(s)!"
            )
            for i, pos in enumerate(result["positions"]):
                print(
                    f"  Match {i+1}: '{pos['match']}' at position {pos['start']}-{pos['end']}"
                )
        else:
            print(
                f"✗ Pattern '{pattern_match}' not found in the output string."
            )

    except re.error as e:
        print(f"Error in regex pattern '{pattern_match}': {e}")
        result["error"] = str(e)

    return result


# Example usage with different patterns:

# 1. Search for exact User-Agent pattern
# user_agent_pattern = r'User-Agent:"UDR-5a7bd676-ceeb-44bb-95e0-f6a55a328b03 udr001\.oracle\.com"'
# result = search_in_custom_output(your_output_string, user_agent_pattern)

# 2. Search for any UDR pattern (case insensitive)
# udr_pattern = r'UDR-[a-f0-9-]+'  # Matches UDR with UUID pattern
# result = search_in_custom_output(your_output_string, udr_pattern, case_sensitive=False)

# 3. Search for plain text (no regex)
# plain_text = "Connection refused"
# result = search_in_custom_output(your_output_string, plain_text)

# 4. Search for email patterns
# email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
# result = search_in_custom_output(your_output_string, email_pattern)

# 5. Search for URLs
# url_pattern = r'https?://[^\s"]+'
# result = search_in_custom_output(your_output_string, url_pattern)
