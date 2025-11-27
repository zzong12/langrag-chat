#!/bin/bash

# Deployment script for langrag application
# Usage: ./deploy.sh

set -e

# Configuration
REGISTRY="registry.cn-hangzhou.aliyuncs.com"
IMAGE_NAME="openz/langrag"
IMAGE_TAG="0.0.1"
FULL_IMAGE="${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}"
REMOTE_HOST="root@47.92.139.154"
DEPLOY_DIR="/data/projects/langrag"
REMOTE_PORT="30006"

echo "=== LangRAG Deployment Script ==="
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ .env file not found! Please create it first."
    exit 1
fi

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
echo "Service URL: http://47.92.139.154:${REMOTE_PORT}"
echo "Health check: http://47.92.139.154:${REMOTE_PORT}/api/health"
EOF

# Cleanup
rm -rf ${TEMP_DIR}

echo ""
echo "✅ Deployment completed successfully!"
echo ""
echo "Service Information:"
echo "  - URL: http://47.92.139.154:${REMOTE_PORT}"
echo "  - Health: http://47.92.139.154:${REMOTE_PORT}/api/health"
echo ""
echo "To check logs: ssh ${REMOTE_HOST} 'cd ${DEPLOY_DIR} && docker-compose logs -f'"
echo "To restart: ssh ${REMOTE_HOST} 'cd ${DEPLOY_DIR} && docker-compose restart'"
