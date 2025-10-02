# RBAC Integration Visual Guide

## Before & After: Navigation Menu

### Before (Role-based only on is_staff flag)
```
All Staff Users See:
├── Dashboard
├── Calendar
├── Timeline
├── Orchestrator          ← Visible to ALL staff
├── Fairness Dashboard    ← Visible to ALL staff
├── User Management       ← Visible to ALL staff
├── Team Management       ← Visible to ALL staff
├── Profile
├── Shift Swaps
├── Leave Requests
└── Settings

All Employees See:
├── Dashboard
├── Calendar
├── Timeline
├── Profile
├── Shift Swaps
├── Leave Requests
└── Settings
```

### After (RBAC Permissions)
```
Admin Sees:
├── Dashboard
├── Calendar               [can_view_schedule]
├── Timeline               [can_view_schedule]
├── Orchestrator           [can_run_orchestrator]
├── Fairness Dashboard     [can_view_analytics + can_view_schedule]
├── User Management        [can_manage_users]
├── Team Management        [can_manage_teams]
├── Role Management        [can_assign_roles] ← NEW!
├── Profile
├── Shift Swaps
├── Leave Requests
└── Settings

Manager Sees:
├── Dashboard
├── Calendar               [can_view_schedule]
├── Timeline               [can_view_schedule]
├── Orchestrator           [can_run_orchestrator]
├── Fairness Dashboard     [can_view_analytics + can_view_schedule]
├── Team Management        [can_manage_teams]
├── Profile
├── Shift Swaps
├── Leave Requests
└── Settings

Scheduler Sees:
├── Dashboard
├── Calendar               [can_view_schedule]
├── Timeline               [can_view_schedule]
├── Orchestrator           [can_run_orchestrator]
├── Fairness Dashboard     [can_view_analytics + can_view_schedule]
├── Profile
├── Shift Swaps
├── Leave Requests
└── Settings

Team Lead Sees:
├── Dashboard
├── Calendar               [can_view_schedule]
├── Timeline               [can_view_schedule]
├── Profile
├── Shift Swaps
├── Leave Requests
└── Settings

Employee Sees:
├── Dashboard
├── Calendar               [can_view_schedule]
├── Timeline               [can_view_schedule]
├── Profile
├── Shift Swaps
├── Leave Requests
└── Settings
```

## Before & After: Calendar Page

### Before
```typescript
// No permission checks
const handleDateSelect = (info: DateSelectArg) => {
  const newShift = confirm(`Create new shift for ${formatDate(info.start)}?`);
  if (newShift) {
    console.log('Creating new shift...');
  }
};
```

**Result:** ALL users could attempt to create shifts

### After
```typescript
const { hasPermission } = usePermissions();

const handleDateSelect = (info: DateSelectArg) => {
  if (!hasPermission('can_create_shifts')) {
    alert('You do not have permission to create shifts.');
    return;
  }
  
  const newShift = confirm(`Create new shift for ${formatDate(info.start)}?`);
  if (newShift) {
    console.log('Creating new shift...');
  }
};
```

**Result:** Only schedulers/managers/admins can create shifts

## Before & After: Shift Swaps Page

### Before
```tsx
{swap.status === 'pending' && showRequester && (
  <Box sx={{ display: 'flex', gap: 1 }}>
    <Button onClick={() => handleResponseOpen(swap, 'approve')}>
      Approve
    </Button>
    <Button onClick={() => handleResponseOpen(swap, 'reject')}>
      Reject
    </Button>
  </Box>
)}
```

**Result:** ALL staff could see approve/reject buttons (based on is_staff)

### After
```tsx
{swap.status === 'pending' && showRequester && (
  <Box sx={{ display: 'flex', gap: 1 }}>
    {hasPermission('can_approve_swap') && (
      <Button onClick={() => handleResponseOpen(swap, 'approve')}>
        Approve
      </Button>
    )}
    {hasPermission('can_reject_swap') && (
      <Button onClick={() => handleResponseOpen(swap, 'reject')}>
        Reject
      </Button>
    )}
  </Box>
)}
```

**Result:** Only team leads/schedulers/managers/admins see buttons

## Before & After: Leave Request Page

### Before
```typescript
const canApprove = (leaveRequest: LeaveRequest): boolean => {
  return (
    user?.permissions?.includes('leaves.change_leaverequest') ||
    user?.is_staff ||
    false
  ) && leaveRequest.status === 'pending';
};
```

**Issues:**
- Mixed Django permissions and is_staff
- Inconsistent with RBAC system
- Hard to maintain

### After
```typescript
const { hasPermission } = usePermissions();

const canApprove = (leaveRequest: LeaveRequest): boolean => {
  return (
    hasPermission('can_approve_leave') && 
    leaveRequest.status === 'pending'
  );
};
```

**Benefits:**
- Clean, consistent pattern
- Uses RBAC permission system
- Easy to understand and maintain

## Permission Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                      User Logs In                            │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│              Backend: /api/users/me/permissions/             │
│                                                               │
│  Returns:                                                     │
│  {                                                            │
│    role: "scheduler",                                         │
│    role_display: "Scheduler",                                 │
│    permissions: {                                             │
│      can_create_shifts: true,                                 │
│      can_edit_shifts: true,                                   │
│      can_approve_swap: true,                                  │
│      ...                                                      │
│    }                                                          │
│  }                                                            │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│           Frontend: usePermissions Hook                      │
│                                                               │
│  - Caches permissions for 5 minutes                          │
│  - Provides helper functions:                                │
│    • hasPermission(name)                                     │
│    • hasAnyPermission([...])                                 │
│    • hasAllPermissions([...])                                │
│    • isRole(name)                                            │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                  Component Usage                             │
│                                                               │
│  Navigation:                                                  │
│    navigationService.getNavigationItems(user)                │
│    → Filters menu items by permissions                       │
│                                                               │
│  Calendar:                                                    │
│    if (hasPermission('can_create_shifts'))                   │
│    → Shows create shift dialog                               │
│                                                               │
│  Swaps:                                                       │
│    {hasPermission('can_approve_swap') && <ApproveButton/>}   │
│    → Shows approve button                                    │
│                                                               │
│  Leaves:                                                      │
│    if (hasPermission('can_approve_leave'))                   │
│    → Shows approve icon                                      │
└─────────────────────────────────────────────────────────────┘
```

## Code Patterns

### Pattern 1: Conditional Rendering

```typescript
// Show/hide entire component
{hasPermission('can_create_shifts') && (
  <Button onClick={handleCreate}>
    Create Shift
  </Button>
)}
```

### Pattern 2: Permission Guard

```typescript
// Check permission before action
const handleAction = () => {
  if (!hasPermission('can_edit_shifts')) {
    alert('You do not have permission to edit shifts.');
    return;
  }
  
  // Proceed with action
  performEdit();
};
```

### Pattern 3: Multiple Permissions (ANY)

```typescript
// User needs ANY of the permissions
{hasAnyPermission(['can_approve_swap', 'can_reject_swap']) && (
  <ActionMenu />
)}
```

### Pattern 4: Multiple Permissions (ALL)

```typescript
// User needs ALL of the permissions
{hasAllPermissions(['can_view_schedule', 'can_view_analytics']) && (
  <FairnessDashboard />
)}
```

### Pattern 5: Role Check

```typescript
// Check user's role
{isRole('admin') && (
  <AdminOnlyFeature />
)}

// Check multiple roles
{(isRole('admin') || isRole('manager')) && (
  <ManagementFeature />
)}
```

## Testing Scenarios

### Scenario 1: Employee User
**Setup:**
```
Role: Employee
Permissions: Basic viewing + request actions
```

**Expected Behavior:**
```
✅ Can view Dashboard
✅ Can view Calendar
✅ Can view Timeline
✅ Can create Shift Swap requests
✅ Can create Leave requests
❌ Cannot see Orchestrator in menu
❌ Cannot see User Management in menu
❌ Cannot see Team Management in menu
❌ Cannot see Role Management in menu
❌ Cannot create shifts (calendar date selection blocked)
❌ Cannot approve swap requests (buttons hidden)
❌ Cannot reject swap requests (buttons hidden)
❌ Cannot approve leave requests (buttons hidden)
❌ Cannot reject leave requests (buttons hidden)
```

### Scenario 2: Team Lead User
**Setup:**
```
Role: Team Lead
Permissions: Employee permissions + team approvals
```

**Expected Behavior:**
```
✅ All Employee permissions
✅ Can see approve/reject buttons on their team's swaps
✅ Can see approve/reject buttons on their team's leaves
❌ Cannot see Orchestrator in menu
❌ Cannot see User Management in menu
❌ Cannot see Team Management in menu (viewing only)
❌ Cannot create shifts
```

### Scenario 3: Scheduler User
**Setup:**
```
Role: Scheduler
Permissions: Employee + Team Lead + shift creation + orchestrator
```

**Expected Behavior:**
```
✅ All Team Lead permissions
✅ Can see Orchestrator in menu
✅ Can create shifts (calendar date selection works)
✅ Can edit shifts
✅ Can approve/reject ALL swaps (not just team)
✅ Can approve/reject ALL leaves (not just team)
✅ Can run orchestrator
❌ Cannot see User Management in menu
❌ Cannot see Team Management in menu
❌ Cannot see Role Management in menu
❌ Cannot delete shifts
```

### Scenario 4: Manager User
**Setup:**
```
Role: Manager
Permissions: All Scheduler + team management + delete shifts
```

**Expected Behavior:**
```
✅ All Scheduler permissions
✅ Can see Team Management in menu
✅ Can delete shifts
✅ Can manage teams (CRUD operations)
❌ Cannot see User Management in menu
❌ Cannot see Role Management in menu
❌ Cannot manage users
❌ Cannot assign roles
```

### Scenario 5: Admin User
**Setup:**
```
Role: Admin
Permissions: ALL permissions
```

**Expected Behavior:**
```
✅ ALL features visible
✅ Can see User Management in menu
✅ Can see Role Management in menu
✅ Can manage users (activate, deactivate, edit)
✅ Can assign roles to users
✅ Can perform ALL actions
```

## Browser Testing Checklist

For each role, verify:

### Navigation Menu
- [ ] Correct items visible
- [ ] Correct items hidden
- [ ] Navigation items are clickable
- [ ] Active item highlighted correctly

### Calendar Page
- [ ] Can view shifts (all roles)
- [ ] Date selection blocked for employees/team leads
- [ ] Date selection works for schedulers+
- [ ] Permission denied message shows correctly

### Shift Swaps Page
- [ ] Can view all swaps (all roles)
- [ ] Can create swap requests (all roles)
- [ ] Approve/reject buttons hidden for employees
- [ ] Approve/reject buttons visible for team leads+
- [ ] Buttons functional when visible

### Leave Requests Page
- [ ] Can view all requests (all roles)
- [ ] Can create leave requests (all roles)
- [ ] Approve/reject icons hidden for employees
- [ ] Approve/reject icons visible for team leads+
- [ ] Icons functional when visible

## Performance Notes

### Permission Caching
- Permissions fetched once on login
- Cached for 5 minutes
- Cached cleared on logout
- Manual refresh available

### Network Impact
- Single API call per session (unless cache expires)
- Minimal network overhead
- Fast permission checks (local cache)

### Render Performance
- Conditional rendering is efficient
- No unnecessary re-renders
- React components memoized where needed

## Debugging Tips

### Check User Permissions
```typescript
// In any component
const { permissions } = usePermissions();
console.log('Current permissions:', permissions);
```

### Test Permission Checks
```typescript
// In any component
const { hasPermission } = usePermissions();
console.log('Can create shifts?', hasPermission('can_create_shifts'));
console.log('Can approve swaps?', hasPermission('can_approve_swap'));
```

### Refresh Permissions
```typescript
// Force refresh if permissions changed
const { refreshPermissions } = usePermissions();
await refreshPermissions();
```

### Check Navigation Items
```typescript
// In console
import { navigationService } from './services/navigationService';
const items = navigationService.getNavigationItems(currentUser);
console.log('Visible menu items:', items);
```

## Common Issues & Solutions

### Issue 1: Permission not taking effect
**Cause:** Permission cache not refreshed  
**Solution:** 
```typescript
const { refreshPermissions } = usePermissions();
await refreshPermissions();
```

### Issue 2: Menu item not showing
**Cause:** Incorrect permission name or missing permission  
**Solution:** Check navigation item definition and role permissions in database

### Issue 3: Button visible but shouldn't be
**Cause:** Wrong permission check  
**Solution:** Verify permission name matches backend

### Issue 4: Action blocked but should work
**Cause:** User role not assigned correct permissions  
**Solution:** Update role permissions in database or RoleManagement page

---

**Document Version:** 1.0  
**Last Updated:** October 1, 2025  
**Status:** Living document - update as features evolve
