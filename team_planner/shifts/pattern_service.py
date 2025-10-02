"""Service for managing recurring shift patterns."""

from datetime import date, datetime, timedelta
from typing import List, Optional

from django.db import models, transaction
from django.utils import timezone

from team_planner.shifts.models import RecurringShiftPattern, Shift


class RecurringPatternService:
    """Service for generating shifts from recurring patterns."""

    @staticmethod
    def generate_shifts_for_pattern(
        pattern: RecurringShiftPattern,
        end_date: Optional[date] = None,
        skip_existing: bool = True,
    ) -> List[Shift]:
        """
        Generate shifts for a recurring pattern up to a specified date.
        
        Args:
            pattern: The recurring pattern to generate shifts from
            end_date: Generate shifts up to this date (defaults to 3 months from now)
            skip_existing: Skip dates that already have shifts
            
        Returns:
            List of created Shift objects
        """
        if not pattern.is_active:
            return []
        
        if end_date is None:
            end_date = date.today() + timedelta(days=90)
        
        # Respect pattern end date
        if pattern.pattern_end_date and end_date > pattern.pattern_end_date:
            end_date = pattern.pattern_end_date
        
        # Start from last generated date or pattern start date
        start_date = pattern.last_generated_date + timedelta(days=1) if pattern.last_generated_date else pattern.pattern_start_date
        
        if start_date > end_date:
            return []
        
        # Generate dates based on recurrence type
        shift_dates = RecurringPatternService._generate_dates(
            pattern, start_date, end_date
        )
        
        created_shifts = []
        
        with transaction.atomic():
            for shift_date in shift_dates:
                # Check for existing shift
                if skip_existing and pattern.assigned_employee:
                    existing = Shift.objects.filter(
                        assigned_employee=pattern.assigned_employee,
                        start_datetime__date=shift_date,
                        template=pattern.template,
                    ).exists()
                    if existing:
                        continue
                
                # Create shift datetime
                start_datetime = datetime.combine(shift_date, pattern.start_time)
                end_datetime = datetime.combine(shift_date, pattern.end_time)
                
                # Make timezone aware
                if timezone.is_aware(datetime.now()):
                    start_datetime = timezone.make_aware(start_datetime)
                    end_datetime = timezone.make_aware(end_datetime)
                
                # Handle overnight shifts
                if pattern.end_time < pattern.start_time:
                    end_datetime += timedelta(days=1)
                
                # Create shift
                shift = Shift.objects.create(
                    template=pattern.template,
                    assigned_employee=pattern.assigned_employee,
                    start_datetime=start_datetime,
                    end_datetime=end_datetime,
                    auto_assigned=False,
                    assignment_reason=f"Generated from pattern: {pattern.name}",
                )
                created_shifts.append(shift)
            
            # Update last generated date
            if shift_dates:
                pattern.last_generated_date = max(shift_dates)
                pattern.save(update_fields=["last_generated_date"])
        
        return created_shifts

    @staticmethod
    def _generate_dates(
        pattern: RecurringShiftPattern,
        start_date: date,
        end_date: date,
    ) -> List[date]:
        """Generate list of dates based on recurrence rules."""
        dates = []
        current_date = start_date
        
        if pattern.recurrence_type == RecurringShiftPattern.RecurrenceType.DAILY:
            while current_date <= end_date:
                dates.append(current_date)
                current_date += timedelta(days=1)
        
        elif pattern.recurrence_type == RecurringShiftPattern.RecurrenceType.WEEKLY:
            # Generate dates for specified weekdays
            while current_date <= end_date:
                if current_date.weekday() in pattern.weekdays:
                    dates.append(current_date)
                current_date += timedelta(days=1)
        
        elif pattern.recurrence_type == RecurringShiftPattern.RecurrenceType.BIWEEKLY:
            # Get reference week (first week of pattern)
            reference_week = start_date.isocalendar()[1]
            
            while current_date <= end_date:
                current_week = current_date.isocalendar()[1]
                # Check if it's an "on" week (even/odd based on reference)
                if (current_week - reference_week) % 2 == 0:
                    if current_date.weekday() in pattern.weekdays:
                        dates.append(current_date)
                current_date += timedelta(days=1)
        
        elif pattern.recurrence_type == RecurringShiftPattern.RecurrenceType.MONTHLY:
            if pattern.day_of_month:
                current = start_date.replace(day=1)  # Start of month
                
                while current <= end_date:
                    try:
                        # Try to create date with specified day
                        target_date = current.replace(day=pattern.day_of_month)
                        if start_date <= target_date <= end_date:
                            dates.append(target_date)
                    except ValueError:
                        # Day doesn't exist in this month (e.g., Feb 31)
                        pass
                    
                    # Move to next month
                    if current.month == 12:
                        current = current.replace(year=current.year + 1, month=1)
                    else:
                        current = current.replace(month=current.month + 1)
        
        return sorted(dates)

    @staticmethod
    def preview_pattern_dates(
        pattern: RecurringShiftPattern,
        preview_days: int = 30,
    ) -> List[date]:
        """
        Preview dates that would be generated for a pattern.
        
        Args:
            pattern: Pattern to preview
            preview_days: Number of days to preview
            
        Returns:
            List of dates
        """
        start_date = pattern.pattern_start_date
        end_date = date.today() + timedelta(days=preview_days)
        
        if pattern.pattern_end_date and end_date > pattern.pattern_end_date:
            end_date = pattern.pattern_end_date
        
        return RecurringPatternService._generate_dates(pattern, start_date, end_date)

    @staticmethod
    def get_patterns_needing_generation(days_ahead: int = 14) -> List[RecurringShiftPattern]:
        """
        Get patterns that need shift generation.
        
        Args:
            days_ahead: Generate shifts this many days ahead
            
        Returns:
            List of patterns that should generate shifts
        """
        target_date = date.today() + timedelta(days=days_ahead)
        
        patterns = RecurringShiftPattern.objects.filter(
            is_active=True,
            pattern_start_date__lte=target_date,
        ).filter(
            models.Q(pattern_end_date__isnull=True) | models.Q(pattern_end_date__gte=date.today())
        ).filter(
            models.Q(last_generated_date__isnull=True) | models.Q(last_generated_date__lt=target_date)
        )
        
        return list(patterns)

    @staticmethod
    def bulk_generate_shifts(days_ahead: int = 14) -> dict:
        """
        Generate shifts for all active patterns.
        
        Args:
            days_ahead: Generate shifts this many days ahead
            
        Returns:
            Dictionary with generation statistics
        """
        patterns = RecurringPatternService.get_patterns_needing_generation(days_ahead)
        end_date = date.today() + timedelta(days=days_ahead)
        
        total_shifts = 0
        pattern_results = []
        
        for pattern in patterns:
            try:
                shifts = RecurringPatternService.generate_shifts_for_pattern(
                    pattern, end_date=end_date
                )
                total_shifts += len(shifts)
                pattern_results.append({
                    "pattern_id": pattern.id,
                    "pattern_name": pattern.name,
                    "shifts_created": len(shifts),
                    "success": True,
                })
            except Exception as e:
                pattern_results.append({
                    "pattern_id": pattern.id,
                    "pattern_name": pattern.name,
                    "shifts_created": 0,
                    "success": False,
                    "error": str(e),
                })
        
        return {
            "patterns_processed": len(patterns),
            "total_shifts_created": total_shifts,
            "results": pattern_results,
        }
