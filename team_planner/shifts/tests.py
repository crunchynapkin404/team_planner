from datetime import datetime, timedelta
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from .models import Shift, ShiftTemplate, SwapRequest
from team_planner.employees.models import EmployeeProfile
from team_planner.leaves.models import LeaveRequest, LeaveType

User = get_user_model()


class SwapRequestTestCase(TestCase):
    """Test cases for swap request functionality."""
    
    def setUp(self):
        """Set up test data."""
        # Create users
        self.user1 = User.objects.create_user(
            username="engineer1",
            email="engineer1@example.com",
            password="testpass123"
        )
        self.user2 = User.objects.create_user(
            username="engineer2", 
            email="engineer2@example.com",
            password="testpass123"
        )
        self.manager = User.objects.create_user(
            username="manager",
            email="manager@example.com",
            password="testpass123",
            is_staff=True
        )
        
        # Create employee profiles
        self.profile1 = EmployeeProfile.objects.create(
            user=self.user1,
            employee_id="EMP001",
            hire_date=timezone.now().date(),
            available_for_incidents=True,
            available_for_waakdienst=True
        )
        self.profile2 = EmployeeProfile.objects.create(
            user=self.user2,
            employee_id="EMP002",
            hire_date=timezone.now().date(),
            available_for_incidents=True,
            available_for_waakdienst=False
        )
        
        # Create shift template
        self.template = ShiftTemplate.objects.create(
            name="Test Incidents Shift",
            shift_type="incidents",
            duration_hours=40
        )
        
        # Create shifts
        start_time = timezone.now() + timedelta(days=7)
        self.shift1 = Shift.objects.create(
            template=self.template,
            assigned_employee=self.user1,
            start_datetime=start_time,
            end_datetime=start_time + timedelta(hours=8),
            status="scheduled"
        )
        self.shift2 = Shift.objects.create(
            template=self.template,
            assigned_employee=self.user2,
            start_datetime=start_time + timedelta(days=1),
            end_datetime=start_time + timedelta(days=1, hours=8),
            status="scheduled"
        )
        
        self.client = Client()
    
    def test_create_swap_request(self):
        """Test creating a swap request."""
        self.client.login(username="engineer1", password="testpass123")
        
        response = self.client.get(
            reverse("shifts:create_swap_request", kwargs={"shift_pk": self.shift1.pk})
        )
        self.assertEqual(response.status_code, 200)
        
        # Create swap request via POST
        data = {
            "target_employee": self.user2.pk,
            "reason": "Need to swap for personal reasons"
        }
        response = self.client.post(
            reverse("shifts:create_swap_request", kwargs={"shift_pk": self.shift1.pk}),
            data
        )
        
        # Should redirect on success
        self.assertEqual(response.status_code, 302)
        
        # Check swap request was created
        swap_request = SwapRequest.objects.get(requesting_shift=self.shift1)
        self.assertEqual(swap_request.requesting_employee, self.user1)
        self.assertEqual(swap_request.target_employee, self.user2)
        self.assertEqual(swap_request.status, "pending")
    
    def test_swap_request_validation(self):
        """Test swap request business logic validation."""
        swap_request = SwapRequest.objects.create(
            requesting_employee=self.user1,
            target_employee=self.user2,
            requesting_shift=self.shift1,
            reason="Test swap"
        )
        
        # Test validation
        errors = swap_request.validate_swap()
        self.assertEqual(len(errors), 0)  # Should be valid
        
        # Test invalid swap (same employee)
        invalid_swap = SwapRequest(
            requesting_employee=self.user1,
            target_employee=self.user1,
            requesting_shift=self.shift1,
            reason="Invalid swap"
        )
        errors = invalid_swap.validate_swap()
        self.assertIn("Cannot swap shift with yourself", errors)
    
    def test_swap_approval(self):
        """Test swap request approval process."""
        swap_request = SwapRequest.objects.create(
            requesting_employee=self.user1,
            target_employee=self.user2,
            requesting_shift=self.shift1,
            reason="Test swap"
        )
        
        # Test approval
        swap_request.approve(self.manager, "Approved for testing")
        
        self.assertEqual(swap_request.status, "approved")
        self.assertEqual(swap_request.approved_by, self.manager)
        self.assertIsNotNone(swap_request.approved_datetime)
        
        # Check that shift was reassigned
        self.shift1.refresh_from_db()
        self.assertEqual(self.shift1.assigned_employee, self.user2)


class LeaveShiftIntegrationTestCase(TestCase):
    """Test cases for leave request and shift integration."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="engineer",
            email="engineer@example.com", 
            password="testpass123"
        )
        
        self.profile = EmployeeProfile.objects.create(
            user=self.user,
            employee_id="EMP001",
            hire_date=timezone.now().date(),
            available_for_incidents=True
        )
        
        # Create leave type
        self.leave_type = LeaveType.objects.create(
            name="Annual Leave",
            default_days_per_year=25,
            is_paid=True
        )
        
        # Create shift template
        self.template = ShiftTemplate.objects.create(
            name="Test Incidents Shift",
            shift_type="incidents",
            duration_hours=40
        )
        
        # Create shift during leave period
        start_time = timezone.now() + timedelta(days=7)
        self.shift = Shift.objects.create(
            template=self.template,
            assigned_employee=self.user,
            start_datetime=start_time,
            end_datetime=start_time + timedelta(hours=8),
            status="scheduled"
        )
    
    def test_leave_request_conflict_detection(self):
        """Test that leave requests detect shift conflicts."""
        leave_request = LeaveRequest.objects.create(
            employee=self.user,
            leave_type=self.leave_type,
            start_date=self.shift.start_datetime.date(),
            end_date=self.shift.end_datetime.date(),
            days_requested=1,
            reason="Test leave"
        )
        
        # Check conflict detection
        self.assertTrue(leave_request.has_shift_conflicts)
        conflicting_shifts = leave_request.get_conflicting_shifts()
        self.assertIn(self.shift, conflicting_shifts)
        
        # Check that leave cannot be approved without resolving conflicts
        self.assertFalse(leave_request.can_be_approved())
        
        # Check blocking message
        blocking_message = leave_request.get_blocking_message()
        self.assertIsNotNone(blocking_message)
        self.assertIn("conflicts with this leave request", blocking_message)
    
    def test_leave_approval_after_swap(self):
        """Test that leave can be approved after shift conflicts are resolved."""
        # Create leave request with conflict
        leave_request = LeaveRequest.objects.create(
            employee=self.user,
            leave_type=self.leave_type,
            start_date=self.shift.start_datetime.date(),
            end_date=self.shift.end_datetime.date(),
            days_requested=1,
            reason="Test leave"
        )
        
        # Initially cannot be approved
        self.assertFalse(leave_request.can_be_approved())
        
        # Create another user to swap with
        other_user = User.objects.create_user(
            username="other_engineer",
            email="other@example.com",
            password="testpass123"
        )
        EmployeeProfile.objects.create(
            user=other_user,
            employee_id="EMP002",
            hire_date=timezone.now().date(),
            available_for_incidents=True
        )
        
        # Create and approve swap request
        swap_request = SwapRequest.objects.create(
            requesting_employee=self.user,
            target_employee=other_user,
            requesting_shift=self.shift,
            reason="For leave"
        )
        swap_request.approve(other_user, "Approved")
        
        # Now leave should be approvable
        self.assertTrue(leave_request.can_be_approved())
        
        # Verify shift was reassigned
        self.shift.refresh_from_db()
        self.assertEqual(self.shift.assigned_employee, other_user)


class PhaseThreeIntegrationTestCase(TestCase):
    """Integration tests for Phase 3 functionality."""
    
    def test_phase_three_models_exist(self):
        """Test that all Phase 3 models are properly created."""
        # Test SwapRequest model
        self.assertTrue(hasattr(SwapRequest, 'requesting_employee'))
        self.assertTrue(hasattr(SwapRequest, 'target_employee'))
        self.assertTrue(hasattr(SwapRequest, 'requesting_shift'))
        self.assertTrue(hasattr(SwapRequest, 'status'))
        
        # Test SwapRequest methods
        self.assertTrue(hasattr(SwapRequest, 'approve'))
        self.assertTrue(hasattr(SwapRequest, 'reject'))
        self.assertTrue(hasattr(SwapRequest, 'cancel'))
        self.assertTrue(hasattr(SwapRequest, 'validate_swap'))
        
        # Test LeaveRequest enhancements
        self.assertTrue(hasattr(LeaveRequest, 'get_conflicting_shifts'))
        self.assertTrue(hasattr(LeaveRequest, 'has_shift_conflicts'))
        self.assertTrue(hasattr(LeaveRequest, 'get_suggested_swap_employees'))
        self.assertTrue(hasattr(LeaveRequest, 'can_be_approved'))
    
    def test_urls_configured(self):
        """Test that URL patterns are properly configured."""
        from django.urls import reverse
        
        # Test shift URLs
        shift_urls = [
            "shifts:shift_list",
            "shifts:swap_list",
            "shifts:bulk_swap_approval",
        ]
        
        for url_name in shift_urls:
            try:
                url = reverse(url_name)
                self.assertIsInstance(url, str)
            except:
                self.fail(f"URL {url_name} not configured properly")
        
        # Test leave URLs  
        leave_urls = [
            "leaves:dashboard",
            "leaves:leave_request_list",
            "leaves:create_leave_request",
        ]
        
        for url_name in leave_urls:
            try:
                url = reverse(url_name)
                self.assertIsInstance(url, str)
            except:
                self.fail(f"URL {url_name} not configured properly")
    
    def test_admin_interfaces_registered(self):
        """Test that admin interfaces are properly registered."""
        from django.contrib import admin
        from .models import Shift, SwapRequest, ShiftTemplate
        
        # Check that models are registered in admin
        self.assertIn(Shift, admin.site._registry)
        self.assertIn(SwapRequest, admin.site._registry)
        self.assertIn(ShiftTemplate, admin.site._registry)
