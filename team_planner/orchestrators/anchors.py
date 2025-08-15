from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, time
from typing import Iterable, List, Tuple
from zoneinfo import ZoneInfo

from django.conf import settings
from django.utils import timezone


WEEKDAY_MON = 0
WEEKDAY_TUE = 1
WEEKDAY_WED = 2
WEEKDAY_THU = 3
WEEKDAY_FRI = 4
WEEKDAY_SAT = 5
WEEKDAY_SUN = 6


def _ensure_tz(dt: datetime, tz: ZoneInfo) -> datetime:
    if timezone.is_aware(dt):
        # Convert to target tz if different
        return dt.astimezone(tz)
    return dt.replace(tzinfo=tz)


def get_team_tz(team) -> ZoneInfo:
    tz_name = getattr(team, "timezone", None) or settings.TIME_ZONE
    try:
        return ZoneInfo(tz_name)
    except Exception:
        return ZoneInfo(settings.TIME_ZONE)


def next_weekday_time(
    ref: datetime,
    weekday: int,
    hour: int,
    minute: int = 0,
    *,
    tz: ZoneInfo | None = None,
    strictly_after: bool = True,
) -> datetime:
    """Return the next datetime (in tz) that falls on given weekday at hour:minute.
    If strictly_after is True and ref is exactly the anchor, return next week's anchor.
    """
    tz = tz or ZoneInfo(settings.TIME_ZONE)
    ref = _ensure_tz(ref, tz)

    # Move to anchor time on the same date first
    candidate = ref
    # Normalize to midnight then set specific time to avoid DST pitfalls at 00:00
    candidate = candidate.replace(hour=0, minute=0, second=0, microsecond=0)

    days_ahead = (weekday - candidate.weekday()) % 7
    candidate = candidate + timedelta(days=days_ahead)

    # Set the desired local time (wall clock); ZoneInfo handles DST when arithmetic crosses boundaries
    candidate = candidate.replace(hour=hour, minute=minute)

    if candidate < ref or (strictly_after and candidate == ref):
        candidate = candidate + timedelta(days=7)
        candidate = candidate.replace(hour=hour, minute=minute)

    return candidate


@dataclass(frozen=True)
class Period:
    start: datetime
    end: datetime

    def as_tuple(self) -> Tuple[datetime, datetime]:
        return (self.start, self.end)


def waakdienst_periods(
    start_at: datetime,
    end_before: datetime,
    *,
    team,
) -> List[Period]:
    """Generate complete waakdienst periods within [start_at, end_before).

    Aligned to team-configured weekday with start_hour and end_hour.
    No partial periods: only include periods where end <= end_before.
    If start_at falls inside a period, we start at the next start anchor.
    """
    tz = get_team_tz(team)
    start_at = _ensure_tz(start_at, tz)
    end_before = _ensure_tz(end_before, tz)

    # Safely coerce nullable config values
    weekday = int((getattr(team, "waakdienst_handover_weekday", None) or WEEKDAY_WED))
    start_hour = int((getattr(team, "waakdienst_start_hour", None) or 17))
    end_hour = int((getattr(team, "waakdienst_end_hour", None) or 8))

    periods: List[Period] = []

    # First start anchor strictly after start_at if inside current period
    start_anchor = next_weekday_time(start_at, weekday, start_hour, tz=tz, strictly_after=True)

    while True:
        # End anchor is the next week's same weekday at end_hour
        end_anchor = start_anchor + timedelta(days=7)
        end_anchor = end_anchor.replace(hour=end_hour, minute=0)

        if end_anchor > end_before:
            break

        periods.append(Period(start=start_anchor, end=end_anchor))
        # Next start anchor is one week later at start_hour
        start_anchor = start_anchor + timedelta(days=7)
        start_anchor = start_anchor.replace(hour=start_hour, minute=0)

    return periods


def business_weeks(
    start_at: datetime,
    end_before: datetime,
    *,
    tz: ZoneInfo | None = None,
    week_start_weekday: int = WEEKDAY_MON,
    start_hour: int = 8,
    week_end_weekday: int = WEEKDAY_FRI,
    end_hour: int = 17,
) -> List[Period]:
    """Generate incident/standby business-week windows within [start_at, end_before).

    Aligned to Monday 08:00 → Friday 17:00 by default. No partial periods.
    If start_at falls inside a period, start at the next Monday 08:00.
    """
    tz = tz or ZoneInfo(settings.TIME_ZONE)
    start_at = _ensure_tz(start_at, tz)
    end_before = _ensure_tz(end_before, tz)

    periods: List[Period] = []

    start_anchor = next_weekday_time(start_at, week_start_weekday, start_hour, tz=tz, strictly_after=True)

    while True:
        # End anchor same calendar week on configured end weekday/hour
        # Compute Monday 00:00 of anchor week, then add offset to end weekday at end_hour
        week_monday = start_anchor - timedelta(days=(start_anchor.weekday() - week_start_weekday) % 7)
        week_monday = week_monday.replace(hour=0, minute=0, second=0, microsecond=0)

        # Compute end anchor
        days_to_end = (week_end_weekday - week_start_weekday) % 7
        end_anchor = week_monday + timedelta(days=days_to_end)
        end_anchor = end_anchor.replace(hour=end_hour, minute=0)

        if end_anchor <= start_anchor:
            # Ensure end is after start (in case of misconfiguration)
            end_anchor = start_anchor.replace(hour=end_hour, minute=0)
            if end_anchor <= start_anchor:
                end_anchor = start_anchor + timedelta(days=5)
                end_anchor = end_anchor.replace(hour=end_hour, minute=0)

        if end_anchor > end_before:
            break

        periods.append(Period(start=start_anchor, end=end_anchor))
        start_anchor = start_anchor + timedelta(days=7)
        start_anchor = start_anchor.replace(hour=start_hour, minute=0)

    return periods
