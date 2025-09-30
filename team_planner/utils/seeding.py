from __future__ import annotations

from dataclasses import dataclass

from django.db import transaction
from django.utils import timezone

from team_planner.employees.models import EmployeeProfile
from team_planner.employees.models import EmployeeSkill
from team_planner.teams.models import Department
from team_planner.teams.models import Team
from team_planner.teams.models import TeamMembership
from team_planner.users.models import User


@dataclass
class SeedSummary:
    department: str
    team: str
    team_id: int
    created: int
    updated: int
    count: int
    categories: dict[str, int]
    usernames: list[str]
    password: str
    admin_username: str | None = None


@transaction.atomic
def seed_demo_data(
    dept_name: str = "Operations",
    team_name: str = "A-Team",
    count: int = 12,
    prefix: str = "demo",
    password: str = "ComplexPassword123!",
    reset: bool = False,
    create_admin: bool = False,
    admin_username: str = "admin",
    admin_password: str = "AdminPassword123!",
) -> SeedSummary:
    count = max(1, int(count))
    prefix = prefix.strip()

    # Ensure skills exist
    incidents_skill, _ = EmployeeSkill.objects.get_or_create(
        name="incidents",
        defaults={"description": "Business hours incidents", "is_active": True},
    )
    waakdienst_skill, _ = EmployeeSkill.objects.get_or_create(
        name="waakdienst",
        defaults={"description": "On-call/waakdienst", "is_active": True},
    )

    # Department and team
    dept, _ = Department.objects.get_or_create(
        name=dept_name, defaults={"description": f"Dept {dept_name}"},
    )
    team, _ = Team.objects.get_or_create(name=team_name, department=dept)

    created = 0
    updated = 0
    categories = {"incidents_only": 0, "waakdienst_only": 0, "both": 0, "neither": 0}
    usernames: list[str] = []

    for i in range(count):
        username = f"{prefix}{i:02d}"
        name = f"{prefix.capitalize()} User {i:02d}"
        usernames.append(username)

        user, u_created = User.objects.get_or_create(
            username=username,
            defaults={
                "email": f"{username}@example.com",
                "is_active": True,
                "name": name,
            },
        )
        if u_created:
            user.set_password(password)
            user.save()

        # Create/Update profile
        profile, p_created = EmployeeProfile.objects.get_or_create(
            user=user,
            defaults={
                "employee_id": f"E{timezone.now().strftime('%y%m%d')}{i:02d}",
                "hire_date": timezone.now().date(),
                "status": EmployeeProfile.Status.ACTIVE,
            },
        )

        # Assign categories in a simple round-robin
        mod = i % 4
        available_for_incidents = mod in (0, 2)
        available_for_waakdienst = mod in (1, 2)

        if reset or p_created:
            profile.available_for_incidents = available_for_incidents
            profile.available_for_waakdienst = available_for_waakdienst
            profile.status = EmployeeProfile.Status.ACTIVE
            profile.save()
            # Reset skills to match category
            if reset:
                profile.skills.clear()
            if available_for_incidents:
                profile.skills.add(incidents_skill)
            if available_for_waakdienst:
                profile.skills.add(waakdienst_skill)

        # Team membership
        tm, tm_created = TeamMembership.objects.get_or_create(user=user, team=team)
        if tm_created:
            if i == 0:
                tm.role = TeamMembership.Role.LEAD
            elif i % 4 == 0:
                tm.role = TeamMembership.Role.SENIOR
            tm.save()

        if u_created or p_created or tm_created:
            created += 1
        else:
            updated += 1

        key = (
            "both"
            if (available_for_incidents and available_for_waakdienst)
            else "incidents_only"
            if available_for_incidents
            else "waakdienst_only"
            if available_for_waakdienst
            else "neither"
        )
        categories[key] += 1

    # Optional admin creation
    admin_user = None
    if create_admin:
        admin_user, created_admin = User.objects.get_or_create(
            username=admin_username,
            defaults={
                "email": f"{admin_username}@example.com",
                "is_staff": True,
                "is_superuser": True,
                "is_active": True,
            },
        )
        if created_admin:
            admin_user.set_password(admin_password)
            admin_user.save()
        else:
            admin_user.is_staff = True
            admin_user.is_superuser = True
            admin_user.is_active = True
            admin_user.set_password(admin_password)
            admin_user.save()

    return SeedSummary(
        department=dept.name,
        team=team.name,
        team_id=int(team.pk),
        created=created,
        updated=updated,
        count=count,
        categories=categories,
        usernames=usernames,
        password=password,
        admin_username=(admin_user.username if admin_user else None),
    )
