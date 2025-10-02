from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import Notification, NotificationPreference, EmailLog


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['title', 'recipient', 'notification_type', 'is_read', 'created', 'read_status']
    list_filter = ['notification_type', 'is_read', 'created']
    search_fields = ['title', 'message', 'recipient__username', 'recipient__email']
    readonly_fields = ['created', 'read_at']
    date_hierarchy = 'created'
    
    fieldsets = (
        (_('Basic Information'), {
            'fields': ('recipient', 'notification_type', 'title', 'message')
        }),
        (_('Related Objects'), {
            'fields': ('related_shift_id', 'related_leave_id', 'related_swap_id'),
            'classes': ('collapse',)
        }),
        (_('Status'), {
            'fields': ('is_read', 'read_at', 'action_url')
        }),
        (_('Additional Data'), {
            'fields': ('data',),
            'classes': ('collapse',)
        }),
        (_('Metadata'), {
            'fields': ('created',),
            'classes': ('collapse',)
        }),
    )
    
    def read_status(self, obj):
        if obj.is_read:
            return format_html('<span style="color: green;">✓ Read</span>')
        return format_html('<span style="color: orange;">● Unread</span>')
    read_status.short_description = _('Status')
    
    actions = ['mark_as_read', 'mark_as_unread']
    
    def mark_as_read(self, request, queryset):
        count = 0
        for notification in queryset:
            if not notification.is_read:
                notification.mark_as_read()
                count += 1
        self.message_user(request, f"{count} notification(s) marked as read.")
    mark_as_read.short_description = _("Mark selected as read")
    
    def mark_as_unread(self, request, queryset):
        count = 0
        for notification in queryset:
            if notification.is_read:
                notification.mark_as_unread()
                count += 1
        self.message_user(request, f"{count} notification(s) marked as unread.")
    mark_as_unread.short_description = _("Mark selected as unread")


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ['user', 'email_enabled', 'inapp_enabled', 'quiet_hours', 'modified']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['created', 'modified']
    
    fieldsets = (
        (_('User'), {
            'fields': ('user',)
        }),
        (_('Email Notifications'), {
            'fields': (
                'email_shift_assigned', 'email_shift_updated', 'email_shift_cancelled',
                'email_swap_requested', 'email_swap_approved', 'email_swap_rejected',
                'email_leave_approved', 'email_leave_rejected',
                'email_schedule_published', 'email_reminders'
            )
        }),
        (_('In-App Notifications'), {
            'fields': (
                'inapp_shift_assigned', 'inapp_shift_updated', 'inapp_shift_cancelled',
                'inapp_swap_requested', 'inapp_swap_approved', 'inapp_swap_rejected',
                'inapp_leave_approved', 'inapp_leave_rejected',
                'inapp_schedule_published', 'inapp_reminders'
            ),
            'classes': ('collapse',)
        }),
        (_('Timing'), {
            'fields': ('quiet_hours_start', 'quiet_hours_end')
        }),
        (_('Metadata'), {
            'fields': ('created', 'modified'),
            'classes': ('collapse',)
        }),
    )
    
    def email_enabled(self, obj):
        count = sum([
            obj.email_shift_assigned, obj.email_shift_updated, obj.email_shift_cancelled,
            obj.email_swap_requested, obj.email_swap_approved, obj.email_swap_rejected,
            obj.email_leave_approved, obj.email_leave_rejected,
            obj.email_schedule_published, obj.email_reminders
        ])
        return format_html(f'<span>{count}/10</span>')
    email_enabled.short_description = _('Email Preferences')
    
    def inapp_enabled(self, obj):
        count = sum([
            obj.inapp_shift_assigned, obj.inapp_shift_updated, obj.inapp_shift_cancelled,
            obj.inapp_swap_requested, obj.inapp_swap_approved, obj.inapp_swap_rejected,
            obj.inapp_leave_approved, obj.inapp_leave_rejected,
            obj.inapp_schedule_published, obj.inapp_reminders
        ])
        return format_html(f'<span>{count}/10</span>')
    inapp_enabled.short_description = _('In-App Preferences')
    
    def quiet_hours(self, obj):
        if obj.quiet_hours_start and obj.quiet_hours_end:
            return f"{obj.quiet_hours_start.strftime('%H:%M')} - {obj.quiet_hours_end.strftime('%H:%M')}"
        return "—"
    quiet_hours.short_description = _('Quiet Hours')


@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = ['subject', 'recipient_email', 'notification_type', 'success_icon', 'sent_at']
    list_filter = ['success', 'notification_type', 'sent_at']
    search_fields = ['subject', 'recipient_email', 'recipient__username', 'error_message']
    readonly_fields = ['sent_at', 'recipient', 'recipient_email', 'subject', 'notification_type', 'success', 'error_message']
    date_hierarchy = 'sent_at'
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def success_icon(self, obj):
        if obj.success:
            return format_html('<span style="color: green; font-size: 16px;">✓</span>')
        return format_html('<span style="color: red; font-size: 16px;">✗</span>')
    success_icon.short_description = _('Status')
