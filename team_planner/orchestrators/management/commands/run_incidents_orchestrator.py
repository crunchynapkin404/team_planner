"""
Management command to run the Incidents Orchestrator for next week scheduling.

This command should be run every Monday morning to schedule the upcoming
business week (Monday-Friday) incidents and incidents-standby shifts.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
import logging

from team_planner.teams.models import Team
from team_planner.orchestrators.incidents import IncidentsOrchestrator
from team_planner.orchestrators.models import OrchestrationRun

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Run Incidents Orchestrator for next week scheduling'

    def add_arguments(self, parser):
        parser.add_argument(
            '--team-id',
            type=int,
            help='Specific team ID to schedule (default: all teams)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview mode without saving assignments',
        )
        parser.add_argument(
            '--weeks-ahead',
            type=int,
            default=1,
            help='Number of weeks ahead to schedule (default: 1)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        weeks_ahead = options['weeks_ahead']
        team_id = options.get('team_id')
        
        # Get teams to process
        if team_id:
            teams = Team.objects.filter(id=team_id)
            if not teams.exists():
                self.stdout.write(
                    self.style.ERROR(f'Team with ID {team_id} not found')
                )
                return
        else:
            teams = Team.objects.all()  # All teams

        if not teams.exists():
            self.stdout.write(self.style.WARNING('No active teams found'))
            return

        total_assignments = 0
        total_errors = 0

        for team in teams:
            self.stdout.write(f'\n📋 Processing team: {team.name}')
            
            try:
                # Initialize orchestrator
                orchestrator = IncidentsOrchestrator(team_id=team.pk)
                
                # Calculate next business week start
                now = timezone.now()
                next_week_start = orchestrator.get_next_business_week_start(now)
                
                # Adjust for weeks ahead
                if weeks_ahead > 1:
                    next_week_start += timedelta(weeks=weeks_ahead - 1)
                
                self.stdout.write(
                    f'   🗓️  Scheduling week starting: {next_week_start.strftime("%Y-%m-%d %H:%M")}'
                )
                
                # Generate assignments
                if dry_run:
                    result = orchestrator.generate_business_week_assignments(
                        next_week_start, dry_run=True
                    )
                    assignments_count = len(result.get('assignments', []))
                    self.stdout.write(
                        f'   ✅ Preview: {assignments_count} assignments would be created'
                    )
                    
                else:
                    # Create run record
                    run = OrchestrationRun.objects.create(
                        name=f"Incidents Auto-Schedule - {team.name}",
                        description=f"Automated Monday scheduling for week {next_week_start.strftime('%Y-%m-%d')}",
                        start_date=next_week_start.date(),
                        end_date=(next_week_start + timedelta(days=4)).date(),
                        schedule_incidents=True,
                        schedule_incidents_standby=True,
                        schedule_waakdienst=False,
                        status=OrchestrationRun.Status.RUNNING,
                        initiated_by=None,  # System-initiated
                    )
                    
                    try:
                        result = orchestrator.generate_business_week_assignments(
                            next_week_start, dry_run=False
                        )
                        assignments_count = len(result.get('assignments', []))
                        
                        # Update run
                        run.status = OrchestrationRun.Status.COMPLETED
                        run.completed_at = timezone.now()
                        run.total_shifts_created = assignments_count
                        run.save()
                        
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'   ✅ Created {assignments_count} assignments (Run #{run.pk})'
                            )
                        )
                        total_assignments += assignments_count
                        
                    except Exception as e:
                        run.status = OrchestrationRun.Status.FAILED
                        run.completed_at = timezone.now()
                        run.error_message = str(e)
                        run.save()
                        raise
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'   ❌ Failed: {str(e)}')
                )
                logger.error(f'Incidents orchestration failed for team {team.name}: {e}')
                total_errors += 1

        # Summary
        self.stdout.write(f'\n📊 SUMMARY:')
        self.stdout.write(f'   Teams processed: {teams.count()}')
        if not dry_run:
            self.stdout.write(f'   Total assignments: {total_assignments}')
        self.stdout.write(f'   Errors: {total_errors}')
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('\n🔍 DRY RUN MODE - No assignments were saved')
            )
        else:
            if total_errors == 0:
                self.stdout.write(
                    self.style.SUCCESS('\n🎉 All teams processed successfully!')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'\n⚠️  Completed with {total_errors} errors')
                )
