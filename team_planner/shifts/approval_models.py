"""
Advanced swap approval rules models.

This module provides models for:
- Configurable approval rules and workflows
- Multi-level approval chains
- Automatic approval criteria
- Approval delegation
- Audit trail
"""

from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from team_planner.contrib.sites.models import TimeStampedModel


class SwapApprovalRule(TimeStampedModel):
    """
    Defines approval rules for shift swaps.
    
    Rules can be based on:
    - Shift characteristics (type, duration, time of day)
    - Employee characteristics (seniority, department, skills)
    - Swap characteristics (advance notice, frequency)
    """
    
    class Priority(models.IntegerChoices):
        LOWEST = 1, _("Lowest")
        LOW = 2, _("Low")
        NORMAL = 3, _("Normal")
        HIGH = 4, _("High")
        HIGHEST = 5, _("Highest")
    
    name = models.CharField(
        _("Rule Name"),
        max_length=200,
        help_text=_("Descriptive name for this rule"),
    )
    description = models.TextField(
        _("Description"),
        blank=True,
        help_text=_("Detailed description of when this rule applies"),
    )
    is_active = models.BooleanField(
        _("Active"),
        default=True,
        help_text=_("Whether this rule is currently active"),
    )
    priority = models.IntegerField(
        _("Priority"),
        choices=Priority.choices,
        default=Priority.NORMAL,
        help_text=_("Rule priority (higher priority rules are evaluated first)"),
    )
    
    # Applicability Conditions
    applies_to_shift_types = models.JSONField(
        _("Shift Types"),
        default=list,
        blank=True,
        help_text=_("List of shift types this rule applies to (empty = all)"),
    )
    applies_to_departments = models.ManyToManyField(
        "teams.Department",
        blank=True,
        verbose_name=_("Departments"),
        help_text=_("Departments this rule applies to (empty = all)"),
    )
    applies_to_teams = models.ManyToManyField(
        "teams.Team",
        blank=True,
        verbose_name=_("Teams"),
        help_text=_("Teams this rule applies to (empty = all)"),
    )
    
    # Automatic Approval Criteria
    auto_approve_enabled = models.BooleanField(
        _("Enable Auto-Approval"),
        default=False,
        help_text=_("Automatically approve swaps that meet criteria"),
    )
    auto_approve_same_shift_type = models.BooleanField(
        _("Same Shift Type Required"),
        default=False,
        help_text=_("Auto-approve only if both shifts are same type"),
    )
    auto_approve_max_advance_hours = models.IntegerField(
        _("Maximum Advance Hours"),
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text=_("Maximum hours in advance for auto-approval (null = no limit)"),
    )
    auto_approve_min_seniority_months = models.IntegerField(
        _("Minimum Seniority (Months)"),
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text=_("Minimum months of seniority required for auto-approval"),
    )
    auto_approve_skills_match_required = models.BooleanField(
        _("Skills Match Required"),
        default=False,
        help_text=_("Auto-approve only if employees have compatible skills"),
    )
    
    # Manual Approval Requirements
    requires_manager_approval = models.BooleanField(
        _("Requires Manager Approval"),
        default=True,
        help_text=_("Requires approval from a manager"),
    )
    requires_admin_approval = models.BooleanField(
        _("Requires Admin Approval"),
        default=False,
        help_text=_("Requires approval from an administrator"),
    )
    approval_levels_required = models.IntegerField(
        _("Approval Levels Required"),
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text=_("Number of approval levels required"),
    )
    
    # Approval Delegation
    allow_delegation = models.BooleanField(
        _("Allow Delegation"),
        default=False,
        help_text=_("Allow approvers to delegate their approval authority"),
    )
    
    # Usage Limits
    max_swaps_per_month_per_employee = models.IntegerField(
        _("Max Swaps Per Month"),
        null=True,
        blank=True,
        validators=[MinValueValidator(1)],
        help_text=_("Maximum swaps allowed per employee per month (null = unlimited)"),
    )
    
    # Notification Settings
    notify_on_auto_approval = models.BooleanField(
        _("Notify on Auto-Approval"),
        default=True,
        help_text=_("Send notifications when swaps are auto-approved"),
    )
    
    class Meta:
        verbose_name = _("Swap Approval Rule")
        verbose_name_plural = _("Swap Approval Rules")
        ordering = ["-priority", "name"]
    
    def __str__(self):
        status = "Active" if self.is_active else "Inactive"
        return f"{self.name} ({status}, Priority: {self.get_priority_display()})"


class SwapApprovalChain(TimeStampedModel):
    """
    Tracks the approval chain for a swap request.
    
    Each swap request can have multiple approval steps,
    tracked in sequence with this model.
    """
    
    class Status(models.TextChoices):
        PENDING = "pending", _("Pending")
        APPROVED = "approved", _("Approved")
        REJECTED = "rejected", _("Rejected")
        SKIPPED = "skipped", _("Skipped")
        DELEGATED = "delegated", _("Delegated")
    
    swap_request = models.ForeignKey(
        "shifts.SwapRequest",
        on_delete=models.CASCADE,
        related_name="approval_chain",
        verbose_name=_("Swap Request"),
    )
    approval_rule = models.ForeignKey(
        SwapApprovalRule,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approval_chains",
        verbose_name=_("Approval Rule"),
    )
    level = models.IntegerField(
        _("Approval Level"),
        validators=[MinValueValidator(1)],
        help_text=_("Sequential approval level (1 = first, 2 = second, etc.)"),
    )
    approver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="swap_approvals_assigned",
        verbose_name=_("Assigned Approver"),
    )
    status = models.CharField(
        _("Status"),
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    decision_datetime = models.DateTimeField(
        _("Decision Date/Time"),
        null=True,
        blank=True,
    )
    decision_notes = models.TextField(
        _("Decision Notes"),
        blank=True,
        help_text=_("Notes or reasoning for the decision"),
    )
    delegated_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="delegated_swap_approvals",
        verbose_name=_("Delegated To"),
        help_text=_("User this approval was delegated to"),
    )
    auto_approved = models.BooleanField(
        _("Auto-Approved"),
        default=False,
        help_text=_("Whether this was automatically approved by rules"),
    )
    
    class Meta:
        verbose_name = _("Swap Approval Chain")
        verbose_name_plural = _("Swap Approval Chains")
        ordering = ["swap_request", "level"]
        unique_together = [["swap_request", "level"]]
    
    def __str__(self):
        return f"L{self.level}: {self.approver.username} - {self.get_status_display()}"
    
    @property
    def is_pending(self):
        return self.status == self.Status.PENDING
    
    @property
    def is_completed(self):
        return self.status in [self.Status.APPROVED, self.Status.REJECTED, self.Status.SKIPPED]
    
    def approve(self, decision_notes=""):
        """Mark this approval step as approved."""
        from django.utils import timezone
        
        self.status = self.Status.APPROVED
        self.decision_datetime = timezone.now()
        self.decision_notes = decision_notes
        self.save()
    
    def reject(self, decision_notes=""):
        """Mark this approval step as rejected."""
        from django.utils import timezone
        
        self.status = self.Status.REJECTED
        self.decision_datetime = timezone.now()
        self.decision_notes = decision_notes
        self.save()
    
    def delegate(self, delegated_to_user, notes=""):
        """Delegate this approval to another user."""
        from django.utils import timezone
        
        self.status = self.Status.DELEGATED
        self.delegated_to = delegated_to_user
        self.decision_datetime = timezone.now()
        self.decision_notes = notes
        self.save()
        
        # Create new approval step for delegated user
        return SwapApprovalChain.objects.create(
            swap_request=self.swap_request,
            approval_rule=self.approval_rule,
            level=self.level,  # Same level
            approver=delegated_to_user,
            status=self.Status.PENDING,
        )


class ApprovalDelegation(TimeStampedModel):
    """
    Tracks delegation of approval authority.
    
    Allows users to delegate their approval authority to others
    for a specified time period or indefinitely.
    """
    
    delegator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="approval_delegations_given",
        verbose_name=_("Delegator"),
        help_text=_("User delegating their approval authority"),
    )
    delegate = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="approval_delegations_received",
        verbose_name=_("Delegate"),
        help_text=_("User receiving the approval authority"),
    )
    start_date = models.DateField(
        _("Start Date"),
        help_text=_("Date when delegation becomes active"),
    )
    end_date = models.DateField(
        _("End Date"),
        null=True,
        blank=True,
        help_text=_("Date when delegation expires (null = indefinite)"),
    )
    is_active = models.BooleanField(
        _("Active"),
        default=True,
        help_text=_("Whether this delegation is currently active"),
    )
    reason = models.TextField(
        _("Reason"),
        blank=True,
        help_text=_("Reason for delegation (e.g., vacation, leave)"),
    )
    
    class Meta:
        verbose_name = _("Approval Delegation")
        verbose_name_plural = _("Approval Delegations")
        ordering = ["-start_date"]
    
    def __str__(self):
        end = self.end_date.isoformat() if self.end_date else "Indefinite"
        return f"{self.delegator.username} → {self.delegate.username} ({self.start_date} to {end})"
    
    @property
    def is_currently_active(self):
        """Check if delegation is active for current date."""
        from django.utils import timezone
        from datetime import date
        
        if not self.is_active:
            return False
        
        today = date.today()
        if today < self.start_date:
            return False
        if self.end_date and today > self.end_date:
            return False
        
        return True


class SwapApprovalAudit(TimeStampedModel):
    """
    Audit trail for swap approval decisions.
    
    Records all actions taken on swap requests for compliance
    and troubleshooting purposes.
    """
    
    class Action(models.TextChoices):
        CREATED = "created", _("Created")
        APPROVED = "approved", _("Approved")
        REJECTED = "rejected", _("Rejected")
        CANCELLED = "cancelled", _("Cancelled")
        DELEGATED = "delegated", _("Delegated")
        AUTO_APPROVED = "auto_approved", _("Auto-Approved")
        RULE_APPLIED = "rule_applied", _("Rule Applied")
        ESCALATED = "escalated", _("Escalated")
    
    swap_request = models.ForeignKey(
        "shifts.SwapRequest",
        on_delete=models.CASCADE,
        related_name="audit_trail",
        verbose_name=_("Swap Request"),
    )
    action = models.CharField(
        _("Action"),
        max_length=20,
        choices=Action.choices,
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="swap_approval_actions",
        verbose_name=_("Actor"),
        help_text=_("User who performed the action"),
    )
    approval_chain = models.ForeignKey(
        SwapApprovalChain,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_entries",
        verbose_name=_("Approval Chain Step"),
    )
    approval_rule = models.ForeignKey(
        SwapApprovalRule,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_entries",
        verbose_name=_("Applied Rule"),
    )
    notes = models.TextField(
        _("Notes"),
        blank=True,
        help_text=_("Additional details about the action"),
    )
    metadata = models.JSONField(
        _("Metadata"),
        default=dict,
        blank=True,
        help_text=_("Additional structured data about the action"),
    )
    
    class Meta:
        verbose_name = _("Swap Approval Audit")
        verbose_name_plural = _("Swap Approval Audits")
        ordering = ["-created"]
    
    def __str__(self):
        actor_name = self.actor.username if self.actor else "System"
        return f"{actor_name}: {self.get_action_display()} - {self.swap_request}"
