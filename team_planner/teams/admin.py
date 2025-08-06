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
    list_display = ["name", "department", "manager", "member_count", "created"]
    list_filter = ["department", "created", "modified"]
    search_fields = ["name", "description", "department__name"]
    readonly_fields = ["created", "modified"]
    
    fieldsets = (
        (None, {
            "fields": ("name", "department", "description", "manager")
        }),
        (_("Timestamps"), {
            "fields": ("created", "modified"),
            "classes": ("collapse",),
        }),
    )
    
    def member_count(self, obj):
        return obj.teammembership_set.filter(is_active=True).count()
    member_count.short_description = _("Active Members")


@admin.register(TeamMembership)
class TeamMembershipAdmin(admin.ModelAdmin):
    list_display = ["user", "team", "role", "joined_date", "is_active"]
    list_filter = ["role", "is_active", "joined_date", "team__department"]
    search_fields = ["user__username", "user__first_name", "user__last_name", "team__name"]
    readonly_fields = ["created", "modified"]
    
    fieldsets = (
        (None, {
            "fields": ("user", "team", "role", "is_active")
        }),
        (_("Timestamps"), {
            "fields": ("joined_date", "created", "modified"),
            "classes": ("collapse",),
        }),
    )
