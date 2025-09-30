"""
Value objects for the domain layer.

Value objects are immutable objects that represent domain concepts
and contain no identity - they are defined by their properties.
"""

import zoneinfo
from dataclasses import dataclass
from datetime import date
from datetime import datetime
from datetime import timedelta
from enum import Enum
from typing import List
from typing import Optional
from typing import Tuple


@dataclass(frozen=True)
class EmployeeId:
    """Unique identifier for an employee."""

    value: int

    def __post_init__(self):
        if self.value <= 0:
            msg = "Employee ID must be positive"
            raise ValueError(msg)


@dataclass(frozen=True)
class TeamId:
    """Unique identifier for a team."""

    value: int

    def __post_init__(self):
        if self.value <= 0:
            msg = "Team ID must be positive"
            raise ValueError(msg)


@dataclass(frozen=True)
class ShiftId:
    """Unique identifier for a shift."""

    value: int

    def __post_init__(self):
        if self.value <= 0:
            msg = "Shift ID must be positive"
            raise ValueError(msg)

    @classmethod
    def generate(cls) -> "ShiftId":
        """Generate a new shift ID (placeholder - would use UUID in real implementation)."""
        import random

        return cls(random.randint(1, 1000000))


@dataclass(frozen=True)
class AssignmentId:
    """Unique identifier for an assignment."""

    value: int

    def __post_init__(self):
        if self.value <= 0:
            msg = "Assignment ID must be positive"
            raise ValueError(msg)

    @classmethod
    def generate(cls) -> "AssignmentId":
        """Generate a new assignment ID (placeholder - would use UUID in real implementation)."""
        import random

        return cls(random.randint(1, 1000000))


@dataclass(frozen=True)
class UserId:
    """Unique identifier for a user."""

    value: int

    def __post_init__(self):
        if self.value <= 0:
            msg = "User ID must be positive"
            raise ValueError(msg)

    @classmethod
    def system(cls) -> "UserId":
        """System user ID for automated operations."""
        return cls(1)


@dataclass(frozen=True)
class TimeRange:
    """Immutable time range with timezone support.

    Addresses Phase 1 critical gap: timezone support for international teams.
    """

    start: datetime
    end: datetime
    timezone: str

    def __post_init__(self):
        if self.start >= self.end:
            msg = "Start time must be before end time"
            raise ValueError(msg)

        if not self.start.tzinfo or not self.end.tzinfo:
            msg = "Times must be timezone-aware"
            raise ValueError(msg)

        # Validate timezone string
        try:
            zoneinfo.ZoneInfo(self.timezone)
        except zoneinfo.ZoneInfoNotFoundError:
            msg = f"Invalid timezone: {self.timezone}"
            raise ValueError(msg)

    def duration_hours(self) -> float:
        """Calculate duration in hours."""
        delta = self.end - self.start
        return delta.total_seconds() / 3600

    def overlaps_with(self, other: "TimeRange") -> bool:
        """Check if this time range overlaps with another."""
        # Convert both ranges to UTC for comparison
        self_start_utc = self.start.astimezone(zoneinfo.ZoneInfo("UTC"))
        self_end_utc = self.end.astimezone(zoneinfo.ZoneInfo("UTC"))
        other_start_utc = other.start.astimezone(zoneinfo.ZoneInfo("UTC"))
        other_end_utc = other.end.astimezone(zoneinfo.ZoneInfo("UTC"))

        return self_start_utc < other_end_utc and self_end_utc > other_start_utc

    def contains(self, moment: datetime) -> bool:
        """Check if a specific moment is within this range."""
        moment_utc = moment.astimezone(zoneinfo.ZoneInfo("UTC"))
        start_utc = self.start.astimezone(zoneinfo.ZoneInfo("UTC"))
        end_utc = self.end.astimezone(zoneinfo.ZoneInfo("UTC"))

        return start_utc <= moment_utc < end_utc

    def to_timezone(self, target_timezone: str) -> "TimeRange":
        """Convert to different timezone."""
        try:
            target_tz = zoneinfo.ZoneInfo(target_timezone)
        except zoneinfo.ZoneInfoNotFoundError:
            msg = f"Invalid target timezone: {target_timezone}"
            raise ValueError(msg)

        new_start = self.start.astimezone(target_tz)
        new_end = self.end.astimezone(target_tz)

        return TimeRange(new_start, new_end, target_timezone)


@dataclass(frozen=True)
class DateRange:
    """Date range for scheduling periods."""

    start: date
    end: date

    def __post_init__(self):
        if self.start >= self.end:
            msg = "Start date must be before end date"
            raise ValueError(msg)

    def contains(self, check_date: date) -> bool:
        """Check if date is within this range."""
        return self.start <= check_date <= self.end

    def duration_days(self) -> int:
        """Calculate duration in days."""
        return (self.end - self.start).days

    @classmethod
    def current_year(cls) -> "DateRange":
        """Create date range for current year."""
        today = date.today()
        return cls(start=date(today.year, 1, 1), end=date(today.year, 12, 31))


class ShiftType(Enum):
    """Enumeration of all supported shift types.

    Based on Phase 1 analysis of SHIFT_SCHEDULING_SPEC.md requirements.
    """

    INCIDENTS = "incidents"
    INCIDENTS_STANDBY = "incidents_standby"
    WAAKDIENST = "waakdienst"
    CHANGES = "changes"
    PROJECTS = "projects"

    @property
    def requires_business_hours(self) -> bool:
        """Whether this shift type uses business hours."""
        return self in [self.INCIDENTS, self.INCIDENTS_STANDBY]

    @property
    def supports_partial_assignment(self) -> bool:
        """Whether this shift type supports partial day assignments."""
        return self in [self.INCIDENTS, self.INCIDENTS_STANDBY]

    @property
    def fairness_weight(self) -> float:
        """Base fairness weight for this shift type."""
        weights = {
            self.INCIDENTS: 1.0,
            self.INCIDENTS_STANDBY: 0.8,
            self.WAAKDIENST: 1.2,  # Higher weight for on-call
            self.CHANGES: 0.6,
            self.PROJECTS: 0.4,
        }
        return weights[self]

    @property
    def is_primary_coverage(self) -> bool:
        """Whether this shift type provides primary coverage."""
        return self in [self.INCIDENTS, self.WAAKDIENST]


@dataclass(frozen=True)
class BusinessHoursConfiguration:
    """Flexible business hours configuration per team.

    Addresses Phase 1 critical gap: configurable business hours.
    """

    monday_start: int | None = 8
    monday_end: int | None = 17
    tuesday_start: int | None = 8
    tuesday_end: int | None = 17
    wednesday_start: int | None = 8
    wednesday_end: int | None = 17
    thursday_start: int | None = 8
    thursday_end: int | None = 17
    friday_start: int | None = 8
    friday_end: int | None = 17
    saturday_start: int | None = None  # No work by default
    saturday_end: int | None = None
    sunday_start: int | None = None  # No work by default
    sunday_end: int | None = None

    def __post_init__(self):
        # Validate hour ranges
        for day in [
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
        ]:
            start = getattr(self, f"{day}_start")
            end = getattr(self, f"{day}_end")

            if start is not None and (start < 0 or start > 23):
                msg = f"{day}_start must be between 0 and 23"
                raise ValueError(msg)
            if end is not None and (end < 0 or end > 23):
                msg = f"{day}_end must be between 0 and 23"
                raise ValueError(msg)
            if start is not None and end is not None and start >= end:
                msg = f"{day}_start must be before {day}_end"
                raise ValueError(msg)

    def get_business_hours_for_day(self, day_of_week: int) -> tuple[int, int] | None:
        """Get business hours for specific day (0=Monday, 6=Sunday)."""
        day_mapping = {
            0: (self.monday_start, self.monday_end),
            1: (self.tuesday_start, self.tuesday_end),
            2: (self.wednesday_start, self.wednesday_end),
            3: (self.thursday_start, self.thursday_end),
            4: (self.friday_start, self.friday_end),
            5: (self.saturday_start, self.saturday_end),
            6: (self.sunday_start, self.sunday_end),
        }

        if day_of_week < 0 or day_of_week > 6:
            msg = "day_of_week must be between 0 and 6"
            raise ValueError(msg)

        start, end = day_mapping[day_of_week]
        if start is None or end is None:
            return None

        return (start, end)

    def is_business_day(self, day_of_week: int) -> bool:
        """Check if day is a business day."""
        return self.get_business_hours_for_day(day_of_week) is not None


@dataclass(frozen=True)
class TeamConfiguration:
    """Team-specific configuration for scheduling.

    Addresses Phase 1 critical gaps: timezone support, configurable business hours,
    and yearly fairness calculation.
    """

    # Timezone configuration
    timezone: str  # e.g., 'Europe/Amsterdam'

    # Business hours configuration
    business_hours: BusinessHoursConfiguration

    # Waakdienst configuration
    waakdienst_start_day: int  # 0-6, default 2 (Wednesday)
    waakdienst_start_hour: int  # 0-23, default 17
    waakdienst_end_hour: int  # 0-23, default 8

    # Holiday configuration
    skip_incidents_on_holidays: bool
    holiday_calendar: str  # ISO country code or custom calendar

    # Constraint configuration
    max_consecutive_weeks: int = 2
    min_rest_hours: int = 48

    # Fairness configuration - addresses Phase 1 gap
    fairness_period_days: int = 365  # Yearly fairness calculation
    fairness_lookback_days: int = 180  # Historical context

    def __post_init__(self):
        # Validate timezone
        try:
            zoneinfo.ZoneInfo(self.timezone)
        except zoneinfo.ZoneInfoNotFoundError:
            msg = f"Invalid timezone: {self.timezone}"
            raise ValueError(msg)

        # Validate waakdienst configuration
        if not (0 <= self.waakdienst_start_day <= 6):
            msg = "waakdienst_start_day must be between 0 and 6"
            raise ValueError(msg)
        if not (0 <= self.waakdienst_start_hour <= 23):
            msg = "waakdienst_start_hour must be between 0 and 23"
            raise ValueError(msg)
        if not (0 <= self.waakdienst_end_hour <= 23):
            msg = "waakdienst_end_hour must be between 0 and 23"
            raise ValueError(msg)

        # Validate constraint values
        if self.max_consecutive_weeks < 1:
            msg = "max_consecutive_weeks must be at least 1"
            raise ValueError(msg)
        if self.min_rest_hours < 0:
            msg = "min_rest_hours must be non-negative"
            raise ValueError(msg)

        # Validate fairness configuration
        if self.fairness_period_days < 1:
            msg = "fairness_period_days must be at least 1"
            raise ValueError(msg)
        if self.fairness_lookback_days < 1:
            msg = "fairness_lookback_days must be at least 1"
            raise ValueError(msg)

    def get_business_hours_range(self, check_date: date) -> TimeRange | None:
        """Get business hours for a specific date."""
        day_of_week = check_date.weekday()
        business_hours = self.business_hours.get_business_hours_for_day(day_of_week)

        if not business_hours:
            return None

        start_hour, end_hour = business_hours
        tz = zoneinfo.ZoneInfo(self.timezone)

        start_datetime = datetime.combine(
            check_date, datetime.min.time().replace(hour=start_hour),
        )
        end_datetime = datetime.combine(
            check_date, datetime.min.time().replace(hour=end_hour),
        )

        start_datetime = start_datetime.replace(tzinfo=tz)
        end_datetime = end_datetime.replace(tzinfo=tz)

        return TimeRange(start_datetime, end_datetime, self.timezone)

    def get_waakdienst_week_range(self, week_start: date) -> TimeRange:
        """Get waakdienst week range (Wed 17:00 - Wed 08:00)."""
        tz = zoneinfo.ZoneInfo(self.timezone)

        # Find the Wednesday of this week
        days_since_monday = week_start.weekday()
        days_to_wednesday = (self.waakdienst_start_day - days_since_monday) % 7
        wednesday = week_start + timedelta(days=days_to_wednesday)

        # Start: Wednesday at start_hour
        start_datetime = datetime.combine(
            wednesday, datetime.min.time().replace(hour=self.waakdienst_start_hour),
        ).replace(tzinfo=tz)

        # End: Next Wednesday at end_hour
        next_wednesday = wednesday + timedelta(days=7)
        end_datetime = datetime.combine(
            next_wednesday, datetime.min.time().replace(hour=self.waakdienst_end_hour),
        ).replace(tzinfo=tz)

        return TimeRange(start_datetime, end_datetime, self.timezone)

    def is_holiday(self, check_date: date) -> bool:
        """Check if date is a holiday for this team."""
        # Placeholder implementation - would integrate with holiday calendar library
        # For now, just check for weekends if no business hours
        day_of_week = check_date.weekday()
        return not self.business_hours.is_business_day(day_of_week)


class AssignmentStatus(Enum):
    """Status of an assignment."""

    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class ConflictSeverity(Enum):
    """Severity levels for assignment conflicts."""

    BLOCKING = "blocking"  # Must be resolved before assignment
    WARNING = "warning"  # Should be reviewed but can proceed
    INFO = "info"  # Informational only


class ConstraintViolation(Enum):
    """Types of constraint violations."""

    EMPLOYEE_UNAVAILABLE = "employee_unavailable"
    TIMEZONE_MISMATCH = "timezone_mismatch"
    OUTSIDE_BUSINESS_HOURS = "outside_business_hours"
    REST_PERIOD_VIOLATION = "rest_period_violation"
    CONSECUTIVE_WEEKS_EXCEEDED = "consecutive_weeks_exceeded"
    LEAVE_CONFLICT = "leave_conflict"
    RECURRING_PATTERN_CONFLICT = "recurring_pattern_conflict"


@dataclass(frozen=True)
class FairnessScore:
    """Fairness score for an employee."""

    incidents_score: float
    incidents_standby_score: float
    waakdienst_score: float
    total_score: float
    period: DateRange

    def __post_init__(self):
        if self.total_score < 0:
            msg = "Total score cannot be negative"
            raise ValueError(msg)


@dataclass(frozen=True)
class AssignmentLoad:
    """Assignment load for an employee in a period."""

    incidents_hours: float
    incidents_standby_hours: float
    waakdienst_hours: float
    total_hours: float
    period: DateRange

    def __post_init__(self):
        expected_total = (
            self.incidents_hours + self.incidents_standby_hours + self.waakdienst_hours
        )
        if (
            abs(self.total_hours - expected_total) > 0.01
        ):  # Allow for floating point precision
            msg = "Total hours must equal sum of individual shift type hours"
            raise ValueError(
                msg,
            )
