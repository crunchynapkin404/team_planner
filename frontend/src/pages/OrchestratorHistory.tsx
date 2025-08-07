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
  Chip,
  IconButton,
  Tooltip,
  Stack,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  CircularProgress,
  Alert,
  Grid,
  Card,
  CardContent,
  LinearProgress,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
} from '@mui/material';
import {
  Visibility,
  Refresh,
  Delete,
  PlayArrow,
  Stop,
  History,
  Assessment,
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { apiClient } from '../services/apiClient';
import { API_CONFIG } from '../config/api';

interface OrchestrationRun {
  id: number;
  name: string;
  status: 'running' | 'completed' | 'failed' | 'cancelled' | 'preview';
  start_date: string;
  end_date: string;
  total_shifts: number;
  incidents_shifts: number;
  waakdienst_shifts: number;
  created_at: string;
  completed_at: string | null;
  initiated_by: string;
  description: string;
  duration: number | null;
  error_message: string | null;
}

interface SystemStatus {
  eligible_incidents: number;
  eligible_waakdienst: number;
  recent_runs: OrchestrationRun[];
  system_status: string;
  active_runs: number;
  success_rate: number;
}

const OrchestratorHistory: React.FC = () => {
  const [runs, setRuns] = useState<OrchestrationRun[]>([]);
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedRun, setSelectedRun] = useState<OrchestrationRun | null>(null);
  const [detailsOpen, setDetailsOpen] = useState(false);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const navigate = useNavigate();

  const loadData = async () => {
    setLoading(true);
    setError(null);
    
    try {
      // Load system status and recent runs
      const statusData = await apiClient.get(API_CONFIG.ENDPOINTS.ORCHESTRATOR_STATUS) as any;
      setSystemStatus(statusData);
      setRuns(statusData.recent_runs || []);
    } catch (err) {
      setError('Network error occurred');
      console.error('Orchestrator status error:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    // Refresh every 30 seconds for real-time updates
    const interval = setInterval(loadData, 30000);
    return () => clearInterval(interval);
  }, []);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'success';
      case 'running': return 'info';
      case 'preview': return 'warning';
      case 'failed': return 'error';
      case 'cancelled': return 'default';
      default: return 'default';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed': return '✅';
      case 'running': return '🔄';
      case 'preview': return '👁️';
      case 'failed': return '❌';
      case 'cancelled': return '⏹️';
      default: return '❓';
    }
  };

  const handleViewDetails = (run: OrchestrationRun) => {
    setSelectedRun(run);
    setDetailsOpen(true);
  };

  const filteredRuns = runs.filter(run => 
    statusFilter === 'all' || run.status === statusFilter
  );

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: 400 }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" gutterBottom>
          Orchestrator Management
        </Typography>
        <Stack direction="row" spacing={2}>
          <Button
            variant="contained"
            startIcon={<PlayArrow />}
            onClick={() => navigate('/orchestrator')}
          >
            New Orchestration
          </Button>
          <Button
            variant="outlined"
            startIcon={<Assessment />}
            onClick={() => navigate('/fairness')}
          >
            Fairness Dashboard
          </Button>
          <Tooltip title="Refresh">
            <IconButton onClick={loadData}>
              <Refresh />
            </IconButton>
          </Tooltip>
        </Stack>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      {/* System Status Overview */}
      {systemStatus && (
        <Grid container spacing={3} sx={{ mb: 3 }}>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Typography color="text.secondary" gutterBottom>
                  System Status
                </Typography>
                <Typography variant="h6" color={systemStatus.system_status === 'operational' ? 'success.main' : 'error.main'}>
                  {systemStatus.system_status === 'operational' ? '🟢 Operational' : '🔴 Issues'}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Typography color="text.secondary" gutterBottom>
                  Incidents Available
                </Typography>
                <Typography variant="h4" color="error">
                  {systemStatus.eligible_incidents}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Typography color="text.secondary" gutterBottom>
                  Waakdienst Available
                </Typography>
                <Typography variant="h4" color="primary">
                  {systemStatus.eligible_waakdienst}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Typography color="text.secondary" gutterBottom>
                  Success Rate
                </Typography>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <LinearProgress
                    variant="determinate"
                    value={systemStatus.success_rate || 0}
                    color="success"
                    sx={{ width: 60, height: 8, borderRadius: 4 }}
                  />
                  <Typography variant="h6">
                    {(systemStatus.success_rate || 0).toFixed(0)}%
                  </Typography>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {/* Orchestration History */}
      <Paper sx={{ p: 3 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h6" gutterBottom>
            Orchestration History
          </Typography>
          <FormControl size="small" sx={{ minWidth: 120 }}>
            <InputLabel>Status Filter</InputLabel>
            <Select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              label="Status Filter"
            >
              <MenuItem value="all">All</MenuItem>
              <MenuItem value="completed">Completed</MenuItem>
              <MenuItem value="running">Running</MenuItem>
              <MenuItem value="preview">Preview</MenuItem>
              <MenuItem value="failed">Failed</MenuItem>
              <MenuItem value="cancelled">Cancelled</MenuItem>
            </Select>
          </FormControl>
        </Box>

        <TableContainer>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Name</TableCell>
                <TableCell align="center">Status</TableCell>
                <TableCell align="center">Period</TableCell>
                <TableCell align="center">Shifts Created</TableCell>
                <TableCell align="center">Started</TableCell>
                <TableCell align="center">Duration</TableCell>
                <TableCell align="center">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {filteredRuns.map((run) => (
                <TableRow key={run.id} hover>
                  <TableCell component="th" scope="row">
                    <Typography variant="body2" fontWeight="bold">
                      {run.name}
                    </Typography>
                    {run.description && (
                      <Typography variant="caption" color="text.secondary" display="block">
                        {run.description}
                      </Typography>
                    )}
                  </TableCell>
                  <TableCell align="center">
                    <Chip
                      icon={<span>{getStatusIcon(run.status)}</span>}
                      label={run.status.charAt(0).toUpperCase() + run.status.slice(1)}
                      color={getStatusColor(run.status) as any}
                      size="small"
                    />
                  </TableCell>
                  <TableCell align="center">
                    <Typography variant="body2">
                      {new Date(run.start_date).toLocaleDateString()} -
                    </Typography>
                    <Typography variant="body2">
                      {new Date(run.end_date).toLocaleDateString()}
                    </Typography>
                  </TableCell>
                  <TableCell align="center">
                    <Stack direction="column" spacing={0.5} alignItems="center">
                      <Typography variant="body2" fontWeight="bold">
                        {run.total_shifts || 0}
                      </Typography>
                      <Stack direction="row" spacing={0.5}>
                        {run.incidents_shifts > 0 && (
                          <Chip label={`I:${run.incidents_shifts}`} color="error" size="small" />
                        )}
                        {run.waakdienst_shifts > 0 && (
                          <Chip label={`W:${run.waakdienst_shifts}`} color="primary" size="small" />
                        )}
                      </Stack>
                    </Stack>
                  </TableCell>
                  <TableCell align="center">
                    <Typography variant="body2">
                      {new Date(run.created_at).toLocaleString()}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      by {run.initiated_by}
                    </Typography>
                  </TableCell>
                  <TableCell align="center">
                    <Typography variant="body2">
                      {run.duration 
                        ? `${Math.round(run.duration / 1000)}s`
                        : run.status === 'running' 
                          ? '⏳ Running'
                          : '-'
                      }
                    </Typography>
                  </TableCell>
                  <TableCell align="center">
                    <Stack direction="row" spacing={1} justifyContent="center">
                      <Tooltip title="View Details">
                        <IconButton
                          size="small"
                          onClick={() => handleViewDetails(run)}
                        >
                          <Visibility />
                        </IconButton>
                      </Tooltip>
                      {run.status === 'running' && (
                        <Tooltip title="Stop">
                          <IconButton size="small" color="error">
                            <Stop />
                          </IconButton>
                        </Tooltip>
                      )}
                      {(run.status === 'failed' || run.status === 'cancelled') && (
                        <Tooltip title="Delete">
                          <IconButton size="small" color="error">
                            <Delete />
                          </IconButton>
                        </Tooltip>
                      )}
                    </Stack>
                  </TableCell>
                </TableRow>
              ))}
              {filteredRuns.length === 0 && (
                <TableRow>
                  <TableCell colSpan={7} align="center">
                    <Typography color="text.secondary" sx={{ py: 2 }}>
                      {statusFilter === 'all' 
                        ? 'No orchestrations found' 
                        : `No ${statusFilter} orchestrations found`
                      }
                    </Typography>
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </TableContainer>
      </Paper>

      {/* Details Dialog */}
      <Dialog
        open={detailsOpen}
        onClose={() => setDetailsOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          <Stack direction="row" alignItems="center" spacing={2}>
            <History />
            <Typography variant="h6">
              Orchestration Details
            </Typography>
          </Stack>
        </DialogTitle>
        <DialogContent>
          {selectedRun && (
            <Grid container spacing={2}>
              <Grid item xs={12} sm={6}>
                <Typography variant="subtitle2" color="text.secondary">
                  Name
                </Typography>
                <Typography variant="body1" gutterBottom>
                  {selectedRun.name}
                </Typography>
              </Grid>
              <Grid item xs={12} sm={6}>
                <Typography variant="subtitle2" color="text.secondary">
                  Status
                </Typography>
                <Chip
                  icon={<span>{getStatusIcon(selectedRun.status)}</span>}
                  label={selectedRun.status.charAt(0).toUpperCase() + selectedRun.status.slice(1)}
                  color={getStatusColor(selectedRun.status) as any}
                  size="small"
                />
              </Grid>
              <Grid item xs={12}>
                <Typography variant="subtitle2" color="text.secondary">
                  Description
                </Typography>
                <Typography variant="body1" gutterBottom>
                  {selectedRun.description || 'No description provided'}
                </Typography>
              </Grid>
              <Grid item xs={12} sm={6}>
                <Typography variant="subtitle2" color="text.secondary">
                  Planning Period
                </Typography>
                <Typography variant="body1" gutterBottom>
                  {new Date(selectedRun.start_date).toLocaleDateString()} - {new Date(selectedRun.end_date).toLocaleDateString()}
                </Typography>
              </Grid>
              <Grid item xs={12} sm={6}>
                <Typography variant="subtitle2" color="text.secondary">
                  Initiated By
                </Typography>
                <Typography variant="body1" gutterBottom>
                  {selectedRun.initiated_by}
                </Typography>
              </Grid>
              <Grid item xs={12} sm={4}>
                <Typography variant="subtitle2" color="text.secondary">
                  Total Shifts
                </Typography>
                <Typography variant="h4" color="success.main">
                  {selectedRun.total_shifts || 0}
                </Typography>
              </Grid>
              <Grid item xs={12} sm={4}>
                <Typography variant="subtitle2" color="text.secondary">
                  Incidents Shifts
                </Typography>
                <Typography variant="h4" color="error">
                  {selectedRun.incidents_shifts || 0}
                </Typography>
              </Grid>
              <Grid item xs={12} sm={4}>
                <Typography variant="subtitle2" color="text.secondary">
                  Waakdienst Shifts
                </Typography>
                <Typography variant="h4" color="primary">
                  {selectedRun.waakdienst_shifts || 0}
                </Typography>
              </Grid>
              {selectedRun.error_message && (
                <Grid item xs={12}>
                  <Alert severity="error">
                    <Typography variant="subtitle2">Error Message:</Typography>
                    <Typography variant="body2">{selectedRun.error_message}</Typography>
                  </Alert>
                </Grid>
              )}
            </Grid>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDetailsOpen(false)}>Close</Button>
          {selectedRun?.status === 'completed' && (
            <Button variant="contained" onClick={() => navigate('/calendar')}>
              View Calendar
            </Button>
          )}
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default OrchestratorHistory;
