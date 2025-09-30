"""
URL configuration for the orchestrator API endpoints.
"""

from django.urls import include
from django.urls import path
from rest_framework.routers import DefaultRouter

from .orchestrator_views_v2 import OrchestratorAPIViewSet
from .orchestrator_views_v2 import OrchestratorStatusView

# Create router for ViewSets
router = DefaultRouter()
router.register(r"orchestrator", OrchestratorAPIViewSet, basename="orchestrator")
router.register(
    r"orchestrator-status", OrchestratorStatusView, basename="orchestrator-status",
)

urlpatterns = [
    # API v2 endpoints (simplified, working version)
    path("v2/", include(router.urls)),
    # Direct endpoints for easier testing
    path(
        "orchestrator/schedule/",
        OrchestratorAPIViewSet.as_view({"post": "orchestrate_schedule"}),
        name="orchestrator-schedule",
    ),
    path(
        "orchestrator/coverage/",
        OrchestratorAPIViewSet.as_view({"get": "shift_coverage"}),
        name="orchestrator-coverage",
    ),
    path(
        "orchestrator/availability/",
        OrchestratorAPIViewSet.as_view({"get": "employee_availability"}),
        name="orchestrator-availability",
    ),
    path(
        "orchestrator/health/",
        OrchestratorStatusView.as_view({"get": "health"}),
        name="orchestrator-health",
    ),
    path(
        "orchestrator/metrics/",
        OrchestratorStatusView.as_view({"get": "metrics"}),
        name="orchestrator-metrics",
    ),
]
