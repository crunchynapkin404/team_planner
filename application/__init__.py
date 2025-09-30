"""Application layer for the Team Planner orchestrator system.

The application layer orchestrates the execution of business use cases by:
1. Providing use case implementations that coordinate domain services
2. Implementing command/query handlers for external interfaces
3. Managing transaction boundaries through Unit of Work pattern
4. Handling application-specific concerns like validation and security

Key Components:
- Use Cases: OrchestrateScheduleUseCase, ResolveConflictsUseCase
- Command Handlers: CreateScheduleCommandHandler, AssignShiftCommandHandler
- Query Handlers: GetScheduleQueryHandler, GetFairnessReportQueryHandler
- Repository Interfaces: Define data access contracts for domain entities
"""

from .commands import AssignShiftCommand
from .commands import AssignShiftCommandHandler
from .commands import CommandError
from .commands import CommandResult
from .commands import CreateScheduleCommand
from .commands import CreateScheduleCommandHandler
from .commands import SwapAssignmentsCommand
from .commands import SwapAssignmentsCommandHandler
from .commands import UnassignShiftCommand
from .commands import UnassignShiftCommandHandler
from .queries import GetEmployeeAvailabilityQuery
from .queries import GetEmployeeAvailabilityQueryHandler
from .queries import GetFairnessReportQuery
from .queries import GetFairnessReportQueryHandler
from .queries import GetScheduleQuery
from .queries import GetScheduleQueryHandler
from .queries import GetUnassignedShiftsQuery
from .queries import GetUnassignedShiftsQueryHandler
from .queries import QueryError
from .queries import QueryResult
from .repositories import AssignmentQuery
from .repositories import AssignmentRepository
from .repositories import EmployeeQuery
from .repositories import EmployeeRepository
from .repositories import LeaveRequestRepository
from .repositories import ShiftQuery
from .repositories import ShiftRepository
from .repositories import UnitOfWork
from .use_cases import ConflictDetectedError
from .use_cases import ConstraintViolationError
from .use_cases import InsufficientCoverageError
from .use_cases import OrchestrateScheduleUseCase
from .use_cases import ResolveConflictsUseCase
from .use_cases import SchedulingError
from .use_cases import SchedulingRequest
from .use_cases import SchedulingResult

__all__ = [
    "AssignShiftCommand",
    "AssignShiftCommandHandler",
    "AssignmentQuery",
    "AssignmentRepository",
    "CommandError",
    "CommandResult",
    "ConflictDetectedError",
    "ConstraintViolationError",
    # Commands
    "CreateScheduleCommand",
    "CreateScheduleCommandHandler",
    "EmployeeQuery",
    # Repositories
    "EmployeeRepository",
    "GetEmployeeAvailabilityQuery",
    "GetEmployeeAvailabilityQueryHandler",
    "GetFairnessReportQuery",
    "GetFairnessReportQueryHandler",
    # Queries
    "GetScheduleQuery",
    "GetScheduleQueryHandler",
    "GetUnassignedShiftsQuery",
    "GetUnassignedShiftsQueryHandler",
    "InsufficientCoverageError",
    "LeaveRequestRepository",
    # Use Cases
    "OrchestrateScheduleUseCase",
    "QueryError",
    "QueryResult",
    "ResolveConflictsUseCase",
    "SchedulingError",
    "SchedulingRequest",
    "SchedulingResult",
    "ShiftQuery",
    "ShiftRepository",
    "SwapAssignmentsCommand",
    "SwapAssignmentsCommandHandler",
    "UnassignShiftCommand",
    "UnassignShiftCommandHandler",
    "UnitOfWork",
]
