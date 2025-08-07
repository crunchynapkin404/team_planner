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
  fairness_score: number;
  available_incidents: boolean;
  available_waakdienst: boolean;
  last_assignment_date: string | null;
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
    waakdienst: emp.waakdienst_count,
    fairness: emp.fairness_score,
  }));

  const pieData = metrics ? [
    { name: 'Excellent (90-100)', value: metrics.fairness_distribution.excellent, color: '#4caf50' },
    { name: 'Good (70-89)', value: metrics.fairness_distribution.good, color: '#2196f3' },
    { name: 'Fair (50-69)', value: metrics.fairness_distribution.fair, color: '#ff9800' },
    { name: 'Poor (0-49)', value: metrics.fairness_distribution.poor, color: '#f44336' },
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
                  {metrics.average_incidents.toFixed(1)}
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
                  {metrics.average_waakdienst.toFixed(1)}
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
                  {metrics.average_total.toFixed(1)}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
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
                <Bar dataKey="incidents" fill="#f44336" name="Incidents" />
                <Bar dataKey="waakdienst" fill="#2196f3" name="Waakdienst" />
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
                    <TableCell align="center">Incidents</TableCell>
                    <TableCell align="center">Waakdienst</TableCell>
                    <TableCell align="center">Total</TableCell>
                    <TableCell align="center">Fairness Score</TableCell>
                    <TableCell align="center">Status</TableCell>
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
                          label={employee.incidents_count}
                          color="error"
                          variant="outlined"
                          size="small"
                        />
                      </TableCell>
                      <TableCell align="center">
                        <Chip
                          label={employee.waakdienst_count}
                          color="primary"
                          variant="outlined"
                          size="small"
                        />
                      </TableCell>
                      <TableCell align="center">
                        <Typography variant="body2" fontWeight="bold">
                          {employee.total_assignments}
                        </Typography>
                      </TableCell>
                      <TableCell align="center">
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <LinearProgress
                            variant="determinate"
                            value={employee.fairness_score}
                            color={getFairnessColor(employee.fairness_score)}
                            sx={{ width: 60, height: 8, borderRadius: 4 }}
                          />
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
            <strong>Fairness Scoring:</strong> Excellent (90-100) = Perfect distribution, 
            Good (70-89) = Minor imbalance, Fair (50-69) = Moderate imbalance, 
            Poor (0-49) = Significant imbalance requiring attention.
          </Typography>
        </Alert>
      </Box>
    </Box>
  );
};

export default FairnessDashboard;
