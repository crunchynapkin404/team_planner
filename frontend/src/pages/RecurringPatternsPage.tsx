/**
 * Recurring Shift Patterns Management Page
 * 
 * Allows users to create, view, edit, and manage recurring shift patterns.
 */

import React, { useState, useEffect } from 'react';
import {
  Box,
  Button,
  Chip,
  CircularProgress,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  FormControl,
  Grid,
  IconButton,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
  Alert,
  Checkbox,
  FormControlLabel,
  FormGroup,
  Tooltip,
} from '@mui/material';
import {
  Add as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  PlayArrow as GenerateIcon,
  Visibility as PreviewIcon,
  AutoMode as BulkGenerateIcon,
} from '@mui/icons-material';
import recurringPatternService, {
  RecurringPattern,
  RecurringPatternCreate,
} from '../services/recurringPatternService';
import { apiClient } from '../services/apiClient';

interface ShiftTemplate {
  id: number;
  name: string;
  shift_type: string;
}

const WEEKDAY_NAMES = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
const RECURRENCE_TYPES = [
  { value: 'daily', label: 'Daily' },
  { value: 'weekly', label: 'Weekly' },
  { value: 'biweekly', label: 'Bi-weekly' },
  { value: 'monthly', label: 'Monthly' },
];

const RecurringPatternsPage: React.FC = () => {
  const [patterns, setPatterns] = useState<RecurringPattern[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  
  // Dialog states
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [editingPattern, setEditingPattern] = useState<RecurringPattern | null>(null);
  const [previewDialogOpen, setPreviewDialogOpen] = useState(false);
  const [previewDates, setPreviewDates] = useState<string[]>([]);
  const [previewPatternName, setPreviewPatternName] = useState('');
  
  // Form states
  const [formData, setFormData] = useState<RecurringPatternCreate>({
    name: '',
    description: '',
    template_id: 0,
    start_time: '09:00',
    end_time: '17:00',
    recurrence_type: 'weekly',
    weekdays: [0, 1, 2, 3, 4], // Monday-Friday by default
    pattern_start_date: new Date().toISOString().split('T')[0],
    is_active: true,
  });
  
  // Dropdown data
  const [templates, setTemplates] = useState<ShiftTemplate[]>([]);
  const [teams, setTeams] = useState<any[]>([]);
  const [employees, setEmployees] = useState<any[]>([]);

  useEffect(() => {
    loadPatterns();
    loadDropdownData();
  }, []);

  const loadPatterns = async () => {
    setLoading(true);
    setError(null);
    try {
      const data: any = await recurringPatternService.listPatterns();
      // Ensure we always have an array
      const patternsArray = Array.isArray(data) ? data : (data?.results || []);
      setPatterns(patternsArray);
    } catch (err: any) {
      setError(err.message || 'Failed to load patterns');
      setPatterns([]); // Reset to empty array on error
    } finally {
      setLoading(false);
    }
  };

  const loadDropdownData = async () => {
    try {
      // Load templates from API
      // For now, using mock data - replace with actual API call when endpoint exists
      setTemplates([
        { id: 1, name: 'Morning Shift', shift_type: 'incidents' },
        { id: 2, name: 'Evening Shift', shift_type: 'incidents' },
        { id: 3, name: 'Night Shift', shift_type: 'waakdienst' },
      ]);
      
      // Load teams
      const teamsRes: any = await apiClient.get('/teams/');
      const teamsData = Array.isArray(teamsRes) ? teamsRes : (teamsRes?.results || []);
      setTeams(teamsData);
      
      // Load users
      const usersRes: any = await apiClient.get('/users/');
      const usersData = Array.isArray(usersRes) ? usersRes : (usersRes?.results || []);
      setEmployees(usersData);
    } catch (err) {
      console.error('Failed to load dropdown data:', err);
    }
  };

  const handleCreate = () => {
    setFormData({
      name: '',
      description: '',
      template_id: 0,
      start_time: '09:00',
      end_time: '17:00',
      recurrence_type: 'weekly',
      weekdays: [0, 1, 2, 3, 4],
      pattern_start_date: new Date().toISOString().split('T')[0],
      is_active: true,
    });
    setEditingPattern(null);
    setCreateDialogOpen(true);
  };

  const handleEdit = (pattern: RecurringPattern) => {
    setFormData({
      name: pattern.name,
      description: pattern.description,
      template_id: pattern.template.id,
      start_time: pattern.start_time,
      end_time: pattern.end_time,
      recurrence_type: pattern.recurrence_type,
      weekdays: pattern.weekdays,
      day_of_month: pattern.day_of_month || undefined,
      pattern_start_date: pattern.pattern_start_date,
      pattern_end_date: pattern.pattern_end_date || undefined,
      assigned_employee_id: pattern.assigned_employee?.id,
      team_id: pattern.team?.id,
      is_active: pattern.is_active,
    });
    setEditingPattern(pattern);
    setCreateDialogOpen(true);
  };

  const handleSave = async () => {
    setError(null);
    setSuccess(null);
    
    try {
      if (editingPattern) {
        await recurringPatternService.updatePattern(editingPattern.id, formData);
        setSuccess('Pattern updated successfully');
      } else {
        await recurringPatternService.createPattern(formData);
        setSuccess('Pattern created successfully');
      }
      setCreateDialogOpen(false);
      loadPatterns();
    } catch (err: any) {
      setError(err.message || 'Failed to save pattern');
    }
  };

  const handleDelete = async (id: number) => {
    if (!window.confirm('Are you sure you want to delete this pattern?')) return;
    
    try {
      await recurringPatternService.deletePattern(id);
      setSuccess('Pattern deleted successfully');
      loadPatterns();
    } catch (err: any) {
      setError(err.message || 'Failed to delete pattern');
    }
  };

  const handleGenerate = async (id: number) => {
    try {
      const result = await recurringPatternService.generateShifts(id, 30);
      setSuccess(result.message);
      loadPatterns();
    } catch (err: any) {
      setError(err.message || 'Failed to generate shifts');
    }
  };

  const handlePreview = async (id: number, name: string) => {
    try {
      const result = await recurringPatternService.previewPattern(id, 30);
      setPreviewDates(result.dates);
      setPreviewPatternName(name);
      setPreviewDialogOpen(true);
    } catch (err: any) {
      setError(err.message || 'Failed to preview pattern');
    }
  };

  const handleBulkGenerate = async () => {
    if (!window.confirm('Generate shifts for all active patterns?')) return;
    
    setLoading(true);
    try {
      const result = await recurringPatternService.bulkGenerate(14);
      setSuccess(result.message);
      loadPatterns();
    } catch (err: any) {
      setError(err.message || 'Failed to bulk generate shifts');
    } finally {
      setLoading(false);
    }
  };

  const handleWeekdayChange = (day: number) => {
    setFormData(prev => ({
      ...prev,
      weekdays: prev.weekdays?.includes(day)
        ? prev.weekdays.filter(d => d !== day)
        : [...(prev.weekdays || []), day],
    }));
  };

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography variant="h4">Recurring Shift Patterns</Typography>
        <Box>
          <Button
            variant="outlined"
            startIcon={<BulkGenerateIcon />}
            onClick={handleBulkGenerate}
            sx={{ mr: 2 }}
            disabled={loading}
          >
            Bulk Generate
          </Button>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={handleCreate}
          >
            Create Pattern
          </Button>
        </Box>
      </Box>

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

      {loading && !previewDialogOpen && (
        <Box sx={{ display: 'flex', justifyContent: 'center', my: 4 }}>
          <CircularProgress />
        </Box>
      )}

      {!loading && (
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Name</TableCell>
                <TableCell>Template</TableCell>
                <TableCell>Recurrence</TableCell>
                <TableCell>Time</TableCell>
                <TableCell>Assigned To</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Last Generated</TableCell>
                <TableCell>Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {Array.isArray(patterns) && patterns.map((pattern) => (
                <TableRow key={pattern.id}>
                  <TableCell>
                    <Typography variant="body2" fontWeight="bold">
                      {pattern.name}
                    </Typography>
                    {pattern.description && (
                      <Typography variant="caption" color="text.secondary">
                        {pattern.description}
                      </Typography>
                    )}
                  </TableCell>
                  <TableCell>
                    {pattern.template.name}
                    <br />
                    <Chip label={pattern.template.shift_type} size="small" />
                  </TableCell>
                  <TableCell>
                    <Chip label={pattern.recurrence_type} size="small" />
                    {pattern.recurrence_type === 'weekly' || pattern.recurrence_type === 'biweekly' ? (
                      <Typography variant="caption" display="block">
                        {pattern.weekdays.map(d => WEEKDAY_NAMES[d].substring(0, 3)).join(', ')}
                      </Typography>
                    ) : null}
                    {pattern.recurrence_type === 'monthly' && pattern.day_of_month ? (
                      <Typography variant="caption" display="block">
                        Day {pattern.day_of_month}
                      </Typography>
                    ) : null}
                  </TableCell>
                  <TableCell>
                    {pattern.start_time} - {pattern.end_time}
                  </TableCell>
                  <TableCell>
                    {pattern.assigned_employee ? (
                      <>{pattern.assigned_employee.first_name} {pattern.assigned_employee.last_name}</>
                    ) : (
                      <Typography variant="caption" color="text.secondary">Unassigned</Typography>
                    )}
                    {pattern.team && (
                      <Typography variant="caption" display="block">
                        Team: {pattern.team.name}
                      </Typography>
                    )}
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={pattern.is_active ? 'Active' : 'Inactive'}
                      color={pattern.is_active ? 'success' : 'default'}
                      size="small"
                    />
                  </TableCell>
                  <TableCell>
                    {pattern.last_generated_date ? (
                      new Date(pattern.last_generated_date).toLocaleDateString()
                    ) : (
                      <Typography variant="caption" color="text.secondary">Never</Typography>
                    )}
                  </TableCell>
                  <TableCell>
                    <Tooltip title="Preview">
                      <IconButton
                        size="small"
                        onClick={() => handlePreview(pattern.id, pattern.name)}
                      >
                        <PreviewIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="Generate Shifts">
                      <IconButton
                        size="small"
                        onClick={() => handleGenerate(pattern.id)}
                        disabled={!pattern.is_active}
                      >
                        <GenerateIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="Edit">
                      <IconButton
                        size="small"
                        onClick={() => handleEdit(pattern)}
                      >
                        <EditIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="Delete">
                      <IconButton
                        size="small"
                        onClick={() => handleDelete(pattern.id)}
                      >
                        <DeleteIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                  </TableCell>
                </TableRow>
              ))}
              {(!Array.isArray(patterns) || patterns.length === 0) && (
                <TableRow>
                  <TableCell colSpan={8} align="center">
                    <Typography color="text.secondary">
                      No recurring patterns found. Create one to get started!
                    </Typography>
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      {/* Create/Edit Dialog */}
      <Dialog open={createDialogOpen} onClose={() => setCreateDialogOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>
          {editingPattern ? 'Edit Pattern' : 'Create Recurring Pattern'}
        </DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Pattern Name"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                required
              />
            </Grid>
            
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Description"
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                multiline
                rows={2}
              />
            </Grid>

            <Grid item xs={12} sm={6}>
              <FormControl fullWidth required>
                <InputLabel>Shift Template</InputLabel>
                <Select
                  value={formData.template_id}
                  onChange={(e) => setFormData({ ...formData, template_id: Number(e.target.value) })}
                  label="Shift Template"
                >
                  {templates.map(t => (
                    <MenuItem key={t.id} value={t.id}>{t.name} ({t.shift_type})</MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>

            <Grid item xs={12} sm={6}>
              <FormControl fullWidth required>
                <InputLabel>Recurrence Type</InputLabel>
                <Select
                  value={formData.recurrence_type}
                  onChange={(e) => setFormData({ ...formData, recurrence_type: e.target.value as any })}
                  label="Recurrence Type"
                >
                  {RECURRENCE_TYPES.map(t => (
                    <MenuItem key={t.value} value={t.value}>{t.label}</MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>

            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Start Time"
                type="time"
                value={formData.start_time}
                onChange={(e) => setFormData({ ...formData, start_time: e.target.value })}
                required
                InputLabelProps={{ shrink: true }}
              />
            </Grid>

            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="End Time"
                type="time"
                value={formData.end_time}
                onChange={(e) => setFormData({ ...formData, end_time: e.target.value })}
                required
                InputLabelProps={{ shrink: true }}
              />
            </Grid>

            {(formData.recurrence_type === 'weekly' || formData.recurrence_type === 'biweekly') && (
              <Grid item xs={12}>
                <Typography variant="subtitle2" gutterBottom>Weekdays</Typography>
                <FormGroup row>
                  {WEEKDAY_NAMES.map((day, index) => (
                    <FormControlLabel
                      key={day}
                      control={
                        <Checkbox
                          checked={formData.weekdays?.includes(index) || false}
                          onChange={() => handleWeekdayChange(index)}
                        />
                      }
                      label={day}
                    />
                  ))}
                </FormGroup>
              </Grid>
            )}

            {formData.recurrence_type === 'monthly' && (
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  label="Day of Month"
                  type="number"
                  value={formData.day_of_month || ''}
                  onChange={(e) => setFormData({ ...formData, day_of_month: Number(e.target.value) })}
                  inputProps={{ min: 1, max: 31 }}
                />
              </Grid>
            )}

            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Pattern Start Date"
                type="date"
                value={formData.pattern_start_date}
                onChange={(e) => setFormData({ ...formData, pattern_start_date: e.target.value })}
                required
                InputLabelProps={{ shrink: true }}
              />
            </Grid>

            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Pattern End Date (Optional)"
                type="date"
                value={formData.pattern_end_date || ''}
                onChange={(e) => setFormData({ ...formData, pattern_end_date: e.target.value })}
                InputLabelProps={{ shrink: true }}
              />
            </Grid>

            <Grid item xs={12} sm={6}>
              <FormControl fullWidth>
                <InputLabel>Assigned Employee (Optional)</InputLabel>
                <Select
                  value={formData.assigned_employee_id || ''}
                  onChange={(e) => setFormData({ ...formData, assigned_employee_id: e.target.value ? Number(e.target.value) : undefined })}
                  label="Assigned Employee (Optional)"
                >
                  <MenuItem value="">None</MenuItem>
                  {employees.map(emp => (
                    <MenuItem key={emp.id} value={emp.id}>
                      {emp.first_name} {emp.last_name} ({emp.username})
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>

            <Grid item xs={12} sm={6}>
              <FormControl fullWidth>
                <InputLabel>Team (Optional)</InputLabel>
                <Select
                  value={formData.team_id || ''}
                  onChange={(e) => setFormData({ ...formData, team_id: e.target.value ? Number(e.target.value) : undefined })}
                  label="Team (Optional)"
                >
                  <MenuItem value="">None</MenuItem>
                  {teams.map(team => (
                    <MenuItem key={team.id} value={team.id}>{team.name}</MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>

            <Grid item xs={12}>
              <FormControlLabel
                control={
                  <Checkbox
                    checked={formData.is_active}
                    onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                  />
                }
                label="Active"
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCreateDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleSave} variant="contained" disabled={!formData.name || !formData.template_id}>
            {editingPattern ? 'Update' : 'Create'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Preview Dialog */}
      <Dialog open={previewDialogOpen} onClose={() => setPreviewDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Preview: {previewPatternName}</DialogTitle>
        <DialogContent>
          <Typography variant="body2" gutterBottom>
            Next 30 days will generate {previewDates.length} shifts:
          </Typography>
          <Box sx={{ mt: 2, maxHeight: 400, overflow: 'auto' }}>
            {previewDates.map((date, index) => (
              <Chip
                key={index}
                label={new Date(date).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })}
                sx={{ m: 0.5 }}
                size="small"
              />
            ))}
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setPreviewDialogOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default RecurringPatternsPage;
