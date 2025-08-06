from decimal import Decimal
from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from team_planner.contrib.sites.models import TimeStampedModel


class EmployeeSkill(TimeStampedModel):
    """Skills that employees can have for shift assignments."""
    
    name = models.CharField(_("Skill Name"), max_length=100, unique=True)
    description = models.TextField(_("Description"), blank=True)
    is_active = models.BooleanField(_("Is Active"), default=True)
    
    class Meta:
        verbose_name = _("Employee Skill")
        verbose_name_plural = _("Employee Skills")
        ordering = ["name"]
    
    def __str__(self):
        return self.name
    
    def get_absolute_url(self):
        return reverse("employees:skill_detail", kwargs={"pk": self.pk})


class EmployeeProfile(TimeStampedModel):
    """Extended user profile for employees."""
    
    class EmploymentType(models.TextChoices):
        FULL_TIME = "full_time", _("Full Time")
        PART_TIME = "part_time", _("Part Time")
        CONTRACT = "contract", _("Contract")
        INTERN = "intern", _("Intern")
    
    class Status(models.TextChoices):
        ACTIVE = "active", _("Active")
        INACTIVE = "inactive", _("Inactive")
        ON_LEAVE = "on_leave", _("On Leave")
        TERMINATED = "terminated", _("Terminated")
    
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="employee_profile",
        verbose_name=_("User"),
    )
    employee_id = models.CharField(
        _("Employee ID"),
        max_length=20,
        unique=True,
        help_text=_("Unique employee identifier"),
    )
    phone_number = models.CharField(
        _("Phone Number"),
        max_length=20,
        blank=True,
    )
    emergency_contact_name = models.CharField(
        _("Emergency Contact Name"),
        max_length=100,
        blank=True,
    )
    emergency_contact_phone = models.CharField(
        _("Emergency Contact Phone"),
        max_length=20,
        blank=True,
    )
    employment_type = models.CharField(
        _("Employment Type"),
        max_length=20,
        choices=EmploymentType.choices,
        default=EmploymentType.FULL_TIME,
    )
    status = models.CharField(
        _("Status"),
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    hire_date = models.DateField(_("Hire Date"))
    termination_date = models.DateField(
        _("Termination Date"),
        null=True,
        blank=True,
    )
    salary = models.DecimalField(
        _("Salary"),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Annual salary"),
    )
    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="managed_employees",
        verbose_name=_("Manager"),
    )
    
    # Shift availability toggles (Phase 1 requirement)
    available_for_incidents = models.BooleanField(
        _("Available for Incidents"),
        default=False,
        help_text=_("Can be assigned to incident shifts (Monday-Friday, 8:00-17:00)")
    )
    available_for_waakdienst = models.BooleanField(
        _("Available for Waakdienst"),
        default=False,
        help_text=_("Can be assigned to on-call/standby shifts (evenings, nights, weekends)")
    )
    
    # Skills many-to-many relationship
    skills = models.ManyToManyField(
        EmployeeSkill,
        blank=True,
        related_name="employees",
        verbose_name=_("Skills"),
        help_text=_("Skills possessed by this employee")
    )
    
    class Meta:
        verbose_name = _("Employee Profile")
        verbose_name_plural = _("Employee Profiles")
        ordering = ["employee_id"]
    
    def __str__(self):
        return f"{self.user.get_full_name()} ({self.employee_id})"
    
    def get_absolute_url(self):
        return reverse("employees:profile_detail", kwargs={"pk": self.pk})
    
    @property
    def is_active(self):
        return self.status == self.Status.ACTIVE
    
    @property
    def full_name(self):
        return self.user.get_full_name() or self.user.username


class LeaveBalance(TimeStampedModel):
    """Employee leave balance tracking."""
    
    employee = models.ForeignKey(
        EmployeeProfile,
        on_delete=models.CASCADE,
        related_name="leave_balances",
        verbose_name=_("Employee"),
    )
    leave_type = models.ForeignKey(
        "leaves.LeaveType",
        on_delete=models.CASCADE,
        verbose_name=_("Leave Type"),
    )
    total_days = models.DecimalField(
        _("Total Days"),
        max_digits=5,
        decimal_places=1,
        default=Decimal("0.0"),
        help_text=_("Total allocated leave days for the year"),
    )
    used_days = models.DecimalField(
        _("Used Days"),
        max_digits=5,
        decimal_places=1,
        default=Decimal("0.0"),
        help_text=_("Leave days already used"),
    )
    year = models.PositiveIntegerField(_("Year"))
    
    class Meta:
        verbose_name = _("Leave Balance")
        verbose_name_plural = _("Leave Balances")
        unique_together = [["employee", "leave_type", "year"]]
        ordering = ["-year", "leave_type__name"]
    
    def __str__(self):
        return f"{self.employee.user.username} - {self.leave_type.name} ({self.year})"
    
    @property
    def remaining_days(self):
        return self.total_days - self.used_days
    
    @property
    def is_exhausted(self):
        return self.remaining_days <= 0
