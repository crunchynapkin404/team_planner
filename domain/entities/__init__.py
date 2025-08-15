"""
Domain entities for the Team Planner orchestrator system.

Entities represent core business objects with identity and lifecycle.
They contain business logic and maintain consistency rules.
"""

from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Any
from ..value_objects import (
    EmployeeId, TeamId, ShiftId, AssignmentId, UserId,
    TimeRange, DateRange, ShiftType, AssignmentStatus,
    FairnessScore, AssignmentLoad, ConflictSeverity,
    TeamConfiguration
)


@dataclass
class Conflict:
    """Represents a scheduling conflict."""
    
    conflict_type: str
    severity: ConflictSeverity
    message: str
    affected_time_range: TimeRange
    resolution_suggestion: Optional[str] = None


@dataclass
class LeaveRequest:
    """Employee leave request."""
    
    id: int
    employee_id: EmployeeId
    start_date: date
    end_date: date
    leave_type: str  # 'vacation', 'leave', 'training'
    status: str      # 'approved', 'pending', 'rejected'
    coverage_type: str  # 'full_day', 'morning', 'afternoon'
    
    def conflicts_with_time_range(self, time_range: TimeRange) -> bool:
        """Check if this leave request conflicts with a time range."""
        if self.status != 'approved':
            return False
        
        # Convert time range to date range for comparison
        shift_start_date = time_range.start.date()
        shift_end_date = time_range.end.date()
        
        # Check if dates overlap
        dates_overlap = (
            self.start_date <= shift_end_date and 
            self.end_date >= shift_start_date
        )
        
        if not dates_overlap:
            return False
        
        # Check coverage type conflicts
        if self.leave_type == 'vacation':
            return True  # Vacation blocks all shifts
        elif self.leave_type == 'leave':
            # Leave only blocks daytime shifts (8-17h)
            shift_hour = time_range.start.hour
            return 8 <= shift_hour <= 17
        elif self.leave_type == 'training':
            return False  # Training doesn't block shifts
        
        return False


@dataclass
class RecurringLeavePattern:
    """Recurring leave pattern for an employee."""
    
    id: int
    employee_id: EmployeeId
    pattern_type: str  # 'weekly', 'biweekly'
    day_of_week: int   # 0-6 (Monday-Sunday)
    coverage_type: str # 'full_day', 'morning', 'afternoon'
    start_date: date
    end_date: Optional[date] = None
    
    def conflicts_with_time_range(self, time_range: TimeRange) -> bool:
        """Check if this recurring pattern conflicts with a time range."""
        shift_date = time_range.start.date()
        
        # Check if shift date is within pattern period
        if shift_date < self.start_date:
            return False
        if self.end_date and shift_date > self.end_date:
            return False
        
        # Check if day of week matches
        if shift_date.weekday() != self.day_of_week:
            return False
        
        # Check if pattern applies on this date
        if self.pattern_type == 'weekly':
            applies = True
        elif self.pattern_type == 'biweekly':
            # Calculate weeks since start date
            weeks_since_start = (shift_date - self.start_date).days // 7
            applies = weeks_since_start % 2 == 0
        else:
            applies = False
        
        if not applies:
            return False
        
        # Check coverage type
        if self.coverage_type == 'full_day':
            return True
        elif self.coverage_type == 'morning':
            return time_range.start.hour < 12
        elif self.coverage_type == 'afternoon':
            return time_range.start.hour >= 12
        
        return False


@dataclass
class Employee:
    """Core employee entity with scheduling constraints.
    
    Based on Phase 1 requirements analysis and SHIFT_SCHEDULING_SPEC.md.
    """
    
    id: EmployeeId
    name: str
    email: str
    team_id: TeamId
    hire_date: date
    termination_date: Optional[date] = None
    
    # Availability configuration - from Phase 1 analysis
    available_for_incidents: bool = True
    available_for_waakdienst: bool = True
    
    # Scheduling constraints - from Phase 1 analysis
    max_consecutive_weeks: int = 2
    min_rest_hours: int = 48
    
    # Current state
    current_assignments: List['Assignment'] = field(default_factory=list)
    leave_requests: List[LeaveRequest] = field(default_factory=list)
    recurring_patterns: List[RecurringLeavePattern] = field(default_factory=list)

    def is_available_for_shift(self, shift_type: ShiftType, time_range: TimeRange) -> bool:
        """Check if employee is available for a specific shift."""
        
        # Check basic availability toggles
        if shift_type == ShiftType.INCIDENTS and not self.available_for_incidents:
            return False
        if shift_type == ShiftType.INCIDENTS_STANDBY and not self.available_for_incidents:
            return False
        if shift_type == ShiftType.WAAKDIENST and not self.available_for_waakdienst:
            return False
        
        # Check if employee is still active
        if self.termination_date and time_range.start.date() > self.termination_date:
            return False
        
        # Check leave request conflicts
        for leave_request in self.leave_requests:
            if leave_request.conflicts_with_time_range(time_range):
                return False
        
        # Check recurring pattern conflicts
        for pattern in self.recurring_patterns:
            if pattern.conflicts_with_time_range(time_range):
                return False
        
        return True

    def calculate_assignment_load(self, period: DateRange) -> AssignmentLoad:
        """Calculate current assignment load for fairness."""
        
        incidents_hours = 0.0
        incidents_standby_hours = 0.0
        waakdienst_hours = 0.0
        
        for assignment in self.current_assignments:
            # Get the shift for this assignment (would be loaded from repository)
            # For now, assume we have access to shift time range
            if hasattr(assignment, 'shift') and assignment.shift:
                shift_start_date = assignment.shift.time_range.start.date()
                shift_end_date = assignment.shift.time_range.end.date()
                
                # Check if assignment falls within the period
                if (period.start <= shift_end_date and period.end >= shift_start_date):
                    duration = assignment.shift.time_range.duration_hours()
                    
                    if assignment.shift.shift_type == ShiftType.INCIDENTS:
                        incidents_hours += duration
                    elif assignment.shift.shift_type == ShiftType.INCIDENTS_STANDBY:
                        incidents_standby_hours += duration
                    elif assignment.shift.shift_type == ShiftType.WAAKDIENST:
                        waakdienst_hours += duration
        
        total_hours = incidents_hours + incidents_standby_hours + waakdienst_hours
        
        return AssignmentLoad(
            incidents_hours=incidents_hours,
            incidents_standby_hours=incidents_standby_hours,
            waakdienst_hours=waakdienst_hours,
            total_hours=total_hours,
            period=period
        )

    def has_conflict_with(self, assignment: 'Assignment') -> Optional[Conflict]:
        """Check if assignment conflicts with constraints."""
        
        if not assignment.shift:
            return None
        
        # Check availability for shift type
        if not self.is_available_for_shift(
            assignment.shift.shift_type, 
            assignment.shift.time_range
        ):
            return Conflict(
                conflict_type="availability",
                severity=ConflictSeverity.BLOCKING,
                message=f"Employee not available for {assignment.shift.shift_type.value}",
                affected_time_range=assignment.shift.time_range,
                resolution_suggestion="Assign to different employee"
            )
        
        # Check rest period conflicts
        rest_conflict = self._check_rest_period_conflict(assignment)
        if rest_conflict:
            return rest_conflict
        
        # Check consecutive weeks limit
        consecutive_conflict = self._check_consecutive_weeks_conflict(assignment)
        if consecutive_conflict:
            return consecutive_conflict
        
        return None

    def _check_rest_period_conflict(self, assignment: 'Assignment') -> Optional[Conflict]:
        """Check if assignment violates minimum rest period."""
        
        if not assignment.shift:
            return None
        
        min_rest_delta = timedelta(hours=self.min_rest_hours)
        
        for existing_assignment in self.current_assignments:
            if not existing_assignment.shift:
                continue
            
            # Check if assignments are close enough to require rest period
            time_between = abs(
                assignment.shift.time_range.start - existing_assignment.shift.time_range.end
            )
            
            if time_between < min_rest_delta:
                return Conflict(
                    conflict_type="rest_period",
                    severity=ConflictSeverity.BLOCKING,
                    message=f"Less than {self.min_rest_hours}h rest between assignments",
                    affected_time_range=assignment.shift.time_range,
                    resolution_suggestion="Schedule with more rest time"
                )
        
        return None

    def _check_consecutive_weeks_conflict(self, assignment: 'Assignment') -> Optional[Conflict]:
        """Check if assignment violates consecutive weeks limit."""
        
        if not assignment.shift:
            return None
        
        # Count consecutive weeks for the same shift type
        shift_week = assignment.shift.time_range.start.date().isocalendar()[1]
        consecutive_weeks = 1  # This assignment counts as 1
        
        for existing_assignment in self.current_assignments:
            if (existing_assignment.shift and 
                existing_assignment.shift.shift_type == assignment.shift.shift_type):
                
                existing_week = existing_assignment.shift.time_range.start.date().isocalendar()[1]
                
                # Check for consecutive weeks (simplified logic)
                if abs(existing_week - shift_week) <= self.max_consecutive_weeks:
                    consecutive_weeks += 1
        
        if consecutive_weeks > self.max_consecutive_weeks:
            return Conflict(
                conflict_type="consecutive_weeks",
                severity=ConflictSeverity.BLOCKING,
                message=f"Exceeds {self.max_consecutive_weeks} consecutive weeks limit",
                affected_time_range=assignment.shift.time_range,
                resolution_suggestion="Assign to different employee"
            )
        
        return None


@dataclass
class Shift:
    """Individual shift with specific time and requirements.
    
    Based on Phase 1 analysis of shift types and requirements.
    """
    
    id: ShiftId
    shift_type: ShiftType
    time_range: TimeRange
    team_id: TeamId
    
    # Assignment state
    assigned_employee: Optional[EmployeeId] = None
    assignment_status: AssignmentStatus = AssignmentStatus.PENDING
    auto_assigned: bool = False
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    modified_at: datetime = field(default_factory=datetime.utcnow)
    notes: str = ""

    def assign_to(self, employee: Employee) -> 'Assignment':
        """Create assignment to employee with validation."""
        
        # Basic validation
        if not employee.is_available_for_shift(self.shift_type, self.time_range):
            raise ValueError(f"Employee {employee.name} not available for this shift")
        
        # Update shift state
        self.assigned_employee = employee.id
        self.assignment_status = AssignmentStatus.CONFIRMED
        self.modified_at = datetime.utcnow()
        
        # Create assignment
        assignment = Assignment(
            id=AssignmentId.generate(),
            employee_id=employee.id,
            shift_id=self.id,
            assigned_at=datetime.utcnow(),
            assigned_by=UserId.system(),
            auto_assigned=True,
            status=AssignmentStatus.CONFIRMED,
            conflicts=[],
            shift=self  # Reference for easy access
        )
        
        return assignment

    def is_compatible_with(self, employee: Employee) -> bool:
        """Check if employee can be assigned to this shift."""
        return employee.is_available_for_shift(self.shift_type, self.time_range)

    def calculate_fairness_weight(self) -> float:
        """Calculate fairness weight for this shift."""
        base_weight = self.shift_type.fairness_weight
        
        # Adjust for shift duration
        duration_hours = self.time_range.duration_hours()
        duration_multiplier = duration_hours / 9.0  # Normalize to 9-hour standard
        
        # Adjust for time of day (nights/weekends get higher weight)
        time_multiplier = 1.0
        if self.time_range.start.hour >= 17 or self.time_range.start.hour <= 8:
            time_multiplier = 1.2  # Night shift bonus
        if self.time_range.start.weekday() >= 5:  # Weekend
            time_multiplier = 1.3  # Weekend bonus
        
        return base_weight * duration_multiplier * time_multiplier


@dataclass
class Assignment:
    """Assignment of an employee to a shift.
    
    Represents the relationship between an employee and a shift with metadata.
    """
    
    id: AssignmentId
    employee_id: EmployeeId
    shift_id: ShiftId
    
    # Assignment metadata
    assigned_at: datetime
    assigned_by: UserId
    auto_assigned: bool
    
    # Status tracking
    status: AssignmentStatus
    conflicts: List[Conflict]
    
    # Reference to shift for convenience (would be loaded by repository)
    shift: Optional[Shift] = None

    @classmethod
    def generate(cls) -> AssignmentId:
        """Generate a new assignment ID."""
        import random
        return AssignmentId(random.randint(1, 1000000))

    def validate(self) -> 'ValidationResult':
        """Validate assignment against all constraints."""
        violations = []
        
        if not self.shift:
            violations.append("No shift associated with assignment")
            return ValidationResult(is_valid=False, violations=violations)
        
        # Would validate against employee constraints, team configuration, etc.
        # This would use domain services for validation
        
        return ValidationResult(is_valid=len(violations) == 0, violations=violations)

    def calculate_impact(self, other_assignments: List['Assignment']) -> 'AssignmentImpact':
        """Calculate impact on fairness and conflicts."""
        
        # Placeholder implementation - would use fairness calculator
        return AssignmentImpact(
            fairness_impact=0.0,
            conflict_count=len(self.conflicts),
            affected_employees=[]
        )


@dataclass
class ValidationResult:
    """Result of validation operation."""
    is_valid: bool
    violations: List[str]


@dataclass 
class AssignmentImpact:
    """Impact of an assignment on the system."""
    fairness_impact: float
    conflict_count: int
    affected_employees: List[EmployeeId]
