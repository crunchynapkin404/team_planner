#!/usr/bin/env python
"""
Create test users with different roles for permission testing.

Usage: python manage.py shell < create_test_users.py
Or: docker-compose exec django python manage.py shell < create_test_users.py
"""

from django.contrib.auth import get_user_model
from team_planner.users.models import RolePermission

User = get_user_model()

# Define test users
test_users = [
    {
        'username': 'test_superadmin',
        'email': 'superadmin@test.com',
        'password': 'TestPass123!',
        'name': 'Super Admin',
        'role': 'admin',
        'is_superuser': True,
        'is_staff': True,
    },
    {
        'username': 'test_manager',
        'email': 'manager@test.com',
        'password': 'TestPass123!',
        'name': 'Test Manager',
        'role': 'manager',
        'is_superuser': False,
        'is_staff': False,
    },
    {
        'username': 'test_planner',
        'email': 'planner@test.com',
        'password': 'TestPass123!',
        'name': 'Test Planner',
        'role': 'scheduler',
        'is_superuser': False,
        'is_staff': False,
    },
    {
        'username': 'test_employee',
        'email': 'employee@test.com',
        'password': 'TestPass123!',
        'name': 'Test Employee',
        'role': 'employee',
        'is_superuser': False,
        'is_staff': False,
    },
    {
        'username': 'test_teamlead',
        'email': 'teamlead@test.com',
        'password': 'TestPass123!',
        'name': 'Test TeamLead',
        'role': 'team_lead',
        'is_superuser': False,
        'is_staff': False,
    },
]

print("=" * 70)
print("Creating Test Users for Permission Testing")
print("=" * 70)
print()

created_users = []

for user_data in test_users:
    username = user_data['username']
    
    # Delete existing user if exists
    if User.objects.filter(username=username).exists():
        User.objects.filter(username=username).delete()
        print(f"🗑️  Deleted existing user: {username}")
    
    # Create user
    user = User.objects.create_user(
        username=user_data['username'],
        email=user_data['email'],
        password=user_data['password'],
        name=user_data['name'],
        role=user_data['role'],
        is_superuser=user_data['is_superuser'],
        is_staff=user_data['is_staff'],
        is_active=True,
        mfa_required=False,  # Disable MFA for testing
    )
    
    created_users.append(user)
    
    # Check if role permissions exist
    try:
        role_perms = RolePermission.objects.get(role=user.role)
        # Count actual permission fields
        perms_count = sum([
            role_perms.can_view_own_shifts,
            role_perms.can_view_team_shifts,
            role_perms.can_view_all_shifts,
            role_perms.can_create_shifts,
            role_perms.can_edit_own_shifts,
            role_perms.can_edit_team_shifts,
            role_perms.can_delete_shifts,
            role_perms.can_request_swap,
            role_perms.can_approve_swap,
            role_perms.can_view_all_swaps,
            role_perms.can_request_leave,
            role_perms.can_approve_leave,
            role_perms.can_view_team_leave,
            role_perms.can_run_orchestrator,
            role_perms.can_override_fairness,
            role_perms.can_manual_assign,
            role_perms.can_manage_team,
            role_perms.can_view_team_analytics,
            role_perms.can_view_reports,
            role_perms.can_export_data,
            role_perms.can_manage_users,
            role_perms.can_assign_roles,
        ])
        print(f"✅ Created: {username:20s} | Role: {user.get_role_display():15s} | Permissions: {perms_count}")
    except RolePermission.DoesNotExist:
        print(f"⚠️  Created: {username:20s} | Role: {user.get_role_display():15s} | WARNING: No permissions defined!")

print()
print("=" * 70)
print("Test Users Created Successfully!")
print("=" * 70)
print()
print("You can now obtain authentication tokens using:")
print()
for user_data in test_users:
    print(f"  curl -X POST http://localhost:8000/api/auth/login/ \\")
    print(f"    -H 'Content-Type: application/json' \\")
    print(f"    -d '{{\"username\": \"{user_data['username']}\", \"password\": \"{user_data['password']}\"}}'")
    print()

print("=" * 70)
