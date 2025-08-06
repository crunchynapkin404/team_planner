from django.urls import path

from . import views

app_name = "leaves"

urlpatterns = [
    # Leave Request URLs
    path("", views.leave_dashboard, name="dashboard"),
    path("requests/", views.LeaveRequestListView.as_view(), name="leave_request_list"),
    path("requests/<int:pk>/", views.LeaveRequestDetailView.as_view(), name="leave_request_detail"),
    path("requests/create/", views.create_leave_request, name="create_leave_request"),
    path("requests/<int:pk>/approve/", views.approve_leave_request, name="approve_leave_request"),
    path("requests/<int:pk>/reject/", views.reject_leave_request, name="reject_leave_request"),
    path("requests/<int:pk>/cancel/", views.cancel_leave_request, name="cancel_leave_request"),
    
    # AJAX URLs
    path("ajax/check-conflicts/", views.check_leave_conflicts_ajax, name="check_conflicts_ajax"),
]
