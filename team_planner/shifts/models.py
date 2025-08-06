from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from team_planner.contrib.sites.models import TimeStampedModel


class ShiftType(models.TextChoices):
    """Shift type choices matching our roadmap requirements."""
    INCIDENTS = "incidents", _("Incidents")
    WAAKDIENST = "waakdienst", _("Waakdienst")
    CHANGES = "changes", _("Changes")
    PROJECTS = "projects", _("Projects")


class ShiftTemplate(TimeStampedModel):
    """Template for creating shifts with predefined settings."""
    
    name = models.CharField(_("Template Name"), max_length=100)
    shift_type = models.CharField(
        _("Shift Type"),
        max_length=20,
        choices=ShiftType.choices
    )
    description = models.TextField(_("Description"), blank=True)
    duration_hours = models.PositiveIntegerField(
        _("Duration (hours)"),
        help_text=_("Expected duration in hours")
    )
    skills_required = models.ManyToManyField(
        "employees.EmployeeSkill",
        blank=True,
        verbose_name=_("Required Skills"),
        help_text=_("Skills required for this shift type")
    )
    is_active = models.BooleanField(_("Is Active"), default=True)
    
    class Meta:
        verbose_name = _("Shift Template")
        verbose_name_plural = _("Shift Templates")
        ordering = ["shift_type", "name"]

    def __str__(self):
        return f"{self.get_shift_type_display()} - {self.name}"

    def get_absolute_url(self):
        return reverse("shifts:template_detail", kwargs={"pk": self.pk})


class Shift(TimeStampedModel):
    """Individual shift assignment."""
    
    class Status(models.TextChoices):
        SCHEDULED = "scheduled", _("Scheduled")
        CONFIRMED = "confirmed", _("Confirmed")
        IN_PROGRESS = "in_progress", _("In Progress")
        COMPLETED = "completed", _("Completed")
        CANCELLED = "cancelled", _("Cancelled")
    
    template = models.ForeignKey(
        ShiftTemplate,
        on_delete=models.PROTECT,
        related_name="shifts",
        verbose_name=_("Template")
    )
    assigned_employee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="assigned_shifts",
        verbose_name=_("Assigned Employee")
    )
    start_datetime = models.DateTimeField(_("Start Date/Time"))
    end_datetime = models.DateTimeField(_("End Date/Time"))
    status = models.CharField(
        _("Status"),
        max_length=20,
        choices=Status.choices,
        default=Status.SCHEDULED
    )
    notes = models.TextField(_("Notes"), blank=True)
    
    # Auto-scheduling metadata
    auto_assigned = models.BooleanField(
        _("Auto Assigned"),
        default=False,
        help_text=_("Was this shift assigned by the orchestrator?")
    )
    assignment_reason = models.TextField(
        _("Assignment Reason"),
        blank=True,
        help_text=_("Reason for assignment (from orchestrator)")
    )
    
    class Meta:
        verbose_name = _("Shift")
        verbose_name_plural = _("Shifts")
        ordering = ["start_datetime"]
        constraints = [
            models.CheckConstraint(
                check=models.Q(end_datetime__gt=models.F("start_datetime")),
                name="end_after_start"
            )
        ]

    def __str__(self):
        return f"{self.template.get_shift_type_display()} - {self.assigned_employee.username} ({self.start_datetime.date()})"

    def get_absolute_url(self):
        return reverse("shifts:shift_detail", kwargs={"pk": self.pk})

    @property
    def duration_hours(self):
        """Calculate actual duration in hours."""
        delta = self.end_datetime - self.start_datetime
        return delta.total_seconds() / 3600


class SwapRequest(TimeStampedModel):
    """Request to swap shifts between employees."""
    
    class Status(models.TextChoices):
        PENDING = "pending", _("Pending")
        APPROVED = "approved", _("Approved") 
        REJECTED = "rejected", _("Rejected")
        CANCELLED = "cancelled", _("Cancelled")
    
    requesting_employee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="swap_requests_made",
        verbose_name=_("Requesting Employee")
    )
    target_employee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="swap_requests_received",
        verbose_name=_("Target Employee")
    )
    requesting_shift = models.ForeignKey(
        Shift,
        on_delete=models.CASCADE,
        related_name="swap_requests_as_source",
        verbose_name=_("Shift to Give Up")
    )
    target_shift = models.ForeignKey(
        Shift,
        on_delete=models.CASCADE,
        related_name="swap_requests_as_target",
        null=True,
        blank=True,
        verbose_name=_("Shift to Take Over")
    )
    status = models.CharField(
        _("Status"),
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    reason = models.TextField(_("Reason"), blank=True)
    response_notes = models.TextField(_("Response Notes"), blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_swaps",
        verbose_name=_("Approved By")
    )
    approved_datetime = models.DateTimeField(_("Approved Date/Time"), null=True, blank=True)
    
    class Meta:
        verbose_name = _("Swap Request")
        verbose_name_plural = _("Swap Requests")
        ordering = ["-created"]

    def __str__(self):
        return f"Swap: {self.requesting_employee.username} → {self.target_employee.username} ({self.get_status_display()})"

    def get_absolute_url(self):
        return reverse("shifts:swap_detail", kwargs={"pk": self.pk})


class FairnessScore(TimeStampedModel):
    """Track fairness scores for employees over time."""
    
    employee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="fairness_scores",
        verbose_name=_("Employee")
    )
    period_start = models.DateField(_("Period Start"))
    period_end = models.DateField(_("Period End"))
    
    # Separate tracking for each shift type
    incidents_days = models.PositiveIntegerField(
        _("Incidents Days"),
        default=0,
        help_text=_("Total days assigned to incident shifts")
    )
    waakdienst_days = models.PositiveIntegerField(
        _("Waakdienst Days"),
        default=0,
        help_text=_("Total days assigned to waakdienst shifts")
    )
    changes_days = models.PositiveIntegerField(
        _("Changes Days"),
        default=0,
        help_text=_("Total days assigned to change shifts")
    )
    projects_days = models.PositiveIntegerField(
        _("Projects Days"),
        default=0,
        help_text=_("Total days assigned to project shifts")
    )
    
    # Fairness calculations
    incidents_fairness_score = models.DecimalField(
        _("Incidents Fairness Score"),
        max_digits=5,
        decimal_places=2,
        default=0.00,
        help_text=_("Fairness score for incident shifts (0-100)")
    )
    waakdienst_fairness_score = models.DecimalField(
        _("Waakdienst Fairness Score"),
        max_digits=5,
        decimal_places=2,
        default=0.00,
        help_text=_("Fairness score for waakdienst shifts (0-100)")
    )
    overall_fairness_score = models.DecimalField(
        _("Overall Fairness Score"),
        max_digits=5,
        decimal_places=2,
        default=0.00,
        help_text=_("Combined fairness score (0-100)")
    )
    
    class Meta:
        verbose_name = _("Fairness Score")
        verbose_name_plural = _("Fairness Scores")
        ordering = ["-period_end", "employee__username"]
        unique_together = [["employee", "period_start", "period_end"]]

    def __str__(self):
        return f"{self.employee.username} - {self.period_start} to {self.period_end} (Score: {self.overall_fairness_score})"

    def get_absolute_url(self):
        return reverse("shifts:fairness_detail", kwargs={"pk": self.pk})

    @property
    def total_shift_days(self):
        """Calculate total days across all shift types."""
        return self.incidents_days + self.waakdienst_days + self.changes_days + self.projects_days


class TimeEntry(TimeStampedModel):
    """Track actual time worked for shifts."""
    
    shift = models.ForeignKey(
        Shift,
        on_delete=models.CASCADE,
        related_name="time_entries",
        verbose_name=_("Shift")
    )
    employee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="time_entries",
        verbose_name=_("Employee")
    )
    clock_in = models.DateTimeField(_("Clock In"))
    clock_out = models.DateTimeField(_("Clock Out"), null=True, blank=True)
    break_duration_minutes = models.PositiveIntegerField(
        _("Break Duration (minutes)"),
        default=0,
        validators=[MinValueValidator(0)]
    )
    notes = models.TextField(_("Notes"), blank=True)
    
    class Meta:
        verbose_name = _("Time Entry")
        verbose_name_plural = _("Time Entries")
        ordering = ["-clock_in"]
        constraints = [
            models.CheckConstraint(
                check=models.Q(clock_out__isnull=True) | models.Q(clock_out__gt=models.F("clock_in")),
                name="clock_out_after_clock_in"
            )
        ]

    def __str__(self):
        status = "In Progress" if not self.clock_out else "Completed"
        return f"{self.employee.username} - {self.shift.template.get_shift_type_display()} ({status})"

    def get_absolute_url(self):
        return reverse("shifts:time_entry_detail", kwargs={"pk": self.pk})

    @property
    def duration_hours(self):
        """Calculate actual working hours (excluding breaks)."""
        if not self.clock_out:
            return None
        
        total_minutes = (self.clock_out - self.clock_in).total_seconds() / 60
        working_minutes = total_minutes - self.break_duration_minutes
        return max(0, working_minutes / 60)  # Ensure non-negative


class OvertimeEntry(TimeStampedModel):
    """Track overtime hours and reasons."""
    
    employee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="overtime_entries",
        verbose_name=_("Employee")
    )
    date = models.DateField(_("Date"))
    hours = models.DecimalField(
        _("Overtime Hours"),
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0.01)]
    )
    reason = models.TextField(_("Reason"))
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_overtime",
        verbose_name=_("Approved By")
    )
    shift = models.ForeignKey(
        Shift,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="overtime_entries",
        verbose_name=_("Related Shift")
    )
    
    class Meta:
        verbose_name = _("Overtime Entry")
        verbose_name_plural = _("Overtime Entries")
        ordering = ["-date"]

    def __str__(self):
        return f"{self.employee.username} - {self.date} ({self.hours}h)"

    def get_absolute_url(self):
        return reverse("shifts:overtime_detail", kwargs={"pk": self.pk})


class SchedulingRule(TimeStampedModel):
    """Configuration rules for the orchestrator."""
    
    name = models.CharField(_("Rule Name"), max_length=100)
    shift_type = models.CharField(
        _("Shift Type"),
        max_length=20,
        choices=ShiftType.choices
    )
    description = models.TextField(_("Description"))
    is_active = models.BooleanField(_("Is Active"), default=True)
    priority = models.PositiveIntegerField(
        _("Priority"),
        default=1,
        help_text=_("Higher numbers = higher priority")
    )
    
    # Rule configuration (JSON field for flexibility)
    configuration = models.JSONField(
        _("Configuration"),
        default=dict,
        help_text=_("Rule-specific configuration parameters")
    )
    
    class Meta:
        verbose_name = _("Scheduling Rule")
        verbose_name_plural = _("Scheduling Rules")
        ordering = ["-priority", "shift_type", "name"]

    def __str__(self):
        return f"{self.get_shift_type_display()} - {self.name} (Priority: {self.priority})"

    def get_absolute_url(self):
        return reverse("shifts:rule_detail", kwargs={"pk": self.pk})
