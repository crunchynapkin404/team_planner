#!/usr/bin/env python3
"""
Debug script to check employees and their availability
"""
import os
import sys
import django

# Add the project root to Python path
sys.path.insert(0, '/home/vscode/team_planner')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
django.setup()

from team_planner.teams.models import Team
from team_planner.employees.models import EmployeeProfile
from team_planner.users.models import User

def check_employees():
    print("=== Checking Employees ===")
    
    teams = Team.objects.all()
    
    for team in teams:
        print(f"\n🏢 Team: {team.name} (ID: {team.pk})")
        
        # Check team members
        if hasattr(team, 'members'):
            members = team.members.all()
            print(f"   👥 Team members: {members.count()}")
            
            for member in members[:5]:  # Show first 5
                try:
                    profile = EmployeeProfile.objects.get(user=member)
                    print(f"      - {member.username} (Profile ID: {profile.pk})")
                except EmployeeProfile.DoesNotExist:
                    print(f"      - {member.username} (❌ No employee profile)")
                    
            if members.count() > 5:
                print(f"      ... and {members.count() - 5} more")
        else:
            print("   ❌ Team has no members attribute")
            
        # Check if there are any employee profiles associated with this team
        profiles = EmployeeProfile.objects.filter(team=team) if hasattr(EmployeeProfile, 'team') else []
        if profiles:
            print(f"   📋 Employee profiles: {len(profiles)}")
        else:
            print("   📋 No employee profiles found for this team")
    
    print(f"\n=== Overall Statistics ===")
    print(f"👤 Total users: {User.objects.count()}")
    print(f"👥 Total employee profiles: {EmployeeProfile.objects.count()}")

if __name__ == "__main__":
    check_employees()
