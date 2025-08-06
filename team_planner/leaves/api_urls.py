from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api import LeaveRequestViewSet, LeaveTypeViewSet

router = DefaultRouter()
router.register('requests', LeaveRequestViewSet, basename='leaverequest')
router.register('leave-types', LeaveTypeViewSet, basename='leavetype')

app_name = 'leaves_api'

urlpatterns = [
    path('', include(router.urls)),
]
