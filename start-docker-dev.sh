#!/bin/bash

# Team Planner Docker Development Setup Script
# This script sets up the development environment using Docker

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Setting up Team Planner Docker Development Environment${NC}"
echo -e "${BLUE}====================================================${NC}"

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
    echo -e "${YELLOW}Environment files not found. Creating default ones...${NC}"
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

    echo -e "${GREEN}Environment files created successfully!${NC}"
fi

echo -e "${GREEN}Building and starting Docker containers...${NC}"

# Stop any existing containers
docker-compose -f docker-compose.local.yml down

# Build and start the containers
docker-compose -f docker-compose.local.yml up --build -d

# Wait for services to start
echo -e "${YELLOW}Waiting for services to start...${NC}"
sleep 10

# Run migrations
echo -e "${GREEN}Running database migrations...${NC}"
docker-compose -f docker-compose.local.yml exec django python manage.py migrate

# Create superuser if needed
echo -e "${BLUE}Setup complete!${NC}"
echo -e "${GREEN}Services running:${NC}"
echo -e "${BLUE}Django Backend: http://localhost:8000${NC}"
echo -e "${BLUE}Django Admin: http://localhost:8000/admin/${NC}"
echo -e "${BLUE}API Documentation: http://localhost:8000/api/docs/${NC}"
echo -e "${BLUE}Mailpit (Email): http://localhost:8025${NC}"
echo -e "${BLUE}Flower (Celery): http://localhost:5555${NC}"
echo -e "${YELLOW}Note: Frontend needs to be configured separately for external access${NC}"

echo -e "${GREEN}To stop containers: docker-compose -f docker-compose.local.yml down${NC}"
echo -e "${GREEN}To view logs: docker-compose -f docker-compose.local.yml logs -f${NC}"
