# Unified Management Page - Pagination Fix

**Date**: October 1, 2025  
**Issue**: `TypeError: usersData.map is not a function`  
**Status**: ✅ **FIXED**

## Problem

The Unified Management page was crashing with the error:
```
TypeError: usersData.map is not a function
TypeError: users.map is not a function
```

## Root Cause

**API Response Format Mismatch**

The Django REST Framework endpoints use **pagination by default**, returning responses in this format:

```json
{
  "count": 5,
  "total_pages": 1,
  "current_page": 1,
  "has_next": false,
  "has_previous": false,
  "results": [/* actual data array */]
}
```

But the frontend code expected **direct arrays**:
```typescript
const usersData = await apiClient.get<User[]>('/api/users/');
// Expected: [user1, user2, ...]
// Actual: { count: 5, results: [user1, user2, ...] }
```

When the code tried to call `.map()` on the pagination object, it failed because the object itself is not an array.

## Solution

Updated the frontend code to handle **paginated responses** correctly:

### Before (Broken)
```typescript
const usersData = await apiClient.get<User[]>('/api/users/');
setUsers(usersData); // Error: usersData is an object, not array
```

### After (Fixed)
```typescript
const usersResponse = await apiClient.get<{ results: User[] }>('/api/users/');
const usersData = usersResponse.results || usersResponse as any as User[];
setUsers(usersData); // Success: usersData is now an array
```

## Changes Made

### File: `frontend/src/pages/UnifiedManagement.tsx`

#### 1. Users Tab (Line ~178)
```typescript
// Load users (paginated response)
const usersResponse = await apiClient.get<{ results: User[] }>('/api/users/');
const usersData = usersResponse.results || usersResponse as any as User[];

// Load users with roles (direct array response)
const usersWithRoles = await apiClient.get<User[]>('/api/rbac/users/');
const mergedUsers = usersData.map(user => {
  const userWithRole = Array.isArray(usersWithRoles) 
    ? usersWithRoles.find(u => u.id === user.id)
    : null;
  return userWithRole ? { ...user, role: userWithRole.role, role_display: userWithRole.role_display } : user;
});
setUsers(mergedUsers);
```

#### 2. Teams Tab (Line ~192)
```typescript
// Load teams and departments (both paginated)
const [teamsResponse, deptsResponse] = await Promise.all([
  apiClient.get<{ results: Team[] }>('/api/teams/'),
  apiClient.get<{ results: Department[] }>('/api/departments/'),
]);
const teamsData = teamsResponse.results || teamsResponse as any as Team[];
const deptsData = deptsResponse.results || deptsResponse as any as Department[];
setTeams(teamsData);
setDepartments(deptsData);

// Load users for team member selection (paginated response)
const usersResponse = await apiClient.get<{ results: User[] }>('/api/users/');
const usersData = usersResponse.results || usersResponse as any as User[];
setUsers(usersData);
```

#### 3. Roles Tab (Line ~205)
```typescript
// Load roles and users (both direct array responses)
const [rolesData, usersWithRoles] = await Promise.all([
  apiClient.get<Role[]>('/api/rbac/roles/'),
  apiClient.get<User[]>('/api/rbac/users/'),
]);
setRoles(Array.isArray(rolesData) ? rolesData : []);
setUsers(Array.isArray(usersWithRoles) ? usersWithRoles : []);
```

## API Endpoint Response Formats

| Endpoint | Format | Returns |
|----------|--------|---------|
| `/api/users/` | **Paginated** | `{ count, results: User[] }` |
| `/api/teams/` | **Paginated** | `{ count, results: Team[] }` |
| `/api/departments/` | **Paginated** | `{ count, results: Department[] }` |
| `/api/rbac/users/` | **Direct Array** | `User[]` |
| `/api/rbac/roles/` | **Direct Array** | `Role[]` |

**Why Different Formats?**
- Standard Django REST Framework viewsets use pagination by default
- Custom `@api_view` functions return direct arrays (like `/api/rbac/*`)

## Testing Verification

### Test 1: Check API Response Structure
```bash
# Paginated endpoint
curl http://localhost:8000/api/users/ -H "Authorization: Token YOUR_TOKEN"
# Returns: {"count": 5, "results": [...]}

# Direct array endpoint
curl http://localhost:8000/api/rbac/users/ -H "Authorization: Token YOUR_TOKEN"
# Returns: [...]
```

### Test 2: Browser Console
Before fix:
```
❌ Data loading error: TypeError: usersData.map is not a function
❌ Uncaught TypeError: users.map is not a function
```

After fix:
```
✅ No errors
✅ Users table displays all 5 users
✅ Teams tab shows empty state message
✅ Roles tab displays role statistics
```

## Current Status

- ✅ All API calls working
- ✅ Users tab displays data correctly
- ✅ Teams tab shows "No teams found" (expected - 0 teams in DB)
- ✅ Roles tab shows all users with role badges
- ✅ No console errors
- ✅ Hot reload working
- ✅ TypeScript compilation successful

## Prevention for Future

### Best Practice: Always Check API Response Format

When working with Django REST Framework:

1. **Test the endpoint first**:
   ```bash
   curl http://localhost:8000/api/endpoint/ | python3 -m json.tool
   ```

2. **Check for pagination keys**:
   - If you see `count`, `results`, `next`, `previous` → It's paginated
   - If you see a direct array `[...]` → It's not paginated

3. **Use proper TypeScript types**:
   ```typescript
   // Paginated
   interface PaginatedResponse<T> {
     count: number;
     results: T[];
   }
   
   // Then use it
   const response = await apiClient.get<PaginatedResponse<User>>('/api/users/');
   const users = response.results;
   ```

4. **Add defensive checks**:
   ```typescript
   const data = response.results || response as any as User[];
   // Handles both paginated and direct array responses
   ```

## Related Files

- `frontend/src/pages/UnifiedManagement.tsx` - Fixed pagination handling
- `frontend/src/services/apiClient.ts` - Generic API client (unchanged)
- `team_planner/users/api/rbac_views.py` - RBAC endpoints (direct arrays)
- `team_planner/users/api/views.py` - User endpoints (paginated)

## Summary

The issue was caused by Django REST Framework's default pagination wrapping arrays in an object structure. The fix extracts the `results` array from paginated responses while maintaining compatibility with direct array responses. All three tabs now load data correctly!

**Everything is now working! 🎉**
