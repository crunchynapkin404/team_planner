# 🐳 Docker Deployment Overview

This project includes several Docker deployment options:

## 📁 Available Docker Configurations

### Core Files (Keep These)
- **`docker-compose.local.yml`** - Original local development (from project template)
- **`docker-compose.production.yml`** - Production deployment (from project template)  
- **`docker-compose.docs.yml`** - Documentation server (from project template)
- **`docker-compose.portainer-final.yml`** - ✅ **Recommended for Portainer deployment**
- **`docker-compose.fullstack.yml`** - Full-stack development with frontend included

## 🚀 Quick Deployment Guide

### For Portainer Users (Recommended):
1. Use **`docker-compose.portainer-final.yml`**
2. Or run setup script: `curl -sSL https://raw.githubusercontent.com/crunchynapkin404/team_planner/main/setup-server-manual.sh | bash`

### For Local Development:
- **Full-stack**: `./start-fullstack-docker.sh`
- **Backend only**: `./start-docker-dev.sh`
- **Native Python**: `./start-dev.sh`

## 📋 Port Configuration
- **Frontend**: `3000`
- **Django Backend**: `8001` (changed from 8000 to avoid conflicts)
- **PostgreSQL**: `5432` (internal)
- **Redis**: `6379` (internal)
- **Email (Mailpit)**: `8025`
- **Flower (Celery)**: `5555`

## 📚 Detailed Documentation
- **Portainer Deployment**: `PORTAINER_DEPLOYMENT.md`
- **General Docker**: `DOCKER_DEPLOYMENT.md`

---
*This overview was created to simplify the Docker deployment options after cleanup.*
