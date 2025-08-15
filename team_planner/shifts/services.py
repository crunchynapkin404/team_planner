from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from django.db import transaction
from django.utils import timezone

from .models import Shift, ShiftAuditLog


@dataclass
class ReassignmentResult:
    shift_id: int
    from_employee_id: int
    to_employee_id: int
    notes: str


@transaction.atomic
def reassign_shift_transactional(
    *,
    shift: Shift,
    new_employee,
    actor=None,
    reason: str = "",
    source: str = "manual",
) -> ReassignmentResult:
    """Reassign a shift to a new employee with audit trail and overlap guard.
    Assumes business validation done by caller (availability, permissions).
    """
    from_employee = shift.assigned_employee

    # Guard: prevent overlapping double-booking for target employee
    overlap = Shift.objects.filter(
        assigned_employee=new_employee,
        start_datetime__lt=shift.end_datetime,
        end_datetime__gt=shift.start_datetime,
    ).exclude(pk=shift.pk).exists()
    if overlap:
        raise ValueError("Target employee has conflicting shifts during this period")

    shift.assigned_employee = new_employee
    shift.notes = f"{(shift.notes or '').strip()}\n{reason}".strip()
    shift.save(update_fields=["assigned_employee", "notes", "modified"])

    ShiftAuditLog.objects.create(
        action=ShiftAuditLog.Action.REASSIGNED,
        shift=shift,
        from_employee=from_employee,
        to_employee=new_employee,
        actor=actor,
        reason=reason,
        source=source,
    )

    return ReassignmentResult(
        shift_id=int(shift.pk),
        from_employee_id=int(getattr(from_employee, 'pk')),
        to_employee_id=int(getattr(new_employee, 'pk')),
        notes=reason,
    )


@transaction.atomic
def swap_shifts_transactional(
    *,
    shift_a: Shift,
    shift_b: Shift,
    actor=None,
    reason: str = "",
    source: str = "swap",
):
    """Atomically swap employees between two shifts with audit logs.
    Minimal guard: ensure employees won't overlap with the counterpart shift times.
    """
    emp_a = shift_a.assigned_employee
    emp_b = shift_b.assigned_employee

    # Overlap guards after swap
    if Shift.objects.filter(
        assigned_employee=emp_b,
        start_datetime__lt=shift_a.end_datetime,
        end_datetime__gt=shift_a.start_datetime,
    ).exclude(pk=shift_b.pk).exists():
        raise ValueError("Swap would create overlap for target employee")

    if Shift.objects.filter(
        assigned_employee=emp_a,
        start_datetime__lt=shift_b.end_datetime,
        end_datetime__gt=shift_b.start_datetime,
    ).exclude(pk=shift_a.pk).exists():
        raise ValueError("Swap would create overlap for requesting employee")

    # Perform swap
    shift_a.assigned_employee = emp_b
    shift_b.assigned_employee = emp_a
    swap_note = reason or "Swapped via approved request"
    shift_a.notes = f"{(shift_a.notes or '').strip()}\n{swap_note}".strip()
    shift_b.notes = f"{(shift_b.notes or '').strip()}\n{swap_note}".strip()
    shift_a.save(update_fields=["assigned_employee", "notes", "modified"])
    shift_b.save(update_fields=["assigned_employee", "notes", "modified"])

    ShiftAuditLog.objects.create(
        action=ShiftAuditLog.Action.SWAP_APPROVED,
        shift=shift_a,
        from_employee=emp_a,
        to_employee=emp_b,
        actor=actor,
        reason=reason,
        source=source,
    )
    ShiftAuditLog.objects.create(
        action=ShiftAuditLog.Action.SWAP_APPROVED,
        shift=shift_b,
        from_employee=emp_b,
        to_employee=emp_a,
        actor=actor,
        reason=reason,
        source=source,
    )
