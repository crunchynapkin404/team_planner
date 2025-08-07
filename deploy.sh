#!/bin/bash
# Quick deployment script for new servers
# Usage: ./deploy.sh [environment] [server-ip-or-domain]

set -e

ENVIRONMENT=${1:-local}
SERVER=${2:-127.0.0.1}

echo "🚀 Deploying Team Planner to $ENVIRONMENT environment"
echo "📍 Server: $SERVER"

# Create environment file
if [ "$ENVIRONMENT" = "production" ]; then
    echo "📝 Creating production environment file..."
    cat > .env.production << EOF
DJANGO_SECRET_KEY=$(openssl rand -hex 32)
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=$SERVER,localhost
VITE_API_BASE_URL=http://$SERVER:8000
DJANGO_SETTINGS_MODULE=config.settings.production
EOF
else
    echo "📝 Creating local environment file..."
    cat > .env.local << EOF
DJANGO_SECRET_KEY=dev-secret-key-$(openssl rand -hex 16)
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=$SERVER,localhost,127.0.0.1,0.0.0.0
VITE_API_BASE_URL=http://$SERVER:8000
DJANGO_SETTINGS_MODULE=config.settings.local
EOF
fi

# Update frontend configuration
echo "🔧 Updating frontend configuration..."
sed -i "s|target: 'http://127.0.0.1:8000'|target: 'http://$SERVER:8000'|g" frontend/vite.config.ts

# Update Django settings if production
if [ "$ENVIRONMENT" = "production" ]; then
    echo "🔧 Updating Django settings for production..."
    # Add server to ALLOWED_HOSTS in production.py
    if ! grep -q "$SERVER" config/settings/production.py; then
        sed -i "/ALLOWED_HOSTS.*=.*\[/a\\    \"$SERVER\"," config/settings/production.py
    fi
fi

echo "✅ Configuration updated!"
echo ""
echo "📋 Next steps:"
echo "1. Install dependencies:"
echo "   Backend: pip install -r requirements/${ENVIRONMENT}.txt"
echo "   Frontend: cd frontend && npm install"
echo ""
echo "2. Set up database:"
echo "   python manage.py migrate"
echo "   python manage.py createsuperuser"
echo ""
echo "3. Start services:"
echo "   Backend: python manage.py runserver 0.0.0.0:8000"
echo "   Frontend: cd frontend && npm run dev"
echo ""
echo "4. Access application:"
echo "   Frontend: http://$SERVER:3000"
echo "   Backend Admin: http://$SERVER:8000/admin/"
echo "   API: http://$SERVER:8000/api/"
