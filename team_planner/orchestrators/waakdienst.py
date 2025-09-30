"""
WaakdienstOrchestrator: Wednesday-Wednesday Evening/Weekend Orchestration

This module implements the WaakdienstOrchestrator for Phase 1.2 of the split
orchestrator architecture. It handles Waakdienst shifts with Wednesday-Wednesday
rotation cycles and constraint-first generation for evening/weekend coverage.

Key Features:
- Wednesday 17:00 start, Wednesday 08:00 end rotation (7 days)
- Constraint-first day-by-day generation
- Evening/weekend focus (excludes business hours patterns)
- Independent fairness tracking for waakdienst
- Continuity preference for week-long assignments
"""

from datetime import datetime
from datetime import timedelta
from typing import Any
from zoneinfo import ZoneInfo

from team_planner.leaves.models import LeaveRequest
from team_planner.orchestrators.base_orchestrator import BaseOrchestrator
from team_planner.orchestrators.fairness_calculators import WaakdienstFairnessCalculator
from team_planner.orchestrators.utils.time_windows import get_waakdienst_week_bounds
from team_planner.orchestrators.utils.time_windows import get_waakdienst_week_start
from team_planner.orchestrators.utils.time_windows import waakdienst_daily_window
from team_planner.shifts.models import Shift
from team_planner.shifts.models import ShiftTemplate
from team_planner.shifts.models import ShiftType
from team_planner.users.models import User


class WaakdienstOrchestrator(BaseOrchestrator):
    """Orchestrator specialized for Waakdienst (evening/weekend) shifts.

    This orchestrator operates on a Wednesday-Wednesday cycle:
    - Rotation Start: Wednesday 17:00
    - Rotation End: Wednesday 08:00+7days
    - Shift Types: Waakdienst only
    - Coverage: Evening hours, weekends, and overnight periods
    - Generation: Constraint-first, day-by-day with continuity preference
    """

    def __init__(self, team_id: int | None = None):
        super().__init__(team_id=team_id)

        # Waakdienst-specific configuration
        self.evening_start_hour = 17  # 17:00 (after business hours)
        self.morning_end_hour = 8  # 08:00 (before business hours)
        self.waakdienst_duration_hours = 15  # Typical overnight shift duration

        # Weekend configuration
        self.weekend_start_hour = 17  # Friday 17:00
        self.weekend_end_hour = 8  # Monday 08:00

    def _get_handled_shift_types(self) -> list[str]:
        """Return shift types handled by this orchestrator."""
        return [ShiftType.WAAKDIENST]

    def _get_rotation_start_weekday(self) -> int:
        """Return Wednesday (2) as the rotation start day."""
        return 2  # Wednesday

    def _get_shift_templates(self) -> list[ShiftTemplate]:
        """Get shift templates for waakdienst shifts.

        Returns one template to avoid duplicate assignments.
        Prefers templates with reasonable waakdienst durations (15-24 hours).
        """
        # Get all active templates for waakdienst
        candidates = ShiftTemplate.objects.filter(
            shift_type=ShiftType.WAAKDIENST, is_active=True,
        ).order_by("duration_hours")

        # Select the best template for waakdienst work
        selected_template = None

        for template in candidates:
            # Prefer templates with reasonable waakdienst durations (15-24 hours)
            if 15 <= (template.duration_hours or 24) <= 24:
                selected_template = template
                break

        # If no suitable template found but at least one exists, use the first
        if not selected_template and candidates.exists():
            selected_template = candidates.first()

        # If none exist, auto-provision a safe default to unblock orchestration
        if not selected_template:
            # Avoid duplicate creation by name
            selected_template, _created = ShiftTemplate.objects.get_or_create(
                shift_type=ShiftType.WAAKDIENST,
                name="Waakdienst Daily (Auto)",
                defaults={
                    "description": "Auto-created template for waakdienst evening/weekend coverage",
                    # 15h covers weeknights; weekend days will still be 24h via windows
                    "duration_hours": 15,
                    "is_active": True,
                },
            )

        return [selected_template] if selected_template else []

    def _create_fairness_calculator(self, start_date: datetime, end_date: datetime):
        """Create waakdienst fairness calculator for this period."""
        return WaakdienstFairnessCalculator(start_date, end_date)

    def _filter_employees_by_availability(self, employees: list[User]) -> list[User]:
        """Filter employees who are available for waakdienst work based on skills."""
        available_employees = []

        for employee in employees:
            profile = getattr(employee, "employee_profile", None)
            if profile:
                # Prefer explicit availability flag; fall back to skill if used
                flag_ok = getattr(profile, "available_for_waakdienst", False)
                # Use case-insensitive match to avoid missing 'Waakdienst' vs 'waakdienst'
                has_skill = profile.skills.filter(
                    name__iexact="waakdienst", is_active=True,
                ).exists()

                if flag_ok or has_skill:
                    available_employees.append(employee)
            # Include admin users without profiles
            elif getattr(employee, "is_superuser", False):
                available_employees.append(employee)

        return available_employees

    def _needs_shift_on_date(self, date: datetime, template: ShiftTemplate) -> bool:
        """Check if we need a waakdienst shift on the given date.

        For waakdienst orchestrator:
        - Monday evening: Yes (after business hours)
        - Tuesday evening: Yes (after business hours)
        - Wednesday evening: Yes (after business hours)
        - Thursday evening: Yes (after business hours)
        - Friday evening: Yes (weekend coverage starts)
        - Saturday: Yes (weekend coverage)
        - Sunday: Yes (weekend coverage)
        """
        # Waakdienst covers evening hours every day
        # The actual shift timing is determined in _calculate_shift_times
        return True

    def _calculate_shift_times(
        self, date: datetime, template: ShiftTemplate,
    ) -> tuple[datetime, datetime]:
        """Calculate start and end times for waakdienst shifts using shared utility."""
        return waakdienst_daily_window(date)

    def _generate_assignments_for_date(
        self,
        date: datetime,
        employees: list[User],
        shift_templates: list[ShiftTemplate],
        last_assigned: dict,
        existing_assignments: list[dict],
    ) -> list[dict]:
        """Generate waakdienst assignments for a specific date including weekends."""
        # All days need waakdienst coverage - no skipping Saturday/Sunday
        return super()._generate_assignments_for_date(
            date, employees, shift_templates, last_assigned, existing_assignments,
        )

    def _find_best_employee_for_shift(
        self,
        date: datetime,
        template: ShiftTemplate,
        employees: list[User],
        last_assigned: User | None,
        existing_assignments: list[dict],
    ) -> User | None:
        """Find the best employee for waakdienst shifts with evening/weekend constraints.

        Note: This method is now only used by the legacy day-by-day generation.
        The new week-based generation uses _select_employee_for_week instead.
        """

        # Filter employees who are specifically available for waakdienst
        shift_type_employees = []

        for employee in employees:
            if not self.is_employee_available_on_date(employee, date):
                continue

            profile = getattr(employee, "employee_profile", None)
            if profile:
                # Check if employee has the "waakdienst" skill
                has_waakdienst_skill = profile.skills.filter(
                    name__iexact="waakdienst", is_active=True,
                ).exists()

                if has_waakdienst_skill:
                    shift_type_employees.append(employee)
            # Include admin users without profiles
            elif getattr(employee, "is_superuser", False):
                shift_type_employees.append(employee)

        if not shift_type_employees:
            return None

        # Apply continuity preference for weekly assignments
        if last_assigned and last_assigned in shift_type_employees:
            # Check if it's still the same waakdienst week (Wed 17:00 - Wed 08:00)
            week_start = self._get_waakdienst_week_start(date)
            assignment_day = (date - week_start).days

            # Prefer continuity within the same waakdienst week (7-day cycle)
            if 0 <= assignment_day <= 6:  # Within the 7-day cycle
                return last_assigned

        # Select by fairness if no continuity preference
        return self._select_employee_by_fairness(
            shift_type_employees, template.shift_type, existing_assignments,
        )

    def generate_assignments(
        self, start_date: datetime, end_date: datetime, dry_run: bool = False,
    ) -> dict[str, Any]:
        """Generate waakdienst assignments using week-by-week logic.

        Override the base class day-by-day logic to implement proper
        week-by-week assignment where one engineer gets the entire week.
        """
        # Reset generation counter for fair rotation
        self._generation_assignment_count = 0

        # Initialize fairness calculator for this period
        self.fairness_calculator = self._create_fairness_calculator(
            start_date, end_date,
        )

        # Get available employees and shift templates
        employees = self.get_available_employees()
        shift_templates = self._get_shift_templates()

        if not employees:
            return {
                "assignments": [],
                "total_shifts": 0,
                "employees_assigned": 0,
                "errors": ["No available employees found"],
            }

        if not shift_templates:
            return {
                "assignments": [],
                "total_shifts": 0,
                "employees_assigned": 0,
                "errors": ["No shift templates configured"],
            }

        # Generate waakdienst weeks for the period
        waakdienst_weeks = self._generate_waakdienst_weeks(start_date, end_date)

        assignments = []
        assigned_employees = set()

        # Assign each week to an available employee
        for week_start, week_end in waakdienst_weeks:
            # Find best employee for this entire week
            week_employee = self._select_employee_for_week(
                employees, week_start, assignments,
            )

            if week_employee:
                # Generate all daily shifts for this week with the same employee
                week_assignments = self._generate_week_assignments(
                    week_employee, week_start, week_end, shift_templates[0],
                )
                assignments.extend(week_assignments)
                assigned_employees.add(week_employee.pk)

        # Calculate fairness metrics for the generated assignments
        fairness_metrics = self._calculate_assignment_fairness(assignments, employees)

        # If not a dry run, save the assignments to the database
        if not dry_run and assignments:
            self._save_orchestration_results(
                start_date, end_date, assignments, fairness_metrics,
            )

        return {
            "assignments": assignments,
            "total_shifts": len(assignments),
            "employees_assigned": len(assigned_employees),
            "fairness_metrics": fairness_metrics,
            "errors": [],
            "warnings": [],
        }

    def _generate_waakdienst_weeks(
        self, start_date: datetime, end_date: datetime,
    ) -> list[tuple[datetime, datetime]]:
        """Generate waakdienst week periods (Wednesday 17:00 to Wednesday 08:00)."""
        weeks = []

        # Find the first Wednesday 17:00 on or after start_date
        current = start_date
        while current.weekday() != 2:  # Find next Wednesday
            current += timedelta(days=1)

        # Set to 17:00 on this Wednesday
        current = current.replace(hour=17, minute=0, second=0, microsecond=0)

        # If this Wednesday 17:00 is before start_date, move to next Wednesday
        if current < start_date:
            current += timedelta(days=7)

        # Generate complete weeks
        while current <= end_date:
            week_start = current
            week_end = current + timedelta(days=7)  # Next Wednesday 17:00
            week_end = week_end.replace(
                hour=8, minute=0, second=0, microsecond=0,
            )  # Actually Wednesday 08:00

            # Only include weeks that fit within our date range
            if week_start <= end_date:
                weeks.append((week_start, week_end))

            current += timedelta(days=7)  # Next Wednesday

        return weeks

    def _select_employee_for_week(
        self,
        employees: list[User],
        week_start: datetime,
        existing_assignments: list[dict],
    ) -> User | None:
        """Select the best employee for an entire waakdienst week."""
        available_employees = []

        for employee in employees:
            # Check if employee is available for the entire week
            if self._is_employee_available_for_week(employee, week_start):
                profile = getattr(employee, "employee_profile", None)
                if profile:
                    # Check if employee has the "waakdienst" skill
                    has_waakdienst_skill = profile.skills.filter(
                        name__iexact="waakdienst", is_active=True,
                    ).exists()

                    if has_waakdienst_skill:
                        available_employees.append(employee)
                # Include admin users without profiles
                elif getattr(employee, "is_superuser", False):
                    available_employees.append(employee)

        if not available_employees:
            return None

        # Use fairness to select employee
        return self._select_employee_by_fairness(
            available_employees, "waakdienst", existing_assignments,
        )

    def _is_employee_available_for_week(
        self, employee: User, week_start: datetime,
    ) -> bool:
        """Check if employee is available for the entire waakdienst week."""
        # Check each day of the week
        current_date = week_start
        for _day in range(7):
            if not self.is_employee_available_on_date(employee, current_date):
                return False
            current_date += timedelta(days=1)
        return True

    def _generate_week_assignments(
        self,
        employee: User,
        week_start: datetime,
        week_end: datetime,
        template: ShiftTemplate,
    ) -> list[dict]:
        """Generate all daily shift assignments for a week with the same employee."""
        assignments = []
        current_date = week_start

        # Generate shifts for 7 days
        for _day in range(7):
            if not self._needs_shift_on_date(current_date, template):
                current_date += timedelta(days=1)
                continue

            shift_start, shift_end = self._calculate_shift_times(current_date, template)

            assignment = {
                "assigned_employee": employee,
                "assigned_employee_id": employee.pk,
                "assigned_employee_name": employee.get_full_name() or employee.username,
                "shift_type": template.shift_type,
                "template": template,
                "start_datetime": shift_start,
                "end_datetime": shift_end,
                "duration_hours": (shift_end - shift_start).total_seconds() / 3600,
                "auto_assigned": True,
                "assignment_reason": f"Week assignment - {template.shift_type}",
            }

            assignments.append(assignment)
            current_date += timedelta(days=1)

        return assignments

    def is_employee_available_on_date(self, employee: User, date: datetime) -> bool:
        """Check if an employee is available for waakdienst on a specific date.

        Waakdienst availability only checks for:
        - Approved vacation leave requests
        - Existing shift assignments
        - Minimum rest requirements

        It does NOT check recurring leave patterns (ATV, etc.) since waakdienst
        (evening/weekend) coverage is compatible with business hours leave patterns.
        """
        # Check for approved vacation leave requests (but not ATV patterns)
        if self._has_approved_vacation_leave(employee, date):
            return False

        # Check for existing shift assignments that would conflict
        if self._has_conflicting_shifts(employee, date):
            return False

        # Check for minimum rest between shifts
        if not self._has_sufficient_rest(employee, date):
            return False

        # Check for maximum consecutive weeks constraint
        return self._within_consecutive_weeks_limit(employee, date)

    def _has_approved_vacation_leave(self, employee: User, date: datetime) -> bool:
        """Check if employee has approved vacation leave on this date.

        Only blocks for actual vacation/leave requests, not recurring patterns like ATV.
        """
        date_obj = date.date()
        return LeaveRequest.objects.filter(
            employee=employee,
            status="approved",
            start_date__lte=date_obj,
            end_date__gte=date_obj,
        ).exists()

    def _has_conflicting_shifts(self, employee: User, date: datetime) -> bool:
        """Check if employee has existing waakdienst shifts that overlap the waakdienst window.

        Daytime shifts (e.g., incidents 08:00–17:00) on the same calendar day are NOT conflicts,
        because waakdienst covers evenings/nights and weekends per spec.
        """
        # Compute the waakdienst window for this day
        window_start, window_end = waakdienst_daily_window(date)

        # Only treat existing waakdienst shifts that overlap as conflicts
        return Shift.objects.filter(
            assigned_employee=employee,
            template__shift_type=ShiftType.WAAKDIENST,
            start_datetime__lt=window_end,
            end_datetime__gt=window_start,
        ).exists()


    def _get_waakdienst_week_start(self, date: datetime) -> datetime:
        """Use shared utility to compute waakdienst week start."""
        return get_waakdienst_week_start(date)

    def generate_waakdienst_week_assignments(
        self, week_start: datetime, dry_run: bool = False,
    ) -> dict:
        """Generate assignments for a complete waakdienst week (Wednesday-Tuesday).

        This is a convenience method for generating a single waakdienst week
        which is the natural unit for waakdienst orchestration.
        """
        # Ensure week_start is a Wednesday
        if week_start.weekday() != 2:
            # Adjust to the Wednesday of this week
            days_to_wednesday = (2 - week_start.weekday()) % 7
            week_start = week_start + timedelta(days=days_to_wednesday)

        # Use shared bounds
        start, end = get_waakdienst_week_bounds(week_start)
        return self.generate_assignments(start, end, dry_run=dry_run)

    def get_next_waakdienst_week_start(
        self, reference_date: datetime | None = None,
    ) -> datetime:
        """Get the start of the next waakdienst week (Wednesday 17:00) after the reference date.

        This is useful for scheduling the next waakdienst orchestration run.
        """
        if reference_date is None:
            reference_date = datetime.now(tz=ZoneInfo("Europe/Amsterdam"))

        # Find next Wednesday
        days_until_wednesday = (2 - reference_date.weekday()) % 7
        if days_until_wednesday == 0 and reference_date.hour >= 17:
            # If it's Wednesday and past 5 PM, get next Wednesday
            days_until_wednesday = 7

        next_wednesday = reference_date + timedelta(days=days_until_wednesday)
        return next_wednesday.replace(hour=17, minute=0, second=0, microsecond=0)

    def get_current_waakdienst_week_range(
        self, reference_date: datetime | None = None,
    ) -> tuple[datetime, datetime]:
        """Get the current waakdienst week range using the shared utility."""
        if reference_date is None:
            reference_date = datetime.now(tz=ZoneInfo("Europe/Amsterdam"))
        # Delegate precise bounds to shared util for consistency
        return get_waakdienst_week_bounds(reference_date)

    def __str__(self):
        """String representation of the orchestrator."""
        team_info = f" (Team {self.team_id})" if self.team_id else ""
        return f"WaakdienstOrchestrator{team_info}"

    def __repr__(self):
        """Detailed representation of the orchestrator."""
        return f"WaakdienstOrchestrator(team_id={self.team_id})"

    # --- Compatibility wrapper for unified base interface ---
    def generate_schedule(
        self,
        start_date: datetime,
        end_date: datetime,
        orchestration_run: Any | None = None,
    ) -> dict[str, Any]:
        """Standard interface wrapper that delegates to week-based generation.

        Returns the same shape as generate_assignments for compatibility.
        """
        # Use dry_run when no orchestration_run provided
        dry_run = orchestration_run is None
        return self.generate_assignments(start_date, end_date, dry_run=dry_run)
