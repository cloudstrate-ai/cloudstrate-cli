"""
Scan commands for discovering cloud infrastructure.

Supports AWS, Kubernetes, and GitHub scanning.
"""

import click
import json
import sys
from pathlib import Path


@click.group()
def scan():
    """Scan cloud infrastructure and repositories."""
    pass


@scan.command()
@click.option(
    "--profile",
    "-p",
    required=True,
    help="AWS profile name for authentication",
)
@click.option(
    "--regions",
    "-r",
    multiple=True,
    default=["us-east-1"],
    help="AWS regions to scan (can be specified multiple times)",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default="aws-scan.json",
    help="Output file path for scan results",
)
@click.option(
    "--include-iam/--no-include-iam",
    default=True,
    help="Include IAM roles and policies in scan",
)
@click.option(
    "--include-network/--no-include-network",
    default=True,
    help="Include VPCs and network topology in scan",
)
@click.pass_context
def aws(
    ctx: click.Context,
    profile: str,
    regions: tuple[str, ...],
    output: str,
    include_iam: bool,
    include_network: bool,
) -> None:
    """Scan AWS organization structure and resources.

    Discovers accounts, OUs, IAM roles, VPCs, and cross-account relationships.

    Example:
        cloudstrate scan aws --profile my-org-profile --output scan.json
    """
    click.echo(f"Scanning AWS with profile: {profile}")
    click.echo(f"Regions: {', '.join(regions)}")

    try:
        from cloudstrate.scanner.aws import AWSScanner

        scanner = AWSScanner(
            profile=profile,
            regions=list(regions),
            include_iam=include_iam,
            include_network=include_network,
        )

        with click.progressbar(length=100, label="Scanning") as bar:
            result = scanner.scan(progress_callback=lambda p: bar.update(int(p)))

        # Write output
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w") as f:
            json.dump(result, f, indent=2, default=str)

        click.echo(f"\nScan complete. Results written to: {output}")
        click.echo(f"  Accounts discovered: {len(result.get('accounts', []))}")
        click.echo(f"  OUs discovered: {len(result.get('organizational_units', []))}")

    except ImportError as e:
        click.echo(f"Error: Scanner module not available: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error during scan: {e}", err=True)
        if ctx.obj.get("verbose"):
            import traceback
            traceback.print_exc()
        sys.exit(1)


@scan.command()
@click.option(
    "--context",
    "-c",
    help="Kubernetes context to use (defaults to current context)",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default="k8s-scan.json",
    help="Output file path for scan results",
)
@click.pass_context
def kubernetes(ctx: click.Context, context: str | None, output: str) -> None:
    """Scan Kubernetes cluster resources.

    Discovers namespaces, deployments, services, and RBAC configuration.

    Example:
        cloudstrate scan kubernetes --context prod-cluster --output k8s.json
    """
    click.echo(f"Scanning Kubernetes cluster: {context or 'current context'}")
    click.echo("Note: Kubernetes scanner not yet implemented")
    # TODO: Implement Kubernetes scanner


@scan.command()
@click.option(
    "--org",
    "-o",
    required=True,
    help="GitHub organization name",
)
@click.option(
    "--output",
    type=click.Path(),
    default="github-scan.json",
    help="Output file path for scan results",
)
@click.option(
    "--include-workflows/--no-include-workflows",
    default=True,
    help="Include GitHub Actions workflows in scan",
)
@click.pass_context
def github(
    ctx: click.Context,
    org: str,
    output: str,
    include_workflows: bool,
) -> None:
    """Scan GitHub organization repositories and configuration.

    Discovers repositories, workflows, and OIDC configurations.

    Example:
        cloudstrate scan github --org my-org --output github.json
    """
    click.echo(f"Scanning GitHub organization: {org}")

    try:
        from cloudstrate.scanner.github import GitHubScanner

        scanner = GitHubScanner(
            organization=org,
            include_workflows=include_workflows,
        )

        result = scanner.scan()

        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w") as f:
            json.dump(result, f, indent=2, default=str)

        click.echo(f"Scan complete. Results written to: {output}")

    except ImportError as e:
        click.echo(f"Error: Scanner module not available: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error during scan: {e}", err=True)
        if ctx.obj.get("verbose"):
            import traceback
            traceback.print_exc()
        sys.exit(1)


@scan.command()
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True),
    required=True,
    help="Path to cartography config.yaml",
)
@click.option(
    "--neo4j-uri",
    default="bolt://localhost:7687",
    help="Neo4j connection URI",
)
@click.pass_context
def cartography(ctx: click.Context, config: str, neo4j_uri: str) -> None:
    """Run Cartography scan and import to Neo4j.

    Uses Cartography to scan AWS resources and import into Neo4j graph database.

    Example:
        cloudstrate scan cartography --config cartography/config.yaml
    """
    click.echo(f"Running Cartography scan with config: {config}")
    click.echo(f"Neo4j URI: {neo4j_uri}")

    try:
        from cloudstrate.scanner.cartography import CartographyScanner

        scanner = CartographyScanner(
            config_path=config,
            neo4j_uri=neo4j_uri,
        )

        scanner.run()
        click.echo("Cartography scan complete")

    except ImportError as e:
        click.echo(f"Error: Cartography module not available: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error during scan: {e}", err=True)
        if ctx.obj.get("verbose"):
            import traceback
            traceback.print_exc()
        sys.exit(1)
