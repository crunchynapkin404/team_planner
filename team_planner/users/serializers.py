"""Serializers for user management and RBAC."""
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import RolePermission, UserRole

User = get_user_model()


class RolePermissionSerializer(serializers.ModelSerializer):
    """Serializer for role permissions."""
    
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    
    class Meta:
        model = RolePermission
        fields = [
            'id', 'role', 'role_display',
            # Shift permissions
            'can_view_own_shifts', 'can_view_team_shifts', 'can_view_all_shifts',
            'can_create_shifts', 'can_edit_own_shifts', 'can_edit_team_shifts', 'can_delete_shifts',
            # Swap permissions
            'can_request_swap', 'can_approve_swap', 'can_view_all_swaps',
            # Leave permissions
            'can_request_leave', 'can_approve_leave', 'can_view_team_leave',
            # Orchestration permissions
            'can_run_orchestrator', 'can_override_fairness', 'can_manual_assign',
            # Team permissions
            'can_manage_team', 'can_view_team_analytics',
            # Reporting permissions
            'can_view_reports', 'can_export_data',
            # User management
            'can_manage_users', 'can_assign_roles',
        ]
        read_only_fields = ['id', 'role', 'role_display']


class UserRoleSerializer(serializers.ModelSerializer):
    """Serializer for user with role information."""
    
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    permissions = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'name', 'role', 'role_display', 'permissions', 'is_active', 'date_joined']
        read_only_fields = ['id', 'username', 'email', 'date_joined']
    
    def get_permissions(self, obj):
        """Get user permissions based on role."""
        if obj.is_superuser:
            # Superuser has all permissions
            return {
                field.name: True
                for field in RolePermission._meta.fields
                if field.name.startswith('can_')
            }
        
        try:
            role_perms = RolePermission.objects.get(role=obj.role)
            return {
                field.name: getattr(role_perms, field.name)
                for field in RolePermission._meta.fields
                if field.name.startswith('can_')
            }
        except RolePermission.DoesNotExist:
            return {}


class PermissionSummarySerializer(serializers.Serializer):
    """Quick permission summary for current user."""
    
    role = serializers.CharField()
    role_display = serializers.CharField()
    is_superuser = serializers.BooleanField()
    permissions = serializers.DictField()


class RoleChoiceSerializer(serializers.Serializer):
    """Serializer for role choices."""
    
    value = serializers.CharField()
    label = serializers.CharField()
    
    @staticmethod
    def get_all_roles():
        """Get all available roles."""
        return [
            {'value': choice[0], 'label': choice[1]}
            for choice in UserRole.choices
        ]


class UpdateUserRoleSerializer(serializers.Serializer):
    """Serializer for updating user role."""
    
    role = serializers.ChoiceField(choices=UserRole.choices)
    
    def validate_role(self, value):
        """Validate that role exists in RolePermission."""
        if not RolePermission.objects.filter(role=value).exists():
            raise serializers.ValidationError(
                f"Role '{value}' does not have defined permissions. Please contact administrator."
            )
        return value
