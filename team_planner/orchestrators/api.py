from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.db import transaction
from datetime import date, datetime, timedelta
import json
import logging
from typing import Any, DefaultDict, Dict, Tuple
from collections import defaultdict

from .models import OrchestrationRun, OrchestrationResult
from .unified import UnifiedOrchestrator, ShiftOrchestrator  # Legacy compatibility
from .fairness_calculators import ComprehensiveFairnessCalculator as FairnessCalculator  # Use comprehensive calculator for API
from team_planner.employees.models import EmployeeProfile
from team_planner.teams.models import Team
from team_planner.shifts.models import ShiftType
from team_planner.users.models import User
from team_planner.shifts.models import Shift, ShiftTemplate
from team_planner.orchestrators.anchors import next_weekday_time, get_team_tz, WEEKDAY_MON, WEEKDAY_FRI
from team_planner.orchestrators.tasks import extend_rolling_horizon_core, extend_rolling_horizon_task
from django.conf import settings

logger = logging.getLogger(__name__)


@api_view(['POST'])
def orchestrator_create_api(request):
    """API endpoint to create orchestrations for React frontend."""
    if not request.user.is_authenticated:
        return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
    
    # Allow staff users or users with specific orchestrator permissions
    if not (request.user.is_staff or request.user.has_perm('orchestrators.add_orchestrationrun')):
        return Response({'error': 'Permission denied - staff access required'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        # Parse request data
        data = request.data
        name = data.get('name', f"Orchestration {timezone.now().date()}")
        description = data.get('description', '')
        start_date_str = data.get('start_date')
        end_date_str = data.get('end_date')
        # preview_only may arrive as bool or string
        _raw_preview = data.get('preview_only', True)
        if isinstance(_raw_preview, str):
            preview_only = _raw_preview.lower() == 'true'
        else:
            preview_only = bool(_raw_preview)
        
        # Parse individual shift type selections
        schedule_incidents = data.get('schedule_incidents', True)
        schedule_incidents_standby = data.get('schedule_incidents_standby', False)
        schedule_waakdienst = data.get('schedule_waakdienst', True)
        
        team_id = data.get('team_id')
        
        if not start_date_str or not end_date_str:
            return Response({'error': 'Start date and end date are required'}, status=status.HTTP_400_BAD_REQUEST)
        
        if not team_id:
            return Response({'error': 'Team selection is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate at least one shift type is selected
        if not any([schedule_incidents, schedule_incidents_standby, schedule_waakdienst]):
            return Response({'error': 'At least one shift type must be selected'}, status=status.HTTP_400_BAD_REQUEST)
        
        start_date = date.fromisoformat(start_date_str)
        end_date = date.fromisoformat(end_date_str)
        
        # Validate date range
        if start_date >= end_date:
            return Response({'error': 'End date must be after start date'}, status=status.HTTP_400_BAD_REQUEST)
        
        if start_date < date.today():
            return Response({'error': 'Start date cannot be in the past'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Convert to timezone-aware datetime for orchestrator
        start_datetime = timezone.make_aware(datetime.combine(start_date, datetime.min.time()))
        end_datetime = timezone.make_aware(datetime.combine(end_date, datetime.max.time()))

        # Round up end_datetime to ensure at least one full anchor-aligned period is included
        try:
            team = Team.objects.get(pk=team_id)
        except Team.DoesNotExist:
            return Response({'error': 'Invalid team'}, status=status.HTTP_400_BAD_REQUEST)
        tz = get_team_tz(team)

        # Compute first incidents week end (Fri 17:00) after the next Mon 08:00 strictly after start
        adjusted_end = end_datetime
        if schedule_incidents or schedule_incidents_standby:
            first_monday = next_weekday_time(start_datetime, WEEKDAY_MON, 8, tz=tz, strictly_after=True)
            # Friday 17:00 of that week
            monday_of_week_dt = first_monday.replace(hour=0, minute=0, second=0, microsecond=0)
            first_friday = monday_of_week_dt + timedelta(days=(WEEKDAY_FRI - WEEKDAY_MON) % 7)
            first_friday = first_friday.replace(hour=17, minute=0, second=0, microsecond=0)
            if first_friday > adjusted_end:
                adjusted_end = first_friday

        if schedule_waakdienst:
            # Team-configurable waakdienst anchors
            weekday = int((getattr(team, 'waakdienst_handover_weekday', None) or 2))
            start_hour = int((getattr(team, 'waakdienst_start_hour', None) or 17))
            end_hour = int((getattr(team, 'waakdienst_end_hour', None) or 8))
            first_waak_start = next_weekday_time(start_datetime, weekday, start_hour, tz=tz, strictly_after=True)
            first_waak_end = (first_waak_start + timedelta(days=7)).replace(hour=end_hour, minute=0, second=0, microsecond=0)
            if first_waak_end > adjusted_end:
                adjusted_end = first_waak_end

        end_datetime = adjusted_end
        
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
                # Create and run orchestrator with selected shift types and orchestration run
                # Determine which shift types to include
                shift_types = []
                if schedule_incidents:
                    shift_types.append(ShiftType.INCIDENTS)
                if schedule_incidents_standby:
                    shift_types.append(ShiftType.INCIDENTS_STANDBY)
                if schedule_waakdienst:
                    shift_types.append(ShiftType.WAAKDIENST)
                
                orchestrator = UnifiedOrchestrator(
                    team=team,
                    start_date=start_datetime,
                    end_date=end_datetime,
                    shift_types=shift_types,
                    dry_run=preview_only,
                    user=request.user
                )
                
                if preview_only:
                    result = orchestrator.preview_schedule()
                    
                    # Store basic run info for preview
                    run.status = OrchestrationRun.Status.PREVIEW
                    run.completed_at = timezone.now()
                    run.total_shifts_created = result['total_shifts']
                    run.incidents_shifts_created = result.get('incidents_shifts', 0)
                    run.incidents_standby_shifts_created = result.get('incidents_standby_shifts', 0)
                    run.waakdienst_shifts_created = result.get('waakdienst_shifts', 0)
                    run.save()
                    
                    # Materialize preview results into OrchestrationResult rows for later application
                    assignments = result.get('assignments', [])
                    fairness_scores = result.get('fairness_scores', {})
                    
                    # Helper to compute Monday of week
                    def monday_of_week(dt: datetime) -> date:
                        return (dt - timedelta(days=dt.weekday())).date()
                    
                    # Aggregate by (shift_type, week_start) -> employee counts and sample reason
                    agg: DefaultDict[Tuple[str, date], Dict[str, Any]] = defaultdict(lambda: {
                        'counts': defaultdict(int),
                        'reason': 'Fair distribution'
                    })
                    
                    for a in assignments:
                        st = a['shift_type']
                        if (st == 'incidents' and not schedule_incidents) or (st == 'waakdienst' and not schedule_waakdienst):
                            continue
                        if st not in ('incidents', 'waakdienst'):
                            continue  # ignore standby in preview apply flow
                        wk = monday_of_week(a['start_datetime'])
                        key = (st, wk)
                        # Count by employee ID or name
                        emp_key = a.get('assigned_employee_id', a.get('assigned_employee_name', 'unknown'))
                        agg[key]['counts'][emp_key] += 1  # type: ignore[index]
                        agg[key]['reason'] = a.get('assignment_reason') or 'Fair distribution'
                    
                    # Create one result per week/type picking the most frequent employee
                    for (st, wk), data_ in agg.items():
                        counts_map = data_.get('counts')
                        if not counts_map:
                            continue
                        employee_id, _ = max(counts_map.items(), key=lambda kv: kv[1])
                        # Convert employee ID to User object for database storage
                        employee_obj = User.objects.get(pk=employee_id)
                        fs = float(fairness_scores.get(employee_id, 0) or 0)
                        OrchestrationResult.objects.update_or_create(
                            orchestration_run=run,
                            shift_type=st,
                            week_start_date=wk,
                            defaults={
                                'employee': employee_obj,
                                'week_end_date': wk + timedelta(days=6),
                                'fairness_score_before': fs,
                                'fairness_score_after': fs,
                                'assignment_reason': data_.get('reason', 'Fair distribution'),
                                'is_applied': False,
                            }
                        )
                    
                    # Store the run ID in session for potential application
                    request.session['orchestration_preview_run_id'] = run.pk
                    
                    return Response({
                        'success': True,
                        'preview': True,
                        'run_id': run.pk,
                        'total_shifts': result['total_shifts'],
                        'incidents_shifts': result.get('incidents_shifts', 0),
                        'incidents_standby_shifts': result.get('incidents_standby_shifts', 0),
                        'waakdienst_shifts': result.get('waakdienst_shifts', 0),
                        'employees_assigned': result['employees_assigned'],
                        'fairness_scores': result.get('fairness_scores', {}),
                        'average_fairness': result.get('average_fairness', 0),
                        'potential_duplicates': result.get('potential_duplicates', []),
                        'reassignment_summary': result.get('reassignment_summary'),
                        'message': f"Preview generated: {result['total_shifts']} shifts planned" + 
                                  (f" ({len(result.get('potential_duplicates', []))} potential duplicates detected)" 
                                   if result.get('potential_duplicates') else "") +
                                  (f" - {result.get('reassignment_summary', {}).get('successful_reassignments', 0)} conflicts auto-resolved"
                                   if result.get('reassignment_summary', {}).get('successful_reassignments', 0) > 0 else "")
                    })
                    
                else:
                    # Apply schedule directly
                    result = orchestrator.apply_schedule()
                    
                    # Update run with results
                    run.status = OrchestrationRun.Status.COMPLETED
                    run.completed_at = timezone.now()
                    run.total_shifts_created = result['total_shifts']
                    run.incidents_shifts_created = result.get('incidents_shifts', 0)
                    run.incidents_standby_shifts_created = result.get('incidents_standby_shifts', 0)
                    run.waakdienst_shifts_created = result.get('waakdienst_shifts', 0)
                    run.save()
                    
                    # Shifts are already created by apply_schedule()
                    # No need to create additional OrchestrationResult records for direct application
                    
                    return Response({
                        'success': True,
                        'applied': True,
                        'run_id': run.pk,
                        'total_shifts': result['total_shifts'],
                        'incidents_shifts': result.get('incidents_shifts', 0),
                        'incidents_standby_shifts': result.get('incidents_standby_shifts', 0),
                        'waakdienst_shifts': result.get('waakdienst_shifts', 0),
                        'employees_assigned': result['employees_assigned'],
                        'fairness_scores': result.get('fairness_scores', {}),
                        'average_fairness': result.get('average_fairness', 0),
                        'created_shifts': len(result.get('created_shifts', [])),
                        'skipped_duplicates': len(result.get('skipped_duplicates', [])),
                        'reassignment_summary': result.get('reassignment_summary'),
                        'message': f"Schedule applied: {len(result.get('created_shifts', []))} shifts created" +
                                  (f", {len(result.get('skipped_duplicates', []))} duplicates skipped" 
                                   if result.get('skipped_duplicates') else "") +
                                  (f" - {result.get('reassignment_summary', {}).get('successful_reassignments', 0)} conflicts auto-resolved"
                                   if result.get('reassignment_summary', {}).get('successful_reassignments', 0) > 0 else "")
                    })
                    
            except Exception as e:
                run.status = OrchestrationRun.Status.FAILED
                run.error_message = str(e)
                run.completed_at = timezone.now()
                run.save()
                logger.error(f"Orchestration failed: {str(e)}", exc_info=True)
                return Response({'error': f'Orchestration failed: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
    except Exception as e:
        logger.error(f"API error: {str(e)}", exc_info=True)
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def orchestrator_apply_preview_api(request):
    """API endpoint to apply a previewed orchestration."""
    if not request.user.is_authenticated:
        return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
    
    # Allow staff users or users with specific orchestrator permissions
    if not (request.user.is_staff or request.user.has_perm('orchestrators.change_orchestrationrun')):
        return Response({'error': 'Permission denied - staff access required'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        # Get the preview run ID from session
        run_id = request.session.get('orchestration_preview_run_id')
        if not run_id:
            return Response({'error': 'No preview data available'}, status=status.HTTP_400_BAD_REQUEST)
        
        run = OrchestrationRun.objects.get(pk=run_id, status=OrchestrationRun.Status.PREVIEW)
        
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
            for result in OrchestrationResult.objects.filter(orchestration_run=run, is_applied=False):
                if result.shift_type == 'incidents':
                    template = incidents_template
                    # Incidents: Monday 8:00 to Friday 17:00
                    start_datetime = timezone.make_aware(
                        datetime.combine(result.week_start_date, datetime.min.time().replace(hour=8))
                    )
                    end_datetime = timezone.make_aware(
                        datetime.combine(result.week_start_date + timedelta(days=4), datetime.min.time().replace(hour=17))
                    )
                else:
                    template = waakdienst_template
                    # Waakdienst: Wednesday 17:00 to next Wednesday 8:00
                    start_datetime = timezone.make_aware(
                        datetime.combine(result.week_start_date + timedelta(days=2), datetime.min.time().replace(hour=17))
                    )
                    end_datetime = timezone.make_aware(
                        datetime.combine(result.week_start_date + timedelta(days=9), datetime.min.time().replace(hour=8))
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
            
            # Clear preview from session
            if 'orchestration_preview_run_id' in request.session:
                del request.session['orchestration_preview_run_id']
            
            return Response({
                'success': True,
                'message': f'Successfully created {shifts_created} shifts',
                'shifts_created': shifts_created,
                'run_id': run.pk
            })
            
    except OrchestrationRun.DoesNotExist:
        return Response({'error': 'Preview orchestration not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def orchestrator_status_api(request):
    """API endpoint to get orchestrator system status."""
    if not request.user.is_authenticated:
        return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
    
    try:
        # Get system statistics
        eligible_incidents = EmployeeProfile.objects.filter(
            status=EmployeeProfile.Status.ACTIVE,
            available_for_incidents=True
        ).count()
        
        eligible_waakdienst = EmployeeProfile.objects.filter(
            status=EmployeeProfile.Status.ACTIVE,
            available_for_waakdienst=True
        ).count()
        
        # Get orchestration statistics
        total_runs = OrchestrationRun.objects.count()
        successful_runs = OrchestrationRun.objects.filter(status=OrchestrationRun.Status.COMPLETED).count()
        success_rate = (successful_runs / total_runs * 100) if total_runs > 0 else 0
        active_runs = OrchestrationRun.objects.filter(status=OrchestrationRun.Status.RUNNING).count()
        
        recent_runs = OrchestrationRun.objects.order_by('-started_at')[:10]
        recent_runs_data = []
        for run in recent_runs:
            duration = None
            if run.started_at and run.completed_at:
                duration = (run.completed_at - run.started_at).total_seconds() * 1000  # milliseconds
            
            recent_runs_data.append({
                'id': run.pk,
                'name': run.name,
                'status': run.status,
                'start_date': run.start_date.isoformat(),
                'end_date': run.end_date.isoformat(),
                'total_shifts': run.total_shifts_created or 0,
                'incidents_shifts': run.incidents_shifts_created or 0,
                'waakdienst_shifts': run.waakdienst_shifts_created or 0,
                'created_at': run.started_at.isoformat() if run.started_at else None,
                'completed_at': run.completed_at.isoformat() if run.completed_at else None,
                'initiated_by': run.initiated_by.get_full_name() or run.initiated_by.username,
                'description': run.description,
                'duration': duration,
                'error_message': run.error_message
            })
        
        return Response({
            'eligible_incidents': eligible_incidents,
            'eligible_waakdienst': eligible_waakdienst,
            'recent_runs': recent_runs_data,
            'system_status': 'operational',
            'total_runs': total_runs,
            'active_runs': active_runs,
            'success_rate': success_rate
        })
        
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def fairness_api(request):
    """API endpoint for fairness dashboard data."""
    try:
        # Get parameters
        time_range = request.GET.get('time_range', 'current_year')
        employee_id = request.GET.get('employee', 'all')
        
        # Calculate date range
        today = timezone.now().date()
        if time_range == 'current_year':
            start_date = today.replace(month=1, day=1)
            end_date = today.replace(month=12, day=31)
        elif time_range == 'last_6_months':
            start_date = today - timedelta(days=180)
            end_date = today
        elif time_range == 'last_3_months':
            start_date = today - timedelta(days=90)
            end_date = today
        else:  # all_time
            start_date = date(2020, 1, 1)  # Far back default
            end_date = today
        
        # Convert to datetime
        start_datetime = timezone.make_aware(datetime.combine(start_date, datetime.min.time()))
        end_datetime = timezone.make_aware(datetime.combine(end_date, datetime.max.time()))
        
        calculator = FairnessCalculator(start_datetime, end_datetime)
        
        # Get active employees
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        employees_query = User.objects.filter(
            is_active=True,
            employee_profile__status='active'
        ).select_related('employee_profile')
        
        if employee_id != 'all':
            employees_query = employees_query.filter(id=employee_id)
        
        active_employees = list(employees_query)
        
        # Calculate current assignments
        assignments = calculator.calculate_current_assignments(active_employees)
        # Build base assignments for ALL employees (0 hours but with capacity)
        base_assignments = {}
        for employee in active_employees:
            profile = getattr(employee, 'employee_profile', None)
            availability_info = calculator.calculate_employee_available_hours(employee)
            available_incidents = getattr(profile, 'available_for_incidents', False) if profile else False
            available_waakdienst = getattr(profile, 'available_for_waakdienst', False) if profile else False
            hours_per_week = availability_info['hours_per_week'] if (available_incidents or available_waakdienst) else 0.0
            base_assignments[employee.pk] = {
                'incidents': 0.0,
                'incidents_standby': 0.0,
                'waakdienst': 0.0,
                'total_hours': 0.0,
                'available_hours_per_week': hours_per_week,
                'availability_percentage': availability_info['percentage'] if hours_per_week > 0 else 0.0,
                'available_incidents': available_incidents,
                'available_waakdienst': available_waakdienst,
            }
        # Merge actual into base
        for emp_id, data in assignments.items():
            base_assignments[emp_id].update({
                'incidents': data.get('incidents', 0.0),
                'incidents_standby': data.get('incidents_standby', 0.0),
                'waakdienst': data.get('waakdienst', 0.0),
                'total_hours': data.get('total_hours', 0.0),
            })
            for k in ('available_hours_per_week', 'availability_percentage'):
                if k in data:
                    base_assignments[emp_id][k] = data[k]
        assignments = base_assignments

        # Per-type totals and capacity (only eligible employees contribute capacity)
        total_incidents = sum(v.get('incidents', 0.0) for v in assignments.values())
        total_standby = sum(v.get('incidents_standby', 0.0) for v in assignments.values())
        total_waakdienst = sum(v.get('waakdienst', 0.0) for v in assignments.values())
        cap_incidents = sum(v.get('available_hours_per_week', 0.0) for v in assignments.values() if v.get('available_incidents'))
        cap_standby = cap_incidents  # same eligibility
        cap_waakdienst = sum(v.get('available_hours_per_week', 0.0) for v in assignments.values() if v.get('available_waakdienst'))

        # Overall totals (for averages context)
        total_employees = len(active_employees)
        avg_incidents = (sum(v.get('incidents', 0.0) for v in assignments.values()) / total_employees) if total_employees else 0.0
        avg_waakdienst = (sum(v.get('waakdienst', 0.0) for v in assignments.values()) / total_employees) if total_employees else 0.0
        avg_total = (sum((v.get('incidents', 0.0)+v.get('incidents_standby',0.0)+v.get('waakdienst',0.0)) for v in assignments.values()) / total_employees) if total_employees else 0.0

        employee_data = []
        fairness_distribution = {'excellent': 0, 'good': 0, 'fair': 0, 'poor': 0, 'na': 0}

        for employee in active_employees:
            data = assignments.get(employee.pk, {})
            cap = float(data.get('available_hours_per_week', 0.0))
            avail_i = bool(data.get('available_incidents'))
            avail_w = bool(data.get('available_waakdienst'))

            inc_hours = float(data.get('incidents', 0.0))
            stb_hours = float(data.get('incidents_standby', 0.0))
            waa_hours = float(data.get('waakdienst', 0.0))

            # Expected per type
            def exp_dev_fair(assigned: float, cap_total: float, type_total: float, eligible: bool):
                if not eligible or cap <= 0 or cap_total <= 0 or type_total <= 0:
                    return (0.0, 0.0, None)  # expected, deviation, fairness=N/A
                expected = (cap / cap_total) * type_total
                deviation = assigned - expected
                ratio = abs(deviation) / expected if expected > 0 else 0.0
                score = max(0.0, 100.0 - ratio * 100.0)
                return (expected, deviation, round(score, 2))

            exp_i, dev_i, fair_i = exp_dev_fair(inc_hours, cap_incidents, total_incidents, avail_i)
            exp_s, dev_s, fair_s = exp_dev_fair(stb_hours, cap_standby, total_standby, avail_i)
            exp_w, dev_w, fair_w = exp_dev_fair(waa_hours, cap_waakdienst, total_waakdienst, avail_w)

            # Overall fairness = average of available type fair scores
            fair_vals = [v for v in (fair_i, fair_s, fair_w) if isinstance(v, (int, float))]
            overall_fairness = round(sum(fair_vals)/len(fair_vals), 2) if fair_vals else None

            # Last assignment date (from applied orchestration results)
            last_assignment = OrchestrationResult.objects.filter(
                employee=employee,
                is_applied=True
            ).order_by('-applied_at').first()

            # Identity and availability flags
            profile = getattr(employee, 'employee_profile', None)
            available_incidents = getattr(profile, 'available_for_incidents', False) if profile else False
            available_waakdienst = getattr(profile, 'available_for_waakdienst', False) if profile else False
            full_name = ''
            try:
                full_name = employee.get_full_name() or ''  # type: ignore[attr-defined]
            except Exception:
                full_name = ''
            username = getattr(employee, 'username', '') or getattr(employee, 'email', '') or f"User {getattr(employee, 'pk', '')}"

            # Build row
            row = {
                'employee_id': employee.pk,
                'employee_name': full_name or username,
                'incidents_count': round(inc_hours, 1),
                'incidents_standby_count': round(stb_hours, 1),
                'waakdienst_count': round(waa_hours, 1),
                'total_assignments': round(inc_hours + stb_hours + waa_hours, 1),
                'fairness_score': overall_fairness if overall_fairness is not None else 0.0,  # legacy key
                'overall_fairness': overall_fairness,
                'incidents_fairness': fair_i,
                'standby_fairness': fair_s,
                'waakdienst_fairness': fair_w,
                'expected_incidents_hours': round(exp_i, 1),
                'deviation_incidents_hours': round(dev_i, 1),
                'expected_standby_hours': round(exp_s, 1),
                'deviation_standby_hours': round(dev_s, 1),
                'expected_waakdienst_hours': round(exp_w, 1),
                'deviation_waakdienst_hours': round(dev_w, 1),
                'available_incidents': available_incidents,
                'available_waakdienst': available_waakdienst,
                'last_assignment_date': last_assignment.applied_at.date().isoformat() if last_assignment and last_assignment.applied_at else None
            }
            employee_data.append(row)

            # Categorize by overall_fairness if present; else N/A
            if overall_fairness is None:
                fairness_distribution['na'] += 1
            elif overall_fairness >= 90:
                fairness_distribution['excellent'] += 1
            elif overall_fairness >= 70:
                fairness_distribution['good'] += 1
            elif overall_fairness >= 50:
                fairness_distribution['fair'] += 1
            else:
                fairness_distribution['poor'] += 1

        # Sort by lowest overall fairness first (None treated as worst)
        employee_data.sort(key=lambda x: (x.get('overall_fairness') is None, x.get('overall_fairness') or 0))

        historical_data = []  # unchanged for now
        return Response({
            'employees': employee_data,
            'metrics': {
                'total_employees': total_employees,
                'average_incidents': avg_incidents,
                'average_waakdienst': avg_waakdienst,
                'average_total': avg_total,
                'fairness_distribution': fairness_distribution,
            },
            'historical': historical_data,
            'time_range': time_range,
        })
    
    except Exception as e:
        logger.error(f"Fairness API error: {str(e)}", exc_info=True)
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def orchestrator_run_horizon_api(request):
    """Run rolling-horizon scheduling and return a JSON summary.
    Body: { months?: int=6, weeks?: int, dry_run: bool=true, team_ids?: number[] }
    """
    if not request.user.is_authenticated:
        return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
    if not (request.user.is_staff or request.user.has_perm('orchestrators.add_orchestrationrun')):
        return Response({'error': 'Permission denied - staff access required'}, status=status.HTTP_403_FORBIDDEN)
    try:
        payload = request.data or {}
        months = int(payload.get('months', 6))
        weeks = payload.get('weeks')
        weeks = int(weeks) if weeks is not None else None
        dry_run = bool(payload.get('dry_run', True))
        team_ids = payload.get('team_ids')
        shift_types = payload.get('shift_types')  # optional list: ['incidents','waakdienst','incidents_standby']
        if team_ids and not isinstance(team_ids, (list, tuple)):
            return Response({'error': 'team_ids must be a list of integers'}, status=status.HTTP_400_BAD_REQUEST)
        if shift_types is not None and not isinstance(shift_types, (list, tuple)):
            return Response({'error': 'shift_types must be a list of strings'}, status=status.HTTP_400_BAD_REQUEST)

        summary = extend_rolling_horizon_core(months=months, dry_run=dry_run, team_ids=team_ids, weeks=weeks, shift_types=list(shift_types) if shift_types is not None else None)
        # Serialize datetimes
        def ser_dt(x):
            return x.isoformat() if isinstance(x, (datetime,)) else x
        summary_out = dict(summary)
        summary_out['now'] = ser_dt(summary['now'])
        summary_out['end'] = ser_dt(summary['end'])
        return Response(summary_out, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Automation API failed: {e}", exc_info=True)
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


from celery.result import AsyncResult

@api_view(['POST'])
def orchestrator_run_horizon_async_api(request):
    """Dispatch rolling-horizon scheduling as a background Celery task.
    Body: { months?: int=6, weeks?: int, dry_run: bool=false, team_ids?: number[] }
    Returns: { task_id }
    """
    if not request.user.is_authenticated:
        return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
    if not (request.user.is_staff or request.user.has_perm('orchestrators.add_orchestrationrun')):
        return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
    payload = request.data or {}
    months = int(payload.get('months', 6))
    weeks = payload.get('weeks')
    weeks = int(weeks) if weeks is not None else None
    dry_run = bool(payload.get('dry_run', False))
    team_ids = payload.get('team_ids')
    shift_types = payload.get('shift_types')
    try:
        team_ids_param = ([*team_ids] if isinstance(team_ids, (list, tuple)) else team_ids)
        shift_types_param = ([*shift_types] if isinstance(shift_types, (list, tuple)) else None)
        async_result = extend_rolling_horizon_task.delay(months=months, dry_run=dry_run, team_ids=team_ids_param, weeks=weeks, shift_types=shift_types_param)  # type: ignore
        return Response({'task_id': async_result.id}, status=status.HTTP_202_ACCEPTED)
    except Exception as e:
        logger.error(f"Failed to dispatch automation task: {e}", exc_info=True)
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def orchestrator_automation_status_api(request):
    """Query Celery task status for automation runs.
    Query: ?task_id=<id>
    """
    if not request.user.is_authenticated:
        return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
    task_id = request.GET.get('task_id')
    if not task_id:
        return Response({'error': 'task_id is required'}, status=status.HTTP_400_BAD_REQUEST)
    res = AsyncResult(task_id)
    data = {'task_id': task_id, 'state': res.state}
    if res.successful():
        try:
            data['result'] = res.get(propagate=False)
        except Exception:
            data['result'] = None
    elif res.failed():
        data['error'] = str(res.result)
    return Response(data)


@api_view(['POST'])
def orchestrator_enable_auto_api(request):
    """Ensure a Celery Beat periodic task exists to extend horizon nightly for configured weeks ahead."""
    if not request.user.is_authenticated:
        return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
    if not (request.user.is_staff or request.user.is_superuser):
        return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
    try:
        from django_celery_beat.models import PeriodicTask, CrontabSchedule
        import json as _json
        schedule, _ = CrontabSchedule.objects.get_or_create(minute='0', hour='2', day_of_week='*', day_of_month='*', month_of_year='*')
        task_name = 'orchestrators.extend_rolling_horizon_nightly'
        weeks = int(getattr(settings, 'ORCHESTRATOR_ROLLING_WEEKS', 26))
        kwargs = {'weeks': weeks, 'dry_run': False, 'team_ids': None}
        pt, created = PeriodicTask.objects.get_or_create(
            name=task_name,
            defaults={
                'crontab': schedule,
                'task': 'orchestrators.extend_rolling_horizon',
                'args': _json.dumps([]),
                'kwargs': _json.dumps(kwargs),
                'enabled': True,
            }
        )
        if not created:
            pt.crontab = schedule
            pt.kwargs = _json.dumps(kwargs)
            pt.enabled = True
            pt.save()
        return Response({'enabled': True, 'periodic_task': {'id': int(getattr(pt, 'id')), 'name': pt.name, 'schedule': '2:00 daily', 'kwargs': kwargs}}, status=status.HTTP_200_OK)
    except ImportError:
        return Response({'error': 'django-celery-beat not installed'}, status=status.HTTP_501_NOT_IMPLEMENTED)
    except Exception as e:
        logger.error(f"Failed to enable auto-run: {e}", exc_info=True)
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def orchestrator_clear_shifts_api(request):
    """Danger: Delete shifts for testing. Optional body: { team_id?: number }.
    Requires staff or superuser.
    """
    if not request.user.is_authenticated:
        return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
    if not (request.user.is_staff or request.user.is_superuser):
        return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
    try:
        payload = request.data or {}
        team_id = payload.get('team_id')
        base_qs = Shift.objects.all()
        if team_id is not None and team_id != "":
            try:
                team_id_int = int(team_id)
            except Exception:
                return Response({'error': 'team_id must be an integer'}, status=status.HTTP_400_BAD_REQUEST)
            base_qs = base_qs.filter(assigned_employee__teams__id=team_id_int)
        # Collect PKs first to avoid backend limitations with DELETE + DISTINCT/JOINS
        ids = list(base_qs.values_list('pk', flat=True).distinct())
        if not ids:
            return Response({'deleted': 0}, status=status.HTTP_200_OK)
        deleted, _ = Shift.objects.filter(pk__in=ids).delete()
        return Response({'deleted': int(deleted)}, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Failed to clear shifts: {e}", exc_info=True)
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def orchestrator_auto_overview_api(request):
    """Return auto-rolling configuration and per-team seed status for the UI."""
    if not request.user.is_authenticated:
        return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
    if not (request.user.is_staff or request.user.has_perm('orchestrators.add_orchestrationrun')):
        return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
    try:
        now = timezone.now()
        require_seed = bool(getattr(settings, 'ORCHESTRATOR_AUTO_ROLL_REQUIRES_SEED', True))
        min_seed_weeks = int(getattr(settings, 'ORCHESTRATOR_MIN_SEED_WEEKS', 26))
        rolling_weeks = int(getattr(settings, 'ORCHESTRATOR_ROLLING_WEEKS', 26))
        seed_target = now + timedelta(weeks=max(1, min_seed_weeks))

        teams_info = []
        qs = Team.objects.filter(teammembership__is_active=True).distinct()

        # Gather beat status and per-team per-type enabled state
        beat = None
        per_team_type_enabled = {}
        try:
            from django_celery_beat.models import PeriodicTask
            task_prefix = 'orchestrators.extend_rolling_horizon_nightly'
            beat_tasks = list(PeriodicTask.objects.filter(name__startswith=task_prefix))
            beat = {'count': len(beat_tasks)}
            for pt in beat_tasks:
                # Expected format: prefix:teamId:shiftType
                parts = pt.name.split(':')
                if len(parts) == 3:
                    _, team_id_str, shift_type = parts
                    try:
                        team_id_int = int(team_id_str)
                    except Exception:
                        continue
                    per_team_type_enabled.setdefault(team_id_int, {})[shift_type] = bool(pt.enabled)
        except Exception:
            beat = None

        for team in qs:
            coverage_qs = Shift.objects.filter(
                assigned_employee__teams=team,
                status__in=[Shift.Status.SCHEDULED, Shift.Status.IN_PROGRESS]
            )
            coverage_end = coverage_qs.order_by('-end_datetime').values_list('end_datetime', flat=True).first()
            has_seed = bool(coverage_qs.filter(end_datetime__gte=seed_target).exists())
            # Per-type presence and latest coverage end
            type_presence = {}
            type_ends = {}
            for st in ('incidents', 'incidents_standby', 'waakdienst'):
                qs_t = coverage_qs.filter(template__shift_type=st)
                type_presence[st] = qs_t.exists()
                last_end = qs_t.order_by('-end_datetime').values_list('end_datetime', flat=True).first()
                type_ends[st] = last_end.isoformat() if last_end else None

            teams_info.append({
                'id': team.pk,
                'name': str(team),
                'coverage_end': coverage_end.isoformat() if coverage_end else None,
                'seed_ready': has_seed,
                'types_present': type_presence,
                'coverage_end_by_type': type_ends,
                'rolling_enabled': per_team_type_enabled.get(team.pk, {}),
            })

        return Response({
            'now': now.isoformat(),
            'require_seed': require_seed,
            'min_seed_weeks': min_seed_weeks,
            'rolling_weeks': rolling_weeks,
            'teams': teams_info,
            'beat': beat,
        })
    except Exception as e:
        logger.error(f"Auto overview API failed: {e}", exc_info=True)
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def orchestrator_auto_toggle_api(request):
    """Enable/disable nightly rolling for a specific team and shift type.
    Body: { team_id: number, shift_type: 'incidents'|'incidents_standby'|'waakdienst', enabled: bool }
    """
    if not request.user.is_authenticated:
        return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
    if not (request.user.is_staff or request.user.is_superuser):
        return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
    try:
        from django_celery_beat.models import PeriodicTask, CrontabSchedule
        import json as _json
        payload = request.data or {}
        if 'team_id' not in payload or 'shift_type' not in payload:
            return Response({'error': 'team_id and shift_type are required'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            team_id = int(str(payload.get('team_id', '')).strip())
        except Exception:
            return Response({'error': 'team_id must be an integer'}, status=status.HTTP_400_BAD_REQUEST)
        shift_type = str(payload.get('shift_type'))
        enabled = bool(payload.get('enabled', True))
        if shift_type not in ('incidents', 'incidents_standby', 'waakdienst'):
            return Response({'error': 'Invalid shift_type'}, status=status.HTTP_400_BAD_REQUEST)
        # Ensure team exists
        Team.objects.get(pk=team_id)

        schedule, _ = CrontabSchedule.objects.get_or_create(minute='0', hour='2', day_of_week='*', day_of_month='*', month_of_year='*')
        task_name = f'orchestrators.extend_rolling_horizon_nightly:{team_id}:{shift_type}'
        weeks = int(getattr(settings, 'ORCHESTRATOR_ROLLING_WEEKS', 26))
        kwargs = {'weeks': weeks, 'dry_run': False, 'team_ids': [team_id], 'shift_types': [shift_type]}
        pt, created = PeriodicTask.objects.get_or_create(
            name=task_name,
            defaults={
                'crontab': schedule,
                'task': 'orchestrators.extend_rolling_horizon',
                'args': _json.dumps([]),
                'kwargs': _json.dumps(kwargs),
                'enabled': enabled,
            }
        )
        if not created:
            pt.crontab = schedule
            pt.kwargs = _json.dumps(kwargs)
            pt.enabled = enabled
            pt.save()
        return Response({'team_id': team_id, 'shift_type': shift_type, 'enabled': pt.enabled}, status=status.HTTP_200_OK)
    except Team.DoesNotExist:
        return Response({'error': 'Invalid team_id'}, status=status.HTTP_400_BAD_REQUEST)
    except ImportError:
        return Response({'error': 'django-celery-beat not installed'}, status=status.HTTP_501_NOT_IMPLEMENTED)
    except Exception as e:
        logger.error(f"Failed to toggle auto-run: {e}", exc_info=True)
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
