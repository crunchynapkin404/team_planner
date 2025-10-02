from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class NotificationsConfig(AppConfig):
    name = "team_planner.notifications"
    verbose_name = _("Notifications")

    def ready(self):
        try:
            import team_planner.notifications.signals  # noqa: F401
        except ImportError:
            pass
