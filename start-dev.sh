#!/bin/bash

# Team Planner Development Server
# This script starts both Django backend and React frontend in development mode

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Starting Team Planner Development Environment${NC}"
echo -e "${BLUE}============================================${NC}"

# Function to cleanup background processes
cleanup() {
    echo -e "\n${YELLOW}Stopping development servers...${NC}"
    kill $DJANGO_PID $REACT_PID 2>/dev/null
    exit 0
}

# Set up signal handler
trap cleanup SIGINT SIGTERM

# Start Django backend
echo -e "${GREEN}Starting Django backend...${NC}"
cd "$(dirname "$0")"

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    echo -e "${YELLOW}Activating virtual environment...${NC}"
    source .venv/bin/activate
fi

# Load environment variables
if [ -f ".envs/.local/.django" ]; then
    echo -e "${YELLOW}Loading Django environment variables...${NC}"
    export $(cat .envs/.local/.django | grep -v '^#' | xargs)
fi

python manage.py runserver 8000 &
DJANGO_PID=$!

# Give Django a moment to start
sleep 3

# Start React frontend
echo -e "${GREEN}Starting React frontend...${NC}"
cd frontend
npm run dev &
REACT_PID=$!

echo -e "${GREEN}Development servers started!${NC}"
echo -e "${BLUE}Django backend: http://localhost:8000${NC}"
echo -e "${BLUE}React frontend: http://localhost:3000${NC}"
echo -e "${BLUE}API documentation: http://localhost:8000/api/docs/${NC}"
echo -e "${YELLOW}Press Ctrl+C to stop both servers${NC}"

# Wait for background processes
wait $DJANGO_PID $REACT_PID
