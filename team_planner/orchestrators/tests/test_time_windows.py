from datetime import date
from datetime import datetime
from datetime import timedelta
from zoneinfo import ZoneInfo

from team_planner.orchestrators.utils.time_windows import business_day_window
from team_planner.orchestrators.utils.time_windows import get_waakdienst_week_bounds
from team_planner.orchestrators.utils.time_windows import waakdienst_daily_window
from team_planner.orchestrators.utils.time_windows import waakdienst_week_windows

TZ = ZoneInfo("Europe/Amsterdam")


def test_business_day_window_basic():
    d = date(2025, 1, 13)  # Monday
    start, end = business_day_window(d)
    assert start.hour == 8
    assert end.hour == 17
    assert start.tzinfo == TZ
    assert end.tzinfo == TZ


def test_waakdienst_daily_window_weekday():
    d = date(2025, 1, 13)  # Monday
    s, e = waakdienst_daily_window(d)
    assert s.hour == 17
    assert e.hour == 8
    assert (e - s) == timedelta(hours=15)


def test_waakdienst_daily_window_weekend_sat():
    d = date(2025, 1, 18)  # Saturday
    s, e = waakdienst_daily_window(d)
    assert s.hour == 8
    assert e.hour == 8
    assert (e - s) == timedelta(hours=24)


def test_get_waakdienst_week_bounds_alignment():
    ref = datetime(2025, 1, 15, 10, 0, tzinfo=TZ)  # Wednesday before 17:00
    start, end = get_waakdienst_week_bounds(ref)
    # start should be previous Wed 17:00 (Jan 8, 17:00)
    assert start.weekday() == 2
    assert start.hour == 17
    assert end.weekday() == 2
    assert end.hour == 8
    # From Wed 17:00 to next Wed 08:00 is 6 days and 15 hours (168-9 = 159h)
    assert (end - start) == timedelta(days=6, hours=15)


def test_waakdienst_week_windows_count():
    ref = datetime(2025, 1, 13, 12, 0, tzinfo=TZ)
    days = waakdienst_week_windows(ref)
    assert len(days) == 7
    # first window must start Wed 17:00 of that week
    first_start, _ = days[0]
    assert first_start.weekday() == 2
    assert first_start.hour == 17
