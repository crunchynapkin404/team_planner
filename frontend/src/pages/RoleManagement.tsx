import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Alert,
  CircularProgress,
  Chip,
  Grid,
  Card,
  CardContent,
} from '@mui/material';
import { Shield, Person } from '@mui/icons-material';
import { apiClient } from '../services/apiClient';
import { usePermissions } from '../hooks/usePermissions';
import RoleBadge from '../components/common/RoleBadge';
import PermissionGate from '../components/auth/PermissionGate';

interface User {
  id: number;
  username: string;
  email: string;
  name: string;
  role: string;
  role_display: string;
  permissions: Record<string, boolean>;
}

interface Role {
  value: string;
  label: string;
  description: string;
}

interface RolePermissions {
  role: string;
  role_display: string;
  permissions: Record<string, boolean>;
}

const RoleManagement: React.FC = () => {
  const { hasPermission } = usePermissions();
  const [users, setUsers] = useState<User[]>([]);
  const [roles, setRoles] = useState<Role[]>([]);
  const [rolePermissions, setRolePermissions] = useState<Record<string, RolePermissions>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedUser, setSelectedUser] = useState<User | null>(null);
  const [newRole, setNewRole] = useState<string>('');
  const [dialogOpen, setDialogOpen] = useState(false);
  const [updating, setUpdating] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    setError(null);

    try {
      // Load users with roles
      const usersData = await apiClient.get<{ users: User[] }>('/api/rbac/users/');
      setUsers(usersData.users || []);

      // Load available roles
      const rolesData = await apiClient.get<{ roles: Role[] }>('/api/rbac/roles/');
      setRoles(rolesData.roles || []);

      // Load permissions for each role
      const permissionsMap: Record<string, RolePermissions> = {};
      for (const role of rolesData.roles || []) {
        try {
          const perms = await apiClient.get<RolePermissions>(`/api/rbac/roles/${role.value}/permissions/`);
          permissionsMap[role.value] = perms;
        } catch (err) {
          console.error(`Failed to load permissions for role ${role.value}:`, err);
        }
      }
      setRolePermissions(permissionsMap);
    } catch (err: any) {
      setError(err.message || 'Failed to load data');
      console.error('Data loading error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleEditRole = (user: User) => {
    setSelectedUser(user);
    setNewRole(user.role);
    setDialogOpen(true);
  };

  const handleUpdateRole = async () => {
    if (!selectedUser || !newRole) return;

    setUpdating(true);
    setError(null);

    try {
      await apiClient.patch(`/api/rbac/users/${selectedUser.id}/role/`, {
        role: newRole,
      });

      // Reload data
      await loadData();
      setDialogOpen(false);
      setSelectedUser(null);
    } catch (err: any) {
      setError(err.message || 'Failed to update user role');
      console.error('Role update error:', err);
    } finally {
      setUpdating(false);
    }
  };

  const getRoleStats = () => {
    const stats: Record<string, number> = {};
    users.forEach(user => {
      stats[user.role] = (stats[user.role] || 0) + 1;
    });
    return stats;
  };

  const countPermissions = (perms: Record<string, boolean>) => {
    return Object.values(perms).filter(Boolean).length;
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  const roleStats = getRoleStats();

  return (
    <PermissionGate permission="can_assign_roles" showError showLoading>
      <Box sx={{ p: 3 }}>
        {/* Header */}
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
          <Box>
            <Typography variant="h4" gutterBottom>
              Role Management
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Manage user roles and view role permissions
            </Typography>
          </Box>
        </Box>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        {/* Role Statistics */}
        <Grid container spacing={2} sx={{ mb: 3 }}>
          {roles.map(role => (
            <Grid item xs={12} sm={6} md={4} lg={2.4} key={role.value}>
              <Card>
                <CardContent>
                  <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                    <Shield sx={{ mr: 1, color: 'primary.main' }} />
                    <Typography variant="h6" component="div">
                      {roleStats[role.value] || 0}
                    </Typography>
                  </Box>
                  <RoleBadge role={role.value} showIcon={false} showTooltip={false} />
                  <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 1 }}>
                    {rolePermissions[role.value] 
                      ? `${countPermissions(rolePermissions[role.value].permissions)} permissions`
                      : 'Loading...'
                    }
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>

        {/* Users Table */}
        <Paper sx={{ width: '100%', overflow: 'hidden' }}>
          <TableContainer sx={{ maxHeight: 600 }}>
            <Table stickyHeader>
              <TableHead>
                <TableRow>
                  <TableCell>User</TableCell>
                  <TableCell>Email</TableCell>
                  <TableCell>Current Role</TableCell>
                  <TableCell>Permissions</TableCell>
                  <TableCell align="right">Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {users.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={5} align="center">
                      <Typography color="text.secondary" sx={{ py: 3 }}>
                        No users found
                      </Typography>
                    </TableCell>
                  </TableRow>
                ) : (
                  users.map((user) => (
                    <TableRow key={user.id} hover>
                      <TableCell>
                        <Box sx={{ display: 'flex', alignItems: 'center' }}>
                          <Person sx={{ mr: 1, color: 'text.secondary' }} />
                          <Box>
                            <Typography variant="body2" fontWeight={500}>
                              {user.name || user.username}
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                              @{user.username}
                            </Typography>
                          </Box>
                        </Box>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2">{user.email}</Typography>
                      </TableCell>
                      <TableCell>
                        <RoleBadge role={user.role} />
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2">
                          {countPermissions(user.permissions)} active
                        </Typography>
                      </TableCell>
                      <TableCell align="right">
                        <Button
                          size="small"
                          variant="outlined"
                          onClick={() => handleEditRole(user)}
                          disabled={!hasPermission('can_assign_roles')}
                        >
                          Change Role
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </Paper>

        {/* Edit Role Dialog */}
        <Dialog open={dialogOpen} onClose={() => !updating && setDialogOpen(false)} maxWidth="sm" fullWidth>
          <DialogTitle>
            Change User Role
          </DialogTitle>
          <DialogContent>
            {selectedUser && (
              <>
                <Typography variant="body2" color="text.secondary" paragraph>
                  Change role for <strong>{selectedUser.name || selectedUser.username}</strong>
                </Typography>
                
                <FormControl fullWidth sx={{ mt: 2 }}>
                  <InputLabel>New Role</InputLabel>
                  <Select
                    value={newRole}
                    onChange={(e) => setNewRole(e.target.value)}
                    label="New Role"
                    disabled={updating}
                  >
                    {roles.map(role => (
                      <MenuItem key={role.value} value={role.value}>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <RoleBadge role={role.value} showTooltip={false} />
                          <Box>
                            <Typography variant="body2">{role.label}</Typography>
                            <Typography variant="caption" color="text.secondary">
                              {role.description}
                            </Typography>
                          </Box>
                        </Box>
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>

                {newRole && rolePermissions[newRole] && (
                  <Box sx={{ mt: 2 }}>
                    <Typography variant="subtitle2" gutterBottom>
                      This role has {countPermissions(rolePermissions[newRole].permissions)} permissions
                    </Typography>
                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, mt: 1 }}>
                      {Object.entries(rolePermissions[newRole].permissions)
                        .filter(([, value]) => value)
                        .slice(0, 10)
                        .map(([key]) => (
                          <Chip
                            key={key}
                            label={key.replace('can_', '').replace(/_/g, ' ')}
                            size="small"
                            variant="outlined"
                          />
                        ))}
                      {countPermissions(rolePermissions[newRole].permissions) > 10 && (
                        <Chip label="..." size="small" variant="outlined" />
                      )}
                    </Box>
                  </Box>
                )}
              </>
            )}
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setDialogOpen(false)} disabled={updating}>
              Cancel
            </Button>
            <Button
              onClick={handleUpdateRole}
              variant="contained"
              disabled={updating || !newRole || newRole === selectedUser?.role}
              startIcon={updating ? <CircularProgress size={20} /> : null}
            >
              {updating ? 'Updating...' : 'Update Role'}
            </Button>
          </DialogActions>
        </Dialog>
      </Box>
    </PermissionGate>
  );
};

export default RoleManagement;
