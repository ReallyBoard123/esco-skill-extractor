#!/bin/bash

# Zrok Regular Tunnel Script for ESCO Skill Extractor Backend

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Starting Zrok Tunnel for ESCO Skill Extractor Backend...${NC}"

# Check if backend is running, start if not
if ! curl -s http://localhost:9000/ > /dev/null; then
    echo -e "${YELLOW}Backend not running on localhost:9000${NC}"
    echo -e "${BLUE}Starting backend automatically...${NC}"
    
    cd /home/pll/git/esco-skill-extractor/api
    source .venv/bin/activate
    
    # Start backend in background
    nohup python -m esco_skill_extractor --port 9000 > backend.log 2>&1 &
    BACKEND_PID=$!
    echo $BACKEND_PID > backend.pid
    
    echo -e "${YELLOW}Waiting for backend to start (this may take a few minutes for BGE-M3 model loading)...${NC}"
    
    # Wait for backend to be ready (up to 5 minutes for model loading)
    for i in {1..150}; do
        if curl -s http://localhost:9000/ > /dev/null 2>&1; then
            echo -e "${GREEN}Backend is ready!${NC}"
            break
        fi
        if [ $i -eq 150 ]; then
            echo -e "${RED}Backend failed to start after 5 minutes${NC}"
            echo -e "${YELLOW}Check backend.log for details${NC}"
            exit 1
        fi
        sleep 2
        if [ $((i % 15)) -eq 0 ]; then
            echo -e "${BLUE}Still waiting... (${i}/150 attempts)${NC}"
        fi
    done
else
    echo -e "${GREEN}Backend is already running on localhost:9000${NC}"
fi

# Kill existing zrok tunnels for this project
if pgrep -f "zrok share public http://localhost:9000" > /dev/null; then
    echo -e "${YELLOW}Killing existing tunnel...${NC}"
    pkill -f "zrok share public http://localhost:9000" || true
    sleep 2
fi

# Start zrok tunnel and capture URL
echo -e "${BLUE}Creating zrok tunnel (this may take a few seconds)...${NC}"

# Check if zrok is configured
if ! zrok status > /dev/null 2>&1; then
    echo -e "${RED}Zrok not configured${NC}"
    echo -e "${YELLOW}Configure zrok first:${NC}"
    echo "   zrok enable <your-token>"
    exit 1
fi

# Start regular tunnel (since reserved doesn't work due to account limits)
echo -e "${BLUE}Starting regular tunnel...${NC}"
nohup zrok share public http://localhost:9000 --headless > zrok.log 2>&1 &
TUNNEL_PID=$!

# Wait for tunnel to initialize and extract URL
echo -e "${YELLOW}Waiting for tunnel to initialize...${NC}"
sleep 8

# Extract tunnel URL from logs
TUNNEL_URL=""
for i in {1..30}; do
    if [ -f "zrok.log" ]; then
        TUNNEL_URL=$(grep -o 'https://[a-z0-9]*\.share\.zrok\.io' zrok.log | head -1)
        if [ -n "$TUNNEL_URL" ]; then
            break
        fi
    fi
    sleep 1
done

if [ -z "$TUNNEL_URL" ]; then
    echo -e "${RED}Failed to extract tunnel URL from logs${NC}"
    echo -e "${YELLOW}Check zrok.log for details${NC}"
    exit 1
fi

echo -e "${GREEN}Zrok tunnel created successfully!${NC}"
echo -e "${BLUE}Public URL: ${GREEN}$TUNNEL_URL${NC}"
echo -e "${YELLOW}URL saved to zrok_url.txt${NC}"

# Save URL to file
echo "$TUNNEL_URL" > zrok_url.txt

# Test tunnel
echo -e "${BLUE}Testing zrok tunnel...${NC}"
sleep 3
if curl -s "$TUNNEL_URL/" > /dev/null 2>&1; then
    echo -e "${GREEN}Zrok tunnel is working perfectly!${NC}"
    echo -e "${GREEN}Ready for ESCO skill extraction API calls${NC}"
else
    echo -e "${YELLOW}Tunnel test inconclusive - should still work${NC}"
fi

echo ""
echo -e "${BLUE}Tunnel Info:${NC}"
echo -e "   Local:  ${YELLOW}http://localhost:9000${NC}"
echo -e "   Public: ${GREEN}$TUNNEL_URL${NC}"
echo -e "   PID:    ${YELLOW}$TUNNEL_PID${NC}"
echo -e "   Type:   ${GREEN}Zrok Regular (Temporary URL)${NC}"
echo ""
echo -e "${YELLOW}For Vercel Deployment:${NC}"
echo -e "   Add this environment variable:"
echo -e "   ${GREEN}NEXT_PUBLIC_API_URL=$TUNNEL_URL${NC}"
echo ""
echo -e "${YELLOW}For Local Development:${NC}"
echo -e "   Update app/.env.local:"
echo -e "   ${GREEN}NEXT_PUBLIC_API_URL=$TUNNEL_URL${NC}"
echo ""
echo -e "${BLUE}Available Endpoints:${NC}"
echo -e "   ${GREEN}$TUNNEL_URL/extract-skills${NC}"
echo -e "   ${GREEN}$TUNNEL_URL/extract-occupations${NC}"
echo ""
echo -e "${YELLOW}Note: Regular tunnels have temporary URLs that change on restart${NC}"
echo -e "${BLUE}For production, consider upgrading zrok account for reserved shares${NC}"
echo ""
echo -e "   - To stop: ${RED}kill $TUNNEL_PID${NC} or ${RED}./scripts/stop-zrok.sh${NC}"
echo ""
echo -e "${BLUE}Monitor logs: ${YELLOW}tail -f zrok.log backend.log${NC}"

# Keep script running to show tunnel status
trap "echo -e '\n${RED}Stopping zrok tunnel...${NC}'; kill $TUNNEL_PID 2>/dev/null || true; exit 0" INT TERM

echo -e "${GREEN}Zrok tunnel is running... Press Ctrl+C to stop${NC}"
wait $TUNNEL_PID