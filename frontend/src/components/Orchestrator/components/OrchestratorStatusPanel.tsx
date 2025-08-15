/**
 * Orchestrator Status Panel - Shows system health and monitoring information
 */

import React from 'react';
import {
  Box,
  Grid,
  Typography,
  Chip,
  LinearProgress,
  Card,
  CardContent,
  IconButton,
  Tooltip,
} from '@mui/material';
import {
  CheckCircle,
  Warning,
  Error,
  Refresh,
  Speed,
  Memory,
} from '@mui/icons-material';
import { useOrchestrator, useOrchestratorStatus } from '../../../hooks/useOrchestrator';
import { OrchestratorService } from '../../../services/orchestratorService';

const OrchestratorStatusPanel: React.FC = () => {
  const { refreshSystemHealth, refreshMetrics, state } = useOrchestrator();
  const { systemHealth, isSystemHealthy } = useOrchestratorStatus();

  const handleRefresh = async () => {
    try {
      await Promise.all([
        refreshSystemHealth(),
        refreshMetrics(),
      ]);
    } catch (error) {
      console.error('Failed to refresh status:', error);
    }
  };

  const getHealthIcon = (status: string) => {
    switch (status) {
      case 'healthy':
        return <CheckCircle color="success" />;
      case 'degraded':
        return <Warning color="warning" />;
      case 'unhealthy':
        return <Error color="error" />;
      default:
        return <Warning color="disabled" />;
    }
  };

  const getHealthColor = (status: string) => {
    switch (status) {
      case 'healthy':
        return 'success' as const;
      case 'degraded':
        return 'warning' as const;
      case 'unhealthy':
        return 'error' as const;
      default:
        return 'default' as const;
    }
  };

  const formatTimestamp = (timestamp?: string) => {
    if (!timestamp) return 'Unknown';
    return new Date(timestamp).toLocaleString();
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
        <Typography variant="h6">
          System Status
        </Typography>
        <Tooltip title="Refresh status">
          <IconButton onClick={handleRefresh} size="small">
            <Refresh />
          </IconButton>
        </Tooltip>
      </Box>

      <Grid container spacing={3}>
        {/* Overall Health */}
        <Grid item xs={12} md={4}>
          <Card sx={{ height: '100%' }}>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                {getHealthIcon(systemHealth?.status || 'unknown')}
                <Typography variant="h6">
                  Overall Health
                </Typography>
              </Box>
              <Chip
                label={systemHealth?.status?.toUpperCase() || 'UNKNOWN'}
                color={getHealthColor(systemHealth?.status || 'unknown')}
                sx={{ mb: 1 }}
              />
              <Typography variant="body2" color="text.secondary">
                Last updated: {formatTimestamp(systemHealth?.timestamp)}
              </Typography>
              {systemHealth?.response_time_ms && (
                <Typography variant="body2" color="text.secondary">
                  Response time: {systemHealth.response_time_ms}ms
                </Typography>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Component Status */}
        <Grid item xs={12} md={4}>
          <Card sx={{ height: '100%' }}>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                <Memory />
                <Typography variant="h6">
                  Components
                </Typography>
              </Box>
              {systemHealth?.components ? (
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                  {Object.entries(systemHealth.components).map(([component, status]) => (
                    <Box key={component} sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <Typography variant="body2" sx={{ textTransform: 'capitalize' }}>
                        {component}
                      </Typography>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                        {getHealthIcon(status)}
                        <Typography variant="body2" color="text.secondary">
                          {status}
                        </Typography>
                      </Box>
                    </Box>
                  ))}
                </Box>
              ) : (
                <Typography variant="body2" color="text.secondary">
                  No component data available
                </Typography>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Performance Metrics */}
        <Grid item xs={12} md={4}>
          <Card sx={{ height: '100%' }}>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                <Speed />
                <Typography variant="h6">
                  Performance
                </Typography>
              </Box>
              {state.systemMetrics ? (
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                  <Box>
                    <Typography variant="body2" color="text.secondary">
                      Assignment Rate (30d)
                    </Typography>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <LinearProgress
                        variant="determinate"
                        value={state.systemMetrics.assignment_rate_percentage}
                        sx={{ flexGrow: 1 }}
                      />
                      <Typography variant="body2">
                        {state.systemMetrics.assignment_rate_percentage.toFixed(1)}%
                      </Typography>
                    </Box>
                  </Box>
                  
                  <Box>
                    <Typography variant="body2" color="text.secondary">
                      Avg. Orchestration Time
                    </Typography>
                    <Typography variant="body1">
                      {state.systemMetrics.average_orchestration_time_seconds 
                        ? OrchestratorService.formatDuration(state.systemMetrics.average_orchestration_time_seconds)
                        : 'N/A'
                      }
                    </Typography>
                  </Box>

                  <Box>
                    <Typography variant="body2" color="text.secondary">
                      Total Shifts (30d)
                    </Typography>
                    <Typography variant="body1">
                      {state.systemMetrics.total_shifts_last_30_days?.toLocaleString() || 'N/A'}
                    </Typography>
                  </Box>
                </Box>
              ) : (
                <Typography variant="body2" color="text.secondary">
                  No performance data available
                </Typography>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* System Information */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                System Information
              </Typography>
              <Grid container spacing={2}>
                <Grid item xs={12} sm={6} md={3}>
                  <Typography variant="body2" color="text.secondary">
                    Version
                  </Typography>
                  <Typography variant="body1">
                    {systemHealth?.version || 'Unknown'}
                  </Typography>
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                  <Typography variant="body2" color="text.secondary">
                    Active Employees
                  </Typography>
                  <Typography variant="body1">
                    {state.systemMetrics?.total_active_employees || 'N/A'}
                  </Typography>
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                  <Typography variant="body2" color="text.secondary">
                    Unassigned Shifts (30d)
                  </Typography>
                  <Typography variant="body1">
                    {state.systemMetrics?.unassigned_shifts_last_30_days || 'N/A'}
                  </Typography>
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                  <Typography variant="body2" color="text.secondary">
                    Status
                  </Typography>
                  <Chip
                    label={isSystemHealthy ? 'Operational' : 'Issues Detected'}
                    color={isSystemHealthy ? 'success' : 'warning'}
                    size="small"
                  />
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default OrchestratorStatusPanel;
