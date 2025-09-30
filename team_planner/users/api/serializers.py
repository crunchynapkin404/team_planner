from django.db import transaction
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
                "id": skill.id,
                "name": skill.name,
                "description": skill.description,
            }
            for skill in obj.skills.all()
        ]

    def get_manager(self, obj):
        """Get manager information."""
        if obj.manager:
            return {
                "id": obj.manager.id,
                "username": obj.manager.username,
                "first_name": obj.manager.first_name,
                "last_name": obj.manager.last_name,
                "email": obj.manager.email,
            }
        return None


class UserSerializer(serializers.ModelSerializer[User]):
    teams = serializers.SerializerMethodField()
    permissions = serializers.SerializerMethodField()
    employee_profile = serializers.SerializerMethodField()
    first_name = serializers.SerializerMethodField()
    last_name = serializers.SerializerMethodField()

    # For write operations
    password = serializers.CharField(write_only=True, required=False)

    # Employee profile fields for create/update operations
    available_for_incidents = serializers.BooleanField(
        write_only=True, required=False, default=False,
    )
    available_for_waakdienst = serializers.BooleanField(
        write_only=True, required=False, default=False,
    )
    employment_type = serializers.CharField(
        write_only=True, required=False, default="full_time",
    )

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
            "password",
            "available_for_incidents",
            "available_for_waakdienst",
            "employment_type",
        ]
        extra_kwargs = {
            "password": {"write_only": True},
        }

    def to_internal_value(self, data):
        """Convert first_name and last_name to name field."""
        # Make a mutable copy of the data
        mutable_data = data.copy() if hasattr(data, "copy") else dict(data)

        # If first_name and/or last_name are provided, combine them into name
        first_name = mutable_data.get("first_name", "")
        last_name = mutable_data.get("last_name", "")

        if first_name or last_name:
            mutable_data["name"] = f"{first_name} {last_name}".strip()

        # Remove the individual name fields from the data to avoid validation issues
        mutable_data.pop("first_name", None)
        mutable_data.pop("last_name", None)

        return super().to_internal_value(mutable_data)

    def create(self, validated_data):
        """Create a new user with password and employee profile."""
        import logging

        logger = logging.getLogger(__name__)

        # Extract employee profile fields
        available_for_incidents = validated_data.pop("available_for_incidents", False)
        available_for_waakdienst = validated_data.pop("available_for_waakdienst", False)
        employment_type = validated_data.pop("employment_type", "full_time")

        logger.info(
            f"Creating user with availability - incidents: {available_for_incidents}, waakdienst: {available_for_waakdienst}",
        )

        password = validated_data.pop("password", None)
        user = User(**validated_data)

        if password:
            user.set_password(password)
        else:
            # Generate a random password if none provided
            import secrets
            import string

            random_password = "".join(
                secrets.choice(string.ascii_letters + string.digits) for _ in range(12)
            )
            user.set_password(random_password)

        # Use a transaction to ensure user and profile are created together
        try:
            with transaction.atomic():
                user.save()
                logger.info(f"Created user: {user.username} (ID: {user.pk})")

                # Create employee profile
                self._create_or_update_employee_profile(
                    user,
                    employment_type=employment_type,
                    available_for_incidents=available_for_incidents,
                    available_for_waakdienst=available_for_waakdienst,
                )
                logger.info(
                    f"Successfully created user {user.username} with employee profile and skills",
                )
        except Exception as e:
            logger.exception(f"Error creating user {user.username}: {e}")
            raise

        return user

    def update(self, instance, validated_data):
        """Update user, handling password and employee profile separately."""
        # Extract employee profile fields
        available_for_incidents = validated_data.pop("available_for_incidents", None)
        available_for_waakdienst = validated_data.pop("available_for_waakdienst", None)
        employment_type = validated_data.pop("employment_type", None)

        password = validated_data.pop("password", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if password:
            instance.set_password(password)

        # Use transaction for user and profile updates
        with transaction.atomic():
            instance.save()

            # Update employee profile if any profile fields were provided
            if any(
                x is not None
                for x in [
                    available_for_incidents,
                    available_for_waakdienst,
                    employment_type,
                ]
            ):
                self._create_or_update_employee_profile(
                    instance,
                    employment_type=employment_type,
                    available_for_incidents=available_for_incidents,
                    available_for_waakdienst=available_for_waakdienst,
                )

        return instance

    def _create_or_update_employee_profile(
        self,
        user,
        employment_type=None,
        available_for_incidents=None,
        available_for_waakdienst=None,
    ):
        """Create or update employee profile and assign skills based on availability."""
        import logging
        from datetime import date

        from team_planner.employees.models import EmployeeProfile

        logger = logging.getLogger(__name__)

        # Create or get employee profile
        profile, created = EmployeeProfile.objects.get_or_create(
            user=user,
            defaults={
                "employee_id": f"EMP{user.pk:03d}",
                "hire_date": date.today(),
                "employment_type": employment_type
                or EmployeeProfile.EmploymentType.FULL_TIME,
                "available_for_incidents": available_for_incidents
                if available_for_incidents is not None
                else False,
                "available_for_waakdienst": available_for_waakdienst
                if available_for_waakdienst is not None
                else False,
            },
        )

        if created:
            logger.info(
                f"Created employee profile for {user.username}: incidents={profile.available_for_incidents}, waakdienst={profile.available_for_waakdienst}",
            )
        else:
            logger.info(f"Found existing employee profile for {user.username}")

        # Update existing profile if not just created
        if not created:
            if employment_type is not None:
                profile.employment_type = employment_type
            if available_for_incidents is not None:
                profile.available_for_incidents = available_for_incidents
            if available_for_waakdienst is not None:
                profile.available_for_waakdienst = available_for_waakdienst
            profile.save()
            logger.info(
                f"Updated employee profile for {user.username}: incidents={profile.available_for_incidents}, waakdienst={profile.available_for_waakdienst}",
            )

        # Assign skills based on availability
        try:
            self._assign_skills_based_on_availability(
                profile, available_for_incidents, available_for_waakdienst,
            )
        except Exception as e:
            logger.exception(f"Error assigning skills to {user.username}: {e}")
            raise

    def _assign_skills_based_on_availability(
        self, profile, available_for_incidents=None, available_for_waakdienst=None,
    ):
        """Assign or remove skills based on availability flags."""
        import logging

        from team_planner.employees.models import EmployeeSkill

        logger = logging.getLogger(__name__)

        # Use the current availability if not specified
        if available_for_incidents is None:
            available_for_incidents = profile.available_for_incidents
        if available_for_waakdienst is None:
            available_for_waakdienst = profile.available_for_waakdienst

        logger.info(
            f"Assigning skills for user {profile.user.username}: incidents={available_for_incidents}, waakdienst={available_for_waakdienst}",
        )

        # Handle incidents skill
        try:
            incidents_skill = EmployeeSkill.objects.get(name="incidents")
            if available_for_incidents:
                profile.skills.add(incidents_skill)
                logger.info(f"Added incidents skill to {profile.user.username}")
            else:
                profile.skills.remove(incidents_skill)
                logger.info(f"Removed incidents skill from {profile.user.username}")
        except EmployeeSkill.DoesNotExist:
            # Skill doesn't exist, create it if user is available for incidents
            if available_for_incidents:
                try:
                    incidents_skill = EmployeeSkill.objects.create(
                        name="incidents",
                        description="Incidents - Monday to Friday 8:00-17:00",
                    )
                    profile.skills.add(incidents_skill)
                    logger.info(
                        f"Created and added incidents skill to {profile.user.username}",
                    )
                except Exception as e:
                    logger.exception(
                        f"Error creating/adding incidents skill for {profile.user.username}: {e}",
                    )
                    raise
        except Exception as e:
            logger.exception(
                f"Unexpected error handling incidents skill for {profile.user.username}: {e}",
            )
            raise

        # Handle waakdienst skill
        try:
            waakdienst_skill = EmployeeSkill.objects.get(name="waakdienst")
            if available_for_waakdienst:
                profile.skills.add(waakdienst_skill)
                logger.info(f"Added waakdienst skill to {profile.user.username}")
            else:
                profile.skills.remove(waakdienst_skill)
                logger.info(f"Removed waakdienst skill from {profile.user.username}")
        except EmployeeSkill.DoesNotExist:
            # Skill doesn't exist, create it if user is available for waakdienst
            if available_for_waakdienst:
                try:
                    waakdienst_skill = EmployeeSkill.objects.create(
                        name="waakdienst",
                        description="Waakdienst - On-call/standby shifts (evenings, nights, weekends)",
                    )
                    profile.skills.add(waakdienst_skill)
                    logger.info(
                        f"Created and added waakdienst skill to {profile.user.username}",
                    )
                except Exception as e:
                    logger.exception(
                        f"Error creating/adding waakdienst skill for {profile.user.username}: {e}",
                    )
                    raise
        except Exception as e:
            logger.exception(
                f"Unexpected error handling waakdienst skill for {profile.user.username}: {e}",
            )
            raise

        # Ensure ManyToMany changes are saved by refreshing the profile
        profile.refresh_from_db()

        # Verify skills were assigned correctly
        final_skills = list(profile.skills.values_list("name", flat=True))
        logger.info(f"Final skills for {profile.user.username}: {final_skills}")

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

            memberships = TeamMembership.objects.filter(
                user=obj, is_active=True,
            ).select_related("team")
            return [
                {
                    "id": membership.team.id,
                    "name": membership.team.name,
                    "role": membership.role,
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
