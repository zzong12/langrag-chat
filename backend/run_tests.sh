#!/bin/bash

# Run all tests
echo "Running RAG Chat Application Tests..."
echo "======================================"
echo ""

cd "$(dirname "$0")"

# Run pytest with verbose output
python -m pytest tests/ -v --tb=short

echo ""
echo "Tests completed!"

