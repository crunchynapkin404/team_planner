# 🐳 Docker Deployment Guide for External Server

## Quick Start - Full Development Environment in Docker

### Prerequisites on External Server
- Docker and Docker Compose installed
- Git installed
- Ports 3000, 8000, 8025, 5555 available

### 1. Clone and Setup
```bash
git clone <your-repo-url> team_planner
cd team_planner
chmod +x start-fullstack-docker.sh
./start-fullstack-docker.sh
```

### 2. Access Your Application
- **Frontend**: http://your-server-ip:3000
- **🔧 Backend API**: `http://your-server-ip:8001` 
- **👤 Admin Panel**: `http://your-server-ip:8001/admin/`
- **📚 API Docs**: `http://your-server-ip:8001/api/docs/`
- **Email**: http://your-server-ip:8025
- **Celery**: http://your-server-ip:5555

### 3. Development Workflow

#### Remote Development Options:

**Option A: VS Code Remote Development**
1. Install "Remote - SSH" extension in VS Code
2. Connect to your server via SSH
3. Open the project folder
4. Edit files directly on the server
5. Both frontend and backend will hot-reload automatically

**Option B: Local Development with Remote Sync**
1. Work locally on your code
2. Use `rsync`, `scp`, or Git to sync changes
3. Docker will pick up changes and reload

**Option C: Git-Based Workflow**
1. Make changes locally
2. Push to Git repository
3. Pull changes on server
4. Docker automatically reloads

### 4. Managing the Docker Environment

#### Start All Services
```bash
./start-fullstack-docker.sh
```

#### Stop All Services
```bash
docker-compose -f docker-compose.fullstack.yml down
```

#### View Logs
```bash
docker-compose -f docker-compose.fullstack.yml logs -f [service_name]
```

#### Restart Specific Service
```bash
docker-compose -f docker-compose.fullstack.yml restart [service_name]
```

#### Access Django Shell
```bash
docker-compose -f docker-compose.fullstack.yml exec django python manage.py shell
```

#### Create Superuser
```bash
docker-compose -f docker-compose.fullstack.yml exec django python manage.py createsuperuser
```

### 5. File Structure for Docker Development
```
team_planner/
├── docker-compose.fullstack.yml    # Full-stack Docker setup
├── start-fullstack-docker.sh       # Quick start script
├── frontend/
│   ├── Dockerfile.dev              # Frontend development container
│   ├── vite.config.docker.ts       # Docker-specific frontend config
│   └── vite.config.ts              # Local development config
└── .envs/.local/                   # Docker environment variables
```

### 6. Persistent Data
- **Database**: PostgreSQL data persists in Docker volume
- **Redis**: Cache data persists in Docker volume
- **File changes**: Real-time sync with hot-reloading

### 7. Production Deployment
For production deployment, use:
```bash
docker-compose -f docker-compose.production.yml up --build -d
```

### 8. Troubleshooting

#### Container Issues
```bash
# Check container status
docker-compose -f docker-compose.fullstack.yml ps

# Rebuild containers
docker-compose -f docker-compose.fullstack.yml up --build --force-recreate

# Clean up everything
docker-compose -f docker-compose.fullstack.yml down -v
docker system prune -a
```

#### Network Issues
- Ensure ports are open in firewall
- Check if services are binding to 0.0.0.0
- Verify Docker network configuration

#### File Sync Issues
- On Windows/Mac with WSL2, ensure file watching works
- Use `CHOKIDAR_USEPOLLING=true` for problematic file systems

### 9. Security Notes for External Server
- Change default passwords in `.envs/.local/.postgres`
- Use firewall to restrict access to development ports
- Consider using a VPN or SSH tunnel for secure access
- Don't use this setup for production without security hardening

### 10. Next Steps
1. Set up SSL/HTTPS for production
2. Configure domain names
3. Set up automated backups
4. Implement monitoring and logging
5. Set up CI/CD pipeline

---

**🎉 You now have a fully containerized development environment that you can deploy anywhere and continue working on remotely!**
