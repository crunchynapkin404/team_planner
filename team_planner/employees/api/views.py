from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from django.http import Http404

from team_planner.employees.models import RecurringLeavePattern
from .serializers import RecurringLeavePatternSerializer

User = get_user_model()


class RecurringLeavePatternViewSet(viewsets.ModelViewSet):
    """ViewSet for managing RecurringLeavePattern objects."""
    
    serializer_class = RecurringLeavePatternSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None  # Disable pagination for this endpoint
    
    def get_queryset(self):
        """Filter patterns to only show the user's own patterns."""
        user_id = self.kwargs.get('user_pk')
        if user_id:
            # Check if user is requesting their own patterns or is admin/manager
            if str(self.request.user.pk) == str(user_id) or self.request.user.is_staff:
                return RecurringLeavePattern.objects.filter(employee_id=user_id)
            else:
                return RecurringLeavePattern.objects.none()
        return RecurringLeavePattern.objects.filter(employee=self.request.user)
    
    def perform_create(self, serializer):
        """Set the employee to the specified user."""
        user_id = self.kwargs.get('user_pk')
        if user_id:
            user = get_object_or_404(User, id=user_id)
            # Check if user is creating for themselves or is admin/manager
            if str(self.request.user.pk) == str(user_id) or self.request.user.is_staff:
                serializer.save(employee=user)
            else:
                raise Http404("You don't have permission to create patterns for this user.")
        else:
            serializer.save(employee=self.request.user)
    
    def perform_update(self, serializer):
        """Ensure user can only update their own patterns."""
        pattern = self.get_object()
        if pattern.employee == self.request.user or self.request.user.is_staff:
            serializer.save()
        else:
            raise Http404("You don't have permission to modify this pattern.")
    
    def perform_destroy(self, instance):
        """Ensure user can only delete their own patterns."""
        if instance.employee == self.request.user or self.request.user.is_staff:
            instance.delete()
        else:
            raise Http404("You don't have permission to delete this pattern.")
