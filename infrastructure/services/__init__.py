"""
Django repository services for infrastructure layer.

Simplified implementation focusing on core functionality.
"""

from datetime import date
from datetime import datetime
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from asgiref.sync import sync_to_async
from django.contrib.auth import get_user_model
from django.db import transaction

# Application layer imports
from application.repositories import UnitOfWork

# Domain layer imports
from domain.entities import Employee
from domain.entities import Shift as DomainShift
from domain.value_objects import AssignmentStatus
from domain.value_objects import BusinessHoursConfiguration
from domain.value_objects import EmployeeId
from domain.value_objects import ShiftId
from domain.value_objects import ShiftType
from domain.value_objects import TeamConfiguration
from domain.value_objects import TeamId
from domain.value_objects import TimeRange
from team_planner.employees.models import EmployeeProfile

# Django model imports
from team_planner.shifts.models import Shift
from team_planner.shifts.models import ShiftTemplate
from team_planner.shifts.models import ShiftType as DjangoShiftType
from team_planner.teams.models import Team

User = get_user_model()


class DjangoUnitOfWork(UnitOfWork):
    """Django-based Unit of Work implementation."""

    def __init__(self):
        super().__init__()
        self._transaction = None

    async def __aenter__(self):
        """Enter async context manager."""
        self._transaction = await sync_to_async(transaction.atomic)()
        await sync_to_async(self._transaction.__enter__)()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context manager."""
        if self._transaction:
            await sync_to_async(self._transaction.__exit__)(exc_type, exc_val, exc_tb)
            self._transaction = None

    async def commit(self) -> None:
        """Commit transaction."""
        # Handled by context manager

    async def rollback(self) -> None:
        """Rollback transaction."""
        if self._transaction:
            msg = "Rollback requested"
            raise Exception(
                msg,
            )  # Will trigger __aexit__ with exception


# Simple helper functions for mapping
def map_django_shift_type_to_domain(django_type: str) -> ShiftType:
    """Map Django shift type to domain ShiftType."""
    if django_type == DjangoShiftType.INCIDENTS:
        return ShiftType.INCIDENTS
    if django_type == DjangoShiftType.INCIDENTS_STANDBY:
        return ShiftType.INCIDENTS_STANDBY
    if django_type == DjangoShiftType.WAAKDIENST:
        return ShiftType.WAAKDIENST
    return ShiftType.INCIDENTS


def map_domain_shift_type_to_django(domain_type: ShiftType) -> str:
    """Map domain ShiftType to Django shift type."""
    if domain_type == ShiftType.INCIDENTS:
        return DjangoShiftType.INCIDENTS
    if domain_type == ShiftType.INCIDENTS_STANDBY:
        return DjangoShiftType.INCIDENTS_STANDBY
    if domain_type == ShiftType.WAAKDIENST:
        return DjangoShiftType.WAAKDIENST
    return DjangoShiftType.INCIDENTS


def map_django_user_to_employee(user: Any) -> Employee:
    """Map Django User to domain Employee."""
    profile = getattr(user, "employee_profile", None)

    # Create default team configuration
    business_hours = BusinessHoursConfiguration()
    TeamConfiguration(
        timezone="Europe/Amsterdam",
        business_hours=business_hours,
        waakdienst_start_day=2,  # Wednesday
        waakdienst_start_hour=17,
        waakdienst_end_hour=8,
        skip_incidents_on_holidays=True,
        holiday_calendar="NL",
    )

    return Employee(
        id=EmployeeId(getattr(user, "pk", 1)),
        name=getattr(user, "get_full_name", lambda: "Unknown")() or "Unknown",
        email=getattr(user, "email", ""),
        team_id=TeamId(1),  # Default team
        hire_date=getattr(profile, "hire_date", date.today())
        if profile
        else date.today(),
        termination_date=getattr(profile, "termination_date", None)
        if profile
        else None,
        available_for_incidents=getattr(profile, "available_for_incidents", True)
        if profile
        else True,
        available_for_waakdienst=getattr(profile, "available_for_waakdienst", True)
        if profile
        else True,
        current_assignments=[],
        leave_requests=[],
        recurring_patterns=[],
    )


def map_django_shift_to_domain(django_shift: Any) -> DomainShift:
    """Map Django Shift to domain Shift."""
    time_range = TimeRange(
        start=django_shift.start_datetime,
        end=django_shift.end_datetime,
        timezone="Europe/Amsterdam",  # Default timezone
    )

    shift_type = map_django_shift_type_to_domain(django_shift.template.shift_type)

    return DomainShift(
        id=ShiftId(getattr(django_shift, "pk", 1)),
        shift_type=shift_type,
        time_range=time_range,
        team_id=TeamId(1),  # Default team
        assigned_employee=EmployeeId(django_shift.assigned_employee.pk)
        if django_shift.assigned_employee
        else None,
        assignment_status=AssignmentStatus.CONFIRMED,
        auto_assigned=getattr(django_shift, "auto_assigned", False),
        created_at=getattr(django_shift, "created_at", datetime.utcnow()),
        modified_at=getattr(django_shift, "updated_at", datetime.utcnow()),
        notes=getattr(django_shift, "assignment_reason", ""),
    )


# Factory function for creating UnitOfWork instances
def create_unit_of_work() -> UnitOfWork:
    """Create a new UnitOfWork instance."""
    return DjangoUnitOfWork()


# Export key functions
__all__ = [
    "DjangoUnitOfWork",
    "create_unit_of_work",
    "map_django_shift_to_domain",
    "map_django_shift_type_to_domain",
    "map_django_user_to_employee",
    "map_domain_shift_type_to_django",
]
