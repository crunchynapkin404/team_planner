import React, { useState, useEffect } from 'react';
import {
  Container,
  Paper,
  Typography,
  Box,
  FormGroup,
  FormControlLabel,
  Switch,
  Divider,
  Button,
  CircularProgress,
  Alert,
  Grid,
  TextField,
} from '@mui/material';
import { Save as SaveIcon } from '@mui/icons-material';
import { notificationService, NotificationPreference } from '../services/notificationService';

const NotificationSettings: React.FC = () => {
  const [preferences, setPreferences] = useState<NotificationPreference | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchPreferences();
  }, []);

  const fetchPreferences = async () => {
    try {
      setLoading(true);
      const data = await notificationService.getPreferences();
      setPreferences(data);
    } catch (err) {
      console.error('Failed to fetch notification preferences:', err);
      setError('Failed to load notification preferences. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    if (!preferences) return;

    try {
      setSaving(true);
      setError(null);
      setSuccess(false);
      await notificationService.updatePreferences(preferences);
      setSuccess(true);
      setTimeout(() => setSuccess(false), 3000);
    } catch (err) {
      console.error('Failed to update notification preferences:', err);
      setError('Failed to save preferences. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  const handleToggle = (field: keyof NotificationPreference) => {
    if (!preferences) return;
    setPreferences({
      ...preferences,
      [field]: !preferences[field],
    });
  };

  const handleQuietHoursChange = (field: 'quiet_hours_start' | 'quiet_hours_end', value: string) => {
    if (!preferences) return;
    setPreferences({
      ...preferences,
      [field]: value || null,
    });
  };

  if (loading) {
    return (
      <Container maxWidth="md" sx={{ mt: 4, mb: 4 }}>
        <Paper sx={{ p: 3 }}>
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
            <CircularProgress />
          </Box>
        </Paper>
      </Container>
    );
  }

  if (!preferences) {
    return (
      <Container maxWidth="md" sx={{ mt: 4, mb: 4 }}>
        <Paper sx={{ p: 3 }}>
          <Alert severity="error">
            Failed to load notification preferences. Please refresh the page.
          </Alert>
        </Paper>
      </Container>
    );
  }

  return (
    <Container maxWidth="md" sx={{ mt: 4, mb: 4 }}>
      <Paper sx={{ p: 3 }}>
        {/* Header */}
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
          <Typography variant="h4" component="h1">
            Notification Settings
          </Typography>
          <Button
            variant="contained"
            startIcon={<SaveIcon />}
            onClick={handleSave}
            disabled={saving}
          >
            {saving ? 'Saving...' : 'Save Changes'}
          </Button>
        </Box>

        {/* Success/Error Alerts */}
        {success && (
          <Alert severity="success" sx={{ mb: 2 }}>
            Notification preferences saved successfully!
          </Alert>
        )}
        {error && (
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        {/* Email Notifications Section */}
        <Box sx={{ mb: 4 }}>
          <Typography variant="h6" gutterBottom>
            Email Notifications
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Choose which events trigger email notifications
          </Typography>
          <FormGroup>
            <FormControlLabel
              control={
                <Switch
                  checked={preferences.email_shift_assigned}
                  onChange={() => handleToggle('email_shift_assigned')}
                />
              }
              label="New shift assigned to me"
            />
            <FormControlLabel
              control={
                <Switch
                  checked={preferences.email_shift_updated}
                  onChange={() => handleToggle('email_shift_updated')}
                />
              }
              label="My shift has been changed"
            />
            <FormControlLabel
              control={
                <Switch
                  checked={preferences.email_shift_cancelled}
                  onChange={() => handleToggle('email_shift_cancelled')}
                />
              }
              label="My shift has been cancelled"
            />
            <FormControlLabel
              control={
                <Switch
                  checked={preferences.email_reminders}
                  onChange={() => handleToggle('email_reminders')}
                />
              }
              label="Reminders for upcoming shifts"
            />
            <FormControlLabel
              control={
                <Switch
                  checked={preferences.email_swap_requested}
                  onChange={() => handleToggle('email_swap_requested')}
                />
              }
              label="Someone requests to swap with me"
            />
            <FormControlLabel
              control={
                <Switch
                  checked={preferences.email_swap_approved}
                  onChange={() => handleToggle('email_swap_approved')}
                />
              }
              label="My swap request is approved"
            />
            <FormControlLabel
              control={
                <Switch
                  checked={preferences.email_swap_rejected}
                  onChange={() => handleToggle('email_swap_rejected')}
                />
              }
              label="My swap request is rejected"
            />
            <FormControlLabel
              control={
                <Switch
                  checked={preferences.email_leave_approved}
                  onChange={() => handleToggle('email_leave_approved')}
                />
              }
              label="My leave request is approved"
            />
            <FormControlLabel
              control={
                <Switch
                  checked={preferences.email_leave_rejected}
                  onChange={() => handleToggle('email_leave_rejected')}
                />
              }
              label="My leave request is rejected"
            />
            <FormControlLabel
              control={
                <Switch
                  checked={preferences.email_schedule_published}
                  onChange={() => handleToggle('email_schedule_published')}
                />
              }
              label="New schedule is published"
            />
          </FormGroup>
        </Box>

        <Divider sx={{ my: 3 }} />

        {/* In-App Notifications Section */}
        <Box sx={{ mb: 4 }}>
          <Typography variant="h6" gutterBottom>
            In-App Notifications
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Choose which events show notifications in the app
          </Typography>
          <FormGroup>
            <FormControlLabel
              control={
                <Switch
                  checked={preferences.inapp_shift_assigned}
                  onChange={() => handleToggle('inapp_shift_assigned')}
                />
              }
              label="New shift assigned to me"
            />
            <FormControlLabel
              control={
                <Switch
                  checked={preferences.inapp_shift_updated}
                  onChange={() => handleToggle('inapp_shift_updated')}
                />
              }
              label="My shift has been changed"
            />
            <FormControlLabel
              control={
                <Switch
                  checked={preferences.inapp_shift_cancelled}
                  onChange={() => handleToggle('inapp_shift_cancelled')}
                />
              }
              label="My shift has been cancelled"
            />
            <FormControlLabel
              control={
                <Switch
                  checked={preferences.inapp_reminders}
                  onChange={() => handleToggle('inapp_reminders')}
                />
              }
              label="Reminders for upcoming shifts"
            />
            <FormControlLabel
              control={
                <Switch
                  checked={preferences.inapp_swap_requested}
                  onChange={() => handleToggle('inapp_swap_requested')}
                />
              }
              label="Someone requests to swap with me"
            />
            <FormControlLabel
              control={
                <Switch
                  checked={preferences.inapp_swap_approved}
                  onChange={() => handleToggle('inapp_swap_approved')}
                />
              }
              label="My swap request is approved"
            />
            <FormControlLabel
              control={
                <Switch
                  checked={preferences.inapp_swap_rejected}
                  onChange={() => handleToggle('inapp_swap_rejected')}
                />
              }
              label="My swap request is rejected"
            />
            <FormControlLabel
              control={
                <Switch
                  checked={preferences.inapp_leave_approved}
                  onChange={() => handleToggle('inapp_leave_approved')}
                />
              }
              label="My leave request is approved"
            />
            <FormControlLabel
              control={
                <Switch
                  checked={preferences.inapp_leave_rejected}
                  onChange={() => handleToggle('inapp_leave_rejected')}
                />
              }
              label="My leave request is rejected"
            />
            <FormControlLabel
              control={
                <Switch
                  checked={preferences.inapp_schedule_published}
                  onChange={() => handleToggle('inapp_schedule_published')}
                />
              }
              label="New schedule is published"
            />
          </FormGroup>
        </Box>

        <Divider sx={{ my: 3 }} />

        {/* Quiet Hours Section */}
        <Box sx={{ mb: 3 }}>
          <Typography variant="h6" gutterBottom>
            Quiet Hours
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Set hours when you don't want to receive email notifications (in-app notifications will still appear)
          </Typography>
          <Grid container spacing={2}>
            <Grid item xs={12} sm={6}>
              <TextField
                label="Start Time"
                type="time"
                value={preferences.quiet_hours_start || ''}
                onChange={(e) => handleQuietHoursChange('quiet_hours_start', e.target.value)}
                fullWidth
                InputLabelProps={{ shrink: true }}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                label="End Time"
                type="time"
                value={preferences.quiet_hours_end || ''}
                onChange={(e) => handleQuietHoursChange('quiet_hours_end', e.target.value)}
                fullWidth
                InputLabelProps={{ shrink: true }}
              />
            </Grid>
          </Grid>
          <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
            Leave empty to receive notifications at all times
          </Typography>
        </Box>

        {/* Save Button (Bottom) */}
        <Box sx={{ display: 'flex', justifyContent: 'flex-end', mt: 3 }}>
          <Button
            variant="contained"
            startIcon={<SaveIcon />}
            onClick={handleSave}
            disabled={saving}
            size="large"
          >
            {saving ? 'Saving...' : 'Save Changes'}
          </Button>
        </Box>
      </Paper>
    </Container>
  );
};

export default NotificationSettings;
