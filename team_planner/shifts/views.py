from datetime import datetime, timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.http import require_http_methods, require_POST
from django.views.generic import ListView, DetailView
from django.utils import timezone
from django.db.models import Q
from django.contrib.auth import get_user_model
from datetime import date
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
import json

from .models import Shift, ShiftTemplate, ShiftType, SwapRequest
from .forms import SwapRequestForm, ShiftSearchForm, BulkSwapApprovalForm
from team_planner.employees.models import EmployeeProfile

User = get_user_model()


class ShiftListView(ListView):
    """List view for shifts with filtering."""
    model = Shift
    template_name = "shifts/shift_list.html"
    context_object_name = "shifts"
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Shift.objects.select_related(
            "template", "assigned_employee"
        ).order_by("-start_datetime")
        
        # Apply filters from search form
        form = ShiftSearchForm(self.request.GET)
        if form.is_valid():
            if form.cleaned_data.get("start_date"):
                queryset = queryset.filter(start_datetime__gte=form.cleaned_data["start_date"])
            if form.cleaned_data.get("end_date"):
                queryset = queryset.filter(end_datetime__lte=form.cleaned_data["end_date"])
            if form.cleaned_data.get("shift_type"):
                queryset = queryset.filter(template__shift_type=form.cleaned_data["shift_type"])
            if form.cleaned_data.get("employee"):
                queryset = queryset.filter(assigned_employee=form.cleaned_data["employee"])
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["search_form"] = ShiftSearchForm(self.request.GET)
        return context


class ShiftDetailView(DetailView):
    """Detail view for a single shift."""
    model = Shift
    template_name = "shifts/shift_detail.html"
    context_object_name = "shift"
    
    def get_queryset(self):
        return Shift.objects.select_related(
            "template", "assigned_employee", "assigned_employee__employee_profile"
        ).prefetch_related("time_entries", "swap_requests_as_source", "swap_requests_as_target")


@login_required
@require_http_methods(["GET", "POST"])
def create_swap_request(request, shift_pk):
    """Create a new swap request for a shift."""
    shift = get_object_or_404(Shift, pk=shift_pk)
    
    # Check if user owns the shift
    if shift.assigned_employee != request.user:
        messages.error(request, "You can only create swap requests for your own shifts.")
        return redirect("shifts:shift_detail", pk=shift.pk)
    
    # Check if shift is in a swappable state
    if shift.status not in ["scheduled", "confirmed"]:
        messages.error(request, "This shift cannot be swapped in its current state.")
        return redirect("shifts:shift_detail", pk=shift.pk)
    
    if request.method == "POST":
        form = SwapRequestForm(
            request.POST,
            requesting_employee=request.user,
            requesting_shift=shift
        )
        if form.is_valid():
            swap_request = form.save(commit=False)
            swap_request.requesting_employee = request.user
            swap_request.requesting_shift = shift
            
            # Validate the swap
            validation_errors = swap_request.validate_swap()
            if validation_errors:
                for error in validation_errors:
                    form.add_error(None, error)
            else:
                swap_request.save()
                messages.success(request, "Swap request created successfully!")
                return redirect("shifts:swap_detail", pk=swap_request.pk)
    else:
        form = SwapRequestForm(requesting_employee=request.user, requesting_shift=shift)
    
    return render(request, "shifts/create_swap_request.html", {
        "form": form,
        "shift": shift,
    })


class SwapRequestListView(ListView):
    """List view for swap requests."""
    model = SwapRequest
    template_name = "shifts/swap_request_list.html"
    context_object_name = "swap_requests"
    paginate_by = 20
    
    def get_queryset(self):
        # Show different swap requests based on user permissions
        user = self.request.user
        
        if user.is_superuser:
            # Admins see all swap requests
            return SwapRequest.objects.select_related(
                "requesting_employee", "target_employee", "requesting_shift",
                "target_shift", "approved_by"
            ).order_by("-created")
        else:
            # Regular users see their own requests (sent and received)
            return SwapRequest.objects.filter(
                Q(requesting_employee=user) | Q(target_employee=user)
            ).select_related(
                "requesting_employee", "target_employee", "requesting_shift",
                "target_shift", "approved_by"
            ).order_by("-created")


class SwapRequestDetailView(DetailView):
    """Detail view for a swap request."""
    model = SwapRequest
    template_name = "shifts/swap_request_detail.html"
    context_object_name = "swap_request"
    
    def get_queryset(self):
        return SwapRequest.objects.select_related(
            "requesting_employee", "target_employee", "requesting_shift__template",
            "target_shift__template", "approved_by"
        )


@login_required
@require_POST
def respond_to_swap_request(request, pk):
    """Respond to a swap request (approve/reject)."""
    swap_request = get_object_or_404(SwapRequest, pk=pk)
    action = request.POST.get("action")
    response_notes = request.POST.get("response_notes", "")
    
    # Check permissions
    if not _can_respond_to_swap(request.user, swap_request):
        return HttpResponseForbidden("You don't have permission to respond to this swap request.")
    
    try:
        if action == "approve":
            swap_request.approve(request.user, response_notes)
            messages.success(request, "Swap request approved successfully!")
        elif action == "reject":
            swap_request.reject(response_notes)
            messages.success(request, "Swap request rejected.")
        else:
            messages.error(request, "Invalid action.")
    except ValueError as e:
        messages.error(request, str(e))
    
    return redirect("shifts:swap_detail", pk=swap_request.pk)


@login_required
@require_POST
def cancel_swap_request(request, pk):
    """Cancel a swap request."""
    swap_request = get_object_or_404(SwapRequest, pk=pk)
    
    # Check if user owns the swap request
    if swap_request.requesting_employee != request.user:
        return HttpResponseForbidden("You can only cancel your own swap requests.")
    
    try:
        swap_request.cancel()
        messages.success(request, "Swap request cancelled.")
    except ValueError as e:
        messages.error(request, str(e))
    
    return redirect("shifts:swap_detail", pk=swap_request.pk)


@login_required
@permission_required("shifts.change_swaprequest", raise_exception=True)
def bulk_swap_approval(request):
    """Bulk approval/rejection of swap requests."""
    if request.method == "POST":
        form = BulkSwapApprovalForm(request.POST, user=request.user)
        if form.is_valid():
            swap_requests = form.cleaned_data["swap_requests"]
            action = form.cleaned_data["action"]
            notes = form.cleaned_data["bulk_response_notes"]
            
            success_count = 0
            error_count = 0
            
            for swap_request in swap_requests:
                try:
                    if action == "approve":
                        swap_request.approve(request.user, notes)
                    elif action == "reject":
                        swap_request.reject(notes)
                    success_count += 1
                except ValueError:
                    error_count += 1
            
            if success_count > 0:
                messages.success(
                    request, 
                    f"Successfully {action}d {success_count} swap request(s)."
                )
            if error_count > 0:
                messages.warning(
                    request,
                    f"{error_count} swap request(s) could not be {action}d."
                )
            
            return redirect("shifts:swap_list")
    else:
        form = BulkSwapApprovalForm(user=request.user)
    
    return render(request, "shifts/bulk_swap_approval.html", {
        "form": form,
    })


@login_required
def get_target_shifts_ajax(request):
    """AJAX endpoint to get shifts for a target employee."""
    employee_id = request.GET.get("employee_id")
    if not employee_id:
        return JsonResponse({"shifts": []})
    
    try:
        employee = User.objects.get(pk=employee_id)
        shifts = Shift.objects.filter(
            assigned_employee=employee,
            status__in=["scheduled", "confirmed"],
            start_datetime__gte=timezone.now()
        ).select_related("template").order_by("start_datetime")
        
        shift_data = [
            {
                "id": shift.pk,
                "display": f"{shift.template.shift_type.title()} - {shift.start_datetime.strftime('%Y-%m-%d %H:%M')}",
                "start_date": shift.start_datetime.isoformat(),
                "end_date": shift.end_datetime.isoformat(),
                "shift_type": shift.template.shift_type,
            }
            for shift in shifts
        ]
        
        return JsonResponse({"shifts": shift_data})
    except User.DoesNotExist:
        return JsonResponse({"shifts": []})


@require_http_methods(["GET"])
def shifts_api(request):
    """API endpoint to get shifts data for the calendar."""
    # Get date range from query parameters
    start_date = request.GET.get('start')
    end_date = request.GET.get('end')
    
    queryset = Shift.objects.select_related(
        'template', 'assigned_employee'
    ).order_by('start_datetime')
    
    # Filter by date range if provided
    if start_date:
        queryset = queryset.filter(start_datetime__gte=start_date)
    if end_date:
        queryset = queryset.filter(end_datetime__lte=end_date)
    
    # Convert to calendar event format
    events = []
    for shift in queryset:
        event = {
            'id': str(shift.pk),
            'title': shift.template.shift_type.title(),
            'start': shift.start_datetime.isoformat(),
            'end': shift.end_datetime.isoformat(),
            'extendedProps': {
                'shiftType': shift.template.shift_type,
                'engineerName': shift.assigned_employee.name if shift.assigned_employee else 'Unassigned',
                'engineerId': str(shift.assigned_employee.pk) if shift.assigned_employee else '',
                'status': 'confirmed',  # Default status
            }
        }
        events.append(event)
    
    return JsonResponse({'events': events})


@require_http_methods(["GET"])
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_api(request):
    """API endpoint to get dashboard data for today's shifts."""
    from django.contrib.auth import get_user_model
    from team_planner.leaves.models import LeaveRequest
    from team_planner.teams.models import TeamMembership
    
    User = get_user_model()
    today = timezone.now().date()
    start_of_day = timezone.make_aware(datetime.combine(today, datetime.min.time()))
    end_of_day = timezone.make_aware(datetime.combine(today, datetime.max.time()))
    
    # Get the requesting user's teams
    user_teams = TeamMembership.objects.filter(
        user=request.user,
        is_active=True
    ).values_list('team_id', flat=True)
    
    # If user is not in any teams, fall back to showing all engineers
    if not user_teams:
        team_member_ids = User.objects.filter(is_active=True).values_list('id', flat=True)
    else:
        # Get all team members from the user's teams
        team_member_ids = TeamMembership.objects.filter(
            team_id__in=user_teams,
            is_active=True
        ).values_list('user_id', flat=True)
    
    # Get today's shifts for team members only
    today_shifts = Shift.objects.filter(
        start_datetime__lte=end_of_day,
        end_datetime__gte=start_of_day,
        status__in=['scheduled', 'confirmed', 'in_progress'],
        assigned_employee_id__in=team_member_ids
    ).select_related('template', 'assigned_employee').order_by('start_datetime')
    
    # Get total active engineers from the user's teams
    total_engineers = User.objects.filter(
        id__in=team_member_ids,
        is_active=True
    ).count()
    
    # Get engineers on leave today from the user's teams
    engineers_on_leave_today = LeaveRequest.objects.filter(
        status='approved',
        start_date__lte=today,
        end_date__gte=today,
        employee_id__in=team_member_ids
    ).values_list('employee_id', flat=True).distinct()
    
    engineers_on_leave_count = len(engineers_on_leave_today)
    
    # Calculate available engineers (total - on leave)
    available_engineers = total_engineers - engineers_on_leave_count
    
    # Initialize result structure
    dashboard_data = {
        'incident_engineer': None,
        'incident_standby_engineer': None,
        'waakdienst_engineer': None,
        'engineers_working': [],
        'engineers_working_count': 0,
        'total_engineers': total_engineers,
        'available_engineers': available_engineers,
        'engineers_on_leave': engineers_on_leave_count
    }
    
    # Process shifts to find today's engineers
    engineers_working = set()
    engineers_working_list = []
    
    for shift in today_shifts:
        engineer_data = {
            'id': shift.assigned_employee.pk,
            'name': shift.assigned_employee.name or shift.assigned_employee.username,
            'username': shift.assigned_employee.username
        }
        
        if shift.template.shift_type == ShiftType.INCIDENTS:
            dashboard_data['incident_engineer'] = engineer_data
        elif shift.template.shift_type == ShiftType.INCIDENTS_STANDBY:
            dashboard_data['incident_standby_engineer'] = engineer_data
        elif shift.template.shift_type == ShiftType.WAAKDIENST:
            dashboard_data['waakdienst_engineer'] = engineer_data
        
        # Add to engineers working set and list
        engineers_working.add(shift.assigned_employee.pk)
        if engineer_data not in engineers_working_list:
            engineers_working_list.append(engineer_data)
    
    dashboard_data['engineers_working'] = engineers_working_list
    dashboard_data['engineers_working_count'] = len(engineers_working)
    
    return JsonResponse(dashboard_data)


def _can_respond_to_swap(user, swap_request):
    """Check if user can respond to a swap request."""
    # Target employee can always respond
    if swap_request.target_employee == user:
        return True
    
    # Superusers can always respond
    if user.is_superuser:
        return True
    
    # Team leads can respond to requests involving their team members
    if hasattr(user, "employee_profile"):
        user_teams = user.employee_profile.teams.all()
        requesting_teams = swap_request.requesting_employee.employee_profile.teams.all()
        target_teams = swap_request.target_employee.employee_profile.teams.all()
        
        if user_teams.intersection(requesting_teams) or user_teams.intersection(target_teams):
            return True
    
    return False
