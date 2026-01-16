"""
Setup command for initializing Cloudstrate environment.

Configures Neo4j, validates AWS/GitHub permissions, and creates config files.
"""

import os
import subprocess
import sys
import time
from pathlib import Path

import click


@click.group()
def setup():
    """Set up and configure Cloudstrate environment."""
    pass


@setup.command()
@click.option(
    "--neo4j-password",
    prompt=True,
    hide_input=True,
    confirmation_prompt=True,
    help="Password for Neo4j database",
)
@click.option(
    "--aws-profile",
    default=None,
    help="AWS profile to use for scanning",
)
@click.option(
    "--github-org",
    default=None,
    help="GitHub organization to scan",
)
@click.option(
    "--skip-neo4j",
    is_flag=True,
    help="Skip Neo4j setup",
)
@click.option(
    "--skip-aws",
    is_flag=True,
    help="Skip AWS validation",
)
@click.option(
    "--skip-github",
    is_flag=True,
    help="Skip GitHub validation",
)
@click.pass_context
def init(
    ctx: click.Context,
    neo4j_password: str,
    aws_profile: str | None,
    github_org: str | None,
    skip_neo4j: bool,
    skip_aws: bool,
    skip_github: bool,
) -> None:
    """Initialize Cloudstrate environment.

    Sets up Neo4j database, validates AWS and GitHub permissions,
    and creates configuration file.

    Example:
        cloudstrate setup init --aws-profile my-org --github-org my-org
    """
    click.echo("\n" + "=" * 60)
    click.echo("  CLOUDSTRATE SETUP")
    click.echo("=" * 60 + "\n")

    config_data = {
        "neo4j": {
            "uri": "bolt://localhost:7687",
            "user": "neo4j",
            "password": neo4j_password,
        },
        "scanner": {"aws": {}, "github": {}},
    }

    success = True

    # Step 1: Neo4j Setup
    if not skip_neo4j:
        click.echo("[1/3] Setting up Neo4j database...")
        neo4j_ok = _setup_neo4j(neo4j_password)
        if not neo4j_ok:
            success = False
        click.echo()

    # Step 2: AWS Setup
    if not skip_aws:
        click.echo("[2/3] Validating AWS permissions...")
        aws_ok, aws_config = _setup_aws(aws_profile)
        if aws_ok:
            config_data["scanner"]["aws"] = aws_config
        else:
            success = False
        click.echo()

    # Step 3: GitHub Setup
    if not skip_github:
        click.echo("[3/3] Validating GitHub permissions...")
        github_ok, github_config = _setup_github(github_org)
        if github_ok:
            config_data["scanner"]["github"] = github_config
        else:
            success = False
        click.echo()

    # Write config file
    config_path = Path("cloudstrate-config.yaml")
    _write_config(config_path, config_data)
    click.echo(f"Configuration written to: {config_path}")

    # Summary
    click.echo("\n" + "=" * 60)
    if success:
        click.echo("  SETUP COMPLETE")
        click.echo("=" * 60)
        click.echo("\nNext steps:")
        click.echo("  1. Run a scan:      cloudstrate scan aws --profile <profile>")
        click.echo("  2. Run mapping:     cloudstrate map phase1 <scan.json>")
        click.echo("  3. Start analyst:   cloudstrate analyst serve")
    else:
        click.echo("  SETUP INCOMPLETE - Some components failed")
        click.echo("=" * 60)
        click.echo("\nRe-run setup after fixing the issues above.")
        sys.exit(1)


@setup.command()
@click.option(
    "--neo4j-uri",
    default="bolt://localhost:7687",
    help="Neo4j connection URI",
)
@click.option(
    "--neo4j-password",
    envvar="NEO4J_PASSWORD",
    help="Neo4j password",
)
@click.pass_context
def neo4j(ctx: click.Context, neo4j_uri: str, neo4j_password: str | None) -> None:
    """Set up Neo4j database and create schema.

    Starts Neo4j if not running, creates indexes and constraints.

    Example:
        cloudstrate setup neo4j --neo4j-password secret
    """
    if not neo4j_password:
        neo4j_password = click.prompt("Neo4j password", hide_input=True)

    click.echo("Setting up Neo4j...")
    _setup_neo4j(neo4j_password, neo4j_uri)


@setup.command()
@click.option(
    "--profile",
    "-p",
    default=None,
    help="AWS profile to validate",
)
@click.option(
    "--show-policy",
    is_flag=True,
    help="Show required IAM policy",
)
@click.pass_context
def aws(ctx: click.Context, profile: str | None, show_policy: bool) -> None:
    """Validate AWS credentials and permissions.

    Checks that the AWS profile has required permissions for scanning.

    Example:
        cloudstrate setup aws --profile my-org-profile
    """
    if show_policy:
        from cloudstrate.setup.aws import AWSSetup
        setup = AWSSetup()
        click.echo("Required IAM Policy:")
        click.echo(setup.get_required_policy())
        return

    click.echo("Validating AWS permissions...")
    _setup_aws(profile)


@setup.command()
@click.option(
    "--org",
    "-o",
    default=None,
    help="GitHub organization to validate",
)
@click.option(
    "--show-scopes",
    is_flag=True,
    help="Show required token scopes",
)
@click.pass_context
def github(ctx: click.Context, org: str | None, show_scopes: bool) -> None:
    """Validate GitHub token and permissions.

    Checks that the GitHub token has required permissions for scanning.

    Example:
        cloudstrate setup github --org my-org
    """
    if show_scopes:
        from cloudstrate.setup.github import GitHubSetup
        setup = GitHubSetup()
        click.echo(setup.get_required_scopes_help())
        return

    click.echo("Validating GitHub permissions...")
    _setup_github(org)


@setup.command()
@click.pass_context
def check(ctx: click.Context) -> None:
    """Check status of all Cloudstrate components.

    Validates Neo4j connection, AWS credentials, and GitHub token.

    Example:
        cloudstrate setup check
    """
    click.echo("\n" + "=" * 60)
    click.echo("  CLOUDSTRATE STATUS CHECK")
    click.echo("=" * 60 + "\n")

    # Load config if exists
    config_path = Path("cloudstrate-config.yaml")
    config = {}
    if config_path.exists():
        import yaml
        with open(config_path) as f:
            config = yaml.safe_load(f) or {}

    # Check Neo4j
    click.echo("[Neo4j]")
    neo4j_config = config.get("neo4j", {})
    _check_neo4j(
        neo4j_config.get("uri", "bolt://localhost:7687"),
        neo4j_config.get("password"),
    )
    click.echo()

    # Check AWS
    click.echo("[AWS]")
    aws_config = config.get("scanner", {}).get("aws", {})
    _check_aws(aws_config.get("profile"))
    click.echo()

    # Check GitHub
    click.echo("[GitHub]")
    github_config = config.get("scanner", {}).get("github", {})
    _check_github(github_config.get("organization"))


def _setup_neo4j(password: str, uri: str = "bolt://localhost:7687") -> bool:
    """Set up Neo4j database."""
    from cloudstrate.setup.neo4j import Neo4jSetup

    setup = Neo4jSetup(uri=uri, password=password)

    # Check if Neo4j is installed
    installed, version = setup.check_neo4j_installed()
    if installed:
        click.echo(f"  Neo4j installed: {version}")
    else:
        click.echo(f"  Neo4j not found locally")
        # Try to start with Docker
        if _start_neo4j_docker(password):
            click.echo("  Started Neo4j in Docker")
            time.sleep(5)  # Wait for startup
        else:
            click.echo("  ERROR: Could not start Neo4j")
            click.echo("  Install Neo4j or Docker to continue")
            return False

    # Check connection
    status = setup.check_connection()
    if status.connected:
        click.echo(f"  Connected to Neo4j {status.version}")
        click.echo(f"  Database: {status.database}")
        click.echo(f"  Existing nodes: {status.node_count}")
    else:
        click.echo(f"  ERROR: {status.error}")
        return False

    # Create indexes
    click.echo("  Creating schema indexes...")
    index_status = setup.create_indexes(verbose=False)
    if index_status.connected:
        click.echo(f"  Created {index_status.indexes_created} indexes")
        click.echo(f"  Created {index_status.constraints_created} constraints")
    else:
        click.echo(f"  WARNING: Could not create indexes: {index_status.error}")

    click.echo("  Neo4j setup complete")
    return True


def _start_neo4j_docker(password: str) -> bool:
    """Start Neo4j using Docker."""
    try:
        # Check if Docker is available
        result = subprocess.run(
            ["docker", "--version"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return False

        # Check if container already exists
        result = subprocess.run(
            ["docker", "ps", "-a", "--filter", "name=cloudstrate-neo4j", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
        )
        if "cloudstrate-neo4j" in result.stdout:
            # Start existing container
            subprocess.run(["docker", "start", "cloudstrate-neo4j"], capture_output=True)
            return True

        # Create and start new container
        result = subprocess.run(
            [
                "docker", "run", "-d",
                "--name", "cloudstrate-neo4j",
                "-p", "7474:7474",
                "-p", "7687:7687",
                "-e", f"NEO4J_AUTH=neo4j/{password}",
                "-e", "NEO4J_PLUGINS=[\"apoc\"]",
                "-v", "cloudstrate-neo4j-data:/data",
                "neo4j:5",
            ],
            capture_output=True,
            text=True,
        )
        return result.returncode == 0

    except Exception:
        return False


def _setup_aws(profile: str | None) -> tuple[bool, dict]:
    """Set up and validate AWS."""
    from cloudstrate.setup.aws import AWSSetup

    setup = AWSSetup(profile=profile)

    # Check credentials
    status = setup.check_credentials()
    if not status.authenticated:
        click.echo(f"  ERROR: {status.error}")
        return False, {}

    click.echo(f"  Authenticated as: {status.user_arn}")
    click.echo(f"  Account: {status.account_id}")
    if status.account_alias:
        click.echo(f"  Alias: {status.account_alias}")
    if status.is_organization_account:
        click.echo(f"  Organization management account")

    # Check permissions
    status = setup.check_permissions()

    failed = status.failed_permissions
    if failed:
        click.echo(f"  WARNING: {len(failed)} permission checks failed:")
        for check in failed:
            click.echo(f"    - {check.service}:{check.action}: {check.error}")
        click.echo("  Run 'cloudstrate setup aws --show-policy' for required IAM policy")
    else:
        click.echo(f"  All {len(status.permission_checks)} permission checks passed")

    click.echo("  AWS setup complete")
    return True, {"profile": profile, "regions": ["us-east-1"]}


def _setup_github(org: str | None) -> tuple[bool, dict]:
    """Set up and validate GitHub."""
    from cloudstrate.setup.github import GitHubSetup

    setup = GitHubSetup(organization=org)

    # Check token
    status = setup.check_token()
    if not status.authenticated:
        click.echo(f"  ERROR: {status.error}")
        click.echo("  Run 'cloudstrate setup github --show-scopes' for help")
        return False, {}

    click.echo(f"  Authenticated as: {status.username}")
    click.echo(f"  Token type: {status.token_type}")

    if org:
        if status.org_accessible:
            click.echo(f"  Organization '{org}' accessible")
        else:
            click.echo(f"  WARNING: Cannot access organization '{org}'")
            if status.error:
                click.echo(f"    {status.error}")

    # Check permissions
    status = setup.check_permissions()
    failed = [p for p in status.permission_checks if not p.allowed]
    if failed:
        click.echo(f"  WARNING: {len(failed)} permission checks failed:")
        for check in failed:
            click.echo(f"    - {check.scope}: {check.error}")
    else:
        click.echo(f"  All permission checks passed")

    click.echo("  GitHub setup complete")
    return True, {"organization": org}


def _check_neo4j(uri: str, password: str | None) -> None:
    """Check Neo4j status."""
    from cloudstrate.setup.neo4j import Neo4jSetup

    if not password:
        click.echo("  Status: Not configured (no password in config)")
        return

    setup = Neo4jSetup(uri=uri, password=password)
    status = setup.check_connection()

    if status.connected:
        click.echo(f"  Status: Connected")
        click.echo(f"  Version: {status.version}")
        click.echo(f"  Nodes: {status.node_count}")
    else:
        click.echo(f"  Status: Not connected")
        click.echo(f"  Error: {status.error}")


def _check_aws(profile: str | None) -> None:
    """Check AWS status."""
    from cloudstrate.setup.aws import AWSSetup

    setup = AWSSetup(profile=profile)
    status = setup.check_credentials()

    if status.authenticated:
        click.echo(f"  Status: Authenticated")
        click.echo(f"  Account: {status.account_id}")
        click.echo(f"  User: {status.user_arn}")
    else:
        click.echo(f"  Status: Not authenticated")
        click.echo(f"  Error: {status.error}")


def _check_github(org: str | None) -> None:
    """Check GitHub status."""
    from cloudstrate.setup.github import GitHubSetup

    setup = GitHubSetup(organization=org)
    status = setup.check_token()

    if status.authenticated:
        click.echo(f"  Status: Authenticated")
        click.echo(f"  User: {status.username}")
        if org:
            click.echo(f"  Organization: {org} ({'accessible' if status.org_accessible else 'not accessible'})")
    else:
        click.echo(f"  Status: Not authenticated")
        click.echo(f"  Error: {status.error}")


def _write_config(path: Path, config: dict) -> None:
    """Write configuration file."""
    import yaml

    with open(path, "w") as f:
        f.write("# Cloudstrate Configuration\n")
        f.write("# Generated by cloudstrate setup init\n\n")
        yaml.dump(config, f, default_flow_style=False)
