"""
Analyst commands for querying and analyzing infrastructure.

Provides natural language query interface and web UI.
"""

import click
import sys


@click.group()
def analyst():
    """Query and analyze infrastructure."""
    pass


@analyst.command()
@click.option(
    "--port",
    "-p",
    default=5001,
    help="Port for analyst server",
)
@click.option(
    "--host",
    default="127.0.0.1",
    help="Host to bind server to",
)
@click.option(
    "--neo4j-uri",
    default="bolt://localhost:7687",
    help="Neo4j connection URI",
    envvar="NEO4J_URI",
)
@click.option(
    "--neo4j-user",
    default="neo4j",
    help="Neo4j username",
    envvar="NEO4J_USER",
)
@click.option(
    "--neo4j-password",
    required=True,
    help="Neo4j password",
    envvar="NEO4J_PASSWORD",
)
@click.pass_context
def serve(
    ctx: click.Context,
    port: int,
    host: str,
    neo4j_uri: str,
    neo4j_user: str,
    neo4j_password: str,
) -> None:
    """Start the analyst web interface.

    Launches web UI for natural language queries against the infrastructure graph.

    Example:
        cloudstrate analyst serve --port 5001 --neo4j-password secret
    """
    click.echo(f"Starting Analyst server on {host}:{port}")
    click.echo(f"Neo4j: {neo4j_uri}")

    try:
        from cloudstrate.analyst.server import AnalystServer

        server = AnalystServer(
            neo4j_uri=neo4j_uri,
            neo4j_user=neo4j_user,
            neo4j_password=neo4j_password,
            config=ctx.obj.get("config"),
        )

        click.echo(f"\nOpen http://{host}:{port} in your browser")
        server.run(host=host, port=port)

    except ImportError as e:
        click.echo(f"Error: Analyst module not available: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error starting server: {e}", err=True)
        if ctx.obj.get("verbose"):
            import traceback
            traceback.print_exc()
        sys.exit(1)


@analyst.command()
@click.argument("question")
@click.option(
    "--neo4j-uri",
    default="bolt://localhost:7687",
    help="Neo4j connection URI",
    envvar="NEO4J_URI",
)
@click.option(
    "--neo4j-user",
    default="neo4j",
    help="Neo4j username",
    envvar="NEO4J_USER",
)
@click.option(
    "--neo4j-password",
    required=True,
    help="Neo4j password",
    envvar="NEO4J_PASSWORD",
)
@click.option(
    "--format",
    "-f",
    type=click.Choice(["text", "json", "table"]),
    default="text",
    help="Output format",
)
@click.pass_context
def query(
    ctx: click.Context,
    question: str,
    neo4j_uri: str,
    neo4j_user: str,
    neo4j_password: str,
    format: str,
) -> None:
    """Run a natural language query.

    Translates natural language to Cypher and executes against Neo4j.

    Example:
        cloudstrate analyst query "Show all production accounts"
    """
    click.echo(f"Query: {question}\n")

    try:
        from cloudstrate.analyst.query import AnalystQuery

        analyst_query = AnalystQuery(
            neo4j_uri=neo4j_uri,
            neo4j_user=neo4j_user,
            neo4j_password=neo4j_password,
            config=ctx.obj.get("config"),
        )

        result = analyst_query.execute(question)

        if format == "json":
            import json
            click.echo(json.dumps(result, indent=2, default=str))
        elif format == "table":
            # Simple table output
            if result.get("data"):
                for row in result["data"]:
                    click.echo(row)
        else:
            # Text format with explanation
            if result.get("explanation"):
                click.echo(result["explanation"])
            if result.get("cypher"):
                click.echo(f"\nCypher query: {result['cypher']}")
            if result.get("data"):
                click.echo(f"\nResults: {len(result['data'])} rows")
                for row in result["data"][:10]:
                    click.echo(f"  {row}")
                if len(result["data"]) > 10:
                    click.echo(f"  ... and {len(result['data']) - 10} more")

    except ImportError as e:
        click.echo(f"Error: Analyst module not available: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error executing query: {e}", err=True)
        if ctx.obj.get("verbose"):
            import traceback
            traceback.print_exc()
        sys.exit(1)


@analyst.command()
@click.option(
    "--neo4j-uri",
    default="bolt://localhost:7687",
    help="Neo4j connection URI",
    envvar="NEO4J_URI",
)
@click.option(
    "--neo4j-user",
    default="neo4j",
    help="Neo4j username",
    envvar="NEO4J_USER",
)
@click.option(
    "--neo4j-password",
    required=True,
    help="Neo4j password",
    envvar="NEO4J_PASSWORD",
)
def stats(neo4j_uri: str, neo4j_user: str, neo4j_password: str) -> None:
    """Show graph database statistics.

    Displays node and relationship counts for the infrastructure graph.

    Example:
        cloudstrate analyst stats --neo4j-password secret
    """
    try:
        from neo4j import GraphDatabase

        driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))

        with driver.session() as session:
            # Node counts by label
            result = session.run("""
                CALL db.labels() YIELD label
                CALL apoc.cypher.run('MATCH (n:`' + label + '`) RETURN count(n) as count', {})
                YIELD value
                RETURN label, value.count as count
                ORDER BY count DESC
            """)

            click.echo("\nNode Counts by Label:")
            click.echo("-" * 40)
            for record in result:
                click.echo(f"  {record['label']}: {record['count']}")

            # Relationship counts
            result = session.run("""
                CALL db.relationshipTypes() YIELD relationshipType
                CALL apoc.cypher.run('MATCH ()-[r:`' + relationshipType + '`]->() RETURN count(r) as count', {})
                YIELD value
                RETURN relationshipType, value.count as count
                ORDER BY count DESC
            """)

            click.echo("\nRelationship Counts:")
            click.echo("-" * 40)
            for record in result:
                click.echo(f"  {record['relationshipType']}: {record['count']}")

        driver.close()

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
