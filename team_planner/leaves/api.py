from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from django.db.models import Q, QuerySet
from datetime import datetime

from .models import LeaveRequest, LeaveType
from .serializers import LeaveRequestSerializer, LeaveTypeSerializer

User = get_user_model()


class LeaveRequestViewSet(viewsets.ModelViewSet):
    """ViewSet for managing leave requests."""
    queryset = LeaveRequest.objects.all()
    serializer_class = LeaveRequestSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self) -> QuerySet[LeaveRequest]:
        """Return leave requests based on user permissions."""
        user = self.request.user
        queryset = LeaveRequest.objects.select_related(
            'employee', 'leave_type', 'approved_by'
        ).order_by('-created')
        
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
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            self.perform_create(serializer)
            return Response({
                'id': serializer.instance.id,
                'message': 'Leave request created successfully.',
                'has_conflicts': serializer.instance.has_shift_conflicts,
                'conflict_warning': 'This request conflicts with assigned shifts.' if serializer.instance.has_shift_conflicts else None
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def my_requests(self, request):
        """Get current user's leave requests."""
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
        
        serializer = self.get_serializer(leave_request)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject a leave request."""
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
        """Check for conflicts when creating a leave request."""
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if not start_date or not end_date:
            return Response(
                {'error': 'Both start_date and end_date are required.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # For now, return no conflicts - this would be implemented with shift checking logic
        return Response({
            'conflicts': [],
            'suggestions': [],
            'has_conflicts': False,
            'message': 'No conflicts found.'
        })
    
    @action(detail=False, methods=['get'])
    def user_stats(self, request):
        """Get user's leave statistics."""
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
