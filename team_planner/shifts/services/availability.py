"""
Availability Service for Team Planner

Calculates employee availability status for scheduling:
- Available (green): No shifts, no leave, under hour limits
- Partially Available (yellow): Some conflicts or near limits
- Unavailable (red): On leave or at/over capacity

Usage:
    from team_planner.shifts.services.availability import AvailabilityService
    
    service = AvailabilityService()
    availability = service.get_availability_matrix(start_date, end_date)
"""

from datetime import datetime, timedelta
from typing import Dict, List, Any
from django.db.models import Q, Sum, F
from django.utils import timezone

from team_planner.shifts.models import Shift, ShiftAssignment, Leave
from team_planner.employees.models import Employee


class AvailabilityStatus:
    """Enum-like class for availability status"""
    AVAILABLE = 'available'
    PARTIAL = 'partial'
    UNAVAILABLE = 'unavailable'


class AvailabilityService:
    """Service for calculating employee availability"""
    
    # Configuration
    MAX_DAILY_HOURS = 12  # Maximum hours per day
    MAX_WEEKLY_HOURS = 48  # Maximum hours per week
    PARTIAL_THRESHOLD = 0.75  # 75% of max = partial availability
    
    def __init__(self):
        pass
    
    def get_availability_matrix(
        self,
        start_date: datetime,
        end_date: datetime,
        employee_ids: List[int] | None = None
    ) -> Dict[str, Dict[str, str]]:
        """
        Get availability matrix for all employees across date range.
        
        Args:
            start_date: Start of date range
            end_date: End of date range
            employee_ids: Optional list of specific employee IDs
            
        Returns:
            Dictionary mapping employee_id -> { date -> status }
            Example:
            {
                "123": {
                    "2025-01-15": "available",
                    "2025-01-16": "partial",
                    "2025-01-17": "unavailable"
                }
            }
        """
        # Get employees
        employees = Employee.objects.all()
        if employee_ids:
            employees = employees.filter(id__in=employee_ids)
        
        # Build availability matrix
        availability = {}
        
        for employee in employees:
            employee_availability = {}
            
            # Check each date in range
            current_date = start_date.date() if isinstance(start_date, datetime) else start_date
            end = end_date.date() if isinstance(end_date, datetime) else end_date
            
            while current_date <= end:
                status = self._get_daily_availability(employee, current_date)
                employee_availability[current_date.isoformat()] = status
                current_date += timedelta(days=1)
            
            availability[str(employee.id)] = employee_availability
        
        return availability
    
    def _get_daily_availability(
        self,
        employee: Employee,
        date: datetime.date
    ) -> str:
        """
        Calculate availability status for an employee on a specific date.
        
        Args:
            employee: The employee to check
            date: The date to check
            
        Returns:
            Status string: 'available', 'partial', or 'unavailable'
        """
        # Check for approved leave
        leave_exists = Leave.objects.filter(
            employee=employee,
            status='approved',
            start_date__lte=date,
            end_date__gte=date
        ).exists()
        
        if leave_exists:
            return AvailabilityStatus.UNAVAILABLE
        
        # Get shifts for this date
        start_datetime = timezone.make_aware(datetime.combine(date, datetime.min.time()))
        end_datetime = start_datetime + timedelta(days=1)
        
        assignments = ShiftAssignment.objects.filter(
            employee=employee,
            shift__start_time__gte=start_datetime,
            shift__start_time__lt=end_datetime
        ).select_related('shift')
        
        # Calculate total hours for the day
        total_hours = 0
        for assignment in assignments:
            shift_duration = (assignment.shift.end_time - assignment.shift.start_time).total_seconds() / 3600
            total_hours += shift_duration
        
        # Check against limits
        if total_hours >= self.MAX_DAILY_HOURS:
            return AvailabilityStatus.UNAVAILABLE
        elif total_hours >= (self.MAX_DAILY_HOURS * self.PARTIAL_THRESHOLD):
            return AvailabilityStatus.PARTIAL
        
        # Check weekly hours
        week_start = start_datetime - timedelta(days=start_datetime.weekday())
        week_end = week_start + timedelta(days=7)
        
        weekly_assignments = ShiftAssignment.objects.filter(
            employee=employee,
            shift__start_time__gte=week_start,
            shift__start_time__lt=week_end
        ).annotate(
            duration=F('shift__end_time') - F('shift__start_time')
        ).aggregate(
            total=Sum('duration')
        )['total']
        
        if weekly_assignments:
            weekly_hours = weekly_assignments.total_seconds() / 3600
            
            if weekly_hours >= self.MAX_WEEKLY_HOURS:
                return AvailabilityStatus.PARTIAL  # Near weekly limit
            elif weekly_hours >= (self.MAX_WEEKLY_HOURS * self.PARTIAL_THRESHOLD):
                return AvailabilityStatus.PARTIAL
        
        # Check for pending leave (less critical)
        pending_leave = Leave.objects.filter(
            employee=employee,
            status='pending',
            start_date__lte=date,
            end_date__gte=date
        ).exists()
        
        if pending_leave:
            return AvailabilityStatus.PARTIAL
        
        # Available!
        return AvailabilityStatus.AVAILABLE
    
    def get_availability_summary(
        self,
        availability_matrix: Dict[str, Dict[str, str]]
    ) -> Dict[str, Any]:
        """
        Generate summary statistics for availability.
        
        Args:
            availability_matrix: Matrix from get_availability_matrix()
            
        Returns:
            Summary statistics
        """
        total_days = 0
        status_counts = {
            AvailabilityStatus.AVAILABLE: 0,
            AvailabilityStatus.PARTIAL: 0,
            AvailabilityStatus.UNAVAILABLE: 0
        }
        
        for employee_data in availability_matrix.values():
            for status in employee_data.values():
                status_counts[status] += 1
                total_days += 1
        
        return {
            'total_employee_days': total_days,
            'available_count': status_counts[AvailabilityStatus.AVAILABLE],
            'partial_count': status_counts[AvailabilityStatus.PARTIAL],
            'unavailable_count': status_counts[AvailabilityStatus.UNAVAILABLE],
            'availability_percentage': (
                (status_counts[AvailabilityStatus.AVAILABLE] / total_days * 100)
                if total_days > 0 else 0
            )
        }
