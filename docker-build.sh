#!/bin/bash

# Script to build Docker image for the project

# Set error handling
set -e

# Default values
DEFAULT_PROJECT_NAME="python-uv-boilerplate"
DEFAULT_VERSION="0.1"

# Prompt for namespace
read -p "Enter Docker namespace (optional): " NAMESPACE
NAMESPACE=${NAMESPACE:+$NAMESPACE/}

# Prompt for Docker image name
read -p "Enter Docker image name (default: $DEFAULT_PROJECT_NAME): " IMAGE_NAME
IMAGE_NAME=${IMAGE_NAME:-$DEFAULT_PROJECT_NAME}

# Prompt for version
read -p "Enter version (default: $DEFAULT_VERSION): " VERSION
VERSION=${VERSION:-$DEFAULT_VERSION}

echo "Starting Docker build process..."

# Run the Docker build command
DOCKER_BUILDKIT=1 docker build -f Dockerfile --target runtime -t "${NAMESPACE}${IMAGE_NAME}:${VERSION}" .

# Check if the build was successful
if [ $? -eq 0 ]; then
    echo "Docker image build successful!"
    echo "Image: ${NAMESPACE}${IMAGE_NAME}:${VERSION}"
else
    echo "Docker image build failed. Please check the output for errors."
    exit 1
fi
