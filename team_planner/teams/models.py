from django.conf import settings
from django.core.validators import MaxValueValidator
from django.core.validators import MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from team_planner.contrib.sites.models import TimeStampedModel


class Department(TimeStampedModel):
    """Department model for organizing teams."""

    name = models.CharField(_("Department Name"), max_length=100, unique=True)
    description = models.TextField(_("Description"), blank=True)
    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="managed_departments",
        verbose_name=_("Department Manager"),
    )

    class Meta:  # type: ignore[override]
        verbose_name = _("Department")
        verbose_name_plural = _("Departments")
        ordering = ["name"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("teams:department_detail", kwargs={"pk": self.pk})


class Team(TimeStampedModel):
    """Team model for organizing employees."""

    name = models.CharField(_("Team Name"), max_length=100)
    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name="teams",
        verbose_name=_("Department"),
    )
    description = models.TextField(_("Description"), blank=True)
    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="managed_teams",
        verbose_name=_("Team Manager"),
    )
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through="TeamMembership",
        related_name="teams",
        verbose_name=_("Team Members"),
    )

    # Scheduling & fairness preferences
    timezone = models.CharField(
        _("Timezone"),
        max_length=64,
        default="Europe/Amsterdam",
        help_text=_(
            "IANA timezone name for this team's scheduling (e.g., Europe/Amsterdam)",
        ),
    )
    waakdienst_handover_weekday = models.PositiveSmallIntegerField(
        _("Waakdienst Handover Weekday"),
        default=2,  # Wednesday (Mon=0)
        validators=[MinValueValidator(0), MaxValueValidator(6)],
        help_text=_("0=Mon … 6=Sun; default Wednesday"),
    )
    waakdienst_start_hour = models.PositiveSmallIntegerField(
        _("Waakdienst Start Hour"),
        default=17,
        validators=[MinValueValidator(0), MaxValueValidator(23)],
        help_text=_("Hour of day (0–23) for waakdienst handover start; default 17"),
    )
    waakdienst_end_hour = models.PositiveSmallIntegerField(
        _("Waakdienst End Hour"),
        default=8,
        validators=[MinValueValidator(0), MaxValueValidator(23)],
        help_text=_("Hour of day (0–23) for next handover end; default 8"),
    )
    incidents_skip_holidays = models.BooleanField(
        _("Skip Incidents/Standby on Holidays"),
        default=True,
        help_text=_(
            "If true, do not generate incidents/standby on holidays; waakdienst continues",
        ),
    )

    class StandbyMode(models.TextChoices):
        GLOBAL_PER_WEEK = "global_per_week", _("Global per week")
        OPTIONAL_PER_WEEK = "optional_per_week", _("Optional per week")

    standby_mode = models.CharField(
        _("Standby Mode"),
        max_length=32,
        choices=StandbyMode.choices,
        default=StandbyMode.OPTIONAL_PER_WEEK,
        help_text=_("Initial policy for incidents-standby scheduling"),
    )

    fairness_window_weeks = models.PositiveSmallIntegerField(
        _("Fairness Window (weeks)"),
        default=26,
        validators=[MinValueValidator(1), MaxValueValidator(104)],
        help_text=_("Rolling window size for fairness calculations; default 26 weeks"),
    )
    joiner_grace_weeks = models.PositiveSmallIntegerField(
        _("Joiner Grace (weeks)"),
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(52)],
        help_text=_(
            "Weeks after joining before heavy shifts (e.g., waakdienst) are assigned",
        ),
    )
    joiner_bootstrap_credit_hours = models.DecimalField(
        _("Joiner Bootstrap Credit (hours)"),
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        default=None,
        help_text=_(
            "Optional initial credit hours for fairness; leave blank to disable",
        ),
    )

    class Meta:  # type: ignore[override]
        verbose_name = _("Team")
        verbose_name_plural = _("Teams")
        ordering = ["department__name", "name"]
        unique_together = [["name", "department"]]

    def __str__(self):
        return f"{self.department.name} - {self.name}"

    def get_absolute_url(self):
        return reverse("teams:team_detail", kwargs={"pk": self.pk})


class TeamMembership(TimeStampedModel):
    """Through model for Team-User relationship with additional fields."""

    class Role(models.TextChoices):
        MEMBER = "member", _("Member")
        LEAD = "lead", _("Team Lead")
        SENIOR = "senior", _("Senior Member")

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name=_("User"),
    )
    team = models.ForeignKey(Team, on_delete=models.CASCADE, verbose_name=_("Team"))
    role = models.CharField(
        _("Role"), max_length=20, choices=Role.choices, default=Role.MEMBER,
    )
    joined_date = models.DateField(_("Joined Date"), auto_now_add=True)
    is_active = models.BooleanField(_("Is Active"), default=True)

    # FTE weighting for fairness expectations
    fte = models.DecimalField(
        _("FTE"),
        max_digits=4,
        decimal_places=2,
        default=1.00,
        validators=[MinValueValidator(0.10), MaxValueValidator(1.00)],
        help_text=_("Full-time equivalent (0.10 – 1.00); used for fairness weighting"),
    )

    class Meta:  # type: ignore[override]
        verbose_name = _("Team Membership")
        verbose_name_plural = _("Team Memberships")
        unique_together = [["user", "team"]]
        ordering = ["-joined_date"]

    def __str__(self):
        role_display = self.get_role_display()  # type: ignore[attr-defined]
        return f"{self.user.username} - {self.team.name} ({role_display})"
