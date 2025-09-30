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
        help_text=_("Can be assigned to incident shifts (Monday-Friday, 8:00-17:00)"),
    )
    available_for_waakdienst = models.BooleanField(
        _("Available for Waakdienst"),
        default=False,
        help_text=_(
            "Can be assigned to on-call/standby shifts (evenings, nights, weekends)",
        ),
    )

    # Skills many-to-many relationship
    skills = models.ManyToManyField(
        EmployeeSkill,
        blank=True,
        related_name="employees",
        verbose_name=_("Skills"),
        help_text=_("Skills possessed by this employee"),
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


class RecurringLeavePattern(TimeStampedModel):
    """Employee recurring leave patterns for profile-based scheduling."""

    class DayOfWeek(models.IntegerChoices):
        MONDAY = 0, _("Monday")
        TUESDAY = 1, _("Tuesday")
        WEDNESDAY = 2, _("Wednesday")
        THURSDAY = 3, _("Thursday")
        FRIDAY = 4, _("Friday")

    class Frequency(models.TextChoices):
        WEEKLY = "weekly", _("Every Week")
        BIWEEKLY = "biweekly", _("Every 2 Weeks")

    class CoverageType(models.TextChoices):
        FULL_DAY = "full_day", _("Full Day (8:00-17:00)")
        MORNING = "morning", _("Morning Only (8:00-12:00)")
        AFTERNOON = "afternoon", _("Afternoon Only (12:00-17:00)")

    employee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="recurring_leave_patterns",
        verbose_name=_("Employee"),
    )

    name = models.CharField(
        _("Pattern Name"),
        max_length=100,
        help_text=_("Descriptive name for this pattern (e.g., 'Monday Mornings Off')"),
    )

    day_of_week = models.IntegerField(
        _("Day of Week"),
        choices=DayOfWeek.choices,
        help_text=_("Which day of the week this pattern applies to"),
    )

    frequency = models.CharField(
        _("Frequency"),
        max_length=20,
        choices=Frequency.choices,
        default=Frequency.WEEKLY,
        help_text=_("How often this pattern repeats"),
    )

    coverage_type = models.CharField(
        _("Coverage Type"),
        max_length=20,
        choices=CoverageType.choices,
        default=CoverageType.FULL_DAY,
        help_text=_("What part of the day is affected"),
    )

    # For biweekly patterns, we need to track which week this started
    pattern_start_date = models.DateField(
        _("Pattern Start Date"),
        help_text=_(
            "Date when this pattern first applies (important for biweekly patterns)",
        ),
    )

    effective_from = models.DateField(
        _("Effective From"), help_text=_("When this pattern becomes active"),
    )

    effective_until = models.DateField(
        _("Effective Until"),
        null=True,
        blank=True,
        help_text=_("When this pattern expires (blank = permanent)"),
    )

    is_active = models.BooleanField(
        _("Is Active"),
        default=True,
        help_text=_("Whether this pattern is currently in effect"),
    )

    notes = models.TextField(
        _("Notes"), blank=True, help_text=_("Additional notes about this pattern"),
    )

    class Meta:
        verbose_name = _("Recurring Leave Pattern")
        verbose_name_plural = _("Recurring Leave Patterns")
        ordering = ["employee__username", "day_of_week", "coverage_type"]

    def __str__(self):
        frequency_display = (
            "Every" if self.frequency == self.Frequency.WEEKLY else "Every 2nd"
        )
        day_name = self.get_day_of_week_display()
        coverage_display = self.get_coverage_type_display()
        return f"{self.employee.get_full_name()}: {frequency_display} {day_name} {coverage_display}"

    def get_absolute_url(self):
        return reverse("employees:pattern_detail", kwargs={"pk": self.pk})

    def get_hours_affected(self):
        """Return number of hours this pattern affects per occurrence."""
        if self.coverage_type == self.CoverageType.FULL_DAY:
            return 9  # 8:00-17:00
        if self.coverage_type in [
            self.CoverageType.MORNING,
            self.CoverageType.AFTERNOON,
        ]:
            return 4  # Half day
        return 0

    def applies_to_date(self, check_date):
        """Check if this pattern applies to a specific date."""
        # Check if date is within effective range
        if check_date < self.effective_from:
            return False
        if self.effective_until and check_date > self.effective_until:
            return False
        if not self.is_active:
            return False

        # Check if it's the right day of week
        if check_date.weekday() != self.day_of_week:
            return False

        # For weekly patterns, always applies if it's the right day
        if self.frequency == self.Frequency.WEEKLY:
            return True

        # For biweekly patterns, check if it's the right week
        if self.frequency == self.Frequency.BIWEEKLY:
            days_since_start = (check_date - self.pattern_start_date).days
            weeks_since_start = days_since_start // 7
            return weeks_since_start % 2 == 0

        return False

    def get_affected_hours_for_date(self, check_date):
        """Get the specific hours affected by this pattern on a given date."""
        if not self.applies_to_date(check_date):
            return None

        from datetime import datetime
        from datetime import time

        from django.utils import timezone

        if self.coverage_type == self.CoverageType.FULL_DAY:
            start_datetime = timezone.make_aware(
                datetime.combine(check_date, time(8, 0)),
            )
            end_datetime = timezone.make_aware(
                datetime.combine(check_date, time(17, 0)),
            )
        elif self.coverage_type == self.CoverageType.MORNING:
            start_datetime = timezone.make_aware(
                datetime.combine(check_date, time(8, 0)),
            )
            end_datetime = timezone.make_aware(
                datetime.combine(check_date, time(12, 0)),
            )
        elif self.coverage_type == self.CoverageType.AFTERNOON:
            start_datetime = timezone.make_aware(
                datetime.combine(check_date, time(12, 0)),
            )
            end_datetime = timezone.make_aware(
                datetime.combine(check_date, time(17, 0)),
            )
        else:
            return None

        return {
            "start_datetime": start_datetime,
            "end_datetime": end_datetime,
            "hours": self.get_hours_affected(),
        }
