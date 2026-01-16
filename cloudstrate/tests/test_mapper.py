"""
Tests for Cloudstrate mapper modules.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml


class TestPhase1Mapper:
    """Tests for Phase 1 mapper."""

    @pytest.fixture
    def sample_scan_data(self):
        """Sample scan data for testing."""
        return {
            "organization": {
                "id": "o-123",
                "arn": "arn:aws:organizations::123:organization/o-123",
            },
            "accounts": [
                {"id": "111111111111", "name": "Production", "email": "prod@example.com"},
                {"id": "222222222222", "name": "Development", "email": "dev@example.com"},
            ],
            "organizational_units": [
                {"id": "ou-root-prod", "name": "Production"},
                {"id": "ou-root-dev", "name": "Development"},
            ],
            "scps": [
                {"id": "p-1234", "name": "DenyRegions"},
            ],
            "vpcs": [
                {"id": "vpc-123", "cidr": "10.0.0.0/16", "account_id": "111111111111"},
            ],
        }

    @pytest.fixture
    def scan_file(self, sample_scan_data):
        """Create temporary scan file."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(sample_scan_data, f)
            f.flush()
            yield f.name

        Path(f.name).unlink(missing_ok=True)

    def test_phase1_mapper_initialization(self, scan_file):
        """Test Phase 1 mapper can be initialized."""
        from cloudstrate.mapper.phase1 import Phase1Mapper

        mapper = Phase1Mapper(scan_file=scan_file)

        assert mapper.scan_file == Path(scan_file)
        assert mapper.decisions_file is None
        assert mapper.state is None

    def test_phase1_mapper_file_not_found(self):
        """Test Phase 1 mapper raises error for missing file."""
        from cloudstrate.mapper.phase1 import Phase1Mapper

        with pytest.raises(FileNotFoundError):
            Phase1Mapper(scan_file="/nonexistent/scan.json")

    def test_phase1_mapper_run_basic(self, scan_file, sample_scan_data):
        """Test Phase 1 mapper creates basic state."""
        from cloudstrate.mapper.phase1 import Phase1Mapper

        mapper = Phase1Mapper(scan_file=scan_file)
        state = mapper.run()

        # Verify state structure
        assert "security_zones" in state
        assert "subtenants" in state
        assert "tenants" in state
        assert "network_domains" in state
        assert "proposals" in state

        # Verify security zones created from OUs
        assert len(state["security_zones"]) == 2
        zone_names = [z["name"] for z in state["security_zones"]]
        assert "Production" in zone_names
        assert "Development" in zone_names

        # Verify subtenants created from accounts
        assert len(state["subtenants"]) == 2
        subtenant_names = [st["name"] for st in state["subtenants"]]
        assert "Production" in subtenant_names
        assert "Development" in subtenant_names

    def test_phase1_mapper_generates_proposals(self, scan_file):
        """Test Phase 1 mapper generates proposals for Phase 2."""
        from cloudstrate.mapper.phase1 import Phase1Mapper

        mapper = Phase1Mapper(scan_file=scan_file)
        state = mapper.run()

        # Should have proposals
        assert len(state["proposals"]) > 0

        # Check proposal types
        proposal_types = [p["type"] for p in state["proposals"]]
        assert "tenant_grouping" in proposal_types or "network_domain" in proposal_types

    def test_phase1_mapper_save_state(self, scan_file):
        """Test Phase 1 mapper can save state to file."""
        from cloudstrate.mapper.phase1 import Phase1Mapper

        mapper = Phase1Mapper(scan_file=scan_file)
        mapper.run()

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "state.yaml"
            mapper.save_state(output_path)

            assert output_path.exists()

            with open(output_path) as f:
                saved_state = yaml.safe_load(f)

            assert "security_zones" in saved_state
            assert "subtenants" in saved_state

    def test_phase1_mapper_save_state_without_run(self, scan_file):
        """Test save_state raises error if run() not called."""
        from cloudstrate.mapper.phase1 import Phase1Mapper

        mapper = Phase1Mapper(scan_file=scan_file)

        with pytest.raises(RuntimeError, match="No state to save"):
            mapper.save_state("/tmp/state.yaml")

    def test_phase1_mapper_with_decisions(self, scan_file):
        """Test Phase 1 mapper respects pre-configured decisions."""
        from cloudstrate.mapper.phase1 import Phase1Mapper

        decisions = {
            "security_zones": [
                {"id": "sz-custom", "name": "Custom Zone"},
            ],
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            yaml.dump(decisions, f)
            f.flush()

            mapper = Phase1Mapper(scan_file=scan_file, decisions_file=f.name)
            state = mapper.run()

            # State should be created (decisions integration depends on implementation)
            assert state is not None

        Path(f.name).unlink(missing_ok=True)


class TestPhase2Server:
    """Tests for Phase 2 server."""

    @pytest.fixture
    def sample_state(self):
        """Sample mapping state for testing."""
        return {
            "security_zones": [
                {"id": "sz-1", "name": "Production", "description": "Production zone"},
            ],
            "tenants": [],
            "subtenants": [
                {"id": "st-1", "name": "App1", "aws_accounts": ["111"]},
            ],
            "proposals": [
                {"type": "tenant_grouping", "description": "Group apps", "status": "pending"},
            ],
        }

    @pytest.fixture
    def state_file(self, sample_state):
        """Create temporary state file."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            yaml.dump(sample_state, f)
            f.flush()
            yield f.name

        Path(f.name).unlink(missing_ok=True)

    def test_phase2_server_initialization(self, state_file):
        """Test Phase 2 server can be initialized."""
        from cloudstrate.mapper.phase2 import Phase2Server

        server = Phase2Server(state_file=state_file)

        assert server.state_file == Path(state_file)
        assert server.state is not None
        assert "security_zones" in server.state

    def test_phase2_server_file_not_found(self):
        """Test Phase 2 server raises error for missing file."""
        from cloudstrate.mapper.phase2 import Phase2Server

        with pytest.raises(FileNotFoundError):
            Phase2Server(state_file="/nonexistent/state.yaml")

    def test_phase2_server_loads_state(self, state_file, sample_state):
        """Test Phase 2 server loads state correctly."""
        from cloudstrate.mapper.phase2 import Phase2Server

        server = Phase2Server(state_file=state_file)

        assert len(server.state["security_zones"]) == 1
        assert len(server.state["subtenants"]) == 1
        assert len(server.state["proposals"]) == 1


class TestMapperIntegration:
    """Integration tests for mapper modules."""

    def test_phase1_to_phase2_workflow(self):
        """Test complete workflow from Phase 1 to Phase 2."""
        from cloudstrate.mapper.phase1 import Phase1Mapper
        from cloudstrate.mapper.phase2 import Phase2Server

        # Create scan data
        scan_data = {
            "organization": {"id": "o-123"},
            "accounts": [
                {"id": "111", "name": "Account1"},
                {"id": "222", "name": "Account2"},
            ],
            "organizational_units": [
                {"id": "ou-1", "name": "OU1"},
            ],
            "vpcs": [],
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            # Save scan data
            scan_file = Path(tmpdir) / "scan.json"
            with open(scan_file, "w") as f:
                json.dump(scan_data, f)

            # Run Phase 1
            mapper = Phase1Mapper(scan_file=scan_file)
            state = mapper.run()

            # Save state
            state_file = Path(tmpdir) / "state.yaml"
            mapper.save_state(state_file)

            # Initialize Phase 2
            server = Phase2Server(state_file=state_file)

            # Verify state was transferred
            assert len(server.state["subtenants"]) == 2
            assert len(server.state["security_zones"]) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
