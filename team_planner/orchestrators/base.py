"""
Base Orchestrator Interface for Split Orchestrator System

This module provides the abstract base class and common interfaces for the split
orchestrator architecture. Each specialized orchestrator inherits from BaseOrchestrator
and implements shift-type-specific logic while sharing common utilities.

The BaseOrchestrator provides:
- Common orchestration lifecycle methods
- Shared utilities for shift creation and tracking
- Standard interfaces for day-by-day generation
- Integration with fairness calculators and constraint checkers
"""

import logging
from abc import ABC
from abc import abstractmethod
from datetime import datetime
from datetime import timedelta
from decimal import Decimal
from typing import Any

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from team_planner.orchestrators.constraints import BaseConstraintChecker
from team_planner.orchestrators.fairness import BaseFairnessCalculator
from team_planner.orchestrators.models import OrchestrationResult
from team_planner.orchestrators.models import OrchestrationRun
from team_planner.shifts.models import Shift
from team_planner.shifts.models import ShiftTemplate
from team_planner.shifts.models import ShiftType

User = get_user_model()
logger = logging.getLogger(__name__)


class BaseOrchestrator(ABC):
    """
    Abstract base class for all shift orchestrators.

    Provides common functionality for day-by-day shift generation with constraint-first
    approach. Each subclass implements shift-type-specific logic while using shared
    utilities for assignment creation and tracking.
    """

    def __init__(
        self, start_date: datetime, end_date: datetime, team_id: int | None = None,
    ):
        self.start_date = start_date
        self.end_date = end_date
        self.team_id = team_id

        # Initialize shift-type-specific calculators and checkers
        self.shift_types = self._get_handled_shift_types()
        self.fairness_calculator = self._create_fairness_calculator()
        self.constraint_checker = self._create_constraint_checker()

        # Track assignments made during this orchestration run
        self.current_assignments: list[dict] = []
        self.orchestration_run: OrchestrationRun | None = None

    @abstractmethod
    def _get_handled_shift_types(self) -> list[str]:
        """Return the shift types this orchestrator handles."""

    @abstractmethod
    def _create_fairness_calculator(self) -> BaseFairnessCalculator:
        """Create the appropriate fairness calculator for this orchestrator."""

    @abstractmethod
    def _create_constraint_checker(self) -> BaseConstraintChecker:
        """Create the appropriate constraint checker for this orchestrator."""

    @abstractmethod
    def _generate_time_periods(self) -> list[tuple[datetime, datetime, str]]:
        """Generate the time periods this orchestrator should handle."""

    @abstractmethod
    def _get_available_employees(self) -> list[Any]:
        """Get employees available for this orchestrator's shift types."""

    def generate_schedule(
        self, orchestration_run: OrchestrationRun | None = None,
    ) -> dict[str, Any]:
        """
        Generate complete schedule for this orchestrator's shift types.

        This is the main entry point for schedule generation using the
        constraint-first, day-by-day approach.
        """
        self.orchestration_run = orchestration_run
        self.current_assignments = []

        logger.info(
            f"Starting {self.__class__.__name__} for period {self.start_date} to {self.end_date}",
        )

        # Get available employees
        available_employees = self._get_available_employees()
        if not available_employees:
            logger.warning(f"No employees available for {self.shift_types}")
            return self._create_empty_result()

        logger.info(f"Found {len(available_employees)} available employees")

        # Generate time periods for this orchestrator
        periods = self._generate_time_periods()
        logger.info(f"Generated {len(periods)} time periods")

        # Process each period with day-by-day generation
        all_assignments = []
        for period_start, period_end, period_label in periods:
            period_assignments = self._generate_period_assignments(
                period_start, period_end, period_label, available_employees,
            )
            all_assignments.extend(period_assignments)

            # Track assignments for conflict prevention
            self.current_assignments.extend(period_assignments)

        logger.info(f"Generated {len(all_assignments)} total assignments")

        # Apply reassignment to resolve conflicts
        all_assignments = self._apply_reassignment_if_needed(all_assignments)

        # Calculate metrics and return result
        return self._create_result(all_assignments, available_employees)

    def _apply_reassignment_if_needed(self, assignments: list[dict]) -> list[dict]:
        """Apply reassignment logic to resolve conflicts."""
        if not self.orchestration_run:
            return assignments

        try:
            from .reassignment import ShiftReassignmentManager

            # Create reassignment manager
            reassignment_manager = ShiftReassignmentManager(
                self.orchestration_run, self.fairness_calculator, team_id=self.team_id,
            )

            logger.info("Starting conflict detection and reassignment...")
            conflicts = reassignment_manager.detect_conflicts(assignments)

            if conflicts:
                logger.info(
                    f"Detected {len(conflicts)} conflicts, attempting automatic reassignment",
                )
                reassignment_manager.resolve_conflicts(conflicts)

                # Handle split assignments by replacing with individual daily assignments
                updated_assignments = []
                for assignment in assignments:
                    if assignment.get("is_split_assignment", False):
                        # This assignment was split, replace with individual daily assignments
                        split_info = assignment.get("split_coverage")
                        if split_info:
                            daily_assignments = (
                                reassignment_manager.create_split_shift_assignments(
                                    assignment, split_info,
                                )
                            )
                            updated_assignments.extend(daily_assignments)
                            logger.info(
                                f"Replaced split assignment with {len(daily_assignments)} daily assignments",
                            )
                        else:
                            updated_assignments.append(assignment)
                    else:
                        updated_assignments.append(assignment)

                reassignment_summary = reassignment_manager.get_reassignment_summary()
                logger.info(
                    f"Reassignment complete: {reassignment_summary['successful_reassignments']} successful, {reassignment_summary['failed_reassignments']} failed",
                )

                return updated_assignments
            logger.info("No conflicts detected")
            return assignments

        except Exception as e:
            logger.exception(f"Error during reassignment: {e}")
            return assignments

    def _generate_period_assignments(
        self,
        period_start: datetime,
        period_end: datetime,
        period_label: str,
        available_employees: list[Any],
    ) -> list[dict]:
        """
        Generate assignments for a single period using day-by-day logic.

        This implements the core constraint-first generation algorithm:
        1. Check constraints for each day
        2. Prefer continuity when possible
        3. Handle conflicts at day level
        4. No post-processing needed
        """
        assignments = []

        # Get daily shifts for this period
        daily_shifts = self._generate_daily_shifts(
            period_start, period_end, period_label,
        )

        # Day-by-day assignment with continuity preference
        current_employee = None

        for day_start, day_end, day_label in daily_shifts:
            day_date = day_start.date()

            # Get employees available for this specific day
            day_available_employees = self._get_employees_available_for_day(
                available_employees, day_date,
            )

            if not day_available_employees:
                logger.warning(f"No employees available for {day_label} on {day_date}")
                continue

            # Prefer continuity: if current employee is available, keep them
            if (
                current_employee
                and current_employee in day_available_employees
                and self._can_continue_assignment(current_employee, day_date)
            ):
                chosen_employee = current_employee
                logger.debug(f"Continuing {chosen_employee.username} for {day_label}")

            else:
                # Need to pick a new employee
                chosen_employee = self._select_best_employee_for_day(
                    day_available_employees, day_date, day_label,
                )
                current_employee = chosen_employee
                logger.debug(f"Selected {chosen_employee.username} for {day_label}")

            # Create assignment for this day
            assignment = self._create_day_assignment(
                chosen_employee, day_start, day_end, day_label,
            )
            assignments.append(assignment)

        return assignments

    def _get_employees_available_for_day(
        self, employees: list[Any], check_date,
    ) -> list[Any]:
        """Get employees available for assignment on a specific date."""
        available = []

        for employee in employees:
            result = self.constraint_checker.check_employee_availability(
                employee, check_date,
            )
            if result.is_available:
                available.append(employee)
            else:
                logger.debug(
                    f"Employee {employee.username} not available on {check_date}: {result.reason}",
                )

        return available

    def _can_continue_assignment(self, employee: Any, check_date) -> bool:
        """Check if employee can continue with assignment (no new conflicts)."""
        # Additional check for assignment continuity
        # This can be overridden by subclasses for specific logic
        return True

    def _select_best_employee_for_day(
        self, available_employees: list[Any], check_date, day_label: str,
    ) -> Any:
        """Select the best employee for a single day based on fairness."""
        # Use fairness calculator to find least assigned employee
        return self.fairness_calculator.get_least_assigned_employee(available_employees)

    @abstractmethod
    def _generate_daily_shifts(
        self, period_start: datetime, period_end: datetime, period_label: str,
    ) -> list[tuple[datetime, datetime, str]]:
        """Generate daily shifts within a period. Implementation depends on shift type."""

    def _create_day_assignment(
        self,
        employee: Any,
        start_datetime: datetime,
        end_datetime: datetime,
        label: str,
    ) -> dict:
        """Create a single day assignment dictionary."""
        # Get template for the first shift type this orchestrator handles
        shift_type = self.shift_types[0]
        template = self._get_shift_template(shift_type)

        return {
            "assigned_employee_id": employee.pk,
            "assigned_employee_name": employee.get_full_name() or employee.username,
            "start_datetime": start_datetime,
            "end_datetime": end_datetime,
            "shift_type": shift_type,
            "template": template,  # Provide template object, not ID
            "template_id": template.pk if template else None,
            "label": label,
            "auto_assigned": True,
            "assignment_reason": f"Generated by {self.__class__.__name__}",
            "duration_hours": (end_datetime - start_datetime).total_seconds() / 3600,
        }


    def _get_shift_template(self, shift_type: str) -> ShiftTemplate | None:
        """Get or create shift template for the given type."""
        try:
            template = ShiftTemplate.objects.filter(
                shift_type=shift_type, is_active=True,
            ).first()

            if not template:
                # Create a basic template
                duration_hours = self._get_default_duration_hours(shift_type)
                template = ShiftTemplate.objects.create(
                    shift_type=shift_type,
                    name=f"{shift_type.replace('_', '-').title()} Daily Shift",
                    description=f"Individual daily shift for {shift_type.replace('_', '-')}",
                    duration_hours=duration_hours,
                    is_active=True,
                )
                logger.info(f"Created new shift template for {shift_type}")

            return template

        except Exception as e:
            logger.exception(f"Error getting shift template for {shift_type}: {e}")
            return None

    def _get_default_duration_hours(self, shift_type: str) -> int:
        """Get default duration hours for a shift type."""
        if shift_type in (ShiftType.INCIDENTS, ShiftType.INCIDENTS_STANDBY):
            return 9  # 08:00-17:00
        if shift_type == ShiftType.WAAKDIENST:
            return 15  # Average daily shift
        return 8  # Default

    def _create_result(
        self, assignments: list[dict], employees: list[Any],
    ) -> dict[str, Any]:
        """Create the final result dictionary with metrics."""
        if not assignments:
            return self._create_empty_result()

        # Calculate metrics by shift type
        shift_counts = {}
        for shift_type in self.shift_types:
            shift_counts[f"{shift_type}_shifts"] = len(
                [a for a in assignments if a["shift_type"] == shift_type],
            )

        # Calculate fairness metrics
        [emp.pk for emp in employees]
        provisional_assignments = (
            self.fairness_calculator.calculate_provisional_assignments(assignments)
        )
        fairness_scores = self.fairness_calculator.calculate_fairness_score(
            provisional_assignments,
        )

        result = {
            "assignments": assignments,
            "total_shifts": len(assignments),
            "employees_assigned": len(
                {a["assigned_employee_id"] for a in assignments},
            ),
            "fairness_scores": fairness_scores,
            "average_fairness": sum(fairness_scores.values()) / len(fairness_scores)
            if fairness_scores
            else 0,
            "period_start": self.start_date,
            "period_end": self.end_date,
            "orchestrator_type": self.__class__.__name__,
            "shift_types": self.shift_types,
        }

        # Add shift type specific counts
        result.update(shift_counts)

        return result

    def _create_empty_result(self) -> dict[str, Any]:
        """Create an empty result when no assignments are made."""
        result = {
            "assignments": [],
            "total_shifts": 0,
            "employees_assigned": 0,
            "fairness_scores": {},
            "average_fairness": 0.0,
            "period_start": self.start_date,
            "period_end": self.end_date,
            "orchestrator_type": self.__class__.__name__,
            "shift_types": self.shift_types,
        }

        # Add zero counts for each shift type
        for shift_type in self.shift_types:
            result[f"{shift_type}_shifts"] = 0

        return result

    def apply_schedule(self, result: dict[str, Any]) -> dict[str, Any]:
        """
        Apply the generated schedule to the database by creating actual Shift objects.

        This method should be called after generate_schedule() to persist the assignments.
        """
        assignments = result.get("assignments", [])
        if not assignments:
            logger.info("No assignments to apply")
            return {"created_shifts": 0, "skipped_duplicates": 0}

        created_shifts = []
        skipped_duplicates = []

        with transaction.atomic():
            for assignment in assignments:
                # Check for duplicates
                if self._check_for_duplicate_shift(assignment):
                    skipped_duplicates.append(assignment)
                    continue

                # Create the shift
                try:
                    shift = self._create_shift_from_assignment(assignment)
                    created_shifts.append(shift)

                    # Create orchestration result record if we have an orchestration run
                    if self.orchestration_run:
                        self._create_orchestration_result(assignment, shift)

                except Exception as e:
                    logger.exception(f"Error creating shift: {e}")
                    continue

        logger.info(
            f"Applied schedule: {len(created_shifts)} shifts created, {len(skipped_duplicates)} duplicates skipped",
        )

        return {
            "created_shifts": len(created_shifts),
            "skipped_duplicates": len(skipped_duplicates),
            "shifts": created_shifts,
            "duplicates": skipped_duplicates,
        }

    def _check_for_duplicate_shift(self, assignment: dict) -> bool:
        """Check if a shift already exists for the same time period and type."""
        existing = Shift.objects.filter(
            template__shift_type=assignment["shift_type"],
            start_datetime=assignment["start_datetime"],
            end_datetime=assignment["end_datetime"],
            assigned_employee_id=assignment["assigned_employee_id"],
        ).exists()

        if existing:
            logger.warning(
                f"Duplicate shift detected: {assignment['shift_type']} "
                f"for {assignment['assigned_employee_name']} "
                f"from {assignment['start_datetime']} to {assignment['end_datetime']}",
            )

        return existing

    def _create_shift_from_assignment(self, assignment: dict) -> Shift:
        """Create a Shift object from an assignment dictionary."""
        template = None
        if assignment.get("template_id"):
            try:
                template = ShiftTemplate.objects.get(pk=assignment["template_id"])
            except ShiftTemplate.DoesNotExist:
                logger.warning(f"Template {assignment['template_id']} not found")

        employee = User.objects.get(pk=assignment["assigned_employee_id"])

        return Shift.objects.create(
            template=template,
            assigned_employee=employee,
            start_datetime=assignment["start_datetime"],
            end_datetime=assignment["end_datetime"],
            status=Shift.Status.SCHEDULED,
            auto_assigned=assignment.get("auto_assigned", True),
            assignment_reason=assignment.get("assignment_reason", ""),
            notes=f"Generated by {self.__class__.__name__}",
        )


    def _create_orchestration_result(
        self, assignment: dict, shift: Shift,
    ) -> OrchestrationResult | None:
        """Create an OrchestrationResult record for tracking."""
        if not self.orchestration_run:
            return None

        # Calculate week period (this might need adjustment based on orchestrator type)
        start_date = assignment["start_datetime"].date()
        week_start = start_date - timedelta(days=start_date.weekday())
        week_end = week_start + timedelta(days=6)

        return OrchestrationResult.objects.create(
            orchestration_run=self.orchestration_run,
            employee_id=assignment["assigned_employee_id"],
            shift_type=assignment["shift_type"],
            week_start_date=week_start,
            week_end_date=week_end,
            fairness_score_before=Decimal("0.0"),  # Could be calculated if needed
            fairness_score_after=Decimal("0.0"),  # Could be calculated if needed
            assignment_reason=assignment.get("assignment_reason", ""),
            is_applied=True,
            applied_at=timezone.now(),
        )


    def preview_schedule(self) -> dict[str, Any]:
        """Generate a preview of the schedule without saving to database."""
        return self.generate_schedule()

    def get_orchestrator_name(self) -> str:
        """Get the name of this orchestrator for logging and identification."""
        return self.__class__.__name__
