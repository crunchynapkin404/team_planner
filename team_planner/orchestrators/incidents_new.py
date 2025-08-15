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


class IncidentsOrchestrator(BaseOrchestrator):
    """Orchestrator specialized for Incidents and Incidents-Standby shifts.
    
    This orchestrator operates on a Monday-Friday business week cycle:
    - Rotation Start: Monday 08:00
    - Rotation End: Friday 17:00
    - Shift Types: Incidents, Incidents-Standby
    - Generation: Constraint-first, day-by-day with continuity preference
    """

    def __init__(self, team_id: Optional[int] = None, 
                 prioritize_standby: bool = False):
        super().__init__(team_id=team_id)
        self.prioritize_standby = prioritize_standby
        
        # Incidents-specific configuration
        self.business_start_hour = 8   # 08:00
        self.business_end_hour = 17    # 17:00
        self.incidents_duration_hours = 9  # Full business day
        self.standby_duration_hours = 15   # Overnight standby coverage

    def _get_handled_shift_types(self) -> List[str]:
        """Return shift types handled by this orchestrator."""
        return [ShiftType.INCIDENTS, ShiftType.INCIDENTS_STANDBY]

    def _get_rotation_start_weekday(self) -> int:
        """Return Monday (0) as the rotation start day."""
        return 0  # Monday

    def _get_shift_templates(self) -> List[ShiftTemplate]:
        """Get shift templates for incidents and standby shifts."""
        templates = list(ShiftTemplate.objects.filter(
            shift_type__in=self._get_handled_shift_types(),
            is_active=True
        ))
        
        # Ensure we have templates for both shift types
        handled_types = {template.shift_type for template in templates}
        
        if ShiftType.INCIDENTS not in handled_types:
            print(f"Warning: No active ShiftTemplate found for {ShiftType.INCIDENTS}")
        
        if ShiftType.INCIDENTS_STANDBY not in handled_types:
            print(f"Warning: No active ShiftTemplate found for {ShiftType.INCIDENTS_STANDBY}")
        
        return templates

    def _create_fairness_calculator(self, start_date: datetime, end_date: datetime):
        """Create incidents fairness calculator for this period.
        
        Note: We use IncidentsFairnessCalculator which only tracks incidents.
        Standby fairness is tracked separately by IncidentsStandbyFairnessCalculator.
        """
        # For now, use incidents calculator. In Phase 2, we'll implement dual tracking
        return IncidentsFairnessCalculator(start_date, end_date)

    def _filter_employees_by_availability(self, employees: List[User]) -> List[User]:
        """Filter employees who are available for incidents work."""
        available_employees = []
        
        for employee in employees:
            profile = getattr(employee, 'employee_profile', None)
            if profile:
                # Check if employee is available for incidents
                available_for_incidents = getattr(profile, 'available_for_incidents', True)
                available_for_standby = getattr(profile, 'available_for_incidents_standby', True)
                
                # Include if available for either incidents or standby
                if available_for_incidents or available_for_standby:
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
        
        elif template.shift_type == ShiftType.INCIDENTS_STANDBY:
            # Incidents standby also only on business days
            return 0 <= weekday <= 4
        
        return False

    def _calculate_shift_times(self, date: datetime, template: ShiftTemplate) -> Tuple[datetime, datetime]:
        """Calculate start and end times for incidents shifts.
        
        Incidents: 08:00 - 17:00 (business hours)
        Incidents-Standby: 17:00 - 08:00+1 (evening coverage)
        """
        if template.shift_type == ShiftType.INCIDENTS:
            # Business hours: 8 AM to 5 PM
            start_time = date.replace(
                hour=self.business_start_hour, 
                minute=0, 
                second=0, 
                microsecond=0
            )
            end_time = date.replace(
                hour=self.business_end_hour, 
                minute=0, 
                second=0, 
                microsecond=0
            )
            
        elif template.shift_type == ShiftType.INCIDENTS_STANDBY:
            # Evening coverage: 5 PM to 8 AM next day
            start_time = date.replace(
                hour=self.business_end_hour, 
                minute=0, 
                second=0, 
                microsecond=0
            )
            end_time = (date + timedelta(days=1)).replace(
                hour=self.business_start_hour, 
                minute=0, 
                second=0, 
                microsecond=0
            )
            
        else:
            # Fallback to template duration
            start_time = date.replace(hour=8, minute=0, second=0, microsecond=0)
            duration = template.duration_hours or 8
            end_time = start_time + timedelta(hours=duration)
        
        return start_time, end_time

    def _find_best_employee_for_shift(self, date: datetime, template: ShiftTemplate,
                                    employees: List[User], 
                                    last_assigned: Optional[User]) -> Optional[User]:
        """Find the best employee for incidents shifts with business-hours constraints."""
        
        # Filter employees who are specifically available for this shift type
        shift_type_employees = []
        
        for employee in employees:
            if not self.is_employee_available_on_date(employee, date):
                continue
                
            profile = getattr(employee, 'employee_profile', None)
            if profile:
                if template.shift_type == ShiftType.INCIDENTS:
                    if getattr(profile, 'available_for_incidents', True):
                        shift_type_employees.append(employee)
                elif template.shift_type == ShiftType.INCIDENTS_STANDBY:
                    if getattr(profile, 'available_for_incidents_standby', True):
                        shift_type_employees.append(employee)
            else:
                # Include employees without profiles
                shift_type_employees.append(employee)
        
        if not shift_type_employees:
            return None
        
        # Apply continuity preference for weekly assignments
        if last_assigned and last_assigned in shift_type_employees:
            # Check if it's still the same week (Monday-Friday)
            week_start = self._get_week_start(date, self._get_rotation_start_weekday())
            assignment_day = (date - week_start).days
            
            # Prefer continuity within the same business week (Mon-Fri)
            if 0 <= assignment_day <= 4:  # Monday to Friday
                return last_assigned
        
        # Select by fairness if no continuity preference
        return self._select_employee_by_fairness(shift_type_employees, template.shift_type)

    def generate_business_week_assignments(self, week_start: datetime, 
                                         dry_run: bool = False) -> dict:
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

    def get_next_business_week_start(self, reference_date: Optional[datetime] = None) -> datetime:
        """Get the start of the next business week (Monday 08:00) after the reference date.
        
        This is useful for scheduling the next incidents orchestration run.
        """
        if reference_date is None:
            tz = pytz.timezone('Europe/Amsterdam')
            reference_date = tz.localize(datetime.now())
        
        # Find next Monday
        days_until_monday = (7 - reference_date.weekday()) % 7
        if days_until_monday == 0 and reference_date.hour >= 8:
            # If it's Monday and past 8 AM, get next Monday
            days_until_monday = 7
        
        next_monday = reference_date + timedelta(days=days_until_monday)
        return next_monday.replace(hour=8, minute=0, second=0, microsecond=0)

    def get_current_business_week_range(self, reference_date: Optional[datetime] = None) -> Tuple[datetime, datetime]:
        """Get the current business week range (Monday 08:00 to Friday 17:00)."""
        if reference_date is None:
            tz = pytz.timezone('Europe/Amsterdam')
            reference_date = tz.localize(datetime.now())
        
        # Find Monday of current week
        days_to_monday = reference_date.weekday()
        week_start = reference_date - timedelta(days=days_to_monday)
        week_start = week_start.replace(hour=8, minute=0, second=0, microsecond=0)
        
        # Friday 17:00
        week_end = week_start + timedelta(days=4, hours=9)  # +4 days, +9 hours from 08:00
        
        return week_start, week_end

    def __str__(self):
        """String representation of the orchestrator."""
        team_info = f" (Team {self.team_id})" if self.team_id else ""
        return f"IncidentsOrchestrator{team_info}"

    def __repr__(self):
        """Detailed representation of the orchestrator."""
        return f"IncidentsOrchestrator(team_id={self.team_id}, prioritize_standby={self.prioritize_standby})"
