"""
API views for the orchestrator system.

This module provides REST API endpoints that integrate the clean architecture
orchestrator with Django REST framework, exposing scheduling operations
to the frontend and external systems.
"""

import logging
from datetime import datetime
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from rest_framework import status
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

# Application layer imports
from application.use_cases import OrchestrateScheduleUseCase

# Domain imports
from domain.value_objects import DateRange
from domain.value_objects import EmployeeId
from domain.value_objects import ShiftType
from domain.value_objects import TimeRange
from infrastructure.repositories import map_django_user_to_employee

# Infrastructure imports
from infrastructure.services import create_unit_of_work

# Django imports
from team_planner.shifts.models import Shift

User = get_user_model()
logger = logging.getLogger(__name__)


class OrchestratorAPIViewSet(viewsets.ViewSet):
    """
    API ViewSet for orchestrator operations.

    Provides endpoints for:
    - Schedule orchestration
    - Conflict resolution
    - Assignment validation
    - Fairness reporting
    """

    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["post"])
    async def orchestrate_schedule(self, request):
        """
        Orchestrate shifts for a given date range and department.

        POST /api/orchestrator/orchestrate_schedule/
        {
            "start_date": "2025-08-12",
            "end_date": "2025-08-19",
            "department_id": "1",
            "shift_types": ["incidents", "waakdienst"],
            "options": {
                "include_standby": true,
                "force_reassignment": false,
                "dry_run": false
            }
        }
        """
        try:
            # Parse request data
            data = request.data
            start_date = datetime.strptime(data["start_date"], "%Y-%m-%d").date()
            end_date = datetime.strptime(data["end_date"], "%Y-%m-%d").date()
            department_id = data["department_id"]
            shift_types = [
                ShiftType(st)
                for st in data.get("shift_types", ["incidents", "waakdienst"])
            ]
            options = data.get("options", {})

            # Create date range
            date_range = DateRange(start=start_date, end=end_date)

            # Create command
            command = OrchestrateScheduleCommand(
                date_range=date_range,
                department_id=department_id,
                shift_types=shift_types,
                include_incidents_standby=options.get("include_standby", True),
                force_reassignment=options.get("force_reassignment", False),
                dry_run=options.get("dry_run", False),
            )

            # Execute use case
            uow = create_unit_of_work()
            use_case = OrchestrateScheduleUseCase(uow)

            async with uow:
                result = await use_case.execute(command)
                if not options.get("dry_run", False):
                    await uow.commit()

            # Format response
            response_data = {
                "success": result.success,
                "message": result.message,
                "statistics": {
                    "total_shifts_created": result.total_shifts_created,
                    "assignments_made": result.assignments_made,
                    "conflicts_resolved": result.conflicts_resolved,
                    "unassigned_shifts": result.unassigned_shifts,
                },
                "assignments": [
                    {
                        "shift_id": assignment.shift_id.value,
                        "employee_id": assignment.employee_id.value,
                        "employee_name": assignment.employee_name,
                        "shift_type": assignment.shift_type.value,
                        "start_time": assignment.start_time.isoformat(),
                        "end_time": assignment.end_time.isoformat(),
                        "auto_assigned": assignment.auto_assigned,
                    }
                    for assignment in result.assignments
                ],
                "conflicts": [
                    {
                        "type": conflict.conflict_type,
                        "severity": conflict.severity.value,
                        "message": conflict.message,
                        "affected_employee_id": conflict.employee_id.value
                        if hasattr(conflict, "employee_id")
                        else None,
                    }
                    for conflict in result.conflicts
                ],
            }

            return Response(response_data, status=status.HTTP_200_OK)

        except ValueError as e:
            logger.exception(f"Validation error in orchestrate_schedule: {e}")
            return Response(
                {"error": "Validation error", "message": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            logger.exception(f"Error in orchestrate_schedule: {e}")
            return Response(
                {"error": "Internal server error", "message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["post"])
    async def resolve_conflicts(self, request):
        """
        Resolve conflicts for specific shifts or employees.

        POST /api/orchestrator/resolve_conflicts/
        {
            "shift_ids": [123, 124, 125],
            "strategy": "fairness_priority", // or "availability_priority"
            "max_iterations": 3
        }
        """
        try:
            data = request.data
            shift_ids = [int(sid) for sid in data.get("shift_ids", [])]
            strategy = data.get("strategy", "fairness_priority")
            max_iterations = data.get("max_iterations", 3)

            # Create command
            command = ResolveConflictsCommand(
                shift_ids=shift_ids,
                resolution_strategy=strategy,
                max_iterations=max_iterations,
            )

            # Execute use case
            uow = create_unit_of_work()
            use_case = ResolveConflictsUseCase(uow)

            async with uow:
                result = await use_case.execute(command)
                await uow.commit()

            response_data = {
                "success": result.success,
                "message": result.message,
                "conflicts_resolved": result.conflicts_resolved,
                "remaining_conflicts": result.remaining_conflicts,
                "resolutions": [
                    {
                        "shift_id": resolution.shift_id.value,
                        "old_employee_id": resolution.old_employee_id.value
                        if resolution.old_employee_id
                        else None,
                        "new_employee_id": resolution.new_employee_id.value,
                        "resolution_reason": resolution.reason,
                    }
                    for resolution in result.resolutions
                ],
            }

            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.exception(f"Error in resolve_conflicts: {e}")
            return Response(
                {"error": "Internal server error", "message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["post"])
    async def validate_assignment(self, request):
        """
        Validate a potential assignment before making it.

        POST /api/orchestrator/validate_assignment/
        {
            "employee_id": 123,
            "shift_id": 456
        }
        """
        try:
            data = request.data
            employee_id = EmployeeId(int(data["employee_id"]))
            shift_id = int(data["shift_id"])

            # Create command
            command = ValidateAssignmentCommand(
                employee_id=employee_id, shift_id=shift_id,
            )

            # Execute use case
            uow = create_unit_of_work()
            use_case = ValidateAssignmentUseCase(uow)

            async with uow:
                result = await use_case.execute(command)

            response_data = {
                "valid": result.is_valid,
                "conflicts": [
                    {
                        "type": conflict.conflict_type,
                        "severity": conflict.severity.value,
                        "message": conflict.message,
                    }
                    for conflict in result.conflicts
                ],
                "recommendations": result.recommendations,
            }

            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.exception(f"Error in validate_assignment: {e}")
            return Response(
                {"error": "Internal server error", "message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["get"])
    @method_decorator(cache_page(60 * 5))  # Cache for 5 minutes
    async def fairness_report(self, request):
        """
        Get fairness report for employees in a date range.

        GET /api/orchestrator/fairness_report/?start_date=2025-08-01&end_date=2025-08-31&department_id=1
        """
        try:
            # Parse query parameters
            start_date_str = request.query_params.get("start_date")
            end_date_str = request.query_params.get("end_date")
            department_id = request.query_params.get("department_id")

            if not all([start_date_str, end_date_str]):
                return Response(
                    {"error": "start_date and end_date are required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
            date_range = DateRange(start=start_date, end=end_date)

            # Create query
            query = GetFairnessReportQuery(
                date_range=date_range, department_id=department_id,
            )

            # Execute use case
            uow = create_unit_of_work()
            use_case = GetFairnessReportUseCase(uow)

            async with uow:
                result = await use_case.execute(query)

            response_data = {
                "period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                },
                "department_id": department_id,
                "fairness_scores": [
                    {
                        "employee_id": score.employee_id.value,
                        "employee_name": score.employee_name,
                        "incidents_score": score.incidents_score,
                        "waakdienst_score": score.waakdienst_score,
                        "total_score": score.total_score,
                        "assignments_count": score.assignments_count,
                        "total_hours": score.total_hours,
                    }
                    for score in result.employee_scores
                ],
                "statistics": {
                    "total_employees": result.total_employees,
                    "average_fairness_score": result.average_fairness_score,
                    "fairness_variance": result.fairness_variance,
                    "most_assigned_employee": result.most_assigned_employee,
                    "least_assigned_employee": result.least_assigned_employee,
                },
            }

            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.exception(f"Error in fairness_report: {e}")
            return Response(
                {"error": "Internal server error", "message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["get"])
    async def employee_availability(self, request):
        """
        Get employee availability for a specific time range.

        GET /api/orchestrator/employee_availability/?start_date=2025-08-01&end_date=2025-08-31&shift_type=incidents
        """
        try:
            # Parse query parameters
            start_date_str = request.query_params.get("start_date")
            end_date_str = request.query_params.get("end_date")
            shift_type_str = request.query_params.get("shift_type", "incidents")

            if not all([start_date_str, end_date_str]):
                return Response(
                    {"error": "start_date and end_date are required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
            shift_type = ShiftType(shift_type_str)

            # Create time range for the date range
            start_datetime = datetime.combine(start_date, datetime.min.time())
            end_datetime = datetime.combine(end_date, datetime.max.time())
            time_range = TimeRange(
                start=start_datetime,
                end=end_datetime,
                timezone="Europe/Amsterdam",  # Default timezone
            )

            # Create query
            GetEmployeeAvailabilityQuery(
                time_range=time_range, shift_type=shift_type,
            )

            # Execute through repository (simplified for now)
            create_unit_of_work()

            # Get all employees and check availability
            users = User.objects.select_related("employee_profile").filter(
                employee_profile__status="active",
            )

            available_employees = []
            for user in users:
                employee = map_django_user_to_employee(user)
                if employee.is_available_for_shift(shift_type, time_range):
                    available_employees.append(
                        {
                            "employee_id": employee.id.value,
                            "name": employee.name,
                            "email": employee.email,
                            "available_for_incidents": employee.available_for_incidents,
                            "available_for_waakdienst": employee.available_for_waakdienst,
                            "current_assignments_count": len(
                                employee.current_assignments,
                            ),
                        },
                    )

            response_data = {
                "time_range": {
                    "start": start_datetime.isoformat(),
                    "end": end_datetime.isoformat(),
                },
                "shift_type": shift_type.value,
                "available_employees": available_employees,
                "total_available": len(available_employees),
            }

            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.exception(f"Error in employee_availability: {e}")
            return Response(
                {"error": "Internal server error", "message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["get"])
    async def shift_coverage(self, request):
        """
        Get shift coverage status for a date range.

        GET /api/orchestrator/shift_coverage/?start_date=2025-08-01&end_date=2025-08-31&department_id=1
        """
        try:
            # Parse query parameters
            start_date_str = request.query_params.get("start_date")
            end_date_str = request.query_params.get("end_date")
            department_id = request.query_params.get("department_id")

            if not all([start_date_str, end_date_str]):
                return Response(
                    {"error": "start_date and end_date are required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()

            # Get shifts in date range
            shifts = Shift.objects.filter(
                start_datetime__date__gte=start_date, start_datetime__date__lte=end_date,
            ).select_related("template", "assigned_employee")

            # Group by date and shift type
            coverage_by_date = {}
            for shift in shifts:
                shift_date = shift.start_datetime.date().isoformat()
                shift_type = shift.template.shift_type

                if shift_date not in coverage_by_date:
                    coverage_by_date[shift_date] = {}

                if shift_type not in coverage_by_date[shift_date]:
                    coverage_by_date[shift_date][shift_type] = {
                        "total_shifts": 0,
                        "assigned_shifts": 0,
                        "unassigned_shifts": 0,
                        "assignments": [],
                    }

                coverage_by_date[shift_date][shift_type]["total_shifts"] += 1

                if shift.assigned_employee:
                    coverage_by_date[shift_date][shift_type]["assigned_shifts"] += 1
                    coverage_by_date[shift_date][shift_type]["assignments"].append(
                        {
                            "shift_id": shift.id,
                            "employee_id": shift.assigned_employee.id,
                            "employee_name": shift.assigned_employee.get_full_name(),
                            "start_time": shift.start_datetime.isoformat(),
                            "end_time": shift.end_datetime.isoformat(),
                        },
                    )
                else:
                    coverage_by_date[shift_date][shift_type]["unassigned_shifts"] += 1

            response_data = {
                "date_range": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                },
                "department_id": department_id,
                "coverage_by_date": coverage_by_date,
                "summary": {
                    "total_days": (end_date - start_date).days + 1,
                    "days_with_coverage": len(coverage_by_date),
                    "days_without_coverage": max(
                        0, (end_date - start_date).days + 1 - len(coverage_by_date),
                    ),
                },
            }

            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.exception(f"Error in shift_coverage: {e}")
            return Response(
                {"error": "Internal server error", "message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# Additional utility views for frontend integration
class OrchestratorStatusView(viewsets.ViewSet):
    """
    Status and health check endpoints for the orchestrator system.
    """

    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["get"])
    def health(self, request):
        """
        Health check endpoint for the orchestrator system.

        GET /api/orchestrator/health/
        """
        try:
            # Basic health checks
            health_status = {
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "version": "2.0.0",
                "components": {
                    "database": "healthy",
                    "orchestrator": "healthy",
                    "cache": "healthy",
                },
            }

            # Check database connectivity
            try:
                User.objects.count()
            except Exception:
                health_status["components"]["database"] = "unhealthy"
                health_status["status"] = "degraded"

            return Response(health_status, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {
                    "status": "unhealthy",
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat(),
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

    @action(detail=False, methods=["get"])
    def metrics(self, request):
        """
        Get orchestrator metrics and statistics.

        GET /api/orchestrator/metrics/
        """
        try:
            # Calculate basic metrics
            total_employees = User.objects.filter(
                employee_profile__status="active",
            ).count()

            total_shifts = Shift.objects.filter(
                start_datetime__gte=datetime.now() - timedelta(days=30),
            ).count()

            assigned_shifts = Shift.objects.filter(
                start_datetime__gte=datetime.now() - timedelta(days=30),
                assigned_employee__isnull=False,
            ).count()

            assignment_rate = (
                (assigned_shifts / total_shifts * 100) if total_shifts > 0 else 0
            )

            metrics = {
                "total_active_employees": total_employees,
                "total_shifts_last_30_days": total_shifts,
                "assigned_shifts_last_30_days": assigned_shifts,
                "assignment_rate_percentage": round(assignment_rate, 2),
                "unassigned_shifts_last_30_days": total_shifts - assigned_shifts,
                "timestamp": datetime.utcnow().isoformat(),
            }

            return Response(metrics, status=status.HTTP_200_OK)

        except Exception as e:
            logger.exception(f"Error in metrics: {e}")
            return Response(
                {"error": "Internal server error", "message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
