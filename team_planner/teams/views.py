from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Department
from .models import Team
from .models import TeamMembership

User = get_user_model()


@api_view(["GET"])
def teams_list_api(request):
    """API endpoint to list all teams."""
    if not request.user.is_authenticated:
        return Response(
            {"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED,
        )

    teams = []
    for team in Team.objects.select_related("department", "manager").all():
        team_data = {
            "id": team.id,
            "name": team.name,
            "description": team.description,
            "department": team.department.name if team.department else "",
            "manager": {
                "id": team.manager.id,
                "name": team.manager.get_full_name(),
                "username": team.manager.username,
                "email": team.manager.email,
            }
            if team.manager
            else None,
            "members": [],
            "created": team.created.isoformat(),
        }

        # Add team members through the TeamMembership model
        memberships = TeamMembership.objects.filter(team=team).select_related("user")
        for membership in memberships:
            member_data = {
                "id": membership.id,
                "user": {
                    "id": membership.user.id,
                    "username": membership.user.username,
                    "email": membership.user.email,
                    "name": membership.user.get_full_name(),
                    "is_active": membership.user.is_active,
                },
                "role": membership.role,
                "joined_date": membership.joined_date.isoformat(),
                "is_active": membership.is_active,
            }
            team_data["members"].append(member_data)

        teams.append(team_data)

    return Response(teams)


@api_view(["GET"])
def departments_list_api(request):
    """API endpoint to list all departments."""
    if not request.user.is_authenticated:
        return Response(
            {"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED,
        )

    departments = []
    for dept in Department.objects.select_related("manager").all():
        dept_data = {
            "id": dept.id,
            "name": dept.name,
            "description": dept.description,
            "manager": {
                "id": dept.manager.id,
                "name": dept.manager.get_full_name(),
                "username": dept.manager.username,
                "email": dept.manager.email,
            }
            if dept.manager
            else None,
        }
        departments.append(dept_data)

    return Response(departments)
