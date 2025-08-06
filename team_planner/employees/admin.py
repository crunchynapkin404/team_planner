from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import EmployeeProfile, EmployeeSkill, LeaveBalance


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
        "hire_date"
    ]
    list_filter = [
        "employment_type", 
        "status", 
        "available_for_incidents",
        "available_for_waakdienst",
        "hire_date"
    ]
    search_fields = ["employee_id", "user__username", "user__first_name", "user__last_name"]
    ordering = ["employee_id"]
    
    fieldsets = (
        (_("Basic Information"), {
            "fields": ("user", "employee_id", "phone_number")
        }),
        (_("Employment Details"), {
            "fields": ("employment_type", "status", "hire_date", "termination_date", "salary", "manager")
        }),
        (_("Emergency Contact"), {
            "fields": ("emergency_contact_name", "emergency_contact_phone"),
            "classes": ("collapse",)
        }),
        (_("Shift Availability"), {
            "fields": ("available_for_incidents", "available_for_waakdienst"),
            "description": _("Toggles for shift assignment eligibility")
        }),
        (_("Skills"), {
            "fields": ("skills",),
            "description": _("Skills possessed by this employee")
        }),
    )
    
    filter_horizontal = ["skills"]
    inlines = [LeaveBalanceInline]
    
    def full_name(self, obj):
        return obj.full_name
    full_name.short_description = _("Full Name")  # type: ignore


@admin.register(LeaveBalance)
class LeaveBalanceAdmin(admin.ModelAdmin):
    list_display = ["employee", "leave_type", "year", "total_days", "used_days", "remaining_days"]
    list_filter = ["year", "leave_type", "created"]
    search_fields = ["employee__user__username", "employee__employee_id", "leave_type__name"]
    ordering = ["-year", "employee__employee_id"]
    
    def remaining_days(self, obj):
        return obj.remaining_days
    remaining_days.short_description = _("Remaining Days")  # type: ignore
