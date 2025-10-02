from datetime import datetime

from django.contrib.auth import get_user_model
from django.db.models import QuerySet
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import status
from rest_framework import viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from team_planner.rbac.decorators import require_permission
from team_planner.notifications.mailer import build_ics_for_leave
from team_planner.notifications.mailer import notify_leave_approved
from team_planner.notifications.services import NotificationService

from .models import LeaveRequest
from .models import LeaveType
from .serializers import LeaveRequestSerializer
from .serializers import LeaveTypeSerializer

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
            "employee", "leave_type", "approved_by",
        ).order_by("-created")

        req = getattr(self, "request", None)
        user = getattr(req, "user", None)
        if not user:
            # No request/user available (e.g., direct method call in tests); return unfiltered
            return queryset

        # Filter based on permissions
        if (
            user.has_perm("leaves.change_leaverequest")
            or user.is_staff
            or user.is_superuser
        ):
            # Staff, admins, and users with change permission can see all requests
            return queryset
        # Regular users can only see their own requests
        return queryset.filter(employee=user)

    def perform_create(self, serializer):
        """Set the employee to the current user when creating a leave request."""
        serializer.save(employee=self.request.user)

    @action(detail=False, methods=["post"], url_path="create")
    def create_request(self, request):
        """Create a new leave request (alternative endpoint)."""
        # Ensure view has a request when called directly
        self.request = request
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            self.perform_create(serializer)
            instance = getattr(serializer, "instance", None)
            return Response(
                {
                    "id": int(getattr(instance, "id", 0)),
                    "message": "Leave request created successfully.",
                    "has_conflicts": bool(
                        getattr(instance, "has_shift_conflicts", False),
                    ),
                    "conflict_warning": "This request conflicts with assigned shifts."
                    if getattr(instance, "has_shift_conflicts", False)
                    else None,
                },
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["get"])
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

    @action(detail=False, methods=["get"])
    def pending(self, request):
        """Get pending leave requests."""
        # Ensure view has a request when called directly
        self.request = request
        queryset = self.get_queryset().filter(status="pending")
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @require_permission('can_request_leave')
    def create(self, request, *args, **kwargs):
        """Create leave request - requires can_request_leave permission."""
        return super().create(request, *args, **kwargs)

    @action(detail=True, methods=["post"])
    @require_permission('can_approve_leave')
    def approve(self, request, pk=None):
        """Approve a leave request - requires can_approve_leave permission."""
        # Ensure view has a request when called directly
        self.request = request
        leave_request = self.get_object()
        user = request.user

        # Check if user has permission to approve
        if not (
            user.has_perm("leaves.change_leaverequest")
            or user.is_staff
            or user.is_superuser
        ):
            return Response(
                {"error": "You do not have permission to approve leave requests."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if leave_request.status != "pending":
            return Response(
                {"error": "Leave request is not in pending status."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check if leave can be approved (no unresolved shift conflicts)
        if not leave_request.can_be_approved():
            return Response(
                {
                    "error": "Cannot approve leave request. There are unresolved shift conflicts.",
                    "detail": "All conflicting shifts must have approved swap requests before the leave can be approved.",
                    "blocking_message": leave_request.get_blocking_message(),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        leave_request.status = "approved"
        leave_request.approved_by = user

        leave_request.approved_at = timezone.now()
        leave_request.save()

        # Notify employee with ICS
        try:
            ics = build_ics_for_leave(leave_request)
            email = getattr(leave_request.employee, "email", None)
            notify_leave_approved(email, ics)
        except Exception:
            pass

        # Send notification via NotificationService
        try:
            NotificationService.notify_leave_approved(
                employee=leave_request.employee,
                leave_request=leave_request,
                approved_by=user
            )
        except Exception as e:
            # Log but don't fail the request if notification fails
            print(f"Failed to send leave approved notification: {e}")

        serializer = self.get_serializer(leave_request)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    @require_permission('can_approve_leave')
    def reject(self, request, pk=None):
        """Reject a leave request - requires can_approve_leave permission."""
        # Ensure view has a request when called directly
        self.request = request
        leave_request = self.get_object()
        user = request.user

        # Check if user has permission to reject
        if not (
            user.has_perm("leaves.change_leaverequest")
            or user.is_staff
            or user.is_superuser
        ):
            return Response(
                {"error": "You do not have permission to reject leave requests."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if leave_request.status != "pending":
            return Response(
                {"error": "Leave request is not in pending status."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        rejection_reason = request.data.get("rejection_reason", "")
        leave_request.status = "rejected"
        leave_request.approved_by = user
        leave_request.rejection_reason = rejection_reason
        leave_request.save()

        # Send notification via NotificationService
        try:
            NotificationService.notify_leave_rejected(
                employee=leave_request.employee,
                leave_request=leave_request,
                rejected_by=user,
                reason=rejection_reason
            )
        except Exception as e:
            # Log but don't fail the request if notification fails
            print(f"Failed to send leave rejected notification: {e}")

        self.get_serializer(leave_request)
        return Response(
            {"message": "Leave request rejected successfully.", "status": "rejected"},
        )

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        """Cancel a leave request."""
        # Ensure view has a request when called directly
        self.request = request
        leave_request = self.get_object()
        user = request.user

        # Only the employee can cancel their own request
        if leave_request.employee != user:
            return Response(
                {"error": "You can only cancel your own leave requests."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if leave_request.status not in ["pending", "approved"]:
            return Response(
                {"error": "Leave request cannot be cancelled."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        leave_request.status = "cancelled"
        leave_request.save()

        return Response(
            {"message": "Leave request cancelled successfully.", "status": "cancelled"},
        )

    @action(detail=True, methods=["get"], url_path="conflicting-shifts")
    def conflicting_shifts(self, request, pk=None):
        """Get shifts that conflict with this leave request."""
        # Ensure view has a request when called directly
        self.request = request
        leave_request = self.get_object()

        # Check if user can access this leave request
        if not (
            request.user.has_perm("leaves.view_leaverequest")
            or request.user.is_staff
            or leave_request.employee == request.user
        ):
            return Response(
                {"error": "Permission denied."}, status=status.HTTP_403_FORBIDDEN,
            )

        conflicting_shifts = leave_request.get_conflicting_shifts()

        # Serialize the shift data
        shifts_data = []
        for shift in conflicting_shifts:
            shifts_data.append(
                {
                    "id": shift.id,
                    "start_datetime": shift.start_datetime,
                    "end_datetime": shift.end_datetime,
                    "shift_type": shift.template.shift_type
                    if shift.template
                    else "unknown",
                    "shift_name": shift.template.name
                    if shift.template
                    else "Unknown Shift",
                    "status": shift.status,
                    "duration_hours": shift.template.duration_hours
                    if shift.template
                    else 0,
                    "notes": shift.notes or "",
                },
            )

        return Response(
            {
                "leave_request_id": leave_request.id,
                "conflicts_count": len(shifts_data),
                "conflicting_shifts": shifts_data,
            },
        )

    @action(detail=False, methods=["get"])
    def check_conflicts(self, request):
        """Check for conflicts when creating a leave request using provided dates and optional times."""
        # Ensure view has a request when called directly
        self.request = request
        start_date_s = request.query_params.get("start_date")
        end_date_s = request.query_params.get("end_date")
        start_time_s = request.query_params.get("start_time")
        end_time_s = request.query_params.get("end_time")
        leave_type_id = request.query_params.get("leave_type_id")

        if not start_date_s or not end_date_s:
            return Response(
                {"error": "Both start_date and end_date are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        start_d = parse_date(start_date_s)
        end_d = parse_date(end_date_s)
        if not start_d or not end_d:
            return Response(
                {"error": "Invalid date format."}, status=status.HTTP_400_BAD_REQUEST,
            )

        # Build a transient LeaveRequest-like object to reuse conflict logic
        leave_type = None
        if leave_type_id:
            try:
                leave_type = LeaveType.objects.get(pk=leave_type_id)
            except LeaveType.DoesNotExist:
                leave_type = None
        tmp = LeaveRequest(
            employee=request.user,
            leave_type=leave_type or LeaveType(name="tmp"),
            start_date=start_d,
            end_date=end_d,
        )
        # Override type-level time window if provided
        if start_time_s:
            try:
                from datetime import time as _t

                hh, mm = [int(x) for x in start_time_s.split(":")]
                tmp.start_time = _t(hh, mm)
            except Exception:
                pass
        if end_time_s:
            try:
                from datetime import time as _t

                hh, mm = [int(x) for x in end_time_s.split(":")]
                tmp.end_time = _t(hh, mm)
            except Exception:
                pass

        conflicts_qs = tmp.get_conflicting_shifts()
        conflicts = []
        for s in conflicts_qs.select_related("template", "assigned_employee"):
            conflicts.append(
                {
                    "id": int(s.id),  # type: ignore[arg-type]
                    "shift_type": getattr(s.template, "shift_type", "unknown"),
                    "shift_name": getattr(s.template, "name", "Shift"),
                    "start_datetime": s.start_datetime.isoformat(),
                    "end_datetime": s.end_datetime.isoformat(),
                    "status": s.status,
                },
            )

        # Rudimentary suggestions: list team members without overlapping shifts for the same window
        suggestions = []
        if conflicts:
            from django.contrib.auth import get_user_model

            from team_planner.teams.models import TeamMembership

            User = get_user_model()

            team_ids = TeamMembership.objects.filter(
                user=request.user, is_active=True,
            ).values_list("team_id", flat=True)
            candidates = (
                User.objects.filter(
                    teammembership__team_id__in=team_ids, is_active=True,
                )
                .exclude(id=request.user.id)
                .distinct()
            )

            for s in conflicts_qs:
                avail = candidates.exclude(
                    assigned_shifts__start_datetime__lt=s.end_datetime,
                    assigned_shifts__end_datetime__gt=s.start_datetime,
                )
                suggestions.append(
                    {
                        "shift_id": int(s.id),  # type: ignore[arg-type]
                        "candidate_ids": list(avail.values_list("id", flat=True)[:10]),
                    },
                )

        return Response(
            {
                "has_conflicts": bool(conflicts),
                "conflicts": conflicts,
                "suggestions": suggestions,
                "message": "Conflicts detected."
                if conflicts
                else "No conflicts found.",
            },
        )

    @action(detail=False, methods=["get"])
    def user_stats(self, request):
        """Get user's leave statistics."""
        # Ensure view has a request when called directly
        self.request = request
        user = request.user
        current_year = datetime.now().year

        # Get user's leave requests for current year
        user_requests = LeaveRequest.objects.filter(
            employee=user, start_date__year=current_year,
        )

        stats = {
            "total_requests": user_requests.count(),
            "pending_requests": user_requests.filter(status="pending").count(),
            "approved_requests": user_requests.filter(status="approved").count(),
            "rejected_requests": user_requests.filter(status="rejected").count(),
            "days_used_this_year": sum(
                req.days_requested for req in user_requests.filter(status="approved")
            ),
            "current_year": current_year,
        }

        return Response(stats)


class LeaveTypeViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for leave types (read-only)."""

    queryset = LeaveType.objects.all()
    serializer_class = LeaveTypeSerializer
    permission_classes = [IsAuthenticated]


# ========== Leave Conflict Resolution API ==========

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def check_leave_conflicts(request):
    """
    Check for conflicts before creating a leave request.
    
    POST /api/leaves/check-conflicts/
    {
        "employee_id": 1,
        "start_date": "2025-02-01",
        "end_date": "2025-02-05",
        "team_id": 1  // optional
    }
    """
    from .conflict_service import LeaveConflictDetector
    
    employee_id = request.data.get("employee_id") or request.user.id
    start_date = parse_date(request.data.get("start_date"))
    end_date = parse_date(request.data.get("end_date"))
    team_id = request.data.get("team_id")
    department_id = request.data.get("department_id")
    
    if not start_date or not end_date:
        return Response(
            {"error": "start_date and end_date are required"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    
    employee = User.objects.get(id=employee_id)
    
    # Check for personal overlaps
    personal_conflicts = LeaveConflictDetector.detect_overlapping_requests(
        employee, start_date, end_date
    )
    
    # Check for team conflicts
    team_conflicts = LeaveConflictDetector.detect_team_conflicts(
        start_date, end_date, team_id, department_id
    )
    
    # Check staffing levels
    staffing = LeaveConflictDetector.analyze_staffing_levels(
        start_date, end_date, team_id, department_id, min_required_staff=2
    )
    
    # Check shift conflicts
    shift_conflicts = LeaveConflictDetector.get_shift_conflicts(
        employee, start_date, end_date
    )
    
    return Response({
        "has_conflicts": len(personal_conflicts) > 0 or staffing['is_understaffed'],
        "personal_conflicts": [
            {
                "id": c.id,
                "start_date": c.start_date.isoformat(),
                "end_date": c.end_date.isoformat(),
                "leave_type": c.leave_type.name,
                "status": c.status,
            }
            for c in personal_conflicts
        ],
        "team_conflicts_by_day": team_conflicts,
        "staffing_analysis": staffing,
        "shift_conflicts": [
            {
                "id": s.id,
                "start": s.start_datetime.isoformat(),
                "end": s.end_datetime.isoformat(),
                "type": s.template.shift_type,
                "status": s.status,
            }
            for s in shift_conflicts
        ],
    }, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def suggest_alternative_dates(request):
    """
    Suggest alternative dates for a leave request.
    
    POST /api/leaves/suggest-alternatives/
    {
        "employee_id": 1,
        "start_date": "2025-02-01",
        "days_requested": 5,
        "team_id": 1  // optional
    }
    """
    from .conflict_service import LeaveConflictDetector
    
    employee_id = request.data.get("employee_id") or request.user.id
    start_date = parse_date(request.data.get("start_date"))
    days_requested = int(request.data.get("days_requested", 1))
    team_id = request.data.get("team_id")
    department_id = request.data.get("department_id")
    
    if not start_date:
        return Response(
            {"error": "start_date is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    
    employee = User.objects.get(id=employee_id)
    
    suggestions = LeaveConflictDetector.suggest_alternative_dates(
        employee, start_date, days_requested, team_id, department_id
    )
    
    return Response({
        "suggestions": [
            {
                "start_date": s['start_date'].isoformat(),
                "end_date": s['end_date'].isoformat(),
                "conflict_score": s['conflict_score'],
                "is_understaffed": s['is_understaffed'],
                "days_offset": s['days_offset'],
            }
            for s in suggestions
        ],
    }, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
@require_permission('can_approve_leave')
def get_conflicting_requests(request):
    """
    Get all conflicting leave requests that need resolution.
    
    GET /api/leaves/conflicts/
    ?start_date=2025-02-01&end_date=2025-02-28
    """
    start_date = parse_date(request.query_params.get("start_date"))
    end_date = parse_date(request.query_params.get("end_date"))
    team_id = request.query_params.get("team_id")
    department_id = request.query_params.get("department_id")
    
    if not start_date or not end_date:
        return Response(
            {"error": "start_date and end_date are required"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    
    from .conflict_service import LeaveConflictDetector
    
    # Get team conflicts
    team_conflicts = LeaveConflictDetector.detect_team_conflicts(
        start_date, end_date, team_id, department_id
    )
    
    # Filter to days with 2+ people on leave
    conflict_days = {
        day_key: day_data
        for day_key, day_data in team_conflicts.items()
        if day_data['leave_count'] >= 2
    }
    
    # Get staffing analysis
    staffing = LeaveConflictDetector.analyze_staffing_levels(
        start_date, end_date, team_id, department_id, min_required_staff=2
    )
    
    return Response({
        "conflict_days": conflict_days,
        "understaffed_days": staffing['understaffed_days'],
        "warning_days": staffing['warning_days'],
        "total_team_size": staffing['total_team_size'],
    }, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@require_permission('can_approve_leave')
def resolve_conflict(request):
    """
    Resolve a leave conflict by approving one request and rejecting others.
    
    POST /api/leaves/resolve-conflict/
    {
        "approve_request_id": 15,
        "reject_request_ids": [16, 17],
        "resolution_notes": "Approved based on seniority"
    }
    """
    from .conflict_service import LeaveConflictResolver
    
    approve_id = request.data.get("approve_request_id")
    reject_ids = request.data.get("reject_request_ids", [])
    resolution_notes = request.data.get("resolution_notes", "")
    
    if not approve_id:
        return Response(
            {"error": "approve_request_id is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    
    try:
        request_to_approve = LeaveRequest.objects.get(id=approve_id)
        requests_to_reject = LeaveRequest.objects.filter(id__in=reject_ids)
        
        result = LeaveConflictResolver.apply_resolution(
            request_to_approve,
            list(requests_to_reject),
            request.user,
            resolution_notes,
        )
        
        return Response(result, status=status.HTTP_200_OK)
        
    except LeaveRequest.DoesNotExist:
        return Response(
            {"error": "Leave request not found"},
            status=status.HTTP_404_NOT_FOUND,
        )
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@require_permission('can_approve_leave')
def get_resolution_recommendation(request):
    """
    Get AI-recommended resolution for conflicting requests.
    
    POST /api/leaves/recommend-resolution/
    {
        "request_ids": [15, 16, 17]
    }
    """
    from .conflict_service import LeaveConflictResolver
    
    request_ids = request.data.get("request_ids", [])
    
    if not request_ids:
        return Response(
            {"error": "request_ids is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    
    try:
        conflicting_requests = list(
            LeaveRequest.objects.filter(id__in=request_ids).select_related(
                'employee', 'leave_type'
            )
        )
        
        recommendation = LeaveConflictResolver.get_recommended_resolution(
            conflicting_requests
        )
        
        # Serialize the recommendation
        recommended_req = recommendation['recommended']
        
        return Response({
            "recommended_request": {
                "id": recommended_req.id,
                "employee": {
                    "id": recommended_req.employee.id,
                    "name": recommended_req.employee.get_full_name(),
                },
                "start_date": recommended_req.start_date.isoformat(),
                "end_date": recommended_req.end_date.isoformat(),
                "leave_type": recommended_req.leave_type.name,
            } if recommended_req else None,
            "recommendation_details": recommendation['recommendation_details'],
            "vote_counts": recommendation['vote_counts'],
            "alternatives": [
                {
                    "id": alt.id,
                    "employee": {
                        "id": alt.employee.id,
                        "name": alt.employee.get_full_name(),
                    },
                    "start_date": alt.start_date.isoformat(),
                    "end_date": alt.end_date.isoformat(),
                }
                for alt in recommendation['alternatives']
            ],
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
