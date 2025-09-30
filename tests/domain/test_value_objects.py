"""
Comprehensive tests for domain layer value objects.

Tests all business logic, validation rules, and edge cases for value objects
as defined in the Phase 2 clean architecture design.
"""

import zoneinfo
from datetime import date
from datetime import datetime

import pytest

from domain.value_objects import AssignmentLoad
from domain.value_objects import BusinessHoursConfiguration
from domain.value_objects import DateRange
from domain.value_objects import EmployeeId
from domain.value_objects import FairnessScore
from domain.value_objects import ShiftType
from domain.value_objects import TeamConfiguration
from domain.value_objects import TimeRange


class TestEmployeeId:
    """Test EmployeeId value object."""

    def test_valid_employee_id(self):
        """Test creation of valid employee ID."""
        emp_id = EmployeeId(123)
        assert emp_id.value == 123

    def test_invalid_employee_id_zero(self):
        """Test that zero employee ID raises error."""
        with pytest.raises(ValueError, match="Employee ID must be positive"):
            EmployeeId(0)

    def test_invalid_employee_id_negative(self):
        """Test that negative employee ID raises error."""
        with pytest.raises(ValueError, match="Employee ID must be positive"):
            EmployeeId(-1)


class TestTimeRange:
    """Test TimeRange value object with timezone support."""

    def test_valid_time_range(self):
        """Test creation of valid time range."""
        tz = zoneinfo.ZoneInfo("Europe/Amsterdam")
        start = datetime(2024, 1, 1, 8, 0, tzinfo=tz)
        end = datetime(2024, 1, 1, 17, 0, tzinfo=tz)

        time_range = TimeRange(start, end, "Europe/Amsterdam")

        assert time_range.start == start
        assert time_range.end == end
        assert time_range.timezone == "Europe/Amsterdam"

    def test_duration_calculation(self):
        """Test duration calculation in hours."""
        tz = zoneinfo.ZoneInfo("Europe/Amsterdam")
        start = datetime(2024, 1, 1, 8, 0, tzinfo=tz)
        end = datetime(2024, 1, 1, 17, 0, tzinfo=tz)

        time_range = TimeRange(start, end, "Europe/Amsterdam")

        assert time_range.duration_hours() == 9.0

    def test_overlaps_with(self):
        """Test overlap detection between time ranges."""
        tz = zoneinfo.ZoneInfo("Europe/Amsterdam")

        range1 = TimeRange(
            datetime(2024, 1, 1, 8, 0, tzinfo=tz),
            datetime(2024, 1, 1, 12, 0, tzinfo=tz),
            "Europe/Amsterdam",
        )

        range2 = TimeRange(
            datetime(2024, 1, 1, 10, 0, tzinfo=tz),
            datetime(2024, 1, 1, 14, 0, tzinfo=tz),
            "Europe/Amsterdam",
        )

        range3 = TimeRange(
            datetime(2024, 1, 1, 13, 0, tzinfo=tz),
            datetime(2024, 1, 1, 17, 0, tzinfo=tz),
            "Europe/Amsterdam",
        )

        assert range1.overlaps_with(range2)  # 10-12 overlap
        assert range2.overlaps_with(range1)  # Symmetric
        assert not range1.overlaps_with(range3)  # No overlap

    def test_contains_moment(self):
        """Test checking if moment is within range."""
        tz = zoneinfo.ZoneInfo("Europe/Amsterdam")
        time_range = TimeRange(
            datetime(2024, 1, 1, 8, 0, tzinfo=tz),
            datetime(2024, 1, 1, 17, 0, tzinfo=tz),
            "Europe/Amsterdam",
        )

        inside_moment = datetime(2024, 1, 1, 12, 0, tzinfo=tz)
        outside_moment = datetime(2024, 1, 1, 18, 0, tzinfo=tz)

        assert time_range.contains(inside_moment)
        assert not time_range.contains(outside_moment)

    def test_timezone_conversion(self):
        """Test converting time range to different timezone."""
        amsterdam_tz = zoneinfo.ZoneInfo("Europe/Amsterdam")
        zoneinfo.ZoneInfo("UTC")

        # Create range in Amsterdam timezone
        amsterdam_range = TimeRange(
            datetime(2024, 1, 1, 8, 0, tzinfo=amsterdam_tz),
            datetime(2024, 1, 1, 17, 0, tzinfo=amsterdam_tz),
            "Europe/Amsterdam",
        )

        # Convert to UTC
        utc_range = amsterdam_range.to_timezone("UTC")

        assert utc_range.timezone == "UTC"
        # Amsterdam is UTC+1 in winter, so 8:00 Amsterdam = 7:00 UTC
        assert utc_range.start.hour == 7
        assert utc_range.end.hour == 16

    def test_invalid_time_range_same_time(self):
        """Test that start >= end raises error."""
        tz = zoneinfo.ZoneInfo("Europe/Amsterdam")
        start = datetime(2024, 1, 1, 8, 0, tzinfo=tz)

        with pytest.raises(ValueError, match="Start time must be before end time"):
            TimeRange(start, start, "Europe/Amsterdam")

    def test_invalid_timezone_naive_datetime(self):
        """Test that timezone-naive datetimes raise error."""
        start = datetime(2024, 1, 1, 8, 0)  # No timezone
        end = datetime(2024, 1, 1, 17, 0)  # No timezone

        with pytest.raises(ValueError, match="Times must be timezone-aware"):
            TimeRange(start, end, "Europe/Amsterdam")

    def test_invalid_timezone_string(self):
        """Test that invalid timezone string raises error."""
        tz = zoneinfo.ZoneInfo("Europe/Amsterdam")
        start = datetime(2024, 1, 1, 8, 0, tzinfo=tz)
        end = datetime(2024, 1, 1, 17, 0, tzinfo=tz)

        with pytest.raises(ValueError, match="Invalid timezone"):
            TimeRange(start, end, "Invalid/Timezone")


class TestShiftType:
    """Test ShiftType enumeration and properties."""

    def test_shift_type_values(self):
        """Test all shift type values."""
        assert ShiftType.INCIDENTS.value == "incidents"
        assert ShiftType.INCIDENTS_STANDBY.value == "incidents_standby"
        assert ShiftType.WAAKDIENST.value == "waakdienst"
        assert ShiftType.CHANGES.value == "changes"
        assert ShiftType.PROJECTS.value == "projects"

    def test_requires_business_hours(self):
        """Test which shift types require business hours."""
        assert ShiftType.INCIDENTS.requires_business_hours
        assert ShiftType.INCIDENTS_STANDBY.requires_business_hours
        assert not ShiftType.WAAKDIENST.requires_business_hours
        assert not ShiftType.CHANGES.requires_business_hours
        assert not ShiftType.PROJECTS.requires_business_hours

    def test_fairness_weights(self):
        """Test fairness weights for different shift types."""
        assert ShiftType.INCIDENTS.fairness_weight == 1.0
        assert ShiftType.INCIDENTS_STANDBY.fairness_weight == 0.8
        assert ShiftType.WAAKDIENST.fairness_weight == 1.2
        assert ShiftType.CHANGES.fairness_weight == 0.6
        assert ShiftType.PROJECTS.fairness_weight == 0.4

    def test_is_primary_coverage(self):
        """Test which shift types provide primary coverage."""
        assert ShiftType.INCIDENTS.is_primary_coverage
        assert ShiftType.WAAKDIENST.is_primary_coverage
        assert not ShiftType.INCIDENTS_STANDBY.is_primary_coverage
        assert not ShiftType.CHANGES.is_primary_coverage
        assert not ShiftType.PROJECTS.is_primary_coverage


class TestBusinessHoursConfiguration:
    """Test business hours configuration."""

    def test_default_business_hours(self):
        """Test default business hours configuration."""
        config = BusinessHoursConfiguration()

        # Monday through Friday should be 8-17
        assert config.monday_start == 8
        assert config.monday_end == 17
        assert config.friday_start == 8
        assert config.friday_end == 17

        # Weekend should be None (no work)
        assert config.saturday_start is None
        assert config.sunday_start is None

    def test_custom_business_hours(self):
        """Test custom business hours configuration."""
        config = BusinessHoursConfiguration(
            monday_start=9, monday_end=18, saturday_start=10, saturday_end=14,
        )

        assert config.monday_start == 9
        assert config.monday_end == 18
        assert config.saturday_start == 10
        assert config.saturday_end == 14

    def test_get_business_hours_for_day(self):
        """Test getting business hours for specific days."""
        config = BusinessHoursConfiguration()

        # Monday (0) should return (8, 17)
        monday_hours = config.get_business_hours_for_day(0)
        assert monday_hours == (8, 17)

        # Saturday (5) should return None
        saturday_hours = config.get_business_hours_for_day(5)
        assert saturday_hours is None

    def test_is_business_day(self):
        """Test business day detection."""
        config = BusinessHoursConfiguration()

        assert config.is_business_day(0)  # Monday
        assert config.is_business_day(4)  # Friday
        assert not config.is_business_day(5)  # Saturday
        assert not config.is_business_day(6)  # Sunday

    def test_invalid_hour_ranges(self):
        """Test validation of hour ranges."""
        with pytest.raises(ValueError, match="monday_start must be between 0 and 23"):
            BusinessHoursConfiguration(monday_start=25)

        with pytest.raises(ValueError, match="monday_start must be before monday_end"):
            BusinessHoursConfiguration(monday_start=18, monday_end=17)


class TestTeamConfiguration:
    """Test team configuration with all settings."""

    def test_valid_team_configuration(self):
        """Test creation of valid team configuration."""
        business_hours = BusinessHoursConfiguration()
        config = TeamConfiguration(
            timezone="Europe/Amsterdam",
            business_hours=business_hours,
            waakdienst_start_day=2,  # Wednesday
            waakdienst_start_hour=17,
            waakdienst_end_hour=8,
            skip_incidents_on_holidays=True,
            holiday_calendar="NL",
            max_consecutive_weeks=2,
            min_rest_hours=48,
            fairness_period_days=365,
            fairness_lookback_days=180,
        )

        assert config.timezone == "Europe/Amsterdam"
        assert config.waakdienst_start_day == 2
        assert config.fairness_period_days == 365

    def test_get_business_hours_range(self):
        """Test getting business hours range for a date."""
        business_hours = BusinessHoursConfiguration()
        config = TeamConfiguration(
            timezone="Europe/Amsterdam",
            business_hours=business_hours,
            waakdienst_start_day=2,
            waakdienst_start_hour=17,
            waakdienst_end_hour=8,
            skip_incidents_on_holidays=True,
            holiday_calendar="NL",
        )

        # Test Monday (business day)
        monday = date(2024, 1, 1)  # Assuming this is a Monday
        if monday.weekday() == 0:  # Ensure it's actually Monday
            range_result = config.get_business_hours_range(monday)
            assert range_result is not None
            assert range_result.duration_hours() == 9.0

    def test_get_waakdienst_week_range(self):
        """Test getting waakdienst week range."""
        business_hours = BusinessHoursConfiguration()
        config = TeamConfiguration(
            timezone="Europe/Amsterdam",
            business_hours=business_hours,
            waakdienst_start_day=2,  # Wednesday
            waakdienst_start_hour=17,
            waakdienst_end_hour=8,
            skip_incidents_on_holidays=True,
            holiday_calendar="NL",
        )

        # Start from a Monday
        monday = date(2024, 1, 1)
        week_range = config.get_waakdienst_week_range(monday)

        assert week_range.timezone == "Europe/Amsterdam"
        # Should be 7 days from Wednesday 17:00 to next Wednesday 08:00
        expected_hours = 7 * 24 - 9  # 7 days minus 9 hours (17:00 to 08:00 gap)
        assert (
            abs(week_range.duration_hours() - expected_hours) < 1
        )  # Allow for some calculation variance

    def test_invalid_timezone(self):
        """Test that invalid timezone raises error."""
        business_hours = BusinessHoursConfiguration()

        with pytest.raises(ValueError, match="Invalid timezone"):
            TeamConfiguration(
                timezone="Invalid/Timezone",
                business_hours=business_hours,
                waakdienst_start_day=2,
                waakdienst_start_hour=17,
                waakdienst_end_hour=8,
                skip_incidents_on_holidays=True,
                holiday_calendar="NL",
            )

    def test_invalid_waakdienst_day(self):
        """Test that invalid waakdienst day raises error."""
        business_hours = BusinessHoursConfiguration()

        with pytest.raises(
            ValueError, match="waakdienst_start_day must be between 0 and 6",
        ):
            TeamConfiguration(
                timezone="Europe/Amsterdam",
                business_hours=business_hours,
                waakdienst_start_day=7,  # Invalid day
                waakdienst_start_hour=17,
                waakdienst_end_hour=8,
                skip_incidents_on_holidays=True,
                holiday_calendar="NL",
            )


class TestFairnessScore:
    """Test fairness score value object."""

    def test_valid_fairness_score(self):
        """Test creation of valid fairness score."""
        period = DateRange(date(2024, 1, 1), date(2024, 12, 31))
        score = FairnessScore(
            incidents_score=5.0,
            incidents_standby_score=2.0,
            waakdienst_score=3.0,
            total_score=10.0,
            period=period,
        )

        assert score.incidents_score == 5.0
        assert score.total_score == 10.0
        assert score.period == period

    def test_negative_total_score_invalid(self):
        """Test that negative total score raises error."""
        period = DateRange(date(2024, 1, 1), date(2024, 12, 31))

        with pytest.raises(ValueError, match="Total score cannot be negative"):
            FairnessScore(
                incidents_score=5.0,
                incidents_standby_score=2.0,
                waakdienst_score=3.0,
                total_score=-1.0,
                period=period,
            )


class TestAssignmentLoad:
    """Test assignment load value object."""

    def test_valid_assignment_load(self):
        """Test creation of valid assignment load."""
        period = DateRange(date(2024, 1, 1), date(2024, 1, 31))
        load = AssignmentLoad(
            incidents_hours=45.0,
            incidents_standby_hours=18.0,
            waakdienst_hours=72.0,
            total_hours=135.0,
            period=period,
        )

        assert load.incidents_hours == 45.0
        assert load.total_hours == 135.0
        assert load.period == period

    def test_mismatched_total_hours_invalid(self):
        """Test that mismatched total hours raises error."""
        period = DateRange(date(2024, 1, 1), date(2024, 1, 31))

        with pytest.raises(ValueError, match="Total hours must equal sum"):
            AssignmentLoad(
                incidents_hours=45.0,
                incidents_standby_hours=18.0,
                waakdienst_hours=72.0,
                total_hours=100.0,  # Should be 135.0
                period=period,
            )
