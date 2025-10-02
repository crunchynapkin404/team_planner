"""
Notification Service - Central hub for sending notifications.

This service handles:
- Creating in-app notifications
- Sending emails
- Respecting user preferences
- Logging email sends
"""

from typing import Optional, Dict, Any, List
from django.contrib.auth import get_user_model
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
import logging

from .models import Notification, NotificationPreference, EmailLog, NotificationType
from .mailer import send_email_with_optional_ics, IcsEvent

User = get_user_model()
logger = logging.getLogger(__name__)


class NotificationService:
    """Service for creating and sending notifications."""
    
    @staticmethod
    def get_or_create_preferences(user) -> NotificationPreference:
        """Get or create notification preferences for a user."""
        preferences, created = NotificationPreference.objects.get_or_create(user=user)
        if created:
            logger.info(f"Created default notification preferences for {user.username}")
        return preferences
    
    @staticmethod
    def create_notification(
        recipient,
        notification_type: str,
        title: str,
        message: str,
        related_shift_id: Optional[int] = None,
        related_leave_id: Optional[int] = None,
        related_swap_id: Optional[int] = None,
        action_url: str = "",
        data: Optional[Dict[str, Any]] = None
    ) -> Notification:
        """Create an in-app notification."""
        notification = Notification.objects.create(
            recipient=recipient,
            notification_type=notification_type,
            title=title,
            message=message,
            related_shift_id=related_shift_id,
            related_leave_id=related_leave_id,
            related_swap_id=related_swap_id,
            action_url=action_url,
            data=data or {}
        )
        logger.info(f"Created notification {notification.id} for {recipient.username}")
        return notification
    
    @staticmethod
    def send_email(
        recipient,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
        notification_type: Optional[str] = None,
        ics_event: Optional[IcsEvent] = None
    ) -> bool:
        """Send an email and log the result."""
        try:
            recipient_email = recipient.email if hasattr(recipient, 'email') else str(recipient)
            
            if not recipient_email:
                logger.warning(f"No email address for user {getattr(recipient, 'username', recipient)}")
                return False
            
            # Use existing mailer function
            send_email_with_optional_ics(
                subject=subject,
                body_text=body_text,
                recipients=[recipient_email],
                body_html=body_html,
                ics_event=ics_event
            )
            
            # Log success
            EmailLog.objects.create(
                recipient=recipient if hasattr(recipient, 'id') else None,
                recipient_email=recipient_email,
                subject=subject,
                notification_type=notification_type,
                success=True
            )
            
            logger.info(f"Sent email '{subject}' to {recipient_email}")
            return True
            
        except Exception as e:
            # Log failure
            EmailLog.objects.create(
                recipient=recipient if hasattr(recipient, 'id') else None,
                recipient_email=recipient_email if 'recipient_email' in locals() else 'unknown',
                subject=subject,
                notification_type=notification_type,
                success=False,
                error_message=str(e)
            )
            
            logger.error(f"Failed to send email '{subject}': {str(e)}")
            return False
    
    @classmethod
    def notify(
        cls,
        recipient,
        notification_type: str,
        title: str,
        message: str,
        email_subject: Optional[str] = None,
        email_body_text: Optional[str] = None,
        email_body_html: Optional[str] = None,
        related_shift_id: Optional[int] = None,
        related_leave_id: Optional[int] = None,
        related_swap_id: Optional[int] = None,
        action_url: str = "",
        data: Optional[Dict[str, Any]] = None,
        ics_event: Optional[IcsEvent] = None
    ) -> Dict[str, Any]:
        """
        Send a notification via all enabled channels (in-app, email).
        
        Returns dict with status of each channel.
        """
        result = {
            'inapp': False,
            'email': False
        }
        
        # Get user preferences
        preferences = cls.get_or_create_preferences(recipient)
        
        # Check quiet hours for email
        in_quiet_hours = preferences.is_in_quiet_hours()
        
        # Send in-app notification
        # Extract the notification type key (e.g., 'shift_assigned' from NotificationType.SHIFT_ASSIGNED)
        type_key = notification_type.replace('_', '_').lower() if '_' in notification_type else notification_type
        
        if preferences.should_send_inapp(type_key):
            try:
                cls.create_notification(
                    recipient=recipient,
                    notification_type=notification_type,
                    title=title,
                    message=message,
                    related_shift_id=related_shift_id,
                    related_leave_id=related_leave_id,
                    related_swap_id=related_swap_id,
                    action_url=action_url,
                    data=data
                )
                result['inapp'] = True
            except Exception as e:
                logger.error(f"Failed to create in-app notification: {str(e)}")
        
        # Send email notification
        if not in_quiet_hours and preferences.should_send_email(type_key):
            if email_subject and (email_body_text or email_body_html):
                result['email'] = cls.send_email(
                    recipient=recipient,
                    subject=email_subject,
                    body_text=email_body_text or "",
                    body_html=email_body_html,
                    notification_type=notification_type,
                    ics_event=ics_event
                )
        
        return result
    
    # Convenience methods for specific notification types
    
    @classmethod
    def notify_shift_assigned(cls, employee, shift, assigned_by=None) -> Dict[str, Any]:
        """Notify employee that they've been assigned a shift."""
        shift_info = f"{shift.start_datetime.strftime('%A, %B %d, %Y at %I:%M %p')}"
        if hasattr(shift, 'template') and shift.template:
            shift_info = f"{shift.template.name} on {shift_info}"
        
        title = "New Shift Assigned"
        message = f"You have been assigned a shift: {shift_info}"
        
        email_subject = f"Team Planner: {title}"
        email_body_text = f"Hello {employee.name},\n\n{message}\n\nPlease check your schedule for details."
        
        # Build ICS event for calendar
        from .mailer import build_ics_for_shift
        ics_event = build_ics_for_shift(shift)
        
        return cls.notify(
            recipient=employee,
            notification_type=NotificationType.SHIFT_ASSIGNED,
            title=title,
            message=message,
            email_subject=email_subject,
            email_body_text=email_body_text,
            related_shift_id=shift.id,
            action_url=f"/schedule/shifts/{shift.id}",
            data={'shift_id': shift.id, 'assigned_by': assigned_by.username if assigned_by else 'system'},
            ics_event=ics_event
        )
    
    @classmethod
    def notify_shift_updated(cls, employee, shift, changes: Dict[str, Any]) -> Dict[str, Any]:
        """Notify employee that their shift has been updated."""
        title = "Shift Updated"
        message = f"Your shift on {shift.start_datetime.strftime('%B %d, %Y')} has been updated."
        
        email_subject = f"Team Planner: {title}"
        email_body_text = f"Hello {employee.name},\n\n{message}\n\nChanges: {', '.join(changes.keys())}\n\nPlease check your schedule."
        
        return cls.notify(
            recipient=employee,
            notification_type=NotificationType.SHIFT_UPDATED,
            title=title,
            message=message,
            email_subject=email_subject,
            email_body_text=email_body_text,
            related_shift_id=shift.id,
            action_url=f"/schedule/shifts/{shift.id}",
            data={'shift_id': shift.id, 'changes': changes}
        )
    
    @classmethod
    def notify_leave_approved(cls, employee, leave_request, approved_by) -> Dict[str, Any]:
        """Notify employee that their leave request was approved."""
        title = "Leave Request Approved"
        message = f"Your leave request for {leave_request.start_date.strftime('%B %d')} - {leave_request.end_date.strftime('%B %d, %Y')} has been approved."
        
        email_subject = f"Team Planner: {title}"
        email_body_text = f"Hello {employee.name},\n\n{message}\n\nApproved by: {approved_by.name}\n\nEnjoy your time off!"
        
        # Build ICS event for leave
        from .mailer import build_ics_for_leave
        ics_event = build_ics_for_leave(leave_request)
        
        return cls.notify(
            recipient=employee,
            notification_type=NotificationType.LEAVE_APPROVED,
            title=title,
            message=message,
            email_subject=email_subject,
            email_body_text=email_body_text,
            related_leave_id=leave_request.id,
            action_url=f"/leaves/{leave_request.id}",
            data={'leave_id': leave_request.id, 'approved_by': approved_by.username},
            ics_event=ics_event
        )
    
    @classmethod
    def notify_leave_rejected(cls, employee, leave_request, rejected_by, reason="") -> Dict[str, Any]:
        """Notify employee that their leave request was rejected."""
        title = "Leave Request Rejected"
        message = f"Your leave request for {leave_request.start_date.strftime('%B %d')} - {leave_request.end_date.strftime('%B %d, %Y')} was not approved."
        
        email_subject = f"Team Planner: {title}"
        email_body_text = f"Hello {employee.name},\n\n{message}\n\nRejected by: {rejected_by.name}"
        if reason:
            email_body_text += f"\nReason: {reason}"
        
        return cls.notify(
            recipient=employee,
            notification_type=NotificationType.LEAVE_REJECTED,
            title=title,
            message=message,
            email_subject=email_subject,
            email_body_text=email_body_text,
            related_leave_id=leave_request.id,
            action_url=f"/leaves/{leave_request.id}",
            data={'leave_id': leave_request.id, 'rejected_by': rejected_by.username, 'reason': reason}
        )
    
    @classmethod
    def notify_swap_requested(cls, target_employee, swap_request, requesting_employee) -> Dict[str, Any]:
        """Notify employee that someone wants to swap shifts with them."""
        title = "Shift Swap Request"
        message = f"{requesting_employee.name} wants to swap shifts with you."
        
        email_subject = f"Team Planner: {title}"
        email_body_text = f"Hello {target_employee.name},\n\n{message}\n\nPlease review and respond to this request."
        
        return cls.notify(
            recipient=target_employee,
            notification_type=NotificationType.SWAP_REQUESTED,
            title=title,
            message=message,
            email_subject=email_subject,
            email_body_text=email_body_text,
            related_swap_id=swap_request.id if hasattr(swap_request, 'id') else None,
            action_url=f"/swaps/{swap_request.id}" if hasattr(swap_request, 'id') else "/swaps",
            data={'requesting_user': requesting_employee.username}
        )
    
    @classmethod
    def notify_swap_approved(cls, employee, swap_request, approved_by) -> Dict[str, Any]:
        """Notify employee that their swap request was approved."""
        title = "Shift Swap Approved"
        message = f"Your shift swap request has been approved by {approved_by.name}."
        
        email_subject = f"Team Planner: {title}"
        email_body_text = f"Hello {employee.name},\n\n{message}\n\nYour shifts have been updated."
        
        return cls.notify(
            recipient=employee,
            notification_type=NotificationType.SWAP_APPROVED,
            title=title,
            message=message,
            email_subject=email_subject,
            email_body_text=email_body_text,
            related_swap_id=swap_request.id if hasattr(swap_request, 'id') else None,
            action_url=f"/swaps/{swap_request.id}" if hasattr(swap_request, 'id') else "/swaps",
            data={'approved_by': approved_by.username}
        )
    
    @classmethod
    def notify_swap_rejected(cls, employee, swap_request, rejected_by, reason="") -> Dict[str, Any]:
        """Notify employee that their swap request was rejected."""
        title = "Shift Swap Rejected"
        message = f"Your shift swap request has been rejected by {rejected_by.name}."
        if reason:
            message += f" Reason: {reason}"
        
        email_subject = f"Team Planner: {title}"
        email_body_text = f"Hello {employee.name},\n\n{message}"
        
        return cls.notify(
            recipient=employee,
            notification_type=NotificationType.SWAP_REJECTED,
            title=title,
            message=message,
            email_subject=email_subject,
            email_body_text=email_body_text,
            related_swap_id=swap_request.id if hasattr(swap_request, 'id') else None,
            action_url=f"/swaps/{swap_request.id}" if hasattr(swap_request, 'id') else "/swaps",
            data={'rejected_by': rejected_by.username, 'reason': reason}
        )
    
    @classmethod
    def notify_schedule_published(cls, employees: List, schedule_info: Dict[str, Any]) -> Dict[str, int]:
        """Notify multiple employees that a new schedule has been published."""
        success_count = 0
        
        for employee in employees:
            result = cls.notify(
                recipient=employee,
                notification_type=NotificationType.SCHEDULE_PUBLISHED,
                title="New Schedule Published",
                message=f"The schedule for {schedule_info.get('period', 'the upcoming period')} is now available.",
                email_subject="Team Planner: New Schedule Published",
                email_body_text=f"Hello {employee.name},\n\nA new schedule has been published. Please review your shifts.",
                action_url="/schedule",
                data=schedule_info
            )
            if result['inapp'] or result['email']:
                success_count += 1
        
        return {'total': len(employees), 'success': success_count}
