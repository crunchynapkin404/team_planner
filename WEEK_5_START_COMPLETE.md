# Week 5 Start - Project Cleanup & Permission Decorator Complete

**Date:** October 1, 2025  
**Status:** ✅ Cleanup Complete | ✅ Permission Decorator Ready

---

## 🧹 Project Cleanup Summary

### Problem
The project had **61 markdown documentation files** in the root directory, making it difficult to navigate and find current information.

### Solution
Organized documentation into a clean structure:

**Before:**
```
team_planner/
├── DAILY_PROGRESS_OCT_1_2025.md
├── DAY_1_COMPLETE.md
├── DAY_2_COMPLETION_REPORT.md
├── WEEK_1_SUMMARY.md
├── WEEK_2_COMPLETION_SUMMARY.md
├── RBAC_BACKEND_COMPLETE.md
├── RBAC_FRONTEND_COMPLETE.md
├── MFA_LOGIN_FLOW_FIX.md
├── PAGINATION_FIX.md
├── PORT_AND_API_FIXES.md
└── ... 51 more files
```

**After:**
```
team_planner/
├── README.md                     # Clean project overview ✅
├── PROJECT_ROADMAP.md           # High-level roadmap ✅
├── NEXT_STEPS_ROADMAP.md        # Detailed Week 5-6 guide ✅
├── LICENSE                       # MIT License
└── docs/
    ├── guides/                   # Setup & planning docs
    │   ├── GETTING_STARTED.md
    │   ├── DEPLOYMENT.md
    │   ├── DOCKER_DEPLOYMENT.md
    │   ├── PHASE_1_IMPLEMENTATION_PLAN.md
    │   └── STRATEGIC_ROADMAP.md
    └── archive/                  # Historical progress reports
        ├── WEEK_1_SUMMARY.md
        ├── WEEK_2_COMPLETION_SUMMARY.md
        ├── RBAC_BACKEND_COMPLETE.md
        ├── MFA_LOGIN_FLOW_FIX.md
        └── 50+ other reports
```

### Results
- ✅ Root directory: 4 essential files only
- ✅ Documentation organized by purpose
- ✅ Historical reports preserved in archive
- ✅ Easy to find current status and next steps

---

## 🔐 Permission Decorator Implementation

### File Created
**`team_planner/rbac/decorators.py`** (254 lines)

### Features Implemented

#### 1. Permission Check Helper Function
```python
def check_user_permission(user, permission_name):
    """Check if user has a specific permission based on their role."""
    - Superusers get all permissions
    - Checks user's role in RolePermission model
    - Returns True/False
```

#### 2. Single Permission Decorator
```python
@require_permission('can_view_schedule')
def list(self, request, *args, **kwargs):
    return super().list(request, *args, **kwargs)
```
- Checks authentication
- Verifies single permission
- Returns 403 if unauthorized

#### 3. Any Permission Decorator (OR logic)
```python
@require_any_permission('can_approve_leave', 'can_manage_users')
def approve(self, request, pk=None):
    # Approval logic
```
- User needs at least ONE of the specified permissions
- Useful for operations that multiple roles can perform

#### 4. All Permissions Decorator (AND logic)
```python
@require_all_permissions('can_manage_users', 'can_assign_roles')
def assign_admin_role(self, request, pk=None):
    # Role assignment logic
```
- User needs ALL specified permissions
- Useful for highly privileged operations

#### 5. Method-Based Permission Mapping
```python
@permission_required_method({
    'GET': 'can_view_schedule',
    'POST': 'can_create_shift',
    'PUT': 'can_edit_shift',
    'DELETE': 'can_delete_shift'
})
class ShiftViewSet(viewsets.ModelViewSet):
    ...
```
- Apply different permissions based on HTTP method
- Class-level decorator

### Error Responses

**401 Unauthorized (not authenticated):**
```json
{
  "error": "Authentication required",
  "detail": "You must be logged in to access this resource."
}
```

**403 Forbidden (lacks permission):**
```json
{
  "error": "Permission denied",
  "detail": "You do not have the required permission: can_create_shift",
  "required_permission": "can_create_shift"
}
```

---

## 📋 Next Steps

### Phase 1: Apply to Shift Views (1 hour)
**File:** `team_planner/shifts/api.py`

Apply decorators to ShiftViewSet:
- [ ] `list()` → `@require_permission('can_view_own_shifts')` or `can_view_all_shifts`
- [ ] `create()` → `@require_permission('can_create_shifts')`
- [ ] `update()`/`partial_update()` → `@require_permission('can_edit_own_shifts')`
- [ ] `destroy()` → `@require_permission('can_delete_shifts')`

### Phase 2: Apply to Swap Views (1 hour)
**File:** `team_planner/shifts/api.py` (SwapRequestViewSet)

- [ ] `create()` → `@require_permission('can_request_swap')`
- [ ] `approve()` → `@require_permission('can_approve_swap')`
- [ ] `reject()` → `@require_permission('can_approve_swap')`

### Phase 3: Apply to Leave Views (1 hour)
**File:** `team_planner/leaves/api.py`

- [ ] `create()` → `@require_permission('can_request_leave')`
- [ ] `approve()` → `@require_permission('can_approve_leave')`
- [ ] `reject()` → `@require_permission('can_approve_leave')`

### Phase 4: Apply to Orchestrator Views (30 min)
**File:** `team_planner/orchestrators/api.py`

- [ ] `create()` → `@require_permission('can_run_orchestrator')`
- [ ] Other actions as needed

### Phase 5: Apply to Management Views (30 min)
**Files:** `team_planner/teams/api_views.py`, `team_planner/users/api/*.py`

- [ ] TeamViewSet → `@require_permission('can_manage_team')`
- [ ] DepartmentViewSet → `@require_permission('can_manage_team')`
- [ ] UserViewSet → `@require_permission('can_manage_users')`

### Phase 6: Testing (1-2 hours)
- [ ] Create test users with different roles
- [ ] Test each endpoint with each role
- [ ] Verify 403 errors for unauthorized access
- [ ] Verify successful access for authorized users
- [ ] Write integration tests

---

## 🎯 Success Criteria

### When Phase 1-5 Complete:
- ✅ All API endpoints require authentication
- ✅ Permission checks happen before any operation
- ✅ 403 errors returned for unauthorized access
- ✅ Super Admin can do everything
- ✅ Read-Only users cannot modify anything
- ✅ Employees can only view/request
- ✅ Managers/Planners have appropriate access

### Testing Checklist:
- [ ] Super Admin: Full access to all endpoints
- [ ] Manager: Can approve but not create shifts
- [ ] Shift Planner: Can create/edit shifts and run orchestrator
- [ ] Employee: Can view own schedule and make requests
- [ ] Read-Only: Can only GET endpoints

---

## 🚀 Ready to Apply!

The permission decorator is ready. Let's start applying it to the views!

**First Target:** ShiftViewSet in `team_planner/shifts/api.py`

Would you like me to:
1. Apply permissions to ShiftViewSet
2. Apply permissions to all ViewSets at once
3. Something else?
