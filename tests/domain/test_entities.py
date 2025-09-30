"""
Comprehensive tests for domain layer entities.

Tests all business logic, constraint validation, and entity behavior
as defined in the Phase 2 clean architecture design.
"""

import zoneinfo
from datetime import date
from datetime import datetime
from datetime import timedelta

import pytest

from domain.entities import Assignment
from domain.entities import Employee
from domain.entities import LeaveRequest
from domain.entities import RecurringLeavePattern
from domain.entities import Shift
from domain.value_objects import AssignmentId
from domain.value_objects import AssignmentStatus
from domain.value_objects import EmployeeId
from domain.value_objects import ShiftId
from domain.value_objects import ShiftType
from domain.value_objects import TeamId
from domain.value_objects import TimeRange
from domain.value_objects import UserId


class TestLeaveRequest:
    """Test leave request entity."""

    def test_vacation_blocks_all_shifts(self):
        """Test that vacation leave blocks all shifts."""
        leave = LeaveRequest(
            id=1,
            employee_id=EmployeeId(123),
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 5),
            leave_type="vacation",
            status="approved",
            coverage_type="full_day",
        )

        tz = zoneinfo.ZoneInfo("Europe/Amsterdam")

        # Daytime shift during leave
        daytime_shift = TimeRange(
            datetime(2024, 1, 2, 9, 0, tzinfo=tz),
            datetime(2024, 1, 2, 17, 0, tzinfo=tz),
            "Europe/Amsterdam",
        )

        # Night shift during leave
        night_shift = TimeRange(
            datetime(2024, 1, 2, 18, 0, tzinfo=tz),
            datetime(2024, 1, 3, 6, 0, tzinfo=tz),
            "Europe/Amsterdam",
        )

        assert leave.conflicts_with_time_range(daytime_shift)
        assert leave.conflicts_with_time_range(night_shift)

    def test_leave_blocks_only_daytime(self):
        """Test that 'leave' type blocks only daytime shifts."""
        leave = LeaveRequest(
            id=1,
            employee_id=EmployeeId(123),
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 5),
            leave_type="leave",
            status="approved",
            coverage_type="full_day",
        )

        tz = zoneinfo.ZoneInfo("Europe/Amsterdam")

        # Daytime shift (should conflict)
        daytime_shift = TimeRange(
            datetime(2024, 1, 2, 9, 0, tzinfo=tz),
            datetime(2024, 1, 2, 17, 0, tzinfo=tz),
            "Europe/Amsterdam",
        )

        # Night shift (should not conflict)
        night_shift = TimeRange(
            datetime(2024, 1, 2, 18, 0, tzinfo=tz),
            datetime(2024, 1, 3, 6, 0, tzinfo=tz),
            "Europe/Amsterdam",
        )

        assert leave.conflicts_with_time_range(daytime_shift)
        assert not leave.conflicts_with_time_range(night_shift)

    def test_training_blocks_no_shifts(self):
        """Test that training leave blocks no shifts."""
        leave = LeaveRequest(
            id=1,
            employee_id=EmployeeId(123),
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 5),
            leave_type="training",
            status="approved",
            coverage_type="full_day",
        )

        tz = zoneinfo.ZoneInfo("Europe/Amsterdam")
        shift = TimeRange(
            datetime(2024, 1, 2, 9, 0, tzinfo=tz),
            datetime(2024, 1, 2, 17, 0, tzinfo=tz),
            "Europe/Amsterdam",
        )

        assert not leave.conflicts_with_time_range(shift)

    def test_pending_leave_no_conflict(self):
        """Test that pending leave requests don't create conflicts."""
        leave = LeaveRequest(
            id=1,
            employee_id=EmployeeId(123),
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 5),
            leave_type="vacation",
            status="pending",  # Not approved
            coverage_type="full_day",
        )

        tz = zoneinfo.ZoneInfo("Europe/Amsterdam")
        shift = TimeRange(
            datetime(2024, 1, 2, 9, 0, tzinfo=tz),
            datetime(2024, 1, 2, 17, 0, tzinfo=tz),
            "Europe/Amsterdam",
        )

        assert not leave.conflicts_with_time_range(shift)


class TestRecurringLeavePattern:
    """Test recurring leave pattern entity."""

    def test_weekly_pattern_conflict(self):
        """Test weekly recurring pattern conflicts."""
        pattern = RecurringLeavePattern(
            id=1,
            employee_id=EmployeeId(123),
            pattern_type="weekly",
            day_of_week=0,  # Monday
            coverage_type="full_day",
            start_date=date(2024, 1, 1),
        )

        tz = zoneinfo.ZoneInfo("Europe/Amsterdam")

        # Monday shift (should conflict)
        monday_shift = TimeRange(
            datetime(2024, 1, 8, 9, 0, tzinfo=tz),  # A Monday
            datetime(2024, 1, 8, 17, 0, tzinfo=tz),
            "Europe/Amsterdam",
        )

        # Tuesday shift (should not conflict)
        tuesday_shift = TimeRange(
            datetime(2024, 1, 9, 9, 0, tzinfo=tz),  # A Tuesday
            datetime(2024, 1, 9, 17, 0, tzinfo=tz),
            "Europe/Amsterdam",
        )

        # Verify the dates are actually Monday and Tuesday
        if monday_shift.start.weekday() == 0:  # Monday
            assert pattern.conflicts_with_time_range(monday_shift)
        if tuesday_shift.start.weekday() == 1:  # Tuesday
            assert not pattern.conflicts_with_time_range(tuesday_shift)

    def test_biweekly_pattern_conflict(self):
        """Test biweekly recurring pattern conflicts."""
        start_date = date(2024, 1, 1)  # Monday
        pattern = RecurringLeavePattern(
            id=1,
            employee_id=EmployeeId(123),
            pattern_type="biweekly",
            day_of_week=0,  # Monday
            coverage_type="full_day",
            start_date=start_date,
        )

        tz = zoneinfo.ZoneInfo("Europe/Amsterdam")

        # First Monday (week 0 - should conflict)
        first_monday = TimeRange(
            datetime.combine(
                start_date, datetime.min.time().replace(hour=9, tzinfo=tz),
            ),
            datetime.combine(
                start_date, datetime.min.time().replace(hour=17, tzinfo=tz),
            ),
            "Europe/Amsterdam",
        )

        # Second Monday (week 1 - should not conflict)
        second_monday = TimeRange(
            datetime.combine(
                start_date + timedelta(weeks=1),
                datetime.min.time().replace(hour=9, tzinfo=tz),
            ),
            datetime.combine(
                start_date + timedelta(weeks=1),
                datetime.min.time().replace(hour=17, tzinfo=tz),
            ),
            "Europe/Amsterdam",
        )

        # Third Monday (week 2 - should conflict again)
        third_monday = TimeRange(
            datetime.combine(
                start_date + timedelta(weeks=2),
                datetime.min.time().replace(hour=9, tzinfo=tz),
            ),
            datetime.combine(
                start_date + timedelta(weeks=2),
                datetime.min.time().replace(hour=17, tzinfo=tz),
            ),
            "Europe/Amsterdam",
        )

        assert pattern.conflicts_with_time_range(first_monday)
        assert not pattern.conflicts_with_time_range(second_monday)
        assert pattern.conflicts_with_time_range(third_monday)

    def test_morning_coverage_type(self):
        """Test morning coverage type conflicts."""
        pattern = RecurringLeavePattern(
            id=1,
            employee_id=EmployeeId(123),
            pattern_type="weekly",
            day_of_week=0,  # Monday
            coverage_type="morning",
            start_date=date(2024, 1, 1),
        )

        tz = zoneinfo.ZoneInfo("Europe/Amsterdam")

        # Morning shift (should conflict)
        morning_shift = TimeRange(
            datetime(2024, 1, 8, 9, 0, tzinfo=tz),  # 9 AM
            datetime(2024, 1, 8, 12, 0, tzinfo=tz),
            "Europe/Amsterdam",
        )

        # Afternoon shift (should not conflict)
        afternoon_shift = TimeRange(
            datetime(2024, 1, 8, 13, 0, tzinfo=tz),  # 1 PM
            datetime(2024, 1, 8, 17, 0, tzinfo=tz),
            "Europe/Amsterdam",
        )

        if morning_shift.start.weekday() == 0:  # Ensure it's Monday
            assert pattern.conflicts_with_time_range(morning_shift)
            assert not pattern.conflicts_with_time_range(afternoon_shift)


class TestEmployee:
    """Test employee entity and business logic."""

    def create_test_employee(self) -> Employee:
        """Create a test employee with default settings."""
        return Employee(
            id=EmployeeId(123),
            name="John Doe",
            email="john@example.com",
            team_id=TeamId(1),
            hire_date=date(2023, 1, 1),
            available_for_incidents=True,
            available_for_waakdienst=True,
            max_consecutive_weeks=2,
            min_rest_hours=48,
        )

    def test_employee_availability_for_incidents(self):
        """Test employee availability checking for incidents."""
        employee = self.create_test_employee()

        tz = zoneinfo.ZoneInfo("Europe/Amsterdam")
        time_range = TimeRange(
            datetime(2024, 1, 1, 9, 0, tzinfo=tz),
            datetime(2024, 1, 1, 17, 0, tzinfo=tz),
            "Europe/Amsterdam",
        )

        assert employee.is_available_for_shift(ShiftType.INCIDENTS, time_range)

        # Test unavailable employee
        employee.available_for_incidents = False
        assert not employee.is_available_for_shift(ShiftType.INCIDENTS, time_range)

    def test_employee_availability_for_waakdienst(self):
        """Test employee availability checking for waakdienst."""
        employee = self.create_test_employee()

        tz = zoneinfo.ZoneInfo("Europe/Amsterdam")
        time_range = TimeRange(
            datetime(2024, 1, 1, 18, 0, tzinfo=tz),
            datetime(2024, 1, 2, 6, 0, tzinfo=tz),
            "Europe/Amsterdam",
        )

        assert employee.is_available_for_shift(ShiftType.WAAKDIENST, time_range)

        # Test unavailable employee
        employee.available_for_waakdienst = False
        assert not employee.is_available_for_shift(ShiftType.WAAKDIENST, time_range)

    def test_terminated_employee_unavailable(self):
        """Test that terminated employees are not available."""
        employee = self.create_test_employee()
        employee.termination_date = date(2024, 1, 1)

        tz = zoneinfo.ZoneInfo("Europe/Amsterdam")
        time_range = TimeRange(
            datetime(2024, 1, 2, 9, 0, tzinfo=tz),  # After termination
            datetime(2024, 1, 2, 17, 0, tzinfo=tz),
            "Europe/Amsterdam",
        )

        assert not employee.is_available_for_shift(ShiftType.INCIDENTS, time_range)

    def test_leave_request_blocks_availability(self):
        """Test that approved leave requests block availability."""
        employee = self.create_test_employee()

        # Add vacation leave
        leave = LeaveRequest(
            id=1,
            employee_id=employee.id,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 5),
            leave_type="vacation",
            status="approved",
            coverage_type="full_day",
        )
        employee.leave_requests.append(leave)

        tz = zoneinfo.ZoneInfo("Europe/Amsterdam")
        time_range = TimeRange(
            datetime(2024, 1, 2, 9, 0, tzinfo=tz),  # During leave
            datetime(2024, 1, 2, 17, 0, tzinfo=tz),
            "Europe/Amsterdam",
        )

        assert not employee.is_available_for_shift(ShiftType.INCIDENTS, time_range)

    def test_recurring_pattern_blocks_availability(self):
        """Test that recurring patterns block availability."""
        employee = self.create_test_employee()

        # Add weekly Monday pattern
        pattern = RecurringLeavePattern(
            id=1,
            employee_id=employee.id,
            pattern_type="weekly",
            day_of_week=0,  # Monday
            coverage_type="full_day",
            start_date=date(2024, 1, 1),
        )
        employee.recurring_patterns.append(pattern)

        tz = zoneinfo.ZoneInfo("Europe/Amsterdam")

        # Monday shift (should be blocked)
        monday_shift = TimeRange(
            datetime(2024, 1, 8, 9, 0, tzinfo=tz),  # A Monday
            datetime(2024, 1, 8, 17, 0, tzinfo=tz),
            "Europe/Amsterdam",
        )

        if monday_shift.start.weekday() == 0:  # Ensure it's Monday
            assert not employee.is_available_for_shift(
                ShiftType.INCIDENTS, monday_shift,
            )


class TestShift:
    """Test shift entity and business logic."""

    def create_test_shift(self) -> Shift:
        """Create a test shift."""
        tz = zoneinfo.ZoneInfo("Europe/Amsterdam")
        time_range = TimeRange(
            datetime(2024, 1, 1, 9, 0, tzinfo=tz),
            datetime(2024, 1, 1, 17, 0, tzinfo=tz),
            "Europe/Amsterdam",
        )

        return Shift(
            id=ShiftId(1),
            shift_type=ShiftType.INCIDENTS,
            time_range=time_range,
            team_id=TeamId(1),
        )

    def create_test_employee(self) -> Employee:
        """Create a test employee."""
        return Employee(
            id=EmployeeId(123),
            name="John Doe",
            email="john@example.com",
            team_id=TeamId(1),
            hire_date=date(2023, 1, 1),
            available_for_incidents=True,
            available_for_waakdienst=True,
        )

    def test_assign_to_available_employee(self):
        """Test assigning shift to available employee."""
        shift = self.create_test_shift()
        employee = self.create_test_employee()

        assignment = shift.assign_to(employee)

        assert assignment.employee_id == employee.id
        assert assignment.shift_id == shift.id
        assert assignment.auto_assigned
        assert shift.assigned_employee == employee.id
        assert shift.assignment_status == AssignmentStatus.CONFIRMED

    def test_assign_to_unavailable_employee_fails(self):
        """Test that assigning to unavailable employee raises error."""
        shift = self.create_test_shift()
        employee = self.create_test_employee()
        employee.available_for_incidents = False  # Make unavailable

        with pytest.raises(ValueError, match="not available for this shift"):
            shift.assign_to(employee)

    def test_shift_compatibility_check(self):
        """Test shift compatibility checking."""
        shift = self.create_test_shift()

        # Available employee
        available_employee = self.create_test_employee()
        assert shift.is_compatible_with(available_employee)

        # Unavailable employee
        unavailable_employee = self.create_test_employee()
        unavailable_employee.available_for_incidents = False
        assert not shift.is_compatible_with(unavailable_employee)

    def test_fairness_weight_calculation(self):
        """Test fairness weight calculation for shifts."""
        tz = zoneinfo.ZoneInfo("Europe/Amsterdam")

        # Standard incidents shift (day, 9 hours)
        day_shift = Shift(
            id=ShiftId(1),
            shift_type=ShiftType.INCIDENTS,
            time_range=TimeRange(
                datetime(2024, 1, 1, 9, 0, tzinfo=tz),
                datetime(2024, 1, 1, 18, 0, tzinfo=tz),
                "Europe/Amsterdam",
            ),
            team_id=TeamId(1),
        )

        # Night waakdienst shift
        night_shift = Shift(
            id=ShiftId(2),
            shift_type=ShiftType.WAAKDIENST,
            time_range=TimeRange(
                datetime(2024, 1, 1, 18, 0, tzinfo=tz),
                datetime(2024, 1, 2, 6, 0, tzinfo=tz),
                "Europe/Amsterdam",
            ),
            team_id=TeamId(1),
        )

        day_weight = day_shift.calculate_fairness_weight()
        night_weight = night_shift.calculate_fairness_weight()

        # Night shift should have higher weight due to:
        # 1. Higher base weight for waakdienst (1.2 vs 1.0)
        # 2. Night time multiplier
        assert night_weight > day_weight


class TestAssignment:
    """Test assignment entity."""

    def create_test_assignment(self) -> Assignment:
        """Create a test assignment."""
        tz = zoneinfo.ZoneInfo("Europe/Amsterdam")
        time_range = TimeRange(
            datetime(2024, 1, 1, 9, 0, tzinfo=tz),
            datetime(2024, 1, 1, 17, 0, tzinfo=tz),
            "Europe/Amsterdam",
        )

        shift = Shift(
            id=ShiftId(1),
            shift_type=ShiftType.INCIDENTS,
            time_range=time_range,
            team_id=TeamId(1),
        )

        return Assignment(
            id=AssignmentId(1),
            employee_id=EmployeeId(123),
            shift_id=shift.id,
            assigned_at=datetime.utcnow(),
            assigned_by=UserId(1),
            auto_assigned=True,
            status=AssignmentStatus.CONFIRMED,
            conflicts=[],
            shift=shift,
        )

    def test_assignment_validation_with_shift(self):
        """Test assignment validation when shift is present."""
        assignment = self.create_test_assignment()
        result = assignment.validate()

        assert result.is_valid
        assert len(result.violations) == 0

    def test_assignment_validation_without_shift(self):
        """Test assignment validation when shift is missing."""
        assignment = self.create_test_assignment()
        assignment.shift = None  # Remove shift reference

        result = assignment.validate()

        assert not result.is_valid
        assert "No shift associated with assignment" in result.violations

    def test_assignment_impact_calculation(self):
        """Test assignment impact calculation."""
        assignment = self.create_test_assignment()
        other_assignments = []  # Empty list for simplicity

        impact = assignment.calculate_impact(other_assignments)

        # Should return valid impact object
        assert impact.conflict_count == 0  # No conflicts in assignment
        assert isinstance(impact.fairness_impact, float)
        assert isinstance(impact.affected_employees, list)
