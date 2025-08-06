from django.urls import path

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
    path("<int:shift_pk>/create-swap/", views.create_swap_request, name="create_swap_request"),
    path("swaps/<int:pk>/respond/", views.respond_to_swap_request, name="respond_to_swap"),
    path("swaps/<int:pk>/cancel/", views.cancel_swap_request, name="cancel_swap_request"),
    
    # AJAX URLs
    path("ajax/target-shifts/", views.get_target_shifts_ajax, name="target_shifts_ajax"),
    
    # API URLs
    path("api/shifts/", views.shifts_api, name="shifts_api"),
]
