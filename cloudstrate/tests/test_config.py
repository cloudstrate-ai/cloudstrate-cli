"""
Tests for Cloudstrate configuration module.
"""

import os
import tempfile
from pathlib import Path

import pytest
import yaml

from cloudstrate.config.schema import (
    CloudstrateConfig,
    LLMConfig,
    Neo4jConfig,
    StateConfig,
    GeminiConfig,
    OllamaConfig,
)
from cloudstrate.config.loader import (
    load_config,
    load_default_config,
    find_config_file,
    save_config,
    _apply_env_overrides,
)


class TestConfigSchema:
    """Tests for configuration schema models."""

    def test_default_config_creates_valid_instance(self):
        """Test that default configuration creates a valid instance."""
        config = CloudstrateConfig()

        assert config.llm.provider == "gemini"
        assert config.neo4j.uri == "bolt://localhost:7687"
        assert config.state.backend == "github"

    def test_llm_config_validates_provider(self):
        """Test that LLM provider must be valid."""
        config = LLMConfig(provider="gemini")
        assert config.provider == "gemini"

        config = LLMConfig(provider="ollama")
        assert config.provider == "ollama"

        config = LLMConfig(provider="vllm")
        assert config.provider == "vllm"

        config = LLMConfig(provider="disabled")
        assert config.provider == "disabled"

    def test_llm_config_rejects_invalid_provider(self):
        """Test that invalid LLM provider raises error."""
        with pytest.raises(ValueError):
            LLMConfig(provider="invalid")

    def test_gemini_config_defaults(self):
        """Test Gemini configuration defaults."""
        config = GeminiConfig()

        assert config.model == "gemini-2.0-flash-exp"
        assert config.api_key_env == "GEMINI_API_KEY"
        assert config.temperature == 0.7
        assert config.max_tokens == 8192

    def test_gemini_config_temperature_validation(self):
        """Test Gemini temperature must be between 0 and 2."""
        config = GeminiConfig(temperature=0.0)
        assert config.temperature == 0.0

        config = GeminiConfig(temperature=2.0)
        assert config.temperature == 2.0

        with pytest.raises(ValueError):
            GeminiConfig(temperature=-0.1)

        with pytest.raises(ValueError):
            GeminiConfig(temperature=2.1)

    def test_ollama_config_defaults(self):
        """Test Ollama configuration defaults."""
        config = OllamaConfig()

        assert config.model == "llama3.1:70b"
        assert config.url == "http://localhost:11434"
        assert config.temperature == 0.7

    def test_neo4j_config_defaults(self):
        """Test Neo4j configuration defaults."""
        config = Neo4jConfig()

        assert config.uri == "bolt://localhost:7687"
        assert config.user == "neo4j"
        assert config.password == ""
        assert config.database == "neo4j"

    def test_state_config_github_backend(self):
        """Test state configuration with GitHub backend."""
        config = StateConfig(backend="github")

        assert config.backend == "github"
        assert config.github.branch == "main"
        assert config.github.path == "cloudstrate-state"

    def test_state_config_s3_backend(self):
        """Test state configuration with S3 backend."""
        config = StateConfig(backend="s3")

        assert config.backend == "s3"
        assert config.s3.prefix == "cloudstrate-state"
        assert config.s3.region == "us-east-1"

    def test_full_config_serialization(self):
        """Test that full config can be serialized and deserialized."""
        config = CloudstrateConfig(
            llm=LLMConfig(provider="ollama"),
            neo4j=Neo4jConfig(password="secret"),
            state=StateConfig(backend="s3"),
        )

        data = config.model_dump()

        assert data["llm"]["provider"] == "ollama"
        assert data["neo4j"]["password"] == "secret"
        assert data["state"]["backend"] == "s3"

        # Deserialize back
        restored = CloudstrateConfig(**data)
        assert restored.llm.provider == "ollama"


class TestConfigLoader:
    """Tests for configuration loading."""

    def test_load_config_from_yaml(self):
        """Test loading configuration from YAML file."""
        config_data = {
            "llm": {"provider": "ollama"},
            "neo4j": {"password": "test123"},
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            yaml.dump(config_data, f)
            f.flush()

            config = load_config(f.name)

            assert config.llm.provider == "ollama"
            assert config.neo4j.password == "test123"

        os.unlink(f.name)

    def test_load_config_file_not_found(self):
        """Test that missing config file raises error."""
        with pytest.raises(FileNotFoundError):
            load_config("/nonexistent/path/config.yaml")

    def test_load_default_config_returns_defaults(self):
        """Test that default config loader returns valid defaults."""
        config = load_default_config()

        assert isinstance(config, CloudstrateConfig)
        assert config.llm.provider in ("gemini", "ollama", "vllm", "disabled")

    def test_env_overrides_applied(self):
        """Test that environment variables override config values."""
        os.environ["CLOUDSTRATE_LLM_PROVIDER"] = "ollama"
        os.environ["CLOUDSTRATE_NEO4J_PASSWORD"] = "env_secret"

        try:
            raw_config = {}
            result = _apply_env_overrides(raw_config)

            assert result["llm"]["provider"] == "ollama"
            assert result["neo4j"]["password"] == "env_secret"
        finally:
            del os.environ["CLOUDSTRATE_LLM_PROVIDER"]
            del os.environ["CLOUDSTRATE_NEO4J_PASSWORD"]

    def test_env_overrides_preserve_existing_values(self):
        """Test that env overrides preserve non-overridden values."""
        os.environ["CLOUDSTRATE_NEO4J_PASSWORD"] = "env_secret"

        try:
            raw_config = {
                "neo4j": {"uri": "bolt://custom:7687"},
            }
            result = _apply_env_overrides(raw_config)

            assert result["neo4j"]["uri"] == "bolt://custom:7687"
            assert result["neo4j"]["password"] == "env_secret"
        finally:
            del os.environ["CLOUDSTRATE_NEO4J_PASSWORD"]

    def test_save_config_creates_yaml_file(self):
        """Test that config can be saved to YAML file."""
        config = CloudstrateConfig(
            llm=LLMConfig(provider="ollama"),
            neo4j=Neo4jConfig(password="test"),
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "test-config.yaml"
            save_config(config, config_path)

            assert config_path.exists()

            # Verify contents
            with open(config_path) as f:
                content = f.read()
                assert "# Cloudstrate Configuration" in content
                data = yaml.safe_load(content.split("\n\n", 1)[1])
                assert data["llm"]["provider"] == "ollama"

    def test_find_config_file_in_current_dir(self):
        """Test finding config file in current directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "cloudstrate-config.yaml"
            config_path.touch()

            # Change to temp directory
            original_dir = os.getcwd()
            os.chdir(tmpdir)

            try:
                found = find_config_file()
                assert found is not None
                assert found.name == "cloudstrate-config.yaml"
            finally:
                os.chdir(original_dir)


class TestConfigValidation:
    """Tests for configuration validation."""

    def test_resilience_config_validates_ranges(self):
        """Test that resilience config validates numeric ranges."""
        from cloudstrate.config.schema import ResilienceConfig

        config = ResilienceConfig(
            max_retries=5,
            initial_delay=1.0,
            max_delay=60.0,
            multiplier=2.0,
            jitter=0.1,
        )

        assert config.max_retries == 5

        # Test invalid values
        with pytest.raises(ValueError):
            ResilienceConfig(max_retries=0)

        with pytest.raises(ValueError):
            ResilienceConfig(initial_delay=-1.0)

        with pytest.raises(ValueError):
            ResilienceConfig(jitter=1.5)

    def test_scanner_config_default_regions(self):
        """Test that scanner config has default regions."""
        from cloudstrate.config.schema import AWSScannerConfig

        config = AWSScannerConfig()
        assert "us-east-1" in config.regions

    def test_extra_fields_allowed(self):
        """Test that extra fields are allowed for forward compatibility."""
        data = {
            "llm": {"provider": "gemini"},
            "future_feature": {"enabled": True},
        }

        config = CloudstrateConfig(**data)
        assert config.llm.provider == "gemini"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
