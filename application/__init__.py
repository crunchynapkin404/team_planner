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

from .use_cases import (
    OrchestrateScheduleUseCase,
    ResolveConflictsUseCase,
    SchedulingRequest,
    SchedulingResult,
    SchedulingError,
    InsufficientCoverageError,
    ConflictDetectedError,
    ConstraintViolationError
)

from .commands import (
    CreateScheduleCommand,
    AssignShiftCommand,
    UnassignShiftCommand,
    SwapAssignmentsCommand,
    CreateScheduleCommandHandler,
    AssignShiftCommandHandler,
    UnassignShiftCommandHandler,
    SwapAssignmentsCommandHandler,
    CommandResult,
    CommandError
)

from .queries import (
    GetScheduleQuery,
    GetEmployeeAvailabilityQuery,
    GetUnassignedShiftsQuery,
    GetFairnessReportQuery,
    GetScheduleQueryHandler,
    GetEmployeeAvailabilityQueryHandler,
    GetUnassignedShiftsQueryHandler,
    GetFairnessReportQueryHandler,
    QueryResult,
    QueryError
)

from .repositories import (
    EmployeeRepository,
    ShiftRepository,
    AssignmentRepository,
    LeaveRequestRepository,
    UnitOfWork,
    EmployeeQuery,
    ShiftQuery,
    AssignmentQuery
)


__all__ = [
    # Use Cases
    'OrchestrateScheduleUseCase',
    'ResolveConflictsUseCase',
    'SchedulingRequest',
    'SchedulingResult',
    'SchedulingError',
    'InsufficientCoverageError',
    'ConflictDetectedError',
    'ConstraintViolationError',
    
    # Commands
    'CreateScheduleCommand',
    'AssignShiftCommand',
    'UnassignShiftCommand',
    'SwapAssignmentsCommand',
    'CreateScheduleCommandHandler',
    'AssignShiftCommandHandler',
    'UnassignShiftCommandHandler',
    'SwapAssignmentsCommandHandler',
    'CommandResult',
    'CommandError',
    
    # Queries
    'GetScheduleQuery',
    'GetEmployeeAvailabilityQuery',
    'GetUnassignedShiftsQuery',
    'GetFairnessReportQuery',
    'GetScheduleQueryHandler',
    'GetEmployeeAvailabilityQueryHandler',
    'GetUnassignedShiftsQueryHandler',
    'GetFairnessReportQueryHandler',
    'QueryResult',
    'QueryError',
    
    # Repositories
    'EmployeeRepository',
    'ShiftRepository',
    'AssignmentRepository',
    'LeaveRequestRepository',
    'UnitOfWork',
    'EmployeeQuery',
    'ShiftQuery',
    'AssignmentQuery'
]
