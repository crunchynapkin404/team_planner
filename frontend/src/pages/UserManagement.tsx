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
  Grid,
  Alert,
  CircularProgress,
  Tooltip,
  Stack,
  Card,
  CardContent,
} from '@mui/material';
import {
  Edit,
  PersonAdd,
  Group,
  Visibility,
  Block,
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';

interface User {
  id: number;
  username: string;
  email: string;
  first_name: string | null;
  last_name: string | null;
  name: string;
  is_active: boolean;
  is_staff: boolean;
  is_superuser: boolean;
  date_joined: string;
  last_login: string | null;
  employee_profile?: {
    employee_id: string;
    employment_type: string;
    status: string;
    available_for_incidents: boolean;
    available_for_waakdienst: boolean;
    hire_date: string;
  };
  teams?: Array<{
    id: number;
    name: string;
    role: string;
  }>;
}

interface Team {
  id: number;
  name: string;
  department: string;
  manager: string;
  member_count: number;
}

const UserManagement: React.FC = () => {
  const [users, setUsers] = useState<User[]>([]);
  const [, setTeams] = useState<Team[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [userDialogOpen, setUserDialogOpen] = useState(false);
  const [selectedUser, setSelectedUser] = useState<User | null>(null);
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    first_name: '',
    last_name: '',
    is_active: true,
    is_staff: false,
    is_superuser: false,
    available_for_incidents: false,
    available_for_waakdienst: false,
    employment_type: 'full_time',
  });
  
  const navigate = useNavigate();

  const loadData = async () => {
    setLoading(true);
    setError(null);
    
    try {
      // Load users
      const usersResponse = await fetch('http://localhost:8000/api/users/', {
        headers: {
          'Authorization': `Token ${localStorage.getItem('token')}`,
        },
      });

      if (usersResponse.ok) {
        const usersData = await usersResponse.json();
        setUsers(usersData.results || usersData);
      } else {
        throw new Error('Failed to load users');
      }

      // Load teams
      const teamsResponse = await fetch('http://localhost:8000/api/teams/', {
        headers: {
          'Authorization': `Token ${localStorage.getItem('token')}`,
        },
      });

      if (teamsResponse.ok) {
        const teamsData = await teamsResponse.json();
        setTeams(teamsData.results || teamsData);
      } else {
        throw new Error('Failed to load teams');
      }
    } catch (err) {
      setError('Failed to load data');
      console.error('Data loading error:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleCreateUser = () => {
    setSelectedUser(null);
    setFormData({
      username: '',
      email: '',
      first_name: '',
      last_name: '',
      is_active: true,
      is_staff: false,
      is_superuser: false,
      available_for_incidents: false,
      available_for_waakdienst: false,
      employment_type: 'full_time',
    });
    setUserDialogOpen(true);
  };

  const handleEditUser = (user: User) => {
    setSelectedUser(user);
    setFormData({
      username: user.username,
      email: user.email,
      first_name: user.first_name || '',
      last_name: user.last_name || '',
      is_active: user.is_active,
      is_staff: user.is_staff,
      is_superuser: user.is_superuser,
      available_for_incidents: user.employee_profile?.available_for_incidents || false,
      available_for_waakdienst: user.employee_profile?.available_for_waakdienst || false,
      employment_type: user.employee_profile?.employment_type || 'full_time',
    });
    setUserDialogOpen(true);
  };

  const handleSaveUser = async () => {
    try {
      const url = selectedUser 
        ? `http://localhost:8000/api/users/${selectedUser.id}/`
        : 'http://localhost:8000/api/users/';
      
      const method = selectedUser ? 'PUT' : 'POST';
      
      const response = await fetch(url, {
        method,
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Token ${localStorage.getItem('token')}`,
        },
        body: JSON.stringify(formData),
      });

      if (response.ok) {
        setUserDialogOpen(false);
        loadData(); // Reload data
      } else {
        const errorData = await response.json();
        setError(Object.values(errorData).flat().join(', '));
      }
    } catch (err) {
      setError('Failed to save user');
      console.error('Save user error:', err);
    }
  };

  const handleToggleUserActive = async (user: User) => {
    try {
      const response = await fetch(`http://localhost:8000/api/users/${user.id}/`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Token ${localStorage.getItem('token')}`,
        },
        body: JSON.stringify({
          is_active: !user.is_active,
        }),
      });

      if (response.ok) {
        loadData(); // Reload data
      } else {
        setError('Failed to update user status');
      }
    } catch (err) {
      setError('Failed to update user status');
      console.error('Toggle user error:', err);
    }
  };

  const getRoleChips = (user: User) => {
    const roles = [];
    
    if (user.is_superuser) {
      roles.push(<Chip key="admin" label="Admin" color="error" size="small" />);
    } else if (user.is_staff) {
      roles.push(<Chip key="staff" label="Staff" color="warning" size="small" />);
    }
    
    if (user.teams && user.teams.length > 0) {
      user.teams.forEach(team => {
        if (team.role === 'manager' || team.role === 'lead') {
          roles.push(<Chip key={`team-${team.id}`} label={`${team.name} Lead`} color="primary" size="small" />);
        }
      });
    }
    
    if (roles.length === 0) {
      roles.push(<Chip key="user" label="User" color="default" size="small" />);
    }
    
    return roles;
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" gutterBottom>
          User Management
        </Typography>
        <Stack direction="row" spacing={2}>
          <Button
            variant="outlined"
            startIcon={<Group />}
            onClick={() => navigate('/team-management')}
          >
            Team Management
          </Button>
          <Button
            variant="contained"
            startIcon={<PersonAdd />}
            onClick={handleCreateUser}
          >
            Add User
          </Button>
        </Stack>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {/* Statistics Cards */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Total Users
              </Typography>
              <Typography variant="h4">
                {users.length}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Active Users
              </Typography>
              <Typography variant="h4" color="success.main">
                {users.filter(u => u.is_active).length}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Staff Members
              </Typography>
              <Typography variant="h4" color="warning.main">
                {users.filter(u => u.is_staff).length}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Admins
              </Typography>
              <Typography variant="h4" color="error.main">
                {users.filter(u => u.is_superuser).length}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Users Table */}
      <Paper>
        <TableContainer>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>User</TableCell>
                <TableCell>Employee ID</TableCell>
                <TableCell>Roles</TableCell>
                <TableCell>Shift Availability</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Last Login</TableCell>
                <TableCell>Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {users.map((user) => (
                <TableRow key={user.id}>
                  <TableCell>
                    <Box>
                      <Typography variant="body1" fontWeight="bold">
                        {user.name || `${user.first_name || ''} ${user.last_name || ''}`.trim() || user.username}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        {user.email}
                      </Typography>
                    </Box>
                  </TableCell>
                  <TableCell>
                    {user.employee_profile?.employee_id || '-'}
                  </TableCell>
                  <TableCell>
                    <Stack direction="row" spacing={1} flexWrap="wrap">
                      {getRoleChips(user)}
                    </Stack>
                  </TableCell>
                  <TableCell>
                    <Stack direction="column" spacing={0.5}>
                      {user.employee_profile?.available_for_incidents && (
                        <Chip label="Incidents" size="small" color="error" />
                      )}
                      {user.employee_profile?.available_for_waakdienst && (
                        <Chip label="Waakdienst" size="small" color="primary" />
                      )}
                      {!user.employee_profile?.available_for_incidents && 
                       !user.employee_profile?.available_for_waakdienst && (
                        <Typography variant="body2" color="text.secondary">
                          None
                        </Typography>
                      )}
                    </Stack>
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={user.is_active ? 'Active' : 'Inactive'}
                      color={user.is_active ? 'success' : 'default'}
                      size="small"
                    />
                  </TableCell>
                  <TableCell>
                    {user.last_login 
                      ? new Date(user.last_login).toLocaleDateString()
                      : 'Never'
                    }
                  </TableCell>
                  <TableCell>
                    <Stack direction="row" spacing={1}>
                      <Tooltip title="View Details">
                        <IconButton size="small" onClick={() => navigate(`/users/${user.id}`)}>
                          <Visibility />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="Edit User">
                        <IconButton size="small" onClick={() => handleEditUser(user)}>
                          <Edit />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title={user.is_active ? 'Deactivate' : 'Activate'}>
                        <IconButton 
                          size="small" 
                          onClick={() => handleToggleUserActive(user)}
                          color={user.is_active ? 'error' : 'success'}
                        >
                          <Block />
                        </IconButton>
                      </Tooltip>
                    </Stack>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </Paper>

      {/* User Dialog */}
      <Dialog open={userDialogOpen} onClose={() => setUserDialogOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>
          {selectedUser ? 'Edit User' : 'Create New User'}
        </DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Username"
                value={formData.username}
                onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                required
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Email"
                type="email"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                required
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="First Name"
                value={formData.first_name}
                onChange={(e) => setFormData({ ...formData, first_name: e.target.value })}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Last Name"
                value={formData.last_name}
                onChange={(e) => setFormData({ ...formData, last_name: e.target.value })}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <FormControl fullWidth>
                <InputLabel>Employment Type</InputLabel>
                <Select
                  value={formData.employment_type}
                  onChange={(e) => setFormData({ ...formData, employment_type: e.target.value })}
                  label="Employment Type"
                >
                  <MenuItem value="full_time">Full Time</MenuItem>
                  <MenuItem value="part_time">Part Time</MenuItem>
                  <MenuItem value="contractor">Contractor</MenuItem>
                  <MenuItem value="intern">Intern</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12}>
              <Typography variant="h6" sx={{ mb: 1 }}>Permissions</Typography>
              <FormControlLabel
                control={
                  <Switch
                    checked={formData.is_active}
                    onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                  />
                }
                label="Active User"
              />
              <FormControlLabel
                control={
                  <Switch
                    checked={formData.is_staff}
                    onChange={(e) => setFormData({ ...formData, is_staff: e.target.checked })}
                  />
                }
                label="Staff Member (can access admin)"
              />
              <FormControlLabel
                control={
                  <Switch
                    checked={formData.is_superuser}
                    onChange={(e) => setFormData({ ...formData, is_superuser: e.target.checked })}
                  />
                }
                label="Administrator (full access)"
              />
            </Grid>
            <Grid item xs={12}>
              <Typography variant="h6" sx={{ mb: 1 }}>Shift Availability</Typography>
              <FormControlLabel
                control={
                  <Switch
                    checked={formData.available_for_incidents}
                    onChange={(e) => setFormData({ ...formData, available_for_incidents: e.target.checked })}
                  />
                }
                label="Available for Incidents (Mon-Fri, 8:00-17:00)"
              />
              <FormControlLabel
                control={
                  <Switch
                    checked={formData.available_for_waakdienst}
                    onChange={(e) => setFormData({ ...formData, available_for_waakdienst: e.target.checked })}
                  />
                }
                label="Available for Waakdienst (Evenings, nights, weekends)"
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setUserDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleSaveUser} variant="contained">
            {selectedUser ? 'Update' : 'Create'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default UserManagement;
