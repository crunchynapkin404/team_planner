# Leave Conflict Resolution - Backend Complete ✅

**Feature**: Week 9-10 Feature 5: Leave Conflict Resolution  
**Status**: Backend 100% Complete | Frontend 0%  
**Date**: Current Session  
**Backend Endpoints**: 5 new API endpoints  

---

## Overview

The Leave Conflict Resolution feature provides a comprehensive system for:
- Detecting overlapping leave requests (personal and team-wide)
- Analyzing staffing levels during leave periods
- Suggesting alternative dates to avoid conflicts
- Priority-based conflict resolution with manager override
- AI-style recommendations using multiple criteria

---

## Backend Components

### 1. Service Layer: `team_planner/leaves/conflict_service.py`

**LeaveConflictDetector Class** (470 lines)

Provides conflict detection and analysis methods:

#### `detect_overlapping_requests(employee, start_date, end_date, exclude_request_id=None)`
- **Purpose**: Find personal leave overlaps for an employee
- **Returns**: `List[LeaveRequest]` - Overlapping PENDING or APPROVED requests
- **Use Case**: Pre-validation when creating new leave request

#### `detect_team_conflicts(start_date, end_date, team_id=None, department_id=None)`
- **Purpose**: Find team-wide conflicts by day
- **Returns**: Dict with day-by-day analysis:
  ```python
  {
    'conflict_days': [
      {
        'date': '2025-01-15',
        'leave_count': 3,
        'employees_on_leave': [employee_ids...]
      }
    ]
  }
  ```
- **Use Case**: Manager dashboard showing daily conflict levels

#### `analyze_staffing_levels(start_date, end_date, team_id, department_id, min_required_staff=2)`
- **Purpose**: Calculate available staff vs required minimum
- **Returns**: Dict with staffing analysis:
  ```python
  {
    'understaffed_days': [
      {
        'date': '2025-01-15',
        'available_staff': 1,
        'required_staff': 2,
        'shortage': 1
      }
    ],
    'warning_days': [...],  # Close to minimum
    'total_team_size': 5
  }
  ```
- **Use Case**: Staffing level warnings and approvals

#### `suggest_alternative_dates(employee, start_date, days_requested, team_id, department_id, search_window_days=60)`
- **Purpose**: Find better dates with fewer conflicts
- **Returns**: List of top 5 alternatives:
  ```python
  [
    {
      'start_date': '2025-01-20',
      'end_date': '2025-01-24',
      'conflict_score': 0.2,  # Lower is better
      'is_understaffed': False,
      'days_offset': 5  # Days from original
    }
  ]
  ```
- **Use Case**: Help employees find conflict-free dates

#### `get_shift_conflicts(employee, start_date, end_date)`
- **Purpose**: Find scheduled/confirmed shifts during leave
- **Returns**: `List[Shift]` - Conflicting shifts
- **Use Case**: Prevent leave when shifts already assigned

---

**LeaveConflictResolver Class**

Provides priority-based resolution:

#### Priority Rules (Enum)
```python
class Priority(IntEnum):
    SENIORITY = 1          # Earliest date_joined wins
    FIRST_REQUEST = 2      # Earliest created timestamp wins
    LEAVE_BALANCE = 3      # Least leave used this year wins
    ROTATION = 4           # Fair rotation (not yet implemented)
    MANAGER_OVERRIDE = 99  # Manual manager decision
```

#### `resolve_by_priority(conflicting_requests, priority_rule)`
- **Purpose**: Apply single priority rule to select winner
- **Returns**: `Optional[LeaveRequest]` - Request to approve
- **Use Case**: Automated resolution based on policy

#### `apply_resolution(request_to_approve, requests_to_reject, resolved_by, resolution_notes)`
- **Purpose**: Execute approval/rejection with notifications
- **Returns**: Dict with approved/rejected IDs
- **Use Case**: Final resolution execution
- **Features**:
  - Transaction-safe
  - Sends notifications to all affected employees
  - Records resolver and notes

#### `get_recommended_resolution(conflicting_requests)`
- **Purpose**: AI-style recommendation using all rules
- **Returns**: Dict with:
  ```python
  {
    'recommended_request': LeaveRequest,
    'recommendation_details': {
      'seniority': LeaveRequest,
      'first_request': LeaveRequest,
      'leave_balance': LeaveRequest
    },
    'vote_counts': {request_id: vote_count},
    'alternatives': [other_request_ids]
  }
  ```
- **Use Case**: Help managers make informed decisions
- **Algorithm**: Vote-based (most rules recommending = winner)

---

### 2. API Endpoints: `team_planner/leaves/api.py`

**5 New Endpoints Added** (~200 lines)

#### 1. `POST /api/leaves/check-conflicts/`
**Function**: `check_leave_conflicts`  
**Permission**: IsAuthenticated  
**Request Body**:
```json
{
  "employee_id": 1,
  "start_date": "2025-01-15",
  "end_date": "2025-01-19",
  "team_id": 1,  // optional
  "department_id": 1  // optional
}
```
**Response**:
```json
{
  "has_conflicts": true,
  "personal_conflicts": [
    {
      "id": 10,
      "start_date": "2025-01-15",
      "end_date": "2025-01-20",
      "status": "approved"
    }
  ],
  "team_conflicts_by_day": {
    "conflict_days": [...]
  },
  "staffing_analysis": {
    "understaffed_days": [...],
    "warning_days": [...],
    "total_team_size": 5
  },
  "shift_conflicts": [...]
}
```
**Use Case**: Pre-validation before creating leave request

---

#### 2. `POST /api/leaves/suggest-alternatives/`
**Function**: `suggest_alternative_dates`  
**Permission**: IsAuthenticated  
**Request Body**:
```json
{
  "employee_id": 1,
  "start_date": "2025-01-15",
  "days_requested": 5,
  "team_id": 1,  // optional
  "department_id": 1  // optional
}
```
**Response**:
```json
{
  "suggestions": [
    {
      "start_date": "2025-01-20",
      "end_date": "2025-01-26",
      "conflict_score": 0.0,
      "is_understaffed": false,
      "days_offset": 5
    }
  ]
}
```
**Use Case**: Show employees better date options

---

#### 3. `GET /api/leaves/conflicts/`
**Function**: `get_conflicting_requests`  
**Permission**: can_approve_leave (managers only)  
**Query Params**:
- `start_date` (required)
- `end_date` (required)
- `team_id` (optional)
- `department_id` (optional)

**Response**:
```json
{
  "conflict_days": [
    {
      "date": "2025-01-15",
      "leave_count": 3,
      "employees_on_leave": [1, 2, 3]
    }
  ],
  "understaffed_days": [...],
  "warning_days": [...],
  "total_team_size": 5
}
```
**Use Case**: Manager dashboard of all conflicts

---

#### 4. `POST /api/leaves/resolve-conflict/`
**Function**: `resolve_conflict`  
**Permission**: can_approve_leave (managers only)  
**Request Body**:
```json
{
  "approve_request_id": 10,
  "reject_request_ids": [11, 12],
  "resolution_notes": "Approved based on seniority"
}
```
**Response**:
```json
{
  "approved_request_id": 10,
  "rejected_request_ids": [11, 12],
  "resolved_by": "manager@example.com",
  "resolution_notes": "Approved based on seniority"
}
```
**Use Case**: Execute manager's resolution decision

---

#### 5. `POST /api/leaves/recommend-resolution/`
**Function**: `get_resolution_recommendation`  
**Permission**: can_approve_leave (managers only)  
**Request Body**:
```json
{
  "request_ids": [10, 11, 12]
}
```
**Response**:
```json
{
  "recommended_request": {
    "id": 10,
    "employee": "John Smith",
    "start_date": "2025-01-15"
  },
  "recommendation_details": {
    "seniority": {
      "id": 10,
      "reason": "Earliest hire date"
    },
    "first_request": {
      "id": 10,
      "reason": "First to submit"
    },
    "leave_balance": {
      "id": 11,
      "reason": "Least leave used"
    }
  },
  "vote_counts": {
    "10": 2,
    "11": 1,
    "12": 0
  },
  "alternatives": [11, 12]
}
```
**Use Case**: AI-style recommendation for managers

---

### 3. URL Routing: `config/api_router.py`

**5 Routes Added**:
```python
path("leaves/check-conflicts/", leaves_api.check_leave_conflicts, name="leaves-check-conflicts"),
path("leaves/suggest-alternatives/", leaves_api.suggest_alternative_dates, name="leaves-suggest-alternatives"),
path("leaves/conflicts/", leaves_api.get_conflicting_requests, name="leaves-conflicts-list"),
path("leaves/resolve-conflict/", leaves_api.resolve_conflict, name="leaves-resolve-conflict"),
path("leaves/recommend-resolution/", leaves_api.get_resolution_recommendation, name="leaves-recommend-resolution"),
```

**Import Added**:
```python
from team_planner.leaves import api as leaves_api
```

**Decorator Imports Fixed**:
```python
from rest_framework.decorators import action, api_view, permission_classes
```

---

## Testing the Backend

### 1. Check Conflicts (Employee)
```bash
curl -X POST http://localhost:8000/api/leaves/check-conflicts/ \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "employee_id": 1,
    "start_date": "2025-01-15",
    "end_date": "2025-01-19",
    "team_id": 1
  }'
```

### 2. Suggest Alternatives (Employee)
```bash
curl -X POST http://localhost:8000/api/leaves/suggest-alternatives/ \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "employee_id": 1,
    "start_date": "2025-01-15",
    "days_requested": 5,
    "team_id": 1
  }'
```

### 3. Get Conflicts (Manager)
```bash
curl -X GET "http://localhost:8000/api/leaves/conflicts/?start_date=2025-01-15&end_date=2025-01-31&team_id=1" \
  -H "Authorization: Token MANAGER_TOKEN"
```

### 4. Get Recommendation (Manager)
```bash
curl -X POST http://localhost:8000/api/leaves/recommend-resolution/ \
  -H "Authorization: Token MANAGER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "request_ids": [10, 11, 12]
  }'
```

### 5. Resolve Conflict (Manager)
```bash
curl -X POST http://localhost:8000/api/leaves/resolve-conflict/ \
  -H "Authorization: Token MANAGER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "approve_request_id": 10,
    "reject_request_ids": [11, 12],
    "resolution_notes": "Approved based on seniority rule"
  }'
```

---

## Integration Points

### Existing Models Used
- **LeaveRequest**: Core model with status, dates, employee
- **Employee**: For team membership and seniority
- **Team/Department**: For team-based conflict analysis
- **Shift**: For shift conflict detection

### Notification Integration
- Uses existing `NotificationService`
- Sends notifications for:
  - Leave approval
  - Leave rejection
  - Resolution notes included

### Permission Integration
- Uses existing RBAC system
- `can_approve_leave` permission for manager endpoints
- `IsAuthenticated` for employee endpoints

---

## Frontend Tasks (Not Yet Implemented)

### 1. TypeScript Service: `frontend/src/services/leaveConflictService.ts`
```typescript
interface ConflictCheckRequest {
  employee_id: number;
  start_date: string;
  end_date: string;
  team_id?: number;
  department_id?: number;
}

interface AlternativeSuggestion {
  start_date: string;
  end_date: string;
  conflict_score: number;
  is_understaffed: boolean;
  days_offset: number;
}

class LeaveConflictService {
  async checkConflicts(data: ConflictCheckRequest): Promise<ConflictCheckResponse>
  async suggestAlternatives(data: AlternativeRequest): Promise<AlternativeSuggestion[]>
  async getConflicts(params: ConflictParams): Promise<ConflictDashboard>
  async resolveConflict(data: ResolutionRequest): Promise<ResolutionResult>
  async getRecommendation(requestIds: number[]): Promise<Recommendation>
}
```

### 2. UI Components Needed

**ConflictWarningBanner** (Priority 1)
- Location: Leave request form
- Purpose: Show conflicts when employee selects dates
- Features:
  - Real-time conflict checking
  - Personal overlap warnings
  - Team conflict indicators
  - Staffing level warnings

**AlternativeDatesDialog** (Priority 2)
- Location: Leave request form
- Purpose: Display suggested alternative dates
- Features:
  - Top 5 alternatives
  - Conflict scores visualization
  - Days offset indicator
  - One-click date selection

**ConflictResolutionPage** (Priority 3)
- Location: Manager section
- Purpose: Dashboard of all conflicts
- Features:
  - Calendar view of conflicts
  - Understaffed days highlighting
  - Filter by team/department/date range
  - Click to resolve individual conflicts

**ConflictDetailsView** (Priority 4)
- Location: Manager section
- Purpose: Detailed view of specific conflict
- Features:
  - List of conflicting requests
  - Employee details (seniority, leave balance)
  - AI recommendation display
  - Reason breakdown for recommendation

**ResolutionActionsPanel** (Priority 5)
- Location: ConflictDetailsView
- Purpose: Execute resolution
- Features:
  - Approve/reject buttons
  - Resolution notes input
  - Confirmation dialog
  - Notification preview

### 3. UI Integration Points

**Leave Request Form Enhancement**:
- Add conflict checking before submission
- Show ConflictWarningBanner if conflicts detected
- Offer AlternativeDatesDialog button
- Prevent submission if serious conflicts

**Manager Dashboard Enhancement**:
- Add "Conflicts" tab
- Show conflict count badge
- Link to ConflictResolutionPage

**Leave Request List Enhancement**:
- Mark conflicting requests with warning icon
- Show conflict details in tooltip
- Quick resolve button for managers

---

## Configuration

### Priority Rules (Configurable)
The system uses priority rules defined in `LeaveConflictResolver.Priority`:

1. **SENIORITY** (1) - Earliest hire date wins
2. **FIRST_REQUEST** (2) - First submitted wins
3. **LEAVE_BALANCE** (3) - Least leave used wins
4. **ROTATION** (4) - Fair rotation (placeholder)
5. **MANAGER_OVERRIDE** (99) - Manual decision

To change default priority, modify the service or add configuration setting.

### Staffing Minimums
- Default: `min_required_staff = 2`
- Warning threshold: 1 below minimum
- Configurable per team/department (future enhancement)

### Search Window
- Default: 60 days before/after original date
- Configurable in API call: `search_window_days` parameter

---

## Known Limitations

1. **ROTATION Priority Not Implemented**
   - Placeholder in code
   - Would require tracking approval history
   - Future enhancement

2. **No Team-Specific Minimums**
   - Uses global `min_required_staff = 2`
   - Future: Add Team.min_staff_level field

3. **No Partial Day Handling**
   - Assumes full-day leave requests
   - Half-day leave may need special handling

4. **No Role-Based Staffing**
   - Doesn't consider skill requirements
   - Just counts total staff available
   - Future: Add critical role coverage

---

## Files Modified

1. **Created**: `team_planner/leaves/conflict_service.py` (~470 lines)
   - LeaveConflictDetector class (5 methods)
   - LeaveConflictResolver class (3 methods + Priority enum)

2. **Modified**: `team_planner/leaves/api.py` (~200 lines added)
   - 5 new API endpoint functions
   - Added imports: `api_view`, `permission_classes`

3. **Modified**: `config/api_router.py`
   - Added import: `from team_planner.leaves import api as leaves_api`
   - Added 5 URL routes

---

## Validation

✅ **Django Check**: No errors
```bash
System check identified no issues (0 silenced).
```

✅ **Import Chain**: All imports resolve correctly
✅ **URL Routing**: 5 routes properly configured
✅ **Permissions**: RBAC integration complete
✅ **Notifications**: Service integration complete

---

## Next Steps

### Immediate (Complete Feature 5)
1. Create TypeScript service (`leaveConflictService.ts`)
2. Build ConflictWarningBanner component
3. Build AlternativeDatesDialog component
4. Integrate into leave request form
5. Test end-to-end workflow

### Manager Tools
6. Build ConflictResolutionPage
7. Build ConflictDetailsView
8. Build ResolutionActionsPanel
9. Add to manager dashboard
10. Test resolution workflow

### Testing & Documentation
11. Create test suite for conflict detection
12. Create test suite for resolution logic
13. Test all API endpoints
14. Document manager workflow
15. Create user guide

### Week 9-10 Remaining
16. Feature 6: Mobile-Responsive Calendar View

---

## Progress Summary

**Week 9-10 Status**: 4.5/6 features complete (75%)

- ✅ Feature 1: Recurring Shift Patterns (100%)
- ✅ Feature 2: Shift Template Library (100%)
- ✅ Feature 3: Bulk Shift Operations (100%)
- ✅ Feature 4: Advanced Swap Approval Rules (Backend 100%, Frontend 0%)
- 🚧 Feature 5: Leave Conflict Resolution (Backend 100%, Frontend 0%)
- ⏳ Feature 6: Mobile-Responsive Calendar View (0%)

**Lines of Code This Session**: ~670 lines
- Service layer: ~470 lines
- API endpoints: ~200 lines

**API Endpoints**: 95 total (90 before + 5 new)

---

## Developer Notes

### Service Layer Pattern
This feature demonstrates the service layer pattern:
- Models handle data
- Services handle business logic
- API views orchestrate and validate
- Clean separation of concerns

### Vote-Based Recommendation
The `get_recommended_resolution()` uses a voting system:
- Applies all priority rules
- Counts which request wins most often
- Provides transparent reasoning
- Managers can override if needed

### Transaction Safety
The `apply_resolution()` method uses transactions:
- All changes atomic
- Rollback on any error
- Notifications sent after commit
- Prevents partial state

### Future Enhancements
- Add configuration for priority weights
- Add team-specific minimum staffing
- Add role-based coverage requirements
- Add vacation blackout periods
- Add automatic conflict resolution option

---

**Status**: ✅ Backend Complete | Ready for Frontend Implementation
