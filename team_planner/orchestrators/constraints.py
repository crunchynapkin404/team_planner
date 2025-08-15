"""
Split Constraint Checkers for Orchestrator System

This module provides specialized constraint checkers for each shift type,
enabling day-by-day availability checking with focus on their specific time ranges.

Each checker focuses on its relevant time periods:
- IncidentsConstraintChecker: Monday-Friday 08:00-17:00 business hours
- WaakdienstConstraintChecker: Evening/weekend coverage periods

This enables constraint-first generation approach where each day is checked
individually before assignment, preventing conflicts at generation time.
"""
from datetime import datetime, date, time, timedelta
from typing import List, Optional, Set, Dict, Any
import logging
from dataclasses import dataclass

from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models import Q

from team_planner.shifts.models import Shift, ShiftType
from team_planner.employees.models import EmployeeProfile, RecurringLeavePattern
from team_planner.leaves.models import LeaveRequest

User = get_user_model()
logger = logging.getLogger(__name__)


@dataclass
class AvailabilityResult:
    """Result of availability check for an employee on a specific date."""
    is_available: bool
    reason: str = ""
    conflicting_leave: Optional[Any] = None
    conflicting_shift: Optional[Any] = None


class BaseConstraintChecker:
    """Base class for all constraint checkers with common functionality."""
    
    def __init__(self, start_date: datetime, end_date: datetime):
        self.start_date = start_date
        self.end_date = end_date
    
    def _get_shift_types(self) -> List[str]:
        """Return the shift types this checker handles. Override in subclasses."""
        raise NotImplementedError("Subclasses must implement _get_shift_types")
    
    def _get_relevant_time_range(self) -> tuple[time, time]:
        """Return the time range this checker cares about. Override in subclasses."""
        raise NotImplementedError("Subclasses must implement _get_relevant_time_range")
    
    def _get_relevant_days(self) -> List[int]:
        """Return the weekdays this checker cares about (0=Monday, 6=Sunday). Override in subclasses."""
        raise NotImplementedError("Subclasses must implement _get_relevant_days")
    
    def is_employee_available_for_shift_type(self, employee: Any) -> bool:
        """Check if employee is available for this checker's shift types via skills."""
        try:
            profile = employee.employee_profile
            shift_types = self._get_shift_types()
            
            if ShiftType.INCIDENTS in shift_types:
                return profile.skills.filter(name='incidents', is_active=True).exists()
            elif ShiftType.WAAKDIENST in shift_types:
                return profile.skills.filter(name='waakdienst', is_active=True).exists()
            else:
                # For other shift types, assume available if profile exists
                return True
                
        except AttributeError:
            # No employee profile - check if admin user
            logger.warning(f"Employee {employee.username} has no employee_profile")
            return getattr(employee, 'is_superuser', False)
    
    def check_approved_leave_conflicts(self, employee: Any, check_date: date) -> AvailabilityResult:
        """Check if employee has approved leave on this date."""
        # Convert date to datetime range for comparison
        day_start = timezone.make_aware(datetime.combine(check_date, time.min))
        day_end = timezone.make_aware(datetime.combine(check_date, time.max))
        
        # Check for approved leave requests that overlap with this date
        conflicting_leaves = LeaveRequest.objects.filter(
            employee=employee,
            status=LeaveRequest.Status.APPROVED,
            start_date__lte=check_date,
            end_date__gte=check_date
        )
        
        if conflicting_leaves.exists():
            leave = conflicting_leaves.first()
            if leave:  # Add null check for type safety
                return AvailabilityResult(
                    is_available=False,
                    reason=f"Approved leave: {leave.leave_type.name}",
                    conflicting_leave=leave
                )
        
        return AvailabilityResult(is_available=True)
    
    def check_existing_shift_conflicts(self, employee: Any, check_date: date) -> AvailabilityResult:
        """Check if employee already has shifts assigned on this date."""
        day_start = timezone.make_aware(datetime.combine(check_date, time.min))
        day_end = timezone.make_aware(datetime.combine(check_date, time.max))
        
        # Check for existing shifts on this date
        conflicting_shifts = Shift.objects.filter(
            assigned_employee=employee,
            start_datetime__date=check_date,
            status__in=[Shift.Status.SCHEDULED, Shift.Status.CONFIRMED]
        )
        
        if conflicting_shifts.exists():
            shift = conflicting_shifts.first()
            if shift:  # Add null check for type safety
                return AvailabilityResult(
                    is_available=False,
                    reason=f"Already assigned: {shift.template.name}",
                    conflicting_shift=shift
                )
        
        return AvailabilityResult(is_available=True)
    
    def check_employee_availability(self, employee: Any, check_date: date) -> AvailabilityResult:
        """
        Check if employee is available for assignment on a specific date.
        This is the main method that orchestrators should call.
        """
        # First check basic profile availability for this shift type
        if not self.is_employee_available_for_shift_type(employee):
            shift_types_str = ", ".join(self._get_shift_types())
            return AvailabilityResult(
                is_available=False,
                reason=f"Not available for {shift_types_str} in profile"
            )
        
        # Check if this day is relevant for this checker
        if check_date.weekday() not in self._get_relevant_days():
            return AvailabilityResult(
                is_available=False,
                reason=f"Not a relevant day for this shift type"
            )
        
        # Check approved leave
        leave_result = self.check_approved_leave_conflicts(employee, check_date)
        if not leave_result.is_available:
            return leave_result
        
        # Check existing shifts
        shift_result = self.check_existing_shift_conflicts(employee, check_date)
        if not shift_result.is_available:
            return shift_result
        
        # Check recurring leave patterns
        pattern_result = self.check_recurring_leave_conflicts(employee, check_date)
        if not pattern_result.is_available:
            return pattern_result
        
        return AvailabilityResult(is_available=True, reason="Available")
    
    def check_recurring_leave_conflicts(self, employee: Any, check_date: date) -> AvailabilityResult:
        """Check recurring leave patterns. Override in subclasses for specific time checking."""
        raise NotImplementedError("Subclasses must implement check_recurring_leave_conflicts")
    
    def get_available_employees(self, employees: List[Any], check_date: date) -> List[Any]:
        """Get all employees available for assignment on a specific date."""
        available = []
        
        for employee in employees:
            result = self.check_employee_availability(employee, check_date)
            if result.is_available:
                available.append(employee)
            else:
                logger.debug(f"Employee {employee.username} not available on {check_date}: {result.reason}")
        
        return available
    
    def get_unavailable_employees_with_reasons(self, employees: List[Any], check_date: date) -> Dict[Any, str]:
        """Get all employees that are unavailable with their reasons."""
        unavailable = {}
        
        for employee in employees:
            result = self.check_employee_availability(employee, check_date)
            if not result.is_available:
                unavailable[employee] = result.reason
        
        return unavailable


class IncidentsConstraintChecker(BaseConstraintChecker):
    """Constraint checker specifically for Incidents shifts (Monday-Friday 08:00-17:00)."""
    
    def _get_shift_types(self) -> List[str]:
        return [ShiftType.INCIDENTS]
    
    def _get_relevant_time_range(self) -> tuple[time, time]:
        """Business hours: 08:00-17:00."""
        return (time(8, 0), time(17, 0))
    
    def _get_relevant_days(self) -> List[int]:
        """Monday-Friday: 0-4."""
        return [0, 1, 2, 3, 4]  # Monday-Friday
    
    def check_recurring_leave_conflicts(self, employee: Any, check_date: date) -> AvailabilityResult:
        """Check recurring leave patterns that affect business hours on weekdays."""
        # RECURRING LEAVE REASSIGNMENT FIX:
        # Always allow assignments for incidents - conflicts will be resolved by reassignment manager
        # This ensures employees with recurring leave patterns are not excluded entirely from incidents shifts
        logger.debug(f"Allowing incidents assignment for {employee.username} on {check_date} - conflicts will be handled by reassignment")
        return AvailabilityResult(is_available=True)


class WaakdienstConstraintChecker(BaseConstraintChecker):
    """Constraint checker specifically for Waakdienst shifts (evening/weekend coverage)."""
    
    def _get_shift_types(self) -> List[str]:
        return [ShiftType.WAAKDIENST]
    
    def _get_relevant_time_range(self) -> tuple[time, time]:
        """Evening/weekend: effectively 17:00-08:00 next day (outside business hours)."""
        return (time(17, 0), time(8, 0))  # Note: this spans midnight
    
    def _get_relevant_days(self) -> List[int]:
        """All days: Waakdienst covers Wednesday-Wednesday including weekends."""
        return [0, 1, 2, 3, 4, 5, 6]  # All days
    
    def check_recurring_leave_conflicts(self, employee: Any, check_date: date) -> AvailabilityResult:
        """Check recurring leave patterns that affect evening/weekend hours."""
        # Get active recurring patterns for this employee
        patterns = RecurringLeavePattern.objects.filter(
            employee=employee,
            is_active=True,
            effective_from__lte=check_date,
        ).filter(
            Q(effective_until__isnull=True) | Q(effective_until__gte=check_date)
        )
        
        for pattern in patterns:
            # Only check patterns that apply to this date
            if pattern.applies_to_date(check_date):
                # For Waakdienst, we're more concerned with full-day patterns or evening patterns
                # Business hours patterns (morning/afternoon only) don't typically conflict with evening coverage
                
                affected_hours = pattern.get_affected_hours_for_date(check_date)
                
                if affected_hours:
                    # Check if this is a full day pattern
                    if pattern.coverage_type == RecurringLeavePattern.CoverageType.FULL_DAY:
                        return AvailabilityResult(
                            is_available=False,
                            reason=f"Recurring leave: {pattern.name} (Full Day)"
                        )
                    
                    # For partial day patterns, check if they affect evening hours
                    # Since Waakdienst typically starts at 17:00, afternoon patterns might conflict
                    pattern_start = affected_hours['start_datetime'].time()
                    pattern_end = affected_hours['end_datetime'].time()
                    
                    # If pattern affects afternoon (12:00-17:00) or extends into evening, it might conflict
                    if pattern.coverage_type == RecurringLeavePattern.CoverageType.AFTERNOON:
                        # Afternoon patterns (12:00-17:00) end at 17:00 when Waakdienst starts
                        # This is a potential handover issue, but let's be permissive for now
                        logger.debug(f"Afternoon pattern {pattern.name} ends at Waakdienst start time - allowing")
                    
                    # Note: Morning patterns (08:00-12:00) don't conflict with evening coverage
        
        return AvailabilityResult(is_available=True)
    
    def check_weekend_availability(self, employee: Any, check_date: date) -> AvailabilityResult:
        """Special check for weekend availability during Waakdienst periods."""
        # For Waakdienst, weekend days are critical
        if check_date.weekday() in [5, 6]:  # Saturday, Sunday
            # Check if employee has any full-day patterns on weekends
            patterns = RecurringLeavePattern.objects.filter(
                employee=employee,
                is_active=True,
                day_of_week=check_date.weekday(),
                coverage_type=RecurringLeavePattern.CoverageType.FULL_DAY,
                effective_from__lte=check_date,
            ).filter(
                Q(effective_until__isnull=True) | Q(effective_until__gte=check_date)
            )
            
            for pattern in patterns:
                if pattern.applies_to_date(check_date):
                    return AvailabilityResult(
                        is_available=False,
                        reason=f"Weekend recurring leave: {pattern.name}"
                    )
        
        return AvailabilityResult(is_available=True)


class ConstraintCheckerFactory:
    """Factory to create the appropriate constraint checker for a shift type."""
    
    @staticmethod
    def create_for_shift_type(shift_type: str, start_date: datetime, end_date: datetime) -> BaseConstraintChecker:
        """Create the appropriate constraint checker for the given shift type."""
        if shift_type == ShiftType.INCIDENTS:
            return IncidentsConstraintChecker(start_date, end_date)
        elif shift_type == ShiftType.WAAKDIENST:
            return WaakdienstConstraintChecker(start_date, end_date)
        else:
            raise ValueError(f"Unknown shift type: {shift_type}")
    
    @staticmethod
    def create_incidents_checker(start_date: datetime, end_date: datetime) -> IncidentsConstraintChecker:
        """Create an IncidentsConstraintChecker."""
        return IncidentsConstraintChecker(start_date, end_date)
    
    @staticmethod
    def create_waakdienst_checker(start_date: datetime, end_date: datetime) -> WaakdienstConstraintChecker:
        """Create a WaakdienstConstraintChecker."""
        return WaakdienstConstraintChecker(start_date, end_date)
