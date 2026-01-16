"""
Neo4j database setup and validation.

Handles connection testing, schema creation, and index management.
"""

import subprocess
import sys
from dataclasses import dataclass
from typing import Optional


@dataclass
class Neo4jStatus:
    """Status of Neo4j setup."""
    connected: bool
    version: Optional[str] = None
    database: Optional[str] = None
    node_count: int = 0
    indexes_created: int = 0
    constraints_created: int = 0
    error: Optional[str] = None


class Neo4jSetup:
    """Neo4j database setup and validation."""

    # Indexes for Cloudstrate schema
    INDEXES = [
        # AWS Organization
        ("AWSAccount", "id"),
        ("AWSAccount", "name"),
        ("AWSOrganizationalUnit", "id"),
        ("AWSOrganization", "id"),

        # Cloudstrate Model
        ("SecurityZone", "id"),
        ("Tenant", "id"),
        ("Subtenant", "id"),
        ("NetworkDomain", "id"),

        # Network
        ("VPC", "id"),
        ("Subnet", "id"),
        ("TransitGateway", "id"),
        ("SecurityGroup", "id"),

        # IAM
        ("IAMRole", "arn"),
        ("IAMPolicy", "arn"),
        ("IAMUser", "arn"),

        # GitHub
        ("GitHubRepository", "full_name"),
        ("GitHubWorkflow", "id"),
    ]

    # Constraints for uniqueness
    CONSTRAINTS = [
        ("AWSAccount", "id"),
        ("SecurityZone", "id"),
        ("Tenant", "id"),
        ("Subtenant", "id"),
    ]

    def __init__(
        self,
        uri: str = "bolt://localhost:7687",
        user: str = "neo4j",
        password: Optional[str] = None,
        database: str = "neo4j",
    ):
        """Initialize Neo4j setup.

        Args:
            uri: Neo4j connection URI
            user: Neo4j username
            password: Neo4j password
            database: Database name
        """
        self.uri = uri
        self.user = user
        self.password = password
        self.database = database
        self._driver = None

    def check_neo4j_installed(self) -> tuple[bool, str]:
        """Check if Neo4j is installed locally.

        Returns:
            Tuple of (installed, version_or_error)
        """
        try:
            result = subprocess.run(
                ["neo4j", "--version"],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                return True, result.stdout.strip()
            return False, "Neo4j command failed"
        except FileNotFoundError:
            return False, "Neo4j not found in PATH"

    def check_connection(self) -> Neo4jStatus:
        """Check Neo4j connection and return status.

        Returns:
            Neo4jStatus with connection details
        """
        if not self.password:
            return Neo4jStatus(
                connected=False,
                error="Neo4j password not provided"
            )

        try:
            from neo4j import GraphDatabase
            from neo4j.exceptions import ServiceUnavailable, AuthError

            driver = GraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password),
            )

            with driver.session(database=self.database) as session:
                # Get version
                result = session.run("CALL dbms.components() YIELD name, versions RETURN name, versions[0] as version")
                record = result.single()
                version = record["version"] if record else "unknown"

                # Get node count
                result = session.run("MATCH (n) RETURN count(n) as count")
                node_count = result.single()["count"]

            driver.close()

            return Neo4jStatus(
                connected=True,
                version=version,
                database=self.database,
                node_count=node_count,
            )

        except AuthError as e:
            return Neo4jStatus(
                connected=False,
                error=f"Authentication failed: {e}"
            )
        except ServiceUnavailable as e:
            return Neo4jStatus(
                connected=False,
                error=f"Neo4j not available at {self.uri}: {e}"
            )
        except Exception as e:
            return Neo4jStatus(
                connected=False,
                error=str(e)
            )

    def create_indexes(self, verbose: bool = False) -> Neo4jStatus:
        """Create indexes for Cloudstrate schema.

        Args:
            verbose: Print progress messages

        Returns:
            Neo4jStatus with index creation results
        """
        if not self.password:
            return Neo4jStatus(
                connected=False,
                error="Neo4j password not provided"
            )

        try:
            from neo4j import GraphDatabase

            driver = GraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password),
            )

            indexes_created = 0
            constraints_created = 0

            with driver.session(database=self.database) as session:
                # Create indexes
                for label, property in self.INDEXES:
                    try:
                        index_name = f"idx_{label.lower()}_{property}"
                        session.run(f"""
                            CREATE INDEX {index_name} IF NOT EXISTS
                            FOR (n:{label})
                            ON (n.{property})
                        """)
                        indexes_created += 1
                        if verbose:
                            print(f"  Created index: {index_name}")
                    except Exception as e:
                        if verbose:
                            print(f"  Index {label}.{property} skipped: {e}")

                # Create constraints
                for label, property in self.CONSTRAINTS:
                    try:
                        constraint_name = f"unique_{label.lower()}_{property}"
                        session.run(f"""
                            CREATE CONSTRAINT {constraint_name} IF NOT EXISTS
                            FOR (n:{label})
                            REQUIRE n.{property} IS UNIQUE
                        """)
                        constraints_created += 1
                        if verbose:
                            print(f"  Created constraint: {constraint_name}")
                    except Exception as e:
                        if verbose:
                            print(f"  Constraint {label}.{property} skipped: {e}")

            driver.close()

            return Neo4jStatus(
                connected=True,
                database=self.database,
                indexes_created=indexes_created,
                constraints_created=constraints_created,
            )

        except Exception as e:
            return Neo4jStatus(
                connected=False,
                error=str(e)
            )

    def clear_database(self, confirm: bool = False) -> bool:
        """Clear all data from the database.

        Args:
            confirm: Must be True to actually clear

        Returns:
            True if cleared successfully
        """
        if not confirm:
            return False

        if not self.password:
            return False

        try:
            from neo4j import GraphDatabase

            driver = GraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password),
            )

            with driver.session(database=self.database) as session:
                session.run("MATCH (n) DETACH DELETE n")

            driver.close()
            return True

        except Exception:
            return False

    def get_schema_info(self) -> dict:
        """Get current schema information.

        Returns:
            Dictionary with labels, relationships, indexes, constraints
        """
        if not self.password:
            return {"error": "Password not provided"}

        try:
            from neo4j import GraphDatabase

            driver = GraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password),
            )

            info = {
                "labels": [],
                "relationships": [],
                "indexes": [],
                "constraints": [],
            }

            with driver.session(database=self.database) as session:
                # Get labels
                result = session.run("CALL db.labels()")
                info["labels"] = [r["label"] for r in result]

                # Get relationship types
                result = session.run("CALL db.relationshipTypes()")
                info["relationships"] = [r["relationshipType"] for r in result]

                # Get indexes
                result = session.run("SHOW INDEXES")
                info["indexes"] = [
                    {"name": r["name"], "type": r["type"], "labelsOrTypes": r.get("labelsOrTypes", [])}
                    for r in result
                ]

                # Get constraints
                result = session.run("SHOW CONSTRAINTS")
                info["constraints"] = [
                    {"name": r["name"], "type": r["type"]}
                    for r in result
                ]

            driver.close()
            return info

        except Exception as e:
            return {"error": str(e)}
