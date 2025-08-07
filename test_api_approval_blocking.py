#!/usr/bin/env python
"""
Simple test to verify API approval validation works correctly.
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
from team_planner.leaves.api import LeaveRequestViewSet
from rest_framework.test import APIRequestFactory
from rest_framework.response import Response

def test_api_approval_blocking():
    """Test that the API properly blocks approval of conflicted leave requests."""
    
    User = get_user_model()
    
    # Clean up and create test user
    User.objects.filter(username='api_test_user').delete()
    user = User.objects.create_user(
        username='api_test_user',
        email='apitest@test.com',
        password='testpass',
        name='API Test User'
    )
    
    # Give user permission to approve leave requests
    from django.contrib.auth.models import Permission
    permission = Permission.objects.get(codename='change_leaverequest')
    user.user_permissions.add(permission)
    
    # Create token for API access
    token, _ = Token.objects.get_or_create(user=user)
    
    # Use existing template or create one
    shift_template = ShiftTemplate.objects.filter(is_active=True).first()
    if not shift_template:
        shift_template = ShiftTemplate.objects.create(
            name='API Test Template',
            shift_type='incidents',
            description='API test template',
            duration_hours=8,
            is_active=True
        )
    
    # Create conflicting shift
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
    
    # Create leave type
    leave_type, _ = LeaveType.objects.get_or_create(
        name='API Test Vacation',
        defaults={
            'description': 'API test vacation leave',
            'requires_approval': True,
            'is_paid': True,
            'is_active': True
        }
    )
    
    # Create conflicting leave request
    leave_request = LeaveRequest.objects.create(
        employee=user,
        leave_type=leave_type,
        start_date=conflict_date,
        end_date=conflict_date + timedelta(days=1),
        days_requested=2,
        reason='API test vacation with conflict',
        status='pending'
    )
    
    print("=== API Leave Approval Conflict Test ===")
    print(f"User: {user.get_full_name()}")
    print(f"Leave Request ID: {leave_request.id}")
    print(f"Has conflicts: {leave_request.has_shift_conflicts}")
    print(f"Can be approved: {leave_request.can_be_approved()}")
    print()
    
    # Test API approval
    factory = APIRequestFactory()
    request = factory.post(f'/api/leave-requests/{leave_request.id}/approve/')
    request.user = user
    
    # Create viewset and test approval
    viewset = LeaveRequestViewSet()
    viewset.action = 'approve'
    viewset.kwargs = {'pk': leave_request.id}
    
    try:
        response = viewset.approve(request, pk=leave_request.id)
        
        if hasattr(response, 'status_code'):
            print(f"API Response Status: {response.status_code}")
            print(f"API Response Data: {response.data}")
            
            if response.status_code == 400:
                print("✅ PASS: API correctly blocked approval due to conflicts")
            else:
                print("❌ FAIL: API should have blocked the approval")
        else:
            print(f"Unexpected response type: {type(response)}")
            
    except Exception as e:
        print(f"Exception during API call: {e}")
    
    # Clean up
    leave_request.delete()
    shift.delete()
    user.delete()
    
    print("\nAPI test completed and cleaned up.")

if __name__ == '__main__':
    test_api_approval_blocking()
