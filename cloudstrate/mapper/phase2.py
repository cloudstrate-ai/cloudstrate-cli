"""
Phase 2 Mapper server wrapper for Cloudstrate CLI.

Wraps the existing proposal_generator_phased.py for use with the CLI.
"""

import sys
from pathlib import Path
from typing import Any, Optional

import yaml


class Phase2Server:
    """Wrapper for Phase 2 interactive review server.

    Launches web UI for reviewing and refining the Cloudstrate model
    with AI-powered proposal generation.
    """

    def __init__(
        self,
        state_file: str | Path,
        config: Optional[Any] = None,
    ):
        """Initialize Phase 2 server.

        Args:
            state_file: Path to mapping state YAML file
            config: Optional CloudstrateConfig instance
        """
        self.state_file = Path(state_file)
        self.config = config

        if not self.state_file.exists():
            raise FileNotFoundError(f"State file not found: {state_file}")

        # Load initial state
        with open(self.state_file) as f:
            self.state = yaml.safe_load(f)

    def run(self, host: str = "127.0.0.1", port: int = 5000) -> None:
        """Start the Phase 2 review server.

        Args:
            host: Host to bind server to
            port: Port for server
        """
        # Try to import existing server
        foundation_path = Path(__file__).parent.parent.parent / "foundation"
        sys.path.insert(0, str(foundation_path))

        try:
            from phased_review_server import create_app

            app = create_app(
                state_file=str(self.state_file),
                config=self.config,
            )

            app.run(host=host, port=port, debug=False)

        except ImportError:
            # Fallback to basic server
            self._run_basic_server(host, port)

    def _run_basic_server(self, host: str, port: int) -> None:
        """Basic Flask server implementation.

        Fallback if the existing server is not available.
        """
        try:
            from flask import Flask, jsonify, request, render_template_string
        except ImportError:
            raise ImportError("Flask is required. Install with: pip install flask")

        app = Flask(__name__)

        TEMPLATE = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Cloudstrate Phase 2 Review</title>
            <style>
                body { font-family: system-ui, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; }
                h1 { color: #333; }
                .section { margin: 20px 0; padding: 20px; border: 1px solid #ddd; border-radius: 8px; }
                .item { background: #f5f5f5; padding: 10px; margin: 10px 0; border-radius: 4px; }
                pre { background: #f0f0f0; padding: 10px; overflow-x: auto; }
            </style>
        </head>
        <body>
            <h1>Cloudstrate Phase 2 Review</h1>
            <p>Review and refine the Cloudstrate model.</p>

            <div class="section">
                <h2>Security Zones ({{ security_zones|length }})</h2>
                {% for zone in security_zones %}
                <div class="item">
                    <strong>{{ zone.id }}</strong>: {{ zone.name }}
                    <br><small>{{ zone.description }}</small>
                </div>
                {% endfor %}
            </div>

            <div class="section">
                <h2>Subtenants ({{ subtenants|length }})</h2>
                {% for st in subtenants %}
                <div class="item">
                    <strong>{{ st.id }}</strong>: {{ st.name }}
                    <br><small>Accounts: {{ st.aws_accounts|join(', ') }}</small>
                </div>
                {% endfor %}
            </div>

            <div class="section">
                <h2>Proposals ({{ proposals|length }})</h2>
                {% for proposal in proposals %}
                <div class="item">
                    <strong>{{ proposal.type }}</strong>: {{ proposal.description }}
                    <br><small>Status: {{ proposal.status }}</small>
                </div>
                {% endfor %}
            </div>

            <div class="section">
                <h2>Raw State</h2>
                <pre>{{ state_yaml }}</pre>
            </div>
        </body>
        </html>
        """

        @app.route("/")
        def index():
            return render_template_string(
                TEMPLATE,
                security_zones=self.state.get("security_zones", []),
                subtenants=self.state.get("subtenants", []),
                tenants=self.state.get("tenants", []),
                proposals=self.state.get("proposals", []),
                state_yaml=yaml.dump(self.state, default_flow_style=False),
            )

        @app.route("/api/state")
        def get_state():
            return jsonify(self.state)

        @app.route("/api/proposals", methods=["GET"])
        def get_proposals():
            return jsonify(self.state.get("proposals", []))

        @app.route("/api/proposals/<proposal_id>/accept", methods=["POST"])
        def accept_proposal(proposal_id):
            for proposal in self.state.get("proposals", []):
                if proposal.get("id") == proposal_id:
                    proposal["status"] = "accepted"
                    self._save_state()
                    return jsonify({"status": "ok"})
            return jsonify({"error": "Proposal not found"}), 404

        @app.route("/api/proposals/<proposal_id>/reject", methods=["POST"])
        def reject_proposal(proposal_id):
            for proposal in self.state.get("proposals", []):
                if proposal.get("id") == proposal_id:
                    proposal["status"] = "rejected"
                    self._save_state()
                    return jsonify({"status": "ok"})
            return jsonify({"error": "Proposal not found"}), 404

        app.run(host=host, port=port, debug=False)

    def _save_state(self) -> None:
        """Save current state to file."""
        with open(self.state_file, "w") as f:
            yaml.dump(self.state, f, default_flow_style=False)
