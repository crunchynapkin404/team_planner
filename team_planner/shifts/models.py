from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from team_planner.contrib.sites.models import TimeStampedModel


class ShiftType(models.TextChoices):
    """Shift type choices matching our roadmap requirements."""

    INCIDENTS = "incidents", _("Incidents")
    INCIDENTS_STANDBY = "incidents_standby", _("Incidents-Standby")
    WAAKDIENST = "waakdienst", _("Waakdienst")
    CHANGES = "changes", _("Changes")
    PROJECTS = "projects", _("Projects")


class ShiftTemplate(TimeStampedModel):
    """Template for creating shifts with predefined settings."""

    name = models.CharField(_("Template Name"), max_length=100)
    shift_type = models.CharField(
        _("Shift Type"), max_length=20, choices=ShiftType.choices,
    )
    description = models.TextField(_("Description"), blank=True)
    duration_hours = models.PositiveIntegerField(
        _("Duration (hours)"), help_text=_("Expected duration in hours"),
    )
    skills_required = models.ManyToManyField(
        "employees.EmployeeSkill",
        blank=True,
        verbose_name=_("Required Skills"),
        help_text=_("Skills required for this shift type"),
    )
    is_active = models.BooleanField(_("Is Active"), default=True)
    
    # Enhanced library fields
    category = models.CharField(
        _("Category"),
        max_length=50,
        blank=True,
        help_text=_("Template category for organization (e.g., 'Weekend', 'Holiday', 'Standard')"),
    )
    tags = models.JSONField(
        _("Tags"),
        default=list,
        blank=True,
        help_text=_("Tags for searchability and filtering"),
    )
    is_favorite = models.BooleanField(
        _("Favorite"),
        default=False,
        help_text=_("Mark as favorite for quick access"),
    )
    usage_count = models.PositiveIntegerField(
        _("Usage Count"),
        default=0,
        help_text=_("Number of times this template has been used"),
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_shift_templates",
        verbose_name=_("Created By"),
    )
    default_start_time = models.TimeField(
        _("Default Start Time"),
        null=True,
        blank=True,
        help_text=_("Suggested start time for this template"),
    )
    default_end_time = models.TimeField(
        _("Default End Time"),
        null=True,
        blank=True,
        help_text=_("Suggested end time for this template"),
    )
    notes = models.TextField(
        _("Notes"),
        blank=True,
        help_text=_("Additional notes or instructions"),
    )

    class Meta:  # type: ignore[override]
        verbose_name = _("Shift Template")
        verbose_name_plural = _("Shift Templates")
        ordering = ["-is_favorite", "-usage_count", "shift_type", "name"]

    def __str__(self):
        return f"{self.get_shift_type_display()} - {self.name}"  # type: ignore[attr-defined]

    def get_absolute_url(self):
        return reverse("shifts:template_detail", kwargs={"pk": self.pk})
    
    def increment_usage(self):
        """Increment the usage count when template is used."""
        self.usage_count += 1
        self.save(update_fields=["usage_count"])


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
        verbose_name=_("Template"),
    )
    assigned_employee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="assigned_shifts",
        verbose_name=_("Assigned Employee"),
    )
    start_datetime = models.DateTimeField(_("Start Date/Time"))
    end_datetime = models.DateTimeField(_("End Date/Time"))
    status = models.CharField(
        _("Status"), max_length=20, choices=Status.choices, default=Status.SCHEDULED,
    )
    notes = models.TextField(_("Notes"), blank=True)

    # Auto-scheduling metadata
    auto_assigned = models.BooleanField(
        _("Auto Assigned"),
        default=False,
        help_text=_("Was this shift assigned by the orchestrator?"),
    )
    assignment_reason = models.TextField(
        _("Assignment Reason"),
        blank=True,
        help_text=_("Reason for assignment (from orchestrator)"),
    )

    class Meta:  # type: ignore[override]
        verbose_name = _("Shift")
        verbose_name_plural = _("Shifts")
        ordering = ["start_datetime"]
        constraints = [
            models.CheckConstraint(
                check=models.Q(end_datetime__gt=models.F("start_datetime")),
                name="end_after_start",
            ),
            models.UniqueConstraint(
                fields=[
                    "assigned_employee",
                    "start_datetime",
                    "end_datetime",
                    "template",
                ],
                name="unique_shift_per_employee_time_and_template",
            ),
        ]

    def __str__(self):
        return f"{self.template.get_shift_type_display()} - {self.assigned_employee.username} ({self.start_datetime.date()})"  # type: ignore[attr-defined]

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
        verbose_name=_("Requesting Employee"),
    )
    target_employee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="swap_requests_received",
        verbose_name=_("Target Employee"),
    )
    requesting_shift = models.ForeignKey(
        Shift,
        on_delete=models.CASCADE,
        related_name="swap_requests_as_source",
        verbose_name=_("Shift to Give Up"),
    )
    target_shift = models.ForeignKey(
        Shift,
        on_delete=models.CASCADE,
        related_name="swap_requests_as_target",
        null=True,
        blank=True,
        verbose_name=_("Shift to Take Over"),
    )
    status = models.CharField(
        _("Status"), max_length=20, choices=Status.choices, default=Status.PENDING,
    )
    reason = models.TextField(_("Reason"), blank=True)
    response_notes = models.TextField(_("Response Notes"), blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_swaps",
        verbose_name=_("Approved By"),
    )
    approved_datetime = models.DateTimeField(
        _("Approved Date/Time"), null=True, blank=True,
    )

    class Meta:  # type: ignore[override]
        verbose_name = _("Swap Request")
        verbose_name_plural = _("Swap Requests")
        ordering = ["-created"]

    def __str__(self):
        return f"Swap: {self.requesting_employee.username} → {self.target_employee.username} ({self.get_status_display()})"  # type: ignore[attr-defined]

    def get_absolute_url(self):
        return reverse("shifts:swap_detail", kwargs={"pk": self.pk})

    @property
    def is_pending(self):
        return self.status == self.Status.PENDING

    @property
    def is_approved(self):
        return self.status == self.Status.APPROVED

    @property
    def can_be_cancelled(self):
        return self.status in [self.Status.PENDING]

    @property
    def can_be_approved(self):
        return self.status == self.Status.PENDING

    def approve(self, approved_by_user, response_notes=""):
        """Approve the swap request and execute the swap."""
        from django.utils import timezone

        from team_planner.notifications.mailer import build_ics_for_shift
        from team_planner.notifications.mailer import notify_swap_approved
        from team_planner.notifications.services import NotificationService

        if not self.can_be_approved:
            msg = "Swap request cannot be approved in current status"
            raise ValueError(msg)

        # Update the swap request
        self.status = self.Status.APPROVED
        self.approved_by = approved_by_user
        self.approved_datetime = timezone.now()
        self.response_notes = response_notes
        self.save()

        # Execute the actual swap
        self._execute_swap()

        # Notify both parties with ICS for the affected shift(s)
        try:
            ics = build_ics_for_shift(self.requesting_shift)
            requester_email = getattr(self.requesting_employee, "email", None)
            target_email = getattr(self.target_employee, "email", None)
            shift_summary = f"Shift on {self.requesting_shift.start_datetime.strftime('%Y-%m-%d %H:%M')}"
            notify_swap_approved(requester_email, target_email, shift_summary, ics)
        except Exception:
            pass

        # Send in-app notifications to both employees
        try:
            # Notify requesting employee
            NotificationService.notify_swap_approved(
                employee=self.requesting_employee,
                swap_request=self,
                approved_by=approved_by_user
            )
            # Notify target employee
            NotificationService.notify_swap_approved(
                employee=self.target_employee,
                swap_request=self,
                approved_by=approved_by_user
            )
        except Exception as e:
            print(f"Failed to send swap approved notifications: {e}")

    def reject(self, response_notes=""):
        """Reject the swap request."""
        from team_planner.notifications.services import NotificationService

        if not self.can_be_approved:
            msg = "Swap request cannot be rejected in current status"
            raise ValueError(msg)

        self.status = self.Status.REJECTED
        self.response_notes = response_notes
        self.save()

        # Send in-app notification to requesting employee
        try:
            NotificationService.notify_swap_rejected(
                employee=self.requesting_employee,
                swap_request=self,
                rejected_by=self.target_employee,
                reason=response_notes
            )
        except Exception as e:
            print(f"Failed to send swap rejected notification: {e}")

    def cancel(self):
        """Cancel the swap request."""
        if not self.can_be_cancelled:
            msg = "Swap request cannot be cancelled in current status"
            raise ValueError(msg)

        self.status = self.Status.CANCELLED
        self.save()

    def _execute_swap(self):
        """Execute the actual shift swap using transactional services and auditing."""
        from .services import reassign_shift_transactional
        from .services import swap_shifts_transactional

        # If there's a target shift, swap the assignments atomically
        if self.target_shift:
            swap_shifts_transactional(
                shift_a=self.requesting_shift,
                shift_b=self.target_shift,
                actor=self.approved_by,
                reason=f"Swap approved via request #{self.pk}",
                source="swap",
            )
        else:
            # Reassign the requesting shift to target employee
            reassign_shift_transactional(
                shift=self.requesting_shift,
                new_employee=self.target_employee,
                actor=self.approved_by,
                reason=f"Reassigned via swap request #{self.pk}",
                source="swap",
            )

    def validate_swap(self):
        """Validate that the swap is feasible."""
        errors = []

        # Check if employees are the same
        if self.requesting_employee == self.target_employee:
            errors.append("Cannot swap shift with yourself")

        # Check if requesting employee owns the requesting shift
        if self.requesting_shift.assigned_employee != self.requesting_employee:
            errors.append("You can only swap your own shifts")

        # If target shift exists, check if target employee owns it
        if (
            self.target_shift
            and self.target_shift.assigned_employee != self.target_employee
        ):
            errors.append("Target employee must own the target shift")

        # Check if shifts overlap for target employee (if no target shift)
        if not self.target_shift:
            overlapping_shifts = Shift.objects.filter(
                assigned_employee=self.target_employee,
                start_datetime__lt=self.requesting_shift.end_datetime,
                end_datetime__gt=self.requesting_shift.start_datetime,
            ).exclude(pk=self.requesting_shift.pk)

            if overlapping_shifts.exists():
                errors.append(
                    "Target employee has conflicting shifts during this period",
                )

        # Check if target employee has availability for the shift type
        try:
            profile = self.target_employee.employee_profile
            shift_type = self.requesting_shift.template.shift_type

            if shift_type == "incidents" and not profile.available_for_incidents:
                errors.append("Target employee is not available for incident shifts")
            elif shift_type == "waakdienst" and not profile.available_for_waakdienst:
                errors.append("Target employee is not available for waakdienst shifts")
        except:
            errors.append("Target employee profile not found")

        return errors


class FairnessScore(TimeStampedModel):
    """Track fairness scores for employees over time."""

    employee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="fairness_scores",
        verbose_name=_("Employee"),
    )
    period_start = models.DateField(_("Period Start"))
    period_end = models.DateField(_("Period End"))

    # Separate tracking for each shift type
    incidents_days = models.PositiveIntegerField(
        _("Incidents Days"),
        default=0,
        help_text=_("Total days assigned to incident shifts"),
    )
    waakdienst_days = models.PositiveIntegerField(
        _("Waakdienst Days"),
        default=0,
        help_text=_("Total days assigned to waakdienst shifts"),
    )
    changes_days = models.PositiveIntegerField(
        _("Changes Days"),
        default=0,
        help_text=_("Total days assigned to change shifts"),
    )
    projects_days = models.PositiveIntegerField(
        _("Projects Days"),
        default=0,
        help_text=_("Total days assigned to project shifts"),
    )

    # Fairness calculations
    incidents_fairness_score = models.DecimalField(
        _("Incidents Fairness Score"),
        max_digits=5,
        decimal_places=2,
        default=0.00,
        help_text=_("Fairness score for incident shifts (0-100)"),
    )
    waakdienst_fairness_score = models.DecimalField(
        _("Waakdienst Fairness Score"),
        max_digits=5,
        decimal_places=2,
        default=0.00,
        help_text=_("Fairness score for waakdienst shifts (0-100)"),
    )
    overall_fairness_score = models.DecimalField(
        _("Overall Fairness Score"),
        max_digits=5,
        decimal_places=2,
        default=0.00,
        help_text=_("Combined fairness score (0-100)"),
    )

    class Meta:  # type: ignore[override]
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
        return (
            self.incidents_days
            + self.waakdienst_days
            + self.changes_days
            + self.projects_days
        )


class TimeEntry(TimeStampedModel):
    """Track actual time worked for shifts."""

    shift = models.ForeignKey(
        Shift,
        on_delete=models.CASCADE,
        related_name="time_entries",
        verbose_name=_("Shift"),
    )
    employee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="time_entries",
        verbose_name=_("Employee"),
    )
    clock_in = models.DateTimeField(_("Clock In"))
    clock_out = models.DateTimeField(_("Clock Out"), null=True, blank=True)
    break_duration_minutes = models.PositiveIntegerField(
        _("Break Duration (minutes)"), default=0, validators=[MinValueValidator(0)],
    )
    notes = models.TextField(_("Notes"), blank=True)

    class Meta:  # type: ignore[override]
        verbose_name = _("Time Entry")
        verbose_name_plural = _("Time Entries")
        ordering = ["-clock_in"]
        constraints = [
            models.CheckConstraint(
                check=models.Q(clock_out__isnull=True)
                | models.Q(clock_out__gt=models.F("clock_in")),
                name="clock_out_after_clock_in",
            ),
        ]

    def __str__(self):
        status = "In Progress" if not self.clock_out else "Completed"
        return f"{self.employee.username} - {self.shift.template.get_shift_type_display()} ({status})"  # type: ignore[attr-defined]

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
        verbose_name=_("Employee"),
    )
    date = models.DateField(_("Date"))
    hours = models.DecimalField(
        _("Overtime Hours"),
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0.01)],
    )
    reason = models.TextField(_("Reason"))
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_overtime",
        verbose_name=_("Approved By"),
    )
    shift = models.ForeignKey(
        Shift,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="overtime_entries",
        verbose_name=_("Related Shift"),
    )

    class Meta:  # type: ignore[override]
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
        _("Shift Type"), max_length=20, choices=ShiftType.choices,
    )
    description = models.TextField(_("Description"))
    is_active = models.BooleanField(_("Is Active"), default=True)
    priority = models.PositiveIntegerField(
        _("Priority"), default=1, help_text=_("Higher numbers = higher priority"),
    )

    # Rule configuration (JSON field for flexibility)
    configuration = models.JSONField(
        _("Configuration"),
        default=dict,
        help_text=_("Rule-specific configuration parameters"),
    )

    class Meta:  # type: ignore[override]
        verbose_name = _("Scheduling Rule")
        verbose_name_plural = _("Scheduling Rules")
        ordering = ["-priority", "shift_type", "name"]

    def __str__(self):
        return (
            f"{self.get_shift_type_display()} - {self.name} (Priority: {self.priority})"  # type: ignore[attr-defined]
        )

    def get_absolute_url(self):
        return reverse("shifts:rule_detail", kwargs={"pk": self.pk})


class ShiftAuditLog(TimeStampedModel):
    """Immutable audit trail for shift changes (swaps, reassignments)."""

    class Action(models.TextChoices):
        REASSIGNED = "reassigned", _("Reassigned")
        SWAP_APPROVED = "swap_approved", _("Swap Approved")

    action = models.CharField(max_length=50, choices=Action.choices)
    shift = models.ForeignKey(
        "Shift", on_delete=models.CASCADE, related_name="audit_logs",
    )
    from_employee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=_("From Employee"),
    )
    to_employee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=_("To Employee"),
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="performed_shift_audits",
        verbose_name=_("Actor"),
    )
    reason = models.TextField(blank=True)
    source = models.CharField(
        max_length=50,
        blank=True,
        help_text=_("Origin of change (swap/leave/admin/etc.)"),
    )

    class Meta:  # type: ignore[override]
        verbose_name = _("Shift Audit Log")
        verbose_name_plural = _("Shift Audit Logs")
        ordering = ["-created", "-id"]


class RecurringShiftPattern(TimeStampedModel):
    """Pattern for generating recurring shifts."""

    class RecurrenceType(models.TextChoices):
        DAILY = "daily", _("Daily")
        WEEKLY = "weekly", _("Weekly")
        BIWEEKLY = "biweekly", _("Bi-weekly")
        MONTHLY = "monthly", _("Monthly")

    class WeekDay(models.IntegerChoices):
        MONDAY = 0, _("Monday")
        TUESDAY = 1, _("Tuesday")
        WEDNESDAY = 2, _("Wednesday")
        THURSDAY = 3, _("Thursday")
        FRIDAY = 4, _("Friday")
        SATURDAY = 5, _("Saturday")
        SUNDAY = 6, _("Sunday")

    name = models.CharField(_("Pattern Name"), max_length=200)
    description = models.TextField(_("Description"), blank=True)
    
    # Template and timing
    template = models.ForeignKey(
        ShiftTemplate,
        on_delete=models.CASCADE,
        related_name="recurring_patterns",
        verbose_name=_("Shift Template"),
    )
    start_time = models.TimeField(_("Start Time"))
    end_time = models.TimeField(_("End Time"))
    
    # Recurrence rules
    recurrence_type = models.CharField(
        _("Recurrence Type"),
        max_length=20,
        choices=RecurrenceType.choices,
        default=RecurrenceType.WEEKLY,
    )
    weekdays = models.JSONField(
        _("Weekdays"),
        default=list,
        blank=True,
        help_text=_("List of weekday numbers (0=Monday, 6=Sunday) for weekly patterns"),
    )
    day_of_month = models.PositiveIntegerField(
        _("Day of Month"),
        null=True,
        blank=True,
        validators=[MinValueValidator(1)],
        help_text=_("Day of month (1-31) for monthly patterns"),
    )
    
    # Date range
    pattern_start_date = models.DateField(_("Pattern Start Date"))
    pattern_end_date = models.DateField(
        _("Pattern End Date"),
        null=True,
        blank=True,
        help_text=_("Leave blank for no end date"),
    )
    
    # Assignment
    assigned_employee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="recurring_shift_patterns",
        verbose_name=_("Assigned Employee"),
        null=True,
        blank=True,
        help_text=_("Leave blank for unassigned pattern"),
    )
    team = models.ForeignKey(
        "teams.Team",
        on_delete=models.CASCADE,
        related_name="recurring_shift_patterns",
        verbose_name=_("Team"),
        null=True,
        blank=True,
    )
    
    # Status
    is_active = models.BooleanField(_("Is Active"), default=True)
    last_generated_date = models.DateField(
        _("Last Generated Date"),
        null=True,
        blank=True,
        help_text=_("Last date shifts were generated for this pattern"),
    )
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_shift_patterns",
        verbose_name=_("Created By"),
    )

    class Meta:  # type: ignore[override]
        verbose_name = _("Recurring Shift Pattern")
        verbose_name_plural = _("Recurring Shift Patterns")
        ordering = ["-created"]
        constraints = [
            models.CheckConstraint(
                check=models.Q(end_time__gt=models.F("start_time")),
                name="pattern_end_after_start",
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_recurrence_type_display()})"

    def get_absolute_url(self):
        return reverse("shifts:pattern_detail", kwargs={"pk": self.pk})


# Advanced Approval Models

class SwapApprovalRule(TimeStampedModel):
    """
    Configurable rules for swap request approvals.
    
    Allows flexible approval workflows with:
    - Priority-based rule matching
    - Auto-approval criteria
    - Multi-level manual approval requirements
    - Delegation support
    - Usage limits
    """
    
    class Priority(models.IntegerChoices):
        LOWEST = 1, _("Lowest")
        LOW = 2, _("Low")
        MEDIUM = 3, _("Medium")
        HIGH = 4, _("High")
        HIGHEST = 5, _("Highest")
    
    # Basic Information
    name = models.CharField(_("Rule Name"), max_length=200)
    description = models.TextField(_("Description"), blank=True)
    priority = models.IntegerField(
        _("Priority"),
        choices=Priority.choices,
        default=Priority.MEDIUM,
        help_text=_("Higher priority rules are evaluated first"),
    )
    is_active = models.BooleanField(_("Is Active"), default=True)
    
    # Applicability Conditions
    applies_to_shift_types = models.JSONField(
        _("Applies to Shift Types"),
        default=list,
        blank=True,
        help_text=_("List of shift types this rule applies to. Empty means all types."),
    )
    
    # Auto-Approval Settings
    auto_approve_enabled = models.BooleanField(
        _("Enable Auto-Approval"),
        default=False,
        help_text=_("If true, requests meeting criteria will be auto-approved"),
    )
    auto_approve_same_shift_type = models.BooleanField(
        _("Require Same Shift Type"),
        default=True,
        help_text=_("Auto-approve only if both shifts are the same type"),
    )
    auto_approve_max_advance_hours = models.IntegerField(
        _("Maximum Advance Hours"),
        null=True,
        blank=True,
        help_text=_("Maximum hours in advance the swap can be requested"),
    )
    auto_approve_min_seniority_months = models.IntegerField(
        _("Minimum Seniority (Months)"),
        null=True,
        blank=True,
        help_text=_("Minimum months of employment required for both employees"),
    )
    auto_approve_skills_match_required = models.BooleanField(
        _("Require Skills Match"),
        default=False,
        help_text=_("Auto-approve only if employees have compatible skills"),
    )
    
    # Manual Approval Requirements
    requires_manager_approval = models.BooleanField(
        _("Requires Manager Approval"),
        default=True,
        help_text=_("Requires approval from a manager"),
    )
    requires_admin_approval = models.BooleanField(
        _("Requires Admin Approval"),
        default=False,
        help_text=_("Requires approval from an administrator"),
    )
    approval_levels_required = models.IntegerField(
        _("Approval Levels Required"),
        default=1,
        validators=[MinValueValidator(1)],
        help_text=_("Number of approval levels required (1-5)"),
    )
    
    # Delegation Settings
    allow_delegation = models.BooleanField(
        _("Allow Delegation"),
        default=True,
        help_text=_("Allow approvers to delegate their approval authority"),
    )
    
    # Usage Limits
    max_swaps_per_month_per_employee = models.IntegerField(
        _("Max Swaps Per Month Per Employee"),
        null=True,
        blank=True,
        help_text=_("Maximum number of swaps an employee can request per month"),
    )
    
    # Notifications
    notify_on_auto_approval = models.BooleanField(
        _("Notify on Auto-Approval"),
        default=True,
        help_text=_("Send notification when a request is auto-approved"),
    )
    
    class Meta:  # type: ignore[override]
        verbose_name = _("Swap Approval Rule")
        verbose_name_plural = _("Swap Approval Rules")
        ordering = ["-priority", "name"]
    
    def __str__(self):
        return f"{self.name} (Priority: {self.get_priority_display()})"


class SwapApprovalChain(TimeStampedModel):
    """
    Tracks the approval chain for a swap request.
    
    Supports multi-level approval workflows where each level must be
    approved sequentially before the swap is executed.
    """
    
    class Status(models.TextChoices):
        PENDING = "pending", _("Pending")
        APPROVED = "approved", _("Approved")
        REJECTED = "rejected", _("Rejected")
        SKIPPED = "skipped", _("Skipped")
        DELEGATED = "delegated", _("Delegated")
    
    swap_request = models.ForeignKey(
        "SwapRequest",
        on_delete=models.CASCADE,
        related_name="approval_chain",
        verbose_name=_("Swap Request"),
    )
    approval_rule = models.ForeignKey(
        "SwapApprovalRule",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approval_chains",
        verbose_name=_("Approval Rule"),
    )
    level = models.IntegerField(
        _("Approval Level"),
        help_text=_("Sequential level in the approval chain (1, 2, 3...)"),
    )
    approver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="approval_tasks",
        verbose_name=_("Approver"),
    )
    status = models.CharField(
        _("Status"),
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    decision_datetime = models.DateTimeField(
        _("Decision DateTime"),
        null=True,
        blank=True,
    )
    decision_notes = models.TextField(_("Decision Notes"), blank=True)
    delegated_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="delegated_approvals",
        verbose_name=_("Delegated To"),
    )
    auto_approved = models.BooleanField(
        _("Auto-Approved"),
        default=False,
        help_text=_("Whether this was auto-approved by the system"),
    )
    
    class Meta:  # type: ignore[override]
        verbose_name = _("Swap Approval Chain")
        verbose_name_plural = _("Swap Approval Chains")
        ordering = ["swap_request", "level"]
        unique_together = [["swap_request", "level"]]
    
    def __str__(self):
        return f"{self.swap_request} - Level {self.level} ({self.get_status_display()})"
    
    def approve(self, decision_notes: str = ""):
        """Mark this approval step as approved."""
        from django.utils import timezone
        self.status = self.Status.APPROVED
        self.decision_datetime = timezone.now()
        self.decision_notes = decision_notes
        self.save()
    
    def reject(self, decision_notes: str = ""):
        """Mark this approval step as rejected."""
        from django.utils import timezone
        self.status = self.Status.REJECTED
        self.decision_datetime = timezone.now()
        self.decision_notes = decision_notes
        self.save()
    
    def delegate(self, user, notes: str = ""):
        """
        Delegate this approval to another user.
        Creates a new approval chain entry for the delegate.
        """
        from django.utils import timezone
        self.status = self.Status.DELEGATED
        self.delegated_to = user
        self.decision_datetime = timezone.now()
        self.decision_notes = notes
        self.save()
        
        # Create new chain entry for delegate
        new_step = SwapApprovalChain.objects.create(
            swap_request=self.swap_request,
            approval_rule=self.approval_rule,
            level=self.level,
            approver=user,
            status=self.Status.PENDING,
        )
        return new_step


class ApprovalDelegation(TimeStampedModel):
    """
    Manages approval delegation relationships.
    
    Allows approvers to temporarily delegate their approval authority
    to another user for a specified time period.
    """
    
    delegator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="delegations_granted",
        verbose_name=_("Delegator"),
    )
    delegate = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="delegations_received",
        verbose_name=_("Delegate"),
    )
    start_date = models.DateField(_("Start Date"))
    end_date = models.DateField(
        _("End Date"),
        null=True,
        blank=True,
        help_text=_("Leave blank for indefinite delegation"),
    )
    is_active = models.BooleanField(_("Is Active"), default=True)
    reason = models.TextField(_("Reason"), blank=True)
    
    class Meta:  # type: ignore[override]
        verbose_name = _("Approval Delegation")
        verbose_name_plural = _("Approval Delegations")
        ordering = ["-start_date"]
    
    def __str__(self):
        return f"{self.delegator} → {self.delegate} ({self.start_date})"
    
    @property
    def is_currently_active(self) -> bool:
        """Check if delegation is currently active based on dates."""
        from datetime import date
        if not self.is_active:
            return False
        today = date.today()
        if self.start_date > today:
            return False
        if self.end_date and self.end_date < today:
            return False
        return True


class SwapApprovalAudit(TimeStampedModel):
    """
    Audit trail for swap approval actions.
    
    Records all actions taken on swap requests for compliance and debugging.
    """
    
    class Action(models.TextChoices):
        CREATED = "created", _("Created")
        APPROVED = "approved", _("Approved")
        REJECTED = "rejected", _("Rejected")
        CANCELLED = "cancelled", _("Cancelled")
        DELEGATED = "delegated", _("Delegated")
        AUTO_APPROVED = "auto_approved", _("Auto-Approved")
        RULE_APPLIED = "rule_applied", _("Rule Applied")
        ESCALATED = "escalated", _("Escalated")
    
    swap_request = models.ForeignKey(
        "SwapRequest",
        on_delete=models.CASCADE,
        related_name="audit_trail",
        verbose_name=_("Swap Request"),
    )
    action = models.CharField(
        _("Action"),
        max_length=20,
        choices=Action.choices,
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="swap_audit_actions",
        verbose_name=_("Actor"),
        help_text=_("User who performed the action (null for system actions)"),
    )
    approval_chain = models.ForeignKey(
        "SwapApprovalChain",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_entries",
        verbose_name=_("Approval Chain"),
    )
    approval_rule = models.ForeignKey(
        "SwapApprovalRule",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_entries",
        verbose_name=_("Approval Rule"),
    )
    notes = models.TextField(_("Notes"), blank=True)
    metadata = models.JSONField(
        _("Metadata"),
        default=dict,
        blank=True,
        help_text=_("Additional structured data about the action"),
    )
    
    class Meta:  # type: ignore[override]
        verbose_name = _("Swap Approval Audit")
        verbose_name_plural = _("Swap Approval Audits")
        ordering = ["-created"]
    
    def __str__(self):
        actor_name = self.actor if self.actor else "System"
        return f"{self.get_action_display()} by {actor_name} at {self.created}"
