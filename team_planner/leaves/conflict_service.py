"""
Leave Conflict Resolution Service.

This module provides functionality for:
- Detecting overlapping leave requests
- Analyzing staffing levels during leave periods
- Suggesting alternative dates
- Priority-based conflict resolution
- Manager override workflow
"""

from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q, Count, Sum
from django.utils import timezone

from ..leaves.models import LeaveRequest, LeaveType
from ..shifts.models import Shift

User = get_user_model()


class LeaveConflictDetector:
    """Service for detecting leave conflicts and understaffing."""
    
    @staticmethod
    def detect_overlapping_requests(
        employee: User,
        start_date: date,
        end_date: date,
        exclude_request_id: Optional[int] = None,
    ) -> List[LeaveRequest]:
        """
        Find overlapping leave requests for the same employee.
        
        Args:
            employee: The employee requesting leave
            start_date: Start date of the leave
            end_date: End date of the leave
            exclude_request_id: Request ID to exclude (for updates)
            
        Returns:
            List of overlapping LeaveRequest objects
        """
        overlapping = LeaveRequest.objects.filter(
            employee=employee,
            status__in=[LeaveRequest.Status.PENDING, LeaveRequest.Status.APPROVED],
            start_date__lte=end_date,
            end_date__gte=start_date,
        )
        
        if exclude_request_id:
            overlapping = overlapping.exclude(id=exclude_request_id)
        
        return list(overlapping.select_related('leave_type'))
    
    @staticmethod
    def detect_team_conflicts(
        start_date: date,
        end_date: date,
        team_id: Optional[int] = None,
        department_id: Optional[int] = None,
    ) -> Dict:
        """
        Detect conflicts where multiple team members request the same dates.
        
        Args:
            start_date: Start date to check
            end_date: End date to check
            team_id: Optional team filter
            department_id: Optional department filter
            
        Returns:
            Dict with conflict analysis per day
        """
        # Get all approved/pending leave requests in the date range
        leave_requests = LeaveRequest.objects.filter(
            status__in=[LeaveRequest.Status.PENDING, LeaveRequest.Status.APPROVED],
            start_date__lte=end_date,
            end_date__gte=start_date,
        ).select_related('employee', 'leave_type')
        
        # Filter by team/department if provided
        if team_id:
            leave_requests = leave_requests.filter(
                employee__employee_profile__teams__id=team_id
            )
        if department_id:
            leave_requests = leave_requests.filter(
                employee__employee_profile__department_id=department_id
            )
        
        # Build day-by-day analysis
        conflicts_by_day = {}
        current_date = start_date
        
        while current_date <= end_date:
            day_leaves = [
                lr for lr in leave_requests
                if lr.start_date <= current_date <= lr.end_date
            ]
            
            conflicts_by_day[current_date.isoformat()] = {
                'date': current_date,
                'leave_count': len(day_leaves),
                'employees_on_leave': [
                    {
                        'id': lr.employee.id,
                        'name': lr.employee.get_full_name(),
                        'leave_type': lr.leave_type.name,
                        'request_id': lr.id,
                    }
                    for lr in day_leaves
                ],
            }
            
            current_date += timedelta(days=1)
        
        return conflicts_by_day
    
    @staticmethod
    def analyze_staffing_levels(
        start_date: date,
        end_date: date,
        team_id: Optional[int] = None,
        department_id: Optional[int] = None,
        min_required_staff: int = 1,
    ) -> Dict:
        """
        Analyze if staffing levels are adequate during leave period.
        
        Args:
            start_date: Start date to analyze
            end_date: End date to analyze
            team_id: Optional team filter
            department_id: Optional department filter
            min_required_staff: Minimum required staff per day
            
        Returns:
            Dict with staffing analysis
        """
        from ..employees.models import EmployeeProfile
        
        # Get total team size
        team_members = User.objects.filter(is_active=True)
        if team_id:
            team_members = team_members.filter(employee_profile__teams__id=team_id)
        if department_id:
            team_members = team_members.filter(
                employee_profile__department_id=department_id
            )
        
        total_team_size = team_members.count()
        
        # Get conflicts by day
        conflicts = LeaveConflictDetector.detect_team_conflicts(
            start_date, end_date, team_id, department_id
        )
        
        # Analyze each day
        understaffed_days = []
        warning_days = []
        
        for day_key, day_data in conflicts.items():
            leave_count = day_data['leave_count']
            available_staff = total_team_size - leave_count
            
            if available_staff < min_required_staff:
                understaffed_days.append({
                    'date': day_data['date'],
                    'available_staff': available_staff,
                    'required_staff': min_required_staff,
                    'shortage': min_required_staff - available_staff,
                    'on_leave': day_data['employees_on_leave'],
                })
            elif available_staff < (min_required_staff + 1):
                # Warning: close to understaffing
                warning_days.append({
                    'date': day_data['date'],
                    'available_staff': available_staff,
                    'required_staff': min_required_staff,
                    'on_leave': day_data['employees_on_leave'],
                })
        
        return {
            'total_team_size': total_team_size,
            'min_required_staff': min_required_staff,
            'is_understaffed': len(understaffed_days) > 0,
            'understaffed_days': understaffed_days,
            'warning_days': warning_days,
            'total_days_analyzed': (end_date - start_date).days + 1,
        }
    
    @staticmethod
    def suggest_alternative_dates(
        employee: User,
        start_date: date,
        days_requested: int,
        team_id: Optional[int] = None,
        department_id: Optional[int] = None,
        search_window_days: int = 60,
    ) -> List[Dict]:
        """
        Suggest alternative date ranges with fewer conflicts.
        
        Args:
            employee: The employee requesting leave
            start_date: Original start date
            days_requested: Number of days needed
            team_id: Optional team filter
            department_id: Optional department filter
            search_window_days: Days before/after to search
            
        Returns:
            List of suggested date ranges sorted by preference
        """
        suggestions = []
        
        # Search in windows around the requested date
        search_start = start_date - timedelta(days=search_window_days)
        search_end = start_date + timedelta(days=search_window_days)
        
        # Try different start dates
        current_test_date = search_start
        while current_test_date <= search_end:
            test_end_date = current_test_date + timedelta(days=days_requested - 1)
            
            # Skip if this is the original request date
            if current_test_date == start_date:
                current_test_date += timedelta(days=1)
                continue
            
            # Check for conflicts
            personal_conflicts = LeaveConflictDetector.detect_overlapping_requests(
                employee, current_test_date, test_end_date
            )
            
            if not personal_conflicts:
                # Check team staffing
                staffing = LeaveConflictDetector.analyze_staffing_levels(
                    current_test_date,
                    test_end_date,
                    team_id,
                    department_id,
                )
                
                conflict_score = len(staffing['understaffed_days']) * 10 + \
                                len(staffing['warning_days']) * 5
                
                suggestions.append({
                    'start_date': current_test_date,
                    'end_date': test_end_date,
                    'conflict_score': conflict_score,
                    'is_understaffed': staffing['is_understaffed'],
                    'available_staff_avg': staffing['total_team_size'] - \
                        (len(staffing['understaffed_days']) + len(staffing['warning_days'])),
                    'days_offset': (current_test_date - start_date).days,
                })
            
            current_test_date += timedelta(days=1)
        
        # Sort by conflict score (lower is better)
        suggestions.sort(key=lambda x: (x['is_understaffed'], x['conflict_score'], abs(x['days_offset'])))
        
        return suggestions[:5]  # Return top 5 alternatives
    
    @staticmethod
    def get_shift_conflicts(
        employee: User,
        start_date: date,
        end_date: date,
    ) -> List[Shift]:
        """
        Get shifts that would conflict with the leave request.
        
        Args:
            employee: The employee
            start_date: Leave start date
            end_date: Leave end date
            
        Returns:
            List of conflicting Shift objects
        """
        return list(Shift.objects.filter(
            assigned_employee=employee,
            start_datetime__date__lte=end_date,
            end_datetime__date__gte=start_date,
            status__in=["scheduled", "confirmed"],
        ).select_related('template').order_by('start_datetime'))


class LeaveConflictResolver:
    """Service for resolving leave conflicts."""
    
    class Priority(int):
        """Priority levels for conflict resolution."""
        SENIORITY = 1
        FIRST_REQUEST = 2
        LEAVE_BALANCE = 3
        ROTATION = 4
        MANAGER_OVERRIDE = 99
    
    @staticmethod
    def resolve_by_priority(
        conflicting_requests: List[LeaveRequest],
        priority_rule: Priority,
    ) -> Optional[LeaveRequest]:
        """
        Resolve conflicts using priority rules.
        
        Args:
            conflicting_requests: List of conflicting leave requests
            priority_rule: Priority rule to apply
            
        Returns:
            The request that should be approved, or None
        """
        if not conflicting_requests:
            return None
        
        if priority_rule == LeaveConflictResolver.Priority.SENIORITY:
            # Approve based on seniority (earliest date_joined)
            return min(
                conflicting_requests,
                key=lambda r: r.employee.date_joined
            )
        
        elif priority_rule == LeaveConflictResolver.Priority.FIRST_REQUEST:
            # Approve whoever requested first
            return min(
                conflicting_requests,
                key=lambda r: r.created
            )
        
        elif priority_rule == LeaveConflictResolver.Priority.LEAVE_BALANCE:
            # Approve whoever has used less leave this year
            from ..employees.models import LeaveBalance
            
            def get_used_days(request):
                balance = LeaveBalance.objects.filter(
                    employee=request.employee,
                    leave_type=request.leave_type,
                    year=date.today().year,
                ).first()
                return balance.used if balance else Decimal('0')
            
            return min(
                conflicting_requests,
                key=get_used_days
            )
        
        elif priority_rule == LeaveConflictResolver.Priority.ROTATION:
            # Approve based on who was denied last time
            # This would require tracking denials - placeholder implementation
            return conflicting_requests[0]
        
        return None
    
    @staticmethod
    @transaction.atomic
    def apply_resolution(
        request_to_approve: LeaveRequest,
        requests_to_reject: List[LeaveRequest],
        resolved_by: User,
        resolution_notes: str = "",
    ) -> Dict:
        """
        Apply a conflict resolution decision.
        
        Args:
            request_to_approve: Request to approve
            requests_to_reject: Requests to reject
            resolved_by: User making the decision
            resolution_notes: Notes about the resolution
            
        Returns:
            Dict with resolution results
        """
        from ..notifications.services import NotificationService
        
        # Approve the selected request
        request_to_approve.status = LeaveRequest.Status.APPROVED
        request_to_approve.approved_by = resolved_by
        request_to_approve.approved_at = timezone.now()
        request_to_approve.save()
        
        # Send approval notification
        NotificationService.notify_leave_approved(
            leave_request=request_to_approve,
            recipient=request_to_approve.employee,
        )
        
        # Reject conflicting requests
        rejected_ids = []
        for request in requests_to_reject:
            request.status = LeaveRequest.Status.REJECTED
            request.rejection_reason = f"Conflict resolution: {resolution_notes}"
            request.save()
            
            rejected_ids.append(request.id)
            
            # Send rejection notification
            NotificationService.notify_leave_rejected(
                leave_request=request,
                recipient=request.employee,
                rejection_reason=request.rejection_reason,
            )
        
        return {
            'approved_request_id': request_to_approve.id,
            'rejected_request_ids': rejected_ids,
            'resolved_by': resolved_by.get_full_name(),
            'resolution_notes': resolution_notes,
        }
    
    @staticmethod
    def get_recommended_resolution(
        conflicting_requests: List[LeaveRequest],
    ) -> Dict:
        """
        Get recommended resolution based on multiple priority rules.
        
        Args:
            conflicting_requests: List of conflicting requests
            
        Returns:
            Dict with recommendations
        """
        if not conflicting_requests:
            return {'recommended': None, 'alternatives': []}
        
        recommendations = {}
        
        # Try each priority rule
        recommendations['by_seniority'] = LeaveConflictResolver.resolve_by_priority(
            conflicting_requests, LeaveConflictResolver.Priority.SENIORITY
        )
        recommendations['by_first_request'] = LeaveConflictResolver.resolve_by_priority(
            conflicting_requests, LeaveConflictResolver.Priority.FIRST_REQUEST
        )
        recommendations['by_leave_balance'] = LeaveConflictResolver.resolve_by_priority(
            conflicting_requests, LeaveConflictResolver.Priority.LEAVE_BALANCE
        )
        
        # Count which request is recommended most often
        vote_counts = {}
        for rule_name, request in recommendations.items():
            if request:
                vote_counts[request.id] = vote_counts.get(request.id, 0) + 1
        
        # Get the request with most votes
        if vote_counts:
            recommended_id = max(vote_counts.items(), key=lambda x: x[1])[0]
            recommended = next(r for r in conflicting_requests if r.id == recommended_id)
        else:
            recommended = conflicting_requests[0]
        
        return {
            'recommended': recommended,
            'recommendation_details': {
                'by_seniority': recommendations['by_seniority'].id if recommendations['by_seniority'] else None,
                'by_first_request': recommendations['by_first_request'].id if recommendations['by_first_request'] else None,
                'by_leave_balance': recommendations['by_leave_balance'].id if recommendations['by_leave_balance'] else None,
            },
            'vote_counts': vote_counts,
            'alternatives': [r for r in conflicting_requests if r.id != recommended.id],
        }
