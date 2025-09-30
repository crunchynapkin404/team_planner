#!/bin/bash

# Team Planner Full-Stack Docker Development Setup
# This script sets up both backend and frontend in Docker

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Setting up Team Planner Full-Stack Docker Environment${NC}"
echo -e "${BLUE}===================================================${NC}"

# Function to cleanup background processes
cleanup() {
    echo -e "\n${YELLOW}Stopping Docker containers...${NC}"
    docker-compose -f docker-compose.fullstack.yml down
    exit 0
}

# Set up signal handler
trap cleanup SIGINT SIGTERM

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Docker is not installed. Please install Docker first.${NC}"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo -e "${RED}Docker Compose is not installed. Please install Docker Compose first.${NC}"
    exit 1
fi

# Create environment files if they don't exist
if [ ! -f ".envs/.local/.django" ]; then
    echo -e "${YELLOW}Creating Docker environment files...${NC}"
    mkdir -p .envs/.local
    
    # Create Django environment file
    cat > .envs/.local/.django << 'EOF'
# General
# ------------------------------------------------------------------------------
USE_DOCKER=true
IPYTHONDIR=/app/.ipython
DEBUG=True

# Database
# ------------------------------------------------------------------------------
DATABASE_URL=postgres://debug:debug@postgres:5432/team_planner

# Redis
# ------------------------------------------------------------------------------
REDIS_URL=redis://redis:6379/0

# Celery
# ------------------------------------------------------------------------------
CELERY_FLOWER_USER=debug
CELERY_FLOWER_PASSWORD=debug

# Email
# ------------------------------------------------------------------------------
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
EOF

    # Create Postgres environment file
    cat > .envs/.local/.postgres << 'EOF'
# PostgreSQL
# ------------------------------------------------------------------------------
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=team_planner
POSTGRES_USER=debug
POSTGRES_PASSWORD=debug
EOF

    echo -e "${GREEN}Environment files created!${NC}"
fi

echo -e "${GREEN}Building and starting all containers...${NC}"

# Stop any existing containers
docker-compose -f docker-compose.fullstack.yml down

# Build and start the containers
docker-compose -f docker-compose.fullstack.yml up --build -d

# Wait for services to start
echo -e "${YELLOW}Waiting for services to initialize...${NC}"
sleep 15

# Run migrations
echo -e "${GREEN}Running database migrations...${NC}"
docker-compose -f docker-compose.fullstack.yml exec django python manage.py migrate

echo -e "${BLUE}✅ Full-Stack Docker Environment Ready!${NC}"
echo -e "${GREEN}Services available at:${NC}"
echo -e "${BLUE}🌐 React Frontend: http://localhost:3000${NC}"
echo -e "${BLUE}🐍 Django Backend: http://localhost:8000${NC}"
echo -e "${BLUE}👤 Django Admin: http://localhost:8000/admin/${NC}"
echo -e "${BLUE}📚 API Documentation: http://localhost:8000/api/docs/${NC}"
echo -e "${BLUE}📧 Mailpit (Email): http://localhost:8025${NC}"
echo -e "${BLUE}🌺 Flower (Celery): http://localhost:5555${NC}"

echo -e "\n${YELLOW}🔧 Development Info:${NC}"
echo -e "${BLUE}• Both frontend and backend support hot-reloading${NC}"
echo -e "${BLUE}• Edit files normally - changes will reflect immediately${NC}"
echo -e "${BLUE}• Database data persists between restarts${NC}"
echo -e "${BLUE}• Press Ctrl+C to stop all containers${NC}"

echo -e "\n${GREEN}🚀 Ready for development! Start editing your code.${NC}"

# Show logs
echo -e "\n${YELLOW}Showing container logs (press Ctrl+C to stop):${NC}"
docker-compose -f docker-compose.fullstack.yml logs -f
