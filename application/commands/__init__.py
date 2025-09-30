"""Command handlers for the scheduling application.

Commands represent intent to change system state. Command handlers
contain the business logic to execute these changes and coordinate
with domain services and repositories.

Key Design Principles:
1. Commands are imperative (CreateSchedule, AssignShift, etc.)
2. Handlers are responsible for orchestration and validation
3. Commands contain all data needed for execution
4. Handlers use Unit of Work for transaction management
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

if TYPE_CHECKING:
    from application.repositories import UnitOfWork
    from domain.entities import Assignment
    from domain.entities import Employee
    from domain.entities import Shift
    from domain.services import ConflictDetector
    from domain.services import FairnessCalculator
    from domain.value_objects import DateRange
    from domain.value_objects import EmployeeId
    from domain.value_objects import ShiftId
    from domain.value_objects import ShiftType
    from domain.value_objects import TimeRange


class CommandError(Exception):
    """Base exception for command execution errors."""



class ValidationError(CommandError):
    """Raised when command validation fails."""



class BusinessRuleViolationError(CommandError):
    """Raised when business rules are violated."""



@dataclass
class Command(ABC):
    """Base class for all commands."""



@dataclass
class CreateScheduleCommand(Command):
    """Command to create a new schedule for a date range."""

    date_range: "DateRange"
    department_ids: list[str]
    requested_by: str
    priority_shifts: list["ShiftId"] | None = None
    constraints: dict[str, Any] | None = None


@dataclass
class AssignShiftCommand(Command):
    """Command to assign a shift to an employee."""

    shift_id: "ShiftId"
    employee_id: "EmployeeId"
    assigned_by: str
    assignment_type: str = "automatic"  # 'automatic', 'manual', 'forced'
    notes: str | None = None


@dataclass
class UnassignShiftCommand(Command):
    """Command to unassign a shift from an employee."""

    assignment_id: str
    reason: str
    unassigned_by: str


@dataclass
class SwapAssignmentsCommand(Command):
    """Command to swap assignments between two employees."""

    assignment_id_1: str
    assignment_id_2: str
    requested_by: str
    approval_required: bool = True


@dataclass
class ResolveConflictCommand(Command):
    """Command to resolve a scheduling conflict."""

    conflict_id: str
    resolution_strategy: str  # 'reassign', 'swap', 'unassign', 'override'
    target_assignments: list[str]
    resolved_by: str
    notes: str | None = None


@dataclass
class CommandResult:
    """Result of command execution."""

    success: bool
    message: str
    data: dict[str, Any] | None = None
    warnings: list[str] | None = None
    errors: list[str] | None = None


class CommandHandler(ABC):
    """Base class for command handlers."""

    def __init__(self, uow: "UnitOfWork"):
        self.uow = uow

    @abstractmethod
    async def handle(self, command: Command) -> CommandResult:
        """Handle the command execution."""

    async def validate_command(self, command: Command) -> list[str]:
        """Validate command before execution."""
        errors = []

        # Basic validation - override in subclasses
        if not isinstance(command, Command):
            errors.append("Invalid command type")

        return errors


class CreateScheduleCommandHandler(CommandHandler):
    """Handler for CreateScheduleCommand."""

    def __init__(
        self,
        uow: "UnitOfWork",
        fairness_calculator: "FairnessCalculator",
        conflict_detector: "ConflictDetector",
    ):
        super().__init__(uow)
        self.fairness_calculator = fairness_calculator
        self.conflict_detector = conflict_detector

    async def handle(self, command: CreateScheduleCommand) -> CommandResult:
        """Handle schedule creation."""
        try:
            # Validate command
            validation_errors = await self.validate_command(command)
            if validation_errors:
                return CommandResult(
                    success=False,
                    message="Command validation failed",
                    errors=validation_errors,
                )

            async with self.uow:
                # Import here to avoid circular dependencies
                from application.use_cases import OrchestrateScheduleUseCase
                from application.use_cases import SchedulingRequest

                # Create scheduling request from command
                scheduling_request = SchedulingRequest(
                    date_range=command.date_range,
                    department_ids=command.department_ids,
                    priority_shifts=command.priority_shifts,
                    constraints=command.constraints,
                )

                # Execute scheduling use case
                use_case = OrchestrateScheduleUseCase(
                    uow=self.uow,
                    fairness_calculator=self.fairness_calculator,
                    conflict_detector=self.conflict_detector,
                )

                result = await use_case.execute(scheduling_request)

                return CommandResult(
                    success=result.success,
                    message=f"Schedule created with {len(result.assignments)} assignments",
                    data={
                        "assignments": [
                            {"id": a.id, "employee_id": a.employee_id}
                            for a in result.assignments
                        ],
                        "unassigned_shifts": [
                            {"id": s.id} for s in result.unassigned_shifts
                        ],
                        "conflicts": result.conflicts_detected,
                        "fairness_scores": {
                            str(k): v for k, v in result.fairness_scores.items()
                        },
                    },
                    warnings=result.warnings,
                )

        except Exception as e:
            return CommandResult(
                success=False,
                message=f"Schedule creation failed: {e!s}",
                errors=[str(e)],
            )

    async def validate_command(self, command: CreateScheduleCommand) -> list[str]:
        """Validate CreateScheduleCommand."""
        errors = await super().validate_command(command)

        if not command.date_range:
            errors.append("Date range is required")

        if not command.department_ids:
            errors.append("At least one department ID is required")

        if not command.requested_by:
            errors.append("Requested by field is required")

        # Validate date range is in the future or present
        if command.date_range and command.date_range.start < date.today():
            errors.append("Cannot create schedule for past dates")

        return errors


class AssignShiftCommandHandler(CommandHandler):
    """Handler for AssignShiftCommand."""

    def __init__(self, uow: "UnitOfWork", conflict_detector: "ConflictDetector"):
        super().__init__(uow)
        self.conflict_detector = conflict_detector

    async def handle(self, command: AssignShiftCommand) -> CommandResult:
        """Handle shift assignment."""
        try:
            # Validate command
            validation_errors = await self.validate_command(command)
            if validation_errors:
                return CommandResult(
                    success=False,
                    message="Command validation failed",
                    errors=validation_errors,
                )

            async with self.uow:
                # Get shift and employee
                shift = await self.uow.shifts.find_by_id(command.shift_id)
                if not shift:
                    return CommandResult(
                        success=False,
                        message=f"Shift {command.shift_id} not found",
                        errors=[f"Shift {command.shift_id} not found"],
                    )

                employee = await self.uow.employees.find_by_id(command.employee_id)
                if not employee:
                    return CommandResult(
                        success=False,
                        message=f"Employee {command.employee_id} not found",
                        errors=[f"Employee {command.employee_id} not found"],
                    )

                # Check for conflicts if not forced assignment
                if command.assignment_type != "forced":
                    # Get existing assignments for conflict detection
                    from application.repositories import AssignmentQuery

                    existing_assignments = await self.uow.assignments.find_all(
                        AssignmentQuery(date_range=shift.time_range, status="active"),
                    )

                    # Create temporary assignment for conflict detection
                    from domain.entities import Assignment

                    temp_assignment = Assignment(
                        id="temp",
                        employee_id=command.employee_id,
                        shift=shift,
                        assigned_at=datetime.now(),
                        status="tentative",
                    )

                    conflicts = self.conflict_detector.detect_conflicts(
                        temp_assignment, employee, existing_assignments,
                    )

                    if conflicts and command.assignment_type != "override":
                        return CommandResult(
                            success=False,
                            message="Assignment conflicts detected",
                            data={
                                "conflicts": [
                                    {
                                        "type": c.conflict_type,
                                        "severity": c.severity.value,
                                        "message": c.message,
                                    }
                                    for c in conflicts
                                ],
                            },
                            errors=["Assignment would create conflicts"],
                        )

                # Create assignment
                from domain.entities import Assignment

                assignment = Assignment(
                    id=f"assign_{datetime.now().timestamp()}",
                    employee_id=command.employee_id,
                    shift=shift,
                    assigned_at=datetime.now(),
                    status="active",
                )

                # Save assignment
                await self.uow.assignments.save(assignment)
                await self.uow.commit()

                return CommandResult(
                    success=True,
                    message=f"Shift {command.shift_id} assigned to employee {command.employee_id}",
                    data={"assignment_id": assignment.id},
                )

        except Exception as e:
            await self.uow.rollback()
            return CommandResult(
                success=False, message=f"Assignment failed: {e!s}", errors=[str(e)],
            )

    async def validate_command(self, command: AssignShiftCommand) -> list[str]:
        """Validate AssignShiftCommand."""
        errors = await super().validate_command(command)

        if not command.shift_id:
            errors.append("Shift ID is required")

        if not command.employee_id:
            errors.append("Employee ID is required")

        if not command.assigned_by:
            errors.append("Assigned by field is required")

        if command.assignment_type not in ["automatic", "manual", "forced", "override"]:
            errors.append("Invalid assignment type")

        return errors


class UnassignShiftCommandHandler(CommandHandler):
    """Handler for UnassignShiftCommand."""

    async def handle(self, command: UnassignShiftCommand) -> CommandResult:
        """Handle shift unassignment."""
        try:
            # Validate command
            validation_errors = await self.validate_command(command)
            if validation_errors:
                return CommandResult(
                    success=False,
                    message="Command validation failed",
                    errors=validation_errors,
                )

            async with self.uow:
                # Get assignment
                assignment = await self.uow.assignments.find_by_id(
                    command.assignment_id,
                )
                if not assignment:
                    return CommandResult(
                        success=False,
                        message=f"Assignment {command.assignment_id} not found",
                        errors=[f"Assignment {command.assignment_id} not found"],
                    )

                # Update assignment status
                assignment.status = "cancelled"
                assignment.cancelled_at = datetime.now()
                assignment.cancellation_reason = command.reason

                # Save changes
                await self.uow.assignments.save(assignment)
                await self.uow.commit()

                return CommandResult(
                    success=True,
                    message=f"Assignment {command.assignment_id} unassigned",
                    data={"assignment_id": assignment.id},
                )

        except Exception as e:
            await self.uow.rollback()
            return CommandResult(
                success=False, message=f"Unassignment failed: {e!s}", errors=[str(e)],
            )

    async def validate_command(self, command: UnassignShiftCommand) -> list[str]:
        """Validate UnassignShiftCommand."""
        errors = await super().validate_command(command)

        if not command.assignment_id:
            errors.append("Assignment ID is required")

        if not command.reason:
            errors.append("Reason is required")

        if not command.unassigned_by:
            errors.append("Unassigned by field is required")

        return errors


class SwapAssignmentsCommandHandler(CommandHandler):
    """Handler for SwapAssignmentsCommand."""

    def __init__(self, uow: "UnitOfWork", conflict_detector: "ConflictDetector"):
        super().__init__(uow)
        self.conflict_detector = conflict_detector

    async def handle(self, command: SwapAssignmentsCommand) -> CommandResult:
        """Handle assignment swap."""
        try:
            # Validate command
            validation_errors = await self.validate_command(command)
            if validation_errors:
                return CommandResult(
                    success=False,
                    message="Command validation failed",
                    errors=validation_errors,
                )

            async with self.uow:
                # Get both assignments
                assignment1 = await self.uow.assignments.find_by_id(
                    command.assignment_id_1,
                )
                assignment2 = await self.uow.assignments.find_by_id(
                    command.assignment_id_2,
                )

                if not assignment1:
                    return CommandResult(
                        success=False,
                        message=f"Assignment {command.assignment_id_1} not found",
                        errors=[f"Assignment {command.assignment_id_1} not found"],
                    )

                if not assignment2:
                    return CommandResult(
                        success=False,
                        message=f"Assignment {command.assignment_id_2} not found",
                        errors=[f"Assignment {command.assignment_id_2} not found"],
                    )

                # Swap employee assignments
                original_employee_1 = assignment1.employee_id
                original_employee_2 = assignment2.employee_id

                assignment1.employee_id = original_employee_2
                assignment2.employee_id = original_employee_1

                # Update timestamps
                swap_time = datetime.now()
                assignment1.modified_at = swap_time
                assignment2.modified_at = swap_time

                # Save changes
                await self.uow.assignments.save(assignment1)
                await self.uow.assignments.save(assignment2)
                await self.uow.commit()

                return CommandResult(
                    success=True,
                    message=f"Assignments {command.assignment_id_1} and {command.assignment_id_2} swapped",
                    data={
                        "swapped_assignments": [
                            {
                                "assignment_id": assignment1.id,
                                "new_employee_id": assignment1.employee_id,
                            },
                            {
                                "assignment_id": assignment2.id,
                                "new_employee_id": assignment2.employee_id,
                            },
                        ],
                    },
                )

        except Exception as e:
            await self.uow.rollback()
            return CommandResult(
                success=False,
                message=f"Assignment swap failed: {e!s}",
                errors=[str(e)],
            )

    async def validate_command(self, command: SwapAssignmentsCommand) -> list[str]:
        """Validate SwapAssignmentsCommand."""
        errors = await super().validate_command(command)

        if not command.assignment_id_1:
            errors.append("First assignment ID is required")

        if not command.assignment_id_2:
            errors.append("Second assignment ID is required")

        if command.assignment_id_1 == command.assignment_id_2:
            errors.append("Cannot swap assignment with itself")

        if not command.requested_by:
            errors.append("Requested by field is required")

        return errors


# Export command handlers
__all__ = [
    "AssignShiftCommand",
    "AssignShiftCommandHandler",
    "BusinessRuleViolationError",
    "Command",
    "CommandError",
    "CommandHandler",
    "CommandResult",
    "CreateScheduleCommand",
    "CreateScheduleCommandHandler",
    "ResolveConflictCommand",
    "SwapAssignmentsCommand",
    "SwapAssignmentsCommandHandler",
    "UnassignShiftCommand",
    "UnassignShiftCommandHandler",
    "ValidationError",
]
