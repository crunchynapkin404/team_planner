from datetime import date
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from team_planner.employees.models import EmployeeProfile
from team_planner.employees.models import EmployeeSkill
from team_planner.orchestrators.utils.time_windows import get_waakdienst_week_bounds
from team_planner.orchestrators.waakdienst import WaakdienstOrchestrator
from team_planner.shifts.models import ShiftTemplate
from team_planner.shifts.models import ShiftType
from team_planner.users.models import User


@pytest.mark.django_db
def test_waakdienst_week_is_assigned_to_single_engineer():
    tz = ZoneInfo("Europe/Amsterdam")

    # Create waakdienst skill and three employees with active profiles
    skill = EmployeeSkill.objects.create(name="waakdienst", is_active=True)

    users: list[User] = []
    for i in range(3):
        u = User.objects.create_user(username=f"waak{i}", password="pass")
        EmployeeProfile.objects.create(
            user=u,
            employee_id=f"E{i:03d}",
            hire_date=date(2020, 1, 1),
            status=EmployeeProfile.Status.ACTIVE,
        )
        # attach skill
        u.employee_profile.skills.add(skill)
        users.append(u)

    # Create an active waakdienst shift template
    ShiftTemplate.objects.create(
        name="Waakdienst Default",
        shift_type=ShiftType.WAAKDIENST,
        duration_hours=15,
        is_active=True,
    )

    # Choose a reference date and get exact week bounds
    ref = datetime(2025, 9, 10, 12, 0, tzinfo=tz)  # Wednesday noon
    start, end = get_waakdienst_week_bounds(ref)

    orch = WaakdienstOrchestrator()
    result = orch.generate_assignments(start, end, dry_run=True)

    assert result["errors"] == []
    assignments = result["assignments"]

    # Exactly 7 daily blocks in the waakdienst week
    assert len(assignments) == 7

    # All assignments go to the same employee for continuity
    emp_ids = {a["assigned_employee_id"] for a in assignments}
    assert len(emp_ids) == 1

    # First start and last end align with the week bounds
    assert assignments[0]["start_datetime"] == start
    assert assignments[-1]["end_datetime"] == end

    # Durations should follow pattern (Wed..Tue): 15,15,15,24,24,15,15
    durations = [
        int((a["end_datetime"] - a["start_datetime"]).total_seconds() // 3600)
        for a in assignments
    ]
    assert durations == [15, 15, 15, 24, 24, 15, 15]
