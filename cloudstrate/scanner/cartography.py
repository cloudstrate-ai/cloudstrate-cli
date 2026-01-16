"""
Cartography Scanner wrapper for Cloudstrate CLI.

Wraps the existing cartography integration for use with the CLI.
"""

import sys
from pathlib import Path
from typing import Any, Optional


class CartographyScanner:
    """Wrapper for Cartography-based scanning.

    Provides a unified interface for running Cartography scans
    and importing results into Neo4j.
    """

    def __init__(
        self,
        config_path: str,
        neo4j_uri: str = "bolt://localhost:7687",
        neo4j_user: str = "neo4j",
        neo4j_password: Optional[str] = None,
    ):
        """Initialize Cartography scanner.

        Args:
            config_path: Path to Cartography config.yaml
            neo4j_uri: Neo4j connection URI
            neo4j_user: Neo4j username
            neo4j_password: Neo4j password
        """
        self.config_path = Path(config_path)
        self.neo4j_uri = neo4j_uri
        self.neo4j_user = neo4j_user
        self.neo4j_password = neo4j_password

        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

    def run(self) -> dict[str, Any]:
        """Run Cartography scan.

        Executes Cartography to scan AWS resources and import into Neo4j.

        Returns:
            Dictionary with scan results and statistics.
        """
        # Add cartography module to path
        cartography_path = Path(__file__).parent.parent.parent / "foundation" / "cartography"
        sys.path.insert(0, str(cartography_path))

        try:
            from scan import CartographyRunner

            runner = CartographyRunner(
                config_path=str(self.config_path),
                neo4j_uri=self.neo4j_uri,
                neo4j_user=self.neo4j_user,
                neo4j_password=self.neo4j_password,
            )

            return runner.run()

        except ImportError:
            # Fallback: run cartography directly via subprocess
            return self._run_subprocess()

    def _run_subprocess(self) -> dict[str, Any]:
        """Run Cartography via subprocess.

        Fallback method if the Python module is not available.
        """
        import subprocess
        import yaml

        # Load config
        with open(self.config_path) as f:
            config = yaml.safe_load(f)

        # Build cartography command
        cmd = [
            "cartography",
            "--neo4j-uri", self.neo4j_uri,
            "--neo4j-user", self.neo4j_user,
        ]

        if self.neo4j_password:
            cmd.extend(["--neo4j-password-env-var", "NEO4J_PASSWORD"])

        # Add AWS profile if specified
        aws_profile = config.get("aws", {}).get("profile")
        if aws_profile:
            import os
            os.environ["AWS_PROFILE"] = aws_profile

        # Run cartography
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env={
                **dict(subprocess.os.environ),
                "NEO4J_PASSWORD": self.neo4j_password or "",
            },
        )

        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
        }

    def enrich(self) -> dict[str, Any]:
        """Run Cloudstrate enrichment on Cartography data.

        Adds Cloudstrate-specific labels and relationships to the Neo4j graph.

        Returns:
            Dictionary with enrichment statistics.
        """
        cartography_path = Path(__file__).parent.parent.parent / "foundation" / "cartography"
        sys.path.insert(0, str(cartography_path))

        try:
            from enrich import CloudstrateEnricher

            enricher = CloudstrateEnricher(
                neo4j_uri=self.neo4j_uri,
                neo4j_user=self.neo4j_user,
                neo4j_password=self.neo4j_password,
            )

            return enricher.enrich()

        except ImportError as e:
            raise ImportError(
                f"Could not import CloudstrateEnricher. "
                f"Ensure cartography module is available: {e}"
            )
