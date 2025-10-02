from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.mixins import CreateModelMixin
from rest_framework.mixins import ListModelMixin
from rest_framework.mixins import RetrieveModelMixin
from rest_framework.mixins import UpdateModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from team_planner.rbac.decorators import require_permission
from .serializers import UserSerializer

User = get_user_model()


class UserViewSet(
    RetrieveModelMixin,
    ListModelMixin,
    UpdateModelMixin,
    CreateModelMixin,
    GenericViewSet,
):
    serializer_class = UserSerializer
    queryset = User.objects.all()
    lookup_field = "username"
    permission_classes = [IsAuthenticated]

    def get_object(self):
        """Override to support both username and ID lookups."""
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        lookup_value = self.kwargs.get(lookup_url_kwarg)
        
        # Try to get by ID first (if it's a number)
        if lookup_value and lookup_value.isdigit():
            try:
                queryset = self.filter_queryset(self.get_queryset())
                obj = queryset.get(id=int(lookup_value))
                self.check_object_permissions(self.request, obj)
                return obj
            except User.DoesNotExist:
                pass
        
        # Fall back to username lookup
        return super().get_object()

    def get_queryset(self):
        # If user is staff/admin, they can see all users
        if self.request.user.is_staff or self.request.user.is_superuser:
            return self.queryset.all()

        # Regular users can only see themselves
        return self.queryset.filter(id=self.request.user.id)

    def get_permissions(self):
        """Set permissions based on action."""
        if self.action == "create":
            # Only staff/admin can create users
            permission_classes = [IsAuthenticated]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]

    @require_permission('can_manage_users')
    def list(self, request, *args, **kwargs):
        """List users - requires can_manage_users permission."""
        return super().list(request, *args, **kwargs)
    
    @require_permission('can_manage_users')
    def create(self, request, *args, **kwargs):
        """Create user - requires can_manage_users permission."""
        return super().create(request, *args, **kwargs)
    
    @require_permission('can_manage_users')
    def update(self, request, *args, **kwargs):
        """Update user - requires can_manage_users permission."""
        return super().update(request, *args, **kwargs)
    
    @require_permission('can_manage_users')
    def partial_update(self, request, *args, **kwargs):
        """Partially update user - requires can_manage_users permission."""
        return super().partial_update(request, *args, **kwargs)

    def perform_create(self, serializer):
        """Override to add permission check for user creation."""
        if not (self.request.user.is_staff or self.request.user.is_superuser):
            from rest_framework.exceptions import PermissionDenied

            msg = "Only staff members can create users."
            raise PermissionDenied(msg)
        serializer.save()

    @action(detail=False)
    def me(self, request):
        # Return a minimal payload as expected by tests
        user = request.user
        base_url = request.build_absolute_uri("/").rstrip("/")
        url = f"{base_url}/api/users/{user.username}/"
        return Response(
            status=status.HTTP_200_OK,
            data={
                "username": user.username,
                "url": url,
                "name": user.name,
            },
        )

    @action(detail=False, url_path="me/full")
    def me_full(self, request):
        """Return full user info (used by frontend for RBAC/navigation)."""
        serializer = UserSerializer(request.user, context={"request": request})
        return Response(status=status.HTTP_200_OK, data=serializer.data)

    @action(detail=False, methods=["put", "patch"], url_path="me/profile")
    def update_profile(self, request):
        """Update user and employee profile data."""
        user = request.user
        data = request.data

        # Handle name field properly
        if "first_name" in data or "last_name" in data:
            first_name = data.get("first_name", "").strip()
            last_name = data.get("last_name", "").strip()
            # Combine first_name and last_name into the name field
            full_name = f"{first_name} {last_name}".strip()
            user.name = full_name

        # Update other user fields
        user_fields = ["email"]
        for field in user_fields:
            if field in data:
                setattr(user, field, data[field])

        user.save()

        # Update employee profile if it exists
        try:

            employee_profile = user.employee_profile

            # Map frontend field names to backend field names
            profile_field_mapping = {
                "phone": "phone_number",
                "phone_number": "phone_number",
                "emergency_contact_name": "emergency_contact_name",
                "emergency_contact_phone": "emergency_contact_phone",
                "employment_type": "employment_type",
                "status": "status",
                "hire_date": "hire_date",
                "termination_date": "termination_date",
                "salary": "salary",
                "available_for_incidents": "available_for_incidents",
                "available_for_waakdienst": "available_for_waakdienst",
                "can_work_weekends": "available_for_waakdienst",
            }

            for frontend_field, backend_field in profile_field_mapping.items():
                if frontend_field in data:
                    setattr(employee_profile, backend_field, data[frontend_field])

            employee_profile.save()

        except Exception:
            # Employee profile doesn't exist or other error, which is fine for some users
            pass

        # Return updated user data
        serializer = UserSerializer(user, context={"request": request})
        return Response(status=status.HTTP_200_OK, data=serializer.data)

    @action(detail=False, methods=["get"], url_path="me/dashboard")
    def dashboard(self, request):
        """Get user-specific dashboard data."""
        from team_planner.shifts.models import Shift
        from team_planner.shifts.models import SwapRequest

        user = request.user
        today = timezone.now().date()

        # Get upcoming shifts (next 5)
        upcoming_shifts = Shift.objects.filter(
            assigned_employee=user, start_datetime__gte=timezone.now(),
        ).order_by("start_datetime")[:5]

        upcoming_shifts_data = [
            {
                "id": shift.id,
                "title": f"{shift.template.name} - {shift.template.shift_type}",
                "start_time": shift.start_datetime.isoformat(),
                "end_time": shift.end_datetime.isoformat(),
                "shift_type": shift.template.shift_type,
                "status": shift.status,
                "is_upcoming": True,
            }
            for shift in upcoming_shifts
        ]

        # Get incoming swap requests
        incoming_swap_requests = SwapRequest.objects.filter(
            target_employee=user, status=SwapRequest.Status.PENDING,
        ).select_related("requesting_employee", "requesting_shift", "target_shift")

        incoming_swaps_data = []
        for swap in incoming_swap_requests:
            # Handle case where target_shift might be None
            if swap.target_shift and swap.target_shift.template:
                target_shift_data = {
                    "id": swap.target_shift.id,
                    "title": f"{swap.target_shift.template.name} - {swap.target_shift.template.shift_type}",
                    "start_time": swap.target_shift.start_datetime.isoformat(),
                    "end_time": swap.target_shift.end_datetime.isoformat(),
                    "shift_type": swap.target_shift.template.shift_type,
                    "status": swap.target_shift.status,
                    "is_upcoming": swap.target_shift.start_datetime >= timezone.now(),
                }
            else:
                target_shift_data = None

            incoming_swaps_data.append(
                {
                    "id": swap.id,
                    "requester": {
                        "id": swap.requesting_employee.id,
                        "username": swap.requesting_employee.username,
                        "first_name": swap.requesting_employee.first_name,
                        "last_name": swap.requesting_employee.last_name,
                    },
                    "target_shift": target_shift_data,
                    "offered_shift": {
                        "id": swap.requesting_shift.id,
                        "title": f"{swap.requesting_shift.template.name} - {swap.requesting_shift.template.shift_type}",
                        "start_time": swap.requesting_shift.start_datetime.isoformat(),
                        "end_time": swap.requesting_shift.end_datetime.isoformat(),
                        "shift_type": swap.requesting_shift.template.shift_type,
                        "status": swap.requesting_shift.status,
                        "is_upcoming": swap.requesting_shift.start_datetime
                        >= timezone.now(),
                    },
                    "status": swap.status,
                    "created_at": swap.created.isoformat(),
                    "message": swap.message if hasattr(swap, "message") else None,
                },
            )

        # Get outgoing swap requests
        outgoing_swap_requests = SwapRequest.objects.filter(
            requesting_employee=user, status=SwapRequest.Status.PENDING,
        ).select_related("target_employee", "requesting_shift", "target_shift")

        outgoing_swaps_data = [
            {
                "id": swap.id,
                "target_employee": {
                    "id": swap.target_employee.id,
                    "username": swap.target_employee.username,
                    "first_name": swap.target_employee.first_name,
                    "last_name": swap.target_employee.last_name,
                },
                "requested_shift": {
                    "id": swap.target_shift.id,
                    "title": f"{swap.target_shift.template.name} - {swap.target_shift.template.shift_type}",
                    "start_time": swap.target_shift.start_datetime.isoformat(),
                    "end_time": swap.target_shift.end_datetime.isoformat(),
                    "shift_type": swap.target_shift.template.shift_type,
                    "status": swap.target_shift.status,
                    "is_upcoming": swap.target_shift.start_datetime >= timezone.now(),
                },
                "offered_shift": {
                    "id": swap.requesting_shift.id,
                    "title": f"{swap.requesting_shift.template.name} - {swap.requesting_shift.template.shift_type}",
                    "start_time": swap.requesting_shift.start_datetime.isoformat(),
                    "end_time": swap.requesting_shift.end_datetime.isoformat(),
                    "shift_type": swap.requesting_shift.template.shift_type,
                    "status": swap.requesting_shift.status,
                    "is_upcoming": swap.requesting_shift.start_datetime
                    >= timezone.now(),
                },
                "status": swap.status,
                "created_at": swap.created.isoformat(),
                "message": swap.message if hasattr(swap, "message") else None,
            }
            for swap in outgoing_swap_requests
        ]

        # Get recent activities (simplified for now)
        recent_activities = []

        # Add recent shifts
        recent_shifts = Shift.objects.filter(
            assigned_employee=user, modified__gte=timezone.now() - timedelta(days=7),
        ).order_by("-modified")[:3]

        for shift in recent_shifts:
            recent_activities.append(
                {
                    "id": f"shift_{shift.id}",
                    "type": "shift",
                    "message": f"Shift {shift.template.name} on {shift.start_datetime.date()}",
                    "status": "info",
                    "created_at": shift.modified.isoformat(),
                    "related_object_id": shift.id,
                },
            )

        # Add recent swap requests
        recent_swaps = SwapRequest.objects.filter(requesting_employee=user).order_by(
            "-created",
        )[:2]

        for swap in recent_swaps:
            # Handle case where target_shift might be None
            if swap.target_shift:
                shift_name = swap.target_shift.template.name
            else:
                shift_name = "Unknown shift"

            recent_activities.append(
                {
                    "id": f"swap_{swap.id}",
                    "type": "swap_request",
                    "message": f"Swap request {swap.status} for {shift_name}",
                    "status": swap.status,
                    "created_at": swap.created.isoformat(),
                    "related_object_id": swap.id,
                },
            )

        # Sort activities by date
        recent_activities.sort(key=lambda x: x["created_at"], reverse=True)
        recent_activities = recent_activities[:5]

        # Calculate stats for this month
        start_of_month = today.replace(day=1)
        next_month = (start_of_month.replace(day=28) + timedelta(days=4)).replace(day=1)

        total_shifts_this_month = Shift.objects.filter(
            assigned_employee=user,
            start_datetime__gte=start_of_month,
            start_datetime__lt=next_month,
        ).count()

        completed_shifts = Shift.objects.filter(
            assigned_employee=user,
            start_datetime__gte=start_of_month,
            start_datetime__lt=next_month,
            status=Shift.Status.COMPLETED,
        ).count()

        upcoming_shifts_count = Shift.objects.filter(
            assigned_employee=user,
            start_datetime__gte=timezone.now(),
            start_datetime__lt=next_month,
        ).count()

        swap_requests_pending = SwapRequest.objects.filter(
            requesting_employee=user, status=SwapRequest.Status.PENDING,
        ).count()

        dashboard_data = {
            "upcoming_shifts": upcoming_shifts_data,
            "incoming_swap_requests": incoming_swaps_data,
            "outgoing_swap_requests": outgoing_swaps_data,
            "recent_activities": recent_activities,
            "shift_stats": {
                "total_shifts_this_month": total_shifts_this_month,
                "completed_shifts": completed_shifts,
                "upcoming_shifts": upcoming_shifts_count,
                "swap_requests_pending": swap_requests_pending,
            },
        }

        return Response(dashboard_data)
