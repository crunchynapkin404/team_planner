# Production Readiness Guide - Team Planner

**Version:** 1.0  
**Date:** October 2, 2025  
**Status:** Week 11-12 Implementation Guide

---

## Overview

This guide provides comprehensive instructions for preparing the Team Planner application for production deployment, covering security hardening, performance optimization, monitoring setup, backup procedures, and deployment automation.

---

## Table of Contents

1. [Security Hardening](#security-hardening)
2. [Performance Optimization](#performance-optimization)
3. [Database Optimization](#database-optimization)
4. [Error Logging & Monitoring](#error-logging--monitoring)
5. [Backup & Recovery](#backup--recovery)
6. [Deployment Configuration](#deployment-configuration)
7. [Testing & Validation](#testing--validation)
8. [Go-Live Checklist](#go-live-checklist)

---

## 1. Security Hardening

### 1.1 Django Settings Configuration

**File:** `config/settings/production.py`

```python
# Security Settings
DEBUG = False
SECRET_KEY = env('DJANGO_SECRET_KEY')  # Must be 50+ characters, randomly generated
ALLOWED_HOSTS = ['yourdomain.com', 'www.yourdomain.com']

# HTTPS Enforcement
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# HSTS (HTTP Strict Transport Security)
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Cookie Security
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_AGE = 43200  # 12 hours

CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Lax'

# Content Security
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'

# CORS Configuration (if needed)
CORS_ALLOWED_ORIGINS = [
    "https://yourdomain.com",
    "https://www.yourdomain.com",
]
CORS_ALLOW_CREDENTIALS = True
```

### 1.2 Generate Secure SECRET_KEY

```bash
# Generate a secure secret key
python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'

# Add to environment variables
export DJANGO_SECRET_KEY='your-generated-key-here'
```

### 1.3 Change Admin URL

**File:** `config/urls.py`

```python
# Instead of /admin/, use custom URL
path('secure-admin-panel-2024/', admin.site.urls),
```

### 1.4 Database Security

```python
# Production database configuration
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': env('POSTGRES_DB'),
        'USER': env('POSTGRES_USER'),
        'PASSWORD': env('POSTGRES_PASSWORD'),  # Strong password (20+ chars)
        'HOST': env('POSTGRES_HOST'),
        'PORT': env('POSTGRES_PORT', default='5432'),
        'CONN_MAX_AGE': 600,  # Connection pooling
        'OPTIONS': {
            'sslmode': 'require',  # Enforce SSL
        }
    }
}
```

### 1.5 Password Policy

Ensure all 4 Django password validators are enabled:

```python
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 12}  # Increase to 12 characters
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]
```

### 1.6 Rate Limiting

Install and configure Django rate limiting:

```bash
pip install django-ratelimit
```

```python
# In views where needed
from django_ratelimit.decorators import ratelimit

@ratelimit(key='ip', rate='5/m', method='POST')
def login_view(request):
    # Login logic
    pass
```

### 1.7 Security Headers

Add security headers middleware:

```python
# config/middleware.py
class SecurityHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'same-origin'
        response['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
        return response

# Add to MIDDLEWARE
MIDDLEWARE = [
    # ... existing middleware
    'config.middleware.SecurityHeadersMiddleware',
]
```

---

## 2. Performance Optimization

### 2.1 Database Query Optimization

#### Add select_related() and prefetch_related()

**File:** `team_planner/shifts/api.py`

```python
# Before (N+1 query problem)
shifts = Shift.objects.all()

# After (optimized)
shifts = Shift.objects.select_related(
    'employee',
    'shift_type',
    'team'
).prefetch_related(
    'tags',
    'swap_requests'
)
```

#### Optimize Leave Request queries

**File:** `team_planner/leaves/api.py`

```python
# Optimize list endpoint
queryset = LeaveRequest.objects.select_related(
    'employee__user',
    'leave_type',
    'approved_by'
).prefetch_related(
    'conflicts'
).order_by('-start_date')
```

### 2.2 Add Database Indexes

**Create migration:**

```bash
python manage.py makemigrations --empty shifts --name add_performance_indexes
```

**File:** `team_planner/shifts/migrations/XXXX_add_performance_indexes.py`

```python
from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('shifts', 'previous_migration'),
    ]

    operations = [
        # Index for date range queries
        migrations.AddIndex(
            model_name='shift',
            index=models.Index(fields=['start_time', 'end_time'], name='shift_date_idx'),
        ),
        # Index for employee lookups
        migrations.AddIndex(
            model_name='shift',
            index=models.Index(fields=['employee', 'start_time'], name='shift_emp_date_idx'),
        ),
        # Index for team lookups
        migrations.AddIndex(
            model_name='shift',
            index=models.Index(fields=['team', 'start_time'], name='shift_team_date_idx'),
        ),
        # Index for swap requests
        migrations.AddIndex(
            model_name='swaprequest',
            index=models.Index(fields=['status', 'created_at'], name='swap_status_idx'),
        ),
        # Index for leave requests
        migrations.AddIndex(
            model_name='leaverequest',
            index=models.Index(fields=['employee', 'start_date', 'end_date'], name='leave_emp_date_idx'),
        ),
    ]
```

### 2.3 Enable Query Caching

Install Django Redis:

```bash
pip install django-redis
```

Configure caching:

```python
# config/settings/production.py
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': env('REDIS_URL', default='redis://127.0.0.1:6379/1'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'PARSER_CLASS': 'redis.connection.HiredisParser',
            'CONNECTION_POOL_CLASS_KWARGS': {
                'max_connections': 50,
                'retry_on_timeout': True,
            },
            'COMPRESSOR': 'django_redis.compressors.zlib.ZlibCompressor',
        },
        'KEY_PREFIX': 'team_planner',
        'TIMEOUT': 300,  # 5 minutes default
    }
}

# Session backend
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'
```

### 2.4 Cache API Responses

Add caching decorator to expensive endpoints:

```python
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator

@api_view(['GET'])
@cache_page(60 * 5)  # Cache for 5 minutes
def get_schedule(request):
    # Expensive computation
    pass

# For ViewSets
class ShiftViewSet(viewsets.ModelViewSet):
    @method_decorator(cache_page(60 * 2))
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
```

### 2.5 Frontend Optimization

**Enable Production Build:**

```bash
cd frontend
npm run build

# Verify bundle size
ls -lh dist/assets/
```

**Configure nginx for static file caching:**

```nginx
# Static files with long cache
location /static/ {
    alias /var/www/team_planner/staticfiles/;
    expires 1y;
    add_header Cache-Control "public, immutable";
}

# JavaScript/CSS with versioning
location ~* \.(js|css)$ {
    expires 1y;
    add_header Cache-Control "public, immutable";
}

# HTML - no cache (for SPA)
location ~* \.html$ {
    expires -1;
    add_header Cache-Control "no-store, no-cache, must-revalidate";
}
```

### 2.6 Enable Gzip Compression

```python
# config/settings/production.py
MIDDLEWARE = [
    'django.middleware.gzip.GZipMiddleware',  # Add at top
    # ... other middleware
]
```

**nginx configuration:**

```nginx
gzip on;
gzip_vary on;
gzip_types text/plain text/css text/xml text/javascript application/javascript application/json;
gzip_min_length 1000;
gzip_comp_level 6;
```

---

## 3. Database Optimization

### 3.1 PostgreSQL Configuration

**File:** `postgresql.conf`

```ini
# Memory Settings
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 16MB
maintenance_work_mem = 128MB

# Connection Settings
max_connections = 100

# Query Planning
random_page_cost = 1.1
effective_io_concurrency = 200

# Write-Ahead Log
wal_buffers = 16MB
checkpoint_completion_target = 0.9

# Autovacuum (important for performance)
autovacuum = on
autovacuum_max_workers = 3
```

### 3.2 Regular Maintenance

Create maintenance script:

```bash
#!/bin/bash
# maintenance.sh

# Vacuum and analyze database
psql -U $POSTGRES_USER -d $POSTGRES_DB -c "VACUUM ANALYZE;"

# Reindex
psql -U $POSTGRES_USER -d $POSTGRES_DB -c "REINDEX DATABASE $POSTGRES_DB;"

echo "Database maintenance completed at $(date)"
```

Add to crontab:

```bash
# Run every Sunday at 2 AM
0 2 * * 0 /path/to/maintenance.sh >> /var/log/db_maintenance.log 2>&1
```

### 3.3 Connection Pooling

Install pgbouncer:

```bash
sudo apt-get install pgbouncer
```

Configure pgbouncer:

```ini
# /etc/pgbouncer/pgbouncer.ini
[databases]
team_planner = host=localhost port=5432 dbname=team_planner

[pgbouncer]
listen_port = 6432
listen_addr = 127.0.0.1
auth_type = md5
auth_file = /etc/pgbouncer/userlist.txt
pool_mode = transaction
max_client_conn = 100
default_pool_size = 25
```

Update Django settings:

```python
DATABASES = {
    'default': {
        # ... other settings
        'PORT': '6432',  # pgbouncer port
    }
}
```

---

## 4. Error Logging & Monitoring

### 4.1 Install Sentry

```bash
pip install sentry-sdk
```

**Configure Sentry:**

```python
# config/settings/production.py
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

sentry_sdk.init(
    dsn=env('SENTRY_DSN'),
    integrations=[DjangoIntegration()],
    traces_sample_rate=0.1,  # 10% of transactions
    send_default_pii=False,  # Don't send user data
    environment='production',
    release=env('APP_VERSION', default='1.0.0'),
)
```

### 4.2 Configure Structured Logging

```python
# config/settings/production.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
        'json': {
            '()': 'pythonjsonlogger.jsonlogger.JsonFormatter',
            'format': '%(asctime)s %(name)s %(levelname)s %(message)s'
        }
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose'
        },
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/team_planner/django.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 10,
            'formatter': 'json',
        },
        'error_file': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/team_planner/django_errors.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 10,
            'formatter': 'json',
        },
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler',
            'filters': ['require_debug_false'],
        }
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file', 'mail_admins'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['error_file', 'mail_admins'],
            'level': 'ERROR',
            'propagate': False,
        },
        'team_planner': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
}
```

### 4.3 Health Check Endpoint

**Create health check view:**

```python
# team_planner/utils/health.py
from django.http import JsonResponse
from django.db import connection
from django.core.cache import cache
import datetime

def health_check(request):
    """System health check endpoint"""
    health = {
        'status': 'healthy',
        'timestamp': datetime.datetime.now().isoformat(),
        'checks': {}
    }
    
    # Database check
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        health['checks']['database'] = 'ok'
    except Exception as e:
        health['checks']['database'] = f'error: {str(e)}'
        health['status'] = 'unhealthy'
    
    # Cache check
    try:
        cache.set('health_check', 'ok', 10)
        if cache.get('health_check') == 'ok':
            health['checks']['cache'] = 'ok'
        else:
            health['checks']['cache'] = 'error'
            health['status'] = 'degraded'
    except Exception as e:
        health['checks']['cache'] = f'error: {str(e)}'
        health['status'] = 'degraded'
    
    status_code = 200 if health['status'] == 'healthy' else 503
    return JsonResponse(health, status=status_code)

# Add to urls.py
path('health/', health_check, name='health_check'),
```

### 4.4 Application Performance Monitoring

Install New Relic or similar:

```bash
pip install newrelic
```

Configure:

```python
# newrelic.ini
[newrelic]
license_key = YOUR_LICENSE_KEY
app_name = Team Planner Production
monitor_mode = true
log_level = info
```

Run with New Relic:

```bash
NEW_RELIC_CONFIG_FILE=newrelic.ini newrelic-admin run-program gunicorn config.wsgi:application
```

---

## 5. Backup & Recovery

### 5.1 Automated Database Backups

**Create backup script:**

```bash
#!/bin/bash
# backup_database.sh

BACKUP_DIR="/var/backups/team_planner"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="$BACKUP_DIR/db_backup_$TIMESTAMP.sql.gz"

# Create backup directory if not exists
mkdir -p $BACKUP_DIR

# Perform backup
pg_dump -U $POSTGRES_USER $POSTGRES_DB | gzip > $BACKUP_FILE

# Keep only last 30 days of backups
find $BACKUP_DIR -name "db_backup_*.sql.gz" -mtime +30 -delete

# Verify backup
if [ -f "$BACKUP_FILE" ]; then
    echo "Backup completed: $BACKUP_FILE"
    # Upload to S3 (optional)
    # aws s3 cp $BACKUP_FILE s3://your-backup-bucket/team_planner/
else
    echo "Backup failed!"
    exit 1
fi
```

**Schedule daily backups:**

```bash
# crontab -e
0 2 * * * /path/to/backup_database.sh >> /var/log/backup.log 2>&1
```

### 5.2 Media Files Backup

```bash
#!/bin/bash
# backup_media.sh

MEDIA_DIR="/var/www/team_planner/media"
BACKUP_DIR="/var/backups/team_planner/media"
TIMESTAMP=$(date +"%Y%m%d")

rsync -avz --delete $MEDIA_DIR/ $BACKUP_DIR/$TIMESTAMP/

# Optional: Upload to S3
# aws s3 sync $BACKUP_DIR/$TIMESTAMP/ s3://your-backup-bucket/team_planner/media/$TIMESTAMP/
```

### 5.3 Restore Procedures

**Database restore:**

```bash
#!/bin/bash
# restore_database.sh

BACKUP_FILE=$1

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <backup_file.sql.gz>"
    exit 1
fi

# Stop application
systemctl stop gunicorn

# Restore database
gunzip -c $BACKUP_FILE | psql -U $POSTGRES_USER $POSTGRES_DB

# Run migrations (if needed)
cd /var/www/team_planner
python manage.py migrate

# Restart application
systemctl start gunicorn

echo "Database restored from $BACKUP_FILE"
```

### 5.4 Disaster Recovery Plan

**Document:**

1. **RPO (Recovery Point Objective):** 24 hours (daily backups)
2. **RTO (Recovery Time Objective):** 2 hours
3. **Backup Locations:**
   - Local: `/var/backups/team_planner/`
   - Remote: S3 bucket (if configured)
4. **Recovery Steps:**
   1. Provision new server (if hardware failure)
   2. Install dependencies
   3. Restore latest database backup
   4. Restore media files
   5. Update DNS (if server change)
   6. Run health checks
   7. Notify users

---

## 6. Deployment Configuration

### 6.1 Gunicorn Configuration

**File:** `/etc/systemd/system/gunicorn.service`

```ini
[Unit]
Description=Gunicorn daemon for Team Planner
After=network.target postgresql.service

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/team_planner
Environment="PATH=/var/www/team_planner/venv/bin"
Environment="DJANGO_SETTINGS_MODULE=config.settings.production"
ExecStart=/var/www/team_planner/venv/bin/gunicorn \
    --workers 4 \
    --worker-class sync \
    --bind unix:/run/gunicorn.sock \
    --timeout 60 \
    --max-requests 1000 \
    --max-requests-jitter 50 \
    --access-logfile /var/log/team_planner/gunicorn_access.log \
    --error-logfile /var/log/team_planner/gunicorn_error.log \
    --log-level info \
    config.wsgi:application

[Install]
WantedBy=multi-user.target
```

**Start service:**

```bash
sudo systemctl daemon-reload
sudo systemctl enable gunicorn
sudo systemctl start gunicorn
sudo systemctl status gunicorn
```

### 6.2 Nginx Configuration

**File:** `/etc/nginx/sites-available/team_planner`

```nginx
upstream team_planner_backend {
    server unix:/run/gunicorn.sock fail_timeout=0;
}

server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;

    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Logging
    access_log /var/log/nginx/team_planner_access.log;
    error_log /var/log/nginx/team_planner_error.log;

    # Client max body size
    client_max_body_size 10M;

    # Static files
    location /static/ {
        alias /var/www/team_planner/staticfiles/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Media files
    location /media/ {
        alias /var/www/team_planner/media/;
        expires 30d;
        add_header Cache-Control "public";
    }

    # Frontend (SPA)
    location / {
        root /var/www/team_planner/frontend/dist;
        try_files $uri $uri/ /index.html;
        
        # No cache for index.html
        location = /index.html {
            expires -1;
            add_header Cache-Control "no-store, no-cache, must-revalidate";
        }
    }

    # API endpoints
    location /api/ {
        proxy_pass http://team_planner_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
    }

    # Health check
    location /health/ {
        proxy_pass http://team_planner_backend;
        access_log off;
    }
}
```

**Enable site:**

```bash
sudo ln -s /etc/nginx/sites-available/team_planner /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 6.3 SSL Certificate (Let's Encrypt)

```bash
# Install Certbot
sudo apt-get install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Auto-renewal is configured automatically
sudo systemctl status certbot.timer
```

### 6.4 Environment Variables

**File:** `/var/www/team_planner/.env.production`

```bash
# Django
DJANGO_SETTINGS_MODULE=config.settings.production
DJANGO_SECRET_KEY=<generated-secret-key>
DJANGO_ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# Database
DATABASE_URL=postgres://user:password@localhost:5432/team_planner
POSTGRES_DB=team_planner
POSTGRES_USER=team_planner_user
POSTGRES_PASSWORD=<strong-password>
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# Redis
REDIS_URL=redis://127.0.0.1:6379/1

# Email
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=<app-password>
DEFAULT_FROM_EMAIL=Team Planner <noreply@yourdomain.com>

# Sentry
SENTRY_DSN=<your-sentry-dsn>

# Application
APP_VERSION=1.0.0
```

---

## 7. Testing & Validation

### 7.1 Load Testing

Install Locust:

```bash
pip install locust
```

**Create load test:**

```python
# locustfile.py
from locust import HttpUser, task, between

class TeamPlannerUser(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        # Login
        response = self.client.post("/api/auth/login/", json={
            "username": "testuser",
            "password": "testpass123"
        })
        self.token = response.json()['token']
        self.headers = {'Authorization': f'Token {self.token}'}
    
    @task(3)
    def view_shifts(self):
        self.client.get("/api/shifts/", headers=self.headers)
    
    @task(2)
    def view_calendar(self):
        self.client.get("/api/calendar/events/", headers=self.headers)
    
    @task(1)
    def create_swap_request(self):
        self.client.post("/api/swap-requests/", headers=self.headers, json={
            "shift_id": 1,
            "target_employee_id": 2,
            "reason": "Load test"
        })
```

**Run load test:**

```bash
locust -f locustfile.py --host=https://yourdomain.com --users 100 --spawn-rate 10
```

### 7.2 Security Testing

```bash
# Install OWASP ZAP
docker pull owasp/zap2docker-stable

# Run baseline scan
docker run -v $(pwd):/zap/wrk/:rw -t owasp/zap2docker-stable \
    zap-baseline.py -t https://yourdomain.com -r zap_report.html
```

### 7.3 Smoke Tests

**Post-deployment smoke test:**

```bash
#!/bin/bash
# smoke_test.sh

BASE_URL="https://yourdomain.com"

echo "Running smoke tests..."

# Test 1: Health check
echo "Test 1: Health check"
response=$(curl -s -o /dev/null -w "%{http_code}" $BASE_URL/health/)
if [ $response -eq 200 ]; then
    echo "✓ Health check passed"
else
    echo "✗ Health check failed (HTTP $response)"
    exit 1
fi

# Test 2: Frontend loads
echo "Test 2: Frontend loads"
response=$(curl -s -o /dev/null -w "%{http_code}" $BASE_URL/)
if [ $response -eq 200 ]; then
    echo "✓ Frontend loads"
else
    echo "✗ Frontend failed (HTTP $response)"
    exit 1
fi

# Test 3: API responds
echo "Test 3: API endpoint"
response=$(curl -s -o /dev/null -w "%{http_code}" $BASE_URL/api/shift-types/)
if [ $response -eq 200 ]; then
    echo "✓ API responds"
else
    echo "✗ API failed (HTTP $response)"
    exit 1
fi

# Test 4: Login endpoint
echo "Test 4: Login endpoint"
response=$(curl -s -o /dev/null -w "%{http_code}" -X POST $BASE_URL/api/auth/login/ \
    -H "Content-Type: application/json" \
    -d '{"username":"test","password":"test"}')
if [ $response -eq 400 ] || [ $response -eq 401 ]; then
    echo "✓ Login endpoint responds correctly"
else
    echo "✗ Login endpoint unexpected response (HTTP $response)"
    exit 1
fi

echo "All smoke tests passed!"
```

---

## 8. Go-Live Checklist

### Pre-Deployment (1 Week Before)

- [ ] Security audit completed
- [ ] Performance testing completed
- [ ] Load testing passed (100+ concurrent users)
- [ ] Database optimizations applied
- [ ] Backup procedures tested
- [ ] Monitoring configured and tested
- [ ] SSL certificate installed
- [ ] DNS configured
- [ ] User documentation completed
- [ ] Training materials ready
- [ ] Support procedures documented

### Deployment Day

- [ ] Notify users of scheduled maintenance
- [ ] Create final database backup
- [ ] Deploy to staging environment first
- [ ] Run smoke tests on staging
- [ ] Deploy to production
- [ ] Run migrations
- [ ] Collect static files
- [ ] Restart services
- [ ] Run smoke tests on production
- [ ] Verify health check endpoint
- [ ] Test critical user flows
- [ ] Monitor error logs (first 30 minutes)
- [ ] Monitor performance metrics
- [ ] Notify users of successful deployment

### Post-Deployment (First Week)

- [ ] Monitor error rates daily
- [ ] Monitor performance metrics
- [ ] Check backup completion
- [ ] Review user feedback
- [ ] Address any urgent issues
- [ ] Create post-deployment report
- [ ] Schedule follow-up review

---

## Monitoring Dashboard

### Key Metrics to Track

1. **Application Health**
   - Uptime percentage
   - Response times (p50, p95, p99)
   - Error rate
   - Request rate

2. **Database**
   - Query performance
   - Connection pool usage
   - Slow query count
   - Database size

3. **Infrastructure**
   - CPU usage
   - Memory usage
   - Disk space
   - Network traffic

4. **Business Metrics**
   - Active users
   - Shift assignments created
   - Swap requests processed
   - Leave requests approved

---

## Rollback Procedure

If critical issues are discovered:

1. **Immediate Actions**
   ```bash
   # Stop current version
   sudo systemctl stop gunicorn
   
   # Restore previous code
   cd /var/www/team_planner
   git checkout <previous-tag>
   
   # Restore database (if migrations ran)
   gunzip -c /var/backups/team_planner/pre_deployment_backup.sql.gz | \
       psql -U $POSTGRES_USER $POSTGRES_DB
   
   # Restart services
   sudo systemctl start gunicorn
   ```

2. **Communicate**
   - Notify users of rollback
   - Explain issue and timeline for fix
   - Provide workaround if available

3. **Post-Mortem**
   - Document what went wrong
   - Identify root cause
   - Update procedures to prevent recurrence

---

## Conclusion

This production readiness guide provides a comprehensive framework for deploying Team Planner to production. Follow each section systematically, test thoroughly, and monitor continuously.

**Next Steps:**
1. Review and customize configurations for your environment
2. Set up staging environment
3. Perform security audit
4. Complete performance testing
5. Train support team
6. Schedule deployment

**Estimated Timeline:**
- Week 11: Security, Performance, Monitoring (40 hours)
- Week 12: Documentation, Testing, Training (40 hours)
- Week 13: Deployment Preparation and Execution (20 hours)

**Total: 100 hours (2.5 weeks)**

---

**Document Version:** 1.0  
**Last Updated:** October 2, 2025  
**Maintained By:** Development Team
