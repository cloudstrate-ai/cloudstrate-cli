"""
Pydantic models for Cloudstrate configuration.

Provides type-safe configuration with validation.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Literal, Optional
from pathlib import Path


class GeminiConfig(BaseModel):
    """Configuration for Google Gemini LLM."""

    model: str = Field(
        default="gemini-2.0-flash-exp",
        description="Gemini model name",
    )
    api_key_env: str = Field(
        default="GEMINI_API_KEY",
        description="Environment variable containing API key",
    )
    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Sampling temperature",
    )
    max_tokens: int = Field(
        default=8192,
        gt=0,
        description="Maximum tokens in response",
    )


class OllamaConfig(BaseModel):
    """Configuration for Ollama local LLM."""

    model: str = Field(
        default="llama3.1:70b",
        description="Ollama model name",
    )
    url: str = Field(
        default="http://localhost:11434",
        description="Ollama API URL",
    )
    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Sampling temperature",
    )
    context_window: int = Field(
        default=32768,
        gt=0,
        description="Context window size",
    )


class VLLMConfig(BaseModel):
    """Configuration for vLLM server."""

    model: str = Field(
        default="meta-llama/Llama-3.1-70B-Instruct",
        description="HuggingFace model name",
    )
    url: str = Field(
        default="http://localhost:8000",
        description="vLLM server URL",
    )
    api_key: Optional[str] = Field(
        default=None,
        description="Optional API key for vLLM server",
    )


class LLMConfig(BaseModel):
    """LLM provider configuration."""

    provider: Literal["gemini", "ollama", "vllm", "disabled"] = Field(
        default="gemini",
        description="LLM provider to use",
    )
    gemini: GeminiConfig = Field(default_factory=GeminiConfig)
    ollama: OllamaConfig = Field(default_factory=OllamaConfig)
    vllm: VLLMConfig = Field(default_factory=VLLMConfig)
    context_injection: bool = Field(
        default=True,
        description="Inject Cloudstrate documentation into prompts (required for local LLMs)",
    )


class Neo4jConfig(BaseModel):
    """Neo4j database configuration."""

    uri: str = Field(
        default="bolt://localhost:7687",
        description="Neo4j connection URI",
    )
    user: str = Field(
        default="neo4j",
        description="Neo4j username",
    )
    password: str = Field(
        default="",
        description="Neo4j password",
    )
    database: str = Field(
        default="neo4j",
        description="Neo4j database name",
    )


class GitHubStateConfig(BaseModel):
    """GitHub state backend configuration."""

    repo: str = Field(
        default="",
        description="GitHub repository (owner/repo)",
    )
    branch: str = Field(
        default="main",
        description="Branch to store state",
    )
    path: str = Field(
        default="cloudstrate-state",
        description="Path within repository for state files",
    )
    token_env: str = Field(
        default="GITHUB_TOKEN",
        description="Environment variable containing GitHub token",
    )


class S3StateConfig(BaseModel):
    """S3 state backend configuration."""

    bucket: str = Field(
        default="",
        description="S3 bucket name",
    )
    prefix: str = Field(
        default="cloudstrate-state",
        description="Key prefix for state files",
    )
    region: str = Field(
        default="us-east-1",
        description="AWS region for S3 bucket",
    )
    profile: Optional[str] = Field(
        default=None,
        description="AWS profile for S3 access",
    )


class StateConfig(BaseModel):
    """State management configuration."""

    backend: Literal["github", "s3", "local"] = Field(
        default="github",
        description="State storage backend",
    )
    github: GitHubStateConfig = Field(default_factory=GitHubStateConfig)
    s3: S3StateConfig = Field(default_factory=S3StateConfig)
    local_path: str = Field(
        default=".cloudstrate-state",
        description="Local directory for state (when backend=local)",
    )


class AWSScannerConfig(BaseModel):
    """AWS scanner configuration."""

    profile: str = Field(
        default="",
        description="AWS profile name",
    )
    regions: list[str] = Field(
        default_factory=lambda: ["us-east-1"],
        description="AWS regions to scan",
    )
    include_iam: bool = Field(
        default=True,
        description="Include IAM roles and policies",
    )
    include_network: bool = Field(
        default=True,
        description="Include VPC and network topology",
    )
    include_cloudtrail: bool = Field(
        default=True,
        description="Include CloudTrail configurations",
    )


class KubernetesScannerConfig(BaseModel):
    """Kubernetes scanner configuration."""

    context: Optional[str] = Field(
        default=None,
        description="Kubernetes context to use",
    )
    namespaces: list[str] = Field(
        default_factory=list,
        description="Namespaces to scan (empty = all)",
    )


class GitHubScannerConfig(BaseModel):
    """GitHub scanner configuration."""

    organization: str = Field(
        default="",
        description="GitHub organization name",
    )
    include_workflows: bool = Field(
        default=True,
        description="Include GitHub Actions workflows",
    )
    include_oidc: bool = Field(
        default=True,
        description="Include OIDC configuration",
    )


class ScannerConfig(BaseModel):
    """Scanner configuration."""

    aws: AWSScannerConfig = Field(default_factory=AWSScannerConfig)
    kubernetes: KubernetesScannerConfig = Field(default_factory=KubernetesScannerConfig)
    github: GitHubScannerConfig = Field(default_factory=GitHubScannerConfig)


class AthenaConfig(BaseModel):
    """Athena configuration for CloudTrail analysis."""

    database: str = Field(
        default="cloudtrail_logs",
        description="Athena database name",
    )
    workgroup: str = Field(
        default="primary",
        description="Athena workgroup",
    )
    region: str = Field(
        default="us-east-1",
        description="AWS region for Athena",
    )
    output_location: Optional[str] = Field(
        default=None,
        description="S3 output location (optional if workgroup has default)",
    )


class AnalystConfig(BaseModel):
    """Analyst configuration."""

    port: int = Field(
        default=5001,
        description="Port for analyst web server",
    )
    host: str = Field(
        default="127.0.0.1",
        description="Host to bind analyst server",
    )
    enable_cloudtrail: bool = Field(
        default=True,
        description="Enable CloudTrail log analysis",
    )
    athena: AthenaConfig = Field(default_factory=AthenaConfig)


class OIDCConfig(BaseModel):
    """OIDC authentication configuration."""

    enabled: bool = Field(
        default=False,
        description="Enable OIDC authentication",
    )
    issuer: str = Field(
        default="",
        description="OIDC issuer URL",
    )
    client_id: str = Field(
        default="",
        description="OIDC client ID",
    )
    client_secret_env: str = Field(
        default="OIDC_CLIENT_SECRET",
        description="Environment variable for OIDC client secret",
    )
    scopes: list[str] = Field(
        default_factory=lambda: ["openid", "profile", "email"],
        description="OIDC scopes to request",
    )


class AuthConfig(BaseModel):
    """Authentication configuration."""

    mode: Literal["none", "api_key", "oidc"] = Field(
        default="none",
        description="Authentication mode",
    )
    api_key_env: str = Field(
        default="CLOUDSTRATE_API_KEY",
        description="Environment variable for API key",
    )
    oidc: OIDCConfig = Field(default_factory=OIDCConfig)


class KnowledgeBaseConfig(BaseModel):
    """Knowledge base (RAG) configuration."""

    enabled: bool = Field(
        default=False,
        description="Enable knowledge base",
    )
    vector_store: Literal["chromadb", "pinecone"] = Field(
        default="chromadb",
        description="Vector store to use",
    )
    chromadb_path: str = Field(
        default=".cloudstrate-knowledge",
        description="Path for ChromaDB storage",
    )
    embedding_model: str = Field(
        default="all-MiniLM-L6-v2",
        description="Sentence transformer model for embeddings",
    )


class ResilienceConfig(BaseModel):
    """API resilience configuration."""

    max_retries: int = Field(
        default=5,
        ge=1,
        description="Maximum retry attempts",
    )
    initial_delay: float = Field(
        default=1.0,
        gt=0,
        description="Initial backoff delay in seconds",
    )
    max_delay: float = Field(
        default=60.0,
        gt=0,
        description="Maximum backoff delay in seconds",
    )
    multiplier: float = Field(
        default=2.0,
        gt=1,
        description="Backoff multiplier",
    )
    jitter: float = Field(
        default=0.1,
        ge=0,
        le=1,
        description="Random jitter factor (0-1)",
    )


class CloudstrateConfig(BaseModel):
    """Root Cloudstrate configuration."""

    llm: LLMConfig = Field(default_factory=LLMConfig)
    neo4j: Neo4jConfig = Field(default_factory=Neo4jConfig)
    state: StateConfig = Field(default_factory=StateConfig)
    scanner: ScannerConfig = Field(default_factory=ScannerConfig)
    analyst: AnalystConfig = Field(default_factory=AnalystConfig)
    auth: AuthConfig = Field(default_factory=AuthConfig)
    knowledge: KnowledgeBaseConfig = Field(default_factory=KnowledgeBaseConfig)
    resilience: ResilienceConfig = Field(default_factory=ResilienceConfig)

    model_config = {
        "extra": "allow",  # Allow extra fields for forward compatibility
    }
