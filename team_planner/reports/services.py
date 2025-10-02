"""Report generation services."""
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

from django.contrib.auth import get_user_model
from django.db.models import Count, F, Q, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone

from team_planner.employees.models import EmployeeProfile, LeaveBalance
from team_planner.leaves.models import LeaveRequest
from team_planner.shifts.models import Shift, SwapRequest
from team_planner.teams.models import Team, TeamMembership

User = get_user_model()


class ReportService:
    """Service for generating reports."""

    @staticmethod
    def get_schedule_report(
        start_date: date | None = None,
        end_date: date | None = None,
        team_id: int | None = None,
        department_id: int | None = None,
    ) -> dict[str, Any]:
        """
        Generate schedule report for a date range.
        
        Args:
            start_date: Start date for report
            end_date: End date for report
            team_id: Filter by team
            department_id: Filter by department
            
        Returns:
            Dictionary with schedule data
        """
        # Default to current week if no dates provided
        if not start_date:
            start_date = timezone.now().date() - timedelta(days=timezone.now().weekday())
        if not end_date:
            end_date = start_date + timedelta(days=6)
            
        # Build query
        shifts = Shift.objects.select_related(
            'assigned_employee',
            'template',
            'assigned_employee__employee_profile',
        ).filter(
            start_datetime__date__gte=start_date,
            start_datetime__date__lte=end_date,
        )
        
        # Apply filters
        if team_id:
            shifts = shifts.filter(assigned_employee__teams__id=team_id)
        if department_id:
            shifts = shifts.filter(assigned_employee__teams__department__id=department_id)
            
        # Group by date and employee
        schedule_data = []
        for shift in shifts.order_by('start_datetime'):
            schedule_data.append({
                'id': shift.id,
                'date': shift.start_datetime.date(),
                'start_time': shift.start_datetime.time(),
                'end_time': shift.end_datetime.time(),
                'employee_id': shift.assigned_employee.id,
                'employee_name': shift.assigned_employee.get_full_name(),
                'shift_type': shift.template.get_shift_type_display(),
                'status': shift.get_status_display(),
                'auto_assigned': shift.auto_assigned,
            })
            
        return {
            'start_date': start_date,
            'end_date': end_date,
            'total_shifts': len(schedule_data),
            'shifts': schedule_data,
        }

    @staticmethod
    def get_fairness_distribution_report(
        team_id: int | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> dict[str, Any]:
        """
        Generate fairness distribution report showing shift distribution across employees.
        
        Args:
            team_id: Filter by team
            start_date: Start date for analysis
            end_date: End date for analysis
            
        Returns:
            Dictionary with fairness metrics
        """
        # Default to last 4 weeks if no dates provided
        if not end_date:
            end_date = timezone.now().date()
        if not start_date:
            start_date = end_date - timedelta(days=28)
            
        # Get employees
        employees = User.objects.filter(
            employee_profile__status='active',
        ).select_related('employee_profile')
        
        if team_id:
            employees = employees.filter(teams__id=team_id)
            
        # Calculate shift distribution
        distribution = []
        for employee in employees:
            shifts = Shift.objects.filter(
                assigned_employee=employee,
                start_datetime__date__gte=start_date,
                start_datetime__date__lte=end_date,
            ).select_related('template')
            
            # Count by shift type
            incidents = shifts.filter(template__shift_type='incidents').count()
            waakdienst = shifts.filter(template__shift_type='waakdienst').count()
            standby = shifts.filter(template__shift_type='incidents_standby').count()
            
            # Calculate total hours
            total_hours = Decimal('0')
            for shift in shifts:
                duration = shift.end_datetime - shift.start_datetime
                total_hours += Decimal(str(duration.total_seconds() / 3600))
                
            # Get FTE from team membership
            fte = Decimal('1.0')
            if team_id:
                membership = TeamMembership.objects.filter(
                    user=employee,
                    team_id=team_id,
                    is_active=True,
                ).first()
                if membership:
                    fte = membership.fte
                    
            distribution.append({
                'employee_id': employee.id,
                'employee_name': employee.get_full_name(),
                'fte': float(fte),
                'total_shifts': shifts.count(),
                'total_hours': float(total_hours),
                'incidents_count': incidents,
                'waakdienst_count': waakdienst,
                'standby_count': standby,
                'hours_per_fte': float(total_hours / fte) if fte > 0 else 0,
            })
            
        # Sort by hours per FTE for fairness comparison
        distribution.sort(key=lambda x: x['hours_per_fte'], reverse=True)
        
        # Calculate fairness metrics
        if distribution:
            avg_hours_per_fte = sum(e['hours_per_fte'] for e in distribution) / len(distribution)
            max_hours = max(e['hours_per_fte'] for e in distribution)
            min_hours = min(e['hours_per_fte'] for e in distribution)
            variance = max_hours - min_hours
        else:
            avg_hours_per_fte = 0
            max_hours = 0
            min_hours = 0
            variance = 0
            
        return {
            'start_date': start_date,
            'end_date': end_date,
            'team_id': team_id,
            'employee_count': len(distribution),
            'average_hours_per_fte': round(avg_hours_per_fte, 2),
            'max_hours_per_fte': round(max_hours, 2),
            'min_hours_per_fte': round(min_hours, 2),
            'variance': round(variance, 2),
            'distribution': distribution,
        }

    @staticmethod
    def get_leave_balance_report(
        employee_id: int | None = None,
        team_id: int | None = None,
        year: int | None = None,
    ) -> dict[str, Any]:
        """
        Generate leave balance report.
        
        Args:
            employee_id: Filter by employee
            team_id: Filter by team
            year: Filter by year
            
        Returns:
            Dictionary with leave balance data
        """
        if not year:
            year = timezone.now().year
            
        # Get leave balances
        balances = LeaveBalance.objects.filter(year=year).select_related(
            'employee__user',
            'leave_type',
        )
        
        if employee_id:
            balances = balances.filter(employee__user_id=employee_id)
        if team_id:
            balances = balances.filter(employee__user__teams__id=team_id)
            
        # Build report data
        balance_data = []
        for balance in balances:
            balance_data.append({
                'employee_id': balance.employee.user.id,
                'employee_name': balance.employee.user.get_full_name(),
                'leave_type': balance.leave_type.name,
                'total_days': float(balance.total_days),
                'used_days': float(balance.used_days),
                'remaining_days': float(balance.remaining_days),
                'is_exhausted': balance.is_exhausted,
            })
            
        return {
            'year': year,
            'total_balances': len(balance_data),
            'balances': balance_data,
        }

    @staticmethod
    def get_swap_history_report(
        employee_id: int | None = None,
        team_id: int | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> dict[str, Any]:
        """
        Generate swap history report.
        
        Args:
            employee_id: Filter by employee
            team_id: Filter by team
            start_date: Start date for report
            end_date: End date for report
            
        Returns:
            Dictionary with swap history data
        """
        # Default to last 3 months if no dates provided
        if not end_date:
            end_date = timezone.now().date()
        if not start_date:
            start_date = end_date - timedelta(days=90)
            
        # Get swap requests
        swaps = SwapRequest.objects.select_related(
            'requesting_employee',
            'target_employee',
            'requesting_shift__template',
            'target_shift__template',
        ).filter(
            created__date__gte=start_date,
            created__date__lte=end_date,
        )
        
        if employee_id:
            swaps = swaps.filter(
                Q(requesting_employee_id=employee_id) | Q(target_employee_id=employee_id)
            )
        if team_id:
            swaps = swaps.filter(
                Q(requesting_employee__teams__id=team_id) | Q(target_employee__teams__id=team_id)
            )
            
        # Build report data
        swap_data = []
        for swap in swaps.order_by('-created'):
            swap_data.append({
                'id': swap.id,
                'created_date': swap.created.date(),
                'requesting_employee': swap.requesting_employee.get_full_name(),
                'target_employee': swap.target_employee.get_full_name(),
                'requesting_shift_date': swap.requesting_shift.start_datetime.date(),
                'target_shift_date': swap.target_shift.start_datetime.date() if swap.target_shift else None,
                'status': swap.get_status_display(),
                'approved_date': swap.approved_at.date() if swap.approved_at else None,
            })
            
        # Calculate statistics
        total_swaps = len(swap_data)
        approved = sum(1 for s in swap_data if s['status'] == 'Approved')
        rejected = sum(1 for s in swap_data if s['status'] == 'Rejected')
        pending = sum(1 for s in swap_data if s['status'] == 'Pending')
        
        return {
            'start_date': start_date,
            'end_date': end_date,
            'total_swaps': total_swaps,
            'approved_count': approved,
            'rejected_count': rejected,
            'pending_count': pending,
            'approval_rate': round((approved / total_swaps * 100) if total_swaps > 0 else 0, 2),
            'swaps': swap_data,
        }

    @staticmethod
    def get_employee_hours_report(
        employee_id: int | None = None,
        team_id: int | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> dict[str, Any]:
        """
        Generate employee hours worked report.
        
        Args:
            employee_id: Filter by employee
            team_id: Filter by team
            start_date: Start date for report
            end_date: End date for report
            
        Returns:
            Dictionary with hours worked data
        """
        # Default to current month if no dates provided
        if not end_date:
            end_date = timezone.now().date()
        if not start_date:
            start_date = end_date.replace(day=1)
            
        # Get employees
        employees = User.objects.filter(
            employee_profile__status='active',
        ).select_related('employee_profile')
        
        if employee_id:
            employees = employees.filter(id=employee_id)
        if team_id:
            employees = employees.filter(teams__id=team_id)
            
        # Calculate hours for each employee
        hours_data = []
        for employee in employees:
            shifts = Shift.objects.filter(
                assigned_employee=employee,
                start_datetime__date__gte=start_date,
                start_datetime__date__lte=end_date,
                status__in=['completed', 'confirmed', 'scheduled'],
            ).select_related('template')
            
            # Calculate hours by shift type
            total_hours = Decimal('0')
            incidents_hours = Decimal('0')
            waakdienst_hours = Decimal('0')
            
            for shift in shifts:
                duration = shift.end_datetime - shift.start_datetime
                hours = Decimal(str(duration.total_seconds() / 3600))
                total_hours += hours
                
                if shift.template.shift_type == 'incidents':
                    incidents_hours += hours
                elif shift.template.shift_type in ['waakdienst', 'incidents_standby']:
                    waakdienst_hours += hours
                    
            hours_data.append({
                'employee_id': employee.id,
                'employee_name': employee.get_full_name(),
                'total_hours': float(total_hours),
                'incidents_hours': float(incidents_hours),
                'waakdienst_hours': float(waakdienst_hours),
                'shift_count': shifts.count(),
            })
            
        # Sort by total hours
        hours_data.sort(key=lambda x: x['total_hours'], reverse=True)
        
        return {
            'start_date': start_date,
            'end_date': end_date,
            'employee_count': len(hours_data),
            'total_hours': sum(e['total_hours'] for e in hours_data),
            'hours': hours_data,
        }

    @staticmethod
    def get_weekend_holiday_distribution_report(
        team_id: int | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> dict[str, Any]:
        """
        Generate weekend and holiday distribution report.
        
        Args:
            team_id: Filter by team
            start_date: Start date for analysis
            end_date: End date for analysis
            
        Returns:
            Dictionary with weekend/holiday distribution data
        """
        # Default to last 3 months if no dates provided
        if not end_date:
            end_date = timezone.now().date()
        if not start_date:
            start_date = end_date - timedelta(days=90)
            
        # Get employees
        employees = User.objects.filter(
            employee_profile__status='active',
        ).select_related('employee_profile')
        
        if team_id:
            employees = employees.filter(teams__id=team_id)
            
        # Calculate weekend/holiday shifts
        distribution = []
        for employee in employees:
            shifts = Shift.objects.filter(
                assigned_employee=employee,
                start_datetime__date__gte=start_date,
                start_datetime__date__lte=end_date,
            )
            
            # Count weekend shifts (Saturday=5, Sunday=6)
            weekend_shifts = sum(
                1 for shift in shifts 
                if shift.start_datetime.weekday() in [5, 6]
            )
            
            # For holidays, we'd need a holiday calendar - simplified for now
            # In a real implementation, integrate with workalendar or similar
            holiday_shifts = 0  # Placeholder
            
            distribution.append({
                'employee_id': employee.id,
                'employee_name': employee.get_full_name(),
                'weekend_shifts': weekend_shifts,
                'holiday_shifts': holiday_shifts,
                'total_special_shifts': weekend_shifts + holiday_shifts,
            })
            
        # Sort by total special shifts
        distribution.sort(key=lambda x: x['total_special_shifts'], reverse=True)
        
        return {
            'start_date': start_date,
            'end_date': end_date,
            'team_id': team_id,
            'employee_count': len(distribution),
            'total_weekend_shifts': sum(e['weekend_shifts'] for e in distribution),
            'total_holiday_shifts': sum(e['holiday_shifts'] for e in distribution),
            'distribution': distribution,
        }
