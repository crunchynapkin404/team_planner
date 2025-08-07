#!/usr/bin/env python
"""
Test the new leave type conflict handling functionality.
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

def test_leave_conflict_handling():
    """Test different leave types and their conflict handling."""
    
    User = get_user_model()
    
    # Create test user
    user, created = User.objects.get_or_create(
        username='leave_test_user',
        defaults={
            'email': 'leavetest@test.com',
            'name': 'Leave Test User'
        }
    )
    
    # Get leave types
    vacation_type = LeaveType.objects.get(name='Vacation')
    leave_type = LeaveType.objects.get(name='Leave')
    
    # Get shift templates
    incidents_template = ShiftTemplate.objects.filter(shift_type='incidents').first()
    waakdienst_template = ShiftTemplate.objects.filter(shift_type='waakdienst').first()
    
    if not incidents_template:
        incidents_template = ShiftTemplate.objects.create(
            name='Test Incidents',
            shift_type='incidents',
            duration_hours=8
        )
    
    if not waakdienst_template:
        waakdienst_template = ShiftTemplate.objects.create(
            name='Test Waakdienst',
            shift_type='waakdienst',
            duration_hours=12
        )
    
    # Create test shifts for next week
    test_date = date.today() + timedelta(days=7)
    
    # Clean up any existing shifts
    Shift.objects.filter(
        assigned_employee=user,
        start_datetime__date=test_date
    ).delete()
    
    # Create an incidents shift (day shift)
    incidents_shift = Shift.objects.create(
        template=incidents_template,
        assigned_employee=user,
        start_datetime=timezone.make_aware(
            datetime.combine(test_date, time(8, 0))
        ),
        end_datetime=timezone.make_aware(
            datetime.combine(test_date, time(17, 0))
        ),
        status='confirmed'
    )
    
    # Create a waakdienst shift (evening/night shift)
    waakdienst_shift = Shift.objects.create(
        template=waakdienst_template,
        assigned_employee=user,
        start_datetime=timezone.make_aware(
            datetime.combine(test_date, time(18, 0))
        ),
        end_datetime=timezone.make_aware(
            datetime.combine(test_date + timedelta(days=1), time(6, 0))
        ),
        status='confirmed'
    )
    
    print("=== Testing Leave Type Conflict Handling ===")
    print(f"Test date: {test_date}")
    print(f"Incidents shift: {incidents_shift.start_datetime} to {incidents_shift.end_datetime}")
    print(f"Waakdienst shift: {waakdienst_shift.start_datetime} to {waakdienst_shift.end_datetime}")
    print()
    
    # Test 1: Vacation (full unavailable) - should conflict with BOTH shifts
    vacation_request = LeaveRequest(
        employee=user,
        leave_type=vacation_type,
        start_date=test_date,
        end_date=test_date,
        days_requested=1,
        reason='Test vacation',
        status='pending'
    )
    
    vacation_conflicts = vacation_request.get_conflicting_shifts()
    print(f"VACATION conflicts: {vacation_conflicts.count()} shifts")
    print(f"  - Conflicts with incidents: {vacation_conflicts.filter(template__shift_type='incidents').exists()}")
    print(f"  - Conflicts with waakdienst: {vacation_conflicts.filter(template__shift_type='waakdienst').exists()}")
    print(f"  - Can be approved: {vacation_request.can_be_approved()}")
    print()
    
    # Test 2: Leave (daytime only) - should conflict with incidents but NOT waakdienst
    leave_request = LeaveRequest(
        employee=user,
        leave_type=leave_type,
        start_date=test_date,
        end_date=test_date,
        days_requested=1,
        reason='Test leave',
        status='pending'
    )
    
    leave_conflicts = leave_request.get_conflicting_shifts()
    print(f"LEAVE conflicts: {leave_conflicts.count()} shifts")
    print(f"  - Conflicts with incidents: {leave_conflicts.filter(template__shift_type='incidents').exists()}")
    print(f"  - Conflicts with waakdienst: {leave_conflicts.filter(template__shift_type='waakdienst').exists()}")
    print(f"  - Can be approved: {leave_request.can_be_approved()}")
    print()
    
    # Test 3: Training (no conflict) - should conflict with NO shifts
    training_type = LeaveType.objects.get(name='Training')
    training_request = LeaveRequest(
        employee=user,
        leave_type=training_type,
        start_date=test_date,
        end_date=test_date,
        days_requested=1,
        reason='Test training',
        status='pending'
    )
    
    training_conflicts = training_request.get_conflicting_shifts()
    print(f"TRAINING conflicts: {training_conflicts.count()} shifts")
    print(f"  - Conflicts with incidents: {training_conflicts.filter(template__shift_type='incidents').exists()}")
    print(f"  - Conflicts with waakdienst: {training_conflicts.filter(template__shift_type='waakdienst').exists()}")
    print(f"  - Can be approved: {training_request.can_be_approved()}")
    print()
    
    # Test 4: Recurring leave
    print("=== Testing Recurring Leave ===")
    recurring_leave = LeaveRequest.objects.create(
        employee=user,
        leave_type=leave_type,
        start_date=test_date + timedelta(days=7),  # Different date to avoid conflicts
        end_date=test_date + timedelta(days=7),
        days_requested=1,
        reason='Weekly recurring leave',
        status='pending',
        is_recurring=True,
        recurrence_type='weekly',
        recurrence_end_date=test_date + timedelta(days=35)  # 5 weeks
    )
    
    instances = recurring_leave.create_recurring_instances()
    print(f"Created {len(instances)} recurring instances")
    for i, instance in enumerate(instances, 1):
        print(f"  Instance {i}: {instance.start_date} to {instance.end_date}")
    
    # Verification
    print("\n=== Verification ===")
    if vacation_conflicts.count() == 2:
        print("✅ PASS: Vacation correctly blocks all shifts")
    else:
        print("❌ FAIL: Vacation should block all shifts")
    
    if leave_conflicts.count() == 1 and leave_conflicts.filter(template__shift_type='incidents').exists():
        print("✅ PASS: Leave correctly blocks only day shifts")
    else:
        print("❌ FAIL: Leave should only block day shifts")
    
    if training_conflicts.count() == 0:
        print("✅ PASS: Training correctly blocks no shifts")
    else:
        print("❌ FAIL: Training should not block any shifts")
    
    if len(instances) == 4:  # 5 weeks total, minus the original = 4 instances
        print("✅ PASS: Recurring leave created correct number of instances")
    else:
        print(f"❌ FAIL: Expected 4 recurring instances, got {len(instances)}")
    
    # Clean up
    vacation_request.delete()
    leave_request.delete()
    training_request.delete()
    recurring_leave.delete()
    for instance in instances:
        instance.delete()
    incidents_shift.delete()
    waakdienst_shift.delete()
    
    print("\nTest completed and cleaned up.")

if __name__ == '__main__':
    test_leave_conflict_handling()
