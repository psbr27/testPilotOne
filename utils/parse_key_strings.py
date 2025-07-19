# log_parser.py
import re
import json

def _parse_key_value_string(s):
    """
    Parses a string of key=value pairs, handling nested structures like {} and [].
    This is a simplified parser and might need adjustments for more complex nested structures.
    """
    result = {}
    # Use a regex to find key=value pairs, accounting for nested structures
    # This regex is simplified and might not catch all edge cases for very deep nesting.
    # It tries to capture content within brackets or until a comma or end of string.
    # It also handles key='value' or key="value"
    matches = re.finditer(r"(\w+)=(?:'([^']*)'|\"([^\"]*)\"|([^,{}[\]]+(?:{[^}]+}|\[[^\]]+\]|[^,}]*)))(?:\s*,\s*|$)", s)

    for match in matches:
        key = match.group(1).strip()
        # Prioritize single-quoted, then double-quoted, then unquoted
        value_str = match.group(2) or match.group(3) or match.group(4)
        value_str = value_str.strip() if value_str else ''

        # Try to convert to more appropriate types
        if value_str.startswith('[') and value_str.endswith(']'):
            # This is a list. Split by comma, handling single quotes.
            # Using a more robust split for list items, considering nested structures
            items = []
            # This regex splits by comma that is NOT inside square brackets or curly braces
            for item in re.split(r",\s*(?![^\[]*\])(?![^{]*})", value_str[1:-1]):
                item = item.strip()
                if item:
                    if '=' in item and not (item.startswith('{') or item.startswith('[')): # Check for key=value within list if not already a nested structure
                        sub_key, sub_val = item.split('=', 1)
                        items.append({sub_key.strip(): sub_val.strip().strip("'\"")})
                    elif item.startswith('{') and item.endswith('}'):
                        items.append(_parse_key_value_string(item[1:-1])) # Recursively parse nested dict
                    elif item.startswith('[') and item.endswith(']'):
                        # This case would need a recursive call for lists of lists
                        # For now, treat as string or further parsing might be needed
                        items.append(item)
                    else:
                        items.append(item.strip("'\""))
            result[key] = items
        elif value_str.startswith('{') and value_str.endswith('}'):
            # This is a nested dictionary. Recursively parse.
            result[key] = _parse_key_value_string(value_str[1:-1])
        elif value_str == 'null':
            result[key] = None
        elif value_str.lower() == 'true':
            result[key] = True
        elif value_str.lower() == 'false':
            result[key] = False
        elif re.fullmatch(r'-?\d+(\.\d+)?([eE][+-]?\d+)?', value_str): # Check if it's a number (int or float) including scientific notation
            try:
                result[key] = int(value_str)
            except ValueError:
                try:
                    result[key] = float(value_str)
                except ValueError:
                    result[key] = value_str.strip("'\"") # Fallback to string
        else:
            result[key] = value_str.strip("'\"") # Remove quotes if present
    return result

def parse_log_string_to_dict(log_entry_string):
    """
    Parses a complex log string containing 'message' and 'endOfBatch' fields
    into a structured Python dictionary.

    Args:
        log_entry_string (str): The raw log string to parse.
                                 Expected format: '"message": "...", "endOfBatch": false/true'

    Returns:
        dict: A dictionary representation of the parsed log entry, or an empty
              dictionary if parsing fails.
    """
    try:
        parsed_data = {}
        clean_log_string = log_entry_string.strip().replace('\n', '').replace('\t', '')

        # Extract message and endOfBatch parts
        message_match = re.search(r'"message":\s*"(.*?)",\s*"endOfBatch":\s*(true|false)', clean_log_string, re.DOTALL)

        if message_match:
            message_content = message_match.group(1)
            end_of_batch = message_match.group(2).lower() == 'true'

            parsed_data["endOfBatch"] = end_of_batch

            # Now, parse the complex 'message' content
            main_observation_match = re.match(
                r"Client observation\s*(\{.*\})\s*created for the request\. New headers are\s*\[(.*)\]",
                message_content, re.DOTALL
            )

            if main_observation_match:
                observation_str = main_observation_match.group(1)
                headers_str = main_observation_match.group(2)

                # Clean up escape characters in headers (e.g., \\" to ")
                headers_str = headers_str.replace('\\"', '"')

                # Parse the observation string
                observation_dict = _parse_key_value_string(observation_str)
                parsed_data["message_details"] = observation_dict

                # Parse headers
                headers = {}
                # Regex to split headers by colon, handling quoted values.
                # It looks for "key":"value" or key:"value" patterns.
                header_pairs = re.findall(r'([^:]+):"([^"]*)"', headers_str)
                for key, value in header_pairs:
                    headers[key.strip()] = value.strip()

                parsed_data["headers"] = headers
            else:
                # Fallback if the main observation pattern is not found
                parsed_data["message_details"] = message_content.strip()
    except Exception as e:
        # print(f"Error parsing log entry: {e}")
        parsed_data = {}

    return parsed_data

# if __name__ == "__main__":
#     # Example Usage:
#     test_log_string = """
#     "message": "Client observation {name=http.client.requests(null), error=null, context=name='http.client.requests', contextualName='null', error='null', lowCardinalityKeyValues=[http.method='PUT', http.status_code='UNKNOWN', spring.cloud.gateway.route.id='nrf_nfm_direct', spring.cloud.gateway.route.uri='egress://request.uri'], highCardinalityKeyValues=[http.uri='http://ocslf-egressgateway:8080/nnrf-nfm/v1/nf-instances/5a7bd676-ceeb-44bb-95e0-f6a55a328b03'], map=[class io.micrometer.core.instrument.Timer$Sample='io.micrometer.core.instrument.Timer$Sample@25d47ab0', class io.micrometer.core.instrument.LongTaskTimer$Sample='SampleImpl{duration(seconds)=1.9556E-5, duration(nanos)=19556.0, startTimeNanos=11466888301893055}'], parentObservation={name=http.server.requests(null), error=null, context=name='http.server.requests', contextualName='null', error='null', lowCardinalityKeyValues=[exception='none', method='PUT', outcome='SUCCESS', status='200', uri='UNKNOWN'], highCardinalityKeyValues=[http.url='/nnrf-nfm/v1/nf-instances/5a7bd676-ceeb-44bb-95e0-f6a55a328b03'], map=[class io.micrometer.core.instrument.Timer$Sample='io.micrometer.core.instrument.Timer$Sample@231d10af', class io.micrometer.core.instrument.LongTaskTimer$Sample='SampleImpl{duration(seconds)=0.00134436, duration(nanos)=1344360.0, startTimeNanos=11466888300582575}'], parentObservation=null}} created for the request. New headers are [x-http2-scheme:\"http\", host:\"ocslf-egressgateway:8080\", accept:\"*/*\", content-type:\"application/json; charset=utf-8\", 3gpp-sbi-max-rsp-time:\"1000\", 3gpp-sbi-sender-timestamp:\"Mon, 14 Jul 2025 16:59:22.483 GMT\", content-length:\"768\", x-http2-stream-id:\"7\", User-Agent:\"UDR-5a7bd676-ceeb-44bb-95e0-f6a55a328b03 udr001.oracle.com\", sbi-timer-feature:\"false\"]",
#     "endOfBatch": false
#     """
#     parsed_result = parse_log_string_to_dict(test_log_string)
#     print(json.dumps(parsed_result, indent=2))

#     print("\n--- Testing another example (if needed) ---")
#     another_log = """
#     "message": "Some simple message with key=value and another=123", "endOfBatch": true
#     """
#     parsed_another = parse_log_string_to_dict(another_log)
#     print(json.dumps(parsed_another, indent=2))