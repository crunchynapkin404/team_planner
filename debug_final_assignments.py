#!/usr/bin/env python3
"""
Debug script to check the final shift assignments after reassignment
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
from team_planner.shifts.models import Shift
from team_planner.employees.models import RecurringLeavePattern

def check_final_assignments():
    print("=== Checking Final Shift Assignments After Reassignment ===")
    
    # Get A-Team
    try:
        team = Team.objects.get(name="A-Team")
        print(f"✅ Using team: {team.name} (ID: {team.pk})")
    except Team.DoesNotExist:
        print("❌ A-Team not found")
        return
    
    # Check recent shifts for this team (last 10)
    recent_shifts = Shift.objects.filter(
        template__shift_type="incidents"
    ).order_by('-created')[:10]
    
    print(f"\n📋 Recent Incidents Shifts:")
    for shift in recent_shifts:
        employee_name = shift.assigned_employee.username
        
        # Check if this employee has conflicts on this day
        has_pattern = RecurringLeavePattern.objects.filter(
            employee=shift.assigned_employee,
            is_active=True
        ).exists()
        
        if has_pattern:
            patterns = RecurringLeavePattern.objects.filter(
                employee=shift.assigned_employee,
                is_active=True
            )
            conflict_on_day = False
            for pattern in patterns:
                if pattern.applies_to_date(shift.start_datetime.date()):
                    conflict_on_day = True
                    break
            
            status = "❌ CONFLICT!" if conflict_on_day else "✅ No conflict"
        else:
            status = "✅ No patterns"
        
        print(f"   📅 {shift.start_datetime.date()} {shift.start_datetime.time()}-{shift.end_datetime.time()}")
        print(f"      👤 {employee_name} - {status}")
        
        if has_pattern and status == "❌ CONFLICT!":
            print(f"      ⚠️  This assignment should have been reassigned!")

if __name__ == "__main__":
    check_final_assignments()
