#!/usr/bin/env python
"""
Create test shifts for today to demonstrate dashboard functionality.
"""
import os
import sys
import django
from datetime import datetime, timedelta
from django.utils import timezone

# Add the project directory to the Python path
sys.path.append('/home/bart/VsCode/TeamPlanner/team_planner')

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
os.environ.setdefault('DATABASE_URL', 'sqlite:///db.sqlite3')
os.environ.setdefault('USE_DOCKER', 'no')
os.environ.setdefault('DEBUG', 'True')

django.setup()

from django.contrib.auth import get_user_model
from team_planner.shifts.models import Shift, ShiftTemplate, ShiftType
from team_planner.employees.models import EmployeeProfile

User = get_user_model()

def create_test_data():
    """Create test shifts for today."""
    print("Creating test shifts for today...")
    
    today = timezone.now().date()
    start_of_day = timezone.make_aware(datetime.combine(today, datetime.min.time().replace(hour=8)))
    
    # Create users if they don't exist
    users = []
    for i, username in enumerate(['john.doe', 'jane.smith', 'alice.johnson'], 1):
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                'email': f'{username}@example.com',
                'name': username.replace('.', ' ').title(),
            }
        )
        if created:
            print(f"Created user: {user.username}")
        
        # Create employee profile
        profile, profile_created = EmployeeProfile.objects.get_or_create(
            user=user,
            defaults={
                'employee_id': f'EMP{i:03d}',
                'hire_date': today,
                'available_for_incidents': True,
                'available_for_waakdienst': True,
            }
        )
        if profile_created:
            print(f"Created employee profile for: {user.username}")
        
        users.append(user)
    
    # Create shift templates if they don't exist
    templates = {}
    for shift_type in [ShiftType.INCIDENTS, ShiftType.INCIDENTS_STANDBY, ShiftType.WAAKDIENST]:
        template, created = ShiftTemplate.objects.get_or_create(
            shift_type=shift_type,
            name=f"Default {shift_type.title()}",
            defaults={
                'description': f"Default template for {shift_type} shifts",
                'duration_hours': 9 if shift_type != ShiftType.WAAKDIENST else 24,
            }
        )
        if created:
            print(f"Created template: {template.name}")
        templates[shift_type] = template
    
    # Clear existing shifts for today
    Shift.objects.filter(
        start_datetime__date=today
    ).delete()
    print("Cleared existing shifts for today")
    
    # Create today's shifts
    shifts_to_create = [
        {
            'template': templates[ShiftType.INCIDENTS],
            'user': users[0],  # john.doe
            'start_hour': 8,
            'duration_hours': 9,
        },
        {
            'template': templates[ShiftType.INCIDENTS_STANDBY],
            'user': users[1],  # jane.smith
            'start_hour': 8,
            'duration_hours': 9,
        },
        {
            'template': templates[ShiftType.WAAKDIENST],
            'user': users[2],  # alice.johnson
            'start_hour': 0,
            'duration_hours': 24,
        },
    ]
    
    for shift_data in shifts_to_create:
        start_time = start_of_day.replace(hour=shift_data['start_hour'])
        end_time = start_time + timedelta(hours=shift_data['duration_hours'])
        
        shift = Shift.objects.create(
            template=shift_data['template'],
            assigned_employee=shift_data['user'],
            start_datetime=start_time,
            end_datetime=end_time,
            status=Shift.Status.SCHEDULED,
            auto_assigned=True,
            assignment_reason="Created for dashboard demo"
        )
        print(f"Created shift: {shift.template.shift_type} for {shift.assigned_employee.username}")
    
    print("Test data creation completed!")
    print("\nToday's assignments:")
    print(f"- Incidents: {users[0].name}")
    print(f"- Incidents-Standby: {users[1].name}")
    print(f"- Waakdienst: {users[2].name}")

if __name__ == '__main__':
    create_test_data()
