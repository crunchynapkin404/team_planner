#!/usr/bin/env python3
"""
Debug script to test orchestrator preview_only behavior
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

def test_orchestrator():
    print("=== Testing Orchestrator Behavior ===")
    
    # Get a team
    teams = Team.objects.all()
    if not teams:
        print("❌ No teams found in database")
        return
    
    team = teams.first()
    print(f"✅ Using team: {team.name} (ID: {team.pk})")
    
    # Test dates
    start_date = timezone.make_aware(datetime.combine(date(2025, 10, 1), datetime.min.time()))
    end_date = timezone.make_aware(datetime.combine(date(2025, 10, 7), datetime.max.time()))
    
    print(f"📅 Date range: {start_date} to {end_date}")
    
    # Count existing shifts (simplified query)
    existing_shifts = Shift.objects.all().count()
    print(f"📊 Total existing shifts in database: {existing_shifts}")
    
    # Test with dry_run=False (should create shifts)
    print("\n--- Testing with dry_run=False ---")
    orchestrator = UnifiedOrchestrator(
        team=team,
        start_date=start_date,
        end_date=end_date,
        shift_types=[ShiftType.INCIDENTS],
        dry_run=False,
        user=None
    )
    
    print(f"🔧 Created orchestrator with dry_run={orchestrator.dry_run}")
    
    try:
        print("🚀 Calling apply_schedule()...")
        result = orchestrator.apply_schedule()
        print(f"✅ apply_schedule() result:")
        print(f"   - Total shifts: {result.get('total_shifts', 0)}")
        print(f"   - Created shifts: {len(result.get('created_shifts', []))}")
        print(f"   - Employees assigned: {result.get('employees_assigned', 0)}")
        
        # Count shifts after
        new_total_shifts = Shift.objects.all().count()
        print(f"📊 Total shifts after orchestration: {new_total_shifts}")
        print(f"📈 New shifts created: {new_total_shifts - existing_shifts}")
        
    except Exception as e:
        print(f"❌ Error in apply_schedule(): {e}")
        import traceback
        traceback.print_exc()
    
    print("\n--- Testing API behavior simulation ---")
    # Simulate what the API does
    preview_only = False  # This is what we fixed in the frontend/API
    dry_run = preview_only  # This is what the API passes to UnifiedOrchestrator
    
    print(f"📤 API would send: preview_only={preview_only}")
    print(f"🔧 UnifiedOrchestrator gets: dry_run={dry_run}")
    
    if preview_only:
        print("� API would call: orchestrator.preview_schedule()")
    else:
        print("💾 API would call: orchestrator.apply_schedule()")
        print(f"🔍 But apply_schedule() checks: if self.dry_run ({dry_run}):")
        if dry_run:
            print("⚠️  Would switch to preview_schedule() anyway!")
        else:
            print("✅ Would proceed with actual scheduling")

if __name__ == "__main__":
    test_orchestrator()
