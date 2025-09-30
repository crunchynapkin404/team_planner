from __future__ import annotations

from collections import defaultdict
from datetime import date
from datetime import datetime
from datetime import timedelta
from zoneinfo import ZoneInfo

import pytest

from team_planner.employees.models import EmployeeProfile
from team_planner.employees.models import EmployeeSkill
from team_planner.orchestrators.incidents import IncidentsOrchestrator
from team_planner.orchestrators.incidents_standby import IncidentsStandbyOrchestrator
from team_planner.orchestrators.utils.time_windows import get_waakdienst_week_bounds
from team_planner.orchestrators.waakdienst import WaakdienstOrchestrator
from team_planner.shifts.models import ShiftTemplate
from team_planner.shifts.models import ShiftType
from team_planner.users.models import User

TZ = ZoneInfo("Europe/Amsterdam")


def _create_incident_employees(n: int = 3) -> list[User]:
    users: list[User] = []
    inc_skill, _ = EmployeeSkill.objects.get_or_create(
        name="incidents", defaults={"is_active": True},
    )
    for i in range(n):
        u = User.objects.create_user(username=f"inc{i}", password="pass")
        prof = EmployeeProfile.objects.create(
            user=u,
            employee_id=f"I{i:03d}",
            hire_date=date(2020, 1, 1),
            status=EmployeeProfile.Status.ACTIVE,
            available_for_incidents=True,
        )
        # Attach incidents skill to satisfy constraint checker
        prof.skills.add(inc_skill)
        users.append(u)
    return users


def _create_waakdienst_employees(n: int = 3) -> list[User]:
    skill, _ = EmployeeSkill.objects.get_or_create(
        name="waakdienst", defaults={"is_active": True},
    )
    users: list[User] = []
    for i in range(n):
        u = User.objects.create_user(username=f"waak{i}", password="pass")
        prof = EmployeeProfile.objects.create(
            user=u,
            employee_id=f"W{i:03d}",
            hire_date=date(2020, 1, 1),
            status=EmployeeProfile.Status.ACTIVE,
            available_for_waakdienst=True,
        )
        prof.skills.add(skill)
        users.append(u)
    return users


def _count_weekdays(start: datetime, end: datetime) -> int:
    # Inclusive start, exclusive end for counting days
    cur = start
    count = 0
    while cur < end:
        if cur.weekday() < 5:
            count += 1
        cur += timedelta(days=1)
    return count


@pytest.mark.django_db
def test_incidents_orchestrator_52_weeks_independent():
    _create_incident_employees(3)

    # Anchor to a Monday 08:00 local time
    start = datetime(2025, 9, 8, 8, 0, tzinfo=TZ)  # Monday
    end = start + timedelta(weeks=52)

    orch = IncidentsOrchestrator(start_date=start, end_date=end)
    result = orch.generate_schedule()

    assert result["total_shifts"] > 0
    assert result.get("errors", []) == []

    assignments = result["assignments"]

    # Expect 5 business days per week for 52 weeks
    expected_days = _count_weekdays(start, end)
    assert expected_days == 5 * 52
    assert len(assignments) == expected_days

    # Continuity: each ISO week should be assigned to a single engineer when no conflicts
    by_week: dict[tuple[int, int], set[int]] = defaultdict(set)
    for a in assignments:
        sd = a["start_datetime"].astimezone(TZ)
        year, week, _ = sd.isocalendar()
        by_week[(year, week)].add(a["assigned_employee_id"])

    # Over the 52 weeks in range, each week should have one unique engineer
    assert all(len(s) == 1 for s in by_week.values())

    # Fairness sanity: distribution difference between most/least weeks per person <= 1
    week_count_by_emp: dict[int, int] = defaultdict(int)
    for emp_set in by_week.values():
        emp_id = next(iter(emp_set))
        week_count_by_emp[emp_id] += 1
    if week_count_by_emp:  # defensive
        counts = list(week_count_by_emp.values())
        assert max(counts) - min(counts) <= 1


@pytest.mark.django_db
def test_incidents_standby_orchestrator_52_weeks_independent():
    _create_incident_employees(3)

    # Anchor to a Monday 08:00 local time
    start = datetime(2025, 9, 8, 8, 0, tzinfo=TZ)  # Monday
    end = start + timedelta(weeks=52)

    orch = IncidentsStandbyOrchestrator(start_date=start, end_date=end)
    result = orch.generate_schedule()

    assert result["total_shifts"] > 0
    assert result.get("errors", []) == []

    assignments = result["assignments"]

    # Expect 5 business days per week for 52 weeks
    expected_days = _count_weekdays(start, end)
    assert expected_days == 5 * 52
    assert len(assignments) == expected_days

    # Continuity: each ISO week should be assigned to a single engineer when no conflicts
    by_week: dict[tuple[int, int], set[int]] = defaultdict(set)
    for a in assignments:
        sd = a["start_datetime"].astimezone(TZ)
        year, week, _ = sd.isocalendar()
        by_week[(year, week)].add(a["assigned_employee_id"])

    assert all(len(s) == 1 for s in by_week.values())

    # Fairness sanity: distribution difference between most/least weeks per person <= 1
    week_count_by_emp: dict[int, int] = defaultdict(int)
    for emp_set in by_week.values():
        emp_id = next(iter(emp_set))
        week_count_by_emp[emp_id] += 1
    if week_count_by_emp:
        counts = list(week_count_by_emp.values())
        assert max(counts) - min(counts) <= 1


@pytest.mark.django_db
def test_waakdienst_orchestrator_52_weeks_independent():
    _create_waakdienst_employees(3)

    # Ensure an active waakdienst template exists
    ShiftTemplate.objects.create(
        name="Waakdienst Default",
        shift_type=ShiftType.WAAKDIENST,
        duration_hours=15,
        is_active=True,
    )

    # Use a Wednesday reference and expand to 52 weeks exactly
    ref = datetime(2025, 9, 10, 12, 0, tzinfo=TZ)  # Wednesday
    start_week_start, _ = get_waakdienst_week_bounds(ref)
    start = start_week_start
    # Include exactly 52 waakdienst weeks: last week starts at start + 7*51 days
    end = start + timedelta(days=7 * 51, hours=1)

    orch = WaakdienstOrchestrator()
    result = orch.generate_assignments(start, end, dry_run=True)

    assert result.get("errors", []) == []
    assignments = result["assignments"]

    # Expect 52 weeks * 7 daily assignments
    assert len(assignments) == 52 * 7

    # Group by waakdienst week; each group should have 7 days and a single engineer
    groups: dict[datetime, list[dict]] = defaultdict(list)
    for a in assignments:
        ws, we = get_waakdienst_week_bounds(a["start_datetime"])
        groups[ws].append(a)

    assert len(groups) == 52
    for ws, items in groups.items():
        assert len(items) == 7
        emp_ids = {it["assigned_employee_id"] for it in items}
        assert len(emp_ids) == 1

    # Fairness sanity: all available users are used and distribution is balanced (±1)
    week_count_by_emp: dict[int, int] = defaultdict(int)
    for items in groups.values():
        emp_id = items[0]["assigned_employee_id"]
        week_count_by_emp[emp_id] += 1
    # Expect at least 3 employees used
    assert len(week_count_by_emp.keys()) >= 3
    counts = list(week_count_by_emp.values())
    assert max(counts) - min(counts) <= 1
