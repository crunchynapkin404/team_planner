from django.core.management.base import BaseCommand

from team_planner.employees.models import EmployeeProfile
from team_planner.employees.models import EmployeeSkill
from team_planner.users.api.serializers import UserSerializer
from team_planner.users.models import User


class Command(BaseCommand):
    help = "Test user creation with skills assignment"

    def add_arguments(self, parser):
        parser.add_argument(
            "--username",
            type=str,
            default="test_skills_user",
            help="Username for the test user",
        )
        parser.add_argument(
            "--incidents",
            action="store_true",
            help="Make user available for incidents",
        )
        parser.add_argument(
            "--waakdienst",
            action="store_true",
            help="Make user available for waakdienst",
        )
        parser.add_argument(
            "--cleanup",
            action="store_true",
            help="Delete the test user after creation (for testing)",
        )

    def handle(self, *args, **options):
        username = options["username"]
        available_for_incidents = options["incidents"]
        available_for_waakdienst = options["waakdienst"]
        cleanup = options["cleanup"]

        self.stdout.write(self.style.SUCCESS("Testing user creation with skills:"))
        self.stdout.write(f"  Username: {username}")
        self.stdout.write(f"  Available for incidents: {available_for_incidents}")
        self.stdout.write(f"  Available for waakdienst: {available_for_waakdienst}")

        # Clean up existing user if it exists
        User.objects.filter(username=username).delete()

        # Test data for creating a new user
        test_data = {
            "username": username,
            "email": f"{username}@example.com",
            "first_name": "Test",
            "last_name": "User",
            "available_for_incidents": available_for_incidents,
            "available_for_waakdienst": available_for_waakdienst,
            "employment_type": "full_time",
            "password": "testpass123",
        }

        try:
            # Create user using serializer
            serializer = UserSerializer(data=test_data)
            if serializer.is_valid():
                user = serializer.save()
                self.stdout.write(
                    self.style.SUCCESS(f"✓ User created successfully: {user.username}"),
                )

                # Check if profile was created
                try:
                    profile = user.employee_profile
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"✓ Employee profile created: {profile.employee_id}",
                        ),
                    )
                    self.stdout.write(
                        f"  - available_for_incidents: {profile.available_for_incidents}",
                    )
                    self.stdout.write(
                        f"  - available_for_waakdienst: {profile.available_for_waakdienst}",
                    )

                    # Check skills
                    skills = profile.skills.all()
                    self.stdout.write(f"  - Skills count: {skills.count()}")
                    for skill in skills:
                        self.stdout.write(
                            f"    * {skill.name} (active: {skill.is_active})",
                        )

                    # Test orchestrator queries
                    self.stdout.write("\n=== Testing orchestrator queries ===")

                    # Test incidents availability
                    incidents_users = User.objects.filter(
                        is_active=True,
                        employee_profile__status=EmployeeProfile.Status.ACTIVE,
                        employee_profile__available_for_incidents=True,
                    ).count()
                    self.stdout.write(
                        f"Users available for incidents: {incidents_users}",
                    )

                    # Test waakdienst availability by skill
                    waakdienst_users_by_skill = (
                        User.objects.filter(
                            is_active=True,
                            employee_profile__skills__name="waakdienst",
                            employee_profile__skills__is_active=True,
                        )
                        .distinct()
                        .count()
                    )
                    self.stdout.write(
                        f"Users with waakdienst skill: {waakdienst_users_by_skill}",
                    )

                    # Check specific user in queries
                    user_in_incidents = User.objects.filter(
                        username=username,
                        is_active=True,
                        employee_profile__status=EmployeeProfile.Status.ACTIVE,
                        employee_profile__available_for_incidents=True,
                    ).exists()
                    self.stdout.write(
                        f"Test user found in incidents query: {user_in_incidents}",
                    )

                    user_in_waakdienst = User.objects.filter(
                        username=username,
                        is_active=True,
                        employee_profile__skills__name="waakdienst",
                        employee_profile__skills__is_active=True,
                    ).exists()
                    self.stdout.write(
                        f"Test user found in waakdienst query: {user_in_waakdienst}",
                    )

                    # Show all skills in database
                    self.stdout.write("\n=== All skills in database ===")
                    all_skills = EmployeeSkill.objects.all()
                    for skill in all_skills:
                        employee_count = skill.employees.count()
                        self.stdout.write(
                            f"  - {skill.name}: {employee_count} employees (active: {skill.is_active})",
                        )

                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f"✗ Error accessing employee profile: {e}"),
                    )

                if cleanup:
                    user.delete()
                    self.stdout.write(
                        self.style.WARNING("🗑 Test user deleted as requested"),
                    )

            else:
                self.stdout.write(
                    self.style.ERROR(
                        f"✗ Serializer validation failed: {serializer.errors}",
                    ),
                )

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"✗ Error creating user: {e}"))
            import traceback

            self.stdout.write(traceback.format_exc())
