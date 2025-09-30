from datetime import time

from django.core.management.base import BaseCommand

from team_planner.leaves.models import LeaveType


class Command(BaseCommand):
    help = "Create or update leave types with proper conflict handling"

    def handle(self, *args, **options):
        # Vacation - Full unavailable, requires swaps for all shifts
        vacation, created = LeaveType.objects.get_or_create(
            name="Vacation",
            defaults={
                "description": "Full vacation time - unavailable for all shifts",
                "conflict_handling": LeaveType.ConflictHandling.FULL_UNAVAILABLE,
                "requires_approval": True,
                "is_paid": True,
                "color": "#ff6b6b",
                "default_days_per_year": 25.0,
            },
        )
        if not created:
            vacation.conflict_handling = LeaveType.ConflictHandling.FULL_UNAVAILABLE
            vacation.description = "Full vacation time - unavailable for all shifts"
            vacation.save()

        self.stdout.write(
            self.style.SUCCESS(
                f"{'Created' if created else 'Updated'} Vacation leave type",
            ),
        )

        # Leave - Daytime only, available for waakdienst
        leave, created = LeaveType.objects.get_or_create(
            name="Leave",
            defaults={
                "description": "Daytime leave (8-17h) - still available for waakdienst shifts",
                "conflict_handling": LeaveType.ConflictHandling.DAYTIME_ONLY,
                "start_time": time(8, 0),
                "end_time": time(17, 0),
                "requires_approval": True,
                "is_paid": True,
                "color": "#4ecdc4",
                "default_days_per_year": 0.0,
            },
        )
        if not created:
            leave.conflict_handling = LeaveType.ConflictHandling.DAYTIME_ONLY
            leave.start_time = time(8, 0)
            leave.end_time = time(17, 0)
            leave.description = (
                "Daytime leave (8-17h) - still available for waakdienst shifts"
            )
            leave.save()

        self.stdout.write(
            self.style.SUCCESS(
                f"{'Created' if created else 'Updated'} Leave leave type",
            ),
        )

        # Sick Leave - Full unavailable but no swaps required (emergency)
        sick, created = LeaveType.objects.get_or_create(
            name="Sick Leave",
            defaults={
                "description": "Sick leave - unavailable for all shifts",
                "conflict_handling": LeaveType.ConflictHandling.FULL_UNAVAILABLE,
                "requires_approval": False,  # Usually doesn't require pre-approval
                "is_paid": True,
                "color": "#ffa726",
                "default_days_per_year": 0.0,
            },
        )
        if not created:
            sick.conflict_handling = LeaveType.ConflictHandling.FULL_UNAVAILABLE
            sick.description = "Sick leave - unavailable for all shifts"
            sick.save()

        self.stdout.write(
            self.style.SUCCESS(
                f"{'Created' if created else 'Updated'} Sick Leave leave type",
            ),
        )

        # Training - No conflict (can attend training and still be available)
        training, created = LeaveType.objects.get_or_create(
            name="Training",
            defaults={
                "description": "Training/Professional Development - available for emergency shifts",
                "conflict_handling": LeaveType.ConflictHandling.NO_CONFLICT,
                "requires_approval": True,
                "is_paid": True,
                "color": "#9c27b0",
                "default_days_per_year": 5.0,
            },
        )
        if not created:
            training.conflict_handling = LeaveType.ConflictHandling.NO_CONFLICT
            training.description = (
                "Training/Professional Development - available for emergency shifts"
            )
            training.save()

        self.stdout.write(
            self.style.SUCCESS(
                f"{'Created' if created else 'Updated'} Training leave type",
            ),
        )

        self.stdout.write(
            self.style.SUCCESS(
                "Successfully configured all leave types with conflict handling!",
            ),
        )
