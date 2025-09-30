"""
Base Orchestrator Class for Split Architecture

This module implements the foundation for Phase 1.2: Individual Orchestrators.
The BaseOrchestrator provides common orchestration functionality while allowing
specialized orchestrators for different shift types.

Architecture:
- BaseOrchestrator: Common orchestration patterns and constraint-first generation
- IncidentsOrchestrator: Monday-Friday business hours with constraint-first logic
- WaakdienstOrchestrator: Wednesday-Wednesday evening/weekend with constraint-first logic
"""

from abc import ABC
from abc import abstractmethod
from datetime import datetime
from datetime import timedelta
from typing import Any

from django.conf import settings
from django.db import models
from django.db import transaction

from team_planner.leaves.models import LeaveRequest
from team_planner.orchestrators.fairness_calculators import BaseFairnessCalculator
from team_planner.shifts.models import Shift
from team_planner.shifts.models import ShiftTemplate
from team_planner.users.models import User


class BaseOrchestrator(ABC):
    """Base orchestrator providing common orchestration functionality.

    This base class implements constraint-first generation where we check
    availability day-by-day before making assignments, eliminating the need
    for complex post-processing reassignment logic.

    Key principles:
    1. Day-by-day generation with continuity preference
    2. Constraint checking before assignment (not after)
    3. Shift-type specific fairness tracking
    4. Independent operation per orchestrator
    """

    def __init__(self, team_id: int | None = None):
        self.team_id = team_id
        self.fairness_calculator: BaseFairnessCalculator | None = None
        self._generation_assignment_count = (
            0  # Track assignments during current generation
        )

        # Configurable parameters
        self.max_consecutive_weeks = int(
            getattr(settings, "ORCHESTRATOR_MAX_CONSECUTIVE_WEEKS", 2),
        )
        self.min_rest_hours = int(getattr(settings, "ORCHESTRATOR_MIN_REST_HOURS", 48))
        self.continuity_preference_weight = float(
            getattr(settings, "ORCHESTRATOR_CONTINUITY_WEIGHT", 1.5),
        )

    @abstractmethod
    def _get_handled_shift_types(self) -> list[str]:
        """Return the shift types this orchestrator handles.
        Must be implemented by subclasses.
        """

    @abstractmethod
    def _get_rotation_start_weekday(self) -> int:
        """Return the weekday (0=Monday) when this orchestrator's rotation starts.
        Must be implemented by subclasses.
        """

    @abstractmethod
    def _get_shift_templates(self) -> list[ShiftTemplate]:
        """Return shift templates this orchestrator uses for generation.
        Must be implemented by subclasses.
        """

    @abstractmethod
    def _create_fairness_calculator(
        self, start_date: datetime, end_date: datetime,
    ) -> BaseFairnessCalculator:
        """Create the appropriate fairness calculator for this orchestrator.
        Must be implemented by subclasses.
        """

    def get_available_employees(self) -> list[User]:
        """Get employees available for this orchestrator's shift types."""
        query = User.objects.filter(
            is_active=True, employee_profile__status="active",
        ).select_related("employee_profile")

        # Filter by team if specified
        if self.team_id:
            query = query.filter(teams=self.team_id)

        employees = list(query)

        # Filter by shift type availability - subclasses can override this
        return self._filter_employees_by_availability(employees)

    def _filter_employees_by_availability(self, employees: list[User]) -> list[User]:
        """Filter employees by availability for this orchestrator's shift types.
        Base implementation uses skill-based filtering for handled shift types.
        """
        handled_shift_types = self._get_handled_shift_types()
        if not handled_shift_types:
            return employees

        available_employees = []
        for employee in employees:
            profile = getattr(employee, "employee_profile", None)
            if not profile:
                continue

            # Check if employee has skills for any of the handled shift types
            has_required_skill = False
            for shift_type in handled_shift_types:
                skill_name = shift_type.lower()
                if profile.skills.filter(name=skill_name).exists():
                    has_required_skill = True
                    break

            if has_required_skill:
                available_employees.append(employee)

        return available_employees

    def is_employee_available_on_date(self, employee: User, date: datetime) -> bool:
        """Check if an employee is available on a specific date.

        This is the core constraint checking method that eliminates the need
        for post-processing reassignment logic.
        """
        # Check for approved leave requests
        if self._has_approved_leave(employee, date):
            return False

        # Check for recurring leave patterns that affect this date
        if self._has_recurring_leave_conflict(employee, date):
            return False

        # Check for minimum rest between shifts
        if not self._has_sufficient_rest(employee, date):
            return False

        # Check for maximum consecutive weeks constraint
        return self._within_consecutive_weeks_limit(employee, date)

    def _has_approved_leave(self, employee: User, date: datetime) -> bool:
        """Check if employee has approved leave on this date."""
        date_obj = date.date()
        return LeaveRequest.objects.filter(
            employee=employee,
            status="approved",
            start_date__lte=date_obj,
            end_date__gte=date_obj,
        ).exists()

    def _has_recurring_leave_conflict(self, employee: User, date: datetime) -> bool:
        """Check if employee has recurring leave patterns affecting this date."""
        try:
            from team_planner.employees.models import RecurringLeavePattern

            # Get active patterns for this employee
            patterns = RecurringLeavePattern.objects.filter(
                employee=employee,
                is_active=True,
                effective_from__lte=date.date(),
            ).filter(
                models.Q(effective_until__isnull=True)
                | models.Q(effective_until__gte=date.date()),
            )

            return any(pattern.applies_to_date(date.date()) for pattern in patterns)
        except ImportError:
            # If RecurringLeavePattern doesn't exist, no conflict
            return False

    def _has_sufficient_rest(self, employee: User, date: datetime) -> bool:
        """Check if employee has sufficient rest before this assignment."""
        if self.min_rest_hours <= 0:
            return True

        # Check for recent shifts within min_rest_hours
        cutoff = date - timedelta(hours=self.min_rest_hours)

        recent_shifts = Shift.objects.filter(
            assigned_employee=employee,
            end_datetime__gte=cutoff,
            end_datetime__lt=date,
            template__shift_type__in=self._get_handled_shift_types(),
        )

        return not recent_shifts.exists()

    def _within_consecutive_weeks_limit(self, employee: User, date: datetime) -> bool:
        """Check if assigning this employee would exceed consecutive weeks limit."""
        if self.max_consecutive_weeks <= 0:
            return True

        # Find the start of the week for this date based on rotation
        rotation_start_weekday = self._get_rotation_start_weekday()
        week_start = self._get_week_start(date, rotation_start_weekday)

        # Count consecutive weeks backward
        consecutive_weeks = 0
        check_week_start = week_start

        while consecutive_weeks < self.max_consecutive_weeks:
            check_week_end = check_week_start + timedelta(days=7)

            # Check if employee worked during this week
            week_shifts = Shift.objects.filter(
                assigned_employee=employee,
                start_datetime__gte=check_week_start,
                start_datetime__lt=check_week_end,
                template__shift_type__in=self._get_handled_shift_types(),
            )

            if week_shifts.exists():
                consecutive_weeks += 1
                check_week_start -= timedelta(days=7)
            else:
                break

        return consecutive_weeks < self.max_consecutive_weeks

    def _get_week_start(self, date: datetime, start_weekday: int) -> datetime:
        """Get the start of the week for a given date and rotation start day."""
        days_since_start = (date.weekday() - start_weekday) % 7
        week_start = date - timedelta(days=days_since_start)
        return week_start.replace(hour=0, minute=0, second=0, microsecond=0)

    def generate_assignments(
        self, start_date: datetime, end_date: datetime, dry_run: bool = False,
    ) -> dict[str, Any]:
        """Generate shift assignments using constraint-first day-by-day logic.

        This is the main orchestration method that implements our new
        constraint-first approach instead of week-first with post-processing.
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

        # Generate day-by-day assignments
        assignments = []
        current_date = start_date
        last_assigned_employee: dict[
            str, User,
        ] = {}  # Track last assigned per shift type

        while current_date < end_date:
            # Generate assignments for this specific date
            daily_assignments = self._generate_assignments_for_date(
                current_date,
                employees,
                shift_templates,
                last_assigned_employee,
                assignments,
            )

            assignments.extend(daily_assignments)

            # Update continuity tracking
            for assignment in daily_assignments:
                shift_type = assignment["shift_type"]
                last_assigned_employee[shift_type] = assignment["assigned_employee"]

            current_date += timedelta(days=1)

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
            "employees_assigned": len(
                {a["assigned_employee_id"] for a in assignments},
            ),
            "errors": [],
            "fairness_metrics": fairness_metrics,
        }

    def _generate_day_by_day_assignments(
        self,
        start_date: datetime,
        end_date: datetime,
        employees: list[User],
        shift_templates: list[ShiftTemplate],
    ) -> list[dict]:
        """Generate assignments day by day with constraint checking and continuity preference.

        This method implements the core constraint-first logic that eliminates
        the need for complex post-processing reassignment.
        """
        assignments = []
        current_date = start_date
        last_assigned_employee = {}  # Track last assigned employee per shift type for continuity

        while current_date < end_date:
            # Generate assignments for this specific date
            daily_assignments = self._generate_assignments_for_date(
                current_date,
                employees,
                shift_templates,
                last_assigned_employee,
                assignments,
            )

            assignments.extend(daily_assignments)

            # Update continuity tracking
            for assignment in daily_assignments:
                shift_type = assignment["shift_type"]
                last_assigned_employee[shift_type] = assignment["assigned_employee"]

            current_date += timedelta(days=1)

        return assignments

    def _generate_assignments_for_date(
        self,
        date: datetime,
        employees: list[User],
        shift_templates: list[ShiftTemplate],
        last_assigned: dict[str, User],
        existing_assignments: list[dict],
    ) -> list[dict]:
        """Generate assignments for a specific date with constraint checking."""
        daily_assignments = []

        # Create a working copy of existing assignments to update during the day
        working_assignments = list(existing_assignments or [])

        for template in shift_templates:
            shift_type = template.shift_type

            # Check if we need a shift of this type on this date
            if not self._needs_shift_on_date(date, template):
                continue

            # Find the best employee for this shift with constraint checking
            # Use the working assignments list that includes assignments made earlier today
            assigned_employee = self._find_best_employee_for_shift(
                date,
                template,
                employees,
                last_assigned.get(shift_type),
                working_assignments,
            )

            if assigned_employee:
                # Calculate shift start and end times
                shift_start, shift_end = self._calculate_shift_times(date, template)

                assignment = {
                    "assigned_employee": assigned_employee,
                    "assigned_employee_id": assigned_employee.pk,
                    "shift_type": shift_type,
                    "template": template,
                    "start_datetime": shift_start,
                    "end_datetime": shift_end,
                    "duration_hours": (shift_end - shift_start).total_seconds() / 3600,
                    "auto_assigned": True,  # Mark as automatically assigned
                }

                daily_assignments.append(assignment)
                # Update working assignments to include this new assignment for subsequent selections
                working_assignments.append(assignment)

        return daily_assignments

    def _needs_shift_on_date(self, date: datetime, template: ShiftTemplate) -> bool:
        """Check if we need a shift of this template type on the given date.
        Base implementation returns True - subclasses should override for specific logic.
        """
        return True

    def _find_best_employee_for_shift(
        self,
        date: datetime,
        template: ShiftTemplate,
        employees: list[User],
        last_assigned: User | None,
        existing_assignments: list[dict],
    ) -> User | None:
        """Find the best employee for a shift with constraint checking and fairness-first selection."""
        available_employees = []

        # First pass: find all available employees
        for employee in employees:
            if self.is_employee_available_on_date(employee, date):
                available_employees.append(employee)

        if not available_employees:
            return None

        # Select based on fairness first - this ensures fair distribution
        selected_employee = self._select_employee_by_fairness(
            available_employees, template.shift_type, existing_assignments,
        )

        # Apply weak continuity preference if fairness scores are very close (within 5 points)
        # and not for incidents to ensure completely fair incident distribution
        if (
            last_assigned
            and last_assigned in available_employees
            and template.shift_type not in ["incidents"]
            and selected_employee
        ):
            # Get fairness scores for comparison
            current_assignments = (
                self.fairness_calculator.calculate_current_assignments(
                    available_employees,
                )
                if self.fairness_calculator
                else {}
            )
            if existing_assignments:
                provisional_assignments = (
                    self.fairness_calculator.calculate_provisional_assignments(
                        existing_assignments,
                    )
                    if self.fairness_calculator
                    else {}
                )
                # Merge historical and provisional
                for emp_id, provisional_data in provisional_assignments.items():
                    if emp_id in current_assignments:
                        for key, value in provisional_data.items():
                            if key in current_assignments[emp_id] and isinstance(
                                value, (int, float),
                            ):
                                current_assignments[emp_id][key] += value
                    else:
                        current_assignments[emp_id] = provisional_data

            fairness_scores = (
                self.fairness_calculator.calculate_fairness_score(current_assignments)
                if self.fairness_calculator
                else {}
            )

            last_assigned_score = fairness_scores.get(last_assigned.pk, 0.0)
            selected_score = fairness_scores.get(selected_employee.pk, 0.0)

            # Only prefer continuity if scores are very close (within 5 points)
            if abs(last_assigned_score - selected_score) <= 5.0:
                return last_assigned

        return selected_employee

    def _select_employee_by_fairness(
        self,
        employees: list[User],
        shift_type: str,
        existing_assignments: list[dict] | None = None,
    ) -> User | None:
        """Select employee based on fairness - prioritizing those with lowest workload.

        Uses total assigned hours to ensure fair distribution. Lower hours = higher priority.
        When workloads are equal, uses employee ID for consistent ordering.
        """
        if not employees:
            return None

        if not self.fairness_calculator:
            # Without fairness calculator, use simple round-robin by ID
            employees.sort(key=lambda emp: emp.pk)
            return employees[0]

        # Calculate current workload including provisional assignments
        if existing_assignments:
            # Get historical assignments for all employees
            current_assignments = (
                self.fairness_calculator.calculate_current_assignments(employees)
            )

            # Add provisional assignments from current generation
            provisional_assignments = (
                self.fairness_calculator.calculate_provisional_assignments(
                    existing_assignments,
                )
            )

            # Merge historical and provisional assignments
            for emp_id, provisional_data in provisional_assignments.items():
                if emp_id in current_assignments:
                    # Add provisional hours to existing assignments
                    for key, value in provisional_data.items():
                        if key in current_assignments[emp_id] and isinstance(
                            value, (int, float),
                        ):
                            current_assignments[emp_id][key] += value
                        elif key not in current_assignments[emp_id]:
                            current_assignments[emp_id][key] = value
                else:
                    current_assignments[emp_id] = provisional_data
        else:
            # Use historical assignments only (this now includes all employees with 0 hours if no history)
            current_assignments = (
                self.fairness_calculator.calculate_current_assignments(employees)
            )

        # Find employees with lowest total hours (most fair = least assigned)
        min_hours = float("inf")
        best_candidates = []

        for employee in employees:
            emp_data = current_assignments.get(employee.pk, {})
            total_hours = emp_data.get("total_hours", 0.0)

            if total_hours < min_hours:
                min_hours = total_hours
                best_candidates = [employee]  # New minimum, reset candidates
            elif total_hours == min_hours:
                best_candidates.append(employee)  # Tie, add to candidates

        # If there's only one candidate, return it
        if len(best_candidates) == 1:
            return best_candidates[0]

        # Break ties using rotating selection for better distribution
        if len(best_candidates) > 1:
            # Use generation assignment count for consistent rotation across entire generation
            # This ensures fair distribution from the start when all employees have equal hours

            # Sort by ID for consistent order, then select based on generation-wide rotation
            best_candidates.sort(key=lambda emp: emp.pk)
            selected_index = self._generation_assignment_count % len(best_candidates)

            # Increment generation counter for next selection
            self._generation_assignment_count += 1

            return best_candidates[selected_index]

        return best_candidates[0] if best_candidates else employees[0]

    def _calculate_shift_times(
        self, date: datetime, template: ShiftTemplate,
    ) -> tuple[datetime, datetime]:
        """Calculate start and end times for a shift on a given date.
        Base implementation - subclasses should override for specific timing logic.
        """
        # Default: 8-hour shift starting at 8 AM
        start_time = date.replace(hour=8, minute=0, second=0, microsecond=0)
        end_time = start_time + timedelta(hours=template.duration_hours or 8)
        return start_time, end_time

    def _calculate_assignment_fairness(
        self, assignments: list[dict], employees: list[User],
    ) -> dict[str, Any]:
        """Calculate fairness metrics for generated assignments."""
        if not self.fairness_calculator:
            return {}

        # Convert assignments to format expected by fairness calculator
        in_memory_assignments = []
        for assignment in assignments:
            in_memory_assignments.append(
                {
                    "assigned_employee_id": assignment["assigned_employee_id"],
                    "shift_type": assignment["shift_type"],
                    "start_datetime": assignment["start_datetime"],
                    "end_datetime": assignment["end_datetime"],
                    "auto_assigned": assignment.get("auto_assigned", True),
                },
            )

        # Calculate provisional fairness
        provisional_assignments = (
            self.fairness_calculator.calculate_provisional_assignments(
                in_memory_assignments,
            )
        )
        fairness_scores = self.fairness_calculator.calculate_fairness_score(
            provisional_assignments,
        )

        # Calculate summary statistics
        scores = list(fairness_scores.values())
        if scores:
            avg_fairness = sum(scores) / len(scores)
            min_fairness = min(scores)
            max_fairness = max(scores)
        else:
            avg_fairness = min_fairness = max_fairness = 0.0

        return {
            "fairness_scores": fairness_scores,
            "average_fairness": round(avg_fairness, 2),
            "min_fairness": round(min_fairness, 2),
            "max_fairness": round(max_fairness, 2),
            "total_assignments": len(assignments),
        }

    def _save_orchestration_results(
        self,
        start_date: datetime,
        end_date: datetime,
        assignments: list[dict],
        fairness_metrics: dict[str, Any],
    ):
        """Save orchestration results to database."""
        try:
            with transaction.atomic():
                # Just create the shift assignments - skip the complex orchestration tracking for now
                created_shifts = []
                for assignment in assignments:
                    shift = Shift.objects.create(
                        template=assignment["template"],
                        assigned_employee=assignment["assigned_employee"],
                        start_datetime=assignment["start_datetime"],
                        end_datetime=assignment["end_datetime"],
                        auto_assigned=assignment.get("auto_assigned", True),
                    )
                    created_shifts.append(shift)

                return created_shifts

        except Exception:
            # Log error but don't fail the entire generation
            import traceback

            traceback.print_exc()
            return None
