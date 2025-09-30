"""
Incidents Orchestrator for Split Orchestrator System

This module provides the IncidentsOrchestrator class that handles incidents shift
scheduling using a sophisticated week-long assignment strategy. It inherits from
BaseOrchestrator but overrides the assignment logic to ensure the same engineer
works the entire week, with day-level reassignment only for conflicts.
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


class IncidentsOrchestrator(BaseOrchestrator):
    """
    Orchestrator for incidents shifts using week-long assignment strategy.

    This orchestrator implements sophisticated week-long assignment logic where
    the same engineer works the entire week, with day-level reassignment only
    for unavoidable conflicts (leave, other shifts).
    """

    def __init__(
        self, start_date: datetime, end_date: datetime, team_id: int | None = None,
    ):
        """Initialize the incidents orchestrator."""
        super().__init__(start_date, end_date, team_id)

    def _get_handled_shift_types(self) -> list[str]:
        """Return shift types handled by this orchestrator."""
        return [ShiftType.INCIDENTS]

    def _create_fairness_calculator(self) -> BaseFairnessCalculator:
        """Create incidents fairness calculator for this period."""
        return FairnessCalculatorFactory.create_incidents_calculator(
            self.start_date, self.end_date,
        )

    def _create_constraint_checker(self) -> BaseConstraintChecker:
        """Create incidents constraint checker."""
        return ConstraintCheckerFactory.create_incidents_checker(
            self.start_date, self.end_date,
        )

    def _generate_time_periods(self) -> list[tuple[datetime, datetime, str]]:
        """Generate business week periods (Monday-Friday) for incidents."""
        periods = []
        current = self.start_date

        while current < self.end_date:
            # Find Monday of this week
            monday = current - timedelta(days=current.weekday())
            # Ensure we don't go before start_date
            week_start = max(monday, self.start_date)
            # Friday of this week
            week_end = min(monday + timedelta(days=4, hours=17), self.end_date)

            if week_start < week_end:
                periods.append(
                    (week_start, week_end, f"Week {week_start.strftime('%Y-%m-%d')}"),
                )

            # Move to next Monday
            current = monday + timedelta(days=7)

        return periods

    def _get_available_employees(self) -> list[Any]:
        """Get employees available for incidents shifts."""
        return list(
            User.objects.filter(
                is_active=True,
                employee_profile__status=EmployeeProfile.Status.ACTIVE,
                employee_profile__available_for_incidents=True,
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
        Override BaseOrchestrator to implement week-long assignment logic for incidents.

        Strategy: Prefer same engineer for entire week, but reassign only individual
        conflicted days to maintain week-long assignment principle.
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
        
        # Ensure all employees have total_hours field for sorting
        for emp in available_employees:
            if emp.pk not in current_assignments:
                current_assignments[emp.pk] = {"incidents": 0.0, "total_hours": 0.0}
            elif "total_hours" not in current_assignments[emp.pk]:
                # Calculate total_hours from all shift types
                emp_data = current_assignments[emp.pk]
                total = sum(emp_data.get(shift_type, 0.0) for shift_type in ["incidents", "incidents_standby", "waakdienst"])
                current_assignments[emp.pk]["total_hours"] = total

        # Add assignments already made in THIS orchestration run to the fairness calculation
        for assignment in self.current_assignments:
            emp_id = assignment.get("assigned_employee_id")
            shift_type = assignment.get("shift_type", "").lower()
            duration_hours = assignment.get("duration_hours", 0.0)

            if (
                emp_id
                and emp_id in [emp.pk for emp in available_employees]
                and shift_type == "incidents"
            ):
                if emp_id not in current_assignments:
                    current_assignments[emp_id] = {"incidents": 0.0, "total_hours": 0.0}
                current_assignments[emp_id]["incidents"] += duration_hours
                # CRITICAL: Also update total_hours for fairness sorting
                if "total_hours" not in current_assignments[emp_id]:
                    current_assignments[emp_id]["total_hours"] = 0.0
                current_assignments[emp_id]["total_hours"] += duration_hours

        # Check each employee's availability for this specific week
        employee_availability = {}

        for emp in available_employees:
            # Check partial availability for the week
            daily_shifts[0][0]
            daily_shifts[-1][1]

            # Get conflicts for this employee during the week
            conflicts = []
            available_days = 0
            total_possible_hours = 0.0
            available_hours = 0.0

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
            # Simple but effective fairness: sort by total hours worked, pick least loaded
            def get_total_hours(emp):
                emp_data = current_assignments.get(emp.pk, {})
                current_total = emp_data.get("total_hours", 0.0)
                # Use incidents hours from new_assignments for this type
                new_incidents = new_assignments[emp.pk].get("incidents", 0.0)
                return current_total + new_incidents

            fully_available.sort(key=get_total_hours)
            chosen_employee = fully_available[0]
            
            # FIXED: Actually create assignments for the chosen employee
            for day_start, day_end, day_label in daily_shifts:
                duration_hours = (day_end - day_start).total_seconds() / 3600.0
                
                # Get the template for incidents shifts
                template = self._get_shift_template("incidents")
                
                assignment = {
                    "assigned_employee_id": chosen_employee.pk,
                    "assigned_employee_name": chosen_employee.get_full_name() or chosen_employee.username,
                    "start_datetime": day_start,
                    "end_datetime": day_end,
                    "shift_type": "incidents",
                    "duration_hours": duration_hours,
                    "assignment_reason": f"Week-long assignment ({period_label}) - {day_label}",
                    "template": template,  # Add actual template object
                    "template_id": template.pk if template else None,
                    "template_name": "Incidents Daily Shift",
                    "auto_assigned": True,
                }
                assignments.append(assignment)
                
                # CRITICAL: Add to self.current_assignments so it's seen by next week's fairness calc
                self.current_assignments.append(assignment)
                
                # Track for fairness in local tracking
                new_assignments[chosen_employee.pk]["incidents"] += duration_hours
            
            logger.info(f"Assigned {chosen_employee.username} to full week {period_label}")

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

    def _select_employee_by_enhanced_fairness(
        self,
        eligible_employees: list[Any],
        current_assignments: dict,
        new_assignments: dict,
        shift_type: str,
    ) -> Any:
        """Enhanced fairness-based employee selection that actively minimizes inequality.
        
        Uses multiple fairness criteria:
        1. Primary: Fairness score after proposed assignment  
        2. Secondary: Load balancing to avoid clustering
        3. Tertiary: Total workload distribution
        """
        if not eligible_employees:
            raise ValueError("No eligible employees provided")
            
        if len(eligible_employees) == 1:
            return eligible_employees[0]
        
        # Calculate enhanced fairness metrics for each employee
        best_employee = None
        best_score = float('-inf')
        
        # Estimate hours for this assignment (standard incidents week)
        shift_hours = 45.0  # Standard incidents week
        
        for employee in eligible_employees:
            # Get current state
            emp_current = current_assignments.get(
                employee.pk, 
                {"incidents": 0.0, "incidents_standby": 0.0, "waakdienst": 0.0, "total_hours": 0.0}
            )
            emp_new = new_assignments[employee.pk]
            
            # Calculate proposed total after this assignment
            proposed_current = emp_current[shift_type.lower()] + emp_new[shift_type.lower()]
            proposed_total = emp_current.get("total_hours", 0.0) + emp_new.get("total_hours", 0.0)
            
            # Simulate assignment to calculate fairness impact
            projected_assignments = {}
            for emp_id, data in current_assignments.items():
                if emp_id == employee.pk:
                    # Add proposed assignment
                    projected_assignments[emp_id] = dict(data)
                    projected_assignments[emp_id][shift_type.lower()] = proposed_current + shift_hours
                    projected_assignments[emp_id]["total_hours"] = proposed_total + shift_hours
                    # Ensure availability info is present
                    projected_assignments[emp_id]["available_hours_per_week"] = data.get("available_hours_per_week", 45.0)
                    projected_assignments[emp_id]["availability_percentage"] = data.get("availability_percentage", 100.0)
                else:
                    projected_assignments[emp_id] = dict(data)
                    # Ensure availability info is present for all employees
                    projected_assignments[emp_id]["available_hours_per_week"] = data.get("available_hours_per_week", 45.0)
                    projected_assignments[emp_id]["availability_percentage"] = data.get("availability_percentage", 100.0)
            
            # Calculate fairness scores for this scenario
            fairness_scores = self.fairness_calculator.calculate_fairness_score(projected_assignments)
            
            # Enhanced scoring with multiple factors
            emp_fairness = fairness_scores.get(employee.pk, 0.0)
            
            # Factor 1: Individual fairness improvement (primary weight: 60%)
            individual_score = emp_fairness * 0.6
            
            # Factor 2: System-wide fairness improvement (secondary weight: 25%)
            avg_fairness = sum(fairness_scores.values()) / len(fairness_scores)
            std_deviation = (sum((s - avg_fairness) ** 2 for s in fairness_scores.values()) / len(fairness_scores)) ** 0.5
            system_score = (100 - std_deviation) * 0.25  # Lower deviation = better
            
            # Factor 3: Load balancing bonus (tertiary weight: 15%)
            total_assigned = sum(data.get("total_hours", 0) for data in current_assignments.values())
            if total_assigned > 0:
                current_load_ratio = emp_current.get("total_hours", 0) / total_assigned
                balance_bonus = (1.0 - min(current_load_ratio, 1.0)) * 15.0  # Bonus for under-loaded
            else:
                balance_bonus = 15.0  # Full bonus if no prior assignments
            
            # Combined enhanced score
            enhanced_score = individual_score + system_score + balance_bonus
            
            if enhanced_score > best_score:
                best_score = enhanced_score
                best_employee = employee
        
        return best_employee or eligible_employees[0]

    def _select_employee_by_simple_fairness(
        self,
        eligible_employees: list[Any],
        current_assignments: dict,
        new_assignments: dict,
        shift_type: str,
    ) -> Any:
        """Simple but effective fairness-based employee selection."""
        if not eligible_employees:
            raise ValueError("No eligible employees provided")
            
        if len(eligible_employees) == 1:
            return eligible_employees[0]
        
        # Sort by total workload (least loaded first) 
        def fairness_sort_key(emp):
            emp_current = current_assignments.get(emp.pk, {})
            total_current = emp_current.get("total_hours", 0.0)
            
            # Add any new assignments made in this run
            emp_new = new_assignments[emp.pk]
            total_new = sum(emp_new.values())
            
            return total_current + total_new

        eligible_employees.sort(key=fairness_sort_key)
        return eligible_employees[0]

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
                current_assignments.get(emp.pk, {}).get("incidents", 0.0)
                + new_assignments[emp.pk]["incidents"]
            )
            # Sort by availability first, then fairness
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
                new_assignments[primary_employee.pk]["incidents"] += hours

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
                current_assignments.get(emp.pk, {}).get("incidents", 0.0)
                + new_assignments[emp.pk]["incidents"]
            )

        available_for_day.sort(key=fairness_sort_key)
        coverage_employee = available_for_day[0]

        logger.info(f"Coverage for {label}: {coverage_employee.username}")

        # Create assignment and track fairness
        assignment = self._create_day_assignment(
            coverage_employee, start_datetime, end_datetime, label,
        )
        hours = (end_datetime - start_datetime).total_seconds() / 3600.0
        new_assignments[coverage_employee.pk]["incidents"] += hours

        return assignment
