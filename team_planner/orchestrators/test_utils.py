"""
Test utilities and fixtures for the Team Planner project.

This module provides common test fixtures and utilities to create test data
consistently across all test suites.
"""
from datetime import datetime, timedelta
from django.contrib.auth import get_user_model
from django.utils import timezone

from team_planner.teams.models import Department, Team
from team_planner.employees.models import EmployeeProfile
from team_planner.shifts.models import ShiftTemplate, ShiftType
from team_planner.leaves.models import LeaveType

User = get_user_model()


class TestDataFactory:
    """Factory for creating test data with proper relationships."""
    
    @staticmethod
    def create_department(name="Test Department", manager=None):
        """Create a test department."""
        return Department.objects.create(
            name=name,
            description=f"Description for {name}",
            manager=manager
        )
    
    @staticmethod
    def create_team(name="Test Team", department=None, manager=None):
        """Create a test team with required department."""
        if department is None:
            department = TestDataFactory.create_department()
        
        return Team.objects.create(
            name=name,
            department=department,
            description=f"Description for {name}",
            manager=manager
        )
    
    @staticmethod
    def create_user(username=None, email=None, password="testpass123", **kwargs):
        """Create a test user."""
        if username is None:
            username = f"testuser_{timezone.now().timestamp()}"
        if email is None:
            email = f"{username}@example.com"
        
        return User.objects.create_user(
            username=username,
            email=email,
            password=password,
            **kwargs
        )
    
    @staticmethod
    def create_employee_profile(user, **defaults):
        """Create an employee profile for testing."""
        profile_defaults = {
            'employee_id': f'EMP{user.pk:03d}',
            'hire_date': timezone.now().date(),
            'available_for_incidents': True,
            'available_for_waakdienst': True,
        }
        profile_defaults.update(defaults)
        
        return EmployeeProfile.objects.create(
            user=user,
            **profile_defaults
        )
    
    @staticmethod
    def create_team_membership(user, team, role='member'):
        """Create a team membership for testing."""
        from team_planner.teams.models import TeamMembership
        
        return TeamMembership.objects.create(
            user=user,
            team=team,
            role=role,
            is_active=True
        )
    
    @staticmethod
    def create_shift_template(name=None, shift_type=ShiftType.INCIDENTS, **kwargs):
        """Create a shift template."""
        if name is None:
            name = f"{shift_type.title()} Shift Template"
        
        defaults = {
            'name': name,
            'shift_type': shift_type,
            'duration_hours': 8 if shift_type == ShiftType.INCIDENTS else 24,
            'description': f'Template for {shift_type} shifts'
        }
        defaults.update(kwargs)
        
        return ShiftTemplate.objects.create(**defaults)
    
    @staticmethod
    def create_leave_type(name="Vacation", **kwargs):
        """Create a leave type."""
        defaults = {
            'name': name,
            'description': f'{name} leave type',
            'requires_approval': True,
            'default_days_per_year': 25
        }
        defaults.update(kwargs)
        
        leave_type, created = LeaveType.objects.get_or_create(
            name=defaults['name'],
            defaults=defaults
        )
        return leave_type
    
    @staticmethod
    def create_test_scenario(num_employees=3, team_name="Test Team", department_name="Test Department"):
        """Create a complete test scenario with multiple employees."""
        # Create department and team
        department = TestDataFactory.create_department(name=department_name)
        team = TestDataFactory.create_team(name=team_name, department=department)
        
        # Create employees
        employees = []
        for i in range(num_employees):
            user = TestDataFactory.create_user(username=f'emp{i}')
            profile = TestDataFactory.create_employee_profile(
                user=user, 
                employee_id=f'EMP{i:03d}',
                available_for_incidents=(i % 2 == 0),  # Alternate availability
                available_for_waakdienst=(i % 3 != 0)   # Most available for waakdienst
            )
            
            # Create team membership
            TestDataFactory.create_team_membership(user, team)
            
            employees.append(user)
        
        # Create shift templates
        incidents_template = TestDataFactory.create_shift_template(
            shift_type=ShiftType.INCIDENTS
        )
        waakdienst_template = TestDataFactory.create_shift_template(
            shift_type=ShiftType.WAAKDIENST
        )
        
        # Create leave type
        leave_type = TestDataFactory.create_leave_type()
        
        return {
            'department': department,
            'team': team,
            'employees': employees,
            'incidents_template': incidents_template,
            'waakdienst_template': waakdienst_template,
            'leave_type': leave_type
        }


class BaseTestCase:
    """Base test case with common setup utilities."""
    
    def setUp(self):
        """Set up common test data."""
        # Create basic scenario
        self.test_data = TestDataFactory.create_test_scenario()
        
        # Extract commonly used objects
        self.department = self.test_data['department']
        self.team = self.test_data['team']
        self.employees = self.test_data['employees']
        self.incidents_template = self.test_data['incidents_template']
        self.waakdienst_template = self.test_data['waakdienst_template']
        self.leave_type = self.test_data['leave_type']
        
        # Create admin user
        self.admin_user = TestDataFactory.create_user(
            username='admin',
            email='admin@example.com',
            is_staff=True,
            is_superuser=True
        )
        
        # Common date ranges for testing
        self.start_date = timezone.make_aware(datetime(2025, 8, 4))  # Monday
        self.end_date = timezone.make_aware(datetime(2025, 8, 11))   # Next Monday (1 week)
        self.month_end_date = timezone.make_aware(datetime(2025, 9, 1))  # 4 weeks later
    
    def create_additional_employee(self, username=None, **kwargs):
        """Create an additional employee for this test."""
        user = TestDataFactory.create_user(username=username)
        profile = TestDataFactory.create_employee_profile(
            user=user,
            team=self.team,
            **kwargs
        )
        return user
