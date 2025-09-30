from django.urls import path

from . import api
from . import views

app_name = "shifts"

urlpatterns = [
    # Shift URLs
    path("", views.ShiftListView.as_view(), name="shift_list"),
    path("<int:pk>/", views.ShiftDetailView.as_view(), name="shift_detail"),
    # Swap Request URLs
    path("swaps/", views.SwapRequestListView.as_view(), name="swap_list"),
    path("swaps/<int:pk>/", views.SwapRequestDetailView.as_view(), name="swap_detail"),
    path("swaps/bulk-approval/", views.bulk_swap_approval, name="bulk_swap_approval"),
    path(
        "<int:shift_pk>/create-swap/",
        views.create_swap_request,
        name="create_swap_request",
    ),
    path(
        "swaps/<int:pk>/respond/", views.respond_to_swap_request, name="respond_to_swap",
    ),
    path(
        "swaps/<int:pk>/cancel/", views.cancel_swap_request, name="cancel_swap_request",
    ),
    # AJAX URLs
    path(
        "ajax/target-shifts/", views.get_target_shifts_ajax, name="target_shifts_ajax",
    ),
    # API URLs
    path("api/shifts/", views.shifts_api, name="shifts_api"),
    path("api/dashboard/", views.dashboard_api, name="dashboard_api"),
    path(
        "api/swap-requests/<int:pk>/respond/",
        api.respond_to_swap_request_api,
        name="respond_to_swap_api",
    ),
    path(
        "api/swap-requests/create/",
        api.create_swap_request_api,
        name="create_swap_request_api",
    ),
    path(
        "api/swap-requests/bulk-create/",
        api.create_bulk_swap_request_api,
        name="create_bulk_swap_request_api",
    ),
    path(
        "api/user/upcoming-shifts/",
        api.user_upcoming_shifts_api,
        name="user_upcoming_shifts_api",
    ),
    path("api/user/shifts/", api.get_user_shifts_api, name="user_shifts_api"),
    path(
        "api/user/incoming-swap-requests/",
        api.user_incoming_swap_requests_api,
        name="user_incoming_swap_requests_api",
    ),
    path(
        "api/user/outgoing-swap-requests/",
        api.user_outgoing_swap_requests_api,
        name="user_outgoing_swap_requests_api",
    ),
    path("api/team-members/", api.get_team_members_api, name="team_members_api"),
    path(
        "api/employee-shifts/", api.get_employee_shifts_api, name="employee_shifts_api",
    ),
]
