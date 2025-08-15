"""
Incidents Orchestrator for Split Orchestrator System

This module provides the IncidentsOrchestrator class that handles incidents shift
scheduling using a sophisticated week-long assignment strategy. It inherits from
BaseOrchestrator but overrides the assignment logic to ensure the same engineer
works the entire week, with day-level reassignment only for conflicts.
"""
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple, Optional
import logging

from django.contrib.auth import get_user_model
from django.utils import timezone

from team_planner.shifts.models import ShiftType
from team_planner.employees.models import EmployeeProfile
from team_planner.orchestrators.base import BaseOrchestrator
from team_planner.orchestrators.algorithms import ConstraintChecker, FairnessCalculator

User = get_user_model()
logger = logging.getLogger(__name__)


class IncidentsOrchestrator(BaseOrchestrator):
    """
    Orchestrator for incidents shifts using week-long assignment strategy.
    
    This orchestrator implements sophisticated week-long assignment logic where
    the same engineer works the entire week, with day-level reassignment only
    for unavoidable conflicts (leave, other shifts).
    """
    
    def __init__(self, start_date: datetime, end_date: datetime, team_id: Optional[int] = None):
        """Initialize the incidents orchestrator."""
        super().__init__(start_date, end_date, team_id)
    
    def _get_handled_shift_types(self) -> List[str]:
        """Return shift types handled by this orchestrator."""
        return [ShiftType.INCIDENTS]
    
    def _create_fairness_calculator(self):
        """Create incidents fairness calculator for this period."""
        # Return the instance directly since BaseOrchestrator expects it
        return FairnessCalculator(self.start_date, self.end_date)
    
    def _create_constraint_checker(self):
        """Create incidents constraint checker."""
        # Return the instance directly since BaseOrchestrator expects it
        return ConstraintChecker(self.start_date, self.end_date, self.team_id)
    
    def _generate_time_periods(self) -> List[Tuple[datetime, datetime, str]]:
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
                periods.append((week_start, week_end, f"Week {week_start.strftime('%Y-%m-%d')}"))
            
            # Move to next Monday
            current = monday + timedelta(days=7)
        
        return periods
    
    def _get_available_employees(self) -> List[Any]:
        """Get employees available for incidents shifts."""
        return list(User.objects.filter(
            is_active=True,
            employee_profile__status=EmployeeProfile.Status.ACTIVE,
            employee_profile__available_for_incidents=True
        ).select_related('employee_profile'))
    
    def _generate_daily_shifts(self, period_start: datetime, period_end: datetime, 
                             period_label: str) -> List[Tuple[datetime, datetime, str]]:
        """Generate daily shifts for Monday-Friday business days."""
        daily_shifts = []
        current = period_start
        
        while current < period_end:
            # Only Monday-Friday (weekdays 0-4)
            if current.weekday() < 5:
                day_start = current.replace(hour=8, minute=0, second=0, microsecond=0)
                day_end = current.replace(hour=17, minute=0, second=0, microsecond=0)
                
                # Ensure we don't go beyond period_end
                if day_start < period_end:
                    actual_end = min(day_end, period_end)
                    daily_shifts.append((day_start, actual_end, f"{current.strftime('%A %Y-%m-%d')}"))
            
            # Move to next day
            current += timedelta(days=1)
        
        return daily_shifts

    def _generate_period_assignments(self, period_start: datetime, period_end: datetime, 
                                   period_label: str, available_employees: List[Any]) -> List[Dict]:
        """
        Override BaseOrchestrator to implement week-long assignment logic for incidents.
        
        Strategy: Prefer same engineer for entire week, but reassign only individual 
        conflicted days to maintain week-long assignment principle.
        """
        from collections import defaultdict
        
        assignments = []
        
        # Get daily shifts for this period (Monday-Friday business week)
        daily_shifts = self._generate_daily_shifts(period_start, period_end, period_label)
        
        if not daily_shifts:
            return assignments
        
        # Track assignments made in this run for fairness
        new_assignments = defaultdict(lambda: {'incidents': 0.0, 'incidents_standby': 0.0, 'waakdienst': 0.0})
        
        # Get current assignments for fairness calculation
        current_assignments = self.fairness_calculator.calculate_current_assignments(available_employees)
        
        # Check each employee's availability for this specific week
        employee_availability = {}
        constraint_checker = ConstraintChecker(period_start, period_end)
        
        for emp in available_employees:
            # Check partial availability for the week
            week_start = daily_shifts[0][0]
            week_end = daily_shifts[-1][1]
            
            # Get conflicts for this employee during the week
            conflicts = []
            available_days = 0
            total_possible_hours = 0.0
            available_hours = 0.0
            
            for day_start, day_end, day_label in daily_shifts:
                day_date = day_start.date()
                day_hours = (day_end - day_start).total_seconds() / 3600.0
                total_possible_hours += day_hours
                
                # Check if employee is available for this day
                if constraint_checker.is_employee_available(emp, day_start, day_end, ShiftType.INCIDENTS):
                    available_days += 1
                    available_hours += day_hours
                else:
                    conflicts.append(day_label)
            
            # Store availability info for this employee
            employee_availability[emp.pk] = {
                'available_days': available_days,
                'total_days': len(daily_shifts),
                'conflicts': conflicts,
                'available_hours': available_hours,
                'total_possible_hours': total_possible_hours,
                'availability_ratio': available_hours / total_possible_hours if total_possible_hours > 0 else 0.0
            }
        
        # Separate employees into fully vs partially available
        fully_available = []
        partially_available = []
        
        for emp in available_employees:
            availability = employee_availability.get(emp.pk, {})
            if availability.get('availability_ratio', 0) >= 1.0:
                fully_available.append(emp)
            elif availability.get('availability_ratio', 0) > 0:
                partially_available.append(emp)
        
        logger.info(f"Week {period_label}: {len(fully_available)} fully available, {len(partially_available)} partially available")
        
        # Strategy 1: Try to assign entire week to a fully available employee
        if fully_available:
            # Sort by fairness (least assigned first)
            def sort_key(emp):
                return current_assignments.get(emp.pk, {}).get('incidents', 0.0) + new_assignments[emp.pk]['incidents']
            
            fully_available.sort(key=sort_key)
            chosen_employee = fully_available[0]
            
            logger.info(f"Assigning entire week {period_label} to {chosen_employee.username} (fully available)")
            
            # Assign all days to this employee
            for day_start, day_end, day_label in daily_shifts:
                assignment = self._create_day_assignment(chosen_employee, day_start, day_end, day_label)
                assignments.append(assignment)
                
                # Track for fairness
                hours = (day_end - day_start).total_seconds() / 3600.0
                new_assignments[chosen_employee.pk]['incidents'] += hours
        
        # Strategy 2: Assign to partially available employees with coverage for conflicts
        elif partially_available:
            assignments.extend(self._assign_partial_week_with_coverage(
                daily_shifts, partially_available, available_employees, 
                current_assignments, new_assignments, employee_availability
            ))
        
        # Strategy 3: No one available - log warning  
        else:
            logger.warning(f"No employees available for week {period_label}")
        
        return assignments
    
    def _assign_partial_week_with_coverage(self, daily_shifts, partially_available, 
                                         all_employees, current_assignments, new_assignments, employee_availability):
        """Assign week-long assignment with day-level reassignment for conflicts only."""
        assignments = []
        
        if not partially_available:
            return assignments
        
        # Pick the most available employee as primary
        def availability_sort_key(emp):
            availability = employee_availability.get(emp.pk, {})
            fairness = current_assignments.get(emp.pk, {}).get('incidents', 0.0) + new_assignments[emp.pk]['incidents']
            # Sort by availability first, then fairness
            return (-availability.get('availability_ratio', 0), fairness)
        
        partially_available.sort(key=availability_sort_key)
        primary_employee = partially_available[0]
        
        logger.info(f"Using {primary_employee.username} as primary for partial week (conflicts: {employee_availability[primary_employee.pk]['conflicts']})")
        
        # Assign primary employee to all non-conflicted days
        for day_start, day_end, day_label in daily_shifts:
            if day_label not in employee_availability[primary_employee.pk]['conflicts']:
                assignment = self._create_day_assignment(primary_employee, day_start, day_end, day_label)
                assignments.append(assignment)
                
                # Track for fairness
                hours = (day_end - day_start).total_seconds() / 3600.0
                new_assignments[primary_employee.pk]['incidents'] += hours
        
        # Find coverage for conflicted days
        for day_start, day_end, day_label in daily_shifts:
            if day_label in employee_availability[primary_employee.pk]['conflicts']:
                coverage_assignment = self._find_day_coverage(
                    day_start, day_end, day_label, all_employees, 
                    current_assignments, new_assignments
                )
                if coverage_assignment:
                    assignments.append(coverage_assignment)
        
        return assignments
    
    def _find_day_coverage(self, start_datetime, end_datetime, label, all_employees,
                          current_assignments, new_assignments):
        """Find coverage for a single conflicted day."""
        constraint_checker = ConstraintChecker(start_datetime, end_datetime)
        
        # Find available employees for this specific day
        available_for_day = []
        for emp in all_employees:
            if constraint_checker.is_employee_available(emp, start_datetime, end_datetime, ShiftType.INCIDENTS):
                available_for_day.append(emp)
        
        if not available_for_day:
            logger.warning(f"No coverage available for {label}")
            return None
        
        # Sort by fairness (least assigned first)
        def fairness_sort_key(emp):
            return current_assignments.get(emp.pk, {}).get('incidents', 0.0) + new_assignments[emp.pk]['incidents']
        
        available_for_day.sort(key=fairness_sort_key)
        coverage_employee = available_for_day[0]
        
        logger.info(f"Coverage for {label}: {coverage_employee.username}")
        
        # Create assignment and track fairness
        assignment = self._create_day_assignment(coverage_employee, start_datetime, end_datetime, label)
        hours = (end_datetime - start_datetime).total_seconds() / 3600.0
        new_assignments[coverage_employee.pk]['incidents'] += hours
        
        return assignment
