#!/bin/bash

# Deployment script for langrag application
# Usage: ./deploy.sh
#
# Required environment variables (can be set in .env or exported):
#   DEPLOY_REGISTRY - Docker registry URL (e.g., registry.cn-hangzhou.aliyuncs.com)
#   DEPLOY_IMAGE_NAME - Docker image name (e.g., openz/langrag)
#   DEPLOY_IMAGE_TAG - Docker image tag (e.g., 0.0.1)
#   DEPLOY_REMOTE_HOST - Remote server SSH connection (e.g., root@example.com)
#   DEPLOY_REMOTE_DIR - Remote deployment directory (e.g., /data/projects/langrag)
#   DEPLOY_REMOTE_PORT - Remote service port (e.g., 30006)
#   DEPLOY_REMOTE_IP - Remote server IP address (e.g., 1.2.3.4)

set -e

# Load environment variables from .env if it exists
if [ -f .env ]; then
    export $(grep -v '^#' .env | grep -E '^DEPLOY_' | xargs)
fi

# Configuration - read from environment variables with validation
REGISTRY="${DEPLOY_REGISTRY:-}"
IMAGE_NAME="${DEPLOY_IMAGE_NAME:-}"
IMAGE_TAG="${DEPLOY_IMAGE_TAG:-0.0.2}"
REMOTE_HOST="${DEPLOY_REMOTE_HOST:-}"
DEPLOY_DIR="${DEPLOY_REMOTE_DIR:-}"
REMOTE_PORT="${DEPLOY_REMOTE_PORT:-}"
REMOTE_IP="${DEPLOY_REMOTE_IP:-}"

# Validate required variables
if [ -z "$REGISTRY" ] || [ -z "$IMAGE_NAME" ] || [ -z "$REMOTE_HOST" ] || [ -z "$DEPLOY_DIR" ] || [ -z "$REMOTE_PORT" ] || [ -z "$REMOTE_IP" ]; then
    echo "❌ Missing required deployment configuration!"
    echo ""
    echo "Please set the following environment variables (in .env or export them):"
    echo "  DEPLOY_REGISTRY - Docker registry URL"
    echo "  DEPLOY_IMAGE_NAME - Docker image name"
    echo "  DEPLOY_IMAGE_TAG - Docker image tag (default: 0.0.1)"
    echo "  DEPLOY_REMOTE_HOST - Remote server SSH connection (e.g., user@host)"
    echo "  DEPLOY_REMOTE_DIR - Remote deployment directory"
    echo "  DEPLOY_REMOTE_PORT - Remote service port"
    echo "  DEPLOY_REMOTE_IP - Remote server IP address"
    echo ""
    echo "Example .env entries:"
    echo "  DEPLOY_REGISTRY=registry.example.com"
    echo "  DEPLOY_IMAGE_NAME=namespace/langrag"
    echo "  DEPLOY_IMAGE_TAG=0.0.1"
    echo "  DEPLOY_REMOTE_HOST=user@example.com"
    echo "  DEPLOY_REMOTE_DIR=/data/projects/langrag"
    echo "  DEPLOY_REMOTE_PORT=30006"
    echo "  DEPLOY_REMOTE_IP=1.2.3.4"
    exit 1
fi

FULL_IMAGE="${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}"

echo "=== LangRAG Deployment Script ==="
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ .env file not found! Please create it first."
    exit 1
fi

# Step 0: Build frontend first
echo "Step 0: Building frontend..."
cd frontend
if [ ! -d node_modules ]; then
    echo "Installing frontend dependencies..."
    npm install
fi
echo "Building frontend..."
npm run build
cd ..

# Copy frontend build to backend static (for Docker build context)
echo "Copying frontend build to backend static..."
rm -rf backend/static/*
cp -r frontend/build/* backend/static/ 2>/dev/null || mkdir -p backend/static

# Step 1: Build Docker image for amd64 platform
echo "Step 1: Building Docker image for amd64 platform..."
docker buildx build \
    --platform linux/amd64 \
    --tag ${FULL_IMAGE} \
    --file backend/Dockerfile \
    --load \
    backend/

if [ $? -ne 0 ]; then
    echo "❌ Docker build failed!"
    exit 1
fi

echo "✓ Docker image built successfully"
echo ""

# Step 2: Push image to registry
echo "Step 2: Pushing image to registry..."
docker push ${FULL_IMAGE}

if [ $? -ne 0 ]; then
    echo "❌ Docker push failed!"
    exit 1
fi

echo "✓ Image pushed to registry successfully"
echo ""

# Step 3: Prepare deployment files
echo "Step 3: Preparing deployment files..."
TEMP_DIR=$(mktemp -d)
DEPLOY_TEMP="${TEMP_DIR}/langrag"

mkdir -p ${DEPLOY_TEMP}

# Copy necessary files
cp docker-compose.yml ${DEPLOY_TEMP}/
cp .env ${DEPLOY_TEMP}/.env

# Create deployment archive
cd ${TEMP_DIR}
tar -czf langrag-deploy.tar.gz langrag/
cd - > /dev/null

echo "✓ Deployment files prepared"
echo ""

# Step 4: Deploy to remote server
echo "Step 4: Deploying to remote server..."

# Create remote directory
ssh ${REMOTE_HOST} "mkdir -p ${DEPLOY_DIR}"

# Copy files to remote server
scp ${TEMP_DIR}/langrag-deploy.tar.gz ${REMOTE_HOST}:${DEPLOY_DIR}/

# Extract and setup on remote server
ssh ${REMOTE_HOST} << EOF
set -e
cd ${DEPLOY_DIR}
echo "Extracting deployment files..."
tar -xzf langrag-deploy.tar.gz
mv langrag/* .
rm -rf langrag langrag-deploy.tar.gz

# Create necessary directories
mkdir -p uploads logs
chmod 755 uploads logs

# Remove old image to force pull of new one
echo "Removing old Docker image (if exists)..."
docker rmi ${FULL_IMAGE} 2>/dev/null || true

# Pull latest image
echo "Pulling Docker image..."
docker pull ${FULL_IMAGE}

# Check if docker-compose or docker compose is available
if command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE_CMD="docker-compose"
elif docker compose version &> /dev/null; then
    DOCKER_COMPOSE_CMD="docker compose"
else
    echo "Installing docker-compose..."
    curl -L "https://github.com/docker/compose/releases/download/v2.24.0/docker-compose-\$(uname -s)-\$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
    DOCKER_COMPOSE_CMD="docker-compose"
fi

# Stop existing containers
echo "Stopping existing containers..."
\$DOCKER_COMPOSE_CMD down 2>/dev/null || true

# Start services
echo "Starting services..."
\$DOCKER_COMPOSE_CMD up -d

# Wait for service to be ready
echo "Waiting for service to be ready..."
sleep 10

# Check service status
echo "Checking service status..."
\$DOCKER_COMPOSE_CMD ps

echo ""
echo "=== Deployment Complete ==="
echo "Service URL: http://${REMOTE_IP}:${REMOTE_PORT}"
echo "Health check: http://${REMOTE_IP}:${REMOTE_PORT}/api/health"
EOF

# Cleanup
rm -rf ${TEMP_DIR}

echo ""
echo "✅ Deployment completed successfully!"
echo ""
echo "Service Information:"
echo "  - URL: http://${REMOTE_IP}:${REMOTE_PORT}"
echo "  - Health: http://${REMOTE_IP}:${REMOTE_PORT}/api/health"
echo ""
echo "To check logs: ssh ${REMOTE_HOST} 'cd ${DEPLOY_DIR} && docker compose logs -f'"
echo "To restart: ssh ${REMOTE_HOST} 'cd ${DEPLOY_DIR} && docker compose restart'"
