#!/bin/bash

# Zrok Reserved Share Management Script for ESCO Skill Extractor

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

RESERVED_NAME="escobackend"
RESERVED_URL="https://${RESERVED_NAME}.share.zrok.io"

show_help() {
    echo -e "${BLUE}🔧 Zrok Reserved Share Management for ESCO Skill Extractor${NC}"
    echo -e "${BLUE}==========================================================${NC}"
    echo ""
    echo "Commands:"
    echo "  create    - Create new reserved share"
    echo "  status    - Check reserved share status"
    echo "  release   - Delete reserved share"
    echo "  info      - Show reserved share info"
    echo ""
    echo "Reserved Name: ${GREEN}$RESERVED_NAME${NC}"
    echo "Reserved URL:  ${GREEN}$RESERVED_URL${NC}"
}

create_reserved() {
    echo -e "${BLUE}📝 Creating reserved share: ${GREEN}$RESERVED_NAME${NC}"
    
    if zrok overview | grep -q "$RESERVED_NAME"; then
        echo -e "${YELLOW}⚠️  Reserved share '$RESERVED_NAME' already exists${NC}"
        return 0
    fi
    
    echo -e "${BLUE}🔧 Creating reserved share...${NC}"
    zrok reserve public http://localhost:9000 --unique-name "$RESERVED_NAME"
    echo -e "${GREEN}✅ Reserved share created successfully!${NC}"
    echo -e "${GREEN}🌐 URL: $RESERVED_URL${NC}"
}

check_status() {
    echo -e "${BLUE}📊 Reserved Share Status${NC}"
    echo -e "${BLUE}======================${NC}"
    
    if zrok overview | grep -q "$RESERVED_NAME"; then
        echo -e "${GREEN}✅ Reserved share exists: $RESERVED_NAME${NC}"
        echo -e "${GREEN}🌐 URL: $RESERVED_URL${NC}"
        
        # Check if tunnel is running
        if pgrep -f "zrok share reserved $RESERVED_NAME" > /dev/null; then
            echo -e "${GREEN}✅ Tunnel is running${NC}"
        else
            echo -e "${YELLOW}⚠️  Tunnel is not running${NC}"
            echo -e "${BLUE}💡 Start with: ./scripts/start-zrok.sh${NC}"
        fi
    else
        echo -e "${RED}❌ Reserved share does not exist${NC}"
        echo -e "${BLUE}💡 Create with: $0 create${NC}"
    fi
}

release_reserved() {
    echo -e "${YELLOW}⚠️  Releasing reserved share: $RESERVED_NAME${NC}"
    echo -e "${YELLOW}This will delete the persistent URL${NC}"
    read -p "Are you sure? (y/N): " confirm
    
    if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
        echo -e "${BLUE}🗑️  Releasing reserved share...${NC}"
        zrok release "$RESERVED_NAME"
        echo -e "${GREEN}✅ Reserved share released${NC}"
    else
        echo -e "${BLUE}ℹ️  Cancelled${NC}"
    fi
}

show_info() {
    echo -e "${BLUE}📋 Reserved Share Information${NC}"
    echo -e "${BLUE}============================${NC}"
    echo ""
    echo -e "Name:           ${GREEN}$RESERVED_NAME${NC}"
    echo -e "URL:            ${GREEN}$RESERVED_URL${NC}"
    echo -e "Local Backend:  ${YELLOW}http://localhost:9000${NC}"
    echo ""
    echo -e "${BLUE}🔧 Management Commands:${NC}"
    echo -e "  Start tunnel:   ${YELLOW}./scripts/start-zrok.sh${NC}"
    echo -e "  Stop tunnel:    ${YELLOW}./scripts/stop-zrok.sh${NC}"
    echo -e "  Check status:   ${YELLOW}$0 status${NC}"
    echo ""
    echo -e "${BLUE}💡 Benefits of Reserved Shares:${NC}"
    echo -e "  ✅ Persistent URL across restarts"
    echo -e "  ✅ No URL changes for frontend config"
    echo -e "  ✅ Production-ready deployment"
    echo -e "  ✅ Perfect for Vercel deployment"
}

# Main command handling
case "${1:-help}" in
    create)
        create_reserved
        ;;
    status)
        check_status
        ;;
    release)
        release_reserved
        ;;
    info)
        show_info
        ;;
    help|*)
        show_help
        ;;
esac