#!/bin/bash

# Build script for OP-Z Sample Manager

set -e

echo "Building OP-Z Sample Manager..."

# Clean previous builds
rm -rf build dist

# Run PyInstaller
pyinstaller opz-sample-manager.spec

echo ""
echo "Build complete!"
echo "App bundle: dist/OP-Z Sample Manager.app"
