from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class LeavesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "team_planner.leaves"
    verbose_name = _("Leaves")
