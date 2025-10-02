import React from 'react';
import { usePermissions, UserPermissions } from '../../hooks/usePermissions';
import { CircularProgress, Box, Alert } from '@mui/material';

interface PermissionGateProps {
  children: React.ReactNode;
  permission?: keyof UserPermissions['permissions'];
  permissions?: Array<keyof UserPermissions['permissions']>;
  requireAll?: boolean; // If true, requires all permissions; if false, requires any
  role?: string;
  roles?: string[];
  fallback?: React.ReactNode;
  showLoading?: boolean;
  showError?: boolean;
}

export const PermissionGate: React.FC<PermissionGateProps> = ({
  children,
  permission,
  permissions,
  requireAll = false,
  role,
  roles,
  fallback = null,
  showLoading = false,
  showError = false,
}) => {
  const {
    permissions: userPermissions,
    loading,
    error,
    hasPermission,
    hasAnyPermission,
    hasAllPermissions,
    isRole,
  } = usePermissions();

  if (loading && showLoading) {
    return (
      <Box display="flex" justifyContent="center" p={2}>
        <CircularProgress size={24} />
      </Box>
    );
  }

  if (error && showError) {
    return (
      <Alert severity="error" sx={{ mb: 2 }}>
        {error}
      </Alert>
    );
  }

  // If still loading or error, don't show content
  if (loading || error || !userPermissions) {
    return <>{fallback}</>;
  }

  // Check role-based access
  if (role && !isRole(role)) {
    return <>{fallback}</>;
  }

  if (roles && roles.length > 0) {
    const hasRole = roles.some(r => isRole(r));
    if (!hasRole) {
      return <>{fallback}</>;
    }
  }

  // Check permission-based access
  if (permission && !hasPermission(permission)) {
    return <>{fallback}</>;
  }

  if (permissions && permissions.length > 0) {
    const hasAccess = requireAll
      ? hasAllPermissions(permissions)
      : hasAnyPermission(permissions);
    
    if (!hasAccess) {
      return <>{fallback}</>;
    }
  }

  // User has required permissions/roles
  return <>{children}</>;
};

export default PermissionGate;
