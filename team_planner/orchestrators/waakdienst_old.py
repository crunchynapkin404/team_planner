"""
WaakdienstOrchestrator - Evening/Weekend Shift Management

This orchestrator handles Waakdienst shifts with:
- Wednesday 17:00 to Wednesday 08:00 24/7 coverage
- Evening/weekend focused constraint checking
- Natural conflict avoidance for evening/weekend periods
- Independent fairness tracking
- Autonomous rolling generation every Wednesday

Key Features:
- Constraint-first generation (no post-processing needed)
- 24/7 coverage across evening/weekend periods
- Preference for employee availability during non-business hours
- DST-aware week boundary handling
"""
from datetime import datetime, time, timedelta
from typing import List, Dict, Optional, Any, Tuple
import logging

from django.contrib.auth import get_user_model
from django.utils import timezone

from team_planner.shifts.models import ShiftType, Shift
from team_planner.employees.models import EmployeeProfile
from team_planner.orchestrators.base import BaseOrchestrator
from team_planner.orchestrators.fairness import FairnessCalculatorFactory
from team_planner.orchestrators.constraints import ConstraintCheckerFactory
from team_planner.orchestrators.anchors import waakdienst_periods, get_team_tz

User = get_user_model()
logger = logging.getLogger(__name__)


class WaakdienstOrchestrator(BaseOrchestrator):
    """
    WaakdienstOrchestrator manages 24/7 Waakdienst coverage from Wednesday-to-Wednesday.
    
    This orchestrator focuses on:
    - Evening/weekend availability constraints
    - Natural 24/7 coverage patterns
    - Minimal business hours disruption
    - Independent fairness tracking
    """
    
    def __init__(self, start_date: datetime, end_date: datetime, team_id: Optional[int] = None):
        super().__init__(start_date, end_date, team_id)
        logger.info(f"WaakdienstOrchestrator initialized for team {team_id} "
                   f"from {start_date} to {end_date}")
    
    def _get_handled_shift_types(self) -> List[str]:
        """Return the shift types this orchestrator handles."""
        return ['waakdienst']
    
    def _create_fairness_calculator(self):
        """Create the waakdienst fairness calculator."""
        return FairnessCalculatorFactory.create_waakdienst_calculator(self.start_date, self.end_date)
    
    def _create_constraint_checker(self):
        """Create the waakdienst constraint checker."""
        return ConstraintCheckerFactory.create_waakdienst_checker(self.start_date, self.end_date)
    
    def _get_available_employees(self) -> List[Any]:
        """Get employees available for waakdienst shifts."""
        # Get employees with waakdienst availability toggle enabled
        available_employees = User.objects.filter(
            is_active=True,
            employee_profile__available_for_waakdienst=True
        ).select_related('employee_profile')
        
        return list(available_employees)
    
    def _generate_time_periods(self) -> List[Tuple[datetime, datetime, str]]:
        """Generate Wednesday-to-Wednesday waakdienst periods."""
        from team_planner.teams.models import Team
        
        # Get team if available
        team = None
        if self.team_id:
            try:
                team = Team.objects.get(pk=self.team_id)
            except Team.DoesNotExist:
                logger.warning(f"Team {self.team_id} not found, using default settings")
        
        if team:
            # Generate waakdienst week periods (Wednesday-Wednesday)
            periods = waakdienst_periods(self.start_date, self.end_date, team=team)
            return [(p.start, p.end, 'waakdienst_week') for p in periods]
        else:
            # Fallback: generate weekly periods manually
            periods = []
            current = self.start_date
            # Find Wednesday of the first week
            days_since_wednesday = (current.weekday() - 2) % 7
            wednesday = current - timedelta(days=days_since_wednesday)
            
            while wednesday < self.end_date:
                next_wednesday = wednesday + timedelta(days=7)
                week_start = timezone.make_aware(datetime.combine(wednesday.date(), time(17, 0)))
                week_end = timezone.make_aware(datetime.combine(next_wednesday.date(), time(8, 0)))
                
                if week_start < self.end_date:
                    periods.append((week_start, week_end, 'waakdienst_week'))
                wednesday = next_wednesday
            
            return periods
    
    def _generate_daily_shifts(self, period_start: datetime, period_end: datetime, 
                             period_label: str) -> List[Tuple[datetime, datetime, str]]:
        """Generate 24/7 coverage for a waakdienst week period."""
        shifts = []
        
        # Waakdienst is typically one person for the entire week
        # Wednesday 17:00 to next Wednesday 08:00
        waakdienst_start = period_start
        waakdienst_end = period_end
        
        shifts.append((waakdienst_start, waakdienst_end, f"waakdienst_{period_start.strftime('%Y%m%d')}"))
        
        logger.debug(f"Generated waakdienst shift: {waakdienst_start} to {waakdienst_end}")
        return shifts
    
    def _assign_employee_to_shift(self, shift_start: datetime, shift_end: datetime, 
                                shift_label: str, assigned_employees: Dict[str, Any]) -> Optional[int]:
        """
        Assign an employee to a waakdienst shift using constraint-first approach.
        
        Args:
            shift_start: Start datetime of the shift
            shift_end: End datetime of the shift
            shift_label: Label/identifier for the shift
            assigned_employees: Current assignments for tracking
            
        Returns:
            Employee ID if assignment successful, None otherwise
        """
        # Get available employees with waakdienst skill
        waakdienst_employees = self._get_available_employees()
        
        if not waakdienst_employees:
            logger.warning("No employees available with waakdienst skill")
            return None
        
        # Get employees available for this specific day/period
        available_employees = []
        check_date = shift_start.date()
        
        for employee in waakdienst_employees:
            result = self.constraint_checker.check_employee_availability(employee, check_date)
            if result.is_available:
                available_employees.append(employee)
        
        if not available_employees:
            logger.warning(f"No available employees for waakdienst shift {shift_label}")
            return None
        
        # Use fairness calculator to get the best candidate
        best_employee = self.fairness_calculator.get_least_assigned_employee(available_employees)
        
        if best_employee:
            logger.info(f"Assigned {best_employee.user.username} to waakdienst {shift_label}")
            return best_employee.user.id
        
        return None
    
    def generate_schedule(self, orchestration_run: Optional[Any] = None) -> Dict[str, Any]:
        """
        Generate waakdienst schedule using constraint-first day-by-day approach.
        
        Returns:
            Dict containing generation results and statistics
        """
        logger.info(f"Starting waakdienst schedule generation for team {self.team_id}")
        
        # Use the inherited generate_schedule method from BaseOrchestrator
        return super().generate_schedule(orchestration_run)
    
    def generate_next_week(self) -> Dict[str, Any]:
        """
        Generate schedule for the next waakdienst week only.
        This is called by the autonomous rolling system every Wednesday.
        
        Returns:
            Dict containing generation results for the single week
        """
        logger.info("Generating next waakdienst week")
        
        # Calculate next Wednesday period
        from team_planner.teams.models import Team
        
        team = None
        if self.team_id:
            try:
                team = Team.objects.get(pk=self.team_id)
            except Team.DoesNotExist:
                pass
        
        # Find the next Wednesday period that needs coverage
        now = timezone.now()
        
        if team:
            next_periods = waakdienst_periods(
                now, 
                now + timedelta(weeks=2),  # Look ahead 2 weeks 
                team=team
            )
        else:
            # Fallback: create a simple weekly period
            next_periods = []
            current = now
            days_since_wednesday = (current.weekday() - 2) % 7
            next_wednesday = current + timedelta(days=7 - days_since_wednesday)
            week_start = timezone.make_aware(datetime.combine(next_wednesday.date(), time(17, 0)))
            week_end = week_start + timedelta(days=7)
            
            from team_planner.orchestrators.anchors import Period
            next_periods = [Period(start=week_start, end=week_end)]
        
        if not next_periods:
            logger.warning("No upcoming waakdienst periods found")
            return {'success': False, 'error': 'No periods to generate'}
        
        # Take the first period that doesn't have existing coverage
        next_period = next_periods[0]
        for period in next_periods:
            # Check if this period already has coverage
            existing_shifts = Shift.objects.filter(
                start_datetime__gte=period.start,
                end_datetime__lte=period.end,
                template__shift_type='waakdienst'
            )
            if not existing_shifts.exists():
                next_period = period
                break
        
        # Temporarily adjust our date range to cover just this period
        original_start = self.start_date
        original_end = self.end_date
        
        self.start_date = next_period.start
        self.end_date = next_period.end
        
        try:
            result = self.generate_schedule()
            logger.info(f"Generated waakdienst week: {next_period.start} to {next_period.end}")
            return result
        finally:
            # Restore original date range
            self.start_date = original_start
            self.end_date = original_end
    
    def get_coverage_hours_range(self) -> Tuple[time, time]:
        """Get the 24/7 coverage range for waakdienst shifts."""
        return (time(0, 0), time(23, 59))
    
    def get_coverage_days(self) -> List[int]:
        """Get all days for waakdienst coverage (24/7)."""
        return [0, 1, 2, 3, 4, 5, 6]  # All days of the week
    
    def is_coverage_day(self, check_date) -> bool:
        """Check if a date needs waakdienst coverage (always True for 24/7)."""
        return True
    
    def is_coverage_hours(self, check_time: time) -> bool:
        """Check if a time needs waakdienst coverage (always True for 24/7)."""
        return True
