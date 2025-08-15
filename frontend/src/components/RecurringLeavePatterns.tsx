import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  FormControlLabel,
  Switch,
  Grid,
  Chip,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  IconButton,
  Alert,
  Stack,
} from '@mui/material';
import {
  Add,
  Edit,
  Delete,
  Schedule,
  EventBusy,
} from '@mui/icons-material';
import { RecurringLeavePattern, RecurringLeavePatternForm } from '../types';
import { apiClient } from '../services/apiClient';

interface RecurringLeavePatternsProps {
  userId: number;
}

const DAY_CHOICES = [
  { value: 0, label: 'Monday' },
  { value: 1, label: 'Tuesday' },
  { value: 2, label: 'Wednesday' },
  { value: 3, label: 'Thursday' },
  { value: 4, label: 'Friday' },
];

const FREQUENCY_CHOICES = [
  { value: 'weekly', label: 'Every Week' },
  { value: 'biweekly', label: 'Every 2 Weeks' },
];

const COVERAGE_CHOICES = [
  { value: 'full_day', label: 'Full Day (8:00-17:00)' },
  { value: 'morning', label: 'Morning Only (8:00-12:00)' },
  { value: 'afternoon', label: 'Afternoon Only (12:00-17:00)' },
];

const RecurringLeavePatterns: React.FC<RecurringLeavePatternsProps> = ({ userId }) => {
  const [patterns, setPatterns] = useState<RecurringLeavePattern[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingPattern, setEditingPattern] = useState<RecurringLeavePattern | null>(null);
  const [formData, setFormData] = useState<RecurringLeavePatternForm>({
    name: '',
    day_of_week: 0,
    frequency: 'weekly',
    coverage_type: 'full_day',
    pattern_start_date: new Date().toISOString().split('T')[0],
    effective_from: new Date().toISOString().split('T')[0],
    effective_until: '',
    is_active: true,
    notes: '',
  });

    const loadPatterns = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiClient.get<any>(`/api/users/${userId}/recurring-leave-patterns/`);
      console.log('API Response:', response);
      
      // Handle both array response and paginated response
      let patternsData: RecurringLeavePattern[] = [];
      if (Array.isArray(response)) {
        patternsData = response;
      } else if (response && Array.isArray(response.results)) {
        patternsData = response.results;
      } else if (response && response.data && Array.isArray(response.data)) {
        patternsData = response.data;
      }
      
      setPatterns(patternsData);
    } catch (err: any) {
      console.error('Error loading patterns:', err);
      setError(err.message || 'Failed to load recurring leave patterns');
      setPatterns([]); // Set empty array on error
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (userId && userId > 0) {
      loadPatterns();
    } else {
      console.warn('RecurringLeavePatterns: Invalid userId provided:', userId);
      setPatterns([]);
      setLoading(false);
    }
  }, [userId]);

  const handleOpenDialog = (pattern?: RecurringLeavePattern) => {
    if (pattern) {
      setEditingPattern(pattern);
      setFormData({
        name: pattern.name,
        day_of_week: pattern.day_of_week,
        frequency: pattern.frequency,
        coverage_type: pattern.coverage_type,
        pattern_start_date: pattern.pattern_start_date,
        effective_from: pattern.effective_from,
        effective_until: pattern.effective_until || '',
        is_active: pattern.is_active,
        notes: pattern.notes,
      });
    } else {
      setEditingPattern(null);
      setFormData({
        name: '',
        day_of_week: 0,
        frequency: 'weekly',
        coverage_type: 'full_day',
        pattern_start_date: new Date().toISOString().split('T')[0],
        effective_from: new Date().toISOString().split('T')[0],
        effective_until: '',
        is_active: true,
        notes: '',
      });
    }
    setDialogOpen(true);
  };

  const handleCloseDialog = () => {
    setDialogOpen(false);
    setEditingPattern(null);
  };

  const handleSavePattern = async () => {
    try {
      setError(null);
      const payload = {
        ...formData,
        effective_until: formData.effective_until || null,
      };

      if (editingPattern) {
        await apiClient.put(`/api/users/${userId}/recurring-leave-patterns/${editingPattern.id}/`, payload);
      } else {
        await apiClient.post(`/api/users/${userId}/recurring-leave-patterns/`, payload);
      }

      await loadPatterns();
      handleCloseDialog();
    } catch (err: any) {
      setError(err.message || 'Failed to save pattern');
    }
  };

  const handleDeletePattern = async (patternId: number) => {
    if (!confirm('Are you sure you want to delete this recurring leave pattern?')) {
      return;
    }

    try {
      setError(null);
      await apiClient.delete(`/api/users/${userId}/recurring-leave-patterns/${patternId}/`);
      await loadPatterns();
    } catch (err: any) {
      setError(err.message || 'Failed to delete pattern');
    }
  };

  const formatPatternDescription = (pattern: RecurringLeavePattern) => {
    const day = DAY_CHOICES.find(d => d.value === pattern.day_of_week)?.label;
    const frequency = FREQUENCY_CHOICES.find(f => f.value === pattern.frequency)?.label;
    const coverage = COVERAGE_CHOICES.find(c => c.value === pattern.coverage_type)?.label;
    return `${frequency} ${day} - ${coverage}`;
  };

  if (loading) {
    return (
      <Card>
        <CardContent>
          <Typography>Loading recurring leave patterns...</Typography>
        </CardContent>
      </Card>
    );
  }

  return (
    <>
      <Card>
        <CardContent>
          <Stack direction="row" justifyContent="space-between" alignItems="center" mb={2}>
            <Typography variant="h6" component="h2">
              <Schedule sx={{ mr: 1, verticalAlign: 'middle' }} />
              Recurring Leave Patterns
            </Typography>
            <Button
              variant="contained"
              startIcon={<Add />}
              onClick={() => handleOpenDialog()}
            >
              Add Pattern
            </Button>
          </Stack>

          {error && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {error}
            </Alert>
          )}

          {patterns.length === 0 ? (
            <Box textAlign="center" py={4}>
              <EventBusy sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
              <Typography variant="h6" color="text.secondary" gutterBottom>
                No Recurring Leave Patterns
              </Typography>
              <Typography color="text.secondary" paragraph>
                You don't have any recurring leave patterns set up. These patterns help the
                scheduling system automatically account for your regular time off (like every
                Monday morning or every other Friday).
              </Typography>
              <Button
                variant="contained"
                startIcon={<Add />}
                onClick={() => handleOpenDialog()}
              >
                Create Your First Pattern
              </Button>
            </Box>
          ) : (
            <List>
              {(patterns || []).map((pattern) => (
                <ListItem key={pattern.id} divider>
                  <ListItemText
                    primary={pattern.name}
                    secondary={
                      <Stack spacing={1}>
                        <Typography variant="body2">
                          {formatPatternDescription(pattern)}
                        </Typography>
                        <Stack direction="row" spacing={1}>
                          <Chip
                            label={pattern.is_active ? 'Active' : 'Inactive'}
                            color={pattern.is_active ? 'success' : 'default'}
                            size="small"
                          />
                          <Chip
                            label={`From ${pattern.effective_from}`}
                            size="small"
                            variant="outlined"
                          />
                          {pattern.effective_until && (
                            <Chip
                              label={`Until ${pattern.effective_until}`}
                              size="small"
                              variant="outlined"
                            />
                          )}
                        </Stack>
                        {pattern.notes && (
                          <Typography variant="body2" color="text.secondary">
                            {pattern.notes}
                          </Typography>
                        )}
                      </Stack>
                    }
                  />
                  <ListItemSecondaryAction>
                    <IconButton
                      edge="end"
                      onClick={() => handleOpenDialog(pattern)}
                      sx={{ mr: 1 }}
                    >
                      <Edit />
                    </IconButton>
                    <IconButton
                      edge="end"
                      onClick={() => handleDeletePattern(pattern.id)}
                      color="error"
                    >
                      <Delete />
                    </IconButton>
                  </ListItemSecondaryAction>
                </ListItem>
              ))}
            </List>
          )}
        </CardContent>
      </Card>

      {/* Add/Edit Pattern Dialog */}
      <Dialog open={dialogOpen} onClose={handleCloseDialog} maxWidth="md" fullWidth>
        <DialogTitle>
          {editingPattern ? 'Edit Recurring Leave Pattern' : 'Add Recurring Leave Pattern'}
        </DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Pattern Name"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="e.g., Monday Mornings Off"
                helperText="Give this pattern a descriptive name"
              />
            </Grid>

            <Grid item xs={12} sm={6}>
              <FormControl fullWidth>
                <InputLabel>Day of Week</InputLabel>
                <Select
                  value={formData.day_of_week}
                  label="Day of Week"
                  onChange={(e) => setFormData({ ...formData, day_of_week: Number(e.target.value) })}
                >
                  {DAY_CHOICES.map((day) => (
                    <MenuItem key={day.value} value={day.value}>
                      {day.label}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>

            <Grid item xs={12} sm={6}>
              <FormControl fullWidth>
                <InputLabel>Frequency</InputLabel>
                <Select
                  value={formData.frequency}
                  label="Frequency"
                  onChange={(e) => setFormData({ ...formData, frequency: e.target.value as 'weekly' | 'biweekly' })}
                >
                  {FREQUENCY_CHOICES.map((freq) => (
                    <MenuItem key={freq.value} value={freq.value}>
                      {freq.label}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>

            <Grid item xs={12}>
              <FormControl fullWidth>
                <InputLabel>Coverage Type</InputLabel>
                <Select
                  value={formData.coverage_type}
                  label="Coverage Type"
                  onChange={(e) => setFormData({ ...formData, coverage_type: e.target.value as any })}
                >
                  {COVERAGE_CHOICES.map((coverage) => (
                    <MenuItem key={coverage.value} value={coverage.value}>
                      {coverage.label}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>

            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                type="date"
                label="Pattern Start Date"
                value={formData.pattern_start_date}
                onChange={(e) => setFormData({ ...formData, pattern_start_date: e.target.value })}
                helperText="Important for bi-weekly patterns"
                InputLabelProps={{ shrink: true }}
              />
            </Grid>

            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                type="date"
                label="Effective From"
                value={formData.effective_from}
                onChange={(e) => setFormData({ ...formData, effective_from: e.target.value })}
                helperText="When this pattern becomes active"
                InputLabelProps={{ shrink: true }}
              />
            </Grid>

            <Grid item xs={12}>
              <TextField
                fullWidth
                type="date"
                label="Effective Until (Optional)"
                value={formData.effective_until}
                onChange={(e) => setFormData({ ...formData, effective_until: e.target.value })}
                helperText="Leave empty for permanent pattern"
                InputLabelProps={{ shrink: true }}
              />
            </Grid>

            <Grid item xs={12}>
              <FormControlLabel
                control={
                  <Switch
                    checked={formData.is_active}
                    onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                  />
                }
                label="Active"
              />
            </Grid>

            <Grid item xs={12}>
              <TextField
                fullWidth
                multiline
                rows={3}
                label="Notes"
                value={formData.notes}
                onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                placeholder="Additional notes about this pattern..."
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDialog}>Cancel</Button>
          <Button variant="contained" onClick={handleSavePattern}>
            {editingPattern ? 'Update' : 'Create'} Pattern
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
};

export default RecurringLeavePatterns;
