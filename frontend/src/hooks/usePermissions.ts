import { useState, useEffect, useCallback } from 'react';
import { apiClient } from '../services/apiClient';

export interface UserPermissions {
  role: string;
  role_display: string;
  permissions: {
    // Shift Management
    can_view_own_shifts: boolean;
    can_view_team_shifts: boolean;
    can_view_all_shifts: boolean;
    can_create_shifts: boolean;
    can_edit_own_shifts: boolean;
    can_edit_team_shifts: boolean;
    can_delete_shifts: boolean;
    
    // Swap Management
    can_request_swap: boolean;
    can_approve_swap: boolean;
    can_view_all_swaps: boolean;
    
    // Leave Management
    can_request_leave: boolean;
    can_approve_leave: boolean;
    can_view_team_leave: boolean;
    
    // Orchestrator
    can_run_orchestrator: boolean;
    can_override_fairness: boolean;
    can_manual_assign: boolean;
    
    // Team Management
    can_manage_team: boolean;
    can_view_team_analytics: boolean;
    
    // Reports & Analytics
    can_view_reports: boolean;
    can_export_data: boolean;
    
    // System Administration
    can_manage_users: boolean;
    can_assign_roles: boolean;
  };
}

interface UsePermissionsReturn {
  permissions: UserPermissions | null;
  loading: boolean;
  error: string | null;
  hasPermission: (permission: keyof UserPermissions['permissions']) => boolean;
  hasAnyPermission: (permissions: Array<keyof UserPermissions['permissions']>) => boolean;
  hasAllPermissions: (permissions: Array<keyof UserPermissions['permissions']>) => boolean;
  isRole: (role: string) => boolean;
  refresh: () => Promise<void>;
}

let permissionsCache: UserPermissions | null = null;
let cacheTimestamp: number = 0;
const CACHE_DURATION = 5 * 60 * 1000; // 5 minutes

export const usePermissions = (): UsePermissionsReturn => {
  const [permissions, setPermissions] = useState<UserPermissions | null>(permissionsCache);
  const [loading, setLoading] = useState<boolean>(!permissionsCache);
  const [error, setError] = useState<string | null>(null);

  const fetchPermissions = useCallback(async (force: boolean = false) => {
    const now = Date.now();
    
    // Use cache if available and not expired
    if (!force && permissionsCache && (now - cacheTimestamp) < CACHE_DURATION) {
      setPermissions(permissionsCache);
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const data = await apiClient.get<UserPermissions>('/api/users/me/permissions/');
      permissionsCache = data;
      cacheTimestamp = now;
      setPermissions(data);
    } catch (err: any) {
      const errorMessage = err.message || 'Failed to fetch permissions';
      setError(errorMessage);
      console.error('Permissions fetch error:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchPermissions();
  }, [fetchPermissions]);

  const hasPermission = useCallback(
    (permission: keyof UserPermissions['permissions']): boolean => {
      if (!permissions) return false;
      return permissions.permissions[permission] === true;
    },
    [permissions]
  );

  const hasAnyPermission = useCallback(
    (perms: Array<keyof UserPermissions['permissions']>): boolean => {
      if (!permissions) return false;
      return perms.some(perm => permissions.permissions[perm] === true);
    },
    [permissions]
  );

  const hasAllPermissions = useCallback(
    (perms: Array<keyof UserPermissions['permissions']>): boolean => {
      if (!permissions) return false;
      return perms.every(perm => permissions.permissions[perm] === true);
    },
    [permissions]
  );

  const isRole = useCallback(
    (role: string): boolean => {
      if (!permissions) return false;
      return permissions.role.toLowerCase() === role.toLowerCase();
    },
    [permissions]
  );

  const refresh = useCallback(async () => {
    await fetchPermissions(true);
  }, [fetchPermissions]);

  return {
    permissions,
    loading,
    error,
    hasPermission,
    hasAnyPermission,
    hasAllPermissions,
    isRole,
    refresh,
  };
};

// Clear cache on logout
export const clearPermissionsCache = () => {
  permissionsCache = null;
  cacheTimestamp = 0;
};
