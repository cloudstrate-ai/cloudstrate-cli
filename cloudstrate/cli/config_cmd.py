"""
Configuration commands for managing Cloudstrate settings.

Provides commands to view, set, and validate configuration.
"""

import click
import sys
from pathlib import Path


@click.group(name="config")
def config_cmd():
    """Manage Cloudstrate configuration."""
    pass


@config_cmd.command(name="show")
@click.option(
    "--format",
    "-f",
    type=click.Choice(["yaml", "json", "table"]),
    default="yaml",
    help="Output format",
)
@click.pass_context
def show_config(ctx: click.Context, format: str) -> None:
    """Show current configuration.

    Displays the loaded configuration from cloudstrate-config.yaml.

    Example:
        cloudstrate config show --format yaml
    """
    config = ctx.obj.get("config", {})

    if format == "yaml":
        import yaml
        click.echo(yaml.dump(config.model_dump() if hasattr(config, 'model_dump') else config, default_flow_style=False))
    elif format == "json":
        import json
        click.echo(json.dumps(config.model_dump() if hasattr(config, 'model_dump') else config, indent=2))
    else:
        # Table format
        def print_dict(d, indent=0):
            for key, value in d.items():
                if isinstance(value, dict):
                    click.echo("  " * indent + f"{key}:")
                    print_dict(value, indent + 1)
                else:
                    click.echo("  " * indent + f"{key}: {value}")

        data = config.model_dump() if hasattr(config, 'model_dump') else config
        print_dict(data)


@config_cmd.command(name="set")
@click.argument("key")
@click.argument("value")
@click.option(
    "--config-file",
    "-c",
    type=click.Path(),
    default="cloudstrate-config.yaml",
    help="Configuration file to modify",
)
def set_config(key: str, value: str, config_file: str) -> None:
    """Set a configuration value.

    Updates a configuration value in cloudstrate-config.yaml.
    Use dot notation for nested keys.

    Example:
        cloudstrate config set llm.provider ollama
        cloudstrate config set neo4j.uri bolt://remote:7687
    """
    import yaml

    config_path = Path(config_file)

    # Load existing config or start fresh
    if config_path.exists():
        with open(config_path) as f:
            config = yaml.safe_load(f) or {}
    else:
        config = {}

    # Parse the key path and set value
    keys = key.split(".")
    current = config

    for k in keys[:-1]:
        if k not in current:
            current[k] = {}
        current = current[k]

    # Try to parse value as int, float, bool, or keep as string
    if value.lower() == "true":
        value = True
    elif value.lower() == "false":
        value = False
    else:
        try:
            value = int(value)
        except ValueError:
            try:
                value = float(value)
            except ValueError:
                pass  # Keep as string

    current[keys[-1]] = value

    # Write back
    with open(config_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False)

    click.echo(f"Set {key} = {value} in {config_file}")


@config_cmd.command(name="init")
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default="cloudstrate-config.yaml",
    help="Output file for configuration",
)
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Overwrite existing configuration",
)
def init_config(output: str, force: bool) -> None:
    """Initialize a new configuration file.

    Creates a cloudstrate-config.yaml with default values.

    Example:
        cloudstrate config init --output cloudstrate-config.yaml
    """
    import yaml

    output_path = Path(output)

    if output_path.exists() and not force:
        click.echo(f"Configuration file already exists: {output}", err=True)
        click.echo("Use --force to overwrite")
        sys.exit(1)

    default_config = {
        "llm": {
            "provider": "gemini",
            "gemini": {
                "model": "gemini-2.0-flash-exp",
            },
            "ollama": {
                "model": "llama3.1:70b",
                "url": "http://localhost:11434",
            },
        },
        "neo4j": {
            "uri": "bolt://localhost:7687",
            "user": "neo4j",
            "password": "",  # User must set this
        },
        "state": {
            "backend": "github",
            "github": {
                "repo": "",
                "branch": "main",
                "path": "cloudstrate-state",
            },
        },
        "scanner": {
            "aws": {
                "profile": "",
                "regions": ["us-east-1"],
            },
        },
        "analyst": {
            "port": 5001,
            "enable_cloudtrail": True,
        },
    }

    with open(output_path, "w") as f:
        f.write("# Cloudstrate Configuration\n")
        f.write("# See documentation for all available options\n\n")
        yaml.dump(default_config, f, default_flow_style=False)

    click.echo(f"Configuration initialized: {output}")
    click.echo("\nNext steps:")
    click.echo("  1. Edit the configuration file to set your values")
    click.echo("  2. Set neo4j.password")
    click.echo("  3. Set scanner.aws.profile")


@config_cmd.command(name="validate")
@click.option(
    "--config-file",
    "-c",
    type=click.Path(exists=True),
    default="cloudstrate-config.yaml",
    help="Configuration file to validate",
)
def validate_config(config_file: str) -> None:
    """Validate a configuration file.

    Checks that the configuration is valid and all required values are set.

    Example:
        cloudstrate config validate --config-file cloudstrate-config.yaml
    """
    try:
        from cloudstrate.config.loader import load_config
        from cloudstrate.config.schema import CloudstrateConfig

        config = load_config(config_file)

        click.echo(f"Configuration file is valid: {config_file}")

        # Check for common issues
        warnings = []

        if not config.neo4j.password:
            warnings.append("neo4j.password is not set")

        if config.state.backend == "github" and not config.state.github.repo:
            warnings.append("state.github.repo is not set")

        if config.llm.provider == "gemini":
            import os
            if not os.environ.get("GEMINI_API_KEY"):
                warnings.append("GEMINI_API_KEY environment variable not set")

        if warnings:
            click.echo("\nWarnings:")
            for warning in warnings:
                click.echo(f"  - {warning}")
        else:
            click.echo("All required values are set.")

    except Exception as e:
        click.echo(f"Configuration validation failed: {e}", err=True)
        sys.exit(1)
