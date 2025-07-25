#!/bin/bash

# Package TestPilot for Customer Distribution
# This script creates a clean distribution package

set -e

DIST_NAME="testpilot_dist"
BUILD_DIR="dist/testPilot"

echo "Packaging TestPilot for customer distribution..."

# Check if build exists
if [ ! -d "$BUILD_DIR" ]; then
    echo "Error: Build directory not found. Please run ./build_with_spec.sh first"
    exit 1
fi

# Create temporary packaging directory
TEMP_DIR=$(mktemp -d)
PACKAGE_DIR="$TEMP_DIR/$DIST_NAME"
mkdir -p "$PACKAGE_DIR"

echo "Copying distribution files..."

# Copy the built application
cp -r "$BUILD_DIR"/* "$PACKAGE_DIR/"

# Copy configuration directory (with example config)
mkdir -p "$PACKAGE_DIR/config"
cp config/hosts.json "$PACKAGE_DIR/config/hosts.json.example"
if [ -f "config/resource_map.json" ]; then
    cp config/resource_map.json "$PACKAGE_DIR/config/"
fi

# Copy deployment documentation
cp DEPLOYMENT_GUIDE.md "$PACKAGE_DIR/"
cp setup_testpilot.sh "$PACKAGE_DIR/"

# Create a README for the distribution
cat > "$PACKAGE_DIR/README.txt" << 'EOF'
TestPilot Distribution Package
==============================

This package contains:
- testPilot: The main executable
- _internal/: Required dependencies (do not modify)
- config/: Configuration directory
  - hosts.json.example: Example configuration file
- setup_testpilot.sh: Interactive setup assistant
- DEPLOYMENT_GUIDE.md: Comprehensive deployment documentation

To get started:
1. Run: ./setup_testpilot.sh
2. Or see DEPLOYMENT_GUIDE.md for manual setup

For detailed instructions, see DEPLOYMENT_GUIDE.md
EOF

# Create version file
cat > "$PACKAGE_DIR/VERSION" << EOF
TestPilot Version Information
Build Date: $(date -u)
EOF

# Get the original directory before changing directories
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Create the archive
echo "Creating distribution archive..."
cd "$TEMP_DIR"
tar -czf "$DIST_NAME.tar.gz" "$DIST_NAME"

# Copy to script directory
cp "$DIST_NAME.tar.gz" "$SCRIPT_DIR/"

# Cleanup
cd "$SCRIPT_DIR"
rm -rf "$TEMP_DIR"

echo "✅ Distribution package created: $DIST_NAME.tar.gz"
echo ""
echo "Package contents:"
echo "- TestPilot executable and dependencies"
echo "- Setup assistant (setup_testpilot.sh)"
echo "- Documentation (DEPLOYMENT_GUIDE.md)"
echo "- Example configuration"
echo ""
echo "To test the package:"
echo "1. tar -xzf $DIST_NAME.tar.gz"
echo "2. cd $DIST_NAME"
echo "3. ./setup_testpilot.sh"
