#!/usr/bin/env python3
"""
Debug script to check shift type matching
"""
import os
import sys
import django

# Add the project root to Python path
sys.path.insert(0, '/home/vscode/team_planner')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
django.setup()

from team_planner.shifts.models import ShiftTemplate, ShiftType

def check_shift_types():
    print("=== Checking Shift Type Matching ===")
    
    print("📋 Available ShiftType enum values:")
    for shift_type in ShiftType:
        print(f"   - {shift_type.name} = '{shift_type.value}' (label: {shift_type.label})")
    
    print(f"\n📋 Templates in database:")
    templates = ShiftTemplate.objects.all()
    for template in templates:
        print(f"   - {template.name}: shift_type='{template.shift_type}' (active: {template.is_active})")
    
    print(f"\n🔍 Testing template lookup for 'incidents':")
    # Test the same lookup that the orchestrator uses
    incidents_template = ShiftTemplate.objects.filter(
        shift_type="incidents", is_active=True
    ).first()
    
    if incidents_template:
        print(f"   ✅ Found template: {incidents_template.name} (ID: {incidents_template.pk})")
    else:
        print(f"   ❌ No template found for shift_type='incidents'")
        
        # Check what happens if we use the enum value
        enum_template = ShiftTemplate.objects.filter(
            shift_type=ShiftType.INCIDENTS, is_active=True
        ).first()
        
        if enum_template:
            print(f"   ✅ Found template using ShiftType.INCIDENTS: {enum_template.name}")
        else:
            print(f"   ❌ No template found using ShiftType.INCIDENTS either")

if __name__ == "__main__":
    check_shift_types()
