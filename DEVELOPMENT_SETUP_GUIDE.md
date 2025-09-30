# Team Planner - Complete Development Setup & Debugging Guide

## 🚀 Quick Start Guide

This guide will take you from the current cleaned-up state to a fully working team scheduling system.

### Prerequisites
- Python 3.11+
- Node.js 18+
- Git
- VS Code (recommended)

## 📋 **PHASE 1: Environment Setup & Verification**

### Step 1: Environment Configuration

1. **Set up environment variables**:
```bash
# Copy and configure environment
cp .env.example .env.local

# Edit .env.local with these values:
export DATABASE_URL=sqlite:///db.sqlite3
export DJANGO_SETTINGS_MODULE=config.settings.local
export DJANGO_SECRET_KEY=your-development-secret-key-here
export DJANGO_DEBUG=True
export DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0
```

2. **Load environment for current session**:
```bash
export DATABASE_URL=sqlite:///db.sqlite3
export DJANGO_SETTINGS_MODULE=config.settings.local
export DJANGO_SECRET_KEY=your-development-secret-key-here
export DJANGO_DEBUG=True
```

3. **Verify Django setup**:
```bash
python3 manage.py check
# Should output: System check identified no issues (0 silenced).
```

### Step 2: Database Setup

```bash
# Apply migrations
python3 manage.py migrate

# Create superuser
python3 manage.py createsuperuser
# Username: admin
# Email: admin@teamplanner.local
# Password: AdminPassword123!
```

### Step 3: Install Dependencies

```bash
# Backend dependencies (should already be installed)
pip install -r requirements/local.txt

# Frontend dependencies
cd frontend
npm install
npm audit fix
cd ..
```

## 🔍 **PHASE 2: Critical Issue Diagnosis**

### Step 4: Diagnose Employee Availability Issue

This is the #1 blocker. Let's diagnose why no employees are available for shifts.

**Run the diagnostic script**:
```bash
python3 manage.py shell
```

**In the Django shell, run this diagnostic**:
```python
# === EMPLOYEE AVAILABILITY DIAGNOSTIC ===
from team_planner.employees.models import EmployeeProfile, EmployeeSkill
from team_planner.users.models import User
from django.contrib.auth import get_user_model

print("=== EMPLOYEE AVAILABILITY DIAGNOSTIC ===\n")

# Check if we have any users
users = User.objects.all()
print(f"Total users in database: {users.count()}")
for user in users[:5]:
    print(f"  - {user.username} (active: {user.is_active})")

print("\n" + "="*50)

# Check employee profiles
profiles = EmployeeProfile.objects.all()
print(f"Total employee profiles: {profiles.count()}")

for profile in profiles[:5]:
    print(f"\nEmployee: {profile.user.username}")
    print(f"  Available for incidents: {profile.available_for_incidents}")
    print(f"  Available for waakdienst: {profile.available_for_waakdienst}")
    skills = list(profile.skills.all())
    print(f"  Skills: {[skill.name for skill in skills] if skills else 'NO SKILLS'}")

print("\n" + "="*50)

# Check available skills in system
all_skills = EmployeeSkill.objects.all()
print(f"Available skills in system: {all_skills.count()}")
for skill in all_skills:
    print(f"  - {skill.name}: {skill.description}")

print("\n" + "="*50)

# Check constraint checker availability
from team_planner.orchestrators.constraints import ConstraintChecker
from datetime import datetime, timezone
import zoneinfo

# Create a test time range
tz = zoneinfo.ZoneInfo("Europe/Amsterdam")
start_time = datetime(2025, 10, 7, 8, 0, tzinfo=tz)
end_time = datetime(2025, 10, 7, 17, 0, tzinfo=tz)

checker = ConstraintChecker()

# Test incidents availability
incidents_available = checker.get_available_employees(
    start_time=start_time,
    end_time=end_time,
    shift_type="incidents"
)
print(f"Employees available for incidents: {len(incidents_available)}")
for emp in incidents_available:
    print(f"  - {emp.user.username}")

# Test waakdienst availability  
waakdienst_available = checker.get_available_employees(
    start_time=start_time,
    end_time=end_time,
    shift_type="waakdienst"
)
print(f"Employees available for waakdienst: {len(waakdienst_available)}")
for emp in waakdienst_available:
    print(f"  - {emp.user.username}")

print("\n=== DIAGNOSTIC COMPLETE ===")
```

**Expected Issues & Solutions**:
- **No employee profiles**: Need to create them
- **No skills assigned**: Skills system not working
- **availability flags False**: Need to set them correctly

### Step 5: Create Test Data

If the diagnostic shows missing data, create test employees:

```python
# === CREATE TEST EMPLOYEES ===
from team_planner.utils.seeding import seed_demo_data

print("Creating test employees...")
summary = seed_demo_data(
    count=8,  # Create 8 test employees
    create_admin=True,
    admin_username="admin",
    admin_password="AdminPassword123!"
)

print(f"Created {summary.created} employees")
print(f"Team: {summary.team}")
print(f"Usernames: {summary.usernames}")
print(f"Categories: {summary.categories}")
```

**Re-run the diagnostic** to verify employees now have skills.

## 🧪 **PHASE 3: Fix & Test Core Functionality**

### Step 6: Run Targeted Tests

Now test specific functionality:

```bash
# Test employee availability detection
python3 manage.py test team_planner.orchestrators.tests.ConstraintCheckerTestCase.test_get_available_employees_incidents -v 2

# Test fairness calculation
python3 manage.py test team_planner.orchestrators.tests.FairnessCalculatorTestCase -v 2

# Test orchestration workflow
python3 manage.py test team_planner.orchestrators.tests.ShiftOrchestratorTestCase.test_preview_schedule_basic -v 2
```

### Step 7: Fix Skills Assignment

If skills aren't being assigned properly, fix the skill assignment method:

```bash
python3 manage.py shell
```

```python
# === FIX SKILLS ASSIGNMENT ===
from team_planner.employees.models import EmployeeProfile, EmployeeSkill

# Create required skills if they don't exist
incidents_skill, created = EmployeeSkill.objects.get_or_create(
    name="incidents",
    defaults={
        "description": "Incidents - Business hours shift management (Monday-Friday 8-17)"
    }
)
print(f"Incidents skill: {'created' if created else 'already exists'}")

waakdienst_skill, created = EmployeeSkill.objects.get_or_create(
    name="waakdienst", 
    defaults={
        "description": "Waakdienst - On-call/standby shifts (evenings, nights, weekends)"
    }
)
print(f"Waakdienst skill: {'created' if created else 'already exists'}")

# Assign skills to all employees based on their availability flags
profiles = EmployeeProfile.objects.all()
for profile in profiles:
    print(f"\nProcessing {profile.user.username}:")
    
    # Assign incidents skill if available
    if profile.available_for_incidents:
        profile.skills.add(incidents_skill)
        print(f"  ✓ Added incidents skill")
    
    # Assign waakdienst skill if available  
    if profile.available_for_waakdienst:
        profile.skills.add(waakdienst_skill)
        print(f"  ✓ Added waakdienst skill")
        
    skills = list(profile.skills.values_list('name', flat=True))
    print(f"  Final skills: {skills}")

print("\n=== SKILLS ASSIGNMENT COMPLETE ===")
```

### Step 8: Test Schedule Generation

Test if orchestration now works:

```python
# === TEST SCHEDULE GENERATION ===
from team_planner.orchestrators.algorithms import generate_schedule
from team_planner.teams.models import Team
from datetime import datetime, timedelta
import zoneinfo

# Get test team
team = Team.objects.first()
if not team:
    print("ERROR: No teams found. Create a team first.")
    exit()

print(f"Testing schedule generation for team: {team.name}")

# Set up test period (one week)
tz = zoneinfo.ZoneInfo("Europe/Amsterdam")
start_date = datetime(2025, 10, 7, tzinfo=tz)  # Monday
end_date = start_date + timedelta(days=7)      # Next Monday

print(f"Period: {start_date.date()} to {end_date.date()}")

# Test incidents orchestration
try:
    result = generate_schedule(
        team=team,
        start_date=start_date,
        end_date=end_date,
        shift_types={
            'incidents': True,
            'incidents_standby': False,
            'waakdienst': False
        },
        preview_mode=True
    )
    
    print(f"\n✓ Schedule generation SUCCESS!")
    print(f"  Incidents shifts: {result.get('incidents_shifts', 0)}")
    print(f"  Total shifts: {result.get('total_shifts', 0)}")
    
    if result.get('total_shifts', 0) > 0:
        print("🎉 CORE FUNCTIONALITY IS WORKING!")
    else:
        print("⚠️  Schedule generated but no shifts created")
        
except Exception as e:
    print(f"❌ Schedule generation FAILED: {e}")
    import traceback
    traceback.print_exc()
```

## 🎯 **PHASE 4: Fix Authentication & API Tests**

### Step 9: Fix Test Authentication

Create a test user with proper permissions:

```python
# === FIX TEST AUTHENTICATION ===
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from rest_framework.authtoken.models import Token

User = get_user_model()

# Create staff test user
test_user, created = User.objects.get_or_create(
    username="teststaff",
    defaults={
        "email": "test@teamplanner.local",
        "is_staff": True,
        "is_active": True,
        "first_name": "Test",
        "last_name": "Staff"
    }
)

if created:
    test_user.set_password("TestPassword123!")
    test_user.save()
    print(f"✓ Created test staff user: {test_user.username}")

# Create auth token
token, created = Token.objects.get_or_create(user=test_user)
print(f"✓ Auth token: {token.key}")

# Add necessary permissions
permissions = Permission.objects.filter(
    content_type__app_label__in=['orchestrators', 'shifts', 'teams', 'employees']
)
test_user.user_permissions.set(permissions)
print(f"✓ Added {permissions.count()} permissions")
```

### Step 10: Test API Endpoints

Test the orchestration API:

```bash
# Test API with curl (replace TOKEN with actual token from previous step)
curl -H "Authorization: Token YOUR_TOKEN_HERE" \
     -H "Content-Type: application/json" \
     -X POST \
     -d '{"team_id": 1, "start_date": "2025-10-07", "end_date": "2025-10-14", "shift_types": ["incidents"], "preview": true}' \
     http://localhost:8000/api/orchestrator/schedule/
```

## 🖥️ **PHASE 5: Frontend Integration**

### Step 11: Fix Frontend Issues

```bash
cd frontend

# Fix ESLint config
npm install @typescript-eslint/eslint-plugin @typescript-eslint/parser --save-dev

# Run tests
npm test

# Start development server
npm run dev
```

### Step 12: Test Full Stack

1. **Start backend**:
```bash
# Terminal 1
export DATABASE_URL=sqlite:///db.sqlite3
export DJANGO_SETTINGS_MODULE=config.settings.local
python3 manage.py runserver
```

2. **Start frontend**:
```bash
# Terminal 2  
cd frontend
npm run dev
```

3. **Test workflow**:
   - Visit http://localhost:5173
   - Login with admin credentials
   - Navigate to orchestrator page
   - Try generating a schedule

## 🧪 **PHASE 6: Verify All Tests**

### Step 13: Run Full Test Suite

```bash
# Run all tests
export DATABASE_URL=sqlite:///db.sqlite3
export DJANGO_SETTINGS_MODULE=config.settings.local
python3 manage.py test --verbosity=2

# Target should be 90%+ pass rate (up from current 74%)
```

### Step 14: Fix Remaining Test Failures

Focus on these test categories in order:
1. `ConstraintCheckerTestCase` - Employee availability
2. `FairnessCalculatorTestCase` - Fairness calculations  
3. `OrchestrationAPITestCase` - API authentication
4. `ShiftOrchestratorTestCase` - Schedule generation

## 📚 **TROUBLESHOOTING GUIDE**

### Common Issues & Solutions

**Issue**: "No employees available for shifts"
**Solution**: Run employee diagnostic (Step 4) and skills assignment (Step 7)

**Issue**: "Authentication failed in tests"  
**Solution**: Run test user creation (Step 9)

**Issue**: "ESLint configuration error"
**Solution**: Reinstall ESLint dependencies (Step 11)

**Issue**: "Database migration errors"
**Solution**: 
```bash
python3 manage.py migrate --fake-initial
python3 manage.py migrate
```

**Issue**: "Import errors in Python"
**Solution**: Ensure you're in project root and environment is loaded

### Getting Help

**Debug Mode**: Always run with `DJANGO_DEBUG=True` for detailed errors

**Logging**: Check logs with:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

**Database Inspection**:
```bash
python3 manage.py shell
>>> from django.db import connection
>>> connection.queries  # See recent SQL queries
```

## 🎯 **SUCCESS CHECKLIST**

- [ ] Environment variables configured
- [ ] Database migrated and superuser created
- [ ] Employee diagnostic shows employees with skills
- [ ] At least one orchestration test passes
- [ ] Test user with auth token created
- [ ] API returns successful response
- [ ] Frontend runs without errors
- [ ] Full stack workflow completes
- [ ] Test pass rate > 90%

## 🚀 **Next Steps After Setup**

Once this setup is complete, you'll have:
1. ✅ Working employee availability detection
2. ✅ Functional schedule generation  
3. ✅ API authentication working
4. ✅ Frontend-backend integration
5. ✅ Comprehensive test coverage

From there, you can focus on:
- Advanced scheduling algorithms
- Real-time updates
- Enhanced UI/UX
- Performance optimization
- Production deployment

This guide transforms your project from a cleaned codebase into a fully functional team scheduling system. Follow the phases in order, and you'll have a working system within a few days!
