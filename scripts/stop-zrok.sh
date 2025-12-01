#!/bin/bash

# Stop Zrok Tunnel and Backend for ESCO Skill Extractor

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Stopping ESCO Skill Extractor services...${NC}"

# Stop zrok tunnel
if pgrep -f "zrok share reserved escobackend" > /dev/null; then
    echo -e "${YELLOW}Stopping zrok tunnel...${NC}"
    pkill -f "zrok share reserved escobackend"
    echo -e "${GREEN}✅ Zrok tunnel stopped${NC}"
else
    echo -e "${YELLOW}No zrok tunnel running${NC}"
fi

# Stop backend if PID file exists
if [ -f "backend.pid" ]; then
    BACKEND_PID=$(cat backend.pid)
    if kill -0 $BACKEND_PID 2>/dev/null; then
        echo -e "${YELLOW}Stopping backend (PID: $BACKEND_PID)...${NC}"
        kill $BACKEND_PID
        echo -e "${GREEN}✅ Backend stopped${NC}"
    else
        echo -e "${YELLOW}Backend PID $BACKEND_PID not running${NC}"
    fi
    rm -f backend.pid
else
    # Fallback: kill any ESCO backend process
    if pgrep -f "esco_skill_extractor" > /dev/null; then
        echo -e "${YELLOW}Stopping ESCO backend processes...${NC}"
        pkill -f "esco_skill_extractor"
        echo -e "${GREEN}✅ Backend processes stopped${NC}"
    else
        echo -e "${YELLOW}No backend processes running${NC}"
    fi
fi

# Clean up log files (optional)
echo -e "${BLUE}Cleaning up log files...${NC}"
rm -f zrok.log backend.log

echo -e "${GREEN}✅ All services stopped successfully${NC}"