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

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Set, TYPE_CHECKING
from datetime import datetime, date
from dataclasses import dataclass

# Import at runtime for dataclass fields
from domain.entities import Employee, Shift, Assignment
from domain.value_objects import TimeRange, ShiftType, EmployeeId, ShiftId


@dataclass
class EmployeeQuery:
    """Query object for employee filtering."""
    active_only: bool = True
    department_ids: Optional[List[str]] = None
    role_ids: Optional[List[str]] = None
    available_during: Optional[TimeRange] = None
    has_skills: Optional[List[str]] = None
    exclude_ids: Optional[List[EmployeeId]] = None


@dataclass
class ShiftQuery:
    """Query object for shift filtering."""
    date_range: Optional[TimeRange] = None
    departments: Optional[List[str]] = None
    shift_types: Optional[List[ShiftType]] = None
    status: Optional[str] = None  # 'assigned', 'unassigned', 'pending'
    assigned_to: Optional[List[EmployeeId]] = None
    requires_skills: Optional[List[str]] = None


@dataclass
class AssignmentQuery:
    """Query object for assignment filtering."""
    employee_id: Optional[EmployeeId] = None
    shift_id: Optional[ShiftId] = None
    date_range: Optional[TimeRange] = None
    status: Optional[str] = None  # 'active', 'tentative', 'cancelled'
    departments: Optional[List[str]] = None


class EmployeeRepository(ABC):
    """Repository for employee aggregate operations."""
    
    @abstractmethod
    async def find_by_id(self, employee_id: EmployeeId) -> Optional[Employee]:
        """Find employee by ID."""
        pass
    
    @abstractmethod
    async def find_all(self, query: Optional[EmployeeQuery] = None) -> List[Employee]:
        """Find employees matching query criteria."""
        pass
    
    @abstractmethod
    async def find_available_for_shift(
        self, 
        shift_time: TimeRange,
        required_skills: List[str],
        exclude_employees: Optional[List[EmployeeId]] = None
    ) -> List[Employee]:
        """Find employees available for a specific shift."""
        pass
    
    @abstractmethod
    async def get_employee_assignments_count(
        self, 
        employee_id: EmployeeId,
        date_range: TimeRange
    ) -> int:
        """Get count of assignments for employee in date range."""
        pass
    
    @abstractmethod
    async def get_employees_by_department(self, department_id: str) -> List[Employee]:
        """Get all employees in a department."""
        pass
    
    @abstractmethod
    async def save(self, employee: Employee) -> None:
        """Save or update employee."""
        pass
    
    @abstractmethod
    async def delete(self, employee_id: EmployeeId) -> None:
        """Delete employee."""
        pass


class ShiftRepository(ABC):
    """Repository for shift aggregate operations."""
    
    @abstractmethod
    async def find_by_id(self, shift_id: ShiftId) -> Optional[Shift]:
        """Find shift by ID."""
        pass
    
    @abstractmethod
    async def find_all(self, query: Optional[ShiftQuery] = None) -> List[Shift]:
        """Find shifts matching query criteria."""
        pass
    
    @abstractmethod
    async def find_unassigned_in_range(self, date_range: TimeRange) -> List[Shift]:
        """Find unassigned shifts in date range."""
        pass
    
    @abstractmethod
    async def find_conflicting_shifts(
        self, 
        employee_id: EmployeeId,
        time_range: TimeRange
    ) -> List[Shift]:
        """Find shifts that would conflict with employee assignment."""
        pass
    
    @abstractmethod
    async def find_by_department_and_date(
        self, 
        department_id: str,
        target_date: date
    ) -> List[Shift]:
        """Find shifts for department on specific date."""
        pass
    
    @abstractmethod
    async def get_shift_coverage_requirements(
        self, 
        date_range: TimeRange
    ) -> Dict[str, int]:
        """Get coverage requirements by shift type."""
        pass
    
    @abstractmethod
    async def save(self, shift: Shift) -> None:
        """Save or update shift."""
        pass
    
    @abstractmethod
    async def save_batch(self, shifts: List[Shift]) -> None:
        """Save multiple shifts in batch."""
        pass
    
    @abstractmethod
    async def delete(self, shift_id: ShiftId) -> None:
        """Delete shift."""
        pass


class AssignmentRepository(ABC):
    """Repository for assignment aggregate operations."""
    
    @abstractmethod
    async def find_by_id(self, assignment_id: str) -> Optional[Assignment]:
        """Find assignment by ID."""
        pass
    
    @abstractmethod
    async def find_all(self, query: Optional[AssignmentQuery] = None) -> List[Assignment]:
        """Find assignments matching query criteria."""
        pass
    
    @abstractmethod
    async def find_by_employee_and_date_range(
        self, 
        employee_id: EmployeeId,
        date_range: TimeRange
    ) -> List[Assignment]:
        """Find assignments for employee in date range."""
        pass
    
    @abstractmethod
    async def find_by_shift(self, shift_id: ShiftId) -> List[Assignment]:
        """Find all assignments for a shift."""
        pass
    
    @abstractmethod
    async def find_conflicting_assignments(
        self, 
        employee_id: EmployeeId,
        time_range: TimeRange
    ) -> List[Assignment]:
        """Find assignments that would conflict with new assignment."""
        pass
    
    @abstractmethod
    async def get_assignment_statistics(
        self, 
        employee_id: EmployeeId,
        date_range: TimeRange
    ) -> Dict[str, Any]:
        """Get assignment statistics for employee in date range."""
        pass
    
    @abstractmethod
    async def save(self, assignment: Assignment) -> None:
        """Save or update assignment."""
        pass
    
    @abstractmethod
    async def save_batch(self, assignments: List[Assignment]) -> None:
        """Save multiple assignments in batch."""
        pass
    
    @abstractmethod
    async def delete(self, assignment_id: str) -> None:
        """Delete assignment."""
        pass


class LeaveRequestRepository(ABC):
    """Repository for leave request operations."""
    
    @abstractmethod
    async def find_by_employee_and_date_range(
        self, 
        employee_id: EmployeeId,
        date_range: TimeRange
    ) -> List[Dict[str, Any]]:
        """Find leave requests for employee in date range."""
        pass
    
    @abstractmethod
    async def find_approved_leave_in_range(
        self, 
        date_range: TimeRange
    ) -> List[Dict[str, Any]]:
        """Find all approved leave requests in date range."""
        pass
    
    @abstractmethod
    async def is_employee_on_leave(
        self, 
        employee_id: EmployeeId,
        time_range: TimeRange
    ) -> bool:
        """Check if employee has approved leave during time range."""
        pass


class UnitOfWork(ABC):
    """Unit of Work pattern for managing transactions."""
    
    def __init__(self):
        self.employees: Optional['EmployeeRepository'] = None
        self.shifts: Optional['ShiftRepository'] = None
        self.assignments: Optional['AssignmentRepository'] = None
        self.leave_requests: Optional['LeaveRequestRepository'] = None
    
    @abstractmethod
    async def __aenter__(self):
        """Enter async context manager."""
        pass
    
    @abstractmethod
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context manager."""
        pass
    
    @abstractmethod
    async def commit(self) -> None:
        """Commit transaction."""
        pass
    
    @abstractmethod
    async def rollback(self) -> None:
        """Rollback transaction."""
        pass


# Export all repository interfaces
__all__ = [
    'EmployeeQuery',
    'ShiftQuery', 
    'AssignmentQuery',
    'EmployeeRepository',
    'ShiftRepository',
    'AssignmentRepository',
    'LeaveRequestRepository',
    'UnitOfWork'
]
