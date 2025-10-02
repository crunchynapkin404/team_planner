"""Permission utilities for role-based access control."""
from rest_framework.permissions import BasePermission
from .models import RolePermission, UserRole


class HasRolePermission(BasePermission):
    """Check if user has a specific permission based on their role."""
    
    permission_name = None  # Set in subclass
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        if request.user.is_superuser:
            return True
        
        if self.permission_name:
            return check_user_permission(request.user, self.permission_name)
        
        return False


class IsManager(BasePermission):
    """User must be Manager or higher."""
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        if request.user.is_superuser:
            return True
        
        return request.user.role in [UserRole.MANAGER, UserRole.ADMIN]


class IsScheduler(BasePermission):
    """User must be Scheduler or higher."""
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        if request.user.is_superuser:
            return True
        
        return request.user.role in [UserRole.SCHEDULER, UserRole.MANAGER, UserRole.ADMIN]


class CanManageTeam(BasePermission):
    """User can manage the specific team."""
    
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        
        if request.user.is_superuser:
            return True
        
        # Check if user is team manager
        if hasattr(obj, 'manager') and obj.manager == request.user:
            return True
        
        # Check role permission
        return check_user_permission(request.user, 'can_manage_team')


def check_user_permission(user, permission_name):
    """
    Check if user has a specific permission based on role.
    
    Args:
        user: User instance
        permission_name: String name of permission (e.g., 'can_approve_swap')
    
    Returns:
        Boolean indicating if user has permission
    """
    if user.is_superuser:
        return True
    
    try:
        role_perms = RolePermission.objects.get(role=user.role)
        return getattr(role_perms, permission_name, False)
    except RolePermission.DoesNotExist:
        return False


def get_user_permissions(user):
    """Get all permissions for a user."""
    if user.is_superuser:
        # Superuser has all permissions
        return {
            field.name: True
            for field in RolePermission._meta.fields
            if field.name.startswith('can_')
        }
    
    try:
        role_perms = RolePermission.objects.get(role=user.role)
        return {
            field.name: getattr(role_perms, field.name)
            for field in RolePermission._meta.fields
            if field.name.startswith('can_')
        }
    except RolePermission.DoesNotExist:
        return {}


class RoleBasedViewMixin:
    """Mixin for views that require role-based permissions."""
    
    permission_required = None  # Set in subclass
    
    def check_permissions(self, request):
        super().check_permissions(request)
        
        if self.permission_required and not request.user.is_superuser:
            if not check_user_permission(request.user, self.permission_required):
                from rest_framework.exceptions import PermissionDenied
                raise PermissionDenied(
                    f"Your role does not have '{self.permission_required}' permission"
                )
