import json
import re
import os

def load_resource_map(resource_map_path):
    """Load the resource map from the given JSON file."""
    with open(resource_map_path, "r") as f:
        return json.load(f)

def save_resource_map(resource_map, resource_map_path):
    """Save the resource map to the given JSON file."""
    with open(resource_map_path, "w") as f:
        json.dump(resource_map, f, indent=4)

def map_localhost_url(url, resource_map):
    """
    Map a localhost URL to the correct FQDN using the resource map.
    Example:
    http://localhost:5001/nudr-config/v1/... -> http://ocslf-nudr-config.ocnrfslf.svc.tailgate.lab.us.oracle.com:5001/nudr-config/v1/...
    """
    match = re.search(r"http://localhost:(\\d+)/(\\w+)", url)
    if not match:
        return url  # No mapping possible
    port, key = match.groups()
    fqdn = resource_map.get(key)
    if not fqdn:
        return url  # No mapping found
    return re.sub(r"http://localhost:(\\d+)", f"http://{fqdn}:\\1", url)

def build_resource_map_from_virtualservices(virtualservice_fqdns):
    """
    Given a list of FQDNs, build a resource map where the key is the service name (first segment) and the value is the FQDN.
    Example: 'ocslf-nudr-config.ocnrfslf.svc.tailgate.lab.us.oracle.com' -> key: 'nudr-config', value: FQDN
    """
    resource_map = {}
    for fqdn in virtualservice_fqdns:
        # Extract the service key from the FQDN, e.g., ocslf-nudr-config -> nudr-config
        match = re.match(r"[\w-]+-(\w+)\\.", fqdn)
        if match:
            key = match.group(1)
            resource_map[key] = fqdn
    return resource_map

def discover_virtualservices(namespace=None):
    """
    Discover virtualservices using kubectl. Returns a list of FQDNs.
    """
    import subprocess
    cmd = ["kubectl", "get", "virtualservices", "-o", "json"]
    if namespace:
        cmd = ["kubectl", "get", "virtualservices", "-n", namespace, "-o", "json"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"kubectl error: {result.stderr}")
    data = json.loads(result.stdout)
    fqdns = []
    for item in data.get("items", []):
        # Try to extract host FQDNs from spec.hosts
        hosts = item.get("spec", {}).get("hosts", [])
        fqdns.extend(hosts)
    return fqdns

def automate_virtualservice_mapping_and_url_rewriting(urls, resource_map_path="config/resource_map.json", namespace=None):
    """
    Automate the process: discover virtualservices, build & save resource map, rewrite localhost URLs.
    Returns the rewritten URLs.
    """
    # Step 1: Discover virtualservices
    fqdns = discover_virtualservices(namespace)
    # Step 2: Build and save resource map
    resource_map = build_resource_map_from_virtualservices(fqdns)
    save_resource_map(resource_map, resource_map_path)
    # Step 3: Rewrite URLs
    rewritten_urls = [map_localhost_url(url, resource_map) for url in urls]
    return rewritten_urls

def get_connect_to_and_pod_mode(hosts_json_path):
    """
    Read hosts.json and return connect_to (as a list) and pod_mode (bool)
    """
    with open(hosts_json_path, "r") as f:
        data = json.load(f)
    connect_to = data.get("connect_to", "all")
    if isinstance(connect_to, str):
        connect_to = [x.strip() for x in connect_to.split(",")]
    pod_mode = bool(data.get("pod_mode", False))
    return connect_to, pod_mode
