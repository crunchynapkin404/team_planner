from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import FairnessScore
from .models import OvertimeEntry
from .models import SchedulingRule
from .models import Shift
from .models import ShiftTemplate
from .models import SwapRequest
from .models import TimeEntry


@admin.register(ShiftTemplate)
class ShiftTemplateAdmin(admin.ModelAdmin):
    list_display = ["name", "shift_type", "duration_hours", "is_active", "created"]
    list_filter = ["shift_type", "is_active", "created"]
    search_fields = ["name", "description"]
    ordering = ["shift_type", "name"]
    filter_horizontal = ["skills_required"]

    fieldsets = (
        (_("Basic Information"), {"fields": ("name", "shift_type", "description")}),
        (
            _("Configuration"),
            {"fields": ("duration_hours", "skills_required", "is_active")},
        ),
    )


@admin.register(Shift)
class ShiftAdmin(admin.ModelAdmin):
    list_display = [
        "shift_summary",
        "assigned_employee",
        "status",
        "start_datetime",
        "end_datetime",
        "auto_assigned",
    ]
    list_filter = [
        "template__shift_type",
        "status",
        "auto_assigned",
        "start_datetime",
        "created",
    ]
    search_fields = [
        "assigned_employee__username",
        "assigned_employee__first_name",
        "assigned_employee__last_name",
        "template__name",
        "notes",
    ]
    ordering = ["-start_datetime"]
    readonly_fields = ["auto_assigned", "assignment_reason"]

    fieldsets = (
        (
            _("Shift Details"),
            {
                "fields": (
                    "template",
                    "assigned_employee",
                    "start_datetime",
                    "end_datetime",
                ),
            },
        ),
        (_("Status & Notes"), {"fields": ("status", "notes")}),
        (
            _("Auto-Assignment Info"),
            {
                "fields": ("auto_assigned", "assignment_reason"),
                "classes": ("collapse",),
            },
        ),
    )

    def shift_summary(self, obj):
        return f"{obj.template.get_shift_type_display()} - {obj.start_datetime.date()}"

    shift_summary.short_description = _("Shift")  # type: ignore


@admin.register(SwapRequest)
class SwapRequestAdmin(admin.ModelAdmin):
    list_display = [
        "swap_summary",
        "status",
        "created",
        "approved_by",
        "approved_datetime",
    ]
    list_filter = ["status", "created", "approved_datetime"]
    search_fields = [
        "requesting_employee__username",
        "requesting_employee__first_name",
        "requesting_employee__last_name",
        "target_employee__username",
        "target_employee__first_name",
        "target_employee__last_name",
        "reason",
        "response_notes",
    ]
    ordering = ["-created"]
    readonly_fields = ["approved_datetime"]

    fieldsets = (
        (
            _("Swap Details"),
            {
                "fields": (
                    "requesting_employee",
                    "target_employee",
                    "requesting_shift",
                    "target_shift",
                ),
            },
        ),
        (_("Request Information"), {"fields": ("reason", "status", "response_notes")}),
        (
            _("Approval"),
            {"fields": ("approved_by", "approved_datetime"), "classes": ("collapse",)},
        ),
    )

    def swap_summary(self, obj):
        return f"{obj.requesting_employee.username} ↔ {obj.target_employee.username}"

    swap_summary.short_description = _("Swap")  # type: ignore


@admin.register(FairnessScore)
class FairnessScoreAdmin(admin.ModelAdmin):
    list_display = [
        "employee",
        "period_summary",
        "incidents_days",
        "waakdienst_days",
        "overall_fairness_score",
    ]
    list_filter = ["period_start", "period_end", "created"]
    search_fields = [
        "employee__username",
        "employee__first_name",
        "employee__last_name",
    ]
    ordering = ["-period_end", "employee__username"]
    readonly_fields = [
        "incidents_fairness_score",
        "waakdienst_fairness_score",
        "overall_fairness_score",
    ]

    fieldsets = (
        (
            _("Period & Employee"),
            {"fields": ("employee", "period_start", "period_end")},
        ),
        (
            _("Shift Days"),
            {
                "fields": (
                    "incidents_days",
                    "waakdienst_days",
                    "changes_days",
                    "projects_days",
                ),
            },
        ),
        (
            _("Fairness Scores"),
            {
                "fields": (
                    "incidents_fairness_score",
                    "waakdienst_fairness_score",
                    "overall_fairness_score",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    def period_summary(self, obj):
        return f"{obj.period_start} to {obj.period_end}"

    period_summary.short_description = _("Period")  # type: ignore


class TimeEntryInline(admin.TabularInline):
    model = TimeEntry
    extra = 0
    fields = ["employee", "clock_in", "clock_out", "break_duration_minutes", "notes"]
    readonly_fields = ["created", "modified"]


@admin.register(TimeEntry)
class TimeEntryAdmin(admin.ModelAdmin):
    list_display = [
        "employee",
        "shift",
        "clock_in",
        "clock_out",
        "total_hours",
        "created",
    ]
    list_filter = ["clock_in", "clock_out", "created"]
    search_fields = [
        "employee__username",
        "employee__first_name",
        "employee__last_name",
        "shift__template__name",
    ]
    ordering = ["-clock_in"]

    fieldsets = (
        (_("Time Entry"), {"fields": ("shift", "employee", "clock_in", "clock_out")}),
        (_("Breaks & Notes"), {"fields": ("break_duration_minutes", "notes")}),
    )

    def total_hours(self, obj):
        if obj.clock_out and obj.clock_in:
            duration = obj.clock_out - obj.clock_in
            hours = duration.total_seconds() / 3600 - (obj.break_duration_minutes / 60)
            return f"{hours:.2f}h"
        return "In Progress"

    total_hours.short_description = _("Total Hours")  # type: ignore


@admin.register(OvertimeEntry)
class OvertimeEntryAdmin(admin.ModelAdmin):
    list_display = [
        "employee",
        "date",
        "hours",
        "reason_summary",
        "approved_by",
        "created",
    ]
    list_filter = ["date", "approved_by", "created"]
    search_fields = [
        "employee__username",
        "employee__first_name",
        "employee__last_name",
        "reason",
    ]
    ordering = ["-date"]

    fieldsets = (
        (_("Overtime Details"), {"fields": ("employee", "shift", "date", "hours")}),
        (_("Approval"), {"fields": ("reason", "approved_by")}),
    )

    def reason_summary(self, obj):
        return obj.reason[:50] + "..." if len(obj.reason) > 50 else obj.reason

    reason_summary.short_description = _("Reason")  # type: ignore


@admin.register(SchedulingRule)
class SchedulingRuleAdmin(admin.ModelAdmin):
    list_display = ["name", "shift_type", "priority", "is_active", "created"]
    list_filter = ["shift_type", "is_active", "priority", "created"]
    search_fields = ["name", "description"]
    ordering = ["-priority", "shift_type", "name"]

    fieldsets = (
        (_("Rule Information"), {"fields": ("name", "shift_type", "description")}),
        (_("Configuration"), {"fields": ("priority", "is_active", "configuration")}),
    )
