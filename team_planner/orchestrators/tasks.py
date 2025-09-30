from __future__ import annotations

from dataclasses import asdict
from dataclasses import dataclass
from datetime import datetime
from datetime import timedelta
from typing import TYPE_CHECKING
from typing import Any

from celery import shared_task
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from team_planner.orchestrators.unified import UnifiedOrchestrator
from team_planner.shifts.models import Shift
from team_planner.shifts.models import ShiftType
from team_planner.teams.models import Team

if TYPE_CHECKING:
    from collections.abc import Iterable


@dataclass
class TeamHorizonReport:
    team_id: int
    team_name: str
    start: datetime
    end: datetime
    preview: bool
    created: int
    duplicates_skipped: int
    incidents: int
    incidents_standby: int
    waakdienst: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _plan_for_team(
    team: Team,
    start_dt: datetime,
    end_dt: datetime,
    dry_run: bool,
    shift_types: list[str] | None = None,
) -> TeamHorizonReport:
    # Determine which shift types to schedule
    include_incidents = True if shift_types is None else ("incidents" in shift_types)
    include_standby = (
        (team.standby_mode == Team.StandbyMode.GLOBAL_PER_WEEK)
        if shift_types is None
        else ("incidents_standby" in shift_types)
    )
    include_waakdienst = True if shift_types is None else ("waakdienst" in shift_types)

    # Track results across all orchestrators
    total_created = 0
    incidents_count = 0
    standby_count = 0
    waakdienst_count = 0

    # Run each shift type independently using UnifiedOrchestrator
    if include_incidents:
        orch = UnifiedOrchestrator(
            team=team,
            start_date=start_dt,
            end_date=end_dt,
            shift_types=[ShiftType.INCIDENTS],
            dry_run=dry_run,
        )

        if dry_run:
            result = orch.preview_schedule()
        else:
            with transaction.atomic():
                result = orch.apply_schedule()

        incidents_count = result.get("total_shifts_created", 0)
        if not dry_run:
            total_created += incidents_count

    if include_standby:
        orch = UnifiedOrchestrator(
            team=team,
            start_date=start_dt,
            end_date=end_dt,
            shift_types=[ShiftType.INCIDENTS_STANDBY],
            dry_run=dry_run,
        )

        if dry_run:
            result = orch.preview_schedule()
        else:
            with transaction.atomic():
                result = orch.apply_schedule()

        standby_count = result.get("total_shifts_created", 0)
        if not dry_run:
            total_created += standby_count

    if include_waakdienst:
        orch = UnifiedOrchestrator(
            team=team,
            start_date=start_dt,
            end_date=end_dt,
            shift_types=[ShiftType.WAAKDIENST],
            dry_run=dry_run,
        )

        if dry_run:
            result = orch.preview_schedule()
        else:
            with transaction.atomic():
                result = orch.apply_schedule()

        waakdienst_count = result.get("total_shifts_created", 0)
        if not dry_run:
            total_created += waakdienst_count

    return TeamHorizonReport(
        team_id=team.pk,
        team_name=str(team),
        start=start_dt,
        end=end_dt,
        preview=dry_run,
        created=total_created if not dry_run else 0,
        duplicates_skipped=0,  # UnifiedOrchestrator handles duplicates internally
        incidents=incidents_count,
        incidents_standby=standby_count,
        waakdienst=waakdienst_count,
    )


def extend_rolling_horizon_core(
    months: int = 6,
    dry_run: bool = False,
    team_ids: Iterable[int] | None = None,
    weeks: int | None = None,
    shift_types: list[str] | None = None,
) -> dict[str, Any]:
    """Extend schedules up to now + N months or weeks using complete, anchor-aligned periods per team.

    - Only runs for teams that already have an initial manual plan reaching a configured horizon
      when ORCHESTRATOR_AUTO_ROLL_REQUIRES_SEED=True (default). Seed horizon defaults to 26 weeks
      and can be tuned via ORCHESTRATOR_MIN_SEED_WEEKS.
    - No partial periods are generated (orchestrator generators enforce anchors).
    - Idempotent: relies on unique constraints and duplicate skipping.
    - Scopes to teams with at least one active member.
    """
    now = timezone.now()

    # Determine horizon end from settings (weeks preferred) or fallback to months
    default_weeks = int(getattr(settings, "ORCHESTRATOR_ROLLING_WEEKS", 26))
    weeks_to_roll = int(weeks or default_weeks)
    if weeks_to_roll > 0:
        end_dt = now + timedelta(weeks=weeks_to_roll)
    else:
        end_dt = now + timedelta(days=months * 30)

    qs = Team.objects.all()
    if team_ids:
        qs = qs.filter(id__in=list(team_ids))

    # Only plan for teams that have active memberships
    qs = qs.filter(teammembership__is_active=True).distinct()

    require_seed = bool(getattr(settings, "ORCHESTRATOR_AUTO_ROLL_REQUIRES_SEED", True))
    min_seed_weeks = int(getattr(settings, "ORCHESTRATOR_MIN_SEED_WEEKS", 26))
    seed_target_dt = now + timedelta(weeks=max(1, min_seed_weeks))

    reports: list[TeamHorizonReport] = []
    for team in qs:
        if require_seed:
            has_seed = Shift.objects.filter(
                assigned_employee__teams=team,
                end_datetime__gte=seed_target_dt,
                status__in=[Shift.Status.SCHEDULED, Shift.Status.IN_PROGRESS],
            ).exists()
            if not has_seed:
                continue

        start_dt = now
        report = _plan_for_team(
            team, start_dt, end_dt, dry_run=dry_run, shift_types=shift_types,
        )
        reports.append(report)

    return {
        "now": now,
        "end": end_dt,
        "dry_run": dry_run,
        "teams": [r.to_dict() for r in reports],
        "totals": {
            "teams": len(reports),
            "created": sum(r.created for r in reports),
            "duplicates_skipped": sum(r.duplicates_skipped for r in reports),
            "incidents": sum(r.incidents for r in reports),
            "incidents_standby": sum(r.incidents_standby for r in reports),
            "waakdienst": sum(r.waakdienst for r in reports),
        },
    }


@shared_task(name="orchestrators.extend_rolling_horizon")
def extend_rolling_horizon_task(
    months: int = 6,
    dry_run: bool = False,
    team_ids: list[int] | None = None,
    weeks: int | None = None,
    shift_types: list[str] | None = None,
) -> dict[str, Any]:
    """Celery task wrapper for rolling horizon extension.

    Example dispatch:
      extend_rolling_horizon_task.delay(weeks=26, dry_run=False, shift_types=['incidents','waakdienst'])
    """
    return extend_rolling_horizon_core(
        months=months,
        dry_run=dry_run,
        team_ids=team_ids,
        weeks=weeks,
        shift_types=shift_types,
    )
