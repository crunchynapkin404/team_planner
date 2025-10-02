# 🚀 Quick Reference - RBAC System

## Access URLs

| Page | URL | Required Permission |
|------|-----|-------------------|
| **Unified Management** | `/management` | Any management permission |
| Dashboard | `/dashboard` | (none) |
| Calendar | `/calendar` | `can_view_schedule` |
| Shift Swaps | `/swaps` | (none for viewing) |
| Leave Requests | `/leaves` | (none for viewing) |
| Orchestrator | `/orchestrator` | `can_run_orchestrator` |

## Permissions Quick Reference

### 22 Available Permissions

**Shift Management:**
- `can_create_shifts` - Create new shifts
- `can_edit_shifts` - Modify existing shifts  
- `can_delete_shifts` - Delete shifts
- `can_view_all_shifts` - View all shifts (not just own)

**Swap Management:**
- `can_approve_swap` - Approve swap requests
- `can_reject_swap` - Reject swap requests

**Leave Management:**
- `can_approve_leave` - Approve leave requests
- `can_reject_leave` - Reject leave requests

**Team Management:**
- `can_manage_team` - Manage own team
- `can_view_team` - View team information

**User Management:**
- `can_view_users` - View user list
- `can_edit_users` - Edit user information
- `can_manage_users` - Full user CRUD

**Orchestrator:**
- `can_run_orchestrator` - Execute orchestration
- `can_view_orchestrator` - View orchestrator dashboard
- `can_configure_orchestrator` - Configure orchestrator settings

**Reports & Analytics:**
- `can_view_reports` - View reports
- `can_export_data` - Export data
- `can_view_analytics` - View fairness dashboard

**System Administration:**
- `can_manage_departments` - Manage departments
- `can_manage_shifts_types` - Manage shift types
- `can_assign_roles` - Assign roles to users
- `can_manage_settings` - System settings
- `can_manage_teams` - Full team CRUD

## Roles Overview

| Role | Key Permissions | Primary Use Case |
|------|----------------|------------------|
| **Employee** | View schedule, request swaps/leaves | Standard team member |
| **Team Lead** | + Approve team's swaps/leaves | First-level approval |
| **Scheduler** | + Create shifts, run orchestrator | Schedule management |
| **Manager** | + Manage teams, delete shifts | Department management |
| **Admin** | ALL permissions | System administration |

## Code Patterns

### Check Single Permission
```typescript
import { usePermissions } from '../hooks/usePermissions';

const MyComponent = () => {
  const { hasPermission } = usePermissions();
  
  if (hasPermission('can_create_shifts')) {
    // Show create button
  }
};
```

### Check Multiple Permissions (ANY)
```typescript
if (hasAnyPermission(['can_approve_swap', 'can_reject_swap'])) {
  // Show action menu
}
```

### Check Multiple Permissions (ALL)
```typescript
if (hasAllPermissions(['can_view_schedule', 'can_view_analytics'])) {
  // Show combined view
}
```

### Check Role
```typescript
if (isRole('admin')) {
  // Show admin features
}
```

### Hide UI Element
```typescript
import PermissionGate from '../components/auth/PermissionGate';

<PermissionGate permission="can_create_shifts">
  <Button onClick={handleCreate}>Create Shift</Button>
</PermissionGate>
```

### Disable Tab
```typescript
<Tab 
  label="Settings" 
  disabled={!hasPermission('can_manage_settings')}
/>
```

### Protect Function
```typescript
const handleDelete = () => {
  if (!hasPermission('can_delete_shifts')) {
    alert('You do not have permission to delete shifts.');
    return;
  }
  
  // Proceed with delete
  performDelete();
};
```

## Navigation Items & Permissions

```typescript
{
  text: 'Calendar',
  path: '/calendar',
  permission: 'can_view_schedule'
},
{
  text: 'Orchestrator',
  path: '/orchestrator',
  permission: 'can_run_orchestrator'
},
{
  text: 'Management',
  path: '/management',
  permission: ['can_manage_users', 'can_manage_teams', 'can_assign_roles'],
  requiresAny: true // User needs ANY of these
}
```

## Common Tasks

### Add New Permission-Protected Feature

1. **Update Backend** (if needed):
```python
# team_planner/users/models.py
class RolePermission(models.Model):
    can_new_feature = models.BooleanField(default=False)
```

2. **Update Frontend Hook** (if needed):
```typescript
// frontend/src/hooks/usePermissions.ts
export interface UserPermissions {
  permissions: {
    can_new_feature: boolean;
    // ... other permissions
  };
}
```

3. **Add to Navigation**:
```typescript
// frontend/src/services/navigationService.ts
{ 
  text: 'New Feature',
  path: '/new-feature',
  permission: 'can_new_feature'
}
```

4. **Protect Component**:
```typescript
// frontend/src/pages/NewFeature.tsx
import { usePermissions } from '../hooks/usePermissions';

const NewFeature = () => {
  const { hasPermission } = usePermissions();
  
  const handleAction = () => {
    if (!hasPermission('can_new_feature')) {
      alert('No permission');
      return;
    }
    // Do action
  };
  
  return (
    <PermissionGate permission="can_new_feature">
      <Button onClick={handleAction}>Action</Button>
    </PermissionGate>
  );
};
```

### Change User Role

**Via API:**
```bash
curl -X PATCH http://localhost:8000/api/rbac/users/3/role/ \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"role": "manager"}'
```

**Via UI:**
1. Navigate to `/management`
2. Click "Roles" tab
3. Find user in table
4. Click "Change Role"
5. Select new role
6. Save

### Test Permissions

**Browser Console:**
```javascript
// Check current user permissions
fetch('/api/users/me/permissions/', {
  headers: { 'Authorization': 'Token YOUR_TOKEN' }
})
.then(r => r.json())
.then(console.log);
```

**Component:**
```typescript
const { permissions } = usePermissions();
console.log('My permissions:', permissions);
```

## Troubleshooting

### Permission Not Working

**Check:**
1. User has correct role assigned
2. Role has permission enabled in database
3. Permission cache hasn't expired (5 min)
4. Correct permission name used

**Force Refresh:**
```typescript
const { refreshPermissions } = usePermissions();
await refreshPermissions();
```

### Menu Item Not Showing

**Check:**
1. Permission name matches exactly
2. User role has the permission
3. Navigation service has correct permission
4. No typos in permission string

**Debug:**
```typescript
// In navigationService.ts
console.log('Checking access for:', item.text);
console.log('Required permission:', item.permission);
console.log('User has permission:', userService.hasPermission(user, item.permission));
```

### Tab Disabled When It Shouldn't Be

**Check:**
1. Permission check on Tab component
2. User actually has the permission
3. Permission cached correctly

**Debug:**
```typescript
const { hasPermission, permissions } = usePermissions();
console.log('Can manage users:', hasPermission('can_manage_users'));
console.log('All permissions:', permissions);
```

## Docker Commands

```bash
# Check container status
docker-compose ps

# View frontend logs
docker-compose logs -f frontend

# View backend logs  
docker-compose logs -f django

# Restart containers
docker-compose restart

# Rebuild and restart
docker-compose up -d --build

# Stop all
docker-compose down

# Start all
docker-compose up -d
```

## Database Queries

```bash
# Enter Django shell
docker-compose exec django python manage.py shell

# Check user role
from django.contrib.auth import get_user_model
User = get_user_model()
user = User.objects.get(username='admin')
print(user.role)

# Check role permissions
from team_planner.users.models import RolePermission
perms = RolePermission.objects.get(role='admin')
print(perms.__dict__)

# List all users with roles
for user in User.objects.all():
    print(f"{user.username}: {user.role}")
```

## Environment

**Development:**
- Backend: http://localhost:8000
- Frontend: http://localhost:3001
- Admin: http://localhost:8000/admin

**Credentials:**
- Admin: admin / admin123
- Test User: testuser / testpass

**Hot Reload:**
- Frontend: ✅ Automatic (Vite HMR)
- Backend: ✅ Automatic (Django runserver)

## Files to Know

**Backend:**
- `team_planner/users/models.py` - User, RolePermission models
- `team_planner/users/permissions.py` - Permission utilities
- `team_planner/users/api/rbac_views.py` - RBAC API endpoints
- `config/api_router.py` - URL routing

**Frontend:**
- `frontend/src/hooks/usePermissions.ts` - Permission hook
- `frontend/src/components/auth/PermissionGate.tsx` - Gate component
- `frontend/src/components/common/RoleBadge.tsx` - Role display
- `frontend/src/services/navigationService.ts` - Menu filtering
- `frontend/src/pages/UnifiedManagement.tsx` - Management console

**Documentation:**
- `RBAC_PHASE_2_COMPLETE.md` - Complete technical details
- `RBAC_PERMISSIONS_APPLIED.md` - Integration guide
- `RBAC_VISUAL_GUIDE.md` - Visual guide with examples
- `SESSION_COMPLETE_OCT_1_2025.md` - Session summary

---

**Last Updated:** October 1, 2025  
**System Status:** ✅ Fully Operational  
**Test Coverage:** Frontend Complete, Backend Pending
