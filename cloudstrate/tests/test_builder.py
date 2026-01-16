"""
Tests for Cloudstrate builder modules.
"""

import tempfile
from pathlib import Path

import pytest
import yaml


class TestTerraformBuilder:
    """Tests for Terraform builder."""

    @pytest.fixture
    def sample_state(self):
        """Sample mapping state for testing."""
        return {
            "security_zones": [
                {"id": "sz-prod", "name": "Production"},
            ],
            "tenants": [
                {"id": "t-1", "name": "Tenant1", "security_zone": "sz-prod"},
            ],
            "subtenants": [
                {"id": "st-1", "name": "App1", "tenant": "t-1", "aws_accounts": ["111111111111"]},
                {"id": "st-2", "name": "App2", "tenant": "t-1", "aws_accounts": ["222222222222"]},
            ],
            "network_domains": [
                {"id": "nd-1", "name": "Production Network", "vpcs": ["vpc-123"]},
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

    def test_terraform_builder_initialization(self, state_file):
        """Test Terraform builder can be initialized."""
        from cloudstrate.builder.terraform import TerraformBuilder

        builder = TerraformBuilder(
            state_file=state_file,
            output_dir="/tmp/generated",
        )

        assert builder.state_file == Path(state_file)
        assert builder.output_dir == Path("/tmp/generated")
        assert builder.format == "terraform"

    def test_terraform_builder_default_modules(self, state_file):
        """Test Terraform builder has default modules."""
        from cloudstrate.builder.terraform import TerraformBuilder

        builder = TerraformBuilder(state_file=state_file)

        assert "aws" in builder.modules
        assert "tenants" in builder.modules

    def test_terraform_builder_file_not_found(self):
        """Test Terraform builder raises error for missing file."""
        from cloudstrate.builder.terraform import TerraformBuilder

        with pytest.raises(FileNotFoundError):
            TerraformBuilder(state_file="/nonexistent/state.yaml")

    def test_terraform_builder_loads_state(self, state_file, sample_state):
        """Test Terraform builder loads state correctly."""
        from cloudstrate.builder.terraform import TerraformBuilder

        builder = TerraformBuilder(state_file=state_file)

        assert len(builder.state["security_zones"]) == 1
        assert len(builder.state["subtenants"]) == 2

    def test_terraform_builder_generate_creates_files(self, state_file):
        """Test Terraform builder creates output files."""
        from cloudstrate.builder.terraform import TerraformBuilder

        with tempfile.TemporaryDirectory() as tmpdir:
            builder = TerraformBuilder(
                state_file=state_file,
                output_dir=tmpdir,
            )

            result = builder.generate()

            # Check result
            assert result["files_created"] > 0
            assert result["output_dir"] == tmpdir

            # Check files exist
            output_dir = Path(tmpdir)
            assert (output_dir / "main.tf").exists()
            assert (output_dir / "variables.tf").exists()
            assert (output_dir / "outputs.tf").exists()

    def test_terraform_builder_main_tf_content(self, state_file):
        """Test main.tf content is valid."""
        from cloudstrate.builder.terraform import TerraformBuilder

        with tempfile.TemporaryDirectory() as tmpdir:
            builder = TerraformBuilder(
                state_file=state_file,
                output_dir=tmpdir,
            )

            builder.generate()

            main_tf = (Path(tmpdir) / "main.tf").read_text()

            # Check required content
            assert "terraform {" in main_tf
            assert "required_version" in main_tf
            assert "aws" in main_tf
            assert "provider" in main_tf

    def test_terraform_builder_variables_tf_content(self, state_file):
        """Test variables.tf content is valid."""
        from cloudstrate.builder.terraform import TerraformBuilder

        with tempfile.TemporaryDirectory() as tmpdir:
            builder = TerraformBuilder(
                state_file=state_file,
                output_dir=tmpdir,
            )

            builder.generate()

            variables_tf = (Path(tmpdir) / "variables.tf").read_text()

            # Check required variables
            assert "variable" in variables_tf
            assert "aws_region" in variables_tf

    def test_terraform_builder_tfvars_content(self, state_file):
        """Test terraform.tfvars content is valid."""
        from cloudstrate.builder.terraform import TerraformBuilder

        with tempfile.TemporaryDirectory() as tmpdir:
            builder = TerraformBuilder(
                state_file=state_file,
                output_dir=tmpdir,
            )

            builder.generate()

            tfvars = (Path(tmpdir) / "terraform.tfvars").read_text()

            # Check content
            assert "aws_region" in tfvars
            assert "Cloudstrate" in tfvars


class TestBuilderIntegration:
    """Integration tests for builder modules."""

    def test_full_generation_workflow(self):
        """Test complete Terraform generation workflow."""
        from cloudstrate.builder.terraform import TerraformBuilder

        # Create state
        state = {
            "security_zones": [{"id": "sz-1", "name": "Zone1"}],
            "tenants": [],
            "subtenants": [
                {"id": "st-1", "name": "Sub1", "aws_accounts": ["111"]},
            ],
            "network_domains": [],
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            # Save state
            state_file = Path(tmpdir) / "state.yaml"
            with open(state_file, "w") as f:
                yaml.dump(state, f)

            # Generate Terraform
            output_dir = Path(tmpdir) / "generated"
            builder = TerraformBuilder(
                state_file=state_file,
                output_dir=output_dir,
            )

            result = builder.generate()

            # Verify generation succeeded
            assert result["files_created"] >= 3
            assert output_dir.exists()

            # Verify all expected files exist
            assert (output_dir / "main.tf").exists()
            assert (output_dir / "variables.tf").exists()
            assert (output_dir / "outputs.tf").exists()
            assert (output_dir / "terraform.tfvars").exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
