from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Department
from .models import Team
from .models import TeamMembership
from .serializers import DepartmentSerializer
from .serializers import TeamMembershipSerializer
from .serializers import TeamSerializer

User = get_user_model()


class TeamViewSet(viewsets.ModelViewSet):
    """ViewSet for managing teams."""

    serializer_class = TeamSerializer
    queryset = Team.objects.select_related("department", "manager").prefetch_related(
        "teammembership_set__user",
    )
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        """Set permissions based on action."""
        if self.action in ["create", "update", "partial_update", "destroy"]:
            # Only staff/admin can create/modify teams
            permission_classes = [IsAuthenticated]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]

    def perform_create(self, serializer):
        """Override to add permission check for team creation."""
        if not (self.request.user.is_staff or self.request.user.is_superuser):
            from rest_framework.exceptions import PermissionDenied

            msg = "Only staff members can create teams."
            raise PermissionDenied(msg)

        # Debug logging
        import logging

        logger = logging.getLogger(__name__)
        logger.info(f"Creating team with data: {self.request.data}")
        logger.info(
            f"User: {self.request.user.username} (staff: {self.request.user.is_staff})",
        )

        serializer.save()

    def create(self, request, *args, **kwargs):
        """Override create to provide better error logging."""
        import logging

        logger = logging.getLogger(__name__)

        logger.info(f"Team create request from user: {request.user.username}")
        logger.info(f"Request data: {request.data}")

        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            logger.error(f"Team creation validation errors: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data, status=status.HTTP_201_CREATED, headers=headers,
        )

    def perform_update(self, serializer):
        """Override to add permission check for team updates."""
        if not (self.request.user.is_staff or self.request.user.is_superuser):
            from rest_framework.exceptions import PermissionDenied

            msg = "Only staff members can modify teams."
            raise PermissionDenied(msg)
        serializer.save()

    def perform_destroy(self, instance):
        """Override to add permission check for team deletion."""
        if not (self.request.user.is_staff or self.request.user.is_superuser):
            from rest_framework.exceptions import PermissionDenied

            msg = "Only staff members can delete teams."
            raise PermissionDenied(msg)
        instance.delete()

    @action(detail=True, methods=["post"])
    def add_member(self, request, pk=None):
        """Add a member to the team."""
        if not (request.user.is_staff or request.user.is_superuser):
            return Response(
                {"error": "Only staff members can add team members."},
                status=status.HTTP_403_FORBIDDEN,
            )

        team = self.get_object()
        user_id = request.data.get("user_id")
        role = request.data.get("role", TeamMembership.Role.MEMBER)
        fte = request.data.get("fte", 1.00)

        if not user_id:
            return Response(
                {"error": "user_id is required."}, status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {"error": "User not found."}, status=status.HTTP_404_NOT_FOUND,
            )

        # Check if membership already exists
        if TeamMembership.objects.filter(team=team, user=user).exists():
            return Response(
                {"error": "User is already a member of this team."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Create membership
        membership = TeamMembership.objects.create(
            team=team, user=user, role=role, fte=fte,
        )

        serializer = TeamMembershipSerializer(membership)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["delete"])
    def remove_member(self, request, pk=None):
        """Remove a member from the team."""
        if not (request.user.is_staff or request.user.is_superuser):
            return Response(
                {"error": "Only staff members can remove team members."},
                status=status.HTTP_403_FORBIDDEN,
            )

        team = self.get_object()
        user_id = request.data.get("user_id")

        if not user_id:
            return Response(
                {"error": "user_id is required."}, status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            membership = TeamMembership.objects.get(team=team, user_id=user_id)
            membership.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except TeamMembership.DoesNotExist:
            return Response(
                {"error": "User is not a member of this team."},
                status=status.HTTP_404_NOT_FOUND,
            )


class DepartmentViewSet(viewsets.ModelViewSet):
    """ViewSet for managing departments."""

    serializer_class = DepartmentSerializer
    queryset = Department.objects.select_related("manager")
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        """Set permissions based on action."""
        if self.action in ["create", "update", "partial_update", "destroy"]:
            # Only staff/admin can create/modify departments
            permission_classes = [IsAuthenticated]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]

    def perform_create(self, serializer):
        """Override to add permission check for department creation."""
        if not (self.request.user.is_staff or self.request.user.is_superuser):
            from rest_framework.exceptions import PermissionDenied

            msg = "Only staff members can create departments."
            raise PermissionDenied(msg)
        serializer.save()

    def perform_update(self, serializer):
        """Override to add permission check for department updates."""
        if not (self.request.user.is_staff or self.request.user.is_superuser):
            from rest_framework.exceptions import PermissionDenied

            msg = "Only staff members can modify departments."
            raise PermissionDenied(msg)
        serializer.save()

    def perform_destroy(self, instance):
        """Override to add permission check for department deletion."""
        if not (self.request.user.is_staff or self.request.user.is_superuser):
            from rest_framework.exceptions import PermissionDenied

            msg = "Only staff members can delete departments."
            raise PermissionDenied(msg)
        instance.delete()
