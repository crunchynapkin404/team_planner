"""
WaakdienstAdapter

Adapter to expose a uniform `generate_schedule` interface for Waakdienst,
wrapping the existing week-based `generate_assignments` API. This allows
progress toward a single orchestrator contract without changing behavior.

Feature-flagged via settings.ORCHESTRATOR_USE_WAAKDIENST_ADAPTER (default False).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from typing import Any

from django.conf import settings

if TYPE_CHECKING:
    from datetime import datetime

    from team_planner.orchestrators.waakdienst import WaakdienstOrchestrator


def waakdienst_adapter_enabled() -> bool:
    return bool(getattr(settings, "ORCHESTRATOR_USE_WAAKDIENST_ADAPTER", False))


@dataclass
class WaakdienstAdapter:
    orchestrator: WaakdienstOrchestrator

    def generate_schedule(
        self, start_date: datetime, end_date: datetime, dry_run: bool = True,
    ) -> dict[str, Any]:
        # Delegate to existing week-based implementation; keep payload shape
        return self.orchestrator.generate_assignments(
            start_date, end_date, dry_run=dry_run,
        )

    # Preserve existing UnifiedOrchestrator call path for weekly generation
    def generate_waakdienst_week_assignments(
        self, week_start: datetime, dry_run: bool = False,
    ) -> dict[str, Any]:
        return self.orchestrator.generate_waakdienst_week_assignments(
            week_start, dry_run=dry_run,
        )
