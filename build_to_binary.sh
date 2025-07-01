#!/bin/bash
# Build script to generate a standalone testPilot binary using pyinstaller
# Usage: bash build_to_binary.sh

set -e

# Clean previous builds
echo "[INFO] Cleaning previous build artifacts..."
rm -rf dist build *.spec

# Detect entry point
ENTRY_POINT="test_pilot.py"

# Data files (payloads, config, etc.) are NOT bundled in the binary.
# Users should distribute the config and payloads folders alongside the binary.

# Build with PyInstaller
# --onedir: bundle into a directory with binary and all required libraries
# --name: set output binary name
# --clean: clean PyInstaller cache and remove temporary files before building
# --hidden-import: ensure all dynamic imports are included (add more as needed)

pyinstaller --onedir --name testPilot --clean \
    --hidden-import=pandas \
    --hidden-import=tabulate \
    --hidden-import=paramiko \
    --hidden-import=openpyxl \
    --hidden-import=json \
    --hidden-import=re \
    --hidden-import=logger \
    --hidden-import=validation_engine \
    --hidden-import=response_parser \
    --hidden-import=test_pilot_core \
    --hidden-import=excel_parser \
    --hidden-import=ssh_connector \
    --hidden-import=dry_run \
    --hidden-import=console_table_fmt \
    --hidden-import=log_analyzer \
    --hidden-import=table_demo \
    --hidden-import=test_result \
    --hidden-import=parse_instant_utils \
    --hidden-import=parse_utils \
    --hidden-import=curl_builder \
    --hidden-import=deepdiff \
    $ENTRY_POINT

# Final package will be in dist/testPilot/ (Linux/Mac) or dist/testPilot/ (Windows)
echo "[SUCCESS] Build complete. Find your binary and libraries in the dist/testPilot/ directory."
