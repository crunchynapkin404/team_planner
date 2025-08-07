# Deployment Guide for Team Planner

## ⚠️ Current Configuration Status

**The current setup is NOT ready for production deployment** without modifications. Here's what needs to be changed:

## 🔧 Required Changes for New Server Deployment

### 1. Frontend Configuration

**Current Issue**: Hardcoded localhost URLs in `frontend/vite.config.ts`

**For Production**:
```typescript
// Replace the proxy target in vite.config.ts
target: 'http://your-server-ip:8000',  // Replace with actual server IP/domain
```

**For Different Environments**:
- **Development**: `http://127.0.0.1:8000`
- **Staging**: `http://staging-server-ip:8000`
- **Production**: `http://your-domain.com` or `https://your-domain.com`

### 2. Django Settings

**Current Issue**: Limited ALLOWED_HOSTS in `config/settings/local.py`

**Update for Production**:
```python
# In config/settings/production.py
ALLOWED_HOSTS = [
    'your-domain.com',
    'www.your-domain.com', 
    'your-server-ip',
    'localhost',  # Keep for local development
]
```

### 3. Database Configuration

**Current**: Uses SQLite (development only)
**Production**: Requires PostgreSQL

Update `.envs/.production/.django`:
```env
POSTGRES_HOST=your-db-host
POSTGRES_PORT=5432
POSTGRES_DB=team_planner_prod
POSTGRES_USER=team_planner_user
POSTGRES_PASSWORD=your-secure-password
```

### 4. Environment Variables

Create these files for different environments:

**`.env.local`** (Development):
```env
DJANGO_SECRET_KEY=dev-secret-key
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0
VITE_API_BASE_URL=http://127.0.0.1:8000
```

**`.env.production`** (Production):
```env
DJANGO_SECRET_KEY=your-super-secure-secret-key
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=your-domain.com,your-server-ip
VITE_API_BASE_URL=https://your-domain.com
DJANGO_SECURE_SSL_REDIRECT=True
```

## 🐳 Docker Deployment Options

### Option 1: Local Development
```bash
docker-compose -f docker-compose.local.yml up
```

### Option 2: Production Deployment
```bash
docker-compose -f docker-compose.production.yml up
```

## 🚀 Manual Deployment Steps

### For a New Server:

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/your-username/team_planner.git
   cd team_planner
   ```

2. **Update Configuration**:
   ```bash
   # Copy environment template
   cp .env.example .env.production
   
   # Edit with your server details
   nano .env.production
   ```

3. **Update Frontend Config**:
   ```bash
   # Edit frontend/vite.config.ts
   # Replace 'http://127.0.0.1:8000' with your server URL
   nano frontend/vite.config.ts
   ```

4. **Update Django Settings**:
   ```bash
   # Edit config/settings/production.py
   # Add your domain to ALLOWED_HOSTS
   nano config/settings/production.py
   ```

5. **Install Dependencies**:
   ```bash
   # Backend
   pip install -r requirements/production.txt
   
   # Frontend  
   cd frontend
   npm install
   npm run build
   ```

6. **Database Setup**:
   ```bash
   python manage.py migrate
   python manage.py collectstatic
   python manage.py createsuperuser
   ```

7. **Start Services**:
   ```bash
   # Backend
   python manage.py runserver 0.0.0.0:8000
   
   # Frontend (in production, serve built files with nginx)
   npm run preview
   ```

## 🔒 Security Considerations

### Required for Production:
- [ ] Change `DJANGO_SECRET_KEY` to a unique, secure value
- [ ] Set `DJANGO_DEBUG=False`
- [ ] Configure HTTPS/SSL certificates
- [ ] Update `ALLOWED_HOSTS` with your domain
- [ ] Use environment variables for sensitive data
- [ ] Configure secure database credentials
- [ ] Set up proper firewall rules
- [ ] Configure CORS settings

## 📝 Configuration Files to Update

Before deploying to a new server, update these files:

1. **`frontend/vite.config.ts`** - API endpoint URLs
2. **`config/settings/production.py`** - ALLOWED_HOSTS
3. **`.envs/.production/.django`** - Environment variables
4. **`.envs/.production/.postgres`** - Database credentials

## ⚡ Quick Server Change Checklist

- [ ] Update API URLs in `frontend/vite.config.ts`
- [ ] Add server IP/domain to `ALLOWED_HOSTS`
- [ ] Update environment variables
- [ ] Configure database connection
- [ ] Test all endpoints work
- [ ] Verify authentication flow
- [ ] Check CORS settings
- [ ] Test leave management functionality

## 🆘 Common Issues

1. **CORS Errors**: Update ALLOWED_HOSTS and CORS settings
2. **API Connection Failed**: Check vite.config.ts proxy settings
3. **Database Connection**: Verify PostgreSQL credentials
4. **Static Files**: Run `collectstatic` in production
5. **Permission Errors**: Check file permissions and ownership

## 📞 Support

If you encounter issues during deployment, check:
1. Backend logs: `python manage.py runserver --verbosity=2`
2. Frontend dev tools: Browser console for API errors
3. Network connectivity between frontend and backend
4. Database connection and migrations status
