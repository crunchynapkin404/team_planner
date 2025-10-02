"""API views for reports."""
from datetime import date, datetime

from django.utils.dateparse import parse_date
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from team_planner.rbac.decorators import require_any_permission

from .services import ReportService


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@require_any_permission('can_run_orchestrator', 'can_manage_team', 'is_superuser')
def schedule_report(request: Request) -> Response:
    """
    Get schedule report for a date range.
    
    Query parameters:
        - start_date: Start date (YYYY-MM-DD)
        - end_date: End date (YYYY-MM-DD)
        - team_id: Filter by team ID
        - department_id: Filter by department ID
    """
    start_date = parse_date(request.query_params.get('start_date', ''))
    end_date = parse_date(request.query_params.get('end_date', ''))
    team_id = request.query_params.get('team_id')
    department_id = request.query_params.get('department_id')
    
    try:
        report_data = ReportService.get_schedule_report(
            start_date=start_date,
            end_date=end_date,
            team_id=int(team_id) if team_id else None,
            department_id=int(department_id) if department_id else None,
        )
        return Response(report_data)
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST,
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@require_any_permission('can_run_orchestrator', 'can_manage_team', 'is_superuser')
def fairness_distribution_report(request: Request) -> Response:
    """
    Get fairness distribution report.
    
    Query parameters:
        - team_id: Filter by team ID
        - start_date: Start date (YYYY-MM-DD)
        - end_date: End date (YYYY-MM-DD)
    """
    team_id = request.query_params.get('team_id')
    start_date = parse_date(request.query_params.get('start_date', ''))
    end_date = parse_date(request.query_params.get('end_date', ''))
    
    try:
        report_data = ReportService.get_fairness_distribution_report(
            team_id=int(team_id) if team_id else None,
            start_date=start_date,
            end_date=end_date,
        )
        return Response(report_data)
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST,
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@require_any_permission('can_approve_leave', 'can_manage_team', 'is_superuser')
def leave_balance_report(request: Request) -> Response:
    """
    Get leave balance report.
    
    Query parameters:
        - employee_id: Filter by employee ID
        - team_id: Filter by team ID
        - year: Filter by year (default: current year)
    """
    employee_id = request.query_params.get('employee_id')
    team_id = request.query_params.get('team_id')
    year_param = request.query_params.get('year')
    
    year = None
    if year_param:
        try:
            year = int(year_param)
        except ValueError:
            return Response(
                {'error': 'Invalid year parameter'},
                status=status.HTTP_400_BAD_REQUEST,
            )
    
    try:
        report_data = ReportService.get_leave_balance_report(
            employee_id=int(employee_id) if employee_id else None,
            team_id=int(team_id) if team_id else None,
            year=year,
        )
        return Response(report_data)
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST,
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@require_any_permission('can_run_orchestrator', 'can_manage_team', 'is_superuser')
def swap_history_report(request: Request) -> Response:
    """
    Get swap history report.
    
    Query parameters:
        - employee_id: Filter by employee ID
        - team_id: Filter by team ID
        - start_date: Start date (YYYY-MM-DD)
        - end_date: End date (YYYY-MM-DD)
    """
    employee_id = request.query_params.get('employee_id')
    team_id = request.query_params.get('team_id')
    start_date = parse_date(request.query_params.get('start_date', ''))
    end_date = parse_date(request.query_params.get('end_date', ''))
    
    try:
        report_data = ReportService.get_swap_history_report(
            employee_id=int(employee_id) if employee_id else None,
            team_id=int(team_id) if team_id else None,
            start_date=start_date,
            end_date=end_date,
        )
        return Response(report_data)
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST,
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@require_any_permission('can_run_orchestrator', 'can_manage_team', 'is_superuser')
def employee_hours_report(request: Request) -> Response:
    """
    Get employee hours worked report.
    
    Query parameters:
        - employee_id: Filter by employee ID
        - team_id: Filter by team ID
        - start_date: Start date (YYYY-MM-DD)
        - end_date: End date (YYYY-MM-DD)
    """
    employee_id = request.query_params.get('employee_id')
    team_id = request.query_params.get('team_id')
    start_date = parse_date(request.query_params.get('start_date', ''))
    end_date = parse_date(request.query_params.get('end_date', ''))
    
    try:
        report_data = ReportService.get_employee_hours_report(
            employee_id=int(employee_id) if employee_id else None,
            team_id=int(team_id) if team_id else None,
            start_date=start_date,
            end_date=end_date,
        )
        return Response(report_data)
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST,
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@require_any_permission('can_run_orchestrator', 'can_manage_team', 'is_superuser')
def weekend_holiday_distribution_report(request: Request) -> Response:
    """
    Get weekend and holiday distribution report.
    
    Query parameters:
        - team_id: Filter by team ID
        - start_date: Start date (YYYY-MM-DD)
        - end_date: End date (YYYY-MM-DD)
    """
    team_id = request.query_params.get('team_id')
    start_date = parse_date(request.query_params.get('start_date', ''))
    end_date = parse_date(request.query_params.get('end_date', ''))
    
    try:
        report_data = ReportService.get_weekend_holiday_distribution_report(
            team_id=int(team_id) if team_id else None,
            start_date=start_date,
            end_date=end_date,
        )
        return Response(report_data)
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST,
        )
