#!/bin/bash

# Test script for deployed service
# Usage: ./test_deployment.sh

set -e

REMOTE_HOST="47.92.139.154"
REMOTE_PORT="30006"
BASE_URL="http://${REMOTE_HOST}:${REMOTE_PORT}"

echo "=== Testing LangRAG Deployment ==="
echo ""

# Test 1: Health check
echo "Test 1: Health Check"
echo "GET ${BASE_URL}/api/health"
HEALTH_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" ${BASE_URL}/api/health)
HTTP_CODE=$(echo "$HEALTH_RESPONSE" | grep "HTTP_CODE" | cut -d: -f2)
BODY=$(echo "$HEALTH_RESPONSE" | sed '/HTTP_CODE/d')

if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ Health check passed (HTTP $HTTP_CODE)"
    echo "$BODY" | python3 -m json.tool 2>/dev/null || echo "$BODY"
else
    echo "❌ Health check failed (HTTP $HTTP_CODE)"
    echo "$BODY"
    exit 1
fi
echo ""

# Test 2: Root endpoint
echo "Test 2: Root Endpoint"
echo "GET ${BASE_URL}/"
ROOT_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" ${BASE_URL}/)
HTTP_CODE=$(echo "$ROOT_RESPONSE" | grep "HTTP_CODE" | cut -d: -f2)

if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ Root endpoint accessible (HTTP $HTTP_CODE)"
else
    echo "⚠️  Root endpoint returned HTTP $HTTP_CODE"
fi
echo ""

# Test 3: Documents API
echo "Test 3: Documents API"
echo "GET ${BASE_URL}/api/documents"
DOCS_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" ${BASE_URL}/api/documents)
HTTP_CODE=$(echo "$DOCS_RESPONSE" | grep "HTTP_CODE" | cut -d: -f2)
BODY=$(echo "$DOCS_RESPONSE" | sed '/HTTP_CODE/d')

if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ Documents API accessible (HTTP $HTTP_CODE)"
    echo "$BODY" | python3 -m json.tool 2>/dev/null || echo "$BODY"
else
    echo "⚠️  Documents API returned HTTP $HTTP_CODE"
    echo "$BODY"
fi
echo ""

# Test 4: API Documentation
echo "Test 4: API Documentation"
echo "GET ${BASE_URL}/docs"
DOCS_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" ${BASE_URL}/docs)
HTTP_CODE=$(echo "$DOCS_RESPONSE" | grep "HTTP_CODE" | cut -d: -f2)

if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ API documentation accessible (HTTP $HTTP_CODE)"
else
    echo "⚠️  API documentation returned HTTP $HTTP_CODE"
fi
echo ""

echo "=== All Tests Completed ==="
echo ""
echo "Service is accessible at: ${BASE_URL}"

