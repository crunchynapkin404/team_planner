from rest_framework import serializers

from team_planner.users.models import User


class TeamSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    role = serializers.CharField()


class EmployeeProfileSerializer(serializers.Serializer):
    """Serializer for employee profile data."""
    id = serializers.IntegerField()
    employee_id = serializers.CharField()
    phone_number = serializers.CharField()
    emergency_contact_name = serializers.CharField()
    emergency_contact_phone = serializers.CharField()
    employment_type = serializers.CharField()
    status = serializers.CharField()
    hire_date = serializers.DateField()
    termination_date = serializers.DateField(allow_null=True)
    salary = serializers.DecimalField(max_digits=10, decimal_places=2, allow_null=True)
    available_for_incidents = serializers.BooleanField()
    available_for_waakdienst = serializers.BooleanField()
    skills = serializers.SerializerMethodField()
    manager = serializers.SerializerMethodField()
    
    def get_skills(self, obj):
        """Get employee skills."""
        return [
            {
                'id': skill.id,
                'name': skill.name,
                'description': skill.description,
            }
            for skill in obj.skills.all()
        ]
    
    def get_manager(self, obj):
        """Get manager information."""
        if obj.manager:
            return {
                'id': obj.manager.id,
                'username': obj.manager.username,
                'first_name': obj.manager.first_name,
                'last_name': obj.manager.last_name,
                'email': obj.manager.email,
            }
        return None


class UserSerializer(serializers.ModelSerializer[User]):
    teams = serializers.SerializerMethodField()
    permissions = serializers.SerializerMethodField()
    employee_profile = serializers.SerializerMethodField()
    first_name = serializers.SerializerMethodField()
    last_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "username", 
            "email",
            "first_name",
            "last_name", 
            "name",
            "is_active",
            "is_staff",
            "is_superuser",
            "date_joined",
            "last_login",
            "teams",
            "permissions",
            "employee_profile",
        ]

    def get_first_name(self, obj):
        """Get first name from the name field."""
        return obj.first_name_display

    def get_last_name(self, obj):
        """Get last name from the name field."""
        return obj.last_name_display

    def get_teams(self, obj):
        """Get user's teams with roles."""
        try:
            from team_planner.teams.models import TeamMembership
            memberships = TeamMembership.objects.filter(user=obj, is_active=True).select_related('team')
            return [
                {
                    'id': membership.team.id,
                    'name': membership.team.name,
                    'role': membership.role,
                }
                for membership in memberships
            ]
        except Exception:
            return []

    def get_permissions(self, obj):
        """Get user's permissions."""
        try:
            # Get all permissions for the user
            permissions = obj.get_all_permissions()
            return list(permissions)
        except Exception:
            return []
    
    def get_employee_profile(self, obj):
        """Get employee profile data."""
        try:
            profile = obj.employee_profile
            return EmployeeProfileSerializer(profile).data
        except Exception:
            return None
