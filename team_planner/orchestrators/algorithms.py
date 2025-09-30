"""
Orchestrator algorithms for fair shift distribution.

This module implements the core scheduling algorithms according to SHIFT_SCHEDULING_SPEC.md:
1. Incidents: Individual daily shifts, same engineer for the week (Mon-Fri)
2. Incidents-Standby: Individual daily shifts, same engineer for the week (Mon-Fri)
3. Waakdienst: Individual daily shifts, same engineer for the week (Wed 17:00 - Wed 08:00)

Enhanced with automatic conflict detection and reassignment capabilities.
"""

import logging
from collections import defaultdict
from datetime import datetime
from datetime import time
from datetime import timedelta
from typing import Any

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone

from team_planner.employees.models import EmployeeProfile
from team_planner.leaves.models import Holiday  # include Holiday for skip logic
from team_planner.leaves.models import LeaveRequest  # include Holiday for skip logic
from team_planner.orchestrators.anchors import business_weeks
from team_planner.orchestrators.anchors import get_team_tz
from team_planner.orchestrators.anchors import waakdienst_periods
from team_planner.shifts.models import Shift
from team_planner.shifts.models import ShiftTemplate
from team_planner.shifts.models import ShiftType
from team_planner.teams.models import Team

User = get_user_model()
logger = logging.getLogger(__name__)


class FairnessCalculator:
    """Calculate fairness scores for shift assignments using hour-based scoring with
    enhancements:
    - Prorated fairness for mid-period hires (hire_date)
    - Historical decay for assignments before the period
    - Desirability weights (holiday/weekend)
    - Returning-from-extended-leave adjustment (>30 days)
    - Manual override adjustment (reduced weight)
    """

    # Default tuning parameters
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
        # Allow overrides
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

    # --- Holiday helpers for desirability weighting ---
    def _ensure_holiday_cache(self):
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
        # Exponential decay with half-life
        # For shifts before start_date, compute age in days relative to start_date
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
        if auto_assigned is False:
            return hours * self.MANUAL_OVERRIDE_MULTIPLIER
        return hours

    def calculate_current_assignments(
        self, employees: list[Any],
    ) -> dict[int, dict[str, float]]:
        """Calculate current shift assignments using hours with desirability and history decay.
        Include ALL employees in the result, even those with zero assignments, to ensure
        fair distribution and prevent the same employees from being repeatedly selected.
        """
        assignments: dict[int, dict[str, float]] = {}

        history_start = self.start_date - timedelta(days=self.HISTORY_WINDOW_DAYS)

        for employee in employees:
            # Initialize employee data (ensure all employees are included)
            data = {
                "incidents": 0.0,
                "incidents_standby": 0.0,
                "waakdienst": 0.0,
                "total_hours": 0.0,
                # Track manual overrides for observability (not currently used in score directly)
                "manual_override_hours": 0.0,
                "manual_override_count": 0,
            }

            # In-period shifts
            period_qs = Shift.objects.filter(
                assigned_employee=employee,
                start_datetime__gte=self.start_date,
                end_datetime__lte=self.end_date,
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
                if st == ShiftType.INCIDENTS:
                    data["incidents"] += adjusted
                elif st == ShiftType.INCIDENTS_STANDBY:
                    data["incidents_standby"] += adjusted
                elif st == ShiftType.WAAKDIENST:
                    data["waakdienst"] += adjusted

            # Add decayed historical contribution (before start_date within window)
            history_qs = Shift.objects.filter(
                assigned_employee=employee,
                end_datetime__lt=self.start_date,
                end_datetime__gte=history_start,
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
                if st == ShiftType.INCIDENTS:
                    data["incidents"] += adjusted
                elif st == ShiftType.INCIDENTS_STANDBY:
                    data["incidents_standby"] += adjusted
                elif st == ShiftType.WAAKDIENST:
                    data["waakdienst"] += adjusted

            # Availability (per-week) for proportional fairness
            availability_info = self.calculate_employee_available_hours(employee)
            data["available_hours_per_week"] = availability_info["hours_per_week"]
            data["availability_percentage"] = availability_info["percentage"]

            # Include ALL employees, even those with zero assignments
            assignments[employee.pk] = data

        return dict(assignments)

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

    def calculate_fairness_score(
        self, assignments: dict[int, dict[str, float]],
    ) -> dict[int, float]:
        """Calculate fairness scores based on proportional hour distribution.
        Uses percentage deviation: score = 100 - (|assigned - expected| / max(1, expected)) * 100.
        Accepts both hour-based dicts (with 'total_hours') and legacy count-based dicts.
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

        # Normalize: derive 'total_hours' if missing (sum numeric fields except availability keys)
        normalized = {}
        for emp_id, data in assignments.items():
            norm = dict(data)
            if "total_hours" not in norm:
                total = 0.0
                for k, v in norm.items():
                    if k in ("available_hours_per_week", "availability_percentage"):
                        continue
                    if isinstance(v, (int, float)):
                        total += float(v)
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
        Applies desirability weights for holidays/weekends and manual override multiplier when
        provided in the assignment dict (auto_assigned flag). Historical decay does not apply
        to provisional plans.
        """
        assignments: dict[int, dict[str, float]] = defaultdict(
            lambda: {
                "incidents": 0.0,
                "incidents_standby": 0.0,
                "waakdienst": 0.0,
                "total_hours": 0.0,
            },
        )
        employees: dict[int, Any] = {}

        for a in in_memory_assignments:
            emp_id = a["assigned_employee_id"]
            emp = (
                User.objects.get(pk=emp_id)
                if emp_id not in employees
                else employees[emp_id]
            )
            employees[emp_id] = emp
            st = a["shift_type"]
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

            assignments[emp.pk]["total_hours"] += hours
            if st == ShiftType.INCIDENTS:
                assignments[emp.pk]["incidents"] += hours
            elif st == ShiftType.INCIDENTS_STANDBY:
                assignments[emp.pk]["incidents_standby"] += hours
            elif st == ShiftType.WAAKDIENST:
                assignments[emp.pk]["waakdienst"] += hours

        # Add availability for proportional fairness
        for emp_id, emp in employees.items():
            info = self.calculate_employee_available_hours(emp)
            assignments[emp_id]["available_hours_per_week"] = info["hours_per_week"]
            assignments[emp_id]["availability_percentage"] = info["percentage"]

        return dict(assignments)

    # --- Returning employee (>30 days leave) support ---
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


class ConstraintChecker:
    """Check constraints for shift assignments."""

    def __init__(
        self,
        start_date: datetime,
        end_date: datetime,
        team_id: int | None = None,
        orchestrator=None,
    ):
        self.start_date = start_date
        self.end_date = end_date
        self.team_id = team_id
        self.orchestrator = orchestrator
        # Configurable knobs
        self.max_consecutive_weeks: int = int(
            getattr(settings, "ORCHESTRATOR_MAX_CONSECUTIVE_WEEKS", 2),
        )
        self.min_rest_hours: int = int(
            getattr(settings, "ORCHESTRATOR_MIN_REST_HOURS", 48),
        )

    def get_available_employees(self, shift_type: str) -> list[Any]:
        """Get employees available for a specific shift type based on skills."""
        query = (
            User.objects.filter(is_active=True, employee_profile__status="active")
            .select_related("employee_profile")
            .prefetch_related("employee_profile__skills")
        )

        # Filter by team if specified
        if self.team_id:
            query = query.filter(teams=self.team_id)

        employees = list(query)

        available = []
        for employee in employees:
            try:
                profile = employee.employee_profile  # type: ignore[attr-defined]

                # Get required skill name based on shift type
                required_skill = None
                if shift_type in [ShiftType.INCIDENTS, ShiftType.INCIDENTS_STANDBY]:
                    required_skill = "incidents"
                elif shift_type == ShiftType.WAAKDIENST:
                    required_skill = "waakdienst"

                # Check if employee has the required skill
                if required_skill:
                    has_skill = profile.skills.filter(
                        name=required_skill, is_active=True,
                    ).exists()

                    if has_skill:
                        available.append(employee)

            except EmployeeProfile.DoesNotExist:
                continue

        return available

    def check_leave_conflicts(
        self, employee: Any, start_date: datetime, end_date: datetime,
    ) -> bool:
        """Check if employee has approved leave during the period."""
        leave_requests = LeaveRequest.objects.filter(
            employee=employee,
            status="approved",
            start_date__lte=end_date.date(),
            end_date__gte=start_date.date(),
        )
        return leave_requests.exists()

    def check_recurring_pattern_conflicts(
        self, employee: Any, start_date: datetime, end_date: datetime, shift_type: str,
    ) -> bool:
        """Check if employee has recurring leave patterns that conflict with this assignment."""
        # Only check incidents shifts (recurring leave doesn't affect waakdienst)
        if shift_type == ShiftType.WAAKDIENST:
            return False

        # RECURRING LEAVE REASSIGNMENT FIX:
        # Always allow assignments - conflicts will be resolved by reassignment manager
        # This ensures employees with recurring leave patterns are not excluded entirely
        logger.debug(
            f"Allowing assignment for {employee.username} - conflicts will be handled by reassignment",
        )
        return False

    def get_partial_availability_for_week(
        self, employee: Any, week_start: datetime, week_end: datetime, shift_type: str,
    ) -> dict[str, Any]:
        """Get detailed availability information for an employee during a week, considering recurring patterns."""
        if shift_type == ShiftType.WAAKDIENST:
            # Waakdienst is not affected by recurring patterns
            if not self.check_leave_conflicts(
                employee, week_start, week_end,
            ) and not self.check_existing_assignments(
                employee, week_start, week_end, shift_type,
            ):
                return {"available": True, "partial": False, "conflicts": []}
            return {"available": False, "partial": False, "conflicts": []}

        from team_planner.employees.models import RecurringLeavePattern

        # Get active patterns for this employee
        patterns = RecurringLeavePattern.objects.filter(
            employee=employee,
            is_active=True,
            effective_from__lte=week_end.date(),
        ).filter(
            models.Q(effective_until__isnull=True)
            | models.Q(effective_until__gte=week_start.date()),
        )

        conflicts = []
        total_available_hours = 0
        total_possible_hours = 0

        # Check each weekday (Monday-Friday for incidents)
        current_date = week_start.date()
        while current_date <= week_end.date() and current_date.weekday() < 5:
            day_conflicts = []
            day_available_hours = 9  # Full day 08:00-17:00

            # Check for regular leave conflicts
            if self.check_leave_conflicts(
                employee,
                datetime.combine(current_date, datetime.min.time()),
                datetime.combine(current_date, datetime.max.time()),
            ):
                day_available_hours = 0
                day_conflicts.append({"type": "leave", "hours": 9})
            else:
                # Check recurring patterns for this day
                for pattern in patterns:
                    if pattern.applies_to_date(current_date):
                        affected_hours = pattern.get_affected_hours_for_date(
                            current_date,
                        )
                        if affected_hours:
                            day_available_hours -= affected_hours["hours"]
                            day_conflicts.append(
                                {
                                    "type": "recurring_pattern",
                                    "pattern": pattern,
                                    "hours": affected_hours["hours"],
                                    "start_datetime": affected_hours["start_datetime"],
                                    "end_datetime": affected_hours["end_datetime"],
                                },
                            )

            total_available_hours += max(0, day_available_hours)
            total_possible_hours += 9

            if day_conflicts:
                conflicts.append(
                    {
                        "date": current_date,
                        "conflicts": day_conflicts,
                        "available_hours": max(0, day_available_hours),
                    },
                )

            current_date += timedelta(days=1)

        # Check existing assignments
        if self.check_existing_assignments(employee, week_start, week_end, shift_type):
            return {"available": False, "partial": False, "conflicts": conflicts}

        is_available = total_available_hours > 0
        is_partial = 0 < total_available_hours < total_possible_hours

        return {
            "available": is_available,
            "partial": is_partial,
            "conflicts": conflicts,
            "available_hours": total_available_hours,
            "total_hours": total_possible_hours,
            "availability_percentage": (
                total_available_hours / total_possible_hours * 100
            )
            if total_possible_hours > 0
            else 0,
        }

    def check_existing_assignments(
        self,
        employee: Any,
        start_date: datetime,
        end_date: datetime,
        shift_type: str | None = None,
    ) -> bool:
        """Check if employee already has shifts during the period. Type-aware to avoid cross-type blocking."""
        qs = Shift.objects.filter(
            assigned_employee=employee,
            start_datetime__lt=end_date,
            end_datetime__gt=start_date,
            status__in=[Shift.Status.SCHEDULED, Shift.Status.IN_PROGRESS],
        ).select_related("template")

        if shift_type in [ShiftType.INCIDENTS, ShiftType.INCIDENTS_STANDBY]:
            qs = qs.filter(
                template__shift_type__in=[
                    ShiftType.INCIDENTS,
                    ShiftType.INCIDENTS_STANDBY,
                ],
            )
        elif shift_type == ShiftType.WAAKDIENST:
            qs = qs.filter(template__shift_type=ShiftType.WAAKDIENST)
        # else leave as-is

        return qs.exists()

    def check_incidents_conflicts_for_week(
        self,
        employee: Any,
        week_start: datetime,
        week_end: datetime,
        checking_shift_type: str,
        existing_assignments: list[dict],
    ) -> bool:
        """Check if employee already has incidents or incidents-standby assigned for this week."""
        if checking_shift_type not in [
            ShiftType.INCIDENTS,
            ShiftType.INCIDENTS_STANDBY,
        ]:
            return False

        # Check existing assignments from this orchestration run
        for assignment in existing_assignments:
            if (
                assignment["assigned_employee_id"] == employee.pk
                and assignment["week_start_date"] == week_start.date()
                and assignment["shift_type"]
                in [ShiftType.INCIDENTS, ShiftType.INCIDENTS_STANDBY]
                and assignment["shift_type"] != checking_shift_type
            ):
                logger.info(
                    f"Preventing double incidents assignment: {employee.username} already has {assignment['shift_type']} for week {week_start.date()}",
                )
                return True

        # Check existing shifts in database for the same week
        week_shifts = Shift.objects.filter(
            assigned_employee=employee,
            start_datetime__gte=week_start,
            start_datetime__lt=week_end + timedelta(days=1),
            status__in=[Shift.Status.SCHEDULED, Shift.Status.IN_PROGRESS],
        ).select_related("template")

        for shift in week_shifts:
            if (
                shift.template.shift_type
                in [ShiftType.INCIDENTS, ShiftType.INCIDENTS_STANDBY]
                and shift.template.shift_type != checking_shift_type
            ):
                logger.info(
                    f"Preventing double incidents assignment: {employee.username} already has existing {shift.template.shift_type} for week {week_start.date()}",
                )
                return True

        return False

    # ---- Advanced constraint helpers ----
    def _iter_current_run_assignments(self) -> list[dict[str, Any]]:
        try:
            return list(getattr(self.orchestrator, "current_run_assignments", []) or [])
        except Exception:
            return []

    def _has_shift_in_range(
        self, employee: Any, start_dt: datetime, end_dt: datetime, types: list[str],
    ) -> bool:
        """Check DB and current run for any shifts of given types overlapping [start_dt, end_dt)."""
        qs = Shift.objects.filter(
            assigned_employee=employee,
            start_datetime__lt=end_dt,
            end_datetime__gt=start_dt,
            status__in=[Shift.Status.SCHEDULED, Shift.Status.IN_PROGRESS],
        ).filter(template__shift_type__in=types)
        if qs.exists():
            return True
        for a in self._iter_current_run_assignments():
            try:
                if a["assigned_employee_id"] != employee.pk:
                    continue
                if a["shift_type"] not in types:
                    continue
                if a["start_datetime"] < end_dt and a["end_datetime"] > start_dt:
                    return True
            except Exception:
                continue
        return False

    def check_waakdienst_back_to_back(
        self, employee: Any, week_start: datetime, week_end: datetime,
    ) -> bool:
        """Prevent back-to-back waakdienst weeks by checking the previous waakdienst period."""
        prev_week_start = week_start - timedelta(days=7)
        prev_week_end = week_end - timedelta(days=7)
        return self._has_shift_in_range(
            employee, prev_week_start, prev_week_end, [ShiftType.WAAKDIENST],
        )

    def count_consecutive_weeks(
        self, employee: Any, shift_type: str, week_start: datetime, week_end: datetime,
    ) -> int:
        """Count how many consecutive previous weeks (up to a small cap) this employee had this shift type."""
        count = 0
        # Check up to 10 prior weeks defensively
        for i in range(1, 11):
            prev_start = week_start - timedelta(days=7 * i)
            prev_end = week_end - timedelta(days=7 * i)
            if self._has_shift_in_range(employee, prev_start, prev_end, [shift_type]):
                count += 1
            else:
                break
        return count

    def violates_min_rest(
        self, employee: Any, start_date: datetime, end_date: datetime, shift_type: str,
    ) -> bool:
        """Enforce minimum rest between incidents and waakdienst shifts in both directions.
        If assigning one type, make sure no other-type shift is within min_rest_hours before start
        or within min_rest_hours after end.
        """
        rest = timedelta(hours=self.min_rest_hours)
        if shift_type in [ShiftType.INCIDENTS, ShiftType.INCIDENTS_STANDBY]:
            other_types = [ShiftType.WAAKDIENST]
        elif shift_type == ShiftType.WAAKDIENST:
            other_types = [ShiftType.INCIDENTS, ShiftType.INCIDENTS_STANDBY]
        else:
            return False

        # Window to search other-type shifts
        win_start = start_date - rest
        win_end = end_date + rest

        # DB search
        other_qs = Shift.objects.filter(
            assigned_employee=employee,
            template__shift_type__in=other_types,
            start_datetime__lt=win_end,
            end_datetime__gt=win_start,
            status__in=[Shift.Status.SCHEDULED, Shift.Status.IN_PROGRESS],
        )
        for s in other_qs:
            # If previous other-type shift ends too close to this start
            if timedelta(0) <= (start_date - s.end_datetime) < rest:
                return True
            # If next other-type shift starts too soon after this end
            if timedelta(0) <= (s.start_datetime - end_date) < rest:
                return True

        # Current run assignments
        for a in self._iter_current_run_assignments():
            try:
                if a["assigned_employee_id"] != employee.pk:
                    continue
                if a["shift_type"] not in other_types:
                    continue
                if a["start_datetime"] >= win_end or a["end_datetime"] <= win_start:
                    continue
                if timedelta(0) <= (start_date - a["end_datetime"]) < rest:
                    return True
                if timedelta(0) <= (a["start_datetime"] - end_date) < rest:
                    return True
            except Exception:
                continue
        return False

    def is_employee_available(
        self, employee: Any, start_date: datetime, end_date: datetime, shift_type: str,
    ) -> bool:
        """Check if employee is available for assignment."""
        # Check skill-based availability
        try:
            profile = employee.employee_profile  # type: ignore[attr-defined]

            # Get required skill name based on shift type
            required_skill = None
            if shift_type in [ShiftType.INCIDENTS, ShiftType.INCIDENTS_STANDBY]:
                required_skill = "incidents"
            elif shift_type == ShiftType.WAAKDIENST:
                required_skill = "waakdienst"

            # Check if employee has the required skill
            if required_skill:
                has_skill = profile.skills.filter(
                    name=required_skill, is_active=True,
                ).exists()

                if not has_skill:
                    return False

        except EmployeeProfile.DoesNotExist:
            return False

        # Check leave conflicts
        if self.check_leave_conflicts(employee, start_date, end_date):
            return False

        # Check recurring pattern conflicts
        if self.check_recurring_pattern_conflicts(
            employee, start_date, end_date, shift_type,
        ):
            return False

        # Check existing assignments
        if self.check_existing_assignments(employee, start_date, end_date, shift_type):
            return False

        # Enforce min rest between incidents and waakdienst in both directions
        if self.violates_min_rest(employee, start_date, end_date, shift_type):
            logger.info(
                f"Rest constraint violation: {employee.username} cannot take {shift_type} due to {self.min_rest_hours}h rest rule",
            )
            return False

        # Waakdienst-specific: prevent back-to-back weeks and enforce max consecutive weeks
        if shift_type == ShiftType.WAAKDIENST:
            # Determine waakdienst week bounds if not already aligned
            week_start, week_end = start_date, end_date
            if self.check_waakdienst_back_to_back(employee, week_start, week_end):
                logger.info(
                    f"Back-to-back waakdienst prevented for {employee.username} (week starting {week_start})",
                )
                return False
            consec = self.count_consecutive_weeks(
                employee, ShiftType.WAAKDIENST, week_start, week_end,
            )
            if consec >= max(1, self.max_consecutive_weeks - 1):
                logger.info(
                    f"Max consecutive waakdienst weeks reached for {employee.username}: {consec} prior weeks",
                )
                return False

        # Check for incidents/incidents-standby conflicts for the same week
        if (
            hasattr(self, "orchestrator")
            and self.orchestrator
            and shift_type in [ShiftType.INCIDENTS, ShiftType.INCIDENTS_STANDBY]
        ):
            if self.orchestrator.check_incidents_conflicts_for_employee(
                employee, start_date, end_date, shift_type,
            ):
                return False

        return True


class ShiftOrchestrator:
    """Main orchestrator for generating shift schedules according to specification."""

    def __init__(
        self,
        start_date: datetime,
        end_date: datetime,
        team_id: int | None = None,
        schedule_incidents: bool = True,
        schedule_incidents_standby: bool = False,
        schedule_waakdienst: bool = True,
        orchestration_run=None,
    ):
        self.start_date = start_date
        self.end_date = end_date
        self.team_id = team_id
        self.schedule_incidents = schedule_incidents
        self.schedule_incidents_standby = schedule_incidents_standby
        self.schedule_waakdienst = schedule_waakdienst
        self.orchestration_run = orchestration_run
        self.fairness_calculator = FairnessCalculator(start_date, end_date)
        self.constraint_checker = ConstraintChecker(
            start_date, end_date, team_id=team_id, orchestrator=self,
        )
        # Track assignments made during this orchestration run to prevent conflicts
        self.current_run_assignments = []

        # Initialize reassignment manager if orchestration_run is provided
        self.reassignment_manager = None
        if orchestration_run:
            from .reassignment import ShiftReassignmentManager

            self.reassignment_manager = ShiftReassignmentManager(
                orchestration_run, self.fairness_calculator,
            )

        # Lazy-loaded team and holidays cache
        self._team: Team | None = None
        self._holiday_exact_dates: set | None = None
        self._holiday_recurring_md: set[tuple[int, int]] | None = None

    def get_team(self) -> Team | None:
        if self._team is not None:
            return self._team
        if not self.team_id:
            return None
        try:
            self._team = Team.objects.get(pk=self.team_id)
        except Team.DoesNotExist:
            self._team = None
        return self._team

    def get_timezone(self):
        team = self.get_team()
        return get_team_tz(team) if team else timezone.get_current_timezone()

    def _ensure_holiday_cache(self):
        """Load holidays for the overall orchestration period once.
        Caches exact date holidays and recurring (month, day) tuples.
        """
        if (
            self._holiday_exact_dates is not None
            and self._holiday_recurring_md is not None
        ):
            return
        # Load all holidays within range and all recurring definitions
        range_start = self.start_date.date()
        range_end = self.end_date.date()
        qs = Holiday.objects.filter(
            models.Q(date__gte=range_start, date__lte=range_end)
            | models.Q(is_recurring=True),
        )
        exact = set()
        recurring_md: set[tuple[int, int]] = set()
        for h in qs:
            if h.is_recurring:
                recurring_md.add((h.date.month, h.date.day))
            # Always collect exact date; harmless even if outside range due to filter
            exact.add(h.date)
        self._holiday_exact_dates = exact
        self._holiday_recurring_md = recurring_md

    def _is_holiday(self, d) -> bool:
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

    def generate_incidents_weeks(self) -> list[tuple[datetime, datetime, str]]:
        """Generate business-week periods for incidents shifts using DST-safe anchors."""
        tz = self.get_timezone()
        periods = business_weeks(self.start_date, self.end_date, tz=tz)
        return [(p.start, p.end, "business_week") for p in periods]

    def generate_waakdienst_weeks(self) -> list[tuple[datetime, datetime, str]]:
        """Generate waakdienst periods aligned to team-configured anchors (no partial periods)."""
        team = self.get_team()
        if not team:
            # Fallback to legacy behavior if no team is provided
            weeks = []
            current = self.start_date
            # Find the first Wednesday 17:00 that starts a complete waakdienst period
            days_since_wednesday = (current.weekday() - 2) % 7
            wednesday = current - timedelta(days=days_since_wednesday)
            # If we're past Wednesday 17:00, move to next Wednesday
            wednesday_1700 = timezone.make_aware(
                datetime.combine(wednesday.date(), time(17, 0)),
            )
            if current > wednesday_1700:
                wednesday = wednesday + timedelta(days=7)

            while wednesday < self.end_date:
                next_wednesday = wednesday + timedelta(days=7)
                week_start = timezone.make_aware(
                    datetime.combine(wednesday.date(), time(17, 0)),
                )
                week_end = timezone.make_aware(
                    datetime.combine(next_wednesday.date(), time(8, 0)),
                )
                # Only include complete periods that end before our end_date
                if week_end <= self.end_date:
                    weeks.append((week_start, week_end, "waakdienst_week"))
                wednesday = next_wednesday
            return weeks
        periods = waakdienst_periods(self.start_date, self.end_date, team=team)
        return [(p.start, p.end, "waakdienst_week") for p in periods]

    def generate_daily_shifts_for_week(
        self, week_start: datetime, week_end: datetime, shift_type: str, week_type: str,
    ) -> list[tuple[datetime, datetime, str]]:
        """Generate individual daily shifts for a week, honoring holiday skip policy for incidents."""
        daily_shifts = []
        team = self.get_team()

        if week_type == "business_week":
            # Incidents/Incidents-Standby: Monday-Friday 08:00-17:00
            current_day = week_start
            for day_num in range(5):  # Monday to Friday
                day_start = current_day.replace(
                    hour=8, minute=0, second=0, microsecond=0,
                )
                day_end = current_day.replace(
                    hour=17, minute=0, second=0, microsecond=0,
                )
                # Optionally skip holidays for incidents/standby
                if (
                    team
                    and getattr(team, "incidents_skip_holidays", False)
                    and shift_type in [ShiftType.INCIDENTS, ShiftType.INCIDENTS_STANDBY]
                ):
                    if self._is_holiday(day_start.date()):
                        current_day += timedelta(days=1)
                        continue
                daily_shifts.append(
                    (day_start, day_end, f"{shift_type}_day_{day_num + 1}"),
                )
                current_day += timedelta(days=1)

        elif week_type == "waakdienst_week":
            # Waakdienst: 7 individual daily shifts as per specification
            # Week runs from Wednesday 17:00 to next Wednesday 08:00

            # Wednesday Evening: 17:00 - Thursday 08:00 (15 hours overnight)
            wed_start = week_start  # This is already Wednesday 17:00
            thu_morning = wed_start + timedelta(hours=15)  # Thursday 08:00
            daily_shifts.append((wed_start, thu_morning, f"{shift_type}_wed_evening"))

            # Thursday Evening: 17:00 - Friday 08:00 (15 hours overnight)
            thu_evening = wed_start.replace(hour=17) + timedelta(
                days=1,
            )  # Thursday 17:00
            fri_morning = thu_evening + timedelta(hours=15)  # Friday 08:00
            daily_shifts.append((thu_evening, fri_morning, f"{shift_type}_thu_evening"))

            # Friday Evening: 17:00 - Saturday 08:00 (15 hours overnight)
            fri_evening = wed_start.replace(hour=17) + timedelta(days=2)  # Friday 17:00
            sat_morning = fri_evening + timedelta(hours=15)  # Saturday 08:00
            daily_shifts.append((fri_evening, sat_morning, f"{shift_type}_fri_evening"))

            # Saturday: 08:00 - Sunday 08:00 (24 hours full day)
            sat_start = sat_morning  # Saturday 08:00
            sun_start = sat_start + timedelta(hours=24)  # Sunday 08:00
            daily_shifts.append((sat_start, sun_start, f"{shift_type}_sat_full"))

            # Sunday: 08:00 - Monday 08:00 (24 hours full day)
            mon_start = sun_start + timedelta(hours=24)  # Monday 08:00
            daily_shifts.append((sun_start, mon_start, f"{shift_type}_sun_full"))

            # Monday Evening: 17:00 - Tuesday 08:00 (15 hours overnight)
            mon_evening = wed_start.replace(hour=17) + timedelta(days=5)  # Monday 17:00
            tue_morning = mon_evening + timedelta(hours=15)  # Tuesday 08:00
            daily_shifts.append((mon_evening, tue_morning, f"{shift_type}_mon_evening"))

            # Tuesday Evening: 17:00 - Wednesday 08:00 (15 hours overnight) - FINAL shift
            tue_evening = wed_start.replace(hour=17) + timedelta(
                days=6,
            )  # Tuesday 17:00
            wed_end = week_end  # This is next Wednesday 08:00
            daily_shifts.append((tue_evening, wed_end, f"{shift_type}_tue_evening"))

        return daily_shifts

    def get_shift_template(self, shift_type: str) -> ShiftTemplate | None:
        """Get or create shift template for the given type."""
        # Individual daily shift durations (hours)
        if shift_type in (ShiftType.INCIDENTS, ShiftType.INCIDENTS_STANDBY):
            duration_hours = 9  # Single day 08:00-17:00
        elif shift_type == ShiftType.WAAKDIENST:
            duration_hours = 15  # Average daily shift (varies from 15-24 hours)
        else:
            duration_hours = 8  # Default

        # Try to get an existing template first, or create if none exist
        try:
            template = ShiftTemplate.objects.filter(
                shift_type=shift_type, is_active=True,
            ).first()

            if not template:
                # No active template found, create one
                template = ShiftTemplate.objects.create(
                    shift_type=shift_type,
                    name=f"{shift_type.replace('_', '-').title()} Daily Shift",
                    description=f"Individual daily shift for {shift_type.replace('_', '-')}",
                    duration_hours=duration_hours,
                    is_active=True,
                )
                logger.info(f"Created new shift template for {shift_type}")

        except Exception as e:
            logger.exception(f"Error getting shift template for {shift_type}: {e}")
            # Fallback to first available template
            template = ShiftTemplate.objects.filter(shift_type=shift_type).first()
            if not template:
                msg = f"No shift template found for {shift_type}"
                raise ValueError(msg)

        return template

    def assign_shifts_fairly(
        self, shift_type: str, weeks: list[tuple[datetime, datetime, str]],
    ) -> list[dict]:
        """Assign shifts using fair distribution algorithm with recurring pattern awareness."""
        available_employees = self.constraint_checker.get_available_employees(
            shift_type,
        )
        if not available_employees:
            logger.warning(f"No employees available for {shift_type} shifts")
            return []

        # Get current assignments for fairness calculation
        current_assignments = self.fairness_calculator.calculate_current_assignments(
            available_employees,
        )

        # Sort employees by current assignment count (fairness)
        def sort_key(emp):
            emp_assignments = current_assignments.get(
                emp.pk, {"incidents": 0.0, "incidents_standby": 0.0, "waakdienst": 0.0},
            )
            return emp_assignments.get(shift_type.lower(), 0.0)

        # Track assignments made in this run — per shift type to keep pools independent
        new_assignments = defaultdict(
            lambda: {"incidents": 0.0, "incidents_standby": 0.0, "waakdienst": 0.0},
        )
        assignments = []

        for week_start, week_end, week_type in weeks:
            # Generate daily shifts for this week
            daily_shifts = self.generate_daily_shifts_for_week(
                week_start, week_end, shift_type, week_type,
            )

            if not daily_shifts:
                continue

            # Check for employees with partial availability due to recurring patterns
            if shift_type in [ShiftType.INCIDENTS, ShiftType.INCIDENTS_STANDBY]:
                # Handle incidents shifts with potential recurring pattern conflicts
                week_assignments = (
                    self.assign_incidents_week_with_patterns_and_conflicts(
                        week_start,
                        week_end,
                        week_type,
                        shift_type,
                        available_employees,
                        current_assignments,
                        new_assignments,
                        daily_shifts,
                        assignments,
                    )
                )
                assignments.extend(week_assignments)
            else:
                # Handle waakdienst normally (not affected by recurring patterns)
                week_assignments = self.assign_full_week_normal(
                    week_start,
                    week_end,
                    week_type,
                    shift_type,
                    available_employees,
                    current_assignments,
                    new_assignments,
                    daily_shifts,
                )
                assignments.extend(week_assignments)

        return assignments

    def assign_incidents_week_with_patterns_and_conflicts(
        self,
        week_start: datetime,
        week_end: datetime,
        week_type: str,
        shift_type: str,
        available_employees: list[Any],
        current_assignments: dict,
        new_assignments: dict,
        daily_shifts: list[tuple],
        existing_assignments: list[dict],
    ) -> list[dict]:
        """Assign incidents week considering recurring leave patterns, smart reassignment, and conflicts checking."""

        # Check each employee's availability for this specific week
        employee_availability = {}
        for emp in available_employees:
            availability_info = (
                self.constraint_checker.get_partial_availability_for_week(
                    emp, week_start, week_end, shift_type,
                )
            )
            employee_availability[emp.pk] = {"employee": emp, "info": availability_info}

        # Separate fully available vs partially available employees
        fully_available = []
        partially_available = []

        for data in employee_availability.values():
            emp = data["employee"]
            # Avoid assigning the same engineer to both incidents and incidents-standby in the same week
            try:
                if self.check_incidents_conflicts_for_employee(
                    emp, week_start, week_end, shift_type,
                ):
                    logger.info(
                        f"Skipping {emp.username} for {shift_type} week {week_start.date()} due to existing complementary assignment in the same week",
                    )
                    continue
            except Exception as e:
                logger.warning(f"Weekly conflict check failed for {emp}: {e}")

            if data["info"]["available"]:
                if data["info"]["partial"]:
                    partially_available.append(data)
                else:
                    fully_available.append(data)

        # Strategy 1: Try to assign to someone fully available first
        if fully_available and partially_available:
            # Compare best fully-available vs best partially-available by fairness load
            def load_for(emp):
                emp_assignments = current_assignments.get(
                    emp.pk,
                    {"incidents": 0.0, "incidents_standby": 0.0, "waakdienst": 0.0},
                )
                current_hours = emp_assignments.get(shift_type.lower(), 0.0)
                new_hours = new_assignments[emp.pk].get(shift_type.lower(), 0.0)
                return current_hours + new_hours

            def sort_key_with_new(emp_data):
                emp = emp_data["employee"]
                return load_for(emp)

            fully_available.sort(key=sort_key_with_new)
            best_full = fully_available[0]

            # Sort partial by availability percentage (desc) then fairness load (asc)
            def sort_key_partial(emp_data):
                emp = emp_data["employee"]
                availability_pct = emp_data["info"].get("availability_percentage", 0)
                return (-availability_pct, load_for(emp))

            partially_available.sort(key=sort_key_partial)
            best_partial = partially_available[0]

            # Threshold: prefer partial if availability >= 60% and fairness load is not worse than full by more than 2 hours
            partial_availability = best_partial["info"].get(
                "availability_percentage", 0,
            )
            full_load = load_for(best_full["employee"])
            partial_load = load_for(best_partial["employee"])

            if partial_availability >= 60 and partial_load <= full_load + 2:
                # Assign partial week with coverage
                return self.assign_partial_week_with_coverage(
                    week_start,
                    week_end,
                    shift_type,
                    [best_partial],
                    available_employees,
                    current_assignments,
                    new_assignments,
                    daily_shifts,
                )
            # Assign full week to best full candidate
            assigned_employee = best_full["employee"]
            return self.create_full_week_assignments(
                assigned_employee, daily_shifts, shift_type, new_assignments,
            )

        if fully_available and not partially_available:
            # Sort by fairness + new assignments
            def sort_key_with_new(emp_data):
                emp = emp_data["employee"]
                emp_assignments = current_assignments.get(
                    emp.pk,
                    {"incidents": 0.0, "incidents_standby": 0.0, "waakdienst": 0.0},
                )
                current_hours = emp_assignments.get(shift_type.lower(), 0.0)
                new_hours = new_assignments[emp.pk].get(shift_type.lower(), 0.0)
                return current_hours + new_hours

            fully_available.sort(key=sort_key_with_new)
            assigned_employee = fully_available[0]["employee"]
            return self.create_full_week_assignments(
                assigned_employee, daily_shifts, shift_type, new_assignments,
            )

        # Strategy 2: Handle partial availability with smart reassignment
        if partially_available:
            return self.assign_partial_week_with_coverage(
                week_start,
                week_end,
                shift_type,
                partially_available,
                available_employees,
                current_assignments,
                new_assignments,
                daily_shifts,
            )

        # Strategy 3: No one available for this week
        logger.warning(f"No employees available for {shift_type} week {week_start}")
        return []

    def assign_partial_week_with_coverage(
        self,
        week_start: datetime,
        week_end: datetime,
        shift_type: str,
        partially_available: list[dict],
        all_employees: list[Any],
        current_assignments: dict,
        new_assignments: dict,
        daily_shifts: list[tuple],
    ) -> list[dict]:
        """Assign week-long assignment with day-level reassignment for conflicts only.

        Strategy: Prefer same engineer for entire week, but reassign only individual
        conflicted days to maintain week-long assignment principle.
        """

        # Find the employee with the highest availability percentage who also has the least assignments
        def sort_key_partial(emp_data):
            emp = emp_data["employee"]
            availability_pct = emp_data["info"]["availability_percentage"]
            emp_assignments = current_assignments.get(
                emp.pk, {"incidents": 0.0, "incidents_standby": 0.0, "waakdienst": 0.0},
            )
            current_hours = emp_assignments.get(shift_type.lower(), 0.0)
            new_hours = new_assignments[emp.pk].get(shift_type.lower(), 0.0)

            # Prioritize high availability first, then low assignment count
            return (-availability_pct, current_hours + new_hours)

        partially_available.sort(key=sort_key_partial)
        primary_employee_data = partially_available[0]
        primary_employee = primary_employee_data["employee"]
        conflicts = primary_employee_data["info"]["conflicts"]

        assignments = []
        conflicted_days = []

        # Step 1: Assign primary employee to all non-conflicted days
        for day_start, day_end, day_label in daily_shifts:
            day_date = day_start.date()

            # Check if primary employee has conflicts on this day
            day_conflicts = [c for c in conflicts if c["date"] == day_date]

            if not day_conflicts:
                # Primary employee available for full day - assign immediately
                assignments.extend(
                    self.create_day_assignment(
                        primary_employee,
                        day_start,
                        day_end,
                        day_label,
                        shift_type,
                        new_assignments,
                    ),
                )
                logger.info(
                    f"✅ Assigned {primary_employee.username} to {day_label} (no conflicts)",
                )
            else:
                # Day has conflicts - track for reassignment
                conflicted_days.append(
                    (day_start, day_end, day_label, day_conflicts[0]),
                )
                logger.info(
                    f"⚠️ Day conflict for {primary_employee.username} on {day_label}, will reassign",
                )

        # Step 2: Reassign only the conflicted days to other employees
        for day_start, day_end, day_label, day_conflict in conflicted_days:
            available_hours = day_conflict["available_hours"]

            if available_hours > 0:
                # Partial day conflict - split the day
                logger.info(
                    f"🔄 Splitting {day_label}: {primary_employee.username} works {available_hours}h, finding coverage for rest",
                )
                split_assignments = self.assign_split_day_with_coverage(
                    day_start,
                    day_end,
                    day_label,
                    shift_type,
                    primary_employee,
                    day_conflict,
                    all_employees,
                    current_assignments,
                    new_assignments,
                )
                assignments.extend(split_assignments)
            else:
                # Full day conflict - reassign entire day to someone else
                logger.info(
                    f"🔄 Reassigning {day_label}: finding replacement for {primary_employee.username}",
                )
                coverage_assignments = self.find_day_coverage(
                    day_start,
                    day_end,
                    day_label,
                    shift_type,
                    all_employees,
                    current_assignments,
                    new_assignments,
                    exclude_employee=primary_employee,
                )
                assignments.extend(coverage_assignments)

        # Log the final assignment pattern
        assigned_days = len(daily_shifts) - len(conflicted_days)
        logger.info(
            f"📋 Week assignment result: {primary_employee.username} gets {assigned_days}/{len(daily_shifts)} days, {len(conflicted_days)} days reassigned",
        )

        return assignments

    def assign_split_day_with_coverage(
        self,
        day_start: datetime,
        day_end: datetime,
        day_label: str,
        shift_type: str,
        primary_employee: Any,
        day_conflict: dict,
        all_employees: list[Any],
        current_assignments: dict,
        new_assignments: dict,
    ) -> list[dict]:
        """Assign a split day where primary employee works partial hours and coverage handles the rest."""

        assignments = []

        # Determine available and unavailable periods for primary employee
        for conflict_detail in day_conflict["conflicts"]:
            if conflict_detail["type"] == "recurring_pattern":
                pattern = conflict_detail["pattern"]

                if pattern.coverage_type == "morning":
                    # Primary unavailable 8-12, available 12-17
                    # Find coverage for morning (8-12)
                    morning_start = day_start
                    morning_end = day_start.replace(hour=12, minute=0)
                    coverage_assignments = self.find_day_coverage(
                        morning_start,
                        morning_end,
                        f"{day_label}_morning_coverage",
                        shift_type,
                        all_employees,
                        current_assignments,
                        new_assignments,
                        exclude_employee=primary_employee,
                    )
                    assignments.extend(coverage_assignments)

                    # Assign afternoon to primary (12-17)
                    afternoon_start = day_start.replace(hour=12, minute=0)
                    afternoon_end = day_end
                    assignments.extend(
                        self.create_day_assignment(
                            primary_employee,
                            afternoon_start,
                            afternoon_end,
                            f"{day_label}_afternoon_primary",
                            shift_type,
                            new_assignments,
                        ),
                    )

                elif pattern.coverage_type == "afternoon":
                    # Primary available 8-12, unavailable 12-17
                    # Assign morning to primary (8-12)
                    morning_start = day_start
                    morning_end = day_start.replace(hour=12, minute=0)
                    assignments.extend(
                        self.create_day_assignment(
                            primary_employee,
                            morning_start,
                            morning_end,
                            f"{day_label}_morning_primary",
                            shift_type,
                            new_assignments,
                        ),
                    )

                    # Find coverage for afternoon (12-17)
                    afternoon_start = day_start.replace(hour=12, minute=0)
                    afternoon_end = day_end
                    coverage_assignments = self.find_day_coverage(
                        afternoon_start,
                        afternoon_end,
                        f"{day_label}_afternoon_coverage",
                        shift_type,
                        all_employees,
                        current_assignments,
                        new_assignments,
                        exclude_employee=primary_employee,
                    )
                    assignments.extend(coverage_assignments)

                # For full day conflicts, this would be handled by find_day_coverage above

        return assignments

    def find_day_coverage(
        self,
        start_datetime: datetime,
        end_datetime: datetime,
        label: str,
        shift_type: str,
        all_employees: list[Any],
        current_assignments: dict,
        new_assignments: dict,
        exclude_employee: Any = None,
    ) -> list[dict]:
        """Find an employee to cover a specific time period, prioritizing fairness and continuity."""

        # Filter out excluded employee and find available employees
        candidate_employees = []
        for emp in all_employees:
            if exclude_employee and emp.pk == exclude_employee.pk:
                continue

            # Check if employee is available for this specific time period
            if self.constraint_checker.is_employee_available(
                emp, start_datetime, end_datetime, shift_type,
            ):
                candidate_employees.append(emp)

        if not candidate_employees:
            logger.warning(f"No coverage found for {label} on {start_datetime.date()}")
            return []

        # Strategy 1: Prioritize employees who have complementary patterns (reciprocal benefit)
        coverage_employee = self.find_complementary_pattern_employee(
            candidate_employees,
            start_datetime,
            current_assignments,
            new_assignments,
            shift_type,
        )

        if coverage_employee:
            logger.info(
                f"🔄 Found complementary pattern coverage: {coverage_employee.username} for {label}",
            )
            return self.create_day_assignment(
                coverage_employee,
                start_datetime,
                end_datetime,
                label,
                shift_type,
                new_assignments,
            )

        # Strategy 2: Fall back to least-assigned available employee (fairness priority)
        def sort_key_coverage(emp):
            emp_assignments = current_assignments.get(
                emp.pk, {"incidents": 0.0, "incidents_standby": 0.0, "waakdienst": 0.0},
            )
            current_hours = emp_assignments.get(shift_type.lower(), 0.0)
            new_hours = new_assignments[emp.pk].get(shift_type.lower(), 0.0)
            total_hours = current_hours + new_hours

            # Secondary sort: prefer employees who are significantly under-assigned
            return (total_hours, emp.pk)  # pk for consistent tie-breaking

        candidate_employees.sort(key=sort_key_coverage)
        coverage_employee = candidate_employees[0]

        # Log the fairness impact
        emp_load = sort_key_coverage(coverage_employee)[0]
        logger.info(
            f"🔄 Fairness coverage: {coverage_employee.username} for {label} (load: {emp_load:.1f}h)",
        )

        return self.create_day_assignment(
            coverage_employee,
            start_datetime,
            end_datetime,
            label,
            shift_type,
            new_assignments,
        )

    def find_complementary_pattern_employee(
        self,
        candidates: list[Any],
        target_datetime: datetime,
        current_assignments: dict,
        new_assignments: dict,
        shift_type: str,
    ) -> Any | None:
        """Find employee with complementary recurring pattern who could benefit from this assignment."""
        from team_planner.employees.models import RecurringLeavePattern

        target_date = target_datetime.date()
        target_day_of_week = target_date.weekday()

        # Look for employees who have recurring patterns on different days
        # and would benefit from taking this assignment
        best_candidate = None
        best_score = float("inf")

        for emp in candidates:
            # Get employee's patterns
            patterns = RecurringLeavePattern.objects.filter(
                employee=emp,
                is_active=True,
                effective_from__lte=target_date,
            ).filter(
                models.Q(effective_until__isnull=True)
                | models.Q(effective_until__gte=target_date),
            )

            # Calculate employee's current assignment load
            emp_assignments = current_assignments.get(
                emp.pk, {"incidents": 0.0, "incidents_standby": 0.0, "waakdienst": 0.0},
            )
            current_hours = emp_assignments.get(shift_type.lower(), 0.0)
            new_hours = new_assignments[emp.pk].get(shift_type.lower(), 0.0)
            total_hours = current_hours + new_hours

            # Prefer employees who:
            # 1. Have patterns on different days (complementary)
            # 2. Have lower assignment hours
            has_pattern_conflict_today = any(
                pattern.day_of_week == target_day_of_week for pattern in patterns
            )

            if not has_pattern_conflict_today:  # Good - no conflict today
                if total_hours < best_score:
                    best_score = total_hours
                    best_candidate = emp

        return best_candidate

    def create_day_assignment(
        self,
        employee: Any,
        start_datetime: datetime,
        end_datetime: datetime,
        label: str,
        shift_type: str,
        new_assignments: dict,
    ) -> list[dict]:
        """Create a single day assignment for an employee and track new hours per shift type."""
        template = self.get_shift_template(shift_type)
        if not template:
            return []
        duration_hours = (end_datetime - start_datetime).total_seconds() / 3600
        assignment = {
            "template_id": template.pk if template else None,
            "assigned_employee_id": employee.pk,
            "assigned_employee_name": employee.get_full_name(),
            "start_datetime": start_datetime,
            "end_datetime": end_datetime,
            "shift_type": shift_type,
            "week_start_date": start_datetime.date(),
            "auto_assigned": True,
            "assignment_reason": f"Fair distribution - {shift_type} - {label}",
            "duration_hours": duration_hours,
        }
        # Update new assignments tracking per type
        new_assignments[employee.pk][shift_type.lower()] = (
            new_assignments[employee.pk].get(shift_type.lower(), 0.0) + duration_hours
        )
        return [assignment]

    def create_full_week_assignments(
        self,
        employee: Any,
        daily_shifts: list[tuple],
        shift_type: str,
        new_assignments: dict,
    ) -> list[dict]:
        """Create assignments for a full week to a single employee."""
        template = self.get_shift_template(shift_type)
        if not template:
            return []

        # Guardrail: prevent double incidents/standby in same week
        try:
            week_start = daily_shifts[0][0]
            week_end = daily_shifts[-1][1]
            if self.check_incidents_conflicts_for_employee(
                employee, week_start, week_end, shift_type,
            ):
                logger.info(
                    f"Prevented double assignment: {employee.username} already has complementary {shift_type} in same week",
                )
                return []
        except Exception as e:
            logger.warning(
                f"Weekly conflict guard failed in create_full_week_assignments: {e}",
            )

        assignments = []
        total_hours = 0

        for day_start, day_end, day_label in daily_shifts:
            duration_hours = (day_end - day_start).total_seconds() / 3600
            total_hours += duration_hours
            assignments.append(
                {
                    "template_id": template.pk if template else None,
                    "assigned_employee_id": employee.pk,
                    "assigned_employee_name": employee.get_full_name(),
                    "start_datetime": day_start,
                    "end_datetime": day_end,
                    "shift_type": shift_type,
                    "week_start_date": daily_shifts[0][0].date()
                    if daily_shifts
                    else day_start.date(),
                    "auto_assigned": True,
                    "assignment_reason": f"Fair distribution - {shift_type} - {day_label}",
                    "duration_hours": duration_hours,
                },
            )

        # Update new assignments tracking (in hours) per type
        new_assignments[employee.pk][shift_type.lower()] = (
            new_assignments[employee.pk].get(shift_type.lower(), 0.0) + total_hours
        )

        return assignments

    def assign_full_week_normal(
        self,
        week_start: datetime,
        week_end: datetime,
        week_type: str,
        shift_type: str,
        available_employees: list[Any],
        current_assignments: dict,
        new_assignments: dict,
        daily_shifts: list[tuple],
    ) -> list[dict]:
        """Assign a full week normally (for waakdienst or when no patterns conflict)."""

        # Filter employees who are available for the entire week
        eligible_employees = [
            emp
            for emp in available_employees
            if self.constraint_checker.is_employee_available(
                emp, week_start, week_end, shift_type,
            )
        ]

        if not eligible_employees:
            logger.warning(f"No eligible employees for {shift_type} week {week_start}")
            return []

        # Sort by fairness (least assigned first) + new assignments
        def sort_key(emp):
            emp_assignments = current_assignments.get(
                emp.pk, {"incidents": 0.0, "incidents_standby": 0.0, "waakdienst": 0.0},
            )
            current_hours = emp_assignments.get(shift_type.lower(), 0.0)
            new_hours = new_assignments[emp.pk].get(shift_type.lower(), 0.0)
            return current_hours + new_hours

        eligible_employees.sort(key=sort_key)
        assigned_employee = eligible_employees[0]

        return self.create_full_week_assignments(
            assigned_employee, daily_shifts, shift_type, new_assignments,
        )

    def generate_schedule(self) -> dict[str, Any]:
        """Generate complete schedule for the period."""
        return self.orchestrate()

    def orchestrate(self) -> dict[str, Any]:
        """Generate schedule assignments for the specified period."""
        logger.info(
            f"Starting orchestration for period {self.start_date} to {self.end_date}",
        )
        logger.info(
            f"Shift types: incidents={self.schedule_incidents}, incidents_standby={self.schedule_incidents_standby}, waakdienst={self.schedule_waakdienst}",
        )

        all_assignments = []

        # Preload holiday cache if needed
        team = self.get_team()
        if team and getattr(team, "incidents_skip_holidays", False):
            self._ensure_holiday_cache()

        # Generate Incidents shifts first
        if self.schedule_incidents:
            incidents_weeks = self.generate_incidents_weeks()
            incidents_assignments = self.assign_shifts_fairly(
                ShiftType.INCIDENTS, incidents_weeks,
            )
            # Track assignments to prevent conflicts
            for assignment in incidents_assignments:
                self.add_assignment_to_tracker(assignment)
            all_assignments.extend(incidents_assignments)
            logger.info(
                f"Generated {len(incidents_assignments)} incidents daily shifts",
            )

        # Generate Incidents-Standby shifts (with conflict checking)
        if self.schedule_incidents_standby:
            incidents_weeks = self.generate_incidents_weeks()  # Same weeks as incidents
            standby_assignments = self.assign_shifts_fairly(
                ShiftType.INCIDENTS_STANDBY, incidents_weeks,
            )
            # Track assignments
            for assignment in standby_assignments:
                self.add_assignment_to_tracker(assignment)
            all_assignments.extend(standby_assignments)
            logger.info(
                f"Generated {len(standby_assignments)} incidents-standby daily shifts",
            )

        # Generate Waakdienst shifts
        if self.schedule_waakdienst:
            waakdienst_weeks = self.generate_waakdienst_weeks()
            waakdienst_assignments = self.assign_shifts_fairly(
                ShiftType.WAAKDIENST, waakdienst_weeks,
            )
            # Track assignments
            for assignment in waakdienst_assignments:
                self.add_assignment_to_tracker(assignment)
            all_assignments.extend(waakdienst_assignments)
            logger.info(
                f"Generated {len(waakdienst_assignments)} waakdienst daily shifts",
            )

        # Detect and resolve conflicts if reassignment manager is available
        reassignment_summary = None
        if self.reassignment_manager:
            logger.info("Starting conflict detection and reassignment...")
            conflicts = self.reassignment_manager.detect_conflicts(all_assignments)

            if conflicts:
                logger.info(
                    f"Detected {len(conflicts)} conflicts, attempting automatic reassignment",
                )
                self.reassignment_manager.resolve_conflicts(conflicts)

                # Handle split assignments by replacing with individual daily assignments
                updated_assignments = []
                split_assignments_to_remove = []

                for assignment in all_assignments:
                    if assignment.get("is_split_assignment", False):
                        # This assignment was split, replace with individual daily assignments
                        split_info = assignment.get("split_coverage")
                        if split_info:
                            daily_assignments = self.reassignment_manager.create_split_shift_assignments(
                                assignment, split_info,
                            )
                            updated_assignments.extend(daily_assignments)
                            split_assignments_to_remove.append(assignment)
                            logger.info(
                                f"Replaced split assignment with {len(daily_assignments)} daily assignments",
                            )
                    else:
                        updated_assignments.append(assignment)

                # Replace all_assignments with the updated list
                all_assignments = updated_assignments

                reassignment_summary = (
                    self.reassignment_manager.get_reassignment_summary()
                )
                logger.info(
                    f"Reassignment complete: {reassignment_summary['successful_reassignments']} successful, {reassignment_summary['failed_reassignments']} failed",
                )
            else:
                logger.info("No conflicts detected")
                reassignment_summary = (
                    self.reassignment_manager.get_reassignment_summary()
                )

        # Calculate metrics
        incidents_count = len(
            [a for a in all_assignments if a["shift_type"] == ShiftType.INCIDENTS],
        )
        incidents_standby_count = len(
            [
                a
                for a in all_assignments
                if a["shift_type"] == ShiftType.INCIDENTS_STANDBY
            ],
        )
        waakdienst_count = len(
            [a for a in all_assignments if a["shift_type"] == ShiftType.WAAKDIENST],
        )

        # Calculate fairness metrics based on the generated plan (provisional)
        all_employees = list({a["assigned_employee_id"] for a in all_assignments})
        provisional_assignments = (
            self.fairness_calculator.calculate_provisional_assignments(all_assignments)
            if all_assignments
            else {}
        )
        fairness_scores = self.fairness_calculator.calculate_fairness_score(
            provisional_assignments,
        )

        result = {
            "assignments": all_assignments,
            "total_shifts": len(all_assignments),
            "incidents_shifts": incidents_count,
            "incidents_standby_shifts": incidents_standby_count,
            "waakdienst_shifts": waakdienst_count,
            "employees_assigned": len(all_employees),
            "fairness_scores": fairness_scores,
            "average_fairness": sum(fairness_scores.values()) / len(fairness_scores)
            if fairness_scores
            else 0,
            "period_start": self.start_date,
            "period_end": self.end_date,
            "reassignment_summary": reassignment_summary,
        }

        logger.info(
            f"Orchestration complete: {result['total_shifts']} daily shifts generated",
        )
        logger.info(
            f"Breakdown: {incidents_count} incidents, {incidents_standby_count} incidents-standby, {waakdienst_count} waakdienst",
        )

        if reassignment_summary:
            logger.info(
                f"Conflicts resolved: {reassignment_summary['successful_reassignments']} reassignments, {reassignment_summary['manual_interventions_required']} manual interventions needed",
            )

        # Also include DB-based fairness for reference
        try:
            # Convert employee IDs to employee objects
            employee_objects = [User.objects.get(pk=emp_id) for emp_id in all_employees]
            (
                self.fairness_calculator.calculate_current_assignments(employee_objects)
            )
            # Skip DB fairness scores to avoid JSON serialization issues with User objects
            # result['db_fairness_scores'] = self.fairness_calculator.calculate_fairness_score(final_assignments_db)
        except Exception as e:
            logger.warning(f"DB fairness calculation skipped: {e}")

        return result

    def preview_schedule(self) -> dict[str, Any]:
        """Generate schedule preview without saving, with duplicate detection."""
        schedule = self.generate_schedule()

        # Check for duplicates in preview
        potential_duplicates = []
        for assignment in schedule["assignments"]:
            if self.check_for_duplicate_shifts(assignment):
                potential_duplicates.append(
                    {
                        "shift_type": assignment["shift_type"],
                        "start_datetime": assignment["start_datetime"],
                        "end_datetime": assignment["end_datetime"],
                        "assigned_employee": assignment["assigned_employee_name"],
                    },
                )

        schedule["potential_duplicates"] = potential_duplicates
        if potential_duplicates:
            logger.warning(
                f"Preview detected {len(potential_duplicates)} potential duplicate shifts",
            )

        return schedule

    def check_for_duplicate_shifts(self, assignment: dict) -> bool:
        """Check if a shift already exists for the same time period and shift type."""
        existing_shifts = Shift.objects.filter(
            template__shift_type=assignment["shift_type"],
            start_datetime=assignment["start_datetime"],
            end_datetime=assignment["end_datetime"],
        ).exists()

        if existing_shifts:
            logger.warning(
                f"Duplicate shift detected: {assignment['shift_type']} "
                f"from {assignment['start_datetime']} to {assignment['end_datetime']}",
            )
            return True
        return False

    def apply_schedule(self) -> dict[str, Any]:
        """Generate and save schedule to database with duplicate prevention."""
        schedule = self.generate_schedule()

        created_shifts = []
        skipped_duplicates = []

        for assignment in schedule["assignments"]:
            # Check for duplicates before creating
            if self.check_for_duplicate_shifts(assignment):
                skipped_duplicates.append(
                    {
                        "shift_type": assignment["shift_type"],
                        "start_datetime": assignment["start_datetime"],
                        "end_datetime": assignment["end_datetime"],
                        "assigned_employee": assignment["assigned_employee_name"],
                    },
                )
                continue

            # Get the template and employee by ID
            template = (
                ShiftTemplate.objects.get(pk=assignment["template_id"])
                if assignment["template_id"]
                else None
            )
            employee = User.objects.get(pk=assignment["assigned_employee_id"])

            shift = Shift.objects.create(
                template=template,
                assigned_employee=employee,
                start_datetime=assignment["start_datetime"],
                end_datetime=assignment["end_datetime"],
                status="scheduled",
                auto_assigned=assignment["auto_assigned"],
                assignment_reason=assignment["assignment_reason"],
            )
            created_shifts.append(shift)

        schedule["created_shifts"] = created_shifts
        schedule["skipped_duplicates"] = skipped_duplicates

        if skipped_duplicates:
            logger.warning(f"Skipped {len(skipped_duplicates)} duplicate shifts")

        logger.info(
            f"Applied schedule: {len(created_shifts)} daily shifts created, {len(skipped_duplicates)} duplicates skipped",
        )
        return schedule

    def check_incidents_conflicts_for_employee(
        self, employee: Any, start_date: datetime, end_date: datetime, shift_type: str,
    ) -> bool:
        """Check if employee already has incidents or incidents-standby assigned for the same week period.
        Prevent same engineer from getting both roles within the same Mon-Fri business week.
        """
        if shift_type not in [ShiftType.INCIDENTS, ShiftType.INCIDENTS_STANDBY]:
            return False

        # Helper to get Monday (date) of the business week for a datetime
        def week_monday(d: datetime):
            return (d - timedelta(days=d.weekday())).date()

        req_week = week_monday(start_date)

        # Check assignments already produced in this run (strongest guardrail)
        for assignment in self.current_run_assignments:
            if (
                assignment["assigned_employee_id"] == employee.pk
                and assignment["shift_type"]
                in [ShiftType.INCIDENTS, ShiftType.INCIDENTS_STANDBY]
                and assignment["shift_type"] != shift_type
            ):
                a_week = week_monday(assignment["start_datetime"])
                if a_week == req_week:
                    logger.info(
                        f"Preventing double incidents assignment: {employee.username} already has {assignment['shift_type']} in week starting {req_week}",
                    )
                    return True
                # Fallback: overlap in time (kept for robustness)
                if (
                    assignment["start_datetime"] < end_date
                    and assignment["end_datetime"] > start_date
                ):
                    logger.info(
                        f"Preventing overlapping incidents assignment: {employee.username} already has {assignment['shift_type']} overlapping with requested {shift_type}",
                    )
                    return True

        # DB-level check for existing shifts in the same business week
        try:
            week_start = datetime.combine(
                req_week, time(0, 0, 0, tzinfo=getattr(start_date, "tzinfo", None)),
            )
        except Exception:
            # Fallback to timezone aware composition
            week_start = timezone.make_aware(datetime.combine(req_week, time(0, 0)))
        week_end = week_start + timedelta(days=7)

        week_shifts = Shift.objects.filter(
            assigned_employee=employee,
            start_datetime__gte=week_start,
            start_datetime__lt=week_end,
            status__in=[Shift.Status.SCHEDULED, Shift.Status.IN_PROGRESS],
        ).select_related("template")

        for shift in week_shifts:
            if (
                shift.template.shift_type
                in [ShiftType.INCIDENTS, ShiftType.INCIDENTS_STANDBY]
                and shift.template.shift_type != shift_type
            ):
                logger.info(
                    f"Preventing double incidents assignment (DB): {employee.username} already has existing {shift.template.shift_type} in week starting {req_week}",
                )
                return True

        return False

    def add_assignment_to_tracker(self, assignment: dict):
        """Add an assignment to the current run tracker."""
        self.current_run_assignments.append(assignment)
