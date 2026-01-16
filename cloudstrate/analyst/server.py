"""
Analyst server wrapper for Cloudstrate CLI.

Wraps the existing neo4j_explorer.py for use with the CLI.
"""

import sys
from pathlib import Path
from typing import Any, Optional


class AnalystServer:
    """Wrapper for Analyst web interface.

    Launches web UI for natural language queries against the infrastructure graph.
    """

    def __init__(
        self,
        neo4j_uri: str = "bolt://localhost:7687",
        neo4j_user: str = "neo4j",
        neo4j_password: Optional[str] = None,
        config: Optional[Any] = None,
    ):
        """Initialize Analyst server.

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

    def run(self, host: str = "127.0.0.1", port: int = 5001) -> None:
        """Start the Analyst server.

        Args:
            host: Host to bind server to
            port: Port for server
        """
        # Try to import existing explorer
        foundation_path = Path(__file__).parent.parent.parent / "foundation"
        sys.path.insert(0, str(foundation_path))

        try:
            from neo4j_explorer import create_app

            app = create_app(
                neo4j_uri=self.neo4j_uri,
                neo4j_user=self.neo4j_user,
                neo4j_password=self.neo4j_password,
                config=self.config,
            )

            app.run(host=host, port=port, debug=False)

        except ImportError:
            # Fallback to basic server
            self._run_basic_server(host, port)

    def _run_basic_server(self, host: str, port: int) -> None:
        """Basic Flask server implementation.

        Fallback if the existing explorer is not available.
        """
        try:
            from flask import Flask, jsonify, request, render_template_string
            from neo4j import GraphDatabase
        except ImportError as e:
            raise ImportError(
                f"Required packages not available: {e}. "
                "Install with: pip install flask neo4j"
            )

        app = Flask(__name__)

        # Connect to Neo4j
        driver = GraphDatabase.driver(
            self.neo4j_uri,
            auth=(self.neo4j_user, self.neo4j_password),
        )

        TEMPLATE = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Cloudstrate Analyst</title>
            <style>
                body { font-family: system-ui, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; }
                h1 { color: #333; }
                .query-box { width: 100%; padding: 10px; font-size: 16px; margin: 10px 0; }
                button { padding: 10px 20px; background: #007bff; color: white; border: none; cursor: pointer; }
                button:hover { background: #0056b3; }
                .results { margin-top: 20px; }
                pre { background: #f0f0f0; padding: 15px; overflow-x: auto; }
                .error { color: red; }
            </style>
        </head>
        <body>
            <h1>Cloudstrate Analyst</h1>
            <p>Query your infrastructure using natural language or Cypher.</p>

            <input type="text" class="query-box" id="query"
                   placeholder="Enter your question or Cypher query...">
            <button onclick="runQuery()">Run Query</button>

            <div class="results" id="results"></div>

            <h2>Example Queries</h2>
            <ul>
                <li>MATCH (a:AWSAccount) RETURN a.name, a.id LIMIT 10</li>
                <li>MATCH (v:VPC) RETURN v.id, v.cidr LIMIT 10</li>
                <li>MATCH (r:IAMRole)-[:TRUSTS]->(a:AWSAccount) RETURN r.name, a.name LIMIT 10</li>
            </ul>

            <script>
                async function runQuery() {
                    const query = document.getElementById('query').value;
                    const resultsDiv = document.getElementById('results');

                    try {
                        const response = await fetch('/api/query', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({query: query})
                        });
                        const data = await response.json();

                        if (data.error) {
                            resultsDiv.innerHTML = '<p class="error">' + data.error + '</p>';
                        } else {
                            resultsDiv.innerHTML = '<pre>' + JSON.stringify(data.results, null, 2) + '</pre>';
                        }
                    } catch (err) {
                        resultsDiv.innerHTML = '<p class="error">Error: ' + err.message + '</p>';
                    }
                }
            </script>
        </body>
        </html>
        """

        @app.route("/")
        def index():
            return render_template_string(TEMPLATE)

        @app.route("/api/query", methods=["POST"])
        def run_query():
            data = request.get_json()
            query = data.get("query", "")

            # If it looks like Cypher, run it directly
            if query.strip().upper().startswith(("MATCH", "RETURN", "CREATE", "CALL")):
                try:
                    with driver.session() as session:
                        result = session.run(query)
                        records = [dict(record) for record in result]
                        return jsonify({"results": records})
                except Exception as e:
                    return jsonify({"error": str(e)})

            # Otherwise, treat as natural language (would need LLM integration)
            return jsonify({
                "error": "Natural language queries require LLM integration. "
                         "Please use Cypher queries directly."
            })

        @app.route("/api/stats")
        def stats():
            try:
                with driver.session() as session:
                    # Get node counts
                    result = session.run("""
                        CALL db.labels() YIELD label
                        RETURN label,
                               size([(n) WHERE label IN labels(n) | n]) as count
                        ORDER BY count DESC
                    """)
                    node_counts = {r["label"]: r["count"] for r in result}

                    return jsonify({"node_counts": node_counts})
            except Exception as e:
                return jsonify({"error": str(e)})

        @app.teardown_appcontext
        def close_driver(exception):
            driver.close()

        app.run(host=host, port=port, debug=False)
