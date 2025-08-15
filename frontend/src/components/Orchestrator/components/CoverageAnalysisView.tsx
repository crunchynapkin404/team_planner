/**
 * Coverage Analysis View - Shows shift coverage analysis
 */

import React, { useState } from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  Button,
  TextField,
  CircularProgress,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  Alert,
} from '@mui/material';
import { Analytics, Refresh, CalendarToday } from '@mui/icons-material';
import { useOrchestrator } from '../../../hooks/useOrchestrator';

const CoverageAnalysisView: React.FC = () => {
  const { 
    getCoverageForCurrentWeek, 
    getCoverageForNextWeek, 
    getCoverage,
    state,
    getCoverageSummary,
  } = useOrchestrator();

  const [dateRange, setDateRange] = useState({
    startDate: '',
    endDate: '',
  });
  const [isLoading, setIsLoading] = useState(false);

  const handleQuickCoverage = async (type: 'current' | 'next') => {
    setIsLoading(true);
    try {
      if (type === 'current') {
        await getCoverageForCurrentWeek();
      } else {
        await getCoverageForNextWeek();
      }
    } catch (error) {
      console.error('Failed to get coverage:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCustomCoverage = async () => {
    if (!dateRange.startDate || !dateRange.endDate) return;
    
    setIsLoading(true);
    try {
      await getCoverage({
        start_date: dateRange.startDate,
        end_date: dateRange.endDate,
      });
    } catch (error) {
      console.error('Failed to get coverage:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const renderCoverageTable = () => {
    if (!state.coverageData) return null;

    const coverageByDate = state.coverageData.coverage_by_date;
    const dates = Object.keys(coverageByDate).sort();

    return (
      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Date</TableCell>
              <TableCell>Shift Type</TableCell>
              <TableCell align="center">Total Shifts</TableCell>
              <TableCell align="center">Assigned</TableCell>
              <TableCell align="center">Unassigned</TableCell>
              <TableCell align="center">Coverage</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {dates.map(date => (
              Object.entries(coverageByDate[date]).map(([shiftType, coverage]) => (
                <TableRow key={`${date}-${shiftType}`}>
                  <TableCell>{date}</TableCell>
                  <TableCell sx={{ textTransform: 'capitalize' }}>{shiftType}</TableCell>
                  <TableCell align="center">{coverage.total_shifts}</TableCell>
                  <TableCell align="center">{coverage.assigned_shifts}</TableCell>
                  <TableCell align="center">{coverage.unassigned_shifts}</TableCell>
                  <TableCell align="center">
                    <Chip
                      label={`${Math.round((coverage.assigned_shifts / coverage.total_shifts) * 100)}%`}
                      color={coverage.unassigned_shifts === 0 ? 'success' : 'warning'}
                      size="small"
                    />
                  </TableCell>
                </TableRow>
              ))
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    );
  };

  return (
    <Box sx={{ maxWidth: 1000, mx: 'auto' }}>
      <Typography variant="h5" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <Analytics color="primary" />
        Coverage Analysis
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Analyze shift coverage for different time periods
      </Typography>

      <Grid container spacing={3}>
        {/* Quick Actions */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Quick Analysis
              </Typography>
              <Grid container spacing={2}>
                <Grid item xs={12} sm={4}>
                  <Button
                    fullWidth
                    variant="contained"
                    startIcon={<CalendarToday />}
                    onClick={() => handleQuickCoverage('current')}
                    disabled={isLoading}
                  >
                    Current Week
                  </Button>
                </Grid>
                <Grid item xs={12} sm={4}>
                  <Button
                    fullWidth
                    variant="outlined"
                    startIcon={<CalendarToday />}
                    onClick={() => handleQuickCoverage('next')}
                    disabled={isLoading}
                  >
                    Next Week
                  </Button>
                </Grid>
                <Grid item xs={12} sm={4}>
                  <Button
                    fullWidth
                    variant="outlined"
                    startIcon={<Refresh />}
                    onClick={() => handleQuickCoverage('current')}
                    disabled={isLoading}
                  >
                    Refresh
                  </Button>
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        </Grid>

        {/* Custom Date Range */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Custom Date Range
              </Typography>
              <Grid container spacing={2} alignItems="end">
                <Grid item xs={12} sm={4}>
                  <TextField
                    fullWidth
                    label="Start Date"
                    type="date"
                    value={dateRange.startDate}
                    onChange={(e) => setDateRange(prev => ({ ...prev, startDate: e.target.value }))}
                    InputLabelProps={{ shrink: true }}
                  />
                </Grid>
                <Grid item xs={12} sm={4}>
                  <TextField
                    fullWidth
                    label="End Date"
                    type="date"
                    value={dateRange.endDate}
                    onChange={(e) => setDateRange(prev => ({ ...prev, endDate: e.target.value }))}
                    InputLabelProps={{ shrink: true }}
                  />
                </Grid>
                <Grid item xs={12} sm={4}>
                  <Button
                    fullWidth
                    variant="contained"
                    onClick={handleCustomCoverage}
                    disabled={isLoading || !dateRange.startDate || !dateRange.endDate}
                  >
                    Analyze Coverage
                  </Button>
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        </Grid>

        {/* Results */}
        {isLoading && (
          <Grid item xs={12}>
            <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
              <CircularProgress />
            </Box>
          </Grid>
        )}

        {state.coverageData && !isLoading && (
          <>
            {/* Summary */}
            <Grid item xs={12}>
              <Alert severity="info">
                {getCoverageSummary()}
              </Alert>
            </Grid>

            {/* Coverage Table */}
            <Grid item xs={12}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Coverage Details
                  </Typography>
                  {renderCoverageTable()}
                </CardContent>
              </Card>
            </Grid>
          </>
        )}

        {!state.coverageData && !isLoading && (
          <Grid item xs={12}>
            <Box sx={{ textAlign: 'center', py: 4 }}>
              <Typography variant="body1" color="text.secondary">
                No coverage data available. Click one of the analysis buttons to load data.
              </Typography>
            </Box>
          </Grid>
        )}
      </Grid>
    </Box>
  );
};

export default CoverageAnalysisView;
