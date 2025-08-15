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

from datetime import datetime, timedelta
from typing import List, Optional, Tuple
import pytz

from team_planner.users.models import User
from team_planner.shifts.models import ShiftType, ShiftTemplate
from team_planner.orchestrators.base_orchestrator import BaseOrchestrator
from team_planner.orchestrators.fairness_calculators import (
    IncidentsFairnessCalculator,
    IncidentsStandbyFairnessCalculator
)

from django.contrib.auth import get_user_model
from django.utils import timezone

from team_planner.shifts.models import ShiftType
from team_planner.employees.models import EmployeeProfile
from team_planner.orchestrators.base import BaseOrchestrator
from team_planner.orchestrators.fairness import FairnessCalculatorFactory
from team_planner.orchestrators.constraints import ConstraintCheckerFactory
from team_planner.orchestrators.anchors import business_weeks, get_team_tz

User = get_user_model()
logger = logging.getLogger(__name__)


class IncidentsOrchestrator(BaseOrchestrator):
    """
    Orchestrator for Incidents and Incidents-Standby shifts.
    
    Handles Monday-Friday business hours shifts with day-by-day generation
    and business hours constraint checking. Uses separate fairness tracking
    for Incidents vs Incidents-Standby to prevent cross-contamination.
    """
    
    def __init__(self, start_date: datetime, end_date: datetime, team_id: Optional[int] = None,
                 schedule_incidents: bool = True, schedule_incidents_standby: bool = False):
        """
        Initialize IncidentsOrchestrator.
        
        Args:
            start_date: Start of generation period
            end_date: End of generation period  
            team_id: Optional team ID for team-specific settings
            schedule_incidents: Whether to generate Incidents shifts
            schedule_incidents_standby: Whether to generate Incidents-Standby shifts
        """
        self.schedule_incidents = schedule_incidents
        self.schedule_incidents_standby = schedule_incidents_standby
        
        super().__init__(start_date, end_date, team_id)
        
        logger.info(f"IncidentsOrchestrator initialized: incidents={schedule_incidents}, standby={schedule_incidents_standby}")
    
    def _get_handled_shift_types(self) -> List[str]:
        """Return the shift types this orchestrator handles."""
        shift_types = []
        if self.schedule_incidents:
            shift_types.append(ShiftType.INCIDENTS)
        if self.schedule_incidents_standby:
            shift_types.append(ShiftType.INCIDENTS_STANDBY)
        return shift_types
    
    def _create_fairness_calculator(self):
        """Create appropriate fairness calculator based on enabled shift types."""
        # For now, use the Incidents calculator as primary
        # In the future, we might need a combined calculator for both types
        return FairnessCalculatorFactory.create_incidents_calculator(
            self.start_date, self.end_date
        )
    
    def _create_constraint_checker(self):
        """Create the IncidentsConstraintChecker for business hours checking."""
        return ConstraintCheckerFactory.create_incidents_checker(
            self.start_date, self.end_date
        )
    
    def _generate_time_periods(self) -> List[Tuple[datetime, datetime, str]]:
        """Generate Monday-Friday business week periods."""
        # Use the existing business_weeks utility for consistent DST handling
        from team_planner.teams.models import Team
        
        # Get team timezone if available
        tz = timezone.get_current_timezone()
        if self.team_id:
            try:
                team = Team.objects.get(pk=self.team_id)
                tz = get_team_tz(team)
            except Team.DoesNotExist:
                logger.warning(f"Team {self.team_id} not found, using default timezone")
        
        # Generate business week periods (Monday-Friday)
        periods = business_weeks(self.start_date, self.end_date, tz=tz)
        return [(p.start, p.end, 'business_week') for p in periods]
    
    def _get_available_employees(self) -> List[Any]:
        """Get employees available for incidents shifts."""
        # Get employees with incidents availability toggle enabled
        available_employees = User.objects.filter(
            is_active=True,
            employee_profile__available_for_incidents=True
        ).select_related('employee_profile')
        
        return list(available_employees)
    
    def generate_schedule(self, orchestration_run: Optional[Any] = None) -> Dict[str, Any]:
        """
        Generate complete incidents schedule using constraint-first approach.
        
        Processes both Incidents and Incidents-Standby if enabled, ensuring
        mutual exclusivity (no employee gets both types in same week).
        """
        self.orchestration_run = orchestration_run
        self.current_assignments = []
        
        logger.info(f"Starting IncidentsOrchestrator for period {self.start_date} to {self.end_date}")
        
        # Get available employees  
        available_employees = self._get_available_employees()
        if not available_employees:
            logger.warning("No employees available for incidents shifts")
            return self._create_empty_result()
        
        logger.info(f"Found {len(available_employees)} employees available for incidents")
        
        # Generate business week periods
        periods = self._generate_time_periods()
        logger.info(f"Generated {len(periods)} business weeks")
        
        all_assignments = []
        
        # Generate Incidents shifts first (primary)
        if self.schedule_incidents:
            incidents_assignments = self._generate_shift_type_assignments(
                periods, available_employees, ShiftType.INCIDENTS
            )
            all_assignments.extend(incidents_assignments)
            logger.info(f"Generated {len(incidents_assignments)} incidents assignments")
        
        # Generate Incidents-Standby shifts (ensuring no conflicts with Incidents)
        if self.schedule_incidents_standby:
            standby_assignments = self._generate_shift_type_assignments(
                periods, available_employees, ShiftType.INCIDENTS_STANDBY
            )
            all_assignments.extend(standby_assignments)
            logger.info(f"Generated {len(standby_assignments)} incidents-standby assignments")
        
        logger.info(f"Total assignments generated: {len(all_assignments)}")
        
        # Create result with metrics
        return self._create_result(all_assignments, available_employees)
    
    def _generate_shift_type_assignments(self, periods: List[Tuple[datetime, datetime, str]], 
                                       available_employees: List[Any], shift_type: str) -> List[Dict]:
        """Generate assignments for a specific shift type across all periods."""
        assignments = []
        
        for period_start, period_end, period_label in periods:
            # Get employees available for this period and shift type
            period_employees = self._get_employees_available_for_period(
                available_employees, period_start, period_end, shift_type
            )
            
            if not period_employees:
                logger.warning(f"No employees available for {shift_type} in period {period_start.date()}")
                continue
            
            # Generate assignments for this period
            period_assignments = self._generate_period_assignments_for_shift_type(
                period_start, period_end, period_label, period_employees, shift_type
            )
            assignments.extend(period_assignments)
        
        return assignments
    
    def _get_employees_available_for_period(self, employees: List[Any], 
                                          period_start: datetime, period_end: datetime,
                                          shift_type: str) -> List[Any]:
        """Get employees available for the entire period, considering mutual exclusivity."""
        available = []
        
        for employee in employees:
            # Check basic availability for this shift type
            if not self._is_employee_available_for_shift_type(employee, shift_type):
                continue
            
            # Check for mutual exclusivity conflicts within the current assignments
            if self._has_conflicting_assignment_in_period(employee, period_start, period_end, shift_type):
                logger.debug(f"Employee {employee.username} has conflicting assignment in period {period_start.date()}")
                continue
            
            available.append(employee)
        
        return available
    
    def _is_employee_available_for_shift_type(self, employee: Any, shift_type: str) -> bool:
        """Check if employee is available for this specific shift type."""
        try:
            profile = employee.employee_profile
            
            # For Incidents orchestrator, all shift types require incidents availability
            return profile.available_for_incidents
            
        except AttributeError:
            logger.warning(f"Employee {employee.username} has no employee_profile")
            return False
    
    def _has_conflicting_assignment_in_period(self, employee: Any, 
                                            period_start: datetime, period_end: datetime,
                                            shift_type: str) -> bool:
        """
        Check if employee already has a conflicting assignment in this period.
        
        Implements mutual exclusivity: no employee can have both Incidents and 
        Incidents-Standby in the same business week.
        """
        for assignment in self.current_assignments:
            if assignment['assigned_employee_id'] != employee.pk:
                continue
            
            assignment_start = assignment['start_datetime']
            assignment_end = assignment['end_datetime']
            
            # Check if assignment overlaps with this period
            if not (assignment_end <= period_start or assignment_start >= period_end):
                # There's an overlap - check for conflicts
                assignment_type = assignment['shift_type']
                
                # Mutual exclusivity: can't have both incidents and standby in same week
                if ((shift_type == ShiftType.INCIDENTS and assignment_type == ShiftType.INCIDENTS_STANDBY) or
                    (shift_type == ShiftType.INCIDENTS_STANDBY and assignment_type == ShiftType.INCIDENTS)):
                    return True
                
                # Same shift type conflict (shouldn't normally happen)
                if shift_type == assignment_type:
                    return True
        
        return False
    
    def _generate_period_assignments_for_shift_type(self, period_start: datetime, period_end: datetime,
                                                  period_label: str, available_employees: List[Any],
                                                  shift_type: str) -> List[Dict]:
        """Generate assignments for a specific shift type within a single period."""
        assignments = []
        
        # Generate daily shifts for this period
        daily_shifts = self._generate_daily_shifts(period_start, period_end, f"{period_label}_{shift_type}")
        
        # Day-by-day assignment with continuity preference
        current_employee = None
        
        for day_start, day_end, day_label in daily_shifts:
            day_date = day_start.date()
            
            # Get employees available for this specific day
            day_available_employees = self._get_employees_available_for_day(
                available_employees, day_date
            )
            
            if not day_available_employees:
                logger.warning(f"No employees available for {day_label} on {day_date}")
                continue
            
            # Prefer continuity: if current employee is available, keep them
            if (current_employee and 
                current_employee in day_available_employees and
                self._can_continue_assignment(current_employee, day_date)):
                
                chosen_employee = current_employee
                logger.debug(f"Continuing {chosen_employee.username} for {day_label}")
                
            else:
                # Need to pick a new employee
                chosen_employee = self._select_best_employee_for_day(
                    day_available_employees, day_date, day_label
                )
                current_employee = chosen_employee
                logger.debug(f"Selected {chosen_employee.username} for {day_label}")
            
            # Create assignment for this day
            assignment = self._create_day_assignment_for_shift_type(
                chosen_employee, day_start, day_end, day_label, shift_type
            )
            assignments.append(assignment)
            
            # Track this assignment for conflict checking
            self.current_assignments.append(assignment)
        
        return assignments
    
    def _generate_daily_shifts(self, period_start: datetime, period_end: datetime, 
                             period_label: str) -> List[Tuple[datetime, datetime, str]]:
        """Generate daily shifts within a business week period."""
        daily_shifts = []
        current_day = period_start.date()
        day_num = 0
        
        while current_day <= period_end.date() and day_num < 5:  # Max 5 business days
            # Only include weekdays (Monday=0 to Friday=4)
            if current_day.weekday() < 5:
                # Create 08:00-17:00 shift for this day
                day_start = timezone.make_aware(
                    datetime.combine(current_day, time(8, 0))
                )
                day_end = timezone.make_aware(
                    datetime.combine(current_day, time(17, 0))
                )
                
                day_label = f"{period_label}_day_{day_num + 1}"
                daily_shifts.append((day_start, day_end, day_label))
                day_num += 1
            
            current_day += timedelta(days=1)
        
        return daily_shifts
    
    def _create_day_assignment_for_shift_type(self, employee: Any, start_datetime: datetime,
                                            end_datetime: datetime, label: str, shift_type: str) -> Dict:
        """Create a day assignment for a specific shift type."""
        template = self._get_shift_template(shift_type)
        
        assignment = {
            'assigned_employee_id': employee.pk,
            'assigned_employee_name': employee.get_full_name() or employee.username,
            'start_datetime': start_datetime,
            'end_datetime': end_datetime,
            'shift_type': shift_type,
            'template_id': template.pk if template else None,
            'label': label,
            'auto_assigned': True,
            'assignment_reason': f'Generated by IncidentsOrchestrator for {shift_type}',
            'duration_hours': 9.0,  # Business hours: 08:00-17:00
        }
        
        return assignment
    
    def generate_next_week(self) -> Dict[str, Any]:
        """
        Generate assignments for the next business week only.
        
        This method is designed for rolling generation - called every Monday
        to generate the upcoming week's assignments.
        """
        # Calculate next Monday
        today = timezone.now().date()
        days_until_monday = (7 - today.weekday()) % 7
        if days_until_monday == 0:  # Today is Monday
            days_until_monday = 7
        
        next_monday = today + timedelta(days=days_until_monday)
        
        # Set period to next week only
        week_start = timezone.make_aware(
            datetime.combine(next_monday, time(8, 0))
        )
        week_end = timezone.make_aware(
            datetime.combine(next_monday + timedelta(days=4), time(17, 0))
        )
        
        # Temporarily adjust dates for single week generation
        original_start = self.start_date
        original_end = self.end_date
        
        self.start_date = week_start
        self.end_date = week_end
        
        try:
            result = self.generate_schedule()
            result['is_rolling_generation'] = True
            result['generated_week'] = next_monday.isoformat()
            
            logger.info(f"Generated next week ({next_monday}) with {result['total_shifts']} shifts")
            return result
            
        finally:
            # Restore original dates
            self.start_date = original_start
            self.end_date = original_end
    
    def get_business_hours_range(self) -> Tuple[time, time]:
        """Get the business hours range for incidents shifts."""
        return (time(8, 0), time(17, 0))
    
    def get_business_days(self) -> List[int]:
        """Get the business days (weekdays) for incidents shifts."""
        return [0, 1, 2, 3, 4]  # Monday through Friday
    
    def is_business_day(self, check_date) -> bool:
        """Check if a date is a business day."""
        return check_date.weekday() in self.get_business_days()
    
    def is_business_hours(self, check_time: time) -> bool:
        """Check if a time falls within business hours."""
        start_time, end_time = self.get_business_hours_range()
        return start_time <= check_time <= end_time
