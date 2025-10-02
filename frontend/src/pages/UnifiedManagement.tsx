import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Tabs,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Button,
  IconButton,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Switch,
  FormControlLabel,
  Alert,
  CircularProgress,
  Tooltip,
  Stack,
  Card,
  CardContent,
  Grid,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
} from '@mui/material';
import {
  Person,
  People,
  Shield,
  Edit,
  PersonAdd,
  GroupAdd,
  Delete,
  Block,
  CheckCircle,
  PersonRemove,
} from '@mui/icons-material';
import { formatDate } from '../utils/dateUtils';
import { apiClient } from '../services/apiClient';
import { usePermissions } from '../hooks/usePermissions';
import RoleBadge from '../components/common/RoleBadge';
import PermissionGate from '../components/auth/PermissionGate';

interface User {
  id: number;
  username: string;
  email: string;
  first_name: string | null;
  last_name: string | null;
  name: string;
  is_active: boolean;
  is_staff: boolean;
  date_joined: string;
  role?: string;
  role_display?: string;
}

interface Team {
  id: number;
  name: string;
  description: string;
  department: string;
  department_name: string;
  manager: User | null;
  members: TeamMember[];
  created: string;
}

interface TeamMember {
  id: number;
  user: User;
  role: string;
  joined_date: string;
  is_active: boolean;
}

interface Role {
  value: string;
  label: string;
  description: string;
}

interface Department {
  id: number;
  name: string;
  description: string;
}

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`management-tabpanel-${index}`}
      aria-labelledby={`management-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ pt: 3 }}>{children}</Box>}
    </div>
  );
}

const UnifiedManagement: React.FC = () => {
  const { hasPermission, loading: permissionsLoading } = usePermissions();
  const [tabValue, setTabValue] = useState(0);
  
  // Common state
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  
  // Users state
  const [users, setUsers] = useState<User[]>([]);
  const [userDialogOpen, setUserDialogOpen] = useState(false);
  const [selectedUser, setSelectedUser] = useState<User | null>(null);
  const [userFormData, setUserFormData] = useState({
    username: '',
    email: '',
    first_name: '',
    last_name: '',
    is_active: true,
  });
  
  // Teams state
  const [teams, setTeams] = useState<Team[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [teamDialogOpen, setTeamDialogOpen] = useState(false);
  const [selectedTeam, setSelectedTeam] = useState<Team | null>(null);
  const [teamFormData, setTeamFormData] = useState({
    name: '',
    description: '',
    department: '',
  });
  const [addMemberDialogOpen, setAddMemberDialogOpen] = useState(false);
  const [selectedUserId, setSelectedUserId] = useState<string>('');
  const [selectedMemberRole, setSelectedMemberRole] = useState<string>('member');
  
  // Department state
  const [departmentDialogOpen, setDepartmentDialogOpen] = useState(false);
  const [selectedDepartment, setSelectedDepartment] = useState<Department | null>(null);
  const [departmentFormData, setDepartmentFormData] = useState({
    name: '',
    description: '',
    manager: '',
  });
  const [showDepartments, setShowDepartments] = useState(true);
  
  // Roles state
  const [roles, setRoles] = useState<Role[]>([]);
  const [roleDialogOpen, setRoleDialogOpen] = useState(false);
  const [selectedUserForRole, setSelectedUserForRole] = useState<User | null>(null);
  const [newRole, setNewRole] = useState<string>('');

  useEffect(() => {
    // Wait for permissions to load before fetching data
    if (!permissionsLoading) {
      loadData();
    }
  }, [tabValue, permissionsLoading]);

  const loadData = async () => {
    setLoading(true);
    setError(null);

    try {
      if (tabValue === 0 && hasPermission('can_manage_users')) {
        // Load users (paginated response)
        const usersResponse = await apiClient.get<{ results: User[] }>('/api/users/');
        const usersData = usersResponse.results || usersResponse as any as User[];
        
        // Load users with roles (direct array response)
        const usersWithRoles = await apiClient.get<User[]>('/api/rbac/users/');
        // Merge role information
        const mergedUsers = usersData.map(user => {
          const userWithRole = Array.isArray(usersWithRoles) 
            ? usersWithRoles.find(u => u.id === user.id)
            : null;
          return userWithRole ? { ...user, role: userWithRole.role, role_display: userWithRole.role_display } : user;
        });
        setUsers(mergedUsers);
      } else if (tabValue === 1 && hasPermission('can_manage_team')) {
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
      } else if (tabValue === 2 && hasPermission('can_assign_roles')) {
        // Load roles and users (both direct array responses)
        const [rolesData, usersWithRoles] = await Promise.all([
          apiClient.get<Role[]>('/api/rbac/roles/'),
          apiClient.get<User[]>('/api/rbac/users/'),
        ]);
        setRoles(Array.isArray(rolesData) ? rolesData : []);
        setUsers(Array.isArray(usersWithRoles) ? usersWithRoles : []);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load data');
      console.error('Data loading error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleTabChange = (_event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
    setError(null);
    setSuccess(null);
  };

  // User Management Functions
  const handleActivateUser = async (userId: number) => {
    try {
      await apiClient.patch(`/api/users/${userId}/`, { is_active: true });
      setSuccess('User activated successfully');
      loadData();
    } catch (err: any) {
      setError(err.message || 'Failed to activate user');
    }
  };

  const handleDeactivateUser = async (userId: number) => {
    if (!confirm('Are you sure you want to deactivate this user?')) return;
    
    try {
      await apiClient.patch(`/api/users/${userId}/`, { is_active: false });
      setSuccess('User deactivated successfully');
      loadData();
    } catch (err: any) {
      setError(err.message || 'Failed to deactivate user');
    }
  };

  const handleEditUser = (user: User) => {
    setSelectedUser(user);
    setUserFormData({
      username: user.username,
      email: user.email,
      first_name: user.first_name || '',
      last_name: user.last_name || '',
      is_active: user.is_active,
    });
    setUserDialogOpen(true);
  };

  const handleSaveUser = async () => {
    if (!selectedUser) return;

    try {
      await apiClient.patch(`/api/users/${selectedUser.id}/`, userFormData);
      setSuccess('User updated successfully');
      setUserDialogOpen(false);
      loadData();
    } catch (err: any) {
      setError(err.message || 'Failed to update user');
    }
  };

  // Team Management Functions
  const handleCreateTeam = () => {
    setSelectedTeam(null);
    setTeamFormData({ name: '', description: '', department: '' });
    setTeamDialogOpen(true);
  };

  const handleEditTeam = (team: Team) => {
    setSelectedTeam(team);
    setTeamFormData({
      name: team.name,
      description: team.description,
      department: team.department,
    });
    setTeamDialogOpen(true);
  };

  const handleSaveTeam = async () => {
    try {
      if (selectedTeam) {
        await apiClient.patch(`/api/teams/${selectedTeam.id}/`, teamFormData);
        setSuccess('Team updated successfully');
      } else {
        await apiClient.post('/api/teams/', teamFormData);
        setSuccess('Team created successfully');
      }
      setTeamDialogOpen(false);
      loadData();
    } catch (err: any) {
      setError(err.message || 'Failed to save team');
    }
  };

  const handleDeleteTeam = async (teamId: number) => {
    if (!confirm('Are you sure you want to delete this team?')) return;
    
    try {
      await apiClient.delete(`/api/teams/${teamId}/`);
      setSuccess('Team deleted successfully');
      loadData();
    } catch (err: any) {
      setError(err.message || 'Failed to delete team');
    }
  };

  const handleAddMember = (team: Team) => {
    setSelectedTeam(team);
    setSelectedUserId('');
    setSelectedMemberRole('member');
    setAddMemberDialogOpen(true);
  };

  const handleSaveTeamMember = async () => {
    if (!selectedTeam || !selectedUserId) return;

    try {
      await apiClient.post(`/api/teams/${selectedTeam.id}/add_member/`, {
        user_id: parseInt(selectedUserId),
        role: selectedMemberRole,
      });
      setSuccess('Team member added successfully');
      setAddMemberDialogOpen(false);
      loadData();
    } catch (err: any) {
      setError(err.message || 'Failed to add team member');
    }
  };

  // Department Management Functions
  const handleCreateDepartment = () => {
    setSelectedDepartment(null);
    setDepartmentFormData({ name: '', description: '', manager: '' });
    setDepartmentDialogOpen(true);
  };

  const handleEditDepartment = (department: Department) => {
    setSelectedDepartment(department);
    setDepartmentFormData({
      name: department.name,
      description: department.description,
      manager: (department as any).manager || '',
    });
    setDepartmentDialogOpen(true);
  };

  const handleSaveDepartment = async () => {
    try {
      if (selectedDepartment) {
        await apiClient.patch(`/api/departments/${selectedDepartment.id}/`, departmentFormData);
        setSuccess('Department updated successfully');
      } else {
        await apiClient.post('/api/departments/', departmentFormData);
        setSuccess('Department created successfully');
      }
      setDepartmentDialogOpen(false);
      loadData();
    } catch (err: any) {
      setError(err.message || 'Failed to save department');
    }
  };

  const handleDeleteDepartment = async (departmentId: number) => {
    if (!confirm('Are you sure you want to delete this department? This will also delete all teams in this department.')) return;
    
    try {
      await apiClient.delete(`/api/departments/${departmentId}/`);
      setSuccess('Department deleted successfully');
      loadData();
    } catch (err: any) {
      setError(err.message || 'Failed to delete department');
    }
  };

  const handleRemoveMember = async (teamId: number, memberId: number) => {
    if (!confirm('Are you sure you want to remove this member?')) return;
    
    try {
      await apiClient.delete(`/api/teams/${teamId}/remove_member/`, {
        data: { user_id: memberId }
      });
      setSuccess('Team member removed successfully');
      loadData();
    } catch (err: any) {
      setError(err.message || 'Failed to remove team member');
    }
  };

  // Role Management Functions
  const handleChangeRole = (user: User) => {
    setSelectedUserForRole(user);
    setNewRole(user.role || 'employee');
    setRoleDialogOpen(true);
  };

  const handleSaveRole = async () => {
    if (!selectedUserForRole) return;

    try {
      await apiClient.patch(`/api/rbac/users/${selectedUserForRole.id}/role/`, {
        role: newRole,
      });
      setSuccess('User role updated successfully');
      setRoleDialogOpen(false);
      loadData();
    } catch (err: any) {
      setError(err.message || 'Failed to update role');
    }
  };

  const getRoleStats = () => {
    const stats: Record<string, number> = {};
    users.forEach(user => {
      const role = user.role || 'employee';
      stats[role] = (stats[role] || 0) + 1;
    });
    return stats;
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '400px' }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box sx={{ width: '100%', minHeight: '100%' }}>
      {/* Header */}
      <Box sx={{ mb: 3 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          Management Console
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Manage users, teams, and roles from a single interface
        </Typography>
      </Box>

      {/* Alert Messages */}
      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}
      {success && (
        <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccess(null)}>
          {success}
        </Alert>
      )}

      {/* Tabs */}
      <Paper sx={{ mb: 3 }}>
        <Tabs value={tabValue} onChange={handleTabChange} aria-label="management tabs">
          <Tab 
            icon={<Person />} 
            label="Users" 
            id="management-tab-0"
            disabled={!hasPermission('can_manage_users')}
          />
          <Tab 
            icon={<People />} 
            label="Teams" 
            id="management-tab-1"
            disabled={!hasPermission('can_manage_team')}
          />
          <Tab 
            icon={<Shield />} 
            label="Roles" 
            id="management-tab-2"
            disabled={!hasPermission('can_assign_roles')}
          />
        </Tabs>
      </Paper>

      {/* Users Tab */}
      <TabPanel value={tabValue} index={0}>
        <PermissionGate permission="can_manage_users">
          <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
            <Typography variant="h6">User Management</Typography>
            <Button
              variant="contained"
              startIcon={<PersonAdd />}
              onClick={() => {
                setSelectedUser(null);
                setUserFormData({ username: '', email: '', first_name: '', last_name: '', is_active: true });
                setUserDialogOpen(true);
              }}
            >
              Add User
            </Button>
          </Stack>

          <TableContainer component={Paper}>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Username</TableCell>
                  <TableCell>Name</TableCell>
                  <TableCell>Email</TableCell>
                  <TableCell>Role</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Joined</TableCell>
                  <TableCell align="right">Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {loading ? (
                  <TableRow>
                    <TableCell colSpan={7} align="center">
                      <CircularProgress size={24} />
                    </TableCell>
                  </TableRow>
                ) : users.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={7} align="center">
                      <Typography color="text.secondary">No users found</Typography>
                    </TableCell>
                  </TableRow>
                ) : (
                  users.map((user) => (
                    <TableRow key={user.id}>
                      <TableCell>{user.username}</TableCell>
                      <TableCell>{user.name || '-'}</TableCell>
                      <TableCell>{user.email}</TableCell>
                      <TableCell>
                        {user.role ? (
                          <RoleBadge role={user.role} />
                        ) : (
                          <Chip label="No Role" size="small" />
                        )}
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={user.is_active ? 'Active' : 'Inactive'}
                          color={user.is_active ? 'success' : 'default'}
                          size="small"
                        />
                      </TableCell>
                      <TableCell>{formatDate(user.date_joined)}</TableCell>
                      <TableCell align="right">
                        <Tooltip title="Edit">
                          <IconButton size="small" onClick={() => handleEditUser(user)}>
                            <Edit fontSize="small" />
                          </IconButton>
                        </Tooltip>
                        {user.is_active ? (
                          <Tooltip title="Deactivate">
                            <IconButton
                              size="small"
                              color="error"
                              onClick={() => handleDeactivateUser(user.id)}
                            >
                              <Block fontSize="small" />
                            </IconButton>
                          </Tooltip>
                        ) : (
                          <Tooltip title="Activate">
                            <IconButton
                              size="small"
                              color="success"
                              onClick={() => handleActivateUser(user.id)}
                            >
                              <CheckCircle fontSize="small" />
                            </IconButton>
                          </Tooltip>
                        )}
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </PermissionGate>
      </TabPanel>

      {/* Teams Tab */}
      <TabPanel value={tabValue} index={1}>
        <PermissionGate permission="can_manage_team">
          {/* Department Management Section */}
          <Paper sx={{ p: 2, mb: 3 }}>
            <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
              <Typography variant="h6">Departments</Typography>
              <Stack direction="row" spacing={1}>
                <Button
                  size="small"
                  onClick={() => setShowDepartments(!showDepartments)}
                >
                  {showDepartments ? 'Hide' : 'Show'}
                </Button>
                <Button
                  variant="contained"
                  size="small"
                  onClick={handleCreateDepartment}
                >
                  Create Department
                </Button>
              </Stack>
            </Stack>

            {showDepartments && (
              <>
                {loading ? (
                  <Box sx={{ display: 'flex', justifyContent: 'center', p: 2 }}>
                    <CircularProgress size={24} />
                  </Box>
                ) : departments.length === 0 ? (
                  <Box sx={{ p: 2, textAlign: 'center' }}>
                    <Typography color="text.secondary">
                      No departments found. Create one to start organizing teams!
                    </Typography>
                  </Box>
                ) : (
                  <TableContainer>
                    <Table size="small">
                      <TableHead>
                        <TableRow>
                          <TableCell>Name</TableCell>
                          <TableCell>Description</TableCell>
                          <TableCell align="right">Actions</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {departments.map((dept) => (
                          <TableRow key={dept.id}>
                            <TableCell>{dept.name}</TableCell>
                            <TableCell>{dept.description || '-'}</TableCell>
                            <TableCell align="right">
                              <Stack direction="row" spacing={1} justifyContent="flex-end">
                                <IconButton
                                  size="small"
                                  onClick={() => handleEditDepartment(dept)}
                                >
                                  <Edit fontSize="small" />
                                </IconButton>
                                <IconButton
                                  size="small"
                                  color="error"
                                  onClick={() => handleDeleteDepartment(dept.id)}
                                >
                                  <Delete fontSize="small" />
                                </IconButton>
                              </Stack>
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </TableContainer>
                )}
              </>
            )}
          </Paper>

          {/* Team Management Section */}
          <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
            <Typography variant="h6">Teams</Typography>
            <Button
              variant="contained"
              startIcon={<GroupAdd />}
              onClick={handleCreateTeam}
              disabled={departments.length === 0}
            >
              Create Team
            </Button>
          </Stack>
          
          {departments.length === 0 && (
            <Alert severity="info" sx={{ mb: 2 }}>
              Please create a department first before creating teams.
            </Alert>
          )}

          {loading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
              <CircularProgress />
            </Box>
          ) : teams.length === 0 ? (
            <Box sx={{ p: 4, textAlign: 'center' }}>
              <Typography color="text.secondary">No teams found. Create your first team!</Typography>
            </Box>
          ) : (
            <Grid container spacing={2}>
              {teams.map((team) => (
                <Grid item xs={12} md={6} key={team.id}>
                  <Card>
                  <CardContent>
                    <Stack direction="row" justifyContent="space-between" alignItems="start" sx={{ mb: 2 }}>
                      <Box>
                        <Typography variant="h6">{team.name}</Typography>
                        <Typography variant="body2" color="text.secondary">
                          {team.description}
                        </Typography>
                        <Chip
                          label={team.department_name}
                          size="small"
                          sx={{ mt: 1 }}
                        />
                      </Box>
                      <Stack direction="row" spacing={1}>
                        <IconButton size="small" onClick={() => handleEditTeam(team)}>
                          <Edit fontSize="small" />
                        </IconButton>
                        <IconButton
                          size="small"
                          color="error"
                          onClick={() => handleDeleteTeam(team.id)}
                        >
                          <Delete fontSize="small" />
                        </IconButton>
                      </Stack>
                    </Stack>

                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                      <Typography variant="subtitle2">
                        Members ({team.members?.length || 0})
                      </Typography>
                      <Button
                        size="small"
                        startIcon={<PersonAdd />}
                        onClick={() => handleAddMember(team)}
                      >
                        Add
                      </Button>
                    </Box>

                    <List dense>
                      {team.members?.map((member) => (
                        <ListItem key={member.id}>
                          <ListItemText
                            primary={member.user.name || member.user.username}
                            secondary={member.role}
                          />
                          <ListItemSecondaryAction>
                            <IconButton
                              edge="end"
                              size="small"
                              onClick={() => handleRemoveMember(team.id, member.id)}
                            >
                              <PersonRemove fontSize="small" />
                            </IconButton>
                          </ListItemSecondaryAction>
                        </ListItem>
                      ))}
                    </List>
                  </CardContent>
                </Card>
              </Grid>
            ))}
            </Grid>
          )}
        </PermissionGate>
      </TabPanel>

      {/* Roles Tab */}
      <TabPanel value={tabValue} index={2}>
        <PermissionGate permission="can_assign_roles">
          <Typography variant="h6" sx={{ mb: 2 }}>
            Role Management
          </Typography>

          {/* Role Statistics */}
          <Grid container spacing={2} sx={{ mb: 3 }}>
            {Object.entries(getRoleStats()).map(([role, count]) => (
              <Grid item xs={12} sm={6} md={2.4} key={role}>
                <Card>
                  <CardContent>
                    <Typography variant="h4" align="center">
                      {count}
                    </Typography>
                    <Box sx={{ display: 'flex', justifyContent: 'center', mt: 1 }}>
                      <RoleBadge role={role} />
                    </Box>
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>

          {/* Users with Roles */}
          <TableContainer component={Paper}>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Username</TableCell>
                  <TableCell>Name</TableCell>
                  <TableCell>Email</TableCell>
                  <TableCell>Current Role</TableCell>
                  <TableCell align="right">Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {loading ? (
                  <TableRow>
                    <TableCell colSpan={5} align="center">
                      <CircularProgress size={24} />
                    </TableCell>
                  </TableRow>
                ) : users.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={5} align="center">
                      <Typography color="text.secondary">No users found</Typography>
                    </TableCell>
                  </TableRow>
                ) : (
                  users.map((user) => (
                    <TableRow key={user.id}>
                      <TableCell>{user.username}</TableCell>
                      <TableCell>{user.name || '-'}</TableCell>
                      <TableCell>{user.email}</TableCell>
                      <TableCell>
                        {user.role ? (
                          <RoleBadge role={user.role} />
                        ) : (
                          <Chip label="No Role" size="small" />
                        )}
                      </TableCell>
                      <TableCell align="right">
                        <Button
                          size="small"
                          variant="outlined"
                          onClick={() => handleChangeRole(user)}
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
        </PermissionGate>
      </TabPanel>

      {/* User Edit Dialog */}
      <Dialog open={userDialogOpen} onClose={() => setUserDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>{selectedUser ? 'Edit User' : 'Add User'}</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <TextField
              label="Username"
              value={userFormData.username}
              onChange={(e) => setUserFormData({ ...userFormData, username: e.target.value })}
              fullWidth
              disabled={!!selectedUser}
            />
            <TextField
              label="Email"
              value={userFormData.email}
              onChange={(e) => setUserFormData({ ...userFormData, email: e.target.value })}
              fullWidth
            />
            <TextField
              label="First Name"
              value={userFormData.first_name}
              onChange={(e) => setUserFormData({ ...userFormData, first_name: e.target.value })}
              fullWidth
            />
            <TextField
              label="Last Name"
              value={userFormData.last_name}
              onChange={(e) => setUserFormData({ ...userFormData, last_name: e.target.value })}
              fullWidth
            />
            <FormControlLabel
              control={
                <Switch
                  checked={userFormData.is_active}
                  onChange={(e) => setUserFormData({ ...userFormData, is_active: e.target.checked })}
                />
              }
              label="Active"
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setUserDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleSaveUser} variant="contained">
            Save
          </Button>
        </DialogActions>
      </Dialog>

      {/* Team Edit Dialog */}
      <Dialog open={teamDialogOpen} onClose={() => setTeamDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>{selectedTeam ? 'Edit Team' : 'Create Team'}</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <TextField
              label="Team Name"
              value={teamFormData.name}
              onChange={(e) => setTeamFormData({ ...teamFormData, name: e.target.value })}
              fullWidth
            />
            <TextField
              label="Description"
              value={teamFormData.description}
              onChange={(e) => setTeamFormData({ ...teamFormData, description: e.target.value })}
              multiline
              rows={3}
              fullWidth
            />
            <FormControl fullWidth>
              <InputLabel>Department</InputLabel>
              <Select
                value={teamFormData.department}
                onChange={(e) => setTeamFormData({ ...teamFormData, department: e.target.value })}
                label="Department"
              >
                {departments.map((dept) => (
                  <MenuItem key={dept.id} value={dept.id.toString()}>
                    {dept.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setTeamDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleSaveTeam} variant="contained">
            Save
          </Button>
        </DialogActions>
      </Dialog>

      {/* Add Team Member Dialog */}
      <Dialog open={addMemberDialogOpen} onClose={() => setAddMemberDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Add Team Member</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <FormControl fullWidth>
              <InputLabel>User</InputLabel>
              <Select
                value={selectedUserId}
                onChange={(e) => setSelectedUserId(e.target.value)}
                label="User"
              >
                {users
                  .filter(u => !selectedTeam?.members?.find(m => m.user.id === u.id))
                  .map((user) => (
                    <MenuItem key={user.id} value={user.id.toString()}>
                      {user.name || user.username}
                    </MenuItem>
                  ))}
              </Select>
            </FormControl>
            <FormControl fullWidth>
              <InputLabel>Role</InputLabel>
              <Select
                value={selectedMemberRole}
                onChange={(e) => setSelectedMemberRole(e.target.value)}
                label="Role"
              >
                <MenuItem value="member">Member</MenuItem>
                <MenuItem value="lead">Lead</MenuItem>
                <MenuItem value="manager">Manager</MenuItem>
              </Select>
            </FormControl>
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setAddMemberDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleSaveTeamMember} variant="contained">
            Add
          </Button>
        </DialogActions>
      </Dialog>

      {/* Change Role Dialog */}
      <Dialog open={roleDialogOpen} onClose={() => setRoleDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Change User Role</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <Typography variant="body2" color="text.secondary">
              Changing role for: <strong>{selectedUserForRole?.name || selectedUserForRole?.username}</strong>
            </Typography>
            <FormControl fullWidth>
              <InputLabel>New Role</InputLabel>
              <Select
                value={newRole}
                onChange={(e) => setNewRole(e.target.value)}
                label="New Role"
              >
                {roles.map((role) => (
                  <MenuItem key={role.value} value={role.value}>
                    <Stack direction="row" spacing={1} alignItems="center">
                      <RoleBadge role={role.value} />
                      <Typography variant="body2" color="text.secondary">
                        - {role.description}
                      </Typography>
                    </Stack>
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setRoleDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleSaveRole} variant="contained">
            Save
          </Button>
        </DialogActions>
      </Dialog>

      {/* Department Dialog */}
      <Dialog open={departmentDialogOpen} onClose={() => setDepartmentDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>{selectedDepartment ? 'Edit Department' : 'Create Department'}</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <TextField
              label="Department Name"
              value={departmentFormData.name}
              onChange={(e) => setDepartmentFormData({ ...departmentFormData, name: e.target.value })}
              fullWidth
              required
            />
            <TextField
              label="Description"
              value={departmentFormData.description}
              onChange={(e) => setDepartmentFormData({ ...departmentFormData, description: e.target.value })}
              fullWidth
              multiline
              rows={3}
            />
            <FormControl fullWidth>
              <InputLabel>Manager (Optional)</InputLabel>
              <Select
                value={departmentFormData.manager}
                onChange={(e) => setDepartmentFormData({ ...departmentFormData, manager: e.target.value })}
                label="Manager (Optional)"
              >
                <MenuItem value="">
                  <em>None</em>
                </MenuItem>
                {users.map((user) => (
                  <MenuItem key={user.id} value={user.id}>
                    {user.name || user.username}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDepartmentDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleSaveDepartment} variant="contained">
            {selectedDepartment ? 'Save' : 'Create'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default UnifiedManagement;
