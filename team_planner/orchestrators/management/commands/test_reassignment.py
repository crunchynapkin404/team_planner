"""
Django management command to test and demonstrate orchestrator reassignment functionality.
"""

from datetime import date
from datetime import datetime
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.core.management.base import CommandError
from django.utils import timezone

from team_planner.employees.models import RecurringLeavePattern
from team_planner.orchestrators.models import OrchestrationRun
from team_planner.orchestrators.unified import UnifiedOrchestrator
from team_planner.teams.models import Team

User = get_user_model()


class Command(BaseCommand):
    help = "Test and demonstrate orchestrator reassignment functionality"

    def add_arguments(self, parser):
        parser.add_argument(
            "--start-date",
            type=str,
            help="Start date for orchestration (YYYY-MM-DD), defaults to next Monday",
        )
        parser.add_argument(
            "--end-date",
            type=str,
            help="End date for orchestration (YYYY-MM-DD), defaults to 2 weeks from start",
        )
        parser.add_argument(
            "--team-id",
            type=int,
            default=1,
            help="Team ID to schedule for (default: 1)",
        )
        parser.add_argument(
            "--create-test-data",
            action="store_true",
            help="Create test user with recurring leave pattern",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Run in preview mode only (no database changes)",
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS("🚀 Orchestrator Reassignment Test Command"),
        )
        self.stdout.write("=" * 60)

        # Parse dates
        start_date = self._parse_start_date(options["start_date"])
        end_date = self._parse_end_date(options["end_date"], start_date)

        self.stdout.write(
            f"📅 Testing period: {start_date.date()} to {end_date.date()}",
        )

        # Create test data if requested
        if options["create_test_data"]:
            self._create_test_data()

        # Get user for orchestration run
        user = self._get_orchestration_user()

        # Create orchestration run
        run = OrchestrationRun.objects.create(
            name=f"Reassignment Test - {timezone.now().strftime('%Y-%m-%d %H:%M')}",
            description="Testing automatic reassignment for recurring leave conflicts",
            initiated_by=user,
            start_date=start_date.date(),
            end_date=end_date.date(),
            schedule_incidents=True,
            schedule_incidents_standby=False,
            schedule_waakdienst=True,
            status=OrchestrationRun.Status.RUNNING,
        )

        self.stdout.write(f"📝 Created orchestration run: {run.name} (ID: {run.pk})")

        try:
            # Get team for testing
            team = Team.objects.get(pk=options["team_id"])

            # Create orchestrator with reassignment
            orchestrator = UnifiedOrchestrator(
                team=team,
                start_date=start_date,
                end_date=end_date,
                dry_run=options["dry_run"],
            )

            self.stdout.write("🔍 Running orchestration with conflict detection...")

            if options["dry_run"]:
                result = orchestrator.preview_schedule()
                self.stdout.write(
                    self.style.WARNING("📋 DRY RUN - No shifts were actually created"),
                )
            else:
                result = orchestrator.apply_schedule()
                self.stdout.write(self.style.SUCCESS("💾 Shifts created in database"))

            self._display_results(result)

            # Update run status
            run.status = (
                OrchestrationRun.Status.COMPLETED
                if not options["dry_run"]
                else OrchestrationRun.Status.PREVIEW
            )
            run.completed_at = timezone.now()
            run.total_shifts_created = result["total_shifts"]
            run.incidents_shifts_created = result.get("incidents_shifts", 0)
            run.waakdienst_shifts_created = result.get("waakdienst_shifts", 0)
            run.save()

            self.stdout.write(self.style.SUCCESS("🎉 Test completed successfully!"))

        except Exception as e:
            run.status = OrchestrationRun.Status.FAILED
            run.error_message = str(e)
            run.completed_at = timezone.now()
            run.save()

            self.stdout.write(self.style.ERROR(f"❌ Error: {e!s}"))
            msg = f"Orchestration failed: {e!s}"
            raise CommandError(msg)

    def _parse_start_date(self, start_date_str):
        """Parse start date or default to next Monday."""
        if start_date_str:
            try:
                return datetime.strptime(start_date_str, "%Y-%m-%d")
            except ValueError:
                msg = "Invalid start date format. Use YYYY-MM-DD"
                raise CommandError(msg)

        # Default to next Monday
        today = date.today()
        days_until_monday = (7 - today.weekday()) % 7
        if days_until_monday == 0:  # Today is Monday
            days_until_monday = 7  # Next Monday
        next_monday = today + timedelta(days=days_until_monday)
        return datetime.combine(next_monday, datetime.min.time())

    def _parse_end_date(self, end_date_str, start_date):
        """Parse end date or default to 2 weeks from start."""
        if end_date_str:
            try:
                return datetime.strptime(end_date_str, "%Y-%m-%d")
            except ValueError:
                msg = "Invalid end date format. Use YYYY-MM-DD"
                raise CommandError(msg)

        # Default to 2 weeks from start
        return start_date + timedelta(weeks=2)

    def _create_test_data(self):
        """Create test user with recurring leave pattern."""
        self.stdout.write("🧪 Creating test data...")

        # Get or create test user
        test_user, created = User.objects.get_or_create(
            username="test_reassignment_user",
            defaults={
                "name": "Test Reassignment User",
                "email": "test.reassignment@example.com",
                "is_staff": True,
            },
        )

        if created:
            self.stdout.write(f"✅ Created test user: {test_user.username}")
        else:
            self.stdout.write(f"📋 Using existing test user: {test_user.username}")

        # Create employee profile with availability flags
        from team_planner.employees.models import EmployeeProfile

        profile, profile_created = EmployeeProfile.objects.get_or_create(
            user=test_user,
            defaults={
                "employee_id": "TEST001",
                "hire_date": timezone.now().date(),
                "available_for_incidents": True,
                "available_for_waakdienst": True,
                "status": "active",
            },
        )

        if profile_created:
            self.stdout.write("✅ Created employee profile with shift availability")
        else:
            # Update availability flags if profile already exists
            profile.available_for_incidents = True
            profile.available_for_waakdienst = True
            profile.status = "active"
            profile.save()
            self.stdout.write("📋 Updated employee profile availability")

        # Create recurring leave pattern
        pattern, created = RecurringLeavePattern.objects.get_or_create(
            employee=test_user,
            name="Monday Morning Unavailable",
            day_of_week=0,  # Monday
            defaults={
                "frequency": RecurringLeavePattern.Frequency.WEEKLY,
                "coverage_type": RecurringLeavePattern.CoverageType.MORNING,
                "pattern_start_date": date.today(),
                "effective_from": date.today(),
                "is_active": True,
                "notes": "Test pattern for reassignment demo",
            },
        )

        if created:
            self.stdout.write(f"✅ Created recurring leave pattern: {pattern.name}")
        else:
            self.stdout.write(f"📋 Using existing pattern: {pattern.name}")

    def _get_orchestration_user(self):
        """Get a user to use for the orchestration run."""
        # Try to get staff user first
        staff_user = User.objects.filter(is_staff=True).first()
        if staff_user:
            return staff_user

        # Fall back to any user
        user = User.objects.first()
        if user:
            return user

        msg = "No users found. Please create at least one user."
        raise CommandError(msg)

    def _display_results(self, result):
        """Display orchestration results."""
        self.stdout.write("\\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("📊 ORCHESTRATION RESULTS"))
        self.stdout.write("=" * 60)

        self.stdout.write(f"Total shifts generated: {result['total_shifts']}")
        self.stdout.write(f"Incidents shifts: {result.get('incidents_shifts', 0)}")
        self.stdout.write(f"Waakdienst shifts: {result.get('waakdienst_shifts', 0)}")
        self.stdout.write(f"Employees assigned: {result['employees_assigned']}")
        self.stdout.write(
            f"Average fairness score: {result.get('average_fairness', 0):.2f}",
        )

        # Display reassignment summary
        reassignment_summary = result.get("reassignment_summary")
        if reassignment_summary:
            self.stdout.write("\\n" + self.style.WARNING("🔄 REASSIGNMENT SUMMARY"))
            self.stdout.write("-" * 30)
            self.stdout.write(
                f"Total conflicts detected: {reassignment_summary['total_conflicts_detected']}",
            )
            self.stdout.write(
                f"Successful reassignments: {reassignment_summary['successful_reassignments']}",
            )
            self.stdout.write(
                f"Split coverage reassignments: {reassignment_summary.get('split_coverage_reassignments', 0)}",
            )
            self.stdout.write(
                f"Failed reassignments: {reassignment_summary['failed_reassignments']}",
            )
            self.stdout.write(
                f"Manual interventions required: {reassignment_summary['manual_interventions_required']}",
            )

            if reassignment_summary["total_conflicts_detected"] > 0:
                self.stdout.write("\\n📋 Conflicts by type:")
                for conflict_type, count in reassignment_summary[
                    "conflicts_by_type"
                ].items():
                    if count > 0:
                        self.stdout.write(f"  - {conflict_type}: {count}")

            if reassignment_summary["reassignments"]:
                self.stdout.write("\\n🔄 Reassignment details:")
                for i, reassignment in enumerate(
                    reassignment_summary["reassignments"], 1,
                ):
                    original_emp = reassignment["original_employee"]
                    new_emp = reassignment.get("new_employee")
                    status = (
                        self.style.SUCCESS("✅ SUCCESS")
                        if reassignment["success"]
                        else self.style.ERROR("❌ FAILED")
                    )
                    strategy = reassignment.get("strategy", "unknown")

                    self.stdout.write(f"  {i}. {status} ({strategy})")
                    self.stdout.write(f"     From: {original_emp.username}")

                    if strategy == "split_coverage":
                        split_info = reassignment.get("split_info", {})
                        self.stdout.write(
                            f"     Split Coverage: {split_info.get('kept_days', 0)} days kept, {split_info.get('reassigned_days', 0)} days to {new_emp.username if new_emp else 'unknown'}",
                        )
                    else:
                        self.stdout.write(
                            f"     To: {new_emp.username if new_emp else 'Manual intervention required'}",
                        )

                    self.stdout.write(f"     Reason: {reassignment['reason']}")
                    self.stdout.write(
                        f"     Conflicts resolved: {len(reassignment['conflicts_resolved'])}",
                    )
        else:
            self.stdout.write(
                "\\n"
                + self.style.SUCCESS(
                    "✅ No conflicts detected - no reassignments needed!",
                ),
            )

        # Display duplicate information if available
        if result.get("potential_duplicates"):
            self.stdout.write("\\n" + self.style.WARNING("⚠️  POTENTIAL DUPLICATES"))
            self.stdout.write(
                f"Found {len(result['potential_duplicates'])} potential duplicate shifts",
            )

        if result.get("skipped_duplicates"):
            self.stdout.write("\\n" + self.style.WARNING("⚠️  SKIPPED DUPLICATES"))
            self.stdout.write(
                f"Skipped {len(result['skipped_duplicates'])} duplicate shifts during creation",
            )
