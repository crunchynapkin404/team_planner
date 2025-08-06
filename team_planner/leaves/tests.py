from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import date, time, timedelta

from team_planner.employees.models import EmployeeProfile
from team_planner.shifts.models import Shift, ShiftTemplate
from team_planner.leaves.models import LeaveRequest, LeaveType


User = get_user_model()


class LeaveRequestTestCase(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(username="user1", email="user1@example.com")
        self.user2 = User.objects.create_user(username="user2", email="user2@example.com")
        
        self.employee1 = EmployeeProfile.objects.create(
            user=self.user1,
            employee_id="EMP001",
            hire_date=timezone.now().date()
        )
        self.employee2 = EmployeeProfile.objects.create(
            user=self.user2,
            employee_id="EMP002",
            hire_date=timezone.now().date(),
            available_for_incidents=True,  # Enable availability for incidents
            available_for_waakdienst=True  # Enable availability for waakdienst
        )
        
        # Create a leave type
        self.leave_type = LeaveType.objects.create(
            name="vacation",
            description="Vacation leave"
        )
        
        # Create a shift template
        self.shift_template = ShiftTemplate.objects.create(
            name="Incidents Shift",
            shift_type="incidents",
            duration_hours=8
        )
        
        # Create a shift that will conflict with leave
        self.shift1 = Shift.objects.create(
            template=self.shift_template,
            assigned_employee=self.user1,
            start_datetime=timezone.make_aware(
                timezone.datetime.combine(
                    date.today() + timedelta(days=5),
                    time(9, 0)
                )
            ),
            end_datetime=timezone.make_aware(
                timezone.datetime.combine(
                    date.today() + timedelta(days=5),
                    time(17, 0)
                )
            ),
            status="confirmed"
        )

    def test_create_leave_request(self):
        """Test creating a basic leave request."""
        leave_request = LeaveRequest.objects.create(
            employee=self.user1,
            leave_type=self.leave_type,
            start_date=date.today() + timedelta(days=10),
            end_date=date.today() + timedelta(days=12),
            days_requested=3.0,
            reason="Family vacation"
        )
        
        self.assertEqual(leave_request.status, "pending")
        self.assertEqual(leave_request.employee, self.user1)
        self.assertEqual(leave_request.leave_type, self.leave_type)

    def test_shift_conflict_detection(self):
        """Test that leave requests detect shift conflicts."""
        # Create leave request that conflicts with existing shift
        leave_request = LeaveRequest.objects.create(
            employee=self.user1,
            leave_type=self.leave_type,
            start_date=date.today() + timedelta(days=4),
            end_date=date.today() + timedelta(days=6),
            days_requested=3.0,
            reason="Medical appointment"
        )
        
        # Check if conflicts are detected
        conflicting_shifts = leave_request.get_conflicting_shifts()
        self.assertEqual(conflicting_shifts.count(), 1)
        self.assertEqual(conflicting_shifts.first(), self.shift1)
        
        # Check convenience property
        self.assertTrue(leave_request.has_shift_conflicts)

    def test_no_shift_conflicts(self):
        """Test leave request with no shift conflicts."""
        # Create leave request that doesn't conflict
        leave_request = LeaveRequest.objects.create(
            employee=self.user1,
            leave_type=self.leave_type,
            start_date=date.today() + timedelta(days=20),
            end_date=date.today() + timedelta(days=22),
            days_requested=3.0,
            reason="Weekend trip"
        )
        
        # Check no conflicts
        conflicting_shifts = leave_request.get_conflicting_shifts()
        self.assertEqual(conflicting_shifts.count(), 0)
        self.assertFalse(leave_request.has_shift_conflicts)

    def test_suggested_swap_employees(self):
        """Test getting suggested employees for swap."""
        leave_request = LeaveRequest.objects.create(
            employee=self.user1,
            leave_type=self.leave_type,
            start_date=date.today() + timedelta(days=4),
            end_date=date.today() + timedelta(days=6),
            days_requested=3.0
        )
        
        suggested_employees = leave_request.get_suggested_swap_employees()
        # Should suggest employee2 who is available (returns User objects)
        self.assertIn(self.user2, suggested_employees)

    def test_can_be_approved_no_conflicts(self):
        """Test that leave without conflicts can be approved."""
        leave_request = LeaveRequest.objects.create(
            employee=self.user1,
            leave_type=self.leave_type,
            start_date=date.today() + timedelta(days=20),
            end_date=date.today() + timedelta(days=22),
            days_requested=3.0
        )
        
        self.assertTrue(leave_request.can_be_approved())

    def test_can_be_approved_with_conflicts(self):
        """Test that leave with conflicts cannot be automatically approved."""
        leave_request = LeaveRequest.objects.create(
            employee=self.user1,
            leave_type=self.leave_type,
            start_date=date.today() + timedelta(days=4),
            end_date=date.today() + timedelta(days=6),
            days_requested=3.0
        )
        
        # Should not be approvable due to shift conflicts
        self.assertFalse(leave_request.can_be_approved())


class LeaveRequestIntegrationTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", 
            email="test@example.com",
            name="Test User"
        )
        self.employee = EmployeeProfile.objects.create(
            user=self.user,
            employee_id="EMP001",
            hire_date=timezone.now().date()
        )
        self.leave_type = LeaveType.objects.create(
            name="vacation",
            description="Vacation leave"
        )

    def test_leave_request_str_representation(self):
        """Test string representation of leave request."""
        leave_request = LeaveRequest.objects.create(
            employee=self.user,
            leave_type=self.leave_type,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=2),
            days_requested=3.0
        )
        
        # User.get_full_name() returns "None None" since first_name/last_name are None
        expected_str = f"None None - vacation ({leave_request.start_date} to {leave_request.end_date})"
        self.assertEqual(str(leave_request), expected_str)

    def test_leave_request_status_choices(self):
        """Test that leave request status choices are valid."""
        valid_statuses = ["pending", "approved", "rejected", "cancelled"]
        
        for status in valid_statuses:
            leave_request = LeaveRequest.objects.create(
                employee=self.user,
                leave_type=self.leave_type,
                start_date=date.today(),
                end_date=date.today() + timedelta(days=1),
                days_requested=2.0,
                status=status
            )
            self.assertEqual(leave_request.status, status)

    def test_leave_type_choices(self):
        """Test that leave types work correctly."""
        leave_types = ["sick", "personal"]  # Avoid 'vacation' which already exists in setUp
        
        for i, type_name in enumerate(leave_types):
            leave_type = LeaveType.objects.create(
                name=f"{type_name}_{i}",  # Make names unique
                description=f"{type_name} leave"
            )
            leave_request = LeaveRequest.objects.create(
                employee=self.user,
                leave_type=leave_type,
                start_date=date.today(),
                end_date=date.today() + timedelta(days=1),
                days_requested=2.0
            )
            self.assertEqual(leave_request.leave_type.name, f"{type_name}_{i}")
