"""Query handlers for the scheduling application.

Queries represent requests for data without side effects. Query handlers
are responsible for retrieving and transforming data according to specific
application needs.

Key Design Principles:
1. Queries are immutable requests for data
2. Handlers focus on data retrieval and transformation
3. Read-only operations with no side effects
4. Optimized for specific UI/API needs
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, TYPE_CHECKING
from datetime import datetime, date
from dataclasses import dataclass

if TYPE_CHECKING:
    from ..repositories import UnitOfWork, EmployeeQuery, ShiftQuery, AssignmentQuery
    from domain.entities import Employee, Shift, Assignment
    from domain.value_objects import TimeRange, ShiftType, EmployeeId, ShiftId, DateRange


class QueryError(Exception):
    """Base exception for query execution errors."""
    pass


@dataclass
class Query(ABC):
    """Base class for all queries."""
    pass


@dataclass
class GetScheduleQuery(Query):
    """Query to get schedule for a date range."""
    date_range: 'DateRange'
    department_ids: Optional[List[str]] = None
    include_unassigned: bool = True
    include_conflicts: bool = True


@dataclass
class GetEmployeeAvailabilityQuery(Query):
    """Query to get employee availability for a time period."""
    employee_id: 'EmployeeId'
    date_range: 'DateRange'
    include_assignments: bool = True
    include_leave: bool = True


@dataclass
class GetUnassignedShiftsQuery(Query):
    """Query to get unassigned shifts."""
    date_range: 'DateRange'
    department_ids: Optional[List[str]] = None
    shift_types: Optional[List['ShiftType']] = None
    priority_only: bool = False


@dataclass
class GetFairnessReportQuery(Query):
    """Query to get fairness analysis for employees."""
    date_range: 'DateRange'
    department_ids: Optional[List[str]] = None
    include_projections: bool = False


@dataclass
class GetConflictAnalysisQuery(Query):
    """Query to get conflict analysis for a date range."""
    date_range: 'DateRange'
    department_ids: Optional[List[str]] = None
    severity_threshold: str = 'low'  # 'low', 'medium', 'high'


@dataclass
class GetCoverageAnalysisQuery(Query):
    """Query to get coverage analysis for shifts."""
    date_range: 'DateRange'
    department_ids: Optional[List[str]] = None
    include_requirements: bool = True


@dataclass
class QueryResult:
    """Result of query execution."""
    success: bool
    data: Optional[Dict[str, Any]] = None
    message: Optional[str] = None
    errors: Optional[List[str]] = None


class QueryHandler(ABC):
    """Base class for query handlers."""
    
    def __init__(self, uow: 'UnitOfWork'):
        self.uow = uow
    
    @abstractmethod
    async def handle(self, query: Query) -> QueryResult:
        """Handle the query execution."""
        pass


class GetScheduleQueryHandler(QueryHandler):
    """Handler for GetScheduleQuery."""
    
    async def handle(self, query: GetScheduleQuery) -> QueryResult:
        """Handle schedule retrieval."""
        try:
            async with self.uow:
                # Import here to avoid circular dependencies
                from ..repositories import ShiftQuery, AssignmentQuery
                
                # Convert DateRange to TimeRange for queries
                time_range_start = datetime.combine(query.date_range.start, datetime.min.time())
                time_range_end = datetime.combine(query.date_range.end, datetime.max.time())
                from domain.value_objects import TimeRange
                query_time_range = TimeRange(time_range_start, time_range_end)
                
                # Get all shifts in date range
                shift_query = ShiftQuery(
                    date_range=query_time_range,
                    departments=query.department_ids
                )
                shifts = await self.uow.shifts.find_all(shift_query)
                
                # Get all assignments in date range
                assignment_query = AssignmentQuery(
                    date_range=query_time_range,
                    departments=query.department_ids,
                    status='active'
                )
                assignments = await self.uow.assignments.find_all(assignment_query)
                
                # Group assignments by shift
                assignments_by_shift = {}
                for assignment in assignments:
                    if assignment.shift_id not in assignments_by_shift:
                        assignments_by_shift[assignment.shift_id] = []
                    assignments_by_shift[assignment.shift_id].append(assignment)
                
                # Build schedule data
                schedule_data = {
                    'date_range': {
                        'start': query.date_range.start.isoformat(),
                        'end': query.date_range.end.isoformat()
                    },
                    'shifts': [],
                    'summary': {
                        'total_shifts': len(shifts),
                        'assigned_shifts': len([s for s in shifts if s.id in assignments_by_shift]),
                        'unassigned_shifts': len([s for s in shifts if s.id not in assignments_by_shift]),
                        'total_assignments': len(assignments)
                    }
                }
                
                # Add shift details
                for shift in shifts:
                    shift_assignments = assignments_by_shift.get(shift.id, [])
                    shift_data = {
                        'id': str(shift.id),
                        'start_time': shift.time_range.start.isoformat(),
                        'end_time': shift.time_range.end.isoformat(),
                        'shift_type': shift.shift_type.value,
                        'department': getattr(shift, 'department', 'Unknown'),
                        'is_assigned': len(shift_assignments) > 0,
                        'assignments': [
                            {
                                'id': str(assignment.id),
                                'employee_id': str(assignment.employee_id),
                                'assigned_at': assignment.assigned_at.isoformat(),
                                'status': assignment.status.value
                            }
                            for assignment in shift_assignments
                        ]
                    }
                    
                    if query.include_unassigned or shift_data['is_assigned']:
                        schedule_data['shifts'].append(shift_data)
                
                return QueryResult(
                    success=True,
                    data=schedule_data,
                    message=f"Retrieved schedule for {len(schedule_data['shifts'])} shifts"
                )
                
        except Exception as e:
            return QueryResult(
                success=False,
                message=f"Failed to retrieve schedule: {str(e)}",
                errors=[str(e)]
            )


class GetEmployeeAvailabilityQueryHandler(QueryHandler):
    """Handler for GetEmployeeAvailabilityQuery."""
    
    async def handle(self, query: GetEmployeeAvailabilityQuery) -> QueryResult:
        """Handle employee availability retrieval."""
        try:
            async with self.uow:
                # Get employee
                employee = await self.uow.employees.find_by_id(query.employee_id)
                if not employee:
                    return QueryResult(
                        success=False,
                        message=f"Employee {query.employee_id} not found",
                        errors=[f"Employee {query.employee_id} not found"]
                    )
                
                availability_data = {
                    'employee_id': str(query.employee_id),
                    'employee_name': employee.name,
                    'date_range': {
                        'start': query.date_range.start.isoformat(),
                        'end': query.date_range.end.isoformat()
                    },
                    'availability_periods': [],
                    'assignments': [],
                    'leave_requests': []
                }
                
                # Get assignments if requested
                if query.include_assignments:
                    # Convert DateRange to TimeRange
                    time_range_start = datetime.combine(query.date_range.start, datetime.min.time())
                    time_range_end = datetime.combine(query.date_range.end, datetime.max.time())
                    from domain.value_objects import TimeRange
                    query_time_range = TimeRange(time_range_start, time_range_end)
                    
                    assignments = await self.uow.assignments.find_by_employee_and_date_range(
                        query.employee_id, query_time_range
                    )
                    
                    availability_data['assignments'] = [
                        {
                            'id': str(assignment.id),
                            'shift_id': str(assignment.shift_id),
                            'start_time': assignment.shift.time_range.start.isoformat() if assignment.shift else None,
                            'end_time': assignment.shift.time_range.end.isoformat() if assignment.shift else None,
                            'status': assignment.status.value
                        }
                        for assignment in assignments
                    ]
                
                # Get leave requests if requested
                if query.include_leave:
                    # Convert DateRange to TimeRange
                    time_range_start = datetime.combine(query.date_range.start, datetime.min.time())
                    time_range_end = datetime.combine(query.date_range.end, datetime.max.time())
                    from domain.value_objects import TimeRange
                    query_time_range = TimeRange(time_range_start, time_range_end)
                    
                    leave_requests = await self.uow.leave_requests.find_by_employee_and_date_range(
                        query.employee_id, query_time_range
                    )
                    
                    availability_data['leave_requests'] = [
                        {
                            'start_date': leave['start_date'],
                            'end_date': leave['end_date'],
                            'leave_type': leave['leave_type'],
                            'status': leave['status']
                        }
                        for leave in leave_requests
                    ]
                
                return QueryResult(
                    success=True,
                    data=availability_data,
                    message=f"Retrieved availability for employee {query.employee_id}"
                )
                
        except Exception as e:
            return QueryResult(
                success=False,
                message=f"Failed to retrieve employee availability: {str(e)}",
                errors=[str(e)]
            )


class GetUnassignedShiftsQueryHandler(QueryHandler):
    """Handler for GetUnassignedShiftsQuery."""
    
    async def handle(self, query: GetUnassignedShiftsQuery) -> QueryResult:
        """Handle unassigned shifts retrieval."""
        try:
            async with self.uow:
                # Convert DateRange to TimeRange
                time_range_start = datetime.combine(query.date_range.start, datetime.min.time())
                time_range_end = datetime.combine(query.date_range.end, datetime.max.time())
                from domain.value_objects import TimeRange
                query_time_range = TimeRange(time_range_start, time_range_end)
                
                # Get unassigned shifts
                unassigned_shifts = await self.uow.shifts.find_unassigned_in_range(query_time_range)
                
                # Filter by departments if specified
                if query.department_ids:
                    unassigned_shifts = [
                        shift for shift in unassigned_shifts
                        if getattr(shift, 'department', None) in query.department_ids
                    ]
                
                # Filter by shift types if specified
                if query.shift_types:
                    unassigned_shifts = [
                        shift for shift in unassigned_shifts
                        if shift.shift_type in query.shift_types
                    ]
                
                shifts_data = {
                    'date_range': {
                        'start': query.date_range.start.isoformat(),
                        'end': query.date_range.end.isoformat()
                    },
                    'unassigned_shifts': [
                        {
                            'id': str(shift.id),
                            'start_time': shift.time_range.start.isoformat(),
                            'end_time': shift.time_range.end.isoformat(),
                            'shift_type': shift.shift_type.value,
                            'department': getattr(shift, 'department', 'Unknown'),
                            'required_skills': getattr(shift, 'required_skills', []),
                            'priority': getattr(shift, 'priority', 'normal')
                        }
                        for shift in unassigned_shifts
                    ],
                    'summary': {
                        'total_unassigned': len(unassigned_shifts),
                        'by_shift_type': {},
                        'by_department': {}
                    }
                }
                
                # Calculate summary statistics
                for shift in unassigned_shifts:
                    shift_type = shift.shift_type.value
                    department = getattr(shift, 'department', 'Unknown')
                    
                    if shift_type not in shifts_data['summary']['by_shift_type']:
                        shifts_data['summary']['by_shift_type'][shift_type] = 0
                    shifts_data['summary']['by_shift_type'][shift_type] += 1
                    
                    if department not in shifts_data['summary']['by_department']:
                        shifts_data['summary']['by_department'][department] = 0
                    shifts_data['summary']['by_department'][department] += 1
                
                return QueryResult(
                    success=True,
                    data=shifts_data,
                    message=f"Retrieved {len(unassigned_shifts)} unassigned shifts"
                )
                
        except Exception as e:
            return QueryResult(
                success=False,
                message=f"Failed to retrieve unassigned shifts: {str(e)}",
                errors=[str(e)]
            )


class GetFairnessReportQueryHandler(QueryHandler):
    """Handler for GetFairnessReportQuery."""
    
    def __init__(self, uow: 'UnitOfWork', fairness_calculator):
        super().__init__(uow)
        self.fairness_calculator = fairness_calculator
    
    async def handle(self, query: GetFairnessReportQuery) -> QueryResult:
        """Handle fairness report retrieval."""
        try:
            async with self.uow:
                # Import here to avoid circular dependencies
                from ..repositories import EmployeeQuery
                
                # Get employees for analysis
                employee_query = EmployeeQuery(
                    active_only=True,
                    department_ids=query.department_ids
                )
                employees = await self.uow.employees.find_all(employee_query)
                
                fairness_data = {
                    'date_range': {
                        'start': query.date_range.start.isoformat(),
                        'end': query.date_range.end.isoformat()
                    },
                    'employee_fairness': [],
                    'summary': {
                        'total_employees': len(employees),
                        'average_fairness': 0.0,
                        'fairness_variance': 0.0,
                        'most_unfair': None,
                        'most_fair': None
                    }
                }
                
                fairness_scores = []
                
                # Calculate fairness for each employee
                for employee in employees:
                    # Convert DateRange to TimeRange for assignment query
                    time_range_start = datetime.combine(query.date_range.start, datetime.min.time())
                    time_range_end = datetime.combine(query.date_range.end, datetime.max.time())
                    from domain.value_objects import TimeRange
                    query_time_range = TimeRange(time_range_start, time_range_end)
                    
                    assignments = await self.uow.assignments.find_by_employee_and_date_range(
                        employee.id, query_time_range
                    )
                    
                    fairness_result = self.fairness_calculator.calculate_employee_fairness(
                        employee, assignments, query.date_range
                    )
                    
                    employee_fairness = {
                        'employee_id': str(employee.id),
                        'employee_name': employee.name,
                        'total_score': fairness_result.total_score,
                        'incidents_score': fairness_result.incidents_score,
                        'incidents_standby_score': fairness_result.incidents_standby_score,
                        'waakdienst_score': fairness_result.waakdienst_score,
                        'assignment_count': len(assignments)
                    }
                    
                    fairness_data['employee_fairness'].append(employee_fairness)
                    fairness_scores.append(fairness_result.total_score)
                
                # Calculate summary statistics
                if fairness_scores:
                    fairness_data['summary']['average_fairness'] = sum(fairness_scores) / len(fairness_scores)
                    
                    if len(fairness_scores) > 1:
                        import statistics
                        fairness_data['summary']['fairness_variance'] = statistics.variance(fairness_scores)
                    
                    # Find most/least fair employees
                    min_score = min(fairness_scores)
                    max_score = max(fairness_scores)
                    
                    for emp_fairness in fairness_data['employee_fairness']:
                        if emp_fairness['total_score'] == min_score:
                            fairness_data['summary']['most_fair'] = emp_fairness['employee_id']
                        if emp_fairness['total_score'] == max_score:
                            fairness_data['summary']['most_unfair'] = emp_fairness['employee_id']
                
                return QueryResult(
                    success=True,
                    data=fairness_data,
                    message=f"Generated fairness report for {len(employees)} employees"
                )
                
        except Exception as e:
            return QueryResult(
                success=False,
                message=f"Failed to generate fairness report: {str(e)}",
                errors=[str(e)]
            )


# Export query handlers
__all__ = [
    'QueryError',
    'Query',
    'GetScheduleQuery',
    'GetEmployeeAvailabilityQuery',
    'GetUnassignedShiftsQuery',
    'GetFairnessReportQuery',
    'GetConflictAnalysisQuery',
    'GetCoverageAnalysisQuery',
    'QueryResult',
    'QueryHandler',
    'GetScheduleQueryHandler',
    'GetEmployeeAvailabilityQueryHandler',
    'GetUnassignedShiftsQueryHandler',
    'GetFairnessReportQueryHandler'
]
