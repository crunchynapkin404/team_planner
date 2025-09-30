"""
IncidentsOrchestrator: Monday-Friday Business Hours Orchestration

This module implements the IncidentsOrchestrator for Phase 1.2 of the split
orchestrator architecture. It handles both Incidents and Incidents-Standby
shifts with Monday-Friday rotation cycles and constraint-first generation.

Key Features:
- Monday 08:00 start, Friday 17:00 end rotation
- Constraint-first day-by-day generation
- Business hours focus (excludes evening/weekend patterns)
- Independent fairness tracking for incidents vs standby
- Continuity preference for week-long assignments
"""

from datetime import datetime
from datetime import timedelta
from zoneinfo import ZoneInfo

import pytz

from team_planner.orchestrators.base_orchestrator import BaseOrchestrator
from team_planner.orchestrators.fairness_calculators import IncidentsFairnessCalculator
from team_planner.orchestrators.fairness_calculators import (
    IncidentsStandbyFairnessCalculator,
)
from team_planner.shifts.models import ShiftTemplate
from team_planner.shifts.models import ShiftType
from team_planner.users.models import User


class IncidentsOrchestrator(BaseOrchestrator):
    """Orchestrator specialized for Incidents and Incidents-Standby shifts.

    This orchestrator operates on a Monday-Friday business week cycle:
    - Rotation Start: Monday 08:00
    - Rotation End: Friday 17:00
    - Shift Types: Incidents, Incidents-Standby
    - Generation: Constraint-first, day-by-day with continuity preference
    """

    def __init__(
        self,
        team_id: int | None = None,
        prioritize_standby: bool = False,
        include_standby: bool = True,
    ):
        super().__init__(team_id=team_id)
        self.prioritize_standby = prioritize_standby
        self.include_standby = include_standby

        # Incidents-specific configuration
        self.business_start_hour = 8  # 08:00
        self.business_end_hour = 17  # 17:00
        self.incidents_duration_hours = 9  # Full business day
        self.standby_duration_hours = 15  # Overnight standby coverage

    def _get_handled_shift_types(self) -> list[str]:
        """Return shift types handled by this orchestrator."""
        return [ShiftType.INCIDENTS, ShiftType.INCIDENTS_STANDBY]

    def _get_rotation_start_weekday(self) -> int:
        """Return Monday (0) as the rotation start day."""
        return 0  # Monday

    def _get_shift_templates(self) -> list[ShiftTemplate]:
        """Get or create shift templates for incidents and standby shifts.
        Auto-provision safe defaults if missing to avoid blocking orchestration.
        """
        wanted_types = [ShiftType.INCIDENTS]
        if self.include_standby:
            wanted_types.append(ShiftType.INCIDENTS_STANDBY)

        existing = list(
            ShiftTemplate.objects.filter(
                shift_type__in=wanted_types,
                is_active=True,
            ),
        )

        have_incidents = any(t.shift_type == ShiftType.INCIDENTS for t in existing)
        have_standby = any(
            t.shift_type == ShiftType.INCIDENTS_STANDBY for t in existing
        )

        if not have_incidents:
            tmpl, _ = ShiftTemplate.objects.get_or_create(
                shift_type=ShiftType.INCIDENTS,
                name="Incidents Daily (Auto)",
                defaults={
                    "description": "Auto-created template for incidents 08:00-17:00",
                    "duration_hours": 9,
                    "is_active": True,
                },
            )
            existing.append(tmpl)

        if self.include_standby and not have_standby:
            tmpl, _ = ShiftTemplate.objects.get_or_create(
                shift_type=ShiftType.INCIDENTS_STANDBY,
                name="Incidents Standby Daily (Auto)",
                defaults={
                    "description": "Auto-created template for incidents standby 08:00-17:00",
                    "duration_hours": 9,
                    "is_active": True,
                },
            )
            existing.append(tmpl)

        return existing

    def _create_fairness_calculator(self, start_date: datetime, end_date: datetime):
        """Create incidents fairness calculator for this period.

        Note: We use IncidentsFairnessCalculator which only tracks incidents.
        Standby fairness is tracked separately by IncidentsStandbyFairnessCalculator.
        """
        # For now, use incidents calculator. In Phase 2, we'll implement dual tracking
        return IncidentsFairnessCalculator(start_date, end_date)

    def _filter_employees_by_availability(self, employees: list[User]) -> list[User]:
        """Filter employees who are available for incidents work."""
        available_employees = []

        for employee in employees:
            profile = getattr(employee, "employee_profile", None)
            if profile:
                # Check if employee is available for incidents (standby uses same flag)
                available_for_incidents = getattr(
                    profile, "available_for_incidents", False,
                )
                # Note: There is no separate available_for_incidents_standby flag in the model.
                # Standby eligibility follows incidents availability for business-hours backup.
                if available_for_incidents:
                    available_employees.append(employee)
            else:
                # Include employees without profiles (assume available)
                available_employees.append(employee)

        return available_employees

    def _needs_shift_on_date(self, date: datetime, template: ShiftTemplate) -> bool:
        """Check if we need a shift of this template type on the given date.

        For incidents orchestrator:
        - Incidents: Monday-Friday only
        - Incidents-Standby: Monday-Friday only (evening coverage)
        """
        weekday = date.weekday()  # 0=Monday, 6=Sunday

        if template.shift_type == ShiftType.INCIDENTS:
            # Incidents only on business days (Monday-Friday)
            return 0 <= weekday <= 4

        if template.shift_type == ShiftType.INCIDENTS_STANDBY:
            # Incidents standby also only on business days
            return 0 <= weekday <= 4

        return False

    def _calculate_shift_times(
        self, date: datetime, template: ShiftTemplate,
    ) -> tuple[datetime, datetime]:
        """Calculate start and end times for incidents shifts.

        Per spec:
        - Incidents: 08:00 - 17:00 (business hours)
        - Incidents-Standby: 08:00 - 17:00 (simultaneous backup during business hours)
        """
        # Business hours: 8 AM to 5 PM for both incidents and standby
        start_time = date.replace(
            hour=self.business_start_hour,
            minute=0,
            second=0,
            microsecond=0,
        )
        end_time = date.replace(
            hour=self.business_end_hour,
            minute=0,
            second=0,
            microsecond=0,
        )
        # Ensure timezone-aware (Europe/Amsterdam)
        tz = ZoneInfo("Europe/Amsterdam")
        if start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=tz)
        else:
            start_time = start_time.astimezone(tz)
        if end_time.tzinfo is None:
            end_time = end_time.replace(tzinfo=tz)
        else:
            end_time = end_time.astimezone(tz)
        return start_time, end_time

    def _find_best_employee_for_shift(
        self,
        date: datetime,
        template: ShiftTemplate,
        employees: list[User],
        last_assigned: User | None,
        existing_assignments: list[dict],
    ) -> User | None:
        """Find the best employee for incidents shifts with business-hours constraints."""

        # Filter employees who are specifically available for this shift type
        shift_type_employees = []

        # Exclude employees already assigned to the other incidents-type shift for this same day
        assigned_emp_ids_same_day: set[int] = set()
        if existing_assignments:
            for a in existing_assignments:
                a_date = a.get("start_datetime")
                if not a_date:
                    continue
                if a_date.date() != date.date():
                    continue
                # Only consider incidents/standby window overlaps
                if a.get("shift_type") in (
                    ShiftType.INCIDENTS,
                    ShiftType.INCIDENTS_STANDBY,
                ):
                    emp_id_val = a.get("assigned_employee_id")
                    if isinstance(emp_id_val, int):
                        assigned_emp_ids_same_day.add(emp_id_val)

        for employee in employees:
            if not self.is_employee_available_on_date(employee, date):
                continue

            # Prevent assigning the same engineer to both primary and standby on the same day
            if getattr(employee, "pk", None) in assigned_emp_ids_same_day:
                continue

            profile = getattr(employee, "employee_profile", None)
            if profile:
                if template.shift_type == ShiftType.INCIDENTS:
                    if getattr(profile, "available_for_incidents", False):
                        shift_type_employees.append(employee)
                elif template.shift_type == ShiftType.INCIDENTS_STANDBY:
                    # Standby uses the same availability flag as incidents for business-hours backup
                    if getattr(profile, "available_for_incidents", False):
                        shift_type_employees.append(employee)
            else:
                # Include employees without profiles
                shift_type_employees.append(employee)

        if not shift_type_employees:
            return None

        # Apply continuity preference only if last_assigned already has an assignment
        # earlier in THIS business week (prevents cross-week stickiness)
        if last_assigned and last_assigned in shift_type_employees:
            week_start = self._get_week_start(date, self._get_rotation_start_weekday())
            has_same_week_assignment = False
            for a in existing_assignments or []:
                if a.get("assigned_employee_id") == getattr(last_assigned, "pk", None):
                    sd = a.get("start_datetime")
                    if sd and week_start <= sd < (week_start + timedelta(days=7)):
                        has_same_week_assignment = True
                        break
            if has_same_week_assignment:
                assignment_day = (date - week_start).days
                if 0 <= assignment_day <= 4:  # Monday to Friday
                    return last_assigned

        # Select by fairness if no continuity preference
        # For standby, use a separate fairness calculator to keep counters independent
        if template.shift_type == ShiftType.INCIDENTS_STANDBY:
            standby_calc = IncidentsStandbyFairnessCalculator(
                date, date + timedelta(days=7),
            )
            # Build current assignments baseline
            current_assignments = standby_calc.calculate_current_assignments(
                shift_type_employees,
            )
            # Add provisional from existing_assignments
            if existing_assignments:
                provisional = standby_calc.calculate_provisional_assignments(
                    existing_assignments,
                )
                for emp_id, pdata in provisional.items():
                    if emp_id in current_assignments:
                        for key, val in pdata.items():
                            if key in current_assignments[emp_id] and isinstance(
                                val, (int, float),
                            ):
                                current_assignments[emp_id][key] += val
                            elif key not in current_assignments[emp_id]:
                                current_assignments[emp_id][key] = val
                    else:
                        current_assignments[emp_id] = pdata

            # Find candidates with min total hours
            min_hours = float("inf")
            candidates: list[User] = []
            for emp in shift_type_employees:
                data = current_assignments.get(emp.pk, {})
                total = data.get("total_hours", 0.0)
                if total < min_hours:
                    min_hours = total
                    candidates = [emp]
                elif total == min_hours:
                    candidates.append(emp)

            if len(candidates) == 1:
                return candidates[0]
            # Tie-break with rotating selection
            candidates.sort(key=lambda e: e.pk)
            idx = self._generation_assignment_count % len(candidates)
            self._generation_assignment_count += 1
            return candidates[idx]

        return self._select_employee_by_fairness(
            shift_type_employees, template.shift_type, existing_assignments,
        )

    def generate_business_week_assignments(
        self, week_start: datetime, dry_run: bool = False,
    ) -> dict:
        """Generate assignments for a complete business week (Monday-Friday).

        This is a convenience method for generating a single business week
        which is the natural unit for incidents orchestration.
        """
        # Ensure week_start is a Monday
        if week_start.weekday() != 0:
            # Adjust to the Monday of this week
            days_to_monday = week_start.weekday()
            week_start = week_start - timedelta(days=days_to_monday)

        # Business week ends Friday at 17:00
        week_end = week_start + timedelta(days=4, hours=17)
        week_start = week_start.replace(hour=8, minute=0, second=0, microsecond=0)

        return self.generate_assignments(week_start, week_end, dry_run=dry_run)

    def get_next_business_week_start(
        self, reference_date: datetime | None = None,
    ) -> datetime:
        """Get the start of the next business week (Monday 08:00) after the reference date.

        This is useful for scheduling the next incidents orchestration run.
        """
        if reference_date is None:
            tz = pytz.timezone("Europe/Amsterdam")
            reference_date = tz.localize(datetime.now())

        # Find next Monday
        days_until_monday = (7 - reference_date.weekday()) % 7
        if days_until_monday == 0 and reference_date.hour >= 8:
            # If it's Monday and past 8 AM, get next Monday
            days_until_monday = 7

        next_monday = reference_date + timedelta(days=days_until_monday)
        return next_monday.replace(hour=8, minute=0, second=0, microsecond=0)

    def get_current_business_week_range(
        self, reference_date: datetime | None = None,
    ) -> tuple[datetime, datetime]:
        """Get the current business week range (Monday 08:00 to Friday 17:00)."""
        if reference_date is None:
            tz = pytz.timezone("Europe/Amsterdam")
            reference_date = tz.localize(datetime.now())

        # Find Monday of current week
        days_to_monday = reference_date.weekday()
        week_start = reference_date - timedelta(days=days_to_monday)
        week_start = week_start.replace(hour=8, minute=0, second=0, microsecond=0)

        # Friday 17:00
        week_end = week_start + timedelta(
            days=4, hours=9,
        )  # +4 days, +9 hours from 08:00

        return week_start, week_end

    def __str__(self):
        """String representation of the orchestrator."""
        team_info = f" (Team {self.team_id})" if self.team_id else ""
        return f"IncidentsOrchestrator{team_info}"

    def __repr__(self):
        """Detailed representation of the orchestrator."""
        return f"IncidentsOrchestrator(team_id={self.team_id}, prioritize_standby={self.prioritize_standby})"
