#!/usr/bin/env python3
"""
Debug script to check recurring leave patterns and reassignment logic
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
from team_planner.employees.models import RecurringLeavePattern
from team_planner.users.models import User

def check_reassignment_logic():
    print("=== Checking Recurring Leave Patterns and Reassignment ===")
    
    # Get A-Team
    try:
        team = Team.objects.get(name="A-Team")
        print(f"✅ Using team: {team.name} (ID: {team.pk})")
    except Team.DoesNotExist:
        print("❌ A-Team not found")
        return
    
    # Check recurring leave patterns for team members
    print(f"\n📋 Recurring Leave Patterns for Team Members:")
    members = team.members.all()
    
    for member in members:
        patterns = RecurringLeavePattern.objects.filter(
            employee=member,
            is_active=True
        )
        
        if patterns.exists():
            print(f"   👤 {member.username}:")
            for pattern in patterns:
                print(f"      - {pattern.name}")
                print(f"        Active: {pattern.is_active}")
                print(f"        From: {pattern.effective_from} to {pattern.effective_until}")
                
                # Test if pattern applies to a specific date
                test_date = date(2025, 10, 6)  # Monday
                if pattern.applies_to_date(test_date):
                    hours = pattern.get_affected_hours_for_date(test_date)
                    print(f"        ✅ Applies to {test_date}: {hours}")
                else:
                    print(f"        ❌ Does not apply to {test_date}")
        else:
            print(f"   👤 {member.username}: No recurring leave patterns")
    
    # Test the constraint checking directly
    print(f"\n🔍 Testing Constraint Checking:")
    from team_planner.orchestrators.algorithms import ConstraintChecker
    
    test_start = timezone.make_aware(datetime.combine(date(2025, 10, 6), datetime.min.time()))
    test_end = timezone.make_aware(datetime.combine(date(2025, 10, 6), datetime.max.time()))
    
    constraint_checker = ConstraintChecker(
        test_start, test_end, team_id=team.pk
    )
    
    print(f"   📅 Testing period: {test_start} to {test_end}")
    
    for member in members[:5]:  # Test first 5 members
        has_conflicts = constraint_checker.check_recurring_pattern_conflicts(
            member, test_start, test_end, "incidents"
        )
        print(f"   👤 {member.username}: recurring conflicts = {has_conflicts}")

if __name__ == "__main__":
    check_reassignment_logic()
