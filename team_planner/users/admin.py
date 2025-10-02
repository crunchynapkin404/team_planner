from allauth.account.decorators import secure_admin_login
from django.conf import settings
from django.contrib import admin
from django.contrib.auth import admin as auth_admin
from django.utils.translation import gettext_lazy as _

from .forms import UserAdminChangeForm
from .forms import UserAdminCreationForm
from .models import User, TwoFactorDevice, MFALoginAttempt

if settings.DJANGO_ADMIN_FORCE_ALLAUTH:
    # Force the `admin` sign in process to go through the `django-allauth` workflow:
    # https://docs.allauth.org/en/latest/common/admin.html#admin
    admin.autodiscover()
    admin.site.login = secure_admin_login(admin.site.login)  # type: ignore[method-assign]


@admin.register(User)
class UserAdmin(auth_admin.UserAdmin):
    form = UserAdminChangeForm
    add_form = UserAdminCreationForm
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (_("Personal info"), {"fields": ("name", "email")}),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )
    list_display = ["username", "name", "is_superuser"]
    search_fields = ["name"]


@admin.register(TwoFactorDevice)
class TwoFactorDeviceAdmin(admin.ModelAdmin):
    list_display = ['user', 'is_verified', 'device_name', 'last_used', 'created']
    list_filter = ['is_verified', 'created', 'last_used']
    search_fields = ['user__username', 'user__email', 'user__name']
    readonly_fields = ['secret_key', 'backup_codes', 'created', 'modified']
    
    fieldsets = (
        ('User Information', {
            'fields': ('user',)
        }),
        ('Device Details', {
            'fields': ('device_name', 'is_verified', 'last_used')
        }),
        ('Security', {
            'fields': ('secret_key', 'backup_codes'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created', 'modified'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['reset_mfa']
    
    def reset_mfa(self, request, queryset):
        """Reset MFA for selected users."""
        count = queryset.delete()[0]
        self.message_user(
            request,
            f'Successfully reset MFA for {count} user(s).'
        )
    reset_mfa.short_description = "Reset MFA for selected users"


@admin.register(MFALoginAttempt)
class MFALoginAttemptAdmin(admin.ModelAdmin):
    list_display = ['user', 'success', 'ip_address', 'failure_reason', 'created']
    list_filter = ['success', 'failure_reason', 'created']
    search_fields = ['user__username', 'user__email', 'ip_address']
    readonly_fields = ['user', 'success', 'ip_address', 'user_agent', 'failure_reason', 'created', 'modified']
    
    fieldsets = (
        ('Attempt Information', {
            'fields': ('user', 'success', 'failure_reason')
        }),
        ('Network Details', {
            'fields': ('ip_address', 'user_agent')
        }),
        ('Timestamps', {
            'fields': ('created', 'modified')
        }),
    )
    
    def has_add_permission(self, request):
        """Prevent manual creation of login attempts."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Make login attempts read-only."""
        return False
