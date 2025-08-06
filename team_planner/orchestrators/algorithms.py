"""
Orchestrator algorithms for fair shift distribution.

This module implements the core scheduling algorithms according to SHIFT_SCHEDULING_SPEC.md:
1. Incidents: Individual daily shifts, same engineer for the week (Mon-Fri)
2. Incidents-Standby: Individual daily shifts, same engineer for the week (Mon-Fri)  
3. Waakdienst: Individual daily shifts, same engineer for the week (Wed 17:00 - Wed 08:00)
"""
from datetime import datetime, timedelta, time
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
        assignments = defaultdict(lambda: {'incidents': 0, 'incidents_standby': 0, 'waakdienst': 0})
        
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
                    assignments[employee.pk]['incidents'] += 1  # Count individual daily shifts
                elif shift_type == ShiftType.INCIDENTS_STANDBY:
                    assignments[employee.pk]['incidents_standby'] += 1  # Count individual daily shifts
                elif shift_type == ShiftType.WAAKDIENST:
                    assignments[employee.pk]['waakdienst'] += 1  # Count individual daily shifts
        
        return dict(assignments)
    
    def calculate_fairness_score(self, assignments: Dict[int, Dict[str, int]]) -> Dict[int, float]:
        """Calculate fairness scores based on assignment distribution."""
        if not assignments:
            return {}
        
        # Calculate average assignments for each shift type
        num_employees = len(assignments)
        total_incidents = sum(data['incidents'] for data in assignments.values())
        total_incidents_standby = sum(data['incidents_standby'] for data in assignments.values())
        total_waakdienst = sum(data['waakdienst'] for data in assignments.values())
        
        avg_incidents = total_incidents / num_employees if num_employees > 0 else 0
        avg_incidents_standby = total_incidents_standby / num_employees if num_employees > 0 else 0
        avg_waakdienst = total_waakdienst / num_employees if num_employees > 0 else 0
        
        fairness_scores = {}
        for employee_id, data in assignments.items():
            # Calculate deviation from average (lower is better)
            incidents_deviation = abs(data['incidents'] - avg_incidents)
            incidents_standby_deviation = abs(data['incidents_standby'] - avg_incidents_standby)
            waakdienst_deviation = abs(data['waakdienst'] - avg_waakdienst)
            
            # Convert to score (100 = perfect fairness, lower = less fair)
            total_deviation = incidents_deviation + incidents_standby_deviation + waakdienst_deviation
            fairness_score = max(0, 100 - (total_deviation * 10))
            fairness_scores[employee_id] = fairness_score
        
        return fairness_scores


class ConstraintChecker:
    """Check constraints for shift assignments."""
    
    def __init__(self, start_date: datetime, end_date: datetime, team_id: Optional[int] = None):
        self.start_date = start_date
        self.end_date = end_date
        self.team_id = team_id
    
    def get_available_employees(self, shift_type: str) -> List[Any]:
        """Get employees available for a specific shift type."""
        query = User.objects.filter(
            is_active=True,
            employee_profile__status='active'
        ).select_related('employee_profile')
        
        # Filter by team if specified
        if self.team_id:
            query = query.filter(teams=self.team_id)
        
        employees = list(query)
        
        available = []
        for employee in employees:
            try:
                profile = employee.employee_profile
                if shift_type == ShiftType.INCIDENTS and profile.available_for_incidents:
                    available.append(employee)
                elif shift_type == ShiftType.INCIDENTS_STANDBY and profile.available_for_incidents:
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
            start_date__lte=end_date.date(),
            end_date__gte=start_date.date()
        )
        return leave_requests.exists()
    
    def check_existing_assignments(self, employee: Any, start_date: datetime, end_date: datetime) -> bool:
        """Check if employee already has shifts during the period."""
        existing_shifts = Shift.objects.filter(
            assigned_employee=employee,
            start_datetime__lt=end_date,
            end_datetime__gt=start_date
        )
        return existing_shifts.exists()
    
    def is_employee_available(self, employee: Any, start_date: datetime, end_date: datetime, shift_type: str) -> bool:
        """Check if employee is available for assignment."""
        # Check availability toggle
        try:
            profile = employee.employee_profile
            if shift_type == ShiftType.INCIDENTS and not profile.available_for_incidents:
                return False
            if shift_type == ShiftType.INCIDENTS_STANDBY and not profile.available_for_incidents:
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
    """Main orchestrator for generating shift schedules according to specification."""
    
    def __init__(self, start_date: datetime, end_date: datetime, team_id: Optional[int] = None, 
                 schedule_incidents: bool = True, schedule_incidents_standby: bool = False, 
                 schedule_waakdienst: bool = True):
        self.start_date = start_date
        self.end_date = end_date
        self.team_id = team_id
        self.schedule_incidents = schedule_incidents
        self.schedule_incidents_standby = schedule_incidents_standby
        self.schedule_waakdienst = schedule_waakdienst
        self.fairness_calculator = FairnessCalculator(start_date, end_date)
        self.constraint_checker = ConstraintChecker(start_date, end_date, team_id=team_id)
    
    def generate_incidents_weeks(self) -> List[Tuple[datetime, datetime, str]]:
        """Generate Monday-Friday weeks for incidents shifts."""
        weeks = []
        current = self.start_date
        
        # Find Monday of the first week
        days_since_monday = current.weekday()
        monday = current - timedelta(days=days_since_monday)
        
        while monday < self.end_date:
            friday = monday + timedelta(days=4)
            if friday.date() <= self.end_date.date():
                week_start = timezone.make_aware(datetime.combine(monday.date(), time(8, 0)))
                week_end = timezone.make_aware(datetime.combine(friday.date(), time(17, 0)))
                weeks.append((week_start, week_end, 'business_week'))
            
            monday += timedelta(weeks=1)
        
        return weeks
    
    def generate_waakdienst_weeks(self) -> List[Tuple[datetime, datetime, str]]:
        """Generate Wednesday 17:00 to Wednesday 08:00 weeks for waakdienst shifts."""
        weeks = []
        current = self.start_date
        
        # Find Wednesday of the first week
        days_since_wednesday = (current.weekday() - 2) % 7
        wednesday = current - timedelta(days=days_since_wednesday)
        
        while wednesday < self.end_date:
            next_wednesday = wednesday + timedelta(days=7)
            week_start = timezone.make_aware(datetime.combine(wednesday.date(), time(17, 0)))
            week_end = timezone.make_aware(datetime.combine(next_wednesday.date(), time(8, 0)))
            
            if week_start < timezone.make_aware(datetime.combine(self.end_date.date(), time(23, 59))):
                weeks.append((week_start, week_end, 'waakdienst_week'))
            
            wednesday = next_wednesday
        
        return weeks
    
    def generate_daily_shifts_for_week(self, week_start: datetime, week_end: datetime, 
                                     shift_type: str, week_type: str) -> List[Tuple[datetime, datetime, str]]:
        """Generate individual daily shifts for a week."""
        daily_shifts = []
        
        if week_type == 'business_week':
            # Incidents/Incidents-Standby: Monday-Friday 08:00-17:00
            current_day = week_start
            for day_num in range(5):  # Monday to Friday
                day_start = current_day.replace(hour=8, minute=0, second=0, microsecond=0)
                day_end = current_day.replace(hour=17, minute=0, second=0, microsecond=0)
                daily_shifts.append((day_start, day_end, f"{shift_type}_day_{day_num + 1}"))
                current_day += timedelta(days=1)
        
        elif week_type == 'waakdienst_week':
            # Waakdienst: 7 individual daily shifts as per specification
            current = week_start
            
            # Wednesday Evening: 17:00 - Thursday 08:00 (15 hours overnight)
            wed_end = current.replace(hour=17) + timedelta(days=1, hours=-9)  # Thursday 08:00
            daily_shifts.append((current, wed_end, f"{shift_type}_wed_evening"))
            
            # Thursday Evening: 17:00 - Friday 08:00 (15 hours overnight)
            thu_start = current.replace(hour=17) + timedelta(days=1)
            thu_end = thu_start + timedelta(hours=15)
            daily_shifts.append((thu_start, thu_end, f"{shift_type}_thu_evening"))
            
            # Friday Evening: 17:00 - Saturday 08:00 (15 hours overnight)
            fri_start = current.replace(hour=17) + timedelta(days=2)
            fri_end = fri_start + timedelta(hours=15)
            daily_shifts.append((fri_start, fri_end, f"{shift_type}_fri_evening"))
            
            # Saturday: 08:00 - Sunday 08:00 (24 hours full day)
            sat_start = current.replace(hour=8) + timedelta(days=3)
            sat_end = sat_start + timedelta(hours=24)
            daily_shifts.append((sat_start, sat_end, f"{shift_type}_sat_full"))
            
            # Sunday: 08:00 - Monday 08:00 (24 hours full day)
            sun_start = sat_end
            sun_end = sun_start + timedelta(hours=24)
            daily_shifts.append((sun_start, sun_end, f"{shift_type}_sun_full"))
            
            # Monday Evening: 17:00 - Tuesday 08:00 (15 hours overnight)
            mon_start = current.replace(hour=17) + timedelta(days=5)
            mon_end = mon_start + timedelta(hours=15)
            daily_shifts.append((mon_start, mon_end, f"{shift_type}_mon_evening"))
            
            # Tuesday Evening: 17:00 - Wednesday 08:00 (15 hours overnight)
            tue_start = current.replace(hour=17) + timedelta(days=6)
            tue_end = week_end  # This ends the waakdienst week
            daily_shifts.append((tue_start, tue_end, f"{shift_type}_tue_evening"))
        
        return daily_shifts
    
    def get_shift_template(self, shift_type: str) -> Optional[ShiftTemplate]:
        """Get or create shift template for the given type."""
        # Individual daily shift durations (hours)
        if shift_type == ShiftType.INCIDENTS:
            duration_hours = 9  # Single day 08:00-17:00
        elif shift_type == ShiftType.INCIDENTS_STANDBY:
            duration_hours = 9  # Single day 08:00-17:00
        elif shift_type == ShiftType.WAAKDIENST:
            duration_hours = 15  # Average daily shift (varies from 15-24 hours)
        else:
            duration_hours = 8  # Default
        
        template, created = ShiftTemplate.objects.get_or_create(
            shift_type=shift_type,
            defaults={
                'name': f'{shift_type.replace("_", "-").title()} Daily Shift',
                'description': f'Individual daily shift for {shift_type.replace("_", "-")}',
                'duration_hours': duration_hours,
                'is_active': True
            }
        )
        return template
    
    def assign_shifts_fairly(self, shift_type: str, weeks: List[Tuple[datetime, datetime, str]]) -> List[Dict]:
        """Assign shifts using fair distribution algorithm."""
        available_employees = self.constraint_checker.get_available_employees(shift_type)
        if not available_employees:
            logger.warning(f"No employees available for {shift_type} shifts")
            return []
        
        # Get current assignments for fairness calculation
        current_assignments = self.fairness_calculator.calculate_current_assignments(available_employees)
        
        # Sort employees by current assignment count (fairness)
        def sort_key(emp):
            emp_assignments = current_assignments.get(emp.pk, {'incidents': 0, 'incidents_standby': 0, 'waakdienst': 0})
            return emp_assignments.get(shift_type.lower(), 0)
        
        # Track assignments made in this run
        new_assignments = defaultdict(int)
        assignments = []
        
        for week_start, week_end, week_type in weeks:
            # Generate daily shifts for this week
            daily_shifts = self.generate_daily_shifts_for_week(week_start, week_end, shift_type, week_type)
            
            if not daily_shifts:
                continue
            
            # Filter employees who are available for the entire week
            eligible_employees = [
                emp for emp in available_employees
                if self.constraint_checker.is_employee_available(emp, week_start, week_end, shift_type)
            ]
            
            if not eligible_employees:
                logger.warning(f"No eligible employees for {shift_type} week {week_start}")
                continue
            
            # Sort by fairness (least assigned first) + new assignments
            eligible_employees.sort(key=lambda emp: (
                sort_key(emp) + new_assignments[emp.pk]
            ))
            
            # Assign the same engineer to ALL daily shifts for this week
            assigned_employee = eligible_employees[0]
            
            # Create individual daily shift assignments
            template = self.get_shift_template(shift_type)
            if template:
                for day_start, day_end, day_label in daily_shifts:
                    assignment = {
                        'template': template,
                        'assigned_employee': assigned_employee,
                        'start_datetime': day_start,
                        'end_datetime': day_end,
                        'shift_type': shift_type,
                        'auto_assigned': True,
                        'assignment_reason': f'Fair distribution - {shift_type} - {day_label}',
                        'week_start': week_start,
                        'week_end': week_end
                    }
                    assignments.append(assignment)
                    new_assignments[assigned_employee.pk] += 1
        
        return assignments
    
    def generate_schedule(self) -> Dict[str, Any]:
        """Generate complete schedule for the period."""
        logger.info(f"Starting orchestration for period {self.start_date} to {self.end_date}")
        logger.info(f"Shift types: incidents={self.schedule_incidents}, incidents_standby={self.schedule_incidents_standby}, waakdienst={self.schedule_waakdienst}")
        
        all_assignments = []
        
        # Generate Incidents shifts
        if self.schedule_incidents:
            incidents_weeks = self.generate_incidents_weeks()
            incidents_assignments = self.assign_shifts_fairly(ShiftType.INCIDENTS, incidents_weeks)
            all_assignments.extend(incidents_assignments)
            logger.info(f"Generated {len(incidents_assignments)} incidents daily shifts")
        
        # Generate Incidents-Standby shifts
        if self.schedule_incidents_standby:
            incidents_weeks = self.generate_incidents_weeks()  # Same weeks as incidents
            standby_assignments = self.assign_shifts_fairly(ShiftType.INCIDENTS_STANDBY, incidents_weeks)
            all_assignments.extend(standby_assignments)
            logger.info(f"Generated {len(standby_assignments)} incidents-standby daily shifts")
        
        # Generate Waakdienst shifts
        if self.schedule_waakdienst:
            waakdienst_weeks = self.generate_waakdienst_weeks()
            waakdienst_assignments = self.assign_shifts_fairly(ShiftType.WAAKDIENST, waakdienst_weeks)
            all_assignments.extend(waakdienst_assignments)
            logger.info(f"Generated {len(waakdienst_assignments)} waakdienst daily shifts")
        
        # Calculate metrics
        incidents_count = len([a for a in all_assignments if a['shift_type'] == ShiftType.INCIDENTS])
        incidents_standby_count = len([a for a in all_assignments if a['shift_type'] == ShiftType.INCIDENTS_STANDBY])
        waakdienst_count = len([a for a in all_assignments if a['shift_type'] == ShiftType.WAAKDIENST])
        
        # Calculate fairness metrics
        all_employees = list(set([a['assigned_employee'] for a in all_assignments]))
        final_assignments = self.fairness_calculator.calculate_current_assignments(all_employees)
        fairness_scores = self.fairness_calculator.calculate_fairness_score(final_assignments)
        
        result = {
            'assignments': all_assignments,
            'total_shifts': len(all_assignments),
            'incidents_shifts': incidents_count,
            'incidents_standby_shifts': incidents_standby_count,
            'waakdienst_shifts': waakdienst_count,
            'employees_assigned': len(all_employees),
            'fairness_scores': fairness_scores,
            'average_fairness': sum(fairness_scores.values()) / len(fairness_scores) if fairness_scores else 0,
            'period_start': self.start_date,
            'period_end': self.end_date
        }
        
        logger.info(f"Orchestration complete: {result['total_shifts']} daily shifts generated")
        logger.info(f"Breakdown: {incidents_count} incidents, {incidents_standby_count} incidents-standby, {waakdienst_count} waakdienst")
        return result
    
    def preview_schedule(self) -> Dict[str, Any]:
        """Generate schedule preview without saving, with duplicate detection."""
        schedule = self.generate_schedule()
        
        # Check for duplicates in preview
        potential_duplicates = []
        for assignment in schedule['assignments']:
            if self.check_for_duplicate_shifts(assignment):
                potential_duplicates.append({
                    'shift_type': assignment['template'].shift_type,
                    'start_datetime': assignment['start_datetime'],
                    'end_datetime': assignment['end_datetime'],
                    'assigned_employee': assignment['assigned_employee'].get_full_name()
                })
        
        schedule['potential_duplicates'] = potential_duplicates
        if potential_duplicates:
            logger.warning(f"Preview detected {len(potential_duplicates)} potential duplicate shifts")
            
        return schedule
    
    def check_for_duplicate_shifts(self, assignment: Dict) -> bool:
        """Check if a shift already exists for the same time period and shift type."""
        existing_shifts = Shift.objects.filter(
            template__shift_type=assignment['template'].shift_type,
            start_datetime=assignment['start_datetime'],
            end_datetime=assignment['end_datetime']
        ).exists()
        
        if existing_shifts:
            logger.warning(
                f"Duplicate shift detected: {assignment['template'].shift_type} "
                f"from {assignment['start_datetime']} to {assignment['end_datetime']}"
            )
            return True
        return False

    def apply_schedule(self) -> Dict[str, Any]:
        """Generate and save schedule to database with duplicate prevention."""
        schedule = self.generate_schedule()
        
        created_shifts = []
        skipped_duplicates = []
        
        for assignment in schedule['assignments']:
            # Check for duplicates before creating
            if self.check_for_duplicate_shifts(assignment):
                skipped_duplicates.append({
                    'shift_type': assignment['template'].shift_type,
                    'start_datetime': assignment['start_datetime'],
                    'end_datetime': assignment['end_datetime'],
                    'assigned_employee': assignment['assigned_employee'].get_full_name()
                })
                continue
                
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
        schedule['skipped_duplicates'] = skipped_duplicates
        
        if skipped_duplicates:
            logger.warning(f"Skipped {len(skipped_duplicates)} duplicate shifts")
            
        logger.info(f"Applied schedule: {len(created_shifts)} daily shifts created, {len(skipped_duplicates)} duplicates skipped")
        return schedule
