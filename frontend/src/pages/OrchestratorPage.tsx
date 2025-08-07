import React, { useState } from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  TextField,
  FormControlLabel,
  Checkbox,
  Grid,
  Card,
  CardContent,
  Alert,
  CircularProgress,
  Chip,
  Stack,
  MenuItem,
  Select,
  FormControl,
  InputLabel,
} from '@mui/material';
// Using standard HTML date inputs instead of MUI date pickers for now
import { PlayArrow, Preview, CheckCircle, Assessment, History } from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { apiClient } from '../services/apiClient';
import { API_CONFIG } from '../config/api';

interface OrchestratorPageProps {}

interface OrchestrationResult {
  total_shifts: number;
  incidents_shifts: number;
  incidents_standby_shifts: number;
  waakdienst_shifts: number;
  employees_assigned: number;
  fairness_scores: Record<string, number>;
  average_fairness: number;
  potential_duplicates?: Array<{
    shift_type: string;
    start_datetime: string;
    end_datetime: string;
    assigned_employee: string;
  }>;
  skipped_duplicates?: Array<{
    shift_type: string;
    start_datetime: string;
    end_datetime: string;
    assigned_employee: string;
  }>;
}

interface Team {
  id: number;
  name: string;
}

const OrchestratorPage: React.FC<OrchestratorPageProps> = () => {
  const [startDate, setStartDate] = useState<Date | null>(getNextMonday());
  const [endDate, setEndDate] = useState<Date | null>(getEndOfYear());
  const [description, setDescription] = useState('');
  const [previewOnly, setPreviewOnly] = useState(true);
  const [scheduleIncidents, setScheduleIncidents] = useState(true);
  const [scheduleIncidentsStandby, setScheduleIncidentsStandby] = useState(false);
  const [scheduleWaakdienst, setScheduleWaakdienst] = useState(true);
  const [selectedTeam, setSelectedTeam] = useState<number | ''>('');
  const [teams, setTeams] = useState<Team[]>([]);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<OrchestrationResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  // Load teams on component mount
  React.useEffect(() => {
    const loadTeams = async () => {
      try {
        const teamData = await apiClient.get(API_CONFIG.ENDPOINTS.TEAMS_LIST) as any;
        setTeams(teamData);
      } catch (err) {
        console.error('Failed to load teams:', err);
      }
    };
    loadTeams();
  }, []);

  function getNextMonday(): Date {
    const today = new Date();
    const dayOfWeek = today.getDay();
    const daysUntilMonday = dayOfWeek === 0 ? 1 : 8 - dayOfWeek; // 0 = Sunday
    const nextMonday = new Date(today);
    nextMonday.setDate(today.getDate() + daysUntilMonday);
    return nextMonday;
  }

  function getEndOfYear(): Date {
    const today = new Date();
    return new Date(today.getFullYear(), 11, 31); // December 31st
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!startDate || !endDate) {
      setError('Please select both start and end dates');
      return;
    }

    if (startDate >= endDate) {
      setError('End date must be after start date');
      return;
    }

    if (!selectedTeam) {
      setError('Please select a team');
      return;
    }

    if (!scheduleIncidents && !scheduleIncidentsStandby && !scheduleWaakdienst) {
      setError('Please select at least one shift type');
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const requestData = {
        name: `Orchestration ${startDate.toISOString().split('T')[0]} to ${endDate.toISOString().split('T')[0]}`,
        description: description,
        start_date: startDate.toISOString().split('T')[0],
        end_date: endDate.toISOString().split('T')[0],
        preview_only: previewOnly.toString(),
        schedule_incidents: scheduleIncidents,
        schedule_incidents_standby: scheduleIncidentsStandby,
        schedule_waakdienst: scheduleWaakdienst,
        team_id: selectedTeam
      };

      const result = await apiClient.post(API_CONFIG.ENDPOINTS.ORCHESTRATOR_CREATE, requestData) as any;
      
      if (previewOnly) {
        // Handle preview result
        setResult(result);
      } else {
        // Handle direct application
        navigate('/calendar');
      }
    } catch (err: any) {
      setError(err.response?.data?.error || 'Network error occurred');
      console.error('Orchestration error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleApplyPreview = async () => {
    setLoading(true);
    try {
      await apiClient.post(API_CONFIG.ENDPOINTS.ORCHESTRATOR_APPLY_PREVIEW, {});
      navigate('/calendar');
    } catch (err: any) {
      setError(err.response?.data?.error || 'Network error occurred');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h4" gutterBottom>
          Shift Orchestrator
        </Typography>
        <Stack direction="row" spacing={2}>
          <Button
            variant="outlined"
            startIcon={<Assessment />}
            onClick={() => navigate('/fairness')}
          >
            Fairness Dashboard
          </Button>
          <Button
            variant="outlined"
            startIcon={<History />}
            onClick={() => navigate('/orchestrator-history')}
          >
            History
          </Button>
        </Stack>
      </Box>
      <Typography variant="body1" color="text.secondary" paragraph>
        Generate fair shift assignments for incidents and waakdienst using the orchestration engine.
      </Typography>

      <Grid container spacing={3}>
        <Grid item xs={12} md={8}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Orchestration Parameters
            </Typography>

            <form onSubmit={handleSubmit}>
              <Grid container spacing={2}>
                <Grid item xs={12} sm={6}>
                  <TextField
                    label="Start Date"
                    type="date"
                    value={startDate ? startDate.toISOString().split('T')[0] : ''}
                    onChange={(e) => setStartDate(e.target.value ? new Date(e.target.value) : null)}
                    fullWidth
                    required
                    InputLabelProps={{
                      shrink: true,
                    }}
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <TextField
                    label="End Date"
                    type="date"
                    value={endDate ? endDate.toISOString().split('T')[0] : ''}
                    onChange={(e) => setEndDate(e.target.value ? new Date(e.target.value) : null)}
                    fullWidth
                    required
                    InputLabelProps={{
                      shrink: true,
                    }}
                  />
                </Grid>
              </Grid>

              <Grid container spacing={2} sx={{ mt: 1 }}>
                <Grid item xs={12} sm={6}>
                  <FormControl fullWidth required>
                    <InputLabel>Team</InputLabel>
                    <Select
                      value={selectedTeam}
                      onChange={(e) => setSelectedTeam(e.target.value as number)}
                      label="Team"
                    >
                      {teams.map((team) => (
                        <MenuItem key={team.id} value={team.id}>
                          {team.name}
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                </Grid>
                <Grid item xs={12} sm={6}>
                  <Typography variant="subtitle2" gutterBottom>
                    Shift Types to Schedule
                  </Typography>
                  <Stack spacing={1}>
                    <FormControlLabel
                      control={
                        <Checkbox
                          checked={scheduleIncidents}
                          onChange={(e) => setScheduleIncidents(e.target.checked)}
                        />
                      }
                      label="Incidents - Business hours coverage (Mon-Fri 08:00-17:00)"
                    />
                    <FormControlLabel
                      control={
                        <Checkbox
                          checked={scheduleIncidentsStandby}
                          onChange={(e) => setScheduleIncidentsStandby(e.target.checked)}
                        />
                      }
                      label="Incidents-Standby - Secondary coverage (Mon-Fri 08:00-17:00)"
                    />
                    <FormControlLabel
                      control={
                        <Checkbox
                          checked={scheduleWaakdienst}
                          onChange={(e) => setScheduleWaakdienst(e.target.checked)}
                        />
                      }
                      label="Waakdienst - On-call coverage (evenings, nights, weekends)"
                    />
                  </Stack>
                </Grid>
              </Grid>

              <TextField
                label="Description (Optional)"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                multiline
                rows={3}
                fullWidth
                sx={{ mt: 2 }}
                placeholder="Describe this orchestration run..."
              />

              <FormControlLabel
                control={
                  <Checkbox
                    checked={previewOnly}
                    onChange={(e) => setPreviewOnly(e.target.checked)}
                  />
                }
                label="Preview Only (Don't create actual shifts)"
                sx={{ mt: 2, display: 'block' }}
              />

              {error && (
                <Alert severity="error" sx={{ mt: 2 }}>
                  {error}
                </Alert>
              )}

              <Box sx={{ mt: 3 }}>
                <Button
                  type="submit"
                  variant="contained"
                  disabled={loading}
                  startIcon={loading ? <CircularProgress size={20} /> : previewOnly ? <Preview /> : <PlayArrow />}
                  sx={{ mr: 2 }}
                >
                  {loading ? 'Processing...' : previewOnly ? 'Generate Preview' : 'Apply Orchestration'}
                </Button>
                <Button
                  variant="outlined"
                  onClick={() => navigate('/calendar')}
                  disabled={loading}
                >
                  Cancel
                </Button>
              </Box>
            </form>
          </Paper>

          {/* Preview Results */}
          {result && (
            <Paper sx={{ p: 3, mt: 3 }}>
              <Typography variant="h6" gutterBottom>
                Orchestration Preview Results
              </Typography>
              
              <Grid container spacing={2}>
                <Grid item xs={12} sm={3}>
                  <Card>
                    <CardContent>
                      <Typography color="text.secondary" gutterBottom>
                        Total Shifts
                      </Typography>
                      <Typography variant="h4">
                        {result.total_shifts}
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                  <Card>
                    <CardContent>
                      <Typography color="text.secondary" gutterBottom>
                        Incidents Shifts
                      </Typography>
                      <Typography variant="h4" color="error">
                        {result.incidents_shifts}
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                  <Card>
                    <CardContent>
                      <Typography color="text.secondary" gutterBottom>
                        Incidents-Standby Shifts
                      </Typography>
                      <Typography variant="h4" color="warning.main">
                        {result.incidents_standby_shifts}
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                  <Card>
                    <CardContent>
                      <Typography color="text.secondary" gutterBottom>
                        Waakdienst Shifts
                      </Typography>
                      <Typography variant="h4" color="primary">
                        {result.waakdienst_shifts}
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                  <Card>
                    <CardContent>
                      <Typography color="text.secondary" gutterBottom>
                        Engineers Assigned
                      </Typography>
                      <Typography variant="h4" color="success.main">
                        {result.employees_assigned}
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
              </Grid>

              {/* Duplicate Warnings */}
              {(result.potential_duplicates && result.potential_duplicates.length > 0) && (
                <Alert severity="warning" sx={{ mt: 3 }}>
                  <Typography variant="h6" gutterBottom>
                    Potential Duplicate Shifts Detected ({result.potential_duplicates.length})
                  </Typography>
                  <Typography variant="body2" paragraph>
                    The following shifts already exist and would be duplicated if you apply this orchestration:
                  </Typography>
                  <Stack spacing={1}>
                    {result.potential_duplicates.map((duplicate, index) => (
                      <Chip
                        key={index}
                        label={`${duplicate.shift_type}: ${duplicate.assigned_employee} (${new Date(duplicate.start_datetime).toLocaleDateString()} - ${new Date(duplicate.end_datetime).toLocaleDateString()})`}
                        color="warning"
                        variant="outlined"
                        size="small"
                      />
                    ))}
                  </Stack>
                </Alert>
              )}

              {(result.skipped_duplicates && result.skipped_duplicates.length > 0) && (
                <Alert severity="info" sx={{ mt: 3 }}>
                  <Typography variant="h6" gutterBottom>
                    Skipped Duplicate Shifts ({result.skipped_duplicates.length})
                  </Typography>
                  <Typography variant="body2" paragraph>
                    The following shifts were skipped because they already exist:
                  </Typography>
                  <Stack spacing={1}>
                    {result.skipped_duplicates.map((duplicate, index) => (
                      <Chip
                        key={index}
                        label={`${duplicate.shift_type}: ${duplicate.assigned_employee} (${new Date(duplicate.start_datetime).toLocaleDateString()} - ${new Date(duplicate.end_datetime).toLocaleDateString()})`}
                        color="info"
                        variant="outlined"
                        size="small"
                      />
                    ))}
                  </Stack>
                </Alert>
              )}

              <Box sx={{ mt: 3 }}>
                <Typography variant="h6" gutterBottom>
                  Fairness Distribution
                </Typography>
                <Stack direction="row" spacing={1} flexWrap="wrap">
                  {Object.entries(result.fairness_scores || {}).map(([employee, score]) => (
                    <Chip
                      key={employee}
                      label={`${employee}: ${score.toFixed(1)}`}
                      color={score > result.average_fairness ? 'warning' : 'success'}
                      variant="outlined"
                    />
                  ))}
                </Stack>
                <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                  Average Fairness Score: {result.average_fairness.toFixed(2)}
                </Typography>
              </Box>

              <Box sx={{ mt: 3 }}>
                <Button
                  variant="contained"
                  color="success"
                  startIcon={<CheckCircle />}
                  onClick={handleApplyPreview}
                  disabled={loading}
                  sx={{ mr: 2 }}
                >
                  Apply This Schedule
                </Button>
                <Button
                  variant="outlined"
                  onClick={() => navigate('/calendar')}
                >
                  View Calendar
                </Button>
              </Box>
            </Paper>
          )}
        </Grid>

        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                System Information
              </Typography>
              <Typography variant="body2" paragraph>
                The orchestrator will assign shifts based on:
              </Typography>
              <ul>
                <li>Employee availability toggles</li>
                <li>Fair distribution algorithms</li>
                <li>Existing shift assignments</li>
                <li>Leave requests and conflicts</li>
              </ul>
            </CardContent>
          </Card>

          <Card sx={{ mt: 2 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Shift Types
              </Typography>
              <Box sx={{ mb: 2 }}>
                <Chip label="Incidents" color="error" sx={{ mr: 1 }} />
                <Typography variant="body2" component="span">
                  Monday-Friday, 8:00-17:00
                </Typography>
              </Box>
              <Box>
                <Chip label="Waakdienst" color="primary" sx={{ mr: 1 }} />
                <Typography variant="body2" component="span">
                  Evenings, nights & weekends
                </Typography>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default OrchestratorPage;
