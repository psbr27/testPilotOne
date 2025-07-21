import json
from typing import Any, Dict, List, Union, Tuple

def compare_json_objects(json1: Union[str, dict], json2: Union[str, dict], 
                        comparison_type: str = "structure_and_values") -> Dict[str, Any]:
    """
    Compare two JSON objects and return match percentage with detailed analysis.
    
    Args:
        json1: First JSON (string or dict)
        json2: Second JSON (string or dict)
        comparison_type: Type of comparison
            - "structure_only": Compare only keys/structure
            - "values_only": Compare only values (assuming same structure)
            - "structure_and_values": Compare both structure and values (default)
            - "deep": Deep comparison including nested objects
    
    Returns:
        Dict with match percentage and detailed comparison results
    """
    
    # Parse JSON strings if needed
    def parse_json(json_obj):
        if isinstance(json_obj, str):
            try:
                return json.loads(json_obj)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON string: {e}")
        return json_obj
    
    obj1 = parse_json(json1)
    obj2 = parse_json(json2)
    
    if comparison_type == "structure_only":
        return compare_structure_only(obj1, obj2)
    elif comparison_type == "values_only":
        return compare_values_only(obj1, obj2)
    elif comparison_type == "structure_and_values":
        return compare_structure_and_values(obj1, obj2)
    elif comparison_type == "deep":
        return deep_compare(obj1, obj2)
    else:
        raise ValueError("Invalid comparison_type")

def compare_structure_only(obj1: Any, obj2: Any) -> Dict[str, Any]:
    """Compare only the structure (keys) of JSON objects."""
    
    def get_structure(obj, path=""):
        if isinstance(obj, dict):
            return {f"{path}.{k}" if path else k: get_structure(v, f"{path}.{k}" if path else k) 
                   for k in obj.keys()}
        elif isinstance(obj, list):
            return [get_structure(item, f"{path}[{i}]") for i, item in enumerate(obj)]
        else:
            return type(obj).__name__
    
    structure1 = get_structure(obj1)
    structure2 = get_structure(obj2)
    
    def count_keys(struct):
        if isinstance(struct, dict):
            return len(struct) + sum(count_keys(v) for v in struct.values())
        elif isinstance(struct, list):
            return sum(count_keys(item) for item in struct)
        else:
            return 0
    
    keys1 = set(str(structure1).replace("'", '"'))
    keys2 = set(str(structure2).replace("'", '"'))
    
    total_keys = len(keys1.union(keys2))
    matching_keys = len(keys1.intersection(keys2))
    
    percentage = (matching_keys / total_keys * 100) if total_keys > 0 else 100
    
    return {
        "match_percentage": round(percentage, 2),
        "comparison_type": "structure_only",
        "total_keys": total_keys,
        "matching_keys": matching_keys,
        "missing_in_json2": list(keys1 - keys2),
        "missing_in_json1": list(keys2 - keys1)
    }

def compare_values_only(obj1: Any, obj2: Any) -> Dict[str, Any]:
    """Compare only values assuming same structure."""
    
    def extract_values(obj):
        if isinstance(obj, dict):
            return [extract_values(v) for v in obj.values()]
        elif isinstance(obj, list):
            return [extract_values(item) for item in obj]
        else:
            return obj
    
    values1 = str(extract_values(obj1))
    values2 = str(extract_values(obj2))
    
    # Simple string comparison for values
    if values1 == values2:
        percentage = 100.0
    else:
        # Calculate similarity based on common characters/substrings
        common_chars = sum(1 for c1, c2 in zip(values1, values2) if c1 == c2)
        max_length = max(len(values1), len(values2))
        percentage = (common_chars / max_length * 100) if max_length > 0 else 100
    
    return {
        "match_percentage": round(percentage, 2),
        "comparison_type": "values_only",
        "values_match": values1 == values2
    }

def compare_structure_and_values(obj1: Any, obj2: Any) -> Dict[str, Any]:
    """Compare both structure and values."""
    
    def flatten_json(obj, parent_key='', sep='.'):
        items = []
        if isinstance(obj, dict):
            for k, v in obj.items():
                new_key = f"{parent_key}{sep}{k}" if parent_key else k
                items.extend(flatten_json(v, new_key, sep=sep).items())
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                new_key = f"{parent_key}[{i}]"
                items.extend(flatten_json(v, new_key, sep=sep).items())
        else:
            return {parent_key: obj}
        return dict(items)
    
    flat1 = flatten_json(obj1)
    flat2 = flatten_json(obj2)
    
    all_keys = set(flat1.keys()).union(set(flat2.keys()))
    matching_pairs = 0
    total_pairs = len(all_keys)
    
    mismatched_keys = []
    missing_keys = []
    
    for key in all_keys:
        if key in flat1 and key in flat2:
            if flat1[key] == flat2[key]:
                matching_pairs += 1
            else:
                mismatched_keys.append({
                    "key": key,
                    "value1": flat1[key],
                    "value2": flat2[key]
                })
        else:
            missing_keys.append({
                "key": key,
                "present_in": "json1" if key in flat1 else "json2",
                "value": flat1.get(key, flat2.get(key))
            })
    
    percentage = (matching_pairs / total_pairs * 100) if total_pairs > 0 else 100
    
    return {
        "match_percentage": round(percentage, 2),
        "comparison_type": "structure_and_values",
        "total_fields": total_pairs,
        "matching_fields": matching_pairs,
        "mismatched_fields": len(mismatched_keys),
        "missing_fields": len(missing_keys),
        "mismatched_details": mismatched_keys,
        "missing_details": missing_keys
    }

def deep_compare(obj1: Any, obj2: Any) -> Dict[str, Any]:
    """Deep comparison with detailed analysis."""
    
    def deep_compare_recursive(o1, o2, path=""):
        results = {
            "matches": 0,
            "total": 0,
            "differences": []
        }
        
        if type(o1) != type(o2):
            results["total"] = 1
            results["differences"].append({
                "path": path,
                "type": "type_mismatch",
                "value1": f"{type(o1).__name__}: {o1}",
                "value2": f"{type(o2).__name__}: {o2}"
            })
            return results
        
        if isinstance(o1, dict):
            all_keys = set(o1.keys()).union(set(o2.keys()))
            for key in all_keys:
                current_path = f"{path}.{key}" if path else key
                if key not in o1:
                    results["total"] += 1
                    results["differences"].append({
                        "path": current_path,
                        "type": "missing_in_first",
                        "value2": o2[key]
                    })
                elif key not in o2:
                    results["total"] += 1
                    results["differences"].append({
                        "path": current_path,
                        "type": "missing_in_second",
                        "value1": o1[key]
                    })
                else:
                    sub_result = deep_compare_recursive(o1[key], o2[key], current_path)
                    results["matches"] += sub_result["matches"]
                    results["total"] += sub_result["total"]
                    results["differences"].extend(sub_result["differences"])
        
        elif isinstance(o1, list):
            max_len = max(len(o1), len(o2))
            for i in range(max_len):
                current_path = f"{path}[{i}]"
                if i >= len(o1):
                    results["total"] += 1
                    results["differences"].append({
                        "path": current_path,
                        "type": "missing_in_first",
                        "value2": o2[i]
                    })
                elif i >= len(o2):
                    results["total"] += 1
                    results["differences"].append({
                        "path": current_path,
                        "type": "missing_in_second",
                        "value1": o1[i]
                    })
                else:
                    sub_result = deep_compare_recursive(o1[i], o2[i], current_path)
                    results["matches"] += sub_result["matches"]
                    results["total"] += sub_result["total"]
                    results["differences"].extend(sub_result["differences"])
        
        else:
            results["total"] = 1
            if o1 == o2:
                results["matches"] = 1
            else:
                results["differences"].append({
                    "path": path,
                    "type": "value_mismatch",
                    "value1": o1,
                    "value2": o2
                })
        
        return results
    
    result = deep_compare_recursive(obj1, obj2)
    percentage = (result["matches"] / result["total"] * 100) if result["total"] > 0 else 100
    
    return {
        "match_percentage": round(percentage, 2),
        "comparison_type": "deep",
        "total_comparisons": result["total"],
        "successful_matches": result["matches"],
        "differences_count": len(result["differences"]),
        "differences": result["differences"]
    }

# # Example usage and test cases
# if __name__ == "__main__":
#     # Example JSONs
#     json1 = {
#         "name": "John",
#         "age": 30,
#         "city": "New York",
#         "hobbies": ["reading", "swimming"],
#         "address": {
#             "street": "123 Main St",
#             "zip": "10001"
#         }
#     }
    
#     json2 = {
#         "name": "John",
#         "age": 31,
#         "city": "New York",
#         "hobbies": ["reading", "cycling"],
#         "address": {
#             "street": "123 Main St",
#             "zip": "10001"
#         }
#     }
    
#     # Test all comparison types
#     print("=== Structure Only ===")
#     result = compare_json_objects(json1, json2, "structure_only")
#     print(f"Match: {result['match_percentage']}%")
    
#     print("\n=== Structure and Values ===")
#     result = compare_json_objects(json1, json2, "structure_and_values")
#     print(f"Match: {result['match_percentage']}%")
#     print(f"Mismatched fields: {result['mismatched_fields']}")
    
#     print("\n=== Deep Comparison ===")
#     result = compare_json_objects(json1, json2, "deep")
#     print(f"Match: {result['match_percentage']}%")
#     print(f"Differences: {result['differences_count']}")
    
#     # Quick function for simple percentage
#     def get_json_match_percentage(json1, json2):
#         """Quick function to get just the match percentage."""
#         result = compare_json_objects(json1, json2, "structure_and_values")
#         return result["match_percentage"]
    
#     # Usage: 
#     # percentage = get_json_match_percentage(your_json1, your_json2)
#     # print(f"JSON Match: {percentage}%")