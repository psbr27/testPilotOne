import ast
import json
import re
from utils.curl_output_parser import analyze_curl_output


def set_pdb_trace():
    import pdb; pdb.set_trace()

def replace_placeholder_in_command(command, service_map):
    # Use a regular expression to find all occurrences of {placeholder}
    # The pattern \{([^}]+)\} captures anything inside curly braces.
    matches = re.findall(r'\{([^}]+)\}', command)

    updated_command = command

    for placeholder_name in matches:
        if placeholder_name in service_map:
            # The value in svc_map is a string representation of a list, e.g., "['host.com']"
            # We need to convert it to an actual Python list to get the first element.
            try:
                # ast.literal_eval is safer than eval() for converting string literals
                service_list = ast.literal_eval(service_map[placeholder_name])
                if service_list: # Ensure the list is not empty
                    replacement_value = service_list[0]
                else:
                    print(f"Warning: Service map value for '{placeholder_name}' is an empty list. Skipping replacement.")
                    continue
            except (ValueError, SyntaxError) as e:
                print(f"Error: Could not parse service map value for '{placeholder_name}': {service_map[placeholder_name]}. Error: {e}")
                continue # Skip this replacement if parsing fails

            # Replace the {placeholder} with the actual service host
            # Use re.sub to replace based on the captured group, ensuring we replace
            # the exact {placeholder_name} that was found.
            # Using re.escape for the placeholder_name ensures special characters are treated literally.
            updated_command = re.sub(re.escape('{' + placeholder_name + '}'), replacement_value, updated_command)
        else:
            print(f"Warning: Placeholder '{placeholder_name}' not found in svc_map. Command not fully updated.")

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
    if 'NF-Service-Instance' in filtered_dict2.keys():
        filtered_dict2['NF-Instance'] = filtered_dict2.pop('NF-Service-Instance')
        
    # Get all unique keys from both dictionaries
    all_keys = set(filtered_dict1.keys()) | set(filtered_dict2.keys())
    
    # if Timestamp is present in filtered_dict1 or filtered_dict2, remove it
    filtered_dict1 = {k: v for k, v in filtered_dict1.items() if 'timestamp' not in k.lower()}
    filtered_dict2 = {k: v for k, v in filtered_dict2.items() if 'timestamp' not in k.lower()}
    
    # check the lengths of both dictionaries after filtering; if the length is not same
    # dont compare the dictionaries directly instead check if dict1 is present in dict2 
    # and check the values of the dict1 key matches in dict2
    if len(filtered_dict1) != len(filtered_dict2):
        comparison = {
            'equal': False,
            'only_in_dict1': set(filtered_dict1.keys()) - set(filtered_dict2.keys()),
            'only_in_dict2': set(filtered_dict2.keys()) - set(filtered_dict1.keys()),
            'common_keys': set(filtered_dict1.keys()) & set(filtered_dict2.keys()),
            'value_differences': {},
            'summary': {}
        }
        
        # Check value differences for common keys
        for key in comparison['common_keys']:
            val1 = filtered_dict1.get(key)
            val2 = filtered_dict2.get(key)
            if val1 != val2:
                comparison['value_differences'][key] = {
                    'dict1_value': val1,
                    'dict2_value': val2
                }
            else:
                comparison['equal'] = True  # If all common keys match, set equal to True
        
        # Create summary
        comparison['summary'] = {
            'total_keys_dict1': len(filtered_dict1),
            'total_keys_dict2': len(filtered_dict2),
            'common_keys_count': len(comparison['common_keys']),
            'keys_only_in_dict1': len(comparison['only_in_dict1']),
            'keys_only_in_dict2': len(comparison['only_in_dict2']),
            'value_differences_count': len(comparison['value_differences'])
        }
    else:
        # If lengths are the same, compare directly
        comparison = {
            'equal': filtered_dict1 == filtered_dict2,
            'only_in_dict1': set(filtered_dict1.keys()) - set(filtered_dict2.keys()),
            'only_in_dict2': set(filtered_dict2.keys()) - set(filtered_dict1.keys()),
            'common_keys': set(filtered_dict1.keys()) & set(filtered_dict2.keys()),
            'value_differences': {},
            'summary': {}
        }
        
    return comparison

# # Your test data
# dict1 = {'Timestamp': 'Mon, 02 May 2022 07:26:25 UTC', 'Load-Metric': '0.23533762%', 'NF-Instance': '5a7bd676-ceeb-44bb-95e0-f6a55a328b03'}
# dict2 = {'Load-Metric': '2%', 'NF-Service-Instance': '5a7bd676-ceeb-44bb-95e0-f6a55a328b03'}

# # Compare the dictionaries
# result = compare_dicts_ignore_timestamp(dict1, dict2)

# # Print results
# print("=== Dictionary Comparison (Ignoring Timestamps) ===")
# print(f"Dictionaries are equal: {result['equal']}")
# print(f"\nKeys only in dict1: {result['only_in_dict1']}")
# print(f"Keys only in dict2: {result['only_in_dict2']}")
# print(f"Common keys: {result['common_keys']}")

# if result['value_differences']:
#     print(f"\nValue differences:")
#     for key, values in result['value_differences'].items():
#         print(f"  {key}: '{values['dict1_value']}' vs '{values['dict2_value']}'")

# print(f"\n=== Summary ===")
# for key, value in result['summary'].items():
#     print(f"{key.replace('_', ' ').title()}: {value}")
