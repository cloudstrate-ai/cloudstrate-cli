"""
Tests for Cloudstrate scanner modules.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestAWSScanner:
    """Tests for AWS scanner wrapper."""

    def test_aws_scanner_initialization(self):
        """Test AWS scanner can be initialized with required params."""
        from cloudstrate.scanner.aws import AWSScanner

        scanner = AWSScanner(
            profile="test-profile",
            regions=["us-east-1", "us-west-2"],
            include_iam=True,
            include_network=True,
        )

        assert scanner.profile == "test-profile"
        assert scanner.regions == ["us-east-1", "us-west-2"]
        assert scanner.include_iam is True
        assert scanner.include_network is True

    def test_aws_scanner_default_values(self):
        """Test AWS scanner has sensible defaults."""
        from cloudstrate.scanner.aws import AWSScanner

        scanner = AWSScanner(profile="test")

        assert scanner.regions == []  # Empty means all enabled regions
        assert scanner.include_iam is True
        assert scanner.include_network is True
        assert scanner.cross_account_role == "OrganizationAccountAccessRole"
        assert scanner.max_workers == 10

    @patch("cloudstrate.scanner.aws.AWSScanner._get_discovery")
    def test_aws_scanner_scan_calls_discovery_methods(self, mock_get_discovery):
        """Test that scan() calls the underlying discovery methods."""
        from cloudstrate.scanner.aws import AWSScanner

        # Setup mock
        mock_discovery = MagicMock()
        mock_discovery.discover_organization_structure.return_value = {
            "organization": {"id": "o-123"},
            "accounts": [{"id": "111"}],
            "organizational_units": [{"id": "ou-123"}],
            "scps": [],
        }
        mock_discovery.discover_network_topology.return_value = {
            "vpcs": [{"id": "vpc-123"}],
            "subnets": [],
            "transit_gateways": [],
            "peering_connections": [],
        }
        mock_discovery.discover_ram_shares.return_value = {"ram_shares": []}
        mock_discovery.discover_cross_account_roles.return_value = {
            "cross_account_roles": []
        }
        mock_discovery.discover_iam_roles.return_value = {"iam_roles": []}

        mock_get_discovery.return_value = mock_discovery

        scanner = AWSScanner(profile="test")
        result = scanner.scan()

        # Verify all discovery methods were called
        mock_discovery.discover_organization_structure.assert_called_once()
        mock_discovery.discover_network_topology.assert_called_once()
        mock_discovery.discover_ram_shares.assert_called_once()
        mock_discovery.discover_cross_account_roles.assert_called_once()
        mock_discovery.discover_iam_roles.assert_called_once()

        # Verify result structure
        assert "organization" in result
        assert "accounts" in result
        assert "vpcs" in result
        assert "scan_metadata" in result

    @patch("cloudstrate.scanner.aws.AWSScanner._get_discovery")
    def test_aws_scanner_scan_without_network(self, mock_get_discovery):
        """Test scan with include_network=False skips network discovery."""
        from cloudstrate.scanner.aws import AWSScanner

        mock_discovery = MagicMock()
        mock_discovery.discover_organization_structure.return_value = {
            "organization": {},
            "accounts": [],
            "organizational_units": [],
            "scps": [],
        }
        mock_discovery.discover_ram_shares.return_value = {"ram_shares": []}
        mock_discovery.discover_cross_account_roles.return_value = {
            "cross_account_roles": []
        }
        mock_discovery.discover_iam_roles.return_value = {"iam_roles": []}

        mock_get_discovery.return_value = mock_discovery

        scanner = AWSScanner(profile="test", include_network=False)
        result = scanner.scan()

        # Network discovery should NOT be called
        mock_discovery.discover_network_topology.assert_not_called()

        # VPCs should not be in result
        assert "vpcs" not in result

    @patch("cloudstrate.scanner.aws.AWSScanner._get_discovery")
    def test_aws_scanner_scan_without_iam(self, mock_get_discovery):
        """Test scan with include_iam=False skips IAM discovery."""
        from cloudstrate.scanner.aws import AWSScanner

        mock_discovery = MagicMock()
        mock_discovery.discover_organization_structure.return_value = {
            "organization": {},
            "accounts": [],
            "organizational_units": [],
            "scps": [],
        }
        mock_discovery.discover_network_topology.return_value = {
            "vpcs": [],
            "subnets": [],
            "transit_gateways": [],
            "peering_connections": [],
        }
        mock_discovery.discover_ram_shares.return_value = {"ram_shares": []}

        mock_get_discovery.return_value = mock_discovery

        scanner = AWSScanner(profile="test", include_iam=False)
        result = scanner.scan()

        # IAM discovery should NOT be called
        mock_discovery.discover_cross_account_roles.assert_not_called()
        mock_discovery.discover_iam_roles.assert_not_called()

        # IAM fields should not be in result
        assert "iam_roles" not in result
        assert "cross_account_roles" not in result

    @patch("cloudstrate.scanner.aws.AWSScanner._get_discovery")
    def test_aws_scanner_progress_callback(self, mock_get_discovery):
        """Test that progress callback is invoked during scan."""
        from cloudstrate.scanner.aws import AWSScanner

        mock_discovery = MagicMock()
        mock_discovery.discover_organization_structure.return_value = {
            "organization": {},
            "accounts": [],
            "organizational_units": [],
            "scps": [],
        }
        mock_discovery.discover_network_topology.return_value = {
            "vpcs": [],
            "subnets": [],
            "transit_gateways": [],
            "peering_connections": [],
        }
        mock_discovery.discover_ram_shares.return_value = {"ram_shares": []}
        mock_discovery.discover_cross_account_roles.return_value = {
            "cross_account_roles": []
        }
        mock_discovery.discover_iam_roles.return_value = {"iam_roles": []}

        mock_get_discovery.return_value = mock_discovery

        progress_values = []

        def progress_callback(progress):
            progress_values.append(progress)

        scanner = AWSScanner(profile="test")
        scanner.scan(progress_callback=progress_callback)

        # Progress should be called 5 times (5 steps)
        assert len(progress_values) == 5
        # Final progress should be 100
        assert progress_values[-1] == 100.0

    def test_aws_scanner_scan_organization_only(self):
        """Test scan_organization_only returns limited data."""
        from cloudstrate.scanner.aws import AWSScanner

        with patch.object(AWSScanner, "_get_discovery") as mock_get_discovery:
            mock_discovery = MagicMock()
            mock_discovery.discover_organization_structure.return_value = {
                "organization": {"id": "o-123"},
                "accounts": [{"id": "111"}],
            }
            mock_get_discovery.return_value = mock_discovery

            scanner = AWSScanner(profile="test")
            result = scanner.scan_organization_only()

            mock_discovery.discover_organization_structure.assert_called_once()
            mock_discovery.discover_network_topology.assert_not_called()


class TestGitHubScanner:
    """Tests for GitHub scanner wrapper."""

    def test_github_scanner_initialization(self):
        """Test GitHub scanner can be initialized."""
        from cloudstrate.scanner.github import GitHubScanner

        scanner = GitHubScanner(
            organization="test-org",
            include_workflows=True,
            include_oidc=True,
        )

        assert scanner.organization == "test-org"
        assert scanner.include_workflows is True
        assert scanner.include_oidc is True
        assert scanner.token_env == "GITHUB_TOKEN"

    def test_github_scanner_requires_token(self):
        """Test GitHub scanner raises error without token."""
        from cloudstrate.scanner.github import GitHubScanner
        import os

        # Ensure token is not set
        if "GITHUB_TOKEN" in os.environ:
            del os.environ["GITHUB_TOKEN"]

        scanner = GitHubScanner(organization="test-org")

        with pytest.raises(ValueError, match="token not found"):
            scanner.scan()


class TestCartographyScanner:
    """Tests for Cartography scanner wrapper."""

    def test_cartography_scanner_initialization(self):
        """Test Cartography scanner initialization."""
        from cloudstrate.scanner.cartography import CartographyScanner

        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as f:
            f.write(b"neo4j:\n  uri: bolt://localhost:7687\n")
            f.flush()

            scanner = CartographyScanner(
                config_path=f.name,
                neo4j_uri="bolt://localhost:7687",
                neo4j_user="neo4j",
                neo4j_password="secret",
            )

            assert scanner.neo4j_uri == "bolt://localhost:7687"
            assert scanner.neo4j_user == "neo4j"

    def test_cartography_scanner_config_not_found(self):
        """Test Cartography scanner raises error for missing config."""
        from cloudstrate.scanner.cartography import CartographyScanner

        with pytest.raises(FileNotFoundError):
            CartographyScanner(config_path="/nonexistent/config.yaml")


class TestScannerIntegration:
    """Integration tests for scanner modules."""

    def test_aws_scanner_result_structure(self):
        """Test that AWS scanner returns expected structure."""
        from cloudstrate.scanner.aws import AWSScanner

        with patch.object(AWSScanner, "_get_discovery") as mock_get_discovery:
            mock_discovery = MagicMock()
            mock_discovery.discover_organization_structure.return_value = {
                "organization": {"id": "o-123", "arn": "arn:aws:organizations::123:organization/o-123"},
                "accounts": [
                    {"id": "111111111111", "name": "Account1", "email": "a1@example.com"},
                    {"id": "222222222222", "name": "Account2", "email": "a2@example.com"},
                ],
                "organizational_units": [
                    {"id": "ou-root-1234", "name": "Production"},
                ],
                "scps": [
                    {"id": "p-1234", "name": "DenyPolicy"},
                ],
            }
            mock_discovery.discover_network_topology.return_value = {
                "vpcs": [{"id": "vpc-123", "cidr": "10.0.0.0/16"}],
                "subnets": [{"id": "subnet-123", "vpc_id": "vpc-123"}],
                "transit_gateways": [],
                "peering_connections": [],
            }
            mock_discovery.discover_ram_shares.return_value = {"ram_shares": []}
            mock_discovery.discover_cross_account_roles.return_value = {
                "cross_account_roles": []
            }
            mock_discovery.discover_iam_roles.return_value = {"iam_roles": []}

            mock_get_discovery.return_value = mock_discovery

            scanner = AWSScanner(profile="test")
            result = scanner.scan()

            # Verify complete structure
            assert isinstance(result, dict)
            assert "organization" in result
            assert "accounts" in result
            assert len(result["accounts"]) == 2
            assert "organizational_units" in result
            assert "scps" in result
            assert "vpcs" in result
            assert "scan_metadata" in result
            assert "scan_time" in result["scan_metadata"]
            assert "profile" in result["scan_metadata"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
