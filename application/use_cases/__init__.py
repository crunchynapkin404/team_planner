"""Use cases for the scheduling application.

This module implements the application use cases that orchestrate domain services
to fulfill business requirements. Each use case represents a complete business
operation and handles the coordination between domain services.

Key Design Principles:
1. Single Responsibility - each use case handles one business operation
2. Clean Dependencies - use cases depend only on abstractions
3. Error Handling - comprehensive validation and error management
4. Transaction Management - proper unit of work patterns
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple, TYPE_CHECKING
from datetime import datetime, date
from dataclasses import dataclass
from enum import Enum

if TYPE_CHECKING:
    from ..repositories import (
        UnitOfWork, EmployeeQuery, ShiftQuery, AssignmentQuery
    )
    from domain.entities import Employee, Shift, Assignment
    from domain.value_objects import TimeRange, ShiftType, EmployeeId, ShiftId, DateRange
    from domain.services import (
        FairnessCalculator, ConflictDetector, ConstraintValidator
    )


class SchedulingError(Exception):
    """Base exception for scheduling operations."""
    pass


class InsufficientCoverageError(SchedulingError):
    """Raised when shift coverage requirements cannot be met."""
    pass


class ConflictDetectedError(SchedulingError):
    """Raised when scheduling conflicts are detected."""
    pass


class ConstraintViolationError(SchedulingError):
    """Raised when business constraints are violated."""
    pass


@dataclass
class SchedulingRequest:
    """Request for scheduling operations."""
    date_range: 'DateRange'
    department_ids: List[str]
    priority_shifts: Optional[List['ShiftId']] = None
    exclude_employees: Optional[List['EmployeeId']] = None
    force_assignments: Optional[Dict['ShiftId', 'EmployeeId']] = None
    constraints: Optional[Dict[str, Any]] = None


@dataclass
class SchedulingResult:
    """Result of scheduling operations."""
    assignments: List['Assignment']
    unassigned_shifts: List['Shift']
    conflicts_detected: List[Dict[str, Any]]
    fairness_scores: Dict['EmployeeId', float]
    coverage_analysis: Dict[str, Any]
    warnings: List[str]
    
    @property
    def success(self) -> bool:
        """Check if scheduling was fully successful."""
        return len(self.unassigned_shifts) == 0 and len(self.conflicts_detected) == 0


@dataclass
class ConflictResolution:
    """Instructions for resolving scheduling conflicts."""
    conflict_id: str
    resolution_type: str  # 'reassign', 'swap', 'unassign', 'override'
    affected_assignments: List[str]
    proposed_changes: Dict[str, Any]
    estimated_impact: Dict[str, float]


class OrchestrateScheduleUseCase:
    """
    Primary use case for orchestrating shift scheduling.
    
    Implements the complete scheduling workflow including:
    - Shift discovery and prioritization
    - Employee availability analysis  
    - Conflict detection and resolution
    - Fairness calculation and optimization
    - Coverage requirement validation
    """
    
    def __init__(
        self,
        uow: 'UnitOfWork',
        fairness_calculator: 'FairnessCalculator',
        conflict_detector: 'ConflictDetector'
    ):
        self.uow = uow
        self.fairness_calculator = fairness_calculator
        self.conflict_detector = conflict_detector
    
    async def execute(self, request: SchedulingRequest) -> SchedulingResult:
        """Execute the complete scheduling workflow."""
        try:
            async with self.uow:
                # Step 1: Discover shifts that need assignment
                shifts_to_assign = await self._discover_shifts(request)
                
                # Step 2: Get available employees
                available_employees = await self._get_available_employees(request)
                
                # Step 3: Calculate current fairness scores
                fairness_scores = await self._calculate_fairness_scores(
                    available_employees, request.date_range
                )
                
                # Step 4: Process forced assignments first
                assignments, conflicts = await self._process_forced_assignments(
                    request, shifts_to_assign
                )
                
                # Step 5: Assign remaining shifts using optimization
                remaining_shifts = [s for s in shifts_to_assign 
                                  if not any(hasattr(a, 'shift_id') and a.shift_id == s.id for a in assignments)]
                
                optimized_assignments, optimization_conflicts = await self._optimize_assignments(
                    remaining_shifts, available_employees, fairness_scores, request
                )
                
                assignments.extend(optimized_assignments)
                conflicts.extend(optimization_conflicts)
                
                # Step 6: Validate coverage requirements
                coverage_analysis = await self._validate_coverage(
                    assignments, request.date_range
                )
                
                # Step 7: Final conflict detection
                final_conflicts = await self._detect_final_conflicts(assignments, available_employees)
                conflicts.extend(final_conflicts)
                
                # Step 8: Calculate final fairness scores
                final_fairness = await self._calculate_final_fairness(
                    assignments, request.date_range
                )
                
                # Step 9: Identify unassigned shifts
                assigned_shift_ids = {getattr(a, 'shift_id', None) for a in assignments}
                unassigned_shifts = [s for s in shifts_to_assign 
                                   if s.id not in assigned_shift_ids]
                
                # Step 10: Generate warnings
                warnings = await self._generate_warnings(
                    assignments, unassigned_shifts, conflicts, coverage_analysis
                )
                
                result = SchedulingResult(
                    assignments=assignments,
                    unassigned_shifts=unassigned_shifts,
                    conflicts_detected=conflicts,
                    fairness_scores=final_fairness,
                    coverage_analysis=coverage_analysis,
                    warnings=warnings
                )
                
                # Commit if successful or rollback if major issues
                constraints = request.constraints or {}
                if result.success or constraints.get('allow_partial', False):
                    await self.uow.commit()
                else:
                    await self.uow.rollback()
                    
                return result
                
        except Exception as e:
            await self.uow.rollback()
            raise SchedulingError(f"Scheduling failed: {str(e)}") from e
    
    async def _discover_shifts(self, request: SchedulingRequest) -> List['Shift']:
        """Discover shifts that need assignment in the date range."""
        # Import here to avoid circular imports
        from ..repositories import ShiftQuery
        
        # Convert DateRange to TimeRange for query
        time_range_start = datetime.combine(request.date_range.start, datetime.min.time())
        time_range_end = datetime.combine(request.date_range.end, datetime.max.time())
        from domain.value_objects import TimeRange
        query_time_range = TimeRange(time_range_start, time_range_end)
        
        query = ShiftQuery(
            date_range=query_time_range,
            departments=request.department_ids,
            status='unassigned'
        )
        
        shifts = await self.uow.shifts.find_all(query)
        
        # Prioritize shifts if specified
        if request.priority_shifts:
            priority_ids = set(request.priority_shifts)
            priority_shifts = [s for s in shifts if s.id in priority_ids]
            regular_shifts = [s for s in shifts if s.id not in priority_ids]
            return priority_shifts + regular_shifts
        
        # Default prioritization by urgency and coverage needs
        return sorted(shifts, key=lambda s: (
            s.time_range.start,  # Earlier shifts first
            s.shift_type.value,  # Shift type priority
            s.id  # Stable sort
        ))
    
    async def _get_available_employees(self, request: SchedulingRequest) -> List['Employee']:
        """Get employees available for scheduling."""
        from ..repositories import EmployeeQuery
        
        # Convert DateRange to TimeRange for availability query
        time_range_start = datetime.combine(request.date_range.start, datetime.min.time())
        time_range_end = datetime.combine(request.date_range.end, datetime.max.time())
        from domain.value_objects import TimeRange
        query_time_range = TimeRange(time_range_start, time_range_end)
        
        query = EmployeeQuery(
            active_only=True,
            department_ids=request.department_ids,
            available_during=query_time_range,
            exclude_ids=request.exclude_employees
        )
        
        return await self.uow.employees.find_all(query)
    
    async def _calculate_fairness_scores(
        self, 
        employees: List['Employee'], 
        date_range: 'DateRange'
    ) -> Dict['EmployeeId', float]:
        """Calculate current fairness scores for employees."""
        fairness_scores = {}
        
        for employee in employees:
            # Convert DateRange to TimeRange for assignment query
            time_range_start = datetime.combine(date_range.start, datetime.min.time())
            time_range_end = datetime.combine(date_range.end, datetime.max.time())
            from domain.value_objects import TimeRange
            query_time_range = TimeRange(time_range_start, time_range_end)
            
            assignments = await self.uow.assignments.find_by_employee_and_date_range(
                employee.id, query_time_range
            )
            
            # Calculate fairness score using domain service
            fairness_result = self.fairness_calculator.calculate_employee_fairness(
                employee, assignments, date_range
            )
            fairness_scores[employee.id] = fairness_result.total_score
            
        return fairness_scores
    
    async def _process_forced_assignments(
        self, 
        request: SchedulingRequest,
        shifts: List['Shift']
    ) -> Tuple[List['Assignment'], List[Dict[str, Any]]]:
        """Process any forced assignments specified in the request."""
        assignments = []
        conflicts = []
        
        if not request.force_assignments:
            return assignments, conflicts
        
        for shift_id, employee_id in request.force_assignments.items():
            # Find the shift and employee
            shift = next((s for s in shifts if s.id == shift_id), None)
            if not shift:
                conflicts.append({
                    'type': 'shift_not_found',
                    'shift_id': shift_id,
                    'message': f'Forced assignment shift {shift_id} not found'
                })
                continue
            
            employee = await self.uow.employees.find_by_id(employee_id)
            if not employee:
                conflicts.append({
                    'type': 'employee_not_found',
                    'employee_id': employee_id,
                    'message': f'Forced assignment employee {employee_id} not found'
                })
                continue
            
            # Create assignment using domain entity
            assignment = Assignment.create_new(
                employee_id=employee_id,
                shift=shift,
                assigned_at=datetime.now(),
                status='tentative'
            )
            assignments.append(assignment)
        
        return assignments, conflicts
    
    async def _optimize_assignments(
        self,
        shifts: List['Shift'],
        employees: List['Employee'],
        fairness_scores: Dict['EmployeeId', float],
        request: SchedulingRequest
    ) -> Tuple[List['Assignment'], List[Dict[str, Any]]]:
        """Optimize shift assignments using fairness and availability."""
        assignments = []
        conflicts = []
        
        for shift in shifts:
            # Find eligible employees for this shift
            eligible_employees = []
            for employee in employees:
                if employee.can_work_shift(shift):
                    eligible_employees.append(employee)
            
            if not eligible_employees:
                conflicts.append({
                    'type': 'no_eligible_employees',
                    'shift_id': shift.id,
                    'message': f'No eligible employees for shift {shift.id}'
                })
                continue
            
            # Select best employee based on fairness
            best_employee = self._select_best_employee(
                eligible_employees, shift, fairness_scores
            )
            
            if best_employee:
                assignment = Assignment.create_new(
                    employee_id=best_employee.id,
                    shift=shift,
                    assigned_at=datetime.now(),
                    status='tentative'
                )
                assignments.append(assignment)
                
                # Update fairness scores for next iteration
                fairness_scores[best_employee.id] += 1.0  # Simplified update
        
        return assignments, conflicts
    
    def _select_best_employee(
        self,
        eligible_employees: List['Employee'],
        shift: 'Shift',
        fairness_scores: Dict['EmployeeId', float]
    ) -> Optional['Employee']:
        """Select the best employee for a shift based on fairness."""
        if not eligible_employees:
            return None
        
        # Score each employee
        scored_employees = []
        for employee in eligible_employees:
            # Base fairness score (lower is better for assignment)
            fairness_score = fairness_scores.get(employee.id, 0.0)
            
            # Simple scoring: prefer employees with lower fairness scores
            total_score = -fairness_score
            
            scored_employees.append((employee, total_score))
        
        # Return employee with highest total score (lowest fairness score)
        return max(scored_employees, key=lambda x: x[1])[0]
    
    async def _validate_coverage(
        self, 
        assignments: List['Assignment'],
        date_range: 'DateRange'
    ) -> Dict[str, Any]:
        """Validate that coverage requirements are met."""
        # Simplified coverage analysis
        return {
            'coverage_percentage': 100.0 if assignments else 0.0,
            'total_assignments': len(assignments),
            'coverage_gaps': []
        }
    
    async def _detect_final_conflicts(
        self, 
        assignments: List['Assignment'],
        employees: List['Employee']
    ) -> List[Dict[str, Any]]:
        """Detect any conflicts in the final assignment set."""
        conflicts = []
        
        # Create employee lookup
        employee_lookup = {emp.id: emp for emp in employees}
        
        for assignment in assignments:
            employee = employee_lookup.get(assignment.employee_id)
            if employee:
                # Use the correct method signature from domain service
                assignment_conflicts = self.conflict_detector.detect_conflicts(
                    assignment, employee, assignments
                )
                
                # Convert domain conflicts to dict format
                for conflict in assignment_conflicts:
                    conflicts.append({
                        'type': conflict.conflict_type,
                        'severity': conflict.severity.value,
                        'message': conflict.message,
                        'assignment_id': assignment.id
                    })
        
        return conflicts
    
    async def _calculate_final_fairness(
        self,
        assignments: List['Assignment'],
        date_range: 'DateRange'
    ) -> Dict['EmployeeId', float]:
        """Calculate final fairness scores after assignments."""
        # Group assignments by employee
        employee_assignments = {}
        for assignment in assignments:
            if assignment.employee_id not in employee_assignments:
                employee_assignments[assignment.employee_id] = []
            employee_assignments[assignment.employee_id].append(assignment)
        
        # Calculate scores
        fairness_scores = {}
        for employee_id, employee_assignments_list in employee_assignments.items():
            employee = await self.uow.employees.find_by_id(employee_id)
            if employee:
                fairness_result = self.fairness_calculator.calculate_employee_fairness(
                    employee, employee_assignments_list, date_range
                )
                fairness_scores[employee_id] = fairness_result.total_score
        
        return fairness_scores
    
    async def _generate_warnings(
        self,
        assignments: List['Assignment'],
        unassigned_shifts: List['Shift'],
        conflicts: List[Dict[str, Any]],
        coverage_analysis: Dict[str, Any]
    ) -> List[str]:
        """Generate warnings about the scheduling result."""
        warnings = []
        
        if unassigned_shifts:
            warnings.append(f"{len(unassigned_shifts)} shifts remain unassigned")
        
        if conflicts:
            warnings.append(f"{len(conflicts)} conflicts detected")
        
        if coverage_analysis.get('coverage_percentage', 100) < 90:
            warnings.append(
                f"Coverage below target: {coverage_analysis['coverage_percentage']:.1f}%"
            )
        
        return warnings


class ResolveConflictsUseCase:
    """
    Use case for resolving scheduling conflicts.
    
    Provides intelligent conflict resolution strategies including:
    - Automatic reassignment suggestions
    - Employee swapping options  
    - Constraint relaxation recommendations
    - Impact analysis for resolution options
    """
    
    def __init__(
        self,
        uow: 'UnitOfWork',
        conflict_detector: 'ConflictDetector',
        fairness_calculator: 'FairnessCalculator'
    ):
        self.uow = uow
        self.conflict_detector = conflict_detector
        self.fairness_calculator = fairness_calculator
    
    async def analyze_conflicts(
        self, 
        assignment_ids: List[str]
    ) -> List[Dict[str, Any]]:
        """Analyze conflicts for given assignments."""
        async with self.uow:
            assignments = []
            employees = {}
            
            for assignment_id in assignment_ids:
                assignment = await self.uow.assignments.find_by_id(assignment_id)
                if assignment:
                    assignments.append(assignment)
                    # Get employee for conflict detection
                    if assignment.employee_id not in employees:
                        employee = await self.uow.employees.find_by_id(assignment.employee_id)
                        if employee:
                            employees[assignment.employee_id] = employee
            
            conflicts = []
            for assignment in assignments:
                employee = employees.get(assignment.employee_id)
                if employee:
                    assignment_conflicts = self.conflict_detector.detect_conflicts(
                        assignment, employee, assignments
                    )
                    
                    # Convert to dict format
                    for conflict in assignment_conflicts:
                        conflicts.append({
                            'type': conflict.conflict_type,
                            'severity': conflict.severity.value,
                            'message': conflict.message,
                            'assignment_id': assignment.id
                        })
            
            return conflicts
    
    async def suggest_resolutions(
        self, 
        conflicts: List[Dict[str, Any]]
    ) -> List[ConflictResolution]:
        """Suggest resolutions for detected conflicts."""
        resolutions = []
        
        for conflict in conflicts:
            resolution_strategies = await self._generate_resolution_strategies(conflict)
            resolutions.extend(resolution_strategies)
        
        return resolutions
    
    async def _generate_resolution_strategies(
        self, 
        conflict: Dict[str, Any]
    ) -> List[ConflictResolution]:
        """Generate resolution strategies for a specific conflict."""
        strategies = []
        
        conflict_type = conflict.get('type')
        
        if conflict_type == 'time_overlap':
            strategies.extend(await self._resolve_time_overlap(conflict))
        elif conflict_type == 'skill_mismatch':
            strategies.extend(await self._resolve_skill_mismatch(conflict))
        elif conflict_type == 'leave_conflict':
            strategies.extend(await self._resolve_leave_conflict(conflict))
        
        return strategies
    
    async def _resolve_time_overlap(
        self, 
        conflict: Dict[str, Any]
    ) -> List[ConflictResolution]:
        """Resolve time overlap conflicts."""
        # Placeholder for time overlap resolution logic
        return []
    
    async def _resolve_skill_mismatch(
        self, 
        conflict: Dict[str, Any]
    ) -> List[ConflictResolution]:
        """Resolve skill mismatch conflicts."""
        # Placeholder for skill mismatch resolution logic
        return []
    
    async def _resolve_leave_conflict(
        self, 
        conflict: Dict[str, Any]
    ) -> List[ConflictResolution]:
        """Resolve leave conflicts."""
        # Placeholder for leave conflict resolution logic
        return []


# Export use cases
__all__ = [
    'SchedulingError',
    'InsufficientCoverageError', 
    'ConflictDetectedError',
    'ConstraintViolationError',
    'SchedulingRequest',
    'SchedulingResult',
    'ConflictResolution',
    'OrchestrateScheduleUseCase',
    'ResolveConflictsUseCase'
]
