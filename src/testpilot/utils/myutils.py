import ast
import json
import re

from .curl_output_parser import analyze_curl_output


def set_pdb_trace():
    import pdb

    pdb.set_trace()


def replace_placeholder_in_command(command, service_map):
    # Use a regular expression to find all occurrences of {placeholder}
    # The pattern \{([^}]+)\} captures anything inside curly braces.
    matches = re.findall(r"\{([^}]+)\}", command)

    updated_command = command

    for placeholder_name in matches:
        if placeholder_name in service_map:
            # The value in svc_map is a string representation of a list, e.g., "['host.com']"
            # We need to convert it to an actual Python list to get the first element.
            try:
                service_value = service_map[placeholder_name]

                # Check if the value is already a string (not a list representation)
                if isinstance(service_value, str) and not (
                    service_value.startswith("[")
                    or service_value.startswith("(")
                ):
                    # It's a plain string, use it directly
                    replacement_value = service_value
                elif isinstance(service_value, (list, tuple)):
                    # It's already a list/tuple, use first element
                    if service_value:
                        replacement_value = service_value[0]
                    else:
                        print(
                            f"Warning: Service map value for '{placeholder_name}' is an empty list. Skipping replacement."
                        )
                        continue
                else:
                    # Try to parse as string representation of list
                    service_list = ast.literal_eval(str(service_value))
                    if service_list:  # Ensure the list is not empty
                        replacement_value = service_list[0]
                    else:
                        print(
                            f"Warning: Service map value for '{placeholder_name}' is an empty list. Skipping replacement."
                        )
                        continue
            except (ValueError, SyntaxError, TypeError) as e:
                print(
                    f"Error: Could not parse service map value for '{placeholder_name}': {service_map[placeholder_name]}. Error: {e}"
                )
                print(f"Value type: {type(service_map[placeholder_name])}")
                # Try to use the value as-is if it's a string-like object
                try:
                    replacement_value = str(service_map[placeholder_name])
                    print(f"Using string representation: {replacement_value}")
                except Exception as fallback_e:
                    print(f"Fallback conversion failed: {fallback_e}")
                    continue  # Skip this replacement if all parsing fails

            # Replace the {placeholder} with the actual service host
            # Use re.sub to replace based on the captured group, ensuring we replace
            # the exact {placeholder_name} that was found.
            # Using re.escape for the placeholder_name ensures special characters are treated literally.
            updated_command = re.sub(
                re.escape("{" + placeholder_name + "}"),
                replacement_value,
                updated_command,
            )
        else:
            # Handle the case where the placeholder is not found in the service map
            print(
                f"Warning: Placeholder '{placeholder_name}' not found in service map."
            )
            print(f"Available service map keys: {list(service_map.keys())}")
            print(f"Service map contents: {service_map}")
            # TODO: Consider whether this should be an error or warning

    return updated_command


def prettify_curl_output(output_string):
    lines = output_string.splitlines()
    analyze_curl_output(lines)


def compare_dicts_ignore_timestamp(filtered_dict1, filtered_dict2):
    """
    Compare two dictionaries while ignoring any keys containing 'timestamp' (case-insensitive)
    Returns: dict with comparison results
    """
    # rename the NF-Service-Instance key to NF-Instance
    # TODO: This is a temporary fix; please fix it in the input Excel file pattern_match
    if "NF-Service-Instance" in filtered_dict2.keys():
        filtered_dict2["NF-Instance"] = filtered_dict2.pop(
            "NF-Service-Instance"
        )

    # Get all unique keys from both dictionaries
    all_keys = set(filtered_dict1.keys()) | set(filtered_dict2.keys())

    # if Timestamp is present in filtered_dict1 or filtered_dict2, remove it
    filtered_dict1 = {
        k: v for k, v in filtered_dict1.items() if "timestamp" not in k.lower()
    }
    filtered_dict2 = {
        k: v for k, v in filtered_dict2.items() if "timestamp" not in k.lower()
    }

    # check the lengths of both dictionaries after filtering; if the length is not same
    # dont compare the dictionaries directly instead check if dict1 is present in dict2
    # and check the values of the dict1 key matches in dict2
    if len(filtered_dict1) != len(filtered_dict2):
        comparison = {
            "equal": False,
            "only_in_dict1": set(filtered_dict1.keys())
            - set(filtered_dict2.keys()),
            "only_in_dict2": set(filtered_dict2.keys())
            - set(filtered_dict1.keys()),
            "common_keys": set(filtered_dict1.keys())
            & set(filtered_dict2.keys()),
            "value_differences": {},
            "summary": {},
        }

        # Check value differences for common keys
        for key in comparison["common_keys"]:
            val1 = filtered_dict1.get(key)
            val2 = filtered_dict2.get(key)
            if val1 != val2:
                comparison["value_differences"][key] = {
                    "dict1_value": val1,
                    "dict2_value": val2,
                }
                if (
                    isinstance(val1, str)
                    and isinstance(val2, str)
                    and (val1 in val2 or val2 in val1)
                ):
                    # If one value is a substring of the other, consider it a match
                    comparison["value_differences"][key] = {
                        "dict1_value": val1,
                        "dict2_value": val2,
                    }
                    comparison["equal"] = True
            else:
                # If values are equal, we don't need to record them in value_differences
                comparison["equal"] = True

        # Create summary
        comparison["summary"] = {
            "total_keys_dict1": len(filtered_dict1),
            "total_keys_dict2": len(filtered_dict2),
            "common_keys_count": len(comparison["common_keys"]),
            "keys_only_in_dict1": len(comparison["only_in_dict1"]),
            "keys_only_in_dict2": len(comparison["only_in_dict2"]),
            "value_differences_count": len(comparison["value_differences"]),
        }
    else:
        # If lengths are the same, compare directly
        comparison = {
            "equal": filtered_dict1 == filtered_dict2,
            "only_in_dict1": set(filtered_dict1.keys())
            - set(filtered_dict2.keys()),
            "only_in_dict2": set(filtered_dict2.keys())
            - set(filtered_dict1.keys()),
            "common_keys": set(filtered_dict1.keys())
            & set(filtered_dict2.keys()),
            "value_differences": {},
            "summary": {},
        }

    return comparison
