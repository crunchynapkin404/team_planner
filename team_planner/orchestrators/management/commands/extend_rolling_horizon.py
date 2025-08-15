"""Extend team schedules to a rolling horizon using orchestrator generators.

Usage:
  python manage.py extend_rolling_horizon --months 6 [--dry-run] [--teams 1 2 3]
"""
from __future__ import annotations

from typing import List, Optional

from django.core.management.base import BaseCommand

from team_planner.orchestrators.tasks import extend_rolling_horizon_core


class Command(BaseCommand):
    help = "Extend schedules up to now + N months (anchor-aligned, idempotent)."

    def add_arguments(self, parser):
        parser.add_argument("--months", type=int, default=6, help="Months to extend (default 6)")
        parser.add_argument("--dry-run", action="store_true", help="Preview only, no DB writes")
        parser.add_argument(
            "--teams",
            nargs="*",
            type=int,
            help="Optional list of team IDs to limit extension to",
        )

    def handle(self, *args, **options):
        months: int = options["months"]
        dry_run: bool = options["dry_run"]
        team_ids: Optional[List[int]] = options.get("teams")

        summary = extend_rolling_horizon_core(months=months, dry_run=dry_run, team_ids=team_ids)

        totals = summary["totals"]
        self.stdout.write(self.style.SUCCESS(
            f"Horizon extended to {summary['end'].date()} for {totals['teams']} teams"
        ))
        self.stdout.write(
            f"Created: {totals['created']} | Duplicates skipped: {totals['duplicates_skipped']} | "
            f"Incidents: {totals['incidents']} | Standby: {totals['incidents_standby']} | Waakdienst: {totals['waakdienst']}"
        )

        # Pretty print per-team summary
        for t in summary["teams"]:
            mode = "DRY-RUN" if t["preview"] else "APPLIED"
            self.stdout.write(
                f"- Team {t['team_name']} (id={t['team_id']}): {mode} | "
                f"Incidents={t['incidents']}, Standby={t['incidents_standby']}, Waakdienst={t['waakdienst']} | "
                f"Created={t['created']}, Duplicates={t['duplicates_skipped']}"
            )
