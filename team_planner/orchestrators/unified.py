"""
Unified Orchestrator Interface

This module provides a unified interface to the split orchestrator system,
maintaining compatibility with existing views while using the new specialized
orchestrators under the hood.
"""

import logging
from datetime import datetime
from datetime import timedelta

from django.utils import timezone

from team_planner.shifts.models import ShiftType
from team_planner.teams.models import Team

from .incidents import IncidentsOrchestrator
from .incidents_standby import IncidentsStandbyOrchestrator
from .models import OrchestrationRun
from .waakdienst import WaakdienstOrchestrator

try:
    from .adapters.waakdienst_adapter import WaakdienstAdapter
    from .adapters.waakdienst_adapter import waakdienst_adapter_enabled
except Exception:  # pragma: no cover - adapter optional
    WaakdienstAdapter = None  # type: ignore[assignment]

    def waakdienst_adapter_enabled() -> bool:  # type: ignore[func-assign]
        return False


logger = logging.getLogger(__name__)


class UnifiedOrchestrator:
    """
    Unified interface that routes to appropriate specialized orchestrators.

    This maintains compatibility with existing views while using the new
    split orchestrator architecture under the hood.
    """

    def __init__(
        self,
        team: Team,
        start_date: datetime,
        end_date: datetime,
        shift_types: list[ShiftType] | None = None,
        dry_run: bool = True,
        user=None,
    ):
        self.team = team
        self.start_date = start_date
        self.end_date = end_date
        self.shift_types = shift_types or list(ShiftType)
        self.dry_run = dry_run
        self.user = user  # For orchestration run tracking

        # Track results from both orchestrators
        self.results = {"assignments": [], "errors": [], "warnings": [], "stats": {}}

        # Initialize save operation tracking
        self.created_shifts = 0
        self.updated_shifts = 0
        self.conflicts_resolved = 0

        # Initialize specialized orchestrators
        self.incidents_orchestrator = None
        self.incidents_standby_orchestrator = None
        self.waakdienst_orchestrator = None

        # Create separate orchestrators for incidents and incidents-standby
        if ShiftType.INCIDENTS in self.shift_types:
            self.incidents_orchestrator = IncidentsOrchestrator(
                start_date=start_date, end_date=end_date, team_id=team.pk,
            )

        if ShiftType.INCIDENTS_STANDBY in self.shift_types:
            self.incidents_standby_orchestrator = IncidentsStandbyOrchestrator(
                start_date=start_date, end_date=end_date, team_id=team.pk,
            )

        if self._should_handle_waakdienst():
            base_waakdienst = WaakdienstOrchestrator(team_id=team.pk)
            # Wrap with adapter only when feature flag enabled
            if WaakdienstAdapter and waakdienst_adapter_enabled():
                self.waakdienst_orchestrator = WaakdienstAdapter(base_waakdienst)  # type: ignore[assignment]
            else:
                self.waakdienst_orchestrator = base_waakdienst

    def _should_handle_incidents(self) -> bool:
        """Check if we should handle incidents shifts."""
        return ShiftType.INCIDENTS in self.shift_types

    def _should_handle_incidents_standby(self) -> bool:
        """Check if we should handle incidents-standby shifts."""
        return ShiftType.INCIDENTS_STANDBY in self.shift_types

    def _should_handle_waakdienst(self) -> bool:
        """Check if we should handle waakdienst shifts."""
        return ShiftType.WAAKDIENST in self.shift_types

    def preview_schedule(self) -> dict:
        """Generate a preview without saving to database."""
        logger.info(
            f"Creating preview for team {self.team.name} from {self.start_date} to {self.end_date}",
        )

        # Run incidents orchestrator if needed
        if self.incidents_orchestrator:
            try:
                incidents_result = self._run_incidents_orchestrator()
                self._merge_results("incidents", incidents_result)
            except Exception as e:
                logger.exception(f"Incidents orchestrator failed: {e}")
                self.results["errors"].append(f"Incidents scheduling failed: {e!s}")

        # Run incidents-standby orchestrator if needed
        if self.incidents_standby_orchestrator:
            try:
                standby_result = self._run_incidents_standby_orchestrator()
                self._merge_results("incidents_standby", standby_result)
            except Exception as e:
                logger.exception(f"Incidents-Standby orchestrator failed: {e}")
                self.results["errors"].append(
                    f"Incidents-Standby scheduling failed: {e!s}",
                )

        # Run waakdienst orchestrator if needed
        if self.waakdienst_orchestrator:
            try:
                waakdienst_result = self._run_waakdienst_orchestrator()
                self._merge_results("waakdienst", waakdienst_result)
            except Exception as e:
                logger.exception(f"Waakdienst orchestrator failed: {e}")
                self.results["errors"].append(f"Waakdienst scheduling failed: {e!s}")

        # Format results for compatibility with existing views
        return self._format_preview_result()

    def apply_schedule(self) -> dict:
        """Generate and save the schedule to database."""
        if self.dry_run:
            logger.warning(
                "apply_schedule called but dry_run=True, switching to preview mode",
            )
            return self.preview_schedule()

        logger.info(
            f"Applying schedule for team {self.team.name} from {self.start_date} to {self.end_date}",
        )

        # Use existing orchestration run if available (for legacy compatibility)
        orchestration_run = getattr(self, "orchestration_run", None)
        if orchestration_run:
            run = orchestration_run
        else:
            # Create orchestration run record
            run = OrchestrationRun.objects.create(
                name=f"Split Orchestrator - {self.team.name}",
                description="Automated scheduling using split orchestrator architecture",
                start_date=self.start_date.date(),
                end_date=self.end_date.date(),
                schedule_incidents=ShiftType.INCIDENTS in self.shift_types,
                schedule_incidents_standby=ShiftType.INCIDENTS_STANDBY
                in self.shift_types,
                schedule_waakdienst=ShiftType.WAAKDIENST in self.shift_types,
                status=OrchestrationRun.Status.RUNNING,
                initiated_by=self.user,
            )

        try:
            # Run orchestrators
            total_assignments = 0


            if self.incidents_orchestrator:
                incidents_result = self._run_incidents_orchestrator(save=True)
                self._merge_results("incidents", incidents_result)
                total_assignments += len(incidents_result.get("assignments", []))

            if self.incidents_standby_orchestrator:
                standby_result = self._run_incidents_standby_orchestrator(save=True)
                self._merge_results("incidents_standby", standby_result)
                total_assignments += len(standby_result.get("assignments", []))

            if self.waakdienst_orchestrator:
                waakdienst_result = self._run_waakdienst_orchestrator(save=True)
                self._merge_results("waakdienst", waakdienst_result)
                total_assignments += len(waakdienst_result.get("assignments", []))


            # Update run status
            run.status = OrchestrationRun.Status.COMPLETED
            run.completed_at = timezone.now()
            run.total_shifts_created = total_assignments
            if self.results["errors"]:
                run.error_message = "\n".join(self.results["errors"])
            if self.results["warnings"]:
                run.execution_log = "Warnings:\n" + "\n".join(self.results["warnings"])
            run.save()

            # Create result records and actual shifts for individual assignments
            created_shifts = 0

            # Import here to avoid circular imports
            from team_planner.shifts.models import Shift

            # Process all assignments
            for i, assignment in enumerate(self.results["assignments"], 1):
                try:
                    # Extract values carefully
                    template = assignment.get("template")
                    employee_id = assignment.get("assigned_employee_id")
                    start_dt = assignment.get("start_datetime")
                    end_dt = assignment.get("end_datetime")

                    # Validate all fields are present
                    if not all([template, employee_id, start_dt, end_dt]):
                        continue

                    # Check if shift already exists
                    existing_shift = Shift.objects.filter(
                        template=template,
                        assigned_employee_id=employee_id,
                        start_datetime=start_dt,
                        end_datetime=end_dt,
                    ).first()

                    if existing_shift:
                        continue

                    # Create shift
                    Shift.objects.create(
                        template=template,
                        assigned_employee_id=employee_id,
                        start_datetime=start_dt,
                        end_datetime=end_dt,
                        status=Shift.Status.SCHEDULED,
                    )

                    created_shifts += 1

                    if i <= 5 or i % 50 == 0:  # Log first 5 and every 50th
                        pass

                except Exception as e:
                    logger.exception(f"Failed to create shift {i}: {e}")
                    # Continue with next assignment instead of failing completely
                    continue


            # Update the run with actual created shifts count
            run.total_shifts_created = created_shifts
            run.save()

            logger.info(
                f"Successfully created {created_shifts} shifts for team {self.team.name}",
            )

        except Exception as e:
            run.status = OrchestrationRun.Status.FAILED
            run.completed_at = timezone.now()
            run.error_message = str(e)
            run.save()
            logger.exception(f"Orchestration failed for team {self.team.name}: {e}")
            raise

        return self._format_apply_result(run)

    def _run_incidents_orchestrator(self, save: bool = False) -> dict:
        """Run the incidents orchestrator for the specified date range."""
        if not self.incidents_orchestrator:
            return {"assignments": [], "errors": [], "warnings": [], "stats": {}}

        try:
            # The new IncidentsOrchestrator uses the BaseOrchestrator.generate_schedule() interface
            if save:
                # Create orchestration run for tracking
                from .models import OrchestrationRun

                run = OrchestrationRun.objects.create(
                    name=f"Incidents - {self.team.name}",
                    description="Automated incidents scheduling",
                    start_date=self.start_date.date(),
                    end_date=self.end_date.date(),
                    schedule_incidents=True,
                    schedule_incidents_standby=False,
                    schedule_waakdienst=False,
                    status=OrchestrationRun.Status.RUNNING,
                    initiated_by=self.user,
                )

                # Generate and save schedule
                result = self.incidents_orchestrator.generate_schedule(
                    orchestration_run=run,
                )

                # Update run status
                run.status = OrchestrationRun.Status.COMPLETED
                run.completed_at = timezone.now()
                run.save()

            else:
                # Preview mode - don't save
                result = self.incidents_orchestrator.generate_schedule()

            # Convert to expected format
            assignments = result.get("assignments", [])
            return {
                "assignments": assignments,
                "errors": result.get("errors", []),
                "warnings": result.get("warnings", []),
                "stats": {
                    "weeks_generated": len(assignments) // 5
                    if assignments
                    else 0,  # 5 days per week
                    "business_days": len(assignments),
                },
            }

        except Exception as e:
            logger.exception(f"IncidentsOrchestrator failed: {e}")
            import traceback

            traceback.print_exc()
            return {
                "assignments": [],
                "errors": [f"Incidents orchestrator failed: {e!s}"],
                "warnings": [],
                "stats": {},
            }

    def _run_incidents_standby_orchestrator(self, save: bool = False) -> dict:
        """Run the incidents-standby orchestrator for the specified date range."""
        if not self.incidents_standby_orchestrator:
            return {"assignments": [], "errors": [], "warnings": [], "stats": {}}

        try:
            # The new IncidentsStandbyOrchestrator uses the BaseOrchestrator.generate_schedule() interface
            if save:
                # Create orchestration run for tracking
                from .models import OrchestrationRun

                run = OrchestrationRun.objects.create(
                    name=f"Incidents-Standby - {self.team.name}",
                    description="Automated incidents-standby scheduling",
                    start_date=self.start_date.date(),
                    end_date=self.end_date.date(),
                    schedule_incidents=False,
                    schedule_incidents_standby=True,
                    schedule_waakdienst=False,
                    status=OrchestrationRun.Status.RUNNING,
                    initiated_by=self.user,
                )

                # Generate and save schedule
                result = self.incidents_standby_orchestrator.generate_schedule(
                    orchestration_run=run,
                )

                # Update run status
                run.status = OrchestrationRun.Status.COMPLETED
                run.completed_at = timezone.now()
                run.save()

            else:
                # Preview mode - don't save
                result = self.incidents_standby_orchestrator.generate_schedule()

            # Convert to expected format
            assignments = result.get("assignments", [])
            return {
                "assignments": assignments,
                "errors": result.get("errors", []),
                "warnings": result.get("warnings", []),
                "stats": {
                    "weeks_generated": len(assignments) // 5
                    if assignments
                    else 0,  # 5 days per week
                    "business_days": len(assignments),
                },
            }

        except Exception as e:
            logger.exception(f"IncidentsStandbyOrchestrator failed: {e}")
            import traceback

            traceback.print_exc()
            return {
                "assignments": [],
                "errors": [f"Incidents-Standby orchestrator failed: {e!s}"],
                "warnings": [],
                "stats": {},
            }

    def _run_waakdienst_orchestrator(self, save: bool = False) -> dict:
        """Run the waakdienst orchestrator for the specified date range."""
        # If adapter path is enabled, use uniform interface
        if (
            self.waakdienst_orchestrator
            and waakdienst_adapter_enabled()
            and hasattr(self.waakdienst_orchestrator, "generate_schedule")
        ):
            # Use adapter's generate_schedule; it defaults to dry_run=True which matches preview path
            # For save=True, unified.apply_schedule consolidates saving, so adapter preview is sufficient.
            # Adapter defaults to dry_run=True which is correct for preview; for save path we still preview here
            result = self.waakdienst_orchestrator.generate_schedule(
                self.start_date, self.end_date,
            )
            assignments = result.get("assignments", [])
            return {
                "assignments": assignments,
                "errors": result.get("errors", []),
                "warnings": result.get("warnings", []),
                "stats": {
                    "weeks_generated": len(assignments) // 21 if assignments else 0,
                    "evening_shifts": len(
                        [
                            a
                            for a in assignments
                            if str(
                                getattr(
                                    a.get("shift_type"), "value", a.get("shift_type"),
                                ),
                            )
                            == "waakdienst"
                        ],
                    ),
                },
            }

        current_date = self.start_date
        all_assignments = []

        # Align to Wednesday 17:00 start
        while current_date.weekday() != 2 or current_date.hour < 17:
            if current_date.weekday() == 2 and current_date.hour < 17:
                current_date = current_date.replace(
                    hour=17, minute=0, second=0, microsecond=0,
                )
                break
            current_date += timedelta(days=1)
            current_date = current_date.replace(
                hour=17, minute=0, second=0, microsecond=0,
            )

        while current_date < self.end_date:
            # Calculate week end (next Wednesday 08:00)
            week_end = current_date + timedelta(days=7)
            week_end = week_end.replace(hour=8, minute=0, second=0, microsecond=0)

            if current_date >= self.end_date:
                break

            # Generate waakdienst week
            week_result = {}
            if self.waakdienst_orchestrator is not None:
                week_result = (
                    self.waakdienst_orchestrator.generate_waakdienst_week_assignments(
                        current_date, dry_run=(not save),
                    )
                )

            if week_result.get("assignments"):
                all_assignments.extend(week_result["assignments"])

            # Move to next Wednesday
            current_date = week_end.replace(hour=17)

        return {
            "assignments": all_assignments,
            "errors": [],
            "warnings": [],
            "stats": {
                "weeks_generated": len(all_assignments) // 21
                if all_assignments
                else 0,  # 21 shifts per week
                "evening_shifts": len(
                    [
                        a
                        for a in all_assignments
                        if str(
                            getattr(a.get("shift_type"), "value", a.get("shift_type")),
                        )
                        == "waakdienst"
                    ],
                ),
            },
        }

    def _merge_results(self, orchestrator_type: str, result: dict):
        """Merge results from an orchestrator into the unified results."""
        self.results["assignments"].extend(result.get("assignments", []))
        self.results["errors"].extend(result.get("errors", []))
        self.results["warnings"].extend(result.get("warnings", []))
        self.results["stats"][orchestrator_type] = result.get("stats", {})

    def _format_preview_result(self) -> dict:
        """Format results for preview display with legacy API compatibility."""

        # Calculate shift type counts (handle enum or string values)
        def st(val):
            try:
                from team_planner.shifts.models import ShiftType as ST

                if val in (ST.INCIDENTS, ST.INCIDENTS_STANDBY, ST.WAAKDIENST):
                    return val.value  # type: ignore[attr-defined]
            except Exception:
                pass
            return str(val) if val is not None else ""

        incidents_shifts = len(
            [
                a
                for a in self.results["assignments"]
                if st(a.get("shift_type")) == "incidents"
            ],
        )
        incidents_standby_shifts = len(
            [
                a
                for a in self.results["assignments"]
                if st(a.get("shift_type")) == "incidents_standby"
            ],
        )
        waakdienst_shifts = len(
            [
                a
                for a in self.results["assignments"]
                if st(a.get("shift_type")) == "waakdienst"
            ],
        )
        total_shifts = len(self.results["assignments"])

        # Extract fairness scores from assignments and calculate metrics
        fairness_scores = {}
        unique_employees = set()
        for assignment in self.results["assignments"]:
            emp_id = assignment.get("employee_id") or assignment.get(
                "assigned_employee_id",
            )
            if emp_id:
                fairness_scores[emp_id] = assignment.get("fairness_after", 0.0)
                unique_employees.add(emp_id)

        # Calculate average fairness
        average_fairness = (
            sum(fairness_scores.values()) / len(fairness_scores)
            if fairness_scores
            else 0.0
        )

        return {
            "success": len(self.results["errors"]) == 0,
            "assignments": self.results["assignments"],
            "total_assignments": total_shifts,  # New format
            "total_shifts": total_shifts,  # Legacy compatibility
            "total_shifts_created": total_shifts,  # For callers expecting created count in both modes
            "incidents_shifts": incidents_shifts,  # Legacy compatibility
            "incidents_standby_shifts": incidents_standby_shifts,  # Legacy compatibility
            "waakdienst_shifts": waakdienst_shifts,  # Legacy compatibility
            "employees_assigned": len(unique_employees),  # Legacy compatibility
            "fairness_scores": fairness_scores,  # Legacy compatibility
            "average_fairness": average_fairness,  # Legacy compatibility
            "errors": self.results["errors"],
            "warnings": self.results["warnings"],
            "stats": self.results["stats"],
            "orchestrator_type": "split_orchestrator",
            "start_date": self.start_date,
            "end_date": self.end_date,
            "shift_types": self.shift_types,
        }

    def _format_save_result(self) -> dict:
        """Format results for save operations with legacy API compatibility."""

        # Calculate shift type counts (handle enum or string values)
        def st2(val):
            try:
                from team_planner.shifts.models import ShiftType as ST

                if val in (ST.INCIDENTS, ST.INCIDENTS_STANDBY, ST.WAAKDIENST):
                    return val.value  # type: ignore[attr-defined]
            except Exception:
                pass
            return str(val) if val is not None else ""

        incidents_shifts = len(
            [
                a
                for a in self.results["assignments"]
                if st2(a.get("shift_type")) == "incidents"
            ],
        )
        incidents_standby_shifts = len(
            [
                a
                for a in self.results["assignments"]
                if st2(a.get("shift_type")) == "incidents_standby"
            ],
        )
        waakdienst_shifts = len(
            [
                a
                for a in self.results["assignments"]
                if st2(a.get("shift_type")) == "waakdienst"
            ],
        )
        total_shifts = len(self.results["assignments"])

        # Extract fairness scores from assignments and calculate metrics
        fairness_scores = {}
        unique_employees = set()
        for assignment in self.results["assignments"]:
            emp_id = assignment.get("employee_id") or assignment.get(
                "assigned_employee_id",
            )
            if emp_id:
                fairness_scores[emp_id] = assignment.get("fairness_after", 0.0)
                unique_employees.add(emp_id)

        # Calculate average fairness
        average_fairness = (
            sum(fairness_scores.values()) / len(fairness_scores)
            if fairness_scores
            else 0.0
        )

        return {
            "success": len(self.results["errors"]) == 0,
            "total_assignments": total_shifts,  # New format
            "total_shifts": total_shifts,  # Legacy compatibility
            "incidents_shifts": incidents_shifts,  # Legacy compatibility
            "incidents_standby_shifts": incidents_standby_shifts,  # Legacy compatibility
            "waakdienst_shifts": waakdienst_shifts,  # Legacy compatibility
            "employees_assigned": len(unique_employees),  # Legacy compatibility
            "fairness_scores": fairness_scores,  # Legacy compatibility
            "average_fairness": average_fairness,  # Legacy compatibility
            "errors": self.results["errors"],
            "warnings": self.results["warnings"],
            "stats": self.results["stats"],
            "created_shifts": self.created_shifts,
            "updated_shifts": self.updated_shifts,
            "conflicts_resolved": self.conflicts_resolved,
            "orchestrator_type": "split_orchestrator",
        }

    def _format_apply_result(self, run: OrchestrationRun) -> dict:
        """Format results for applied schedule with legacy API compatibility."""
        # Calculate shift type counts from results
        incidents_shifts = len(
            [
                a
                for a in self.results["assignments"]
                if a.get("shift_type") == "incidents"
            ],
        )
        incidents_standby_shifts = len(
            [
                a
                for a in self.results["assignments"]
                if a.get("shift_type") == "incidents-standby"
            ],
        )
        waakdienst_shifts = len(
            [
                a
                for a in self.results["assignments"]
                if a.get("shift_type") == "waakdienst"
            ],
        )

        # Calculate unique employees assigned
        unique_employees = set()
        for assignment in self.results["assignments"]:
            if assignment.get("assigned_employee_id"):
                unique_employees.add(assignment["assigned_employee_id"])

        return {
            "success": run.status == OrchestrationRun.Status.COMPLETED,
            "run_id": run.pk,
            "assignments_created": run.total_shifts_created,
            "total_shifts": run.total_shifts_created,  # Legacy compatibility
            "incidents_shifts": incidents_shifts,  # Legacy compatibility
            "incidents_standby_shifts": incidents_standby_shifts,  # Legacy compatibility
            "waakdienst_shifts": waakdienst_shifts,  # Legacy compatibility
            "employees_assigned": len(unique_employees),  # API compatibility
            "created_shifts": self.results.get(
                "created_shifts", [],
            ),  # Legacy compatibility
            "errors": [run.error_message] if run.error_message else [],
            "warnings": [run.execution_log] if run.execution_log else [],
            "stats": self.results["stats"],
            "orchestrator_type": "split_orchestrator",
        }


# Maintain backward compatibility
class ShiftOrchestrator(UnifiedOrchestrator):
    """
    Legacy interface for backward compatibility.

    This class provides the same interface as the old ShiftOrchestrator
    but uses the new split orchestrator system internally.
    """

    def __init__(
        self,
        start_date: datetime,
        end_date: datetime,
        schedule_incidents: bool = True,
        schedule_incidents_standby: bool = False,
        schedule_waakdienst: bool = True,
        team: Team | None = None,
        team_id: int | None = None,
        orchestration_run: OrchestrationRun | None = None,
        **kwargs,
    ):
        # Convert boolean flags to shift types
        shift_types = []
        if schedule_incidents:
            shift_types.append(ShiftType.INCIDENTS)
        if schedule_incidents_standby:
            shift_types.append(ShiftType.INCIDENTS_STANDBY)
        if schedule_waakdienst:
            shift_types.append(ShiftType.WAAKDIENST)

        # Handle team selection
        if team is None and team_id is not None:
            team = Team.objects.get(pk=team_id)
        elif team is None:
            team = Team.objects.first()
            if team is None:
                msg = "No team available for orchestration"
                raise ValueError(msg)

        # Extract user from orchestration_run if available
        user = (
            orchestration_run.initiated_by if orchestration_run else kwargs.get("user")
        )
        kwargs["user"] = user

        super().__init__(team, start_date, end_date, shift_types, **kwargs)

        # Store orchestration run for legacy compatibility
        self.orchestration_run = orchestration_run


# Export for compatibility
__all__ = ["ShiftOrchestrator", "UnifiedOrchestrator"]
