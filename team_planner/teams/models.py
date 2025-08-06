from django.conf import settings
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
        verbose_name=_("Department Manager")
    )

    class Meta:
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
        verbose_name=_("Department")
    )
    description = models.TextField(_("Description"), blank=True)
    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="managed_teams",
        verbose_name=_("Team Manager")
    )
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through="TeamMembership",
        related_name="teams",
        verbose_name=_("Team Members")
    )

    class Meta:
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
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name=_("User")
    )
    team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        verbose_name=_("Team")
    )
    role = models.CharField(
        _("Role"),
        max_length=20,
        choices=Role.choices,
        default=Role.MEMBER
    )
    joined_date = models.DateField(_("Joined Date"), auto_now_add=True)
    is_active = models.BooleanField(_("Is Active"), default=True)

    class Meta:
        verbose_name = _("Team Membership")
        verbose_name_plural = _("Team Memberships")
        unique_together = [["user", "team"]]
        ordering = ["-joined_date"]

    def __str__(self):
        return f"{self.user.username} - {self.team.name} ({self.get_role_display()})"
