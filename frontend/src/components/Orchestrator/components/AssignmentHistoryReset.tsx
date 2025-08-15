import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  Alert,
  CircularProgress,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  TextField,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  Grid,
  Divider,
  FormHelperText
} from '@mui/material';
import {
  Warning,
  Delete,
  Preview
} from '@mui/icons-material';

interface AssignmentStats {
  employee_id: number;
  username: string;
  total_shifts: number;
  shift_types: { [key: string]: number };
}

interface PreviewData {
  total_shifts_to_reset: number;
  cutoff_date: string;
  days_back: number;
  filters: {
    team_id?: string;
    employee_id?: string;
  };
  assignment_distribution: AssignmentStats[];
  shift_type_breakdown: { [key: string]: number };
  affected_employees: number;
}

interface Team {
  pk: number;
  name: string;
}

interface Employee {
  pk: number;
  username: string;
  first_name?: string;
  last_name?: string;
}

const AssignmentHistoryReset: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewData, setPreviewData] = useState<PreviewData | null>(null);
  const [teams, setTeams] = useState<Team[]>([]);
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [confirmDialogOpen, setConfirmDialogOpen] = useState(false);
  const [success, setSuccess] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Form state
  const [selectedTeam, setSelectedTeam] = useState<string>('');
  const [selectedEmployee, setSelectedEmployee] = useState<string>('');
  const [daysBack, setDaysBack] = useState<number>(90);

  useEffect(() => {
    loadInitialData();
  }, []);

  const loadInitialData = async () => {
    try {
      // Load teams and employees - you'll need to implement these API calls
      // For now, using placeholder data structure
      const teamsResponse = await fetch('/api/teams/');
      if (teamsResponse.ok) {
        const teamsData = await teamsResponse.json();
        setTeams(teamsData);
      }

      const employeesResponse = await fetch('/api/users/');
      if (employeesResponse.ok) {
        const employeesData = await employeesResponse.json();
        setEmployees(employeesData);
      }
    } catch (err) {
      console.error('Error loading initial data:', err);
    }
  };

  const loadPreview = async () => {
    setPreviewLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams();
      if (selectedTeam) params.append('team_id', selectedTeam);
      if (selectedEmployee) params.append('employee_id', selectedEmployee);
      params.append('days_back', daysBack.toString());

      const response = await fetch(`/orchestrator/api/orchestrator/assignment-history-preview/?${params}`);
      const data = await response.json();

      if (response.ok) {
        setPreviewData(data.preview);
      } else {
        setError(data.error || 'Failed to load preview');
      }
    } catch (err) {
      setError('Network error while loading preview');
    } finally {
      setPreviewLoading(false);
    }
  };

  const performReset = async () => {
    setLoading(true);
    setError(null);
    setSuccess(null);

    try {
      const requestData = {
        days_back: daysBack,
        confirm: true,
        ...(selectedTeam && { team_id: parseInt(selectedTeam) }),
        ...(selectedEmployee && { employee_id: parseInt(selectedEmployee) })
      };

      const response = await fetch('/orchestrator/api/orchestrator/reset-history/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.getAttribute('value') || ''
        },
        body: JSON.stringify(requestData)
      });

      const data = await response.json();

      if (response.ok) {
        setSuccess(`Successfully reset assignment history: ${data.summary.shifts_deleted} shifts deleted`);
        setPreviewData(null);
        setConfirmDialogOpen(false);
        setDialogOpen(false);
      } else {
        setError(data.error || 'Failed to reset assignment history');
      }
    } catch (err) {
      setError('Network error during reset');
    } finally {
      setLoading(false);
    }
  };

  const getDisplayName = (stats: AssignmentStats) => {
    const employee = employees.find(e => e.pk === stats.employee_id);
    if (employee && (employee.first_name || employee.last_name)) {
      return `${employee.first_name || ''} ${employee.last_name || ''}`.trim();
    }
    return stats.username;
  };

  const getSeverityColor = (shiftCount: number, totalShifts: number) => {
    const percentage = (shiftCount / totalShifts) * 100;
    if (percentage > 70) return 'error';
    if (percentage > 40) return 'warning';
    return 'success';
  };

  return (
    <Card sx={{ maxWidth: 1200, margin: 'auto', mt: 2 }}>
      <CardContent>
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
          <Typography variant="h5" component="h2">
            Assignment History Management
          </Typography>
          <Button
            variant="contained"
            color="warning"
            startIcon={<Delete />}
            onClick={() => setDialogOpen(true)}
          >
            Reset Assignment History
          </Button>
        </Box>

        <Alert severity="info" sx={{ mb: 2 }}>
          Use this tool to reset assignment history when fairness distribution becomes unbalanced. 
          This will help ensure all employees get equal opportunities for shift assignments.
        </Alert>

        {success && (
          <Alert severity="success" onClose={() => setSuccess(null)} sx={{ mb: 2 }}>
            {success}
          </Alert>
        )}

        {error && (
          <Alert severity="error" onClose={() => setError(null)} sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        {/* Reset Dialog */}
        <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="md" fullWidth>
          <DialogTitle>
            <Box display="flex" alignItems="center">
              <Warning color="warning" sx={{ mr: 1 }} />
              Reset Assignment History
            </Box>
          </DialogTitle>
          <DialogContent>
            <Grid container spacing={2} sx={{ mt: 1 }}>
              <Grid item xs={12} md={4}>
                <FormControl fullWidth>
                  <InputLabel>Team (Optional)</InputLabel>
                  <Select
                    value={selectedTeam}
                    onChange={(e) => setSelectedTeam(e.target.value)}
                    label="Team (Optional)"
                  >
                    <MenuItem value="">All Teams</MenuItem>
                    {teams.map((team) => (
                      <MenuItem key={team.pk} value={team.pk.toString()}>
                        {team.name}
                      </MenuItem>
                    ))}
                  </Select>
                  <FormHelperText>Filter reset to specific team</FormHelperText>
                </FormControl>
              </Grid>

              <Grid item xs={12} md={4}>
                <FormControl fullWidth>
                  <InputLabel>Employee (Optional)</InputLabel>
                  <Select
                    value={selectedEmployee}
                    onChange={(e) => setSelectedEmployee(e.target.value)}
                    label="Employee (Optional)"
                  >
                    <MenuItem value="">All Employees</MenuItem>
                    {employees.map((employee) => (
                      <MenuItem key={employee.pk} value={employee.pk.toString()}>
                        {getDisplayName({ employee_id: employee.pk, username: employee.username } as AssignmentStats)}
                      </MenuItem>
                    ))}
                  </Select>
                  <FormHelperText>Reset specific employee only</FormHelperText>
                </FormControl>
              </Grid>

              <Grid item xs={12} md={4}>
                <TextField
                  fullWidth
                  label="Days Back"
                  type="number"
                  value={daysBack}
                  onChange={(e) => setDaysBack(parseInt(e.target.value) || 90)}
                  inputProps={{ min: 1, max: 365 }}
                  helperText="Number of days of history to reset"
                />
              </Grid>

              <Grid item xs={12}>
                <Box display="flex" gap={2}>
                  <Button
                    variant="outlined"
                    startIcon={<Preview />}
                    onClick={loadPreview}
                    disabled={previewLoading}
                  >
                    {previewLoading ? <CircularProgress size={20} /> : 'Preview'}
                  </Button>
                  <Button
                    variant="contained"
                    color="warning"
                    startIcon={<Delete />}
                    onClick={() => setConfirmDialogOpen(true)}
                    disabled={!previewData || loading}
                  >
                    Reset History
                  </Button>
                </Box>
              </Grid>
            </Grid>

            {previewData && (
              <Box mt={3}>
                <Divider sx={{ mb: 2 }} />
                <Typography variant="h6" gutterBottom>
                  Preview: {previewData.total_shifts_to_reset} shifts will be deleted
                </Typography>
                
                <Grid container spacing={2} sx={{ mb: 2 }}>
                  <Grid item xs={12} md={6}>
                    <Typography variant="subtitle2">Shift Type Breakdown:</Typography>
                    <Box display="flex" flexWrap="wrap" gap={1} mt={1}>
                      {Object.entries(previewData.shift_type_breakdown).map(([type, count]) => (
                        <Chip 
                          key={type} 
                          label={`${type}: ${count}`} 
                          size="small" 
                          variant="outlined"
                        />
                      ))}
                    </Box>
                  </Grid>
                  <Grid item xs={12} md={6}>
                    <Typography variant="subtitle2">
                      Affected Employees: {previewData.affected_employees}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Date range: Last {previewData.days_back} days
                    </Typography>
                  </Grid>
                </Grid>

                <TableContainer component={Paper} sx={{ maxHeight: 300 }}>
                  <Table stickyHeader size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>Employee</TableCell>
                        <TableCell align="right">Total Shifts</TableCell>
                        <TableCell>Shift Types</TableCell>
                        <TableCell align="center">Fairness Impact</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {previewData.assignment_distribution.map((stats) => (
                        <TableRow key={stats.employee_id}>
                          <TableCell>
                            <Typography variant="body2">
                              {getDisplayName(stats)}
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                              ID: {stats.employee_id}
                            </Typography>
                          </TableCell>
                          <TableCell align="right">
                            <Chip
                              label={stats.total_shifts}
                              color={getSeverityColor(stats.total_shifts, previewData.total_shifts_to_reset)}
                              size="small"
                            />
                          </TableCell>
                          <TableCell>
                            <Box display="flex" flexWrap="wrap" gap={0.5}>
                              {Object.entries(stats.shift_types).map(([type, count]) => (
                                <Chip 
                                  key={type} 
                                  label={`${type.substring(0, 3)}: ${count}`} 
                                  size="small" 
                                  variant="outlined"
                                />
                              ))}
                            </Box>
                          </TableCell>
                          <TableCell align="center">
                            {stats.total_shifts > (previewData.total_shifts_to_reset / previewData.affected_employees * 2) ? (
                              <Chip label="High Impact" color="error" size="small" />
                            ) : stats.total_shifts > (previewData.total_shifts_to_reset / previewData.affected_employees) ? (
                              <Chip label="Medium Impact" color="warning" size="small" />
                            ) : (
                              <Chip label="Low Impact" color="success" size="small" />
                            )}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              </Box>
            )}
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setDialogOpen(false)}>
              Cancel
            </Button>
          </DialogActions>
        </Dialog>

        {/* Confirmation Dialog */}
        <Dialog open={confirmDialogOpen} onClose={() => setConfirmDialogOpen(false)}>
          <DialogTitle>
            <Box display="flex" alignItems="center">
              <Warning color="error" sx={{ mr: 1 }} />
              Confirm Reset
            </Box>
          </DialogTitle>
          <DialogContent>
            <Alert severity="warning" sx={{ mb: 2 }}>
              This action cannot be undone. Are you sure you want to delete{' '}
              {previewData?.total_shifts_to_reset} shifts from the assignment history?
            </Alert>
            <Typography variant="body2">
              This will reset fairness calculations and allow for more balanced future assignments.
            </Typography>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setConfirmDialogOpen(false)}>
              Cancel
            </Button>
            <Button 
              onClick={performReset} 
              color="error" 
              variant="contained"
              disabled={loading}
              startIcon={loading ? <CircularProgress size={20} /> : <Delete />}
            >
              {loading ? 'Resetting...' : 'Confirm Reset'}
            </Button>
          </DialogActions>
        </Dialog>
      </CardContent>
    </Card>
  );
};

export default AssignmentHistoryReset;
