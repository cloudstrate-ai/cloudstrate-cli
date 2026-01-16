# Cloudstrate CLI Dockerfile
# Multi-cloud governance platform

FROM python:3.11-slim AS base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd --gid 1000 cloudstrate \
    && useradd --uid 1000 --gid cloudstrate --shell /bin/bash --create-home cloudstrate

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY --chown=cloudstrate:cloudstrate . .

# Install cloudstrate package
RUN pip install --no-cache-dir -e .

# Switch to non-root user
USER cloudstrate

# Default command
ENTRYPOINT ["cloudstrate"]
CMD ["--help"]

# --- Development image with additional tools ---
FROM base AS dev

USER root

# Install development dependencies
RUN pip install --no-cache-dir \
    pytest \
    pytest-cov \
    pytest-mock \
    black \
    ruff \
    mypy

USER cloudstrate

CMD ["--help"]

# --- Analyst server image ---
FROM base AS analyst

# Expose analyst server port
EXPOSE 5001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5001/health || exit 1

# Run analyst server
CMD ["analyst", "serve", "--host", "0.0.0.0", "--port", "5001"]

# --- Scanner image (for batch jobs) ---
FROM base AS scanner

# Scanner runs as batch job, no exposed ports
CMD ["scan", "--help"]
