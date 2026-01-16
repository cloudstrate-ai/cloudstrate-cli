"""
Map commands for creating Cloudstrate model from scanned infrastructure.

Supports Phase 1 (automatic mapping) and Phase 2 (interactive review).
"""

import click
import sys
from pathlib import Path


@click.group(name="map")
def map_cmd():
    """Map infrastructure to Cloudstrate model."""
    pass


@map_cmd.command()
@click.argument("scan_file", type=click.Path(exists=True))
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default="mapping-state.yaml",
    help="Output file for mapping state",
)
@click.option(
    "--decisions",
    "-d",
    type=click.Path(),
    help="Optional decisions file for pre-configured mappings",
)
@click.pass_context
def phase1(ctx: click.Context, scan_file: str, output: str, decisions: str | None) -> None:
    """Run Phase 1 automatic mapping.

    Analyzes scan results and creates initial Cloudstrate model with
    security zones, tenants, and subtenants.

    Example:
        cloudstrate map phase1 aws-scan.json --output state.yaml
    """
    click.echo(f"Running Phase 1 mapping on: {scan_file}")

    try:
        from cloudstrate.mapper.phase1 import Phase1Mapper

        mapper = Phase1Mapper(
            scan_file=scan_file,
            decisions_file=decisions,
        )

        state = mapper.run()

        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        mapper.save_state(output_path)

        click.echo(f"Phase 1 mapping complete. State written to: {output}")
        click.echo(f"  Security zones: {len(state.get('security_zones', []))}")
        click.echo(f"  Tenants: {len(state.get('tenants', []))}")
        click.echo(f"  Subtenants: {len(state.get('subtenants', []))}")

    except ImportError as e:
        click.echo(f"Error: Mapper module not available: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error during mapping: {e}", err=True)
        if ctx.obj.get("verbose"):
            import traceback
            traceback.print_exc()
        sys.exit(1)


@map_cmd.command()
@click.option(
    "--state",
    "-s",
    type=click.Path(exists=True),
    default="mapping-state.yaml",
    help="Path to mapping state file",
)
@click.option(
    "--port",
    "-p",
    default=5000,
    help="Port for review server",
)
@click.option(
    "--host",
    default="127.0.0.1",
    help="Host to bind review server to",
)
@click.pass_context
def phase2(ctx: click.Context, state: str, port: int, host: str) -> None:
    """Start Phase 2 interactive review server.

    Launches web UI for reviewing and refining the Cloudstrate model
    with AI-powered proposal generation.

    Example:
        cloudstrate map phase2 --state mapping-state.yaml --port 5000
    """
    click.echo(f"Starting Phase 2 review server on {host}:{port}")
    click.echo(f"State file: {state}")

    try:
        from cloudstrate.mapper.phase2 import Phase2Server

        server = Phase2Server(
            state_file=state,
            config=ctx.obj.get("config"),
        )

        click.echo(f"\nOpen http://{host}:{port} in your browser")
        server.run(host=host, port=port)

    except ImportError as e:
        click.echo(f"Error: Mapper module not available: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error starting server: {e}", err=True)
        if ctx.obj.get("verbose"):
            import traceback
            traceback.print_exc()
        sys.exit(1)


@map_cmd.command()
@click.option(
    "--state",
    "-s",
    type=click.Path(exists=True),
    required=True,
    help="Path to mapping state file",
)
@click.option(
    "--format",
    "-f",
    type=click.Choice(["yaml", "json", "table"]),
    default="table",
    help="Output format",
)
def show(state: str, format: str) -> None:
    """Show current mapping state.

    Displays security zones, tenants, and subtenants from the mapping state.

    Example:
        cloudstrate map show --state mapping-state.yaml --format table
    """
    import yaml
    import json

    with open(state) as f:
        data = yaml.safe_load(f)

    if format == "yaml":
        click.echo(yaml.dump(data, default_flow_style=False))
    elif format == "json":
        click.echo(json.dumps(data, indent=2))
    else:
        # Table format
        click.echo("\nSecurity Zones:")
        click.echo("-" * 50)
        for zone in data.get("security_zones", []):
            click.echo(f"  {zone['id']}: {zone.get('name', 'N/A')}")

        click.echo("\nTenants:")
        click.echo("-" * 50)
        for tenant in data.get("tenants", []):
            click.echo(f"  {tenant['id']}: {tenant.get('name', 'N/A')}")
            click.echo(f"    Security Zone: {tenant.get('security_zone')}")

        click.echo("\nSubtenants:")
        click.echo("-" * 50)
        for subtenant in data.get("subtenants", []):
            click.echo(f"  {subtenant['id']}: {subtenant.get('name', 'N/A')}")
            click.echo(f"    Tenant: {subtenant.get('tenant')}")
            click.echo(f"    Accounts: {len(subtenant.get('aws_accounts', []))}")
