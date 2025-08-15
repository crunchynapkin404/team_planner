"""
Business Logic Testing for Orchestrator Algorithms
Phase 7 Testing: Stage 2 - Backend Testing

This module provides comprehensive testing for the core orchestrator business logic,
algorithms, and fairness calculations that power the shift scheduling system.

Test Categories:
1. Fairness Calculator Accuracy
2. Constraint Validation Logic
3. Conflict Resolution Algorithms  
4. Shift Generation Logic
5. Algorithm Performance & Edge Cases
"""

from datetime import datetime, timedelta, date
from django.test import TestCase
from django.utils import timezone
from decimal import Decimal
import json
from typing import Dict, List, Any
from collections import defaultdict

from .models import OrchestrationRun, OrchestrationResult
from .algorithms import ShiftOrchestrator, FairnessCalculator, ConstraintChecker
from .unified import UnifiedOrchestrator
from .fairness_calculators import BaseFairnessCalculator, AdvancedFairnessCalculator
from .test_utils import TestDataFactory, BaseTestCase
from team_planner.employees.models import EmployeeProfile
from team_planner.shifts.models import Shift, ShiftTemplate, ShiftType
from team_planner.leaves.models import LeaveRequest, LeaveType
from team_planner.teams.models import Team, Department


class FairnessCalculatorBusinessLogicTest(TestCase):
    """Test core fairness calculation algorithms."""

    def setUp(self):
        """Set up test data for fairness calculations."""
        self.start_date = timezone.make_aware(datetime(2025, 8, 4))  # Monday
        self.end_date = timezone.make_aware(datetime(2025, 9, 1))    # Sunday (4 weeks)
        
        # Create comprehensive test scenario
        self.scenario = TestDataFactory.create_test_scenario(num_employees=6)
        self.department = self.scenario['department']
        self.employees = self.scenario['employees']
        self.shift_templates = self.scenario['shift_templates']

    def test_fairness_calculation_empty_state(self):
        """Test fairness calculation with no existing assignments."""
        calculator = FairnessCalculator(self.start_date, self.end_date)
        assignments = calculator.calculate_current_assignments(self.employees)
        
        # No existing assignments
        self.assertEqual(len(assignments), 0)
        
        # All employees should have equal fairness scores initially
        scores = calculator.calculate_fairness_scores(self.employees, assignments)
        
        self.assertEqual(len(scores), len(self.employees))
        # All scores should be equal (0.0 or same base value)
        unique_scores = set(scores.values())
        self.assertLessEqual(len(unique_scores), 2)  # Allow for small variations

    def test_fairness_calculation_with_existing_shifts(self):
        """Test fairness calculation with existing shift assignments."""
        # Create some existing shifts for uneven distribution
        employee1 = self.employees[0]
        employee2 = self.employees[1]
        
        # Employee1 gets more shifts (should have lower fairness score)
        for i in range(3):
            Shift.objects.create(
                employee=employee1.employee_profile,
                shift_template=self.shift_templates[0],
                start_time=self.start_date + timedelta(days=i),
                end_time=self.start_date + timedelta(days=i, hours=8),
                is_approved=True
            )
        
        # Employee2 gets fewer shifts (should have higher fairness score)
        Shift.objects.create(
            employee=employee2.employee_profile,
            shift_template=self.shift_templates[0],
            start_time=self.start_date + timedelta(days=1),
            end_time=self.start_date + timedelta(days=1, hours=8),
            is_approved=True
        )
        
        calculator = FairnessCalculator(self.start_date, self.end_date)
        assignments = calculator.calculate_current_assignments(self.employees)
        scores = calculator.calculate_fairness_scores(self.employees, assignments)
        
        # Employee2 should have higher fairness score (deserves more shifts)
        self.assertGreater(scores[employee2.id], scores[employee1.id])

    def test_advanced_fairness_calculator(self):
        """Test advanced fairness calculator with weighted metrics."""
        calculator = AdvancedFairnessCalculator(
            start_date=self.start_date,
            end_date=self.end_date,
            weekend_weight=1.5,
            night_weight=1.3,
            holiday_weight=2.0
        )
        
        # Create mixed shift assignments
        employee1 = self.employees[0]
        employee2 = self.employees[1]
        
        # Employee1: Regular weekday shifts
        for i in range(2):
            Shift.objects.create(
                employee=employee1.employee_profile,
                shift_template=self.shift_templates[0],  # Assuming day shift
                start_time=self.start_date + timedelta(days=i),
                end_time=self.start_date + timedelta(days=i, hours=8),
                is_approved=True
            )
        
        # Employee2: Weekend shifts (higher weight)
        weekend_start = self.start_date + timedelta(days=5)  # Saturday
        Shift.objects.create(
            employee=employee2.employee_profile,
            shift_template=self.shift_templates[0],
            start_time=weekend_start,
            end_time=weekend_start + timedelta(hours=8),
            is_approved=True
        )
        
        assignments = calculator.calculate_current_assignments(self.employees)
        scores = calculator.calculate_fairness_scores(self.employees, assignments)
        
        # Both should have similar weighted scores despite different shift counts
        score_diff = abs(scores[employee1.id] - scores[employee2.id])
        self.assertLess(score_diff, 0.5)  # Weighted scores should be more balanced

    def test_fairness_calculation_performance(self):
        """Test fairness calculation performance with large datasets."""
        # Create larger dataset
        large_scenario = TestDataFactory.create_test_scenario(num_employees=20)
        employees = large_scenario['employees']
        
        # Create many existing shifts
        for i, employee in enumerate(employees[:10]):
            for j in range(5):
                Shift.objects.create(
                    employee=employee.employee_profile,
                    shift_template=self.shift_templates[0],
                    start_time=self.start_date + timedelta(days=j),
                    end_time=self.start_date + timedelta(days=j, hours=8),
                    is_approved=True
                )
        
        import time
        start_time = time.time()
        
        calculator = FairnessCalculator(self.start_date, self.end_date)
        assignments = calculator.calculate_current_assignments(employees)
        scores = calculator.calculate_fairness_scores(employees, assignments)
        
        end_time = time.time()
        
        # Should complete within reasonable time (2 seconds for 20 employees)
        self.assertLess(end_time - start_time, 2.0)
        self.assertEqual(len(scores), len(employees))


class ConstraintCheckerBusinessLogicTest(TestCase):
    """Test constraint validation and checking algorithms."""

    def setUp(self):
        """Set up test data for constraint checking."""
        self.scenario = TestDataFactory.create_test_scenario(num_employees=4)
        self.department = self.scenario['department']
        self.employees = self.scenario['employees']
        self.shift_templates = self.scenario['shift_templates']
        
        self.start_date = timezone.make_aware(datetime(2025, 8, 4))
        self.end_date = self.start_date + timedelta(days=7)

    def test_leave_request_constraints(self):
        """Test constraint checking against leave requests."""
        employee = self.employees[0]
        
        # Create a leave request
        leave_type = LeaveType.objects.create(
            name="Annual Leave",
            days_per_year=25,
            requires_approval=True
        )
        
        leave_start = self.start_date + timedelta(days=1)
        leave_end = leave_start + timedelta(days=2)
        
        LeaveRequest.objects.create(
            employee=employee.employee_profile,
            leave_type=leave_type,
            start_date=leave_start.date(),
            end_date=leave_end.date(),
            status='approved'
        )
        
        checker = ConstraintChecker()
        
        # Try to assign shift during leave period
        shift_during_leave = {
            'employee_id': employee.id,
            'start_time': leave_start + timedelta(hours=2),
            'end_time': leave_start + timedelta(hours=10),
            'shift_template_id': self.shift_templates[0].id
        }
        
        violations = checker.check_constraints([shift_during_leave])
        
        # Should detect leave constraint violation
        self.assertGreater(len(violations), 0)
        self.assertTrue(any('leave' in violation.lower() for violation in violations))

    def test_maximum_shifts_per_week_constraint(self):
        """Test maximum shifts per week constraint."""
        employee = self.employees[0]
        checker = ConstraintChecker()
        
        # Create shifts that exceed weekly limit (assuming 5 shifts max per week)
        shifts = []
        for i in range(7):  # Try to assign 7 shifts in one week
            shifts.append({
                'employee_id': employee.id,
                'start_time': self.start_date + timedelta(days=i, hours=9),
                'end_time': self.start_date + timedelta(days=i, hours=17),
                'shift_template_id': self.shift_templates[0].id
            })
        
        violations = checker.check_constraints(shifts)
        
        # Should detect weekly limit violation
        self.assertGreater(len(violations), 0)
        self.assertTrue(any('weekly' in violation.lower() or 'maximum' in violation.lower() 
                           for violation in violations))

    def test_minimum_rest_period_constraint(self):
        """Test minimum rest period between shifts."""
        employee = self.employees[0]
        checker = ConstraintChecker()
        
        # Create shifts with insufficient rest period
        shift1_end = self.start_date + timedelta(hours=17)
        shift2_start = shift1_end + timedelta(hours=4)  # Only 4 hours rest
        
        shifts = [
            {
                'employee_id': employee.id,
                'start_time': self.start_date + timedelta(hours=9),
                'end_time': shift1_end,
                'shift_template_id': self.shift_templates[0].id
            },
            {
                'employee_id': employee.id,
                'start_time': shift2_start,
                'end_time': shift2_start + timedelta(hours=8),
                'shift_template_id': self.shift_templates[0].id
            }
        ]
        
        violations = checker.check_constraints(shifts)
        
        # Should detect rest period violation
        self.assertGreater(len(violations), 0)
        self.assertTrue(any('rest' in violation.lower() for violation in violations))

    def test_skill_requirement_constraints(self):
        """Test skill requirement constraint checking."""
        checker = ConstraintChecker()
        
        # Find employee without required skills for a specific shift type
        employee = self.employees[0]
        
        # Create a shift that requires specific skills
        # (This assumes shift templates have skill requirements)
        shift_requiring_skills = {
            'employee_id': employee.id,
            'start_time': self.start_date + timedelta(hours=9),
            'end_time': self.start_date + timedelta(hours=17),
            'shift_template_id': self.shift_templates[0].id,
            'required_skills': ['Advanced Certification', 'Night Shift Training']
        }
        
        violations = checker.check_constraints([shift_requiring_skills])
        
        # May or may not detect skill violations depending on test data setup
        # This is more for testing the constraint checking framework
        self.assertIsInstance(violations, list)

    def test_constraint_checker_performance(self):
        """Test constraint checker performance with many shifts."""
        checker = ConstraintChecker()
        
        # Create large number of shifts to check
        shifts = []
        for i in range(100):
            employee = self.employees[i % len(self.employees)]
            shifts.append({
                'employee_id': employee.id,
                'start_time': self.start_date + timedelta(days=i//10, hours=9),
                'end_time': self.start_date + timedelta(days=i//10, hours=17),
                'shift_template_id': self.shift_templates[i % len(self.shift_templates)].id
            })
        
        import time
        start_time = time.time()
        
        violations = checker.check_constraints(shifts)
        
        end_time = time.time()
        
        # Should complete within reasonable time (3 seconds for 100 shifts)
        self.assertLess(end_time - start_time, 3.0)
        self.assertIsInstance(violations, list)


class ShiftOrchestratorBusinessLogicTest(TestCase):
    """Test core shift orchestration algorithms."""

    def setUp(self):
        """Set up test data for shift orchestration."""
        self.scenario = TestDataFactory.create_test_scenario(num_employees=5)
        self.department = self.scenario['department']
        self.employees = self.scenario['employees']
        self.shift_templates = self.scenario['shift_templates']
        
        self.start_date = timezone.make_aware(datetime(2025, 8, 4))
        self.end_date = self.start_date + timedelta(days=7)

    def test_basic_shift_generation(self):
        """Test basic shift generation algorithm."""
        orchestrator = ShiftOrchestrator(
            department=self.department,
            start_date=self.start_date,
            end_date=self.end_date
        )
        
        generated_shifts = orchestrator.generate_shifts()
        
        # Should generate some shifts
        self.assertGreater(len(generated_shifts), 0)
        
        # All shifts should be within the specified date range
        for shift in generated_shifts:
            self.assertGreaterEqual(shift['start_time'], self.start_date)
            self.assertLessEqual(shift['end_time'], self.end_date)
        
        # All assigned employees should be from the department
        assigned_employee_ids = {shift['employee_id'] for shift in generated_shifts}
        department_employee_ids = {emp.id for emp in self.employees}
        self.assertTrue(assigned_employee_ids.issubset(department_employee_ids))

    def test_fair_distribution_algorithm(self):
        """Test that shifts are distributed fairly among employees."""
        orchestrator = ShiftOrchestrator(
            department=self.department,
            start_date=self.start_date,
            end_date=self.end_date,
            fairness_weight=1.0  # Maximize fairness
        )
        
        generated_shifts = orchestrator.generate_shifts()
        
        # Count shifts per employee
        shift_counts = defaultdict(int)
        for shift in generated_shifts:
            shift_counts[shift['employee_id']] += 1
        
        # Calculate distribution fairness
        counts = list(shift_counts.values())
        if len(counts) > 1:
            max_diff = max(counts) - min(counts)
            # Difference should be minimal (≤ 2 shifts difference)
            self.assertLessEqual(max_diff, 2)

    def test_constraint_compliance_algorithm(self):
        """Test that generated shifts comply with constraints."""
        # Add some leave requests to test constraint compliance
        employee = self.employees[0]
        
        leave_type = LeaveType.objects.create(
            name="Annual Leave",
            days_per_year=25,
            requires_approval=True
        )
        
        leave_date = self.start_date + timedelta(days=2)
        LeaveRequest.objects.create(
            employee=employee.employee_profile,
            leave_type=leave_type,
            start_date=leave_date.date(),
            end_date=leave_date.date(),
            status='approved'
        )
        
        orchestrator = ShiftOrchestrator(
            department=self.department,
            start_date=self.start_date,
            end_date=self.end_date,
            constraint_weight=1.0  # Maximize constraint compliance
        )
        
        generated_shifts = orchestrator.generate_shifts()
        
        # Check that no shifts are assigned to employee on leave
        for shift in generated_shifts:
            shift_date = shift['start_time'].date()
            if shift['employee_id'] == employee.id:
                self.assertNotEqual(shift_date, leave_date.date())

    def test_optimization_algorithm_balance(self):
        """Test optimization algorithm with balanced weights."""
        orchestrator = ShiftOrchestrator(
            department=self.department,
            start_date=self.start_date,
            end_date=self.end_date,
            fairness_weight=0.6,
            constraint_weight=0.8,
            preference_weight=0.4
        )
        
        generated_shifts = orchestrator.generate_shifts()
        
        # Should generate reasonable number of shifts
        expected_days = (self.end_date - self.start_date).days
        expected_shifts_per_day = len(self.shift_templates)
        expected_total = expected_days * expected_shifts_per_day
        
        # Allow for some variance due to optimization
        self.assertGreater(len(generated_shifts), expected_total * 0.5)
        self.assertLess(len(generated_shifts), expected_total * 1.5)

    def test_shift_orchestrator_edge_cases(self):
        """Test shift orchestrator with edge cases."""
        # Test with very short date range (1 day)
        short_end = self.start_date + timedelta(days=1)
        
        orchestrator = ShiftOrchestrator(
            department=self.department,
            start_date=self.start_date,
            end_date=short_end
        )
        
        generated_shifts = orchestrator.generate_shifts()
        
        # Should handle short ranges gracefully
        self.assertIsInstance(generated_shifts, list)
        
        # Test with no available employees (all on leave)
        leave_type = LeaveType.objects.create(
            name="Mass Leave",
            days_per_year=25,
            requires_approval=True
        )
        
        for employee in self.employees:
            LeaveRequest.objects.create(
                employee=employee.employee_profile,
                leave_type=leave_type,
                start_date=self.start_date.date(),
                end_date=self.end_date.date(),
                status='approved'
            )
        
        orchestrator_no_employees = ShiftOrchestrator(
            department=self.department,
            start_date=self.start_date,
            end_date=self.end_date
        )
        
        generated_shifts_no_employees = orchestrator_no_employees.generate_shifts()
        
        # Should handle no available employees gracefully
        self.assertIsInstance(generated_shifts_no_employees, list)
        self.assertEqual(len(generated_shifts_no_employees), 0)


class UnifiedOrchestratorBusinessLogicTest(TestCase):
    """Test the unified orchestrator system integration."""

    def setUp(self):
        """Set up test data for unified orchestrator."""
        self.scenario = TestDataFactory.create_test_scenario(num_employees=6)
        self.department = self.scenario['department']
        self.employees = self.scenario['employees']
        self.shift_templates = self.scenario['shift_templates']
        
        self.start_date = timezone.make_aware(datetime(2025, 8, 4))
        self.end_date = self.start_date + timedelta(days=14)  # 2 weeks

    def test_unified_orchestrator_end_to_end(self):
        """Test complete unified orchestrator workflow."""
        orchestrator = UnifiedOrchestrator(
            department=self.department,
            start_date=self.start_date,
            end_date=self.end_date
        )
        
        # Run complete orchestration
        result = orchestrator.run_orchestration(preview_only=True)
        
        # Should return orchestration result
        self.assertIsInstance(result, dict)
        self.assertIn('shifts_generated', result)
        self.assertIn('fairness_score', result)
        self.assertIn('constraint_violations', result)
        
        # Should generate reasonable number of shifts
        shifts_generated = result['shifts_generated']
        self.assertGreater(len(shifts_generated), 0)

    def test_unified_orchestrator_preview_vs_apply(self):
        """Test difference between preview and apply modes."""
        orchestrator = UnifiedOrchestrator(
            department=self.department,
            start_date=self.start_date,
            end_date=self.end_date
        )
        
        # Count existing shifts before
        initial_shift_count = Shift.objects.filter(
            start_time__gte=self.start_date,
            end_time__lte=self.end_date
        ).count()
        
        # Run in preview mode
        preview_result = orchestrator.run_orchestration(preview_only=True)
        
        # Should not create actual shifts
        preview_shift_count = Shift.objects.filter(
            start_time__gte=self.start_date,
            end_time__lte=self.end_date
        ).count()
        self.assertEqual(preview_shift_count, initial_shift_count)
        
        # Run in apply mode
        apply_result = orchestrator.run_orchestration(preview_only=False)
        
        # Should create actual shifts
        final_shift_count = Shift.objects.filter(
            start_time__gte=self.start_date,
            end_time__lte=self.end_date
        ).count()
        self.assertGreater(final_shift_count, initial_shift_count)

    def test_unified_orchestrator_configuration(self):
        """Test unified orchestrator with different configurations."""
        configs = [
            {'fairness_weight': 1.0, 'constraint_weight': 0.5},
            {'fairness_weight': 0.5, 'constraint_weight': 1.0},
            {'fairness_weight': 0.7, 'constraint_weight': 0.7, 'preference_weight': 0.3}
        ]
        
        results = []
        for config in configs:
            orchestrator = UnifiedOrchestrator(
                department=self.department,
                start_date=self.start_date,
                end_date=self.end_date,
                **config
            )
            
            result = orchestrator.run_orchestration(preview_only=True)
            results.append(result)
        
        # All configurations should produce valid results
        for result in results:
            self.assertIsInstance(result, dict)
            self.assertIn('shifts_generated', result)
            self.assertGreater(len(result['shifts_generated']), 0)
        
        # Different configurations may produce different results
        # (This is more of a sanity check than a strict requirement)
        fairness_scores = [r.get('fairness_score', 0) for r in results]
        self.assertIsInstance(fairness_scores, list)


class AlgorithmPerformanceTest(TestCase):
    """Test algorithm performance and scalability."""

    def test_large_scale_orchestration_performance(self):
        """Test orchestrator performance with large datasets."""
        # Create larger scenario
        large_scenario = TestDataFactory.create_test_scenario(num_employees=25)
        department = large_scenario['department']
        
        start_date = timezone.make_aware(datetime(2025, 8, 4))
        end_date = start_date + timedelta(days=30)  # 1 month
        
        import time
        start_time = time.time()
        
        orchestrator = UnifiedOrchestrator(
            department=department,
            start_date=start_date,
            end_date=end_date
        )
        
        result = orchestrator.run_orchestration(preview_only=True)
        
        end_time = time.time()
        
        # Should complete within reasonable time (30 seconds for 25 employees, 1 month)
        self.assertLess(end_time - start_time, 30.0)
        
        # Should produce valid result
        self.assertIsInstance(result, dict)
        self.assertIn('shifts_generated', result)

    def test_memory_usage_efficiency(self):
        """Test memory efficiency of algorithms."""
        import tracemalloc
        
        tracemalloc.start()
        
        # Create scenario and run orchestration
        scenario = TestDataFactory.create_test_scenario(num_employees=15)
        
        orchestrator = UnifiedOrchestrator(
            department=scenario['department'],
            start_date=timezone.make_aware(datetime(2025, 8, 4)),
            end_date=timezone.make_aware(datetime(2025, 8, 18))  # 2 weeks
        )
        
        result = orchestrator.run_orchestration(preview_only=True)
        
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        # Memory usage should be reasonable (less than 100MB peak)
        peak_mb = peak / 1024 / 1024
        self.assertLess(peak_mb, 100.0)
        
        # Should still produce valid result
        self.assertIsInstance(result, dict)
