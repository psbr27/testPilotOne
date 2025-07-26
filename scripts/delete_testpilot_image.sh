#!/bin/bash

# Script to delete testpilot-jenkins Docker container and image
# This script handles both running and stopped containers

set -e  # Exit on any error

echo "🗑️  Starting testpilot-jenkins cleanup..."

# Function to check if container exists
container_exists() {
    docker ps -a --format "table {{.Names}}" | grep -q "^testpilot-jenkins-pod$"
}

# Function to check if image exists
image_exists() {
    docker images --format "table {{.Repository}}:{{.Tag}}" | grep -q "^testpilot-jenkins:1.0.0$"
}

# Stop and remove container if it exists
if container_exists; then
    echo "📦 Found testpilot-jenkins-pod container"

    # Check if container is running
    if docker ps --format "table {{.Names}}" | grep -q "^testpilot-jenkins-pod$"; then
        echo "⏹️  Stopping running container..."
        docker stop testpilot-jenkins-pod
    fi

    echo "🗑️  Removing container..."
    docker rm testpilot-jenkins-pod
    echo "✅ Container removed successfully"
else
    echo "ℹ️  No testpilot-jenkins-pod container found"
fi

# Remove image if it exists
if image_exists; then
    echo "🖼️  Found testpilot-jenkins:1.0.0 image"
    echo "🗑️  Removing image..."
    docker rmi testpilot-jenkins:1.0.0
    echo "✅ Image removed successfully"
else
    echo "ℹ️  No testpilot-jenkins:1.0.0 image found"
fi

# Clean up any dangling images
echo "🧹 Cleaning up dangling images..."
docker image prune -f > /dev/null 2>&1 || true

echo ""
echo "🎉 Cleanup completed!"
echo ""
echo "📊 Current Docker state:"
echo "Images:"
docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}"
echo ""
echo "Containers:"
docker ps -a --format "table {{.Names}}\t{{.Image}}\t{{.Status}}"
