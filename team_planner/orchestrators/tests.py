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
from typing import Dict, cast

from .models import OrchestrationRun, OrchestrationResult
from .algorithms import ShiftOrchestrator, FairnessCalculator, ConstraintChecker
from .test_utils import TestDataFactory, BaseTestCase
from team_planner.employees.models import EmployeeProfile
from team_planner.shifts.models import Shift, ShiftTemplate, ShiftType
from team_planner.leaves.models import LeaveRequest, LeaveType
from team_planner.teams.models import Team, Department
from .anchors import Period, next_weekday_time, waakdienst_periods, business_weeks

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
        assignments = cast(Dict[int, Dict[str, float]], {
            self.users[0].pk: {'incidents': 2.0, 'incidents_standby': 1.0, 'waakdienst': 1.0},
            self.users[1].pk: {'incidents': 2.0, 'incidents_standby': 1.0, 'waakdienst': 1.0},
            self.users[2].pk: {'incidents': 2.0, 'incidents_standby': 1.0, 'waakdienst': 1.0},
            self.users[3].pk: {'incidents': 2.0, 'incidents_standby': 1.0, 'waakdienst': 1.0},
        })
        
        calculator = FairnessCalculator(self.start_date, self.end_date)
        fairness_scores = calculator.calculate_fairness_score(assignments)
        
        # All scores should be 100 (perfect fairness)
        for score in fairness_scores.values():
            self.assertEqual(score, 100.0)
    
    def test_calculate_fairness_score_uneven_distribution(self):
        """Test fairness score calculation with uneven distribution."""
        # Create uneven assignments
        assignments = cast(Dict[int, Dict[str, float]], {
            self.users[0].pk: {'incidents': 4.0, 'incidents_standby': 2.0, 'waakdienst': 2.0},
            self.users[1].pk: {'incidents': 1.0, 'incidents_standby': 0.0, 'waakdienst': 0.0},
            self.users[2].pk: {'incidents': 2.0, 'incidents_standby': 1.0, 'waakdienst': 1.0},
            self.users[3].pk: {'incidents': 1.0, 'incidents_standby': 1.0, 'waakdienst': 1.0},
        })
        
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


class AnchorHelpersTestCase(TestCase):
    def setUp(self):
        # Team with default preferences (Wed 17 → next Wed 08) in Europe/Amsterdam
        self.department = Department.objects.create(name="Ops")
        self.team = Team.objects.create(name="NOC", department=self.department)

    def test_next_weekday_time_basic(self):
        tz = timezone.get_current_timezone()
        ref = timezone.make_aware(datetime(2025, 1, 6, 7, 0))  # Mon 07:00
        nxt = next_weekday_time(ref, 0, 8, tz=tz)  # Next Mon 08:00 strictly after
        self.assertEqual(nxt.weekday(), 0)
        self.assertEqual(nxt.hour, 8)
        self.assertGreater(nxt, ref)

    def test_waakdienst_periods_no_partial(self):
        # Start inside a waakdienst period; should start at next start anchor
        start_at = timezone.make_aware(datetime(2025, 1, 8, 18, 0))  # Wed 18:00 (inside period)
        end_before = timezone.make_aware(datetime(2025, 1, 30, 0, 0))
        periods = waakdienst_periods(start_at, end_before, team=self.team)
        self.assertTrue(all(p.start < p.end for p in periods))
        self.assertTrue(all(p.end <= end_before for p in periods))
        # Ensure first period starts after the ref time (no partial inclusion)
        self.assertGreaterEqual(periods[0].start, next_weekday_time(start_at, 2, 17, tz=timezone.get_current_timezone()))

    def test_business_weeks_mon_fri(self):
        start_at = timezone.make_aware(datetime(2025, 3, 3, 10, 0))  # Mon 10:00
        end_before = timezone.make_aware(datetime(2025, 3, 24, 0, 0))
        weeks = business_weeks(start_at, end_before)
        self.assertTrue(all(w.start.weekday() == 0 and w.start.hour == 8 for w in weeks))
        self.assertTrue(all(w.end.weekday() == 4 and w.end.hour == 17 for w in weeks))
        # No partial periods beyond end_before
        self.assertTrue(all(w.end <= end_before for w in weeks))

    def test_dst_transition(self):
        # Cover EU DST start (last Sun of Mar) and end (last Sun of Oct)
        # Ensure anchors stay on wall clock times
        march_ref = timezone.make_aware(datetime(2025, 3, 26, 12, 0))  # Wed before DST start (2025-03-30)
        end_before = timezone.make_aware(datetime(2025, 4, 20, 0, 0))
        periods = waakdienst_periods(march_ref, end_before, team=self.team)
        for p in periods:
            self.assertIn(p.start.hour, (17,))
            self.assertIn(p.end.hour, (8,))


class HolidayPolicyTestCase(TestCase, BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)
        # Use 1 week horizon like BaseTestCase
        self.end_date = self.end_date  # already set by BaseTestCase
        # Ensure team skips holidays
        self.team.incidents_skip_holidays = True
        self.team.save()

    def test_incidents_skip_holiday_day(self):
        # Create a holiday on Wednesday within the week
        from team_planner.leaves.models import Holiday
        week_monday = self.start_date.date()
        wednesday = week_monday + timedelta(days=2)
        Holiday.objects.create(name="Test Holiday", date=wednesday, is_recurring=False)

        orchestrator = ShiftOrchestrator(
            self.start_date,
            self.end_date,
            team_id=self.team.pk,
            schedule_incidents=True,
            schedule_incidents_standby=False,
            schedule_waakdienst=False,
        )
        result = orchestrator.preview_schedule()
        # Expect 4 incident daily shifts (Mon/Tue/Thu/Fri), not 5
        self.assertEqual(result['incidents_shifts'], 4)
        self.assertEqual(result['total_shifts'], 4)

    def test_waakdienst_not_affected_by_holiday(self):
        # Create a holiday; waakdienst should still generate full set of daily shifts (7 per waakdienst period)
        from team_planner.leaves.models import Holiday
        from team_planner.orchestrators.anchors import next_weekday_time, get_team_tz
        Holiday.objects.create(name="Holiday", date=self.start_date.date() + timedelta(days=1), is_recurring=False)

        tz = get_team_tz(self.team)
        weekday = int(getattr(self.team, 'waakdienst_handover_weekday', 2))
        start_hour = int(getattr(self.team, 'waakdienst_start_hour', 17))
        end_hour = int(getattr(self.team, 'waakdienst_end_hour', 8))
        first_start = next_weekday_time(self.start_date, weekday, start_hour, tz=tz, strictly_after=True)
        first_end = (first_start + timedelta(days=7)).replace(hour=end_hour, minute=0, second=0, microsecond=0)

        orchestrator = ShiftOrchestrator(
            self.start_date,
            first_end,  # ensure complete waakdienst period included
            team_id=self.team.pk,
            schedule_incidents=False,
            schedule_incidents_standby=False,
            schedule_waakdienst=True,
        )
        result = orchestrator.preview_schedule()
        self.assertGreaterEqual(result['waakdienst_shifts'], 7)


class WaakdienstAnchorConfigTestCase(TestCase):
    def setUp(self):
        self.department = Department.objects.create(name="Ops")
        self.team = Team.objects.create(
            name="NOC",
            department=self.department,
            waakdienst_handover_weekday=1,  # Tuesday
            waakdienst_start_hour=18,
            waakdienst_end_hour=9,
        )
        # Choose dates that will encompass at least one full period
        self.start_date = timezone.make_aware(datetime(2025, 1, 1, 12, 0))
        self.end_date = timezone.make_aware(datetime(2025, 1, 20, 0, 0))

    def test_orchestrator_respects_team_anchors(self):
        orch = ShiftOrchestrator(
            self.start_date,
            self.end_date,
            team_id=self.team.pk,
            schedule_incidents=False,
            schedule_incidents_standby=False,
            schedule_waakdienst=True,
        )
        weeks = orch.generate_waakdienst_weeks()
        self.assertTrue(len(weeks) > 0)
        start, end, kind = weeks[0]
        # Start on Tuesday 18:00, end on next Tuesday 09:00
        self.assertEqual(start.weekday(), 1)
        self.assertEqual(start.hour, 18)
        self.assertEqual(end.weekday(), 1)
        self.assertEqual(end.hour, 9)
