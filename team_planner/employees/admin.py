from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import EmployeeProfile
from .models import EmployeeSkill
from .models import LeaveBalance
from .models import RecurringLeavePattern


@admin.register(EmployeeSkill)
class EmployeeSkillAdmin(admin.ModelAdmin):
    list_display = ["name", "is_active", "created", "modified"]
    list_filter = ["is_active", "created"]
    search_fields = ["name", "description"]
    ordering = ["name"]


class LeaveBalanceInline(admin.TabularInline):
    model = LeaveBalance
    extra = 0
    fields = ["leave_type", "year", "total_days", "used_days"]
    readonly_fields = ["created", "modified"]


@admin.register(EmployeeProfile)
class EmployeeProfileAdmin(admin.ModelAdmin):
    list_display = [
        "employee_id",
        "full_name",
        "employment_type",
        "status",
        "available_for_incidents",
        "available_for_waakdienst",
        "hire_date",
    ]
    list_filter = [
        "employment_type",
        "status",
        "available_for_incidents",
        "available_for_waakdienst",
        "hire_date",
    ]
    search_fields = [
        "employee_id",
        "user__username",
        "user__first_name",
        "user__last_name",
    ]
    ordering = ["employee_id"]

    fieldsets = (
        (_("Basic Information"), {"fields": ("user", "employee_id", "phone_number")}),
        (
            _("Employment Details"),
            {
                "fields": (
                    "employment_type",
                    "status",
                    "hire_date",
                    "termination_date",
                    "salary",
                    "manager",
                ),
            },
        ),
        (
            _("Emergency Contact"),
            {
                "fields": ("emergency_contact_name", "emergency_contact_phone"),
                "classes": ("collapse",),
            },
        ),
        (
            _("Shift Availability"),
            {
                "fields": ("available_for_incidents", "available_for_waakdienst"),
                "description": _("Toggles for shift assignment eligibility"),
            },
        ),
        (
            _("Skills"),
            {
                "fields": ("skills",),
                "description": _("Skills possessed by this employee"),
            },
        ),
    )

    filter_horizontal = ["skills"]
    inlines = [LeaveBalanceInline]

    def full_name(self, obj):
        return obj.full_name

    full_name.short_description = _("Full Name")  # type: ignore


@admin.register(LeaveBalance)
class LeaveBalanceAdmin(admin.ModelAdmin):
    list_display = [
        "employee",
        "leave_type",
        "year",
        "total_days",
        "used_days",
        "remaining_days",
    ]
    list_filter = ["year", "leave_type", "created"]
    search_fields = [
        "employee__user__username",
        "employee__employee_id",
        "leave_type__name",
    ]
    ordering = ["-year", "employee__employee_id"]

    def remaining_days(self, obj):
        return obj.remaining_days

    remaining_days.short_description = _("Remaining Days")  # type: ignore


@admin.register(RecurringLeavePattern)
class RecurringLeavePatternAdmin(admin.ModelAdmin):
    list_display = [
        "employee",
        "name",
        "get_pattern_display",
        "coverage_type",
        "is_active",
        "effective_from",
        "effective_until",
    ]
    list_filter = [
        "day_of_week",
        "frequency",
        "coverage_type",
        "is_active",
        "effective_from",
    ]
    search_fields = [
        "employee__username",
        "employee__first_name",
        "employee__last_name",
        "name",
    ]
    ordering = ["employee__username", "day_of_week", "coverage_type"]

    fieldsets = (
        (_("Employee & Pattern"), {"fields": ("employee", "name", "is_active")}),
        (
            _("Pattern Configuration"),
            {
                "fields": (
                    "day_of_week",
                    "frequency",
                    "coverage_type",
                    "pattern_start_date",
                ),
                "description": _("Define when and how often this pattern occurs"),
            },
        ),
        (
            _("Effective Period"),
            {
                "fields": ("effective_from", "effective_until"),
                "description": _(
                    "When this pattern is active (leave until blank for permanent)",
                ),
            },
        ),
        (_("Additional Information"), {"fields": ("notes",), "classes": ("collapse",)}),
    )

    def get_pattern_display(self, obj):
        frequency_display = "Every" if obj.frequency == "weekly" else "Every 2nd"
        day_name = obj.get_day_of_week_display()
        return f"{frequency_display} {day_name}"

    get_pattern_display.short_description = _("Pattern")  # type: ignore

    def save_model(self, request, obj, form, change):
        # Auto-set pattern_start_date if not provided
        if not obj.pattern_start_date:
            obj.pattern_start_date = obj.effective_from
        super().save_model(request, obj, form, change)
