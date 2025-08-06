from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.generic import TemplateView
from django.utils import timezone
from django.db import transaction
from datetime import date, datetime, timedelta
import json

from .models import OrchestrationRun, OrchestrationResult
from .algorithms import ShiftOrchestrator, FairnessCalculator
from team_planner.employees.models import EmployeeProfile
from team_planner.shifts.models import Shift, ShiftTemplate


@login_required
@permission_required('orchestrators.view_orchestrationrun', raise_exception=True)
def orchestrator_dashboard(request):
    """Main orchestrator dashboard showing recent runs and quick actions."""
    recent_runs = OrchestrationRun.objects.order_by('-started_at')[:10]
    active_runs = OrchestrationRun.objects.filter(status=OrchestrationRun.Status.RUNNING)
    
    # Statistics
    total_runs = OrchestrationRun.objects.count()
    successful_runs = OrchestrationRun.objects.filter(status=OrchestrationRun.Status.COMPLETED).count()
    success_rate = (successful_runs / total_runs * 100) if total_runs > 0 else 0
    
    context = {
        'recent_runs': recent_runs,
        'active_runs': active_runs,
        'total_runs': total_runs,
        'successful_runs': successful_runs,
        'success_rate': success_rate,
    }
    
    return render(request, 'orchestrators/dashboard.html', context)


@login_required
@permission_required('orchestrators.add_orchestrationrun', raise_exception=True)
def create_orchestration(request):
    """Create a new orchestration run."""
    if request.method == 'POST':
        try:
            # Parse form data
            name = request.POST.get('name')
            description = request.POST.get('description', '')
            start_date = date.fromisoformat(request.POST.get('start_date'))
            end_date = date.fromisoformat(request.POST.get('end_date'))
            preview_only = request.POST.get('preview_only') == 'true'
            
            # Parse shift type selections
            schedule_incidents = request.POST.get('schedule_incidents') == 'on'
            schedule_incidents_standby = request.POST.get('schedule_incidents_standby') == 'on'
            schedule_waakdienst = request.POST.get('schedule_waakdienst') == 'on'
            
            # Validate at least one shift type is selected
            if not any([schedule_incidents, schedule_incidents_standby, schedule_waakdienst]):
                messages.error(request, 'At least one shift type must be selected.')
                return redirect('orchestrators:dashboard')
            
            # Validate date range
            if start_date >= end_date:
                messages.error(request, 'End date must be after start date.')
                return redirect('orchestrators:dashboard')
            
            # Convert to datetime for orchestrator
            start_datetime = datetime.combine(start_date, datetime.min.time())
            end_datetime = datetime.combine(end_date, datetime.max.time())
            
            with transaction.atomic():
                # Create orchestration run
                run = OrchestrationRun.objects.create(
                    name=name,
                    description=description,
                    initiated_by=request.user,
                    start_date=start_date,
                    end_date=end_date,
                    schedule_incidents=schedule_incidents,
                    schedule_incidents_standby=schedule_incidents_standby,
                    schedule_waakdienst=schedule_waakdienst,
                    status=OrchestrationRun.Status.RUNNING
                )
                
                try:
                    # Create and run orchestrator with selected shift types
                    orchestrator = ShiftOrchestrator(
                        start_datetime, 
                        end_datetime,
                        schedule_incidents=schedule_incidents,
                        schedule_incidents_standby=schedule_incidents_standby,
                        schedule_waakdienst=schedule_waakdienst
                    )
                    
                    if preview_only:
                        result = orchestrator.preview_schedule()
                        
                        # Store preview in session
                        request.session['orchestration_preview'] = {
                            'run_id': run.pk,
                            'result': result,
                            'start_date': start_date.isoformat(),
                            'end_date': end_date.isoformat(),
                        }
                        
                        run.status = OrchestrationRun.Status.PREVIEW
                        run.save()
                        
                        shift_summary = []
                        if schedule_incidents:
                            shift_summary.append(f"{result['incidents_shifts']} incidents")
                        if schedule_incidents_standby:
                            shift_summary.append(f"{result['incidents_standby_shifts']} incidents-standby")
                        if schedule_waakdienst:
                            shift_summary.append(f"{result['waakdienst_shifts']} waakdienst")
                        
                        messages.success(request, f"Preview generated: {result['total_shifts']} daily shifts planned ({', '.join(shift_summary)})")
                        return redirect('orchestrators:preview')
                    else:
                        result = orchestrator.apply_schedule()
                        
                        # Update run with results
                        run.status = OrchestrationRun.Status.COMPLETED
                        run.completed_at = timezone.now()
                        run.total_shifts_created = result['total_shifts']
                        run.incidents_shifts_created = result['incidents_shifts']
                        run.incidents_standby_shifts_created = result['incidents_standby_shifts']
                        run.waakdienst_shifts_created = result['waakdienst_shifts']
                        run.save()
                        
                        # Create results records
                        for shift in result.get('created_shifts', []):
                            OrchestrationResult.objects.create(
                                orchestration_run=run,
                                shift=shift,
                                assignment_reason=shift.assignment_reason or 'Fair distribution algorithm'
                            )
                        
                        shift_summary = []
                        if schedule_incidents:
                            shift_summary.append(f"{result['incidents_shifts']} incidents")
                        if schedule_incidents_standby:
                            shift_summary.append(f"{result['incidents_standby_shifts']} incidents-standby")
                        if schedule_waakdienst:
                            shift_summary.append(f"{result['waakdienst_shifts']} waakdienst")
                        
                        messages.success(
                            request, 
                            f"Orchestration completed! Created {result['total_shifts']} daily shifts ({', '.join(shift_summary)})"
                        )
                        
                        return redirect('orchestrators:detail', run_id=run.pk)
                        
                except Exception as e:
                    run.status = OrchestrationRun.Status.FAILED
                    run.error_message = str(e)
                    run.completed_at = timezone.now()
                    run.save()
                    raise
                    
        except Exception as e:
            messages.error(request, f'Orchestration failed: {str(e)}')
            return redirect('orchestrators:dashboard')
    
    # GET request - show form
    # Get available employees for preview
    eligible_incidents = EmployeeProfile.objects.filter(
        status=EmployeeProfile.Status.ACTIVE,
        available_for_incidents=True
    ).count()
    
    eligible_waakdienst = EmployeeProfile.objects.filter(
        status=EmployeeProfile.Status.ACTIVE,
        available_for_waakdienst=True
    ).count()
    
    context = {
        'eligible_incidents': eligible_incidents,
        'eligible_waakdienst': eligible_waakdienst,
    }
    
    return render(request, 'orchestrators/create.html', context)


@login_required
@permission_required('orchestrators.view_orchestrationrun', raise_exception=True)
def orchestration_detail(request, pk):
    """View details of an orchestration run."""
    run = get_object_or_404(OrchestrationRun, pk=pk)
    
    # Get results grouped by week
    results = OrchestrationResult.objects.filter(
        orchestration_run=run
    ).order_by('week_start_date', 'shift_type')
    
    # Group results by week for display
    weeks = {}
    for result in results:
        week_key = result.week_start_date
        if week_key not in weeks:
            weeks[week_key] = {'incidents': None, 'waakdienst': None}
        weeks[week_key][result.shift_type] = result
    
    # Calculate fairness distribution
    fairness_stats = {}
    for result in results:
        emp_id = result.employee.id
        if emp_id not in fairness_stats:
            fairness_stats[emp_id] = {
                'employee': result.employee,
                'incidents_count': 0,
                'waakdienst_count': 0,
                'total_score': 0
            }
        
        if result.shift_type == 'incidents':
            fairness_stats[emp_id]['incidents_count'] += 1
        else:
            fairness_stats[emp_id]['waakdienst_count'] += 1
        
        fairness_stats[emp_id]['total_score'] += float(result.fairness_score_after)
    
    context = {
        'run': run,
        'weeks': sorted(weeks.items()),
        'fairness_stats': fairness_stats.values(),
        'can_apply': (run.status == OrchestrationRun.Status.PREVIEW and 
                     not OrchestrationResult.objects.filter(orchestration_run=run, is_applied=True).exists()),
    }
    
    return render(request, 'orchestrators/detail.html', context)


@login_required
@permission_required('orchestrators.change_orchestrationrun', raise_exception=True)
@require_http_methods(["POST"])
def apply_orchestration(request, pk):
    """Apply a preview orchestration to create actual shifts."""
    run = get_object_or_404(OrchestrationRun, pk=pk)
    
    if run.status != OrchestrationRun.Status.PREVIEW:
        return JsonResponse({'error': 'Can only apply preview orchestrations'}, status=400)
    
    if OrchestrationResult.objects.filter(orchestration_run=run, is_applied=True).exists():
        return JsonResponse({'error': 'Orchestration already applied'}, status=400)
    
    try:
        with transaction.atomic():
            # Get or create shift templates
            incidents_template, _ = ShiftTemplate.objects.get_or_create(
                shift_type='incidents',
                name='Weekly Incidents Shift',
                defaults={
                    'description': 'Monday-Friday incident handling shift',
                    'duration_hours': 40,  # 5 days * 8 hours
                }
            )
            
            waakdienst_template, _ = ShiftTemplate.objects.get_or_create(
                shift_type='waakdienst',
                name='Weekly Waakdienst Shift',
                defaults={
                    'description': 'On-call/standby shift covering evenings, nights and weekends',
                    'duration_hours': 168,  # 7 days * 24 hours
                }
            )
            
            # Create actual shifts from orchestration results
            shifts_created = 0
            for result in OrchestrationResult.objects.filter(orchestration_run=run):
                if result.shift_type == 'incidents':
                    template = incidents_template
                    # Incidents: Monday 8:00 to Friday 17:00
                    start_datetime = timezone.make_aware(
                        timezone.datetime.combine(result.week_start_date, timezone.datetime.min.time().replace(hour=8))
                    )
                    end_datetime = timezone.make_aware(
                        timezone.datetime.combine(result.week_end_date - timedelta(days=2), timezone.datetime.min.time().replace(hour=17))
                    )
                else:
                    template = waakdienst_template
                    # Waakdienst: Wednesday 17:00 to next Wednesday 8:00
                    start_datetime = timezone.make_aware(
                        timezone.datetime.combine(result.week_start_date + timedelta(days=2), timezone.datetime.min.time().replace(hour=17))
                    )
                    end_datetime = timezone.make_aware(
                        timezone.datetime.combine(result.week_start_date + timedelta(days=9), timezone.datetime.min.time().replace(hour=8))
                    )
                
                # Create the shift
                shift = Shift.objects.create(
                    template=template,
                    assigned_employee=result.employee,
                    start_datetime=start_datetime,
                    end_datetime=end_datetime,
                    status=Shift.Status.SCHEDULED,
                    auto_assigned=True,
                    assignment_reason=f'Created by orchestration: {run.name}'
                )
                
                # Mark result as applied
                result.is_applied = True
                result.applied_at = timezone.now()
                result.save()
                
                shifts_created += 1
            
            # Update orchestration run status
            run.status = OrchestrationRun.Status.COMPLETED
            run.completed_at = timezone.now()
            run.total_shifts_created = shifts_created
            run.save()
            
            return JsonResponse({
                'success': True,
                'message': f'Successfully created {shifts_created} shifts',
                'shifts_created': shifts_created
            })
            
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@permission_required('orchestrators.view_orchestrationresult', raise_exception=True)
def fairness_report(request):
    """Generate fairness distribution report across all employees."""
    # Get active employees
    employees = EmployeeProfile.objects.filter(
        status=EmployeeProfile.Status.ACTIVE
    ).select_related('user')
    
    # Calculate fairness statistics
    fairness_data = []
    for profile in employees:
        # Get recent orchestration results
        recent_results = OrchestrationResult.objects.filter(
            employee=profile.user,
            orchestration_run__status=OrchestrationRun.Status.COMPLETED,
            is_applied=True
        ).order_by('-week_start_date')[:12]  # Last 12 assignments
        
        incidents_count = recent_results.filter(shift_type='incidents').count()
        waakdienst_count = recent_results.filter(shift_type='waakdienst').count()
        
        fairness_data.append({
            'employee': profile,
            'incidents_count': incidents_count,
            'waakdienst_count': waakdienst_count,
            'total_assignments': incidents_count + waakdienst_count,
            'available_incidents': profile.available_for_incidents,
            'available_waakdienst': profile.available_for_waakdienst,
        })
    
    # Calculate averages for comparison
    total_employees = len(fairness_data)
    if total_employees > 0:
        avg_incidents = sum(d['incidents_count'] for d in fairness_data) / total_employees
        avg_waakdienst = sum(d['waakdienst_count'] for d in fairness_data) / total_employees
        avg_total = sum(d['total_assignments'] for d in fairness_data) / total_employees
    else:
        avg_incidents = avg_waakdienst = avg_total = 0
    
    context = {
        'fairness_data': fairness_data,
        'avg_incidents': avg_incidents,
        'avg_waakdienst': avg_waakdienst,
        'avg_total': avg_total,
    }
    
    return render(request, 'orchestrators/fairness_report.html', context)


@login_required
def preview_view(request):
    """Display orchestration preview."""
    preview_data = request.session.get('orchestration_preview')
    if not preview_data:
        messages.error(request, "No preview data available")
        return redirect('orchestrators:dashboard')
    
    context = {
        'preview': preview_data['result'],
        'start_date': preview_data['start_date'],
        'end_date': preview_data['end_date'],
    }
    
    return render(request, 'orchestrators/preview.html', context)


@login_required
@require_http_methods(["POST"])
def apply_preview(request):
    """Apply a previewed schedule."""
    preview_data = request.session.get('orchestration_preview')
    if not preview_data:
        return JsonResponse({'error': 'No preview data available'}, status=400)
    
    try:
        start_date = date.fromisoformat(preview_data['start_date'])
        end_date = date.fromisoformat(preview_data['end_date'])
        
        # Convert to datetime
        start_datetime = datetime.combine(start_date, datetime.min.time())
        end_datetime = datetime.combine(end_date, datetime.max.time())
        
        # Create orchestrator and apply
        orchestrator = ShiftOrchestrator(start_datetime, end_datetime)
        result = orchestrator.apply_schedule()
        
        # Get the run from preview
        run_id = preview_data.get('run_id')
        if run_id:
            run = OrchestrationRun.objects.get(pk=run_id)
            run.status = OrchestrationRun.Status.COMPLETED
            run.completed_at = timezone.now()
            run.total_shifts_created = result['total_shifts']
            run.incidents_shifts_created = result['incident_shifts']
            run.waakdienst_shifts_created = result['waakdienst_shifts']
            run.save()
            
            # Create results records
            for shift in result.get('created_shifts', []):
                OrchestrationResult.objects.create(
                    orchestration_run=run,
                    shift=shift,
                    assignment_reason=shift.assignment_reason or 'Fair distribution algorithm'
                )
        
        # Clear preview from session
        del request.session['orchestration_preview']
        
        return JsonResponse({
            'success': True,
            'message': f"Schedule applied! Created {result['total_shifts']} shifts",
            'total_shifts': result['total_shifts'],
            'redirect_url': '/orchestrators/'
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def orchestration_history(request):
    """View orchestration history."""
    runs = OrchestrationRun.objects.select_related('initiated_by').order_by('-started_at')
    
    return render(request, 'orchestrators/history.html', {
        'runs': runs
    })


@login_required
def fairness_dashboard(request):
    """Fairness metrics and visualization."""
    # Calculate fairness for current year
    today = timezone.now().date()
    year_start = datetime.combine(today.replace(month=1, day=1), datetime.min.time())
    year_end = datetime.combine(today.replace(month=12, day=31), datetime.max.time())
    
    calculator = FairnessCalculator(year_start, year_end)
    
    # Get all active employees
    from django.contrib.auth import get_user_model
    User = get_user_model()
    active_employees = User.objects.filter(
        is_active=True,
        employee_profile__status='active'
    ).select_related('employee_profile')
    
    # Calculate assignments and fairness
    assignments = calculator.calculate_current_assignments(list(active_employees))
    fairness_scores = calculator.calculate_fairness_score(assignments)
    
    # Prepare data for charts
    employee_data = []
    for employee in active_employees:
        emp_assignments = assignments.get(employee.pk, {'incidents': 0, 'waakdienst': 0})
        fairness_score = fairness_scores.get(employee.pk, 0)
        
        employee_data.append({
            'name': employee.get_full_name() or employee.username,
            'incidents': emp_assignments['incidents'],
            'waakdienst': emp_assignments['waakdienst'],
            'total': emp_assignments['incidents'] + emp_assignments['waakdienst'],
            'fairness_score': fairness_score
        })
    
    # Sort by fairness score (lowest first - needs attention)
    employee_data.sort(key=lambda x: x['fairness_score'])
    
    context = {
        'employee_data': employee_data,
        'year': today.year,
        'total_employees': len(employee_data),
        'average_fairness': sum(fairness_scores.values()) / len(fairness_scores) if fairness_scores else 0,
    }
    
    return render(request, 'orchestrators/fairness.html', context)


@login_required
def fairness_api(request):
    """API endpoint for fairness data."""
    # Get date range from query params
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    if not start_date or not end_date:
        # Default to current year
        today = timezone.now().date()
        start_date = today.replace(month=1, day=1)
        end_date = today.replace(month=12, day=31)
    else:
        start_date = datetime.fromisoformat(start_date).date()
        end_date = datetime.fromisoformat(end_date).date()
    
    # Convert to datetime
    start_datetime = datetime.combine(start_date, datetime.min.time())
    end_datetime = datetime.combine(end_date, datetime.max.time())
    
    calculator = FairnessCalculator(start_datetime, end_datetime)
    
    # Get active employees
    from django.contrib.auth import get_user_model
    User = get_user_model()
    active_employees = User.objects.filter(
        is_active=True,
        employee_profile__status='active'
    ).select_related('employee_profile')
    
    assignments = calculator.calculate_current_assignments(list(active_employees))
    fairness_scores = calculator.calculate_fairness_score(assignments)
    
    # Format for chart consumption
    data = {
        'employees': [],
        'incidents': [],
        'waakdienst': [],
        'fairness_scores': []
    }
    
    for employee in active_employees:
        emp_assignments = assignments.get(employee.pk, {'incidents': 0, 'waakdienst': 0})
        fairness_score = fairness_scores.get(employee.pk, 0)
        
        data['employees'].append(employee.get_full_name() or employee.username)
        data['incidents'].append(emp_assignments['incidents'])
        data['waakdienst'].append(emp_assignments['waakdienst'])
        data['fairness_scores'].append(fairness_score)
    
    return JsonResponse(data)
