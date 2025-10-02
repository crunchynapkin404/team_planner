from rest_framework import serializers
from .models import Notification, NotificationPreference


class NotificationSerializer(serializers.ModelSerializer):
    """Serializer for Notification model."""
    
    class Meta:
        model = Notification
        fields = [
            'id', 'notification_type', 'title', 'message',
            'related_shift_id', 'related_leave_id', 'related_swap_id',
            'data', 'is_read', 'read_at', 'action_url', 'created'
        ]
        read_only_fields = ['id', 'created', 'read_at']


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    """Serializer for NotificationPreference model."""
    
    class Meta:
        model = NotificationPreference
        fields = [
            'id', 'user',
            # Email preferences
            'email_shift_assigned', 'email_shift_updated', 'email_shift_cancelled',
            'email_swap_requested', 'email_swap_approved', 'email_swap_rejected',
            'email_leave_approved', 'email_leave_rejected',
            'email_schedule_published', 'email_reminders',
            # In-app preferences
            'inapp_shift_assigned', 'inapp_shift_updated', 'inapp_shift_cancelled',
            'inapp_swap_requested', 'inapp_swap_approved', 'inapp_swap_rejected',
            'inapp_leave_approved', 'inapp_leave_rejected',
            'inapp_schedule_published', 'inapp_reminders',
            # Timing
            'quiet_hours_start', 'quiet_hours_end',
            'created', 'modified'
        ]
        read_only_fields = ['id', 'user', 'created', 'modified']
