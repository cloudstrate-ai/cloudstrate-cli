"""
AWS Scanner wrapper for Cloudstrate CLI.

Wraps the existing discover_aws_organization.py for use with the CLI.
"""

import json
import sys
from pathlib import Path
from typing import Any, Callable, Optional

# Add foundation to path for importing existing module
foundation_path = Path(__file__).parent.parent.parent / "foundation"
if str(foundation_path) not in sys.path:
    sys.path.insert(0, str(foundation_path))


class AWSScanner:
    """Wrapper for AWS Organization discovery.

    Provides a unified interface for the CLI to scan AWS infrastructure.
    """

    def __init__(
        self,
        profile: str,
        regions: Optional[list[str]] = None,
        include_iam: bool = True,
        include_network: bool = True,
        cross_account_role: str = "OrganizationAccountAccessRole",
        max_workers: int = 10,
    ):
        """Initialize AWS scanner.

        Args:
            profile: AWS profile name for authentication
            regions: AWS regions to scan (default: all enabled regions)
            include_iam: Include IAM roles and policies in scan
            include_network: Include VPC and network topology
            cross_account_role: Name of role to assume in member accounts
            max_workers: Maximum parallel workers for scanning
        """
        self.profile = profile
        self.regions = regions or []
        self.include_iam = include_iam
        self.include_network = include_network
        self.cross_account_role = cross_account_role
        self.max_workers = max_workers
        self._discovery = None

    def _get_discovery(self):
        """Lazy-load the discovery class."""
        if self._discovery is None:
            try:
                from discover_aws_organization import AWSOrganizationDiscovery

                self._discovery = AWSOrganizationDiscovery(
                    management_account_profile=self.profile,
                    cross_account_role_name=self.cross_account_role,
                    regions=self.regions,
                    max_workers=self.max_workers,
                )
            except ImportError as e:
                raise ImportError(
                    f"Could not import AWSOrganizationDiscovery. "
                    f"Ensure foundation module is available: {e}"
                )
        return self._discovery

    def scan(
        self,
        progress_callback: Optional[Callable[[float], None]] = None,
    ) -> dict[str, Any]:
        """Run AWS organization scan.

        Args:
            progress_callback: Optional callback for progress updates (0-100)

        Returns:
            Dictionary containing scan results with:
            - organization: Organization structure
            - accounts: List of AWS accounts
            - organizational_units: List of OUs
            - scps: Service Control Policies
            - vpcs: VPC configurations (if include_network)
            - iam_roles: IAM roles (if include_iam)
            - etc.
        """
        discovery = self._get_discovery()
        result = {}

        # Progress tracking
        total_steps = 5
        current_step = 0

        def update_progress():
            nonlocal current_step
            current_step += 1
            if progress_callback:
                progress_callback((current_step / total_steps) * 100)

        # Step 1: Discover organization structure
        org_data = discovery.discover_organization_structure()
        result["organization"] = org_data.get("organization", {})
        result["accounts"] = org_data.get("accounts", [])
        result["organizational_units"] = org_data.get("organizational_units", [])
        result["scps"] = org_data.get("scps", [])
        update_progress()

        # Step 2: Discover network topology (if enabled)
        if self.include_network:
            network_data = discovery.discover_network_topology()
            result["vpcs"] = network_data.get("vpcs", [])
            result["subnets"] = network_data.get("subnets", [])
            result["transit_gateways"] = network_data.get("transit_gateways", [])
            result["peering_connections"] = network_data.get("peering_connections", [])
        update_progress()

        # Step 3: Discover RAM shares
        ram_data = discovery.discover_ram_shares()
        result["ram_shares"] = ram_data.get("ram_shares", [])
        update_progress()

        # Step 4: Discover IAM (if enabled)
        if self.include_iam:
            iam_roles = discovery.discover_cross_account_roles()
            result["cross_account_roles"] = iam_roles.get("cross_account_roles", [])

            iam_data = discovery.discover_iam_roles()
            result["iam_roles"] = iam_data.get("iam_roles", [])
        update_progress()

        # Step 5: Add metadata
        from datetime import datetime

        result["scan_metadata"] = {
            "scan_time": datetime.utcnow().isoformat(),
            "profile": self.profile,
            "regions": self.regions,
            "include_iam": self.include_iam,
            "include_network": self.include_network,
        }
        update_progress()

        return result

    def scan_organization_only(self) -> dict[str, Any]:
        """Scan only organization structure (fast scan).

        Returns:
            Dictionary with organization, accounts, OUs, and SCPs.
        """
        discovery = self._get_discovery()
        return discovery.discover_organization_structure()

    def scan_network_only(self) -> dict[str, Any]:
        """Scan only network topology.

        Returns:
            Dictionary with VPCs, subnets, TGWs, and peering.
        """
        discovery = self._get_discovery()
        return discovery.discover_network_topology()

    def scan_iam_only(self) -> dict[str, Any]:
        """Scan only IAM configuration.

        Returns:
            Dictionary with IAM roles and cross-account roles.
        """
        discovery = self._get_discovery()
        result = {}
        result.update(discovery.discover_cross_account_roles())
        result.update(discovery.discover_iam_roles())
        return result
