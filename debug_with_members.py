#!/usr/bin/env python3
"""
Debug script to test orchestrator with a team that has members
"""
import os
import sys
import django

# Add the project root to Python path
sys.path.insert(0, '/home/vscode/team_planner')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
django.setup()

from datetime import datetime, date
from django.utils import timezone
from team_planner.teams.models import Team
from team_planner.shifts.models import ShiftType, Shift
from team_planner.orchestrators.unified import UnifiedOrchestrator
from team_planner.users.models import User

def test_with_members():
    print("=== Testing Orchestrator with Team that Has Members ===")
    
    # Get A-Team which has 15 members
    try:
        team = Team.objects.get(name="A-Team")
        print(f"✅ Using team: {team.name} (ID: {team.pk})")
        print(f"👥 Team members: {team.members.count()}")
    except Team.DoesNotExist:
        print("❌ A-Team not found")
        return
    
    # Get a test user for the orchestration run
    user = User.objects.first()
    if not user:
        print("❌ No users found")
        return
    
    # Test dates
    start_date = timezone.make_aware(datetime.combine(date(2025, 10, 1), datetime.min.time()))
    end_date = timezone.make_aware(datetime.combine(date(2025, 10, 7), datetime.max.time()))
    
    print(f"📅 Date range: {start_date} to {end_date}")
    
    # Count existing shifts
    existing_shifts = Shift.objects.all().count()
    print(f"📊 Total existing shifts in database: {existing_shifts}")
    
    # Test with dry_run=False (should create shifts)
    print("\n--- Testing with Team That Has Members ---")
    orchestrator = UnifiedOrchestrator(
        team=team,
        start_date=start_date,
        end_date=end_date,
        shift_types=[ShiftType.INCIDENTS],
        dry_run=False,
        user=user,
    )
    
    print(f"🔧 Created orchestrator with dry_run={orchestrator.dry_run}")
    
    try:
        print("🚀 Calling apply_schedule()...")
        result = orchestrator.apply_schedule()
        print(f"✅ apply_schedule() result:")
        print(f"   - Total shifts: {result.get('total_shifts', 0)}")
        print(f"   - Created shifts: {len(result.get('created_shifts', []))}")
        print(f"   - Employees assigned: {result.get('employees_assigned', 0)}")
        print(f"   - Assignments: {len(result.get('assignments', []))}")
        
        # Count shifts after
        new_total_shifts = Shift.objects.all().count()
        print(f"📊 Total shifts after orchestration: {new_total_shifts}")
        print(f"📈 New shifts created: {new_total_shifts - existing_shifts}")
        
        if result.get('assignments'):
            print("\n📋 Sample assignments:")
            for i, assignment in enumerate(result['assignments'][:3]):
                print(f"   {i+1}. {assignment.get('assigned_employee_name', 'Unknown')} - {assignment.get('shift_type', 'Unknown')} - {assignment.get('start_datetime', 'Unknown date')}")
        
    except Exception as e:
        print(f"❌ Error in apply_schedule(): {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_with_members()
