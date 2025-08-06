#!/bin/bash

# Script to start Django backend on a consistent port (8000)
# This ensures the frontend always knows where to find the backend

# Kill any existing Django processes on port 8000
echo "Stopping any existing Django servers on port 8000..."
pkill -f "manage.py runserver" || true
lsof -ti:8000 | xargs kill -9 2>/dev/null || true

# Wait a moment for processes to terminate
sleep 2

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    echo "Activating virtual environment..."
    source .venv/bin/activate
fi

# Load environment variables
if [ -f ".envs/.local/.django" ]; then
    echo "Loading Django environment variables..."
    export $(cat .envs/.local/.django | grep -v '^#' | xargs)
fi

if [ -f ".envs/.local/.postgres" ]; then
    echo "Loading Postgres environment variables..."
    export $(cat .envs/.local/.postgres | grep -v '^#' | xargs)
fi

# Start Django server on port 8000
echo "Starting Django server on port 8000..."
python manage.py runserver 8000
