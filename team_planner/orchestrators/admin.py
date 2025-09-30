from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import OrchestrationConstraint
from .models import OrchestrationResult
from .models import OrchestrationRun


class OrchestrationResultInline(admin.TabularInline):
    model = OrchestrationResult
    extra = 0
    readonly_fields = [
        "employee",
        "shift_type",
        "week_start_date",
        "week_end_date",
        "fairness_score_before",
        "fairness_score_after",
        "assignment_reason",
        "is_applied",
        "applied_at",
    ]
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


class OrchestrationConstraintInline(admin.TabularInline):
    model = OrchestrationConstraint
    extra = 0
    readonly_fields = [
        "constraint_type",
        "severity",
        "employee",
        "start_date",
        "end_date",
        "shift_type",
        "description",
        "violations_count",
    ]
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(OrchestrationRun)
class OrchestrationRunAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "status_badge",
        "start_date",
        "end_date",
        "total_shifts_created",
        "initiated_by",
        "started_at",
        "duration_display",
    ]
    list_filter = ["status", "started_at", "initiated_by", "start_date"]
    search_fields = ["name", "description", "initiated_by__username"]
    ordering = ["-started_at"]

    readonly_fields = [
        "status",
        "started_at",
        "completed_at",
        "duration_display",
        "total_shifts_created",
        "incidents_shifts_created",
        "waakdienst_shifts_created",
        "execution_log",
        "error_message",
    ]

    fieldsets = (
        (
            _("Basic Information"),
            {"fields": ("name", "description", "status", "initiated_by")},
        ),
        (_("Planning Period"), {"fields": ("start_date", "end_date")}),
        (
            _("Configuration"),
            {
                "fields": ("max_consecutive_weeks", "fairness_weight"),
                "classes": ("collapse",),
            },
        ),
        (
            _("Execution Details"),
            {
                "fields": (
                    "started_at",
                    "completed_at",
                    "duration_display",
                    "total_shifts_created",
                    "incidents_shifts_created",
                    "waakdienst_shifts_created",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            _("Logs"),
            {"fields": ("execution_log", "error_message"), "classes": ("collapse",)},
        ),
    )

    inlines = [OrchestrationConstraintInline, OrchestrationResultInline]

    def status_badge(self, obj):
        colors = {
            "running": "#ffc107",
            "completed": "#28a745",
            "failed": "#dc3545",
            "cancelled": "#6c757d",
            "preview": "#17a2b8",
        }
        color = colors.get(obj.status, "#6c757d")
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; '
            'border-radius: 4px; font-size: 12px;">{}</span>',
            color,
            obj.get_status_display(),
        )

    status_badge.short_description = _("Status")  # type: ignore

    def duration_display(self, obj):
        duration = obj.duration
        if duration:
            total_seconds = int(duration.total_seconds())
            hours, remainder = divmod(total_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return "-"

    duration_display.short_description = _("Duration")  # type: ignore

    def has_delete_permission(self, request, obj=None):
        # Only allow deletion of failed or cancelled runs
        if obj and obj.status in ["completed", "running"]:
            return False
        return super().has_delete_permission(request, obj)


@admin.register(OrchestrationResult)
class OrchestrationResultAdmin(admin.ModelAdmin):
    list_display = [
        "orchestration_run",
        "employee_name",
        "shift_type_badge",
        "week_start_date",
        "fairness_impact",
        "is_applied",
    ]
    list_filter = [
        "shift_type",
        "is_applied",
        "week_start_date",
        "orchestration_run__status",
    ]
    search_fields = [
        "employee__username",
        "employee__first_name",
        "employee__last_name",
        "orchestration_run__name",
    ]
    ordering = ["-orchestration_run__started_at", "week_start_date"]

    readonly_fields = [
        "orchestration_run",
        "employee",
        "shift_type",
        "week_start_date",
        "week_end_date",
        "fairness_score_before",
        "fairness_score_after",
        "assignment_reason",
        "applied_at",
    ]

    fieldsets = (
        (
            _("Assignment Details"),
            {
                "fields": (
                    "orchestration_run",
                    "employee",
                    "shift_type",
                    "week_start_date",
                    "week_end_date",
                ),
            },
        ),
        (
            _("Fairness Impact"),
            {
                "fields": (
                    "fairness_score_before",
                    "fairness_score_after",
                    "assignment_reason",
                ),
            },
        ),
        (_("Application Status"), {"fields": ("is_applied", "applied_at")}),
    )

    def employee_name(self, obj):
        return obj.employee.get_full_name() or obj.employee.username

    employee_name.short_description = _("Employee")  # type: ignore

    def shift_type_badge(self, obj):
        colors = {"incidents": "#007bff", "waakdienst": "#6f42c1"}
        color = colors.get(obj.shift_type, "#6c757d")
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; '
            'border-radius: 4px; font-size: 12px;">{}</span>',
            color,
            obj.get_shift_type_display(),
        )

    shift_type_badge.short_description = _("Shift Type")  # type: ignore

    def fairness_impact(self, obj):
        impact = obj.fairness_score_after - obj.fairness_score_before
        color = "#28a745" if impact >= 0 else "#dc3545"
        return format_html(
            '<span style="color: {}; font-weight: bold;">+{:.2f}</span>', color, impact,
        )

    fairness_impact.short_description = _("Fairness Impact")  # type: ignore

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        # Only allow deletion if not applied
        if obj and obj.is_applied:
            return False
        return super().has_delete_permission(request, obj)


@admin.register(OrchestrationConstraint)
class OrchestrationConstraintAdmin(admin.ModelAdmin):
    list_display = [
        "orchestration_run",
        "constraint_type_badge",
        "severity_badge",
        "employee_name",
        "date_range",
        "violations_count",
        "is_active",
    ]
    list_filter = [
        "constraint_type",
        "severity",
        "is_active",
        "orchestration_run__status",
    ]
    search_fields = ["employee__username", "description", "orchestration_run__name"]
    ordering = ["-orchestration_run__started_at", "severity", "constraint_type"]

    readonly_fields = ["orchestration_run", "violations_count", "violation_details"]

    fieldsets = (
        (
            _("Constraint Details"),
            {
                "fields": (
                    "orchestration_run",
                    "constraint_type",
                    "severity",
                    "description",
                ),
            },
        ),
        (_("Scope"), {"fields": ("employee", "start_date", "end_date", "shift_type")}),
        (
            _("Status"),
            {"fields": ("is_active", "violations_count", "violation_details")},
        ),
    )

    def employee_name(self, obj):
        if obj.employee:
            return obj.employee.get_full_name() or obj.employee.username
        return _("All Employees")

    employee_name.short_description = _("Employee")  # type: ignore

    def constraint_type_badge(self, obj):
        colors = {
            "availability": "#17a2b8",
            "leave_conflict": "#fd7e14",
            "max_consecutive": "#6610f2",
            "skill_requirement": "#20c997",
            "fairness_threshold": "#ffc107",
            "custom": "#6c757d",
        }
        color = colors.get(obj.constraint_type, "#6c757d")
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; '
            'border-radius: 4px; font-size: 12px;">{}</span>',
            color,
            obj.get_constraint_type_display(),
        )

    constraint_type_badge.short_description = _("Type")  # type: ignore

    def severity_badge(self, obj):
        colors = {"hard": "#dc3545", "soft": "#ffc107", "advisory": "#28a745"}
        color = colors.get(obj.severity, "#6c757d")
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; '
            'border-radius: 4px; font-size: 12px;">{}</span>',
            color,
            obj.get_severity_display(),
        )

    severity_badge.short_description = _("Severity")  # type: ignore

    def date_range(self, obj):
        if obj.start_date and obj.end_date:
            return f"{obj.start_date} to {obj.end_date}"
        if obj.start_date:
            return f"From {obj.start_date}"
        if obj.end_date:
            return f"Until {obj.end_date}"
        return "-"

    date_range.short_description = _("Date Range")  # type: ignore

    def has_add_permission(self, request):
        return False
