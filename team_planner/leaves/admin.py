from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import Holiday
from .models import LeaveRequest
from .models import LeaveType


@admin.register(LeaveType)
class LeaveTypeAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "default_days_per_year",
        "requires_approval",
        "is_paid",
        "is_active",
    ]
    list_filter = ["requires_approval", "is_paid", "is_active", "created"]
    search_fields = ["name", "description"]
    ordering = ["name"]

    fieldsets = (
        (_("Basic Information"), {"fields": ("name", "description", "color")}),
        (
            _("Leave Policy"),
            {
                "fields": (
                    "default_days_per_year",
                    "requires_approval",
                    "is_paid",
                    "is_active",
                ),
            },
        ),
    )


@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = [
        "employee_name",
        "leave_type",
        "start_date",
        "end_date",
        "days_requested",
        "status",
        "created",
    ]
    list_filter = ["status", "leave_type", "start_date", "created"]
    search_fields = [
        "employee__username",
        "employee__first_name",
        "employee__last_name",
        "reason",
    ]
    ordering = ["-created"]

    fieldsets = (
        (
            _("Leave Details"),
            {
                "fields": (
                    "employee",
                    "leave_type",
                    "start_date",
                    "end_date",
                    "days_requested",
                ),
            },
        ),
        (_("Request Information"), {"fields": ("reason", "status")}),
        (
            _("Approval"),
            {
                "fields": ("approved_by", "approved_at", "rejection_reason"),
                "classes": ("collapse",),
            },
        ),
    )

    def employee_name(self, obj):
        return obj.employee.get_full_name() or obj.employee.username

    employee_name.short_description = _("Employee")  # type: ignore


@admin.register(Holiday)
class HolidayAdmin(admin.ModelAdmin):
    list_display = ["name", "date", "is_recurring", "created"]
    list_filter = ["is_recurring", "date", "created"]
    search_fields = ["name", "description"]
    ordering = ["date"]

    fieldsets = (
        (_("Holiday Information"), {"fields": ("name", "date", "description")}),
        (_("Settings"), {"fields": ("is_recurring",)}),
    )
