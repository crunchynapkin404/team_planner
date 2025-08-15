/**
 * Assignment Summary - Shows orchestration results and current assignments
 */

import React, { useState, useEffect } from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Alert,
  LinearProgress,
  IconButton,
  Tooltip,
} from '@mui/material';
import {
  Assignment,
  Person,
  ExpandMore,
  CheckCircle,
  Error,
  Refresh,
} from '@mui/icons-material';
import { useOrchestrator } from '../../../hooks/useOrchestrator';

const AssignmentSummary: React.FC = () => {
  const { state, refreshSystemHealth } = useOrchestrator();
  const [expandedAccordion, setExpandedAccordion] = useState<string | false>(false);

  useEffect(() => {
    // Refresh system health on component mount
    refreshSystemHealth();
  }, [refreshSystemHealth]);

  const handleAccordionChange = (panel: string) => (
    _event: React.SyntheticEvent,
    isExpanded: boolean
  ) => {
    setExpandedAccordion(isExpanded ? panel : false);
  };

  const getResultIcon = (success: boolean) => {
    if (success) {
      return <CheckCircle color="success" />;
    } else {
      return <Error color="error" />;
    }
  };

  const formatDateTime = (dateTimeString: string) => {
    return new Date(dateTimeString).toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const renderLatestResult = () => {
    if (!state.lastOrchestration) {
      return (
        <Box sx={{ textAlign: 'center', py: 4 }}>
          <Typography variant="body1" color="text.secondary">
            No recent orchestration results available.
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Run a schedule orchestration to see results here.
          </Typography>
        </Box>
      );
    }

    const result = state.lastOrchestration;
    
    return (
      <Card>
        <CardContent>
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
            <Typography variant="h6" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              {getResultIcon(result.success)}
              Latest Orchestration Result
            </Typography>
            <Box sx={{ display: 'flex', gap: 1 }}>
              <Chip
                label={result.success ? 'Success' : 'Failed'}
                color={result.success ? 'success' : 'error'}
                size="small"
              />
              <Tooltip title="Refresh system health">
                <IconButton size="small" onClick={refreshSystemHealth}>
                  <Refresh />
                </IconButton>
              </Tooltip>
            </Box>
          </Box>

          {result.warnings && result.warnings.length > 0 && (
            <Alert severity="warning" sx={{ mb: 2 }}>
              {result.warnings.length} warning(s) found during orchestration
            </Alert>
          )}

          <Grid container spacing={2}>
            <Grid item xs={12} sm={6} md={3}>
              <Typography variant="body2" color="text.secondary">
                Assignments Made
              </Typography>
              <Typography variant="body1">
                {result.statistics.assignments_made}
              </Typography>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <Typography variant="body2" color="text.secondary">
                Unassigned Shifts
              </Typography>
              <Typography variant="body1">
                {result.statistics.unassigned_shifts}
              </Typography>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <Typography variant="body2" color="text.secondary">
                Conflicts Detected
              </Typography>
              <Typography variant="body1">
                {result.statistics.conflicts_detected}
              </Typography>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <Typography variant="body2" color="text.secondary">
                Execution Time
              </Typography>
              <Typography variant="body1">
                {result.execution_time ? `${result.execution_time.toFixed(2)}s` : 'N/A'}
              </Typography>
            </Grid>
          </Grid>

          {result.assignments && result.assignments.length > 0 && (
            <Accordion
              expanded={expandedAccordion === 'assignments'}
              onChange={handleAccordionChange('assignments')}
              sx={{ mt: 2 }}
            >
              <AccordionSummary expandIcon={<ExpandMore />}>
                <Typography variant="subtitle1">
                  View Assignments ({result.assignments.length})
                </Typography>
              </AccordionSummary>
              <AccordionDetails>
                <TableContainer component={Paper} variant="outlined">
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>Employee</TableCell>
                        <TableCell>Shift Type</TableCell>
                        <TableCell>Start Time</TableCell>
                        <TableCell>End Time</TableCell>
                        <TableCell>Auto Assigned</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {result.assignments.map((assignment: any, index: number) => (
                        <TableRow key={assignment.assignment_id || index}>
                          <TableCell>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                              <Person fontSize="small" />
                              {assignment.employee_name || `Employee ${assignment.employee_id}`}
                            </Box>
                          </TableCell>
                          <TableCell>
                            <Chip
                              label={assignment.shift_type}
                              size="small"
                              variant="outlined"
                            />
                          </TableCell>
                          <TableCell>
                            {assignment.start_datetime ? formatDateTime(assignment.start_datetime) : 'N/A'}
                          </TableCell>
                          <TableCell>
                            {assignment.end_datetime ? formatDateTime(assignment.end_datetime) : 'N/A'}
                          </TableCell>
                          <TableCell>
                            <Chip
                              label={assignment.auto_assigned ? 'Auto' : 'Manual'}
                              size="small"
                              color={assignment.auto_assigned ? 'primary' : 'default'}
                            />
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              </AccordionDetails>
            </Accordion>
          )}

          {result.conflicts && result.conflicts.length > 0 && (
            <Accordion
              expanded={expandedAccordion === 'conflicts'}
              onChange={handleAccordionChange('conflicts')}
              sx={{ mt: 1 }}
            >
              <AccordionSummary expandIcon={<ExpandMore />}>
                <Typography variant="subtitle1" color="error">
                  Conflicts ({result.conflicts.length})
                </Typography>
              </AccordionSummary>
              <AccordionDetails>
                {result.conflicts.map((conflict: any, index: number) => (
                  <Alert key={conflict.conflict_id || index} severity={conflict.severity || 'error'} sx={{ mb: 1 }}>
                    <Typography variant="subtitle2">
                      {conflict.type.replace(/_/g, ' ').toUpperCase()}
                    </Typography>
                    <Typography variant="body2">
                      {conflict.description}
                    </Typography>
                  </Alert>
                ))}
              </AccordionDetails>
            </Accordion>
          )}

          {result.warnings && result.warnings.length > 0 && (
            <Accordion
              expanded={expandedAccordion === 'warnings'}
              onChange={handleAccordionChange('warnings')}
              sx={{ mt: 1 }}
            >
              <AccordionSummary expandIcon={<ExpandMore />}>
                <Typography variant="subtitle1" color="warning.main">
                  Warnings ({result.warnings.length})
                </Typography>
              </AccordionSummary>
              <AccordionDetails>
                {result.warnings.map((warning: string, index: number) => (
                  <Alert key={index} severity="warning" sx={{ mb: 1 }}>
                    {warning}
                  </Alert>
                ))}
              </AccordionDetails>
            </Accordion>
          )}
        </CardContent>
      </Card>
    );
  };

  const renderSystemSummary = () => {
    const health = state.systemHealth;
    const metrics = state.systemMetrics;
    
    if (!health && !metrics) {
      return (
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              System Summary
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Loading system data...
            </Typography>
            <LinearProgress sx={{ mt: 2 }} />
          </CardContent>
        </Card>
      );
    }

    return (
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            System Summary
          </Typography>
          
          <Grid container spacing={2}>
            <Grid item xs={12} sm={6} md={3}>
              <Box sx={{ textAlign: 'center', p: 2, bgcolor: 'primary.light', borderRadius: 1 }}>
                <Typography variant="h4" color="primary.contrastText">
                  {health?.status === 'healthy' ? '✓' : '✗'}
                </Typography>
                <Typography variant="body2" color="primary.contrastText">
                  System Health
                </Typography>
              </Box>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <Box sx={{ textAlign: 'center', p: 2, bgcolor: 'success.light', borderRadius: 1 }}>
                <Typography variant="h4" color="success.contrastText">
                  {metrics?.total_active_employees || 0}
                </Typography>
                <Typography variant="body2" color="success.contrastText">
                  Active Employees
                </Typography>
              </Box>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <Box sx={{ textAlign: 'center', p: 2, bgcolor: 'warning.light', borderRadius: 1 }}>
                <Typography variant="h4" color="warning.contrastText">
                  {metrics?.unassigned_shifts_last_30_days || 0}
                </Typography>
                <Typography variant="body2" color="warning.contrastText">
                  Unassigned Shifts
                </Typography>
              </Box>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <Box sx={{ textAlign: 'center', p: 2, bgcolor: 'info.light', borderRadius: 1 }}>
                <Typography variant="h4" color="info.contrastText">
                  {metrics?.assignment_rate_percentage ? `${metrics.assignment_rate_percentage.toFixed(1)}%` : 'N/A'}
                </Typography>
                <Typography variant="body2" color="info.contrastText">
                  Assignment Rate
                </Typography>
              </Box>
            </Grid>
          </Grid>

          {health?.timestamp && (
            <Box sx={{ mt: 3, p: 2, bgcolor: 'grey.50', borderRadius: 1 }}>
              <Typography variant="subtitle2" gutterBottom>
                Last Health Check
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {formatDateTime(health.timestamp)}
              </Typography>
            </Box>
          )}
        </CardContent>
      </Card>
    );
  };

  return (
    <Box sx={{ maxWidth: 1200, mx: 'auto' }}>
      <Typography variant="h5" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <Assignment color="primary" />
        Assignment Summary
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        View orchestration results, current assignments, and system summary
      </Typography>

      <Grid container spacing={3}>
        {/* System Summary */}
        <Grid item xs={12}>
          {renderSystemSummary()}
        </Grid>

        {/* Latest Orchestration Result */}
        <Grid item xs={12}>
          {renderLatestResult()}
        </Grid>
      </Grid>
    </Box>
  );
};

export default AssignmentSummary;
