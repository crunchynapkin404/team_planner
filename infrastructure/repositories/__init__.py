"""Django-based repository implementations for the scheduling domain.

This module provides concrete implementations of the repository interfaces
using Django ORM. It bridges the domain layer with Django's persistence layer
while maintaining clean architecture principles.

Key Design Principles:
1. Maps domain entities to/from Django models
2. Handles all ORM-specific operations
3. Provides transaction management through Django ORM
4. Optimizes queries to prevent N+1 problems
5. Maintains domain model purity (no Django dependencies in domain)
"""

import asyncio
from datetime import date
from datetime import datetime
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Set

from asgiref.sync import sync_to_async
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from application.repositories import AssignmentQuery
from application.repositories import AssignmentRepository
from application.repositories import EmployeeQuery

# Application layer imports
from application.repositories import EmployeeRepository
from application.repositories import LeaveRequestRepository
from application.repositories import ShiftQuery
from application.repositories import ShiftRepository
from application.repositories import UnitOfWork
from domain.entities import Assignment

# Domain layer imports
from domain.entities import Employee
from domain.entities import Shift as DomainShift
from domain.value_objects import AssignmentId
from domain.value_objects import AssignmentStatus
from domain.value_objects import BusinessHoursConfiguration
from domain.value_objects import DateRange
from domain.value_objects import EmployeeId
from domain.value_objects import ShiftId
from domain.value_objects import ShiftType
from domain.value_objects import TeamConfiguration
from domain.value_objects import TeamId
from domain.value_objects import TimeRange
from team_planner.employees.models import EmployeeProfile
from team_planner.employees.models import EmployeeSkill
from team_planner.employees.models import RecurringLeavePattern
from team_planner.leaves.models import LeaveRequest

# Django model imports
from team_planner.shifts.models import Shift
from team_planner.shifts.models import ShiftTemplate
from team_planner.shifts.models import ShiftType as DjangoShiftType
from team_planner.teams.models import Department
from team_planner.teams.models import Team
from team_planner.teams.models import TeamMembership

User = get_user_model()


class DjangoEmployeeRepository(EmployeeRepository):
    """Django ORM implementation of EmployeeRepository."""

    async def find_by_id(self, employee_id: EmployeeId) -> Employee | None:
        """Find employee by ID."""
        try:
            user = await sync_to_async(
                User.objects.select_related("employee_profile").get,
            )(id=employee_id.value)
            return self._map_to_domain_employee(user)
        except User.DoesNotExist:
            return None

    async def find_all(self, query: EmployeeQuery | None = None) -> list[Employee]:
        """Find employees matching query criteria."""
        queryset = User.objects.select_related("employee_profile").prefetch_related(
            "employee_profile__skills", "teams",
        )

        if query:
            if query.active_only:
                queryset = queryset.filter(
                    employee_profile__status=EmployeeProfile.Status.ACTIVE,
                )

            if query.department_ids:
                queryset = queryset.filter(
                    teams__department__id__in=query.department_ids,
                )

            if query.exclude_ids:
                exclude_values = [emp_id.value for emp_id in query.exclude_ids]
                queryset = queryset.exclude(id__in=exclude_values)

            if query.has_skills:
                queryset = queryset.filter(
                    employee_profile__skills__name__in=query.has_skills,
                ).distinct()

        users = await sync_to_async(list)(queryset)
        return [self._map_to_domain_employee(user) for user in users]

    async def find_available_for_shift(
        self,
        shift_time: TimeRange,
        required_skills: list[str],
        exclude_employees: list[EmployeeId] | None = None,
    ) -> list[Employee]:
        """Find employees available for a specific shift."""
        queryset = (
            User.objects.select_related("employee_profile")
            .prefetch_related("employee_profile__skills")
            .filter(employee_profile__status=EmployeeProfile.Status.ACTIVE)
        )

        # Filter by required skills if specified
        if required_skills:
            queryset = queryset.filter(
                employee_profile__skills__name__in=required_skills,
            ).distinct()

        # Exclude specified employees
        if exclude_employees:
            exclude_values = [emp_id.value for emp_id in exclude_employees]
            queryset = queryset.exclude(id__in=exclude_values)

        # Check availability based on shift time (simplified)
        # In a full implementation, this would check:
        # - Leave requests
        # - Existing assignments
        # - Recurring leave patterns
        # - Employee availability preferences

        users = await sync_to_async(list)(queryset)
        return [self._map_to_domain_employee(user) for user in users]

    async def get_employee_assignments_count(
        self, employee_id: EmployeeId, date_range: TimeRange,
    ) -> int:
        """Get count of assignments for employee in date range."""
        return await sync_to_async(
            Shift.objects.filter(
                assigned_employee_id=employee_id.value,
                start_datetime__gte=date_range.start,
                end_datetime__lte=date_range.end,
                status__in=[
                    Shift.Status.SCHEDULED,
                    Shift.Status.CONFIRMED,
                    Shift.Status.IN_PROGRESS,
                ],
            ).count,
        )()

    async def get_employees_by_department(self, department_id: str) -> list[Employee]:
        """Get all employees in a department."""
        users = await sync_to_async(list)(
            User.objects.select_related("employee_profile")
            .filter(
                teams__department__id=department_id,
                employee_profile__status=EmployeeProfile.Status.ACTIVE,
            )
            .distinct(),
        )
        return [self._map_to_domain_employee(user) for user in users]

    async def save(self, employee: Employee) -> None:
        """Save or update employee."""
        # In a full implementation, this would update the Django User and EmployeeProfile
        # For now, this is a placeholder as employee updates are typically
        # handled through separate user management endpoints

    async def delete(self, employee_id: EmployeeId) -> None:
        """Delete employee."""
        # In a full implementation, this would deactivate rather than delete
        await sync_to_async(User.objects.filter(id=employee_id.value).update)(
            employee_profile__status=EmployeeProfile.Status.INACTIVE,
        )

    def _map_to_domain_employee(self, user: Any) -> Employee:
        """Map Django User to domain Employee."""
        profile = getattr(user, "employee_profile", None)
        if not profile:
            msg = f"User {user.pk} has no employee profile"
            raise ValueError(msg)

        # Get team configuration (simplified - takes first team)
        team_memberships = getattr(user, "teams", None)
        team_id = None

        if team_memberships and hasattr(team_memberships, "all"):
            teams = list(team_memberships.all())
            if teams:
                team = teams[0]
                team_id = TeamId(team.pk)

                # Create business hours configuration
                business_hours = BusinessHoursConfiguration(
                    monday_start=8,
                    monday_end=17,
                    tuesday_start=8,
                    tuesday_end=17,
                    wednesday_start=8,
                    wednesday_end=17,
                    thursday_start=8,
                    thursday_end=17,
                    friday_start=8,
                    friday_end=17,
                    saturday_start=None,
                    saturday_end=None,
                    sunday_start=None,
                    sunday_end=None,
                )

                TeamConfiguration(
                    timezone=team.timezone,
                    business_hours=business_hours,
                    waakdienst_start_day=team.waakdienst_handover_weekday,
                    waakdienst_start_hour=team.waakdienst_start_hour,
                    waakdienst_end_hour=team.waakdienst_end_hour,
                    skip_incidents_on_holidays=team.incidents_skip_holidays,
                    holiday_calendar="NL",  # Default to Netherlands
                    fairness_period_days=365,  # 1 year
                )

        return Employee(
            id=EmployeeId(user.pk),
            name=getattr(
                user, "get_full_name", lambda: getattr(user, "username", "Unknown"),
            )()
            or getattr(user, "username", "Unknown"),
            email=getattr(user, "email", ""),
            team_id=team_id or TeamId(1),  # Default team if none found
            hire_date=getattr(profile, "hire_date", date.today()),
            termination_date=getattr(profile, "termination_date", None),
            available_for_incidents=getattr(profile, "available_for_incidents", True),
            available_for_waakdienst=getattr(profile, "available_for_waakdienst", True),
            current_assignments=[],
            leave_requests=[],
            recurring_patterns=[],
        )


class DjangoShiftRepository(ShiftRepository):
    """Django ORM implementation of ShiftRepository."""

    async def find_by_id(self, shift_id: ShiftId) -> DomainShift | None:
        """Find shift by ID."""
        try:
            django_shift = await sync_to_async(
                Shift.objects.select_related("template", "assigned_employee").get,
            )(id=shift_id.value)
            return self._map_to_domain_shift(django_shift)
        except Shift.DoesNotExist:
            return None

    async def find_all(self, query: ShiftQuery | None = None) -> list[DomainShift]:
        """Find shifts matching query criteria."""
        queryset = Shift.objects.select_related("template", "assigned_employee")

        if query:
            if query.date_range:
                queryset = queryset.filter(
                    start_datetime__gte=query.date_range.start,
                    end_datetime__lte=query.date_range.end,
                )

            if query.shift_types:
                django_shift_types = [
                    self._map_to_django_shift_type(st) for st in query.shift_types
                ]
                queryset = queryset.filter(template__shift_type__in=django_shift_types)

            if query.status:
                if query.status == "assigned":
                    queryset = queryset.exclude(assigned_employee__isnull=True)
                elif query.status == "unassigned":
                    queryset = queryset.filter(assigned_employee__isnull=True)
                elif query.status == "pending":
                    queryset = queryset.filter(status=Shift.Status.SCHEDULED)

            if query.assigned_to:
                employee_ids = [emp_id.value for emp_id in query.assigned_to]
                queryset = queryset.filter(assigned_employee__id__in=employee_ids)

        shifts = await sync_to_async(list)(queryset)
        return [self._map_to_domain_shift(shift) for shift in shifts]

    async def find_unassigned_in_range(
        self, date_range: TimeRange,
    ) -> list[DomainShift]:
        """Find unassigned shifts in date range."""
        shifts = await sync_to_async(list)(
            Shift.objects.select_related("template").filter(
                start_datetime__gte=date_range.start,
                end_datetime__lte=date_range.end,
                assigned_employee__isnull=True,
                status=Shift.Status.SCHEDULED,
            ),
        )
        return [self._map_to_domain_shift(shift) for shift in shifts]

    async def find_conflicting_shifts(
        self, employee_id: EmployeeId, time_range: TimeRange,
    ) -> list[DomainShift]:
        """Find shifts that would conflict with employee assignment."""
        shifts = await sync_to_async(list)(
            Shift.objects.select_related("template").filter(
                assigned_employee_id=employee_id.value,
                start_datetime__lt=time_range.end,
                end_datetime__gt=time_range.start,
                status__in=[
                    Shift.Status.SCHEDULED,
                    Shift.Status.CONFIRMED,
                    Shift.Status.IN_PROGRESS,
                ],
            ),
        )
        return [self._map_to_domain_shift(shift) for shift in shifts]

    async def find_by_department_and_date(
        self, department_id: str, target_date: date,
    ) -> list[DomainShift]:
        """Find shifts for department on specific date."""
        # This would require linking shifts to departments through teams
        # For now, return all shifts on the date
        start_datetime = timezone.make_aware(
            datetime.combine(target_date, datetime.min.time()),
        )
        end_datetime = timezone.make_aware(
            datetime.combine(target_date, datetime.max.time()),
        )

        shifts = await sync_to_async(list)(
            Shift.objects.select_related("template", "assigned_employee").filter(
                start_datetime__gte=start_datetime, start_datetime__lt=end_datetime,
            ),
        )
        return [self._map_to_domain_shift(shift) for shift in shifts]

    async def get_shift_coverage_requirements(
        self, date_range: TimeRange,
    ) -> dict[str, int]:
        """Get coverage requirements by shift type."""
        # This would analyze shift templates and team requirements
        # For now, return a simplified structure
        return {
            "incidents": 5,  # 5 days per week
            "incidents_standby": 5,  # Optional
            "waakdienst": 7,  # 7 days per week
        }

    async def save(self, shift: DomainShift) -> None:
        """Save or update shift."""
        # Create or update Django Shift object
        django_shift_data = {
            "start_datetime": shift.time_range.start,
            "end_datetime": shift.time_range.end,
            "status": shift.assignment_status.value
            if hasattr(shift.assignment_status, "value")
            else str(shift.assignment_status),
            "auto_assigned": getattr(shift, "auto_assigned", True),
            "assignment_reason": getattr(shift, "notes", ""),
        }

        # Get or create template
        template = await self._get_or_create_template(shift.shift_type)
        django_shift_data["template"] = template

        if shift.assigned_employee:
            django_shift_data["assigned_employee_id"] = shift.assigned_employee.value

        if shift.id:
            # Update existing
            await sync_to_async(Shift.objects.filter(id=shift.id.value).update)(
                **django_shift_data,
            )
        else:
            # Create new
            django_shift = await sync_to_async(Shift.objects.create)(
                **django_shift_data,
            )
            # Update domain shift with new ID
            object.__setattr__(shift, "id", ShiftId(django_shift.pk))

    async def save_batch(self, shifts: list[DomainShift]) -> None:
        """Save multiple shifts in batch."""
        for shift in shifts:
            await self.save(shift)

    async def delete(self, shift_id: ShiftId) -> None:
        """Delete shift."""
        await sync_to_async(Shift.objects.filter(id=shift_id.value).delete)()

    def _map_to_domain_shift(self, django_shift: Any) -> DomainShift:
        """Map Django Shift to domain Shift."""
        time_range = TimeRange(
            start=django_shift.start_datetime,
            end=django_shift.end_datetime,
            timezone=django_shift.start_datetime.tzinfo.zone
            if django_shift.start_datetime.tzinfo
            else "UTC",
        )

        shift_type = self._map_to_domain_shift_type(django_shift.template.shift_type)

        # Get team ID from shift template or default
        team_id = TeamId(
            1,
        )  # Default team - in real implementation would get from template

        return DomainShift(
            id=ShiftId(django_shift.pk),
            shift_type=shift_type,
            time_range=time_range,
            team_id=team_id,
            assigned_employee=EmployeeId(django_shift.assigned_employee.pk)
            if django_shift.assigned_employee
            else None,
            assignment_status=self._map_to_domain_assignment_status(
                django_shift.status,
            ),
            auto_assigned=getattr(django_shift, "auto_assigned", False),
            created_at=getattr(django_shift, "created_at", datetime.utcnow()),
            modified_at=getattr(django_shift, "updated_at", datetime.utcnow()),
            notes=getattr(django_shift, "assignment_reason", ""),
        )

    def _map_to_domain_shift_type(self, django_shift_type: str) -> ShiftType:
        """Map Django shift type to domain ShiftType."""
        if django_shift_type == DjangoShiftType.INCIDENTS:
            return ShiftType.INCIDENTS
        if django_shift_type == DjangoShiftType.INCIDENTS_STANDBY:
            return ShiftType.INCIDENTS_STANDBY
        if django_shift_type == DjangoShiftType.WAAKDIENST:
            return ShiftType.WAAKDIENST
        return ShiftType.INCIDENTS  # Default fallback

    def _map_to_django_shift_type(self, domain_shift_type: ShiftType) -> str:
        """Map domain ShiftType to Django shift type."""
        if domain_shift_type == ShiftType.INCIDENTS:
            return DjangoShiftType.INCIDENTS
        if domain_shift_type == ShiftType.INCIDENTS_STANDBY:
            return DjangoShiftType.INCIDENTS_STANDBY
        if domain_shift_type == ShiftType.WAAKDIENST:
            return DjangoShiftType.WAAKDIENST
        return DjangoShiftType.INCIDENTS  # Default fallback

    def _map_to_domain_assignment_status(self, django_status: str) -> AssignmentStatus:
        """Map Django shift status to domain assignment status."""
        # Simplified mapping - in real implementation would be more sophisticated
        if django_status in ["scheduled", "confirmed"]:
            return AssignmentStatus.CONFIRMED
        if django_status == "cancelled":
            return AssignmentStatus.CANCELLED
        return AssignmentStatus.PENDING

    def _map_to_django_status(self, domain_status: AssignmentStatus) -> str:
        """Map domain assignment status to Django shift status."""
        if domain_status == AssignmentStatus.CONFIRMED:
            return "confirmed"
        if domain_status == AssignmentStatus.CANCELLED:
            return "cancelled"
        return "scheduled"

    def _get_shift_required_skills(self, template: ShiftTemplate) -> list[str]:
        """Get required skills for a shift template."""
        return [skill.name for skill in template.skills_required.all()]

    async def _get_or_create_template(self, shift_type: ShiftType) -> ShiftTemplate:
        """Get or create shift template for shift type."""
        django_shift_type = self._map_to_django_shift_type(shift_type)

        template, created = await sync_to_async(ShiftTemplate.objects.get_or_create)(
            shift_type=django_shift_type,
            name=f"Default {shift_type.value}",
            defaults={
                "description": f"Default template for {shift_type.value} shifts",
                "duration_hours": 9
                if shift_type in [ShiftType.INCIDENTS, ShiftType.INCIDENTS_STANDBY]
                else 15,
            },
        )
        return template


class DjangoAssignmentRepository(AssignmentRepository):
    """Django ORM implementation of AssignmentRepository."""

    async def find_by_id(self, assignment_id: str) -> Assignment | None:
        """Find assignment by ID."""
        try:
            # Assignments are represented by Shift objects in Django
            django_shift = await sync_to_async(
                Shift.objects.select_related("template", "assigned_employee").get,
            )(id=assignment_id)
            return self._map_to_domain_assignment(django_shift)
        except Shift.DoesNotExist:
            return None

    async def find_all(
        self, query: AssignmentQuery | None = None,
    ) -> list[Assignment]:
        """Find assignments matching query criteria."""
        queryset = Shift.objects.select_related(
            "template", "assigned_employee",
        ).exclude(assigned_employee__isnull=True)

        if query:
            if query.employee_id:
                queryset = queryset.filter(assigned_employee_id=query.employee_id.value)

            if query.shift_id:
                queryset = queryset.filter(id=query.shift_id.value)

            if query.date_range:
                queryset = queryset.filter(
                    start_datetime__gte=query.date_range.start,
                    end_datetime__lte=query.date_range.end,
                )

            if query.status:
                if query.status == "active":
                    queryset = queryset.filter(
                        status__in=[
                            Shift.Status.SCHEDULED,
                            Shift.Status.CONFIRMED,
                            Shift.Status.IN_PROGRESS,
                        ],
                    )
                elif query.status == "cancelled":
                    queryset = queryset.filter(status=Shift.Status.CANCELLED)

        shifts = await sync_to_async(list)(queryset)
        return [self._map_to_domain_assignment(shift) for shift in shifts]

    async def find_by_employee_and_date_range(
        self, employee_id: EmployeeId, date_range: TimeRange,
    ) -> list[Assignment]:
        """Find assignments for employee in date range."""
        shifts = await sync_to_async(list)(
            Shift.objects.select_related("template")
            .filter(
                assigned_employee_id=employee_id.value,
                start_datetime__gte=date_range.start,
                end_datetime__lte=date_range.end,
            )
            .exclude(assigned_employee__isnull=True),
        )
        return [self._map_to_domain_assignment(shift) for shift in shifts]

    async def find_by_shift(self, shift_id: ShiftId) -> list[Assignment]:
        """Find all assignments for a shift."""
        try:
            shift = await sync_to_async(
                Shift.objects.select_related("template", "assigned_employee").get,
            )(id=shift_id.value)
            if shift.assigned_employee:
                return [self._map_to_domain_assignment(shift)]
            return []
        except Shift.DoesNotExist:
            return []

    async def find_conflicting_assignments(
        self, employee_id: EmployeeId, time_range: TimeRange,
    ) -> list[Assignment]:
        """Find assignments that would conflict with new assignment."""
        shifts = await sync_to_async(list)(
            Shift.objects.select_related("template").filter(
                assigned_employee_id=employee_id.value,
                start_datetime__lt=time_range.end,
                end_datetime__gt=time_range.start,
                status__in=[
                    Shift.Status.SCHEDULED,
                    Shift.Status.CONFIRMED,
                    Shift.Status.IN_PROGRESS,
                ],
            ),
        )
        return [self._map_to_domain_assignment(shift) for shift in shifts]

    async def get_assignment_statistics(
        self, employee_id: EmployeeId, date_range: TimeRange,
    ) -> dict[str, Any]:
        """Get assignment statistics for employee in date range."""
        shifts = await sync_to_async(list)(
            Shift.objects.select_related("template").filter(
                assigned_employee_id=employee_id.value,
                start_datetime__gte=date_range.start,
                end_datetime__lte=date_range.end,
            ),
        )

        stats = {
            "total_assignments": len(shifts),
            "incidents_count": 0,
            "incidents_standby_count": 0,
            "waakdienst_count": 0,
            "total_hours": 0.0,
        }

        for shift in shifts:
            duration = (
                shift.end_datetime - shift.start_datetime
            ).total_seconds() / 3600
            stats["total_hours"] += duration

            if shift.template.shift_type == DjangoShiftType.INCIDENTS:
                stats["incidents_count"] += 1
            elif shift.template.shift_type == DjangoShiftType.INCIDENTS_STANDBY:
                stats["incidents_standby_count"] += 1
            elif shift.template.shift_type == DjangoShiftType.WAAKDIENST:
                stats["waakdienst_count"] += 1

        return stats

    async def save(self, assignment: Assignment) -> None:
        """Save or update assignment."""
        # Assignments are saved as part of shift updates
        # This would update the assigned_employee field on the Shift
        if hasattr(assignment, "shift_id") and assignment.shift_id:
            await sync_to_async(
                Shift.objects.filter(id=assignment.shift_id.value).update,
            )(
                assigned_employee_id=assignment.employee_id.value,
                status=assignment.status.value
                if hasattr(assignment.status, "value")
                else assignment.status,
            )

    async def save_batch(self, assignments: list[Assignment]) -> None:
        """Save multiple assignments in batch."""
        for assignment in assignments:
            await self.save(assignment)

    async def delete(self, assignment_id: str) -> None:
        """Delete assignment."""
        # This would unassign the employee from the shift
        await sync_to_async(Shift.objects.filter(id=assignment_id).update)(
            assigned_employee=None, status=Shift.Status.SCHEDULED,
        )

    def _map_to_domain_assignment(self, django_shift: Any) -> Assignment:
        """Map Django Shift to domain Assignment."""
        if not django_shift.assigned_employee:
            msg = "Cannot create assignment from unassigned shift"
            raise ValueError(msg)

        time_range = TimeRange(
            start=django_shift.start_datetime,
            end=django_shift.end_datetime,
            timezone=django_shift.start_datetime.tzinfo.zone
            if django_shift.start_datetime.tzinfo
            else "UTC",
        )

        # Create shift entity for the assignment
        team_id = TeamId(1)  # Default team
        domain_shift = DomainShift(
            id=ShiftId(django_shift.pk),
            shift_type=self._map_to_domain_shift_type(django_shift.template.shift_type),
            time_range=time_range,
            team_id=team_id,
            assigned_employee=EmployeeId(django_shift.assigned_employee.pk),
            assignment_status=AssignmentStatus.CONFIRMED,  # Simplified mapping
            auto_assigned=getattr(django_shift, "auto_assigned", False),
        )

        # Use proper UserId instead of None
        from domain.value_objects import UserId

        return Assignment(
            id=AssignmentId(django_shift.pk),  # Use proper AssignmentId
            employee_id=EmployeeId(django_shift.assigned_employee.pk),
            shift_id=ShiftId(django_shift.pk),
            assigned_at=getattr(django_shift, "created_at", datetime.utcnow()),
            assigned_by=UserId.system(),  # System user for auto assignments
            auto_assigned=getattr(django_shift, "auto_assigned", True),
            status=AssignmentStatus.CONFIRMED
            if django_shift.status in ["scheduled", "confirmed", "in_progress"]
            else AssignmentStatus.CANCELLED,
            conflicts=[],  # Would be populated by conflict detector
            shift=domain_shift,
        )

    def _map_to_domain_shift_type(self, django_shift_type: str) -> ShiftType:
        """Map Django shift type to domain ShiftType."""
        mapping = {
            DjangoShiftType.INCIDENTS: ShiftType.INCIDENTS,
            DjangoShiftType.INCIDENTS_STANDBY: ShiftType.INCIDENTS_STANDBY,
            DjangoShiftType.WAAKDIENST: ShiftType.WAAKDIENST,
        }
        return mapping.get(django_shift_type, ShiftType.INCIDENTS)


class DjangoLeaveRequestRepository(LeaveRequestRepository):
    """Django ORM implementation of LeaveRequestRepository."""

    async def find_by_employee_and_date_range(
        self, employee_id: EmployeeId, date_range: TimeRange,
    ) -> list[dict[str, Any]]:
        """Find leave requests for employee in date range."""
        leave_requests = await sync_to_async(list)(
            LeaveRequest.objects.filter(
                employee_id=employee_id.value,
                start_date__lte=date_range.end.date(),
                end_date__gte=date_range.start.date(),
            ).order_by("start_date"),
        )

        return [
            {
                "id": leave.id,
                "employee_id": leave.employee_id,
                "start_date": leave.start_date.isoformat(),
                "end_date": leave.end_date.isoformat(),
                "leave_type": leave.leave_type.name if leave.leave_type else "Unknown",
                "status": leave.status,
                "coverage_type": getattr(leave, "coverage_type", "full_day"),
            }
            for leave in leave_requests
        ]

    async def find_approved_leave_in_range(
        self, date_range: TimeRange,
    ) -> list[dict[str, Any]]:
        """Find all approved leave requests in date range."""
        leave_requests = await sync_to_async(list)(
            LeaveRequest.objects.filter(
                start_date__lte=date_range.end.date(),
                end_date__gte=date_range.start.date(),
                status="approved",
            )
            .select_related("leave_type")
            .order_by("start_date"),
        )

        return [
            {
                "id": leave.id,
                "employee_id": leave.employee_id,
                "start_date": leave.start_date.isoformat(),
                "end_date": leave.end_date.isoformat(),
                "leave_type": leave.leave_type.name if leave.leave_type else "Unknown",
                "status": leave.status,
                "coverage_type": getattr(leave, "coverage_type", "full_day"),
            }
            for leave in leave_requests
        ]

    async def is_employee_on_leave(
        self, employee_id: EmployeeId, time_range: TimeRange,
    ) -> bool:
        """Check if employee has approved leave during time range."""
        count = await sync_to_async(
            LeaveRequest.objects.filter(
                employee_id=employee_id.value,
                start_date__lte=time_range.end.date(),
                end_date__gte=time_range.start.date(),
                status="approved",
            ).count,
        )()

        return count > 0


class DjangoUnitOfWork(UnitOfWork):
    """Django-based Unit of Work implementation."""

    def __init__(self):
        super().__init__()
        self.employees = DjangoEmployeeRepository()
        self.shifts = DjangoShiftRepository()
        self.assignments = DjangoAssignmentRepository()
        self.leave_requests = DjangoLeaveRequestRepository()
        self._transaction = None

    async def __aenter__(self):
        """Enter async context manager."""
        # Start Django database transaction
        self._transaction = await sync_to_async(transaction.atomic)()
        await sync_to_async(self._transaction.__enter__)()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context manager."""
        if self._transaction:
            if exc_type is not None:
                # Exception occurred, rollback
                await sync_to_async(self._transaction.__exit__)(
                    exc_type, exc_val, exc_tb,
                )
            else:
                # No exception, commit
                await sync_to_async(self._transaction.__exit__)(None, None, None)
            self._transaction = None

    async def commit(self) -> None:
        """Commit transaction."""
        # Transaction will be committed when exiting context manager

    async def rollback(self) -> None:
        """Rollback transaction."""
        # Force transaction rollback
        if self._transaction:
            await sync_to_async(self._transaction.rollback)()


# Factory function for creating UnitOfWork instances
def create_unit_of_work() -> UnitOfWork:
    """Create a new UnitOfWork instance."""
    return DjangoUnitOfWork()


# Export implementations
__all__ = [
    "DjangoAssignmentRepository",
    "DjangoEmployeeRepository",
    "DjangoLeaveRequestRepository",
    "DjangoShiftRepository",
    "DjangoUnitOfWork",
    "create_unit_of_work",
]
