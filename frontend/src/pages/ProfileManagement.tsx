import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Grid,
  TextField,
  Button,
  Card,
  CardContent,
  CardActions,
  Avatar,
  Divider,
  Alert,
  Chip,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Switch,
  FormControlLabel,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Stack,
  CircularProgress,
  IconButton,
  Tooltip,
} from '@mui/material';
import {
  Person,
  Email,
  Phone,
  Work,
  Group,
  Security,
  Settings,
  Edit,
  Save,
  Cancel,
  PhotoCamera,
  Notifications,
  Schedule,
} from '@mui/icons-material';
import { apiClient } from '../services/apiClient';
import { API_CONFIG } from '../config/api';
import RecurringLeavePatterns from '../components/RecurringLeavePatterns';
import MFASettings from '../components/auth/MFASettings';

interface User {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  is_active: boolean;
  date_joined: string;
  last_login: string;
  employee_profile?: EmployeeProfile;
}

interface EmployeeProfile {
  id: number;
  employee_id: string;
  phone_number: string;
  emergency_contact_name: string;
  emergency_contact_phone: string;
  employment_type: string;
  status: string;
  hire_date: string;
  termination_date?: string;
  available_for_incidents: boolean;
  available_for_waakdienst: boolean;
  skills: Array<{
    id: number;
    name: string;
    description: string;
  }>;
  manager?: {
    id: number;
    username: string;
    first_name: string;
    last_name: string;
    email: string;
  };
}

interface NotificationSettings {
  email_notifications: boolean;
  shift_reminders: boolean;
  schedule_changes: boolean;
  team_updates: boolean;
}

const ProfileManagement: React.FC = () => {
  const [user, setUser] = useState<User | null>(null);
  const [employee, setEmployee] = useState<EmployeeProfile | null>(null);
  const [notifications, setNotifications] = useState<NotificationSettings>({
    email_notifications: true,
    shift_reminders: true,
    schedule_changes: true,
    team_updates: false,
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [editMode, setEditMode] = useState(false);
  const [passwordDialogOpen, setPasswordDialogOpen] = useState(false);
  const [formData, setFormData] = useState({
    first_name: '',
    last_name: '',
    email: '',
    phone: '',
    department: '',
    position: '',
    max_hours_per_week: 40,
    can_work_weekends: false,
  });
  const [passwordData, setPasswordData] = useState({
    current_password: '',
    new_password: '',
    confirm_password: '',
  });

  const loadProfile = async () => {
    setLoading(true);
    setError(null);
    
    try {
      // Load user profile using the API client
  // Use the full user endpoint so we get id and employee_profile
  const userData = await apiClient.get<User>(API_CONFIG.ENDPOINTS.USERS_ME_FULL);
      setUser(userData);
      setEmployee(userData.employee_profile || null);
      setFormData({
        first_name: userData.first_name || '',
        last_name: userData.last_name || '',
        email: userData.email || '',
        phone: userData.employee_profile?.phone_number || '',
        department: '', // This field might not be available in the current model
        position: '', // This field might not be available in the current model
        max_hours_per_week: 40, // Default value
        can_work_weekends: userData.employee_profile?.available_for_waakdienst || false,
      });

      // For now, we'll set default notification settings since there's no API endpoint yet
      setNotifications({
        email_notifications: true,
        shift_reminders: true,
        schedule_changes: true,
        team_updates: false,
      });
    } catch (err) {
      setError('Failed to load profile data');
      console.error('Profile loading error:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadProfile();
  }, []);

  const handleSaveProfile = async () => {
    setSaving(true);
    setError(null);
    setSuccess(null);

    try {
      await apiClient.put('/api/users/me/profile/', {
        first_name: formData.first_name,
        last_name: formData.last_name,
        email: formData.email,
        phone_number: formData.phone,
        available_for_waakdienst: formData.can_work_weekends,
        // Note: department and position might need to be added to the backend
      });

      setSuccess('Profile updated successfully');
      setEditMode(false);
      loadProfile(); // Reload data
    } catch (err: any) {
      setError(err.message || 'Failed to update profile');
      console.error('Save profile error:', err);
    } finally {
      setSaving(false);
    }
  };

  const handleSaveNotifications = async () => {
    // TODO: Implement notification settings API endpoint
    setSuccess('Notification settings feature coming soon');
  };

  const handleChangePassword = async () => {
    if (passwordData.new_password !== passwordData.confirm_password) {
      setError('New passwords do not match');
      return;
    }

    // TODO: Implement change password API endpoint
    setSuccess('Password change feature coming soon');
    setPasswordDialogOpen(false);
    setPasswordData({
      current_password: '',
      new_password: '',
      confirm_password: '',
    });
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
          Profile Management
        </Typography>
        <Stack direction="row" spacing={2}>
          {editMode ? (
            <>
              <Button
                variant="outlined"
                startIcon={<Cancel />}
                onClick={() => {
                  setEditMode(false);
                  setFormData({
                    first_name: user?.first_name || '',
                    last_name: user?.last_name || '',
                    email: user?.email || '',
                    phone: employee?.phone_number || '',
                    department: '', // Not available in current model
                    position: '', // Not available in current model
                    max_hours_per_week: 40, // Default value
                    can_work_weekends: employee?.available_for_waakdienst || false,
                  });
                }}
              >
                Cancel
              </Button>
              <Button
                variant="contained"
                startIcon={<Save />}
                onClick={handleSaveProfile}
                disabled={saving}
              >
                {saving ? 'Saving...' : 'Save Changes'}
              </Button>
            </>
          ) : (
            <Button
              variant="contained"
              startIcon={<Edit />}
              onClick={() => setEditMode(true)}
            >
              Edit Profile
            </Button>
          )}
        </Stack>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {success && (
        <Alert severity="success" sx={{ mb: 2 }}>
          {success}
        </Alert>
      )}

      <Grid container spacing={3}>
        {/* Profile Information */}
        <Grid item xs={12} md={8}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
                <Avatar sx={{ width: 80, height: 80, mr: 2 }}>
                  <Person sx={{ fontSize: 40 }} />
                </Avatar>
                <Box>
                  <Typography variant="h5">
                    {user?.first_name} {user?.last_name}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    @{user?.username}
                  </Typography>
                  <Stack direction="row" spacing={1} sx={{ mt: 1 }}>
                    {/* Note: is_manager is not available in current employee profile model */}
                    <Chip 
                      label={user?.is_active ? 'Active' : 'Inactive'} 
                      color={user?.is_active ? 'success' : 'error'} 
                      size="small" 
                    />
                    {employee?.status && (
                      <Chip 
                        label={employee.status.charAt(0).toUpperCase() + employee.status.slice(1)} 
                        color="primary" 
                        size="small" 
                      />
                    )}
                  </Stack>
                </Box>
                {editMode && (
                  <Tooltip title="Change Photo">
                    <IconButton sx={{ ml: 'auto' }}>
                      <PhotoCamera />
                    </IconButton>
                  </Tooltip>
                )}
              </Box>

              <Divider sx={{ mb: 3 }} />

              <Grid container spacing={3}>
                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    label="First Name"
                    value={formData.first_name}
                    onChange={(e) => setFormData({ ...formData, first_name: e.target.value })}
                    disabled={!editMode}
                    InputProps={{
                      startAdornment: <Person sx={{ mr: 1, color: 'text.secondary' }} />,
                    }}
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    label="Last Name"
                    value={formData.last_name}
                    onChange={(e) => setFormData({ ...formData, last_name: e.target.value })}
                    disabled={!editMode}
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    label="Email"
                    type="email"
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    disabled={!editMode}
                    InputProps={{
                      startAdornment: <Email sx={{ mr: 1, color: 'text.secondary' }} />,
                    }}
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    label="Phone"
                    value={formData.phone}
                    onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                    disabled={!editMode}
                    InputProps={{
                      startAdornment: <Phone sx={{ mr: 1, color: 'text.secondary' }} />,
                    }}
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    label="Department"
                    value={formData.department}
                    onChange={(e) => setFormData({ ...formData, department: e.target.value })}
                    disabled={!editMode}
                    InputProps={{
                      startAdornment: <Work sx={{ mr: 1, color: 'text.secondary' }} />,
                    }}
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    label="Position"
                    value={formData.position}
                    onChange={(e) => setFormData({ ...formData, position: e.target.value })}
                    disabled={!editMode}
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    label="Max Hours Per Week"
                    type="number"
                    value={formData.max_hours_per_week}
                    onChange={(e) => setFormData({ ...formData, max_hours_per_week: parseInt(e.target.value) })}
                    disabled={!editMode}
                    InputProps={{
                      startAdornment: <Schedule sx={{ mr: 1, color: 'text.secondary' }} />,
                    }}
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={formData.can_work_weekends}
                        onChange={(e) => setFormData({ ...formData, can_work_weekends: e.target.checked })}
                        disabled={!editMode}
                      />
                    }
                    label="Available for weekend work"
                  />
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        </Grid>

        {/* Sidebar */}
        <Grid item xs={12} md={4}>
          {/* Account Info */}
          <Card sx={{ mb: 3 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Account Information
              </Typography>
              <List dense>
                <ListItem>
                  <ListItemIcon>
                    <Person />
                  </ListItemIcon>
                  <ListItemText
                    primary="Employee ID"
                    secondary={employee?.employee_id || 'Not assigned'}
                  />
                </ListItem>
                <ListItem>
                  <ListItemIcon>
                    <Schedule />
                  </ListItemIcon>
                  <ListItemText
                    primary="Hire Date"
                    secondary={employee?.hire_date ? new Date(employee.hire_date).toLocaleDateString() : 'N/A'}
                  />
                </ListItem>
                <ListItem>
                  <ListItemIcon>
                    <Group />
                  </ListItemIcon>
                  <ListItemText
                    primary="Teams"
                    secondary="Feature not available yet"
                  />
                </ListItem>
              </List>
            </CardContent>
            <CardActions>
              <Button
                size="small"
                startIcon={<Security />}
                onClick={() => setPasswordDialogOpen(true)}
              >
                Change Password
              </Button>
            </CardActions>
          </Card>

          {/* Multi-Factor Authentication */}
          <Card>
            <MFASettings />
          </Card>

          {/* Notification Settings */}
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                <Notifications sx={{ mr: 1, verticalAlign: 'middle' }} />
                Notification Settings
              </Typography>
              <List dense>
                <ListItem>
                  <ListItemText primary="Email Notifications" />
                  <Switch
                    checked={notifications.email_notifications}
                    onChange={(e) => setNotifications({ ...notifications, email_notifications: e.target.checked })}
                  />
                </ListItem>
                <ListItem>
                  <ListItemText primary="Shift Reminders" />
                  <Switch
                    checked={notifications.shift_reminders}
                    onChange={(e) => setNotifications({ ...notifications, shift_reminders: e.target.checked })}
                  />
                </ListItem>
                <ListItem>
                  <ListItemText primary="Schedule Changes" />
                  <Switch
                    checked={notifications.schedule_changes}
                    onChange={(e) => setNotifications({ ...notifications, schedule_changes: e.target.checked })}
                  />
                </ListItem>
                <ListItem>
                  <ListItemText primary="Team Updates" />
                  <Switch
                    checked={notifications.team_updates}
                    onChange={(e) => setNotifications({ ...notifications, team_updates: e.target.checked })}
                  />
                </ListItem>
              </List>
            </CardContent>
            <CardActions>
              <Button
                size="small"
                startIcon={<Settings />}
                onClick={handleSaveNotifications}
              >
                Save Settings
              </Button>
            </CardActions>
          </Card>
        </Grid>

        {/* Recurring Leave Patterns */}
        <Grid item xs={12}>
          {user?.id ? (
            <RecurringLeavePatterns userId={user.id} />
          ) : (
            <Card>
              <CardContent>
                <Typography>Loading user information...</Typography>
              </CardContent>
            </Card>
          )}
        </Grid>
      </Grid>

      {/* Change Password Dialog */}
      <Dialog open={passwordDialogOpen} onClose={() => setPasswordDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Change Password</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <TextField
              fullWidth
              label="Current Password"
              type="password"
              value={passwordData.current_password}
              onChange={(e) => setPasswordData({ ...passwordData, current_password: e.target.value })}
            />
            <TextField
              fullWidth
              label="New Password"
              type="password"
              value={passwordData.new_password}
              onChange={(e) => setPasswordData({ ...passwordData, new_password: e.target.value })}
            />
            <TextField
              fullWidth
              label="Confirm New Password"
              type="password"
              value={passwordData.confirm_password}
              onChange={(e) => setPasswordData({ ...passwordData, confirm_password: e.target.value })}
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setPasswordDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleChangePassword} variant="contained">
            Change Password
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default ProfileManagement;
