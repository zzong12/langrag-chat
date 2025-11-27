#!/bin/bash

# Build script for RAG Chat Application

echo "Building RAG Chat Application..."

# Build frontend
echo "Building frontend..."
cd frontend
npm install
npm run build

# Copy build to backend static
echo "Copying frontend build to backend static directory..."
rm -rf ../backend/static/*
cp -r build/* ../backend/static/

echo "Build complete! Frontend files are in backend/static/"
echo "You can now run the backend server."

