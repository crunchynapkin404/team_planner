#!/usr/bin/env python3
"""
Team Planner - Automated Diagnostic & Setup Script

This script diagnoses the current state of your team planner system
and automatically fixes the most critical issues.

Usage:
    python3 debug_and_setup.py
"""

import os
import sys
import django
from pathlib import Path

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
os.environ.setdefault('DATABASE_URL', 'sqlite:///db.sqlite3')

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Initialize Django
django.setup()

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from rest_framework.authtoken.models import Token
from team_planner.employees.models import EmployeeProfile, EmployeeSkill
from team_planner.teams.models import Team, Department
from team_planner.utils.seeding import seed_demo_data
from datetime import datetime, timedelta
import zoneinfo

User = get_user_model()

def print_section(title):
    """Print a formatted section header"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def print_success(message):
    """Print success message"""
    print(f"✅ {message}")

def print_warning(message):
    """Print warning message"""
    print(f"⚠️  {message}")

def print_error(message):
    """Print error message"""
    print(f"❌ {message}")

def print_info(message):
    """Print info message"""
    print(f"ℹ️  {message}")

def diagnose_system():
    """Diagnose current system state"""
    print_section("SYSTEM DIAGNOSTIC")
    
    # Check users
    users = User.objects.all()
    print_info(f"Total users: {users.count()}")
    if users.count() == 0:
        print_warning("No users found in system")
    else:
        for user in users[:3]:
            print(f"   - {user.username} (staff: {user.is_staff}, active: {user.is_active})")
    
    # Check employee profiles
    profiles = EmployeeProfile.objects.all()
    print_info(f"Employee profiles: {profiles.count()}")
    
    profiles_with_skills = 0
    for profile in profiles:
        skills = profile.skills.all()
        if skills.exists():
            profiles_with_skills += 1
            print(f"   - {profile.user.username}: {[s.name for s in skills]}")
        else:
            print(f"   - {profile.user.username}: NO SKILLS")
    
    print_info(f"Profiles with skills: {profiles_with_skills}/{profiles.count()}")
    
    # Check skills
    skills = EmployeeSkill.objects.all()
    print_info(f"Available skills: {skills.count()}")
    for skill in skills:
        print(f"   - {skill.name}: {skill.description}")
    
    # Check teams
    teams = Team.objects.all()
    print_info(f"Teams: {teams.count()}")
    for team in teams[:3]:
        members = team.members.count()
        print(f"   - {team.name}: {members} members")
    
    return {
        'users': users.count(),
        'profiles': profiles.count(),
        'profiles_with_skills': profiles_with_skills,
        'skills': skills.count(),
        'teams': teams.count()
    }

def setup_required_skills():
    """Create required skills if they don't exist"""
    print_section("SETTING UP SKILLS")
    
    incidents_skill, created = EmployeeSkill.objects.get_or_create(
        name="incidents",
        defaults={
            "description": "Incidents - Business hours shift management (Monday-Friday 8-17)"
        }
    )
    if created:
        print_success("Created 'incidents' skill")
    else:
        print_info("'incidents' skill already exists")
    
    waakdienst_skill, created = EmployeeSkill.objects.get_or_create(
        name="waakdienst",
        defaults={
            "description": "Waakdienst - On-call/standby shifts (evenings, nights, weekends)"
        }
    )
    if created:
        print_success("Created 'waakdienst' skill")
    else:
        print_info("'waakdienst' skill already exists")
    
    return incidents_skill, waakdienst_skill

def assign_skills_to_employees(incidents_skill, waakdienst_skill):
    """Assign skills to employees based on availability flags"""
    print_section("ASSIGNING SKILLS TO EMPLOYEES")
    
    profiles = EmployeeProfile.objects.all()
    if profiles.count() == 0:
        print_warning("No employee profiles found")
        return
    
    for profile in profiles:
        assigned = []
        
        if profile.available_for_incidents:
            profile.skills.add(incidents_skill)
            assigned.append("incidents")
        
        if profile.available_for_waakdienst:
            profile.skills.add(waakdienst_skill)
            assigned.append("waakdienst")
        
        if assigned:
            print_success(f"{profile.user.username}: assigned {', '.join(assigned)}")
        else:
            print_warning(f"{profile.user.username}: no skills assigned (availability flags False)")

def create_sample_data():
    """Create sample employees and teams"""
    print_section("CREATING SAMPLE DATA")
    
    try:
        summary = seed_demo_data(
            count=8,
            create_admin=True,
            admin_username="admin",
            admin_password="AdminPassword123!"
        )
        
        print_success(f"Created {summary.created} employees")
        print_info(f"Team: {summary.team.name}")
        print_info(f"Usernames: {summary.usernames[:5]}...")
        print_info(f"Categories: incidents_only={summary.categories['incidents_only']}, "
                  f"waakdienst_only={summary.categories['waakdienst_only']}, "
                  f"both={summary.categories['both']}")
        
        return summary
        
    except Exception as e:
        print_error(f"Failed to create sample data: {e}")
        return None

def create_test_user():
    """Create test user with proper permissions for API testing"""
    print_section("CREATING TEST USER")
    
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
        print_success(f"Created test staff user: {test_user.username}")
    else:
        print_info(f"Test user already exists: {test_user.username}")
    
    # Create auth token
    token, created = Token.objects.get_or_create(user=test_user)
    if created:
        print_success(f"Created auth token: {token.key}")
    else:
        print_info(f"Auth token exists: {token.key}")
    
    # Add permissions
    permissions = Permission.objects.filter(
        content_type__app_label__in=['orchestrators', 'shifts', 'teams', 'employees']
    )
    test_user.user_permissions.set(permissions)
    print_success(f"Added {permissions.count()} permissions")
    
    return test_user, token

def test_availability_detection():
    """Test employee availability detection"""
    print_section("TESTING AVAILABILITY DETECTION")
    
    try:
        from team_planner.orchestrators.constraints import ConstraintChecker
        
        # Create test time range
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
        print_info(f"Employees available for incidents: {len(incidents_available)}")
        for emp in incidents_available[:3]:
            print(f"   - {emp.user.username}")
        
        # Test waakdienst availability
        waakdienst_available = checker.get_available_employees(
            start_time=start_time,
            end_time=end_time,
            shift_type="waakdienst"
        )
        print_info(f"Employees available for waakdienst: {len(waakdienst_available)}")
        for emp in waakdienst_available[:3]:
            print(f"   - {emp.user.username}")
        
        if len(incidents_available) > 0 or len(waakdienst_available) > 0:
            print_success("Availability detection is working!")
            return True
        else:
            print_error("No employees detected as available")
            return False
            
    except Exception as e:
        print_error(f"Availability detection failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_schedule_generation():
    """Test schedule generation"""
    print_section("TESTING SCHEDULE GENERATION")
    
    try:
        from team_planner.orchestrators.algorithms import generate_schedule
        
        # Get test team
        team = Team.objects.first()
        if not team:
            print_error("No teams found")
            return False
        
        print_info(f"Testing with team: {team.name}")
        
        # Set up test period
        tz = zoneinfo.ZoneInfo("Europe/Amsterdam")
        start_date = datetime(2025, 10, 7, tzinfo=tz)
        end_date = start_date + timedelta(days=7)
        
        print_info(f"Period: {start_date.date()} to {end_date.date()}")
        
        # Test schedule generation
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
        
        incidents_shifts = result.get('incidents_shifts', 0)
        total_shifts = result.get('total_shifts', 0)
        
        print_info(f"Incidents shifts: {incidents_shifts}")
        print_info(f"Total shifts: {total_shifts}")
        
        if total_shifts > 0:
            print_success("Schedule generation is working!")
            return True
        else:
            print_warning("Schedule generated but no shifts created")
            return False
            
    except Exception as e:
        print_error(f"Schedule generation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def run_critical_tests():
    """Run critical functionality tests"""
    print_section("RUNNING CRITICAL TESTS")
    
    import subprocess
    
    test_commands = [
        (
            "Employee Availability",
            ["python3", "manage.py", "test", 
             "team_planner.orchestrators.tests.ConstraintCheckerTestCase.test_get_available_employees_incidents", 
             "-v", "2"]
        ),
        (
            "Fairness Calculator", 
            ["python3", "manage.py", "test",
             "team_planner.orchestrators.tests.FairnessCalculatorTestCase.test_calculate_fairness_score_perfect_distribution",
             "-v", "2"]
        )
    ]
    
    results = {}
    for test_name, command in test_commands:
        try:
            print_info(f"Running {test_name} test...")
            result = subprocess.run(command, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                print_success(f"{test_name} test PASSED")
                results[test_name] = True
            else:
                print_error(f"{test_name} test FAILED")
                results[test_name] = False
        except Exception as e:
            print_error(f"{test_name} test ERROR: {e}")
            results[test_name] = False
    
    return results

def main():
    """Main diagnostic and setup routine"""
    print("🚀 Team Planner - Automated Diagnostic & Setup")
    print("=" * 60)
    
    # Step 1: Diagnose current state
    diagnosis = diagnose_system()
    
    # Step 2: Create sample data if needed
    if diagnosis['users'] == 0 or diagnosis['profiles'] < 3:
        print_warning("Insufficient data detected, creating sample data...")
        summary = create_sample_data()
        if summary:
            # Re-diagnose after data creation
            diagnosis = diagnose_system()
    
    # Step 3: Setup skills
    incidents_skill, waakdienst_skill = setup_required_skills()
    
    # Step 4: Assign skills to employees
    assign_skills_to_employees(incidents_skill, waakdienst_skill)
    
    # Step 5: Create test user
    test_user, token = create_test_user()
    
    # Step 6: Test availability detection
    availability_working = test_availability_detection()
    
    # Step 7: Test schedule generation
    schedule_working = test_schedule_generation()
    
    # Step 8: Run critical tests
    test_results = run_critical_tests()
    
    # Final summary
    print_section("SETUP COMPLETE - SUMMARY")
    
    print_info(f"Users: {User.objects.count()}")
    print_info(f"Employee profiles: {EmployeeProfile.objects.count()}")
    print_info(f"Teams: {Team.objects.count()}")
    print_info(f"Skills: {EmployeeSkill.objects.count()}")
    
    print("\n🔧 System Status:")
    print(f"   Availability Detection: {'✅ Working' if availability_working else '❌ Not Working'}")
    print(f"   Schedule Generation: {'✅ Working' if schedule_working else '❌ Not Working'}")
    
    print("\n🧪 Test Results:")
    for test_name, passed in test_results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"   {test_name}: {status}")
    
    print(f"\n🔑 Test Credentials:")
    print(f"   Admin User: admin / AdminPassword123!")
    print(f"   Test User: {test_user.username} / TestPassword123!")
    print(f"   API Token: {token.key}")
    
    print("\n🚀 Next Steps:")
    if availability_working and schedule_working:
        print("   ✅ Core functionality is working!")
        print("   ✅ You can now run the full test suite:")
        print("      python3 manage.py test --verbosity=2")
        print("   ✅ Start the development server:")
        print("      python3 manage.py runserver")
    else:
        print("   ⚠️  Core functionality needs debugging")
        print("   📖 See DEVELOPMENT_SETUP_GUIDE.md for detailed troubleshooting")
    
    print("\n" + "="*60)
    print("🎉 Setup script completed!")

if __name__ == "__main__":
    main()
