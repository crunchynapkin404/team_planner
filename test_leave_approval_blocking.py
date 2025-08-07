#!/usr/bin/env python
"""
Test script to verify that leave requests with conflicting shifts cannot be approved.
"""
import os
import django
from datetime import date, timedelta, datetime, time

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
django.setup()

from django.contrib.auth import get_user_model
from django.utils import timezone
from team_planner.leaves.models import LeaveRequest, LeaveType
from team_planner.shifts.models import Shift, ShiftTemplate
from team_planner.teams.models import Team, Department

User = get_user_model()

def test_leave_approval_blocking():
    """Test that leave requests with conflicts cannot be approved."""
    
    # Clean up any existing test data
    User.objects.filter(username='conflict_test_user').delete()
    
    # Create test user
    user = User.objects.create_user(
        username='conflict_test_user',
        email='conflict@test.com',
        password='testpass',
        name='Conflict Test User'
    )
    
    # Try to use existing templates, or create minimal ones
    shift_template = ShiftTemplate.objects.filter(is_active=True).first()
    if not shift_template:
        shift_template = ShiftTemplate.objects.create(
            name='Test Template',
            shift_type='incidents',
            description='Test template',
            duration_hours=8,
            is_active=True
        )
    
    # Create a conflicting shift for next week
    conflict_date = date.today() + timedelta(days=7)
    
    shift = Shift.objects.create(
        template=shift_template,
        assigned_employee=user,
        start_datetime=timezone.make_aware(
            datetime.combine(conflict_date, time(8, 0))
        ),
        end_datetime=timezone.make_aware(
            datetime.combine(conflict_date, time(17, 0))
        ),
        status='confirmed'
    )
    
    # Get or create leave type
    leave_type, _ = LeaveType.objects.get_or_create(
        name='Vacation',
        defaults={
            'description': 'Vacation leave',
            'requires_approval': True,
            'is_paid': True,
            'is_active': True
        }
    )
    
    # Create leave request that conflicts with the shift
    leave_request = LeaveRequest.objects.create(
        employee=user,
        leave_type=leave_type,
        start_date=conflict_date,
        end_date=conflict_date + timedelta(days=1),
        days_requested=2,
        reason='Test vacation with conflict',
        status='pending'
    )
    
    print("=== Leave Approval Conflict Test ===")
    print(f"User: {user.get_full_name()}")
    print(f"Shift: {shift.start_datetime} to {shift.end_datetime}")
    print(f"Leave: {leave_request.start_date} to {leave_request.end_date}")
    print()
    
    # Check if conflicts are detected
    conflicts = leave_request.get_conflicting_shifts()
    print(f"Conflicting shifts detected: {conflicts.count()}")
    print(f"Has shift conflicts: {leave_request.has_shift_conflicts}")
    print()
    
    # Check if leave can be approved
    can_approve = leave_request.can_be_approved()
    print(f"Can be approved: {can_approve}")
    
    if not can_approve:
        blocking_message = leave_request.get_blocking_message()
        print(f"Blocking message: {blocking_message}")
        print("✅ PASS: Leave request is correctly blocked due to conflicts")
    else:
        print("❌ FAIL: Leave request should be blocked but isn't")
    
    print()
    
    # Test what happens when we try to approve anyway
    if not can_approve:
        print("Testing approval attempt on conflicted leave request...")
        try:
            # This should not work in practice due to validation
            leave_request.status = 'approved'
            leave_request.save()
            print("❌ FAIL: Leave was approved despite conflicts")
        except Exception as e:
            print(f"Exception during approval: {e}")
    
    # Show what would need to happen to approve
    print("\nTo approve this leave request:")
    print("1. Create a swap request for the conflicting shift")
    print("2. Have the swap request approved")
    print("3. Then the leave request can be approved")
    
    # Clean up
    leave_request.delete()
    shift.delete()
    user.delete()
    
    print("\nTest completed and cleaned up.")

if __name__ == '__main__':
    test_leave_approval_blocking()
