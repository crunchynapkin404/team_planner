"""
Django management command to run the orchestrator.

This command provides a CLI interface to the orchestrator system,
allowing scheduled execution and manual orchestration operations.
"""

import asyncio
from datetime import datetime, date, timedelta
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from typing import List

# Infrastructure imports
from infrastructure.services import create_unit_of_work

# Application layer imports
from application.use_cases import OrchestrateScheduleUseCase, SchedulingRequest
from domain.services import FairnessCalculator, ConflictDetector

# Domain imports
from domain.value_objects import DateRange, ShiftType

# Django imports
from team_planner.teams.models import Team


class Command(BaseCommand):
    """
    Django management command for orchestrator operations.
    
    Usage examples:
    python manage.py run_orchestrator --start-date 2025-08-12 --end-date 2025-08-19 --department 1
    python manage.py run_orchestrator --next-week --all-departments
    python manage.py run_orchestrator --current-week --dry-run
    """
    
    help = 'Run the shift orchestrator for specified date ranges and departments'
    
    def add_arguments(self, parser):
        """Add command line arguments."""
        
        # Date range options
        parser.add_argument(
            '--start-date',
            type=str,
            help='Start date in YYYY-MM-DD format'
        )
        parser.add_argument(
            '--end-date', 
            type=str,
            help='End date in YYYY-MM-DD format'
        )
        parser.add_argument(
            '--current-week',
            action='store_true',
            help='Orchestrate for current week (Monday to Sunday)'
        )
        parser.add_argument(
            '--next-week',
            action='store_true',
            help='Orchestrate for next week (Monday to Sunday)'
        )
        parser.add_argument(
            '--weeks-ahead',
            type=int,
            help='Number of weeks ahead to orchestrate (1-12)'
        )
        
        # Department options
        parser.add_argument(
            '--department',
            type=str,
            help='Specific department ID to orchestrate'
        )
        parser.add_argument(
            '--all-departments',
            action='store_true',
            help='Orchestrate for all active departments'
        )
        
        # Shift type options
        parser.add_argument(
            '--shift-types',
            nargs='+',
            choices=['incidents', 'incidents_standby', 'waakdienst'],
            default=['incidents', 'waakdienst'],
            help='Shift types to orchestrate (default: incidents waakdienst)'
        )
        parser.add_argument(
            '--include-standby',
            action='store_true',
            help='Include incidents-standby shifts'
        )
        
        # Execution options
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview changes without saving to database'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force reassignment of existing shifts'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Verbose output with detailed information'
        )
    
    def handle(self, *args, **options):
        """Handle the command execution."""
        
        try:
            # Parse date range
            date_range = self._parse_date_range(options)
            self.stdout.write(f"Date range: {date_range.start} to {date_range.end}")
            
            # Parse departments
            department_ids = self._parse_departments(options)
            self.stdout.write(f"Departments: {department_ids}")
            
            # Parse shift types
            shift_types = [ShiftType(st) for st in options['shift_types']]
            if options['include_standby']:
                shift_types.append(ShiftType.INCIDENTS_STANDBY)
            self.stdout.write(f"Shift types: {[st.value for st in shift_types]}")
            
            # Run orchestrator for each department
            total_results = []
            for department_id in department_ids:
                result = asyncio.run(self._run_orchestrator(
                    date_range=date_range,
                    department_id=department_id,
                    shift_types=shift_types,
                    options=options
                ))
                total_results.append(result)
            
            # Display summary
            self._display_summary(total_results, options)
            
        except CommandError:
            raise
        except Exception as e:
            raise CommandError(f"Orchestrator execution failed: {e}")
    
    def _parse_date_range(self, options) -> DateRange:
        """Parse date range from command options."""
        
        today = date.today()
        
        if options['current_week']:
            # Current week (Monday to Sunday)
            days_since_monday = today.weekday()
            monday = today - timedelta(days=days_since_monday)
            sunday = monday + timedelta(days=6)
            return DateRange(start=monday, end=sunday)
        
        elif options['next_week']:
            # Next week (Monday to Sunday)
            days_since_monday = today.weekday()
            next_monday = today + timedelta(days=(7 - days_since_monday))
            next_sunday = next_monday + timedelta(days=6)
            return DateRange(start=next_monday, end=next_sunday)
        
        elif options['weeks_ahead']:
            weeks = options['weeks_ahead']
            if weeks < 1 or weeks > 12:
                raise CommandError("weeks_ahead must be between 1 and 12")
            
            # N weeks ahead (Monday to Sunday)
            days_since_monday = today.weekday()
            target_monday = today + timedelta(days=(7 * weeks - days_since_monday))
            target_sunday = target_monday + timedelta(days=6)
            return DateRange(start=target_monday, end=target_sunday)
        
        elif options['start_date'] and options['end_date']:
            # Custom date range
            try:
                start_date = datetime.strptime(options['start_date'], '%Y-%m-%d').date()
                end_date = datetime.strptime(options['end_date'], '%Y-%m-%d').date()
                
                if start_date >= end_date:
                    raise CommandError("start_date must be before end_date")
                
                return DateRange(start=start_date, end=end_date)
                
            except ValueError as e:
                raise CommandError(f"Invalid date format: {e}")
        
        else:
            raise CommandError(
                "Must specify date range using --current-week, --next-week, "
                "--weeks-ahead, or --start-date and --end-date"
            )
    
    def _parse_departments(self, options) -> List[str]:
        """Parse department IDs from command options."""
        
        if options['department']:
            # Validate department exists
            try:
                Team.objects.get(id=options['department'])
                return [options['department']]
            except Team.DoesNotExist:
                raise CommandError(f"Department {options['department']} not found")
        
        elif options['all_departments']:
            # Get all active departments
            departments = Team.objects.filter(
                # Add any active filters here
            ).values_list('id', flat=True)
            
            if not departments:
                raise CommandError("No active departments found")
            
            return [str(dept_id) for dept_id in departments]
        
        else:
            raise CommandError(
                "Must specify department using --department or --all-departments"
            )
    
    async def _run_orchestrator(
        self, 
        date_range: DateRange, 
        department_id: str,
        shift_types: List[ShiftType],
        options: dict
    ):
        """Run orchestrator for specific department and date range."""
        
        if options['verbose']:
            self.stdout.write(
                f"\nOrchestrating department {department_id} "
                f"from {date_range.start} to {date_range.end}..."
            )
        
        # Create request
        request = SchedulingRequest(
            date_range=date_range,
            department_ids=[department_id],
            priority_shifts=None,
            exclude_employees=None,
            force_assignments=None,
            constraints={
                'force_reassignment': options.get('force', False),
                'dry_run': options.get('dry_run', False),
                'allow_partial': True
            }
        )
        
        # Execute use case with simplified setup
        uow = create_unit_of_work()
        
        # Create domain services with default config
        from domain.value_objects import TeamConfiguration, BusinessHoursConfiguration
        default_config = TeamConfiguration(
            timezone='Europe/Amsterdam',
            business_hours=BusinessHoursConfiguration(),
            waakdienst_start_day=2,
            waakdienst_start_hour=17,
            waakdienst_end_hour=8,
            skip_incidents_on_holidays=True,
            holiday_calendar='NL'
        )
        
        fairness_calculator = FairnessCalculator(default_config)
        conflict_detector = ConflictDetector()
        
        use_case = OrchestrateScheduleUseCase(uow, fairness_calculator, conflict_detector)
        
        result = await use_case.execute(request)
        
        if options['verbose']:
            self._display_result(result, department_id, options)
        
        return result
    
    def _display_result(self, result, department_id: str, options: dict):
        """Display detailed result for a single department."""
        
        status_color = self.style.SUCCESS if result.success else self.style.ERROR
        
        self.stdout.write(
            status_color(f"\nDepartment {department_id}: {'SUCCESS' if result.success else 'FAILED'}")
        )
        self.stdout.write(f"  Assignments made: {len(result.assignments)}")
        self.stdout.write(f"  Unassigned shifts: {len(result.unassigned_shifts)}")
        self.stdout.write(f"  Conflicts detected: {len(result.conflicts_detected)}")
        
        if result.conflicts_detected:
            self.stdout.write(self.style.WARNING(f"  Conflicts found: {len(result.conflicts_detected)}"))
            for conflict in result.conflicts_detected[:5]:  # Show first 5 conflicts
                self.stdout.write(f"    - {conflict.get('message', 'Unknown conflict')}")
            if len(result.conflicts_detected) > 5:
                self.stdout.write(f"    ... and {len(result.conflicts_detected) - 5} more")
        
        if result.warnings:
            self.stdout.write(self.style.WARNING(f"  Warnings: {len(result.warnings)}"))
            for warning in result.warnings[:3]:  # Show first 3 warnings
                self.stdout.write(f"    - {warning}")
        
        if options.get('dry_run'):
            self.stdout.write(self.style.WARNING("  (DRY RUN - no changes saved)"))
    
    def _display_summary(self, results: List, options: dict):
        """Display summary of all orchestration results."""
        
        self.stdout.write("\n" + "="*50)
        self.stdout.write("ORCHESTRATION SUMMARY")
        self.stdout.write("="*50)
        
        total_departments = len(results)
        successful_departments = sum(1 for r in results if r.success)
        total_assignments = sum(len(r.assignments) for r in results)
        total_conflicts = sum(len(r.conflicts_detected) for r in results)
        total_unassigned = sum(len(r.unassigned_shifts) for r in results)
        
        self.stdout.write(f"Departments processed: {total_departments}")
        self.stdout.write(f"Successful departments: {successful_departments}")
        self.stdout.write(f"Failed departments: {total_departments - successful_departments}")
        self.stdout.write(f"Total assignments made: {total_assignments}")
        self.stdout.write(f"Total conflicts found: {total_conflicts}")
        self.stdout.write(f"Total unassigned shifts: {total_unassigned}")
        
        if total_assignments > 0:
            assignment_rate = (total_assignments / (total_assignments + total_unassigned)) * 100
            self.stdout.write(f"Assignment rate: {assignment_rate:.1f}%")
        
        if options.get('dry_run'):
            self.stdout.write(self.style.WARNING("\nDRY RUN MODE - No changes were saved to the database"))
        else:
            self.stdout.write(self.style.SUCCESS("\nOrchestration completed successfully!"))
        
        # Recommendations
        if total_unassigned > 0:
            self.stdout.write(
                self.style.WARNING(
                    f"\nRecommendation: {total_unassigned} shifts remain unassigned. "
                    "Consider running conflict resolution or checking employee availability."
                )
            )
        
        if total_conflicts > 0:
            self.stdout.write(
                self.style.WARNING(
                    f"\nRecommendation: {total_conflicts} conflicts were found. "
                    "Consider running: python manage.py resolve_conflicts"
                )
            )
