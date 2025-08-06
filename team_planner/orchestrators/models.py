from decimal import Decimal
from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator

from team_planner.contrib.sites.models import TimeStampedModel


class OrchestrationRun(TimeStampedModel):
    """Track orchestration runs for auditing and rollback purposes."""
    
    class Status(models.TextChoices):
        RUNNING = "running", _("Running")
        COMPLETED = "completed", _("Completed")
        FAILED = "failed", _("Failed")
        CANCELLED = "cancelled", _("Cancelled")
        PREVIEW = "preview", _("Preview Mode")
    
    name = models.CharField(_("Run Name"), max_length=200)
    description = models.TextField(_("Description"), blank=True)
    status = models.CharField(
        _("Status"),
        max_length=20,
        choices=Status.choices,
        default=Status.RUNNING
    )
    
    # Planning period
    start_date = models.DateField(_("Planning Start Date"))
    end_date = models.DateField(_("Planning End Date"))
    
    # Execution details
    initiated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="orchestration_runs",
        verbose_name=_("Initiated By")
    )
    started_at = models.DateTimeField(_("Started At"), auto_now_add=True)
    completed_at = models.DateTimeField(_("Completed At"), null=True, blank=True)
    
    # Results and metrics
    total_shifts_created = models.PositiveIntegerField(_("Total Shifts Created"), default=0)
    incidents_shifts_created = models.PositiveIntegerField(_("Incidents Shifts Created"), default=0)
    waakdienst_shifts_created = models.PositiveIntegerField(_("Waakdienst Shifts Created"), default=0)
    
    # Configuration used
    max_consecutive_weeks = models.PositiveIntegerField(
        _("Max Consecutive Weeks"),
        default=2,
        help_text=_("Maximum consecutive weeks same person can be assigned")
    )
    fairness_weight = models.DecimalField(
        _("Fairness Weight"),
        max_digits=3,
        decimal_places=2,
        default=Decimal("1.00"),
        validators=[MinValueValidator(Decimal("0.1")), MaxValueValidator(Decimal("2.0"))],
        help_text=_("Weight given to fairness vs other constraints")
    )
    
    # Execution log
    execution_log = models.TextField(_("Execution Log"), blank=True)
    error_message = models.TextField(_("Error Message"), blank=True)
    
    class Meta:
        verbose_name = _("Orchestration Run")
        verbose_name_plural = _("Orchestration Runs")
        ordering = ["-started_at"]
    
    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"
    
    def get_absolute_url(self):
        return reverse("orchestrators:run_detail", kwargs={"pk": self.pk})
    
    @property
    def duration(self):
        """Calculate execution duration."""
        if self.completed_at and self.started_at:
            return self.completed_at - self.started_at
        return None
    
    @property
    def is_active(self):
        """Check if orchestration is currently running."""
        return self.status == self.Status.RUNNING


class OrchestrationResult(TimeStampedModel):
    """Individual shift assignments created during orchestration."""
    
    orchestration_run = models.ForeignKey(
        OrchestrationRun,
        on_delete=models.CASCADE,
        related_name="results",
        verbose_name=_("Orchestration Run")
    )
    
    # Employee assignment
    employee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="orchestration_results",
        verbose_name=_("Employee")
    )
    
    # Shift details
    shift_type = models.CharField(
        _("Shift Type"),
        max_length=20,
        choices=[
            ("incidents", _("Incidents")),
            ("waakdienst", _("Waakdienst")),
        ]
    )
    week_start_date = models.DateField(_("Week Start Date"))
    week_end_date = models.DateField(_("Week End Date"))
    
    # Assignment reasoning
    fairness_score_before = models.DecimalField(
        _("Fairness Score Before"),
        max_digits=8,
        decimal_places=2,
        help_text=_("Employee's fairness score before this assignment")
    )
    fairness_score_after = models.DecimalField(
        _("Fairness Score After"),
        max_digits=8,
        decimal_places=2,
        help_text=_("Employee's fairness score after this assignment")
    )
    assignment_reason = models.TextField(
        _("Assignment Reason"),
        help_text=_("Algorithm's reason for this assignment")
    )
    
    # Status tracking
    is_applied = models.BooleanField(
        _("Is Applied"),
        default=False,
        help_text=_("Whether this result has been applied to create actual shifts")
    )
    applied_at = models.DateTimeField(_("Applied At"), null=True, blank=True)
    
    class Meta:
        verbose_name = _("Orchestration Result")
        verbose_name_plural = _("Orchestration Results")
        ordering = ["week_start_date", "shift_type", "employee__username"]
        unique_together = [["orchestration_run", "shift_type", "week_start_date"]]
    
    def __str__(self):
        return f"{self.employee.username} - {self.get_shift_type_display()} (Week {self.week_start_date})"
    
    def get_absolute_url(self):
        return reverse("orchestrators:result_detail", kwargs={"pk": self.pk})


class OrchestrationConstraint(TimeStampedModel):
    """Define constraints for the orchestration algorithm."""
    
    class ConstraintType(models.TextChoices):
        AVAILABILITY = "availability", _("Availability")
        LEAVE_CONFLICT = "leave_conflict", _("Leave Conflict")
        MAX_CONSECUTIVE = "max_consecutive", _("Max Consecutive Weeks")
        SKILL_REQUIREMENT = "skill_requirement", _("Skill Requirement")
        FAIRNESS_THRESHOLD = "fairness_threshold", _("Fairness Threshold")
        CUSTOM = "custom", _("Custom")
    
    class Severity(models.TextChoices):
        HARD = "hard", _("Hard Constraint (Must Not Violate)")
        SOFT = "soft", _("Soft Constraint (Prefer Not to Violate)")
        ADVISORY = "advisory", _("Advisory (Track Only)")
    
    orchestration_run = models.ForeignKey(
        OrchestrationRun,
        on_delete=models.CASCADE,
        related_name="constraints",
        verbose_name=_("Orchestration Run")
    )
    
    constraint_type = models.CharField(
        _("Constraint Type"),
        max_length=30,
        choices=ConstraintType.choices
    )
    severity = models.CharField(
        _("Severity"),
        max_length=20,
        choices=Severity.choices,
        default=Severity.HARD
    )
    
    # Constraint details
    employee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="orchestration_constraints",
        verbose_name=_("Employee"),
        help_text=_("Employee this constraint applies to (null = all employees)")
    )
    start_date = models.DateField(_("Start Date"), null=True, blank=True)
    end_date = models.DateField(_("End Date"), null=True, blank=True)
    shift_type = models.CharField(
        _("Shift Type"),
        max_length=20,
        blank=True,
        help_text=_("Shift type this constraint applies to (empty = all types)")
    )
    
    description = models.TextField(_("Description"))
    is_active = models.BooleanField(_("Is Active"), default=True)
    
    # Violation tracking
    violations_count = models.PositiveIntegerField(_("Violations Count"), default=0)
    violation_details = models.TextField(_("Violation Details"), blank=True)
    
    class Meta:
        verbose_name = _("Orchestration Constraint")
        verbose_name_plural = _("Orchestration Constraints")
        ordering = ["severity", "constraint_type"]
    
    def __str__(self):
        employee_part = f" ({self.employee.username})" if self.employee else " (All)"
        return f"{self.get_constraint_type_display()}{employee_part} - {self.get_severity_display()}"
    
    def get_absolute_url(self):
        return reverse("orchestrators:constraint_detail", kwargs={"pk": self.pk})
