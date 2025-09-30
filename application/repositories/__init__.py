"""Repository interfaces for the scheduling domain.

This module defines abstract repository interfaces that provide data access
operations for domain entities. The actual implementations will be in the
infrastructure layer, following the Clean Architecture pattern.

Key Design Principles:
1. Domain-centric interfaces (not data-centric)
2. Repository pattern for aggregate boundaries
3. Query object pattern for complex filtering
4. Unit of Work pattern for transaction management
"""

from abc import ABC
from abc import abstractmethod
from dataclasses import dataclass
from datetime import date
from datetime import datetime
from typing import TYPE_CHECKING
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Set

from domain.entities import Assignment

# Import at runtime for dataclass fields
from domain.entities import Employee
from domain.entities import Shift
from domain.value_objects import EmployeeId
from domain.value_objects import ShiftId
from domain.value_objects import ShiftType
from domain.value_objects import TimeRange


@dataclass
class EmployeeQuery:
    """Query object for employee filtering."""

    active_only: bool = True
    department_ids: list[str] | None = None
    role_ids: list[str] | None = None
    available_during: TimeRange | None = None
    has_skills: list[str] | None = None
    exclude_ids: list[EmployeeId] | None = None


@dataclass
class ShiftQuery:
    """Query object for shift filtering."""

    date_range: TimeRange | None = None
    departments: list[str] | None = None
    shift_types: list[ShiftType] | None = None
    status: str | None = None  # 'assigned', 'unassigned', 'pending'
    assigned_to: list[EmployeeId] | None = None
    requires_skills: list[str] | None = None


@dataclass
class AssignmentQuery:
    """Query object for assignment filtering."""

    employee_id: EmployeeId | None = None
    shift_id: ShiftId | None = None
    date_range: TimeRange | None = None
    status: str | None = None  # 'active', 'tentative', 'cancelled'
    departments: list[str] | None = None


class EmployeeRepository(ABC):
    """Repository for employee aggregate operations."""

    @abstractmethod
    async def find_by_id(self, employee_id: EmployeeId) -> Employee | None:
        """Find employee by ID."""

    @abstractmethod
    async def find_all(self, query: EmployeeQuery | None = None) -> list[Employee]:
        """Find employees matching query criteria."""

    @abstractmethod
    async def find_available_for_shift(
        self,
        shift_time: TimeRange,
        required_skills: list[str],
        exclude_employees: list[EmployeeId] | None = None,
    ) -> list[Employee]:
        """Find employees available for a specific shift."""

    @abstractmethod
    async def get_employee_assignments_count(
        self, employee_id: EmployeeId, date_range: TimeRange,
    ) -> int:
        """Get count of assignments for employee in date range."""

    @abstractmethod
    async def get_employees_by_department(self, department_id: str) -> list[Employee]:
        """Get all employees in a department."""

    @abstractmethod
    async def save(self, employee: Employee) -> None:
        """Save or update employee."""

    @abstractmethod
    async def delete(self, employee_id: EmployeeId) -> None:
        """Delete employee."""


class ShiftRepository(ABC):
    """Repository for shift aggregate operations."""

    @abstractmethod
    async def find_by_id(self, shift_id: ShiftId) -> Shift | None:
        """Find shift by ID."""

    @abstractmethod
    async def find_all(self, query: ShiftQuery | None = None) -> list[Shift]:
        """Find shifts matching query criteria."""

    @abstractmethod
    async def find_unassigned_in_range(self, date_range: TimeRange) -> list[Shift]:
        """Find unassigned shifts in date range."""

    @abstractmethod
    async def find_conflicting_shifts(
        self, employee_id: EmployeeId, time_range: TimeRange,
    ) -> list[Shift]:
        """Find shifts that would conflict with employee assignment."""

    @abstractmethod
    async def find_by_department_and_date(
        self, department_id: str, target_date: date,
    ) -> list[Shift]:
        """Find shifts for department on specific date."""

    @abstractmethod
    async def get_shift_coverage_requirements(
        self, date_range: TimeRange,
    ) -> dict[str, int]:
        """Get coverage requirements by shift type."""

    @abstractmethod
    async def save(self, shift: Shift) -> None:
        """Save or update shift."""

    @abstractmethod
    async def save_batch(self, shifts: list[Shift]) -> None:
        """Save multiple shifts in batch."""

    @abstractmethod
    async def delete(self, shift_id: ShiftId) -> None:
        """Delete shift."""


class AssignmentRepository(ABC):
    """Repository for assignment aggregate operations."""

    @abstractmethod
    async def find_by_id(self, assignment_id: str) -> Assignment | None:
        """Find assignment by ID."""

    @abstractmethod
    async def find_all(
        self, query: AssignmentQuery | None = None,
    ) -> list[Assignment]:
        """Find assignments matching query criteria."""

    @abstractmethod
    async def find_by_employee_and_date_range(
        self, employee_id: EmployeeId, date_range: TimeRange,
    ) -> list[Assignment]:
        """Find assignments for employee in date range."""

    @abstractmethod
    async def find_by_shift(self, shift_id: ShiftId) -> list[Assignment]:
        """Find all assignments for a shift."""

    @abstractmethod
    async def find_conflicting_assignments(
        self, employee_id: EmployeeId, time_range: TimeRange,
    ) -> list[Assignment]:
        """Find assignments that would conflict with new assignment."""

    @abstractmethod
    async def get_assignment_statistics(
        self, employee_id: EmployeeId, date_range: TimeRange,
    ) -> dict[str, Any]:
        """Get assignment statistics for employee in date range."""

    @abstractmethod
    async def save(self, assignment: Assignment) -> None:
        """Save or update assignment."""

    @abstractmethod
    async def save_batch(self, assignments: list[Assignment]) -> None:
        """Save multiple assignments in batch."""

    @abstractmethod
    async def delete(self, assignment_id: str) -> None:
        """Delete assignment."""


class LeaveRequestRepository(ABC):
    """Repository for leave request operations."""

    @abstractmethod
    async def find_by_employee_and_date_range(
        self, employee_id: EmployeeId, date_range: TimeRange,
    ) -> list[dict[str, Any]]:
        """Find leave requests for employee in date range."""

    @abstractmethod
    async def find_approved_leave_in_range(
        self, date_range: TimeRange,
    ) -> list[dict[str, Any]]:
        """Find all approved leave requests in date range."""

    @abstractmethod
    async def is_employee_on_leave(
        self, employee_id: EmployeeId, time_range: TimeRange,
    ) -> bool:
        """Check if employee has approved leave during time range."""


class UnitOfWork(ABC):
    """Unit of Work pattern for managing transactions."""

    def __init__(self):
        self.employees: EmployeeRepository | None = None
        self.shifts: ShiftRepository | None = None
        self.assignments: AssignmentRepository | None = None
        self.leave_requests: LeaveRequestRepository | None = None

    @abstractmethod
    async def __aenter__(self):
        """Enter async context manager."""

    @abstractmethod
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context manager."""

    @abstractmethod
    async def commit(self) -> None:
        """Commit transaction."""

    @abstractmethod
    async def rollback(self) -> None:
        """Rollback transaction."""


# Export all repository interfaces
__all__ = [
    "AssignmentQuery",
    "AssignmentRepository",
    "EmployeeQuery",
    "EmployeeRepository",
    "LeaveRequestRepository",
    "ShiftQuery",
    "ShiftRepository",
    "UnitOfWork",
]
