"""
Conflict Detection Service for Team Planner

Detects scheduling conflicts across 4 categories:
1. Double-booking: Same employee, overlapping shift times
2. Leave conflicts: Shift scheduled during approved leave
3. Over-scheduled: Employee exceeds max hours per week/month
4. Skill mismatch: Employee lacks required skills for shift type

Usage:
    from team_planner.shifts.services.conflict_detector import ConflictDetector
    
    detector = ConflictDetector()
    conflicts = detector.detect_all_conflicts(start_date, end_date)
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from django.db.models import Q, Sum, F
from django.utils import timezone

from team_planner.shifts.models import Shift, ShiftAssignment, Leave, ShiftType
from team_planner.employees.models import Employee


class ConflictType:
    """Enum-like class for conflict types"""
    DOUBLE_BOOKING = 'double_booking'
    LEAVE_CONFLICT = 'leave_conflict'
    OVER_SCHEDULED = 'over_scheduled'
    SKILL_MISMATCH = 'skill_mismatch'


class ConflictSeverity:
    """Enum-like class for conflict severity"""
    HIGH = 'high'
    MEDIUM = 'medium'
    LOW = 'low'


class ConflictDetector:
    """Service for detecting scheduling conflicts"""
    
    # Configuration
    MAX_HOURS_PER_WEEK = 48  # Maximum hours per week per employee
    MAX_HOURS_PER_MONTH = 200  # Maximum hours per month per employee
    
    def __init__(self):
        self.conflicts = []
    
    def detect_all_conflicts(
        self,
        start_date: datetime,
        end_date: datetime,
        employee_id: Optional[int] = None
    ) -> Dict[int, List[Dict[str, Any]]]:
        """
        Detect all conflicts for shifts in the given date range.
        
        Args:
            start_date: Start of date range to check
            end_date: End of date range to check
            employee_id: Optional filter for specific employee
            
        Returns:
            Dictionary mapping shift_id to list of conflicts
        """
        self.conflicts = []
        
        # Get all assignments in date range
        assignments = ShiftAssignment.objects.filter(
            shift__start_time__gte=start_date,
            shift__start_time__lte=end_date
        ).select_related('shift', 'shift__shift_type', 'employee')
        
        if employee_id:
            assignments = assignments.filter(employee_id=employee_id)
        
        # Build conflict dictionary
        conflict_dict = {}
        
        for assignment in assignments:
            shift_conflicts = []
            
            # Check each conflict type
            shift_conflicts.extend(self._check_double_booking(assignment))
            shift_conflicts.extend(self._check_leave_conflicts(assignment))
            shift_conflicts.extend(self._check_over_scheduled(assignment))
            shift_conflicts.extend(self._check_skill_mismatch(assignment))
            
            if shift_conflicts:
                conflict_dict[assignment.shift.id] = shift_conflicts
        
        return conflict_dict
    
    def _check_double_booking(
        self,
        assignment: ShiftAssignment
    ) -> List[Dict[str, Any]]:
        """
        Check if employee has overlapping shifts.
        
        Args:
            assignment: The shift assignment to check
            
        Returns:
            List of double-booking conflicts
        """
        conflicts = []
        
        shift = assignment.shift
        employee = assignment.employee
        
        # Find overlapping shifts for same employee
        overlapping = ShiftAssignment.objects.filter(
            employee=employee,
            shift__start_time__lt=shift.end_time,
            shift__end_time__gt=shift.start_time
        ).exclude(
            shift_id=shift.id
        ).select_related('shift')
        
        for overlap in overlapping:
            conflicts.append({
                'type': ConflictType.DOUBLE_BOOKING,
                'severity': ConflictSeverity.HIGH,
                'message': f'Overlaps with shift #{overlap.shift.id}',
                'details': {
                    'conflicting_shift_id': overlap.shift.id,
                    'conflicting_shift_start': overlap.shift.start_time.isoformat(),
                    'conflicting_shift_end': overlap.shift.end_time.isoformat(),
                    'overlap_hours': self._calculate_overlap_hours(
                        shift.start_time,
                        shift.end_time,
                        overlap.shift.start_time,
                        overlap.shift.end_time
                    )
                },
                'suggestion': 'Reassign one shift or adjust times to avoid overlap'
            })
        
        return conflicts
    
    def _check_leave_conflicts(
        self,
        assignment: ShiftAssignment
    ) -> List[Dict[str, Any]]:
        """
        Check if employee is on approved leave during shift.
        
        Args:
            assignment: The shift assignment to check
            
        Returns:
            List of leave conflicts
        """
        conflicts = []
        
        shift = assignment.shift
        employee = assignment.employee
        
        # Find approved leave overlapping with shift
        overlapping_leaves = Leave.objects.filter(
            employee=employee,
            status='approved',
            start_date__lt=shift.end_time.date(),
            end_date__gt=shift.start_time.date()
        )
        
        for leave in overlapping_leaves:
            # Determine severity based on leave type
            severity = ConflictSeverity.HIGH if leave.leave_type in ['sick', 'emergency'] else ConflictSeverity.MEDIUM
            
            conflicts.append({
                'type': ConflictType.LEAVE_CONFLICT,
                'severity': severity,
                'message': f'Employee on {leave.leave_type} leave',
                'details': {
                    'leave_id': leave.id,
                    'leave_type': leave.leave_type,
                    'leave_start': leave.start_date.isoformat(),
                    'leave_end': leave.end_date.isoformat(),
                    'leave_status': leave.status
                },
                'suggestion': f'Find replacement or cancel {"urgent - " if severity == ConflictSeverity.HIGH else ""}shift'
            })
        
        return conflicts
    
    def _check_over_scheduled(
        self,
        assignment: ShiftAssignment
    ) -> List[Dict[str, Any]]:
        """
        Check if employee exceeds maximum hours per week/month.
        
        Args:
            assignment: The shift assignment to check
            
        Returns:
            List of over-scheduling conflicts
        """
        conflicts = []
        
        shift = assignment.shift
        employee = assignment.employee
        
        # Calculate shift duration
        shift_hours = (shift.end_time - shift.start_time).total_seconds() / 3600
        
        # Check weekly hours
        week_start = shift.start_time - timedelta(days=shift.start_time.weekday())
        week_end = week_start + timedelta(days=7)
        
        weekly_hours = ShiftAssignment.objects.filter(
            employee=employee,
            shift__start_time__gte=week_start,
            shift__start_time__lt=week_end
        ).annotate(
            duration=F('shift__end_time') - F('shift__start_time')
        ).aggregate(
            total=Sum('duration')
        )['total']
        
        if weekly_hours:
            total_weekly_seconds = weekly_hours.total_seconds()
            total_weekly_hours = total_weekly_seconds / 3600
            
            if total_weekly_hours > self.MAX_HOURS_PER_WEEK:
                conflicts.append({
                    'type': ConflictType.OVER_SCHEDULED,
                    'severity': ConflictSeverity.MEDIUM,
                    'message': f'Exceeds weekly limit: {total_weekly_hours:.1f}h / {self.MAX_HOURS_PER_WEEK}h',
                    'details': {
                        'period': 'week',
                        'current_hours': total_weekly_hours,
                        'max_hours': self.MAX_HOURS_PER_WEEK,
                        'excess_hours': total_weekly_hours - self.MAX_HOURS_PER_WEEK,
                        'week_start': week_start.isoformat(),
                        'week_end': week_end.isoformat()
                    },
                    'suggestion': 'Reduce shift hours or reassign some shifts to other employees'
                })
        
        # Check monthly hours
        month_start = shift.start_time.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if shift.start_time.month == 12:
            month_end = month_start.replace(year=month_start.year + 1, month=1)
        else:
            month_end = month_start.replace(month=month_start.month + 1)
        
        monthly_hours = ShiftAssignment.objects.filter(
            employee=employee,
            shift__start_time__gte=month_start,
            shift__start_time__lt=month_end
        ).annotate(
            duration=F('shift__end_time') - F('shift__start_time')
        ).aggregate(
            total=Sum('duration')
        )['total']
        
        if monthly_hours:
            total_monthly_seconds = monthly_hours.total_seconds()
            total_monthly_hours = total_monthly_seconds / 3600
            
            if total_monthly_hours > self.MAX_HOURS_PER_MONTH:
                conflicts.append({
                    'type': ConflictType.OVER_SCHEDULED,
                    'severity': ConflictSeverity.LOW,
                    'message': f'Exceeds monthly limit: {total_monthly_hours:.1f}h / {self.MAX_HOURS_PER_MONTH}h',
                    'details': {
                        'period': 'month',
                        'current_hours': total_monthly_hours,
                        'max_hours': self.MAX_HOURS_PER_MONTH,
                        'excess_hours': total_monthly_hours - self.MAX_HOURS_PER_MONTH,
                        'month_start': month_start.isoformat(),
                        'month_end': month_end.isoformat()
                    },
                    'suggestion': 'Distribute workload across multiple employees or schedule overtime approval'
                })
        
        return conflicts
    
    def _check_skill_mismatch(
        self,
        assignment: ShiftAssignment
    ) -> List[Dict[str, Any]]:
        """
        Check if employee has required skills for shift type.
        
        Args:
            assignment: The shift assignment to check
            
        Returns:
            List of skill mismatch conflicts
        """
        conflicts = []
        
        shift = assignment.shift
        employee = assignment.employee
        
        # Check if shift type has required skills
        if not shift.shift_type:
            return conflicts
        
        # Get required skills for shift type
        required_skills = getattr(shift.shift_type, 'required_skills', None)
        if not required_skills:
            return conflicts
        
        # Get employee skills
        employee_skills = set(getattr(employee, 'skills', []))
        
        # Check for missing skills
        if isinstance(required_skills, (list, set)):
            required_skills_set = set(required_skills)
            missing_skills = required_skills_set - employee_skills
            
            if missing_skills:
                conflicts.append({
                    'type': ConflictType.SKILL_MISMATCH,
                    'severity': ConflictSeverity.MEDIUM,
                    'message': f'Missing required skills: {", ".join(missing_skills)}',
                    'details': {
                        'required_skills': list(required_skills_set),
                        'employee_skills': list(employee_skills),
                        'missing_skills': list(missing_skills),
                        'shift_type_name': shift.shift_type.name
                    },
                    'suggestion': 'Assign to qualified employee or provide training'
                })
        
        return conflicts
    
    def _calculate_overlap_hours(
        self,
        start1: datetime,
        end1: datetime,
        start2: datetime,
        end2: datetime
    ) -> float:
        """
        Calculate hours of overlap between two time periods.
        
        Args:
            start1: Start of first period
            end1: End of first period
            start2: Start of second period
            end2: End of second period
            
        Returns:
            Hours of overlap
        """
        latest_start = max(start1, start2)
        earliest_end = min(end1, end2)
        
        if latest_start >= earliest_end:
            return 0.0
        
        overlap = earliest_end - latest_start
        return overlap.total_seconds() / 3600
    
    def get_conflict_summary(
        self,
        conflicts: Dict[int, List[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """
        Generate summary statistics for conflicts.
        
        Args:
            conflicts: Dictionary of conflicts by shift_id
            
        Returns:
            Summary statistics
        """
        total_conflicts = sum(len(c) for c in conflicts.values())
        
        conflict_counts = {
            ConflictType.DOUBLE_BOOKING: 0,
            ConflictType.LEAVE_CONFLICT: 0,
            ConflictType.OVER_SCHEDULED: 0,
            ConflictType.SKILL_MISMATCH: 0
        }
        
        severity_counts = {
            ConflictSeverity.HIGH: 0,
            ConflictSeverity.MEDIUM: 0,
            ConflictSeverity.LOW: 0
        }
        
        for shift_conflicts in conflicts.values():
            for conflict in shift_conflicts:
                conflict_counts[conflict['type']] += 1
                severity_counts[conflict['severity']] += 1
        
        return {
            'total_conflicts': total_conflicts,
            'affected_shifts': len(conflicts),
            'by_type': conflict_counts,
            'by_severity': severity_counts
        }
