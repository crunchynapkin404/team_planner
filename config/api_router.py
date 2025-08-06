from django.conf import settings
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework.routers import SimpleRouter

from team_planner.users.api.views import UserViewSet
from team_planner.leaves.api import LeaveRequestViewSet, LeaveTypeViewSet

router = DefaultRouter() if settings.DEBUG else SimpleRouter()

router.register("users", UserViewSet)
router.register("leaves/requests", LeaveRequestViewSet, basename='leaverequest')
router.register("leaves/leave-types", LeaveTypeViewSet, basename='leavetype')


app_name = "api"
urlpatterns = router.urls + [
    path("teams/", include("team_planner.teams.urls", namespace="teams")),
]
