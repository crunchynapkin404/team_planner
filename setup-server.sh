#!/bin/bash

# Quick Team Planner Setup for Portainer Server
# Run this script on your server to prepare for Portainer deployment

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🐳 Team Planner Server Setup for Portainer${NC}"
echo -e "${BLUE}=========================================${NC}"

# Check if git is installed
if ! command -v git &> /dev/null; then
    echo -e "${RED}Git is not installed. Please install git first.${NC}"
    exit 1
fi

# Check if docker is running
if ! docker info &> /dev/null; then
    echo -e "${RED}Docker is not running or not installed.${NC}"
    exit 1
fi

# Create deployment directory
DEPLOY_DIR="/opt/team_planner"
echo -e "${YELLOW}Creating deployment directory: $DEPLOY_DIR${NC}"

if [ -d "$DEPLOY_DIR" ]; then
    echo -e "${YELLOW}Directory exists. Updating...${NC}"
    cd "$DEPLOY_DIR"
    git pull
else
    echo -e "${YELLOW}Cloning repository...${NC}"
    sudo mkdir -p "$DEPLOY_DIR"
    sudo chown $USER:$USER "$DEPLOY_DIR"
    git clone https://github.com/crunchynapkin404/team_planner.git "$DEPLOY_DIR"
    cd "$DEPLOY_DIR"
fi

# Make scripts executable
chmod +x start-*.sh

# Create environment directory
mkdir -p .envs/.local

# Create environment files
echo -e "${YELLOW}Creating environment configuration...${NC}"

cat > .envs/.local/.django << 'EOF'
# General
USE_DOCKER=true
IPYTHONDIR=/app/.ipython
DEBUG=true

# Database
DATABASE_URL=postgres://teamplanner:securepassword123@postgres:5432/team_planner

# Redis
REDIS_URL=redis://redis:6379/0

# Celery
CELERY_FLOWER_USER=admin
CELERY_FLOWER_PASSWORD=admin123

# Email
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
EOF

cat > .envs/.local/.postgres << 'EOF'
# PostgreSQL
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=team_planner
POSTGRES_USER=teamplanner
POSTGRES_PASSWORD=securepassword123
EOF

echo -e "${GREEN}✅ Server setup complete!${NC}"
echo
echo -e "${BLUE}Next steps:${NC}"
echo -e "${YELLOW}1. Open Portainer: http://$(hostname -I | awk '{print $1}'):9000${NC}"
echo -e "${YELLOW}2. Create a new stack named 'team-planner'${NC}"
echo -e "${YELLOW}3. Use one of these methods:${NC}"
echo
echo -e "${GREEN}Method A - Git Repository (Recommended):${NC}"
echo -e "   Repository URL: https://github.com/crunchynapkin404/team_planner.git"
echo -e "   Compose path: docker-compose.portainer-simple.yml"
echo
echo -e "${GREEN}Method B - Upload compose file:${NC}"
echo -e "   Upload: $DEPLOY_DIR/docker-compose.portainer-simple.yml"
echo
echo -e "${GREEN}Method C - Web editor:${NC}"
echo -e "   Copy contents of docker-compose.portainer-simple.yml"
echo -e "   Update build context paths to: $DEPLOY_DIR"
echo
echo -e "${BLUE}After deployment, access your app at:${NC}"
echo -e "${GREEN}• Frontend: http://$(hostname -I | awk '{print $1}'):3000${NC}"
echo -e "${GREEN}• Backend: http://$(hostname -I | awk '{print $1}'):8000${NC}"
echo -e "${GREEN}• Admin: http://$(hostname -I | awk '{print $1}'):8000/admin/${NC}"
echo -e "${GREEN}• Email: http://$(hostname -I | awk '{print $1}'):8025${NC}"
echo
echo -e "${YELLOW}📁 Project location: $DEPLOY_DIR${NC}"
echo -e "${YELLOW}📖 See PORTAINER_DEPLOYMENT.md for detailed instructions${NC}"
