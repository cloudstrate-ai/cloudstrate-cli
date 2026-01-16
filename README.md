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

### 1. Setup Environment

```bash
# Full setup (Neo4j, AWS, GitHub validation)
cloudstrate setup init

# Or setup individual components
cloudstrate setup neo4j --neo4j-password your-password
cloudstrate setup aws --profile your-profile
cloudstrate setup github --org your-org

# Check status
cloudstrate setup check
```

### 2. Initialize Configuration (Optional)

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
cloudstrate setup --help    # Environment setup
cloudstrate scan --help     # Infrastructure scanning
cloudstrate map --help      # Model mapping
cloudstrate analyst --help  # Query interface
cloudstrate build --help    # Terraform generation
cloudstrate config --help   # Configuration management
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

## Docker Deployment

### Quick Start with Docker Compose

```bash
# Start Cloudstrate with Neo4j
docker-compose up -d        # v1 syntax
# or: docker compose up -d  # v2 syntax

# View logs
docker-compose logs -f

# Access services:
# - Neo4j Browser: http://localhost:7474
# - Analyst Server: http://localhost:5001
```

### Environment Variables

Create a `.env` file:

```bash
NEO4J_PASSWORD=your-secure-password
GITHUB_TOKEN=your-github-token
GEMINI_API_KEY=your-gemini-key
AWS_PROFILE=your-profile
```

### Run CLI Commands

```bash
# Interactive CLI
docker-compose --profile cli run --rm cli

# Run a scan
docker-compose --profile scanner run --rm scanner scan aws --output /app/data/scan.json
```

### Build Images

```bash
# Build all images
docker-compose build

# Build specific target
docker build -t cloudstrate:latest --target base .
docker build -t cloudstrate:analyst --target analyst .
docker build -t cloudstrate:scanner --target scanner .
```

## Kubernetes Deployment

### Prerequisites

- Kubernetes cluster (kind, minikube, Docker Desktop, or k3d)
- kubectl configured

### Deploy with Script

```bash
# Build and deploy
./kubernetes/deploy.sh --build

# Deploy only (image already built)
./kubernetes/deploy.sh
```

### Deploy Manually

```bash
# Build image and load into cluster (kind example)
docker build -t cloudstrate:latest .
kind load docker-image cloudstrate:latest

# Deploy with kustomize
kubectl apply -k kubernetes/

# Check status
kubectl get all -n cloudstrate
```

### Access Services

```bash
# NodePort access (default)
# Neo4j Browser: http://localhost:30474
# Analyst Server: http://localhost:30501

# Or use port-forwarding
kubectl port-forward -n cloudstrate svc/neo4j 7474:7474 7687:7687
kubectl port-forward -n cloudstrate svc/analyst 5001:5001
```

### Run Scanner Job

```bash
# Edit scanner-job.yaml with your scan command, then:
kubectl apply -f kubernetes/scanner-job.yaml

# Watch job progress
kubectl logs -f job/cloudstrate-scanner -n cloudstrate
```

### Configuration

Edit `kubernetes/secret.yaml` before deploying:

```yaml
stringData:
  NEO4J_PASSWORD: "your-password"
  GITHUB_TOKEN: "ghp_..."
  GEMINI_API_KEY: "..."
```

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
