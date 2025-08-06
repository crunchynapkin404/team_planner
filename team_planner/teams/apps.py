from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class TeamsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "team_planner.teams"
    verbose_name = _("Teams")
