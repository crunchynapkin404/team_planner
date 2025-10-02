"""
Advanced swap approval service.

This module provides business logic for:
- Evaluating approval rules
- Creating approval chains
- Processing approvals/rejections
- Handling delegations
- Auto-approval logic
- Audit trail creation
"""

from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q, Count
from django.utils import timezone

from .models import (
    SwapRequest,
    Shift,
    SwapApprovalRule,
    SwapApprovalChain,
    ApprovalDelegation,
    SwapApprovalAudit,
)

User = get_user_model()


class ApprovalRuleEvaluator:
    """Evaluates approval rules and determines if auto-approval is possible."""
    
    @staticmethod
    def find_applicable_rule(swap_request: SwapRequest) -> Optional[SwapApprovalRule]:
        """
        Find the highest priority applicable rule for a swap request.
        
        Args:
            swap_request: The swap request to evaluate
            
        Returns:
            The applicable rule or None if no rules match
        """
        # Get requesting and target shifts
        requesting_shift = swap_request.requesting_shift
        target_shift = swap_request.target_shift
        
        # Start with active rules ordered by priority
        rules = SwapApprovalRule.objects.filter(is_active=True).order_by('-priority', 'name')
        
        # Filter by shift type
        for rule in rules:
            # Check shift types
            if rule.applies_to_shift_types:
                shift_types = rule.applies_to_shift_types
                req_type = requesting_shift.template.shift_type
                if req_type not in shift_types:
                    continue
                if target_shift:
                    tgt_type = target_shift.template.shift_type
                    if tgt_type not in shift_types:
                        continue
            
            # If we made it here, rule is applicable
            return rule
        
        return None
    
    @staticmethod
    def evaluate_auto_approval(
        swap_request: SwapRequest,
        rule: SwapApprovalRule
    ) -> Tuple[bool, str]:
        """
        Evaluate if a swap request can be auto-approved.
        
        Args:
            swap_request: The swap request to evaluate
            rule: The approval rule to apply
            
        Returns:
            Tuple of (can_auto_approve, reason)
        """
        if not rule.auto_approve_enabled:
            return False, "Auto-approval not enabled for this rule"
        
        reasons = []
        
        # Check same shift type requirement
        if rule.auto_approve_same_shift_type:
            req_type = swap_request.requesting_shift.template.shift_type
            if swap_request.target_shift:
                tgt_type = swap_request.target_shift.template.shift_type
                if req_type != tgt_type:
                    reasons.append("Shift types do not match")
        
        # Check advance notice requirement
        if rule.auto_approve_max_advance_hours is not None:
            req_shift_start = swap_request.requesting_shift.start_datetime
            hours_until_shift = (req_shift_start - timezone.now()).total_seconds() / 3600
            if hours_until_shift < rule.auto_approve_max_advance_hours:
                reasons.append(f"Insufficient advance notice ({hours_until_shift:.1f} hours)")
        
        # Check seniority requirement
        if rule.auto_approve_min_seniority_months is not None:
            req_employee = swap_request.requesting_employee
            tgt_employee = swap_request.target_employee
            
            # Calculate seniority (simplified - uses date_joined)
            req_seniority_months = (timezone.now().date() - req_employee.date_joined.date()).days / 30
            tgt_seniority_months = (timezone.now().date() - tgt_employee.date_joined.date()).days / 30
            
            min_required = rule.auto_approve_min_seniority_months
            if req_seniority_months < min_required or tgt_seniority_months < min_required:
                reasons.append(f"Insufficient seniority (minimum {min_required} months required)")
        
        # Check skills match requirement
        if rule.auto_approve_skills_match_required:
            req_skills = set(swap_request.requesting_shift.template.skills_required.all())
            if swap_request.target_shift:
                tgt_skills = set(swap_request.target_shift.template.skills_required.all())
                # Check if employees have compatible skills
                # This is a simplified check - would need more complex logic in production
                pass
        
        # Check monthly swap limit
        if rule.max_swaps_per_month_per_employee is not None:
            # Count swaps for this month
            current_month_start = date.today().replace(day=1)
            req_employee_swaps = SwapRequest.objects.filter(
                requesting_employee=swap_request.requesting_employee,
                status=SwapRequest.Status.APPROVED,
                created__gte=current_month_start,
            ).count()
            
            if req_employee_swaps >= rule.max_swaps_per_month_per_employee:
                reasons.append(f"Monthly swap limit reached ({rule.max_swaps_per_month_per_employee})")
        
        # If any reasons exist, cannot auto-approve
        if reasons:
            return False, "; ".join(reasons)
        
        return True, "All auto-approval criteria met"
    
    @staticmethod
    def create_approval_chain(
        swap_request: SwapRequest,
        rule: SwapApprovalRule
    ) -> List[SwapApprovalChain]:
        """
        Create the approval chain for a swap request based on the rule.
        
        Args:
            swap_request: The swap request
            rule: The approval rule to apply
            
        Returns:
            List of created approval chain steps
        """
        chain_steps = []
        
        # Determine approvers based on rule
        approvers = []
        
        if rule.requires_manager_approval:
            # Find the manager (simplified - would need proper org structure)
            # For now, find users with can_manage_team permission
            managers = User.objects.filter(
                Q(user_permissions__codename='can_manage_team') |
                Q(groups__permissions__codename='can_manage_team')
            ).distinct()
            
            if managers.exists():
                approvers.append(managers.first())
        
        if rule.requires_admin_approval:
            # Find admins
            admins = User.objects.filter(is_superuser=True)
            if admins.exists():
                approvers.append(admins.first())
        
        # If no specific approvers found, add at least one level
        if not approvers:
            # Default to superusers
            approvers = list(User.objects.filter(is_superuser=True)[:1])
        
        # Create approval chain steps
        for level, approver in enumerate(approvers, start=1):
            if level > rule.approval_levels_required:
                break
            
            # Check for active delegations
            active_delegation = ApprovalDelegation.objects.filter(
                delegator=approver,
                is_active=True,
                start_date__lte=date.today(),
            ).filter(
                Q(end_date__isnull=True) | Q(end_date__gte=date.today())
            ).first()
            
            actual_approver = active_delegation.delegate if active_delegation else approver
            
            chain_step = SwapApprovalChain.objects.create(
                swap_request=swap_request,
                approval_rule=rule,
                level=level,
                approver=actual_approver,
                status=SwapApprovalChain.Status.PENDING,
            )
            chain_steps.append(chain_step)
        
        return chain_steps


class SwapApprovalService:
    """Main service for handling swap approvals."""
    
    @staticmethod
    @transaction.atomic
    def process_new_swap_request(swap_request: SwapRequest) -> Dict:
        """
        Process a new swap request and determine approval workflow.
        
        Args:
            swap_request: The newly created swap request
            
        Returns:
            Dict with processing results
        """
        # Find applicable rule
        rule = ApprovalRuleEvaluator.find_applicable_rule(swap_request)
        
        if not rule:
            # No rule found - use default approval process
            result = {
                "auto_approved": False,
                "requires_approval": True,
                "approval_levels": 1,
                "message": "No specific rule found - using default approval process",
            }
            
            # Create audit entry
            SwapApprovalAudit.objects.create(
                swap_request=swap_request,
                action=SwapApprovalAudit.Action.CREATED,
                actor=swap_request.requesting_employee,
                notes="Swap request created - no specific approval rule found",
            )
            
            return result
        
        # Create audit entry for rule application
        SwapApprovalAudit.objects.create(
            swap_request=swap_request,
            action=SwapApprovalAudit.Action.RULE_APPLIED,
            actor=swap_request.requesting_employee,
            approval_rule=rule,
            notes=f"Applied approval rule: {rule.name}",
        )
        
        # Check for auto-approval
        can_auto_approve, reason = ApprovalRuleEvaluator.evaluate_auto_approval(
            swap_request, rule
        )
        
        if can_auto_approve:
            # Auto-approve the swap
            swap_request.status = SwapRequest.Status.APPROVED
            swap_request.approved_by = None  # System approval
            swap_request.approved_datetime = timezone.now()
            swap_request.response_notes = f"Auto-approved: {reason}"
            swap_request.save()
            
            # Create audit entry
            SwapApprovalAudit.objects.create(
                swap_request=swap_request,
                action=SwapApprovalAudit.Action.AUTO_APPROVED,
                actor=None,  # System
                approval_rule=rule,
                notes=reason,
            )
            
            # Execute the swap
            swap_request._execute_swap()
            
            # Send notifications if configured
            if rule.notify_on_auto_approval:
                # Would send notifications here
                pass
            
            return {
                "auto_approved": True,
                "requires_approval": False,
                "rule": rule.name,
                "reason": reason,
                "message": "Swap request auto-approved",
            }
        
        # Create approval chain
        chain_steps = ApprovalRuleEvaluator.create_approval_chain(swap_request, rule)
        
        return {
            "auto_approved": False,
            "requires_approval": True,
            "approval_levels": len(chain_steps),
            "rule": rule.name,
            "reason": reason,
            "approvers": [step.approver.username for step in chain_steps],
            "message": f"Requires {len(chain_steps)}-level approval",
        }
    
    @staticmethod
    @transaction.atomic
    def process_approval_decision(
        chain_step: SwapApprovalChain,
        approver: User,
        decision: str,  # 'approve' or 'reject'
        notes: str = "",
    ) -> Dict:
        """
        Process an approval decision for a chain step.
        
        Args:
            chain_step: The approval chain step
            approver: The user making the decision
            decision: 'approve' or 'reject'
            notes: Decision notes
            
        Returns:
            Dict with decision results
        """
        swap_request = chain_step.swap_request
        
        # Verify approver has authority
        if chain_step.approver != approver:
            # Check if approver is a delegate
            delegation = ApprovalDelegation.objects.filter(
                delegator=chain_step.approver,
                delegate=approver,
                is_active=True,
                start_date__lte=date.today(),
            ).filter(
                Q(end_date__isnull=True) | Q(end_date__gte=date.today())
            ).first()
            
            if not delegation:
                raise ValueError("User does not have approval authority for this request")
        
        if decision == 'approve':
            chain_step.approve(notes)
            
            # Create audit entry
            SwapApprovalAudit.objects.create(
                swap_request=swap_request,
                action=SwapApprovalAudit.Action.APPROVED,
                actor=approver,
                approval_chain=chain_step,
                notes=notes,
            )
            
            # Check if all approval levels are complete
            pending_steps = swap_request.approval_chain.filter(
                status=SwapApprovalChain.Status.PENDING
            )
            
            if not pending_steps.exists():
                # All approvals complete - approve the swap
                swap_request.status = SwapRequest.Status.APPROVED
                swap_request.approved_by = approver
                swap_request.approved_datetime = timezone.now()
                swap_request.response_notes = "All approval levels completed"
                swap_request.save()
                
                # Execute the swap
                swap_request._execute_swap()
                
                return {
                    "decision": "approved",
                    "swap_approved": True,
                    "message": "All approvals complete - swap executed",
                }
            
            return {
                "decision": "approved",
                "swap_approved": False,
                "pending_approvals": pending_steps.count(),
                "message": f"Approval level {chain_step.level} complete - {pending_steps.count()} levels remaining",
            }
        
        elif decision == 'reject':
            chain_step.reject(notes)
            
            # Create audit entry
            SwapApprovalAudit.objects.create(
                swap_request=swap_request,
                action=SwapApprovalAudit.Action.REJECTED,
                actor=approver,
                approval_chain=chain_step,
                notes=notes,
            )
            
            # Reject the entire swap request
            swap_request.status = SwapRequest.Status.REJECTED
            swap_request.response_notes = f"Rejected at approval level {chain_step.level}: {notes}"
            swap_request.save()
            
            return {
                "decision": "rejected",
                "swap_approved": False,
                "message": f"Swap request rejected at level {chain_step.level}",
            }
        
        else:
            raise ValueError(f"Invalid decision: {decision}")
    
    @staticmethod
    @transaction.atomic
    def delegate_approval(
        chain_step: SwapApprovalChain,
        delegator: User,
        delegate: User,
        notes: str = "",
    ) -> SwapApprovalChain:
        """
        Delegate an approval to another user.
        
        Args:
            chain_step: The approval chain step to delegate
            delegator: The user delegating
            delegate: The user receiving the delegation
            notes: Delegation notes
            
        Returns:
            The new approval chain step for the delegate
        """
        # Verify delegation is allowed
        if not chain_step.approval_rule or not chain_step.approval_rule.allow_delegation:
            raise ValueError("Delegation not allowed for this approval rule")
        
        # Verify delegator has authority
        if chain_step.approver != delegator:
            raise ValueError("User does not have authority to delegate this approval")
        
        # Create audit entry
        SwapApprovalAudit.objects.create(
            swap_request=chain_step.swap_request,
            action=SwapApprovalAudit.Action.DELEGATED,
            actor=delegator,
            approval_chain=chain_step,
            notes=f"Delegated to {delegate.username}: {notes}",
            metadata={"delegate_id": delegate.id},
        )
        
        # Delegate the approval
        new_step = chain_step.delegate(delegate, notes)
        
        return new_step
    
    @staticmethod
    def get_pending_approvals_for_user(user: User) -> List[SwapApprovalChain]:
        """
        Get all pending approval steps assigned to a user.
        
        Args:
            user: The user to get approvals for
            
        Returns:
            List of pending approval chain steps
        """
        return SwapApprovalChain.objects.filter(
            approver=user,
            status=SwapApprovalChain.Status.PENDING,
        ).select_related(
            'swap_request',
            'swap_request__requesting_employee',
            'swap_request__target_employee',
            'swap_request__requesting_shift',
            'swap_request__target_shift',
            'approval_rule',
        )
    
    @staticmethod
    def get_approval_statistics(start_date: date, end_date: date) -> Dict:
        """
        Get approval statistics for a date range.
        
        Args:
            start_date: Start date for statistics
            end_date: End date for statistics
            
        Returns:
            Dict with approval statistics
        """
        swaps = SwapRequest.objects.filter(
            created__date__gte=start_date,
            created__date__lte=end_date,
        )
        
        total_requests = swaps.count()
        auto_approved = swaps.filter(
            approved_by__isnull=True,
            status=SwapRequest.Status.APPROVED,
        ).count()
        
        manually_approved = swaps.filter(
            approved_by__isnull=False,
            status=SwapRequest.Status.APPROVED,
        ).count()
        
        rejected = swaps.filter(status=SwapRequest.Status.REJECTED).count()
        pending = swaps.filter(status=SwapRequest.Status.PENDING).count()
        
        # Average approval time
        approved_swaps = swaps.filter(status=SwapRequest.Status.APPROVED)
        avg_approval_time = None
        if approved_swaps.exists():
            total_time = sum([
                (s.approved_datetime - s.created).total_seconds()
                for s in approved_swaps if s.approved_datetime
            ])
            avg_approval_time = total_time / approved_swaps.count() / 3600  # in hours
        
        return {
            "total_requests": total_requests,
            "auto_approved": auto_approved,
            "manually_approved": manually_approved,
            "rejected": rejected,
            "pending": pending,
            "auto_approval_rate": (auto_approved / total_requests * 100) if total_requests > 0 else 0,
            "approval_rate": ((auto_approved + manually_approved) / total_requests * 100) if total_requests > 0 else 0,
            "average_approval_time_hours": avg_approval_time,
        }
