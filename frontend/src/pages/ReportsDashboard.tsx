/**
 * Reports Dashboard - Main page for viewing all reports
 */
import React, { useState, useEffect } from 'react';
import {
  Box,
  Container,
  Typography,
  Paper,
  Tabs,
  Tab,
  Grid,
  Card,
  CardContent,
  CardActions,
  Button,
  TextField,
  MenuItem,
  Alert,
  CircularProgress,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
} from '@mui/material';
import {
  Assessment as AssessmentIcon,
  BarChart as BarChartIcon,
  EventNote as EventNoteIcon,
  SwapHoriz as SwapIcon,
  AccessTime as HoursIcon,
  Weekend as WeekendIcon,
} from '@mui/icons-material';
import { reportService, type ReportFilters } from '../services/reportService';
import { apiClient } from '../services/apiClient';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`report-tabpanel-${index}`}
      aria-labelledby={`report-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

interface Team {
  id: number;
  name: string;
}

interface Department {
  id: number;
  name: string;
}

export default function ReportsDashboard() {
  const [activeTab, setActiveTab] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [teams, setTeams] = useState<Team[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);

  // Common filters
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [selectedTeam, setSelectedTeam] = useState<number | ''>('');
  const [selectedDepartment, setSelectedDepartment] = useState<number | ''>('');
  const [selectedYear, setSelectedYear] = useState(new Date().getFullYear());

  // Report data
  const [scheduleData, setScheduleData] = useState<any>(null);
  const [fairnessData, setFairnessData] = useState<any>(null);
  const [leaveBalanceData, setLeaveBalanceData] = useState<any>(null);
  const [swapHistoryData, setSwapHistoryData] = useState<any>(null);
  const [employeeHoursData, setEmployeeHoursData] = useState<any>(null);
  const [weekendHolidayData, setWeekendHolidayData] = useState<any>(null);

  // Load teams and departments
  useEffect(() => {
    const loadFilters = async () => {
      try {
        const [teamsRes, deptsRes]: any = await Promise.all([
          apiClient.get('/teams/'),
          apiClient.get('/departments/'),
        ]);
        // Handle both paginated and non-paginated responses
        const teamsData = Array.isArray(teamsRes) ? teamsRes : (teamsRes?.results || []);
        const deptsData = Array.isArray(deptsRes) ? deptsRes : (deptsRes?.results || []);
        setTeams(teamsData);
        setDepartments(deptsData);
      } catch (err) {
        console.error('Failed to load filter data:', err);
      }
    };
    loadFilters();
  }, []);

  const handleTabChange = (_event: React.SyntheticEvent, newValue: number) => {
    setActiveTab(newValue);
    setError(null);
  };

  const buildFilters = (): ReportFilters => ({
    start_date: startDate || undefined,
    end_date: endDate || undefined,
    team_id: selectedTeam || undefined,
    department_id: selectedDepartment || undefined,
    year: selectedYear,
  });

  const loadScheduleReport = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await reportService.getScheduleReport(buildFilters());
      setScheduleData(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load schedule report');
    } finally {
      setLoading(false);
    }
  };

  const loadFairnessReport = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await reportService.getFairnessReport(buildFilters());
      setFairnessData(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load fairness report');
    } finally {
      setLoading(false);
    }
  };

  const loadLeaveBalanceReport = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await reportService.getLeaveBalanceReport(buildFilters());
      setLeaveBalanceData(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load leave balance report');
    } finally {
      setLoading(false);
    }
  };

  const loadSwapHistoryReport = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await reportService.getSwapHistoryReport(buildFilters());
      setSwapHistoryData(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load swap history report');
    } finally {
      setLoading(false);
    }
  };

  const loadEmployeeHoursReport = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await reportService.getEmployeeHoursReport(buildFilters());
      setEmployeeHoursData(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load employee hours report');
    } finally {
      setLoading(false);
    }
  };

  const loadWeekendHolidayReport = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await reportService.getWeekendHolidayReport(buildFilters());
      setWeekendHolidayData(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load weekend/holiday report');
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString();
  };

  return (
    <Container maxWidth="xl" sx={{ mt: 4, mb: 4 }}>
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <AssessmentIcon fontSize="large" />
          Reports & Analytics
        </Typography>
        <Typography variant="body1" color="text.secondary">
          View detailed reports on schedules, fairness, leave balances, and more
        </Typography>
      </Box>

      <Paper sx={{ mb: 3 }}>
        <Tabs value={activeTab} onChange={handleTabChange} aria-label="report tabs">
          <Tab icon={<EventNoteIcon />} label="Schedule" />
          <Tab icon={<BarChartIcon />} label="Fairness" />
          <Tab icon={<AssessmentIcon />} label="Leave Balance" />
          <Tab icon={<SwapIcon />} label="Swap History" />
          <Tab icon={<HoursIcon />} label="Employee Hours" />
          <Tab icon={<WeekendIcon />} label="Weekend/Holiday" />
        </Tabs>
      </Paper>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {/* Common Filters */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          Filters
        </Typography>
        <Grid container spacing={2}>
          <Grid item xs={12} sm={6} md={3}>
            <TextField
              label="Start Date"
              type="date"
              fullWidth
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              InputLabelProps={{ shrink: true }}
            />
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <TextField
              label="End Date"
              type="date"
              fullWidth
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              InputLabelProps={{ shrink: true }}
            />
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <TextField
              select
              label="Team"
              fullWidth
              value={selectedTeam}
              onChange={(e) => setSelectedTeam(e.target.value as number | '')}
            >
              <MenuItem value="">All Teams</MenuItem>
              {teams.map((team) => (
                <MenuItem key={team.id} value={team.id}>
                  {team.name}
                </MenuItem>
              ))}
            </TextField>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <TextField
              select
              label="Department"
              fullWidth
              value={selectedDepartment}
              onChange={(e) => setSelectedDepartment(e.target.value as number | '')}
            >
              <MenuItem value="">All Departments</MenuItem>
              {departments.map((dept) => (
                <MenuItem key={dept.id} value={dept.id}>
                  {dept.name}
                </MenuItem>
              ))}
            </TextField>
          </Grid>
        </Grid>
      </Paper>

      {/* Schedule Report */}
      <TabPanel value={activeTab} index={0}>
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Schedule Report
            </Typography>
            <Typography variant="body2" color="text.secondary" paragraph>
              View all scheduled shifts for a specific date range
            </Typography>
            {scheduleData && (
              <Box sx={{ mt: 2 }}>
                <Grid container spacing={2} sx={{ mb: 2 }}>
                  <Grid item xs={12} sm={4}>
                    <Chip label={`Total Shifts: ${scheduleData.total_shifts}`} color="primary" />
                  </Grid>
                  <Grid item xs={12} sm={4}>
                    <Chip label={`From: ${formatDate(scheduleData.start_date)}`} />
                  </Grid>
                  <Grid item xs={12} sm={4}>
                    <Chip label={`To: ${formatDate(scheduleData.end_date)}`} />
                  </Grid>
                </Grid>
                <TableContainer>
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>Date</TableCell>
                        <TableCell>Employee</TableCell>
                        <TableCell>Shift Type</TableCell>
                        <TableCell>Time</TableCell>
                        <TableCell>Status</TableCell>
                        <TableCell>Auto</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {scheduleData.shifts.map((shift: any) => (
                        <TableRow key={shift.id}>
                          <TableCell>{formatDate(shift.date)}</TableCell>
                          <TableCell>{shift.employee_name}</TableCell>
                          <TableCell>{shift.shift_type}</TableCell>
                          <TableCell>
                            {shift.start_time} - {shift.end_time}
                          </TableCell>
                          <TableCell>
                            <Chip label={shift.status} size="small" color="default" />
                          </TableCell>
                          <TableCell>{shift.auto_assigned ? '✓' : '-'}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              </Box>
            )}
          </CardContent>
          <CardActions>
            <Button
              variant="contained"
              onClick={loadScheduleReport}
              disabled={loading}
              startIcon={loading ? <CircularProgress size={20} /> : null}
            >
              Generate Report
            </Button>
          </CardActions>
        </Card>
      </TabPanel>

      {/* Fairness Report */}
      <TabPanel value={activeTab} index={1}>
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Fairness Distribution Report
            </Typography>
            <Typography variant="body2" color="text.secondary" paragraph>
              Analyze shift distribution equity across employees
            </Typography>
            {fairnessData && (
              <Box sx={{ mt: 2 }}>
                <Grid container spacing={2} sx={{ mb: 2 }}>
                  <Grid item xs={12} sm={3}>
                    <Chip label={`Employees: ${fairnessData.employee_count}`} color="primary" />
                  </Grid>
                  <Grid item xs={12} sm={3}>
                    <Chip label={`Avg Hours/FTE: ${fairnessData.average_hours_per_fte}`} />
                  </Grid>
                  <Grid item xs={12} sm={3}>
                    <Chip label={`Variance: ${fairnessData.variance}`} color="warning" />
                  </Grid>
                  <Grid item xs={12} sm={3}>
                    <Chip label={`From: ${formatDate(fairnessData.start_date)}`} />
                  </Grid>
                </Grid>
                <TableContainer>
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>Employee</TableCell>
                        <TableCell>FTE</TableCell>
                        <TableCell>Total Shifts</TableCell>
                        <TableCell>Total Hours</TableCell>
                        <TableCell>Incidents</TableCell>
                        <TableCell>Waakdienst</TableCell>
                        <TableCell>Hours/FTE</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {fairnessData.distribution.map((emp: any) => (
                        <TableRow key={emp.employee_id}>
                          <TableCell>{emp.employee_name}</TableCell>
                          <TableCell>{emp.fte}</TableCell>
                          <TableCell>{emp.total_shifts}</TableCell>
                          <TableCell>{emp.total_hours.toFixed(1)}</TableCell>
                          <TableCell>{emp.incidents_count}</TableCell>
                          <TableCell>{emp.waakdienst_count}</TableCell>
                          <TableCell>
                            <strong>{emp.hours_per_fte.toFixed(1)}</strong>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              </Box>
            )}
          </CardContent>
          <CardActions>
            <Button
              variant="contained"
              onClick={loadFairnessReport}
              disabled={loading}
              startIcon={loading ? <CircularProgress size={20} /> : null}
            >
              Generate Report
            </Button>
          </CardActions>
        </Card>
      </TabPanel>

      {/* Leave Balance Report */}
      <TabPanel value={activeTab} index={2}>
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Leave Balance Report
            </Typography>
            <Typography variant="body2" color="text.secondary" paragraph>
              View employee leave balances for the year
            </Typography>
            <Box sx={{ mb: 2 }}>
              <TextField
                label="Year"
                type="number"
                value={selectedYear}
                onChange={(e) => setSelectedYear(parseInt(e.target.value))}
                sx={{ width: 150 }}
              />
            </Box>
            {leaveBalanceData && (
              <Box sx={{ mt: 2 }}>
                <Chip label={`Total Balances: ${leaveBalanceData.total_balances}`} color="primary" sx={{ mb: 2 }} />
                <TableContainer>
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>Employee</TableCell>
                        <TableCell>Leave Type</TableCell>
                        <TableCell>Total Days</TableCell>
                        <TableCell>Used Days</TableCell>
                        <TableCell>Remaining</TableCell>
                        <TableCell>Status</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {leaveBalanceData.balances.map((balance: any, index: number) => (
                        <TableRow key={index}>
                          <TableCell>{balance.employee_name}</TableCell>
                          <TableCell>{balance.leave_type}</TableCell>
                          <TableCell>{balance.total_days}</TableCell>
                          <TableCell>{balance.used_days}</TableCell>
                          <TableCell>
                            <strong>{balance.remaining_days}</strong>
                          </TableCell>
                          <TableCell>
                            {balance.is_exhausted ? (
                              <Chip label="Exhausted" size="small" color="error" />
                            ) : (
                              <Chip label="Available" size="small" color="success" />
                            )}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              </Box>
            )}
          </CardContent>
          <CardActions>
            <Button
              variant="contained"
              onClick={loadLeaveBalanceReport}
              disabled={loading}
              startIcon={loading ? <CircularProgress size={20} /> : null}
            >
              Generate Report
            </Button>
          </CardActions>
        </Card>
      </TabPanel>

      {/* Swap History Report */}
      <TabPanel value={activeTab} index={3}>
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Swap History Report
            </Typography>
            <Typography variant="body2" color="text.secondary" paragraph>
              Track shift swap requests and their outcomes
            </Typography>
            {swapHistoryData && (
              <Box sx={{ mt: 2 }}>
                <Grid container spacing={2} sx={{ mb: 2 }}>
                  <Grid item xs={12} sm={3}>
                    <Chip label={`Total: ${swapHistoryData.total_swaps}`} color="primary" />
                  </Grid>
                  <Grid item xs={12} sm={3}>
                    <Chip label={`Approved: ${swapHistoryData.approved_count}`} color="success" />
                  </Grid>
                  <Grid item xs={12} sm={3}>
                    <Chip label={`Rejected: ${swapHistoryData.rejected_count}`} color="error" />
                  </Grid>
                  <Grid item xs={12} sm={3}>
                    <Chip label={`Rate: ${swapHistoryData.approval_rate}%`} color="info" />
                  </Grid>
                </Grid>
                <TableContainer>
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>Created</TableCell>
                        <TableCell>Requesting</TableCell>
                        <TableCell>Target</TableCell>
                        <TableCell>Req. Shift Date</TableCell>
                        <TableCell>Target Shift Date</TableCell>
                        <TableCell>Status</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {swapHistoryData.swaps.map((swap: any) => (
                        <TableRow key={swap.id}>
                          <TableCell>{formatDate(swap.created_date)}</TableCell>
                          <TableCell>{swap.requesting_employee}</TableCell>
                          <TableCell>{swap.target_employee}</TableCell>
                          <TableCell>{formatDate(swap.requesting_shift_date)}</TableCell>
                          <TableCell>{swap.target_shift_date ? formatDate(swap.target_shift_date) : 'N/A'}</TableCell>
                          <TableCell>
                            <Chip 
                              label={swap.status} 
                              size="small" 
                              color={swap.status === 'Approved' ? 'success' : swap.status === 'Rejected' ? 'error' : 'default'}
                            />
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              </Box>
            )}
          </CardContent>
          <CardActions>
            <Button
              variant="contained"
              onClick={loadSwapHistoryReport}
              disabled={loading}
              startIcon={loading ? <CircularProgress size={20} /> : null}
            >
              Generate Report
            </Button>
          </CardActions>
        </Card>
      </TabPanel>

      {/* Employee Hours Report */}
      <TabPanel value={activeTab} index={4}>
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Employee Hours Report
            </Typography>
            <Typography variant="body2" color="text.secondary" paragraph>
              Track hours worked by each employee
            </Typography>
            {employeeHoursData && (
              <Box sx={{ mt: 2 }}>
                <Grid container spacing={2} sx={{ mb: 2 }}>
                  <Grid item xs={12} sm={4}>
                    <Chip label={`Employees: ${employeeHoursData.employee_count}`} color="primary" />
                  </Grid>
                  <Grid item xs={12} sm={4}>
                    <Chip label={`Total Hours: ${employeeHoursData.total_hours.toFixed(1)}`} color="info" />
                  </Grid>
                  <Grid item xs={12} sm={4}>
                    <Chip label={`From: ${formatDate(employeeHoursData.start_date)}`} />
                  </Grid>
                </Grid>
                <TableContainer>
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>Employee</TableCell>
                        <TableCell>Total Hours</TableCell>
                        <TableCell>Incidents Hours</TableCell>
                        <TableCell>Waakdienst Hours</TableCell>
                        <TableCell>Shift Count</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {employeeHoursData.hours.map((emp: any) => (
                        <TableRow key={emp.employee_id}>
                          <TableCell>{emp.employee_name}</TableCell>
                          <TableCell>
                            <strong>{emp.total_hours.toFixed(1)}</strong>
                          </TableCell>
                          <TableCell>{emp.incidents_hours.toFixed(1)}</TableCell>
                          <TableCell>{emp.waakdienst_hours.toFixed(1)}</TableCell>
                          <TableCell>{emp.shift_count}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              </Box>
            )}
          </CardContent>
          <CardActions>
            <Button
              variant="contained"
              onClick={loadEmployeeHoursReport}
              disabled={loading}
              startIcon={loading ? <CircularProgress size={20} /> : null}
            >
              Generate Report
            </Button>
          </CardActions>
        </Card>
      </TabPanel>

      {/* Weekend/Holiday Report */}
      <TabPanel value={activeTab} index={5}>
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Weekend & Holiday Distribution
            </Typography>
            <Typography variant="body2" color="text.secondary" paragraph>
              Analyze weekend and holiday shift distribution
            </Typography>
            {weekendHolidayData && (
              <Box sx={{ mt: 2 }}>
                <Grid container spacing={2} sx={{ mb: 2 }}>
                  <Grid item xs={12} sm={4}>
                    <Chip label={`Employees: ${weekendHolidayData.employee_count}`} color="primary" />
                  </Grid>
                  <Grid item xs={12} sm={4}>
                    <Chip label={`Weekend Shifts: ${weekendHolidayData.total_weekend_shifts}`} color="warning" />
                  </Grid>
                  <Grid item xs={12} sm={4}>
                    <Chip label={`Holiday Shifts: ${weekendHolidayData.total_holiday_shifts}`} color="error" />
                  </Grid>
                </Grid>
                <TableContainer>
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>Employee</TableCell>
                        <TableCell>Weekend Shifts</TableCell>
                        <TableCell>Holiday Shifts</TableCell>
                        <TableCell>Total Special</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {weekendHolidayData.distribution.map((emp: any) => (
                        <TableRow key={emp.employee_id}>
                          <TableCell>{emp.employee_name}</TableCell>
                          <TableCell>{emp.weekend_shifts}</TableCell>
                          <TableCell>{emp.holiday_shifts}</TableCell>
                          <TableCell>
                            <strong>{emp.total_special_shifts}</strong>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              </Box>
            )}
          </CardContent>
          <CardActions>
            <Button
              variant="contained"
              onClick={loadWeekendHolidayReport}
              disabled={loading}
              startIcon={loading ? <CircularProgress size={20} /> : null}
            >
              Generate Report
            </Button>
          </CardActions>
        </Card>
      </TabPanel>
    </Container>
  );
}
