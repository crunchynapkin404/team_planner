#!/bin/bash

# Team Planner Manual Server Setup (No GitHub Auth Required)
# Run this script on your server

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🐳 Team Planner Server Setup (Manual)${NC}"
echo -e "${BLUE}====================================${NC}"

# Create deployment directory
DEPLOY_DIR="/opt/team_planner"
echo -e "${YELLOW}Creating deployment directory: $DEPLOY_DIR${NC}"

sudo mkdir -p "$DEPLOY_DIR"
sudo chown $USER:$USER "$DEPLOY_DIR"
cd "$DEPLOY_DIR"

# Download files directly instead of git clone
echo -e "${YELLOW}Downloading project files...${NC}"

# Create basic structure
mkdir -p frontend compose/local/django .envs/.local

# Download docker-compose file
echo -e "${YELLOW}Downloading docker-compose configuration...${NC}"
curl -sSL https://raw.githubusercontent.com/crunchynapkin404/team_planner/main/docker-compose.portainer-simple.yml -o docker-compose.yml

# Create basic Django requirements (we'll build from base image)
echo -e "${YELLOW}Creating requirements file...${NC}"
cat > requirements.txt << 'EOF'
django==5.1.11
djangorestframework==3.16.0
psycopg==3.2.9
redis==6.3.0
celery==5.5.3
django-environ==0.12.0
django-cors-headers==4.7.0
python-slugify==8.0.4
argon2-cffi==25.1.0
whitenoise==6.9.0
EOF

# Create manage.py
echo -e "${YELLOW}Creating Django management file...${NC}"
cat > manage.py << 'EOF'
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)
EOF

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

# Create simplified docker-compose for manual setup
echo -e "${YELLOW}Creating simplified Docker Compose configuration...${NC}"
cat > docker-compose-simple.yml << 'EOF'
version: '3.8'

volumes:
  postgres_data:
  redis_data:

services:
  web:
    image: python:3.12-slim
    container_name: team_planner_web
    depends_on:
      - postgres
      - redis
    volumes:
      - ./:/app
    working_dir: /app
    environment:
      - DEBUG=true
      - DATABASE_URL=postgres://teamplanner:securepassword123@postgres:5432/team_planner
      - REDIS_URL=redis://redis:6379/0
    ports:
      - '8001:8000'
    command: >
      bash -c "
        echo 'Installing dependencies...' &&
        pip install django djangorestframework psycopg redis celery django-environ django-cors-headers &&
        echo 'Starting Django...' &&
        python -c \"
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'team_planner.settings')
from django.core.wsgi import get_wsgi_application
from django.core.management import execute_from_command_line
from django.conf import settings
if not settings.configured:
    settings.configure(
        DEBUG=True,
        SECRET_KEY='dev-key-not-for-production',
        DATABASES={'default': {'ENGINE': 'django.db.backends.postgresql', 'NAME': 'team_planner', 'USER': 'teamplanner', 'PASSWORD': 'securepassword123', 'HOST': 'postgres', 'PORT': '5432'}},
        INSTALLED_APPS=['django.contrib.admin', 'django.contrib.auth', 'django.contrib.contenttypes', 'django.contrib.sessions', 'django.contrib.messages', 'django.contrib.staticfiles'],
        MIDDLEWARE=['django.middleware.security.SecurityMiddleware', 'django.contrib.sessions.middleware.SessionMiddleware', 'django.middleware.common.CommonMiddleware', 'django.middleware.csrf.CsrfViewMiddleware', 'django.contrib.auth.middleware.AuthenticationMiddleware', 'django.contrib.messages.middleware.MessageMiddleware'],
        ROOT_URLCONF='__main__',
        STATIC_URL='/static/',
        ALLOWED_HOSTS=['*']
    )
django.setup()
from django.http import HttpResponse
from django.urls import path
def hello(request): return HttpResponse('Team Planner API is running! Setup complete.')
urlpatterns = [path('', hello)]
execute_from_command_line(['manage.py', 'runserver', '0.0.0.0:8000'])
\"
      "
    restart: unless-stopped

  postgres:
    image: postgres:15-alpine
    container_name: team_planner_postgres
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_DB=team_planner
      - POSTGRES_USER=teamplanner
      - POSTGRES_PASSWORD=securepassword123
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    container_name: team_planner_redis
    volumes:
      - redis_data:/data
    restart: unless-stopped

  mailpit:
    image: axllent/mailpit:latest
    container_name: team_planner_mailpit
    ports:
      - "8025:8025"
    restart: unless-stopped
EOF

echo -e "${GREEN}✅ Manual server setup complete!${NC}"
echo
echo -e "${BLUE}Next steps:${NC}"
echo -e "${YELLOW}1. In Portainer, create a new stack named 'team-planner'${NC}"
echo -e "${YELLOW}2. Use Web Editor and paste the contents of docker-compose-simple.yml${NC}"
echo -e "${YELLOW}3. Deploy the stack${NC}"
echo
echo -e "${GREEN}After deployment:${NC}"
echo -e "${BLUE}• Test API: http://$(hostname -I | awk '{print $1}'):8001${NC}"
echo -e "${BLUE}• Email: http://$(hostname -I | awk '{print $1}'):8025${NC}"
echo
echo -e "${YELLOW}📁 Project location: $DEPLOY_DIR${NC}"
echo -e "${YELLOW}📁 Docker Compose file: $DEPLOY_DIR/docker-compose-simple.yml${NC}"
EOF
