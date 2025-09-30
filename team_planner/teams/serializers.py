from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import Department
from .models import Team
from .models import TeamMembership

User = get_user_model()


class DepartmentSerializer(serializers.ModelSerializer):
    """Serializer for Department model."""

    manager_name = serializers.CharField(source="manager.get_full_name", read_only=True)

    class Meta:
        model = Department
        fields = [
            "id",
            "name",
            "description",
            "manager",
            "manager_name",
            "created",
            "modified",
        ]
        read_only_fields = ["id", "created", "modified"]


class TeamMembershipSerializer(serializers.ModelSerializer):
    """Serializer for TeamMembership model."""

    user_username = serializers.CharField(source="user.username", read_only=True)
    user_name = serializers.CharField(source="user.get_full_name", read_only=True)
    user_email = serializers.CharField(source="user.email", read_only=True)

    class Meta:
        model = TeamMembership
        fields = [
            "id",
            "user",
            "user_username",
            "user_name",
            "user_email",
            "role",
            "fte",
            "joined_date",
            "is_active",
            "created",
            "modified",
        ]
        read_only_fields = ["id", "joined_date", "created", "modified"]


class TeamSerializer(serializers.ModelSerializer):
    """Serializer for Team model."""

    department_name = serializers.CharField(source="department.name", read_only=True)
    manager_name = serializers.CharField(source="manager.get_full_name", read_only=True)
    members = TeamMembershipSerializer(
        source="teammembership_set", many=True, read_only=True,
    )
    member_count = serializers.SerializerMethodField()

    class Meta:
        model = Team
        fields = [
            "id",
            "name",
            "description",
            "department",
            "department_name",
            "manager",
            "manager_name",
            "timezone",
            "waakdienst_handover_weekday",
            "waakdienst_start_hour",
            "waakdienst_end_hour",
            "incidents_skip_holidays",
            "standby_mode",
            "fairness_window_weeks",
            "joiner_grace_weeks",
            "joiner_bootstrap_credit_hours",
            "members",
            "member_count",
            "created",
            "modified",
        ]
        read_only_fields = ["id", "created", "modified"]

    def get_member_count(self, obj):
        """Get the number of active members in the team."""
        return obj.teammembership_set.filter(is_active=True).count()

    def validate_name(self, value):
        """Validate that team name is unique within the department."""
        department = (
            self.instance.department
            if self.instance
            else self.initial_data.get("department")
        )
        if department:
            existing = Team.objects.filter(name=value, department=department)
            if self.instance:
                existing = existing.exclude(pk=self.instance.pk)
            if existing.exists():
                msg = "A team with this name already exists in this department."
                raise serializers.ValidationError(
                    msg,
                )
        return value
