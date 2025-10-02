#!/bin/bash
# Startup script for Team Planner backend with proper database configuration

cd /home/vscode/team_planner

# Set database URL to use SQLite file in project directory
export DATABASE_URL="sqlite:///$(pwd)/db.sqlite3"

echo "Using database: $DATABASE_URL"

# Check if database exists and has tables
if [ ! -f "db.sqlite3" ]; then
    echo "Database file not found. Running migrations..."
    python3 manage.py migrate
    echo "Creating superuser..."
    python3 manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    print('Created admin user: admin / admin123')
else:
    print('Admin user already exists')
"
else
    echo "Database exists. Checking for pending migrations..."
    python3 manage.py migrate
fi

echo ""
echo "========================================="
echo "Starting Django development server..."
echo "Backend: http://0.0.0.0:8000"
echo "Admin: http://0.0.0.0:8000/admin"
echo "Login: admin / admin123"
echo "========================================="
echo ""

# Start the server
python3 manage.py runserver 0.0.0.0:8000
