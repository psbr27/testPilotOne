"""
Configuration resolver utility for handling environment variables and template substitution.
"""

import json
import os
import re
from typing import Any, Dict, Optional, Union


def resolve_env_vars(value: Any) -> Any:
    """
    Recursively resolve environment variables in configuration values.

    Supports:
    - ${VAR_NAME} - Required variable, raises error if not found
    - ${VAR_NAME:-default} - Optional variable with default value

    Args:
        value: Configuration value (string, dict, list, or other)

    Returns:
        Resolved value with environment variables substituted
    """
    if isinstance(value, str):
        # Pattern to match ${VAR} or ${VAR:-default}
        pattern = r"\$\{([^}]+)\}"

        def replacer(match):
            var_expr = match.group(1)

            # Check for default value syntax
            if ":-" in var_expr:
                var_name, default_value = var_expr.split(":-", 1)
                return os.getenv(var_name, default_value)
            else:
                # Required variable - raise error if not found
                env_value = os.getenv(var_expr)
                if env_value is None:
                    raise ValueError(
                        f"Required environment variable '{var_expr}' not found. "
                        f"Please set it before running TestPilot."
                    )
                return env_value

        # Only perform substitution if pattern is found
        if re.search(pattern, value):
            return re.sub(pattern, replacer, value)
        return value

    elif isinstance(value, dict):
        return {k: resolve_env_vars(v) for k, v in value.items()}

    elif isinstance(value, list):
        return [resolve_env_vars(item) for item in value]

    else:
        return value


def load_config_with_env(config_path: str) -> Dict[str, Any]:
    """
    Load configuration file and resolve environment variables.

    Args:
        config_path: Path to configuration file

    Returns:
        Loaded configuration with environment variables resolved

    Raises:
        ValueError: If required environment variables are missing
        FileNotFoundError: If configuration file doesn't exist
    """
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_path, "r") as f:
        config = json.load(f)

    # Resolve environment variables
    resolved_config = resolve_env_vars(config)

    return resolved_config


def validate_host_config(host_config: Dict[str, Any]) -> None:
    """
    Validate host configuration for required fields and security.

    Args:
        host_config: Host configuration dictionary

    Raises:
        ValueError: If configuration is invalid
    """
    required_fields = ["name", "hostname", "username"]

    for field in required_fields:
        if field not in host_config or not host_config[field]:
            raise ValueError(
                f"Host configuration missing required field: {field}"
            )

    # Ensure either password or key_file is provided, but not both
    has_password = host_config.get("password") is not None
    has_key = host_config.get("key_file") is not None

    if not has_password and not has_key:
        raise ValueError(
            f"Host '{host_config['name']}' must have either 'password' or 'key_file' configured"
        )

    if has_password and has_key:
        # Warning only - some users might need both
        import logging

        logger = logging.getLogger(__name__)
        logger.warning(
            f"Host '{host_config['name']}' has both password and key_file configured. "
            "Consider using only one authentication method for better security."
        )


def mask_sensitive_data(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a copy of configuration with sensitive data masked for logging.

    Args:
        config: Original configuration

    Returns:
        Configuration copy with sensitive fields masked
    """
    import copy

    masked = copy.deepcopy(config)

    sensitive_fields = [
        "password",
        "key_file",
        "private_key",
        "secret",
        "token",
    ]

    def mask_dict(d: Dict[str, Any]):
        for key, value in d.items():
            if any(sensitive in key.lower() for sensitive in sensitive_fields):
                if value:
                    d[key] = "***MASKED***"
            elif isinstance(value, dict):
                mask_dict(value)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        mask_dict(item)

    mask_dict(masked)
    return masked


def create_example_env_file(
    hosts_config: Dict[str, Any], output_path: str = ".env.example"
) -> None:
    """
    Generate an example .env file based on current configuration template.

    Args:
        hosts_config: Configuration dictionary with placeholder variables
        output_path: Path to write the example file
    """
    env_vars = set()

    # Extract all environment variable references
    def extract_vars(value: Any):
        if isinstance(value, str):
            matches = re.findall(r"\$\{([^}:]+)(?::-[^}]*)?\}", value)
            env_vars.update(matches)
        elif isinstance(value, dict):
            for v in value.values():
                extract_vars(v)
        elif isinstance(value, list):
            for item in value:
                extract_vars(item)

    extract_vars(hosts_config)

    # Generate example content
    content = [
        "# Auto-generated TestPilot environment variables example",
        "# Copy to .env and fill in your actual values",
        "# Generated from current configuration template",
        "",
    ]

    for var in sorted(env_vars):
        if var.startswith("HOST"):
            content.append(f"{var}=your_value_here")
        else:
            content.append(f"{var}=")

    with open(output_path, "w") as f:
        f.write("\n".join(content) + "\n")
