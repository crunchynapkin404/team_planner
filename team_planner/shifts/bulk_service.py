"""
Bulk shift operations service.

This module provides services for performing bulk operations on shifts:
- Bulk create shifts from templates
- Bulk assign employees to shifts
- Bulk modify shift properties (times, status, etc.)
- Bulk delete with validation
- CSV import/export functionality
"""

import csv
import io
from datetime import datetime, time, timedelta
from typing import Any, Dict, List, Optional, Tuple

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from .models import Shift, ShiftTemplate

User = get_user_model()


class BulkOperationError(Exception):
    """Raised when a bulk operation fails validation."""
    pass


class BulkShiftService:
    """Service for bulk shift operations."""
    
    @staticmethod
    def bulk_create_from_template(
        template_id: int,
        date_range: Tuple[datetime, datetime],
        employee_ids: List[int],
        start_time: Optional[time] = None,
        end_time: Optional[time] = None,
        rotation_strategy: str = 'sequential',  # sequential, distribute
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """
        Create multiple shifts from a template over a date range.
        
        Args:
            template_id: Template to use
            date_range: Tuple of (start_date, end_date)
            employee_ids: List of employee IDs to assign
            start_time: Override start time (uses template default if None)
            end_time: Override end time (uses template default if None)
            rotation_strategy: How to assign employees ('sequential' or 'distribute')
            dry_run: If True, validate but don't create
            
        Returns:
            Dict with results summary
        """
        template = ShiftTemplate.objects.get(id=template_id)
        employees = User.objects.filter(id__in=employee_ids)
        
        if not employees.exists():
            raise BulkOperationError("No valid employees provided")
        
        # Use template defaults if times not provided
        use_start_time = start_time or template.default_start_time
        use_end_time = end_time or template.default_end_time
        
        if not use_start_time or not use_end_time:
            raise BulkOperationError("Start and end times must be provided or set in template")
        
        start_date, end_date = date_range
        shifts_to_create = []
        conflicts = []
        
        # Generate dates
        current_date = start_date
        employee_index = 0
        employee_list = list(employees)
        
        while current_date <= end_date:
            # Assign employee based on strategy
            if rotation_strategy == 'sequential':
                employee = employee_list[employee_index % len(employee_list)]
                employee_index += 1
            else:  # distribute
                # For distribute, cycle through all employees before repeating
                employee = employee_list[employee_index % len(employee_list)]
                employee_index += 1
            
            # Create datetime objects
            start_datetime = datetime.combine(current_date, use_start_time)
            end_datetime = datetime.combine(current_date, use_end_time)
            
            # Handle overnight shifts
            if use_end_time < use_start_time:
                end_datetime += timedelta(days=1)
            
            # Make timezone-aware
            start_datetime = timezone.make_aware(start_datetime)
            end_datetime = timezone.make_aware(end_datetime)
            
            # Check for conflicts
            existing_shifts = Shift.objects.filter(
                assigned_employee=employee,
                start_datetime__lt=end_datetime,
                end_datetime__gt=start_datetime,
            )
            
            if existing_shifts.exists():
                conflicts.append({
                    'date': current_date.isoformat(),
                    'employee': employee.username,
                    'employee_id': employee.id,
                    'reason': 'Employee already has a shift in this time period',
                })
            else:
                shifts_to_create.append(Shift(
                    template=template,
                    assigned_employee=employee,
                    start_datetime=start_datetime,
                    end_datetime=end_datetime,
                    status=Shift.Status.SCHEDULED,
                ))
            
            current_date += timedelta(days=1)
        
        result = {
            'template_name': template.name,
            'date_range': f"{start_date.isoformat()} to {end_date.isoformat()}",
            'total_days': (end_date - start_date).days + 1,
            'shifts_to_create': len(shifts_to_create),
            'conflicts': len(conflicts),
            'conflict_details': conflicts,
            'created': 0,
        }
        
        if not dry_run and shifts_to_create:
            with transaction.atomic():
                created_shifts = Shift.objects.bulk_create(shifts_to_create)
                result['created'] = len(created_shifts)
                
                # Increment template usage
                template.usage_count += len(created_shifts)
                template.save(update_fields=['usage_count'])
        
        return result
    
    @staticmethod
    def bulk_assign_employees(
        shift_ids: List[int],
        employee_id: int,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """
        Assign an employee to multiple unassigned or reassign existing shifts.
        
        Args:
            shift_ids: List of shift IDs to reassign
            employee_id: Employee to assign
            dry_run: If True, validate but don't update
            
        Returns:
            Dict with results summary
        """
        employee = User.objects.get(id=employee_id)
        shifts = Shift.objects.filter(id__in=shift_ids)
        
        if not shifts.exists():
            raise BulkOperationError("No valid shifts provided")
        
        conflicts = []
        shifts_to_update = []
        
        for shift in shifts:
            # Check for conflicts with employee's existing shifts
            conflicting_shifts = Shift.objects.filter(
                assigned_employee=employee,
                start_datetime__lt=shift.end_datetime,
                end_datetime__gt=shift.start_datetime,
            ).exclude(id=shift.id)
            
            if conflicting_shifts.exists():
                conflicts.append({
                    'shift_id': shift.id,
                    'date': shift.start_datetime.date().isoformat(),
                    'time': f"{shift.start_datetime.time()} - {shift.end_datetime.time()}",
                    'reason': 'Employee has conflicting shift',
                })
            else:
                shifts_to_update.append(shift)
        
        result = {
            'employee': employee.username,
            'employee_id': employee_id,
            'total_shifts': shifts.count(),
            'shifts_to_update': len(shifts_to_update),
            'conflicts': len(conflicts),
            'conflict_details': conflicts,
            'updated': 0,
        }
        
        if not dry_run and shifts_to_update:
            with transaction.atomic():
                for shift in shifts_to_update:
                    shift.assigned_employee = employee
                    shift.save(update_fields=['assigned_employee'])
                result['updated'] = len(shifts_to_update)
        
        return result
    
    @staticmethod
    def bulk_modify_times(
        shift_ids: List[int],
        new_start_time: Optional[time] = None,
        new_end_time: Optional[time] = None,
        time_offset_minutes: Optional[int] = None,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """
        Modify times for multiple shifts.
        
        Args:
            shift_ids: List of shift IDs to modify
            new_start_time: New start time (optional)
            new_end_time: New end time (optional)
            time_offset_minutes: Offset to add/subtract from current times (optional)
            dry_run: If True, validate but don't update
            
        Returns:
            Dict with results summary
        """
        shifts = Shift.objects.filter(id__in=shift_ids)
        
        if not shifts.exists():
            raise BulkOperationError("No valid shifts provided")
        
        if not any([new_start_time, new_end_time, time_offset_minutes]):
            raise BulkOperationError("Must provide either new times or time offset")
        
        conflicts = []
        shifts_to_update = []
        
        for shift in shifts:
            old_start = shift.start_datetime
            old_end = shift.end_datetime
            
            # Calculate new times
            if time_offset_minutes:
                new_start_dt = old_start + timedelta(minutes=time_offset_minutes)
                new_end_dt = old_end + timedelta(minutes=time_offset_minutes)
            else:
                new_start_dt = datetime.combine(
                    old_start.date(),
                    new_start_time or old_start.time()
                )
                new_end_dt = datetime.combine(
                    old_end.date() if new_end_time and new_end_time >= (new_start_time or old_start.time()) else (old_end.date() + timedelta(days=1)),
                    new_end_time or old_end.time()
                )
                new_start_dt = timezone.make_aware(new_start_dt)
                new_end_dt = timezone.make_aware(new_end_dt)
            
            # Check for conflicts
            conflicting_shifts = Shift.objects.filter(
                assigned_employee=shift.assigned_employee,
                start_datetime__lt=new_end_dt,
                end_datetime__gt=new_start_dt,
            ).exclude(id=shift.id)
            
            if conflicting_shifts.exists():
                conflicts.append({
                    'shift_id': shift.id,
                    'employee': shift.assigned_employee.username,
                    'old_time': f"{old_start.time()} - {old_end.time()}",
                    'new_time': f"{new_start_dt.time()} - {new_end_dt.time()}",
                    'reason': 'Would conflict with existing shift',
                })
            else:
                shift.start_datetime = new_start_dt
                shift.end_datetime = new_end_dt
                shifts_to_update.append(shift)
        
        result = {
            'total_shifts': shifts.count(),
            'shifts_to_update': len(shifts_to_update),
            'conflicts': len(conflicts),
            'conflict_details': conflicts,
            'updated': 0,
        }
        
        if not dry_run and shifts_to_update:
            with transaction.atomic():
                Shift.objects.bulk_update(
                    shifts_to_update,
                    ['start_datetime', 'end_datetime']
                )
                result['updated'] = len(shifts_to_update)
        
        return result
    
    @staticmethod
    def bulk_delete(
        shift_ids: List[int],
        force: bool = False,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """
        Delete multiple shifts with validation.
        
        Args:
            shift_ids: List of shift IDs to delete
            force: If True, skip validation checks
            dry_run: If True, validate but don't delete
            
        Returns:
            Dict with results summary
        """
        shifts = Shift.objects.filter(id__in=shift_ids)
        
        if not shifts.exists():
            raise BulkOperationError("No valid shifts provided")
        
        warnings = []
        shifts_to_delete = []
        
        for shift in shifts:
            # Check if shift is in progress or completed
            if not force and shift.status in [Shift.Status.IN_PROGRESS, Shift.Status.COMPLETED]:
                warnings.append({
                    'shift_id': shift.id,
                    'employee': shift.assigned_employee.username,
                    'date': shift.start_datetime.date().isoformat(),
                    'status': shift.status,
                    'reason': f'Shift is {shift.get_status_display()}',
                })
            else:
                shifts_to_delete.append(shift)
        
        result = {
            'total_shifts': shifts.count(),
            'shifts_to_delete': len(shifts_to_delete),
            'warnings': len(warnings),
            'warning_details': warnings,
            'deleted': 0,
        }
        
        if not dry_run and shifts_to_delete:
            with transaction.atomic():
                delete_count = len(shifts_to_delete)
                Shift.objects.filter(id__in=[s.id for s in shifts_to_delete]).delete()
                result['deleted'] = delete_count
        
        return result
    
    @staticmethod
    def export_to_csv(shift_ids: List[int]) -> str:
        """
        Export shifts to CSV format.
        
        Args:
            shift_ids: List of shift IDs to export
            
        Returns:
            CSV string
        """
        shifts = Shift.objects.filter(id__in=shift_ids).select_related(
            'template', 'assigned_employee'
        )
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            'Shift ID',
            'Template Name',
            'Shift Type',
            'Employee Username',
            'Employee Email',
            'Start Date',
            'Start Time',
            'End Date',
            'End Time',
            'Status',
            'Duration (hours)',
            'Notes',
            'Auto Assigned',
        ])
        
        # Write data
        for shift in shifts:
            writer.writerow([
                shift.id,
                shift.template.name,
                shift.template.get_shift_type_display(),
                shift.assigned_employee.username,
                shift.assigned_employee.email,
                shift.start_datetime.date().isoformat(),
                shift.start_datetime.time().isoformat(),
                shift.end_datetime.date().isoformat(),
                shift.end_datetime.time().isoformat(),
                shift.get_status_display(),
                shift.duration_hours,
                shift.notes,
                shift.auto_assigned,
            ])
        
        return output.getvalue()
    
    @staticmethod
    def import_from_csv(
        csv_content: str,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """
        Import shifts from CSV format.
        
        CSV Format:
        Template Name, Employee Username, Start Date, Start Time, End Date, End Time, Status, Notes
        
        Args:
            csv_content: CSV string content
            dry_run: If True, validate but don't create
            
        Returns:
            Dict with results summary
        """
        input_stream = io.StringIO(csv_content)
        reader = csv.DictReader(input_stream)
        
        errors = []
        shifts_to_create = []
        row_number = 0
        
        for row in reader:
            row_number += 1
            try:
                # Get template
                template = ShiftTemplate.objects.get(name=row['Template Name'])
                
                # Get employee
                employee = User.objects.get(username=row['Employee Username'])
                
                # Parse dates and times
                start_date = datetime.strptime(row['Start Date'], '%Y-%m-%d').date()
                start_time_obj = datetime.strptime(row['Start Time'], '%H:%M:%S').time()
                end_date = datetime.strptime(row['End Date'], '%Y-%m-%d').date()
                end_time_obj = datetime.strptime(row['End Time'], '%H:%M:%S').time()
                
                start_datetime = timezone.make_aware(
                    datetime.combine(start_date, start_time_obj)
                )
                end_datetime = timezone.make_aware(
                    datetime.combine(end_date, end_time_obj)
                )
                
                # Get status
                status = row.get('Status', 'Scheduled').lower()
                status_map = {
                    'scheduled': Shift.Status.SCHEDULED,
                    'confirmed': Shift.Status.CONFIRMED,
                    'in progress': Shift.Status.IN_PROGRESS,
                    'completed': Shift.Status.COMPLETED,
                    'cancelled': Shift.Status.CANCELLED,
                }
                shift_status = status_map.get(status, Shift.Status.SCHEDULED)
                
                shifts_to_create.append(Shift(
                    template=template,
                    assigned_employee=employee,
                    start_datetime=start_datetime,
                    end_datetime=end_datetime,
                    status=shift_status,
                    notes=row.get('Notes', ''),
                ))
                
            except ShiftTemplate.DoesNotExist:
                errors.append({
                    'row': row_number,
                    'error': f"Template '{row.get('Template Name')}' not found",
                })
            except User.DoesNotExist:
                errors.append({
                    'row': row_number,
                    'error': f"Employee '{row.get('Employee Username')}' not found",
                })
            except (ValueError, KeyError) as e:
                errors.append({
                    'row': row_number,
                    'error': f"Invalid data format: {str(e)}",
                })
        
        result = {
            'total_rows': row_number,
            'valid_shifts': len(shifts_to_create),
            'errors': len(errors),
            'error_details': errors,
            'created': 0,
        }
        
        if not dry_run and shifts_to_create:
            with transaction.atomic():
                created_shifts = Shift.objects.bulk_create(shifts_to_create)
                result['created'] = len(created_shifts)
        
        return result
