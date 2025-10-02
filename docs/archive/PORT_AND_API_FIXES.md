# Port Configuration and API Endpoint Fixes

**Date**: October 1, 2025  
**Status**: ✅ Complete

## Issues Resolved

### 1. Port Configuration (3001 → 3000)

**Problem**: 
- Frontend was mapped to external port 3001, user preferred port 3000
- Vite config still had port 3001 hardcoded
- WebSocket HMR failing when accessing via external IP (10.0.10.41)

**Solution**:
- Updated `docker-compose.yml`: Changed `ports: "3001:3000"` → `"3000:3000"`
- Updated `frontend/vite.config.ts`: Changed `port: 3001` → `port: 3000`
- Added HMR configuration for external access:
  ```typescript
  hmr: {
    host: '10.0.10.41',
    port: 3000,
    protocol: 'ws',
  }
  ```

### 2. Team Member API Endpoints

**Problem**:
- Frontend was trying to use REST-style nested routes: `/api/teams/{id}/members/`
- Backend uses DRF action endpoints: `/api/teams/{id}/add_member/` and `/api/teams/{id}/remove_member/`
- Resulted in 404 errors when adding/removing team members

**Backend Endpoints** (from `team_planner/teams/api_views.py`):
```python
@action(detail=True, methods=["post"])
def add_member(self, request, pk=None):
    # Expects: { "user_id": int, "role": str, "fte": float }
    
@action(detail=True, methods=["delete"])
def remove_member(self, request, pk=None):
    # Expects: { "user_id": int }
```

**Solutions Applied**:

**Add Member** (`UnifiedManagement.tsx` line ~342):
```typescript
// Before:
await apiClient.post(`/api/teams/${selectedTeam.id}/members/`, {...})

// After:
await apiClient.post(`/api/teams/${selectedTeam.id}/add_member/`, {
  user_id: parseInt(selectedUserId),
  role: selectedMemberRole,
});
```

**Remove Member** (`UnifiedManagement.tsx` line ~401):
```typescript
// Before:
await apiClient.delete(`/api/teams/${teamId}/members/${memberId}/`)

// After:
await apiClient.delete(`/api/teams/${teamId}/remove_member/`, {
  data: { user_id: memberId }
});
```

## Files Modified

1. **docker-compose.yml**
   - Changed frontend port mapping

2. **frontend/vite.config.ts**
   - Updated port from 3001 to 3000
   - Added HMR configuration for external IP access
   - Added `strictPort: true` for consistency

3. **frontend/src/pages/UnifiedManagement.tsx**
   - Fixed `handleSaveTeamMember()` to use `/add_member/` endpoint
   - Fixed `handleRemoveMember()` to use `/remove_member/` endpoint with proper data format

## Testing

### Access URLs:
- **Frontend**: http://10.0.10.41:3000
- **Backend**: http://10.0.10.41:8000
- **Management Page**: http://10.0.10.41:3000/management

### Verification Steps:
1. ✅ Frontend accessible on port 3000
2. ✅ WebSocket HMR connection working (no console warnings)
3. ⏳ Team member add/remove functionality (ready to test)
4. ⏳ Department CRUD operations (ready to test)

## Next Steps

1. **Test Team Management**:
   - Create a department
   - Create a team with that department
   - Add members to the team
   - Remove members from the team
   - Verify all operations succeed

2. **Test Department Management**:
   - Create departments
   - Edit department details
   - Delete departments
   - Verify manager assignment works

3. **Verify RBAC**:
   - Test with different user roles
   - Ensure permission checks work correctly
   - Verify unauthorized users see appropriate errors

## Technical Notes

### Docker Port Mapping
- External (host): `0.0.0.0:3000`
- Internal (container): `3000`
- Vite server binds to: `0.0.0.0:3000` (all interfaces)

### Vite Proxy Configuration
The proxy is correctly configured to forward API requests:
- `/api/*` → `http://django:8000`
- `/shifts/api/*` → `http://django:8000`
- `/orchestrators/api/*` → `http://django:8000`

### API Client Configuration
- Uses empty `BASE_URL: ''` to rely on Vite proxy
- Token authentication via localStorage
- Requests made to relative paths (e.g., `/api/teams/`)

## Lessons Learned

1. **Port Consistency**: When changing Docker port mappings, also check application configs (Vite, etc.)
2. **API Contracts**: Always verify backend endpoint patterns (REST vs Actions) before implementing frontend calls
3. **HMR Configuration**: For external network access, HMR needs explicit host configuration
4. **DRF Actions**: Django REST Framework custom actions use different URL patterns than nested routes
