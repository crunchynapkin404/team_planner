"""
Split Fairness Calculators for Orchestrator System

This module provides specialized fairness calculators for each shift type,
replacing the monolithic FairnessCalculator with focused, single-responsibility calculators.

Each calculator tracks fairness independently for its specific shift type:
- IncidentsFairnessCalculator: Only Incidents shifts
- IncidentsStandbyFairnessCalculator: Only Incidents-Standby shifts
- WaakdienstFairnessCalculator: Only Waakdienst shifts
"""

import logging
from collections import defaultdict
from datetime import datetime
from datetime import timedelta
from typing import Any

from django.contrib.auth import get_user_model

from team_planner.shifts.models import Shift
from team_planner.shifts.models import ShiftType

User = get_user_model()
logger = logging.getLogger(__name__)


class BaseFairnessCalculator:
    """Base class for all fairness calculators with common functionality."""

    # Shared tuning parameters
    WEEKEND_WEIGHT = 1.2
    HOLIDAY_WEIGHT = 1.5
    MANUAL_OVERRIDE_MULTIPLIER = 0.8
    HISTORY_WINDOW_DAYS = 180
    DECAY_HALF_LIFE_DAYS = 90

    def __init__(self, start_date: datetime, end_date: datetime):
        self.start_date = start_date
        self.end_date = end_date
        self._shift_types = self._get_tracked_shift_types()

    def _get_tracked_shift_types(self) -> list[str]:
        """Return the shift types this calculator tracks. Override in subclasses."""
        msg = "Subclasses must implement _get_tracked_shift_types"
        raise NotImplementedError(msg)

    def _get_base_queryset(self):
        """Get base queryset for shifts this calculator tracks.

        For fairness calculation, we look at historical data, not the future period
        being scheduled. This ensures fairness is based on past assignments.
        """
        # Look at historical data in a rolling window, not the scheduling period
        history_end = self.start_date  # Up to when scheduling starts
        history_start = history_end - timedelta(days=self.HISTORY_WINDOW_DAYS)

        return Shift.objects.filter(
            template__shift_type__in=self._shift_types,
            start_datetime__gte=history_start,
            start_datetime__lt=history_end,  # Don't include the period being scheduled
        ).select_related("assigned_employee", "template")

    def calculate_current_assignments(
        self, employees: list[Any],
    ) -> dict[int, dict[str, float]]:
        """Calculate current shift assignments for given employees."""
        if not employees:
            return {}

        # Get employee IDs
        employee_ids = [emp.pk for emp in employees]

        # Query shifts for these employees in our tracked shift types
        shifts = self._get_base_queryset().filter(assigned_employee__in=employee_ids)

        # Initialize result structure
        assignments = {}
        for emp in employees:
            assignments[emp.pk] = dict.fromkeys(self._shift_types, 0.0)

        # Calculate hours per employee per shift type
        for shift in shifts:
            if shift.assigned_employee.pk in assignments:
                duration_hours = (
                    shift.end_datetime - shift.start_datetime
                ).total_seconds() / 3600
                shift_type_key = shift.template.shift_type.lower()
                if shift_type_key in assignments[shift.assigned_employee.pk]:
                    assignments[shift.assigned_employee.pk][shift_type_key] += (
                        duration_hours
                    )

        return assignments

    def calculate_provisional_assignments(
        self, assignments_list: list[dict],
    ) -> dict[int, dict[str, float]]:
        """Calculate provisional assignments from a list of assignment dictionaries."""
        provisional = defaultdict(
            lambda: dict.fromkeys(self._shift_types, 0.0),
        )

        for assignment in assignments_list:
            emp_id = assignment.get("assigned_employee_id")
            shift_type = assignment.get("shift_type", "").lower()
            duration_hours = assignment.get("duration_hours", 0.0)

            if emp_id and shift_type in [st.lower() for st in self._shift_types]:
                provisional[emp_id][shift_type] += duration_hours

        return dict(provisional)

    def calculate_fairness_score(
        self, assignments: dict[int, dict[str, float]],
    ) -> dict[int, float]:
        """Calculate fairness scores based on assignments."""
        if not assignments:
            return {}

        fairness_scores = {}

        # Calculate total hours per employee across all tracked shift types
        total_hours = {}
        for emp_id, shift_assignments in assignments.items():
            total_hours[emp_id] = sum(shift_assignments.values())

        # Calculate average hours
        all_hours = list(total_hours.values())
        if not all_hours:
            return dict.fromkeys(assignments.keys(), 0.0)

        avg_hours = sum(all_hours) / len(all_hours)

        # Calculate fairness score (lower is better - less overworked)
        for emp_id, hours in total_hours.items():
            if avg_hours > 0:
                # Score based on deviation from average
                fairness_scores[emp_id] = hours / avg_hours
            else:
                fairness_scores[emp_id] = 0.0

        return fairness_scores

    def get_least_assigned_employee(self, employees: list[Any]) -> Any | None:
        """Get the employee with the least assignments in tracked shift types."""
        assignments = self.calculate_current_assignments(employees)
        fairness_scores = self.calculate_fairness_score(assignments)

        if not fairness_scores:
            return employees[0] if employees else None

        # Return employee with lowest fairness score (least assigned)
        least_assigned_id = min(
            fairness_scores.keys(), key=lambda x: fairness_scores[x],
        )

        for emp in employees:
            if emp.pk == least_assigned_id:
                return emp

        return employees[0] if employees else None


class IncidentsFairnessCalculator(BaseFairnessCalculator):
    """Fairness calculator specifically for Incidents shifts only."""

    def _get_tracked_shift_types(self) -> list[str]:
        return [ShiftType.INCIDENTS]

    def calculate_incidents_load(self, employees: list[Any]) -> dict[int, float]:
        """Calculate the current incidents workload for each employee."""
        assignments = self.calculate_current_assignments(employees)
        return {
            emp_id: data.get("incidents", 0.0) for emp_id, data in assignments.items()
        }

    def get_next_incidents_candidate(self, employees: list[Any]) -> Any | None:
        """Get the next best candidate for incidents assignment based on fairness."""
        incidents_loads = self.calculate_incidents_load(employees)

        if not incidents_loads:
            return employees[0] if employees else None

        # Sort by incidents load (ascending - least loaded first)
        sorted_employees = sorted(
            employees, key=lambda emp: incidents_loads.get(emp.pk, 0.0),
        )
        return sorted_employees[0] if sorted_employees else None


class IncidentsStandbyFairnessCalculator(BaseFairnessCalculator):
    """Fairness calculator specifically for Incidents-Standby shifts only."""

    def _get_tracked_shift_types(self) -> list[str]:
        return [ShiftType.INCIDENTS_STANDBY]

    def calculate_standby_load(self, employees: list[Any]) -> dict[int, float]:
        """Calculate the current incidents-standby workload for each employee."""
        assignments = self.calculate_current_assignments(employees)
        return {
            emp_id: data.get("incidents_standby", 0.0)
            for emp_id, data in assignments.items()
        }

    def get_next_standby_candidate(self, employees: list[Any]) -> Any | None:
        """Get the next best candidate for incidents-standby assignment based on fairness."""
        standby_loads = self.calculate_standby_load(employees)

        if not standby_loads:
            return employees[0] if employees else None

        # Sort by standby load (ascending - least loaded first)
        sorted_employees = sorted(
            employees, key=lambda emp: standby_loads.get(emp.pk, 0.0),
        )
        return sorted_employees[0] if sorted_employees else None


class WaakdienstFairnessCalculator(BaseFairnessCalculator):
    """Fairness calculator specifically for Waakdienst shifts only."""

    def _get_tracked_shift_types(self) -> list[str]:
        return [ShiftType.WAAKDIENST]

    def calculate_waakdienst_load(self, employees: list[Any]) -> dict[int, float]:
        """Calculate the current waakdienst workload for each employee."""
        assignments = self.calculate_current_assignments(employees)
        return {
            emp_id: data.get("waakdienst", 0.0) for emp_id, data in assignments.items()
        }

    def get_next_waakdienst_candidate(self, employees: list[Any]) -> Any | None:
        """Get the next best candidate for waakdienst assignment based on fairness."""
        waakdienst_loads = self.calculate_waakdienst_load(employees)

        if not waakdienst_loads:
            return employees[0] if employees else None

        # Sort by waakdienst load (ascending - least loaded first)
        sorted_employees = sorted(
            employees, key=lambda emp: waakdienst_loads.get(emp.pk, 0.0),
        )
        return sorted_employees[0] if sorted_employees else None

    def calculate_weekend_burden(self, employees: list[Any]) -> dict[int, float]:
        """Calculate weekend/holiday burden for waakdienst employees."""
        self.calculate_current_assignments(employees)
        weekend_burden = {}

        # Query weekend shifts specifically
        weekend_shifts = self._get_base_queryset().filter(
            assigned_employee__in=[emp.pk for emp in employees],
            start_datetime__week_day__in=[1, 7],  # Sunday=1, Saturday=7 in Django
        )

        for emp in employees:
            emp_weekend_shifts = [
                s for s in weekend_shifts if s.assigned_employee.pk == emp.pk
            ]
            total_weekend_hours = sum(
                (shift.end_datetime - shift.start_datetime).total_seconds() / 3600
                for shift in emp_weekend_shifts
            )
            weekend_burden[emp.pk] = total_weekend_hours

        return weekend_burden


class FairnessCalculatorFactory:
    """Factory to create the appropriate fairness calculator for a shift type."""

    @staticmethod
    def create_for_shift_type(
        shift_type: str, start_date: datetime, end_date: datetime,
    ) -> BaseFairnessCalculator:
        """Create the appropriate fairness calculator for the given shift type."""
        if shift_type == ShiftType.INCIDENTS:
            return IncidentsFairnessCalculator(start_date, end_date)
        if shift_type == ShiftType.INCIDENTS_STANDBY:
            return IncidentsStandbyFairnessCalculator(start_date, end_date)
        if shift_type == ShiftType.WAAKDIENST:
            return WaakdienstFairnessCalculator(start_date, end_date)
        msg = f"Unknown shift type: {shift_type}"
        raise ValueError(msg)

    @staticmethod
    def create_incidents_calculator(
        start_date: datetime, end_date: datetime,
    ) -> IncidentsFairnessCalculator:
        """Create an IncidentsFairnessCalculator."""
        return IncidentsFairnessCalculator(start_date, end_date)

    @staticmethod
    def create_standby_calculator(
        start_date: datetime, end_date: datetime,
    ) -> IncidentsStandbyFairnessCalculator:
        """Create an IncidentsStandbyFairnessCalculator."""
        return IncidentsStandbyFairnessCalculator(start_date, end_date)

    @staticmethod
    def create_waakdienst_calculator(
        start_date: datetime, end_date: datetime,
    ) -> WaakdienstFairnessCalculator:
        """Create a WaakdienstFairnessCalculator."""
        return WaakdienstFairnessCalculator(start_date, end_date)
