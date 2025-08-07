#!/usr/bin/env python
"""
Create test data to demonstrate leave approval blocking due to shift conflicts.
"""
import os
import django
from datetime import date, timedelta, datetime, time

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
django.setup()

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.authtoken.models import Token
from team_planner.leaves.models import LeaveRequest, LeaveType
from team_planner.shifts.models import Shift, ShiftTemplate

def create_test_scenario():
    """Create a test scenario with conflicting shifts and leave request."""
    
    User = get_user_model()
    
    # Create or get test user
    user, created = User.objects.get_or_create(
        username='demo_user',
        defaults={
            'email': 'demo@test.com',
            'name': 'Demo User',
            'is_staff': True,  # Give staff permission for testing
        }
    )
    
    if created:
        user.set_password('demopass')
        user.save()
        print(f"Created new user: {user.username}")
    else:
        print(f"Using existing user: {user.username}")
    
    # Create or get token
    token, _ = Token.objects.get_or_create(user=user)
    print(f"User token: {token.key}")
    
    # Use existing template or create one
    shift_template = ShiftTemplate.objects.filter(is_active=True).first()
    if not shift_template:
        shift_template = ShiftTemplate.objects.create(
            name='Demo Incident Shift',
            shift_type='incidents',
            description='Demo incident shift for testing',
            duration_hours=8,
            is_active=True
        )
        print(f"Created new shift template: {shift_template}")
    else:
        print(f"Using existing shift template: {shift_template}")
    
    # Create a shift for next Monday
    next_monday = date.today() + timedelta(days=(7 - date.today().weekday()))
    
    # Clean up any existing conflicts
    Shift.objects.filter(
        assigned_employee=user,
        start_datetime__date=next_monday
    ).delete()
    
    shift = Shift.objects.create(
        template=shift_template,
        assigned_employee=user,
        start_datetime=timezone.make_aware(
            datetime.combine(next_monday, time(8, 0))
        ),
        end_datetime=timezone.make_aware(
            datetime.combine(next_monday, time(17, 0))
        ),
        status='confirmed'
    )
    print(f"Created shift: {shift.start_datetime} to {shift.end_datetime}")
    
    # Create leave type
    leave_type, _ = LeaveType.objects.get_or_create(
        name='Vacation',
        defaults={
            'description': 'Vacation leave',
            'requires_approval': True,
            'is_paid': True,
            'is_active': True
        }
    )
    
    # Clean up existing conflicting leave requests
    LeaveRequest.objects.filter(
        employee=user,
        start_date=next_monday
    ).delete()
    
    # Create conflicting leave request
    leave_request = LeaveRequest.objects.create(
        employee=user,
        leave_type=leave_type,
        start_date=next_monday,
        end_date=next_monday + timedelta(days=1),
        days_requested=2,
        reason='Demo vacation - will conflict with shift',
        status='pending'
    )
    
    print(f"Created leave request: {leave_request.start_date} to {leave_request.end_date}")
    print(f"Leave request ID: {leave_request.id}")
    print(f"Has conflicts: {leave_request.has_shift_conflicts}")
    print(f"Can be approved: {leave_request.can_be_approved()}")
    
    if leave_request.has_shift_conflicts:
        print(f"Blocking message: {leave_request.get_blocking_message()}")
    
    print()
    print("=== Test Scenario Created ===")
    print("You can now test the following:")
    print("1. Log in to the frontend with:")
    print(f"   Username: {user.username}")
    print(f"   Password: demopass")
    print("2. Go to Leave Requests page")
    print(f"3. Try to approve leave request ID {leave_request.id}")
    print("4. You should see that approval is blocked due to shift conflicts")
    print()
    print("Or test via API:")
    print(f"curl -X POST -H 'Authorization: Token {token.key}' \\")
    print(f"     http://localhost:8000/api/leave-requests/{leave_request.id}/approve/")

if __name__ == '__main__':
    create_test_scenario()
