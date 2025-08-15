import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Grid,
  Card,
  CardContent,
  CircularProgress,
  Alert,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  LinearProgress,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Stack,
  IconButton,
  Tooltip,
} from '@mui/material';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
} from 'recharts';
import { Refresh, Info } from '@mui/icons-material';
import { apiClient } from '../services/apiClient';
import { API_CONFIG } from '../config/api';

interface FairnessData {
  employee_name: string;
  employee_id: number;
  incidents_count: number;
  waakdienst_count: number;
  total_assignments: number;
  fairness_score: number; // legacy overall
  available_incidents: boolean;
  available_waakdienst: boolean;
  last_assignment_date: string | null;
  incidents_standby_count?: number;
  expected_hours?: number;
  deviation_hours?: number;
  // new per-type fields
  overall_fairness?: number | null;
  incidents_fairness?: number | null;
  standby_fairness?: number | null;
  waakdienst_fairness?: number | null;
  expected_incidents_hours?: number;
  deviation_incidents_hours?: number;
  expected_standby_hours?: number;
  deviation_standby_hours?: number;
  expected_waakdienst_hours?: number;
  deviation_waakdienst_hours?: number;
}

interface FairnessMetrics {
  total_employees: number;
  average_incidents: number;
  average_waakdienst: number;
  average_total: number;
  fairness_distribution: {
    excellent: number; // 90-100
    good: number; // 70-89
    fair: number; // 50-69
    poor: number; // 0-49
    na?: number; // no expectation and no assignments
  };
}

interface HistoricalData {
  date: string;
  employee_name: string;
  fairness_score: number;
}

const FairnessDashboard: React.FC = () => {
  const [fairnessData, setFairnessData] = useState<FairnessData[]>([]);
  const [metrics, setMetrics] = useState<FairnessMetrics | null>(null);
  const [historicalData, setHistoricalData] = useState<HistoricalData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [timeRange, setTimeRange] = useState('current_year');
  const [selectedEmployee, setSelectedEmployee] = useState<number | 'all'>('all');

  const loadFairnessData = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const params = new URLSearchParams({
        time_range: timeRange,
        employee: selectedEmployee.toString()
      });
      
      const data = await apiClient.get(`${API_CONFIG.ENDPOINTS.ORCHESTRATOR_FAIRNESS}?${params}`) as any;
      setFairnessData(data.employees || []);
      setMetrics(data.metrics || null);
      setHistoricalData(data.historical || []);
    } catch (err) {
      setError('Network error occurred');
      console.error('Fairness data error:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadFairnessData();
  }, [timeRange, selectedEmployee]);

  const getFairnessColor = (score: number) => {
    if (score >= 90) return 'success';
    if (score >= 70) return 'info';
    if (score >= 50) return 'warning';
    return 'error';
  };

  const getFairnessLabel = (score: number) => {
    if (score >= 90) return 'Excellent';
    if (score >= 70) return 'Good';
    if (score >= 50) return 'Fair';
    return 'Poor';
  };

  // Prepare chart data
  const chartData = fairnessData.map(emp => ({
    name: emp.employee_name.length > 10 ? emp.employee_name.substring(0, 10) + '...' : emp.employee_name,
    incidents: emp.incidents_count,
    incidents_standby: emp.incidents_standby_count || 0,
    waakdienst: emp.waakdienst_count,
    fairness: emp.fairness_score,
  }));

  const pieData = metrics ? [
    { name: 'Excellent (90-100)', value: metrics.fairness_distribution.excellent, color: '#4caf50' },
    { name: 'Good (70-89)', value: metrics.fairness_distribution.good, color: '#2196f3' },
    { name: 'Fair (50-69)', value: metrics.fairness_distribution.fair, color: '#ff9800' },
    { name: 'Poor (0-49)', value: metrics.fairness_distribution.poor, color: '#f44336' },
    ...(metrics.fairness_distribution.na !== undefined ? [{ name: 'N/A', value: metrics.fairness_distribution.na, color: '#9e9e9e' }] : []),
  ] : [];

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
          Fairness Dashboard
        </Typography>
        <Stack direction="row" spacing={2} alignItems="center">
          <FormControl size="small" sx={{ minWidth: 150 }}>
            <InputLabel>Time Range</InputLabel>
            <Select
              value={timeRange}
              onChange={(e) => setTimeRange(e.target.value)}
              label="Time Range"
            >
              <MenuItem value="current_year">Current Year</MenuItem>
              <MenuItem value="last_6_months">Last 6 Months</MenuItem>
              <MenuItem value="last_3_months">Last 3 Months</MenuItem>
              <MenuItem value="all_time">All Time</MenuItem>
            </Select>
          </FormControl>
          <FormControl size="small" sx={{ minWidth: 150 }}>
            <InputLabel>Employee</InputLabel>
            <Select
              value={selectedEmployee}
              onChange={(e) => setSelectedEmployee(e.target.value as number | 'all')}
              label="Employee"
            >
              <MenuItem value="all">All Employees</MenuItem>
              {fairnessData.map((emp) => (
                <MenuItem key={emp.employee_id} value={emp.employee_id}>
                  {emp.employee_name}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <Tooltip title="Refresh Data">
            <IconButton onClick={loadFairnessData}>
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

      {/* Metrics Overview */}
      {metrics && (
        <Grid container spacing={3} sx={{ mb: 3 }}>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Typography color="text.secondary" gutterBottom>
                  Total Employees
                </Typography>
                <Typography variant="h4">
                  {metrics.total_employees}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Typography color="text.secondary" gutterBottom>
                  Avg Incidents
                </Typography>
                <Typography variant="h4" color="error">
                  {metrics.average_incidents.toFixed(1)} hours
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Typography color="text.secondary" gutterBottom>
                  Avg Waakdienst
                </Typography>
                <Typography variant="h4" color="primary">
                  {metrics.average_waakdienst.toFixed(1)} hours
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Typography color="text.secondary" gutterBottom>
                  Avg Total
                </Typography>
                <Typography variant="h4" color="success.main">
                  {metrics.average_total.toFixed(1)} hours
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {metrics && metrics.total_employees > 0 && fairnessData.every(e => (e.total_assignments ?? 0) === 0) && (
        <Alert severity="info" sx={{ mb: 2 }}>
          No assignments found in the selected period. Try expanding the time range or verify that shifts have been generated/applied.
        </Alert>
      )}

      <Grid container spacing={3}>
        {/* Assignment Distribution Chart */}
        <Grid item xs={12} lg={8}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Assignment Distribution by Employee
            </Typography>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis />
                <RechartsTooltip />
                <Bar dataKey="incidents" fill="#f44336" name="Incidents (h)" />
                <Bar dataKey="incidents_standby" fill="#ff6d00" name="Standby (h)" />
                <Bar dataKey="waakdienst" fill="#2196f3" name="Waakdienst (h)" />
              </BarChart>
            </ResponsiveContainer>
          </Paper>
        </Grid>

        {/* Fairness Distribution Pie Chart */}
        <Grid item xs={12} lg={4}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Fairness Distribution
            </Typography>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={pieData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, value }: any) => `${name}: ${value}`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {pieData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <RechartsTooltip />
              </PieChart>
            </ResponsiveContainer>
          </Paper>
        </Grid>

        {/* Employee Details Table */}
        <Grid item xs={12}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Employee Fairness Details
            </Typography>
            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Employee</TableCell>
                    <TableCell align="center">Incidents (h)</TableCell>
                    <TableCell align="center">Standby (h)</TableCell>
                    <TableCell align="center">Waakdienst (h)</TableCell>
                    <TableCell align="center">Total (h)</TableCell>
                    <TableCell align="center">I Fair</TableCell>
                    <TableCell align="center">S Fair</TableCell>
                    <TableCell align="center">W Fair</TableCell>
                    <TableCell align="center">Overall</TableCell>
                    <TableCell align="center">I Δ (h)</TableCell>
                    <TableCell align="center">S Δ (h)</TableCell>
                    <TableCell align="center">W Δ (h)</TableCell>
                    <TableCell align="center">Availability</TableCell>
                    <TableCell align="center">Last Assignment</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {fairnessData.map((employee) => (
                    <TableRow key={employee.employee_id}>
                      <TableCell component="th" scope="row">
                        <Typography variant="body2" fontWeight="bold">
                          {employee.employee_name}
                        </Typography>
                      </TableCell>
                      <TableCell align="center">
                        <Chip
                          label={Number(employee.incidents_count ?? 0).toFixed(1)}
                          color="error"
                          variant="outlined"
                          size="small"
                        />
                      </TableCell>
                      <TableCell align="center">
                        <Chip
                          label={Number(employee.incidents_standby_count ?? 0).toFixed(1)}
                          color="warning"
                          variant="outlined"
                          size="small"
                        />
                      </TableCell>
                      <TableCell align="center">
                        <Chip
                          label={Number(employee.waakdienst_count ?? 0).toFixed(1)}
                          color="primary"
                          variant="outlined"
                          size="small"
                        />
                      </TableCell>
                      <TableCell align="center">
                        <Typography variant="body2" fontWeight="bold">
                          {Number(employee.total_assignments ?? 0).toFixed(1)}
                        </Typography>
                      </TableCell>
                      <TableCell align="center">
                        <Typography variant="body2" color="text.secondary">
                          {employee.expected_hours !== undefined ? employee.expected_hours.toFixed(1) : '—'}
                        </Typography>
                      </TableCell>
                      <TableCell align="center">
                        <Typography variant="body2" color={((employee.deviation_hours || 0) === 0 ? 'success.main' : (Math.abs(employee.deviation_hours || 0) <= 4 ? 'info.main' : Math.abs(employee.deviation_hours || 0) <= 12 ? 'warning.main' : 'error.main'))}>
                          {employee.deviation_hours !== undefined ? (employee.deviation_hours > 0 ? '+' : '') + employee.deviation_hours.toFixed(1) : '—'}
                        </Typography>
                      </TableCell>
                      <TableCell align="center">
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, justifyContent: 'center' }}>
                          <LinearProgress variant="determinate" value={employee.incidents_fairness ?? 0} color={getFairnessColor(employee.incidents_fairness ?? 0)} sx={{ width: 60, height: 8, borderRadius: 4 }} />
                          <Typography variant="body2">{employee.incidents_fairness != null ? Math.round(employee.incidents_fairness) : '—'}</Typography>
                        </Box>
                      </TableCell>
                      <TableCell align="center">
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, justifyContent: 'center' }}>
                          <LinearProgress variant="determinate" value={employee.standby_fairness ?? 0} color={getFairnessColor(employee.standby_fairness ?? 0)} sx={{ width: 60, height: 8, borderRadius: 4 }} />
                          <Typography variant="body2">{employee.standby_fairness != null ? Math.round(employee.standby_fairness) : '—'}</Typography>
                        </Box>
                      </TableCell>
                      <TableCell align="center">
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, justifyContent: 'center' }}>
                          <LinearProgress variant="determinate" value={employee.waakdienst_fairness ?? 0} color={getFairnessColor(employee.waakdienst_fairness ?? 0)} sx={{ width: 60, height: 8, borderRadius: 4 }} />
                          <Typography variant="body2">{employee.waakdienst_fairness != null ? Math.round(employee.waakdienst_fairness) : '—'}</Typography>
                        </Box>
                      </TableCell>
                      <TableCell align="center">
                        <Chip label={employee.overall_fairness != null ? Math.round(employee.overall_fairness) : 'N/A'} color={getFairnessColor(employee.overall_fairness ?? 0)} size="small" />
                      </TableCell>
                      <TableCell align="center">
                        <Typography variant="body2" color={((employee.deviation_incidents_hours || 0) === 0 ? 'success.main' : (Math.abs(employee.deviation_incidents_hours || 0) <= 4 ? 'info.main' : Math.abs(employee.deviation_incidents_hours || 0) <= 12 ? 'warning.main' : 'error.main'))}>
                          {employee.deviation_incidents_hours !== undefined ? (employee.deviation_incidents_hours > 0 ? '+' : '') + Number(employee.deviation_incidents_hours).toFixed(1) : '—'}
                        </Typography>
                      </TableCell>
                      <TableCell align="center">
                        <Typography variant="body2" color={((employee.deviation_standby_hours || 0) === 0 ? 'success.main' : (Math.abs(employee.deviation_standby_hours || 0) <= 4 ? 'info.main' : Math.abs(employee.deviation_standby_hours || 0) <= 12 ? 'warning.main' : 'error.main'))}>
                          {employee.deviation_standby_hours !== undefined ? (employee.deviation_standby_hours > 0 ? '+' : '') + Number(employee.deviation_standby_hours).toFixed(1) : '—'}
                        </Typography>
                      </TableCell>
                      <TableCell align="center">
                        <Typography variant="body2" color={((employee.deviation_waakdienst_hours || 0) === 0 ? 'success.main' : (Math.abs(employee.deviation_waakdienst_hours || 0) <= 12 ? 'info.main' : Math.abs(employee.deviation_waakdienst_hours || 0) <= 24 ? 'warning.main' : 'error.main'))}>
                          {employee.deviation_waakdienst_hours !== undefined ? (employee.deviation_waakdienst_hours > 0 ? '+' : '') + Number(employee.deviation_waakdienst_hours).toFixed(1) : '—'}
                        </Typography>
                      </TableCell>
                      <TableCell align="center">
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, justifyContent: 'center' }}>
                          <LinearProgress variant="determinate" value={employee.fairness_score} color={getFairnessColor(employee.fairness_score)} sx={{ width: 60, height: 8, borderRadius: 4 }} />
                          <Typography variant="body2">
                            {employee.fairness_score.toFixed(0)}
                          </Typography>
                        </Box>
                      </TableCell>
                      <TableCell align="center">
                        <Chip
                          label={getFairnessLabel(employee.fairness_score)}
                          color={getFairnessColor(employee.fairness_score)}
                          size="small"
                        />
                      </TableCell>
                      <TableCell align="center">
                        <Stack direction="row" spacing={0.5} justifyContent="center">
                          {employee.available_incidents && (
                            <Chip label="I" color="error" size="small" />
                          )}
                          {employee.available_waakdienst && (
                            <Chip label="W" color="primary" size="small" />
                          )}
                        </Stack>
                      </TableCell>
                      <TableCell align="center">
                        <Typography variant="body2" color="text.secondary">
                          {employee.last_assignment_date
                            ? new Date(employee.last_assignment_date).toLocaleDateString()
                            : 'Never'}
                        </Typography>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </Paper>
        </Grid>

        {/* Fairness Trend Over Time */}
        {historicalData.length > 0 && (
          <Grid item xs={12}>
            <Paper sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom>
                Fairness Trend Over Time
              </Typography>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={historicalData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" />
                  <YAxis />
                  <RechartsTooltip />
                  <Line
                    type="monotone"
                    dataKey="fairness_score"
                    stroke="#8884d8"
                    strokeWidth={2}
                  />
                </LineChart>
              </ResponsiveContainer>
            </Paper>
          </Grid>
        )}
      </Grid>

      {/* Help Information */}
      <Box sx={{ mt: 3 }}>
        <Alert severity="info" icon={<Info />}>
          <Typography variant="body2">
            <strong>Fairness scoring</strong> compares assigned hours to expected hours based on each person's availability. Score = 100 − percentage deviation. Columns show Expected (h) and Δ Hours. Standby is included in totals.
          </Typography>
        </Alert>
      </Box>
    </Box>
  );
};

export default FairnessDashboard;
