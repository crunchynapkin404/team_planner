"""URL configuration for reports API."""
from django.urls import path

from . import api

app_name = "reports"

urlpatterns = [
    path("schedule/", api.schedule_report, name="schedule"),
    path("fairness/", api.fairness_distribution_report, name="fairness"),
    path("leave-balance/", api.leave_balance_report, name="leave-balance"),
    path("swap-history/", api.swap_history_report, name="swap-history"),
    path("employee-hours/", api.employee_hours_report, name="employee-hours"),
    path("weekend-holiday/", api.weekend_holiday_distribution_report, name="weekend-holiday"),
]
