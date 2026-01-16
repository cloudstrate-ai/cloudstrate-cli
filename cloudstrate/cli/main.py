"""
Main CLI entry point for Cloudstrate.

Provides the root command group and imports all subcommands.
"""

import click
from cloudstrate import __version__


@click.group()
@click.version_option(version=__version__, prog_name="cloudstrate")
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True),
    help="Path to cloudstrate-config.yaml",
    envvar="CLOUDSTRATE_CONFIG",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Enable verbose output",
)
@click.pass_context
def cli(ctx: click.Context, config: str | None, verbose: bool) -> None:
    """Cloudstrate - Multi-cloud governance platform.

    Scan, map, analyze, and generate Terraform for your cloud infrastructure.
    """
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    ctx.obj["config_path"] = config

    # Load configuration if specified
    if config:
        from cloudstrate.config.loader import load_config
        ctx.obj["config"] = load_config(config)
    else:
        from cloudstrate.config.loader import load_default_config
        ctx.obj["config"] = load_default_config()


# Import and register subcommands
from cloudstrate.cli.scan import scan
from cloudstrate.cli.map import map_cmd
from cloudstrate.cli.analyst import analyst
from cloudstrate.cli.build import build
from cloudstrate.cli.config_cmd import config_cmd
from cloudstrate.cli.setup import setup

cli.add_command(scan)
cli.add_command(map_cmd)
cli.add_command(analyst)
cli.add_command(build)
cli.add_command(config_cmd)
cli.add_command(setup)
