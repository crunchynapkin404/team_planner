# 🐳 Portainer Deployment Guide for Team Planner

## Prerequisites
- Portainer running on your server
- Git installed on the server
- Access to Portainer web interface

## 🚀 Deployment Steps

### Method 1: Git Repository Stack (Recommended)

#### 1. Access Portainer
Navigate to your Portainer instance (usually `http://your-server-ip:9000`)

#### 2. Create New Stack
1. Go to **Stacks** in the left sidebar
2. Click **+ Add stack**
3. Give it a name: `team-planner`

#### 3. Configure Git Repository
1. Select **Repository** tab
2. Fill in the following:
   - **Repository URL**: `https://github.com/crunchynapkin404/team_planner.git`
   - **Repository reference**: `main`
   - **Compose path**: `docker-compose.portainer.yml`

#### 4. Set Environment Variables (Optional)
Add these environment variables if you want to customize:
```env
POSTGRES_PASSWORD=your_secure_password_here
CELERY_FLOWER_PASSWORD=your_flower_password
DJANGO_SECRET_KEY=your_secret_key_here
```

#### 5. Deploy
1. Click **Deploy the stack**
2. Wait for Portainer to pull the code and build containers
3. Monitor the build process in the logs

### Method 2: Upload Docker Compose File

#### 1. Upload Compose File
1. In Portainer, go to **Stacks** → **+ Add stack**
2. Name it: `team-planner`
3. Select **Upload** tab
4. Upload the `docker-compose.portainer.yml` file

#### 2. Build Context Issue
**⚠️ Important**: This method won't work directly because Docker needs to build from source code. Use Method 1 (Git Repository) instead.

### Method 3: Manual Server Setup + Portainer Stack

#### 1. Clone Repository on Server
```bash
# SSH into your server
cd /opt  # or your preferred directory
git clone https://github.com/crunchynapkin404/team_planner.git
cd team_planner
```

#### 2. Create Stack in Portainer
1. Go to **Stacks** → **+ Add stack**
2. Name: `team-planner`
3. Select **Web editor** tab
4. Copy and paste the contents of `docker-compose.portainer.yml`
5. Modify the build contexts to absolute paths:
   ```yaml
   build:
     context: /opt/team_planner  # Update this path
     dockerfile: ./compose/local/django/Dockerfile
   ```

## 📊 After Deployment

### Services Available
- **Frontend**: `http://your-server-ip:3000`
- **Backend API**: `http://your-server-ip:8001`
- **Admin Panel**: `http://your-server-ip:8001/admin/`
- **API Documentation**: `http://your-server-ip:8001/api/docs/`
- **Email Testing**: `http://your-server-ip:8025`
- **Celery Monitoring**: `http://your-server-ip:5555`

### Initial Setup
1. **Create Django Superuser**:
   - In Portainer, go to **Containers**
   - Find `team_planner_django`
   - Click **Console** → **Connect**
   - Run: `python manage.py createsuperuser`

2. **Run Migrations** (if needed):
   ```bash
   python manage.py migrate
   ```

## 🔧 Managing Your Application

### View Logs
1. In Portainer, go to **Containers** or **Stacks**
2. Click on any container name
3. Go to **Logs** tab
4. View real-time logs

### Update Application
1. **For Git Repository Stack**:
   - Go to **Stacks** → Your stack
   - Click **Pull and redeploy**
   - Portainer will pull latest code and rebuild

2. **For Manual Setup**:
   ```bash
   # SSH to server
   cd /opt/team_planner
   git pull
   # Then redeploy stack in Portainer
   ```

### Restart Services
1. Go to **Stacks** → Your stack
2. Click **Stop** then **Start**
3. Or restart individual containers in **Containers** section

### Scale Services
1. Go to **Stacks** → Your stack
2. Click on service name
3. Adjust **Replicas** count
4. Click **Update**

## 🛠️ Troubleshooting

### Build Failures
- Check **Logs** in Portainer stack deployment
- Ensure Git repository is accessible
- Verify Docker build context paths

### Port Conflicts
- Check if ports 3000, 8000, 8025, 5555 are available
- Modify ports in docker-compose file if needed

### Database Connection Issues
- Verify PostgreSQL container is running
- Check database credentials in environment variables
- Look at Django container logs

### Frontend Not Loading
- Check if frontend container is running
- Verify port 3000 is accessible
- Check frontend build logs

## 🔐 Security Notes

### For Production
1. **Change Default Passwords**:
   ```env
   POSTGRES_PASSWORD=your_very_secure_password
   CELERY_FLOWER_PASSWORD=your_secure_flower_password
   ```

2. **Use Environment Variables**:
   - Don't hardcode secrets in docker-compose.yml
   - Use Portainer's environment variables feature

3. **Network Security**:
   - Consider using Portainer's network isolation
   - Set up reverse proxy with SSL
   - Restrict database port access

4. **Backup Strategy**:
   - Regularly backup PostgreSQL data volume
   - Export important configurations

## 🚀 Production Deployment

For production, use the production compose file:
```bash
# Use this compose file instead:
docker-compose.production.yml
```

Key differences:
- Optimized for production
- Includes Traefik reverse proxy
- SSL/HTTPS support
- Better security settings
- Separate production environment variables

## 📝 Next Steps

1. **SSL/HTTPS**: Set up reverse proxy with SSL certificates
2. **Domain**: Configure custom domain name
3. **Monitoring**: Add monitoring stack (Prometheus/Grafana)
4. **Backups**: Set up automated backups
5. **CI/CD**: Configure automated deployments

---

**🎉 Your Team Planner is now running on your server with Portainer!**

You can continue developing by:
1. Making changes locally
2. Pushing to Git repository  
3. Using "Pull and redeploy" in Portainer to update

This gives you the best of both worlds - easy deployment with Portainer and continuous development workflow!
