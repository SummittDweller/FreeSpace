#!/bin/bash

# run.sh - Build .venv if needed and launch the FreeSpace app

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}FreeSpace App Launcher${NC}"

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo -e "${GREEN}Creating virtual environment...${NC}"
    python3 -m venv .venv
fi

# Activate virtual environment
echo -e "${GREEN}Activating virtual environment...${NC}"
source .venv/bin/activate

# Install/upgrade dependencies
echo -e "${GREEN}Installing dependencies...${NC}"
pip install --upgrade pip
pip install -r requirements.txt

# Launch the app
echo -e "${GREEN}Launching FreeSpace app...${NC}"
python main.py
