from django.contrib.auth import get_user_model
from django.db import models
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.decorators import permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Shift
from .models import SwapRequest

User = get_user_model()


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def respond_to_swap_request_api(request, pk):
    """API endpoint to respond to a swap request."""
    try:
        swap_request = get_object_or_404(SwapRequest, pk=pk)

        # Check if user can respond to this swap request
        if swap_request.target_employee != request.user:
            return Response(
                {"error": "You can only respond to swap requests directed to you."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Check if request is still pending
        if swap_request.status != SwapRequest.Status.PENDING:
            return Response(
                {"error": "This swap request has already been processed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        action = request.data.get("action")
        message = request.data.get("message", "")

        if action == "approve":
            # Delegate to model method (handles transactional swap + notifications)
            swap_request.approve(approved_by_user=request.user, response_notes=message)
            return Response(
                {
                    "message": "Swap request approved successfully.",
                    "status": swap_request.status,
                    "id": swap_request.pk,
                },
            )
        if action == "reject":
            swap_request.reject(response_notes=message)
            return Response(
                {"message": "Swap request rejected.", "status": swap_request.status},
            )
        return Response(
            {"error": 'Invalid action. Must be "approve" or "reject".'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def user_upcoming_shifts_api(request):
    """API endpoint to get user's upcoming shifts."""
    from .models import Shift

    limit = int(request.GET.get("limit", 5))

    upcoming_shifts = Shift.objects.filter(
        assigned_employee=request.user, start_datetime__gte=timezone.now(),
    ).order_by("start_datetime")[:limit]

    shifts_data = [
        {
            "id": shift.pk,
            "title": f"{shift.template.name} - {shift.template.shift_type}",
            "start_time": shift.start_datetime.isoformat(),
            "end_time": shift.end_datetime.isoformat(),
            "shift_type": shift.template.shift_type,
            "status": shift.status,
            "is_upcoming": True,
        }
        for shift in upcoming_shifts
    ]

    return Response(shifts_data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def user_incoming_swap_requests_api(request):
    """API endpoint to get user's incoming swap requests."""

    incoming_requests = SwapRequest.objects.filter(
        target_employee=request.user,
    ).select_related("requesting_employee", "requesting_shift", "target_shift")

    requests_data = []

    for swap in incoming_requests:
        try:
            # Defensive checks to handle missing data
            if not swap.requesting_employee or not swap.requesting_shift:
                continue

            requesting_shift_data = None
            if (
                swap.requesting_shift
                and hasattr(swap.requesting_shift, "template")
                and swap.requesting_shift.template
            ):
                requesting_shift_data = {
                    "id": swap.requesting_shift.pk,
                    "title": f"{swap.requesting_shift.template.name} - {swap.requesting_shift.template.shift_type}",
                    "start_time": swap.requesting_shift.start_datetime.isoformat(),
                    "end_time": swap.requesting_shift.end_datetime.isoformat(),
                    "shift_type": swap.requesting_shift.template.shift_type,
                }

            target_shift_data = None
            if (
                swap.target_shift
                and hasattr(swap.target_shift, "template")
                and swap.target_shift.template
            ):
                target_shift_data = {
                    "id": swap.target_shift.pk,
                    "title": f"{swap.target_shift.template.name} - {swap.target_shift.template.shift_type}",
                    "start_time": swap.target_shift.start_datetime.isoformat(),
                    "end_time": swap.target_shift.end_datetime.isoformat(),
                    "shift_type": swap.target_shift.template.shift_type,
                }

            request_data = {
                "id": swap.pk,
                "requester": {
                    "id": swap.requesting_employee.pk,
                    "username": swap.requesting_employee.username,
                    "first_name": getattr(
                        swap.requesting_employee,
                        "first_name_display",
                        swap.requesting_employee.username,
                    ),
                    "last_name": getattr(
                        swap.requesting_employee, "last_name_display", "",
                    ),
                },
                "target_employee": {
                    "id": swap.target_employee.pk,
                    "username": swap.target_employee.username,
                    "first_name": getattr(
                        swap.target_employee,
                        "first_name_display",
                        swap.target_employee.username,
                    ),
                    "last_name": getattr(swap.target_employee, "last_name_display", ""),
                },
                "requesting_shift": requesting_shift_data,
                "target_shift": target_shift_data,
                "reason": swap.reason or "",
                "status": swap.status,
                "response_notes": swap.response_notes or "",
                "created_at": swap.created.isoformat(),
                "approved_by": {
                    "username": swap.approved_by.username,
                    "first_name": getattr(
                        swap.approved_by,
                        "first_name_display",
                        swap.approved_by.username,
                    ),
                    "last_name": getattr(swap.approved_by, "last_name_display", ""),
                }
                if swap.approved_by
                else None,
                "approved_datetime": swap.approved_datetime.isoformat()
                if swap.approved_datetime
                else None,
            }

            requests_data.append(request_data)

        except Exception:
            # Log the error but continue processing other requests
            continue

    return Response(requests_data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def user_outgoing_swap_requests_api(request):
    """API endpoint to get user's outgoing swap requests."""

    outgoing_requests = SwapRequest.objects.filter(
        requesting_employee=request.user,
    ).select_related("target_employee", "requesting_shift", "target_shift")

    requests_data = []

    for swap in outgoing_requests:
        try:
            # Defensive checks to handle missing data
            if not swap.requesting_employee or not swap.requesting_shift:
                continue

            requesting_shift_data = None
            if (
                swap.requesting_shift
                and hasattr(swap.requesting_shift, "template")
                and swap.requesting_shift.template
            ):
                requesting_shift_data = {
                    "id": swap.requesting_shift.pk,
                    "title": f"{swap.requesting_shift.template.name} - {swap.requesting_shift.template.shift_type}",
                    "start_time": swap.requesting_shift.start_datetime.isoformat(),
                    "end_time": swap.requesting_shift.end_datetime.isoformat(),
                    "shift_type": swap.requesting_shift.template.shift_type,
                }

            target_shift_data = None
            if (
                swap.target_shift
                and hasattr(swap.target_shift, "template")
                and swap.target_shift.template
            ):
                target_shift_data = {
                    "id": swap.target_shift.pk,
                    "title": f"{swap.target_shift.template.name} - {swap.target_shift.template.shift_type}",
                    "start_time": swap.target_shift.start_datetime.isoformat(),
                    "end_time": swap.target_shift.end_datetime.isoformat(),
                    "shift_type": swap.target_shift.template.shift_type,
                }

            request_data = {
                "id": swap.pk,
                "requester": {
                    "id": swap.requesting_employee.pk,
                    "username": swap.requesting_employee.username,
                    "first_name": getattr(
                        swap.requesting_employee,
                        "first_name_display",
                        swap.requesting_employee.username,
                    ),
                    "last_name": getattr(
                        swap.requesting_employee, "last_name_display", "",
                    ),
                },
                "target_employee": {
                    "id": swap.target_employee.pk,
                    "username": swap.target_employee.username,
                    "first_name": getattr(
                        swap.target_employee,
                        "first_name_display",
                        swap.target_employee.username,
                    ),
                    "last_name": getattr(swap.target_employee, "last_name_display", ""),
                },
                "requesting_shift": requesting_shift_data,
                "target_shift": target_shift_data,
                "reason": swap.reason or "",
                "status": swap.status,
                "response_notes": swap.response_notes or "",
                "created_at": swap.created.isoformat(),
                "approved_by": {
                    "username": swap.approved_by.username,
                    "first_name": getattr(
                        swap.approved_by,
                        "first_name_display",
                        swap.approved_by.username,
                    ),
                    "last_name": getattr(swap.approved_by, "last_name_display", ""),
                }
                if swap.approved_by
                else None,
                "approved_datetime": swap.approved_datetime.isoformat()
                if swap.approved_datetime
                else None,
            }

            requests_data.append(request_data)

        except Exception:
            # Log the error but continue processing other requests
            continue

    return Response(requests_data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_swap_request_api(request):
    """API endpoint to create a new swap request."""
    try:
        requesting_shift_id = request.data.get("requesting_shift_id")
        target_employee_id = request.data.get("target_employee_id")
        target_shift_id = request.data.get("target_shift_id")  # Optional
        reason = request.data.get("reason", "")

        # Validate requesting shift
        requesting_shift = get_object_or_404(Shift, pk=requesting_shift_id)
        if requesting_shift.assigned_employee != request.user:
            return Response(
                {"error": "You can only create swap requests for your own shifts."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Check if shift is in a swappable state
        if requesting_shift.status not in ["scheduled", "confirmed"]:
            return Response(
                {"error": "This shift cannot be swapped in its current state."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate target employee
        target_employee = get_object_or_404(User, pk=target_employee_id)
        if target_employee == request.user:
            return Response(
                {"error": "You cannot create a swap request with yourself."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate target shift if provided
        target_shift = None
        if target_shift_id:
            target_shift = get_object_or_404(Shift, pk=target_shift_id)
            if target_shift.assigned_employee != target_employee:
                return Response(
                    {
                        "error": "Selected target shift must belong to the target employee.",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # Create the swap request
        swap_request = SwapRequest.objects.create(
            requesting_employee=request.user,
            target_employee=target_employee,
            requesting_shift=requesting_shift,
            target_shift=target_shift,
            reason=reason,
        )

        # Validate the swap
        validation_errors = swap_request.validate_swap()
        if validation_errors:
            swap_request.delete()
            return Response(
                {"errors": validation_errors}, status=status.HTTP_400_BAD_REQUEST,
            )

        # Send notification to target employee
        try:
            from team_planner.notifications.services import NotificationService
            NotificationService.notify_swap_requested(
                target_employee=target_employee,
                swap_request=swap_request,
                requesting_employee=request.user
            )
        except Exception as e:
            # Log but don't fail the request if notification fails
            print(f"Failed to send swap request notification: {e}")

        return Response(
            {
                "message": "Swap request created successfully!",
                "swap_request_id": swap_request.pk,
            },
            status=status.HTTP_201_CREATED,
        )

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_user_shifts_api(request):
    """API endpoint to get user's shifts for swap requests."""
    try:
        from django.utils import timezone

        shifts = (
            Shift.objects.filter(
                assigned_employee=request.user, status__in=["scheduled", "confirmed"],
            )
            .select_related("template")
            .order_by("start_datetime")
        )

        now = timezone.now()

        shifts_data = [
            {
                "id": shift.pk,
                "title": f"{shift.template.name} - {shift.template.shift_type}",
                "start_time": shift.start_datetime.isoformat(),
                "end_time": shift.end_datetime.isoformat(),
                "shift_type": shift.template.shift_type,
                "status": shift.status,
                "is_upcoming": shift.start_datetime > now,
            }
            for shift in shifts
        ]

        return Response(shifts_data)

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_team_members_api(request):
    """API endpoint to get team members for swap requests."""
    try:
        # Get team members excluding current user
        from team_planner.teams.models import TeamMembership

        team_memberships = TeamMembership.objects.filter(
            user=request.user,
        ).select_related("team")

        # Get all users in the same teams
        team_ids = [membership.team.pk for membership in team_memberships]
        team_members = (
            User.objects.filter(teammembership__team__id__in=team_ids, is_active=True)
            .exclude(pk=request.user.pk)
            .distinct()
            .order_by("name", "username")
        )

        members_data = [
            {
                "id": user.pk,
                "username": getattr(user, "username", getattr(user, "email", "")),
                "first_name": getattr(
                    user, "first_name_display", getattr(user, "username", ""),
                ),
                "last_name": getattr(user, "last_name_display", ""),
                "display_name": getattr(
                    user,
                    "display_name",
                    getattr(user, "name", getattr(user, "username", "")),
                ),
            }
            for user in team_members
        ]

        return Response(members_data)

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_employee_shifts_api(request):
    """API endpoint to get shifts for a specific employee."""
    try:
        employee_id = request.GET.get("employee_id")
        if not employee_id:
            return Response(
                {"error": "employee_id parameter is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        employee = get_object_or_404(User, pk=employee_id)

        # Get employee's shifts that can be swapped
        shifts = (
            Shift.objects.filter(
                assigned_employee=employee, status__in=["scheduled", "confirmed"],
            )
            .select_related("template")
            .order_by("start_datetime")
        )

        shifts_data = [
            {
                "id": shift.pk,
                "title": f"{shift.template.name} - {shift.template.shift_type}",
                "start_time": shift.start_datetime.isoformat(),
                "end_time": shift.end_datetime.isoformat(),
                "shift_type": shift.template.shift_type,
                "status": shift.status,
            }
            for shift in shifts
        ]

        return Response(shifts_data)

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_bulk_swap_request_api(request):
    """API endpoint to create multiple swap requests at once."""
    try:
        shifts_data = request.data.get("shifts", [])
        reason = request.data.get("reason", "")
        request.data.get("swap_type", "any_available")

        if not shifts_data:
            return Response(
                {"error": "No shifts provided for bulk swap."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        created_requests = []
        failed_requests = []

        for shift_data in shifts_data:
            try:
                requesting_shift_id = shift_data.get("requesting_shift_id")
                target_employee_id = shift_data.get("target_employee_id")
                target_shift_id = shift_data.get("target_shift_id")

                # Validate requesting shift
                requesting_shift = get_object_or_404(Shift, pk=requesting_shift_id)
                if requesting_shift.assigned_employee != request.user:
                    failed_requests.append(
                        {
                            "requesting_shift_id": requesting_shift_id,
                            "error": "You can only create swap requests for your own shifts.",
                        },
                    )
                    continue

                # Check if shift is in a swappable state
                if requesting_shift.status not in ["scheduled", "confirmed"]:
                    failed_requests.append(
                        {
                            "requesting_shift_id": requesting_shift_id,
                            "error": "This shift cannot be swapped in its current state.",
                        },
                    )
                    continue

                # Validate target employee
                target_employee = get_object_or_404(User, pk=target_employee_id)
                if target_employee == request.user:
                    failed_requests.append(
                        {
                            "requesting_shift_id": requesting_shift_id,
                            "error": "You cannot create a swap request with yourself.",
                        },
                    )
                    continue

                # Validate target shift if provided
                target_shift = None
                if target_shift_id:
                    target_shift = get_object_or_404(Shift, pk=target_shift_id)
                    if target_shift.assigned_employee != target_employee:
                        failed_requests.append(
                            {
                                "requesting_shift_id": requesting_shift_id,
                                "error": "Selected target shift must belong to the target employee.",
                            },
                        )
                        continue

                # Check for existing pending swap requests for this shift
                existing_request = SwapRequest.objects.filter(
                    requesting_shift=requesting_shift, status=SwapRequest.Status.PENDING,
                ).first()

                if existing_request:
                    failed_requests.append(
                        {
                            "requesting_shift_id": requesting_shift_id,
                            "error": "A pending swap request already exists for this shift.",
                        },
                    )
                    continue

                # Create the swap request
                swap_request = SwapRequest.objects.create(
                    requesting_employee=request.user,
                    target_employee=target_employee,
                    requesting_shift=requesting_shift,
                    target_shift=target_shift,
                    reason=reason,
                    status=SwapRequest.Status.PENDING,
                )

                # Send notification to target employee
                try:
                    from team_planner.notifications.services import NotificationService
                    NotificationService.notify_swap_requested(
                        target_employee=target_employee,
                        swap_request=swap_request,
                        requesting_employee=request.user
                    )
                except Exception as e:
                    print(f"Failed to send swap request notification: {e}")

                created_requests.append(swap_request.pk)

            except Exception as e:
                failed_requests.append(
                    {
                        "requesting_shift_id": shift_data.get(
                            "requesting_shift_id", "unknown",
                        ),
                        "error": str(e),
                    },
                )

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
            message = (
                f"Failed to create any swap requests. {failed_count} requests failed."
            )

        return Response(
            {
                "success": success,
                "message": message,
                "created_requests": created_requests,
                "failed_requests": failed_requests,
            },
        )

    except Exception as e:
        return Response(
            {"error": f"Bulk swap request failed: {e!s}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# ============================================================================
# Recurring Pattern API Endpoints
# ============================================================================

@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def recurring_pattern_list_create(request):
    """List or create recurring shift patterns."""
    from team_planner.rbac.decorators import require_any_permission
    from team_planner.shifts.models import RecurringShiftPattern, ShiftTemplate
    from team_planner.shifts.pattern_service import RecurringPatternService

    # Check permissions
    has_permission = (
        request.user.is_superuser
        or request.user.profile.role.permissions.filter(
            name__in=["can_run_orchestrator", "can_manage_team"]
        ).exists()
    )
    
    if not has_permission:
        return Response(
            {"error": "You do not have permission to manage recurring patterns."},
            status=status.HTTP_403_FORBIDDEN,
        )

    if request.method == "GET":
        # List patterns
        patterns = RecurringShiftPattern.objects.select_related(
            "template", "assigned_employee", "team", "created_by"
        ).all()
        
        # Filter by query params
        team_id = request.GET.get("team")
        employee_id = request.GET.get("employee")
        is_active = request.GET.get("is_active")
        
        if team_id:
            patterns = patterns.filter(team_id=team_id)
        if employee_id:
            patterns = patterns.filter(assigned_employee_id=employee_id)
        if is_active is not None:
            patterns = patterns.filter(is_active=is_active.lower() == "true")
        
        patterns = patterns.order_by("-created")
        
        data = [
            {
                "id": p.pk,
                "name": p.name,
                "description": p.description,
                "template": {
                    "id": p.template.pk,
                    "name": p.template.name,
                    "shift_type": p.template.shift_type,
                },
                "start_time": p.start_time.strftime("%H:%M"),
                "end_time": p.end_time.strftime("%H:%M"),
                "recurrence_type": p.recurrence_type,
                "weekdays": p.weekdays,
                "day_of_month": p.day_of_month,
                "pattern_start_date": p.pattern_start_date.isoformat(),
                "pattern_end_date": p.pattern_end_date.isoformat() if p.pattern_end_date else None,
                "assigned_employee": {
                    "id": p.assigned_employee.pk,
                    "username": p.assigned_employee.username,
                    "first_name": p.assigned_employee.first_name,
                    "last_name": p.assigned_employee.last_name,
                } if p.assigned_employee else None,
                "team": {
                    "id": p.team.pk,
                    "name": p.team.name,
                } if p.team else None,
                "is_active": p.is_active,
                "last_generated_date": p.last_generated_date.isoformat() if p.last_generated_date else None,
                "created_by": {
                    "id": p.created_by.pk,
                    "username": p.created_by.username,
                } if p.created_by else None,
                "created": p.created.isoformat(),
            }
            for p in patterns
        ]
        
        return Response(data)

    elif request.method == "POST":
        # Create pattern
        try:
            template = get_object_or_404(ShiftTemplate, pk=request.data.get("template_id"))
            
            pattern = RecurringShiftPattern.objects.create(
                name=request.data.get("name"),
                description=request.data.get("description", ""),
                template=template,
                start_time=request.data.get("start_time"),
                end_time=request.data.get("end_time"),
                recurrence_type=request.data.get("recurrence_type"),
                weekdays=request.data.get("weekdays", []),
                day_of_month=request.data.get("day_of_month"),
                pattern_start_date=request.data.get("pattern_start_date"),
                pattern_end_date=request.data.get("pattern_end_date"),
                assigned_employee_id=request.data.get("assigned_employee_id"),
                team_id=request.data.get("team_id"),
                is_active=request.data.get("is_active", True),
                created_by=request.user,
            )
            
            return Response(
                {
                    "id": pattern.pk,
                    "message": "Recurring pattern created successfully.",
                },
                status=status.HTTP_201_CREATED,
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )


@api_view(["GET", "PUT", "DELETE"])
@permission_classes([IsAuthenticated])
def recurring_pattern_detail(request, pk):
    """Get, update, or delete a recurring pattern."""
    from team_planner.shifts.models import RecurringShiftPattern, ShiftTemplate

    # Check permissions
    has_permission = (
        request.user.is_superuser
        or request.user.profile.role.permissions.filter(
            name__in=["can_run_orchestrator", "can_manage_team"]
        ).exists()
    )
    
    if not has_permission:
        return Response(
            {"error": "You do not have permission to manage recurring patterns."},
            status=status.HTTP_403_FORBIDDEN,
        )

    pattern = get_object_or_404(
        RecurringShiftPattern.objects.select_related("template", "assigned_employee", "team"),
        pk=pk
    )

    if request.method == "GET":
        data = {
            "id": pattern.pk,
            "name": pattern.name,
            "description": pattern.description,
            "template": {
                "id": pattern.template.pk,
                "name": pattern.template.name,
                "shift_type": pattern.template.shift_type,
            },
            "start_time": pattern.start_time.strftime("%H:%M"),
            "end_time": pattern.end_time.strftime("%H:%M"),
            "recurrence_type": pattern.recurrence_type,
            "weekdays": pattern.weekdays,
            "day_of_month": pattern.day_of_month,
            "pattern_start_date": pattern.pattern_start_date.isoformat(),
            "pattern_end_date": pattern.pattern_end_date.isoformat() if pattern.pattern_end_date else None,
            "assigned_employee": {
                "id": pattern.assigned_employee.pk,
                "username": pattern.assigned_employee.username,
                "first_name": pattern.assigned_employee.first_name,
                "last_name": pattern.assigned_employee.last_name,
            } if pattern.assigned_employee else None,
            "team": {
                "id": pattern.team.pk,
                "name": pattern.team.name,
            } if pattern.team else None,
            "is_active": pattern.is_active,
            "last_generated_date": pattern.last_generated_date.isoformat() if pattern.last_generated_date else None,
            "created": pattern.created.isoformat(),
        }
        return Response(data)

    elif request.method == "PUT":
        try:
            if "template_id" in request.data:
                pattern.template = get_object_or_404(ShiftTemplate, pk=request.data["template_id"])
            if "name" in request.data:
                pattern.name = request.data["name"]
            if "description" in request.data:
                pattern.description = request.data["description"]
            if "start_time" in request.data:
                pattern.start_time = request.data["start_time"]
            if "end_time" in request.data:
                pattern.end_time = request.data["end_time"]
            if "recurrence_type" in request.data:
                pattern.recurrence_type = request.data["recurrence_type"]
            if "weekdays" in request.data:
                pattern.weekdays = request.data["weekdays"]
            if "day_of_month" in request.data:
                pattern.day_of_month = request.data["day_of_month"]
            if "pattern_start_date" in request.data:
                pattern.pattern_start_date = request.data["pattern_start_date"]
            if "pattern_end_date" in request.data:
                pattern.pattern_end_date = request.data["pattern_end_date"]
            if "assigned_employee_id" in request.data:
                pattern.assigned_employee_id = request.data["assigned_employee_id"]
            if "team_id" in request.data:
                pattern.team_id = request.data["team_id"]
            if "is_active" in request.data:
                pattern.is_active = request.data["is_active"]
            
            pattern.save()
            
            return Response({"message": "Pattern updated successfully."})
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

    elif request.method == "DELETE":
        pattern.delete()
        return Response(
            {"message": "Pattern deleted successfully."},
            status=status.HTTP_204_NO_CONTENT,
        )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def generate_pattern_shifts(request, pk):
    """Generate shifts from a recurring pattern."""
    from datetime import date, timedelta
    from team_planner.shifts.models import RecurringShiftPattern
    from team_planner.shifts.pattern_service import RecurringPatternService

    # Check permissions
    has_permission = (
        request.user.is_superuser
        or request.user.profile.role.permissions.filter(
            name__in=["can_run_orchestrator", "can_manage_team"]
        ).exists()
    )
    
    if not has_permission:
        return Response(
            {"error": "You do not have permission to generate shifts."},
            status=status.HTTP_403_FORBIDDEN,
        )

    pattern = get_object_or_404(RecurringShiftPattern, pk=pk)
    
    # Get end date from request or default to 30 days ahead
    days_ahead = int(request.data.get("days_ahead", 30))
    end_date = date.today() + timedelta(days=days_ahead)
    
    try:
        shifts = RecurringPatternService.generate_shifts_for_pattern(
            pattern, end_date=end_date
        )
        
        return Response({
            "message": f"Successfully generated {len(shifts)} shifts.",
            "shifts_created": len(shifts),
            "pattern_id": pattern.pk,
            "pattern_name": pattern.name,
        })
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def preview_pattern(request, pk):
    """Preview dates that would be generated for a pattern."""
    from team_planner.shifts.models import RecurringShiftPattern
    from team_planner.shifts.pattern_service import RecurringPatternService

    pattern = get_object_or_404(RecurringShiftPattern, pk=pk)
    
    preview_days = int(request.data.get("preview_days", 30))
    
    try:
        dates = RecurringPatternService.preview_pattern_dates(pattern, preview_days)
        
        return Response({
            "pattern_name": pattern.name,
            "preview_days": preview_days,
            "dates": [d.isoformat() for d in dates],
            "count": len(dates),
        })
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def bulk_generate_shifts(request):
    """Generate shifts for all active patterns."""
    from team_planner.shifts.pattern_service import RecurringPatternService

    # Check permissions
    has_permission = (
        request.user.is_superuser
        or request.user.profile.role.permissions.filter(
            name__in=["can_run_orchestrator", "can_manage_team"]
        ).exists()
    )
    
    if not has_permission:
        return Response(
            {"error": "You do not have permission to generate shifts."},
            status=status.HTTP_403_FORBIDDEN,
        )

    days_ahead = int(request.data.get("days_ahead", 14))
    
    try:
        result = RecurringPatternService.bulk_generate_shifts(days_ahead)
        
        return Response({
            "message": f"Processed {result['patterns_processed']} patterns, created {result['total_shifts_created']} shifts.",
            "patterns_processed": result["patterns_processed"],
            "total_shifts_created": result["total_shifts_created"],
            "results": result["results"],
        })
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# ============================================================================
# Shift Template Library API Endpoints
# ============================================================================

@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def template_list_create(request):
    """List or create shift templates."""
    from team_planner.shifts.models import ShiftTemplate

    # Check permissions for POST
    if request.method == "POST":
        has_permission = (
            request.user.is_superuser
            or request.user.profile.role.permissions.filter(
                name__in=["can_run_orchestrator", "can_manage_team"]
            ).exists()
        )
        
        if not has_permission:
            return Response(
                {"error": "You do not have permission to create templates."},
                status=status.HTTP_403_FORBIDDEN,
            )

    if request.method == "GET":
        # List templates
        templates = ShiftTemplate.objects.prefetch_related("skills_required").all()
        
        # Filter by query params
        shift_type = request.GET.get("shift_type")
        category = request.GET.get("category")
        is_active = request.GET.get("is_active")
        is_favorite = request.GET.get("is_favorite")
        search = request.GET.get("search")
        
        if shift_type:
            templates = templates.filter(shift_type=shift_type)
        if category:
            templates = templates.filter(category=category)
        if is_active is not None:
            templates = templates.filter(is_active=is_active.lower() == "true")
        if is_favorite is not None:
            templates = templates.filter(is_favorite=is_favorite.lower() == "true")
        if search:
            templates = templates.filter(
                models.Q(name__icontains=search) | 
                models.Q(description__icontains=search)
            )
        
        data = [
            {
                "id": t.pk,
                "name": t.name,
                "shift_type": t.shift_type,
                "shift_type_display": t.get_shift_type_display(),
                "description": t.description,
                "duration_hours": t.duration_hours,
                "skills_required": [
                    {"id": s.pk, "name": s.name} 
                    for s in t.skills_required.all()
                ],
                "is_active": t.is_active,
                "category": t.category,
                "tags": t.tags,
                "is_favorite": t.is_favorite,
                "usage_count": t.usage_count,
                "created_by": {
                    "id": t.created_by.pk,
                    "username": t.created_by.username,
                } if t.created_by else None,
                "default_start_time": t.default_start_time.strftime("%H:%M") if t.default_start_time else None,
                "default_end_time": t.default_end_time.strftime("%H:%M") if t.default_end_time else None,
                "notes": t.notes,
                "created": t.created.isoformat(),
            }
            for t in templates
        ]
        
        return Response(data)

    elif request.method == "POST":
        # Create template
        try:
            template = ShiftTemplate.objects.create(
                name=request.data.get("name"),
                shift_type=request.data.get("shift_type"),
                description=request.data.get("description", ""),
                duration_hours=request.data.get("duration_hours"),
                is_active=request.data.get("is_active", True),
                category=request.data.get("category", ""),
                tags=request.data.get("tags", []),
                is_favorite=request.data.get("is_favorite", False),
                created_by=request.user,
                default_start_time=request.data.get("default_start_time"),
                default_end_time=request.data.get("default_end_time"),
                notes=request.data.get("notes", ""),
            )
            
            # Add skills if provided
            skill_ids = request.data.get("skill_ids", [])
            if skill_ids:
                template.skills_required.set(skill_ids)
            
            return Response(
                {
                    "id": template.pk,
                    "message": "Template created successfully.",
                },
                status=status.HTTP_201_CREATED,
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )


@api_view(["GET", "PUT", "DELETE"])
@permission_classes([IsAuthenticated])
def template_detail(request, pk):
    """Get, update, or delete a template."""
    from team_planner.shifts.models import ShiftTemplate

    # Check permissions for PUT/DELETE
    if request.method in ["PUT", "DELETE"]:
        has_permission = (
            request.user.is_superuser
            or request.user.profile.role.permissions.filter(
                name__in=["can_run_orchestrator", "can_manage_team"]
            ).exists()
        )
        
        if not has_permission:
            return Response(
                {"error": "You do not have permission to modify templates."},
                status=status.HTTP_403_FORBIDDEN,
            )

    template = get_object_or_404(
        ShiftTemplate.objects.prefetch_related("skills_required"),
        pk=pk
    )

    if request.method == "GET":
        data = {
            "id": template.pk,
            "name": template.name,
            "shift_type": template.shift_type,
            "shift_type_display": template.get_shift_type_display(),
            "description": template.description,
            "duration_hours": template.duration_hours,
            "skills_required": [
                {"id": s.pk, "name": s.name} 
                for s in template.skills_required.all()
            ],
            "is_active": template.is_active,
            "category": template.category,
            "tags": template.tags,
            "is_favorite": template.is_favorite,
            "usage_count": template.usage_count,
            "created_by": {
                "id": template.created_by.pk,
                "username": template.created_by.username,
            } if template.created_by else None,
            "default_start_time": template.default_start_time.strftime("%H:%M") if template.default_start_time else None,
            "default_end_time": template.default_end_time.strftime("%H:%M") if template.default_end_time else None,
            "notes": template.notes,
            "created": template.created.isoformat(),
        }
        return Response(data)

    elif request.method == "PUT":
        try:
            if "name" in request.data:
                template.name = request.data["name"]
            if "shift_type" in request.data:
                template.shift_type = request.data["shift_type"]
            if "description" in request.data:
                template.description = request.data["description"]
            if "duration_hours" in request.data:
                template.duration_hours = request.data["duration_hours"]
            if "is_active" in request.data:
                template.is_active = request.data["is_active"]
            if "category" in request.data:
                template.category = request.data["category"]
            if "tags" in request.data:
                template.tags = request.data["tags"]
            if "is_favorite" in request.data:
                template.is_favorite = request.data["is_favorite"]
            if "default_start_time" in request.data:
                template.default_start_time = request.data["default_start_time"]
            if "default_end_time" in request.data:
                template.default_end_time = request.data["default_end_time"]
            if "notes" in request.data:
                template.notes = request.data["notes"]
            
            template.save()
            
            # Update skills if provided
            if "skill_ids" in request.data:
                template.skills_required.set(request.data["skill_ids"])
            
            return Response({"message": "Template updated successfully."})
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

    elif request.method == "DELETE":
        template.delete()
        return Response(
            {"message": "Template deleted successfully."},
            status=status.HTTP_204_NO_CONTENT,
        )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def clone_template(request, pk):
    """Clone an existing template."""
    from team_planner.shifts.models import ShiftTemplate

    # Check permissions
    has_permission = (
        request.user.is_superuser
        or request.user.profile.role.permissions.filter(
            name__in=["can_run_orchestrator", "can_manage_team"]
        ).exists()
    )
    
    if not has_permission:
        return Response(
            {"error": "You do not have permission to clone templates."},
            status=status.HTTP_403_FORBIDDEN,
        )

    original = get_object_or_404(ShiftTemplate, pk=pk)
    
    try:
        # Clone the template
        cloned = ShiftTemplate.objects.create(
            name=f"{original.name} (Copy)",
            shift_type=original.shift_type,
            description=original.description,
            duration_hours=original.duration_hours,
            is_active=original.is_active,
            category=original.category,
            tags=original.tags,
            is_favorite=False,  # Don't clone favorite status
            usage_count=0,  # Reset usage count
            created_by=request.user,
            default_start_time=original.default_start_time,
            default_end_time=original.default_end_time,
            notes=original.notes,
        )
        
        # Clone skills
        cloned.skills_required.set(original.skills_required.all())
        
        return Response(
            {
                "id": cloned.pk,
                "message": "Template cloned successfully.",
            },
            status=status.HTTP_201_CREATED,
        )
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def toggle_favorite(request, pk):
    """Toggle favorite status of a template."""
    from team_planner.shifts.models import ShiftTemplate

    template = get_object_or_404(ShiftTemplate, pk=pk)
    
    template.is_favorite = not template.is_favorite
    template.save(update_fields=["is_favorite"])
    
    return Response({
        "message": f"Template {'added to' if template.is_favorite else 'removed from'} favorites.",
        "is_favorite": template.is_favorite,
    })


# ============================================================================
# BULK OPERATIONS APIs
# ============================================================================

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def bulk_create_shifts(request):
    """
    Bulk create shifts from a template.
    
    Request body:
    {
        "template_id": 1,
        "start_date": "2025-01-01",
        "end_date": "2025-01-31",
        "employee_ids": [1, 2, 3],
        "start_time": "09:00:00",  // optional
        "end_time": "17:00:00",    // optional
        "rotation_strategy": "sequential",  // or "distribute"
        "dry_run": false
    }
    """
    from datetime import datetime
    from .bulk_service import BulkShiftService, BulkOperationError
    
    try:
        template_id = request.data.get("template_id")
        start_date_str = request.data.get("start_date")
        end_date_str = request.data.get("end_date")
        employee_ids = request.data.get("employee_ids", [])
        start_time_str = request.data.get("start_time")
        end_time_str = request.data.get("end_time")
        rotation_strategy = request.data.get("rotation_strategy", "sequential")
        dry_run = request.data.get("dry_run", False)
        
        if not all([template_id, start_date_str, end_date_str, employee_ids]):
            return Response(
                {"error": "template_id, start_date, end_date, and employee_ids are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        # Parse dates
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
        
        # Parse times if provided
        start_time = None
        end_time = None
        if start_time_str:
            start_time = datetime.strptime(start_time_str, "%H:%M:%S").time()
        if end_time_str:
            end_time = datetime.strptime(end_time_str, "%H:%M:%S").time()
        
        result = BulkShiftService.bulk_create_from_template(
            template_id=template_id,
            date_range=(start_date, end_date),
            employee_ids=employee_ids,
            start_time=start_time,
            end_time=end_time,
            rotation_strategy=rotation_strategy,
            dry_run=dry_run,
        )
        
        return Response(result, status=status.HTTP_200_OK)
        
    except BulkOperationError as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_400_BAD_REQUEST,
        )
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def bulk_assign_employees(request):
    """
    Bulk assign an employee to multiple shifts.
    
    Request body:
    {
        "shift_ids": [1, 2, 3, 4],
        "employee_id": 5,
        "dry_run": false
    }
    """
    from .bulk_service import BulkShiftService, BulkOperationError
    
    try:
        shift_ids = request.data.get("shift_ids", [])
        employee_id = request.data.get("employee_id")
        dry_run = request.data.get("dry_run", False)
        
        if not all([shift_ids, employee_id]):
            return Response(
                {"error": "shift_ids and employee_id are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        result = BulkShiftService.bulk_assign_employees(
            shift_ids=shift_ids,
            employee_id=employee_id,
            dry_run=dry_run,
        )
        
        return Response(result, status=status.HTTP_200_OK)
        
    except BulkOperationError as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_400_BAD_REQUEST,
        )
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def bulk_modify_times(request):
    """
    Bulk modify shift times.
    
    Request body:
    {
        "shift_ids": [1, 2, 3, 4],
        "new_start_time": "10:00:00",  // optional
        "new_end_time": "18:00:00",    // optional
        "time_offset_minutes": 60,     // optional (shift times by this amount)
        "dry_run": false
    }
    """
    from datetime import datetime
    from .bulk_service import BulkShiftService, BulkOperationError
    
    try:
        shift_ids = request.data.get("shift_ids", [])
        new_start_time_str = request.data.get("new_start_time")
        new_end_time_str = request.data.get("new_end_time")
        time_offset_minutes = request.data.get("time_offset_minutes")
        dry_run = request.data.get("dry_run", False)
        
        if not shift_ids:
            return Response(
                {"error": "shift_ids is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        # Parse times if provided
        new_start_time = None
        new_end_time = None
        if new_start_time_str:
            new_start_time = datetime.strptime(new_start_time_str, "%H:%M:%S").time()
        if new_end_time_str:
            new_end_time = datetime.strptime(new_end_time_str, "%H:%M:%S").time()
        
        result = BulkShiftService.bulk_modify_times(
            shift_ids=shift_ids,
            new_start_time=new_start_time,
            new_end_time=new_end_time,
            time_offset_minutes=time_offset_minutes,
            dry_run=dry_run,
        )
        
        return Response(result, status=status.HTTP_200_OK)
        
    except BulkOperationError as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_400_BAD_REQUEST,
        )
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def bulk_delete_shifts(request):
    """
    Bulk delete shifts.
    
    Request body:
    {
        "shift_ids": [1, 2, 3, 4],
        "force": false,  // skip validation
        "dry_run": false
    }
    """
    from .bulk_service import BulkShiftService, BulkOperationError
    
    try:
        shift_ids = request.data.get("shift_ids", [])
        force = request.data.get("force", False)
        dry_run = request.data.get("dry_run", False)
        
        if not shift_ids:
            return Response(
                {"error": "shift_ids is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        result = BulkShiftService.bulk_delete(
            shift_ids=shift_ids,
            force=force,
            dry_run=dry_run,
        )
        
        return Response(result, status=status.HTTP_200_OK)
        
    except BulkOperationError as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_400_BAD_REQUEST,
        )
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def export_shifts_csv(request):
    """
    Export shifts to CSV.
    
    Request body:
    {
        "shift_ids": [1, 2, 3, 4]
    }
    """
    from django.http import HttpResponse
    from .bulk_service import BulkShiftService
    
    try:
        shift_ids = request.data.get("shift_ids", [])
        
        if not shift_ids:
            return Response(
                {"error": "shift_ids is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        csv_content = BulkShiftService.export_to_csv(shift_ids)
        
        response = HttpResponse(csv_content, content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="shifts_export.csv"'
        return response
        
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def import_shifts_csv(request):
    """
    Import shifts from CSV.
    
    Request body:
    {
        "csv_content": "...",  // CSV string
        "dry_run": false
    }
    
    Or send file:
    multipart/form-data with 'file' field
    """
    from .bulk_service import BulkShiftService
    
    try:
        # Handle file upload
        if 'file' in request.FILES:
            csv_file = request.FILES['file']
            csv_content = csv_file.read().decode('utf-8')
        else:
            csv_content = request.data.get("csv_content")
        
        if not csv_content:
            return Response(
                {"error": "csv_content or file is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        dry_run = request.data.get("dry_run", False)
        
        result = BulkShiftService.import_from_csv(
            csv_content=csv_content,
            dry_run=dry_run,
        )
        
        return Response(result, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# ========== Advanced Approval System API ==========

@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def approval_rules_api(request):
    """
    List or create approval rules.
    
    GET: List all active approval rules (managers/admins only)
    POST: Create a new approval rule (managers/admins only)
    """
    from .models import SwapApprovalRule
    
    # Check permissions
    if not (request.user.is_superuser or 
            request.user.has_perm('shifts.can_manage_team')):
        return Response(
            {"error": "Permission denied. Manager or admin access required."},
            status=status.HTTP_403_FORBIDDEN,
        )
    
    if request.method == "GET":
        rules = SwapApprovalRule.objects.filter(is_active=True).order_by('-priority', 'name')
        
        rules_data = []
        for rule in rules:
            rules_data.append({
                "id": rule.id,
                "name": rule.name,
                "description": rule.description,
                "priority": rule.priority,
                "priority_display": rule.get_priority_display(),
                "is_active": rule.is_active,
                "applies_to_shift_types": rule.applies_to_shift_types,
                "auto_approve_enabled": rule.auto_approve_enabled,
                "auto_approve_same_shift_type": rule.auto_approve_same_shift_type,
                "auto_approve_max_advance_hours": rule.auto_approve_max_advance_hours,
                "auto_approve_min_seniority_months": rule.auto_approve_min_seniority_months,
                "auto_approve_skills_match_required": rule.auto_approve_skills_match_required,
                "requires_manager_approval": rule.requires_manager_approval,
                "requires_admin_approval": rule.requires_admin_approval,
                "approval_levels_required": rule.approval_levels_required,
                "allow_delegation": rule.allow_delegation,
                "max_swaps_per_month_per_employee": rule.max_swaps_per_month_per_employee,
                "notify_on_auto_approval": rule.notify_on_auto_approval,
                "created": rule.created.isoformat(),
                "modified": rule.modified.isoformat(),
            })
        
        return Response(rules_data, status=status.HTTP_200_OK)
    
    elif request.method == "POST":
        try:
            rule = SwapApprovalRule.objects.create(
                name=request.data.get("name"),
                description=request.data.get("description", ""),
                priority=request.data.get("priority", 3),
                is_active=request.data.get("is_active", True),
                applies_to_shift_types=request.data.get("applies_to_shift_types", []),
                auto_approve_enabled=request.data.get("auto_approve_enabled", False),
                auto_approve_same_shift_type=request.data.get("auto_approve_same_shift_type", True),
                auto_approve_max_advance_hours=request.data.get("auto_approve_max_advance_hours"),
                auto_approve_min_seniority_months=request.data.get("auto_approve_min_seniority_months"),
                auto_approve_skills_match_required=request.data.get("auto_approve_skills_match_required", False),
                requires_manager_approval=request.data.get("requires_manager_approval", True),
                requires_admin_approval=request.data.get("requires_admin_approval", False),
                approval_levels_required=request.data.get("approval_levels_required", 1),
                allow_delegation=request.data.get("allow_delegation", True),
                max_swaps_per_month_per_employee=request.data.get("max_swaps_per_month_per_employee"),
                notify_on_auto_approval=request.data.get("notify_on_auto_approval", True),
            )
            
            return Response(
                {
                    "message": "Approval rule created successfully",
                    "id": rule.id,
                    "name": rule.name,
                },
                status=status.HTTP_201_CREATED,
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )


@api_view(["GET", "PUT", "DELETE"])
@permission_classes([IsAuthenticated])
def approval_rule_detail_api(request, pk):
    """
    Get, update, or delete a specific approval rule.
    """
    from .models import SwapApprovalRule
    
    # Check permissions
    if not (request.user.is_superuser or 
            request.user.has_perm('shifts.can_manage_team')):
        return Response(
            {"error": "Permission denied. Manager or admin access required."},
            status=status.HTTP_403_FORBIDDEN,
        )
    
    rule = get_object_or_404(SwapApprovalRule, pk=pk)
    
    if request.method == "GET":
        return Response({
            "id": rule.id,
            "name": rule.name,
            "description": rule.description,
            "priority": rule.priority,
            "priority_display": rule.get_priority_display(),
            "is_active": rule.is_active,
            "applies_to_shift_types": rule.applies_to_shift_types,
            "auto_approve_enabled": rule.auto_approve_enabled,
            "auto_approve_same_shift_type": rule.auto_approve_same_shift_type,
            "auto_approve_max_advance_hours": rule.auto_approve_max_advance_hours,
            "auto_approve_min_seniority_months": rule.auto_approve_min_seniority_months,
            "auto_approve_skills_match_required": rule.auto_approve_skills_match_required,
            "requires_manager_approval": rule.requires_manager_approval,
            "requires_admin_approval": rule.requires_admin_approval,
            "approval_levels_required": rule.approval_levels_required,
            "allow_delegation": rule.allow_delegation,
            "max_swaps_per_month_per_employee": rule.max_swaps_per_month_per_employee,
            "notify_on_auto_approval": rule.notify_on_auto_approval,
            "created": rule.created.isoformat(),
            "modified": rule.modified.isoformat(),
        }, status=status.HTTP_200_OK)
    
    elif request.method == "PUT":
        try:
            # Update fields
            rule.name = request.data.get("name", rule.name)
            rule.description = request.data.get("description", rule.description)
            rule.priority = request.data.get("priority", rule.priority)
            rule.is_active = request.data.get("is_active", rule.is_active)
            rule.applies_to_shift_types = request.data.get("applies_to_shift_types", rule.applies_to_shift_types)
            rule.auto_approve_enabled = request.data.get("auto_approve_enabled", rule.auto_approve_enabled)
            rule.auto_approve_same_shift_type = request.data.get("auto_approve_same_shift_type", rule.auto_approve_same_shift_type)
            rule.auto_approve_max_advance_hours = request.data.get("auto_approve_max_advance_hours", rule.auto_approve_max_advance_hours)
            rule.auto_approve_min_seniority_months = request.data.get("auto_approve_min_seniority_months", rule.auto_approve_min_seniority_months)
            rule.auto_approve_skills_match_required = request.data.get("auto_approve_skills_match_required", rule.auto_approve_skills_match_required)
            rule.requires_manager_approval = request.data.get("requires_manager_approval", rule.requires_manager_approval)
            rule.requires_admin_approval = request.data.get("requires_admin_approval", rule.requires_admin_approval)
            rule.approval_levels_required = request.data.get("approval_levels_required", rule.approval_levels_required)
            rule.allow_delegation = request.data.get("allow_delegation", rule.allow_delegation)
            rule.max_swaps_per_month_per_employee = request.data.get("max_swaps_per_month_per_employee", rule.max_swaps_per_month_per_employee)
            rule.notify_on_auto_approval = request.data.get("notify_on_auto_approval", rule.notify_on_auto_approval)
            rule.save()
            
            return Response(
                {"message": "Approval rule updated successfully"},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
    
    elif request.method == "DELETE":
        rule.delete()
        return Response(
            {"message": "Approval rule deleted successfully"},
            status=status.HTTP_204_NO_CONTENT,
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def swap_approval_chain_api(request, swap_id):
    """
    Get the approval chain for a swap request.
    """
    from .models import SwapApprovalChain
    
    swap_request = get_object_or_404(SwapRequest, pk=swap_id)
    
    # Check permissions - must be involved in the swap or have management permissions
    if not (swap_request.requesting_employee == request.user or
            swap_request.target_employee == request.user or
            request.user.is_superuser or
            request.user.has_perm('shifts.can_manage_team')):
        return Response(
            {"error": "Permission denied"},
            status=status.HTTP_403_FORBIDDEN,
        )
    
    chain = SwapApprovalChain.objects.filter(
        swap_request=swap_request
    ).select_related('approver', 'delegated_to', 'approval_rule').order_by('level')
    
    chain_data = []
    for step in chain:
        chain_data.append({
            "id": step.id,
            "level": step.level,
            "approver": {
                "id": step.approver.id,
                "username": step.approver.username,
                "email": step.approver.email,
            },
            "status": step.status,
            "status_display": step.get_status_display(),
            "decision_datetime": step.decision_datetime.isoformat() if step.decision_datetime else None,
            "decision_notes": step.decision_notes,
            "delegated_to": {
                "id": step.delegated_to.id,
                "username": step.delegated_to.username,
                "email": step.delegated_to.email,
            } if step.delegated_to else None,
            "auto_approved": step.auto_approved,
            "approval_rule": {
                "id": step.approval_rule.id,
                "name": step.approval_rule.name,
            } if step.approval_rule else None,
        })
    
    return Response(chain_data, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def approve_swap_step_api(request, swap_id):
    """
    Approve a step in the swap approval chain.
    """
    from .approval_service import SwapApprovalService
    from .models import SwapApprovalChain
    
    swap_request = get_object_or_404(SwapRequest, pk=swap_id)
    notes = request.data.get("notes", "")
    
    # Find the pending approval step for this user
    chain_step = SwapApprovalChain.objects.filter(
        swap_request=swap_request,
        approver=request.user,
        status=SwapApprovalChain.Status.PENDING,
    ).first()
    
    if not chain_step:
        return Response(
            {"error": "No pending approval found for you"},
            status=status.HTTP_404_NOT_FOUND,
        )
    
    try:
        result = SwapApprovalService.process_approval_decision(
            chain_step=chain_step,
            approver=request.user,
            decision='approve',
            notes=notes,
        )
        
        return Response(result, status=status.HTTP_200_OK)
        
    except ValueError as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_403_FORBIDDEN,
        )
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def reject_swap_step_api(request, swap_id):
    """
    Reject a step in the swap approval chain.
    """
    from .approval_service import SwapApprovalService
    from .models import SwapApprovalChain
    
    swap_request = get_object_or_404(SwapRequest, pk=swap_id)
    notes = request.data.get("notes", "")
    
    # Find the pending approval step for this user
    chain_step = SwapApprovalChain.objects.filter(
        swap_request=swap_request,
        approver=request.user,
        status=SwapApprovalChain.Status.PENDING,
    ).first()
    
    if not chain_step:
        return Response(
            {"error": "No pending approval found for you"},
            status=status.HTTP_404_NOT_FOUND,
        )
    
    try:
        result = SwapApprovalService.process_approval_decision(
            chain_step=chain_step,
            approver=request.user,
            decision='reject',
            notes=notes,
        )
        
        return Response(result, status=status.HTTP_200_OK)
        
    except ValueError as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_403_FORBIDDEN,
        )
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def delegate_swap_approval_api(request, swap_id):
    """
    Delegate a swap approval to another user.
    """
    from .approval_service import SwapApprovalService
    from .models import SwapApprovalChain
    
    swap_request = get_object_or_404(SwapRequest, pk=swap_id)
    delegate_id = request.data.get("delegate_id")
    notes = request.data.get("notes", "")
    
    if not delegate_id:
        return Response(
            {"error": "delegate_id is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    
    delegate = get_object_or_404(User, pk=delegate_id)
    
    # Find the pending approval step for this user
    chain_step = SwapApprovalChain.objects.filter(
        swap_request=swap_request,
        approver=request.user,
        status=SwapApprovalChain.Status.PENDING,
    ).first()
    
    if not chain_step:
        return Response(
            {"error": "No pending approval found for you"},
            status=status.HTTP_404_NOT_FOUND,
        )
    
    try:
        new_step = SwapApprovalService.delegate_approval(
            chain_step=chain_step,
            delegator=request.user,
            delegate=delegate,
            notes=notes,
        )
        
        return Response(
            {
                "message": "Approval delegated successfully",
                "new_approver": {
                    "id": new_step.approver.id,
                    "username": new_step.approver.username,
                },
            },
            status=status.HTTP_200_OK,
        )
        
    except ValueError as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_403_FORBIDDEN,
        )
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def pending_approvals_api(request):
    """
    Get all pending approvals for the current user.
    """
    from .approval_service import SwapApprovalService
    
    pending_steps = SwapApprovalService.get_pending_approvals_for_user(request.user)
    
    approvals_data = []
    for step in pending_steps:
        swap = step.swap_request
        approvals_data.append({
            "id": step.id,
            "swap_request": {
                "id": swap.id,
                "requesting_employee": {
                    "id": swap.requesting_employee.id,
                    "username": swap.requesting_employee.username,
                },
                "target_employee": {
                    "id": swap.target_employee.id,
                    "username": swap.target_employee.username,
                },
                "requesting_shift": {
                    "id": swap.requesting_shift.id,
                    "start": swap.requesting_shift.start_datetime.isoformat(),
                    "end": swap.requesting_shift.end_datetime.isoformat(),
                    "type": swap.requesting_shift.template.shift_type,
                },
                "target_shift": {
                    "id": swap.target_shift.id,
                    "start": swap.target_shift.start_datetime.isoformat(),
                    "end": swap.target_shift.end_datetime.isoformat(),
                    "type": swap.target_shift.template.shift_type,
                } if swap.target_shift else None,
                "reason": swap.reason,
                "created": swap.created.isoformat(),
            },
            "level": step.level,
            "approval_rule": {
                "id": step.approval_rule.id,
                "name": step.approval_rule.name,
            } if step.approval_rule else None,
        })
    
    return Response(approvals_data, status=status.HTTP_200_OK)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def approval_delegations_api(request):
    """
    List or create approval delegations.
    """
    from .models import ApprovalDelegation
    
    if request.method == "GET":
        # Get delegations where user is either delegator or delegate
        delegations = ApprovalDelegation.objects.filter(
            models.Q(delegator=request.user) | models.Q(delegate=request.user)
        ).select_related('delegator', 'delegate').order_by('-start_date')
        
        delegations_data = []
        for delegation in delegations:
            delegations_data.append({
                "id": delegation.id,
                "delegator": {
                    "id": delegation.delegator.id,
                    "username": delegation.delegator.username,
                },
                "delegate": {
                    "id": delegation.delegate.id,
                    "username": delegation.delegate.username,
                },
                "start_date": delegation.start_date.isoformat(),
                "end_date": delegation.end_date.isoformat() if delegation.end_date else None,
                "is_active": delegation.is_active,
                "is_currently_active": delegation.is_currently_active,
                "reason": delegation.reason,
            })
        
        return Response(delegations_data, status=status.HTTP_200_OK)
    
    elif request.method == "POST":
        try:
            delegate_id = request.data.get("delegate_id")
            if not delegate_id:
                return Response(
                    {"error": "delegate_id is required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            
            delegate = get_object_or_404(User, pk=delegate_id)
            
            delegation = ApprovalDelegation.objects.create(
                delegator=request.user,
                delegate=delegate,
                start_date=request.data.get("start_date"),
                end_date=request.data.get("end_date"),
                is_active=request.data.get("is_active", True),
                reason=request.data.get("reason", ""),
            )
            
            return Response(
                {
                    "message": "Delegation created successfully",
                    "id": delegation.id,
                },
                status=status.HTTP_201_CREATED,
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )


@api_view(["GET", "PUT", "DELETE"])
@permission_classes([IsAuthenticated])
def approval_delegation_detail_api(request, pk):
    """
    Get, update, or delete a specific delegation.
    """
    from .models import ApprovalDelegation
    
    delegation = get_object_or_404(ApprovalDelegation, pk=pk)
    
    # Check permissions - must be delegator
    if delegation.delegator != request.user:
        return Response(
            {"error": "Permission denied"},
            status=status.HTTP_403_FORBIDDEN,
        )
    
    if request.method == "GET":
        return Response({
            "id": delegation.id,
            "delegator": {
                "id": delegation.delegator.id,
                "username": delegation.delegator.username,
            },
            "delegate": {
                "id": delegation.delegate.id,
                "username": delegation.delegate.username,
            },
            "start_date": delegation.start_date.isoformat(),
            "end_date": delegation.end_date.isoformat() if delegation.end_date else None,
            "is_active": delegation.is_active,
            "is_currently_active": delegation.is_currently_active,
            "reason": delegation.reason,
        }, status=status.HTTP_200_OK)
    
    elif request.method == "PUT":
        try:
            delegation.delegate = get_object_or_404(User, pk=request.data.get("delegate_id", delegation.delegate.id))
            delegation.start_date = request.data.get("start_date", delegation.start_date)
            delegation.end_date = request.data.get("end_date", delegation.end_date)
            delegation.is_active = request.data.get("is_active", delegation.is_active)
            delegation.reason = request.data.get("reason", delegation.reason)
            delegation.save()
            
            return Response(
                {"message": "Delegation updated successfully"},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
    
    elif request.method == "DELETE":
        delegation.delete()
        return Response(
            {"message": "Delegation deleted successfully"},
            status=status.HTTP_204_NO_CONTENT,
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def swap_audit_trail_api(request, swap_id):
    """
    Get the audit trail for a swap request.
    """
    from .models import SwapApprovalAudit
    
    swap_request = get_object_or_404(SwapRequest, pk=swap_id)
    
    # Check permissions
    if not (swap_request.requesting_employee == request.user or
            swap_request.target_employee == request.user or
            request.user.is_superuser or
            request.user.has_perm('shifts.can_manage_team')):
        return Response(
            {"error": "Permission denied"},
            status=status.HTTP_403_FORBIDDEN,
        )
    
    audit_entries = SwapApprovalAudit.objects.filter(
        swap_request=swap_request
    ).select_related('actor', 'approval_chain', 'approval_rule').order_by('created')
    
    audit_data = []
    for entry in audit_entries:
        audit_data.append({
            "id": entry.id,
            "action": entry.action,
            "action_display": entry.get_action_display(),
            "actor": {
                "id": entry.actor.id,
                "username": entry.actor.username,
            } if entry.actor else None,
            "approval_chain_level": entry.approval_chain.level if entry.approval_chain else None,
            "approval_rule": {
                "id": entry.approval_rule.id,
                "name": entry.approval_rule.name,
            } if entry.approval_rule else None,
            "notes": entry.notes,
            "metadata": entry.metadata,
            "created": entry.created.isoformat(),
        })
    
    return Response(audit_data, status=status.HTTP_200_OK)
