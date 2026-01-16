"""
Configuration loading utilities.

Loads cloudstrate-config.yaml and environment variables.
"""

import os
import yaml
from pathlib import Path
from typing import Optional

from cloudstrate.config.schema import CloudstrateConfig


def find_config_file() -> Optional[Path]:
    """Find cloudstrate-config.yaml in standard locations.

    Search order:
    1. Current directory
    2. Parent directories (up to 5 levels)
    3. ~/.config/cloudstrate/
    4. /etc/cloudstrate/

    Returns:
        Path to config file if found, None otherwise.
    """
    # Check current and parent directories
    current = Path.cwd()
    for _ in range(5):
        config_path = current / "cloudstrate-config.yaml"
        if config_path.exists():
            return config_path
        current = current.parent

    # Check user config directory
    user_config = Path.home() / ".config" / "cloudstrate" / "cloudstrate-config.yaml"
    if user_config.exists():
        return user_config

    # Check system config directory
    system_config = Path("/etc/cloudstrate/cloudstrate-config.yaml")
    if system_config.exists():
        return system_config

    return None


def load_config(config_path: str | Path) -> CloudstrateConfig:
    """Load configuration from a YAML file.

    Args:
        config_path: Path to cloudstrate-config.yaml

    Returns:
        Validated CloudstrateConfig instance

    Raises:
        FileNotFoundError: If config file doesn't exist
        ValidationError: If config is invalid
    """
    config_path = Path(config_path)

    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_path) as f:
        raw_config = yaml.safe_load(f) or {}

    # Apply environment variable overrides
    raw_config = _apply_env_overrides(raw_config)

    return CloudstrateConfig(**raw_config)


def load_default_config() -> CloudstrateConfig:
    """Load configuration from default location or return defaults.

    Searches for cloudstrate-config.yaml in standard locations.
    If not found, returns default configuration.

    Returns:
        CloudstrateConfig instance
    """
    config_path = find_config_file()

    if config_path:
        return load_config(config_path)

    # Return defaults with environment overrides
    raw_config = _apply_env_overrides({})
    return CloudstrateConfig(**raw_config)


def _apply_env_overrides(config: dict) -> dict:
    """Apply environment variable overrides to configuration.

    Environment variables are mapped as:
    - CLOUDSTRATE_LLM_PROVIDER -> llm.provider
    - CLOUDSTRATE_NEO4J_URI -> neo4j.uri
    - CLOUDSTRATE_NEO4J_PASSWORD -> neo4j.password
    - etc.

    Args:
        config: Raw configuration dictionary

    Returns:
        Configuration with environment overrides applied
    """
    env_mappings = [
        ("CLOUDSTRATE_LLM_PROVIDER", ["llm", "provider"]),
        ("CLOUDSTRATE_NEO4J_URI", ["neo4j", "uri"]),
        ("CLOUDSTRATE_NEO4J_USER", ["neo4j", "user"]),
        ("CLOUDSTRATE_NEO4J_PASSWORD", ["neo4j", "password"]),
        ("CLOUDSTRATE_NEO4J_DATABASE", ["neo4j", "database"]),
        ("CLOUDSTRATE_STATE_BACKEND", ["state", "backend"]),
        ("CLOUDSTRATE_GITHUB_REPO", ["state", "github", "repo"]),
        ("CLOUDSTRATE_GITHUB_BRANCH", ["state", "github", "branch"]),
        ("CLOUDSTRATE_S3_BUCKET", ["state", "s3", "bucket"]),
        ("CLOUDSTRATE_AWS_PROFILE", ["scanner", "aws", "profile"]),
        ("CLOUDSTRATE_ANALYST_PORT", ["analyst", "port"]),
        ("CLOUDSTRATE_AUTH_MODE", ["auth", "mode"]),
    ]

    for env_var, path in env_mappings:
        value = os.environ.get(env_var)
        if value:
            _set_nested(config, path, value)

    return config


def _set_nested(d: dict, path: list[str], value: str) -> None:
    """Set a nested dictionary value.

    Args:
        d: Dictionary to modify
        path: List of keys for nested path
        value: Value to set
    """
    for key in path[:-1]:
        if key not in d:
            d[key] = {}
        d = d[key]

    # Try to convert to appropriate type
    final_key = path[-1]

    # Check if it should be an integer
    if final_key in ("port", "max_retries", "max_tokens", "context_window"):
        try:
            value = int(value)
        except ValueError:
            pass

    d[final_key] = value


def save_config(config: CloudstrateConfig, config_path: str | Path) -> None:
    """Save configuration to a YAML file.

    Args:
        config: CloudstrateConfig instance
        config_path: Path to save configuration
    """
    config_path = Path(config_path)
    config_path.parent.mkdir(parents=True, exist_ok=True)

    with open(config_path, "w") as f:
        f.write("# Cloudstrate Configuration\n")
        f.write("# See documentation for all available options\n\n")
        yaml.dump(config.model_dump(), f, default_flow_style=False)
