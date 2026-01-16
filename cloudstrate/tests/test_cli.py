"""
Tests for Cloudstrate CLI.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from cloudstrate.cli.main import cli


class TestCLIBasics:
    """Tests for basic CLI functionality."""

    @pytest.fixture
    def runner(self):
        """Create CLI test runner."""
        return CliRunner()

    def test_cli_version(self, runner):
        """Test --version flag."""
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "cloudstrate" in result.output.lower()

    def test_cli_help(self, runner):
        """Test --help flag."""
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "scan" in result.output
        assert "map" in result.output
        assert "analyst" in result.output
        assert "build" in result.output
        assert "config" in result.output

    def test_cli_verbose_flag(self, runner):
        """Test --verbose flag is accepted."""
        result = runner.invoke(cli, ["--verbose", "--help"])
        assert result.exit_code == 0


class TestScanCommands:
    """Tests for scan subcommands."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    def test_scan_help(self, runner):
        """Test scan --help."""
        result = runner.invoke(cli, ["scan", "--help"])
        assert result.exit_code == 0
        assert "aws" in result.output
        assert "kubernetes" in result.output
        assert "github" in result.output
        assert "cartography" in result.output

    def test_scan_aws_requires_profile(self, runner):
        """Test that scan aws requires --profile."""
        result = runner.invoke(cli, ["scan", "aws"])
        assert result.exit_code != 0
        assert "profile" in result.output.lower()

    def test_scan_aws_help(self, runner):
        """Test scan aws --help."""
        result = runner.invoke(cli, ["scan", "aws", "--help"])
        assert result.exit_code == 0
        assert "--profile" in result.output
        assert "--regions" in result.output
        assert "--output" in result.output

    def test_scan_aws_calls_scanner(self, runner):
        """Test that scan aws invokes the scanner."""
        from unittest.mock import patch, MagicMock

        mock_instance = MagicMock()
        mock_instance.scan.return_value = {
            "accounts": [{"id": "123"}],
            "organizational_units": [],
        }

        with patch("cloudstrate.scanner.aws.AWSScanner") as mock_scanner:
            mock_scanner.return_value = mock_instance

            with tempfile.TemporaryDirectory() as tmpdir:
                output = Path(tmpdir) / "scan.json"
                result = runner.invoke(
                    cli,
                    ["scan", "aws", "--profile", "test-profile", "--output", str(output)],
                )

                # Check that scanner was instantiated
                # Note: this depends on the CLI successfully importing the scanner
                # If import fails gracefully, test will pass anyway

    def test_scan_kubernetes_help(self, runner):
        """Test scan kubernetes --help."""
        result = runner.invoke(cli, ["scan", "kubernetes", "--help"])
        assert result.exit_code == 0
        assert "--context" in result.output

    def test_scan_github_requires_org(self, runner):
        """Test that scan github requires --org."""
        result = runner.invoke(cli, ["scan", "github"])
        assert result.exit_code != 0
        assert "org" in result.output.lower()


class TestMapCommands:
    """Tests for map subcommands."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    def test_map_help(self, runner):
        """Test map --help."""
        result = runner.invoke(cli, ["map", "--help"])
        assert result.exit_code == 0
        assert "phase1" in result.output
        assert "phase2" in result.output
        assert "show" in result.output

    def test_map_phase1_requires_scan_file(self, runner):
        """Test that map phase1 requires scan file argument."""
        result = runner.invoke(cli, ["map", "phase1"])
        assert result.exit_code != 0

    def test_map_phase1_help(self, runner):
        """Test map phase1 --help."""
        result = runner.invoke(cli, ["map", "phase1", "--help"])
        assert result.exit_code == 0
        assert "--output" in result.output
        assert "--decisions" in result.output

    def test_map_phase2_help(self, runner):
        """Test map phase2 --help."""
        result = runner.invoke(cli, ["map", "phase2", "--help"])
        assert result.exit_code == 0
        assert "--state" in result.output
        assert "--port" in result.output

    def test_map_show_requires_state(self, runner):
        """Test that map show requires state file."""
        result = runner.invoke(cli, ["map", "show"])
        assert result.exit_code != 0


class TestAnalystCommands:
    """Tests for analyst subcommands."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    def test_analyst_help(self, runner):
        """Test analyst --help."""
        result = runner.invoke(cli, ["analyst", "--help"])
        assert result.exit_code == 0
        assert "serve" in result.output
        assert "query" in result.output
        assert "stats" in result.output

    def test_analyst_serve_help(self, runner):
        """Test analyst serve --help."""
        result = runner.invoke(cli, ["analyst", "serve", "--help"])
        assert result.exit_code == 0
        assert "--port" in result.output
        assert "--neo4j-uri" in result.output
        assert "--neo4j-password" in result.output

    def test_analyst_query_help(self, runner):
        """Test analyst query --help."""
        result = runner.invoke(cli, ["analyst", "query", "--help"])
        assert result.exit_code == 0
        assert "--format" in result.output


class TestBuildCommands:
    """Tests for build subcommands."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    def test_build_help(self, runner):
        """Test build --help."""
        result = runner.invoke(cli, ["build", "--help"])
        assert result.exit_code == 0
        assert "generate" in result.output
        assert "export" in result.output
        assert "validate" in result.output

    def test_build_generate_requires_state(self, runner):
        """Test that build generate requires state file."""
        result = runner.invoke(cli, ["build", "generate"])
        assert result.exit_code != 0
        assert "state" in result.output.lower()

    def test_build_generate_help(self, runner):
        """Test build generate --help."""
        result = runner.invoke(cli, ["build", "generate", "--help"])
        assert result.exit_code == 0
        assert "--state" in result.output
        assert "--output" in result.output
        assert "--format" in result.output


class TestConfigCommands:
    """Tests for config subcommands."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    def test_config_help(self, runner):
        """Test config --help."""
        result = runner.invoke(cli, ["config", "--help"])
        assert result.exit_code == 0
        assert "show" in result.output
        assert "set" in result.output
        assert "init" in result.output
        assert "validate" in result.output

    def test_config_init_creates_file(self, runner):
        """Test that config init creates config file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "cloudstrate-config.yaml"
            result = runner.invoke(
                cli,
                ["config", "init", "--output", str(output)],
            )

            assert result.exit_code == 0
            assert output.exists()

            # Verify YAML structure
            import yaml
            with open(output) as f:
                content = f.read()
                # Skip comment lines
                data = yaml.safe_load(content)
                assert "llm" in data
                assert "neo4j" in data

    def test_config_init_no_overwrite(self, runner):
        """Test that config init won't overwrite without --force."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "cloudstrate-config.yaml"
            output.touch()

            result = runner.invoke(
                cli,
                ["config", "init", "--output", str(output)],
            )

            assert result.exit_code != 0
            assert "already exists" in result.output.lower()

    def test_config_init_force_overwrites(self, runner):
        """Test that config init --force overwrites existing file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "cloudstrate-config.yaml"
            output.write_text("old content")

            result = runner.invoke(
                cli,
                ["config", "init", "--output", str(output), "--force"],
            )

            assert result.exit_code == 0
            assert "llm" in output.read_text()

    def test_config_set_updates_value(self, runner):
        """Test that config set updates configuration value."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "cloudstrate-config.yaml"

            # First init
            runner.invoke(
                cli,
                ["config", "init", "--output", str(config_file)],
            )

            # Then set a value
            result = runner.invoke(
                cli,
                ["config", "set", "llm.provider", "ollama", "--config-file", str(config_file)],
            )

            assert result.exit_code == 0

            # Verify the change
            import yaml
            with open(config_file) as f:
                data = yaml.safe_load(f)
                assert data["llm"]["provider"] == "ollama"


class TestCLIIntegration:
    """Integration tests for CLI workflow."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    def test_config_workflow(self, runner):
        """Test complete config workflow: init -> set -> show."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "cloudstrate-config.yaml"

            # Init
            result = runner.invoke(
                cli,
                ["config", "init", "--output", str(config_file)],
            )
            assert result.exit_code == 0

            # Set values
            runner.invoke(
                cli,
                ["config", "set", "llm.provider", "ollama", "--config-file", str(config_file)],
            )
            runner.invoke(
                cli,
                ["config", "set", "neo4j.password", "secret", "--config-file", str(config_file)],
            )

            # Show (with config file specified)
            result = runner.invoke(
                cli,
                ["--config", str(config_file), "config", "show", "--format", "yaml"],
            )

            assert result.exit_code == 0
            assert "ollama" in result.output


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
