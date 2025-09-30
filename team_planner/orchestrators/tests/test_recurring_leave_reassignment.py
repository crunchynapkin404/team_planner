from __future__ import annotations

from datetime import date
from datetime import datetime
from datetime import timedelta
from zoneinfo import ZoneInfo

import pytest

from team_planner.employees.models import EmployeeProfile
from team_planner.employees.models import EmployeeSkill
from team_planner.employees.models import RecurringLeavePattern
from team_planner.orchestrators.incidents import IncidentsOrchestrator
from team_planner.orchestrators.models import OrchestrationRun
from team_planner.users.models import User

TZ = ZoneInfo("Europe/Amsterdam")


@pytest.mark.django_db
def test_recurring_leave_triggers_split_coverage_and_uses_all_available_users():
    # Three incidents-capable employees
    inc_skill, _ = EmployeeSkill.objects.get_or_create(
        name="incidents", defaults={"is_active": True},
    )
    users: list[User] = []
    for i in range(3):
        u = User.objects.create_user(username=f"inc_rl_{i}", password="pass")
        prof = EmployeeProfile.objects.create(
            user=u,
            employee_id=f"IR{i:03d}",
            hire_date=date(2020, 1, 1),
            status=EmployeeProfile.Status.ACTIVE,
            available_for_incidents=True,
        )
        prof.skills.add(inc_skill)
        users.append(u)

    # Employee 0 has a recurring Wednesday full-day pattern (blocks 08:00-17:00)
    RecurringLeavePattern.objects.create(
        employee=users[0],
        name="Wednesdays Off",
        day_of_week=RecurringLeavePattern.DayOfWeek.WEDNESDAY,
        frequency=RecurringLeavePattern.Frequency.WEEKLY,
        coverage_type=RecurringLeavePattern.CoverageType.FULL_DAY,
        pattern_start_date=date(2025, 9, 3),
        effective_from=date(2025, 9, 3),
        is_active=True,
    )

    # Two weeks range
    start = datetime(2025, 9, 8, 8, 0, tzinfo=TZ)  # Monday
    end = start + timedelta(weeks=2)

    orch = IncidentsOrchestrator(start_date=start, end_date=end)
    # Create an orchestration run to enable reassignment flow
    initiator = users[2]
    run = OrchestrationRun.objects.create(
        name="Reassign Test",
        description="Recurring leave split coverage test",
        initiated_by=initiator,
        start_date=start.date(),
        end_date=(end - timedelta(days=1)).date(),
        status=OrchestrationRun.Status.RUNNING,
        schedule_incidents=True,
        schedule_incidents_standby=False,
        schedule_waakdienst=False,
    )
    # Use full generate_schedule to exercise reassignment module
    result = orch.generate_schedule(orchestration_run=run)

    # We should have 2 weeks * 5 days = 10 day-assignments
    assignments = [a for a in result["assignments"] if a["shift_type"] == "incidents"]
    assert len(assignments) == 10

    # Wednesdays should not be assigned to employee 0 due to recurring leave; covered by others
    wed_assignees = set()
    for a in assignments:
        if a["start_datetime"].astimezone(TZ).weekday() == 2:  # Wednesday
            wed_assignees.add(a["assigned_employee_id"])
    assert users[0].pk not in wed_assignees
    # Coverage exists by other employees
    assert len(wed_assignees) >= 1

    # All available users should be used across the two weeks
    used = {a["assigned_employee_id"] for a in assignments}
    assert used.issuperset({u.pk for u in users})
