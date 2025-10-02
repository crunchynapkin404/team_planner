from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.utils import timezone


class NotificationType(models.TextChoices):
    """Types of notifications that can be sent."""
    SHIFT_ASSIGNED = 'shift_assigned', _('Shift Assigned')
    SHIFT_UPDATED = 'shift_updated', _('Shift Updated')
    SHIFT_CANCELLED = 'shift_cancelled', _('Shift Cancelled')
    SWAP_REQUESTED = 'swap_requested', _('Swap Requested')
    SWAP_APPROVED = 'swap_approved', _('Swap Approved')
    SWAP_REJECTED = 'swap_rejected', _('Swap Rejected')
    LEAVE_SUBMITTED = 'leave_submitted', _('Leave Request Submitted')
    LEAVE_APPROVED = 'leave_approved', _('Leave Request Approved')
    LEAVE_REJECTED = 'leave_rejected', _('Leave Request Rejected')
    SCHEDULE_PUBLISHED = 'schedule_published', _('Schedule Published')
    REMINDER = 'reminder', _('Reminder')
    SYSTEM = 'system', _('System Notification')


class NotificationPreference(models.Model):
    """User preferences for notification delivery methods."""
    
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notification_preferences',
        verbose_name=_('User')
    )
    
    # Email notification preferences
    email_shift_assigned = models.BooleanField(_('Email: Shift Assigned'), default=True)
    email_shift_updated = models.BooleanField(_('Email: Shift Updated'), default=True)
    email_shift_cancelled = models.BooleanField(_('Email: Shift Cancelled'), default=True)
    email_swap_requested = models.BooleanField(_('Email: Swap Requested'), default=True)
    email_swap_approved = models.BooleanField(_('Email: Swap Approved'), default=True)
    email_swap_rejected = models.BooleanField(_('Email: Swap Rejected'), default=True)
    email_leave_approved = models.BooleanField(_('Email: Leave Approved'), default=True)
    email_leave_rejected = models.BooleanField(_('Email: Leave Rejected'), default=True)
    email_schedule_published = models.BooleanField(_('Email: Schedule Published'), default=True)
    email_reminders = models.BooleanField(_('Email: Reminders'), default=True)
    
    # In-app notification preferences
    inapp_shift_assigned = models.BooleanField(_('In-App: Shift Assigned'), default=True)
    inapp_shift_updated = models.BooleanField(_('In-App: Shift Updated'), default=True)
    inapp_shift_cancelled = models.BooleanField(_('In-App: Shift Cancelled'), default=True)
    inapp_swap_requested = models.BooleanField(_('In-App: Swap Requested'), default=True)
    inapp_swap_approved = models.BooleanField(_('In-App: Swap Approved'), default=True)
    inapp_swap_rejected = models.BooleanField(_('In-App: Swap Rejected'), default=True)
    inapp_leave_approved = models.BooleanField(_('In-App: Leave Approved'), default=True)
    inapp_leave_rejected = models.BooleanField(_('In-App: Leave Rejected'), default=True)
    inapp_schedule_published = models.BooleanField(_('In-App: Schedule Published'), default=True)
    inapp_reminders = models.BooleanField(_('In-App: Reminders'), default=True)
    
    # Timing preferences
    quiet_hours_start = models.TimeField(_('Quiet Hours Start'), null=True, blank=True, help_text=_('No notifications during quiet hours'))
    quiet_hours_end = models.TimeField(_('Quiet Hours End'), null=True, blank=True)
    
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('Notification Preference')
        verbose_name_plural = _('Notification Preferences')
    
    def __str__(self):
        return f"{self.user.username}'s Notification Preferences"
    
    def should_send_email(self, notification_type: str) -> bool:
        """Check if user wants email for this notification type."""
        field_name = f'email_{notification_type}'
        return getattr(self, field_name, False)
    
    def should_send_inapp(self, notification_type: str) -> bool:
        """Check if user wants in-app notification for this type."""
        field_name = f'inapp_{notification_type}'
        return getattr(self, field_name, True)
    
    def is_in_quiet_hours(self) -> bool:
        """Check if current time is in user's quiet hours."""
        if not self.quiet_hours_start or not self.quiet_hours_end:
            return False
        
        current_time = timezone.localtime().time()
        
        if self.quiet_hours_start < self.quiet_hours_end:
            # Normal case: e.g., 22:00 to 08:00
            return self.quiet_hours_start <= current_time <= self.quiet_hours_end
        else:
            # Crosses midnight: e.g., 22:00 to 08:00 next day
            return current_time >= self.quiet_hours_start or current_time <= self.quiet_hours_end


class Notification(models.Model):
    """In-app notification model."""
    
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name=_('Recipient')
    )
    
    notification_type = models.CharField(
        _('Type'),
        max_length=30,
        choices=NotificationType.choices
    )
    
    title = models.CharField(_('Title'), max_length=255)
    message = models.TextField(_('Message'))
    
    # Related objects (generic relation could be used, but explicit is clearer)
    related_shift_id = models.IntegerField(_('Related Shift ID'), null=True, blank=True)
    related_leave_id = models.IntegerField(_('Related Leave ID'), null=True, blank=True)
    related_swap_id = models.IntegerField(_('Related Swap ID'), null=True, blank=True)
    
    # Metadata
    data = models.JSONField(_('Additional Data'), default=dict, blank=True)
    
    # Status
    is_read = models.BooleanField(_('Is Read'), default=False)
    read_at = models.DateTimeField(_('Read At'), null=True, blank=True)
    
    # URL for action
    action_url = models.CharField(_('Action URL'), max_length=500, blank=True)
    
    created = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        verbose_name = _('Notification')
        verbose_name_plural = _('Notifications')
        ordering = ['-created']
        indexes = [
            models.Index(fields=['recipient', '-created']),
            models.Index(fields=['recipient', 'is_read']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.recipient.username}"
    
    def mark_as_read(self):
        """Mark notification as read."""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])
    
    def mark_as_unread(self):
        """Mark notification as unread."""
        if self.is_read:
            self.is_read = False
            self.read_at = None
            self.save(update_fields=['is_read', 'read_at'])


class EmailLog(models.Model):
    """Log of sent emails for debugging and auditing."""
    
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='email_logs',
        verbose_name=_('Recipient')
    )
    
    recipient_email = models.EmailField(_('Recipient Email'))
    subject = models.CharField(_('Subject'), max_length=255)
    notification_type = models.CharField(
        _('Notification Type'),
        max_length=30,
        choices=NotificationType.choices,
        null=True,
        blank=True
    )
    
    sent_at = models.DateTimeField(_('Sent At'), auto_now_add=True, db_index=True)
    success = models.BooleanField(_('Success'), default=True)
    error_message = models.TextField(_('Error Message'), blank=True)
    
    class Meta:
        verbose_name = _('Email Log')
        verbose_name_plural = _('Email Logs')
        ordering = ['-sent_at']
    
    def __str__(self):
        status = "✓" if self.success else "✗"
        return f"{status} {self.subject} → {self.recipient_email}"
