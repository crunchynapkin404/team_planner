"""
Management command to test the orchestrator with Team 7.

This will create a test orchestration run for the next month to see if
the orchestrator can generate shifts and fill the calendar.

Usage:
    python manage.py test_orchestrator
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import date, datetime, timedelta

from team_planner.orchestrators.algorithms import ShiftOrchestrator
from team_planner.orchestrators.models import OrchestrationRun
from team_planner.shifts.models import Shift
from team_planner.employees.models import EmployeeProfile

User = get_user_model()


class Command(BaseCommand):
    help = 'Test the orchestrator with Team 7 data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--weeks',
            type=int,
            default=4,
            help='Number of weeks to generate shifts for (default: 4)',
        )
        parser.add_argument(
            '--preview-only',
            action='store_true',
            help='Only preview, do not create actual shifts',
        )

    def handle(self, *args, **options):
        weeks = options['weeks']
        preview_only = options['preview_only']
        
        # Calculate date range (next N weeks)
        today = date.today()
        start_date = today + timedelta(days=1)  # Start tomorrow
        end_date = start_date + timedelta(weeks=weeks)
        
        start_datetime = datetime.combine(start_date, datetime.min.time())
        end_datetime = datetime.combine(end_date, datetime.max.time())
        
        self.stdout.write(f'Testing orchestrator for period: {start_date} to {end_date}')
        self.stdout.write(f'Preview only: {preview_only}')
        
        # Check available employees
        incidents_employees = EmployeeProfile.objects.filter(
            status=EmployeeProfile.Status.ACTIVE,
            available_for_incidents=True
        )
        waakdienst_employees = EmployeeProfile.objects.filter(
            status=EmployeeProfile.Status.ACTIVE,
            available_for_waakdienst=True
        )
        
        self.stdout.write(f'\\nAvailable employees:')
        self.stdout.write(f'  - Incidents: {incidents_employees.count()}')
        for emp in incidents_employees:
            skills = list(emp.skills.values_list('name', flat=True))
            self.stdout.write(f'    * {emp.user.username} (skills: {skills})')
        
        self.stdout.write(f'  - Waakdienst: {waakdienst_employees.count()}')
        for emp in waakdienst_employees:
            skills = list(emp.skills.values_list('name', flat=True))
            self.stdout.write(f'    * {emp.user.username} (skills: {skills})')
        
        # Create test user for orchestration run
        test_user, _ = User.objects.get_or_create(
            username='test_orchestrator',
            defaults={'name': 'Test Orchestrator User'}
        )
        
        run = None
        try:
            # Create orchestration run record
            run = OrchestrationRun.objects.create(
                name=f'Test Run - {weeks} weeks',
                description=f'Testing orchestrator with Team 7 for {weeks} weeks',
                initiated_by=test_user,
                start_date=start_date,
                end_date=end_date,
                status=OrchestrationRun.Status.RUNNING
            )
            
            self.stdout.write(f'\\nCreated orchestration run: {run.name} (ID: {run.pk})')
            
            # Create and run orchestrator
            orchestrator = ShiftOrchestrator(start_datetime, end_datetime)
            
            if preview_only:
                self.stdout.write('\\nRunning preview...')
                result = orchestrator.preview_schedule()
                
                run.status = OrchestrationRun.Status.PREVIEW
                run.save()
                
                self.stdout.write(self.style.SUCCESS(f'\\nPREVIEW RESULTS:'))
                self.stdout.write(f'  Total shifts planned: {result.get("total_shifts", 0)}')
                self.stdout.write(f'  Incident shifts: {result.get("incident_shifts", 0)}')
                self.stdout.write(f'  Waakdienst shifts: {result.get("waakdienst_shifts", 0)}')
                
                if 'planned_shifts' in result:
                    self.stdout.write(f'\\n  Planned shifts detail:')
                    for shift_info in result['planned_shifts'][:10]:  # Show first 10
                        self.stdout.write(f'    - {shift_info}')
                    if len(result['planned_shifts']) > 10:
                        self.stdout.write(f'    ... and {len(result["planned_shifts"]) - 10} more')
            else:
                self.stdout.write('\\nApplying schedule (creating actual shifts)...')
                result = orchestrator.apply_schedule()
                
                run.status = OrchestrationRun.Status.COMPLETED
                run.completed_at = timezone.now()
                run.total_shifts_created = result.get('total_shifts', 0)
                run.incidents_shifts_created = result.get('incident_shifts', 0)
                run.waakdienst_shifts_created = result.get('waakdienst_shifts', 0)
                run.save()
                
                self.stdout.write(self.style.SUCCESS(f'\\nORCHESTRATION COMPLETED:'))
                self.stdout.write(f'  Total shifts created: {result.get("total_shifts", 0)}')
                self.stdout.write(f'  Incident shifts: {result.get("incident_shifts", 0)}')
                self.stdout.write(f'  Waakdienst shifts: {result.get("waakdienst_shifts", 0)}')
                
                # Show some created shifts
                created_shifts = result.get('created_shifts', [])
                if created_shifts:
                    self.stdout.write(f'\\n  Sample created shifts:')
                    for shift in created_shifts[:5]:  # Show first 5
                        engineer = shift.assigned_employee.user.username if shift.assigned_employee else 'Unassigned'
                        self.stdout.write(f'    - {shift.template.shift_type}: {engineer} ({shift.start_datetime.date()})')
                
                # Show current shift count
                total_shifts_in_db = Shift.objects.filter(
                    start_datetime__gte=start_datetime,
                    start_datetime__lt=end_datetime
                ).count()
                self.stdout.write(f'\\n  Total shifts now in database for this period: {total_shifts_in_db}')
                
        except Exception as e:
            if run:
                run.status = OrchestrationRun.Status.FAILED
                run.error_message = str(e)
                run.completed_at = timezone.now()
                run.save()
            
            self.stdout.write(self.style.ERROR(f'\\nOrchestration failed: {str(e)}'))
            raise
