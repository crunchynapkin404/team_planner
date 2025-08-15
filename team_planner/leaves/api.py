from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from django.db.models import Q, QuerySet
from datetime import datetime
from django.utils.dateparse import parse_date
from django.utils import timezone

from .models import LeaveRequest, LeaveType
from .serializers import LeaveRequestSerializer, LeaveTypeSerializer
from team_planner.notifications.mailer import notify_leave_approved, build_ics_for_leave

User = get_user_model()


class LeaveRequestViewSet(viewsets.ModelViewSet):
    """ViewSet for managing leave requests."""
    queryset = LeaveRequest.objects.all()
    serializer_class = LeaveRequestSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self) -> QuerySet[LeaveRequest]:
        """Return leave requests based on user permissions.
        Be resilient if self.request isn't set (e.g., when actions are called directly in tests).
        """
        # Base queryset
        queryset = LeaveRequest.objects.select_related(
            'employee', 'leave_type', 'approved_by'
        ).order_by('-created')

        req = getattr(self, 'request', None)
        user = getattr(req, 'user', None)
        if not user:
            # No request/user available (e.g., direct method call in tests); return unfiltered
            return queryset
        
        # Filter based on permissions
        if user.has_perm('leaves.change_leaverequest') or user.is_staff or user.is_superuser:
            # Staff, admins, and users with change permission can see all requests
            return queryset
        else:
            # Regular users can only see their own requests
            return queryset.filter(employee=user)
    
    def perform_create(self, serializer):
        """Set the employee to the current user when creating a leave request."""
        serializer.save(employee=self.request.user)
    
    @action(detail=False, methods=['post'], url_path='create')
    def create_request(self, request):
        """Create a new leave request (alternative endpoint)."""
        # Ensure view has a request when called directly
        self.request = request
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            self.perform_create(serializer)
            instance = getattr(serializer, 'instance', None)
            return Response({
                'id': int(getattr(instance, 'id', 0)),
                'message': 'Leave request created successfully.',
                'has_conflicts': bool(getattr(instance, 'has_shift_conflicts', False)),
                'conflict_warning': 'This request conflicts with assigned shifts.' if getattr(instance, 'has_shift_conflicts', False) else None
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def my_requests(self, request):
        """Get current user's leave requests."""
        # Ensure view has a request when called directly
        self.request = request
        queryset = self.get_queryset().filter(employee=request.user)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def pending(self, request):
        """Get pending leave requests."""
        # Ensure view has a request when called directly
        self.request = request
        queryset = self.get_queryset().filter(status='pending')
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve a leave request."""
        # Ensure view has a request when called directly
        self.request = request
        leave_request = self.get_object()
        user = request.user
        
        # Check if user has permission to approve
        if not (user.has_perm('leaves.change_leaverequest') or user.is_staff or user.is_superuser):
            return Response(
                {'error': 'You do not have permission to approve leave requests.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if leave_request.status != 'pending':
            return Response(
                {'error': 'Leave request is not in pending status.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if leave can be approved (no unresolved shift conflicts)
        if not leave_request.can_be_approved():
            return Response(
                {
                    'error': 'Cannot approve leave request. There are unresolved shift conflicts.',
                    'detail': 'All conflicting shifts must have approved swap requests before the leave can be approved.',
                    'blocking_message': leave_request.get_blocking_message()
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        leave_request.status = 'approved'
        leave_request.approved_by = user
        from django.utils import timezone
        leave_request.approved_at = timezone.now()
        leave_request.save()
        
        # Notify employee with ICS
        try:
            ics = build_ics_for_leave(leave_request)
            email = getattr(leave_request.employee, 'email', None)
            notify_leave_approved(email, ics)
        except Exception:
            pass
        
        serializer = self.get_serializer(leave_request)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject a leave request."""
        # Ensure view has a request when called directly
        self.request = request
        leave_request = self.get_object()
        user = request.user
        
        # Check if user has permission to reject
        if not (user.has_perm('leaves.change_leaverequest') or user.is_staff or user.is_superuser):
            return Response(
                {'error': 'You do not have permission to reject leave requests.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if leave_request.status != 'pending':
            return Response(
                {'error': 'Leave request is not in pending status.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        rejection_reason = request.data.get('rejection_reason', '')
        leave_request.status = 'rejected'
        leave_request.approved_by = user
        leave_request.rejection_reason = rejection_reason
        leave_request.save()
        
        serializer = self.get_serializer(leave_request)
        return Response({
            'message': 'Leave request rejected successfully.',
            'status': 'rejected'
        })
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel a leave request."""
        # Ensure view has a request when called directly
        self.request = request
        leave_request = self.get_object()
        user = request.user
        
        # Only the employee can cancel their own request
        if leave_request.employee != user:
            return Response(
                {'error': 'You can only cancel your own leave requests.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if leave_request.status not in ['pending', 'approved']:
            return Response(
                {'error': 'Leave request cannot be cancelled.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        leave_request.status = 'cancelled'
        leave_request.save()
        
        return Response({
            'message': 'Leave request cancelled successfully.',
            'status': 'cancelled'
        })
    
    @action(detail=True, methods=['get'], url_path='conflicting-shifts')
    def conflicting_shifts(self, request, pk=None):
        """Get shifts that conflict with this leave request."""
        # Ensure view has a request when called directly
        self.request = request
        leave_request = self.get_object()
        
        # Check if user can access this leave request
        if not (request.user.has_perm('leaves.view_leaverequest') or 
                request.user.is_staff or 
                leave_request.employee == request.user):
            return Response({'error': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)
        
        conflicting_shifts = leave_request.get_conflicting_shifts()
        
        # Serialize the shift data
        shifts_data = []
        for shift in conflicting_shifts:
            shifts_data.append({
                'id': shift.id,
                'start_datetime': shift.start_datetime,
                'end_datetime': shift.end_datetime,
                'shift_type': shift.template.shift_type if shift.template else 'unknown',
                'shift_name': shift.template.name if shift.template else 'Unknown Shift',
                'status': shift.status,
                'duration_hours': shift.template.duration_hours if shift.template else 0,
                'notes': shift.notes or '',
            })
        
        return Response({
            'leave_request_id': leave_request.id,
            'conflicts_count': len(shifts_data),
            'conflicting_shifts': shifts_data
        })

    @action(detail=False, methods=['get'])
    def check_conflicts(self, request):
        """Check for conflicts when creating a leave request using provided dates and optional times."""
        # Ensure view has a request when called directly
        self.request = request
        start_date_s = request.query_params.get('start_date')
        end_date_s = request.query_params.get('end_date')
        start_time_s = request.query_params.get('start_time')
        end_time_s = request.query_params.get('end_time')
        leave_type_id = request.query_params.get('leave_type_id')

        if not start_date_s or not end_date_s:
            return Response(
                {'error': 'Both start_date and end_date are required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        start_d = parse_date(start_date_s)
        end_d = parse_date(end_date_s)
        if not start_d or not end_d:
            return Response({'error': 'Invalid date format.'}, status=status.HTTP_400_BAD_REQUEST)

        # Build a transient LeaveRequest-like object to reuse conflict logic
        leave_type = None
        if leave_type_id:
            try:
                leave_type = LeaveType.objects.get(pk=leave_type_id)
            except LeaveType.DoesNotExist:
                leave_type = None
        tmp = LeaveRequest(
            employee=request.user,
            leave_type=leave_type or LeaveType(name='tmp'),
            start_date=start_d,
            end_date=end_d,
        )
        # Override type-level time window if provided
        if start_time_s:
            try:
                from datetime import time as _t
                hh, mm = [int(x) for x in start_time_s.split(':')]
                tmp.start_time = _t(hh, mm)
            except Exception:
                pass
        if end_time_s:
            try:
                from datetime import time as _t
                hh, mm = [int(x) for x in end_time_s.split(':')]
                tmp.end_time = _t(hh, mm)
            except Exception:
                pass

        conflicts_qs = tmp.get_conflicting_shifts()
        conflicts = []
        for s in conflicts_qs.select_related('template', 'assigned_employee'):
            conflicts.append({
                'id': int(getattr(s, 'id')),  # type: ignore[arg-type]
                'shift_type': getattr(s.template, 'shift_type', 'unknown'),
                'shift_name': getattr(s.template, 'name', 'Shift'),
                'start_datetime': s.start_datetime.isoformat(),
                'end_datetime': s.end_datetime.isoformat(),
                'status': s.status,
            })

        # Rudimentary suggestions: list team members without overlapping shifts for the same window
        suggestions = []
        if conflicts:
            from django.contrib.auth import get_user_model
            from team_planner.teams.models import TeamMembership
            from team_planner.shifts.models import Shift as ShiftModel
            User = get_user_model()

            team_ids = TeamMembership.objects.filter(user=request.user, is_active=True).values_list('team_id', flat=True)
            candidates = User.objects.filter(teammembership__team_id__in=team_ids, is_active=True).exclude(id=request.user.id).distinct()

            for s in conflicts_qs:
                avail = candidates.exclude(
                    assigned_shifts__start_datetime__lt=s.end_datetime,
                    assigned_shifts__end_datetime__gt=s.start_datetime,
                )
                suggestions.append({
                    'shift_id': int(getattr(s, 'id')),  # type: ignore[arg-type]
                    'candidate_ids': list(avail.values_list('id', flat=True)[:10]),
                })

        return Response({
            'has_conflicts': bool(conflicts),
            'conflicts': conflicts,
            'suggestions': suggestions,
            'message': 'Conflicts detected.' if conflicts else 'No conflicts found.'
        })
    
    @action(detail=False, methods=['get'])
    def user_stats(self, request):
        """Get user's leave statistics."""
        # Ensure view has a request when called directly
        self.request = request
        user = request.user
        current_year = datetime.now().year
        
        # Get user's leave requests for current year
        user_requests = LeaveRequest.objects.filter(
            employee=user,
            start_date__year=current_year
        )
        
        stats = {
            'total_requests': user_requests.count(),
            'pending_requests': user_requests.filter(status='pending').count(),
            'approved_requests': user_requests.filter(status='approved').count(),
            'rejected_requests': user_requests.filter(status='rejected').count(),
            'days_used_this_year': sum(
                req.days_requested for req in user_requests.filter(status='approved')
            ),
            'current_year': current_year,
        }
        
        return Response(stats)


class LeaveTypeViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for leave types (read-only)."""
    queryset = LeaveType.objects.all()
    serializer_class = LeaveTypeSerializer
    permission_classes = [IsAuthenticated]
