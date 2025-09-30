/**
 * Unified Orchestrator Page - Comprehensive orchestrator interface
 * Combines functionality from OrchestratorPage, OrchestratorDashboard, and OrchestratorHistory
 */

import React, { useState, useEffect } from 'react';
import {
  Box,
  Container,
  Tabs,
  Tab,
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
  Card,
  CardContent,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  IconButton,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  CircularProgress,
  Divider,
} from '@mui/material';
import {
  Preview,
  CheckCircle,
  Refresh,
  AutoAwesome,
  Assessment,
  HealthAndSafety,
  Visibility,
  PlayArrow,
  History,
} from '@mui/icons-material';
import { useOrchestrator } from '../hooks/useOrchestrator';
import { apiClient } from '../services/apiClient';
import { API_CONFIG } from '../config/api';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel({ children, value, index, ...other }: TabPanelProps) {
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`orchestrator-tabpanel-${index}`}
      aria-labelledby={`orchestrator-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ py: 3 }}>{children}</Box>}
    </div>
  );
}

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

interface OrchestrationRun {
  id: number;
  name: string;
  status: 'running' | 'completed' | 'failed' | 'cancelled' | 'preview';
  start_date: string;
  end_date: string;
  created_at: string;
  completed_at?: string;
  result?: OrchestrationResult;
  error?: string;
  team?: Team;
}

const UnifiedOrchestratorPage: React.FC = () => {
  const [tabValue, setTabValue] = useState(0);
  
  // Orchestration form state
  const [startDate, setStartDate] = useState<Date | null>(getNextMonday());
  const [endDate, setEndDate] = useState<Date | null>(getEndOfYear());
  const [previewOnly, setPreviewOnly] = useState(false);
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
  
  // History state - simplified for now
  const [runs, setRuns] = useState<OrchestrationRun[]>([]);
  const [selectedRun, setSelectedRun] = useState<OrchestrationRun | null>(null);
  const [detailsOpen, setDetailsOpen] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(false);
  
  // Dashboard state from useOrchestrator hook
  const {
    state,
    isLoading: dashboardLoading,
    hasError,
    isSystemHealthy,
    isOrchestrationRunning,
    refreshSystemHealth,
    refreshMetrics,
    clearError,
  } = useOrchestrator();

  // Load teams on component mount
  useEffect(() => {
    const loadTeams = async () => {
      try {
        const teamData = await apiClient.get(API_CONFIG.ENDPOINTS.TEAMS_LIST) as any;
        // Handle both direct array and paginated response formats
        const teamsArray = Array.isArray(teamData) ? teamData : (teamData?.results || []);
        setTeams(teamsArray);
      } catch (err) {
        console.error('Failed to load teams:', err);
        setTeams([]); // Ensure teams is always an array
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
  useEffect(() => { loadAutoOverview(); }, []);

  // Reload auto overview when team changes
  useEffect(() => {
    if (selectedTeam) {
      loadAutoOverview();
    }
  }, [selectedTeam]);

  // Load orchestration history - using status endpoint for now
  const loadHistory = async () => {
    setHistoryLoading(true);
    try {
      const response = await apiClient.get(API_CONFIG.ENDPOINTS.ORCHESTRATOR_STATUS) as any;
      // Transform status data into history format for display
      setRuns(response.recent_runs || []);
    } catch (err) {
      console.error('Failed to load orchestration history:', err);
    } finally {
      setHistoryLoading(false);
    }
  };

  useEffect(() => {
    if (tabValue === 2) { // History tab
      loadHistory();
    }
  }, [tabValue]);

  // Map overview into local rolling state when team changes
  useEffect(() => {
    if (!autoOverview || !selectedTeam || !Array.isArray(autoOverview.teams)) return;
    const team = autoOverview.teams.find((t: any) => t.id === selectedTeam);
    if (team && team.rolling_enabled) setRollingEnabled(team.rolling_enabled);
  }, [autoOverview, selectedTeam]);

  function getNextMonday(): Date {
    const today = new Date();
    const dayOfWeek = today.getDay();
    const daysUntilMonday = dayOfWeek === 0 ? 1 : 8 - dayOfWeek;
    const nextMonday = new Date(today);
    nextMonday.setDate(today.getDate() + daysUntilMonday);
    return nextMonday;
  }

  function getEndOfYear(): Date {
    const today = new Date();
    return new Date(today.getFullYear(), 11, 31);
  }

  const formatDateForInput = (date: Date | null): string => {
    if (!date) return '';
    return date.toISOString().split('T')[0];
  };

  const parseInputDate = (dateStr: string): Date | null => {
    if (!dateStr) return null;
    return new Date(dateStr + 'T00:00:00');
  };

  const handleRun = async () => {
    if (!startDate || !endDate || !selectedTeam) {
      setError('Please select start date, end date, and team');
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const payload = {
        team_id: selectedTeam,
        start_date: startDate.toISOString().split('T')[0],
        end_date: endDate.toISOString().split('T')[0],
        preview_only: previewOnly,
        schedule_incidents: scheduleIncidents,
        schedule_incidents_standby: scheduleIncidentsStandby,
        schedule_waakdienst: scheduleWaakdienst,
        rolling_enabled: rollingEnabled,
      };

      const response = await apiClient.post(API_CONFIG.ENDPOINTS.ORCHESTRATOR_CREATE, payload) as any;
      setResult(response);

      if (!previewOnly && response.total_shifts > 0) {
        // Refresh history if we're on the history tab
        if (tabValue === 2) {
          loadHistory();
        }
      }
    } catch (err: any) {
      setError(err.response?.data?.error || err.message || 'Failed to run orchestrator');
    } finally {
      setLoading(false);
    }
  };

  const handleTabChange = (_: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  const handleRefreshDashboard = async () => {
    try {
      await Promise.all([
        refreshSystemHealth(),
        refreshMetrics(),
      ]);
    } catch (error) {
      console.error('Failed to refresh dashboard data:', error);
    }
  };

  const toggleRolling = async (shiftType: 'incidents'|'incidents_standby'|'waakdienst', enabled: boolean) => {
    console.log('toggleRolling called:', { shiftType, enabled, selectedTeam });
    console.log('API_CONFIG endpoints:', API_CONFIG.ENDPOINTS);
    console.log('AUTO_TOGGLE endpoint:', API_CONFIG.ENDPOINTS.ORCHESTRATOR_AUTO_TOGGLE);
    
    if (!selectedTeam) {
      console.error('No team selected');
      setError('Please select a team first');
      return;
    }

    try {
      console.log('Making API call to:', API_CONFIG.ENDPOINTS.ORCHESTRATOR_AUTO_TOGGLE);
      const payload = { 
        team_id: selectedTeam, 
        shift_type: shiftType, 
        enabled 
      };
      console.log('Payload:', payload);
      
      const res = await apiClient.post(API_CONFIG.ENDPOINTS.ORCHESTRATOR_AUTO_TOGGLE, payload) as any;
      console.log('API response:', res);
      
      setRollingEnabled((prev) => ({ ...prev, [shiftType]: !!res.enabled }));
      await loadAutoOverview();
      console.log('Toggle completed successfully');
    } catch (e: any) {
      console.error('Toggle error:', e);
      setError(e?.data?.error || e?.message || 'Failed to toggle rolling planning');
    }
  };

  const getStatusColor = () => {
    if (isOrchestrationRunning) return 'warning';
    if (hasError) return 'error';
    if (isSystemHealthy) return 'success';
    return 'default';
  };

  const getStatusText = () => {
    if (isOrchestrationRunning) return 'Orchestration Running';
    if (hasError) return 'Error Detected';
    if (isSystemHealthy) return 'System Healthy';
    return 'Status Unknown';
  };

  const formatDateTime = (dateStr: string) => {
    return new Date(dateStr).toLocaleString();
  };

  const getStatusChip = (status: string) => {
    const statusConfig = {
      running: { color: 'warning' as const, label: 'Running' },
      completed: { color: 'success' as const, label: 'Completed' },
      failed: { color: 'error' as const, label: 'Failed' },
      cancelled: { color: 'default' as const, label: 'Cancelled' },
      preview: { color: 'info' as const, label: 'Preview' },
    };

    const config = statusConfig[status as keyof typeof statusConfig] || 
                  { color: 'default' as const, label: status };
    
    return <Chip size="small" color={config.color} label={config.label} />;
  };

  const handleViewDetails = (run: OrchestrationRun) => {
    setSelectedRun(run);
    setDetailsOpen(true);
  };

  return (
    <Container maxWidth="xl" sx={{ py: 3 }}>
      {/* Header */}
      <Box sx={{ mb: 3 }}>
        <Grid container alignItems="center" justifyContent="space-between">
          <Grid item>
            <Typography variant="h4" component="h1" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <AutoAwesome color="primary" />
              Orchestrator Control Center
            </Typography>
            <Typography variant="subtitle1" color="text.secondary">
              Intelligent shift scheduling, monitoring, and management
            </Typography>
          </Grid>
          <Grid item>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              <Chip 
                label={getStatusText()}
                color={getStatusColor() as any}
                icon={<HealthAndSafety />}
              />
              <Button
                variant="outlined"
                startIcon={<Refresh />}
                onClick={handleRefreshDashboard}
                disabled={dashboardLoading}
              >
                Refresh
              </Button>
            </Box>
          </Grid>
        </Grid>
      </Box>

      {/* Error Alert */}
      {(hasError || error) && (
        <Alert 
          severity="error" 
          sx={{ mb: 3 }}
          onClose={() => {
            if (hasError) clearError();
            if (error) setError(null);
          }}
        >
          {hasError ? state.error : error}
        </Alert>
      )}

      {/* Main Tabs */}
      <Paper sx={{ mb: 3 }}>
        <Tabs
          value={tabValue}
          onChange={handleTabChange}
          variant="fullWidth"
          sx={{ borderBottom: 1, borderColor: 'divider' }}
        >
          <Tab 
            icon={<PlayArrow />} 
            label="Run Orchestration" 
            id="orchestrator-tab-0"
            aria-controls="orchestrator-tabpanel-0"
          />
          <Tab 
            icon={<Assessment />} 
            label="Dashboard" 
            id="orchestrator-tab-1"
            aria-controls="orchestrator-tabpanel-1"
          />
          <Tab 
            icon={<History />} 
            label="History" 
            id="orchestrator-tab-2"
            aria-controls="orchestrator-tabpanel-2"
          />
        </Tabs>

        {/* Tab 1: Run Orchestration */}
        <TabPanel value={tabValue} index={0}>
          <Grid container spacing={3}>
            <Grid item xs={12} md={6}>
              <Paper sx={{ p: 3 }}>
                <Typography variant="h6" gutterBottom>
                  Orchestration Settings
                </Typography>
                
                <Grid container spacing={2}>
                  <Grid item xs={12}>
                    <FormControl fullWidth>
                      <InputLabel>Team</InputLabel>
                      <Select
                        value={selectedTeam}
                        onChange={(e) => setSelectedTeam(e.target.value as number)}
                        label="Team"
                      >
                        {Array.isArray(teams) && teams.map((team) => (
                          <MenuItem key={team.id} value={team.id}>
                            {team.name}
                          </MenuItem>
                        ))}
                      </Select>
                    </FormControl>
                  </Grid>
                  
                  <Grid item xs={6}>
                    <TextField
                      fullWidth
                      label="Start Date"
                      type="date"
                      value={formatDateForInput(startDate)}
                      onChange={(e) => setStartDate(parseInputDate(e.target.value))}
                      InputLabelProps={{ shrink: true }}
                    />
                  </Grid>
                  
                  <Grid item xs={6}>
                    <TextField
                      fullWidth
                      label="End Date"
                      type="date"
                      value={formatDateForInput(endDate)}
                      onChange={(e) => setEndDate(parseInputDate(e.target.value))}
                      InputLabelProps={{ shrink: true }}
                    />
                  </Grid>
                </Grid>

                <Typography variant="h6" sx={{ mt: 3, mb: 1 }}>
                  Shift Types
                </Typography>
                
                <Stack spacing={1}>
                  <FormControlLabel
                    control={
                      <Checkbox
                        checked={scheduleIncidents}
                        onChange={(e) => setScheduleIncidents(e.target.checked)}
                      />
                    }
                    label="Schedule Incidents"
                  />
                  <FormControlLabel
                    control={
                      <Checkbox
                        checked={scheduleIncidentsStandby}
                        onChange={(e) => setScheduleIncidentsStandby(e.target.checked)}
                      />
                    }
                    label="Schedule Incidents Standby"
                  />
                  <FormControlLabel
                    control={
                      <Checkbox
                        checked={scheduleWaakdienst}
                        onChange={(e) => setScheduleWaakdienst(e.target.checked)}
                      />
                    }
                    label="Schedule Waakdienst"
                  />
                </Stack>

                <Typography variant="h6" sx={{ mt: 3, mb: 1 }}>
                  Options
                </Typography>
                
                <FormControlLabel
                  control={
                    <Checkbox
                      checked={previewOnly}
                      onChange={(e) => setPreviewOnly(e.target.checked)}
                    />
                  }
                  label="Preview Only (don't save to database)"
                />

                <Box sx={{ mt: 3 }}>
                  <Button
                    variant="contained"
                    size="large"
                    startIcon={previewOnly ? <Preview /> : <CheckCircle />}
                    onClick={handleRun}
                    disabled={loading || !selectedTeam}
                    fullWidth
                  >
                    {loading ? 'Running...' : (previewOnly ? 'Preview Orchestration' : 'Run Orchestration')}
                  </Button>
                </Box>
              </Paper>
            </Grid>

            <Grid item xs={12} md={6}>
              {result && (
                <Paper sx={{ p: 3 }}>
                  <Typography variant="h6" gutterBottom>
                    Orchestration Results
                  </Typography>
                  
                  <Grid container spacing={2}>
                    <Grid item xs={6}>
                      <Typography variant="body2" color="text.secondary">
                        Total Shifts
                      </Typography>
                      <Typography variant="h6">{result.total_shifts}</Typography>
                    </Grid>
                    <Grid item xs={6}>
                      <Typography variant="body2" color="text.secondary">
                        Employees Assigned
                      </Typography>
                      <Typography variant="h6">{result.employees_assigned}</Typography>
                    </Grid>
                    <Grid item xs={4}>
                      <Typography variant="body2" color="text.secondary">
                        Incidents
                      </Typography>
                      <Typography variant="h6">{result.incidents_shifts}</Typography>
                    </Grid>
                    <Grid item xs={4}>
                      <Typography variant="body2" color="text.secondary">
                        Incidents Standby
                      </Typography>
                      <Typography variant="h6">{result.incidents_standby_shifts}</Typography>
                    </Grid>
                    <Grid item xs={4}>
                      <Typography variant="body2" color="text.secondary">
                        Waakdienst
                      </Typography>
                      <Typography variant="h6">{result.waakdienst_shifts}</Typography>
                    </Grid>
                    <Grid item xs={12}>
                      <Typography variant="body2" color="text.secondary">
                        Average Fairness Score
                      </Typography>
                      <Typography variant="h6">
                        {result.average_fairness?.toFixed(2) || 'N/A'}
                      </Typography>
                    </Grid>
                  </Grid>

                  {result.potential_duplicates && result.potential_duplicates.length > 0 && (
                    <Box sx={{ mt: 2 }}>
                      <Alert severity="warning">
                        Found {result.potential_duplicates.length} potential duplicate shifts
                      </Alert>
                    </Box>
                  )}
                </Paper>
              )}
            </Grid>
          </Grid>

          {/* Rolling Planning Controls */}
          <Grid container spacing={3} sx={{ mt: 2 }}>
            <Grid item xs={12}>
              <Paper sx={{ p: 3 }}>
                <Typography variant="h6" gutterBottom>
                  Rolling Planning Controls
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  Enable or disable automatic rolling planning per shift type for the selected team.
                </Typography>
                
                {autoOverview && selectedTeam && Array.isArray(autoOverview.teams) && (
                  <Box sx={{ mb: 2 }}>
                    <Alert severity={autoOverview.teams.find((t:any)=>t.id===selectedTeam)?.seed_ready ? 'success' : 'warning'}>
                      {autoOverview.teams.find((t:any)=>t.id===selectedTeam)?.seed_ready 
                        ? 'Initial 6-month plan detected - rolling planning can be enabled' 
                        : 'Needs initial 6-month plan to enable rolling planning'}
                    </Alert>
                  </Box>
                )}

                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                  <Typography variant="subtitle2">Rolling Status (per shift type):</Typography>
                  <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mb: 2 }}>
                    {(['incidents','incidents_standby','waakdienst'] as const).map(st => (
                      <Chip 
                        key={st} 
                        label={`${st}: ${rollingEnabled?.[st] ? 'ON' : 'OFF'}`} 
                        color={rollingEnabled?.[st] ? 'success' : 'default'} 
                      />
                    ))}
                  </Box>
                  
                  <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2 }}>
                    {(['incidents','incidents_standby','waakdienst'] as const).map(st => (
                      <Box key={st} sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Chip label={st} size="small" />
                        <Button
                          size="small"
                          variant={rollingEnabled?.[st] ? 'contained' : 'outlined'}
                          color={rollingEnabled?.[st] ? 'success' : 'primary'}
                          onClick={() => {
                            console.log('Button clicked for:', st, 'current state:', rollingEnabled?.[st]);
                            toggleRolling(st, !rollingEnabled?.[st]);
                          }}
                          disabled={!selectedTeam || loading}
                        >
                          {rollingEnabled?.[st] ? 'Disable' : 'Enable'}
                        </Button>
                      </Box>
                    ))}
                  </Box>
                </Box>
              </Paper>
            </Grid>
          </Grid>
        </TabPanel>

        {/* Tab 2: Dashboard */}
        <TabPanel value={tabValue} index={1}>
          {/* Quick Stats */}
          <Grid container spacing={3} sx={{ mb: 3 }}>
            <Grid item xs={12} sm={6} md={3}>
              <Card>
                <CardContent sx={{ textAlign: 'center' }}>
                  <Typography variant="h4" color="primary">
                    {state.systemMetrics?.total_active_employees || 0}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Active Employees
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <Card>
                <CardContent sx={{ textAlign: 'center' }}>
                  <Typography variant="h4" color="primary">
                    {state.systemMetrics?.assignment_rate_percentage?.toFixed(1) || 0}%
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Assignment Rate
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <Card>
                <CardContent sx={{ textAlign: 'center' }}>
                  <Typography variant="h4" color="primary">
                    {state.systemMetrics?.total_shifts_last_30_days || 0}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Shifts (30 days)
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <Card>
                <CardContent sx={{ textAlign: 'center' }}>
                  <Typography variant="h4" color="primary">
                    {state.systemMetrics?.unassigned_shifts_last_30_days || 0}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Unassigned Shifts
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          </Grid>

          {/* Last Orchestration */}
          {state.lastOrchestration && (
            <Card sx={{ mb: 3 }}>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Last Orchestration
                </Typography>
                <Grid container spacing={2}>
                  <Grid item xs={12} sm={6}>
                    <Typography variant="body2" color="text.secondary">
                      Assignments Made
                    </Typography>
                    <Typography variant="h6">
                      {state.lastOrchestration.statistics?.assignments_made || 0}
                    </Typography>
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <Typography variant="body2" color="text.secondary">
                      Unassigned Shifts
                    </Typography>
                    <Typography variant="h6">
                      {state.lastOrchestration.statistics?.unassigned_shifts || 0}
                    </Typography>
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <Typography variant="body2" color="text.secondary">
                      Conflicts Detected
                    </Typography>
                    <Typography variant="body1">
                      {state.lastOrchestration.statistics?.conflicts_detected || 0}
                    </Typography>
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <Typography variant="body2" color="text.secondary">
                      Warnings
                    </Typography>
                    <Typography variant="body1">
                      {state.lastOrchestration.statistics?.warnings || 0}
                    </Typography>
                  </Grid>
                </Grid>

                {state.lastOrchestration.warnings && state.lastOrchestration.warnings.length > 0 && (
                  <div>
                    <Typography variant="body2" color="text.secondary" gutterBottom>
                      Warning Messages
                    </Typography>
                    {state.lastOrchestration.warnings.map((warning: string, index: number) => (
                      <Alert key={index} severity="warning" sx={{ mb: 1 }}>
                        {warning}
                      </Alert>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          )}
        </TabPanel>

        {/* Tab 3: History */}
        <TabPanel value={tabValue} index={2}>
          {historyLoading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
              <CircularProgress />
            </Box>
          ) : (
            <TableContainer component={Paper}>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Name</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell>Team</TableCell>
                    <TableCell>Date Range</TableCell>
                    <TableCell>Created</TableCell>
                    <TableCell>Total Shifts</TableCell>
                    <TableCell align="right">Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {runs.map((run) => (
                    <TableRow key={run.id}>
                      <TableCell>{run.name || `Run #${run.id}`}</TableCell>
                      <TableCell>{getStatusChip(run.status)}</TableCell>
                      <TableCell>{run.team?.name || 'N/A'}</TableCell>
                      <TableCell>
                        {run.start_date} to {run.end_date}
                      </TableCell>
                      <TableCell>{formatDateTime(run.created_at)}</TableCell>
                      <TableCell>{run.result?.total_shifts || 0}</TableCell>
                      <TableCell align="right">
                        <Tooltip title="View Details">
                          <IconButton onClick={() => handleViewDetails(run)}>
                            <Visibility />
                          </IconButton>
                        </Tooltip>
                      </TableCell>
                    </TableRow>
                  ))}
                  {runs.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={7} align="center">
                        No orchestration runs found
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </TabPanel>
      </Paper>

      {/* Details Dialog */}
      <Dialog 
        open={detailsOpen} 
        onClose={() => setDetailsOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          Orchestration Run Details
        </DialogTitle>
        <DialogContent>
          {selectedRun && (
            <Box>
              <Grid container spacing={2}>
                <Grid item xs={6}>
                  <Typography variant="body2" color="text.secondary">
                    Status
                  </Typography>
                  <Typography variant="body1">
                    {getStatusChip(selectedRun.status)}
                  </Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="body2" color="text.secondary">
                    Team
                  </Typography>
                  <Typography variant="body1">
                    {selectedRun.team?.name || 'N/A'}
                  </Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="body2" color="text.secondary">
                    Date Range
                  </Typography>
                  <Typography variant="body1">
                    {selectedRun.start_date} to {selectedRun.end_date}
                  </Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="body2" color="text.secondary">
                    Created
                  </Typography>
                  <Typography variant="body1">
                    {formatDateTime(selectedRun.created_at)}
                  </Typography>
                </Grid>
              </Grid>

              {selectedRun.result && (
                <>
                  <Divider sx={{ my: 2 }} />
                  <Typography variant="h6" gutterBottom>
                    Results
                  </Typography>
                  <Grid container spacing={2}>
                    <Grid item xs={3}>
                      <Typography variant="body2" color="text.secondary">
                        Total Shifts
                      </Typography>
                      <Typography variant="h6">{selectedRun.result.total_shifts}</Typography>
                    </Grid>
                    <Grid item xs={3}>
                      <Typography variant="body2" color="text.secondary">
                        Incidents
                      </Typography>
                      <Typography variant="h6">{selectedRun.result.incidents_shifts}</Typography>
                    </Grid>
                    <Grid item xs={3}>
                      <Typography variant="body2" color="text.secondary">
                        Incidents Standby
                      </Typography>
                      <Typography variant="h6">{selectedRun.result.incidents_standby_shifts}</Typography>
                    </Grid>
                    <Grid item xs={3}>
                      <Typography variant="body2" color="text.secondary">
                        Waakdienst
                      </Typography>
                      <Typography variant="h6">{selectedRun.result.waakdienst_shifts}</Typography>
                    </Grid>
                    <Grid item xs={6}>
                      <Typography variant="body2" color="text.secondary">
                        Employees Assigned
                      </Typography>
                      <Typography variant="h6">{selectedRun.result.employees_assigned}</Typography>
                    </Grid>
                    <Grid item xs={6}>
                      <Typography variant="body2" color="text.secondary">
                        Average Fairness
                      </Typography>
                      <Typography variant="h6">
                        {selectedRun.result.average_fairness?.toFixed(2) || 'N/A'}
                      </Typography>
                    </Grid>
                  </Grid>
                </>
              )}

              {selectedRun.error && (
                <>
                  <Divider sx={{ my: 2 }} />
                  <Alert severity="error">
                    {selectedRun.error}
                  </Alert>
                </>
              )}
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDetailsOpen(false)}>
            Close
          </Button>
        </DialogActions>
      </Dialog>

      {/* Loading Overlay */}
      {(loading || dashboardLoading) && (
        <Box
          sx={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.5)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 9999,
          }}
        >
          <Card sx={{ p: 3, textAlign: 'center' }}>
            <CircularProgress sx={{ mb: 2 }} />
            <Typography variant="h6">
              {loading ? 'Running Orchestration...' : 'Loading...'}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              This may take a few moments
            </Typography>
          </Card>
        </Box>
      )}
    </Container>
  );
};

export default UnifiedOrchestratorPage;
