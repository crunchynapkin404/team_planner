from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import Department, Team, TeamMembership


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ["name", "manager", "created", "modified"]
    list_filter = ["created", "modified"]
    search_fields = ["name", "description"]
    readonly_fields = ["created", "modified"]
    
    fieldsets = (
        (None, {
            "fields": ("name", "description", "manager")
        }),
        (_("Timestamps"), {
            "fields": ("created", "modified"),
            "classes": ("collapse",),
        }),
    )


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "department",
        "manager",
        "timezone",
        "waakdienst_handover_weekday",
        "member_count",
        "created",
    ]
    list_filter = [
        "department",
        "standby_mode",
        "incidents_skip_holidays",
        "created",
        "modified",
    ]
    search_fields = ["name", "description", "department__name"]
    readonly_fields = ["created", "modified"]
    
    fieldsets = (
        (None, {
            "fields": ("name", "department", "description", "manager")
        }),
        (_("Scheduling & Fairness"), {
            "fields": (
                "timezone",
                "waakdienst_handover_weekday",
                "waakdienst_start_hour",
                "waakdienst_end_hour",
                "incidents_skip_holidays",
                "standby_mode",
                "fairness_window_weeks",
                "joiner_grace_weeks",
                "joiner_bootstrap_credit_hours",
            )
        }),
        (_("Timestamps"), {
            "fields": ("created", "modified"),
            "classes": ("collapse",),
        }),
    )
    
    @admin.display(description=_("Active Members"))
    def member_count(self, obj):
        return obj.teammembership_set.filter(is_active=True).count()


@admin.register(TeamMembership)
class TeamMembershipAdmin(admin.ModelAdmin):
    list_display = ["user", "team", "role", "fte", "joined_date", "is_active"]
    list_filter = ["role", "is_active", "joined_date", "team__department"]
    search_fields = ["user__username", "user__first_name", "user__last_name", "team__name"]
    readonly_fields = ["created", "modified"]
    
    fieldsets = (
        (None, {
            "fields": ("user", "team", "role", "fte", "is_active")
        }),
        (_("Timestamps"), {
            "fields": ("joined_date", "created", "modified"),
            "classes": ("collapse",),
        }),
    )
