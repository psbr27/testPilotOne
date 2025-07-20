import json
import re
from typing import Any, Dict, List


def parse_pattern_match_string(text: str) -> Dict[str, Any]:
    """
    Parse a complex pattern match string containing various formats:
    - JSON-like key:value pairs
    - Quoted strings
    - Header-style entries (key:value with semicolon-separated sub-values)
    - JSON objects
    """
    result = {}
    lines = text.strip().split("\n")

    for line in lines:
        line = line.strip()
        if not line:
            continue

        try:
            # Try to parse each line
            parsed_data = parse_line(line)
            if parsed_data:
                merge_dict(result, parsed_data)
        except Exception as e:
            print(f"Warning: Could not parse line: {line[:50]}... Error: {e}")
            continue

    return result


def parse_line(line: str) -> Dict[str, Any]:
    """Parse a single line and return a dictionary"""
    line = line.strip()

    # 1. Try to parse as complete JSON object
    if line.startswith("{") and line.endswith("}"):
        try:
            return json.loads(line)
        except:
            pass

    # 2. Handle header-style entries (e.g., 3gpp-Sbi-Oci:...)
    if re.match(r'^[^"]+:[^"]*Timestamp:', line):
        return parse_header_style(line)

    # 3. Handle simple key:value with quotes
    if line.startswith('"') and '":' in line:
        return parse_quoted_key_value(line)

    # 4. Handle simple key:value without quotes
    if ":" in line and not line.startswith('"') and "Timestamp:" not in line:
        return parse_simple_key_value(line)

    # 5. Handle standalone quoted strings
    if line.startswith('"') and line.endswith('"') and ":" not in line:
        return parse_standalone_quoted(line)

    return {}


def parse_header_style(line: str) -> Dict[str, Any]:
    """Parse header-style entries like '3gpp-Sbi-Oci:Timestamp: ...'"""
    if ":" not in line:
        return {}

    # Split on first colon to get main key
    main_key, value_part = line.split(":", 1)
    main_key = main_key.strip()
    value_part = value_part.strip()

    # Parse the value part into sub-dictionary
    sub_dict = {}

    # Pattern to match key: value pairs in the value part
    pattern = r'([^:;]+):\s*"?([^";]+)"?'
    matches = re.findall(pattern, value_part)

    for key, value in matches:
        sub_dict[key.strip()] = value.strip()

    return {main_key: sub_dict}


def parse_quoted_key_value(line: str) -> Dict[str, Any]:
    """Parse quoted key:value pairs like '"autoCreate":true'"""
    try:
        # Try to parse as JSON first
        return json.loads("{" + line + "}")
    except:
        # Manual parsing
        if '":' in line:
            key_part, value_part = line.split('":', 1)
            key = key_part.strip('"')
            value = value_part.strip()

            # Try to convert value to appropriate type
            if value.lower() == "true":
                value = True
            elif value.lower() == "false":
                value = False
            elif value.isdigit():
                value = int(value)
            else:
                value = value.strip('"')

            return {key: value}
    return {}


def parse_simple_key_value(line: str) -> Dict[str, Any]:
    """Parse simple key:value pairs like 'server: UDR-...'"""
    if ":" not in line:
        return {}

    key, value = line.split(":", 1)
    key = key.strip().strip('"')
    value = value.strip().strip('"')

    return {key: value}


def parse_standalone_quoted(line: str) -> Dict[str, Any]:
    """Parse standalone quoted strings"""
    content = line.strip('"')
    # Use the content as both key and indicate it's a standalone value
    return {f"standalone_{len(content)}": content}


def merge_dict(target: Dict[str, Any], source: Dict[str, Any]) -> None:
    """Merge source dictionary into target, handling duplicates"""
    for key, value in source.items():
        if key in target:
            # Handle duplicate keys by making them lists
            if not isinstance(target[key], list):
                target[key] = [target[key]]
            target[key].append(value)
        else:
            target[key] = value
