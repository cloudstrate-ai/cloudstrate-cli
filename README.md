# Cloudstrate

Multi-cloud governance platform for scanning, mapping, analyzing, and generating infrastructure as code.

## Features

- **Scanner**: Discover AWS organizations, GitHub repositories, and Kubernetes clusters
- **Mapper**: Automatically map discovered resources to Cloudstrate model (Security Zones, Tenants, Subtenants)
- **Analyst**: Query infrastructure using natural language with Neo4j graph database
- **Builder**: Generate Terraform/OpenTofu from Cloudstrate model

## Installation

```bash
pip install cloudstrate
```

Or install from source:

```bash
pip install -e .
```

## Quick Start

### 1. Initialize Configuration

```bash
cloudstrate config init
```

Edit `cloudstrate-config.yaml` to set your credentials:

```yaml
neo4j:
  uri: bolt://localhost:7687
  user: neo4j
  password: your-password

scanner:
  aws:
    profile: your-aws-profile
```

### 2. Scan AWS Organization

```bash
cloudstrate scan aws --profile your-profile --output scan.json
```

### 3. Run Phase 1 Mapping

```bash
cloudstrate map phase1 scan.json --output mapping-state.yaml
```

### 4. Review with Phase 2 (Interactive)

```bash
cloudstrate map phase2 --state mapping-state.yaml --port 5000
```

Open http://localhost:5000 to review and refine the model.

### 5. Generate Terraform

```bash
cloudstrate build generate --state mapping-state.yaml --output generated/
```

### 6. Query with Analyst

```bash
# Start web interface
cloudstrate analyst serve --port 5001

# Or query directly
cloudstrate analyst query "Show all production accounts"
```

## CLI Reference

```
cloudstrate --help
cloudstrate scan --help
cloudstrate map --help
cloudstrate analyst --help
cloudstrate build --help
cloudstrate config --help
```

## Configuration

Cloudstrate looks for `cloudstrate-config.yaml` in:
1. Current directory
2. Parent directories (up to 5 levels)
3. `~/.config/cloudstrate/`
4. `/etc/cloudstrate/`

Environment variables can override config values:
- `CLOUDSTRATE_NEO4J_PASSWORD`
- `CLOUDSTRATE_LLM_PROVIDER`
- `CLOUDSTRATE_AWS_PROFILE`

## Development

### Setup

```bash
pip install -e ".[dev]"
```

### Run Tests

```bash
pytest
```

### Run with Coverage

```bash
pytest --cov=cloudstrate --cov-report=html
```

## Architecture

```
cloudstrate/
├── cli/           # Click CLI commands
├── config/        # Configuration loading and validation
├── scanner/       # Cloud infrastructure scanners
├── mapper/        # Phase 1 & 2 mapping
├── analyst/       # Natural language query interface
├── builder/       # Terraform generation
├── state/         # State management (GitHub/S3)
├── llm/           # LLM provider abstraction
├── auth/          # OIDC authentication
├── knowledge/     # RAG knowledge base
├── connectors/    # Custom object connectors
└── resilience/    # Rate limiting and backoff
```

## License

MIT
