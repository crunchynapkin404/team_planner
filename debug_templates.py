#!/usr/bin/env python3
"""
Debug script to check what shift templates exist
"""
import os
import sys
import django

# Add the project root to Python path
sys.path.insert(0, '/home/vscode/team_planner')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
django.setup()

from team_planner.teams.models import Team
from team_planner.shifts.models import ShiftTemplate, ShiftType

def check_templates():
    print("=== Checking Shift Templates ===")
    
    all_templates = ShiftTemplate.objects.all()
    print(f"📋 Total shift templates in database: {all_templates.count()}")
    
    if all_templates.count() == 0:
        print("❌ No shift templates found in database!")
        print("   The orchestrator will try to create them automatically.")
        return
    
    # Check by shift type
    for shift_type in ShiftType:
        type_templates = all_templates.filter(shift_type=shift_type)
        print(f"📋 {shift_type.label} templates: {type_templates.count()}")
        
        if type_templates.count() > 0:
            for template in type_templates[:3]:  # Show first 3
                print(f"   - {template.name} (ID: {template.pk})")
            if type_templates.count() > 3:
                print(f"   ... and {type_templates.count() - 3} more")
                
    print("\n=== Checking Teams ===")
    teams = Team.objects.all()
    print(f"🏢 Total teams in database: {teams.count()}")
    
    for team in teams:
        print(f"   - {team.name} (ID: {team.pk})")

if __name__ == "__main__":
    check_templates()
