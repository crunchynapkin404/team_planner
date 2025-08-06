"""
Comprehensive tests for the orchestrator algorithms.

This module tests all critical functionality of the shift orchestration system:
- Fair shift distribution algorithms
- Constraint checking
- Preview and application workflows
- API endpoints
"""
from datetime import datetime, timedelta
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
import json

from .models import OrchestrationRun, OrchestrationResult
from .algorithms import ShiftOrchestrator, FairnessCalculator, ConstraintChecker
from .test_utils import TestDataFactory, BaseTestCase
from team_planner.employees.models import EmployeeProfile
from team_planner.shifts.models import Shift, ShiftTemplate, ShiftType
from team_planner.leaves.models import LeaveRequest, LeaveType
from team_planner.teams.models import Team, Department

User = get_user_model()


class FairnessCalculatorTestCase(TestCase):
    """Test the fairness calculation algorithms."""
    
    def setUp(self):
        """Set up test data."""
        self.start_date = timezone.make_aware(datetime(2025, 8, 4))  # Monday
        self.end_date = timezone.make_aware(datetime(2025, 9, 1))    # Sunday (4 weeks)
        
        # Create test scenario
        scenario = TestDataFactory.create_test_scenario(num_employees=4)
        self.users = scenario['employees']
    
    def test_calculate_current_assignments_empty(self):
        """Test fairness calculation with no existing assignments."""
        calculator = FairnessCalculator(self.start_date, self.end_date)
        assignments = calculator.calculate_current_assignments(self.users)
        
        self.assertEqual(len(assignments), 0)
    
    def test_calculate_fairness_score_perfect_distribution(self):
        """Test fairness score calculation with perfect distribution."""
        # Create equal assignments for all employees
        assignments = {
            self.users[0].pk: {'incidents': 2, 'incidents_standby': 1, 'waakdienst': 1},
            self.users[1].pk: {'incidents': 2, 'incidents_standby': 1, 'waakdienst': 1},
            self.users[2].pk: {'incidents': 2, 'incidents_standby': 1, 'waakdienst': 1},
            self.users[3].pk: {'incidents': 2, 'incidents_standby': 1, 'waakdienst': 1},
        }
        
        calculator = FairnessCalculator(self.start_date, self.end_date)
        fairness_scores = calculator.calculate_fairness_score(assignments)
        
        # All scores should be 100 (perfect fairness)
        for score in fairness_scores.values():
            self.assertEqual(score, 100.0)
    
    def test_calculate_fairness_score_uneven_distribution(self):
        """Test fairness score calculation with uneven distribution."""
        # Create uneven assignments
        assignments = {
            self.users[0].pk: {'incidents': 4, 'incidents_standby': 2, 'waakdienst': 2},
            self.users[1].pk: {'incidents': 1, 'incidents_standby': 0, 'waakdienst': 0},
            self.users[2].pk: {'incidents': 2, 'incidents_standby': 1, 'waakdienst': 1},
            self.users[3].pk: {'incidents': 1, 'incidents_standby': 1, 'waakdienst': 1},
        }
        
        calculator = FairnessCalculator(self.start_date, self.end_date)
        fairness_scores = calculator.calculate_fairness_score(assignments)
        
        # User 0 should have lower fairness (over-assigned)
        # User 1 should have lower fairness (under-assigned)
        # User 2 and 3 should have better fairness
        self.assertLess(fairness_scores[self.users[0].pk], 100)
        self.assertLess(fairness_scores[self.users[1].pk], 100)


class ConstraintCheckerTestCase(TestCase):
    """Test the constraint checking algorithms."""
    
    def setUp(self):
        """Set up test data."""
        self.start_date = timezone.make_aware(datetime(2025, 8, 4))
        self.end_date = timezone.make_aware(datetime(2025, 9, 1))
        
        # Create test scenario
        scenario = TestDataFactory.create_test_scenario(num_employees=2)
        self.team = scenario['team']
        self.employees = scenario['employees']
        
        # Set specific availability for testing
        self.employees[0].employee_profile.available_for_incidents = True
        self.employees[0].employee_profile.available_for_waakdienst = True
        self.employees[0].employee_profile.save()
        
        self.employees[1].employee_profile.available_for_incidents = False
        self.employees[1].employee_profile.available_for_waakdienst = True
        self.employees[1].employee_profile.save()
    
    def test_get_available_employees_incidents(self):
        """Test getting employees available for incidents."""
        checker = ConstraintChecker(self.start_date, self.end_date, self.team.pk)
        available = checker.get_available_employees('incidents')
        
        # Only first employee should be available for incidents
        self.assertEqual(len(available), 1)
        self.assertEqual(available[0], self.employees[0])
    
    def test_get_available_employees_waakdienst(self):
        """Test getting employees available for waakdienst."""
        checker = ConstraintChecker(self.start_date, self.end_date, self.team.pk)
        available = checker.get_available_employees('waakdienst')
        
        # Both employees should be available for waakdienst
        self.assertEqual(len(available), 2)
        self.assertIn(self.employees[0], available)
        self.assertIn(self.employees[1], available)
    
    def test_check_leave_conflicts(self):
        """Test leave conflict detection."""
        # Create leave request
        leave_start = timezone.make_aware(datetime(2025, 8, 11))  # Monday of week 2
        leave_end = timezone.make_aware(datetime(2025, 8, 15))    # Friday of week 2
        
        leave_type = TestDataFactory.create_leave_type()
        LeaveRequest.objects.create(
            employee=self.employees[0],
            leave_type=leave_type,
            start_date=leave_start.date(),
            end_date=leave_end.date(),
            days_requested=5.0,
            status='approved'
        )
        
        checker = ConstraintChecker(self.start_date, self.end_date, self.team.pk)
        has_conflict = checker.check_leave_conflicts(self.employees[0], leave_start, leave_end)
        
        self.assertTrue(has_conflict)


class ShiftOrchestratorTestCase(TestCase, BaseTestCase):
    """Test the main shift orchestrator algorithm."""
    
    def setUp(self):
        """Set up test data."""
        BaseTestCase.setUp(self)
        # Use 1 week for simpler testing
        self.end_date = timezone.make_aware(datetime(2025, 8, 11))   # Next Monday (1 week)
    
    def test_preview_schedule_basic(self):
        """Test basic schedule preview functionality."""
        orchestrator = ShiftOrchestrator(
            self.start_date,
            self.end_date,
            team_id=self.team.pk,
            schedule_incidents=True,
            schedule_waakdienst=True
        )
        
        result = orchestrator.preview_schedule()
        
        # Should generate shifts for 1 week
        self.assertGreater(result['total_shifts'], 0)
        self.assertIn('employees_assigned', result)
        self.assertIn('fairness_scores', result)
    
    def test_apply_schedule_creates_shifts(self):
        """Test that applying schedule creates actual shift records."""
        orchestrator = ShiftOrchestrator(
            self.start_date,
            self.end_date,
            team_id=self.team.pk,
            schedule_incidents=True,
            schedule_waakdienst=False  # Only incidents for simpler test
        )
        
        initial_count = Shift.objects.count()
        result = orchestrator.apply_schedule()
        final_count = Shift.objects.count()
        
        # Should have created new shifts
        self.assertGreater(final_count, initial_count)
        self.assertEqual(result['total_shifts'], final_count - initial_count)
    
    def test_duplicate_detection(self):
        """Test that duplicate shifts are detected and handled."""
        # Create an existing shift
        existing_shift = Shift.objects.create(
            template=self.incidents_template,
            assigned_employee=self.employees[0],
            start_datetime=timezone.make_aware(datetime(2025, 8, 4, 8, 0)),  # Monday 8:00
            end_datetime=timezone.make_aware(datetime(2025, 8, 4, 17, 0)),   # Monday 17:00
            status='scheduled',
            auto_assigned=False
        )
        
        orchestrator = ShiftOrchestrator(
            self.start_date,
            self.end_date,
            team_id=self.team.pk,
            schedule_incidents=True,
            schedule_waakdienst=False
        )
        
        result = orchestrator.preview_schedule()
        
        # Should detect potential duplicates
        self.assertIn('potential_duplicates', result)


class OrchestrationAPITestCase(APITestCase):
    """Test the orchestration API endpoints."""
    
    def setUp(self):
        """Set up test data."""
        # Create test scenario
        scenario = TestDataFactory.create_test_scenario()
        self.team = scenario['team']
        
        # Create admin user
        self.admin_user = TestDataFactory.create_user(
            username='admin',
            email='admin@example.com',
            is_staff=True,
            is_superuser=True
        )
        
        # Use APITestCase's force_authenticate
        self.client.force_login(self.admin_user)
    
    def test_orchestrator_create_api_preview(self):
        """Test the orchestrator creation API in preview mode."""
        url = reverse('orchestrators:create_api')
        data = {
            'name': 'Test Orchestration',
            'description': 'Test description',
            'start_date': '2026-08-04',  # Future date
            'end_date': '2026-08-11',    # Future date
            'team_id': self.team.pk,
            'preview_only': 'true',
            'schedule_incidents': True,
            'schedule_waakdienst': True
        }
        
        response = self.client.post(url, json.dumps(data), content_type='application/json')
        response_data = response.json()
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response_data['success'])
        self.assertTrue(response_data['preview'])
        self.assertIn('run_id', response_data)
        self.assertGreater(response_data['total_shifts'], 0)
    
    def test_orchestrator_create_api_apply(self):
        """Test the orchestrator creation API in apply mode."""
        url = reverse('orchestrators:create_api')
        data = {
            'name': 'Test Orchestration',
            'description': 'Test description',
            'start_date': '2026-08-04',  # Future date
            'end_date': '2026-08-11',    # Future date
            'team_id': self.team.pk,
            'preview_only': 'false',
            'schedule_incidents': True,
            'schedule_waakdienst': False
        }
        
        initial_count = Shift.objects.count()
        response = self.client.post(url, json.dumps(data), content_type='application/json')
        final_count = Shift.objects.count()
        response_data = response.json()
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response_data['success'])
        self.assertTrue(response_data['applied'])
        self.assertGreater(final_count, initial_count)
    
    def test_orchestrator_create_api_validation(self):
        """Test API validation for invalid data."""
        url = reverse('orchestrators:create_api')
        
        # Test missing required fields
        data = {}
        response = self.client.post(url, json.dumps(data), content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Test invalid date range
        data = {
            'start_date': '2026-08-11',  # Future date
            'end_date': '2026-08-04',    # End before start
            'team_id': self.team.pk,
            'schedule_incidents': True
        }
        response = self.client.post(url, json.dumps(data), content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Test no shift types selected
        data = {
            'start_date': '2026-08-04',  # Future date
            'end_date': '2026-08-11',    # Future date
            'team_id': self.team.pk,
            'schedule_incidents': False,
            'schedule_waakdienst': False
        }
        response = self.client.post(url, json.dumps(data), content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_orchestrator_apply_preview_api(self):
        """Test applying a previewed orchestration."""
        # First create a preview
        create_url = reverse('orchestrators:create_api')
        create_data = {
            'name': 'Test Orchestration',
            'start_date': '2026-08-04',  # Future date
            'end_date': '2026-08-11',    # Future date
            'team_id': self.team.pk,
            'preview_only': 'true',
            'schedule_incidents': True,
            'schedule_waakdienst': False
        }
        
        create_response = self.client.post(create_url, json.dumps(create_data), content_type='application/json')
        self.assertEqual(create_response.status_code, status.HTTP_200_OK)
        
        # Then apply the preview
        apply_url = reverse('orchestrators:apply_preview_api')
        initial_count = Shift.objects.count()
        
        apply_response = self.client.post(apply_url, json.dumps({}), content_type='application/json')
        final_count = Shift.objects.count()
        apply_response_data = apply_response.json()
        
        self.assertEqual(apply_response.status_code, status.HTTP_200_OK)
        self.assertTrue(apply_response_data['success'])
        self.assertGreater(final_count, initial_count)
    
    def test_orchestrator_status_api(self):
        """Test the orchestrator status API."""
        url = reverse('orchestrators:status_api')
        response = self.client.get(url)
        response_data = response.json()
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('system_status', response_data)


class OrchestrationModelTestCase(TestCase):
    """Test the orchestration models."""
    
    def setUp(self):
        """Set up test data."""
        scenario = TestDataFactory.create_test_scenario(num_employees=1)
        self.user = TestDataFactory.create_user(username='testuser')
        self.employee = scenario['employees'][0]
    
    def test_orchestration_run_creation(self):
        """Test creating an orchestration run."""
        run = OrchestrationRun.objects.create(
            name='Test Run',
            description='Test description',
            initiated_by=self.user,
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=7),
            schedule_incidents=True,
            schedule_waakdienst=True,
            status=OrchestrationRun.Status.RUNNING
        )
        
        self.assertEqual(run.name, 'Test Run')
        self.assertEqual(run.initiated_by, self.user)
        self.assertEqual(run.status, OrchestrationRun.Status.RUNNING)
        self.assertIsNotNone(run.started_at)
    
    def test_orchestration_result_creation(self):
        """Test creating an orchestration result."""
        run = OrchestrationRun.objects.create(
            name='Test Run',
            initiated_by=self.user,
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=7),
            schedule_incidents=True,
            schedule_waakdienst=True,
            status=OrchestrationRun.Status.RUNNING
        )
        
        result = OrchestrationResult.objects.create(
            orchestration_run=run,
            employee=self.employee,
            shift_type='incidents',
            week_start_date=timezone.now().date(),
            week_end_date=timezone.now().date() + timedelta(days=6),  # Week end date
            fairness_score_before=85.5,
            fairness_score_after=90.0,
            assignment_reason='Best available candidate',
            is_applied=False
        )
        
        self.assertEqual(result.orchestration_run, run)
        self.assertEqual(result.employee, self.employee)
        self.assertEqual(result.shift_type, 'incidents')
        self.assertFalse(result.is_applied)
    
    def test_orchestration_result_str(self):
        """Test the string representation of orchestration result."""
        run = OrchestrationRun.objects.create(
            name='Test Run',
            initiated_by=self.user,
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=7),
            schedule_incidents=True,
            schedule_waakdienst=True,
            status=OrchestrationRun.Status.RUNNING
        )
        
        result = OrchestrationResult.objects.create(
            orchestration_run=run,
            employee=self.employee,
            shift_type='incidents',
            week_start_date=timezone.now().date(),
            week_end_date=timezone.now().date() + timedelta(days=6),  # Week end date
            fairness_score_before=85.5,
            fairness_score_after=90.0,
            assignment_reason='Best available candidate'
        )
        
        expected_str = f"{self.employee.username} - Incidents (Week {timezone.now().date()})"
        self.assertEqual(str(result), expected_str)


class PerformanceTestCase(TestCase, BaseTestCase):
    """Test performance characteristics of the orchestrator."""
    
    def setUp(self):
        """Set up test data for performance testing."""
        # Create large test scenario
        scenario = TestDataFactory.create_test_scenario(num_employees=20, team_name='Large Team')
        self.team = scenario['team']
        self.users = scenario['employees']
        
        # Set up dates
        self.start_date = timezone.make_aware(datetime(2025, 8, 4))   # Monday
        self.month_end_date = timezone.make_aware(datetime(2025, 9, 1))     # 4 weeks later
    
    def test_large_schedule_performance(self):
        """Test performance with a large schedule (1 month)."""
        import time
        start_time = time.time()
        
        orchestrator = ShiftOrchestrator(
            self.start_date,
            self.month_end_date,
            team_id=self.team.pk,
            schedule_incidents=True,
            schedule_waakdienst=True
        )
        
        result = orchestrator.preview_schedule()
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should complete within reasonable time (less than 10 seconds for 1 month)
        self.assertLess(duration, 10.0, f"Orchestration took {duration:.2f} seconds")
        self.assertGreater(result['total_shifts'], 0)
        
        print(f"Performance test: {result['total_shifts']} shifts generated in {duration:.2f} seconds")


class IntegrationTestCase(TestCase):
    """Integration tests for complete workflows."""
    
    def setUp(self):
        """Set up test data for integration testing."""
        # Create test scenario
        scenario = TestDataFactory.create_test_scenario(num_employees=5, team_name='Integration Test Team')
        self.team = scenario['team']
        self.employees = scenario['employees']
        
        # Create admin user
        self.admin_user = TestDataFactory.create_user(
            username='admin',
            email='admin@example.com',
            is_staff=True,
            is_superuser=True
        )
        
        self.client = Client()
        self.client.force_login(self.admin_user)
    
    def test_complete_orchestration_workflow(self):
        """Test the complete orchestration workflow from preview to application."""
        # Step 1: Create a preview
        preview_data = {
            'name': 'Integration Test Orchestration',
            'description': 'Complete workflow test',
            'start_date': '2026-08-04',  # Future date
            'end_date': '2026-08-18',    # Future date (2 weeks)
            'team_id': self.team.pk,
            'preview_only': 'true',
            'schedule_incidents': True,
            'schedule_waakdienst': True
        }
        
        preview_response = self.client.post(
            reverse('orchestrators:create_api'),
            data=json.dumps(preview_data),
            content_type='application/json'
        )
        
        self.assertEqual(preview_response.status_code, 200)
        preview_result = json.loads(preview_response.content)
        self.assertTrue(preview_result['success'])
        self.assertTrue(preview_result['preview'])
        
        # Step 2: Apply the preview
        initial_shift_count = Shift.objects.count()
        
        apply_response = self.client.post(
            reverse('orchestrators:apply_preview_api'),
            content_type='application/json'
        )
        
        self.assertEqual(apply_response.status_code, 200)
        apply_result = json.loads(apply_response.content)
        self.assertTrue(apply_result['success'])
        
        # Step 3: Verify shifts were created
        final_shift_count = Shift.objects.count()
        self.assertGreater(final_shift_count, initial_shift_count)
        
        # Step 4: Verify orchestration run status
        run = OrchestrationRun.objects.get(pk=preview_result['run_id'])
        self.assertEqual(run.status, OrchestrationRun.Status.COMPLETED)
        self.assertIsNotNone(run.completed_at)
        
        print(f"Integration test: Created {final_shift_count - initial_shift_count} shifts")
