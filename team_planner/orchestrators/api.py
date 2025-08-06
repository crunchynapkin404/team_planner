from rest_framework import status
from rest_framework.decorators import api_view
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

from .models import OrchestrationRun, OrchestrationResult
from .algorithms import ShiftOrchestrator, FairnessCalculator
from team_planner.employees.models import EmployeeProfile
from team_planner.shifts.models import Shift, ShiftTemplate

logger = logging.getLogger(__name__)


@api_view(['POST'])
def orchestrator_create_api(request):
    """API endpoint to create orchestrations for React frontend."""
    if not request.user.is_authenticated:
        return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
    
    if not request.user.has_perm('orchestrators.add_orchestrationrun'):
        return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        # Parse request data
        data = request.data
        name = data.get('name', f"Orchestration {timezone.now().date()}")
        description = data.get('description', '')
        start_date_str = data.get('start_date')
        end_date_str = data.get('end_date')
        preview_only = data.get('preview_only', 'true').lower() == 'true'
        
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
                    team_id=team_id,
                    schedule_incidents=schedule_incidents,
                    schedule_incidents_standby=schedule_incidents_standby,
                    schedule_waakdienst=schedule_waakdienst
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
                        'message': f"Preview generated: {result['total_shifts']} shifts planned" + 
                                  (f" ({len(result.get('potential_duplicates', []))} potential duplicates detected)" 
                                   if result.get('potential_duplicates') else "")
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
                        'skipped_duplicates': result.get('skipped_duplicates', []),
                        'message': f"Orchestration completed! Created {result['total_shifts']} shifts" +
                                  (f" ({len(result.get('skipped_duplicates', []))} duplicates skipped)" 
                                   if result.get('skipped_duplicates') else "")
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
    
    if not request.user.has_perm('orchestrators.change_orchestrationrun'):
        return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
    
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
        
        recent_runs = OrchestrationRun.objects.order_by('-started_at')[:5]
        recent_runs_data = []
        for run in recent_runs:
            recent_runs_data.append({
                'id': run.pk,
                'name': run.name,
                'status': run.status,
                'start_date': run.start_date.isoformat(),
                'end_date': run.end_date.isoformat(),
                'total_shifts': run.total_shifts_created,
                'created_at': run.started_at.isoformat()
            })
        
        return Response({
            'eligible_incidents': eligible_incidents,
            'eligible_waakdienst': eligible_waakdienst,
            'recent_runs': recent_runs_data,
            'system_status': 'operational'
        })
        
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
