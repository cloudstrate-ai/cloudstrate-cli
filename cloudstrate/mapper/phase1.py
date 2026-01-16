"""
Phase 1 Mapper wrapper for Cloudstrate CLI.

Wraps the existing mapper.py for use with the CLI.
"""

import json
import sys
import yaml
from pathlib import Path
from typing import Any, Optional


class Phase1Mapper:
    """Wrapper for Phase 1 automatic mapping.

    Analyzes scan results and creates initial Cloudstrate model with
    security zones, tenants, and subtenants.
    """

    def __init__(
        self,
        scan_file: str | Path,
        decisions_file: Optional[str | Path] = None,
    ):
        """Initialize Phase 1 mapper.

        Args:
            scan_file: Path to AWS scan JSON file
            decisions_file: Optional path to pre-configured decisions YAML
        """
        self.scan_file = Path(scan_file)
        self.decisions_file = Path(decisions_file) if decisions_file else None
        self._state: Optional[dict] = None

        if not self.scan_file.exists():
            raise FileNotFoundError(f"Scan file not found: {scan_file}")

        if self.decisions_file and not self.decisions_file.exists():
            raise FileNotFoundError(f"Decisions file not found: {decisions_file}")

    def run(self) -> dict[str, Any]:
        """Run Phase 1 mapping.

        Returns:
            Dictionary containing the mapping state with:
            - security_zones: List of security zones
            - tenants: List of tenants
            - subtenants: List of subtenants
            - network_domains: List of network domains
            - proposals: Generated proposals for Phase 2
        """
        # Load scan data
        with open(self.scan_file) as f:
            scan_data = json.load(f)

        # Load decisions if provided
        decisions = {}
        if self.decisions_file:
            with open(self.decisions_file) as f:
                decisions = yaml.safe_load(f) or {}

        # Try to import existing mapper
        foundation_path = Path(__file__).parent.parent.parent / "foundation"
        sys.path.insert(0, str(foundation_path))

        try:
            from mapper import CloudstrateMapper

            mapper = CloudstrateMapper(
                scan_data=scan_data,
                decisions=decisions,
            )

            self._state = mapper.map_phase1()
            return self._state

        except ImportError:
            # Fallback to basic mapping
            return self._map_basic(scan_data, decisions)

    def _map_basic(
        self, scan_data: dict, decisions: dict
    ) -> dict[str, Any]:
        """Basic Phase 1 mapping implementation.

        Fallback if the existing mapper is not available.
        """
        state = {
            "security_zones": [],
            "tenants": [],
            "subtenants": [],
            "network_domains": [],
            "proposals": [],
        }

        # Create default security zones from OUs
        for ou in scan_data.get("organizational_units", []):
            zone = {
                "id": f"sz-{ou['id'].replace('ou-', '')}",
                "name": ou.get("name", ou["id"]),
                "source_ou_id": ou["id"],
                "description": f"Security zone from OU: {ou.get('name', ou['id'])}",
            }
            state["security_zones"].append(zone)

        # Create subtenants from accounts
        for account in scan_data.get("accounts", []):
            subtenant = {
                "id": f"st-{account['id']}",
                "name": account.get("name", account["id"]),
                "aws_accounts": [account["id"]],
                "description": f"Subtenant for account: {account.get('name', account['id'])}",
            }
            state["subtenants"].append(subtenant)

        # Generate basic proposals
        state["proposals"] = self._generate_proposals(state, scan_data)

        self._state = state
        return state

    def _generate_proposals(
        self, state: dict, scan_data: dict
    ) -> list[dict]:
        """Generate proposals for Phase 2 review."""
        proposals = []

        # Propose tenant groupings
        if len(state["subtenants"]) > 1:
            proposals.append({
                "type": "tenant_grouping",
                "description": "Group subtenants into logical tenants",
                "subtenants": [st["id"] for st in state["subtenants"]],
                "status": "pending",
            })

        # Propose network domains from VPCs
        vpcs = scan_data.get("vpcs", [])
        if vpcs:
            proposals.append({
                "type": "network_domain",
                "description": f"Create network domains from {len(vpcs)} VPCs",
                "vpcs": [vpc["id"] for vpc in vpcs],
                "status": "pending",
            })

        return proposals

    def save_state(self, output_path: str | Path) -> None:
        """Save mapping state to YAML file.

        Args:
            output_path: Path to save state file
        """
        if self._state is None:
            raise RuntimeError("No state to save. Run map() first.")

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w") as f:
            f.write("# Cloudstrate Mapping State\n")
            f.write("# Generated by Phase 1 Mapper\n\n")
            yaml.dump(self._state, f, default_flow_style=False)

    @property
    def state(self) -> Optional[dict]:
        """Get current mapping state."""
        return self._state
