"""
Unified Orchestrator Interface

This module provides a unified interface to the split orchestrator system,
maintaining compatibility with existing views while using the new specialized
orchestrators under the hood.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
from django.utils import timezone
import logging

from team_planner.shifts.models import ShiftType
from team_planner.teams.models import Team
from .models import OrchestrationRun, OrchestrationResult
from .incidents import IncidentsOrchestrator
from .incidents_standby import IncidentsStandbyOrchestrator
from .waakdienst import WaakdienstOrchestrator

logger = logging.getLogger(__name__)


class UnifiedOrchestrator:
    """
    Unified interface that routes to appropriate specialized orchestrators.
    
    This maintains compatibility with existing views while using the new
    split orchestrator architecture under the hood.
    """
    
    def __init__(self, team: Team, start_date: datetime, end_date: datetime, 
                 shift_types: Optional[List[ShiftType]] = None, dry_run: bool = True,
                 user = None):
        self.team = team
        self.start_date = start_date
        self.end_date = end_date
        self.shift_types = shift_types or list(ShiftType)
        self.dry_run = dry_run
        self.user = user  # For orchestration run tracking
        
        # Track results from both orchestrators
        self.results = {
            'assignments': [],
            'errors': [],
            'warnings': [],
            'stats': {}
        }
        
        # Initialize save operation tracking
        self.created_shifts = 0
        self.updated_shifts = 0
        self.conflicts_resolved = 0
        
        # Initialize specialized orchestrators
        self.incidents_orchestrator = None
        self.incidents_standby_orchestrator = None
        self.waakdienst_orchestrator = None
        
        # Create separate orchestrators for incidents and incidents-standby
        if ShiftType.INCIDENTS in self.shift_types:
            self.incidents_orchestrator = IncidentsOrchestrator(
                start_date=start_date,
                end_date=end_date,
                team_id=team.pk
            )
            
        if ShiftType.INCIDENTS_STANDBY in self.shift_types:
            self.incidents_standby_orchestrator = IncidentsStandbyOrchestrator(
                start_date=start_date,
                end_date=end_date,
                team_id=team.pk
            )
            
        if self._should_handle_waakdienst():
            self.waakdienst_orchestrator = WaakdienstOrchestrator(team_id=team.pk)
    
    def _should_handle_incidents(self) -> bool:
        """Check if we should handle incidents shifts."""
        return ShiftType.INCIDENTS in self.shift_types
    
    def _should_handle_incidents_standby(self) -> bool:
        """Check if we should handle incidents-standby shifts."""
        return ShiftType.INCIDENTS_STANDBY in self.shift_types
    
    def _should_handle_waakdienst(self) -> bool:
        """Check if we should handle waakdienst shifts."""
        return ShiftType.WAAKDIENST in self.shift_types
    
    def preview_schedule(self) -> Dict:
        """Generate a preview without saving to database."""
        logger.info(f"Creating preview for team {self.team.name} from {self.start_date} to {self.end_date}")
        
        # Run incidents orchestrator if needed
        if self.incidents_orchestrator:
            try:
                incidents_result = self._run_incidents_orchestrator()
                self._merge_results('incidents', incidents_result)
            except Exception as e:
                logger.error(f"Incidents orchestrator failed: {e}")
                self.results['errors'].append(f"Incidents scheduling failed: {str(e)}")
        
        # Run incidents-standby orchestrator if needed
        if self.incidents_standby_orchestrator:
            try:
                standby_result = self._run_incidents_standby_orchestrator()
                self._merge_results('incidents_standby', standby_result)
            except Exception as e:
                logger.error(f"Incidents-Standby orchestrator failed: {e}")
                self.results['errors'].append(f"Incidents-Standby scheduling failed: {str(e)}")
        
        # Run waakdienst orchestrator if needed  
        if self.waakdienst_orchestrator:
            try:
                waakdienst_result = self._run_waakdienst_orchestrator()
                self._merge_results('waakdienst', waakdienst_result)
            except Exception as e:
                logger.error(f"Waakdienst orchestrator failed: {e}")
                self.results['errors'].append(f"Waakdienst scheduling failed: {str(e)}")
        
        # Format results for compatibility with existing views
        return self._format_preview_result()
    
    def apply_schedule(self) -> Dict:
        """Generate and save the schedule to database."""
        if self.dry_run:
            logger.warning("apply_schedule called but dry_run=True, switching to preview mode")
            return self.preview_schedule()
        
        logger.info(f"Applying schedule for team {self.team.name} from {self.start_date} to {self.end_date}")
        
        # Use existing orchestration run if available (for legacy compatibility)
        orchestration_run = getattr(self, 'orchestration_run', None)
        if orchestration_run:
            run = orchestration_run
        else:
            # Create orchestration run record
            run = OrchestrationRun.objects.create(
                name=f"Split Orchestrator - {self.team.name}",
                description=f"Automated scheduling using split orchestrator architecture",
                start_date=self.start_date.date(),
                end_date=self.end_date.date(),
                schedule_incidents=ShiftType.INCIDENTS in self.shift_types,
                schedule_incidents_standby=ShiftType.INCIDENTS_STANDBY in self.shift_types,
                schedule_waakdienst=ShiftType.WAAKDIENST in self.shift_types,
                status=OrchestrationRun.Status.RUNNING,
                initiated_by=self.user,
            )
        
        try:
            # Run orchestrators
            total_assignments = 0
            
            print(f"DEBUG: Starting orchestration with incidents_orchestrator={self.incidents_orchestrator}, incidents_standby_orchestrator={self.incidents_standby_orchestrator}, waakdienst_orchestrator={self.waakdienst_orchestrator}")
            
            if self.incidents_orchestrator:
                print("DEBUG: Running incidents orchestrator...")
                incidents_result = self._run_incidents_orchestrator(save=True)
                print(f"DEBUG: Incidents result: {len(incidents_result.get('assignments', []))} assignments")
                self._merge_results('incidents', incidents_result)
                total_assignments += len(incidents_result.get('assignments', []))
            
            if self.incidents_standby_orchestrator:
                print("DEBUG: Running incidents-standby orchestrator...")
                standby_result = self._run_incidents_standby_orchestrator(save=True)
                print(f"DEBUG: Incidents-Standby result: {len(standby_result.get('assignments', []))} assignments")
                self._merge_results('incidents_standby', standby_result)
                total_assignments += len(standby_result.get('assignments', []))
            
            if self.waakdienst_orchestrator:
                print("DEBUG: Running waakdienst orchestrator...")
                waakdienst_result = self._run_waakdienst_orchestrator(save=True)
                print(f"DEBUG: Waakdienst result: {len(waakdienst_result.get('assignments', []))} assignments")
                self._merge_results('waakdienst', waakdienst_result)
                total_assignments += len(waakdienst_result.get('assignments', []))
            
            print(f"DEBUG: Total assignments after orchestrators: {total_assignments}")
            print(f"DEBUG: Total assignments in self.results: {len(self.results['assignments'])}")
            
            # Update run status
            run.status = OrchestrationRun.Status.COMPLETED
            run.completed_at = timezone.now()
            run.total_shifts_created = total_assignments
            if self.results['errors']:
                run.error_message = '\n'.join(self.results['errors'])
            if self.results['warnings']:
                run.execution_log = f"Warnings:\n" + '\n'.join(self.results['warnings'])
            run.save()
            
            # Create result records and actual shifts for individual assignments
            created_shifts = 0
            print(f"DEBUG: Creating shifts from {len(self.results['assignments'])} assignments...")
            
            # Import here to avoid circular imports
            from team_planner.shifts.models import Shift
            
            # Process all assignments
            for i, assignment in enumerate(self.results['assignments'], 1):
                try:
                    # Extract values carefully
                    template = assignment.get('template')
                    employee_id = assignment.get('assigned_employee_id')
                    start_dt = assignment.get('start_datetime')
                    end_dt = assignment.get('end_datetime')
                    
                    # Validate all fields are present
                    if not all([template, employee_id, start_dt, end_dt]):
                        print(f"DEBUG: Assignment {i} missing required fields!")
                        continue
                    
                    # Check if shift already exists
                    existing_shift = Shift.objects.filter(
                        template=template,
                        assigned_employee_id=employee_id,
                        start_datetime=start_dt,
                        end_datetime=end_dt
                    ).first()
                    
                    if existing_shift:
                        print(f"DEBUG: Shift {i} already exists (ID: {existing_shift.pk}), skipping")
                        continue
                    
                    # Create shift
                    shift = Shift.objects.create(
                        template=template,
                        assigned_employee_id=employee_id,
                        start_datetime=start_dt,
                        end_datetime=end_dt,
                        status=Shift.Status.SCHEDULED
                    )
                    
                    created_shifts += 1
                    
                    if i <= 5 or i % 50 == 0:  # Log first 5 and every 50th
                        print(f"DEBUG: Created shift {shift.pk} for assignment {i}")
                    
                except Exception as e:
                    print(f"DEBUG: Error creating shift {i}: {e}")
                    logger.error(f"Failed to create shift {i}: {e}")
                    # Continue with next assignment instead of failing completely
                    continue
            
            print(f"DEBUG: Created {created_shifts} actual shifts out of {len(self.results['assignments'])} assignments")
            
            # Update the run with actual created shifts count
            run.total_shifts_created = created_shifts
            run.save()
            
            logger.info(f"Successfully created {created_shifts} shifts for team {self.team.name}")
            
        except Exception as e:
            run.status = OrchestrationRun.Status.FAILED
            run.completed_at = timezone.now()
            run.error_message = str(e)
            run.save()
            logger.error(f"Orchestration failed for team {self.team.name}: {e}")
            raise
        
        return self._format_apply_result(run)
    
    def _run_incidents_orchestrator(self, save: bool = False) -> Dict:
        """Run the incidents orchestrator for the specified date range."""
        if not self.incidents_orchestrator:
            return {'assignments': [], 'errors': [], 'warnings': [], 'stats': {}}
        
        try:
            # The new IncidentsOrchestrator uses the BaseOrchestrator.generate_schedule() interface
            if save:
                # Create orchestration run for tracking
                from .models import OrchestrationRun
                run = OrchestrationRun.objects.create(
                    name=f"Incidents - {self.team.name}",
                    description=f"Automated incidents scheduling",
                    start_date=self.start_date.date(),
                    end_date=self.end_date.date(),
                    schedule_incidents=True,
                    schedule_incidents_standby=False,
                    schedule_waakdienst=False,
                    status=OrchestrationRun.Status.RUNNING,
                    initiated_by=self.user,
                )
                
                # Generate and save schedule
                result = self.incidents_orchestrator.generate_schedule(orchestration_run=run)
                
                # Update run status
                run.status = OrchestrationRun.Status.COMPLETED
                run.completed_at = timezone.now()
                run.save()
                
            else:
                # Preview mode - don't save
                result = self.incidents_orchestrator.generate_schedule()
            
            # Convert to expected format
            assignments = result.get('assignments', [])
            return {
                'assignments': assignments,
                'errors': result.get('errors', []),
                'warnings': result.get('warnings', []),
                'stats': {
                    'weeks_generated': len(assignments) // 5 if assignments else 0,  # 5 days per week
                    'business_days': len(assignments)
                }
            }
            
        except Exception as e:
            logger.error(f"IncidentsOrchestrator failed: {e}")
            import traceback
            traceback.print_exc()
            return {
                'assignments': [],
                'errors': [f"Incidents orchestrator failed: {str(e)}"],
                'warnings': [],
                'stats': {}
            }
    
    def _run_incidents_standby_orchestrator(self, save: bool = False) -> Dict:
        """Run the incidents-standby orchestrator for the specified date range."""
        if not self.incidents_standby_orchestrator:
            return {'assignments': [], 'errors': [], 'warnings': [], 'stats': {}}
        
        try:
            # The new IncidentsStandbyOrchestrator uses the BaseOrchestrator.generate_schedule() interface
            if save:
                # Create orchestration run for tracking
                from .models import OrchestrationRun
                run = OrchestrationRun.objects.create(
                    name=f"Incidents-Standby - {self.team.name}",
                    description=f"Automated incidents-standby scheduling",
                    start_date=self.start_date.date(),
                    end_date=self.end_date.date(),
                    schedule_incidents=False,
                    schedule_incidents_standby=True,
                    schedule_waakdienst=False,
                    status=OrchestrationRun.Status.RUNNING,
                    initiated_by=self.user,
                )
                
                # Generate and save schedule
                result = self.incidents_standby_orchestrator.generate_schedule(orchestration_run=run)
                
                # Update run status
                run.status = OrchestrationRun.Status.COMPLETED
                run.completed_at = timezone.now()
                run.save()
                
            else:
                # Preview mode - don't save
                result = self.incidents_standby_orchestrator.generate_schedule()
            
            # Convert to expected format
            assignments = result.get('assignments', [])
            return {
                'assignments': assignments,
                'errors': result.get('errors', []),
                'warnings': result.get('warnings', []),
                'stats': {
                    'weeks_generated': len(assignments) // 5 if assignments else 0,  # 5 days per week
                    'business_days': len(assignments)
                }
            }
            
        except Exception as e:
            logger.error(f"IncidentsStandbyOrchestrator failed: {e}")
            import traceback
            traceback.print_exc()
            return {
                'assignments': [],
                'errors': [f"Incidents-Standby orchestrator failed: {str(e)}"],
                'warnings': [],
                'stats': {}
            }
    
    def _run_waakdienst_orchestrator(self, save: bool = False) -> Dict:
        """Run the waakdienst orchestrator for the specified date range."""
        current_date = self.start_date
        all_assignments = []
        
        # Align to Wednesday 17:00 start
        while current_date.weekday() != 2 or current_date.hour < 17:
            if current_date.weekday() == 2 and current_date.hour < 17:
                current_date = current_date.replace(hour=17, minute=0, second=0, microsecond=0)
                break
            else:
                current_date += timedelta(days=1)
                current_date = current_date.replace(hour=17, minute=0, second=0, microsecond=0)
        
        while current_date < self.end_date:
            # Calculate week end (next Wednesday 08:00)
            week_end = current_date + timedelta(days=7)
            week_end = week_end.replace(hour=8, minute=0, second=0, microsecond=0)
            
            if current_date >= self.end_date:
                break
                
            # Generate waakdienst week  
            week_result = {}
            if self.waakdienst_orchestrator is not None:
                week_result = self.waakdienst_orchestrator.generate_waakdienst_week_assignments(
                    current_date, dry_run=(save==False)
                )
            
            if week_result.get('assignments'):
                all_assignments.extend(week_result['assignments'])
            
            # Move to next Wednesday
            current_date = week_end.replace(hour=17)
        
        return {
            'assignments': all_assignments,
            'errors': [],
            'warnings': [],
            'stats': {
                'weeks_generated': len(all_assignments) // 21 if all_assignments else 0,  # 21 shifts per week
                'evening_shifts': len([a for a in all_assignments if a.get('shift_type') == ShiftType.WAAKDIENST])
            }
        }
    
    def _merge_results(self, orchestrator_type: str, result: Dict):
        """Merge results from an orchestrator into the unified results."""
        self.results['assignments'].extend(result.get('assignments', []))
        self.results['errors'].extend(result.get('errors', []))
        self.results['warnings'].extend(result.get('warnings', []))
        self.results['stats'][orchestrator_type] = result.get('stats', {})
    
    def _format_preview_result(self) -> Dict:
        """Format results for preview display with legacy API compatibility."""
        # Calculate shift type counts
        incidents_shifts = len([a for a in self.results['assignments'] if a.get('shift_type') == 'incidents'])
        incidents_standby_shifts = len([a for a in self.results['assignments'] if a.get('shift_type') == 'incidents-standby'])
        waakdienst_shifts = len([a for a in self.results['assignments'] if a.get('shift_type') == 'waakdienst'])
        total_shifts = len(self.results['assignments'])
        
        # Extract fairness scores from assignments and calculate metrics
        fairness_scores = {}
        unique_employees = set()
        for assignment in self.results['assignments']:
            emp_id = assignment.get('employee_id') or assignment.get('assigned_employee_id')
            if emp_id:
                fairness_scores[emp_id] = assignment.get('fairness_after', 0.0)
                unique_employees.add(emp_id)
        
        # Calculate average fairness
        average_fairness = sum(fairness_scores.values()) / len(fairness_scores) if fairness_scores else 0.0
        
        return {
            'success': len(self.results['errors']) == 0,
            'assignments': self.results['assignments'],
            'total_assignments': total_shifts,  # New format
            'total_shifts': total_shifts,  # Legacy compatibility
            'incidents_shifts': incidents_shifts,  # Legacy compatibility
            'incidents_standby_shifts': incidents_standby_shifts,  # Legacy compatibility
            'waakdienst_shifts': waakdienst_shifts,  # Legacy compatibility
            'employees_assigned': len(unique_employees),  # Legacy compatibility
            'fairness_scores': fairness_scores,  # Legacy compatibility
            'average_fairness': average_fairness,  # Legacy compatibility
            'errors': self.results['errors'],
            'warnings': self.results['warnings'],
            'stats': self.results['stats'],
            'orchestrator_type': 'split_orchestrator',
            'start_date': self.start_date,
            'end_date': self.end_date,
            'shift_types': self.shift_types
        }
    
    def _format_save_result(self) -> Dict:
        """Format results for save operations with legacy API compatibility."""
        # Calculate shift type counts
        incidents_shifts = len([a for a in self.results['assignments'] if a.get('shift_type') == 'incidents'])
        incidents_standby_shifts = len([a for a in self.results['assignments'] if a.get('shift_type') == 'incidents-standby'])
        waakdienst_shifts = len([a for a in self.results['assignments'] if a.get('shift_type') == 'waakdienst'])
        total_shifts = len(self.results['assignments'])
        
        # Extract fairness scores from assignments and calculate metrics
        fairness_scores = {}
        unique_employees = set()
        for assignment in self.results['assignments']:
            emp_id = assignment.get('employee_id') or assignment.get('assigned_employee_id')
            if emp_id:
                fairness_scores[emp_id] = assignment.get('fairness_after', 0.0)
                unique_employees.add(emp_id)
        
        # Calculate average fairness
        average_fairness = sum(fairness_scores.values()) / len(fairness_scores) if fairness_scores else 0.0
        
        return {
            'success': len(self.results['errors']) == 0,
            'total_assignments': total_shifts,  # New format
            'total_shifts': total_shifts,  # Legacy compatibility
            'incidents_shifts': incidents_shifts,  # Legacy compatibility
            'incidents_standby_shifts': incidents_standby_shifts,  # Legacy compatibility
            'waakdienst_shifts': waakdienst_shifts,  # Legacy compatibility
            'employees_assigned': len(unique_employees),  # Legacy compatibility
            'fairness_scores': fairness_scores,  # Legacy compatibility
            'average_fairness': average_fairness,  # Legacy compatibility
            'errors': self.results['errors'],
            'warnings': self.results['warnings'],
            'stats': self.results['stats'],
            'created_shifts': self.created_shifts,
            'updated_shifts': self.updated_shifts,
            'conflicts_resolved': self.conflicts_resolved,
            'orchestrator_type': 'split_orchestrator'
        }
    
    def _format_apply_result(self, run: OrchestrationRun) -> Dict:
        """Format results for applied schedule with legacy API compatibility."""
        # Calculate shift type counts from results
        incidents_shifts = len([a for a in self.results['assignments'] if a.get('shift_type') == 'incidents'])
        incidents_standby_shifts = len([a for a in self.results['assignments'] if a.get('shift_type') == 'incidents-standby'])
        waakdienst_shifts = len([a for a in self.results['assignments'] if a.get('shift_type') == 'waakdienst'])
        
        # Calculate unique employees assigned
        unique_employees = set()
        for assignment in self.results['assignments']:
            if assignment.get('assigned_employee_id'):
                unique_employees.add(assignment['assigned_employee_id'])
        
        return {
            'success': run.status == OrchestrationRun.Status.COMPLETED,
            'run_id': run.pk,
            'assignments_created': run.total_shifts_created,
            'total_shifts': run.total_shifts_created,  # Legacy compatibility
            'incidents_shifts': incidents_shifts,  # Legacy compatibility  
            'incidents_standby_shifts': incidents_standby_shifts,  # Legacy compatibility
            'waakdienst_shifts': waakdienst_shifts,  # Legacy compatibility
            'employees_assigned': len(unique_employees),  # API compatibility
            'created_shifts': self.results.get('created_shifts', []),  # Legacy compatibility
            'errors': [run.error_message] if run.error_message else [],
            'warnings': [run.execution_log] if run.execution_log else [],
            'stats': self.results['stats'],
            'orchestrator_type': 'split_orchestrator'
        }


# Maintain backward compatibility
class ShiftOrchestrator(UnifiedOrchestrator):
    """
    Legacy interface for backward compatibility.
    
    This class provides the same interface as the old ShiftOrchestrator
    but uses the new split orchestrator system internally.
    """
    
    def __init__(self, start_date: datetime, end_date: datetime,
                 schedule_incidents: bool = True,
                 schedule_incidents_standby: bool = False,
                 schedule_waakdienst: bool = True,
                 team: Optional[Team] = None,
                 team_id: Optional[int] = None,
                 orchestration_run: Optional[OrchestrationRun] = None,
                 **kwargs):
        # Convert boolean flags to shift types
        shift_types = []
        if schedule_incidents:
            shift_types.append(ShiftType.INCIDENTS)
        if schedule_incidents_standby:
            shift_types.append(ShiftType.INCIDENTS_STANDBY)
        if schedule_waakdienst:
            shift_types.append(ShiftType.WAAKDIENST)
        
        # Handle team selection
        if team is None and team_id is not None:
            team = Team.objects.get(pk=team_id)
        elif team is None:
            team = Team.objects.first()
            if team is None:
                raise ValueError("No team available for orchestration")
            
        # Extract user from orchestration_run if available
        user = orchestration_run.initiated_by if orchestration_run else kwargs.get('user')
        kwargs['user'] = user
        
        super().__init__(team, start_date, end_date, shift_types, **kwargs)
        
        # Store orchestration run for legacy compatibility
        self.orchestration_run = orchestration_run


# Export for compatibility
__all__ = ['UnifiedOrchestrator', 'ShiftOrchestrator']
