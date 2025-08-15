from decimal import Decimal
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from datetime import timedelta

from team_planner.contrib.sites.models import TimeStampedModel


class LeaveType(TimeStampedModel):
    """Leave type configuration."""
    
    class ConflictHandling(models.TextChoices):
        FULL_UNAVAILABLE = "full_unavailable", _("Full Unavailable - Blocks all shifts")
        DAYTIME_ONLY = "daytime_only", _("Daytime Only - Blocks day shifts, available for waakdienst")
        NO_CONFLICT = "no_conflict", _("No Conflict - Does not block any shifts")
    
    name = models.CharField(_("Name"), max_length=50, unique=True)
    description = models.TextField(_("Description"), blank=True)
    default_days_per_year = models.DecimalField(
        _("Default Days Per Year"),
        max_digits=5,
        decimal_places=1,
        default=Decimal("0.0"),
        validators=[MinValueValidator(Decimal("0.0"))],
        help_text=_("Default number of days allocated per year"),
    )
    requires_approval = models.BooleanField(
        _("Requires Approval"),
        default=True,
        help_text=_("Whether this leave type requires manager approval"),
    )
    is_paid = models.BooleanField(
        _("Is Paid"),
        default=True,
        help_text=_("Whether this leave type is paid"),
    )
    is_active = models.BooleanField(_("Is Active"), default=True)
    color = models.CharField(
        _("Color"),
        max_length=7,
        default="#007bff",
        help_text=_("Hex color code for calendar display"),
    )
    conflict_handling = models.CharField(
        _("Conflict Handling"),
        max_length=20,
        choices=ConflictHandling.choices,
        default=ConflictHandling.FULL_UNAVAILABLE,
        help_text=_("How this leave type affects shift availability"),
    )
    start_time = models.TimeField(
        _("Start Time"),
        null=True,
        blank=True,
        help_text=_("Start time for partial day leave (leave blank for full day)"),
    )
    end_time = models.TimeField(
        _("End Time"),
        null=True,
        blank=True,
        help_text=_("End time for partial day leave (leave blank for full day)"),
    )
    
    class Meta(TimeStampedModel.Meta):
        verbose_name = _("Leave Type")
        verbose_name_plural = _("Leave Types")
        ordering = ["name"]
    
    def __str__(self):
        return self.name
    
    def get_absolute_url(self):
        return reverse("leaves:leavetype_detail", kwargs={"pk": self.pk})


class LeaveRequest(TimeStampedModel):
    """Employee leave request."""
    
    class Status(models.TextChoices):
        PENDING = "pending", _("Pending")
        APPROVED = "approved", _("Approved")
        REJECTED = "rejected", _("Rejected")
        CANCELLED = "cancelled", _("Cancelled")
    
    class RecurrenceType(models.TextChoices):
        NONE = "none", _("One-time")
        WEEKLY = "weekly", _("Weekly")
        MONTHLY = "monthly", _("Monthly")
        CUSTOM = "custom", _("Custom Pattern")

    employee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="leave_requests",
        verbose_name=_("Employee"),
    )
    leave_type = models.ForeignKey(
        LeaveType,
        on_delete=models.CASCADE,
        verbose_name=_("Leave Type"),
    )
    start_date = models.DateField(_("Start Date"))
    end_date = models.DateField(_("End Date"))
    start_time = models.TimeField(
        _("Start Time"),
        null=True,
        blank=True,
        help_text=_("Start time for partial day leave (uses leave type default if blank)"),
    )
    end_time = models.TimeField(
        _("End Time"),
        null=True,
        blank=True,
        help_text=_("End time for partial day leave (uses leave type default if blank)"),
    )
    days_requested = models.DecimalField(
        _("Days Requested"),
        max_digits=5,
        decimal_places=1,
        validators=[MinValueValidator(Decimal("0.1"))],
    )
    reason = models.TextField(_("Reason"), blank=True)
    status = models.CharField(
        _("Status"),
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    
    # Recurrence fields
    is_recurring = models.BooleanField(
        _("Is Recurring"),
        default=False,
        help_text=_("Whether this is a recurring leave pattern"),
    )
    recurrence_type = models.CharField(
        _("Recurrence Type"),
        max_length=20,
        choices=RecurrenceType.choices,
        default=RecurrenceType.NONE,
    )
    recurrence_end_date = models.DateField(
        _("Recurrence End Date"),
        null=True,
        blank=True,
        help_text=_("When the recurring pattern should end"),
    )
    parent_request = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='child_requests',
        verbose_name=_("Parent Request"),
        help_text=_("Reference to the original recurring request"),
    )
    
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_leave_requests",
        verbose_name=_("Approved By"),
    )
    approved_at = models.DateTimeField(_("Approved At"), null=True, blank=True)
    rejection_reason = models.TextField(_("Rejection Reason"), blank=True)
    
    class Meta(TimeStampedModel.Meta):
        verbose_name = _("Leave Request")
        verbose_name_plural = _("Leave Requests")
        ordering = ["-created", "-start_date"]

    def __str__(self):
        return (
            f"{self.employee.get_full_name()} - "
            f"{self.leave_type.name} "
            f"({self.start_date} to {self.end_date})"
        )

    def get_absolute_url(self):
        return reverse("leaves:request_detail", kwargs={"pk": self.pk})

    @property
    def is_pending(self):
        return self.status == self.Status.PENDING

    @property
    def is_approved(self):
        return self.status == self.Status.APPROVED

    @property
    def can_be_cancelled(self):
        return self.status in [self.Status.PENDING, self.Status.APPROVED]

    def get_conflicting_shifts(self):
        """Get shifts that conflict with this leave request based on leave type."""
        from team_planner.shifts.models import Shift
        from datetime import datetime, time
        
        # If leave type doesn't cause conflicts, return empty queryset
        if self.leave_type.conflict_handling == LeaveType.ConflictHandling.NO_CONFLICT:
            return Shift.objects.none()
        
        # Get base queryset of shifts in the date range
        shifts_queryset = Shift.objects.filter(
            assigned_employee=self.employee,
            start_datetime__date__lte=self.end_date,
            end_datetime__date__gte=self.start_date,
            status__in=['scheduled', 'confirmed']
        ).select_related('template')
        
        # For full unavailable (like vacation), return all shifts
        if self.leave_type.conflict_handling == LeaveType.ConflictHandling.FULL_UNAVAILABLE:
            return shifts_queryset
        
        # For daytime only (like leave), filter by shift type and time
        elif self.leave_type.conflict_handling == LeaveType.ConflictHandling.DAYTIME_ONLY:
            # Get the effective start and end times for this leave
            leave_start_time = self.start_time or self.leave_type.start_time or time(8, 0)
            leave_end_time = self.end_time or self.leave_type.end_time or time(17, 0)
            
            # Filter out waakdienst shifts (keep incidents and other day shifts)
            daytime_shifts = shifts_queryset.exclude(
                template__shift_type='waakdienst'
            )
            
            # Also check if shifts overlap with the time period
            conflicting_ids: list[int] = []
            for shift in daytime_shifts:
                shift_start_time = shift.start_datetime.time()
                shift_end_time = shift.end_datetime.time()
                
                # Check if shift time overlaps with leave time
                if (shift_start_time < leave_end_time and shift_end_time > leave_start_time):
                    # pk is available on all models; cast to int for typing
                    pk_val = shift.pk
                    if pk_val is not None:
                        conflicting_ids.append(int(pk_val))
            
            return daytime_shifts.filter(id__in=conflicting_ids)
        
        return shifts_queryset

    @property 
    def has_shift_conflicts(self):
        """Check if this leave request conflicts with assigned shifts."""
        return self.get_conflicting_shifts().exists()
    
    def get_suggested_swap_employees(self):
        """Get employees who could potentially take over conflicting shifts."""
        from django.contrib.auth import get_user_model
        from team_planner.shifts.models import Shift
        
        User = get_user_model()
        conflicting_shifts = self.get_conflicting_shifts()
        
        if not conflicting_shifts.exists():
            return User.objects.none()
        
        # Get employees who are available for the same shift types
        available_employees = User.objects.filter(is_active=True).exclude(pk=self.employee.pk)
        
        # Filter by availability toggles for each shift type
        incident_shifts = conflicting_shifts.filter(template__shift_type='incidents')
        waakdienst_shifts = conflicting_shifts.filter(template__shift_type='waakdienst')
        
        if incident_shifts.exists():
            available_employees = available_employees.filter(
                employee_profile__available_for_incidents=True
            )
        
        if waakdienst_shifts.exists():
            available_employees = available_employees.filter(
                employee_profile__available_for_waakdienst=True
            )
        
        # Exclude employees who already have shifts during this period
        for shift in conflicting_shifts:
            conflicting_employee_shifts = Shift.objects.filter(
                start_datetime__lt=shift.end_datetime,
                end_datetime__gt=shift.start_datetime,
                status__in=['scheduled', 'confirmed']
            ).values_list('assigned_employee', flat=True)
            
            available_employees = available_employees.exclude(
                pk__in=conflicting_employee_shifts
            )
        
        return available_employees.select_related('employee_profile')
    
    def get_effective_start_time(self):
        """Get the effective start time for this leave request."""
        from datetime import time
        return self.start_time or self.leave_type.start_time or time(8, 0)
    
    def get_effective_end_time(self):
        """Get the effective end time for this leave request."""
        from datetime import time
        return self.end_time or self.leave_type.end_time or time(17, 0)
    
    def is_within_active_planning_window(self) -> bool:
        """Return True if this leave lies within the next 6 months horizon."""
        today = timezone.now().date()
        horizon_end = today + timedelta(days=6*30)
        return self.start_date <= horizon_end

    def can_be_approved(self):
        """Check if leave request can be approved (no unresolved shift conflicts).
        If within 6-month active plan, require manual swap approvals first.
        """
        if self.status != self.Status.PENDING:
            return False

        # All conflicting shifts must be addressed
        conflicting_shifts = self.get_conflicting_shifts()

        if not conflicting_shifts.exists():
            return True

        # Within active window: require approved swap requests for each conflicting shift
        if self.is_within_active_planning_window():
            from team_planner.shifts.models import SwapRequest
            for shift in conflicting_shifts:
                if not SwapRequest.objects.filter(requesting_shift=shift, status=SwapRequest.Status.APPROVED).exists():
                    return False
            return True

        # Outside active window: can pass if conflicts exist but policy may be looser (default to False)
        return False
    
    def get_blocking_message(self):
        """Get message explaining why leave request is blocked."""
        if not self.has_shift_conflicts:
            return None
        
        conflicting_shifts = self.get_conflicting_shifts()
        shift_count = conflicting_shifts.count()
        
        if shift_count == 1:
            shift = conflicting_shifts.first()
            if not shift:
                return (
                    "There is a shift conflict with this leave request. "
                    "Please arrange a swap before the leave can be approved."
                )
            return (
                f"You have a {shift.template.get_shift_type_display()} shift "
                f"on {shift.start_datetime.date()} that conflicts with this leave request. "
                f"Please arrange a swap for this shift before the leave can be approved."
            )
        else:
            return (
                f"You have {shift_count} shifts during this leave period that need to be "
                f"swapped with other employees before the leave can be approved."
            )

    def create_recurring_instances(self):
        """Create child leave requests for a recurring pattern.
        Currently supports weekly recurrence until recurrence_end_date.
        Returns the list of created child requests.
        """
        if not self.is_recurring:
            return []
        if self.recurrence_type != self.RecurrenceType.WEEKLY:
            return []
        if not self.recurrence_end_date:
            return []

        from datetime import timedelta
        instances: list[LeaveRequest] = []  # type: ignore[name-defined]
        # Start from one period after the original request
        delta = timedelta(weeks=1)
        next_start = self.start_date + delta
        next_end = self.end_date + delta

        while next_start <= self.recurrence_end_date:
            child = LeaveRequest.objects.create(
                employee=self.employee,
                leave_type=self.leave_type,
                start_date=next_start,
                end_date=next_end,
                start_time=self.start_time,
                end_time=self.end_time,
                days_requested=self.days_requested,
                reason=self.reason,
                status=self.Status.PENDING,
                is_recurring=False,
                recurrence_type=self.RecurrenceType.NONE,
                parent_request=self,
            )
            instances.append(child)
            next_start += delta
            next_end += delta
        return instances


class Holiday(TimeStampedModel):
    """Public holidays and company-wide closures."""
    
    name = models.CharField(_("Holiday Name"), max_length=100)
    date = models.DateField(_("Date"))
    description = models.TextField(_("Description"), blank=True)
    is_recurring = models.BooleanField(
        _("Is Recurring"),
        default=False,
        help_text=_("Whether this holiday repeats annually"),
    )
    
    class Meta(TimeStampedModel.Meta):
        verbose_name = _("Holiday")
        verbose_name_plural = _("Holidays")
        ordering = ["date"]
        unique_together = [["name", "date"]]
    
    def __str__(self):
        return f"{self.name} ({self.date})"
    
    def get_absolute_url(self):
        return reverse("leaves:holiday_detail", kwargs={"pk": self.pk})
