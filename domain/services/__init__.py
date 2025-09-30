"""
Domain services for the Team Planner orchestrator system.

Domain services contain business logic that doesn't naturally fit
within a single entity or value object.
"""

import statistics
from abc import ABC
from abc import abstractmethod
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from datetime import datetime
from datetime import timedelta
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple

from domain.entities import Assignment
from domain.entities import Conflict
from domain.entities import Employee
from domain.entities import Shift
from domain.value_objects import ConflictSeverity
from domain.value_objects import DateRange
from domain.value_objects import EmployeeId
from domain.value_objects import FairnessScore
from domain.value_objects import ShiftType
from domain.value_objects import TeamConfiguration
from domain.value_objects import TeamId
from domain.value_objects import TimeRange


@dataclass
class WeightedAssignment:
    """Assignment with weight for fairness calculations."""

    assignment: Assignment
    weight: float


@dataclass
class FairnessImpact:
    """Impact of a proposed assignment on overall fairness."""

    employee_fairness_change: float
    team_fairness_variance: float
    improves_distribution: bool


class FairnessCalculator:
    """Calculate fairness scores for shift assignments.

    Addresses Phase 1 critical gap: yearly fairness calculation with
    configurable periods and historical decay.
    """

    def __init__(self, config: TeamConfiguration):
        self.config = config

    def calculate_employee_fairness(
        self, employee: Employee, assignments: list[Assignment], period: DateRange,
    ) -> FairnessScore:
        """Calculate fairness score for an employee.

        Implements yearly fairness period and historical decay
        as identified in Phase 1 requirements analysis.
        """

        # Use configured fairness period instead of hardcoded 6 months
        fairness_start = period.start - timedelta(days=self.config.fairness_period_days)
        fairness_period = DateRange(fairness_start, period.end)

        # Get assignments in fairness period
        fairness_assignments = [
            a for a in assignments if fairness_period.contains(a.assigned_at.date())
        ]

        # Apply historical decay based on lookback configuration
        weighted_assignments = self._apply_historical_decay(
            fairness_assignments, period.start, self.config.fairness_lookback_days,
        )

        # Calculate scores by shift type
        incidents_score = self._calculate_shift_type_score(
            weighted_assignments, ShiftType.INCIDENTS,
        )
        incidents_standby_score = self._calculate_shift_type_score(
            weighted_assignments, ShiftType.INCIDENTS_STANDBY,
        )
        waakdienst_score = self._calculate_shift_type_score(
            weighted_assignments, ShiftType.WAAKDIENST,
        )

        # Calculate total score with shift type weights
        total_score = (
            incidents_score * ShiftType.INCIDENTS.fairness_weight
            + incidents_standby_score * ShiftType.INCIDENTS_STANDBY.fairness_weight
            + waakdienst_score * ShiftType.WAAKDIENST.fairness_weight
        )

        return FairnessScore(
            incidents_score=incidents_score,
            incidents_standby_score=incidents_standby_score,
            waakdienst_score=waakdienst_score,
            total_score=total_score,
            period=fairness_period,
        )

    def calculate_assignment_impact(
        self,
        proposed_assignment: Assignment,
        current_assignments: list[Assignment],
        all_employees: list[Employee],
    ) -> FairnessImpact:
        """Calculate how a proposed assignment affects overall fairness."""

        if not proposed_assignment.shift:
            return FairnessImpact(
                employee_fairness_change=0.0,
                team_fairness_variance=0.0,
                improves_distribution=False,
            )

        # Calculate current fairness scores for all employees
        current_period = DateRange(
            date.today() - timedelta(days=self.config.fairness_period_days),
            date.today(),
        )

        current_scores = {}
        for employee in all_employees:
            employee_assignments = [
                a for a in current_assignments if a.employee_id == employee.id
            ]
            fairness = self.calculate_employee_fairness(
                employee, employee_assignments, current_period,
            )
            current_scores[employee.id] = fairness.total_score

        # Simulate adding the proposed assignment
        if proposed_assignment.employee_id in current_scores:
            # Add weight of proposed assignment
            assignment_weight = proposed_assignment.shift.calculate_fairness_weight()
            new_employee_score = (
                current_scores[proposed_assignment.employee_id] + assignment_weight
            )

            # Calculate impact
            employee_change = (
                new_employee_score - current_scores[proposed_assignment.employee_id]
            )

            # Calculate team variance before and after
            current_variance = (
                statistics.variance(current_scores.values())
                if len(current_scores) > 1
                else 0
            )

            scores_with_assignment = current_scores.copy()
            scores_with_assignment[proposed_assignment.employee_id] = new_employee_score
            new_variance = (
                statistics.variance(scores_with_assignment.values())
                if len(scores_with_assignment) > 1
                else 0
            )

            return FairnessImpact(
                employee_fairness_change=employee_change,
                team_fairness_variance=new_variance - current_variance,
                improves_distribution=new_variance < current_variance,
            )

        return FairnessImpact(
            employee_fairness_change=0.0,
            team_fairness_variance=0.0,
            improves_distribution=False,
        )

    def find_fairest_employee(
        self, candidates: list[Employee], shift: Shift, context: "AssignmentContext",
    ) -> Employee | None:
        """Find the employee with the best fairness score for a shift."""

        if not candidates:
            return None

        current_period = DateRange(
            date.today() - timedelta(days=self.config.fairness_period_days),
            date.today(),
        )

        # Calculate fairness scores for all candidates
        candidate_scores = {}
        for employee in candidates:
            if employee.is_available_for_shift(shift.shift_type, shift.time_range):
                # Get current assignments for this employee
                employee_assignments = context.get_assignments_for_employee(employee.id)
                fairness = self.calculate_employee_fairness(
                    employee, employee_assignments, current_period,
                )
                candidate_scores[employee.id] = fairness.total_score

        if not candidate_scores:
            return None

        # Find employee with lowest score (most fair to assign)
        fairest_employee_id = min(
            candidate_scores.keys(), key=lambda emp_id: candidate_scores[emp_id],
        )
        return next(emp for emp in candidates if emp.id == fairest_employee_id)

    def _apply_historical_decay(
        self, assignments: list[Assignment], calculation_date: date, lookback_days: int,
    ) -> list[WeightedAssignment]:
        """Apply exponential decay to historical assignments."""

        half_life_days = lookback_days / 2  # Configurable half-life
        weighted_assignments = []

        for assignment in assignments:
            days_ago = (calculation_date - assignment.assigned_at.date()).days

            if days_ago <= lookback_days:
                # Apply exponential decay
                decay_factor = 0.5 ** (days_ago / half_life_days)

                weighted_assignments.append(
                    WeightedAssignment(assignment=assignment, weight=decay_factor),
                )

        return weighted_assignments

    def _calculate_shift_type_score(
        self, weighted_assignments: list[WeightedAssignment], shift_type: ShiftType,
    ) -> float:
        """Calculate fairness score for a specific shift type."""

        total_weight = 0.0

        for weighted_assignment in weighted_assignments:
            assignment = weighted_assignment.assignment
            if assignment.shift and assignment.shift.shift_type == shift_type:
                # Calculate assignment weight based on shift properties
                shift_weight = assignment.shift.calculate_fairness_weight()
                total_weight += shift_weight * weighted_assignment.weight

        return total_weight


class ConflictDetector:
    """Detect and categorize assignment conflicts.

    Based on Phase 1 analysis of constraint requirements.
    """

    def detect_conflicts(
        self,
        assignment: Assignment,
        employee: Employee,
        existing_assignments: list[Assignment],
    ) -> list[Conflict]:
        """Detect all conflicts for a proposed assignment."""

        conflicts = []

        if not assignment.shift:
            return conflicts

        # Leave request conflicts
        conflicts.extend(self._check_leave_conflicts(assignment, employee))

        # Recurring pattern conflicts
        conflicts.extend(self._check_recurring_pattern_conflicts(assignment, employee))

        # Rest period conflicts
        conflicts.extend(
            self._check_rest_period_conflicts(assignment, existing_assignments),
        )

        # Consecutive week conflicts
        conflicts.extend(
            self._check_consecutive_week_conflicts(assignment, existing_assignments),
        )

        # Mutual exclusivity conflicts (incidents + waakdienst same week)
        conflicts.extend(
            self._check_mutual_exclusivity_conflicts(assignment, existing_assignments),
        )

        return conflicts

    def categorize_conflict_severity(self, conflict: Conflict) -> ConflictSeverity:
        """Categorize conflict as BLOCKING, WARNING, or INFO."""

        # Hard constraints that must block assignment
        blocking_types = {
            "leave_request",
            "recurring_pattern",
            "employee_unavailable",
            "rest_period",
            "mutual_exclusivity",
        }

        if conflict.conflict_type in blocking_types:
            return ConflictSeverity.BLOCKING

        # Soft constraints that should warn but allow override
        warning_types = {"consecutive_weeks", "fairness_impact"}

        if conflict.conflict_type in warning_types:
            return ConflictSeverity.WARNING

        return ConflictSeverity.INFO

    def _check_leave_conflicts(
        self, assignment: Assignment, employee: Employee,
    ) -> list[Conflict]:
        """Check for conflicts with approved leave requests."""
        conflicts = []

        if not assignment.shift:
            return conflicts

        for leave_request in employee.leave_requests:
            if leave_request.conflicts_with_time_range(assignment.shift.time_range):
                conflicts.append(
                    Conflict(
                        conflict_type="leave_request",
                        severity=ConflictSeverity.BLOCKING,
                        message=f"Conflicts with {leave_request.leave_type} leave from {leave_request.start_date} to {leave_request.end_date}",
                        affected_time_range=assignment.shift.time_range,
                        resolution_suggestion="Assign to different employee or reschedule shift",
                    ),
                )

        return conflicts

    def _check_recurring_pattern_conflicts(
        self, assignment: Assignment, employee: Employee,
    ) -> list[Conflict]:
        """Check for conflicts with recurring leave patterns."""
        conflicts = []

        if not assignment.shift:
            return conflicts

        for pattern in employee.recurring_patterns:
            if pattern.conflicts_with_time_range(assignment.shift.time_range):
                conflicts.append(
                    Conflict(
                        conflict_type="recurring_pattern",
                        severity=ConflictSeverity.BLOCKING,
                        message=f"Conflicts with {pattern.pattern_type} pattern on {pattern.day_of_week}",
                        affected_time_range=assignment.shift.time_range,
                        resolution_suggestion="Assign to different employee",
                    ),
                )

        return conflicts

    def _check_rest_period_conflicts(
        self, assignment: Assignment, existing_assignments: list[Assignment],
    ) -> list[Conflict]:
        """Check for rest period violations."""
        conflicts = []

        if not assignment.shift:
            return conflicts

        # Get employee's existing assignments
        employee_assignments = [
            a for a in existing_assignments if a.employee_id == assignment.employee_id
        ]

        min_rest_hours = 48  # Default, would come from employee or team config
        min_rest_delta = timedelta(hours=min_rest_hours)

        for existing in employee_assignments:
            if not existing.shift:
                continue

            # Check time gap between assignments
            time_gap = min(
                abs(assignment.shift.time_range.start - existing.shift.time_range.end),
                abs(existing.shift.time_range.start - assignment.shift.time_range.end),
            )

            if time_gap < min_rest_delta:
                conflicts.append(
                    Conflict(
                        conflict_type="rest_period",
                        severity=ConflictSeverity.BLOCKING,
                        message=f"Less than {min_rest_hours}h rest between assignments",
                        affected_time_range=assignment.shift.time_range,
                        resolution_suggestion="Schedule with more rest time",
                    ),
                )

        return conflicts

    def _check_consecutive_week_conflicts(
        self, assignment: Assignment, existing_assignments: list[Assignment],
    ) -> list[Conflict]:
        """Check for consecutive week limit violations."""
        conflicts = []

        if not assignment.shift:
            return conflicts

        max_consecutive_weeks = 2  # Default, would come from employee or team config

        # Get employee's assignments for the same shift type
        employee_assignments = [
            a
            for a in existing_assignments
            if (
                a.employee_id == assignment.employee_id
                and a.shift
                and a.shift.shift_type == assignment.shift.shift_type
            )
        ]

        # Count consecutive weeks (simplified implementation)
        assignment_week = assignment.shift.time_range.start.date().isocalendar()[1]
        consecutive_count = 1

        for existing in employee_assignments:
            if existing.shift:
                existing_week = existing.shift.time_range.start.date().isocalendar()[1]
                if abs(existing_week - assignment_week) == 1:
                    consecutive_count += 1

        if consecutive_count > max_consecutive_weeks:
            conflicts.append(
                Conflict(
                    conflict_type="consecutive_weeks",
                    severity=ConflictSeverity.WARNING,
                    message=f"Would exceed {max_consecutive_weeks} consecutive weeks limit",
                    affected_time_range=assignment.shift.time_range,
                    resolution_suggestion="Assign to different employee",
                ),
            )

        return conflicts

    def _check_mutual_exclusivity_conflicts(
        self, assignment: Assignment, existing_assignments: list[Assignment],
    ) -> list[Conflict]:
        """Check for mutual exclusivity violations (e.g., incidents + waakdienst same week)."""
        conflicts = []

        if not assignment.shift:
            return conflicts

        # Get employee's assignments for the same week
        assignment_week_start = assignment.shift.time_range.start.date() - timedelta(
            days=assignment.shift.time_range.start.weekday(),
        )
        assignment_week_start + timedelta(days=6)

        employee_assignments = [
            a
            for a in existing_assignments
            if a.employee_id == assignment.employee_id and a.shift
        ]

        for existing in employee_assignments:
            if not existing.shift:
                continue

            existing_week_start = existing.shift.time_range.start.date() - timedelta(
                days=existing.shift.time_range.start.weekday(),
            )

            # Check if same week
            if existing_week_start == assignment_week_start:
                # Check for mutual exclusivity
                if (
                    assignment.shift.shift_type
                    in [ShiftType.INCIDENTS, ShiftType.INCIDENTS_STANDBY]
                    and existing.shift.shift_type == ShiftType.WAAKDIENST
                ):
                    conflicts.append(
                        Conflict(
                            conflict_type="mutual_exclusivity",
                            severity=ConflictSeverity.BLOCKING,
                            message="Cannot have incidents and waakdienst in same week",
                            affected_time_range=assignment.shift.time_range,
                            resolution_suggestion="Assign to different employee",
                        ),
                    )
                elif (
                    assignment.shift.shift_type == ShiftType.WAAKDIENST
                    and existing.shift.shift_type
                    in [ShiftType.INCIDENTS, ShiftType.INCIDENTS_STANDBY]
                ):
                    conflicts.append(
                        Conflict(
                            conflict_type="mutual_exclusivity",
                            severity=ConflictSeverity.BLOCKING,
                            message="Cannot have waakdienst and incidents in same week",
                            affected_time_range=assignment.shift.time_range,
                            resolution_suggestion="Assign to different employee",
                        ),
                    )

        return conflicts


@dataclass
class ValidationResult:
    """Result of constraint validation."""

    is_valid: bool
    violations: list[str]


@dataclass
class ValidationContext:
    """Context for validation operations."""

    team_config: TeamConfiguration
    current_assignments: list[Assignment]
    employees: list[Employee]


class ConstraintValidator:
    """Validate business constraints for assignments.

    Based on Phase 1 analysis of business requirements.
    """

    def __init__(self, config: TeamConfiguration):
        self.config = config

    def validate_assignment(
        self, assignment: Assignment, employee: Employee, context: ValidationContext,
    ) -> ValidationResult:
        """Validate assignment against all business constraints."""

        violations = []

        if not assignment.shift:
            violations.append("Assignment has no associated shift")
            return ValidationResult(is_valid=False, violations=violations)

        # Employee availability
        if not self._validate_employee_availability(assignment, employee):
            violations.append("Employee not available for this shift type")

        # Timezone compatibility
        if not self._validate_timezone_compatibility(assignment, employee):
            violations.append("Timezone mismatch between employee and shift")

        # Business hours compliance
        if not self._validate_business_hours(assignment):
            violations.append("Shift outside configured business hours")

        # Team membership
        if not self._validate_team_membership(assignment, employee):
            violations.append("Employee not member of shift's team")

        return ValidationResult(is_valid=len(violations) == 0, violations=violations)

    def validate_coverage_completeness(
        self, shifts: list[Shift],
    ) -> "CoverageValidation":
        """Validate that all required hours are covered."""

        coverage_gaps = []

        # Group shifts by date
        shifts_by_date = defaultdict(list)
        for shift in shifts:
            shift_date = shift.time_range.start.date()
            shifts_by_date[shift_date].append(shift)

        # Check each date for coverage gaps
        for shift_date, date_shifts in shifts_by_date.items():
            day_of_week = shift_date.weekday()

            # Check business hours coverage
            business_hours = self.config.get_business_hours_range(shift_date)
            if business_hours:
                incidents_coverage = any(
                    shift.shift_type
                    in [ShiftType.INCIDENTS, ShiftType.INCIDENTS_STANDBY]
                    for shift in date_shifts
                )
                if not incidents_coverage:
                    coverage_gaps.append(f"No incidents coverage on {shift_date}")

            # Check 24/7 coverage (waakdienst should cover non-business hours)
            has_waakdienst = any(
                shift.shift_type == ShiftType.WAAKDIENST for shift in date_shifts
            )
            if not has_waakdienst and (day_of_week >= 5 or not business_hours):
                coverage_gaps.append(f"No waakdienst coverage on {shift_date}")

        return CoverageValidation(
            is_complete=len(coverage_gaps) == 0, gaps=coverage_gaps,
        )

    def _validate_employee_availability(
        self, assignment: Assignment, employee: Employee,
    ) -> bool:
        """Validate employee is available for shift type."""
        if not assignment.shift:
            return False

        return employee.is_available_for_shift(
            assignment.shift.shift_type, assignment.shift.time_range,
        )

    def _validate_timezone_compatibility(
        self, assignment: Assignment, employee: Employee,
    ) -> bool:
        """Validate timezone compatibility."""
        if not assignment.shift:
            return False

        # For now, assume all employees work in team timezone
        # In a real implementation, employees might have their own timezone preferences
        return assignment.shift.time_range.timezone == self.config.timezone

    def _validate_business_hours(self, assignment: Assignment) -> bool:
        """Validate shift falls within business hours if required."""
        if not assignment.shift:
            return False

        # Only incidents and incidents-standby need to be within business hours
        if not assignment.shift.shift_type.requires_business_hours:
            return True

        shift_date = assignment.shift.time_range.start.date()
        business_hours = self.config.get_business_hours_range(shift_date)

        if not business_hours:
            return False  # No business hours defined for this day

        return business_hours.contains(assignment.shift.time_range.start)

    def _validate_team_membership(
        self, assignment: Assignment, employee: Employee,
    ) -> bool:
        """Validate employee belongs to shift's team."""
        if not assignment.shift:
            return False

        return employee.team_id == assignment.shift.team_id


@dataclass
class CoverageValidation:
    """Result of coverage validation."""

    is_complete: bool
    gaps: list[str]


@dataclass
class AssignmentContext:
    """Context for assignment operations."""

    team_config: TeamConfiguration
    current_assignments: list[Assignment]
    employees: list[Employee]

    def get_assignments_for_employee(self, employee_id: EmployeeId) -> list[Assignment]:
        """Get all assignments for a specific employee."""
        return [a for a in self.current_assignments if a.employee_id == employee_id]
