/**
 * Orchestrator Dashboard - Main interface for orchestrator operations
 * Provides comprehensive orchestrator functionality with clean architecture integration
 */

import React, { useState, useEffect } from 'react';
import {
  Box,
  Container,
  Tabs,
  Tab,
  Paper,
  Alert,
  CircularProgress,
  Grid,
  Card,
  CardContent,
  Typography,
  Chip,
  Button,
  Divider,
} from '@mui/material';
import {
  Refresh,
  AutoAwesome,
  Assessment,
  People,
  CalendarToday,
  HealthAndSafety,
  ManageHistory,
} from '@mui/icons-material';
import { useOrchestrator } from '../../hooks/useOrchestrator';
import { OrchestratorService } from '../../services/orchestratorService';
import ScheduleOrchestratorForm from './components/ScheduleOrchestratorForm';
import AssignmentHistoryReset from './components/AssignmentHistoryReset';

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
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

const OrchestratorDashboard: React.FC = () => {
  const {
    state,
    isLoading,
    hasError,
    isOrchestrationRunning,
    hasLastOrchestration,
    isSystemHealthy,
    refreshSystemHealth,
    refreshMetrics,
    clearError,
    getOrchestrationSummary,
  } = useOrchestrator();

  const [currentTab, setCurrentTab] = useState(0);
  const [autoRefresh] = useState(true);

  // Auto-refresh system health and metrics
  useEffect(() => {
    const refreshData = async () => {
      try {
        await Promise.all([
          refreshSystemHealth(),
          refreshMetrics(),
        ]);
      } catch (error) {
        console.error('Failed to refresh system data:', error);
      }
    };

    // Initial load
    refreshData();

    // Set up auto-refresh
    if (autoRefresh) {
      const interval = setInterval(refreshData, 30000); // Every 30 seconds
      return () => clearInterval(interval);
    }
  }, [autoRefresh, refreshSystemHealth, refreshMetrics]);

  const handleTabChange = (_event: React.SyntheticEvent, newValue: number) => {
    setCurrentTab(newValue);
  };

  const handleRefreshClick = async () => {
    try {
      await Promise.all([
        refreshSystemHealth(),
        refreshMetrics(),
      ]);
    } catch (error) {
      console.error('Failed to refresh data:', error);
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

  return (
    <Container maxWidth="xl" sx={{ py: 3 }}>
      {/* Header */}
      <Box sx={{ mb: 3 }}>
        <Grid container alignItems="center" justifyContent="space-between">
          <Grid item>
            <Typography variant="h4" component="h1" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <AutoAwesome color="primary" />
              Orchestrator Dashboard
            </Typography>
            <Typography variant="subtitle1" color="text.secondary">
              Intelligent shift scheduling and management
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
                onClick={handleRefreshClick}
                disabled={isLoading}
              >
                Refresh
              </Button>
            </Box>
          </Grid>
        </Grid>
      </Box>

      {/* Error Alert */}
      {hasError && (
        <Alert 
          severity="error" 
          sx={{ mb: 3 }}
          onClose={clearError}
        >
          {state.error}
        </Alert>
      )}

      {/* Status Panel */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            System Status
          </Typography>
          <Typography variant="body2" color="text.secondary">
            System status panel will be integrated here once import issues are resolved.
          </Typography>
        </CardContent>
      </Card>

      {/* Quick Stats */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Paper sx={{ p: 2, textAlign: 'center' }}>
            <Typography variant="h6" color="primary">
              {state.systemMetrics?.total_active_employees || 0}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Active Employees
            </Typography>
          </Paper>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Paper sx={{ p: 2, textAlign: 'center' }}>
            <Typography variant="h6" color="primary">
              {state.systemMetrics?.assignment_rate_percentage?.toFixed(1) || 0}%
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Assignment Rate
            </Typography>
          </Paper>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Paper sx={{ p: 2, textAlign: 'center' }}>
            <Typography variant="h6" color="primary">
              {hasLastOrchestration ? state.lastOrchestration?.statistics.assignments_made || 0 : 0}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Last Assignments
            </Typography>
          </Paper>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Paper sx={{ p: 2, textAlign: 'center' }}>
            <Typography variant="h6" color="primary">
              {state.systemMetrics?.unassigned_shifts_last_30_days || 0}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Unassigned (30d)
            </Typography>
          </Paper>
        </Grid>
      </Grid>

      {/* Main Content Tabs */}
      <Card>
        <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
          <Tabs value={currentTab} onChange={handleTabChange} aria-label="orchestrator tabs">
            <Tab icon={<AutoAwesome />} label="Schedule" />
            <Tab icon={<Assessment />} label="Coverage" />
            <Tab icon={<People />} label="Availability" />
            <Tab icon={<CalendarToday />} label="Results" />
            <Tab icon={<ManageHistory />} label="Management" />
          </Tabs>
        </Box>

        <TabPanel value={currentTab} index={0}>
          <ScheduleOrchestratorForm />
        </TabPanel>

        <TabPanel value={currentTab} index={1}>
          <Typography variant="h6" gutterBottom>
            Coverage Analysis
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Coverage analysis component will be integrated here once import issues are resolved.
          </Typography>
        </TabPanel>

        <TabPanel value={currentTab} index={2}>
          <Typography variant="h6" gutterBottom>
            Employee Availability
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Availability checker component will be integrated here once import issues are resolved.
          </Typography>
        </TabPanel>

        <TabPanel value={currentTab} index={3}>
          <Typography variant="h6" gutterBottom>
            Assignment Results
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Assignment summary component will be integrated here once import issues are resolved.
          </Typography>
        </TabPanel>

        <TabPanel value={currentTab} index={4}>
          <AssignmentHistoryReset />
        </TabPanel>
      </Card>

      {/* Recent Activity */}
      {hasLastOrchestration && (
        <Card sx={{ mt: 3 }}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Recent Orchestration
            </Typography>
            <Divider sx={{ mb: 2 }} />
            
            <Grid container spacing={2}>
              <Grid item xs={12} md={6}>
                <Typography variant="body2" color="text.secondary">
                  Summary
                </Typography>
                <Typography variant="body1">
                  {getOrchestrationSummary()}
                </Typography>
              </Grid>
              <Grid item xs={12} md={6}>
                <Typography variant="body2" color="text.secondary">
                  Execution Time
                </Typography>
                <Typography variant="body1">
                  {state.lastOrchestration?.execution_time 
                    ? OrchestratorService.formatDuration(state.lastOrchestration.execution_time)
                    : 'Unknown'
                  }
                </Typography>
              </Grid>
            </Grid>

            {state.lastOrchestration?.warnings && state.lastOrchestration.warnings.length > 0 && (
              <Box sx={{ mt: 2 }}>
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  Warnings
                </Typography>
                {state.lastOrchestration.warnings.map((warning, index) => (
                  <Alert key={index} severity="warning" sx={{ mb: 1 }}>
                    {warning}
                  </Alert>
                ))}
              </Box>
            )}
          </CardContent>
        </Card>
      )}

      {/* Loading Overlay */}
      {isLoading && (
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
              {isOrchestrationRunning ? 'Running Orchestration...' : 'Loading...'}
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

export default OrchestratorDashboard;
