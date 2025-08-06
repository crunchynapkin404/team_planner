from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import get_user_model
import json

from .models import SwapRequest, Shift

User = get_user_model()


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def respond_to_swap_request_api(request, pk):
    """API endpoint to respond to a swap request."""
    try:
        swap_request = get_object_or_404(SwapRequest, pk=pk)
        
        # Check if user can respond to this swap request
        if swap_request.target_employee != request.user:
            return Response(
                {'error': 'You can only respond to swap requests directed to you.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check if request is still pending
        if swap_request.status != SwapRequest.Status.PENDING:
            return Response(
                {'error': 'This swap request has already been processed.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        action = request.data.get('action')
        message = request.data.get('message', '')
        
        if action == 'approve':
            swap_request.status = SwapRequest.Status.APPROVED
            swap_request.response_notes = message
            swap_request.approved_by = request.user
            swap_request.approved_datetime = timezone.now()
            swap_request.save()
            
            # Implement the actual shift swapping logic
            requesting_shift = swap_request.requesting_shift
            target_shift = swap_request.target_shift
            
            if target_shift:
                # Direct shift swap - swap the assigned employees
                original_requesting_employee = requesting_shift.assigned_employee
                original_target_employee = target_shift.assigned_employee
                
                requesting_shift.assigned_employee = original_target_employee
                target_shift.assigned_employee = original_requesting_employee
                
                requesting_shift.save()
                target_shift.save()
                
                return Response({
                    'message': 'Swap request approved successfully. Shifts have been swapped.',
                    'swapped_shifts': {
                        'requesting_shift_id': requesting_shift.pk,
                        'target_shift_id': target_shift.pk
                    }
                })
            else:
                # Open swap request - assign the requesting shift to the target employee
                requesting_shift.assigned_employee = swap_request.target_employee
                requesting_shift.save()
                
                return Response({
                    'message': 'Swap request approved successfully. Shift has been assigned to you.',
                    'assigned_shift_id': requesting_shift.pk
                })
            
        elif action == 'reject':
            swap_request.status = SwapRequest.Status.REJECTED
            swap_request.response_notes = message
            swap_request.save()
            
            return Response({'message': 'Swap request rejected.'})
            
        else:
            return Response(
                {'error': 'Invalid action. Must be "approve" or "reject".'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_upcoming_shifts_api(request):
    """API endpoint to get user's upcoming shifts."""
    from django.utils import timezone
    from .models import Shift
    
    limit = int(request.GET.get('limit', 5))
    
    upcoming_shifts = Shift.objects.filter(
        assigned_employee=request.user,
        start_datetime__gte=timezone.now()
    ).order_by('start_datetime')[:limit]
    
    shifts_data = [{
        'id': shift.pk,
        'title': f"{shift.template.name} - {shift.template.shift_type}",
        'start_time': shift.start_datetime.isoformat(),
        'end_time': shift.end_datetime.isoformat(),
        'shift_type': shift.template.shift_type,
        'status': shift.status,
        'is_upcoming': True
    } for shift in upcoming_shifts]
    
    return Response(shifts_data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_incoming_swap_requests_api(request):
    """API endpoint to get user's incoming swap requests."""
    
    incoming_requests = SwapRequest.objects.filter(
        target_employee=request.user
    ).select_related('requesting_employee', 'requesting_shift', 'target_shift')
    
    requests_data = []
    
    for swap in incoming_requests:
        try:
            # Defensive checks to handle missing data
            if not swap.requesting_employee or not swap.requesting_shift:
                continue
                
            requesting_shift_data = None
            if swap.requesting_shift and hasattr(swap.requesting_shift, 'template') and swap.requesting_shift.template:
                requesting_shift_data = {
                    'id': swap.requesting_shift.pk,
                    'title': f"{swap.requesting_shift.template.name} - {swap.requesting_shift.template.shift_type}",
                    'start_time': swap.requesting_shift.start_datetime.isoformat(),
                    'end_time': swap.requesting_shift.end_datetime.isoformat(),
                    'shift_type': swap.requesting_shift.template.shift_type,
                }
            
            target_shift_data = None
            if swap.target_shift and hasattr(swap.target_shift, 'template') and swap.target_shift.template:
                target_shift_data = {
                    'id': swap.target_shift.pk,
                    'title': f"{swap.target_shift.template.name} - {swap.target_shift.template.shift_type}",
                    'start_time': swap.target_shift.start_datetime.isoformat(),
                    'end_time': swap.target_shift.end_datetime.isoformat(),
                    'shift_type': swap.target_shift.template.shift_type,
                }
            
            request_data = {
                'id': swap.pk,
                'requester': {
                    'id': swap.requesting_employee.pk,
                    'username': swap.requesting_employee.username,
                    'first_name': getattr(swap.requesting_employee, 'first_name_display', swap.requesting_employee.username),
                    'last_name': getattr(swap.requesting_employee, 'last_name_display', ''),
                },
                'target_employee': {
                    'id': swap.target_employee.pk,
                    'username': swap.target_employee.username,
                    'first_name': getattr(swap.target_employee, 'first_name_display', swap.target_employee.username),
                    'last_name': getattr(swap.target_employee, 'last_name_display', ''),
                },
                'requesting_shift': requesting_shift_data,
                'target_shift': target_shift_data,
                'reason': swap.reason or '',
                'status': swap.status,
                'response_notes': swap.response_notes or '',
                'created_at': swap.created.isoformat(),
                'approved_by': {
                    'username': swap.approved_by.username,
                    'first_name': getattr(swap.approved_by, 'first_name_display', swap.approved_by.username),
                    'last_name': getattr(swap.approved_by, 'last_name_display', ''),
                } if swap.approved_by else None,
                'approved_datetime': swap.approved_datetime.isoformat() if swap.approved_datetime else None,
            }
            
            requests_data.append(request_data)
            
        except Exception as e:
            # Log the error but continue processing other requests
            print(f"Error processing swap request {swap.pk}: {e}")
            continue

    return Response(requests_data)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_outgoing_swap_requests_api(request):
    """API endpoint to get user's outgoing swap requests."""
    
    outgoing_requests = SwapRequest.objects.filter(
        requesting_employee=request.user
    ).select_related('target_employee', 'requesting_shift', 'target_shift')
    
    requests_data = []
    
    for swap in outgoing_requests:
        try:
            # Defensive checks to handle missing data
            if not swap.requesting_employee or not swap.requesting_shift:
                continue
                
            requesting_shift_data = None
            if swap.requesting_shift and hasattr(swap.requesting_shift, 'template') and swap.requesting_shift.template:
                requesting_shift_data = {
                    'id': swap.requesting_shift.pk,
                    'title': f"{swap.requesting_shift.template.name} - {swap.requesting_shift.template.shift_type}",
                    'start_time': swap.requesting_shift.start_datetime.isoformat(),
                    'end_time': swap.requesting_shift.end_datetime.isoformat(),
                    'shift_type': swap.requesting_shift.template.shift_type,
                }
            
            target_shift_data = None
            if swap.target_shift and hasattr(swap.target_shift, 'template') and swap.target_shift.template:
                target_shift_data = {
                    'id': swap.target_shift.pk,
                    'title': f"{swap.target_shift.template.name} - {swap.target_shift.template.shift_type}",
                    'start_time': swap.target_shift.start_datetime.isoformat(),
                    'end_time': swap.target_shift.end_datetime.isoformat(),
                    'shift_type': swap.target_shift.template.shift_type,
                }
            
            request_data = {
                'id': swap.pk,
                'requester': {
                    'id': swap.requesting_employee.pk,
                    'username': swap.requesting_employee.username,
                    'first_name': getattr(swap.requesting_employee, 'first_name_display', swap.requesting_employee.username),
                    'last_name': getattr(swap.requesting_employee, 'last_name_display', ''),
                },
                'target_employee': {
                    'id': swap.target_employee.pk,
                    'username': swap.target_employee.username,
                    'first_name': getattr(swap.target_employee, 'first_name_display', swap.target_employee.username),
                    'last_name': getattr(swap.target_employee, 'last_name_display', ''),
                },
                'requesting_shift': requesting_shift_data,
                'target_shift': target_shift_data,
                'reason': swap.reason or '',
                'status': swap.status,
                'response_notes': swap.response_notes or '',
                'created_at': swap.created.isoformat(),
                'approved_by': {
                    'username': swap.approved_by.username,
                    'first_name': getattr(swap.approved_by, 'first_name_display', swap.approved_by.username),
                    'last_name': getattr(swap.approved_by, 'last_name_display', ''),
                } if swap.approved_by else None,
                'approved_datetime': swap.approved_datetime.isoformat() if swap.approved_datetime else None,
            }
            
            requests_data.append(request_data)
            
        except Exception as e:
            # Log the error but continue processing other requests
            print(f"Error processing outgoing swap request {swap.pk}: {e}")
            continue

    return Response(requests_data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_swap_request_api(request):
    """API endpoint to create a new swap request."""
    try:
        requesting_shift_id = request.data.get('requesting_shift_id')
        target_employee_id = request.data.get('target_employee_id')
        target_shift_id = request.data.get('target_shift_id')  # Optional
        reason = request.data.get('reason', '')
        
        # Validate requesting shift
        requesting_shift = get_object_or_404(Shift, pk=requesting_shift_id)
        if requesting_shift.assigned_employee != request.user:
            return Response(
                {'error': 'You can only create swap requests for your own shifts.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check if shift is in a swappable state
        if requesting_shift.status not in ["scheduled", "confirmed"]:
            return Response(
                {'error': 'This shift cannot be swapped in its current state.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate target employee
        target_employee = get_object_or_404(User, pk=target_employee_id)
        if target_employee == request.user:
            return Response(
                {'error': 'You cannot create a swap request with yourself.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate target shift if provided
        target_shift = None
        if target_shift_id:
            target_shift = get_object_or_404(Shift, pk=target_shift_id)
            if target_shift.assigned_employee != target_employee:
                return Response(
                    {'error': 'Selected target shift must belong to the target employee.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Create the swap request
        swap_request = SwapRequest.objects.create(
            requesting_employee=request.user,
            target_employee=target_employee,
            requesting_shift=requesting_shift,
            target_shift=target_shift,
            reason=reason
        )
        
        # Validate the swap
        validation_errors = swap_request.validate_swap()
        if validation_errors:
            swap_request.delete()
            return Response(
                {'errors': validation_errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return Response({
            'message': 'Swap request created successfully!',
            'swap_request_id': swap_request.pk
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_shifts_api(request):
    """API endpoint to get user's shifts for swap requests."""
    try:
        from django.utils import timezone
        
        shifts = Shift.objects.filter(
            assigned_employee=request.user,
            status__in=["scheduled", "confirmed"]
        ).select_related('template').order_by('start_datetime')
        
        now = timezone.now()
        
        shifts_data = [{
            'id': shift.pk,
            'title': f"{shift.template.name} - {shift.template.shift_type}",
            'start_time': shift.start_datetime.isoformat(),
            'end_time': shift.end_datetime.isoformat(),
            'shift_type': shift.template.shift_type,
            'status': shift.status,
            'is_upcoming': shift.start_datetime > now,
        } for shift in shifts]
        
        return Response(shifts_data)
        
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_team_members_api(request):
    """API endpoint to get team members for swap requests."""
    try:
        # Get team members excluding current user
        from team_planner.teams.models import TeamMembership
        
        team_memberships = TeamMembership.objects.filter(
            user=request.user
        ).select_related('team')
        
        # Get all users in the same teams
        team_ids = [membership.team.pk for membership in team_memberships]
        team_members = User.objects.filter(
            teammembership__team__id__in=team_ids,
            is_active=True
        ).exclude(pk=request.user.pk).distinct().order_by('name', 'username')
        
        members_data = [{
            'id': user.pk,
            'username': user.username,
            'first_name': getattr(user, 'first_name_display', user.username),
            'last_name': getattr(user, 'last_name_display', ''),
            'display_name': getattr(user, 'display_name', user.username),
        } for user in team_members]
        
        return Response(members_data)
        
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_employee_shifts_api(request):
    """API endpoint to get shifts for a specific employee."""
    try:
        employee_id = request.GET.get('employee_id')
        if not employee_id:
            return Response(
                {'error': 'employee_id parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        employee = get_object_or_404(User, pk=employee_id)
        
        # Get employee's shifts that can be swapped
        shifts = Shift.objects.filter(
            assigned_employee=employee,
            status__in=["scheduled", "confirmed"]
        ).select_related('template').order_by('start_datetime')
        
        shifts_data = [{
            'id': shift.pk,
            'title': f"{shift.template.name} - {shift.template.shift_type}",
            'start_time': shift.start_datetime.isoformat(),
            'end_time': shift.end_datetime.isoformat(),
            'shift_type': shift.template.shift_type,
            'status': shift.status,
        } for shift in shifts]
        
        return Response(shifts_data)
        
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_bulk_swap_request_api(request):
    """API endpoint to create multiple swap requests at once."""
    try:
        shifts_data = request.data.get('shifts', [])
        reason = request.data.get('reason', '')
        swap_type = request.data.get('swap_type', 'any_available')
        
        if not shifts_data:
            return Response(
                {'error': 'No shifts provided for bulk swap.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        created_requests = []
        failed_requests = []
        
        for shift_data in shifts_data:
            try:
                requesting_shift_id = shift_data.get('requesting_shift_id')
                target_employee_id = shift_data.get('target_employee_id')
                target_shift_id = shift_data.get('target_shift_id')
                
                # Validate requesting shift
                requesting_shift = get_object_or_404(Shift, pk=requesting_shift_id)
                if requesting_shift.assigned_employee != request.user:
                    failed_requests.append({
                        'requesting_shift_id': requesting_shift_id,
                        'error': 'You can only create swap requests for your own shifts.'
                    })
                    continue
                
                # Check if shift is in a swappable state
                if requesting_shift.status not in ["scheduled", "confirmed"]:
                    failed_requests.append({
                        'requesting_shift_id': requesting_shift_id,
                        'error': 'This shift cannot be swapped in its current state.'
                    })
                    continue
                
                # Validate target employee
                target_employee = get_object_or_404(User, pk=target_employee_id)
                if target_employee == request.user:
                    failed_requests.append({
                        'requesting_shift_id': requesting_shift_id,
                        'error': 'You cannot create a swap request with yourself.'
                    })
                    continue
                
                # Validate target shift if provided
                target_shift = None
                if target_shift_id:
                    target_shift = get_object_or_404(Shift, pk=target_shift_id)
                    if target_shift.assigned_employee != target_employee:
                        failed_requests.append({
                            'requesting_shift_id': requesting_shift_id,
                            'error': 'Selected target shift must belong to the target employee.'
                        })
                        continue
                
                # Check for existing pending swap requests for this shift
                existing_request = SwapRequest.objects.filter(
                    requesting_shift=requesting_shift,
                    status=SwapRequest.Status.PENDING
                ).first()
                
                if existing_request:
                    failed_requests.append({
                        'requesting_shift_id': requesting_shift_id,
                        'error': 'A pending swap request already exists for this shift.'
                    })
                    continue
                
                # Create the swap request
                swap_request = SwapRequest.objects.create(
                    requesting_employee=request.user,
                    target_employee=target_employee,
                    requesting_shift=requesting_shift,
                    target_shift=target_shift,
                    reason=reason,
                    status=SwapRequest.Status.PENDING
                )
                
                created_requests.append(swap_request.pk)
                
            except Exception as e:
                failed_requests.append({
                    'requesting_shift_id': shift_data.get('requesting_shift_id', 'unknown'),
                    'error': str(e)
                })
        
        # Determine overall success
        success = len(created_requests) > 0
        total_requests = len(shifts_data)
        successful_count = len(created_requests)
        failed_count = len(failed_requests)
        
        if successful_count == total_requests:
            message = f"Successfully created {successful_count} swap request{'s' if successful_count != 1 else ''}."
        elif successful_count > 0:
            message = f"Created {successful_count} of {total_requests} swap requests. {failed_count} failed."
        else:
            message = f"Failed to create any swap requests. {failed_count} requests failed."
        
        return Response({
            'success': success,
            'message': message,
            'created_requests': created_requests,
            'failed_requests': failed_requests,
        })
        
    except Exception as e:
        return Response(
            {'error': f'Bulk swap request failed: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
