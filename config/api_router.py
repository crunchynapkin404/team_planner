from django.conf import settings
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework.routers import SimpleRouter

from team_planner.users.api.views import UserViewSet
from team_planner.leaves.api import LeaveRequestViewSet, LeaveTypeViewSet
from team_planner.teams.views import departments_list_api
from team_planner.employees.api.views import RecurringLeavePatternViewSet
# Import V2 orchestrator API endpoints
from team_planner.orchestrators import api_v2

router = DefaultRouter() if settings.DEBUG else SimpleRouter()

router.register("users", UserViewSet)
router.register("leaves/requests", LeaveRequestViewSet, basename='leaverequest')
router.register("leaves/leave-types", LeaveTypeViewSet, basename='leavetype')
router.register("recurring-leave-patterns", RecurringLeavePatternViewSet, basename='recurring-leave-patterns')

app_name = "api"
urlpatterns = router.urls + [
    path("teams/", include("team_planner.teams.urls", namespace="teams")),
    path("departments/", departments_list_api, name="departments_list"),
    # User-specific recurring leave patterns
    path("users/<int:user_pk>/recurring-leave-patterns/", 
         RecurringLeavePatternViewSet.as_view({'get': 'list', 'post': 'create'}), 
         name='user-recurring-leave-patterns-list'),
    path("users/<int:user_pk>/recurring-leave-patterns/<int:pk>/", 
         RecurringLeavePatternViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}), 
         name='user-recurring-leave-patterns-detail'),
    
    # V2 Orchestrator API endpoints
    path("orchestrator/schedule/", api_v2.orchestrator_schedule_v2, name="orchestrator_schedule_v2"),
    path("orchestrator/coverage/", api_v2.orchestrator_coverage_v2, name="orchestrator_coverage_v2"),
    path("orchestrator/availability/", api_v2.orchestrator_availability_v2, name="orchestrator_availability_v2"),
    path("orchestrator-status/health/", api_v2.orchestrator_health_v2, name="orchestrator_health_v2"),
    path("orchestrator-status/metrics/", api_v2.orchestrator_metrics_v2, name="orchestrator_metrics_v2"),
]
