from typing import Any, Dict, List, Tuple

def _flatten_leaves(obj: Any, prefix: str = "") -> List[Tuple[str, Any]]:
    """
    Recursively traverse `obj` (dicts/lists) and return a list of
    (path, value) for every non‑dict/list leaf.
    e.g. {"a":{"b":1}} -> [("a.b",1)]
    """
    items: List[Tuple[str, Any]] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            path = f"{prefix}.{k}" if prefix else k
            items.extend(_flatten_leaves(v, path))
    elif isinstance(obj, list):
        for idx, v in enumerate(obj):
            path = f"{prefix}[{idx}]"
            items.extend(_flatten_leaves(v, path))
    else:
        items.append((prefix, obj))
    return items

def json_match_percent(expected: Dict[str, Any], actual: Dict[str, Any]) -> float:
    """
    Compute % of (path,value) pairs in `expected` that
    also appear exactly in `actual`.
    """
    exp_leaves = _flatten_leaves(expected)
    act_leaves = set(_flatten_leaves(actual))

    if not exp_leaves:
        # nothing expected → treat as perfect match
        return 100.0

    # count how many expected pairs are also in actual
    matches = sum(1 for leaf in exp_leaves if leaf in act_leaves)

    return matches / len(exp_leaves) * 100.0