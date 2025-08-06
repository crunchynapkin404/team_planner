"""
Orchestrator algorithms for fair shift distribution.

This module implements the core scheduling algorithms for:
1. Fair distribution of incident shifts (5-day weeks)
2. Fair distribution of waakdienst shifts (7-day weeks)
3. Constraint handling (availability toggles, existing leave)
4. Conflict resolution logic
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict
import logging

from django.contrib.auth import get_user_model
from django.utils import timezone

from team_planner.shifts.models import Shift, ShiftTemplate, ShiftType
from team_planner.employees.models import EmployeeProfile
from team_planner.leaves.models import LeaveRequest

User = get_user_model()
logger = logging.getLogger(__name__)


class FairnessCalculator:
    """Calculate fairness scores for shift assignments."""
    
    def __init__(self, start_date: datetime, end_date: datetime):
        self.start_date = start_date
        self.end_date = end_date
    
    def calculate_current_assignments(self, employees: List[Any]) -> Dict[int, Dict[str, int]]:
        """Calculate current shift assignments for fairness tracking."""
        assignments = defaultdict(lambda: {'incidents': 0, 'waakdienst': 0})
        
        for employee in employees:
            # Count existing shifts in the period
            existing_shifts = Shift.objects.filter(
                assigned_employee=employee,
                start_datetime__gte=self.start_date,
                end_datetime__lte=self.end_date
            ).select_related('template')
            
            for shift in existing_shifts:
                shift_type = shift.template.shift_type
                if shift_type == ShiftType.INCIDENTS:
                    assignments[employee.pk]['incidents'] += 5  # 5 days per week
                elif shift_type == ShiftType.WAAKDIENST:
                    assignments[employee.pk]['waakdienst'] += 7  # 7 days per week
        
        return dict(assignments)
    
    def calculate_fairness_score(self, assignments: Dict[int, Dict[str, int]]) -> Dict[int, float]:
        """Calculate fairness scores based on assignment distribution."""
        if not assignments:
            return {}
        
        # Calculate average assignments
        total_incidents = sum(data['incidents'] for data in assignments.values())
        total_waakdienst = sum(data['waakdienst'] for data in assignments.values())
        num_employees = len(assignments)
        
        avg_incidents = total_incidents / num_employees if num_employees > 0 else 0
        avg_waakdienst = total_waakdienst / num_employees if num_employees > 0 else 0
        
        fairness_scores = {}
        for employee_id, data in assignments.items():
            # Calculate deviation from average (lower is better)
            incidents_deviation = abs(data['incidents'] - avg_incidents)
            waakdienst_deviation = abs(data['waakdienst'] - avg_waakdienst)
            
            # Convert to score (100 = perfect fairness, lower = less fair)
            total_deviation = incidents_deviation + waakdienst_deviation
            fairness_score = max(0, 100 - (total_deviation * 10))
            fairness_scores[employee_id] = fairness_score
        
        return fairness_scores


class ConstraintChecker:
    """Check constraints for shift assignments."""
    
    def __init__(self, start_date: datetime, end_date: datetime):
        self.start_date = start_date
        self.end_date = end_date
    
    def get_available_employees(self, shift_type: str) -> List[Any]:
        """Get employees available for a specific shift type."""
        employees = User.objects.filter(
            is_active=True,
            employee_profile__status='active'
        ).select_related('employee_profile')
        
        available = []
        for employee in employees:
            try:
                profile = employee.employee_profile
                if shift_type == ShiftType.INCIDENTS and profile.available_for_incidents:
                    available.append(employee)
                elif shift_type == ShiftType.WAAKDIENST and profile.available_for_waakdienst:
                    available.append(employee)
            except EmployeeProfile.DoesNotExist:
                continue
        
        return available
    
    def check_leave_conflicts(self, employee: Any, start_date: datetime, end_date: datetime) -> bool:
        """Check if employee has approved leave during the period."""
        leave_requests = LeaveRequest.objects.filter(
            employee=employee,
            status='approved',
            start_date__lte=end_date,
            end_date__gte=start_date
        )
        return leave_requests.exists()
    
    def check_existing_assignments(self, employee: Any, start_date: datetime, end_date: datetime) -> bool:
        """Check if employee already has shifts during the period."""
        existing_shifts = Shift.objects.filter(
            assigned_employee=employee,
            start_datetime__lte=end_date,
            end_datetime__gte=start_date
        )
        return existing_shifts.exists()
    
    def is_employee_available(self, employee: Any, start_date: datetime, end_date: datetime, shift_type: str) -> bool:
        """Check if employee is available for assignment."""
        # Check availability toggle
        try:
            profile = employee.employee_profile
            if shift_type == ShiftType.INCIDENTS and not profile.available_for_incidents:
                return False
            if shift_type == ShiftType.WAAKDIENST and not profile.available_for_waakdienst:
                return False
        except EmployeeProfile.DoesNotExist:
            return False
        
        # Check leave conflicts
        if self.check_leave_conflicts(employee, start_date, end_date):
            return False
        
        # Check existing assignments
        if self.check_existing_assignments(employee, start_date, end_date):
            return False
        
        return True


class ShiftOrchestrator:
    """Main orchestrator for generating shift schedules."""
    
    def __init__(self, start_date: datetime, end_date: datetime):
        self.start_date = start_date
        self.end_date = end_date
        self.fairness_calculator = FairnessCalculator(start_date, end_date)
        self.constraint_checker = ConstraintChecker(start_date, end_date)
        self.generated_shifts = []
    
    def generate_week_dates(self) -> List[Tuple[datetime, datetime]]:
        """Generate week start/end dates for the planning period."""
        weeks = []
        current = self.start_date
        
        # Find Monday of the first week
        days_since_monday = current.weekday()
        monday = current - timedelta(days=days_since_monday)
        
        while monday < self.end_date:
            friday = monday + timedelta(days=4)  # Friday
            next_wednesday = monday + timedelta(days=9)  # Next Wednesday
            
            weeks.append((monday, friday))  # Incidents week
            weeks.append((monday, next_wednesday))  # Waakdienst week
            
            monday += timedelta(weeks=1)
        
        return weeks
    
    def get_shift_template(self, shift_type: str) -> Optional[ShiftTemplate]:
        """Get or create shift template for the given type."""
        template, created = ShiftTemplate.objects.get_or_create(
            shift_type=shift_type,
            defaults={
                'name': f'{shift_type.title()} Template',
                'description': f'Automatically generated template for {shift_type} shifts',
                'duration_hours': 40 if shift_type == ShiftType.INCIDENTS else 168,
                'is_active': True
            }
        )
        return template
    
    def assign_shifts_fairly(self, shift_type: str, week_dates: List[Tuple[datetime, datetime]]) -> List[Dict]:
        """Assign shifts using fair distribution algorithm."""
        available_employees = self.constraint_checker.get_available_employees(shift_type)
        if not available_employees:
            logger.warning(f"No employees available for {shift_type} shifts")
            return []
        
        # Get current assignments for fairness calculation
        current_assignments = self.fairness_calculator.calculate_current_assignments(available_employees)
        
        # Sort employees by current assignment count (fairness)
        def sort_key(emp):
            emp_assignments = current_assignments.get(emp.pk, {'incidents': 0, 'waakdienst': 0})
            if shift_type == ShiftType.INCIDENTS:
                return emp_assignments['incidents']
            else:
                return emp_assignments['waakdienst']
        
        # Track assignments made in this run
        new_assignments = defaultdict(int)
        assignments = []
        
        for start_date, end_date in week_dates:
            # Filter employees who are available for this specific week
            eligible_employees = [
                emp for emp in available_employees
                if self.constraint_checker.is_employee_available(emp, start_date, end_date, shift_type)
            ]
            
            if not eligible_employees:
                logger.warning(f"No eligible employees for {shift_type} week {start_date}")
                continue
            
            # Sort by fairness (least assigned first) + new assignments
            eligible_employees.sort(key=lambda emp: (
                sort_key(emp) + new_assignments[emp.pk]
            ))
            
            # Assign to the most fair candidate
            assigned_employee = eligible_employees[0]
            new_assignments[assigned_employee.pk] += 1
            
            # Create assignment data
            template = self.get_shift_template(shift_type)
            if template:
                assignment = {
                    'template': template,
                    'assigned_employee': assigned_employee,
                    'start_datetime': start_date,
                    'end_datetime': end_date,
                    'shift_type': shift_type,
                    'auto_assigned': True,
                    'assignment_reason': f'Fair distribution algorithm - {shift_type}'
                }
                assignments.append(assignment)
        
        return assignments
    
    def generate_schedule(self) -> Dict[str, Any]:
        """Generate complete schedule for the period."""
        logger.info(f"Starting orchestration for period {self.start_date} to {self.end_date}")
        
        # Generate week dates
        all_weeks = self.generate_week_dates()
        incident_weeks = [(start, end) for start, end in all_weeks if (end - start).days == 4]
        waakdienst_weeks = [(start, end) for start, end in all_weeks if (end - start).days == 9]
        
        # Generate assignments
        incident_assignments = self.assign_shifts_fairly(ShiftType.INCIDENTS, incident_weeks)
        waakdienst_assignments = self.assign_shifts_fairly(ShiftType.WAAKDIENST, waakdienst_weeks)
        
        all_assignments = incident_assignments + waakdienst_assignments
        
        # Calculate fairness metrics
        all_employees = list(set([a['assigned_employee'] for a in all_assignments]))
        final_assignments = self.fairness_calculator.calculate_current_assignments(all_employees)
        fairness_scores = self.fairness_calculator.calculate_fairness_score(final_assignments)
        
        result = {
            'assignments': all_assignments,
            'total_shifts': len(all_assignments),
            'incident_shifts': len(incident_assignments),
            'waakdienst_shifts': len(waakdienst_assignments),
            'employees_assigned': len(all_employees),
            'fairness_scores': fairness_scores,
            'average_fairness': sum(fairness_scores.values()) / len(fairness_scores) if fairness_scores else 0,
            'period_start': self.start_date,
            'period_end': self.end_date
        }
        
        logger.info(f"Orchestration complete: {result['total_shifts']} shifts generated")
        return result
    
    def preview_schedule(self) -> Dict[str, Any]:
        """Generate schedule preview without saving."""
        return self.generate_schedule()
    
    def apply_schedule(self) -> Dict[str, Any]:
        """Generate and save schedule to database."""
        schedule = self.generate_schedule()
        
        created_shifts = []
        for assignment in schedule['assignments']:
            shift = Shift.objects.create(
                template=assignment['template'],
                assigned_employee=assignment['assigned_employee'],
                start_datetime=assignment['start_datetime'],
                end_datetime=assignment['end_datetime'],
                status='scheduled',
                auto_assigned=assignment['auto_assigned'],
                assignment_reason=assignment['assignment_reason']
            )
            created_shifts.append(shift)
        
        schedule['created_shifts'] = created_shifts
        logger.info(f"Applied schedule: {len(created_shifts)} shifts created")
        return schedule
