"""
Shift Reassignment Module for Orchestrator

This module handles automatic reassignment of shifts when conflicts are detected,
particularly for recurring leave patterns. It provides intelligent conflict resolution
and maintains audit trails for all reassignments.
"""
from datetime import datetime, timedelta, time
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict
import logging
import logging

from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import models, transaction

from team_planner.shifts.models import Shift, ShiftTemplate, ShiftType
from team_planner.employees.models import EmployeeProfile, RecurringLeavePattern
from team_planner.leaves.models import LeaveRequest
from .models import OrchestrationRun, OrchestrationResult, OrchestrationConstraint

User = get_user_model()
logger = logging.getLogger(__name__)


class ConflictType:
    """Types of conflicts that can trigger reassignment."""
    RECURRING_LEAVE = "recurring_leave"
    APPROVED_LEAVE = "approved_leave"
    DOUBLE_ASSIGNMENT = "double_assignment"
    SKILL_MISMATCH = "skill_mismatch"
    MAX_CONSECUTIVE = "max_consecutive"


class ReassignmentStrategy:
    """Available strategies for resolving conflicts."""
    NEXT_BEST_AVAILABLE = "next_best_available"
    SPLIT_COVERAGE = "split_coverage"
    VOLUNTARY_OVERTIME = "voluntary_overtime"
    MANUAL_INTERVENTION = "manual_intervention"


class ShiftReassignmentManager:
    """Manages automatic reassignment of shifts when conflicts are detected."""
    
    def __init__(self, orchestration_run: OrchestrationRun, fairness_calculator=None):
        self.orchestration_run = orchestration_run
        self.fairness_calculator = fairness_calculator
        self.reassignment_log = []
        self.conflicts_detected = []
        self._employee_cache = {}  # Cache to avoid repeated DB queries
    
    def _get_employee_from_assignment(self, assignment: Dict) -> Any:
        """Get employee object from assignment dict, handling both old and new formats."""
        # Handle new format with assigned_employee_id
        if 'assigned_employee_id' in assignment:
            employee_id = assignment['assigned_employee_id']
            if employee_id not in self._employee_cache:
                self._employee_cache[employee_id] = User.objects.get(pk=employee_id)
            return self._employee_cache[employee_id]
        
        # Handle old format with assigned_employee object (for backward compatibility)
        if 'assigned_employee' in assignment:
            return assignment['assigned_employee']
        
        raise KeyError("Assignment missing both 'assigned_employee_id' and 'assigned_employee'")
    
    def _update_assignment_employee(self, assignment: Dict, new_employee: Any) -> None:
        """Update assignment with new employee, handling both old and new formats."""
        if 'assigned_employee_id' in assignment:
            assignment['assigned_employee_id'] = new_employee.pk
            assignment['assigned_employee_name'] = new_employee.get_full_name()
        else:
            assignment['assigned_employee'] = new_employee
    
    def detect_conflicts(self, assignments: List[Dict]) -> List[Dict]:
        """
        Detect all types of conflicts in the given assignments.
        
        Args:
            assignments: List of shift assignments to check
            
        Returns:
            List of conflict dictionaries with details
        """
        # Keep a reference to the plan to use for fairness sorting during reassignments
        self.current_plan_assignments = list(assignments)
        conflicts = []
        
        for assignment in assignments:
            # Check for recurring leave conflicts
            recurring_conflicts = self._check_recurring_leave_conflicts(assignment)
            conflicts.extend(recurring_conflicts)
            
            # Check for approved leave conflicts
            leave_conflicts = self._check_approved_leave_conflicts(assignment)
            conflicts.extend(leave_conflicts)
            
            # Check for double assignment conflicts
            double_conflicts = self._check_double_assignment_conflicts(assignment, assignments)
            conflicts.extend(double_conflicts)
        
        self.conflicts_detected = conflicts
        return conflicts
    
    def _check_recurring_leave_conflicts(self, assignment: Dict) -> List[Dict]:
        """Check for recurring leave pattern conflicts."""
        conflicts = []
        employee = self._get_employee_from_assignment(assignment)
        start_datetime = assignment['start_datetime']
        end_datetime = assignment['end_datetime']
        shift_type = assignment['shift_type']
        
        # Skip waakdienst shifts as they're not affected by recurring patterns
        if shift_type == ShiftType.WAAKDIENST:
            return conflicts
        
        # Get active recurring patterns for this employee
        patterns = RecurringLeavePattern.objects.filter(
            employee=employee,
            is_active=True,
            effective_from__lte=end_datetime.date(),
        ).filter(
            models.Q(effective_until__isnull=True) | 
            models.Q(effective_until__gte=start_datetime.date())
        )
        
        # Check each day in the assignment period
        current_date = start_datetime.date()
        end_date = end_datetime.date()
        
        while current_date <= end_date:
            # Only check weekdays for incidents shifts
            if current_date.weekday() < 5:  # Monday=0, Friday=4
                for pattern in patterns:
                    if pattern.applies_to_date(current_date):
                        affected_hours = pattern.get_affected_hours_for_date(current_date)
                        if affected_hours:
                            # Check if assignment time actually overlaps with the pattern's affected hours
                            assignment_start = start_datetime
                            assignment_end = end_datetime
                            pattern_start = affected_hours['start_datetime']
                            pattern_end = affected_hours['end_datetime']
                            
                            # Check for time overlap: assignments overlap if start1 < end2 and start2 < end1
                            if assignment_start < pattern_end and pattern_start < assignment_end:
                                conflicts.append({
                                    'type': ConflictType.RECURRING_LEAVE,
                                    'assignment': assignment,
                                    'employee_id': employee.pk,
                                    'employee_name': employee.get_full_name(),
                                    'conflict_date': current_date,
                                    'pattern_id': pattern.pk,
                                    'pattern_name': pattern.name,
                                    'affected_hours': affected_hours,
                                    'severity': 'high',
                                    'description': f"Recurring leave conflict on {current_date}: {pattern.name}"
                                })
            current_date += timedelta(days=1)
        
        return conflicts
    
    def _check_approved_leave_conflicts(self, assignment: Dict) -> List[Dict]:
        """Check for approved leave request conflicts."""
        conflicts = []
        employee = self._get_employee_from_assignment(assignment)
        start_datetime = assignment['start_datetime']
        end_datetime = assignment['end_datetime']
        
        # Check for approved leave requests that overlap
        leave_requests = LeaveRequest.objects.filter(
            employee=employee,
            status='approved',
            start_date__lte=end_datetime.date(),
            end_date__gte=start_datetime.date()
        )
        
        for leave_request in leave_requests:
            conflicts.append({
                'type': ConflictType.APPROVED_LEAVE,
                'assignment': assignment,
                'employee_id': employee.pk,
                'employee_name': employee.get_full_name(),
                'leave_request_id': leave_request.pk,
                'leave_start_date': str(leave_request.start_date),
                'leave_end_date': str(leave_request.end_date),
                'severity': 'critical',
                'description': f"Approved leave conflict: {leave_request.start_date} to {leave_request.end_date}"
            })
        
        return conflicts
    
    def _check_double_assignment_conflicts(self, assignment: Dict, all_assignments: List[Dict]) -> List[Dict]:
        """Check for double assignment conflicts (incidents + incidents-standby)."""
        conflicts = []
        employee = self._get_employee_from_assignment(assignment)
        shift_type = assignment['shift_type']
        start_datetime = assignment['start_datetime']
        end_datetime = assignment['end_datetime']
        
        # Only check for incidents-related conflicts
        if shift_type not in [ShiftType.INCIDENTS, ShiftType.INCIDENTS_STANDBY]:
            return conflicts
        
        # Check against other assignments in the same run
        for other_assignment in all_assignments:
            other_employee = self._get_employee_from_assignment(other_assignment)
            if (other_assignment != assignment and 
                other_employee.pk == employee.pk and
                other_assignment['shift_type'] in [ShiftType.INCIDENTS, ShiftType.INCIDENTS_STANDBY] and
                other_assignment['shift_type'] != shift_type):
                
                # Check for time overlap
                other_start = other_assignment['start_datetime']
                other_end = other_assignment['end_datetime']
                
                if start_datetime < other_end and end_datetime > other_start:
                    conflicts.append({
                        'type': ConflictType.DOUBLE_ASSIGNMENT,
                        'assignment': assignment,
                        'conflicting_assignment': other_assignment,
                        'employee_id': employee.pk,
                        'employee_name': employee.get_full_name(),
                        'severity': 'high',
                        'description': f"Double assignment: {shift_type} conflicts with {other_assignment['shift_type']}"
                    })
        
        return conflicts
    
    def resolve_conflicts(self, conflicts: List[Dict]) -> List[Dict]:
        """
        Resolve detected conflicts using appropriate strategies.
        
        Args:
            conflicts: List of conflicts to resolve
            
        Returns:
            List of reassignment actions taken
        """
        reassignments = []
        
        # Group conflicts by assignment to handle them efficiently
        conflicts_by_assignment = defaultdict(list)
        for conflict in conflicts:
            assignment_id = id(conflict['assignment'])
            conflicts_by_assignment[assignment_id].append(conflict)
        
        for assignment_id, assignment_conflicts in conflicts_by_assignment.items():
            # Get the assignment from the first conflict
            assignment = assignment_conflicts[0]['assignment']
            
            # Determine the best resolution strategy
            strategy = self._determine_resolution_strategy(assignment_conflicts)
            
            # Apply the resolution strategy
            reassignment = self._apply_resolution_strategy(assignment, assignment_conflicts, strategy)
            
            if reassignment:
                reassignments.append(reassignment)
        
        self.reassignment_log.extend(reassignments)
        return reassignments
    
    def _determine_resolution_strategy(self, conflicts: List[Dict]) -> str:
        """Determine the best strategy for resolving a set of conflicts."""
        # Priority order based on conflict severity and type
        has_critical = any(c['severity'] == 'critical' for c in conflicts)
        has_recurring = any(c['type'] == ConflictType.RECURRING_LEAVE for c in conflicts)
        has_approved_leave = any(c['type'] == ConflictType.APPROVED_LEAVE for c in conflicts)
        
        # Critical conflicts (approved leave) require immediate reassignment
        if has_critical or has_approved_leave:
            return ReassignmentStrategy.NEXT_BEST_AVAILABLE
        
        # Recurring leave conflicts should use split coverage when possible
        if has_recurring:
            # Check if we can split coverage (only for incidents shifts with partial conflicts)
            assignment = conflicts[0]['assignment']
            shift_type = assignment['shift_type']
            
            if shift_type in [ShiftType.INCIDENTS, ShiftType.INCIDENTS_STANDBY]:
                # Count total days vs conflict days
                start_date = assignment['start_datetime'].date()
                end_date = assignment['end_datetime'].date()
                
                total_weekdays = 0
                conflict_days = 0
                current_date = start_date
                
                while current_date <= end_date:
                    if current_date.weekday() < 5:  # Weekdays only
                        total_weekdays += 1
                        # Check if this day has conflicts
                        for conflict in conflicts:
                            if (conflict['type'] == ConflictType.RECURRING_LEAVE and 
                                conflict.get('conflict_date') == current_date):
                                conflict_days += 1
                                break
                    current_date += timedelta(days=1)
                
                # If employee is available for some days, use split coverage
                available_days = total_weekdays - conflict_days
                if available_days > 0:
                    logger.info(f"Using split coverage: {available_days}/{total_weekdays} days available")
                    return ReassignmentStrategy.SPLIT_COVERAGE
        
        # Default strategy for full conflicts
        return ReassignmentStrategy.NEXT_BEST_AVAILABLE
    
    def _apply_resolution_strategy(self, assignment: Dict, conflicts: List[Dict], strategy: str) -> Optional[Dict]:
        """Apply the chosen resolution strategy."""
        if strategy == ReassignmentStrategy.NEXT_BEST_AVAILABLE:
            return self._reassign_to_next_best(assignment, conflicts)
        elif strategy == ReassignmentStrategy.SPLIT_COVERAGE:
            return self._split_coverage_reassignment(assignment, conflicts)
        elif strategy == ReassignmentStrategy.MANUAL_INTERVENTION:
            return self._escalate_to_manual(assignment, conflicts)
        
        return None
    
    def _reassign_to_next_best(self, assignment: Dict, conflicts: List[Dict]) -> Optional[Dict]:
        """Reassign shift to the next best available employee."""
        original_employee = self._get_employee_from_assignment(assignment)
        shift_type = assignment['shift_type']
        start_datetime = assignment['start_datetime']
        end_datetime = assignment['end_datetime']
        
        logger.info(f"Attempting reassignment for {original_employee.username} due to conflicts: {[c['type'] for c in conflicts]}")
        
        # Get all available employees for this shift type
        available_employees = self._get_available_employees_for_reassignment(
            shift_type, start_datetime, end_datetime, exclude_employee=original_employee
        )
        
        if not available_employees:
            logger.warning(f"No available employees found for reassignment of {shift_type} shift")
            return self._escalate_to_manual(assignment, conflicts)
        
        # Sort by least hours in this shift type within the current plan (fallback to DB if needed)
        if self.fairness_calculator:
            try:
                load_map = self.fairness_calculator.calculate_provisional_assignments(self.current_plan_assignments)
                key = lambda emp: load_map.get(emp.pk, {}).get(shift_type.lower(), 0.0)
            except Exception:
                current_assignments = self.fairness_calculator.calculate_current_assignments(available_employees)
                key = lambda emp: current_assignments.get(emp.pk, {}).get(shift_type.lower(), 0.0)
            available_employees.sort(key=key)
        
        # Select the best candidate
        new_employee = available_employees[0]
        
        # Create reassignment record
        reassignment = {
            'original_assignment': assignment.copy(),
            'new_employee_id': new_employee.pk,
            'new_employee_name': new_employee.get_full_name(),
            'original_employee_id': original_employee.pk,
            'original_employee_name': original_employee.get_full_name(),
            'conflicts_resolved': conflicts,
            'strategy': ReassignmentStrategy.NEXT_BEST_AVAILABLE,
            'timestamp': timezone.now(),
            'reason': f"Automatic reassignment due to {len(conflicts)} conflict(s)",
            'success': True
        }
        
        # Update the assignment
        self._update_assignment_employee(assignment, new_employee)
        assignment['assignment_reason'] = f"Reassigned from {original_employee.username} due to conflicts"
        assignment['auto_assigned'] = True
        
        # Log the constraint violation for audit purposes
        self._create_constraint_violation_record(original_employee, conflicts)
        
        logger.info(f"Successfully reassigned {shift_type} shift from {original_employee.username} to {new_employee.username}")
        
        return reassignment
    
    def _split_coverage_reassignment(self, assignment: Dict, conflicts: List[Dict]) -> Optional[Dict]:
        """Split shift coverage when partial conflicts exist."""
        original_employee = self._get_employee_from_assignment(assignment)
        shift_type = assignment['shift_type']
        start_datetime = assignment['start_datetime']
        end_datetime = assignment['end_datetime']
        
        logger.info(f"Attempting split coverage for {original_employee.username} with {len(conflicts)} conflicts")
        
        # Get conflict dates
        conflict_dates = set()
        for conflict in conflicts:
            if conflict['type'] == ConflictType.RECURRING_LEAVE:
                conflict_dates.add(conflict['conflict_date'])
        
        # For incidents shifts, we can split by day
        if shift_type in [ShiftType.INCIDENTS, ShiftType.INCIDENTS_STANDBY]:
            return self._split_incidents_week_coverage(assignment, conflicts, conflict_dates)
        
        # For other shift types, fall back to full reassignment
        logger.info(f"Split coverage not supported for {shift_type}, falling back to full reassignment")
        return self._reassign_to_next_best(assignment, conflicts)
    
    def _split_incidents_week_coverage(self, assignment: Dict, conflicts: List[Dict], conflict_dates: set) -> Optional[Dict]:
        """Split incidents week coverage, keeping employee for non-conflict days."""
        original_employee = self._get_employee_from_assignment(assignment)
        shift_type = assignment['shift_type']
        start_datetime = assignment['start_datetime']
        end_datetime = assignment['end_datetime']
        
        # Generate all weekdays in the assignment period
        current_date = start_datetime.date()
        all_weekdays = []
        while current_date <= end_datetime.date():
            if current_date.weekday() < 5:  # Monday=0 to Friday=4
                all_weekdays.append(current_date)
            current_date += timedelta(days=1)
        
        # Separate conflict days from available days
        available_days = [day for day in all_weekdays if day not in conflict_dates]
        
        if not available_days:
            # No days available for original employee
            logger.warning(f"No available days for {original_employee.username}, full reassignment needed")
            return self._reassign_to_next_best(assignment, conflicts)
        
        logger.info(f"Employee {original_employee.username} available for {len(available_days)}/{len(all_weekdays)} days")
        
        # Find replacement employee for conflict days
        conflict_days = [day for day in all_weekdays if day in conflict_dates]
        if not conflict_days:
            # No conflicts to resolve (shouldn't happen)
            return None
        
        # Get available employees for conflict days
        replacement_employee = self._find_replacement_for_days(shift_type, conflict_days, original_employee)
        
        if not replacement_employee:
            logger.warning(f"No replacement found for conflict days, escalating to manual intervention")
            return self._escalate_to_manual(assignment, conflicts)
        
        # Create split assignment structure
        split_info = {
            'original_employee_days': available_days,
            'replacement_employee': replacement_employee,
            'replacement_days': conflict_days,
            'total_days': len(all_weekdays),
            'kept_days': len(available_days),
            'reassigned_days': len(conflict_days)
        }
        
        # Update the main assignment to reflect split coverage
        assignment['assignment_reason'] = f"Split coverage: {len(available_days)} days for {original_employee.username}, {len(conflict_days)} days reassigned to {replacement_employee.username}"
        assignment['split_coverage'] = split_info
        assignment['is_split_assignment'] = True
        
        # Create reassignment record
        reassignment = {
            'original_assignment': assignment.copy(),
            'new_employee_id': replacement_employee.pk,
            'new_employee_name': replacement_employee.get_full_name(),
            'original_employee_id': original_employee.pk,
            'original_employee_name': original_employee.get_full_name(),
            'conflicts_resolved': conflicts,
            'strategy': ReassignmentStrategy.SPLIT_COVERAGE,
            'timestamp': timezone.now(),
            'reason': f"Split coverage: keeping {len(available_days)} days, reassigning {len(conflict_days)} days",
            'success': True,
            'split_info': split_info
        }
        
        # Log the constraint violation for audit purposes
        self._create_constraint_violation_record(original_employee, conflicts)
        
        logger.info(f"Successfully created split coverage: {original_employee.username} keeps {len(available_days)} days, {replacement_employee.username} covers {len(conflict_days)} days")
        
        return reassignment
    
    def _find_replacement_for_days(self, shift_type: str, conflict_days: List, exclude_employee: Any) -> Optional[Any]:
        """Find an employee available to cover specific conflict days."""
        # Get all potentially available employees
        from .algorithms import ConstraintChecker
        
        # Use the first conflict day to create datetime range
        first_day = min(conflict_days)
        last_day = max(conflict_days)
        start_datetime = timezone.make_aware(datetime.combine(first_day, time(8, 0)))
        end_datetime = timezone.make_aware(datetime.combine(last_day, time(17, 0)))
        
        constraint_checker = ConstraintChecker(
            start_datetime, end_datetime, 
            team_id=getattr(self.orchestration_run, 'team_id', None)
        )
        
        all_available = constraint_checker.get_available_employees(shift_type)
        
        # Filter for employees available on ALL conflict days
        suitable_employees = []
        for emp in all_available:
            if emp.pk == exclude_employee.pk:
                continue
            
            # Check if employee is available for all conflict days
            available_for_all_days = True
            for conflict_day in conflict_days:
                day_start = timezone.make_aware(datetime.combine(conflict_day, time(8, 0)))
                day_end = timezone.make_aware(datetime.combine(conflict_day, time(17, 0)))
                
                # Check for leave conflicts on this specific day
                if constraint_checker.check_leave_conflicts(emp, day_start, day_end):
                    available_for_all_days = False
                    break
                
                # Check for recurring pattern conflicts on this specific day
                if constraint_checker.check_recurring_pattern_conflicts(emp, day_start, day_end, shift_type):
                    available_for_all_days = False
                    break
                
                # Check for existing assignments on this specific day
                if constraint_checker.check_existing_assignments(emp, day_start, day_end, shift_type):
                    available_for_all_days = False
                    break
            
            if available_for_all_days:
                suitable_employees.append(emp)
        
        if not suitable_employees:
            return None
        
        # Sort by least hours in this shift type within the current plan (fallback to DB if needed)
        if self.fairness_calculator:
            try:
                load_map = self.fairness_calculator.calculate_provisional_assignments(self.current_plan_assignments)
                suitable_employees.sort(key=lambda emp: load_map.get(emp.pk, {}).get(shift_type.lower(), 0.0))
            except Exception:
                current_assignments = self.fairness_calculator.calculate_current_assignments(suitable_employees)
                suitable_employees.sort(key=lambda emp: current_assignments.get(emp.pk, {}).get(shift_type.lower(), 0.0))
        
        return suitable_employees[0]
    
    def create_split_shift_assignments(self, original_assignment: Dict, split_info: Dict) -> List[Dict]:
        """Create individual daily shift assignments for split coverage."""
        assignments = []
        original_employee = self._get_employee_from_assignment(original_assignment)
        replacement_employee = split_info['replacement_employee']
        shift_type = original_assignment['shift_type']
        
        # Create assignments for original employee's available days
        for day_date in split_info['original_employee_days']:
            day_start = timezone.make_aware(datetime.combine(day_date, time(8, 0)))
            day_end = timezone.make_aware(datetime.combine(day_date, time(17, 0)))
            duration_hours = (day_end - day_start).total_seconds() / 3600
            
            assignment = {
                'assigned_employee_id': original_employee.pk,
                'assigned_employee_name': original_employee.get_full_name(),
                'start_datetime': day_start,
                'end_datetime': day_end,
                'shift_type': shift_type,
                'template': original_assignment['template'],
                'week_start_date': original_assignment.get('week_start_date'),
                'auto_assigned': True,
                'assignment_reason': f"Split coverage - original employee available",
                'is_split_assignment': True,
                'split_coverage_type': 'original_employee_day',
                'duration_hours': duration_hours
            }
            assignments.append(assignment)
        
        # Create assignments for replacement employee's days
        for day_date in split_info['replacement_days']:
            day_start = timezone.make_aware(datetime.combine(day_date, time(8, 0)))
            day_end = timezone.make_aware(datetime.combine(day_date, time(17, 0)))
            duration_hours = (day_end - day_start).total_seconds() / 3600
            
            assignment = {
                'assigned_employee_id': replacement_employee.pk,
                'assigned_employee_name': replacement_employee.get_full_name(),
                'start_datetime': day_start,
                'end_datetime': day_end,
                'shift_type': shift_type,
                'template': original_assignment['template'],
                'week_start_date': original_assignment.get('week_start_date'),
                'auto_assigned': True,
                'assignment_reason': f"Split coverage - covering for {original_employee.username}",
                'is_split_assignment': True,
                'split_coverage_type': 'replacement_employee_day',
                'duration_hours': duration_hours
            }
            assignments.append(assignment)
        
        logger.info(f"Created {len(assignments)} split shift assignments: {len(split_info['original_employee_days'])} for {original_employee.username}, {len(split_info['replacement_days'])} for {replacement_employee.username}")
        
        return assignments
    
    def _escalate_to_manual(self, assignment: Dict, conflicts: List[Dict]) -> Dict:
        """Escalate to manual intervention when automatic reassignment fails."""
        original_employee = self._get_employee_from_assignment(assignment)
        reassignment = {
            'original_assignment': assignment.copy(),
            'new_employee_id': None,
            'new_employee_name': None,
            'original_employee_id': original_employee.pk,
            'original_employee_name': original_employee.get_full_name(),
            'conflicts_resolved': conflicts,
            'strategy': ReassignmentStrategy.MANUAL_INTERVENTION,
            'timestamp': timezone.now(),
            'reason': f"Escalated to manual intervention - no automatic resolution available",
            'success': False,
            'requires_manual_action': True
        }
        
        # Create a constraint violation for tracking
        original_employee = self._get_employee_from_assignment(assignment)
        self._create_constraint_violation_record(original_employee, conflicts)
        
        logger.warning(f"Escalating shift assignment to manual intervention: {assignment['shift_type']} for {original_employee.username}")
        
        return reassignment
    
    def _get_available_employees_for_reassignment(self, shift_type: str, start_datetime: datetime, 
                                                end_datetime: datetime, exclude_employee: Any) -> List[Any]:
        """Get employees available for reassignment, excluding the original employee."""
        from .algorithms import ConstraintChecker
        
        # Create a temporary constraint checker
        constraint_checker = ConstraintChecker(
            start_datetime, end_datetime, 
            team_id=getattr(self.orchestration_run, 'team_id', None)
        )
        
        # Get all available employees
        all_available = constraint_checker.get_available_employees(shift_type)
        
        # Filter out the original employee and those with conflicts
        available_for_reassignment = []
        for emp in all_available:
            if emp.pk == exclude_employee.pk:
                continue
                
            # Check if this employee has conflicts for this specific time period
            if not constraint_checker.check_leave_conflicts(emp, start_datetime, end_datetime):
                if not constraint_checker.check_recurring_pattern_conflicts(emp, start_datetime, end_datetime, shift_type):
                    available_for_reassignment.append(emp)
        
        return available_for_reassignment
    
    def _create_constraint_violation_record(self, employee: Any, conflicts: List[Dict]):
        """Create a constraint violation record for audit purposes."""
        with transaction.atomic():
            for conflict in conflicts:
                OrchestrationConstraint.objects.create(
                    orchestration_run=self.orchestration_run,
                    constraint_type=OrchestrationConstraint.ConstraintType.LEAVE_CONFLICT,
                    severity=OrchestrationConstraint.Severity.HARD,
                    employee=employee,
                    start_date=conflict.get('conflict_date', self.orchestration_run.start_date),
                    end_date=conflict.get('conflict_date', self.orchestration_run.start_date),
                    description=conflict['description'],
                    violations_count=1,
                    violation_details=f"Conflict type: {conflict['type']}, Resolved: {conflict.get('resolved', False)}"
                )
    
    def get_reassignment_summary(self) -> Dict[str, Any]:
        """Get a summary of all reassignments performed."""
        successful_reassignments = [r for r in self.reassignment_log if r['success']]
        failed_reassignments = [r for r in self.reassignment_log if not r['success']]
        split_coverage_reassignments = [r for r in self.reassignment_log if r.get('strategy') == ReassignmentStrategy.SPLIT_COVERAGE]
        
        return {
            'total_conflicts_detected': len(self.conflicts_detected),
            'total_reassignments_attempted': len(self.reassignment_log),
            'successful_reassignments': len(successful_reassignments),
            'failed_reassignments': len(failed_reassignments),
            'split_coverage_reassignments': len(split_coverage_reassignments),
            'manual_interventions_required': len([r for r in self.reassignment_log if r.get('requires_manual_action', False)]),
            'conflicts_by_type': {
                ConflictType.RECURRING_LEAVE: len([c for c in self.conflicts_detected if c['type'] == ConflictType.RECURRING_LEAVE]),
                ConflictType.APPROVED_LEAVE: len([c for c in self.conflicts_detected if c['type'] == ConflictType.APPROVED_LEAVE]),
                ConflictType.DOUBLE_ASSIGNMENT: len([c for c in self.conflicts_detected if c['type'] == ConflictType.DOUBLE_ASSIGNMENT]),
            },
            'reassignments': self.reassignment_log
        }


class ReassignmentValidator:
    """Validates reassignments and ensures they don't create new conflicts."""
    
    @staticmethod
    def validate_reassignment(original_assignment: Dict, new_employee: Any, 
                            start_datetime: datetime, end_datetime: datetime) -> Dict[str, Any]:
        """
        Validate that a reassignment won't create new conflicts.
        
        Returns:
            Dict with validation results and any warnings
        """
        validation_result = {
            'is_valid': True,
            'warnings': [],
            'errors': []
        }
        
        # Check for leave conflicts with new employee
        leave_requests = LeaveRequest.objects.filter(
            employee=new_employee,
            status='approved',
            start_date__lte=end_datetime.date(),
            end_date__gte=start_datetime.date()
        )
        
        if leave_requests.exists():
            validation_result['is_valid'] = False
            validation_result['errors'].append(f"New employee {new_employee.username} has approved leave during assignment period")
        
        # Check for recurring leave patterns
        patterns = RecurringLeavePattern.objects.filter(
            employee=new_employee,
            is_active=True,
            effective_from__lte=end_datetime.date(),
        ).filter(
            models.Q(effective_until__isnull=True) | 
            models.Q(effective_until__gte=start_datetime.date())
        )
        
        current_date = start_datetime.date()
        while current_date <= end_datetime.date():
            if current_date.weekday() < 5:  # Only weekdays
                for pattern in patterns:
                    if pattern.applies_to_date(current_date):
                        validation_result['warnings'].append(
                            f"New employee {new_employee.username} has recurring leave pattern on {current_date}: {pattern.name}"
                        )
            current_date += timedelta(days=1)
        
        return validation_result
