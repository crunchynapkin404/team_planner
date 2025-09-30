from __future__ import annotations

from collections import defaultdict
from datetime import date
from datetime import datetime
from datetime import timedelta
from zoneinfo import ZoneInfo

import pytest

from team_planner.employees.models import EmployeeProfile
from team_planner.employees.models import EmployeeSkill
from team_planner.employees.models import RecurringLeavePattern
from team_planner.leaves.models import LeaveRequest
from team_planner.leaves.models import LeaveType
from team_planner.orchestrators.incidents_new import IncidentsOrchestrator
from team_planner.orchestrators.utils.time_windows import get_waakdienst_week_bounds
from team_planner.orchestrators.waakdienst import WaakdienstOrchestrator
from team_planner.teams.models import Department
from team_planner.teams.models import Team
from team_planner.teams.models import TeamMembership
from team_planner.users.models import User

TZ = ZoneInfo("Europe/Amsterdam")


def _mk_team_with_members(n: int = 15) -> tuple[Team, list[User]]:
    dept = Department.objects.create(name="Ops", description="Operations")
    team = Team.objects.create(name="A", department=dept)

    # Skills
    incidents_skill, _ = EmployeeSkill.objects.get_or_create(
        name="incidents", defaults={"is_active": True},
    )
    waakdienst_skill, _ = EmployeeSkill.objects.get_or_create(
        name="waakdienst", defaults={"is_active": True},
    )

    users: list[User] = []
    for i in range(n):
        u = User.objects.create_user(
            username=f"u{i:02d}", password="pass", email=f"u{i:02d}@example.com",
        )
        prof = EmployeeProfile.objects.create(
            user=u,
            employee_id=f"E{i:03d}",
            hire_date=date(2020, 1, 1),
            status=EmployeeProfile.Status.ACTIVE,
            available_for_incidents=True,
            available_for_waakdienst=True,
        )
        prof.skills.add(incidents_skill)
        prof.skills.add(waakdienst_skill)
        TeamMembership.objects.create(user=u, team=team)
        users.append(u)

    return team, users


def _seed_leave_types() -> tuple[LeaveType, LeaveType]:
    vac, _ = LeaveType.objects.get_or_create(
        name="Vacation",
        defaults={
            "default_days_per_year": 25.0,
            "requires_approval": True,
            "is_paid": True,
            "conflict_handling": LeaveType.ConflictHandling.FULL_UNAVAILABLE,
        },
    )
    day_only, _ = LeaveType.objects.get_or_create(
        name="Personal Day",
        defaults={
            "default_days_per_year": 5.0,
            "requires_approval": True,
            "is_paid": True,
            "conflict_handling": LeaveType.ConflictHandling.DAYTIME_ONLY,
        },
    )
    return vac, day_only


def _add_recurring_leaves(users: list[User], start: date) -> None:
    # First 5 users: weekly Wednesdays off (full-day)
    for u in users[:5]:
        RecurringLeavePattern.objects.create(
            employee=u,
            name="Weekly Wednesday Off",
            day_of_week=RecurringLeavePattern.DayOfWeek.WEDNESDAY,
            frequency=RecurringLeavePattern.Frequency.WEEKLY,
            coverage_type=RecurringLeavePattern.CoverageType.FULL_DAY,
            pattern_start_date=start,
            effective_from=start,
            is_active=True,
        )

    # Next 3 users: biweekly Fridays off (afternoon)
    for u in users[5:8]:
        RecurringLeavePattern.objects.create(
            employee=u,
            name="Biweekly Friday PM",
            day_of_week=RecurringLeavePattern.DayOfWeek.FRIDAY,
            frequency=RecurringLeavePattern.Frequency.BIWEEKLY,
            coverage_type=RecurringLeavePattern.CoverageType.AFTERNOON,
            pattern_start_date=start,
            effective_from=start,
            is_active=True,
        )


def _add_normal_leaves(
    users: list[User], vac: LeaveType, day_only: LeaveType, start_d: date,
) -> None:
    # Deterministic normal leaves:
    # - For each of the remaining users, approve one 3-day vacation starting on a Monday within the window
    # - And one single-day personal leave mid-week
    # Choose spread across first two months to avoid too many overlaps
    monday = (
        start_d
        if start_d.weekday() == 0
        else start_d + timedelta(days=(7 - start_d.weekday()))
    )
    for idx, u in enumerate(users[8:], start=0):
        vac_start = monday + timedelta(weeks=idx % 8)  # within first 8 weeks
        LeaveRequest.objects.create(
            employee=u,
            leave_type=vac,
            start_date=vac_start,
            end_date=vac_start + timedelta(days=2),
            days_requested=3.0,
            status=LeaveRequest.Status.APPROVED,
        )
        # Single-day personal leave on a Wednesday 2 weeks later
        wed = vac_start + timedelta(weeks=2)
        while wed.weekday() != 3 - 1:  # Wednesday=2
            wed += timedelta(days=1)
        LeaveRequest.objects.create(
            employee=u,
            leave_type=day_only,
            start_date=wed,
            end_date=wed,
            days_requested=1.0,
            status=LeaveRequest.Status.APPROVED,
        )


@pytest.mark.django_db
def test_full_scale_incidents_and_standby_52_weeks():
    team, users = _mk_team_with_members(15)
    vac, day_only = _seed_leave_types()

    start = datetime(2025, 9, 8, 8, 0, tzinfo=TZ)  # Monday 08:00
    end = start + timedelta(weeks=52)

    _add_recurring_leaves(users, start.date())
    _add_normal_leaves(users, vac, day_only, start.date())

    orch = IncidentsOrchestrator(team_id=team.pk, include_standby=True)
    result = orch.generate_assignments(start, end, dry_run=True)

    assert result.get("errors", []) == []
    assignments = result["assignments"]
    assert assignments, "Expected assignments to be generated"

    # Expect 5 business days per week for 52 weeks for each of incidents and standby
    expected_days = 5 * 52
    primaries = [a for a in assignments if a["shift_type"] == "incidents"]
    standbys = [a for a in assignments if a["shift_type"] == "incidents_standby"]
    assert len(primaries) == expected_days
    assert len(standbys) == expected_days

    # For each business day, primary and standby must not be the same employee
    # Build map by date
    by_date = defaultdict(dict)
    for a in assignments:
        d = a["start_datetime"].astimezone(TZ).date()
        by_date[(d, a["shift_type"])]["emp"] = a["assigned_employee_id"]

    for _week in range(52 * 5):
        # Iterate through the actual dates in range
        pass

    # Check for each date that both assignments exist and differ
    for key_date in sorted({d for (d, _st) in by_date}):
        primary = by_date.get((key_date, "incidents"), {}).get("emp")
        standby = by_date.get((key_date, "incidents_standby"), {}).get("emp")
        assert primary is not None
        assert standby is not None
        assert primary != standby

    # Fairness: distribution across 15 users should be reasonably balanced (±2)
    def counts_by_emp(items: list[dict]) -> dict[int, int]:
        counts: dict[int, int] = defaultdict(int)
        for it in items:
            counts[int(it["assigned_employee_id"])] += 1
        return counts

    primary_counts = counts_by_emp(primaries)
    standby_counts = counts_by_emp(standbys)

    assert len(primary_counts) >= 12  # most employees used
    assert len(standby_counts) >= 12
    pc_vals = list(primary_counts.values())
    sc_vals = list(standby_counts.values())
    # With recurring + normal leaves, allow a slightly wider spread
    assert max(pc_vals) - min(pc_vals) <= 3
    assert max(sc_vals) - min(sc_vals) <= 5

    # Recurring leave: those with weekly Wednesday off should never be assigned on Wednesdays
    wed_off_ids = {u.pk for u in users[:5]}
    for a in primaries + standbys:
        sd = a["start_datetime"].astimezone(TZ)
        if sd.weekday() == 2:  # Wednesday
            assert a["assigned_employee_id"] not in wed_off_ids


@pytest.mark.django_db
def test_full_scale_waakdienst_52_weeks():
    team, users = _mk_team_with_members(15)
    vac, _ = _seed_leave_types()

    # Some full-unavailable vacation weeks for a few users to force rotation
    ref = datetime(2025, 9, 10, 12, 0, tzinfo=TZ)  # Wednesday reference
    start_week_start, _ = get_waakdienst_week_bounds(ref)
    start = start_week_start
    end = start + timedelta(days=7 * 51, hours=1)  # 52 weeks window

    # Approve some full-week vacations for first 3 users within the period
    for i, u in enumerate(users[:3]):
        week_start = (start + timedelta(weeks=2 * (i + 1))).date()
        LeaveRequest.objects.create(
            employee=u,
            leave_type=vac,
            start_date=week_start,
            end_date=week_start + timedelta(days=4),  # Mon-Fri as full-unavailable
            days_requested=5.0,
            status=LeaveRequest.Status.APPROVED,
        )

    orch = WaakdienstOrchestrator(team_id=team.pk)
    result = orch.generate_assignments(start, end, dry_run=True)
    assert result.get("errors", []) == []
    assignments = result["assignments"]
    assert len(assignments) == 52 * 7

    # Group by waakdienst week start and verify one engineer per week
    groups: dict[datetime, list[dict]] = defaultdict(list)
    for a in assignments:
        ws, _we = get_waakdienst_week_bounds(a["start_datetime"])
        groups[ws].append(a)

    assert len(groups) == 52
    for ws, items in groups.items():
        assert len(items) == 7
        emp_ids = {it["assigned_employee_id"] for it in items}
        assert len(emp_ids) == 1

    # Fairness across 15 members roughly balanced
    week_count_by_emp: dict[int, int] = defaultdict(int)
    for items in groups.values():
        emp_id = int(items[0]["assigned_employee_id"])
        week_count_by_emp[emp_id] += 1
    assert len(week_count_by_emp.keys()) >= 10
    counts = list(week_count_by_emp.values())
    assert max(counts) - min(counts) <= 2
