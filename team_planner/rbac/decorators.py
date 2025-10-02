"""
Permission decorators for enforcing RBAC on API endpoints.

This module provides decorators that can be applied to ViewSet methods
to enforce permission checks before allowing access to API operations.
"""

from functools import wraps
from rest_framework.response import Response
from rest_framework import status
from team_planner.users.models import RolePermission


def check_user_permission(user, permission_name):
    """
    Check if a user has a specific permission based on their role.
    
    Args:
        user: User instance
        permission_name (str): Name of the permission to check
        
    Returns:
        bool: True if user has permission, False otherwise
    """
    # Superusers have all permissions
    if user.is_superuser:
        return True
    
    # Get user's role
    if not hasattr(user, 'role'):
        return False
    
    # Get role permissions
    try:
        role_permissions = RolePermission.objects.get(role=user.role)
        return getattr(role_permissions, permission_name, False)
    except RolePermission.DoesNotExist:
        return False


def require_permission(permission_name):
    """
    Decorator to require a specific permission for a view.
    
    Usage:
        @require_permission('can_view_schedule')
        def list(self, request, *args, **kwargs):
            return super().list(request, *args, **kwargs)
    
    Args:
        permission_name (str): The name of the required permission
        
    Returns:
        Function wrapper that checks permissions before executing the view
        
    Raises:
        401 Unauthorized: If user is not authenticated
        403 Forbidden: If user lacks the required permission
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(self, request, *args, **kwargs):
            # Check authentication
            if not request.user.is_authenticated:
                return Response(
                    {
                        'error': 'Authentication required',
                        'detail': 'You must be logged in to access this resource.'
                    },
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            # Check permission
            if not check_user_permission(request.user, permission_name):
                return Response(
                    {
                        'error': 'Permission denied',
                        'detail': f'You do not have the required permission: {permission_name}',
                        'required_permission': permission_name
                    },
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Permission granted, execute the view
            return view_func(self, request, *args, **kwargs)
        return wrapper
    return decorator


def require_any_permission(*permission_names):
    """
    Decorator to require any one of multiple permissions.
    
    Useful for endpoints that can be accessed by users with different permissions.
    
    Usage:
        @require_any_permission('can_approve_leave', 'can_manage_users')
        def approve(self, request, pk=None):
            # Approval logic
    
    Args:
        *permission_names: Variable number of permission name strings
        
    Returns:
        Function wrapper that checks if user has at least one of the permissions
        
    Raises:
        401 Unauthorized: If user is not authenticated
        403 Forbidden: If user lacks all specified permissions
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(self, request, *args, **kwargs):
            # Check authentication
            if not request.user.is_authenticated:
                return Response(
                    {
                        'error': 'Authentication required',
                        'detail': 'You must be logged in to access this resource.'
                    },
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            # Check if user has any of the required permissions
            has_permission = any(
                check_user_permission(request.user, perm)
                for perm in permission_names
            )
            
            if not has_permission:
                return Response(
                    {
                        'error': 'Permission denied',
                        'detail': f'You need one of these permissions: {", ".join(permission_names)}',
                        'required_permissions': list(permission_names)
                    },
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Permission granted, execute the view
            return view_func(self, request, *args, **kwargs)
        return wrapper
    return decorator


def require_all_permissions(*permission_names):
    """
    Decorator to require all of multiple permissions.
    
    Useful for highly privileged operations that require multiple permissions.
    
    Usage:
        @require_all_permissions('can_manage_users', 'can_assign_roles')
        def assign_admin_role(self, request, pk=None):
            # Role assignment logic
    
    Args:
        *permission_names: Variable number of permission name strings
        
    Returns:
        Function wrapper that checks if user has all specified permissions
        
    Raises:
        401 Unauthorized: If user is not authenticated
        403 Forbidden: If user lacks any of the specified permissions
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(self, request, *args, **kwargs):
            # Check authentication
            if not request.user.is_authenticated:
                return Response(
                    {
                        'error': 'Authentication required',
                        'detail': 'You must be logged in to access this resource.'
                    },
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            # Check if user has all required permissions
            missing_permissions = [
                perm for perm in permission_names
                if not check_user_permission(request.user, perm)
            ]
            
            if missing_permissions:
                return Response(
                    {
                        'error': 'Permission denied',
                        'detail': f'You are missing these permissions: {", ".join(missing_permissions)}',
                        'required_permissions': list(permission_names),
                        'missing_permissions': missing_permissions
                    },
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # All permissions granted, execute the view
            return view_func(self, request, *args, **kwargs)
        return wrapper
    return decorator


def permission_required_method(permission_map):
    """
    Class decorator to apply permissions based on HTTP method.
    
    Usage:
        @permission_required_method({
            'GET': 'can_view_schedule',
            'POST': 'can_create_shift',
            'PUT': 'can_edit_shift',
            'DELETE': 'can_delete_shift'
        })
        class ShiftViewSet(viewsets.ModelViewSet):
            ...
    
    Args:
        permission_map (dict): Mapping of HTTP methods to required permissions
        
    Returns:
        Class wrapper that applies appropriate permission checks
    """
    def decorator(cls):
        original_dispatch = cls.dispatch if hasattr(cls, 'dispatch') else None
        
        def dispatch_with_permission(self, request, *args, **kwargs):
            method = request.method.upper()
            required_permission = permission_map.get(method)
            
            if required_permission:
                if not request.user.is_authenticated:
                    return Response(
                        {
                            'error': 'Authentication required',
                            'detail': 'You must be logged in to access this resource.'
                        },
                        status=status.HTTP_401_UNAUTHORIZED
                    )
                
                if not check_user_permission(request.user, required_permission):
                    return Response(
                        {
                            'error': 'Permission denied',
                            'detail': f'You do not have the required permission: {required_permission}',
                            'required_permission': required_permission
                        },
                        status=status.HTTP_403_FORBIDDEN
                    )
            
            if original_dispatch:
                return original_dispatch(self, request, *args, **kwargs)
            return super(cls, self).dispatch(request, *args, **kwargs)
        
        cls.dispatch = dispatch_with_permission
        return cls
    return decorator
