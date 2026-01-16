"""
Analyst query module for Cloudstrate CLI.

Provides natural language query interface for the CLI.
"""

import sys
from pathlib import Path
from typing import Any, Optional


class AnalystQuery:
    """Natural language query interface for infrastructure analysis.

    Translates natural language to Cypher and executes against Neo4j.
    """

    def __init__(
        self,
        neo4j_uri: str = "bolt://localhost:7687",
        neo4j_user: str = "neo4j",
        neo4j_password: Optional[str] = None,
        config: Optional[Any] = None,
    ):
        """Initialize Analyst query interface.

        Args:
            neo4j_uri: Neo4j connection URI
            neo4j_user: Neo4j username
            neo4j_password: Neo4j password
            config: Optional CloudstrateConfig instance
        """
        self.neo4j_uri = neo4j_uri
        self.neo4j_user = neo4j_user
        self.neo4j_password = neo4j_password
        self.config = config
        self._driver = None

    def _get_driver(self):
        """Lazy-load Neo4j driver."""
        if self._driver is None:
            from neo4j import GraphDatabase

            self._driver = GraphDatabase.driver(
                self.neo4j_uri,
                auth=(self.neo4j_user, self.neo4j_password),
            )
        return self._driver

    def execute(self, question: str) -> dict[str, Any]:
        """Execute a natural language query.

        Args:
            question: Natural language question or Cypher query

        Returns:
            Dictionary with:
            - cypher: The Cypher query that was executed
            - data: Query results
            - explanation: Optional explanation of results
        """
        # Check if it's a Cypher query
        if self._is_cypher(question):
            return self._execute_cypher(question)

        # Otherwise, translate to Cypher using LLM
        return self._execute_natural_language(question)

    def _is_cypher(self, text: str) -> bool:
        """Check if text looks like a Cypher query."""
        cypher_keywords = ("MATCH", "RETURN", "CREATE", "MERGE", "DELETE", "CALL", "WITH")
        return text.strip().upper().startswith(cypher_keywords)

    def _execute_cypher(self, cypher: str) -> dict[str, Any]:
        """Execute a Cypher query directly."""
        driver = self._get_driver()

        try:
            with driver.session() as session:
                result = session.run(cypher)
                records = [dict(record) for record in result]

                return {
                    "cypher": cypher,
                    "data": records,
                    "explanation": f"Executed Cypher query, returned {len(records)} results.",
                }
        except Exception as e:
            return {
                "cypher": cypher,
                "data": [],
                "error": str(e),
            }

    def _execute_natural_language(self, question: str) -> dict[str, Any]:
        """Translate natural language to Cypher and execute.

        Uses LLM to translate the question to Cypher.
        """
        # Try to use existing LLM integration
        foundation_path = Path(__file__).parent.parent.parent / "foundation"
        sys.path.insert(0, str(foundation_path))

        try:
            # Try to get LLM provider
            if self.config and self.config.llm.provider != "disabled":
                cypher = self._translate_with_llm(question)
                if cypher:
                    result = self._execute_cypher(cypher)
                    result["original_question"] = question
                    return result
        except ImportError:
            pass

        # Fallback: try to match common patterns
        cypher = self._translate_basic(question)
        if cypher:
            result = self._execute_cypher(cypher)
            result["original_question"] = question
            return result

        return {
            "cypher": None,
            "data": [],
            "error": "Could not translate question to Cypher. "
                     "LLM integration required for natural language queries.",
            "original_question": question,
        }

    def _translate_with_llm(self, question: str) -> Optional[str]:
        """Translate question to Cypher using LLM."""
        # This would integrate with the LLM module
        # For now, return None to fall back to basic translation
        return None

    def _translate_basic(self, question: str) -> Optional[str]:
        """Basic pattern matching for common questions."""
        question_lower = question.lower()

        # Common query patterns
        patterns = [
            # Accounts
            (["accounts", "aws accounts", "all accounts"],
             "MATCH (a:AWSAccount) RETURN a.name as name, a.id as id LIMIT 50"),

            # Production accounts
            (["production", "prod accounts"],
             "MATCH (a:AWSAccount) WHERE a.name CONTAINS 'prod' OR a.name CONTAINS 'production' RETURN a.name as name, a.id as id"),

            # VPCs
            (["vpcs", "virtual private clouds", "networks"],
             "MATCH (v:VPC) RETURN v.id as id, v.cidr as cidr LIMIT 50"),

            # IAM roles
            (["iam roles", "roles"],
             "MATCH (r:IAMRole) RETURN r.name as name, r.arn as arn LIMIT 50"),

            # Cross-account roles
            (["cross-account", "cross account", "trust relationships"],
             "MATCH (r:IAMRole)-[:TRUSTS]->(a:AWSAccount) RETURN r.name as role, a.name as trusted_account LIMIT 50"),

            # Security groups
            (["security groups", "sgs"],
             "MATCH (sg:SecurityGroup) RETURN sg.name as name, sg.id as id LIMIT 50"),

            # Subnets
            (["subnets"],
             "MATCH (s:Subnet) RETURN s.id as id, s.cidr as cidr, s.availability_zone as az LIMIT 50"),
        ]

        for keywords, cypher in patterns:
            if any(kw in question_lower for kw in keywords):
                return cypher

        return None

    def close(self) -> None:
        """Close Neo4j driver connection."""
        if self._driver:
            self._driver.close()
            self._driver = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
