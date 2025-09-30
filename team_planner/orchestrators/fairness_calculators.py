"""
Split Fairness Calculators for Independent Shift Type Tracking

This module implements Phase 1.1 of the orchestrator split roadmap.
Each fairness calculator is specialized for a specific shift type,
eliminating cross-contamination between shift types.

Architecture:
- BaseFairnessCalculator: Common functionality and interface
- IncidentsFairnessCalculator: Monday-Friday business hours tracking
- IncidentsStandbyFairnessCalculator: Independent standby shift tracking
- WaakdienstFairnessCalculator: Wednesday-Wednesday evening/weekend tracking
"""

from collections import defaultdict
from datetime import datetime
from datetime import timedelta
from typing import Any

from django.db import models

from team_planner.employees.models import EmployeeProfile
from team_planner.leaves.models import Holiday
from team_planner.leaves.models import LeaveRequest
from team_planner.shifts.models import Shift
from team_planner.shifts.models import ShiftType
from team_planner.users.models import User


class BaseFairnessCalculator:
    """Base class providing common fairness calculation functionality.

    This base class handles:
    - Desirability weighting (holidays, weekends)
    - Historical decay for assignments before period
    - Manual override adjustments
    - Employee availability calculations
    - Prorated fairness for mid-period hires/terminations
    """

    # Default tuning parameters - can be overridden per calculator
    WEEKEND_WEIGHT = 1.2
    HOLIDAY_WEIGHT = 1.5
    MANUAL_OVERRIDE_MULTIPLIER = (
        0.8  # count less towards fairness when manually overridden
    )
    HISTORY_WINDOW_DAYS = 180  # how far back to include history with decay
    DECAY_HALF_LIFE_DAYS = 90  # exponential half-life for historical shifts

    def __init__(
        self,
        start_date: datetime,
        end_date: datetime,
        *,
        weekend_weight: float | None = None,
        holiday_weight: float | None = None,
        manual_override_multiplier: float | None = None,
        history_window_days: int | None = None,
        decay_half_life_days: int | None = None,
    ):
        self.start_date = start_date
        self.end_date = end_date
        # Allow parameter overrides
        self.WEEKEND_WEIGHT = weekend_weight or self.WEEKEND_WEIGHT
        self.HOLIDAY_WEIGHT = holiday_weight or self.HOLIDAY_WEIGHT
        self.MANUAL_OVERRIDE_MULTIPLIER = (
            manual_override_multiplier or self.MANUAL_OVERRIDE_MULTIPLIER
        )
        self.HISTORY_WINDOW_DAYS = history_window_days or self.HISTORY_WINDOW_DAYS
        self.DECAY_HALF_LIFE_DAYS = decay_half_life_days or self.DECAY_HALF_LIFE_DAYS
        # Holiday cache for weighting
        self._holiday_exact_dates: set | None = None
        self._holiday_recurring_md: set[tuple[int, int]] | None = None

    def _get_tracked_shift_types(self) -> list[str]:
        """Return the shift types this calculator tracks.
        Must be implemented by subclasses.
        """
        msg = "Subclasses must implement _get_tracked_shift_types"
        raise NotImplementedError(msg)

    # --- Holiday helpers for desirability weighting ---
    def _ensure_holiday_cache(self):
        """Cache holiday data for efficient lookup during weighting calculations."""
        if (
            self._holiday_exact_dates is not None
            and self._holiday_recurring_md is not None
        ):
            return
        range_start = (
            self.start_date - timedelta(days=self.HISTORY_WINDOW_DAYS)
        ).date()
        range_end = self.end_date.date()
        qs = Holiday.objects.filter(
            models.Q(date__gte=range_start, date__lte=range_end)
            | models.Q(is_recurring=True),
        )
        exact: set = set()
        recurring_md: set[tuple[int, int]] = set()
        for h in qs:
            exact.add(h.date)
            if getattr(h, "is_recurring", False):
                recurring_md.add((h.date.month, h.date.day))
        self._holiday_exact_dates = exact
        self._holiday_recurring_md = recurring_md

    def _is_holiday(self, d) -> bool:
        """Check if a date is a holiday (exact date or recurring)."""
        self._ensure_holiday_cache()
        assert (
            self._holiday_exact_dates is not None
        )
        assert (
            self._holiday_recurring_md is not None
        )
        return (d in self._holiday_exact_dates) or (
            (d.month, d.day) in self._holiday_recurring_md
        )

    @staticmethod
    def _overlap_hours(
        bounds_start: datetime, bounds_end: datetime, start: datetime, end: datetime,
    ) -> float:
        """Calculate overlapping hours between two datetime ranges."""
        s = max(bounds_start, start)
        e = min(bounds_end, end)
        if e <= s:
            return 0.0
        return (e - s).total_seconds() / 3600.0

    def _weighted_hours(self, start: datetime, end: datetime) -> float:
        """Compute desirability-weighted hours across the interval.
        Holiday hours = 1.5x, Weekend hours = 1.2x.
        When both apply, holiday weight dominates.
        """
        total = 0.0
        cur = start
        # Iterate day-by-day to account for weekends/holidays and overnight spans
        while cur < end:
            day_start = cur.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)
            hours = self._overlap_hours(day_start, day_end, start, end)
            if hours > 0:
                d = day_start.date()
                is_weekend = day_start.weekday() >= 5
                is_holiday = self._is_holiday(d)
                weight = 1.0
                if is_holiday:
                    weight = max(weight, self.HOLIDAY_WEIGHT)
                if is_weekend:
                    weight = max(weight, self.WEEKEND_WEIGHT)
                total += hours * weight
            cur = day_end
        return total

    # --- Historical decay helper ---
    def _decay_weight_for_date(self, dt: datetime) -> float:
        """Calculate exponential decay weight for historical assignments.
        For shifts before start_date, compute age in days relative to start_date.
        """
        if dt >= self.start_date:
            return 1.0
        age_days = (self.start_date - dt).days
        if self.DECAY_HALF_LIFE_DAYS <= 0:
            return 1.0
        return 0.5 ** (age_days / float(self.DECAY_HALF_LIFE_DAYS))

    # --- Manual override adjustment ---
    def _apply_manual_override_multiplier(
        self, hours: float, auto_assigned: bool,
    ) -> float:
        """Apply reduced weight for manually overridden assignments."""
        if auto_assigned is False:
            return hours * self.MANUAL_OVERRIDE_MULTIPLIER
        return hours

    def calculate_employee_available_hours(self, employee: Any) -> dict[str, float]:
        """Calculate how many hours per week this employee is available for work."""
        from team_planner.employees.models import RecurringLeavePattern

        # Standard incidents week = 45 hours (5 days * 9 hours)
        standard_week_hours = 45.0

        # Get active recurring patterns
        patterns = RecurringLeavePattern.objects.filter(
            employee=employee,
            is_active=True,
            effective_from__lte=self.end_date.date(),
        ).filter(
            models.Q(effective_until__isnull=True)
            | models.Q(effective_until__gte=self.start_date.date()),
        )

        # Calculate weekly reduction due to patterns
        weekly_reduction = 0.0
        for pattern in patterns:
            pattern_hours_per_occurrence = pattern.get_hours_affected()

            if pattern.frequency == "weekly":
                weekly_reduction += pattern_hours_per_occurrence
            elif pattern.frequency == "biweekly":
                weekly_reduction += (
                    pattern_hours_per_occurrence / 2
                )  # Average over 2 weeks

        available_hours = max(0, standard_week_hours - weekly_reduction)
        availability_percentage = (
            (available_hours / standard_week_hours * 100)
            if standard_week_hours > 0
            else 0
        )

        return {
            "hours_per_week": available_hours,
            "percentage": availability_percentage,
            "reduction_hours": weekly_reduction,
        }

    def calculate_current_assignments(
        self, employees: list[Any],
    ) -> dict[int, dict[str, float]]:
        """Calculate current shift assignments for this calculator's tracked shift types.

        Returns assignments dict with only the shift types this calculator tracks,
        plus total_hours and availability information.
        """
        assignments: dict[int, dict[str, float]] = {}
        tracked_types = self._get_tracked_shift_types()
        history_start = self.start_date - timedelta(days=self.HISTORY_WINDOW_DAYS)

        for employee in employees:
            # Initialize data structure for this calculator's shift types
            data = {"total_hours": 0.0}
            for shift_type in tracked_types:
                data[shift_type] = 0.0

            # Add tracking for manual overrides
            data["manual_override_hours"] = 0.0
            data["manual_override_count"] = 0

            # Check for in-period shifts
            period_qs = Shift.objects.filter(
                assigned_employee=employee,
                start_datetime__gte=self.start_date,
                end_datetime__lte=self.end_date,
                template__shift_type__in=tracked_types,  # Only track relevant shift types
            ).select_related("template")

            # Count weighted in-period shifts
            for shift in period_qs:
                base_weighted = self._weighted_hours(
                    shift.start_datetime, shift.end_datetime,
                )
                adjusted = self._apply_manual_override_multiplier(
                    base_weighted, shift.auto_assigned,
                )
                if not shift.auto_assigned:
                    data["manual_override_hours"] += base_weighted
                    data["manual_override_count"] += 1

                st = shift.template.shift_type
                data["total_hours"] += adjusted
                if st in data:  # Should always be true due to filter above
                    data[st] += adjusted

            # Add decayed historical contribution (before start_date within window)
            history_qs = Shift.objects.filter(
                assigned_employee=employee,
                end_datetime__lt=self.start_date,
                end_datetime__gte=history_start,
                template__shift_type__in=tracked_types,  # Only track relevant shift types
            ).select_related("template")

            for shift in history_qs:
                # Weight hours and then decay by age
                weighted = self._weighted_hours(
                    shift.start_datetime, shift.end_datetime,
                )
                weighted = self._apply_manual_override_multiplier(
                    weighted, shift.auto_assigned,
                )
                decay = self._decay_weight_for_date(shift.end_datetime)
                adjusted = weighted * decay

                st = shift.template.shift_type
                data["total_hours"] += adjusted
                if st in data:  # Should always be true due to filter above
                    data[st] += adjusted

            # Add availability information for proportional fairness
            availability_info = self.calculate_employee_available_hours(employee)
            data["available_hours_per_week"] = availability_info["hours_per_week"]
            data["availability_percentage"] = availability_info["percentage"]

            assignments[employee.pk] = data

        return assignments

    def calculate_fairness_score(
        self, assignments: dict[int, dict[str, float]],
    ) -> dict[int, float]:
        """Calculate fairness scores based on proportional hour distribution.
        Uses percentage deviation: score = 100 - (|assigned - expected| / max(1, expected)) * 100.
        """
        if not assignments:
            return {}

        # Build employee profiles for prorating based on hire/termination and returns from leave
        try:
            emp_ids = list(assignments.keys())
            employees_qs = User.objects.filter(pk__in=emp_ids).select_related(
                "employee_profile",
            )
            profiles_by_id: dict[int, EmployeeProfile | None] = {
                u.pk: getattr(u, "employee_profile", None) for u in employees_qs
            }
        except Exception:
            profiles_by_id = {}

        # Ensure all assignments have total_hours
        normalized = {}
        for emp_id, data in assignments.items():
            norm = dict(data)
            if "total_hours" not in norm:
                total = 0.0
                tracked_types = self._get_tracked_shift_types()
                for shift_type in tracked_types:
                    if shift_type in norm and isinstance(
                        norm[shift_type], (int, float),
                    ):
                        total += float(norm[shift_type])
                norm["total_hours"] = total
            normalized[emp_id] = norm

        # Compute active fractions per employee (mid-period hires, terminations, returning after long leave)
        period_days = max(1, (self.end_date.date() - self.start_date.date()).days + 1)
        active_fraction_by_emp: dict[int, float] = {}
        for emp_id in normalized:
            profile = profiles_by_id.get(emp_id)
            # Default fully active
            fraction = 1.0
            if isinstance(profile, EmployeeProfile):
                hire_date = getattr(profile, "hire_date", None)
                termination_date = getattr(profile, "termination_date", None)
                active_start = self.start_date.date()
                if hire_date:
                    active_start = max(active_start, hire_date)
                active_end = self.end_date.date()
                if termination_date:
                    active_end = min(active_end, termination_date)

                # Returning-from-extended-leave (>30 days) adjustment
                return_info = self.get_returning_employee_info(profile.user)  # type: ignore[arg-type]
                if return_info and return_info.get("return_date"):
                    rd = return_info["return_date"]
                    active_start = max(active_start, rd)

                if active_end >= active_start:
                    active_days = (active_end - active_start).days + 1
                    fraction = max(0.0, min(1.0, active_days / float(period_days)))
                else:
                    fraction = 0.0
            active_fraction_by_emp[emp_id] = fraction

        # Calculate total available capacity across all employees (scaled by active fractions)
        total_available_capacity = 0.0
        for emp_id, data in normalized.items():
            base_avail = data.get("available_hours_per_week", 45.0)
            total_available_capacity += base_avail * active_fraction_by_emp.get(
                emp_id, 1.0,
            )

        # Calculate total assigned hours
        total_assigned_hours = sum(data["total_hours"] for data in normalized.values())

        fairness_scores = {}
        for employee_id, data in normalized.items():
            employee_available_hours = data.get("available_hours_per_week", 45.0)
            # Assigned hours are already desirability/override/decay-adjusted
            employee_assigned_hours = data["total_hours"]
            # Scale expected by employee active fraction
            active_fraction = active_fraction_by_emp.get(employee_id, 1.0)
            employee_available_hours *= active_fraction

            if total_available_capacity > 0:
                expected_share = employee_available_hours / total_available_capacity
                expected_hours = expected_share * total_assigned_hours

                if expected_hours <= 0:
                    fairness_score = 100.0 if employee_assigned_hours == 0 else 0.0
                else:
                    deviation_ratio = (
                        abs(employee_assigned_hours - expected_hours) / expected_hours
                    )
                    fairness_score = max(0.0, 100.0 - (deviation_ratio * 100.0))
            else:
                fairness_score = 100.0

            fairness_scores[employee_id] = round(fairness_score, 2)

        return fairness_scores

    def calculate_provisional_assignments(
        self, in_memory_assignments: list[dict],
    ) -> dict[int, dict[str, float]]:
        """Build assignments dict from in-memory assignments list (no DB fetch).

        Only includes assignments for this calculator's tracked shift types.
        Applies desirability weights for holidays/weekends and manual override multiplier.
        Historical decay does not apply to provisional plans.
        """
        assignments: dict[int, dict[str, float]] = defaultdict(
            lambda: {"total_hours": 0.0},
        )
        tracked_types = self._get_tracked_shift_types()

        # Initialize tracked shift types
        for emp_id in assignments:
            for shift_type in tracked_types:
                assignments[emp_id][shift_type] = 0.0

        employees: dict[int, Any] = {}

        for a in in_memory_assignments:
            st = a["shift_type"]
            if st not in tracked_types:
                continue  # Skip shift types not tracked by this calculator

            emp_id = a["assigned_employee_id"]
            emp = (
                User.objects.get(pk=emp_id)
                if emp_id not in employees
                else employees[emp_id]
            )
            employees[emp_id] = emp

            # Ensure employee entry exists with all tracked shift types
            if emp_id not in assignments:
                assignments[emp_id] = {"total_hours": 0.0}
                for shift_type in tracked_types:
                    assignments[emp_id][shift_type] = 0.0

            # Determine hours if not provided and apply desirability/override adjustments
            start_dt = a.get("start_datetime")
            end_dt = a.get("end_datetime")
            hours = a.get("duration_hours")
            if hours is None and start_dt and end_dt:
                hours = self._weighted_hours(start_dt, end_dt)
            elif hours is None:
                hours = 0.0

            # Respect manual override multiplier if explicitly marked
            auto_assigned = a.get("auto_assigned", True)
            hours = self._apply_manual_override_multiplier(hours, auto_assigned)

            assignments[emp_id]["total_hours"] += hours
            assignments[emp_id][st] += hours

        # Add availability for proportional fairness
        for emp_id, emp in employees.items():
            info = self.calculate_employee_available_hours(emp)
            assignments[emp_id]["available_hours_per_week"] = info["hours_per_week"]
            assignments[emp_id]["availability_percentage"] = info["percentage"]

        return dict(assignments)

    def get_returning_employee_info(self, user: Any) -> dict[str, Any] | None:
        """Return info if the user is returning from an approved extended leave (>30 days).
        If such a leave ended shortly before or during the period, we will reduce expected
        hours by prorating active days from the return date.
        """
        try:
            # Find the last approved leave that ended within 30 days before period end or during period
            long_leaves = LeaveRequest.objects.filter(
                employee=user,
                status="approved",
                end_date__lte=self.end_date.date(),
                end_date__gte=self.start_date.date() - timedelta(days=30),
            ).order_by("-end_date")
            for lr in long_leaves:
                # Duration in days
                duration_days = (lr.end_date - lr.start_date).days + 1
                if duration_days >= 30:
                    return {
                        "leave_request_id": lr.pk,
                        "return_date": lr.end_date + timedelta(days=1),
                        "duration_days": duration_days,
                    }
        except Exception:
            pass
        return None


class IncidentsFairnessCalculator(BaseFairnessCalculator):
    """Fairness calculator specialized for incidents shifts (Monday-Friday business hours).

    This calculator only tracks ShiftType.INCIDENTS assignments and fairness.
    It operates on the Monday 08:00 - Friday 17:00 rotation cycle.
    """

    def _get_tracked_shift_types(self) -> list[str]:
        """Return only incidents shift type."""
        return [ShiftType.INCIDENTS]


class IncidentsStandbyFairnessCalculator(BaseFairnessCalculator):
    """Fairness calculator specialized for incidents standby shifts.

    This calculator only tracks ShiftType.INCIDENTS_STANDBY assignments and fairness.
    It operates independently from the primary incidents rotation.
    """

    def _get_tracked_shift_types(self) -> list[str]:
        """Return only incidents standby shift type."""
        return [ShiftType.INCIDENTS_STANDBY]


class WaakdienstFairnessCalculator(BaseFairnessCalculator):
    """Fairness calculator specialized for waakdienst shifts (Wednesday-Wednesday cycle).

    This calculator only tracks ShiftType.WAAKDIENST assignments and fairness.
    It operates on the Wednesday 17:00 - Wednesday 08:00 rotation cycle.
    """

    def _get_tracked_shift_types(self) -> list[str]:
        """Return only waakdienst shift type."""
        return [ShiftType.WAAKDIENST]


class ComprehensiveFairnessCalculator(BaseFairnessCalculator):
    """Comprehensive fairness calculator that tracks all shift types.

    This calculator tracks all shift types (incidents, incidents_standby, waakdienst,
    changes, projects) and provides overall fairness metrics for the API dashboard.
    """

    def _get_tracked_shift_types(self) -> list[str]:
        """Return all shift types for comprehensive tracking."""
        return [
            ShiftType.INCIDENTS,
            ShiftType.INCIDENTS_STANDBY,
            ShiftType.WAAKDIENST,
            ShiftType.CHANGES,
            ShiftType.PROJECTS,
        ]
