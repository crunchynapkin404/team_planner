"""API views for Role-Based Access Control (RBAC)."""
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model
from ..models import RolePermission, UserRole
from ..permissions import IsManager, check_user_permission, get_user_permissions
from ..serializers import (
    UserRoleSerializer,
    RolePermissionSerializer,
    PermissionSummarySerializer,
    RoleChoiceSerializer,
    UpdateUserRoleSerializer,
)

User = get_user_model()


class RolePermissionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing role permissions.
    Read-only - permissions are managed through admin/migrations.
    """
    queryset = RolePermission.objects.all()
    serializer_class = RolePermissionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter by role if specified."""
        queryset = super().get_queryset()
        role = self.request.query_params.get('role')
        if role:
            queryset = queryset.filter(role=role)
        return queryset


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_my_permissions(request):
    """Get current user's permissions."""
    user = request.user
    
    permissions = get_user_permissions(user)
    
    serializer = PermissionSummarySerializer({
        'role': user.role,
        'role_display': user.get_role_display(),
        'is_superuser': user.is_superuser,
        'permissions': permissions,
    })
    
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_available_roles(request):
    """Get all available roles."""
    roles = RoleChoiceSerializer.get_all_roles()
    return Response(roles)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_role_permissions(request, role):
    """Get permissions for a specific role."""
    try:
        role_perms = RolePermission.objects.get(role=role)
        serializer = RolePermissionSerializer(role_perms)
        return Response(serializer.data)
    except RolePermission.DoesNotExist:
        return Response(
            {'error': f'Role "{role}" not found'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_user_role(request, user_id):
    """
    Update a user's role.
    Requires 'can_assign_roles' permission.
    """
    # Check permission
    if not request.user.is_superuser and not check_user_permission(request.user, 'can_assign_roles'):
        return Response(
            {'error': 'You do not have permission to assign roles'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Get user
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response(
            {'error': 'User not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Validate and update role
    serializer = UpdateUserRoleSerializer(data=request.data)
    if serializer.is_valid():
        new_role = serializer.validated_data['role']
        
        # Prevent non-superusers from assigning admin role
        if new_role == UserRole.ADMIN and not request.user.is_superuser:
            return Response(
                {'error': 'Only superusers can assign admin role'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Prevent users from changing their own role
        if user.id == request.user.id:
            return Response(
                {'error': 'You cannot change your own role'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        user.role = new_role
        user.save()
        
        response_serializer = UserRoleSerializer(user)
        return Response({
            'success': True,
            'message': f'User role updated to {user.get_role_display()}',
            'user': response_serializer.data
        })
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_users_with_roles(request):
    """
    List all users with their roles.
    Requires 'can_manage_users' or 'can_view_team_analytics' permission.
    """
    if not request.user.is_superuser:
        if not (check_user_permission(request.user, 'can_manage_users') or 
                check_user_permission(request.user, 'can_view_team_analytics')):
            return Response(
                {'error': 'You do not have permission to view users'},
                status=status.HTTP_403_FORBIDDEN
            )
    
    # Filter by role if specified
    queryset = User.objects.all().order_by('username')
    role = request.query_params.get('role')
    if role:
        queryset = queryset.filter(role=role)
    
    # Filter by active status
    is_active = request.query_params.get('is_active')
    if is_active is not None:
        queryset = queryset.filter(is_active=is_active.lower() == 'true')
    
    serializer = UserRoleSerializer(queryset, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def check_permission(request):
    """
    Check if current user has a specific permission.
    Useful for frontend permission checks.
    """
    permission_name = request.data.get('permission')
    
    if not permission_name:
        return Response(
            {'error': 'Permission name is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    has_permission = check_user_permission(request.user, permission_name)
    
    return Response({
        'permission': permission_name,
        'has_permission': has_permission,
        'user_role': request.user.role,
        'is_superuser': request.user.is_superuser,
    })
