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

# Load Postgres environment variables only when using Docker
if [ -f ".envs/.local/.postgres" ]; then
    if [ "${USE_DOCKER}" = "yes" ]; then
        echo "Loading Postgres environment variables (Docker)..."
        export $(cat .envs/.local/.postgres | grep -v '^#' | xargs)
    else
        echo "Skipping Postgres env (USE_DOCKER=${USE_DOCKER:-no})"
    fi
fi

# Apply pending migrations (safe to run repeatedly in dev)
echo "Applying database migrations (if any)..."
python manage.py migrate --noinput || true

# Start Django server on port 8000 (bind to all interfaces)
echo "Starting Django server on port 8000..."
python manage.py runserver 0.0.0.0:8000
