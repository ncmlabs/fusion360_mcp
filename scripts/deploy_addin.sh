#!/bin/bash
# Deploy FusionMCP add-in to Fusion 360 AddIns folder
# Usage: ./scripts/deploy_addin.sh

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
SOURCE_DIR="$PROJECT_ROOT/FusionAddin"
ADDIN_NAME="FusionMCP"

# Fusion 360 AddIns folder (macOS)
FUSION_ADDINS_DIR="$HOME/Library/Application Support/Autodesk/Autodesk Fusion 360/API/AddIns"
TARGET_DIR="$FUSION_ADDINS_DIR/$ADDIN_NAME"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Deploying FusionMCP Add-in...${NC}"
echo "Source: $SOURCE_DIR"
echo "Target: $TARGET_DIR"
echo ""

# Check if Fusion AddIns folder exists
if [ ! -d "$FUSION_ADDINS_DIR" ]; then
    echo -e "${RED}Error: Fusion 360 AddIns folder not found at:${NC}"
    echo "$FUSION_ADDINS_DIR"
    echo ""
    echo "Make sure Fusion 360 is installed."
    exit 1
fi

# Check if source exists
if [ ! -d "$SOURCE_DIR" ]; then
    echo -e "${RED}Error: Source FusionAddin folder not found at:${NC}"
    echo "$SOURCE_DIR"
    exit 1
fi

# Remove existing add-in if present
if [ -d "$TARGET_DIR" ]; then
    echo -e "${YELLOW}Removing existing add-in...${NC}"
    rm -rf "$TARGET_DIR"
fi

# Create target directory
mkdir -p "$TARGET_DIR"

# Copy add-in files
echo "Copying add-in files..."

# Copy Python files and manifest
cp "$SOURCE_DIR/FusionMCP.py" "$TARGET_DIR/"
cp "$SOURCE_DIR/FusionMCP.manifest" "$TARGET_DIR/"

# Copy core module
mkdir -p "$TARGET_DIR/core"
cp "$SOURCE_DIR/core/"*.py "$TARGET_DIR/core/"

# Copy handlers module
mkdir -p "$TARGET_DIR/handlers"
cp "$SOURCE_DIR/handlers/"*.py "$TARGET_DIR/handlers/"

# Copy serializers module
mkdir -p "$TARGET_DIR/serializers"
cp "$SOURCE_DIR/serializers/"*.py "$TARGET_DIR/serializers/"

# Copy shared module (needed for exceptions)
mkdir -p "$TARGET_DIR/shared"
cp "$PROJECT_ROOT/shared/"*.py "$TARGET_DIR/shared/"

echo ""
echo -e "${GREEN}Add-in deployed successfully!${NC}"
echo ""
echo "Next steps:"
echo "1. Open Fusion 360"
echo "2. Go to Utilities → Add-Ins (or press Shift+S)"
echo "3. Find 'FusionMCP' in the Add-Ins tab"
echo "4. Click 'Run' to start the add-in"
echo ""
echo "The add-in will start an HTTP server on http://localhost:5001"
