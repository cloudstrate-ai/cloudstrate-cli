#!/bin/bash
# Deploy Cloudstrate to local Kubernetes cluster
# Works with: kind, minikube, Docker Desktop, k3d

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NAMESPACE="cloudstrate"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Cloudstrate Kubernetes Deployment ===${NC}"

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo -e "${RED}Error: kubectl not found. Please install kubectl.${NC}"
    exit 1
fi

# Check cluster connection
if ! kubectl cluster-info &> /dev/null; then
    echo -e "${RED}Error: Cannot connect to Kubernetes cluster.${NC}"
    echo "Make sure your cluster is running and kubectl is configured."
    exit 1
fi

echo -e "${GREEN}Connected to cluster:${NC}"
kubectl cluster-info | head -1

# Build the image if requested
if [[ "$1" == "--build" ]]; then
    echo -e "\n${YELLOW}Building cloudstrate image...${NC}"

    # Check what cluster type we're using
    if command -v kind &> /dev/null && kind get clusters 2>/dev/null | grep -q .; then
        echo "Detected kind cluster - building and loading image"
        docker build -t cloudstrate:latest "$SCRIPT_DIR/.."
        kind load docker-image cloudstrate:latest
    elif command -v minikube &> /dev/null && minikube status &>/dev/null; then
        echo "Detected minikube - using minikube docker env"
        eval $(minikube docker-env)
        docker build -t cloudstrate:latest "$SCRIPT_DIR/.."
    else
        echo "Building image locally"
        docker build -t cloudstrate:latest "$SCRIPT_DIR/.."
    fi
fi

# Deploy using kustomize
echo -e "\n${YELLOW}Deploying Cloudstrate...${NC}"
kubectl apply -k "$SCRIPT_DIR"

# Wait for Neo4j to be ready
echo -e "\n${YELLOW}Waiting for Neo4j to be ready...${NC}"
kubectl wait --for=condition=available deployment/neo4j -n "$NAMESPACE" --timeout=120s || {
    echo -e "${YELLOW}Neo4j is still starting, continuing...${NC}"
}

# Wait for Analyst to be ready
echo -e "\n${YELLOW}Waiting for Analyst to be ready...${NC}"
kubectl wait --for=condition=available deployment/analyst -n "$NAMESPACE" --timeout=120s || {
    echo -e "${YELLOW}Analyst is still starting, continuing...${NC}"
}

# Show status
echo -e "\n${GREEN}=== Deployment Status ===${NC}"
kubectl get all -n "$NAMESPACE"

# Show access information
echo -e "\n${GREEN}=== Access Information ===${NC}"
echo -e "Neo4j Browser:    http://localhost:30474"
echo -e "Neo4j Bolt:       bolt://localhost:30687"
echo -e "Analyst Server:   http://localhost:30501"
echo -e ""
echo -e "Or use port-forwarding:"
echo -e "  kubectl port-forward -n $NAMESPACE svc/neo4j 7474:7474 7687:7687"
echo -e "  kubectl port-forward -n $NAMESPACE svc/analyst 5001:5001"
echo -e ""
echo -e "${GREEN}Neo4j credentials: neo4j / cloudstrate${NC}"
echo -e ""
echo -e "To run CLI commands:"
echo -e "  kubectl run -it --rm cloudstrate-cli -n $NAMESPACE --image=cloudstrate:latest -- scan --help"
