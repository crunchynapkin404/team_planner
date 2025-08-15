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
  Alert,
  Chip,
  Stack,
  MenuItem,
  Select,
  FormControl,
  InputLabel,
} from '@mui/material';
import { Preview, CheckCircle } from '@mui/icons-material';
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
  const [previewOnly, setPreviewOnly] = useState(true);
  const [scheduleIncidents, setScheduleIncidents] = useState(true);
  const [scheduleIncidentsStandby, setScheduleIncidentsStandby] = useState(false);
  const [scheduleWaakdienst, setScheduleWaakdienst] = useState(true);
  const [selectedTeam, setSelectedTeam] = useState<number | ''>('');
  const [teams, setTeams] = useState<Team[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [autoOverview, setAutoOverview] = useState<any | null>(null);
  const [rollingEnabled, setRollingEnabled] = useState<Record<string, boolean>>({});
  const [result, setResult] = useState<OrchestrationResult | null>(null);
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

  // Load auto overview
  const loadAutoOverview = async () => {
    try {
      const res = await apiClient.get(API_CONFIG.ENDPOINTS.ORCHESTRATOR_AUTO_OVERVIEW) as any;
      setAutoOverview(res);
    } catch (e) {
      // ignore
    }
  };
  React.useEffect(() => { loadAutoOverview(); }, []);

  // Map overview into local rolling state when team changes
  React.useEffect(() => {
    if (!autoOverview || !selectedTeam) return;
    const team = autoOverview.teams.find((t: any) => t.id === selectedTeam);
    if (team && team.rolling_enabled) setRollingEnabled(team.rolling_enabled);
  }, [autoOverview, selectedTeam]);

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
    // Force preview for manual seeding flow
    setPreviewOnly(true);

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
        start_date: startDate.toISOString().split('T')[0],
        end_date: endDate.toISOString().split('T')[0],
        preview_only: true,
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

  const toggleRolling = async (shiftType: 'incidents'|'incidents_standby'|'waakdienst', enabled: boolean) => {
    try {
      const res = await apiClient.post(API_CONFIG.ENDPOINTS.ORCHESTRATOR_AUTO_TOGGLE, { team_id: selectedTeam, shift_type: shiftType, enabled }) as any;
      setRollingEnabled((prev) => ({ ...prev, [shiftType]: !!res.enabled }));
      await loadAutoOverview();
    } catch (e: any) {
      setError(e?.data?.error || e?.message || 'Failed to toggle');
    }
  };

  // Simplified UI helpers
  const defaultSixMonths = () => {
    const today = new Date();
    const end = new Date(today);
    end.setDate(end.getDate() + 7 * 26);
    setStartDate(getNextMonday());
    setEndDate(end);
  };

  React.useEffect(() => { defaultSixMonths(); }, []);

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>Orchestrator</Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      <Paper sx={{ p: 2, mb: 2 }}>
        <Grid container spacing={2}>
          <Grid item xs={12} md={6}>
            <FormControl fullWidth required>
              <InputLabel>Team</InputLabel>
              <Select
                value={selectedTeam}
                onChange={(e) => setSelectedTeam(e.target.value as number)}
                label="Team"
              >
                {teams.map((t) => (
                  <MenuItem key={t.id} value={t.id}>
                    {t.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            {autoOverview && selectedTeam && (
              <Box sx={{ mt: 1 }}>
                <Alert severity={autoOverview.teams.find((t:any)=>t.id===selectedTeam)?.seed_ready ? 'success' : 'warning'}>
                  {autoOverview.teams.find((t:any)=>t.id===selectedTeam)?.seed_ready ? 'Initial 6-month plan detected' : 'Needs initial 6-month plan to enable rolling'}
                </Alert>
              </Box>
            )}
          </Grid>
          <Grid item xs={12} md={6}>
            <Typography variant="subtitle2">Rolling status (per shift type)</Typography>
            <Stack direction="row" spacing={1} sx={{ mt: 1, flexWrap: 'wrap' }}>
              {(['incidents','incidents_standby','waakdienst'] as const).map(st => (
                <Chip key={st} label={`${st}: ${rollingEnabled?.[st] ? 'ON' : 'OFF'}`} color={rollingEnabled?.[st] ? 'success' : 'default'} />
              ))}
            </Stack>
          </Grid>
        </Grid>
      </Paper>

      <Paper sx={{ p: 2, mb: 2 }}>
        <Typography variant="h6">Create initial 6-month plan (manual)</Typography>
        <Typography variant="body2" color="text.secondary">Pick a shift type and generate a preview, then apply to seed the team.</Typography>
        <Grid container spacing={2} sx={{ mt: 1 }}>
          <Grid item xs={12} sm={4}>
            <TextField
              label="Start"
              type="date"
              value={startDate ? startDate.toISOString().split('T')[0] : ''}
              onChange={(e)=>setStartDate(e.target.value? new Date(e.target.value): null)}
              fullWidth
              InputLabelProps={{
                shrink: true,
              }}
            />
          </Grid>
          <Grid item xs={12} sm={4}>
            <TextField
              label="End (≈6 months)"
              type="date"
              value={endDate ? endDate.toISOString().split('T')[0] : ''}
              onChange={(e)=>setEndDate(e.target.value? new Date(e.target.value): null)}
              fullWidth
              InputLabelProps={{
                shrink: true,
              }}
            />
          </Grid>
          <Grid item xs={12}>
            <Stack direction="row" spacing={2}>
              <FormControlLabel
                control={
                  <Checkbox
                    checked={scheduleIncidents}
                    onChange={(e)=>{setScheduleIncidents(e.target.checked); setScheduleIncidentsStandby(false); setScheduleWaakdienst(false);}}
                  />
                }
                label="Incidents"
              />
              <FormControlLabel
                control={
                  <Checkbox
                    checked={scheduleIncidentsStandby}
                    onChange={(e)=>{setScheduleIncidentsStandby(e.target.checked); setScheduleIncidents(false); setScheduleWaakdienst(false);}}
                  />
                }
                label="Incidents-Standby"
              />
              <FormControlLabel
                control={
                  <Checkbox
                    checked={scheduleWaakdienst}
                    onChange={(e)=>{setScheduleWaakdienst(e.target.checked); setScheduleIncidents(false); setScheduleIncidentsStandby(false);}}
                  />
                }
                label="Waakdienst"
              />
            </Stack>
          </Grid>
          <Grid item xs={12}>
            <Stack direction="row" spacing={1}>
              <Button
                variant="contained"
                startIcon={<Preview />}
                onClick={handleSubmit}
                disabled={!selectedTeam || loading}
              >
                Preview
              </Button>
              <Button
                variant="outlined"
                startIcon={<CheckCircle />}
                onClick={handleApplyPreview}
                disabled={!result || loading}
              >
                Apply
              </Button>
            </Stack>
          </Grid>
        </Grid>
        {result && (
          <Alert severity="info" sx={{ mt: 2 }}>Preview ready: {result.total_shifts} shifts. Apply to create.</Alert>
        )}
      </Paper>

      <Paper sx={{ p: 2 }}>
        <Typography variant="h6">Rolling planning controls</Typography>
        <Typography variant="body2" color="text.secondary">Enable or disable auto-rolling per shift type for the selected team.</Typography>
        <Stack direction="row" spacing={2} sx={{ mt: 1, flexWrap: 'wrap' }}>
          {(['incidents','incidents_standby','waakdienst'] as const).map(st => (
            <Stack key={st} direction="row" spacing={1} alignItems="center">
              <Chip label={st} />
              <Button
                size="small"
                variant={rollingEnabled?.[st] ? 'contained' : 'outlined'}
                onClick={()=>toggleRolling(st, !rollingEnabled?.[st])}
                disabled={!selectedTeam}
              >
                {rollingEnabled?.[st] ? 'Disable' : 'Enable'}
              </Button>
            </Stack>
          ))}
        </Stack>
      </Paper>
    </Box>
  );
};

export default OrchestratorPage;
