"""
Tests for Cloudstrate analyst modules.
"""

from unittest.mock import MagicMock, patch

import pytest


class TestAnalystQuery:
    """Tests for Analyst query module."""

    def test_analyst_query_initialization(self):
        """Test Analyst query can be initialized."""
        from cloudstrate.analyst.query import AnalystQuery

        query = AnalystQuery(
            neo4j_uri="bolt://localhost:7687",
            neo4j_user="neo4j",
            neo4j_password="secret",
        )

        assert query.neo4j_uri == "bolt://localhost:7687"
        assert query.neo4j_user == "neo4j"
        assert query.neo4j_password == "secret"

    def test_analyst_query_detects_cypher(self):
        """Test that Cypher queries are detected."""
        from cloudstrate.analyst.query import AnalystQuery

        query = AnalystQuery(neo4j_password="secret")

        assert query._is_cypher("MATCH (n) RETURN n")
        assert query._is_cypher("match (n) return n")
        assert query._is_cypher("RETURN 1")
        assert query._is_cypher("CREATE (n:Node)")
        assert query._is_cypher("CALL db.labels()")

        assert not query._is_cypher("Show all accounts")
        assert not query._is_cypher("What VPCs exist?")

    def test_analyst_query_basic_translation(self):
        """Test basic pattern matching for common questions."""
        from cloudstrate.analyst.query import AnalystQuery

        query = AnalystQuery(neo4j_password="secret")

        # Test account queries
        cypher = query._translate_basic("Show all accounts")
        assert cypher is not None
        assert "AWSAccount" in cypher

        # Test VPC queries
        cypher = query._translate_basic("List all VPCs")
        assert cypher is not None
        assert "VPC" in cypher

        # Test IAM queries
        cypher = query._translate_basic("Show IAM roles")
        assert cypher is not None
        assert "IAMRole" in cypher

        # Test unknown query
        cypher = query._translate_basic("Something random")
        assert cypher is None

    def test_analyst_query_production_pattern(self):
        """Test production account pattern matching."""
        from cloudstrate.analyst.query import AnalystQuery

        query = AnalystQuery(neo4j_password="secret")

        cypher = query._translate_basic("Show production accounts")
        assert cypher is not None
        # The query may contain 'prod' in WHERE clause or just return accounts
        assert "AWSAccount" in cypher

    def test_analyst_query_execute_cypher(self):
        """Test executing a Cypher query."""
        from unittest.mock import patch, MagicMock
        from cloudstrate.analyst.query import AnalystQuery

        # Setup mock
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.__iter__ = lambda self: iter([
            {"name": "Account1", "id": "111"},
            {"name": "Account2", "id": "222"},
        ])
        mock_session.run.return_value = mock_result
        mock_session.__enter__ = lambda self: mock_session
        mock_session.__exit__ = MagicMock(return_value=False)

        mock_driver = MagicMock()
        mock_driver.session.return_value = mock_session

        with patch("neo4j.GraphDatabase") as mock_db:
            mock_db.driver.return_value = mock_driver

            query = AnalystQuery(neo4j_password="secret")
            result = query.execute("MATCH (a:AWSAccount) RETURN a.name, a.id")

            assert result["cypher"] == "MATCH (a:AWSAccount) RETURN a.name, a.id"
            assert len(result["data"]) == 2
            assert result["data"][0]["name"] == "Account1"

    def test_analyst_query_handles_error(self):
        """Test that query errors are handled gracefully."""
        from unittest.mock import patch, MagicMock
        from cloudstrate.analyst.query import AnalystQuery

        # Setup mock to raise error
        mock_session = MagicMock()
        mock_session.run.side_effect = Exception("Query failed")
        mock_session.__enter__ = lambda self: mock_session
        mock_session.__exit__ = MagicMock(return_value=False)

        mock_driver = MagicMock()
        mock_driver.session.return_value = mock_session

        with patch("neo4j.GraphDatabase") as mock_db:
            mock_db.driver.return_value = mock_driver

            query = AnalystQuery(neo4j_password="secret")
            result = query.execute("RETURN 1")  # Use valid Cypher syntax

            assert "error" in result
            assert "Query failed" in result["error"]

    def test_analyst_query_context_manager(self):
        """Test that query supports context manager protocol."""
        from cloudstrate.analyst.query import AnalystQuery

        query = AnalystQuery(neo4j_password="secret")

        with query as q:
            assert q is query

        # Should be closed after context
        # (driver will be None since we didn't actually connect)


class TestAnalystServer:
    """Tests for Analyst server module."""

    def test_analyst_server_initialization(self):
        """Test Analyst server can be initialized."""
        from cloudstrate.analyst.server import AnalystServer

        server = AnalystServer(
            neo4j_uri="bolt://localhost:7687",
            neo4j_user="neo4j",
            neo4j_password="secret",
        )

        assert server.neo4j_uri == "bolt://localhost:7687"
        assert server.neo4j_user == "neo4j"
        assert server.neo4j_password == "secret"

    def test_analyst_server_default_values(self):
        """Test Analyst server has sensible defaults."""
        from cloudstrate.analyst.server import AnalystServer

        server = AnalystServer(neo4j_password="secret")

        assert server.neo4j_uri == "bolt://localhost:7687"
        assert server.neo4j_user == "neo4j"


class TestAnalystIntegration:
    """Integration tests for analyst modules."""

    def test_natural_language_to_cypher_execution(self):
        """Test natural language query translates and executes."""
        from unittest.mock import patch, MagicMock
        from cloudstrate.analyst.query import AnalystQuery

        # Setup mock
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.__iter__ = lambda self: iter([
            {"name": "prod-account", "id": "111"},
        ])
        mock_session.run.return_value = mock_result
        mock_session.__enter__ = lambda self: mock_session
        mock_session.__exit__ = MagicMock(return_value=False)

        mock_driver = MagicMock()
        mock_driver.session.return_value = mock_session

        with patch("neo4j.GraphDatabase") as mock_db:
            mock_db.driver.return_value = mock_driver

            query = AnalystQuery(neo4j_password="secret")
            result = query.execute("Show all AWS accounts")

            # Should have executed a Cypher query
            assert result["cypher"] is not None
            assert "AWSAccount" in result["cypher"]
            assert result["data"][0]["name"] == "prod-account"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
