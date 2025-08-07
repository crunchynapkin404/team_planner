# Leave Types Implementation

## Overview
This implementation adds enhanced leave type functionality with different conflict handling behaviors and recurring leave support.

## Leave Type Behaviors

### 1. Vacation
- **Conflict Handling**: `FULL_UNAVAILABLE`
- **Behavior**: Blocks **ALL** shifts (both day shifts 8-17h and waakdienst 18-6h)
- **Use Case**: Employee is completely unavailable during vacation time

### 2. Leave
- **Conflict Handling**: `DAYTIME_ONLY`
- **Behavior**: Blocks only **day shifts** (8-17h), remains available for **waakdienst** (18-6h)
- **Use Case**: Employee has daytime obligations but can still handle night duties

### 3. Training
- **Conflict Handling**: `NO_CONFLICT`
- **Behavior**: Does **NOT** block any shifts
- **Use Case**: Employee can be scheduled during training periods

## New Features

### Time-Based Leave Requests
- **Start Time** and **End Time** fields allow partial day leave
- If times are specified, only overlapping shifts are blocked
- If times are blank, full day conflict rules apply

### Recurring Leave
- **Weekly**: Every week on the same day
- **Monthly**: Same date each month
- **Yearly**: Same date each year
- **End Date**: Specify when recurring pattern should stop
- Automatically creates separate leave request instances

## Technical Implementation

### Backend Changes
- `LeaveType.conflict_handling` field with enum choices
- `LeaveType.start_time` and `end_time` for default times
- `LeaveRequest.is_recurring` and recurrence fields
- Enhanced `get_conflicting_shifts()` logic
- `create_recurring_instances()` method

### Frontend Changes
- Time picker inputs for start/end times
- Recurring leave checkbox and options
- Conditional form fields based on recurring selection
- Updated form validation and submission

## Database Migration
- Migration `0002_add_conflict_handling_and_recurring` applied
- Management command `setup_leave_types` creates default types

## Testing
- Comprehensive test script validates all conflict scenarios
- Confirms vacation blocks all shifts, leave blocks only day shifts
- Verifies recurring leave creates correct instances
- Tests time-based conflict detection

## Usage
1. Admin can configure leave types with different conflict behaviors
2. Employees can request leave with optional time ranges
3. System automatically handles conflicts based on leave type
4. Recurring patterns create multiple instances automatically
5. Approval process respects shift conflicts per leave type

This implementation provides flexible leave management that matches real-world scheduling needs while maintaining system integrity.
