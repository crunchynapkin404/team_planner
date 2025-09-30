"""
Incidents-Standby Orchestrator for Split Orchestrator System

This module provides the IncidentsStandbyOrchestrator class that handles incidents-standby
shift scheduling using the same sophisticated week-long assignment strategy as the incidents
orchestrator. It inherits from BaseOrchestrator but provides separate fairness tracking
for standby assignments.
"""

import logging
from datetime import datetime
from datetime import timedelta
from typing import Any

from django.contrib.auth import get_user_model

from team_planner.employees.models import EmployeeProfile
from team_planner.orchestrators.base import BaseOrchestrator
from team_planner.orchestrators.constraints import BaseConstraintChecker
from team_planner.orchestrators.constraints import ConstraintCheckerFactory
from team_planner.orchestrators.fairness import BaseFairnessCalculator
from team_planner.orchestrators.fairness import FairnessCalculatorFactory
from team_planner.orchestrators.utils.time_windows import business_day_window
from team_planner.shifts.models import ShiftType

User = get_user_model()
logger = logging.getLogger(__name__)


class IncidentsStandbyOrchestrator(BaseOrchestrator):
    """
    Orchestrator for incidents-standby shifts using week-long assignment strategy.

    This orchestrator implements the same sophisticated week-long assignment logic
    as IncidentsOrchestrator but for standby shifts, with separate fairness tracking
    to prevent conflicts between incidents and incidents-standby assignments.
    """

    def __init__(
        self, start_date: datetime, end_date: datetime, team_id: int | None = None,
    ):
        """Initialize the incidents-standby orchestrator."""
        super().__init__(start_date, end_date, team_id)

    def _get_handled_shift_types(self) -> list[str]:
        """Return shift types handled by this orchestrator."""
        return [ShiftType.INCIDENTS_STANDBY]

    def _create_fairness_calculator(self) -> BaseFairnessCalculator:
        """Create incidents-standby fairness calculator for this period."""
        return FairnessCalculatorFactory.create_standby_calculator(
            self.start_date, self.end_date,
        )

    def _create_constraint_checker(self) -> BaseConstraintChecker:
        """Create incidents-standby constraint checker."""
        return ConstraintCheckerFactory.create_incidents_checker(
            self.start_date, self.end_date,
        )

    def _generate_time_periods(self) -> list[tuple[datetime, datetime, str]]:
        """Generate weekly time periods for incidents-standby scheduling."""
        periods = []
        current = self.start_date

        while current < self.end_date:
            # Find the Monday of this week
            days_since_monday = current.weekday()
            monday = current - timedelta(days=days_since_monday)
            monday = monday.replace(hour=8, minute=0, second=0, microsecond=0)

            # End of this week (Friday 17:00)
            week_start = max(monday, self.start_date)
            # Friday of this week
            week_end = min(monday + timedelta(days=4, hours=9), self.end_date)

            if week_start < week_end:
                periods.append(
                    (week_start, week_end, f"Week {week_start.strftime('%Y-%m-%d')}"),
                )

            # Move to next Monday
            current = monday + timedelta(days=7)

        return periods

    def _get_available_employees(self) -> list[Any]:
        """Get employees available for incidents-standby shifts."""
        # Incidents-standby uses the same availability field as regular incidents
        return list(
            User.objects.filter(
                is_active=True,
                employee_profile__status=EmployeeProfile.Status.ACTIVE,
                employee_profile__available_for_incidents=True,  # Fixed: use available_for_incidents
            ).select_related("employee_profile"),
        )

    def _generate_daily_shifts(
        self, period_start: datetime, period_end: datetime, period_label: str,
    ) -> list[tuple[datetime, datetime, str]]:
        """Generate daily shifts for Monday-Friday business days."""
        daily_shifts = []
        current = period_start

        while current < period_end:
            # Only Monday-Friday (weekdays 0-4)
            if current.weekday() < 5:
                day_start, day_end = business_day_window(current)

                # Ensure we don't go beyond period_end
                if day_start < period_end:
                    actual_end = min(day_end, period_end)
                    daily_shifts.append(
                        (day_start, actual_end, f"{current.strftime('%A %Y-%m-%d')}"),
                    )

            # Move to next day
            current += timedelta(days=1)

        return daily_shifts

    def _generate_period_assignments(
        self,
        period_start: datetime,
        period_end: datetime,
        period_label: str,
        available_employees: list[Any],
    ) -> list[dict]:
        """
        Generate assignments for incidents-standby using week-long assignment logic.

        This is identical to IncidentsOrchestrator logic but with standby-specific
        fairness tracking and availability checking.
        """
        from collections import defaultdict

        assignments = []

        # Get daily shifts for this period (Monday-Friday business week)
        daily_shifts = self._generate_daily_shifts(
            period_start, period_end, period_label,
        )

        if not daily_shifts:
            return assignments

        # Track assignments made in this run for fairness
        new_assignments = defaultdict(
            lambda: {"incidents": 0.0, "incidents_standby": 0.0, "waakdienst": 0.0},
        )

        # Get current assignments for fairness calculation (historical + already assigned in this run)
        current_assignments = self.fairness_calculator.calculate_current_assignments(
            available_employees,
        )

        # Add assignments already made in THIS orchestration run to the fairness calculation
        for assignment in self.current_assignments:
            emp_id = assignment.get("assigned_employee_id")
            shift_type = assignment.get("shift_type", "").lower()
            duration_hours = assignment.get("duration_hours", 0.0)

            if (
                emp_id
                and emp_id in [emp.pk for emp in available_employees]
                and shift_type == "incidents_standby"
            ):
                if emp_id not in current_assignments:
                    current_assignments[emp_id] = {
                        "incidents": 0.0,
                        "incidents_standby": 0.0,
                        "waakdienst": 0.0,
                    }
                current_assignments[emp_id]["incidents_standby"] += duration_hours

        # Check each employee's availability for this specific week
        employee_availability = {}

        for emp in available_employees:
            # Check partial availability for the week
            available_days = 0
            total_possible_hours = 0
            available_hours = 0
            conflicts = []

            for day_start, day_end, day_label in daily_shifts:
                day_start.date()
                day_hours = (day_end - day_start).total_seconds() / 3600.0
                total_possible_hours += day_hours

                # Check if employee is available for this day
                availability_result = (
                    self.constraint_checker.check_employee_availability(
                        emp, day_start.date(),
                    )
                )
                if availability_result.is_available:
                    available_days += 1
                    available_hours += day_hours
                else:
                    conflicts.append(day_label)

            # Store availability info for this employee
            employee_availability[emp.pk] = {
                "available_days": available_days,
                "total_days": len(daily_shifts),
                "conflicts": conflicts,
                "available_hours": available_hours,
                "total_possible_hours": total_possible_hours,
                "availability_ratio": available_hours / total_possible_hours
                if total_possible_hours > 0
                else 0.0,
            }

        # Separate employees into fully vs partially available
        fully_available = []
        partially_available = []

        for emp in available_employees:
            availability = employee_availability.get(emp.pk, {})
            if availability.get("availability_ratio", 0) >= 1.0:
                fully_available.append(emp)
            elif availability.get("availability_ratio", 0) > 0:
                partially_available.append(emp)

        logger.info(
            f"Week {period_label}: {len(fully_available)} fully available, {len(partially_available)} partially available",
        )

        # Strategy 1: Try to assign entire week to a fully available employee
        if fully_available:
            # Sort by fairness (least assigned first)
            def sort_key(emp):
                return (
                    current_assignments.get(emp.pk, {}).get("incidents_standby", 0.0)
                    + new_assignments[emp.pk]["incidents_standby"]
                )

            fully_available.sort(key=sort_key)
            chosen_employee = fully_available[0]

            logger.info(
                f"Assigning entire week {period_label} to {chosen_employee.username} (fully available)",
            )

            # Assign all days to this employee
            for day_start, day_end, day_label in daily_shifts:
                assignment = self._create_day_assignment(
                    chosen_employee, day_start, day_end, day_label,
                )
                assignments.append(assignment)

                # Track assignment for fairness accumulation within this orchestration run
                self.current_assignments.append(assignment)

                # Track for fairness
                hours = (day_end - day_start).total_seconds() / 3600.0
                new_assignments[chosen_employee.pk]["incidents_standby"] += hours

        # Strategy 2: Assign to partially available employees with coverage for conflicts
        elif partially_available:
            assignments.extend(
                self._assign_partial_week_with_coverage(
                    daily_shifts,
                    partially_available,
                    available_employees,
                    current_assignments,
                    new_assignments,
                    employee_availability,
                ),
            )

        # Strategy 3: No one available - log warning
        else:
            logger.warning(f"No employees available for week {period_label}")

        return assignments

    def _assign_partial_week_with_coverage(
        self,
        daily_shifts,
        partially_available,
        all_employees,
        current_assignments,
        new_assignments,
        employee_availability,
    ):
        """Assign week-long assignment with day-level reassignment for conflicts only."""
        assignments = []

        if not partially_available:
            return assignments

        # Pick the most available employee as primary
        def availability_sort_key(emp):
            availability = employee_availability.get(emp.pk, {})
            fairness = (
                current_assignments.get(emp.pk, {}).get("incidents_standby", 0.0)
                + new_assignments[emp.pk]["incidents_standby"]
            )
            return (-availability.get("availability_ratio", 0), fairness)

        partially_available.sort(key=availability_sort_key)
        primary_employee = partially_available[0]

        logger.info(
            f"Using {primary_employee.username} as primary for partial week (conflicts: {employee_availability[primary_employee.pk]['conflicts']})",
        )

        # Assign primary employee to all non-conflicted days
        for day_start, day_end, day_label in daily_shifts:
            if day_label not in employee_availability[primary_employee.pk]["conflicts"]:
                assignment = self._create_day_assignment(
                    primary_employee, day_start, day_end, day_label,
                )
                assignments.append(assignment)

                # Track assignment for fairness accumulation within this orchestration run
                self.current_assignments.append(assignment)

                # Track for fairness
                hours = (day_end - day_start).total_seconds() / 3600.0
                new_assignments[primary_employee.pk]["incidents_standby"] += hours

        # Find coverage for conflicted days
        for day_start, day_end, day_label in daily_shifts:
            if day_label in employee_availability[primary_employee.pk]["conflicts"]:
                coverage_assignment = self._find_day_coverage(
                    day_start,
                    day_end,
                    day_label,
                    all_employees,
                    current_assignments,
                    new_assignments,
                )
                if coverage_assignment:
                    assignments.append(coverage_assignment)

                    # Track assignment for fairness accumulation within this orchestration run
                    self.current_assignments.append(coverage_assignment)

        return assignments

    def _find_day_coverage(
        self,
        start_datetime,
        end_datetime,
        label,
        all_employees,
        current_assignments,
        new_assignments,
    ):
        """Find coverage for a single conflicted day."""
        # Find available employees for this specific day
        available_for_day = []
        for emp in all_employees:
            availability_result = self.constraint_checker.check_employee_availability(
                emp, start_datetime.date(),
            )
            if availability_result.is_available:
                available_for_day.append(emp)

        if not available_for_day:
            logger.warning(f"No coverage available for {label}")
            return None

        # Sort by fairness (least assigned first)
        def fairness_sort_key(emp):
            return (
                current_assignments.get(emp.pk, {}).get("incidents_standby", 0.0)
                + new_assignments[emp.pk]["incidents_standby"]
            )

        available_for_day.sort(key=fairness_sort_key)
        coverage_employee = available_for_day[0]

        logger.info(f"Coverage for {label}: {coverage_employee.username}")

        # Create assignment and track fairness
        assignment = self._create_day_assignment(
            coverage_employee, start_datetime, end_datetime, label,
        )
        hours = (end_datetime - start_datetime).total_seconds() / 3600.0
        new_assignments[coverage_employee.pk]["incidents_standby"] += hours

        return assignment
