from django.urls import path

from . import api
from . import api_v2
from . import views

app_name = "orchestrators"

urlpatterns = [
    # Dashboard
    path("", views.orchestrator_dashboard, name="dashboard"),
    # Orchestration management
    path("create/", views.create_orchestration, name="create"),
    path("detail/<int:pk>/", views.orchestration_detail, name="detail"),
    path(
        "<int:pk>/", views.orchestration_detail, name="run_detail",
    ),  # Keep for compatibility
    # Automation trigger (synchronous)
    path("automation/run-now/", views.run_horizon_now, name="run_horizon_now"),
    # Reports
    path("fairness/", views.fairness_report, name="fairness_report"),
    # V1 API endpoints for React frontend (legacy)
    path("api/create/", api.orchestrator_create_api, name="create_api"),
    path(
        "api/apply-preview/",
        api.orchestrator_apply_preview_api,
        name="apply_preview_api",
    ),
    path("api/status/", api.orchestrator_status_api, name="status_api"),
    path("api/fairness/", api.fairness_api, name="fairness_api"),
    path("api/run-horizon/", api.orchestrator_run_horizon_api, name="run_horizon_api"),
    path(
        "api/run-horizon-async/",
        api.orchestrator_run_horizon_async_api,
        name="run_horizon_async_api",
    ),
    path(
        "api/automation-status/",
        api.orchestrator_automation_status_api,
        name="automation_status_api",
    ),
    path("api/enable-auto/", api.orchestrator_enable_auto_api, name="enable_auto_api"),
    path(
        "api/clear-shifts/", api.orchestrator_clear_shifts_api, name="clear_shifts_api",
    ),
    path(
        "api/auto-overview/",
        api.orchestrator_auto_overview_api,
        name="auto_overview_api",
    ),
    path("api/auto-toggle/", api.orchestrator_auto_toggle_api, name="auto_toggle_api"),
    # V2 API endpoints for improved React frontend
    path(
        "api/orchestrator/schedule/",
        api_v2.orchestrator_schedule_v2,
        name="schedule_v2",
    ),
    path(
        "api/orchestrator/coverage/",
        api_v2.orchestrator_coverage_v2,
        name="coverage_v2",
    ),
    path(
        "api/orchestrator/availability/",
        api_v2.orchestrator_availability_v2,
        name="availability_v2",
    ),
    path(
        "api/orchestrator/reset-history/",
        api_v2.reset_assignment_history_v2,
        name="reset_history_v2",
    ),
    path(
        "api/orchestrator/assignment-history-preview/",
        api_v2.assignment_history_preview_v2,
        name="assignment_history_preview_v2",
    ),
    path(
        "api/orchestrator-status/health/",
        api_v2.orchestrator_health_v2,
        name="health_v2",
    ),
    path(
        "api/orchestrator-status/metrics/",
        api_v2.orchestrator_metrics_v2,
        name="metrics_v2",
    ),
    # Preview system (placeholder views for now)
    # path('preview/', views.preview_view, name='preview'),
    # path('apply-preview/', views.apply_preview, name='apply_preview'),
]
