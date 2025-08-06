from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_http_methods, require_POST
from django.views.generic import ListView, DetailView, CreateView, UpdateView

from .models import LeaveRequest, LeaveType
from team_planner.shifts.models import SwapRequest


class LeaveRequestListView(ListView):
    """List view for leave requests."""
    model = LeaveRequest
    template_name = "leaves/leave_request_list.html"
    context_object_name = "leave_requests"
    paginate_by = 20
    
    def get_queryset(self):
        user = self.request.user
        
        if user.is_superuser:
            # Admins see all requests
            return LeaveRequest.objects.select_related(
                "employee", "leave_type", "approved_by"
            ).order_by("-created")
        else:
            # Regular users see their own requests
            return LeaveRequest.objects.filter(
                employee=user
            ).select_related(
                "employee", "leave_type", "approved_by"
            ).order_by("-created")


class LeaveRequestDetailView(DetailView):
    """Detail view for a leave request."""
    model = LeaveRequest
    template_name = "leaves/leave_request_detail.html"
    context_object_name = "leave_request"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        leave_request = self.object
        
        # Add conflicting shifts information
        context["conflicting_shifts"] = leave_request.get_conflicting_shifts()
        context["suggested_employees"] = leave_request.get_suggested_swap_employees()
        context["can_be_approved"] = leave_request.can_be_approved()
        context["blocking_message"] = leave_request.get_blocking_message()
        
        # Add related swap requests
        if context["conflicting_shifts"].exists():
            shift_ids = context["conflicting_shifts"].values_list("pk", flat=True)
            context["related_swap_requests"] = SwapRequest.objects.filter(
                requesting_shift__in=shift_ids
            ).select_related(
                "requesting_employee", "target_employee", "approved_by"
            ).order_by("-created")
        
        return context


@login_required
@require_http_methods(["GET", "POST"])
def create_leave_request(request):
    """Create a new leave request."""
    # Simplified form creation for now - will enhance later
    if request.method == "POST":
        # Basic form processing - we'll add proper form later
        messages.success(request, "Leave request functionality will be enhanced in Phase 4")
        return redirect("leaves:leave_request_list")
    
    return render(request, "leaves/create_leave_request.html", {})


@login_required
@permission_required("leaves.change_leaverequest", raise_exception=True)
@require_POST
def approve_leave_request(request, pk):
    """Approve a leave request."""
    leave_request = get_object_or_404(LeaveRequest, pk=pk)
    
    if leave_request.status != LeaveRequest.Status.PENDING:
        messages.error(request, "Leave request is not in pending status.")
        return redirect("leaves:leave_request_detail", pk=pk)
    
    # Check if leave can be approved (no unresolved shift conflicts)
    if not leave_request.can_be_approved():
        messages.error(
            request,
            "Cannot approve leave request. There are unresolved shift conflicts. "
            "All conflicting shifts must have approved swap requests."
        )
        return redirect("leaves:leave_request_detail", pk=pk)
    
    # Approve the leave
    leave_request.status = LeaveRequest.Status.APPROVED
    leave_request.approved_by = request.user
    leave_request.approved_at = timezone.now()
    leave_request.save()
    
    messages.success(request, "Leave request approved successfully!")
    return redirect("leaves:leave_request_detail", pk=pk)


@login_required
@permission_required("leaves.change_leaverequest", raise_exception=True)
@require_POST
def reject_leave_request(request, pk):
    """Reject a leave request."""
    leave_request = get_object_or_404(LeaveRequest, pk=pk)
    rejection_reason = request.POST.get("rejection_reason", "")
    
    if leave_request.status != LeaveRequest.Status.PENDING:
        messages.error(request, "Leave request is not in pending status.")
        return redirect("leaves:leave_request_detail", pk=pk)
    
    leave_request.status = LeaveRequest.Status.REJECTED
    leave_request.approved_by = request.user
    leave_request.approved_at = timezone.now()
    leave_request.rejection_reason = rejection_reason
    leave_request.save()
    
    messages.success(request, "Leave request rejected.")
    return redirect("leaves:leave_request_detail", pk=pk)


@login_required
@require_POST
def cancel_leave_request(request, pk):
    """Cancel a leave request."""
    leave_request = get_object_or_404(LeaveRequest, pk=pk)
    
    # Check ownership
    if leave_request.employee != request.user:
        messages.error(request, "You can only cancel your own leave requests.")
        return redirect("leaves:leave_request_detail", pk=pk)
    
    if not leave_request.can_be_cancelled:
        messages.error(request, "This leave request cannot be cancelled.")
        return redirect("leaves:leave_request_detail", pk=pk)
    
    leave_request.status = LeaveRequest.Status.CANCELLED
    leave_request.save()
    
    messages.success(request, "Leave request cancelled.")
    return redirect("leaves:leave_request_detail", pk=pk)


@login_required
def check_leave_conflicts_ajax(request):
    """AJAX endpoint to check for shift conflicts when creating leave requests."""
    from django.utils.dateparse import parse_date
    
    start_date = parse_date(request.GET.get("start_date", ""))
    end_date = parse_date(request.GET.get("end_date", ""))
    
    if not start_date or not end_date:
        return JsonResponse({"error": "Invalid dates"}, status=400)
    
    # Create a temporary leave request object for conflict checking
    temp_request = LeaveRequest(
        employee=request.user,
        start_date=start_date,
        end_date=end_date
    )
    
    conflicting_shifts = temp_request.get_conflicting_shifts()
    suggested_employees = temp_request.get_suggested_swap_employees()
    
    conflicts_data = [
        {
            "id": shift.pk,
            "shift_type": shift.template.shift_type,  # Use direct field instead of display method
            "start_date": shift.start_datetime.isoformat(),
            "end_date": shift.end_datetime.isoformat(),
            "can_create_swap": True,
        }
        for shift in conflicting_shifts
    ]
    
    suggestions_data = [
        {
            "id": emp.pk,
            "username": emp.username,
            "full_name": emp.get_full_name() or emp.username,
            "available_incidents": emp.employee_profile.available_for_incidents,
            "available_waakdienst": emp.employee_profile.available_for_waakdienst,
        }
        for emp in suggested_employees[:10]  # Limit to 10 suggestions
    ]
    
    return JsonResponse({
        "conflicts": conflicts_data,
        "suggestions": suggestions_data,
        "has_conflicts": bool(conflicts_data),
        "message": temp_request.get_blocking_message() if conflicts_data else None,
    })


@login_required
def leave_dashboard(request):
    """Dashboard showing leave overview and pending approvals."""
    context = {}
    
    # User's recent leave requests
    context["my_recent_requests"] = LeaveRequest.objects.filter(
        employee=request.user
    ).select_related("leave_type", "approved_by").order_by("-created")[:5]
    
    # If user has approval permissions, show pending requests
    if request.user.has_perm("leaves.change_leaverequest"):
        context["pending_approvals"] = LeaveRequest.objects.filter(
            status=LeaveRequest.Status.PENDING
        ).select_related("employee", "leave_type").order_by("created")
        
        # Separate requests with and without conflicts
        context["pending_with_conflicts"] = [
            req for req in context["pending_approvals"] 
            if req.has_shift_conflicts
        ]
        context["pending_without_conflicts"] = [
            req for req in context["pending_approvals"] 
            if not req.has_shift_conflicts
        ]
    
    return render(request, "leaves/dashboard.html", context)
