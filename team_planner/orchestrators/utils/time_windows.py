"""Shared time window utilities for orchestrators.

Centralizes timezone-aware window calculations for incidents and waakdienst per
SHIFT_SCHEDULING_SPEC. All datetimes returned are timezone-aware.
"""

from __future__ import annotations

from datetime import date as d_date
from datetime import datetime
from datetime import time
from datetime import timedelta
from zoneinfo import ZoneInfo

TZ_NAME = "Europe/Amsterdam"
TZ = ZoneInfo(TZ_NAME)


def _as_aware(dt: datetime) -> datetime:
    """Ensure datetime is timezone-aware in Europe/Amsterdam.

    If naive, attach ZoneInfo(TZ_NAME). If already aware, convert.
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=TZ)
    return dt.astimezone(TZ)


def business_day_window(day: d_date | datetime) -> tuple[datetime, datetime]:
    """Return 08:00–17:00 window for a given calendar day in Europe/Amsterdam."""
    day_date = day.date() if isinstance(day, datetime) else day
    start = datetime.combine(day_date, time(8, 0))
    end = datetime.combine(day_date, time(17, 0))
    return _as_aware(start), _as_aware(end)


def waakdienst_daily_window(day: d_date | datetime) -> tuple[datetime, datetime]:
    """Return waakdienst daily window per spec for a given day.

    - Mon/Tue/Wed/Thu: 17:00 → next day 08:00 (15h)
    - Fri: 17:00 → Sat 08:00 (15h)
    - Sat: 08:00 → Sun 08:00 (24h)
    - Sun: 08:00 → Mon 08:00 (24h)
    """
    ref = day if isinstance(day, datetime) else datetime.combine(day, time(0, 0))
    ref = _as_aware(ref)

    wd = ref.weekday()  # 0=Mon..6=Sun
    if wd in (0, 1, 2, 3) or wd == 4:
        start = ref.replace(hour=17, minute=0, second=0, microsecond=0)
        end = (start + timedelta(days=1)).replace(hour=8)
    elif wd in (5, 6):
        start = ref.replace(hour=8, minute=0, second=0, microsecond=0)
        end = (start + timedelta(days=1)).replace(hour=8)
    else:
        # Should never happen
        start = ref.replace(hour=17, minute=0, second=0, microsecond=0)
        end = (start + timedelta(days=1)).replace(hour=8)
    return start, end


def get_waakdienst_week_start(reference: datetime) -> datetime:
    """Return the start of the waakdienst week (Wed 17:00) for a reference datetime."""
    ref = _as_aware(reference)
    if ref.weekday() == 2:  # Wednesday
        if ref.hour >= 17:
            return ref.replace(hour=17, minute=0, second=0, microsecond=0)
        # before 17:00 → previous Wednesday 17:00
        prev = ref - timedelta(days=7)
        return prev.replace(hour=17, minute=0, second=0, microsecond=0)
    # find most recent Wednesday
    days_since_wed = (ref.weekday() - 2) % 7
    if days_since_wed == 0:
        days_since_wed = 7
    start = ref - timedelta(days=days_since_wed)
    return start.replace(hour=17, minute=0, second=0, microsecond=0)


def get_waakdienst_week_bounds(reference: datetime) -> tuple[datetime, datetime]:
    """Return (start, end) for the waakdienst week containing reference.

    Start: Wednesday 17:00
    End: next Wednesday 08:00
    """
    start = get_waakdienst_week_start(reference)
    # Next Wednesday then force 08:00
    end_candidate = start + timedelta(days=7)
    end = end_candidate.replace(hour=8, minute=0, second=0, microsecond=0)
    return start, end


def waakdienst_week_windows(reference: datetime) -> list[tuple[datetime, datetime]]:
    """Return the list of 7 waakdienst daily windows for the week that contains reference."""
    start, _ = get_waakdienst_week_bounds(reference)
    days = []
    for i in range(7):
        day_ref = start + timedelta(days=i)
        s, e = waakdienst_daily_window(day_ref)
        days.append((s, e))
    return days
