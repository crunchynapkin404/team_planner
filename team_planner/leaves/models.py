from decimal import Decimal
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from team_planner.contrib.sites.models import TimeStampedModel


class LeaveType(TimeStampedModel):
    """Leave type configuration."""
    
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
    
    class Meta:
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
    
    class Meta:
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
        """Get shifts that conflict with this leave request."""
        from team_planner.shifts.models import Shift
        
        return Shift.objects.filter(
            assigned_employee=self.employee,
            start_datetime__date__lte=self.end_date,
            end_datetime__date__gte=self.start_date,
            status__in=['scheduled', 'confirmed']
        ).select_related('template')
    
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
    
    def can_be_approved(self):
        """Check if leave request can be approved (no unresolved shift conflicts)."""
        if self.status != self.Status.PENDING:
            return False
        
        # If there are conflicting shifts, check if they have pending/approved swap requests
        conflicting_shifts = self.get_conflicting_shifts()
        
        for shift in conflicting_shifts:
            # Check if shift has an approved swap request that resolves the conflict
            from team_planner.shifts.models import SwapRequest
            
            approved_swaps = SwapRequest.objects.filter(
                requesting_shift=shift,
                status='approved'
            )
            
            if not approved_swaps.exists():
                # No approved swap for this shift - leave cannot be approved
                return False
        
        return True
    
    def get_blocking_message(self):
        """Get message explaining why leave request is blocked."""
        if not self.has_shift_conflicts:
            return None
        
        conflicting_shifts = self.get_conflicting_shifts()
        shift_count = conflicting_shifts.count()
        
        if shift_count == 1:
            shift = conflicting_shifts.first()
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
    
    class Meta:
        verbose_name = _("Holiday")
        verbose_name_plural = _("Holidays")
        ordering = ["date"]
        unique_together = [["name", "date"]]
    
    def __str__(self):
        return f"{self.name} ({self.date})"
    
    def get_absolute_url(self):
        return reverse("leaves:holiday_detail", kwargs={"pk": self.pk})
