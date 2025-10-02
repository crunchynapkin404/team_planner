from django.conf import settings
from django.urls import path
from rest_framework.routers import DefaultRouter
from rest_framework.routers import SimpleRouter

from team_planner.employees.api.views import RecurringLeavePatternViewSet
from team_planner.leaves.api import LeaveRequestViewSet, LeaveTypeViewSet

# Import V2 orchestrator API endpoints
from team_planner.orchestrators import api_v2
from team_planner.teams.api_views import DepartmentViewSet
from team_planner.teams.api_views import TeamViewSet
from team_planner.users.api.views import UserViewSet
from team_planner.users.api import mfa_views
from team_planner.users.api import auth_views
from team_planner.users.api import rbac_views
from team_planner.users.api import registration_views
from team_planner.notifications.api_views import NotificationViewSet, NotificationPreferenceViewSet
from team_planner.reports import api as reports_api
from team_planner.shifts import api as shifts_api
from team_planner.leaves import api as leaves_api

router = DefaultRouter() if settings.DEBUG else SimpleRouter()

router.register("users", UserViewSet)
router.register("teams", TeamViewSet)
router.register("departments", DepartmentViewSet)
router.register("leaves/requests", LeaveRequestViewSet, basename="leaverequest")
router.register("leaves/leave-types", LeaveTypeViewSet, basename="leavetype")
router.register(
    "recurring-leave-patterns",
    RecurringLeavePatternViewSet,
    basename="recurring-leave-patterns",
)
# RBAC - Role permissions viewset
router.register(
    "roles/permissions",
    rbac_views.RolePermissionViewSet,
    basename="role-permissions",
)
# Notifications
router.register("notifications", NotificationViewSet, basename="notification")
router.register("notification-preferences", NotificationPreferenceViewSet, basename="notification-preference")

app_name = "api"
urlpatterns = router.urls + [
    # Keep the old teams include for backwards compatibility with any custom endpoints
    # path("teams/", include("team_planner.teams.urls", namespace="teams")),
    # path("departments/", departments_list_api, name="departments_list"),
    # User-specific recurring leave patterns
    path(
        "users/<int:user_pk>/recurring-leave-patterns/",
        RecurringLeavePatternViewSet.as_view({"get": "list", "post": "create"}),
        name="user-recurring-leave-patterns-list",
    ),
    path(
        "users/<int:user_pk>/recurring-leave-patterns/<int:pk>/",
        RecurringLeavePatternViewSet.as_view(
            {
                "get": "retrieve",
                "put": "update",
                "patch": "partial_update",
                "delete": "destroy",
            },
        ),
        name="user-recurring-leave-patterns-detail",
    ),
    # V2 Orchestrator API endpoints
    path(
        "orchestrator/schedule/",
        api_v2.orchestrator_schedule_v2,
        name="orchestrator_schedule_v2",
    ),
    path(
        "orchestrator/coverage/",
        api_v2.orchestrator_coverage_v2,
        name="orchestrator_coverage_v2",
    ),
    path(
        "orchestrator/availability/",
        api_v2.orchestrator_availability_v2,
        name="orchestrator_availability_v2",
    ),
    path(
        "orchestrator-status/health/",
        api_v2.orchestrator_health_v2,
        name="orchestrator_health_v2",
    ),
    path(
        "orchestrator-status/metrics/",
        api_v2.orchestrator_metrics_v2,
        name="orchestrator_metrics_v2",
    ),
    # MFA endpoints
    path("mfa/setup/", mfa_views.setup_mfa, name="mfa-setup"),
    path("mfa/verify/", mfa_views.verify_mfa, name="mfa-verify"),
    path("mfa/disable/", mfa_views.disable_mfa, name="mfa-disable"),
    path("mfa/status/", mfa_views.mfa_status, name="mfa-status"),
    path("mfa/login/verify/", mfa_views.mfa_login_verify, name="mfa-login-verify"),
    path("mfa/backup-codes/regenerate/", mfa_views.regenerate_backup_codes, name="mfa-regenerate-backup-codes"),
    # Auth with MFA check
    path("auth/login/", auth_views.login_with_mfa_check, name="auth-login-mfa"),
    # Registration endpoints
    path("auth/register/", registration_views.register_user, name="register"),
    path("admin/pending-users/", registration_views.pending_users, name="pending-users"),
    path("admin/approve-user/<int:user_id>/", registration_views.approve_user, name="approve-user"),
    path("admin/reject-user/<int:user_id>/", registration_views.reject_user, name="reject-user"),
    # RBAC endpoints
    path("users/me/permissions/", rbac_views.get_my_permissions, name="my-permissions"),
    path("rbac/roles/", rbac_views.get_available_roles, name="available-roles"),
    path("rbac/roles/<str:role>/permissions/", rbac_views.get_role_permissions, name="role-permissions-detail"),
    path("rbac/users/<int:user_id>/role/", rbac_views.update_user_role, name="update-user-role"),
    path("rbac/users/", rbac_views.list_users_with_roles, name="users-with-roles"),
    path("rbac/permissions/check/", rbac_views.check_permission, name="check-permission"),
    # Reports endpoints
    path("reports/schedule/", reports_api.schedule_report, name="report-schedule"),
    path("reports/fairness/", reports_api.fairness_distribution_report, name="report-fairness"),
    path("reports/leave-balance/", reports_api.leave_balance_report, name="report-leave-balance"),
    path("reports/swap-history/", reports_api.swap_history_report, name="report-swap-history"),
    path("reports/employee-hours/", reports_api.employee_hours_report, name="report-employee-hours"),
    path("reports/weekend-holiday/", reports_api.weekend_holiday_distribution_report, name="report-weekend-holiday"),
    # Recurring Shift Pattern endpoints
    path("patterns/", shifts_api.recurring_pattern_list_create, name="patterns-list"),
    path("patterns/<int:pk>/", shifts_api.recurring_pattern_detail, name="patterns-detail"),
    path("patterns/<int:pk>/generate/", shifts_api.generate_pattern_shifts, name="patterns-generate"),
    path("patterns/<int:pk>/preview/", shifts_api.preview_pattern, name="patterns-preview"),
    path("patterns/bulk-generate/", shifts_api.bulk_generate_shifts, name="patterns-bulk-generate"),
    # Shift Template Library endpoints
    path("templates/", shifts_api.template_list_create, name="templates-list"),
    path("templates/<int:pk>/", shifts_api.template_detail, name="templates-detail"),
    path("templates/<int:pk>/clone/", shifts_api.clone_template, name="templates-clone"),
    path("templates/<int:pk>/favorite/", shifts_api.toggle_favorite, name="templates-favorite"),
    # Bulk Shift Operations endpoints
    path("shifts/bulk-create/", shifts_api.bulk_create_shifts, name="shifts-bulk-create"),
    path("shifts/bulk-assign/", shifts_api.bulk_assign_employees, name="shifts-bulk-assign"),
    path("shifts/bulk-modify-times/", shifts_api.bulk_modify_times, name="shifts-bulk-modify-times"),
    path("shifts/bulk-delete/", shifts_api.bulk_delete_shifts, name="shifts-bulk-delete"),
    path("shifts/export-csv/", shifts_api.export_shifts_csv, name="shifts-export-csv"),
    path("shifts/import-csv/", shifts_api.import_shifts_csv, name="shifts-import-csv"),
    # Advanced Approval System endpoints
    path("approval-rules/", shifts_api.approval_rules_api, name="approval-rules-list"),
    path("approval-rules/<int:pk>/", shifts_api.approval_rule_detail_api, name="approval-rules-detail"),
    path("swap-requests/<int:swap_id>/approval-chain/", shifts_api.swap_approval_chain_api, name="swap-approval-chain"),
    path("swap-requests/<int:swap_id>/approve/", shifts_api.approve_swap_step_api, name="swap-approve-step"),
    path("swap-requests/<int:swap_id>/reject/", shifts_api.reject_swap_step_api, name="swap-reject-step"),
    path("swap-requests/<int:swap_id>/delegate/", shifts_api.delegate_swap_approval_api, name="swap-delegate"),
    path("swap-requests/<int:swap_id>/audit-trail/", shifts_api.swap_audit_trail_api, name="swap-audit-trail"),
    path("pending-approvals/", shifts_api.pending_approvals_api, name="pending-approvals"),
    path("approval-delegations/", shifts_api.approval_delegations_api, name="approval-delegations-list"),
    path("approval-delegations/<int:pk>/", shifts_api.approval_delegation_detail_api, name="approval-delegations-detail"),
    # Leave Conflict Resolution endpoints
    path("leaves/check-conflicts/", leaves_api.check_leave_conflicts, name="leaves-check-conflicts"),
    path("leaves/suggest-alternatives/", leaves_api.suggest_alternative_dates, name="leaves-suggest-alternatives"),
    path("leaves/conflicts/", leaves_api.get_conflicting_requests, name="leaves-conflicts-list"),
    path("leaves/resolve-conflict/", leaves_api.resolve_conflict, name="leaves-resolve-conflict"),
    path("leaves/recommend-resolution/", leaves_api.get_resolution_recommendation, name="leaves-recommend-resolution"),
]
