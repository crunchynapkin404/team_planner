from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from datetime import time
from typing import TYPE_CHECKING

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.utils import timezone

if TYPE_CHECKING:
    from collections.abc import Iterable


@dataclass
class IcsEvent:
    summary: str
    dtstart: datetime
    dtend: datetime
    description: str = ""
    location: str = ""
    uid: str | None = None

    def to_ical(self) -> bytes:
        # Local import to avoid optional dependency issues at import time
        from icalendar import Calendar  # type: ignore[import-not-found]
        from icalendar import Event  # type: ignore[import-not-found]

        cal = Calendar()
        cal.add("prodid", "-//Team Planner//EN")
        cal.add("version", "2.0")
        event = Event()
        event.add(
            "uid",
            self.uid
            or f"team-planner-{uuid.uuid4()}@{getattr(settings, 'SITE_DOMAIN', 'example.com')}",
        )
        event.add("summary", self.summary)
        event.add("dtstart", self.dtstart)
        event.add("dtend", self.dtend)
        if self.description:
            event.add("description", self.description)
        if self.location:
            event.add("location", self.location)
        cal.add_component(event)
        return cal.to_ical()


def send_email_with_optional_ics(
    subject: str,
    body_text: str,
    recipients: Iterable[str],
    *,
    body_html: str | None = None,
    ics_event: IcsEvent | None = None,
    from_email: str | None = None,
) -> None:
    """Send an email, optionally attaching an ICS calendar event for Outlook.

    This uses Django's EmailMultiAlternatives and attaches a text/calendar part
    as .ics so Outlook and other clients recognize the invite.
    """
    from_email = from_email or getattr(settings, "DEFAULT_FROM_EMAIL", None)
    to_list = [e for e in recipients if e]
    if not to_list:
        return
    msg = EmailMultiAlternatives(
        subject=subject, body=body_text, to=to_list, from_email=from_email,
    )
    if body_html:
        msg.attach_alternative(body_html, "text/html")

    if ics_event:
        ical_bytes = ics_event.to_ical()
        msg.attach(filename="invite.ics", content=ical_bytes, mimetype="text/calendar")

    msg.send(fail_silently=True)


# Convenience builders


def build_ics_for_shift(shift) -> IcsEvent:
    """Create an ICS event for a Shift instance."""
    summary = f"{getattr(shift.template, 'name', 'Shift')} ({getattr(shift.template, 'shift_type', '')})"
    desc = f"Assigned to: {getattr(shift.assigned_employee, 'username', 'employee')}\n"
    desc += f"Notes: {getattr(shift, 'notes', '')}".strip()
    return IcsEvent(
        summary=summary,
        dtstart=shift.start_datetime,
        dtend=shift.end_datetime,
        description=desc,
    )


def build_ics_for_leave(leave_request) -> IcsEvent:
    """Create a simple work-hours ICS event for a LeaveRequest (approximate all-day)."""
    tz = timezone.get_current_timezone()
    start_dt = timezone.make_aware(
        datetime.combine(leave_request.start_date, time(8, 0)), tz,
    )
    end_dt = timezone.make_aware(
        datetime.combine(leave_request.end_date, time(17, 0)), tz,
    )
    summary = f"Leave: {getattr(leave_request.leave_type, 'name', 'Leave')}"
    desc = leave_request.reason or "Approved leave"
    return IcsEvent(summary=summary, dtstart=start_dt, dtend=end_dt, description=desc)


def notify_swap_approved(
    requester_email: str | None,
    target_email: str | None,
    shift_summary: str,
    ics_event: IcsEvent | None = None,
):
    subject = "Swap approved"
    body = f"Your swap request has been approved. {shift_summary}"
    if requester_email:
        send_email_with_optional_ics(
            subject, body, recipients=[requester_email], ics_event=ics_event,
        )
    # Notify target as well
    body_target = f"You have been assigned a swap. {shift_summary}"
    if target_email:
        send_email_with_optional_ics(
            subject, body_target, recipients=[target_email], ics_event=ics_event,
        )


def notify_leave_approved(employee_email: str | None, ics_event: IcsEvent | None):
    subject = "Leave approved"
    body = "Your leave request has been approved. An event has been attached."
    if employee_email:
        send_email_with_optional_ics(
            subject, body, recipients=[employee_email], ics_event=ics_event,
        )
